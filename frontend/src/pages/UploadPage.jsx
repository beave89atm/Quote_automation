import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

export default function UploadPage() {
  const navigate = useNavigate();
  const [active, setActive] = useState(false);
  const [pdf, setPdf] = useState(null);
  const [stp, setStp] = useState(null);
  const [title, setTitle] = useState("");
  const [bomConfig, setBomConfig] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const onFiles = useCallback((fileList) => {
    const files = Array.from(fileList || []);
    for (const f of files) {
      const lower = f.name.toLowerCase();
      if (lower.endsWith(".pdf")) setPdf(f);
      else if (lower.endsWith(".stp") || lower.endsWith(".step")) setStp(f);
    }
  }, []);

  async function submit() {
    if (!pdf) {
      setError("PDF is required");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const body = new FormData();
      body.append("pdf", pdf);
      if (stp) body.append("stp", stp);
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

  return (
    <div className="panel">
      <h1 style={{ marginTop: 0 }}>New weld takeoff</h1>
      <p className="muted">
        Drop a fabrication PDF. If you skip the STP, the app searches the Engineering Customer
        Drawings shared drive for a matching part folder and attaches .stp/.step when found.
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
        <p>PDF required · STP/STEP optional</p>
        <div className="file-chips">
          {pdf ? <span className="chip">PDF: {pdf.name}</span> : <span className="chip">No PDF yet</span>}
          {stp ? <span className="chip">STP: {stp.name}</span> : <span className="chip">No STP</span>}
        </div>
        <input
          id="file-input"
          type="file"
          accept=".pdf,.stp,.step"
          multiple
          hidden
          onChange={(e) => onFiles(e.target.files)}
        />
      </div>

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

      <div className="row">
        <button className="btn" type="button" disabled={busy || !pdf} onClick={submit}>
          {busy ? "Uploading…" : "Start takeoff"}
        </button>
        <button
          className="btn ghost"
          type="button"
          onClick={() => {
            setPdf(null);
            setStp(null);
            setTitle("");
            setBomConfig("");
            setError("");
          }}
        >
          Clear
        </button>
      </div>
      {error ? <div className="error">{error}</div> : null}
    </div>
  );
}
