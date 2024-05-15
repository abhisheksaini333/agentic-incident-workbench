import React from "react";
import { Incident, readable } from "./types";

export function TracePanel({ incident }: { incident: Incident }) {
  return (
    <section className="panel trace-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">DURABLE RECORD</p>
          <h3>Decision timeline</h3>
        </div>
        <span className="small muted">{incident.trace.length} events</span>
      </div>
      <ol className="trace">
        {incident.trace.map((event) => (
          <li key={event.id}>
            <time>
              {new Date(event.time * 1000).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              })}
            </time>
            <div>
              <strong>{readable(event.kind)}</strong>
              <p>{event.message}</p>
              <span className="small muted">
                {event.actor}
                {event.references.length
                  ? " · " + event.references.join(", ")
                  : ""}
              </span>
            </div>
          </li>
        ))}
      </ol>
      <div className="usage">
        <span>{incident.budget.steps} steps</span>
        <span>{incident.budget.model_calls} model calls</span>
        <span>{incident.budget.effects} prepared effects</span>
        <span>{incident.budget.seconds.toFixed(2)}s active</span>
      </div>
    </section>
  );
}
