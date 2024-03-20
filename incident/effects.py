from copy import deepcopy
import json
import time
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

    def _accept(self, entry, receipt, now):
        if (
            receipt.get("key") != entry["key"]
            or receipt.get("request_digest") != entry["request_digest"]
            or receipt.get("action") != entry["step"]["action"]
            or receipt.get("generation_before") != entry["generation"]
            or receipt.get("generation_after") != entry["generation"] + 1
            or type(receipt.get("effect_number")) is not int
            or receipt["effect_number"] < 1
            or type(receipt.get("changed")) is not bool
        ):
            raise ValueError("Simulator receipt does not match the prepared request")
        current = self._read(entry["tenant"], entry["key"])
        if current["status"] == "delivered":
            if current["receipt"] != receipt:
                raise ValueError("Simulator replay changed its receipt")
            return receipt
        incident = self.store._get(entry["tenant"], entry["incident_id"])
        current.update(status="delivered", receipt=deepcopy(receipt))
        self.store.db.execute(
            "UPDATE outbox SET body=? WHERE tenant=? AND key=?",
            (json.dumps(current), entry["tenant"], entry["key"]),
        )
        incident["receipts"].append(
            {**deepcopy(receipt), "plan_digest": entry["plan_digest"]}
        )
        append_event(
            incident,
            "effect_acknowledged",
            "executor",
            "Simulator receipt recorded: " + entry["step"]["action"],
            now,
        )
        self._write_incident(incident)
        return receipt

    def reconcile(self, entry, client, now):
        receipt = client.receipt(entry["tenant"], entry["service"], entry["key"])
        if receipt is None:
            return None
        with self.store.transaction():
            return self._accept(entry, receipt, now)

    def _reserve_attempt(self, entry, lease, now):
        with self.store.transaction():
            incident = self.store._get(entry["tenant"], entry["incident_id"])
            self._authorized(incident, lease, now)
            if incident["plan"]["digest"] != entry["plan_digest"]:
                raise ValueError("Prepared action belongs to an older plan")
            current = self._read(entry["tenant"], entry["key"])
            if current["attempts"] >= 3:
                raise ValueError("Effect retry budget exhausted")
            current["attempts"] += 1
            self.store.db.execute(
                "UPDATE outbox SET body=? WHERE tenant=? AND key=?",
                (json.dumps(current), entry["tenant"], entry["key"]),
            )

    def dispatch(self, entry, lease, client, now, after_effect=None):
        started = time.monotonic()
        current_time = lambda: now + time.monotonic() - started
        reconciled = self.reconcile(entry, client, current_time())
        if reconciled is not None:
            return reconciled
        self._reserve_attempt(entry, lease, current_time())
        with self.store.transaction():
            incident = self.store._get(entry["tenant"], entry["incident_id"])
            self._authorized(incident, lease, current_time())
            if incident["plan"]["digest"] != entry["plan_digest"]:
                raise ValueError("Prepared action belongs to an older plan")
            receipt = client.apply(
                entry["tenant"],
                entry["service"],
                entry["step"],
                entry["key"],
                entry["generation"],
            )
            if after_effect:
                after_effect()
            return self._accept(entry, receipt, current_time())
