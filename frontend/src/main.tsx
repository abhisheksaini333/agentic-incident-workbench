import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Api } from "./api.mjs";
import { Login } from "./Login";
import "./styles.css";

type User = { tenant: string; subject: string; roles: string[] };
function App() {
  const [token, setToken] = useState(""),
    [user, setUser] = useState<User | null>(null),
    [error, setError] = useState("");
  const api = useMemo(
    () =>
      new Api(token, () => {
        setToken((current) => (current === token ? "" : current));
      }),
    [token]
  );
  useEffect(() => {
    let active = true;
    setUser(null);
    if (token)
      api
        .call("/api/me")
        .then((data) => {
          if (active) setUser(data);
        })
        .catch((error) => {
          if (active) setError(error.message);
        });
    return () => {
      active = false;
    };
  }, [api, token]);
  async function logout() {
    try {
      await api.call("/api/session", { method: "DELETE" });
    } catch (error) {
      setError((error as Error).message);
    } finally {
      setToken("");
      setUser(null);
    }
  }
  return (
    <>
      <header className="topbar">
        <a className="brand" href="/">
          <span className="brand-mark">IW</span>
          <span>
            INCIDENT<span className="brand-sub">WORKBENCH</span>
          </span>
        </a>
        {user ? (
          <div className="session">
            <span className="tenant">{user.tenant}</span>
            <span className="small muted">
              {user.subject} / {user.roles.join(", ")}
            </span>
            <button className="quiet" onClick={logout}>
              Sign out
            </button>
          </div>
        ) : (
          <span className="lab-label">LOCAL OPERATIONS LAB</span>
        )}
      </header>
      <main>
        {error && (
          <div className="banner error" role="alert">
            {error}
            <button className="quiet" onClick={() => setError("")}>
              Dismiss
            </button>
          </div>
        )}
        {user ? (
          <section>
            <p className="eyebrow">YOUR OPERATIONS DESK</p>
            <h2>Incidents</h2>
            <p className="muted">Signed in as {user.subject}.</p>
          </section>
        ) : token ? (
          <p role="status">Opening your incident desk…</p>
        ) : (
          <Login
            onToken={(value) => {
              setError("");
              setToken(value);
            }}
          />
        )}
      </main>
    </>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
