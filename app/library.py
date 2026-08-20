"""Attach shared-drive drawings onto quote jobs."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from quote_core.config import load_shop_rates
from quote_core.drawing_library import (
    DrawingMatch,
    extract_part_key,
    find_drawings,
    library_roots_from_config,
)

from .db import Job
from .paths import RATES_PATH, UPLOAD_DIR


def lookup_for_job(job: Job) -> DrawingMatch:
    rates = load_shop_rates(RATES_PATH)
    roots = library_roots_from_config(rates.raw)
    part_key = (
        extract_part_key(
            job.pdf_filename,
            getattr(job, "dxf_filename", None),
            job.stp_filename,
            job.title,
        )
        or ""
    )
    return find_drawings(
        part_key,
        roots,
        primary_pdf_name=job.pdf_filename or None,
    )


def attach_library_stp(job: Job, match: DrawingMatch | None = None) -> dict[str, Any]:
    """
    If the job has no STP and the library finds one, copy it into the job upload folder.
    Returns a serializable library summary (always).
    """
    rates = load_shop_rates(RATES_PATH)
    lib_cfg = (rates.raw.get("drawing_library") or {})
    auto = bool(lib_cfg.get("auto_attach_stp", True))

    match = match or lookup_for_job(job)
    summary = match.to_dict()
    summary["auto_attach_enabled"] = auto
    summary["attached"] = False

    if job.stp_path and Path(job.stp_path).exists():
        summary["notes"] = list(summary.get("notes") or []) + [
            "Job already has an STP — shared-drive STP not copied"
        ]
        return summary

    if not auto:
        summary["notes"] = list(summary.get("notes") or []) + [
            "Auto-attach disabled in drawing_library.auto_attach_stp"
        ]
        return summary

    if not match.stp_path or not match.stp_path.exists():
        return summary

    job_dir = UPLOAD_DIR / str(job.id)
    job_dir.mkdir(parents=True, exist_ok=True)
    dest = job_dir / match.stp_path.name
    shutil.copy2(match.stp_path, dest)
    job.stp_filename = match.stp_path.name
    job.stp_path = str(dest)
    summary["attached"] = True
    summary["attached_path"] = str(dest)
    summary["notes"] = list(summary.get("notes") or []) + [
        f"Auto-attached STP from shared drive: {match.stp_path.name}"
    ]
    return summary
