"""Compare all approaches on identical simulator cases, outside the live schema."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import time
import uuid
import psycopg2
from psycopg2 import sql
from .identity import Actor
from .postgres import PostgresStore
from .model_client import ModelClient, REVISION
from .simulator_client import SimulatorClient
from .runners import runner_for
from .workflow import Workflow


def summarize(rows):
    result = {}
    for mode in ("rules", "single", "graph"):
        group = [row for row in rows if row["mode"] == mode]
        if not group:
            continue
        latencies = sorted(row["seconds"] for row in group)
        result[mode] = {
            "cases": len(group),
            "recovered": sum(row["recovered"] for row in group),
            "unnecessary_actions": sum(row["unnecessary_actions"] for row in group),
            "effects": sum(row["effects"] for row in group),
            "model_calls": sum(row["model_calls"] for row in group),
            "input_tokens": sum(row["input_tokens"] for row in group),
            "output_tokens": sum(row["output_tokens"] for row in group),
            "median_seconds": statistics.median(latencies),
            "p95_seconds": latencies[max(0, int(len(latencies) * 0.95 + 0.999) - 1)],
            "statuses": dict(Counter(row["status"] for row in group)),
        }
    return result


def run_case(store, tools, model, case, mode, prefix):
    tenant = prefix + "-" + mode + "-" + case["id"]
    operator = Actor(tenant, tenant + ".operator", frozenset({"operator"}))
    reviewer = Actor(tenant, tenant + ".reviewer", frozenset({"approver"}))
    for actor in (operator, reviewer):
        store.add_account(
            {
                "tenant": tenant,
                "subject": actor.subject,
                "roles": sorted(actor.roles),
                "password_hash": "evaluation-only-no-login",
            }
        )
    tools.provision(tenant, "checkout")
    tools.inject(tenant, "checkout", case["faults"], case["variant"])
    flow = Workflow(store)
    item = flow.create(
        operator, "checkout", "Evaluation " + case["id"], time.time(), mode=mode
    )
    started = time.monotonic()
    runner = runner_for(store, tools, item, model)
    item = runner.run_until_pause(tenant, item["id"])
    if item["status"] == "awaiting_approval":
        # Explicit benchmark reviewer: this is controlled lab authorization,
        # not autonomous approval in the user-facing application.
        item = flow.approve(
            reviewer, item["id"], item["plan"]["digest"], item["revision"], time.time()
        )
        item = runner_for(store, tools, item, model).run_until_pause(tenant, item["id"])
    elapsed = time.monotonic() - started
    workload = tools.workload(tenant, "checkout")
    return {
        "case": case["id"],
        "mode": mode,
        "faults": case["faults"],
        "status": item["status"],
        "recovered": item["status"] == "resolved" and workload["ok"],
        "seconds": elapsed,
        "unnecessary_actions": sum(
            not receipt["changed"] for receipt in item["receipts"]
        ),
        "effects": len(item["receipts"]),
        "model_calls": item["budget"]["model_calls"],
        "input_tokens": sum(record["input_tokens"] for record in item["model_results"]),
        "output_tokens": sum(
            record["output_tokens"] for record in item["model_results"]
        ),
        "workload": workload,
        "incident": item,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--split", choices=["calibration", "held_out"], default="held_out"
    )
    args = parser.parse_args()
    corpus_path = Path(__file__).resolve().parents[1] / "fixtures/evaluation.json"
    corpus = json.loads(corpus_path.read_text())
    url = os.environ["DATABASE_URL"]
    schema = "comparison_" + uuid.uuid4().hex
    connection = psycopg2.connect(url)
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    store = PostgresStore(url, schema)
    tools = SimulatorClient(
        os.environ["SIMULATOR_URL"],
        os.environ["SIMULATOR_KEY"],
        os.environ["SIMULATOR_ADMIN_KEY"],
    )
    model = ModelClient(os.environ["MODEL_URL"], os.environ["MODEL_KEY"])
    rows = []
    prefix = "eval-" + uuid.uuid4().hex[:6]
    try:
        for case in corpus[args.split]:
            # Rotate mode order to reduce systematic warm-cache/order bias.
            modes = ["rules", "single", "graph"]
            offset = len(rows) // 3 % 3
            for mode in modes[offset:] + modes[:offset]:
                row = run_case(store, tools, model, case, mode, prefix)
                rows.append(row)
                print(
                    case["id"],
                    mode,
                    row["status"],
                    round(row["seconds"], 3),
                    flush=True,
                )
        report = {
            "schema_version": 1,
            "split": args.split,
            "corpus_sha256": hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
            "model_revision": REVISION,
            "hardware": {
                "platform": platform.platform(),
                "logical_cpus": os.cpu_count(),
                "model_threads": 2,
            },
            "database_schema": schema,
            "summary": summarize(rows),
            "rows": rows,
            "limitations": [
                "Original bounded simulator, not production incident quality",
                "One measured run per case; no statistical significance claim",
                "Benchmark reviewer approves supported plans; real users require independent approval",
                "All modes share the same metrics, action authority and verification gates",
            ],
        }
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n")
    finally:
        model.close()
        tools.close()
        store.close()
        connection.close()
    # Preserve the disposable schema for independent inspection. It is isolated
    # from the application public schema and can be removed explicitly later.


if __name__ == "__main__":
    main()
