from __future__ import annotations

from pathlib import Path

from quote_core.config import load_shop_rates
from quote_core.time_engine import compute_weld_times
from quote_core.weld.takeoff import WeldLineItem, run_weld_takeoff

from .db import Job, SessionLocal
from .library import attach_library_stp
from .paths import RATES_PATH


def process_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            return
        job.status = "processing"
        job.error_message = None
        db.commit()

        library_info = attach_library_stp(job)
        db.commit()

        rates = load_shop_rates(RATES_PATH)
        result = run_weld_takeoff(
            pdf_path=Path(job.pdf_path),
            stp_path=Path(job.stp_path) if job.stp_path else None,
        )
        items = result.items
        times = compute_weld_times(items, rates, efficiency_pct=job.efficiency_pct)

        takeoff = result.to_dict()
        takeoff["library"] = library_info
        flags = list(result.flags)
        for note in library_info.get("notes") or []:
            if note not in flags:
                flags.append(note)
        if library_info.get("related_pdf_count"):
            names = ", ".join((library_info.get("related_pdfs") or [])[:8])
            more = library_info["related_pdf_count"] - min(8, len(library_info.get("related_pdfs") or []))
            related_flag = f"Related drawings in shared folder: {names}"
            if more > 0:
                related_flag += f" (+{more} more)"
            if related_flag not in flags:
                flags.append(related_flag)

        job.set_takeoff(takeoff)
        job.set_times(times.to_dict())
        job.set_flags(flags)
        job.status = "review"
        db.commit()
    except Exception as exc:  # noqa: BLE001
        job = db.get(Job, job_id)
        if job:
            job.status = "error"
            job.error_message = str(exc)
            db.commit()
    finally:
        db.close()


def recompute_from_items(
    job: Job,
    items_data: list[dict],
    efficiency_pct: float | None = None,
    ipm_overrides: dict[str, float] | None = None,
) -> None:
    rates = load_shop_rates(RATES_PATH)
    items = [
        WeldLineItem(
            size=str(d.get("size") or "unknown"),
            inches=float(d.get("inches") or 0),
            joint_notes=str(d.get("joint_notes") or ""),
            confidence=str(d.get("confidence") or "medium"),
            source=str(d.get("source") or "manual"),
            page=d.get("page"),
            needs_review=bool(d.get("needs_review", False)),
        )
        for d in items_data
    ]
    if efficiency_pct is not None:
        job.efficiency_pct = float(efficiency_pct)
    times = compute_weld_times(
        items,
        rates,
        efficiency_pct=job.efficiency_pct,
        ipm_overrides=ipm_overrides,
    )
    takeoff = job.takeoff()
    takeoff["items"] = [i.to_dict() for i in items]
    takeoff["total_inches"] = sum(i.inches for i in items)
    job.set_takeoff(takeoff)
    job.set_times(times.to_dict())
