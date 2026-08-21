import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";

function pushDisabledReason(job, busy) {
  if (!job) return "Loading job…";
  const pushStatus = job.takeoff?.secturafab?.status;
  if (busy || ["pushing", "retrying_createfile"].includes(pushStatus)) {
    return "Push already in progress — wait for it to finish";
  }
  if (["uploaded", "processing"].includes(job.status)) {
    return "Wait for takeoff to finish before pushing";
  }
  if (job.push_readiness?.ready === false) {
    return job.push_readiness.reason || "needs PDF, STEP, or library match";
  }
  return null;
}

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

function bandForWeight(weight, bands) {
  const ordered = [...(bands || [])].sort((a, b) => {
    const am = a.max_lb == null ? Number.POSITIVE_INFINITY : Number(a.max_lb);
    const bm = b.max_lb == null ? Number.POSITIVE_INFINITY : Number(b.max_lb);
    return am - bm;
  });
  for (const band of ordered) {
    if (band.max_lb == null || Number(weight) < Number(band.max_lb)) return band;
  }
  return ordered[ordered.length - 1] || null;
}

function buildBandBreakdown(ratesBands, times, drivers) {
  if (Array.isArray(times?.band_breakdown) && times.band_breakdown.length) {
    return times.band_breakdown;
  }
  const fallbackBands = [
    {
      id: "lt_20",
      label: "<20 lbs",
      max_lb: 20,
      with_fixture: { per_piece_minutes: 2 },
      no_fixture: { per_piece_minutes: 4 },
    },
    {
      id: "20_50",
      label: "20-50 lbs",
      max_lb: 50,
      with_fixture: { per_piece_minutes: 4 },
      no_fixture: { per_piece_minutes: 6 },
    },
    {
      id: "50_200",
      label: "50-200 lbs",
      max_lb: 200,
      with_fixture: { per_piece_minutes: 7 },
      no_fixture: { per_piece_minutes: 10 },
    },
    {
      id: "gt_200",
      label: ">200 lbs",
      max_lb: null,
      with_fixture: { per_piece_minutes: 10 },
      no_fixture: { per_piece_minutes: 15 },
    },
  ];
  const bands = ratesBands?.length ? ratesBands : fallbackBands;

  const weights =
    times?.component_weights_lb ||
    drivers?.component_weights_lb ||
    drivers?.weight_calc?.component_weights_lb ||
    [];
  const counts = { ...(times?.band_counts || {}) };
  if (Object.keys(counts).length === 0 && weights.length) {
    for (const w of weights) {
      const band = bandForWeight(Number(w), bands);
      if (!band) continue;
      counts[band.label] = (counts[band.label] || 0) + 1;
    }
  }

  return bands.map((band) => {
    const count = Number(counts[band.label] || 0);
    const noMin = Number(
      band.no_fixture?.per_piece_minutes ?? band.no_fixture?.per_part_minutes ?? 0
    );
    const withMin = Number(
      band.with_fixture?.per_piece_minutes ?? band.with_fixture?.per_part_minutes ?? 0
    );
    return {
      id: band.id,
      label: band.label,
      piece_count: count,
      minutes_per_piece_no_fixture: noMin,
      minutes_per_piece_with_fixture: withMin,
      total_minutes_no_fixture: Math.round(count * noMin * 100) / 100,
      total_minutes_with_fixture: Math.round(count * withMin * 100) / 100,
    };
  });
}

