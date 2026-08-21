import { useCallback, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

function stemKey(name) {
  const base = String(name || "").replace(/^.*[\\/]/, "");
  const i = base.lastIndexOf(".");
  return (i >= 0 ? base.slice(0, i) : base).trim().toLowerCase();
}

function pairLocalFiles(fileList) {
  const pdfs = new Map();
  const stps = new Map();
  const skipped = [];

  for (const f of Array.from(fileList || [])) {
    const lower = f.name.toLowerCase();
    const key = stemKey(f.name);
    if (lower.endsWith(".pdf")) pdfs.set(key, f);
    else if (lower.endsWith(".stp") || lower.endsWith(".step")) stps.set(key, f);
    else skipped.push(`Skipped unsupported: ${f.name}`);
  }

  const pairs = [];
  for (const [key, pdf] of [...pdfs.entries()].sort((a, b) =>
    a[1].name.localeCompare(b[1].name, undefined, { sensitivity: "base" })
  )) {
    const stp = stps.get(key) || null;
    if (stp) stps.delete(key);
    pairs.push({
      stem: pdf.name.replace(/\.pdf$/i, ""),
      pdf,
      stp,
    });
  }
  for (const stp of stps.values()) {
    skipped.push(`Skipped STP without matching PDF: ${stp.name}`);
  }
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
        const lower = f.name.toLowerCase();
        const kind = lower.endsWith(".pdf")
          ? "pdf"
          : lower.endsWith(".stp") || lower.endsWith(".step")
            ? "stp"
            : "other";
        byKey.set(`${stemKey(f.name)}:${kind}`, f);
      }
      for (const f of incoming) {
        const lower = f.name.toLowerCase();
        const kind = lower.endsWith(".pdf")
          ? "pdf"
          : lower.endsWith(".stp") || lower.endsWith(".step")
            ? "stp"
            : "other";
        byKey.set(`${stemKey(f.name)}:${kind}`, f);
      }
      return [...byKey.values()];
    });
    setError("");
    setInfo("");
  }, []);

  async function submitSingle() {
    const pair = pairs[0];
    if (!pair) {
      setError("PDF is required");
      return;
    }
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const body = new FormData();
      body.append("pdf", pair.pdf);
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
      setError("Add at least one PDF");
      return;
    }
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const body = new FormData();
      for (const p of pairs) {
        body.append("files", p.pdf);
        if (p.stp) body.append("files", p.stp);
      }
      const result = await api("/api/jobs/batch", { method: "POST", body });
      const n = result.created_count ?? (result.jobs || []).length;
      const skipNotes = [...(result.skipped || []), ...(result.errors || [])];
      if (skipNotes.length) {
        setInfo(
          `Created ${n} job(s). Notes: ${skipNotes.join("; ")}`
        );
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
      <h1 style={{ marginTop: 0 }}>New weld takeoff</h1>
      <p className="muted">
        Drop one drawing, or up to ~20 unrelated PDFs (optional matching STEPs by
        filename). Each PDF stem becomes its own job and can be pushed to its own
        SecturaFAB quote after review. Orphan STPs without a PDF are skipped.
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
        <p>PDF required per part · STP/STEP optional (same filename stem)</p>
        <div className="file-chips">
          {pairs.length ? (
            <span className="chip">
              {pairs.length} part{pairs.length === 1 ? "" : "s"} ready
            </span>
          ) : (
            <span className="chip">No PDF yet</span>
          )}
        </div>
        <input
          id="file-input"
          type="file"
          accept=".pdf,.stp,.step"
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
              <th>STP</th>
            </tr>
          </thead>
          <tbody>
            {pairs.map((p) => (
              <tr key={p.stem}>
                <td className="mono">{p.stem}</td>
                <td>{p.pdf.name}</td>
                <td>{p.stp ? p.stp.name : <span className="muted">— (library lookup)</span>}</td>
              </tr>
            ))}
            {skipped.map((msg) => (
              <tr key={msg}>
                <td colSpan={3} className="muted">
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
              Job name only. Use the dash field below to pick a LIST OF MATERIAL qty
              column on Time-style multi-option drawings.
            </p>
          </div>

          <div className="field" style={{ marginTop: "1rem" }}>
            <label htmlFor="bom-config">BOM dash (qty column)</label>
            <input
              id="bom-config"
              value={bomConfig}
              onChange={(e) => setBomConfig(e.target.value)}
              placeholder="-1"
            />
            <p className="muted" style={{ margin: "0.35rem 0 0", fontSize: "0.85rem" }}>
              Which LIST OF MATERIAL qty column to read. Time-style only:{" "}
              <code>-1</code> of -4/-3/-2/-1, or the <code>1004747-1</code> column
              of two. Most drawings are a single QTY column — this does not invent
              extra dash columns. Blank / <code>-</code> cells in the chosen column
              are omitted. Columns are never summed.
            </p>
          </div>
        </>
      ) : (
        <p className="muted" style={{ marginTop: "1rem" }}>
          Batch mode: each part uses its PDF stem as the job title. Open a job later to
          set BOM config if needed.
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
