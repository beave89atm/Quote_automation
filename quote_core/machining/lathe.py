from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import MachineRoster, MachiningConfig
from .formulas import (
    clamp_rpm,
    passes_for_stock,
    rpm_from_sfm,
    turning_mrr,
    turning_time_min,
)
from .select import suggest_lathe


@dataclass
class LatheQuoteInput:
    material: str = "carbon_steel"
    qty: int = 1
    diameter_in: float = 0.0
    length_in: float = 0.0
    stock_diameter_in: float | None = None
    turn_length_in: float | None = None
    radial_stock_in: float | None = None
    bore_length_in: float | None = None
    bore_diameter_in: float | None = None
    face: bool = True
    needs_live_tooling: bool = False
    setups: int = 1
    doc_in: float | None = None
    ipr: float | None = None
    sfm: float | None = None
    finish: bool = True


def quote_lathe(
    inp: LatheQuoteInput,
    *,
    roster: MachineRoster | None = None,
    config: MachiningConfig | None = None,
) -> dict[str, Any]:
    from .config import load_machine_roster, load_machining_config

    roster = roster or load_machine_roster()
    config = config or load_machining_config()

    if inp.qty < 1:
        raise ValueError("qty must be >= 1")
    if inp.diameter_in <= 0 or inp.length_in <= 0:
        raise ValueError("diameter_in and length_in must be > 0")

    mat = config.resolve_material(inp.material)
    lathe_def = config.defaults.get("lathe") or {}
    rough_doc = float(inp.doc_in if inp.doc_in is not None else lathe_def.get("rough_doc_in") or 0.100)
    finish_doc = float(lathe_def.get("finish_doc_in") or 0.020)
    finish_passes = int(lathe_def.get("finish_passes") or 1) if inp.finish else 0

    stock_d = float(inp.stock_diameter_in if inp.stock_diameter_in is not None else inp.diameter_in)
    if stock_d < inp.diameter_in:
        raise ValueError("stock_diameter_in cannot be smaller than finish diameter_in")
    radial = inp.radial_stock_in
    if radial is None:
        radial = max(0.0, (stock_d - inp.diameter_in) / 2.0)
    turn_len = float(inp.turn_length_in if inp.turn_length_in is not None else inp.length_in)

    sfm = float(inp.sfm if inp.sfm is not None else mat.lathe_sfm)
    rough_ipr = float(inp.ipr if inp.ipr is not None else mat.rough_ipr)
    finish_ipr = mat.finish_ipr

    selection = suggest_lathe(
        roster,
        diameter_in=max(stock_d, inp.diameter_in),
        length_in=inp.length_in,
        needs_live_tooling=inp.needs_live_tooling,
    )
    suggested = selection.get("suggested_machine") or {}
    max_rpm = suggested.get("max_rpm")

    work_d = max(stock_d, inp.diameter_in)
    rpm, rpm_clamped = clamp_rpm(rpm_from_sfm(sfm, work_d), max_rpm)
    mrr = turning_mrr(sfm, rough_ipr, rough_doc) if rough_doc > 0 else 0.0

    ops: list[dict[str, Any]] = []
    cut_min = 0.0

    if inp.face:
        face_travel = work_d / 2.0
        t = turning_time_min(face_travel, rpm, rough_ipr)
        cut_min += t
        ops.append(
            {
                "op": "face",
                "travel_in": round(face_travel, 4),
                "rpm": round(rpm, 2),
                "ipr": rough_ipr,
                "cut_minutes": round(t, 4),
                "formula": "T = (D/2) / (n × IPR)",
            }
        )

    rough_passes = passes_for_stock(radial, rough_doc) if radial > 0 else 0
    if rough_passes:
        t_pass = turning_time_min(turn_len, rpm, rough_ipr)
        t = t_pass * rough_passes
        cut_min += t
        ops.append(
            {
                "op": "rough_turn",
                "length_in": turn_len,
                "radial_stock_in": radial,
                "doc_in": rough_doc,
                "passes": rough_passes,
                "rpm": round(rpm, 2),
                "ipr": rough_ipr,
                "mrr_in3_per_min": round(mrr, 4),
                "cut_minutes": round(t, 4),
                "formula": "T = passes × L / (n × IPR)",
            }
        )

    if finish_passes and turn_len > 0:
        finish_rpm, _ = clamp_rpm(rpm_from_sfm(sfm, inp.diameter_in), max_rpm)
        t_pass = turning_time_min(turn_len, finish_rpm, finish_ipr)
        t = t_pass * finish_passes
        cut_min += t
        ops.append(
            {
                "op": "finish_turn",
                "length_in": turn_len,
                "doc_in": finish_doc,
                "passes": finish_passes,
                "rpm": round(finish_rpm, 2),
                "ipr": finish_ipr,
                "cut_minutes": round(t, 4),
                "formula": "T = passes × L / (n × IPR)",
            }
        )

    if inp.bore_length_in and inp.bore_length_in > 0:
        bore_d = float(inp.bore_diameter_in or (inp.diameter_in * 0.5))
        if bore_d <= 0:
            raise ValueError("bore_diameter_in must be > 0")
        bore_rpm, _ = clamp_rpm(rpm_from_sfm(sfm, bore_d), max_rpm)
        t = turning_time_min(inp.bore_length_in, bore_rpm, rough_ipr)
        cut_min += t
        ops.append(
            {
                "op": "bore",
                "length_in": inp.bore_length_in,
                "diameter_in": bore_d,
                "rpm": round(bore_rpm, 2),
                "ipr": rough_ipr,
                "cut_minutes": round(t, 4),
                "formula": "T = L / (n × IPR) at bore diameter",
            }
        )

    extra_flags: list[dict[str, Any]] = []
    if not ops:
        extra_flags.append(
            {
                "code": "LATHE_NO_FEATURES",
                "message": "No face, turn stock, or bore given — cutting time is 0.",
                "blocking": False,
            }
        )
    if inp.needs_live_tooling:
        extra_flags.append(
            {
                "code": "LATHE_LIVE_TOOLING_NOT_TIMED",
                "message": "Live-tool mill features are not timed in v0 — only the live-tool "
                "Doosan is selected. Add mill-feature inputs on the mill calculator.",
                "blocking": False,
            }
        )

    ncf = config.non_cutting_factor
    run_each = cut_min * ncf
    setup_key = "cnc_lathe_live_tooling" if inp.needs_live_tooling else "cnc_lathe"
    setup_each = float(config.setup_minutes.get(setup_key) or 0)
    setups = max(1, int(inp.setups))
    setup_total = setup_each * setups
    run_total = run_each * inp.qty
    total = setup_total + run_total

    flags = list(selection["shop_flags"]) + extra_flags
    if rpm_clamped:
        flags.append(
            {
                "code": "RPM_CLAMPED_TO_MACHINE",
                "message": f"Calculated RPM capped at machine max {max_rpm}.",
                "blocking": False,
            }
        )
    if mat.lathe_source == "placeholder_catalog" or config.placeholder:
        flags.append(
            {
                "code": "RATES_PLACEHOLDER",
                "message": "Turning SFM/IPR and setup minutes are placeholder catalog values "
                "until Kyle supplies insert grades and shop setup times. Not Kannon shop times.",
                "blocking": False,
            }
        )

    outside = bool(selection["outside_envelope"])
    return {
        "process": "lathe",
        "ok_to_quote": not outside,
        "outside_envelope": outside,
        "placeholder": True,
        "material": {
            "key": mat.key,
            "label": mat.label,
            "requested": inp.material,
            "sfm": sfm,
            "sfm_source": mat.lathe_source,
        },
        "qty": inp.qty,
        "envelope": {
            "diameter_in": inp.diameter_in,
            "length_in": inp.length_in,
            "stock_diameter_in": stock_d,
        },
        "tool": {
            "sfm": sfm,
            "rough_ipr": rough_ipr,
            "finish_ipr": finish_ipr,
            "rough_doc_in": rough_doc,
            "rpm": round(rpm, 2),
            "mrr_in3_per_min": round(mrr, 4),
        },
        "ops": ops,
        "times": {
            "cut_minutes_each": round(cut_min, 3),
            "non_cutting_factor": ncf,
            "non_cutting_placeholder": config.non_cutting_placeholder,
            "run_minutes_each": round(run_each, 3),
            "setup_minutes": round(setup_total, 3),
            "setup_minutes_each_setup": setup_each,
            "setup_count": setups,
            "setup_key": setup_key,
            "setup_placeholder": True,
            "run_minutes_total": round(run_total, 3),
            "total_minutes": round(total, 3),
            "total_hours": round(total / 60.0, 3),
        },
        "machine": {
            "suggested_class": selection["suggested_class"],
            "suggested": selection["suggested_machine"],
            "candidates": [
                {
                    "id": c["machine"]["id"],
                    "display_name": c["machine"]["display_name"],
                    "class": c["machine"]["class"],
                    "live_tooling": c["machine"]["live_tooling"],
                    "score": c["score"],
                    "fits": c["fits"],
                }
                for c in selection["candidates"]
                if c["machine"]["class"] == "cnc_lathe"
            ],
        },
        "flags": flags,
        "formulas": config.formulas,
        "coating": {
            "status": (config.coating or {}).get("status", "stub"),
            "quoted": False,
        },
    }
