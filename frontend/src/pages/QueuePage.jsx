import { useCallback, useEffect, useState } from "react";
import { PublicClientApplication } from "@azure/msal-browser";
import { hostedApi, setHostedToken } from "../api";

const TOKEN_KEY = "kannon_hosted_token";

function weldLabor(job) {
  const flags = (job.qc_report && job.qc_report.flags) || [];
  return flags.filter((flag) => String(flag).toLowerCase().includes("weld labor"));
}

function otherFlags(job) {
  const flags = (job.qc_report && job.qc_report.flags) || [];
  return flags.filter((flag) => !String(flag).toLowerCase().includes("weld labor"));
}

export default function QueuePage() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || "");
  const [me, setMe] = useState(null);
  const [config, setConfig] = useState(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [customer, setCustomer] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [notes, setNotes] = useState("");
  const [scope, setScope] = useState("fab-only");
  const [files, setFiles] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [view, setView] = useState("mine");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    hostedApi("/api/hosted/auth/config")
      .then(setConfig)
      .catch(() => setConfig({ provider: "local", mode: "password", authorize_url: null }));
  }, []);

  const loadJobs = useCallback(async () => {
    if (!localStorage.getItem(TOKEN_KEY)) return;
    const path = view === "all" ? "/api/hosted/jobs?scope=all" : "/api/hosted/jobs";
    const rows = await hostedApi(path);
    setJobs(rows);
    setError("");
  }, [view]);

  useEffect(() => {
    if (!token) {
      setMe(null);
      setJobs([]);
      return undefined;
    }
    let stop = false;
    hostedApi("/api/hosted/me")
      .then((row) => {
        if (!stop) setMe(row);
      })
      .catch((err) => {
        if (err.status === 401) {
          setToken("");
          setHostedToken("");
        }
      });
    return () => {
      stop = true;
    };
  }, [token]);

  useEffect(() => {
    if (!token) return undefined;
    let stop = false;
    const tick = () => {
      loadJobs().catch((err) => {
        if (stop) return;
        if (err.status === 401) {
          setToken("");
          setHostedToken("");
          return;
        }
        setError(err.message || "Could not load jobs");
      });
    };
    tick();
    const timer = setInterval(tick, 4000);
    return () => {
      stop = true;
      clearInterval(timer);
    };
  }, [token, loadJobs]);

  async function onMicrosoft() {
    setBusy(true);
    setError("");
    try {
      const pca = new PublicClientApplication({
        auth: {
          clientId: config.client_id,
          authority: `https://login.microsoftonline.com/${config.tenant_id}`,
          redirectUri: config.redirect_uri || `${window.location.origin}/queue`,
        },
      });
      await pca.initialize();
      const result = await pca.loginPopup({ scopes: ["openid", "profile", "email"] });
      if (!result || !result.idToken) throw new Error("entra_token_missing");
      const data = await hostedApi("/api/hosted/auth/callback", {
        method: "POST",
        json: { id_token: result.idToken },
      });
      setHostedToken(data.token);
      setToken(data.token);
      setMe({ email: data.email, role: data.role });
    } catch (err) {
      setError(err.message || "Sign-in failed");
    } finally {
      setBusy(false);
    }
  }

  async function onDev(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const data = await hostedApi("/api/hosted/auth/dev", {
        method: "POST",
        json: { email },
      });
      setHostedToken(data.token);
      setToken(data.token);
      setMe({ email: data.email, role: data.role });
    } catch (err) {
      setError(err.message || "Sign-in failed");
    } finally {
      setBusy(false);
    }
  }

  async function onLogin(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const data = await hostedApi("/api/hosted/login", {
        method: "POST",
        json: { email, password },
      });
      setHostedToken(data.token);
      setToken(data.token);
      setMe({ email: data.email, role: data.role });
      setPassword("");
    } catch (err) {
      setError(err.message || "Sign-in failed");
    } finally {
      setBusy(false);
    }
  }

  async function onSubmit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const body = new FormData();
      body.set("customer", customer);
      body.set("scope", scope);
      body.set("notes", notes);
      body.set("due_date", dueDate);
      for (const file of files) body.append("files", file);
      await hostedApi("/api/hosted/jobs", { method: "POST", body });
      setFiles([]);
      setNotes("");
      await loadJobs();
    } catch (err) {
      setError(err.message || "Submit failed");
    } finally {
      setBusy(false);
    }
  }

  async function onCancel(jobId) {
    setError("");
    try {
      await hostedApi(`/api/hosted/jobs/${jobId}/cancel`, { method: "POST" });
      await loadJobs();
    } catch (err) {
      setError(err.message || "Cancel failed");
    }
  }

  function logout() {
    setHostedToken("");
    setToken("");
    setMe(null);
    setJobs([]);
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          Kannon <span>Queue</span>
        </div>
        {me ? (
          <nav className="nav">
            <span>{me.email}</span>
            <button className="linkish" type="button" onClick={logout}>
              Log out
            </button>
          </nav>
        ) : null}
      </header>

      {!token ? (
        <form
          className="panel login-card"
          onSubmit={config && config.mode === "password" ? onLogin : (e) => e.preventDefault()}
        >
          <h1>Drop a quote</h1>
          <p>Team sign-in. Sectura stays on the shop box.</p>
          {config && config.provider === "entra" && config.client_id ? (
            <button className="btn" disabled={busy} type="button" onClick={onMicrosoft}>
              {busy ? "Signing in…" : "Sign in with Microsoft"}
            </button>
          ) : null}
          {config && config.dev_bypass ? (
            <>
              <div className="field">
                <label htmlFor="queue-dev-email">Local dev email</label>
                <input
                  id="queue-dev-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="username"
                />
              </div>
              <button className="btn secondary" disabled={busy || !email} type="button" onClick={onDev}>
                Dev sign-in
              </button>
            </>
          ) : null}
          {config && config.mode === "password" ? (
            <>
              <div className="field">
                <label htmlFor="queue-email">Email</label>
                <input
                  id="queue-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="username"
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="queue-password">Password</label>
                <input
                  id="queue-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
              </div>
              <button className="btn" disabled={busy} type="submit">
                {busy ? "Signing in…" : "Sign in"}
              </button>
            </>
          ) : null}
          {error ? <div className="error">{error}</div> : null}
        </form>
      ) : (
        <div className="queue-layout">
          <form className="panel" onSubmit={onSubmit}>
            <h2>New job</h2>
            <div className="field">
              <label htmlFor="customer">Customer</label>
              <input
                id="customer"
                value={customer}
                onChange={(e) => setCustomer(e.target.value)}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="due">Due date</label>
              <input id="due" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="scope">Scope</label>
              <select id="scope" value={scope} onChange={(e) => setScope(e.target.value)}>
                <option value="fab-only">Fab only</option>
                <option value="full-assembly">Full assembly</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="notes">Notes</label>
              <textarea id="notes" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="files">STEP, PDF, DXF, or zip</label>
              <input
                id="files"
                type="file"
                multiple
                accept=".step,.stp,.pdf,.dxf,.zip"
                onChange={(e) => setFiles(Array.from(e.target.files || []))}
              />
            </div>
            <button className="btn" disabled={busy || files.length === 0} type="submit">
              {busy ? "Sending…" : "Submit"}
            </button>
            {error ? <div className="error">{error}</div> : null}
          </form>

          <section className="panel">
            <div className="row">
              <h2>{view === "all" ? "All jobs" : "My jobs"}</h2>
              <button
                className="btn ghost"
                type="button"
                onClick={() => setView(view === "all" ? "mine" : "all")}
              >
                {view === "all" ? "Show mine" : "Show all"}
              </button>
            </div>
            <p>Status refreshes every few seconds. Weld labor is a flag only — no rate is invented.</p>
            {jobs.length === 0 ? <p>No jobs yet.</p> : null}
            {jobs.map((job) => {
              const labor = weldLabor(job);
              const flags = otherFlags(job);
              const mine = me && job.submitted_by === me.email;
              const canCancel = (mine || (me && me.role === "admin")) && (job.status === "queued" || job.status === "claimed");
              return (
                <article key={job.id}>
                  <table className="jobs-table">
                    <tbody>
                      <tr>
                        <th>Customer</th>
                        <td>{job.customer}</td>
                      </tr>
                      <tr>
                        <th>Status</th>
                        <td>
                          <span className={`status ${job.status}`}>{job.status}</span>
                        </td>
                      </tr>
                      <tr>
                        <th>Submitted by</th>
                        <td>{job.submitted_by}</td>
                      </tr>
                      <tr>
                        <th>Scope</th>
                        <td>{job.scope}</td>
                      </tr>
                      {job.sectura_quote_number ? (
                        <tr>
                          <th>Quote</th>
                          <td>{job.sectura_quote_number}</td>
                        </tr>
                      ) : null}
                      {job.error ? (
                        <tr>
                          <th>Error</th>
                          <td>{job.error}</td>
                        </tr>
                      ) : null}
                    </tbody>
                  </table>
                  {labor.length ? (
                    <div className="weld-flag">Weld labor FLAG — no rate invented. {labor.join("; ")}</div>
                  ) : null}
                  {flags.length ? (
                    <ul>
                      {flags.map((flag) => (
                        <li key={flag}>{flag}</li>
                      ))}
                    </ul>
                  ) : null}
                  {canCancel ? (
                    <button className="btn secondary" type="button" onClick={() => onCancel(job.id)}>
                      Cancel
                    </button>
                  ) : null}
                </article>
              );
            })}
          </section>
        </div>
      )}
    </div>
  );
}
