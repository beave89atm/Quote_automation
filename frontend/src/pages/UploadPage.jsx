import { useCallback, useEffect, useMemo, useState } from "react";
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
  const [mode, setMode] = useState("weldment");
  const [pinMode, setPinMode] = useState(false);

  const { pairs, skipped } = useMemo(() => pairLocalFiles(files), [files]);
  const multi = pairs.length > 1;

  useEffect(() => {
    if (pinMode) return;
    if (multi && mode !== "loose_piece") setMode("loose_piece");
    if (!multi && files.length === 0 && mode !== "weldment") setMode("weldment");
  }, [multi, files.length, mode, pinMode]);

  function chooseMode(next) {
    setPinMode(true);
    setMode(next);
    setError("");
    setInfo("");
  }

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
      body.append("intake_mode", "weldment");
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
          intakeMode: "loose_piece",
        },
      });
    } catch (err) {
      setError(err.message || "Batch upload failed");
    } finally {
      setBusy(false);
    }
  }

  const weldmentBlocked = mode === "weldment" && multi;

  return (
    <div className="panel">
      <h1 style={{ marginTop: 0 }}>New quote job</h1>
      <p className="muted">
        Two intake modes. Quote number is the <strong>part number</strong> (repeat
        parts — not a project number). Review here, then push each part into{" "}
        <strong>SecturaFAB</strong>. Printable HTML is a fallback only.
      </p>
      <div className="mode-toggle" role="tablist" aria-label="Intake mode">
        <button
          type="button"
          className={`mode-btn ${mode === "weldment" ? "active" : ""}`}
          onClick={() => chooseMode("weldment")}
        >
          Weldment
        </button>
        <button
          type="button"
          className={`mode-btn ${mode === "loose_piece" ? "active" : ""}`}
          onClick={() => chooseMode("loose_piece")}
        >
          Loose-piece batch
        </button>
      </div>
      {mode === "weldment" ? (
        <p className="muted">
          Drop <strong>one top-level weldment</strong>. The app looks up BOM child
          drawings and STP in the office drawing library (
          <span className="mono">drawing_library.roots</span> — typically Fort Worth
          Engineering Customer Drawings). You do not upload each child. Extra files
          only if they are <em>not</em> already in the library.
        </p>
      ) : (
        <p className="muted">
          Drag all piece-part drawings at once (~30 is fine). Each stem becomes its
          own job and later its own SecturaFAB quote. Sibling library PDFs are not
          this part&apos;s BOM. That part&apos;s STP is still auto-attached when found.
        </p>
      )}
      {weldmentBlocked ? (
        <div className="error">
          Weldment mode is one top-level drawing. Switch to Loose-piece batch to
          drop {pairs.length} parts, or clear extras and keep one weldment.
        </div>
      ) : null}

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
        <p>
          {mode === "loose_piece"
            ? "Drop all piece-part PDFs / DXF / STP at once"
            : "Top-level weldment is enough when the library has the children"}
        </p>
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

      {mode === "weldment" && !multi ? (
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
        {mode === "loose_piece" ? (
          <button
            className="btn"
            type="button"
            disabled={busy || !pairs.length}
            onClick={submitBatch}
          >
            {busy
              ? "Starting batch…"
              : `Start ${pairs.length} individual quote${pairs.length === 1 ? "" : "s"}`}
          </button>
        ) : (
          <button
            className="btn"
            type="button"
            disabled={busy || !pairs.length || weldmentBlocked}
            onClick={submitSingle}
          >
            {busy ? "Uploading…" : "Start weldment takeoff"}
          </button>
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
            setPinMode(false);
            setMode("weldment");
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
