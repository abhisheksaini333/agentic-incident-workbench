import React, { useState } from "react";

export function Login({ onToken }: { onToken: (token: string) => void }) {
  const [subject, setSubject] = useState(""),
    [password, setPassword] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject, password }),
      });
      const result = await response.json();
      if (!response.ok || typeof result.access_token !== "string")
        throw new Error(
          typeof result.detail === "string"
            ? result.detail
            : "Sign-in could not be completed"
        );
      setPassword("");
      onToken(result.access_token);
    } catch (error) {
      setError((error as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="landing-grid">
      <div className="landing">
        <p className="eyebrow">EVIDENCE BEFORE ACTION</p>
        <h1>
          From alarm
          <br />
          to <em>understanding.</em>
        </h1>
        <p>
          Collect the signals. Review the diagnosis. Approve an exact plan, then
          verify that the service recovered.
        </p>
        <div className="principles">
          <span>01 / OBSERVE</span>
          <span>02 / REVIEW</span>
          <span>03 / VERIFY</span>
        </div>
      </div>
      <form className="login panel" onSubmit={submit}>
        <p className="eyebrow">OPERATOR ACCESS</p>
        <h2>Open your desk</h2>
        <p className="muted">
          Use your local incident account. Access stays within your company.
        </p>
        <label>
          Account
          <input
            autoComplete="username"
            value={subject}
            onChange={(event) => setSubject(event.target.value)}
            placeholder="acme.operator"
            maxLength={100}
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            maxLength={128}
            required
          />
        </label>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <button className="primary" disabled={busy}>
          {busy ? "Signing in…" : "Sign in to workbench"}
        </button>
        <p className="small muted">
          Every remediation requires an independent reviewer.
        </p>
      </form>
    </section>
  );
}
