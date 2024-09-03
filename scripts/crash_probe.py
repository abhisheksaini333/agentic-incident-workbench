"""Actual process-kill/restart acceptance against disposable PostgreSQL and HTTP tools."""
import argparse
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psycopg2
from psycopg2 import sql
from incident.postgres import PostgresStore
from incident.simulator_client import SimulatorClient
from incident.model_client import ModelClient
from incident.runners import runner_for
from incident.workflow import Workflow
from incident.identity import Actor
from incident.effects import EffectJournal


def clients(schema):
    store = PostgresStore(os.environ["DATABASE_URL"], schema)
    tools = SimulatorClient(
        os.environ["SIMULATOR_URL"],
        os.environ["SIMULATOR_KEY"],
        os.environ["SIMULATOR_ADMIN_KEY"],
    )
    model = ModelClient(os.environ["MODEL_URL"], os.environ["MODEL_KEY"])
    return store, tools, model


def child(schema, tenant, key, mode):
    store, tools, model = clients(schema)
    kwargs = {"after_effect": lambda: os._exit(91)} if mode == "effect-crash" else {}
    item = store.get(tenant, key)
    result = runner_for(store, tools, item, model, **kwargs).run_until_pause(
        tenant, key
    )
    print(
        json.dumps({"status": result["status"], "revision": result["revision"]}),
        flush=True,
    )
    if mode == "pause":
        while True:
            time.sleep(1)
    model.close()
    tools.close()
    store.close()


def launch(schema, tenant, key, mode):
    return subprocess.Popen(
        [
            sys.executable,
            __file__,
            "--child",
            mode,
            "--schema",
            schema,
            "--tenant",
            tenant,
            "--incident",
            key,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def main(output):
    schema = "crash_" + uuid.uuid4().hex
    tenant = "crash-" + uuid.uuid4().hex[:10]
    connection = psycopg2.connect(os.environ["DATABASE_URL"])
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    store, tools, model = clients(schema)
    operator = Actor(tenant, tenant + ".operator", frozenset({"operator"}))
    reviewer = Actor(tenant, tenant + ".reviewer", frozenset({"approver"}))
    for actor in (operator, reviewer):
        store.add_account(
            {
                "tenant": tenant,
                "subject": actor.subject,
                "roles": sorted(actor.roles),
                "password_hash": "probe-only-no-login",
            }
        )
    tools.provision(tenant, "checkout")
    tools.inject(tenant, "checkout", ["memory_pressure"], 1)
    flow = Workflow(store)
    item = flow.create(
        operator, "checkout", "Durable crash acceptance", time.time(), mode="graph"
    )
    key = item["id"]
    process = launch(schema, tenant, key, "pause")
    try:
        assert select.select([process.stdout], [], [], 30)[
            0
        ], "Worker did not pause in time"
        paused = json.loads(process.stdout.readline())
        assert paused["status"] == "awaiting_approval", paused
        process.kill()
        process.wait(timeout=5)
        assert process.returncode == -signal.SIGKILL
        pending = store.get(tenant, key)
        assert pending["revision"] == paused["revision"] and not pending["receipts"]
        flow.approve(
            reviewer, key, pending["plan"]["digest"], pending["revision"], time.time()
        )
        effect_process = launch(schema, tenant, key, "effect-crash")
        stdout, stderr = effect_process.communicate(timeout=30)
        assert effect_process.returncode == 91, stderr
        before = store.get(tenant, key)
        journal = EffectJournal(store)
        uncertain = journal.pending(tenant, key)
        assert len(uncertain) == 1 and not before["receipts"]
        receipt = tools.receipt(tenant, "checkout", uncertain[0]["key"])
        assert receipt["effect_number"] == 1 and receipt["changed"]
        print(
            "Worker killed while waiting; second process exited after external effect. Waiting for real lease expiry.",
            flush=True,
        )
        expiry = before["lease"]["expires_at"]
        while time.time() <= expiry:
            time.sleep(min(1, max(0.01, expiry - time.time() + 0.01)))
        recovered = launch(schema, tenant, key, "recover")
        stdout, stderr = recovered.communicate(timeout=30)
        assert recovered.returncode == 0, stderr
        after = store.get(tenant, key)
        assert after["status"] == "resolved" and len(after["receipts"]) == 1
        assert not journal.pending(tenant, key)
        runner_for(store, tools, after, model).run_until_pause(tenant, key)
        replay = tools.receipt(tenant, "checkout", uncertain[0]["key"])
        assert replay == receipt and replay["effect_number"] == 1
        assert tools.workload(tenant, "checkout")["ok"]
        report = {
            "passed": True,
            "schema": schema,
            "incident_id": key,
            "pending_decision_kill": "SIGKILL",
            "post_effect_process_exit": 91,
            "model_calls_before_kill": pending["budget"]["model_calls"],
            "model_calls_after_resume": after["budget"]["model_calls"],
            "external_effects": replay["effect_number"],
            "durable_receipts": len(after["receipts"]),
            "real_lease_expiry_waited": True,
            "final_status": after["status"],
            "incident": after,
        }
        Path(output).write_text(json.dumps(report, indent=2) + "\n")
        print(
            "Actual PostgreSQL + HTTP + model process-crash acceptance passed",
            flush=True,
        )
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        store.close()
        tools.close()
        model.close()
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/process-crash.json")
    parser.add_argument("--child", choices=["pause", "effect-crash", "recover"])
    parser.add_argument("--schema")
    parser.add_argument("--tenant")
    parser.add_argument("--incident")
    args = parser.parse_args()
    if args.child:
        child(args.schema, args.tenant, args.incident, args.child)
    else:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        main(args.output)
