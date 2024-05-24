import React, { useState } from "react";
import { Api } from "./api.mjs";
import { Incident, User } from "./types";

export function RecoveryPanel({
  api,
  incident,
  user,
  onChanged,
  onError,
}: {
  api: Api;
  incident: Incident;
  user: User;
  onChanged: () => void;
  onError: (message: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  if (!user.roles.some((role) => ["operator", "admin"].includes(role)))
    return null;
  async function act(name: string) {
    if (
      name === "cancel" &&
      !confirm(
        "Stop further work on this incident? Existing effects and receipts remain recorded."
      )
    )
      return;
    setBusy(true);
    try {
      await api.call("/api/incidents/" + incident.id + "/" + name, {
        method: "POST",
        body: { revision: incident.revision },
      });
      onChanged();
    } catch (error) {
      onError((error as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel recovery">
      <p className="eyebrow">OPERATOR CONTROLS</p>
      <h3>Recovery & investigation</h3>
      <p className="small muted">
        Recollection invalidates the plan and approval. Resuming keeps exact
        approved action identities and reconciles receipts first.
      </p>
      <div className="recovery-actions">
        {["escalated", "awaiting_approval", "approved"].includes(
          incident.status
        ) && (
          <button disabled={busy} onClick={() => act("recollect")}>
            Collect fresh evidence
          </button>
        )}
        {incident.status === "escalated" && incident.approval && (
          <button disabled={busy} onClick={() => act("resume")}>
            Resume approved work
          </button>
        )}
        <button
          className="quiet"
          disabled={busy}
          onClick={() => act("reconcile")}
        >
          Check pending receipts
        </button>
        {!["resolved", "cancelled"].includes(incident.status) && (
          <button
            className="quiet danger"
            disabled={busy}
            onClick={() => act("cancel")}
          >
            Cancel further work
          </button>
        )}
      </div>
    </section>
  );
}
