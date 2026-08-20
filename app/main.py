from __future__ import annotations

import shutil
import threading
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from quote_core.config import load_shop_rates

from .auth import login, require_auth
from .batch import pair_upload_files, paired_part_summary
from .db import Job, SessionLocal, init_db
from .paths import FRONTEND_DIST, RATES_PATH, UPLOAD_DIR, ensure_data_dirs
from .quote_html import render_quote_html
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


def _secturafab_public_status() -> dict[str, Any]:
    from secturafab.config import SecturaFabConfig

    return SecturaFabConfig.from_env().public_status()


def _require_secturafab_credentials() -> None:
    from secturafab.config import SecturaFabConfig

    try:
        SecturaFabConfig.from_env().require_credentials()
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/rates")
def get_rates(_: str = Depends(require_auth)) -> dict[str, Any]:
    rates = load_shop_rates(RATES_PATH)
    return {
        "default_efficiency_pct": rates.default_efficiency_pct,
        "weld_process": rates.weld_process,
        "weld_ipm": rates.weld_ipm,
        "default_ipm": rates.default_ipm,
        "labor_rate_per_hour": rates.labor_rate_per_hour,
        "labor_placeholder": rates.labor_placeholder,
        "labor_notes": rates.labor_notes,
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
        "secturafab": _secturafab_public_status(),
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
    pdf_filename: str,
    pdf_bytes: bytes,
    stp_filename: str | None = None,
    stp_bytes: bytes | None = None,
    title: str = "",
    bom_config: str = "",
) -> dict[str, Any]:
    """Create a job row, write files, return to_dict (caller starts process_job)."""
    from quote_core.bom_config import resolve_bom_config

    ensure_data_dirs()
    db = SessionLocal()
    try:
        rates = load_shop_rates(RATES_PATH)
        job_title = (title or "").strip() or Path(pdf_filename).stem
        resolved_config = resolve_bom_config(
            explicit=bom_config,
            title=job_title,
            pdf_filename=pdf_filename,
        )
        job = Job(
            title=job_title,
            status="uploaded",
            pdf_filename=pdf_filename,
            stp_filename=stp_filename,
            bom_config=resolved_config,
            efficiency_pct=rates.default_efficiency_pct,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        job_dir = UPLOAD_DIR / str(job.id)
        job_dir.mkdir(parents=True, exist_ok=True)
        pdf_dest = job_dir / pdf_filename
        pdf_dest.write_bytes(pdf_bytes)
        job.pdf_path = str(pdf_dest)

        if stp_filename and stp_bytes is not None:
            suffix = Path(stp_filename).suffix.lower()
            if suffix not in {".stp", ".step"}:
                raise HTTPException(400, f"Invalid STP for {pdf_filename}")
            stp_dest = job_dir / stp_filename
            stp_dest.write_bytes(stp_bytes)
            job.stp_path = str(stp_dest)
            job.stp_filename = stp_filename

        db.commit()
        db.refresh(job)
        return job.to_dict()
    finally:
        db.close()


@app.post("/api/jobs")
async def create_job(
    pdf: UploadFile = File(...),
    stp: UploadFile | None = File(None),
    title: str = Form(""),
    bom_config: str = Form(""),
    _: str = Depends(require_auth),
) -> dict[str, Any]:
    if not pdf.filename or not pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "PDF file is required")

    pdf_bytes = await pdf.read()
    stp_name = None
    stp_bytes = None
    if stp and stp.filename:
        stp_name = stp.filename
        stp_bytes = await stp.read()

    payload = _persist_new_job(
        pdf_filename=pdf.filename,
        pdf_bytes=pdf_bytes,
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
    Create one job per PDF stem. Pair optional STP/STEP by matching filename stem.
    Orphan STPs are skipped. Starts takeoff for each created job.
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
            "No PDF files found to create jobs. "
            + ("; ".join(skipped) if skipped else ""),
        )

    created: list[dict[str, Any]] = []
    errors: list[str] = []
    for part in paired:
        try:
            payload = _persist_new_job(
                pdf_filename=part.pdf_name,
                pdf_bytes=part.pdf_bytes,
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
            errors.append(f"{part.pdf_name}: {exc.detail}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{part.pdf_name}: {exc}")

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
    from .push_readiness import job_push_readiness
    from .services import _PUSH_IN_FLIGHT

    job_ids = [int(x) for x in (body.job_ids or []) if int(x) > 0]
    if not job_ids:
        raise HTTPException(400, "job_ids required")

    queued: list[int] = []
    rejected: list[dict[str, Any]] = []

    from secturafab.config import SecturaFabConfig

    try:
        SecturaFabConfig.from_env().require_credentials()
    except ValueError as exc:
        return {
            "queued": [],
            "queued_count": 0,
            "rejected": [
                {"job_id": job_id, "reason": str(exc)} for job_id in job_ids
            ],
        }

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
        if not job.pdf_path:
            raise HTTPException(400, "Job has no PDF")

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
    from .push_readiness import job_push_readiness
    from .services import _PUSH_IN_FLIGHT, push_job_secturafab

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        if job.status in {"uploaded", "processing"}:
            raise HTTPException(400, "Wait for takeoff to finish before pushing")

        _require_secturafab_credentials()

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

    return render_quote_html(data)


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


else:

    @app.get("/")
    def ui_not_built() -> HTMLResponse:
        return HTMLResponse(
            """<!doctype html>
<html><head><meta charset="utf-8"><title>Kannon Quote</title></head>
<body style="font-family:Segoe UI,sans-serif;margin:2rem;max-width:40rem">
<h1>Kannon Quote API is running</h1>
<p>The web UI is not built yet. From the repo:</p>
<pre>cd frontend
npm install
npm run build</pre>
<p>Then restart this server. API health: <a href="/api/health">/api/health</a></p>
<p>Printable quotes still work after login via
<code>/api/jobs/{id}/export.html?token=…</code></p>
</body></html>"""
        )
