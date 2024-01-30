from contextlib import contextmanager
from pathlib import Path
import json
import sqlite3
import threading
from .identity import identifier
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

    def close(self):
        self.db.close()
