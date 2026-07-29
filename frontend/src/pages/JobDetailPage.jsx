import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";

function emptyItem() {
  return {
    size: "1/4",
    inches: 0,
    joint_notes: "",
    confidence: "medium",
    source: "manual",
    needs_review: true,
  };
}

export default function JobDetailPage() {
  const { id } = useParams();
  const [job, setJob] = useState(null);
  const [items, setItems] = useState([]);
  const [efficiency, setEfficiency] = useState(85);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function load() {
    const data = await api(`/api/jobs/${id}`);
    setJob(data);
    setItems(data.takeoff?.items || []);
    setEfficiency(data.efficiency_pct ?? 85);
  }

  useEffect(() => {
    let alive = true;
    let timer;

    async function refresh() {
      const data = await api(`/api/jobs/${id}`);
      if (!alive) return data;
      setJob(data);
      if (!["uploaded", "processing"].includes(data.status)) {
        setItems(data.takeoff?.items || []);
        setEfficiency(data.efficiency_pct ?? 85);
      }
      return data;
    }

    (async () => {
      try {
        const data = await refresh();
        if (!alive) return;
        if (["uploaded", "processing"].includes(data.status)) {
          timer = setInterval(async () => {
            try {
              const latest = await refresh();
              if (!alive) return;
              if (!["uploaded", "processing"].includes(latest.status)) {
                clearInterval(timer);
              }
            } catch {
              /* ignore poll errors */
            }
          }, 1000);
        }
      } catch (err) {
        if (alive) setError(err.message);
      }
    })();

    return () => {
      alive = false;
      if (timer) clearInterval(timer);
    };
  }, [id]);

  async function save(status) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const data = await api(`/api/jobs/${id}`, {
        method: "PATCH",
        json: {
          items,
          efficiency_pct: Number(efficiency),
          status: status || undefined,
        },
      });
      setJob(data);
      setItems(data.takeoff?.items || []);
      setMessage(status ? `Marked ${status}` : "Recalculated");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function pollUntilReady() {
    for (let i = 0; i < 90; i++) {
      await new Promise((r) => setTimeout(r, 1000));
      const data = await api(`/api/jobs/${id}`);
      setJob(data);
      if (!["uploaded", "processing"].includes(data.status)) {
        setItems(data.takeoff?.items || []);
        setEfficiency(data.efficiency_pct ?? 85);
        return data;
      }
    }
    return null;
  }

  async function reprocess() {
    setBusy(true);
    setError("");
    setMessage("Reprocessing…");
    try {
      await api(`/api/jobs/${id}/reprocess`, { method: "POST" });
      const data = await pollUntilReady();
      setMessage(data ? "Takeoff refreshed" : "Still processing — refresh shortly");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function attachStp(file) {
    if (!file) return;
    setBusy(true);
    setError("");
    setMessage("Attaching STP and re-running takeoff…");
    try {
      const body = new FormData();
      body.append("stp", file);
      await api(`/api/jobs/${id}/stp`, { method: "POST", body });
      const data = await pollUntilReady();
      setMessage(data ? "STP attached — takeoff refreshed" : "Still processing — refresh shortly");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function findLibrary() {
    setBusy(true);
    setError("");
    setMessage("Searching shared drawing library…");
    try {
      await api(`/api/jobs/${id}/find-library`, { method: "POST" });
      const data = await pollUntilReady();
      const lib = data?.takeoff?.library;
      if (lib?.attached) {
        setMessage(`Found and attached ${lib.stp_filename} from shared drive`);
      } else if (lib?.stp_filename) {
        setMessage(`Found ${lib.stp_filename} (already on job or attach skipped)`);
      } else {
        setMessage(lib?.notes?.[0] || "No matching STP on the shared drive");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (!job) {
    return (
      <div className="panel">
        <p className="muted">Loading job…</p>
        {error ? <div className="error">{error}</div> : null}
      </div>
    );
  }

  const times = job.times || {};
  const library = job.takeoff?.library || null;

  return (
    <div className="panel">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div>
          <Link to="/jobs">← Jobs</Link>
          <h1 style={{ margin: "0.35rem 0 0" }}>{job.title}</h1>
          <p className="muted">
            #{job.id} · <span className={`status ${job.status}`}>{job.status}</span>
            {job.pdf_filename ? ` · ${job.pdf_filename}` : ""}
            {job.stp_filename ? ` · ${job.stp_filename}` : " · No STP"}
          </p>
          {!job.stp_filename ? (
            <p className="error" style={{ marginTop: "0.5rem" }}>
              No STP on this job — use Find on shared drive, or attach an STP manually.
            </p>
          ) : null}
          {library?.folder ? (
            <p className="muted" style={{ marginTop: "0.5rem" }}>
              Shared folder: {library.folder}
              {library.attached ? " · STP auto-attached" : ""}
              {library.related_pdf_count
                ? ` · ${library.related_pdf_count} related PDF(s)`
                : ""}
            </p>
          ) : null}
        </div>
        <div className="row">
          <a
            className="btn ghost"
            href={`/api/jobs/${id}/export.html?token=${encodeURIComponent(
              localStorage.getItem("kannon_quote_token") || ""
            )}`}
            target="_blank"
            rel="noreferrer"
          >
            Printable
          </a>
          <a
            className="btn ghost"
            href={`/api/jobs/${id}/export?token=${encodeURIComponent(
              localStorage.getItem("kannon_quote_token") || ""
            )}`}
            target="_blank"
            rel="noreferrer"
          >
            JSON
          </a>
        </div>
      </div>

      {job.error_message ? <div className="error">{job.error_message}</div> : null}

      <div className="metrics">
        <div className="metric">
          <div className="label">Total inches</div>
          <div className="value">{times.total_inches ?? "—"}</div>
        </div>
        <div className="metric">
          <div className="label">Weld minutes</div>
          <div className="value">{times.weld_minutes != null ? times.weld_minutes.toFixed(1) : "—"}</div>
        </div>
        <div className="metric">
          <div className="label">Quoted no fixture</div>
          <div className="value">{times.quoted_no_fixture_hours ?? "—"} hr</div>
        </div>
        <div className="metric">
          <div className="label">Quoted with fixture</div>
          <div className="value">{times.quoted_with_fixture_hours ?? "—"} hr</div>
        </div>
      </div>

      {(job.flags || []).length ? (
        <div className="flags">
          <h3>Review flags</h3>
          <ul>
            {job.flags.map((f) => (
              <li key={f}>{f}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="field" style={{ maxWidth: 220 }}>
        <label htmlFor="eff">Efficiency %</label>
        <input
          id="eff"
          type="number"
          min="1"
          max="100"
          value={efficiency}
          onChange={(e) => setEfficiency(e.target.value)}
        />
      </div>

      <h2>Takeoff lines</h2>
      <table className="takeoff-table">
        <thead>
          <tr>
            <th style={{ width: "110px" }}>Size</th>
            <th style={{ width: "120px" }}>Inches</th>
            <th>Notes</th>
            <th style={{ width: "100px" }}>Confidence</th>
            <th style={{ width: "70px" }}></th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, idx) => (
            <tr key={idx}>
              <td>
                <input
                  type="text"
                  value={item.size}
                  onChange={(e) => {
                    const next = [...items];
                    next[idx] = { ...item, size: e.target.value };
                    setItems(next);
                  }}
                />
              </td>
              <td>
                <input
                  type="number"
                  step="0.01"
                  value={item.inches}
                  onChange={(e) => {
                    const next = [...items];
                    next[idx] = { ...item, inches: Number(e.target.value) };
                    setItems(next);
                  }}
                />
              </td>
              <td>
                <input
                  type="text"
                  value={item.joint_notes || ""}
                  onChange={(e) => {
                    const next = [...items];
                    next[idx] = { ...item, joint_notes: e.target.value };
                    setItems(next);
                  }}
                />
              </td>
              <td className="muted">{item.confidence}</td>
              <td>
                <button
                  className="btn ghost"
                  type="button"
                  onClick={() => setItems(items.filter((_, i) => i !== idx))}
                >
                  Del
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="row">
        <button className="btn ghost" type="button" onClick={() => setItems([...items, emptyItem()])}>
          Add line
        </button>
        <button className="btn secondary" type="button" disabled={busy} onClick={() => save()}>
          Recalculate
        </button>
        <button className="btn ok" type="button" disabled={busy} onClick={() => save("accepted")}>
          Accept
        </button>
        <button className="btn warn" type="button" disabled={busy} onClick={() => save("needs_info")}>
          Needs info
        </button>
        <button className="btn ghost" type="button" disabled={busy} onClick={reprocess}>
          Re-run takeoff
        </button>
        <button className="btn secondary" type="button" disabled={busy} onClick={findLibrary}>
          Find on shared drive
        </button>
        <label className="btn ghost" style={{ cursor: busy ? "default" : "pointer" }}>
          {job.stp_filename ? "Replace STP" : "Attach STP"}
          <input
            type="file"
            accept=".stp,.step"
            hidden
            disabled={busy}
            onChange={(e) => {
              const f = e.target.files?.[0];
              e.target.value = "";
              attachStp(f);
            }}
          />
        </label>
      </div>
      {message ? <p className="muted">{message}</p> : null}
      {error ? <div className="error">{error}</div> : null}
    </div>
  );
}
