from copy import deepcopy
import json
from .approval import approved
from .evidence import digest
from .identity import Actor, require
from .trace import append_event
from .budgets import Limits, charge


class EffectJournal:
    def __init__(self, store, limits=None):
        self.store = store
        self.limits = limits or Limits()

    def _authorized(self, incident, lease, now):
        if not self.store.owns_lease(incident, lease, now):
            raise ValueError("Worker lease expired or was replaced")
        if incident["status"] not in {"approved", "executing"} or not approved(
            incident, now
        ):
            raise ValueError("A current exact approval is required")
        account = self.store.account(incident["approval"]["subject"])
        if not account or account["tenant"] != incident["tenant"]:
            raise PermissionError("Approver no longer has access")
        require(
            Actor(account["tenant"], account["subject"], frozenset(account["roles"])),
            "approve",
        )

    def _read(self, tenant, key):
        row = self.store.db.execute(
            "SELECT body FROM outbox WHERE tenant=? AND key=?", (tenant, key)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def _write_incident(self, incident):
        incident["revision"] += 1
        self.store.db.execute(
            "UPDATE incidents SET body=? WHERE tenant=? AND id=?",
            (json.dumps(incident, allow_nan=False), incident["tenant"], incident["id"]),
        )

    def prepare(self, tenant, incident_id, lease, index, now):
        with self.store.transaction():
            incident = self.store._get(tenant, incident_id)
            self._authorized(incident, lease, now)
            plan = incident["plan"]
            if type(index) is not int or not 0 <= index < len(plan["steps"]):
                raise ValueError("Unknown plan action")
            key = digest(
                {
                    "tenant": tenant,
                    "incident": incident_id,
                    "plan_digest": plan["digest"],
                    "index": index,
                }
            )
            previous = self._read(tenant, key)
            if previous:
                return previous
            if index != len(
                [
                    r
                    for r in incident["receipts"]
                    if r.get("plan_digest") == plan["digest"]
                ]
            ):
                raise ValueError("Earlier actions must be acknowledged first")
            step = deepcopy(plan["steps"][index])
            generation = plan["generation"] + index
            entry = {
                "key": key,
                "incident_id": incident_id,
                "tenant": tenant,
                "service": incident["service"],
                "plan_digest": plan["digest"],
                "plan_version": plan["version"],
                "index": index,
                "step": step,
                "generation": generation,
                "created_at": now,
                "status": "pending",
                "attempts": 0,
                "receipt": None,
                "request_digest": digest(
                    {
                        "tenant": tenant,
                        "service": incident["service"],
                        "step": step,
                        "generation": generation,
                    }
                ),
            }
            incident["budget"] = charge(incident["budget"], self.limits, "effect", 0)
            incident["status"] = "executing"
            append_event(
                incident,
                "effect_prepared",
                "executor",
                "Approved action recorded before dispatch: " + step["action"],
                now,
            )
            self.store.db.execute(
                "INSERT INTO outbox VALUES(?,?,?,?)",
                (key, tenant, incident_id, json.dumps(entry)),
            )
            self._write_incident(incident)
            return entry

    def pending(self, tenant, incident_id):
        with self.store.lock:
            rows = self.store.db.execute(
                "SELECT body FROM outbox WHERE tenant=? AND incident_id=?",
                (tenant, incident_id),
            ).fetchall()
            return [
                entry
                for row in rows
                if (entry := json.loads(row[0]))["status"] == "pending"
            ]
