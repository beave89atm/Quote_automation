from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import MachineRoster, MachiningConfig
from .formulas import (
    clamp_rpm,
    interpolate_ipt,
    milling_ipm,
    milling_mrr,
    rpm_from_sfm,
    time_from_path,
    time_from_volume,
)
from .select import suggest_mill


@dataclass
class MillQuoteInput:
    material: str = "carbon_steel"
    qty: int = 1
    length_in: float = 0.0
    width_in: float = 0.0
    height_in: float = 0.0
    face_area_in2: float | None = None
    pocket_volume_in3: float | None = None
    contour_length_in: float | None = None
    hole_count: int = 0
    hole_diameter_in: float | None = None
    hole_depth_in: float | None = None
    needs_4th_axis: bool = False
    fourth_axis_diameter_in: float | None = None
    tool_diameter_in: float | None = None
    flutes: int | None = None
    doc_in: float | None = None
    woc_in: float | None = None
    setups: int = 1
    sfm: float | None = None
    ipt: float | None = None


def _setup_key(suggested_class: str) -> str:
    mapping = {
        "cnc_mill_horizontal": "cnc_mill_horizontal",
        "cnc_mill_4axis": "cnc_mill_4axis",
        "robodrill": "robodrill",
        "cnc_mill_3axis": "cnc_mill_3axis",
        "cnc_mill": "cnc_mill_3axis",
    }
    return mapping.get(suggested_class, "cnc_mill_3axis")


