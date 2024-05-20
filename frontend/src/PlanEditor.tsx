import React, { useState } from "react";
import { Api } from "./api.mjs";
import { Incident, Step, readable } from "./types";

const defaults: Record<string, Record<string, string | number>> = {
  restart_service: {},
  throttle_requests: { percent: 30 },
  rollback_release: { release: "stable" },
  restore_dependency: { dependency: "catalog" },
  rotate_logs: { keep_files: 2 },
  scale_consumers: { replicas: 3 },
};
const bounds: Record<string, [number, number]> = {
  percent: [10, 50],
  keep_files: [1, 10],
  replicas: [2, 4],
};
export function PlanEditor({
  api,
  incident,
  onSaved,
  onCancel,
  onError,
}: {
  api: Api;
  incident: Incident;
  onSaved: () => void;
  onCancel: () => void;
  onError: (message: string) => void;
}) {
  const [steps, setSteps] = useState<Step[]>(() =>
      JSON.parse(JSON.stringify(incident.plan!.steps))
    ),
    [rationale, setRationale] = useState(incident.plan!.rationale),
    [busy, setBusy] = useState(false);
  const [baseline] = useState({
    revision: incident.revision,
    digest: incident.plan!.digest,
  });
  const stale = incident.plan?.digest !== baseline.digest;
  function action(index: number, name: string) {
    setSteps((previous) =>
      previous.map((step, i) =>
        i === index
          ? {
              action: name,
              target: incident.service,
              arguments: { ...defaults[name] },
            }
          : step
      )
    );
  }
  function argument(index: number, name: string, value: number) {
    setSteps((previous) =>
      previous.map((step, i) =>
        i === index
          ? { ...step, arguments: { ...step.arguments, [name]: value } }
          : step
      )
    );
  }
  async function save(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await api.call("/api/incidents/" + incident.id + "/plan", {
        method: "PUT",
        body: { revision: baseline.revision, steps, rationale },
      });
      onSaved();
    } catch (error) {
      onError((error as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form className="plan-editor" onSubmit={save}>
      <h4>Edit proposed actions</h4>
      <p className="small muted">
        Saving creates a new plan version and clears prior approval.
      </p>
      {steps.map((step, index) => (
        <fieldset key={index}>
          <legend>Action {index + 1}</legend>
          <label>
            Remediation
            <select
              value={step.action}
              onChange={(event) => action(index, event.target.value)}
            >
              {Object.keys(defaults).map((name) => (
                <option key={name} value={name}>
                  {readable(name)}
                </option>
              ))}
            </select>
          </label>
          {Object.entries(step.arguments).map(([name, value]) =>
            typeof value === "number" ? (
              <label key={name}>
                {readable(name)}
                <input
                  type="number"
                  min={bounds[name][0]}
                  max={bounds[name][1]}
                  value={value}
                  required
                  onChange={(event) =>
                    argument(index, name, Number(event.target.value))
                  }
                />
              </label>
            ) : (
              <p className="small" key={name}>
                {readable(name)}: <strong>{value}</strong>
              </p>
            )
          )}
          <button
            type="button"
            className="quiet danger"
            disabled={steps.length === 1}
            onClick={() =>
              setSteps((previous) => previous.filter((_, i) => i !== index))
            }
          >
            Remove action
          </button>
        </fieldset>
      ))}
      <button
        type="button"
        className="quiet"
        disabled={steps.length >= 3}
        onClick={() =>
          setSteps((previous) => [
            ...previous,
            {
              action: "restart_service",
              target: incident.service,
              arguments: {},
            },
          ])
        }
      >
        Add action
      </button>
      <label>
        Reason for this plan
        <textarea
          value={rationale}
          onChange={(event) => setRationale(event.target.value)}
          required
          maxLength={1000}
          rows={4}
        />
      </label>
      {stale && (
        <p role="alert" className="error">
          The plan changed while you were editing. Close this editor and review
          the latest version.
        </p>
      )}
      <div className="actions">
        <button type="button" className="quiet" onClick={onCancel}>
          Cancel edit
        </button>
        <button className="primary" disabled={busy || stale}>
          Save new plan version
        </button>
      </div>
    </form>
  );
}
