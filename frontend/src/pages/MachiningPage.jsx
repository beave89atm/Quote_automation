import { useEffect, useState } from "react";
import { api } from "../api";

const MILL_DEFAULTS = {
  material: "carbon_steel",
  qty: 1,
  length_in: 8,
  width_in: 6,
  height_in: 1.5,
  face_area_in2: 48,
  pocket_volume_in3: "",
  contour_length_in: "",
  hole_count: 4,
  hole_diameter_in: 0.375,
  hole_depth_in: 1.5,
  needs_4th_axis: false,
  fourth_axis_diameter_in: "",
  setups: 1,
};

const LATHE_DEFAULTS = {
  material: "carbon_steel",
  qty: 1,
  diameter_in: 4,
  length_in: 6,
  stock_diameter_in: 4.5,
  turn_length_in: 6,
  bore_length_in: "",
  bore_diameter_in: "",
  face: true,
  finish: true,
  needs_live_tooling: false,
  setups: 1,
};

function FlagList({ flags }) {
  if (!flags?.length) return null;
  const blocking = flags.filter((f) => f.blocking);
  const notes = flags.filter((f) => !f.blocking);
  return (
    <>
      {blocking.length > 0 && (
        <div className="flags">
          <h3>Out of envelope — do not silent-quote</h3>
          <ul>
            {blocking.map((f) => (
              <li key={f.code}>
                <span className="mono">{f.code}</span> — {f.message}
              </li>
            ))}
          </ul>
        </div>
      )}
      {notes.length > 0 && (
        <div className="fitup-notes" style={{ borderTop: 0, paddingTop: 0 }}>
          <ul>
            {notes.map((f) => (
              <li key={f.code}>
                <span className="mono">{f.code}</span> — {f.message}
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}

function ResultCard({ result }) {
  if (!result) return null;
  const t = result.times || {};
  const suggested = result.machine?.suggested;
  return (
    <div>
      {!result.ok_to_quote && (
        <p className="error">
          Part is outside the July 27 envelope. Minutes below are for review only.
        </p>
      )}
      <div className="metrics">
        <div className="metric">
          <div className="label">Setup (placeholder)</div>
          <div className="value">{t.setup_minutes} min</div>
        </div>
        <div className="metric">
          <div className="label">Run / pc (incl. non-cut factor)</div>
          <div className="value">{t.run_minutes_each} min</div>
        </div>
        <div className="metric">
          <div className="label">Total</div>
          <div className="value">{t.total_minutes} min</div>
        </div>
        <div className="metric">
          <div className="label">Suggested class</div>
          <div className="value" style={{ fontSize: "1rem" }}>
            {result.machine?.suggested_class}
          </div>
        </div>
      </div>
      {suggested && (
        <p>
          Suggested machine: <strong>{suggested.display_name}</strong>
          {suggested.taper ? ` · ${suggested.taper}` : ""}
          {suggested.live_tooling ? " · live tooling" : ""}
          {suggested.model ? "" : " (exact model TBD)"}
        </p>
      )}
      <FlagList flags={result.flags} />
      <h3>Ops</h3>
      <table className="jobs-table">
        <thead>
          <tr>
            <th>Op</th>
            <th>Cut min</th>
            <th>Formula</th>
          </tr>
        </thead>
        <tbody>
          {(result.ops || []).length === 0 ? (
            <tr>
              <td colSpan={3} className="muted">
                No timed features
              </td>
            </tr>
          ) : (
            result.ops.map((op, i) => (
              <tr key={`${op.op}-${i}`}>
                <td>{op.op}</td>
                <td className="mono">{op.cut_minutes}</td>
                <td className="muted">{op.formula}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
      <details className="fitup-notes">
        <summary>Tooling / feeds used</summary>
        <pre className="mono" style={{ whiteSpace: "pre-wrap" }}>
          {JSON.stringify({ tool: result.tool, material: result.material }, null, 2)}
        </pre>
      </details>
    </div>
  );
}

export default function MachiningPage() {
  const [tab, setTab] = useState("mill");
  const [meta, setMeta] = useState(null);
  const [roster, setRoster] = useState(null);
  const [millForm, setMillForm] = useState(MILL_DEFAULTS);
  const [latheForm, setLatheForm] = useState(LATHE_DEFAULTS);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [m, r] = await Promise.all([api("/api/machining"), api("/api/machines")]);
        setMeta(m);
        setRoster(r);
      } catch (err) {
        setError(err.message);
      }
    })();
  }, []);

  const materials = Object.keys(meta?.materials || { carbon_steel: {} });

  function setField(which, key, value) {
    if (which === "mill") setMillForm((prev) => ({ ...prev, [key]: value }));
    else setLatheForm((prev) => ({ ...prev, [key]: value }));
  }

  function numOrNull(value) {
    if (value === "" || value === null || value === undefined) return null;
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }

  async function submit(which) {
    setBusy(true);
    setError("");
    try {
      if (which === "mill") {
        const body = {
          ...millForm,
          qty: Number(millForm.qty) || 1,
          length_in: Number(millForm.length_in),
          width_in: Number(millForm.width_in),
          height_in: Number(millForm.height_in),
          face_area_in2: numOrNull(millForm.face_area_in2),
          pocket_volume_in3: numOrNull(millForm.pocket_volume_in3),
          contour_length_in: numOrNull(millForm.contour_length_in),
          hole_count: Number(millForm.hole_count) || 0,
          hole_diameter_in: numOrNull(millForm.hole_diameter_in),
          hole_depth_in: numOrNull(millForm.hole_depth_in),
          fourth_axis_diameter_in: numOrNull(millForm.fourth_axis_diameter_in),
          setups: Number(millForm.setups) || 1,
        };
        setResult(await api("/api/machining/mill", { method: "POST", json: body }));
      } else {
        const body = {
          ...latheForm,
          qty: Number(latheForm.qty) || 1,
          diameter_in: Number(latheForm.diameter_in),
          length_in: Number(latheForm.length_in),
          stock_diameter_in: numOrNull(latheForm.stock_diameter_in),
          turn_length_in: numOrNull(latheForm.turn_length_in),
          bore_length_in: numOrNull(latheForm.bore_length_in),
          bore_diameter_in: numOrNull(latheForm.bore_diameter_in),
          setups: Number(latheForm.setups) || 1,
        };
        setResult(await api("/api/machining/lathe", { method: "POST", json: body }));
      }
    } catch (err) {
      setResult(null);
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel">
      <h1 style={{ marginTop: 0 }}>Mill / lathe calculator</h1>
      <p className="muted">
        Reviewable speeds-and-feeds quote. Formulas are published (Harvey Tool,
        Kennametal, MachiningDoctor). <strong>Rates and setup minutes are
        placeholders</strong> until Kyle sends tooling and shop times. Does not
        push to SecturaFAB. Coating is a stub.
      </p>

      <div className="row" style={{ marginTop: 0 }}>
        <button
          type="button"
          className={tab === "mill" ? "btn" : "btn ghost"}
          onClick={() => {
            setTab("mill");
            setResult(null);
          }}
        >
          Mill
        </button>
        <button
          type="button"
          className={tab === "lathe" ? "btn" : "btn ghost"}
          onClick={() => {
            setTab("lathe");
            setResult(null);
          }}
        >
          Lathe
        </button>
      </div>

      {tab === "mill" ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submit("mill");
          }}
        >
          <div className="calc-grid">
            <label className="field">
              Material
              <select
                value={millForm.material}
                onChange={(e) => setField("mill", "material", e.target.value)}
              >
                {materials.map((k) => (
                  <option key={k} value={k}>
                    {meta?.materials?.[k]?.label || k}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Qty
              <input
                type="number"
                min="1"
                value={millForm.qty}
                onChange={(e) => setField("mill", "qty", e.target.value)}
              />
            </label>
            <label className="field">
              Length (in)
              <input
                type="number"
                step="0.01"
                value={millForm.length_in}
                onChange={(e) => setField("mill", "length_in", e.target.value)}
              />
            </label>
            <label className="field">
              Width (in)
              <input
                type="number"
                step="0.01"
                value={millForm.width_in}
                onChange={(e) => setField("mill", "width_in", e.target.value)}
              />
            </label>
            <label className="field">
              Height (in)
              <input
                type="number"
                step="0.01"
                value={millForm.height_in}
                onChange={(e) => setField("mill", "height_in", e.target.value)}
              />
            </label>
            <label className="field">
              Face area (in²)
              <input
                type="number"
                step="0.01"
                value={millForm.face_area_in2}
                onChange={(e) => setField("mill", "face_area_in2", e.target.value)}
              />
            </label>
            <label className="field">
              Pocket volume (in³)
              <input
                type="number"
                step="0.01"
                value={millForm.pocket_volume_in3}
                onChange={(e) => setField("mill", "pocket_volume_in3", e.target.value)}
              />
            </label>
            <label className="field">
              Contour length (in)
              <input
                type="number"
                step="0.01"
                value={millForm.contour_length_in}
                onChange={(e) => setField("mill", "contour_length_in", e.target.value)}
              />
            </label>
            <label className="field">
              Holes
              <input
                type="number"
                min="0"
                value={millForm.hole_count}
                onChange={(e) => setField("mill", "hole_count", e.target.value)}
              />
            </label>
            <label className="field">
              Hole Ø (in)
              <input
                type="number"
                step="0.001"
                value={millForm.hole_diameter_in}
                onChange={(e) => setField("mill", "hole_diameter_in", e.target.value)}
              />
            </label>
            <label className="field">
              Hole depth (in)
              <input
                type="number"
                step="0.01"
                value={millForm.hole_depth_in}
                onChange={(e) => setField("mill", "hole_depth_in", e.target.value)}
              />
            </label>
            <label className="field">
              Setups
              <input
                type="number"
                min="1"
                value={millForm.setups}
                onChange={(e) => setField("mill", "setups", e.target.value)}
              />
            </label>
          </div>
          <label className="row" style={{ marginTop: "0.5rem" }}>
            <input
              type="checkbox"
              checked={millForm.needs_4th_axis}
              onChange={(e) => setField("mill", "needs_4th_axis", e.target.checked)}
            />
            Needs 4th axis (shop limit 20&quot; diameter)
          </label>
          <div className="row">
            <button className="btn" type="submit" disabled={busy}>
              {busy ? "Calculating…" : "Calculate mill"}
            </button>
          </div>
        </form>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submit("lathe");
          }}
        >
          <div className="calc-grid">
            <label className="field">
              Material
              <select
                value={latheForm.material}
                onChange={(e) => setField("lathe", "material", e.target.value)}
              >
                {materials.map((k) => (
                  <option key={k} value={k}>
                    {meta?.materials?.[k]?.label || k}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Qty
              <input
                type="number"
                min="1"
                value={latheForm.qty}
                onChange={(e) => setField("lathe", "qty", e.target.value)}
              />
            </label>
            <label className="field">
              Finish Ø (in)
              <input
                type="number"
                step="0.001"
                value={latheForm.diameter_in}
                onChange={(e) => setField("lathe", "diameter_in", e.target.value)}
              />
            </label>
            <label className="field">
              Length (in)
              <input
                type="number"
                step="0.01"
                value={latheForm.length_in}
                onChange={(e) => setField("lathe", "length_in", e.target.value)}
              />
            </label>
            <label className="field">
              Stock Ø (in)
              <input
                type="number"
                step="0.001"
                value={latheForm.stock_diameter_in}
                onChange={(e) => setField("lathe", "stock_diameter_in", e.target.value)}
              />
            </label>
            <label className="field">
              Turn length (in)
              <input
                type="number"
                step="0.01"
                value={latheForm.turn_length_in}
                onChange={(e) => setField("lathe", "turn_length_in", e.target.value)}
              />
            </label>
            <label className="field">
              Bore length (in)
              <input
                type="number"
                step="0.01"
                value={latheForm.bore_length_in}
                onChange={(e) => setField("lathe", "bore_length_in", e.target.value)}
              />
            </label>
            <label className="field">
              Bore Ø (in)
              <input
                type="number"
                step="0.001"
                value={latheForm.bore_diameter_in}
                onChange={(e) => setField("lathe", "bore_diameter_in", e.target.value)}
              />
            </label>
            <label className="field">
              Setups
              <input
                type="number"
                min="1"
                value={latheForm.setups}
                onChange={(e) => setField("lathe", "setups", e.target.value)}
              />
            </label>
          </div>
          <div className="row">
            <label>
              <input
                type="checkbox"
                checked={latheForm.face}
                onChange={(e) => setField("lathe", "face", e.target.checked)}
              />{" "}
              Face
            </label>
            <label>
              <input
                type="checkbox"
                checked={latheForm.finish}
                onChange={(e) => setField("lathe", "finish", e.target.checked)}
              />{" "}
              Finish pass
            </label>
            <label>
              <input
                type="checkbox"
                checked={latheForm.needs_live_tooling}
                onChange={(e) => setField("lathe", "needs_live_tooling", e.target.checked)}
              />{" "}
              Live tooling (Doosan)
            </label>
          </div>
          <div className="row">
            <button className="btn" type="submit" disabled={busy}>
              {busy ? "Calculating…" : "Calculate lathe"}
            </button>
          </div>
        </form>
      )}

      {error && <div className="error">{error}</div>}
      <ResultCard result={result} />

      {roster && (
        <details className="fitup-notes" style={{ marginTop: "1.5rem" }}>
          <summary>
            Machine roster ({roster.counts?.cnc_lathes} CNC lathes,{" "}
            {roster.counts?.cnc_mills} CNC mills) — July 27 2026 starting list
          </summary>
          <p className="muted">{roster.source}</p>
          <table className="jobs-table">
            <thead>
              <tr>
                <th>Machine</th>
                <th>Class</th>
                <th>Taper / live</th>
                <th>Envelope</th>
              </tr>
            </thead>
            <tbody>
              {[...(roster.lathes || []), ...(roster.mills || [])].map((m) => (
                <tr key={m.id}>
                  <td>
                    {m.display_name}
                    <div className="muted mono">{m.id}</div>
                  </td>
                  <td>
                    {m.class}
                    {m.subclass ? ` / ${m.subclass}` : ""}
                  </td>
                  <td>
                    {m.taper || "—"}
                    {m.live_tooling ? " · live" : ""}
                  </td>
                  <td className="muted">
                    {m.kind === "lathe"
                      ? `Ø ${m.envelope.min_diameter_in}–${m.envelope.max_diameter_in} × ${m.envelope.max_length_in} L (chuck ${m.envelope.max_chuck_diameter_in})`
                      : `${m.envelope.x_in} × ${m.envelope.y_in} × ${m.envelope.z_in}`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}

      {meta?.formulas && (
        <details className="fitup-notes">
          <summary>Published formulas</summary>
          <ul>
            {Object.entries(meta.formulas).map(([k, v]) => (
              <li key={k}>
                <span className="mono">{k}</span>: {v}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
