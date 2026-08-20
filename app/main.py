from __future__ import annotations

import json
import shutil
import threading
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from quote_core.capabilities import load_shop_capabilities
from quote_core.config import load_shop_rates

from .auth import login, require_auth
from .batch import pair_upload_files, paired_part_summary
from .db import Job, SessionLocal, init_db
from .paths import FRONTEND_DIST, RATES_PATH, UPLOAD_DIR, ensure_data_dirs
from .services import process_job, push_jobs_secturafab_batch, recompute_from_items

app = FastAPI(title="Kannon Quote App", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    ensure_data_dirs()
    init_db()


class LoginBody(BaseModel):
    password: str = ""


class ReviewUpdate(BaseModel):
    items: list[dict[str, Any]]
    efficiency_pct: float | None = None
    ipm_overrides: dict[str, float] | None = None
    fitup_drivers: dict[str, Any] | None = None
    bom_config: str | None = None
    title: str | None = None
    status: str | None = Field(
        default=None, description="review | accepted | needs_info"
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/login")
def api_login(body: LoginBody) -> dict[str, Any]:
    token = login(body.password)
    rates = load_shop_rates(RATES_PATH)
    return {
        "token": token,
        "auth_required": bool(rates.shared_password),
        "default_efficiency_pct": rates.default_efficiency_pct,
    }


@app.get("/api/rates")
def get_rates(_: str = Depends(require_auth)) -> dict[str, Any]:
    rates = load_shop_rates(RATES_PATH)
    return {
        "default_efficiency_pct": rates.default_efficiency_pct,
        "weld_process": rates.weld_process,
        "weld_ipm": rates.weld_ipm,
        "default_ipm": rates.default_ipm,
        "fitup": {
            "default_band_id": rates.fitup.default_band_id,
            "formula": "fitup = sum(per-piece minutes for each physical piece by its weight band)",
            "weight_bands": [
                {
                    "id": b.id,
                    "label": b.label,
                    "max_lb": b.max_lb,
                    "with_fixture": {
                        "per_piece_minutes": b.with_fixture.per_piece_minutes,
                        "per_part_minutes": b.with_fixture.per_piece_minutes,
                    },
                    "no_fixture": {
                        "per_piece_minutes": b.no_fixture.per_piece_minutes,
                        "per_part_minutes": b.no_fixture.per_piece_minutes,
                    },
                }
                for b in rates.fitup.bands
            ],
        },
        "always_ask": rates.always_ask,
        "config_path": str(RATES_PATH),
        "help": "Edit config/shop_rates.yaml and restart the server to apply changes.",
    }


@app.get("/api/jobs")
def list_jobs(_: str = Depends(require_auth)) -> list[dict[str, Any]]:
    db = SessionLocal()
    try:
        jobs = db.query(Job).order_by(Job.id.desc()).limit(100).all()
        return [j.to_dict() for j in jobs]
    finally:
        db.close()


class BatchPushBody(BaseModel):
    job_ids: list[int] = Field(default_factory=list)


def _persist_new_job(
    *,
    pdf_filename: str | None = None,
    pdf_bytes: bytes | None = None,
    dxf_filename: str | None = None,
    dxf_bytes: bytes | None = None,
    stp_filename: str | None = None,
    stp_bytes: bytes | None = None,
    title: str = "",
    bom_config: str = "",
) -> dict[str, Any]:
    """Create a job row, write files, return to_dict (caller starts process_job)."""
    from quote_core.bom_config import resolve_bom_config

    has_pdf = bool(pdf_filename and pdf_bytes is not None)
    has_dxf = bool(dxf_filename and dxf_bytes is not None)
    has_stp = bool(stp_filename and stp_bytes is not None)
    if not (has_pdf or has_dxf or has_stp):
        raise HTTPException(400, "Need at least one PDF, DXF, or STP/STEP file")

    ensure_data_dirs()
    db = SessionLocal()
    try:
        rates = load_shop_rates(RATES_PATH)
        fallback_name = pdf_filename or dxf_filename or stp_filename or "job"
        job_title = (title or "").strip() or Path(fallback_name).stem
        resolved_config = resolve_bom_config(
            explicit=bom_config,
            title=job_title,
            pdf_filename=pdf_filename or dxf_filename or stp_filename or "",
        )
        job = Job(
            title=job_title,
            status="uploaded",
            pdf_filename=pdf_filename or "",
            dxf_filename=dxf_filename,
            stp_filename=stp_filename,
            bom_config=resolved_config,
            efficiency_pct=rates.default_efficiency_pct,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        job_dir = UPLOAD_DIR / str(job.id)
        job_dir.mkdir(parents=True, exist_ok=True)

        if has_pdf:
            if not str(pdf_filename).lower().endswith(".pdf"):
                raise HTTPException(400, f"Invalid PDF: {pdf_filename}")
            pdf_dest = job_dir / str(pdf_filename)
            pdf_dest.write_bytes(pdf_bytes or b"")
            job.pdf_path = str(pdf_dest)
            job.pdf_filename = str(pdf_filename)

        if has_dxf:
            suffix = Path(str(dxf_filename)).suffix.lower()
            if suffix != ".dxf":
                raise HTTPException(400, f"Invalid DXF: {dxf_filename}")
            dxf_dest = job_dir / str(dxf_filename)
            dxf_dest.write_bytes(dxf_bytes or b"")
            job.dxf_path = str(dxf_dest)
            job.dxf_filename = str(dxf_filename)

        if has_stp:
            suffix = Path(str(stp_filename)).suffix.lower()
            if suffix not in {".stp", ".step"}:
                raise HTTPException(400, f"Invalid STP: {stp_filename}")
            stp_dest = job_dir / str(stp_filename)
            stp_dest.write_bytes(stp_bytes or b"")
            job.stp_path = str(stp_dest)
            job.stp_filename = str(stp_filename)

        db.commit()
        db.refresh(job)
        return job.to_dict()
    finally:
        db.close()


@app.get("/api/capabilities")
def get_capabilities(_: str = Depends(require_auth)) -> dict[str, Any]:
    caps = load_shop_capabilities()
    return {
        "source": caps.get("source"),
        "as_of": caps.get("as_of"),
        "in_house": caps.get("in_house") or {},
        "outsourced": caps.get("outsourced") or {},
        "placeholders": caps.get("placeholders") or {},
    }


@app.get("/api/secturafab/status")
def secturafab_status(_: str = Depends(require_auth)) -> dict[str, Any]:
    from secturafab.config import SecturaFabConfig

    cfg = SecturaFabConfig.from_env()
    try:
        cfg.require_credentials()
        return {
            "configured": True,
            "auth_mode": "client_credentials" if cfg.uses_client_credentials else "password",
            "message": "Keys present in local .env — push can authenticate.",
        }
    except ValueError as exc:
        return {
            "configured": False,
            "auth_mode": None,
            "message": str(exc),
        }


@app.post("/api/jobs")
async def create_job(
    pdf: UploadFile | None = File(None),
    dxf: UploadFile | None = File(None),
    stp: UploadFile | None = File(None),
    title: str = Form(""),
    bom_config: str = Form(""),
    _: str = Depends(require_auth),
) -> dict[str, Any]:
    pdf_name = pdf.filename if pdf and pdf.filename else None
    pdf_bytes = await pdf.read() if pdf and pdf.filename else None
    dxf_name = dxf.filename if dxf and dxf.filename else None
    dxf_bytes = await dxf.read() if dxf and dxf.filename else None
    stp_name = stp.filename if stp and stp.filename else None
    stp_bytes = await stp.read() if stp and stp.filename else None

    if pdf_name and not pdf_name.lower().endswith(".pdf"):
        raise HTTPException(400, "pdf field must be a .pdf file")
    if dxf_name and not dxf_name.lower().endswith(".dxf"):
        raise HTTPException(400, "dxf field must be a .dxf file")
    if stp_name and Path(stp_name).suffix.lower() not in {".stp", ".step"}:
        raise HTTPException(400, "stp field must be a .stp/.step file")
    if not (pdf_name or dxf_name or stp_name):
        raise HTTPException(400, "Need at least one PDF, DXF, or STP/STEP file")

    payload = _persist_new_job(
        pdf_filename=pdf_name,
        pdf_bytes=pdf_bytes,
        dxf_filename=dxf_name,
        dxf_bytes=dxf_bytes,
        stp_filename=stp_name,
        stp_bytes=stp_bytes,
        title=title,
        bom_config=bom_config,
    )
    threading.Thread(target=process_job, args=(payload["id"],), daemon=True).start()
    return payload


@app.post("/api/jobs/batch")
async def create_jobs_batch(
    files: list[UploadFile] = File(...),
    _: str = Depends(require_auth),
) -> dict[str, Any]:
    """
    Create one job per filename stem. Pair PDF / DXF / STP(STEP) by stem.
    Any non-empty subset is a job. Starts takeoff for each created job.
    """
    if not files:
        raise HTTPException(400, "No files uploaded")

    raw: list[tuple[str, bytes]] = []
    for f in files:
        name = f.filename or ""
        data = await f.read()
        raw.append((name, data))

    paired, skipped = pair_upload_files(raw)
    if not paired:
        raise HTTPException(
            400,
            "No PDF, DXF, or STP/STEP files found to create jobs. "
            + ("; ".join(skipped) if skipped else ""),
        )

    created: list[dict[str, Any]] = []
    errors: list[str] = []
    for part in paired:
        try:
            payload = _persist_new_job(
                pdf_filename=part.pdf_name,
                pdf_bytes=part.pdf_bytes,
                dxf_filename=part.dxf_name,
                dxf_bytes=part.dxf_bytes,
                stp_filename=part.stp_name,
                stp_bytes=part.stp_bytes,
            )
            threading.Thread(
                target=process_job, args=(payload["id"],), daemon=True
            ).start()
            row = dict(payload)
            row["pair"] = paired_part_summary(part)
            created.append(row)
        except HTTPException as exc:
            errors.append(f"{part.stem}: {exc.detail}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{part.stem}: {exc}")

    return {
        "jobs": created,
        "created_count": len(created),
        "skipped": skipped,
        "errors": errors,
    }


@app.post("/api/jobs/batch-push")
def batch_push_secturafab(
    body: BatchPushBody, _: str = Depends(require_auth)
) -> dict[str, Any]:
    """
    Queue sequential SecturaFAB pushes for ready jobs.
    Returns immediately; poll each job's takeoff.secturafab.status.
    """
    from secturafab.config import SecturaFabConfig

    from .push_readiness import job_push_readiness
    from .services import _PUSH_IN_FLIGHT

    try:
        SecturaFabConfig.from_env().require_credentials()
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    job_ids = [int(x) for x in (body.job_ids or []) if int(x) > 0]
    if not job_ids:
        raise HTTPException(400, "job_ids required")

    queued: list[int] = []
    rejected: list[dict[str, Any]] = []

    db = SessionLocal()
    try:
        for job_id in job_ids:
            job = db.get(Job, job_id)
            if not job:
                rejected.append({"job_id": job_id, "reason": "not found"})
                continue
            if job.status in {"uploaded", "processing"}:
                rejected.append(
                    {"job_id": job_id, "reason": "takeoff still running"}
                )
                continue
            readiness = job_push_readiness(job)
            if not readiness["ready"]:
                rejected.append(
                    {
                        "job_id": job_id,
                        "reason": readiness["reason"] or "not ready to push",
                    }
                )
                continue
            takeoff = job.takeoff()
            existing = takeoff.get("secturafab") or {}
            if existing.get("status") in _PUSH_IN_FLIGHT:
                rejected.append(
                    {"job_id": job_id, "reason": "push already in progress"}
                )
                continue
            takeoff["secturafab"] = {
                "ok": False,
                "status": "pushing",
                "attempts": 0,
                "notes": ["SecturaFAB batch push queued"],
                "error": None,
                "last_error": None,
                "next_retry_at": None,
            }
            job.set_takeoff(takeoff)
            queued.append(job_id)
        db.commit()
    finally:
        db.close()

    if queued:
        threading.Thread(
            target=push_jobs_secturafab_batch, args=(queued,), daemon=True
        ).start()

    return {
        "queued": queued,
        "queued_count": len(queued),
        "rejected": rejected,
    }


# Parameterized job routes after static /batch paths so "batch" is never treated as job_id.
@app.get("/api/jobs/{job_id}")
def get_job(job_id: int, _: str = Depends(require_auth)) -> dict[str, Any]:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        return job.to_dict()
    finally:
        db.close()


@app.patch("/api/jobs/{job_id}")
def update_job(
    job_id: int, body: ReviewUpdate, _: str = Depends(require_auth)
) -> dict[str, Any]:
    from quote_core.bom_config import normalize_bom_config

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        if body.title is not None and body.title.strip():
            job.title = body.title.strip()
        if body.bom_config is not None:
            job.bom_config = normalize_bom_config(body.bom_config)
        recompute_from_items(
            job,
            body.items,
            efficiency_pct=body.efficiency_pct,
            ipm_overrides=body.ipm_overrides,
            fitup_drivers=body.fitup_drivers,
        )
        if body.status:
            if body.status not in {"review", "accepted", "needs_info"}:
                raise HTTPException(400, "Invalid status")
            job.status = body.status
        elif job.status == "error":
            job.status = "review"
        db.commit()
        db.refresh(job)
        return job.to_dict()
    finally:
        db.close()


@app.post("/api/jobs/{job_id}/reprocess")
def reprocess_job(job_id: int, _: str = Depends(require_auth)) -> dict[str, Any]:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        payload = job.to_dict()
    finally:
        db.close()
    threading.Thread(target=process_job, args=(job_id,), daemon=True).start()
    return payload


@app.post("/api/jobs/{job_id}/stp")
async def attach_stp(
    job_id: int, stp: UploadFile = File(...), _: str = Depends(require_auth)
) -> dict[str, Any]:
    if not stp.filename:
        raise HTTPException(400, "STP/STEP file is required")
    suffix = Path(stp.filename).suffix.lower()
    if suffix not in {".stp", ".step"}:
        raise HTTPException(400, "STP/STEP file required")

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        job_dir = UPLOAD_DIR / str(job.id)
        job_dir.mkdir(parents=True, exist_ok=True)
        stp_dest = job_dir / stp.filename
        with stp_dest.open("wb") as f:
            shutil.copyfileobj(stp.file, f)
        job.stp_filename = stp.filename
        job.stp_path = str(stp_dest)
        db.commit()
        db.refresh(job)
        job_id_out = job.id
        payload = job.to_dict()
    finally:
        db.close()

    threading.Thread(target=process_job, args=(job_id_out,), daemon=True).start()
    return payload


@app.post("/api/jobs/{job_id}/dxf")
async def attach_dxf(
    job_id: int, dxf: UploadFile = File(...), _: str = Depends(require_auth)
) -> dict[str, Any]:
    if not dxf.filename:
        raise HTTPException(400, "DXF file is required")
    if Path(dxf.filename).suffix.lower() != ".dxf":
        raise HTTPException(400, "DXF file required")

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            raise HTTPException(404, "Job not found")

        job_dir = UPLOAD_DIR / str(job.id)
        job_dir.mkdir(parents=True, exist_ok=True)
        dxf_dest = job_dir / dxf.filename
        with dxf_dest.open("wb") as f:
            shutil.copyfileobj(dxf.file, f)
        job.dxf_filename = dxf.filename
        job.dxf_path = str(dxf_dest)
        db.commit()
        db.refresh(job)
        job_id_out = job.id
        payload = job.to_dict()
    finally:
        db.close()

    threading.Thread(target=process_job, args=(job_id_out,), daemon=True).start()
    return payload


@app.post("/api/jobs/{job_id}/find-library")
def find_library_and_reprocess(
    job_id: int, _: str = Depends(require_auth)
) -> dict[str, Any]:
    """Search the shared drawing library and re-run takeoff (auto-attaches STP if found)."""
    from .library import attach_library_stp, lookup_for_job

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        # Clear existing STP so library attach can replace a missing/bad one only when absent;
        # find-library always prefers library when job has no usable STP.
        match = lookup_for_job(job)
        summary = attach_library_stp(job, match)
        db.commit()
        db.refresh(job)
        payload = job.to_dict()
        payload["library_lookup"] = summary
    finally:
        db.close()

    threading.Thread(target=process_job, args=(job_id,), daemon=True).start()
    return payload


@app.post("/api/jobs/{job_id}/push-secturafab")
def push_job_to_secturafab(job_id: int, _: str = Depends(require_auth)) -> dict[str, Any]:
    """
    Start a background SecturaFAB push (CreateFile retries every 5 min on outage).

    Returns immediately with ``takeoff.secturafab.status`` of ``pushing``;
    poll ``GET /api/jobs/{id}`` until status is ``complete`` or ``failed``.
    """
    from secturafab.config import SecturaFabConfig

    from .push_readiness import job_push_readiness
    from .services import _PUSH_IN_FLIGHT, push_job_secturafab

    try:
        SecturaFabConfig.from_env().require_credentials()
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        if job.status in {"uploaded", "processing"}:
            raise HTTPException(400, "Wait for takeoff to finish before pushing")

        readiness = job_push_readiness(job)
        if not readiness["ready"]:
            raise HTTPException(
                400,
                readiness["reason"]
                or "needs STEP or library match before SecturaFAB push",
            )

        takeoff = job.takeoff()
        existing = takeoff.get("secturafab") or {}
        if existing.get("status") in _PUSH_IN_FLIGHT:
            raise HTTPException(
                409,
                "SecturaFAB push already in progress — wait for it to finish or fail",
            )

        takeoff["secturafab"] = {
            "ok": False,
            "status": "pushing",
            "attempts": 0,
            "notes": ["SecturaFAB push queued"],
            "error": None,
            "last_error": None,
            "next_retry_at": None,
        }
        job.set_takeoff(takeoff)
        db.commit()
        db.refresh(job)
        payload = job.to_dict()
        payload["secturafab_push"] = takeoff["secturafab"]
    finally:
        db.close()

    threading.Thread(target=push_job_secturafab, args=(job_id,), daemon=True).start()
    return payload


@app.get("/api/jobs/{job_id}/export")
def export_job(job_id: int, _: str = Depends(require_auth)) -> JSONResponse:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        return JSONResponse(job.to_dict())
    finally:
        db.close()


@app.get("/api/jobs/{job_id}/export.html", response_class=HTMLResponse)
def export_job_html(job_id: int, _: str = Depends(require_auth)) -> str:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        data = job.to_dict()
    finally:
        db.close()

    times = data.get("times") or {}
    rows = "".join(
        f"<tr><td>{s.get('size')}</td><td>{s.get('inches')}</td>"
        f"<td>{s.get('ipm')}</td><td>{round(s.get('weld_minutes', 0), 2)}</td></tr>"
        for s in times.get("by_size") or []
    )
    flags = "".join(f"<li>{f}</li>" for f in data.get("flags") or [])
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Job {job.id} — {job.title}</title>
<style>
body{{font-family:Segoe UI,sans-serif;margin:2rem;color:#1a1a1a}}
table{{border-collapse:collapse;width:100%;margin:1rem 0}}
th,td{{border:1px solid #ccc;padding:.5rem;text-align:left}}
h1{{margin-bottom:.25rem}} .meta{{color:#555}}
</style></head><body>
<h1>{job.title}</h1>
<p class="meta">Job #{job.id} · Status: {job.status} · Efficiency: {job.efficiency_pct}%</p>
<h2>Weld inches by size</h2>
<table><thead><tr><th>Size</th><th>Inches</th><th>IPM</th><th>Weld min</th></tr></thead>
<tbody>{rows or '<tr><td colspan="4">No lines</td></tr>'}</tbody></table>
<h2>Times</h2>
<ul>
<li>Total inches: {times.get('total_inches', 0)}</li>
<li>Weld minutes: {round(times.get('weld_minutes', 0), 2)}</li>
<li><strong>No fixture: {times.get('quoted_no_fixture_hours', 0)} hr</strong>
 (includes {round(times.get('fitup_no_fixture_minutes', 0), 0):.0f} min fit-up)</li>
<li><strong>With fixture: {times.get('quoted_with_fixture_hours', 0)} hr</strong>
 (includes {round(times.get('fitup_with_fixture_minutes', 0), 0):.0f} min fit-up)</li>
</ul>
<h2>Review flags</h2>
<ul>{flags or '<li>None</li>'}</ul>
<pre style="background:#f6f6f6;padding:1rem;overflow:auto">{json.dumps(data, indent=2)}</pre>
</body></html>"""


# Serve React/static build with SPA fallback for client-side routes.
if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str) -> FileResponse:
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
