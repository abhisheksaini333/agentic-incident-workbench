import React, { useState } from "react";
import { Incident, readable } from "./types";

export function EvidencePanel({ incident }: { incident: Incident }) {
  const [version, setVersion] = useState<number | null>(null);
  const evidence =
    incident.evidence_history.find((item) => item.version === version) ||
    incident.evidence;
  if (!evidence)
    return (
      <section className="panel">
        <h3>Evidence</h3>
        <p className="muted" role="status">
          Waiting for the collector to observe the service.
        </p>
      </section>
    );
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">OBSERVATIONS</p>
          <h3>Service evidence</h3>
        </div>
        <span
          className={"status " + (evidence.healthy ? "resolved" : "escalated")}
        >
          {evidence.healthy ? "healthy" : "degraded"}
        </span>
      </div>
      <label className="compact">
        Evidence snapshot
        <select
          value={evidence.version}
          onChange={(event) => setVersion(Number(event.target.value))}
        >
          {incident.evidence_history.map((item) => (
            <option key={item.version} value={item.version}>
              Snapshot {item.version}
              {incident.plan?.evidence_version === item.version
                ? " · plan evidence"
                : ""}
            </option>
          ))}
        </select>
      </label>
      <div className="metric-grid">
        {evidence.observations
          .filter((item) => item.kind === "metric")
          .map((item) => (
            <div
              className="metric"
              key={item.reference}
              id={"evidence-" + evidence.version + "-" + item.reference}
              tabIndex={-1}
            >
              <span>{readable(item.name!)}</span>
              <strong>{item.value}</strong>
              <small>{item.reference}</small>
            </div>
          ))}
      </div>
      <h4>Service log</h4>
      <ol className="logs">
        {evidence.observations
          .filter((item) => item.kind === "log")
          .map((item) => (
            <li
              key={item.reference}
              id={"evidence-" + evidence.version + "-" + item.reference}
              tabIndex={-1}
            >
              <code>{item.reference}</code>
              <p>{item.text}</p>
            </li>
          ))}
      </ol>
      <p className="small muted">
        Snapshot {evidence.version} · service generation {evidence.generation}.
        Earlier snapshots remain available for review.
      </p>
    </section>
  );
}