export default function JobDetailPage() {
  const { id } = useParams();
  const [job, setJob] = useState(null);
  const [rates, setRates] = useState(null);
  const [items, setItems] = useState([]);
  const [efficiency, setEfficiency] = useState(85);
  const [partCount, setPartCount] = useState(1);
  const [jointCount, setJointCount] = useState(1);
  const [assemblyWeight, setAssemblyWeight] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [pushReady, setPushReady] = useState(false);
  const [pushElapsed, setPushElapsed] = useState(0);

  function applyDrivers(data) {
    const d = data.takeoff?.fitup_drivers || {};
    setPartCount(d.part_count ?? data.times?.part_count ?? 1);
    setJointCount(d.joint_count ?? data.times?.joint_count ?? 1);
    const w = d.assembly_weight_lb ?? data.times?.assembly_weight_lb;
    setAssemblyWeight(w == null || w === "" ? "" : String(w));
  }

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const data = await api("/api/rates");
        if (alive) setRates(data);
      } catch {
        /* rates optional for chart fallback */
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

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
        applyDrivers(data);
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
        } else if (
          ["pushing", "retrying_createfile"].includes(data.takeoff?.secturafab?.status)
        ) {
          timer = setInterval(async () => {
            try {
              const latest = await refresh();
              if (!alive) return;
              const st = latest.takeoff?.secturafab?.status;
              if (!["pushing", "retrying_createfile"].includes(st)) {
                clearInterval(timer);
              }
            } catch {
              /* ignore poll errors */
            }
          }, 15000);
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
          fitup_drivers: {
            part_count: Number(partCount) || 0,
            joint_count: Number(jointCount) || 0,
            assembly_weight_lb: assemblyWeight === "" ? null : Number(assemblyWeight),
          },
          status: status || undefined,
        },
      });
      setJob(data);
      setItems(data.takeoff?.items || []);
      applyDrivers(data);
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
        applyDrivers(data);
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

  async function pushSecturaFab() {
    setBusy(true);
    setError("");
    setPushReady(false);
    setPushElapsed(0);
    setMessage(
      "Starting SecturaFAB push… if drawing upload is down, we retry every 5 minutes automatically."
    );
    if (typeof Notification !== "undefined" && Notification.permission === "default") {
      try {
        await Notification.requestPermission();
      } catch {
        /* ignore */
      }
    }
    const started = Date.now();
    const tick = setInterval(() => {
      setPushElapsed(Math.round((Date.now() - started) / 1000));
    }, 1000);

    function finishPush(push, secs) {
      if (push?.ok || push?.status === "complete") {
        const ready = push.ready !== false;
        setPushReady(ready);
        setMessage(
          ready
            ? `Ready — SecturaFAB quote ${push.quote_number} is complete` +
                (push.item_count != null ? ` · ${push.item_count} items` : "") +
                ` · ${secs}s. Safe to open in SecturaFAB.`
            : `SecturaFAB quote ${push.quote_number} created, but finalize reported a warning — refresh the quote and check Profile/Weld/qty.`
        );
        if (typeof Notification !== "undefined" && Notification.permission === "granted") {
          try {
            new Notification(
              ready
                ? `SecturaFAB ready: ${push.quote_number}`
                : `SecturaFAB push finished with warnings: ${push.quote_number}`,
              {
                body: ready
                  ? "Profile, Weld, and quantities should be attached. Safe to open the quote."
                  : "Open the job in Quote Automation and check Profile/Weld before quoting.",
              }
            );
          } catch {
            /* ignore */
          }
        }
        return;
      }
      setError(push?.error || push?.last_error || "SecturaFAB push failed");
      setMessage("");
    }

    try {
      const data = await api(`/api/jobs/${id}/push-secturafab`, { method: "POST" });
      setJob(data);
      let push = data.secturafab_push || data.takeoff?.secturafab;
      const inFlight = new Set(["pushing", "retrying_createfile"]);

      while (inFlight.has(push?.status)) {
        if (push.status === "retrying_createfile") {
          const next = push.next_retry_at
            ? new Date(push.next_retry_at).toLocaleTimeString()
            : "soon";
          setMessage(
            `Waiting for SecturaFAB CreateFile (drawing upload). Attempt ${
              push.attempts || "?"
            } failed — next retry at ${next}. ` +
              (push.last_error ? `(${push.last_error})` : "")
          );
        } else {
          setMessage(
            "Pushing to SecturaFAB… PDF/STEP assembly can take several minutes. Status updates as steps finish."
          );
        }
        await new Promise((r) => setTimeout(r, 15000));
        const latest = await api(`/api/jobs/${id}`);
        setJob(latest);
        push = latest.takeoff?.secturafab || push;
      }

      const secs = Math.round((Date.now() - started) / 1000);
      if (!push) {
        setError("SecturaFAB push status was lost — refresh the job and check again");
      } else {
        finishPush(push, secs);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      clearInterval(tick);
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
  const drivers = job.takeoff?.fitup_drivers || {};
  const bandBreakdown = buildBandBreakdown(
    rates?.fitup?.weight_bands || [],
    times,
    drivers
  );
  const activeBands = bandBreakdown.filter(
    (r) => (r.piece_count ?? r.part_count ?? 0) > 0
  );
  const totalPieces = bandBreakdown.reduce(
    (s, r) => s + (r.piece_count ?? r.part_count ?? 0),
    0
  );
  const totalNoFixture = bandBreakdown.reduce((s, r) => s + (r.total_minutes_no_fixture || 0), 0);
  const totalWithFixture = bandBreakdown.reduce(
    (s, r) => s + (r.total_minutes_with_fixture || 0),
    0
  );
  const fitupNo =
    times.fitup_no_fixture_minutes != null
      ? Math.round(times.fitup_no_fixture_minutes)
      : Math.round(totalNoFixture);
  const fitupWith =
    times.fitup_with_fixture_minutes != null
      ? Math.round(times.fitup_with_fixture_minutes)
      : Math.round(totalWithFixture);
  const fitupNotes = [
    ...new Set(
      [
        ...(drivers.notes || []),
        ...(times.fitup_notes || []),
        ...(job.flags || []).filter((f) =>
          /fit-?up|weight|BOM|component|band/i.test(String(f))
        ),
      ].filter(Boolean)
    ),
  ];
  const materialLabel = drivers?.weight_calc?.material_label;
  const weightMethod =
    drivers?.weight_calc?.method === "pdf_bom"
      ? "PDF BOM"
      : drivers?.weight_calc?.method
        ? "calculated"
        : null;

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
            {job.bom_config ? ` · BOM -${String(job.bom_config).replace(/^-/, "")}` : ""}
          </p>
          {!job.stp_filename ? (
            <p className="error" style={{ marginTop: "0.5rem" }}>
              No STP on this job — use Find on shared drive, or attach an STP manually.
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
          <div className="label">Fit-up no fixture</div>
          <div className="value">
            {times.fitup_no_fixture_minutes != null
              ? `${Math.round(times.fitup_no_fixture_minutes)} min`
              : "—"}
          </div>
          <div className="muted" style={{ fontSize: "0.8rem", marginTop: "0.25rem" }}>
            quoted total {times.quoted_no_fixture_hours ?? "—"} hr
          </div>
        </div>
        <div className="metric">
          <div className="label">Fit-up with fixture</div>
          <div className="value">
            {times.fitup_with_fixture_minutes != null
              ? `${Math.round(times.fitup_with_fixture_minutes)} min`
              : "—"}
          </div>
          <div className="muted" style={{ fontSize: "0.8rem", marginTop: "0.25rem" }}>
            quoted total {times.quoted_with_fixture_hours ?? "—"} hr
          </div>
        </div>
      </div>

      <details className="fitup-drivers">
        <summary>
          <h2>Fit-up drivers</h2>
          <span className="fitup-summary-meta muted">
            {totalPieces || partCount || "—"} pieces
            {assemblyWeight !== "" ? ` · ${assemblyWeight} lb` : ""}
            {` · ${fitupNo} / ${fitupWith} min`}
            {materialLabel ? ` · ${materialLabel}` : ""}
          </span>
        </summary>

        <div className="row fitup-critical" style={{ flexWrap: "wrap", gap: "1rem" }}>
          <div className="field" style={{ maxWidth: 140 }}>
            <label htmlFor="parts">Pieces</label>
            <input
              id="parts"
              type="number"
              min="0"
              value={partCount}
              onChange={(e) => setPartCount(e.target.value)}
            />
          </div>
          <div className="field" style={{ maxWidth: 200 }}>
            <label htmlFor="weight">Assembly weight (lb)</label>
            <input
              id="weight"
              type="number"
              min="0"
              step="0.1"
              placeholder="auto from PDF/STP"
              value={assemblyWeight}
              onChange={(e) => setAssemblyWeight(e.target.value)}
            />
          </div>
          <div className="field" style={{ maxWidth: 140 }}>
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
        </div>

        {activeBands.length || bandBreakdown.length ? (
          <table className="takeoff-table band-table">
            <thead>
              <tr>
                <th>Weight band</th>
                <th>Pieces</th>
                <th>Min/piece (no fixture)</th>
                <th>Min/piece (with fixture)</th>
                <th>Total (no fixture)</th>
                <th>Total (with fixture)</th>
              </tr>
            </thead>
            <tbody>
              {(activeBands.length ? activeBands : bandBreakdown).map((row) => {
                const pieces = row.piece_count ?? row.part_count ?? 0;
                const minNo =
                  row.minutes_per_piece_no_fixture ?? row.minutes_per_part_no_fixture;
                const minWith =
                  row.minutes_per_piece_with_fixture ?? row.minutes_per_part_with_fixture;
                return (
                  <tr key={row.id}>
                    <td>{row.label}</td>
                    <td className="mono">{pieces}</td>
                    <td className="mono">{minNo}</td>
                    <td className="mono">{minWith}</td>
                    <td className="mono">{row.total_minutes_no_fixture}</td>
                    <td className="mono">{row.total_minutes_with_fixture}</td>
                  </tr>
                );
              })}
              <tr className="band-total-row">
                <td>Total</td>
                <td className="mono">{totalPieces}</td>
                <td></td>
                <td></td>
                <td className="mono">{fitupNo}</td>
                <td className="mono">{fitupWith}</td>
              </tr>
            </tbody>
          </table>
        ) : (
          <p className="muted">No piece weights yet — enter pieces/weight or re-run takeoff.</p>
        )}

        <details className="fitup-notes">
          <summary>
            Details &amp; notes <span className="muted">({fitupNotes.length})</span>
          </summary>
          <p className="muted" style={{ margin: "0.65rem 0 0.35rem" }}>
            Fit-up = sum of per-piece minutes by each physical piece&apos;s weight band
            (BOM qty expanded).
            {weightMethod ? ` Weight source: ${weightMethod}.` : ""}
            {materialLabel ? ` Material: ${materialLabel}.` : ""}
          </p>
          {fitupNotes.length ? (
            <ul>
              {fitupNotes.map((n) => (
                <li key={n}>{n}</li>
              ))}
            </ul>
          ) : (
            <p className="muted" style={{ margin: "0.35rem 0 0.15rem" }}>
              No extra notes.
            </p>
          )}
        </details>
      </details>

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
        <button
          className="btn"
          type="button"
          disabled={Boolean(pushDisabledReason(job, busy))}
          onClick={pushSecturaFab}
          title={
            pushDisabledReason(job, busy) ||
            "Push or update the SecturaFAB quote using the bare part number (reuses an existing quote with that number)"
          }
        >
          Push to SecturaFAB
        </button>
        {pushDisabledReason(job, busy) ? (
          <span className="muted" style={{ alignSelf: "center" }}>
            {pushDisabledReason(job, busy)}
          </span>
        ) : null}
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
      {job.takeoff?.secturafab?.ok || job.takeoff?.secturafab?.status === "complete" ? (
        <p className="muted" style={{ marginTop: "0.5rem" }}>
          Last SecturaFAB push: quote <strong>{job.takeoff.secturafab.quote_number}</strong>
          {job.takeoff.secturafab.item_count != null
            ? ` · ${job.takeoff.secturafab.item_count} items`
            : ""}
          {job.takeoff.secturafab.ready === false
            ? " · finished with warnings"
            : job.takeoff.secturafab.ready
              ? " · ready"
              : ""}
          {job.takeoff.secturafab.uploaded_files?.length
            ? ` · ${job.takeoff.secturafab.uploaded_files.join(", ")}`
            : ""}
        </p>
      ) : null}
      {["pushing", "retrying_createfile"].includes(job.takeoff?.secturafab?.status) ? (
        <p className="muted" style={{ marginTop: "0.5rem" }}>
          SecturaFAB push in progress
          {job.takeoff.secturafab.status === "retrying_createfile"
            ? ` — waiting on CreateFile (attempt ${job.takeoff.secturafab.attempts || "?"}` +
              (job.takeoff.secturafab.next_retry_at
                ? `, next ${new Date(job.takeoff.secturafab.next_retry_at).toLocaleTimeString()}`
                : "") +
              ")"
            : ""}
          . Leave this page open or come back later — retries continue in the background.
        </p>
      ) : null}
      {busy && pushElapsed > 0 ? (
        <p className="push-progress">
          Still working… {pushElapsed}s elapsed. Leave this page open — the quote is not
          finished until you see <em>Ready</em> below.
        </p>
      ) : null}
      {message ? (
        <p className={pushReady ? "push-ready" : "muted"}>{message}</p>
      ) : null}
      {error ? <div className="error">{error}</div> : null}

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

      {library?.folder ? (
        <p className="muted" style={{ marginTop: "1rem", fontSize: "0.85rem" }}>
          Shared folder: {library.folder}
          {library.attached ? " · STP auto-attached" : ""}
          {library.related_pdf_count
            ? ` · ${library.related_pdf_count} related PDF(s)`
            : ""}
        </p>
      ) : null}
    </div>
  );
}
