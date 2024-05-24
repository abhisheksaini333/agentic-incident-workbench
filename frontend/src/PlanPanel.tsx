import React, { useState } from "react";
import { Api } from "./api.mjs";
import { Incident, User, readable } from "./types";
import { PlanEditor } from "./PlanEditor";

export function PlanPanel({
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
  const [reviewed, setReviewed] = useState<string | null>(null),
    [busy, setBusy] = useState(false),
    [editing, setEditing] = useState(false),
    [changeReason, setChangeReason] = useState("");
  const plan = incident.plan;
  if (!plan)
    return (
      <section className="panel">
        <p className="eyebrow">HUMAN DECISION</p>
        <h3>Remediation plan</h3>
        <p className="muted">
          A supported diagnosis is required before a plan can be reviewed.
        </p>
      </section>
    );
  const independent = plan.author !== user.subject;
  const canApprove =
    user.roles.some((role) => ["approver", "admin"].includes(role)) &&
    independent;
  async function approve() {
    setBusy(true);
    try {
      await api.call("/api/incidents/" + incident.id + "/approve", {
        method: "POST",
        body: { revision: incident.revision, digest: plan!.digest },
      });
      setReviewed(null);
      onChanged();
    } catch (error) {
      onError((error as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function requestChanges() {
    setBusy(true);
    try {
      await api.call("/api/incidents/" + incident.id + "/request-changes", {
        method: "POST",
        body: { revision: incident.revision, reason: changeReason },
      });
      setReviewed(null);
      setChangeReason("");
      onChanged();
    } catch (error) {
      onError((error as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel plan-panel">
      <p className="eyebrow">HUMAN DECISION / PLAN {plan.version}</p>
      <h3>Review the exact plan</h3>
      <p className="small muted">
        Based on evidence snapshot {plan.evidence_version}. Review every action
        and its arguments.
      </p>
      <ol className="plan-steps">
        {plan.steps.map((step, index) => (
          <li key={index}>
            <span className="step-number">
              {String(index + 1).padStart(2, "0")}
            </span>
            <div>
              <strong>{readable(step.action)}</strong>
              <p className="small muted">Service: {step.target}</p>
              {Object.entries(step.arguments).map(([name, value]) => (
                <p className="argument" key={name}>
                  <span>{readable(name)}</span>
                  <b>{value}</b>
                </p>
              ))}
            </div>
          </li>
        ))}
      </ol>
      <p className="rationale">{plan.rationale}</p>
      {incident.review_request?.plan_digest === plan.digest && (
        <p className="warning" role="status">
          Changes requested by {incident.review_request.subject}:{" "}
          {incident.review_request.reason}
        </p>
      )}
      {user.roles.some((role) => ["operator", "admin"].includes(role)) &&
        ["awaiting_approval", "approved"].includes(incident.status) &&
        (editing ? (
          <PlanEditor
            api={api}
            incident={incident}
            onSaved={() => {
              setEditing(false);
              onChanged();
            }}
            onCancel={() => setEditing(false)}
            onError={onError}
          />
        ) : (
          <button className="quiet wide" onClick={() => setEditing(true)}>
            Edit proposed plan
          </button>
        ))}
      {incident.status === "awaiting_approval" ? (
        <>
          {canApprove ? (
            <>
              <label className="check">
                <input
                  type="checkbox"
                  checked={reviewed === plan.digest}
                  onChange={(event) =>
                    setReviewed(event.target.checked ? plan.digest : null)
                  }
                />
                I reviewed this evidence and every proposed action.
              </label>
              <button
                className="primary wide"
                disabled={
                  busy ||
                  reviewed !== plan.digest ||
                  incident.review_request?.plan_digest === plan.digest
                }
                onClick={approve}
              >
                {busy ? "Recording approval…" : "Approve this exact plan"}
              </button>
              <details className="request-changes">
                <summary>Request changes instead</summary>
                <label>
                  Changes needed
                  <textarea
                    value={changeReason}
                    onChange={(event) => setChangeReason(event.target.value)}
                    maxLength={500}
                    rows={3}
                  />
                </label>
                <button
                  className="quiet"
                  disabled={busy || !changeReason.trim()}
                  onClick={requestChanges}
                >
                  Send change request
                </button>
              </details>
            </>
          ) : (
            <p className="warning">
              {!independent
                ? "A different reviewer must approve the plan you prepared."
                : "An approver must review this plan before it can run."}
            </p>
          )}
        </>
      ) : incident.approval ? (
        <p className="approval-record">
          Approved by <strong>{incident.approval.subject}</strong>. Effects
          still require fresh authorization and service preconditions.
        </p>
      ) : null}
      {incident.receipts.length > 0 && (
        <div className="receipts">
          <h4>Recorded effects</h4>
          {incident.receipts.map((receipt) => (
            <div className="receipt" key={receipt.key}>
              <strong>{readable(receipt.action)}</strong>
              <span className="small">
                {receipt.changed
                  ? "Changed the failing service"
                  : "No fault change was necessary"}
              </span>
              <code>{receipt.key.slice(0, 14)}</code>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
