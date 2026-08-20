import { useCallback, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

function stemKey(name) {
  const base = String(name || "").replace(/^.*[\\/]/, "");
  const i = base.lastIndexOf(".");
  return (i >= 0 ? base.slice(0, i) : base).trim().toLowerCase();
}

function fileKind(name) {
  const lower = String(name || "").toLowerCase();
  if (lower.endsWith(".pdf")) return "pdf";
  if (lower.endsWith(".dxf")) return "dxf";
  if (lower.endsWith(".stp") || lower.endsWith(".step")) return "stp";
  return "other";
}

function pairLocalFiles(fileList) {
  const groups = new Map();
  const skipped = [];

  for (const f of Array.from(fileList || [])) {
    const kind = fileKind(f.name);
    const key = stemKey(f.name);
    if (kind === "other") {
      skipped.push(`Skipped unsupported: ${f.name}`);
      continue;
    }
    const current = groups.get(key) || { stem: f.name.replace(/\.[^.]+$/, ""), pdf: null, dxf: null, stp: null };
    current[kind] = f;
    if (!current.stem) current.stem = f.name.replace(/\.[^.]+$/, "");
    groups.set(key, current);
  }

  const pairs = [...groups.values()].sort((a, b) =>
    a.stem.localeCompare(b.stem, undefined, { sensitivity: "base" })
  );
  return { pairs, skipped };
}

export default function UploadPage() {
  const navigate = useNavigate();
  const [active, setActive] = useState(false);
  const [files, setFiles] = useState([]);
  const [title, setTitle] = useState("");
  const [bomConfig, setBomConfig] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);

  const { pairs, skipped } = useMemo(() => pairLocalFiles(files), [files]);

  const onFiles = useCallback((fileList) => {
    const incoming = Array.from(fileList || []);
    if (!incoming.length) return;
    setFiles((prev) => {
      const byKey = new Map();
      for (const f of prev) {
        const kind = fileKind(f.name);
        if (kind === "other") continue;
        byKey.set(`${stemKey(f.name)}:${kind}`, f);
      }
      for (const f of incoming) {
        const kind = fileKind(f.name);
        if (kind === "other") continue;
        byKey.set(`${stemKey(f.name)}:${kind}`, f);
      }
      return [...byKey.values()];
    });
    setError("");
    setInfo("");
  }, []);

  async function submitSingle() {
    const pair = pairs[0];
    if (!pair || (!pair.pdf && !pair.dxf && !pair.stp)) {
      setError("Drop at least one PDF, DXF, or STP/STEP");
      return;
    }
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const body = new FormData();
      if (pair.pdf) body.append("pdf", pair.pdf);
      if (pair.dxf) body.append("dxf", pair.dxf);
      if (pair.stp) body.append("stp", pair.stp);
      if (title.trim()) body.append("title", title.trim());
      if (bomConfig.trim()) body.append("bom_config", bomConfig.trim());
      const job = await api("/api/jobs", { method: "POST", body });
      navigate(`/jobs/${job.id}`);
    } catch (err) {
      setError(err.message || "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function submitBatch() {
    if (!pairs.length) {
      setError("Add at least one PDF, DXF, or STP/STEP");
      return;
    }
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const body = new FormData();
      for (const p of pairs) {
        if (p.pdf) body.append("files", p.pdf);
        if (p.dxf) body.append("files", p.dxf);
        if (p.stp) body.append("files", p.stp);
      }
      const result = await api("/api/jobs/batch", { method: "POST", body });
      const n = result.created_count ?? (result.jobs || []).length;
      const skipNotes = [...(result.skipped || []), ...(result.errors || [])];
      if (skipNotes.length) {
        setInfo(`Created ${n} job(s). Notes: ${skipNotes.join("; ")}`);
      }
      navigate("/jobs", {
        state: {
          batchCreated: n,
          batchSkipped: result.skipped || [],
          batchErrors: result.errors || [],
        },
      });
    } catch (err) {
      setError(err.message || "Batch upload failed");
    } finally {
      setBusy(false);
    }
  }

  const multi = pairs.length > 1;

  return (
    <div className="panel">
      <h1 style={{ marginTop: 0 }}>New quote job</h1>
      <p className="muted">
        Drop <strong>all</strong> files the customer sent — PDF, DXF, and/or STP/STEP
        (any subset). Matching filename stems become one job. Review ops here, then
        push the quote into <strong>SecturaFAB</strong> (that is the review surface).
        Printable shop-labor HTML is a fallback only.
      </p>

      <div
        className={`dropzone ${active ? "active" : ""}`}
        onDragEnter={(e) => {
          e.preventDefault();
          setActive(true);
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setActive(true);
        }}
        onDragLeave={() => setActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setActive(false);
          onFiles(e.dataTransfer.files);
        }}
        onClick={() => document.getElementById("file-input").click()}
      >
        <h2>Drag & drop drawings</h2>
        <p>PDF · DXF · STP/STEP — any combination per part stem</p>
        <div className="file-chips">
          {pairs.length ? (
            <span className="chip">
              {pairs.length} part{pairs.length === 1 ? "" : "s"} ready
            </span>
          ) : (
            <span className="chip">No drawings yet</span>
          )}
        </div>
        <input
          id="file-input"
          type="file"
          accept=".pdf,.dxf,.stp,.step"
          multiple
          hidden
          onChange={(e) => {
            onFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {pairs.length || skipped.length ? (
        <table className="jobs-table" style={{ marginTop: "1rem" }}>
          <thead>
            <tr>
              <th>Stem</th>
              <th>PDF</th>
              <th>DXF</th>
              <th>STP</th>
            </tr>
          </thead>
          <tbody>
            {pairs.map((p) => (
              <tr key={p.stem}>
                <td className="mono">{p.stem}</td>
                <td>{p.pdf ? p.pdf.name : <span className="muted">—</span>}</td>
                <td>{p.dxf ? p.dxf.name : <span className="muted">—</span>}</td>
                <td>{p.stp ? p.stp.name : <span className="muted">— (library lookup)</span>}</td>
              </tr>
            ))}
            {skipped.map((msg) => (
              <tr key={msg}>
                <td colSpan={4} className="muted">
                  {msg}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}

      {!multi ? (
        <>
          <div className="field" style={{ marginTop: "1rem" }}>
            <label htmlFor="title">Job title (optional)</label>
            <input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. 28106-1 Lower Boom Weldment"
            />
            <p className="muted" style={{ margin: "0.35rem 0 0", fontSize: "0.85rem" }}>
              For Time multi-option BOMs, put the dash in the title (28106-1) or use the
              field below so the app reads the correct qty column.
            </p>
          </div>

          <div className="field" style={{ marginTop: "1rem" }}>
            <label htmlFor="bom-config">BOM config / dash (optional)</label>
            <input
              id="bom-config"
              value={bomConfig}
              onChange={(e) => setBomConfig(e.target.value)}
              placeholder="-1"
            />
            <p className="muted" style={{ margin: "0.35rem 0 0", fontSize: "0.85rem" }}>
              Example: <code>-1</code> or <code>1</code> selects the <strong>-1</strong> column
              on drawings with -4/-3/-2/-1 qty options. Also auto-detected from titles like
              28106-1 or folders named …28106-1.
            </p>
          </div>
        </>
      ) : (
        <p className="muted" style={{ marginTop: "1rem" }}>
          Batch mode: each stem becomes its own job and its own SecturaFAB quote after
          review.
        </p>
      )}

      <div className="row">
        {multi ? (
          <button
            className="btn"
            type="button"
            disabled={busy || !pairs.length}
            onClick={submitBatch}
          >
            {busy ? "Starting batch…" : `Start batch (${pairs.length})`}
          </button>
        ) : (
          <>
            <button
              className="btn"
              type="button"
              disabled={busy || !pairs.length}
              onClick={submitSingle}
            >
              {busy ? "Uploading…" : "Start takeoff"}
            </button>
            {pairs.length === 1 ? (
              <button
                className="btn secondary"
                type="button"
                disabled={busy}
                onClick={submitBatch}
              >
                Start as batch of 1
              </button>
            ) : null}
          </>
        )}
        <button
          className="btn ghost"
          type="button"
          onClick={() => {
            setFiles([]);
            setTitle("");
            setBomConfig("");
            setError("");
            setInfo("");
          }}
        >
          Clear
        </button>
      </div>
      {error ? <div className="error">{error}</div> : null}
      {info ? <p className="muted">{info}</p> : null}
    </div>
  );
}
