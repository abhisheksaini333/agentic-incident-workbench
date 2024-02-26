from contextlib import contextmanager
from pathlib import Path
import json
import sqlite3
import threading
from .identity import identifier
from .evidence import digest
from .plans import validate_step
from .scenarios import FAULTS, healthy_state, observation


class Simulator:
    def __init__(self, path=":memory:"):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.lock = threading.RLock()
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS services(tenant TEXT,service TEXT,body TEXT NOT NULL,PRIMARY KEY(tenant,service))"
        )

        self.db.execute(
            "CREATE TABLE IF NOT EXISTS receipts(tenant TEXT,key TEXT,body TEXT NOT NULL,PRIMARY KEY(tenant,key))"
        )

    @contextmanager
    def transaction(self):
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                yield
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise

    def _state(self, tenant, service):
        row = self.db.execute(
            "SELECT body FROM services WHERE tenant=? AND service=?", (tenant, service)
        ).fetchone()
        if row is None:
            raise LookupError("Simulated service not found")
        return json.loads(row[0])

    def _save(self, tenant, service, state):
        self.db.execute(
            "UPDATE services SET body=? WHERE tenant=? AND service=?",
            (json.dumps(state), tenant, service),
        )

    def provision(self, tenant, service):
        identifier(tenant)
        identifier(service)
        with self.transaction():
            self.db.execute(
                "INSERT OR IGNORE INTO services VALUES(?,?,?)",
                (tenant, service, json.dumps(healthy_state())),
            )
        return self.observe(tenant, service)

    def inject(self, tenant, service, faults, variant=0):
        if (
            not isinstance(faults, list)
            or len(faults) > 3
            or len(set(faults)) != len(faults)
            or not set(faults).issubset(FAULTS)
        ):
            raise ValueError("Choose up to three distinct known fault families")
        if type(variant) is not int or not 0 <= variant <= 1:
            raise ValueError("Unknown fault variant")
        with self.transaction():
            state = self._state(tenant, service)
            state.update(
                faults=list(faults), variant=variant, generation=state["generation"] + 1
            )
            self._save(tenant, service, state)
            return observation(state)

    def observe(self, tenant, service):
        with self.lock:
            return observation(self._state(tenant, service))

    def apply(self, tenant, service, step, key, expected_generation):
        checked = validate_step(step, service)
        if (
            not isinstance(key, str)
            or not 16 <= len(key) <= 100
            or type(expected_generation) is not int
        ):
            raise ValueError("Invalid effect identity or generation")
        request_digest = digest(
            {
                "tenant": tenant,
                "service": service,
                "step": checked,
                "generation": expected_generation,
            }
        )
        with self.transaction():
            previous = self.db.execute(
                "SELECT body FROM receipts WHERE tenant=? AND key=?", (tenant, key)
            ).fetchone()
            if previous:
                receipt = json.loads(previous[0])
                if receipt["request_digest"] != request_digest:
                    raise ValueError("Effect key is already bound to another request")
                return receipt
            state = self._state(tenant, service)
            if state["generation"] != expected_generation:
                raise ValueError("Service evidence is stale; collect it again")
            fault = next(
                name
                for name, spec in FAULTS.items()
                if spec["action"] == checked["action"]
            )
            changed = fault in state["faults"]
            if changed:
                state["faults"].remove(fault)
            state["effects"] += 1
            state["generation"] += 1
            receipt = {
                "key": key,
                "request_digest": request_digest,
                "action": checked["action"],
                "generation_before": expected_generation,
                "generation_after": state["generation"],
                "changed": changed,
                "effect_number": state["effects"],
            }
            self._save(tenant, service, state)
            self.db.execute(
                "INSERT INTO receipts VALUES(?,?,?)", (tenant, key, json.dumps(receipt))
            )
            return receipt

    def receipt(self, tenant, key):
        with self.lock:
            row = self.db.execute(
                "SELECT body FROM receipts WHERE tenant=? AND key=?", (tenant, key)
            ).fetchone()
            return json.loads(row[0]) if row else None

    def workload(self, tenant, service):
        current = self.observe(tenant, service)
        return {
            "ok": current["healthy"],
            "status": 200 if current["healthy"] else 503,
            "generation": current["generation"],
            "message": "Request completed"
            if current["healthy"]
            else "Service cannot complete the request",
        }

    def prometheus(self, tenant, service):
        identifier(tenant)
        identifier(service)
        current = self.observe(tenant, service)
        return (
            "\n".join(
                f'incident_demo_{name}{{tenant="{tenant}",service="{service}"}} {value}'
                for name, value in sorted(current["metrics"].items())
            )
            + "\n"
        )

    def close(self):
        self.db.close()
