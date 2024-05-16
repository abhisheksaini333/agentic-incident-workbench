import React, { useEffect, useState } from "react";
import { Api } from "./api.mjs";
import { Incident, IncidentSummary, User, readable } from "./types";
import { EvidencePanel } from "./EvidencePanel";
import { TracePanel } from "./TracePanel";
import { CreateIncident } from "./CreateIncident";
import { PlanPanel } from "./PlanPanel";

function IncidentDetail({
  api,
  id,
  user,
  onError,
  onChanged,
  refresh,
}: {
  api: Api;
  id: string;
  user: User;
  onError: (message: string) => void;
  onChanged: () => void;
  refresh: number;
}) {
  const [incident, setIncident] = useState<Incident | null>(null);
  useEffect(() => {
    let active = true,
      busy = false;
    const controller = new AbortController();
    const load = async () => {
      if (busy) return;
      busy = true;
      try {
        const result = await api.call("/api/incidents/" + id, {
          signal: controller.signal,
        });
        if (active) setIncident(result);
      } catch (error) {
        if (active && (error as Error).name !== "AbortError")
          onError((error as Error).message);
      } finally {
        busy = false;
      }
    };
    load();
    const interval = setInterval(load, 1500);
    return () => {
      active = false;
      controller.abort();
      clearInterval(interval);
    };
  }, [api, id, refresh]);
  if (!incident)
    return (
      <div className="empty" role="status">
        Loading incident evidence…
      </div>
    );
  return (
    <article className="incident-detail">
      <header className="incident-heading">
        <div>
          <p className="eyebrow">
            {incident.service} / {incident.id.slice(0, 8)}
          </p>
          <h2>{incident.title}</h2>
        </div>
        <span className={"status " + incident.status}>
          {readable(incident.status)}
        </span>
      </header>
      {incident.error && (
        <p className="warning" role="status">
          Work stopped for review: {readable(incident.error)}.
        </p>
      )}
      <div className="detail-columns">
        <div>
          <EvidencePanel incident={incident} />
          <TracePanel incident={incident} />
        </div>
        <aside>
          <PlanPanel
            api={api}
            incident={incident}
            user={user}
            onChanged={onChanged}
            onError={onError}
          />
          <section className="panel">
            <p className="eyebrow">DIAGNOSIS</p>
            <h3>Working hypotheses</h3>
            {incident.hypotheses.length ? (
              incident.hypotheses.map((item) => (
                <article className="hypothesis" key={item.label}>
                  <strong>{readable(item.label)}</strong>
                  <p>{item.reason}</p>
                  <span className="small muted">
                    {item.source} · {item.references.join(", ")}
                  </span>
                </article>
              ))
            ) : (
              <p className="muted">
                A diagnosis appears after evidence collection.
              </p>
            )}
          </section>
        </aside>
      </div>
    </article>
  );
}

export function Desk({
  api,
  user,
  onError,
}: {
  api: Api;
  user: User;
  onError: (message: string) => void;
}) {
  const [items, setItems] = useState<IncidentSummary[]>([]),
    [selected, setSelected] = useState(""),
    [refresh, setRefresh] = useState(0),
    [creating, setCreating] = useState(false);
  useEffect(() => {
    let active = true,
      busy = false;
    const controller = new AbortController();
    const load = async () => {
      if (busy) return;
      busy = true;
      try {
        const data = await api.call("/api/incidents", {
          signal: controller.signal,
        });
        if (active) setItems(data.incidents);
      } catch (error) {
        if (active && (error as Error).name !== "AbortError")
          onError((error as Error).message);
      } finally {
        busy = false;
      }
    };
    load();
    const interval = setInterval(load, 2500);
    return () => {
      active = false;
      controller.abort();
      clearInterval(interval);
    };
  }, [api, refresh]);
  return (
    <section>
      <div className="desk-heading">
        <div>
          <p className="eyebrow">YOUR OPERATIONS DESK</p>
          <h2>Incidents</h2>
        </div>
        <div className="actions">
          <span className="small muted">Local service simulator</span>
          {user.roles.some((role) => ["operator", "admin"].includes(role)) && (
            <button className="primary" onClick={() => setCreating(true)}>
              Open incident
            </button>
          )}
        </div>
      </div>
      {creating && (
        <CreateIncident
          api={api}
          onClose={() => setCreating(false)}
          onCreated={(incident) => {
            setCreating(false);
            setSelected(incident.id);
            setItems((items) => [incident, ...items]);
            setRefresh((value) => value + 1);
          }}
        />
      )}
      <div className="desk">
        <nav className="queue" aria-label="Incident queue">
          <div className="queue-caption">
            ACTIVE & RECENT <span>{items.length}</span>
          </div>
          {items.length ? (
            items.map((item) => (
              <button
                key={item.id}
                className={
                  "queue-item " + (item.id === selected ? "selected" : "")
                }
                onClick={() => setSelected(item.id)}
              >
                <span className="small muted">{item.service}</span>
                <strong>{item.title}</strong>
                <span className={"status " + item.status}>
                  {readable(item.status)}
                </span>
              </button>
            ))
          ) : (
            <p className="empty">No incidents yet.</p>
          )}
        </nav>
        {selected ? (
          <IncidentDetail
            key={selected}
            api={api}
            id={selected}
            user={user}
            onError={onError}
            refresh={refresh}
            onChanged={() => setRefresh((value) => value + 1)}
          />
        ) : (
          <div className="empty desk-empty">
            <span className="empty-cross" aria-hidden="true">
              +
            </span>
            <h3>Select an incident</h3>
            <p>
              Its evidence, proposed plan and decision history will appear here.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
