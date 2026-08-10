"""Shared SecturaFAB push readiness — refuse only when ItemList cannot be built."""

from __future__ import annotations

from pathlib import Path
from typing import Any


NOT_READY_REASON = "needs PDF, STEP, or library match"


def evaluate_push_readiness(
    *,
    stp_path: str | Path | None = None,
    pdf_path: str | Path | None = None,
    takeoff: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Ready when we can populate SecturaFAB ItemList:

    - STEP on disk, or
    - Engineering library folder (lesson 04 BOM PDFs), or
    - Job PDF on disk (single-PDF shell / quickAddCAD path)
    """
    takeoff = takeoff or {}
    library = takeoff.get("library") or {}
    folder = library.get("folder")

    has_stp = False
    if stp_path:
        has_stp = Path(stp_path).is_file()

    has_pdf = False
    if pdf_path:
        has_pdf = Path(pdf_path).is_file()

    has_library = bool(folder and str(folder).strip())
    ready = has_stp or has_library or has_pdf
    return {
        "ready": ready,
        "reason": None if ready else NOT_READY_REASON,
        "has_stp": has_stp,
        "has_library": has_library,
        "has_pdf": has_pdf,
    }


def job_push_readiness(job: Any) -> dict[str, Any]:
    """Evaluate readiness from an app.db.Job (or duck-typed object)."""
    return evaluate_push_readiness(
        stp_path=getattr(job, "stp_path", None),
        pdf_path=getattr(job, "pdf_path", None),
        takeoff=job.takeoff() if hasattr(job, "takeoff") else {},
    )
