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

from quote_core.config import load_shop_rates

from .auth import login, require_auth
from .db import Job, SessionLocal, init_db
from .paths import FRONTEND_DIST, RATES_PATH, UPLOAD_DIR, ensure_data_dirs
from .services import process_job, recompute_from_items

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


@app.post("/api/jobs")
async def create_job(
    pdf: UploadFile = File(...),
    stp: UploadFile | None = File(None),
    title: str = Form(""),
    _: str = Depends(require_auth),
) -> dict[str, Any]:
    if not pdf.filename or not pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "PDF file is required")

    ensure_data_dirs()
    db = SessionLocal()
    try:
        rates = load_shop_rates(RATES_PATH)
        job = Job(
            title=title.strip() or Path(pdf.filename).stem,
            status="uploaded",
            pdf_filename=pdf.filename,
            stp_filename=stp.filename if stp and stp.filename else None,
            efficiency_pct=rates.default_efficiency_pct,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        job_dir = UPLOAD_DIR / str(job.id)
        job_dir.mkdir(parents=True, exist_ok=True)
        pdf_dest = job_dir / pdf.filename
        with pdf_dest.open("wb") as f:
            shutil.copyfileobj(pdf.file, f)
        job.pdf_path = str(pdf_dest)

        if stp and stp.filename:
            suffix = Path(stp.filename).suffix.lower()
            if suffix not in {".stp", ".step"}:
                raise HTTPException(400, "STP/STEP file required for optional 3D upload")
            stp_dest = job_dir / stp.filename
            with stp_dest.open("wb") as f:
                shutil.copyfileobj(stp.file, f)
            job.stp_path = str(stp_dest)

        db.commit()
        db.refresh(job)
        job_id = job.id
        payload = job.to_dict()
    finally:
        db.close()

    threading.Thread(target=process_job, args=(job_id,), daemon=True).start()
    return payload


@app.patch("/api/jobs/{job_id}")
def update_job(
    job_id: int, body: ReviewUpdate, _: str = Depends(require_auth)
) -> dict[str, Any]:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
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
