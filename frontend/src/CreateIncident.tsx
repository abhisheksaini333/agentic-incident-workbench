import React, { useEffect, useRef, useState } from "react";
import { Api } from "./api.mjs";
import { Incident } from "./types";

export function CreateIncident({
  api,
  onCreated,
  onClose,
}: {
  api: Api;
  onCreated: (incident: Incident) => void;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [services, setServices] = useState<string[]>([]),
    [service, setService] = useState("heap-api"),
    [title, setTitle] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  useEffect(() => {
    dialog.current?.showModal();
    let active = true;
    api
      .call("/api/config")
      .then((config) => {
        if (active) setServices(config.services);
      })
      .catch((error) => {
        if (active) setError(error.message);
      });
    return () => {
      active = false;
    };
  }, [api]);
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const incident = await api.call("/api/incidents", {
        method: "POST",
        body: { service, title },
      });
      onCreated(incident);
    } catch (error) {
      setError((error as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <dialog
      ref={dialog}
      onCancel={onClose}
      aria-labelledby="new-incident-title"
    >
      <form onSubmit={submit}>
        <div className="panel-heading">
          <div>
            <p className="eyebrow">START WITH A SIGNAL</p>
            <h2 id="new-incident-title">Open an incident</h2>
          </div>
          <button
            type="button"
            className="quiet"
            aria-label="Close new incident"
            onClick={onClose}
          >
            ×
          </button>
        </div>
        <p className="muted">
          The worker will collect evidence and prepare a plan. It cannot
          remediate the service until a different reviewer approves.
        </p>
        <label>
          Service
          <select
            value={service}
            onChange={(event) => setService(event.target.value)}
          >
            {services.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
        <label>
          Incident title
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Requests fail on the checkout path"
            required
            maxLength={160}
            autoFocus
          />
        </label>
        <p className="small muted">Diagnosis mode: rules baseline</p>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <div className="actions">
          <button type="button" className="quiet" onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={busy || !services.length}>
            {busy ? "Opening…" : "Collect evidence"}
          </button>
        </div>
      </form>
    </dialog>
  );
}
