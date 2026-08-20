import { useEffect, useState } from "react";
import { api } from "../api";

export default function SettingsPage() {
  const [rates, setRates] = useState(null);
  const [caps, setCaps] = useState(null);
  const [sfStatus, setSfStatus] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        setRates(await api("/api/rates"));
        try {
          setCaps(await api("/api/capabilities"));
        } catch {
          /* optional */
        }
        try {
          setSfStatus(await api("/api/secturafab/status"));
        } catch {
          /* optional */
        }
      } catch (err) {
        setError(err.message);
      }
    })();
  }, []);

  if (error) {
    return (
      <div className="panel">
        <div className="error">{error}</div>
      </div>
    );
  }
  if (!rates) {
    return (
      <div className="panel">
        <p className="muted">Loading rates…</p>
      </div>
    );
  }

  const bands = rates.fitup?.weight_bands || [];

  return (
    <div className="panel">
      <h1 style={{ marginTop: 0 }}>Shop rates</h1>
      <p className="muted">
        Edit <span className="mono">{rates.config_path}</span> and restart the API to apply changes.
        See <span className="mono">config/README.md</span> for field definitions.
      </p>

      <h2>Defaults</h2>
      <ul>
        <li>Efficiency: {rates.default_efficiency_pct}%</li>
        <li>Weld process: {rates.weld_process || "manual"}</li>
        <li>Default IPM: {rates.default_ipm}</li>
      </ul>

      <h2>Manual weld IPM</h2>
      <p className="muted">Robot IPM table will be added later.</p>
      <table className="jobs-table">
        <thead>
          <tr>
            <th>Size</th>
            <th>IPM</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(rates.weld_ipm || {}).map(([size, ipm]) => (
            <tr key={size}>
              <td>{size}</td>
              <td className="mono">{ipm}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Fit-up (per piece by weight band)</h2>
      <p className="muted">
        {rates.fitup?.formula ||
          "sum(per-piece minutes for each physical piece by its weight band)"}
      </p>
      <table className="jobs-table">
        <thead>
          <tr>
            <th>Weight band</th>
            <th>With fixture</th>
            <th>No fixture</th>
          </tr>
        </thead>
        <tbody>
          {bands.map((b) => {
            const withMin =
              b.with_fixture?.per_piece_minutes ?? b.with_fixture?.per_part_minutes;
            const noMin =
              b.no_fixture?.per_piece_minutes ?? b.no_fixture?.per_part_minutes;
            return (
              <tr key={b.id}>
                <td>{b.label}</td>
                <td className="mono">{withMin} min/piece</td>
                <td className="mono">{noMin} min/piece</td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <h2>Always ask</h2>
      <ul>
        {(rates.always_ask || []).map((r) => (
          <li key={r}>{r}</li>
        ))}
      </ul>

      <h2>SecturaFAB</h2>
      {sfStatus ? (
        <p className={sfStatus.configured ? "muted" : "error"}>
          {sfStatus.configured
            ? `Configured (${sfStatus.auth_mode}). Keys stay in local .env — never commit them.`
            : sfStatus.message}
        </p>
      ) : (
        <p className="muted">Status unavailable.</p>
      )}

      {caps ? (
        <>
          <h2>Shop capabilities</h2>
          <p className="muted">
            {caps.source || "Kannon capabilities"} {caps.as_of ? `· ${caps.as_of}` : ""}
          </p>
          <h3>Outsourced (always represented on quotes)</h3>
          <ul>
            {Object.entries(caps.outsourced || {}).map(([key, val]) => (
              <li key={key}>
                <strong>{key.replace(/_/g, " ")}</strong>
                {val?.times ? ` — times ${val.times}` : ""}
                {val?.vendor ? ` · vendor ${val.vendor}` : ""}
              </li>
            ))}
          </ul>
          <h3>In-house snapshot</h3>
          <ul>
            <li>Lasers: 2 Amada (9kW / 3kW), 5×10 sheet, 18ga–3/4&quot; CS</li>
            <li>Brake: Accurpress + Safan, max 250 ton</li>
            <li>Weld: 30 manual bays + 3 OTC robots</li>
            <li>CNC mill/lathe: listed, times PARKED until Kyle un-parks machining</li>
          </ul>
        </>
      ) : null}
    </div>
  );
}
