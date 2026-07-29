import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function JobsPage() {
  const [jobs, setJobs] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const data = await api("/api/jobs");
        if (alive) setJobs(data);
      } catch (err) {
        if (alive) setError(err.message);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className="panel">
      <h1 style={{ marginTop: 0 }}>Jobs</h1>
      {error ? <div className="error">{error}</div> : null}
      <table className="jobs-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Title</th>
            <th>Status</th>
            <th>Inches</th>
            <th>Quoted (fixture)</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((j) => (
            <tr key={j.id}>
              <td className="mono">{j.id}</td>
              <td>{j.title}</td>
              <td>
                <span className={`status ${j.status}`}>{j.status}</span>
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
          ))}
          {!jobs.length ? (
            <tr>
              <td colSpan={6} className="muted">
                No jobs yet. Upload a PDF to start.
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
