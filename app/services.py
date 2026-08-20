from __future__ import annotations

from pathlib import Path
from typing import Any

from quote_core.config import load_shop_rates
from quote_core.dxf_text import extract_dxf_text
from quote_core.operations import propose_operations
from quote_core.time_engine import compute_weld_times
from quote_core.weld.takeoff import WeldLineItem, run_weld_takeoff

from .db import Job, SessionLocal
from .library import attach_library_stp
from .paths import RATES_PATH


def _drivers_from_takeoff(takeoff: dict[str, Any]) -> dict[str, Any]:
    drivers = takeoff.get("fitup_drivers") or {}
    weight_calc = drivers.get("weight_calc") or {}
    components = drivers.get("component_weights_lb")
    if components is None:
        components = weight_calc.get("component_weights_lb")
    return {
        "part_count": int(drivers["part_count"]) if drivers.get("part_count") is not None else None,
        "joint_count": int(drivers["joint_count"]) if drivers.get("joint_count") is not None else None,
        "assembly_weight_lb": (
            float(drivers["assembly_weight_lb"])
            if drivers.get("assembly_weight_lb") is not None
            else None
        ),
        "component_weights_lb": [float(w) for w in (components or [])],
    }


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

        from quote_core.bom_config import format_bom_config_label, resolve_bom_config
        from quote_core.drawing_library import extract_part_key

        intake_mode = (getattr(job, "intake_mode", None) or "weldment").strip().lower()
        if intake_mode not in {"weldment", "loose_piece"}:
            intake_mode = "weldment"
        # Loose-piece: still attach this part's STP, but never treat sibling PDFs as BOM.
        related_pdf_names = (
            []
            if intake_mode == "loose_piece"
            else list(library_info.get("related_pdfs") or [])
        )

        bom_config = resolve_bom_config(
            explicit=job.bom_config,
            title=job.title,
            pdf_filename=job.pdf_filename,
            library_folder=library_info.get("folder"),
            part_key=library_info.get("part_key"),
        )
        if bom_config and bom_config != job.bom_config:
            job.bom_config = bom_config
            db.commit()

        rates = load_shop_rates(RATES_PATH)
        result = run_weld_takeoff(
            pdf_path=Path(job.pdf_path) if job.pdf_path else None,
            stp_path=Path(job.stp_path) if job.stp_path else None,
            library_folder=library_info.get("folder"),
            related_pdf_names=related_pdf_names,
            bom_config=bom_config,
        )
        items = result.items
        takeoff = result.to_dict()
        takeoff["library"] = library_info
        takeoff["bom_config"] = bom_config
        takeoff["intake_mode"] = intake_mode
        part_number = (
            result.part_number
            or extract_part_key(
                job.pdf_filename,
                job.dxf_filename,
                job.stp_filename,
                job.title,
            )
        )
        if part_number:
            takeoff["part_number"] = part_number
            takeoff["quote_number"] = part_number
            job.part_number = part_number
        if result.pdf_bom:
            takeoff["bom"] = result.pdf_bom
        if job.dxf_filename:
            takeoff["dxf_filename"] = job.dxf_filename
        drivers = _drivers_from_takeoff(takeoff)
        times = compute_weld_times(
            items,
            rates,
            efficiency_pct=job.efficiency_pct,
            part_count=drivers["part_count"],
            joint_count=drivers["joint_count"],
            assembly_weight_lb=drivers["assembly_weight_lb"],
            component_weights_lb=drivers.get("component_weights_lb"),
        )
        dxf_text = extract_dxf_text(job.dxf_path) if job.dxf_path else ""
        ops = propose_operations(
            title=job.title or "",
            filenames=[job.pdf_filename, job.dxf_filename or "", job.stp_filename or ""],
            pdf_notes=list(takeoff.get("notes") or []),
            dxf_text=dxf_text,
            has_pdf=bool(job.pdf_path and Path(job.pdf_path).is_file()),
            has_dxf=bool(job.dxf_path and Path(job.dxf_path).is_file()),
            has_stp=bool(job.stp_path and Path(job.stp_path).is_file()),
            weld_items=[i.to_dict() for i in items],
            times=times.to_dict(),
            stp_summary=takeoff.get("stp_summary") or {},
        )
        takeoff["operations"] = ops.to_dict()

        flags = list(result.flags)
        for flag in ops.flags:
            if flag not in flags:
                flags.append(flag)
        if bom_config:
            flags.insert(
                0,
                f"BOM config {format_bom_config_label(bom_config)} — "
                f"using that qty column on multi-option drawings",
            )
        for note in library_info.get("notes") or []:
            if note not in flags:
                flags.append(note)
        for note in times.fitup_notes:
            if note not in flags:
                flags.append(note)
        if intake_mode == "weldment" and library_info.get("related_pdf_count"):
            names = ", ".join((library_info.get("related_pdfs") or [])[:8])
            more = library_info["related_pdf_count"] - min(8, len(library_info.get("related_pdfs") or []))
            related_flag = f"Related drawings in shared folder: {names}"
            if more > 0:
                related_flag += f" (+{more} more)"
            if related_flag not in flags:
                flags.append(related_flag)
        elif intake_mode == "loose_piece":
            loose_flag = (
                "Loose-piece mode: this job is one part number / one SecturaFAB quote. "
                "Sibling drawings in the library folder are not this BOM."
            )
            if loose_flag not in flags:
                flags.append(loose_flag)

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
    fitup_drivers: dict[str, Any] | None = None,
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

    takeoff = job.takeoff()
    takeoff["items"] = [i.to_dict() for i in items]
    takeoff["total_inches"] = sum(i.inches for i in items)

    drivers = dict(takeoff.get("fitup_drivers") or {})
    if fitup_drivers:
        if fitup_drivers.get("part_count") is not None:
            drivers["part_count"] = int(fitup_drivers["part_count"])
        if fitup_drivers.get("joint_count") is not None:
            drivers["joint_count"] = int(fitup_drivers["joint_count"])
        if "assembly_weight_lb" in fitup_drivers:
            w = fitup_drivers.get("assembly_weight_lb")
            drivers["assembly_weight_lb"] = None if w in ("", None) else float(w)
        if fitup_drivers.get("component_weights_lb") is not None:
            drivers["component_weights_lb"] = [
                float(x) for x in fitup_drivers.get("component_weights_lb") or []
            ]
        drivers["source"] = "manual"
    takeoff["fitup_drivers"] = drivers

    times = compute_weld_times(
        items,
        rates,
        efficiency_pct=job.efficiency_pct,
        ipm_overrides=ipm_overrides,
        part_count=drivers.get("part_count"),
        joint_count=drivers.get("joint_count"),
        assembly_weight_lb=drivers.get("assembly_weight_lb"),
        component_weights_lb=drivers.get("component_weights_lb")
        or (drivers.get("weight_calc") or {}).get("component_weights_lb"),
    )
    dxf_text = extract_dxf_text(job.dxf_path) if getattr(job, "dxf_path", None) else ""
    ops = propose_operations(
        title=job.title or "",
        filenames=[
            job.pdf_filename,
            getattr(job, "dxf_filename", None) or "",
            job.stp_filename or "",
        ],
        pdf_notes=list(takeoff.get("notes") or []),
        dxf_text=dxf_text,
        has_pdf=bool(job.pdf_path and Path(job.pdf_path).is_file()),
        has_dxf=bool(getattr(job, "dxf_path", None) and Path(job.dxf_path).is_file()),
        has_stp=bool(job.stp_path and Path(job.stp_path).is_file()),
        weld_items=[i.to_dict() for i in items],
        times=times.to_dict(),
        stp_summary=takeoff.get("stp_summary") or {},
    )
    takeoff["operations"] = ops.to_dict()
    job.set_takeoff(takeoff)
    job.set_times(times.to_dict())
    flags = job.flags()
    for flag in ops.flags:
        if flag not in flags:
            flags.append(flag)
    job.set_flags(flags)


