import { useEffect, useState } from "react";
import { api } from "../api";

export default function SettingsPage() {
  const [rates, setRates] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        setRates(await api("/api/rates"));
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
        <li>Default IPM: {rates.default_ipm}</li>
      </ul>

      <h2>Weld IPM</h2>
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

      <h2>Fit-up</h2>
      <div className="metrics">
        <div className="metric">
          <div className="label">No fixture</div>
          <div className="value" style={{ fontSize: "0.95rem" }}>
            base {rates.fitup_no_fixture.base_minutes} + {rates.fitup_no_fixture.pct_of_weld * 100}% weld +{" "}
            {rates.fitup_no_fixture.per_joint_minutes}/joint
          </div>
        </div>
        <div className="metric">
          <div className="label">With fixture</div>
          <div className="value" style={{ fontSize: "0.95rem" }}>
            base {rates.fitup_with_fixture.base_minutes} + {rates.fitup_with_fixture.pct_of_weld * 100}% weld +{" "}
            {rates.fitup_with_fixture.per_joint_minutes}/joint
          </div>
        </div>
      </div>

      <h2>Always ask</h2>
      <ul>
        {(rates.always_ask || []).map((r) => (
          <li key={r}>{r}</li>
        ))}
      </ul>
    </div>
  );
}
