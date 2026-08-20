import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { api } from "../api";

const PUSH_IN_FLIGHT = new Set(["pushing", "retrying_createfile"]);

function secturaStatus(job) {
  return job?.takeoff?.secturafab?.status || null;
}

function canPush(job) {
  if (!job) return false;
  if (job.status === "uploaded" || job.status === "processing") return false;
  if (PUSH_IN_FLIGHT.has(secturaStatus(job))) return false;
  if (job.push_readiness && job.push_readiness.ready === false) return false;
  return true;
}

function pushBlockReason(job) {
  if (!job) return "";
  if (job.status === "uploaded" || job.status === "processing") return "takeoff running";
  if (PUSH_IN_FLIGHT.has(secturaStatus(job))) return "push in progress";
  if (job.push_readiness && job.push_readiness.ready === false) {
    return job.push_readiness.reason || "needs STEP or library";
  }
  return "";
}

export default function JobsPage() {
  const location = useLocation();
  const [jobs, setJobs] = useState([]);
  const [selected, setSelected] = useState(() => new Set());
  const [error, setError] = useState("");
  const [banner, setBanner] = useState("");
  const [busy, setBusy] = useState(false);

  const loadJobs = useCallback(async () => {
    const data = await api("/api/jobs");
    setJobs(data);
    return data;
  }, []);

  useEffect(() => {
    const st = location.state;
    if (st?.batchCreated != null) {
      const notes = [...(st.batchSkipped || []), ...(st.batchErrors || [])];
      setBanner(
        `Loose-piece batch created ${st.batchCreated} individual quote(s). ` +
          "Quote number = part number. Review each, then push to SecturaFAB." +
          (notes.length ? ` ${notes.join("; ")}` : "")
      );
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        await loadJobs();
      } catch (err) {
        if (alive) setError(err.message);
      }
    })();
    return () => {
      alive = false;
    };
  }, [loadJobs]);

  const needsPoll = useMemo(
    () =>
      jobs.some(
        (j) =>
          j.status === "uploaded" ||
          j.status === "processing" ||
          PUSH_IN_FLIGHT.has(secturaStatus(j))
      ),
    [jobs]
  );

  useEffect(() => {
    if (!needsPoll) return undefined;
    const id = setInterval(() => {
      loadJobs().catch(() => {});
    }, 2500);
    return () => clearInterval(id);
  }, [needsPoll, loadJobs]);

  const readySelected = useMemo(
    () => jobs.filter((j) => selected.has(j.id) && canPush(j)),
    [jobs, selected]
  );

  const allReady = useMemo(() => jobs.filter(canPush), [jobs]);

  function toggle(id) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAllReady() {
    setSelected((prev) => {
      const next = new Set(prev);
      const readyIds = allReady.map((j) => j.id);
      const allOn = readyIds.length > 0 && readyIds.every((id) => next.has(id));
      if (allOn) {
        for (const id of readyIds) next.delete(id);
      } else {
        for (const id of readyIds) next.add(id);
      }
      return next;
    });
  }

  async function pushIds(jobIds) {
    if (!jobIds.length) return;
    setBusy(true);
    setError("");
    try {
      const result = await api("/api/jobs/batch-push", {
        method: "POST",
        json: { job_ids: jobIds },
      });
      const rejected = result.rejected || [];
      setBanner(
        `Queued ${result.queued_count ?? 0} SecturaFAB push(es).` +
          (rejected.length
            ? ` Skipped: ${rejected.map((r) => `#${r.job_id} (${r.reason})`).join("; ")}`
            : "")
      );
      setSelected(new Set());
      await loadJobs();
    } catch (err) {
      setError(err.message || "Batch push failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel">
      <h1 style={{ marginTop: 0 }}>Jobs</h1>
      {banner ? <p className="muted">{banner}</p> : null}
      {error ? <div className="error">{error}</div> : null}

      <div className="row" style={{ marginBottom: "0.75rem", flexWrap: "wrap", gap: "0.5rem" }}>
        <button
          className="btn"
          type="button"
          disabled={busy || !readySelected.length}
          onClick={() => pushIds(readySelected.map((j) => j.id))}
        >
          {busy ? "Queuing…" : `Push selected (${readySelected.length})`}
        </button>
        <button
          className="btn secondary"
          type="button"
          disabled={busy || !allReady.length}
          onClick={() => pushIds(allReady.map((j) => j.id))}
        >
          Push all ready ({allReady.length})
        </button>
        <button className="btn ghost" type="button" onClick={toggleAllReady}>
          Select / clear ready
        </button>
      </div>

      <table className="jobs-table">
        <thead>
          <tr>
            <th></th>
            <th>ID</th>
            <th>Part #</th>
            <th>Title</th>
            <th>Mode</th>
            <th>Status</th>
            <th>SecturaFAB</th>
            <th>Inches</th>
            <th>Quoted (fixture)</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((j) => {
            const sf = secturaStatus(j);
            const pushable = canPush(j);
            return (
              <tr key={j.id}>
                <td>
                  <input
                    type="checkbox"
                    checked={selected.has(j.id)}
                    disabled={!pushable && !selected.has(j.id)}
                    onChange={() => toggle(j.id)}
                    aria-label={`Select job ${j.id}`}
                  />
                </td>
                <td className="mono">{j.id}</td>
                <td className="mono">{j.quote_number || j.part_number || "—"}</td>
                <td>{j.title}</td>
                <td>
                  <span className={`chip ${j.intake_mode === "loose_piece" ? "chip-loose" : "chip-weld"}`}>
                    {j.intake_mode === "loose_piece" ? "Loose piece" : "Weldment"}
                  </span>
                </td>
                <td>
                  <span className={`status ${j.status}`}>{j.status}</span>
                </td>
                <td className="mono">
                  {sf ||
                    (j.takeoff?.secturafab?.quote_number
                      ? String(j.takeoff.secturafab.quote_number)
                      : pushBlockReason(j) || "—")}
                </td>
                <td className="mono">{j.takeoff?.total_inches ?? "—"}</td>
                <td className="mono">
                  {j.times?.quoted_with_fixture_hours != null
                    ? `${j.times.quoted_with_fixture_hours} hr`
                    : "—"}
                </td>
                <td>
                  <Link to={`/jobs/${j.id}`}>Open</Link>
                </td>
              </tr>
            );
          })}
          {!jobs.length ? (
            <tr>
              <td colSpan={10} className="muted">
                No jobs yet. Upload a weldment or a loose-piece batch to start.
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