_PUSH_IN_FLIGHT = {"pushing", "retrying_createfile"}


def _merge_secturafab_progress(job_id: int, info: dict[str, Any]) -> None:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            return
        takeoff = job.takeoff()
        sf = dict(takeoff.get("secturafab") or {})
        notes = list(sf.get("notes") or [])
        incoming_notes = info.get("notes")
        if isinstance(incoming_notes, list):
            for n in incoming_notes:
                if n and n not in notes:
                    notes.append(n)
            sf["notes"] = notes
        for key, val in info.items():
            if key == "notes":
                continue
            sf[key] = val
        takeoff["secturafab"] = sf
        job.set_takeoff(takeoff)
        db.commit()
    finally:
        db.close()


def push_job_secturafab(job_id: int) -> None:
    """Background SecturaFAB push (CreateFile may retry for hours)."""
    from secturafab.push import SecturaFabPushService, PushResult

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            return
        takeoff = job.takeoff()
        times = job.times()
        title = job.title or job.pdf_filename or job.dxf_filename or job.stp_filename or ""
        pdf_filename = job.pdf_filename
        pdf_path = Path(job.pdf_path) if job.pdf_path else None
        dxf_path = Path(job.dxf_path) if job.dxf_path else None
        stp_path = Path(job.stp_path) if job.stp_path else None
    finally:
        db.close()

    def on_progress(info: dict[str, Any]) -> None:
        _merge_secturafab_progress(job_id, info)

    try:
        service = SecturaFabPushService()
        result = service.push_job(
            title=title,
            pdf_filename=pdf_filename,
            pdf_path=pdf_path,
            dxf_path=dxf_path,
            stp_path=stp_path,
            takeoff=takeoff,
            times=times,
            job_id=job_id,
            on_progress=on_progress,
        )
    except Exception as exc:  # noqa: BLE001 — must never leave status stuck on pushing
        err = f"{type(exc).__name__}: {exc}"
        result = PushResult(
            ok=False,
            error=err,
            status="failed",
            last_error=err,
            notes=[f"Background push crashed: {err}"],
        )
        on_progress(
            {
                "ok": False,
                "status": "failed",
                "error": err,
                "last_error": err,
                "notes": [f"Background push crashed: {err}"],
            }
        )

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            return
        takeoff = job.takeoff()
        takeoff["secturafab"] = result.to_dict()
        job.set_takeoff(takeoff)
        flags = job.flags()
        if result.ok:
            flag = (
                f"Pushed to SecturaFAB quote {result.quote_number}"
                + (f" ({result.item_count} items)" if result.item_count is not None else "")
            )
            if flag not in flags:
                flags.append(flag)
            for note in result.notes or []:
                if note.startswith("WARNING:") and note not in flags:
                    flags.append(note)
            job.set_flags(flags)
        else:
            err = result.error or result.last_error or "SecturaFAB push failed"
            fail_flag = f"SecturaFAB push failed: {err}"
            if fail_flag not in flags:
                flags.append(fail_flag)
            if result.item_count == 0 and result.quote_number:
                warn = (
                    f"WARNING: Empty SecturaFAB quote {result.quote_number} "
                    "(0 items) — do not use; attach STEP/library and re-push"
                )
                if warn not in flags:
                    flags.append(warn)
            job.set_flags(flags)
        db.commit()
    finally:
        db.close()


def push_jobs_secturafab_batch(job_ids: list[int]) -> None:
    """Push jobs one after another to avoid SecturaFAB API overload."""
    for job_id in job_ids:
        try:
            push_job_secturafab(int(job_id))
        except Exception:  # noqa: BLE001 — never abort the whole batch
            continue
