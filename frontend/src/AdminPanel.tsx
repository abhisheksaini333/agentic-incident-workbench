import React, { useState } from "react";
import { Api } from "./api.mjs";
import { readable } from "./types";

const services = [
  "heap-api",
  "busy-api",
  "release-api",
  "catalog-api",
  "storage-api",
  "queue-api",
];
const faults = [
  "memory_pressure",
  "cpu_saturation",
  "bad_release",
  "dependency_outage",
  "disk_pressure",
  "queue_backlog",
];
export function AdminPanel({
  api,
  onError,
}: {
  api: Api;
  onError: (message: string) => void;
}) {
  const [service, setService] = useState("heap-api"),
    [fault, setFault] = useState("memory_pressure"),
    [subject, setSubject] = useState(""),
    [roles, setRoles] = useState<string[]>(["viewer"]),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState("");
  async function simulate(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setNotice("");
    try {
      const result = await api.call("/api/simulation", {
        method: "POST",
        body: { service, faults: fault ? [fault] : [], variant: 0 },
      });
      setNotice(
        service +
          " now has service generation " +
          result.generation +
          ". Collect fresh evidence before remediation."
      );
    } catch (error) {
      onError((error as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function updateRoles(event: React.FormEvent) {
    event.preventDefault();
    if (
      !roles.length &&
      !confirm("Remove this account's application access immediately?")
    )
      return;
    setBusy(true);
    setNotice("");
    try {
      await api.call(
        "/api/accounts/" + encodeURIComponent(subject) + "/roles",
        { method: "PUT", body: { roles } }
      );
      setNotice(
        "Access updated for " +
          subject +
          ". Existing sessions use the new roles."
      );
    } catch (error) {
      onError((error as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <details className="admin-panel panel">
      <summary>Local laboratory & account access</summary>
      <p className="small muted">
        Administrator controls affect this tenant's simulator and local
        accounts.
      </p>
      {notice && (
        <p className="approval-record" role="status">
          {notice}
        </p>
      )}
      <div className="admin-columns">
        <form onSubmit={simulate}>
          <h3>Inject a service fault</h3>
          <p className="small muted">
            Replacing service signals can make an existing plan stale. No
            external system is affected.
          </p>
          <label>
            Simulated service
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
            Fault family
            <select
              value={fault}
              onChange={(event) => setFault(event.target.value)}
            >
              <option value="">Healthy baseline</option>
              {faults.map((item) => (
                <option key={item} value={item}>
                  {readable(item)}
                </option>
              ))}
            </select>
          </label>
          <button disabled={busy}>Update simulator signals</button>
        </form>
        <form onSubmit={updateRoles}>
          <h3>Manage account access</h3>
          <label>
            Account identifier
            <input
              value={subject}
              onChange={(event) => setSubject(event.target.value)}
              maxLength={100}
              placeholder="acme.approver"
              required
            />
          </label>
          <fieldset>
            <legend>Current roles to grant</legend>
            {["viewer", "operator", "approver", "admin"].map((role) => (
              <label className="check" key={role}>
                <input
                  type="checkbox"
                  checked={roles.includes(role)}
                  onChange={(event) =>
                    setRoles((previous) =>
                      event.target.checked
                        ? [...previous, role]
                        : previous.filter((value) => value !== role)
                    )
                  }
                />
                {role}
              </label>
            ))}
          </fieldset>
          <button disabled={busy}>Apply access changes</button>
        </form>
      </div>
    </details>
  );
}