def quote_mill(
    inp: MillQuoteInput,
    *,
    roster: MachineRoster | None = None,
    config: MachiningConfig | None = None,
) -> dict[str, Any]:
    from .config import load_machine_roster, load_machining_config

    roster = roster or load_machine_roster()
    config = config or load_machining_config()

    if inp.qty < 1:
        raise ValueError("qty must be >= 1")
    if min(inp.length_in, inp.width_in, inp.height_in) <= 0:
        raise ValueError("length_in, width_in, and height_in must be > 0")

    mat = config.resolve_material(inp.material)
    mill_def = (config.defaults.get("mill") or {})
    tool_d = float(inp.tool_diameter_in or mill_def.get("tool_diameter_in") or 0.5)
    flutes = int(inp.flutes or mill_def.get("flutes") or 4)
    doc = float(
        inp.doc_in
        if inp.doc_in is not None
        else tool_d * float(mill_def.get("doc_fraction_of_d") or 0.25)
    )
    woc = float(
        inp.woc_in
        if inp.woc_in is not None
        else tool_d * float(mill_def.get("woc_fraction_of_d") or 0.50)
    )
    face_woc = tool_d * float(mill_def.get("face_woc_fraction_of_d") or 0.80)

    sfm = float(inp.sfm if inp.sfm is not None else mat.mill_sfm)
    ipt = float(
        inp.ipt
        if inp.ipt is not None
        else interpolate_ipt(tool_d, mat.ipt_by_diameter_in)
    )

    selection = suggest_mill(
        roster,
        length_in=inp.length_in,
        width_in=inp.width_in,
        height_in=inp.height_in,
        needs_4th_axis=inp.needs_4th_axis,
        fourth_axis_diameter_in=inp.fourth_axis_diameter_in,
    )
    suggested = selection.get("suggested_machine") or {}
    max_rpm = suggested.get("max_rpm")
    rpm, rpm_clamped = clamp_rpm(rpm_from_sfm(sfm, tool_d), max_rpm)
    ipm = milling_ipm(rpm, ipt, flutes)
    mrr = milling_mrr(doc, woc, ipm)

    ops: list[dict[str, Any]] = []
    cut_min = 0.0

    face_area = inp.face_area_in2
    if face_area and face_area > 0 and face_woc > 0:
        path = face_area / face_woc
        t = time_from_path(path, ipm)
        cut_min += t
        ops.append(
            {
                "op": "face",
                "path_in": round(path, 4),
                "ipm": round(ipm, 4),
                "cut_minutes": round(t, 4),
                "formula": "path = area / face_WOC; T = path / IPM",
            }
        )

    if inp.pocket_volume_in3 and inp.pocket_volume_in3 > 0:
        t = time_from_volume(inp.pocket_volume_in3, mrr)
        cut_min += t
        ops.append(
            {
                "op": "pocket",
                "volume_in3": inp.pocket_volume_in3,
                "mrr_in3_per_min": round(mrr, 4),
                "cut_minutes": round(t, 4),
                "formula": "T = volume / MRR; MRR = DOC × WOC × IPM",
            }
        )

    if inp.contour_length_in and inp.contour_length_in > 0:
        t = time_from_path(inp.contour_length_in, ipm)
        cut_min += t
        ops.append(
            {
                "op": "contour",
                "path_in": inp.contour_length_in,
                "ipm": round(ipm, 4),
                "cut_minutes": round(t, 4),
                "formula": "T = length / IPM",
            }
        )

    hole_flags: list[dict[str, Any]] = []
    if inp.hole_count > 0:
        hole_d = float(inp.hole_diameter_in or tool_d)
        hole_depth = float(inp.hole_depth_in or inp.height_in)
        if hole_d <= 0 or hole_depth <= 0:
            hole_flags.append(
                {
                    "code": "MILL_HOLE_INPUTS_INCOMPLETE",
                    "message": "Hole count given but diameter/depth not usable — holes not timed.",
                    "blocking": False,
                }
            )
        else:
            drill_rpm, _ = clamp_rpm(rpm_from_sfm(mat.drill_sfm, hole_d), max_rpm)
            drill_ipm = drill_rpm * mat.drill_ipr
            t = time_from_path(hole_depth * inp.hole_count, drill_ipm)
            cut_min += t
            ops.append(
                {
                    "op": "drill",
                    "holes": inp.hole_count,
                    "diameter_in": hole_d,
                    "depth_in": hole_depth,
                    "rpm": round(drill_rpm, 2),
                    "ipr": mat.drill_ipr,
                    "cut_minutes": round(t, 4),
                    "formula": "T = (depth × holes) / (RPM × IPR)",
                    "rates_placeholder": True,
                    "source": mat.drill_source,
                }
            )

    if not ops:
        hole_flags.append(
            {
                "code": "MILL_NO_FEATURES",
                "message": "No face area, pocket volume, contour length, or holes given — "
                "cutting time is 0. Enter features from the drawing.",
                "blocking": False,
            }
        )

    ncf = config.non_cutting_factor
    run_each = cut_min * ncf
    setup_key = _setup_key(selection["suggested_class"])
    setup_each = float(config.setup_minutes.get(setup_key) or config.setup_minutes.get("cnc_mill_3axis") or 0)
    setups = max(1, int(inp.setups))
    setup_total = setup_each * setups
    run_total = run_each * inp.qty
    total = setup_total + run_total

    flags = list(selection["shop_flags"]) + hole_flags
    if rpm_clamped:
        flags.append(
            {
                "code": "RPM_CLAMPED_TO_MACHINE",
                "message": f"Calculated RPM capped at machine max {max_rpm}.",
                "blocking": False,
            }
        )
    if config.placeholder:
        flags.append(
            {
                "code": "RATES_PLACEHOLDER",
                "message": "SFM/IPT are Harvey Tool catalog starting points; setup and "
                "non-cutting factor are placeholders — not Kannon shop times.",
                "blocking": False,
            }
        )

    outside = bool(selection["outside_envelope"])
    return {
        "process": "mill",
        "ok_to_quote": not outside,
        "outside_envelope": outside,
        "placeholder": True,
        "material": {
            "key": mat.key,
            "label": mat.label,
            "requested": inp.material,
            "sfm": sfm,
            "sfm_source": mat.mill_source,
        },
        "qty": inp.qty,
        "envelope": {
            "length_in": inp.length_in,
            "width_in": inp.width_in,
            "height_in": inp.height_in,
        },
        "tool": {
            "diameter_in": tool_d,
            "flutes": flutes,
            "doc_in": doc,
            "woc_in": woc,
            "ipt": ipt,
            "sfm": sfm,
            "rpm": round(rpm, 2),
            "ipm": round(ipm, 4),
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
                    "subclass": c["machine"]["subclass"],
                    "taper": c["machine"]["taper"],
                    "score": c["score"],
                    "fits": c["fits"],
                }
                for c in selection["candidates"]
                if c["machine"]["class"] == "cnc_mill"
            ],
        },
        "flags": flags,
        "formulas": config.formulas,
        "coating": {
            "status": (config.coating or {}).get("status", "stub"),
            "quoted": False,
        },
    }
