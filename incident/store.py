from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
import json
import sqlite3
import threading


class Store:
    def __init__(self, path=":memory:"):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.lock = threading.RLock()
        self.db.execute("PRAGMA journal_mode=WAL")
        self._schema()

    def _schema(self):
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS incidents(id TEXT PRIMARY KEY,tenant TEXT NOT NULL,body TEXT NOT NULL)"
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

    def _get(self, tenant, key):
        row = self.db.execute(
            "SELECT body FROM incidents WHERE tenant=? AND id=?", (tenant, key)
        ).fetchone()
        if row is None:
            raise LookupError("Incident not found")
        return json.loads(row[0])

    def create(self, incident):
        with self.transaction():
            self.db.execute(
                "INSERT INTO incidents VALUES(?,?,?)",
                (
                    incident["id"],
                    incident["tenant"],
                    json.dumps(incident, allow_nan=False),
                ),
            )
        return deepcopy(incident)

    def get(self, tenant, key):
        with self.lock:
            return self._get(tenant, key)

    def mutate(self, tenant, key, change, expected_revision=None):
        with self.transaction():
            current = self._get(tenant, key)
            if (
                expected_revision is not None
                and current["revision"] != expected_revision
            ):
                raise ValueError("Incident revision changed; reload before continuing")
            changed = deepcopy(current)
            change(changed)
            if changed["id"] != key or changed["tenant"] != tenant:
                raise ValueError("Incident identity cannot change")
            changed["revision"] = current["revision"] + 1
            self.db.execute(
                "UPDATE incidents SET body=? WHERE tenant=? AND id=?",
                (json.dumps(changed, allow_nan=False), tenant, key),
            )
            return changed

    def list(self, tenant, limit=50):
        if not 1 <= limit <= 100:
            raise ValueError("Queue limit must be between 1 and 100")
        with self.lock:
            rows = self.db.execute(
                "SELECT body FROM incidents WHERE tenant=?", (tenant,)
            ).fetchall()
            incidents = sorted(
                (json.loads(row[0]) for row in rows),
                key=lambda item: (item["created_at"], item["id"]),
                reverse=True,
            )
            return incidents[:limit]

    def close(self):
        with self.lock:
            self.db.close()
