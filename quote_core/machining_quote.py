"""Machining quote from typed features or from callouts read off a drawing.

Counts shop operations from the feature rules in
``references/machining/OPS_WORKFLOW.md``. Run time and setup stay blank
unless a typed cycle time overrides run time, or stated stock justifies an
operation and Kyle's calculator has the sizes that formula needs. Shop
dollar rates stay blank.

Item-operation codes come only from quote 121671-1
(id 94273b6c-072d-4a44-9519-d0e8f5f0f391, OPEN-NEW):

- ``op_lathe`` / equipment Lathe / Lathe-Setup (CostCalcType 6, fixedtime)
  and Lathe-Time (CostCalcType 9, perunittime, FieldName Per Unit Turning Time)
- ``op_lathe2`` / equipment Lathe 2 / the same two calculators
- ``op_mill`` / equipment CNC Mill / name Milling / Milling-Setup
  (CostCalcType 6, fixedtime) and Milling-Time (CostCalcType 9, perunittime,
  FieldName Per Unit Milling Time)

OperationType is 10. UnitTime on those rows is hours. Setup is the fixed
time, not the stored unit time after dividing by quantity. The dollar rate
on those cost rows is not used. Setup and run stay on separate calculators.
A quote-header row named Milling with equipment Laser and code ``op_mill``
is not an item operation. No other operation code is used. Nothing here
posts an operation or calls Sectura.

When a drawing does not name a machine, ``process_from_stock`` may name
the lathe or mill family from the stock-versus-finished comparison. Turning
needs a finished round smaller than round stock the sheet states. Milling
needs a stated plate with holes, or a stated forging whose finished solid
is a prismatic block. A missing stock form leaves the operation code blank.
A guessed bar size does not qualify. That family maps to ``op_lathe`` or
``op_mill`` only when the comparison justifies it. Lathe 2 (``op_lathe2``)
is used only when the sheet says lathe 2. When that comparison justifies
``op_mill`` from stated plate, or ``op_lathe`` / ``op_lathe2`` from stated
bar or tube whose finished round is smaller, run time and setup may be
filled from ``quote_core.machining_calculator`` (Kyle's stock-versus-finished
workbook). A stated forging can justify mill and does not use that volume
path. A missing size, a tube volume, a forging, or zero cubic inches removed
leaves run time blank. Shop dollar rates stay blank. A typed cycle
time may still override run time only.
"""

from __future__ import annotations

from typing import Any

from quote_core.part_materials import _parse_thickness_token

# Plate thicker than 3/4 in stays a purchased component.
PLATE_PURCHASED_OVER_IN = 0.75

NO_REMOVAL_RATE_NOTE = "No removal rate on file — run time left blank"
NO_SETUP_NOTE = (
    "No shop setup minutes on file — setup time left blank. "
    "Setup is the fixed time, not the unit time after dividing by quantity."
)
CODE_SOURCE_QUOTE = "121671-1"
CODE_SOURCE_ID = "94273b6c-072d-4a44-9519-d0e8f5f0f391"
CODE_SOURCE_STATUS = "OPEN-NEW"
VOLUME_NOTE = (
    "Stock-minus-finished volume is not used. "
    "Per-feature time needs a removal rate or a typed cycle time."
)
DRAWING_NOTE = (
    "Feature list was typed. Drawing callouts were not used for these features."
)
DRAWING_READ_NOTE = (
    "Features were read from callouts in the supplied file. "
    "A requirement that was not in the file was left blank."
)
SHARED_DRIVE_NOTE = (
    "Customer drawings BB1013, BB2000-ASM, the Alcon Supporting Pin, "
    "Time handle shaft 1002309-1, and spacer ring 80015114 have been read. "
    "The rest of the shared drive has not."
)
SEPARATE_CALC_NOTE = "Setup and run are separate calculators, not one time."
NOT_POSTED_NOTE = "Not posted to Sectura."
CYCLE_OVERRIDE_NOTE = "Typed cycle time overrides the estimated run time."
CYCLE_NOT_SPLIT_NOTE = (
    "Typed cycle time was not split across operations — each run time left blank."
)
CALCULATOR_RUN_NOTE = (
    "Run time is the calculator cycle for the whole part "
    "(cut minutes, allowances, and the 1.15 pad)."
)
LATHE_WHICH_NOTE = (
    "Lathe and Lathe 2 are both real — which one is not specified, "
    "so no operation code or setup calculator was chosen."
)

_ITEM_OPS: dict[str, dict[str, str | None]] = {
    "op_mill": {
        "equipment": "CNC Mill",
        "operation_name": "Milling",
        "setup_calculator": "Milling-Setup",
        "run_calculator": "Milling-Time",
        "run_field": "Per Unit Milling Time",
    },
    "op_lathe": {
        "equipment": "Lathe",
        "operation_name": None,
        "setup_calculator": "Lathe-Setup",
        "run_calculator": "Lathe-Time",
        "run_field": "Per Unit Turning Time",
    },
    "op_lathe2": {
        "equipment": "Lathe 2",
        "operation_name": None,
        "setup_calculator": "Lathe-Setup",
        "run_calculator": "Lathe-Time",
        "run_field": "Per Unit Turning Time",
    },
}

_FAMILY_CODE = {
    "mill": "op_mill",
    "lathe": "op_lathe",
    "lathe2": "op_lathe2",
}


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or _blank(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_setup_row(row: dict[str, Any]) -> bool:
    kind = _text(row.get("kind") or row.get("calc")).casefold()
    name = _text(row.get("CalculatorName") or row.get("calculator"))
    calc_type = row.get("CostCalcType")
    if calc_type == 9 or kind == "perunittime":
        return False
    return calc_type == 6 or kind == "fixedtime" or name.endswith("-Setup")


def _is_run_row(row: dict[str, Any]) -> bool:
    kind = _text(row.get("kind") or row.get("calc")).casefold()
    name = _text(row.get("CalculatorName") or row.get("calculator"))
    calc_type = row.get("CostCalcType")
    if calc_type == 6 or kind == "fixedtime" or name.endswith("-Setup"):
        return False
    return calc_type == 9 or kind == "perunittime" or name.endswith("-Time")


def read_setup_fixedtime_hours(row: dict[str, Any] | None) -> float | None:
    """Setup hours are ``fixedtime``. Stored UnitTime (fixedtime / qty) is not setup.

    Dollar amounts on the row are ignored. A missing fixed time stays blank
    rather than substituting the quantity-divided unit time.
    """
    if not isinstance(row, dict) or not _is_setup_row(row):
        return None
    if "fixedtime" not in row or row.get("fixedtime") is None:
        return None
    return _num(row.get("fixedtime"))


def read_run_perunittime_minutes(row: dict[str, Any] | None) -> float | None:
    """Run time is per-unit minutes. Setup fixed time is not added in."""
    if not isinstance(row, dict) or not _is_run_row(row):
        return None
    for key in ("perunittime", "perunittime_min"):
        if key in row and row.get(key) is not None:
            return _num(row.get(key))
    return None


def read_line_operation(setup_row: dict[str, Any], run_row: dict[str, Any] | None = None) -> dict[str, Any]:
    """Read one line operation from quote 121671-1's calculator shape.

    Setup is fixedtime hours. Stored unit time and any dollar rate are ignored.
    A header row named Milling on Laser is not an item operation.
    """
    run_row = run_row or {}
    blank = {
        "operation_code": None,
        "equipment": None,
        "operation_name": None,
        "operation_type": None,
        "setup_fixedtime_hours": None,
        "setup_time_min": None,
        "stored_unit_time_ignored": True,
        "run_perunittime_min": None,
        "shop_rate_per_hour": None,
        "posted": False,
    }
    if is_quote_header_milling_laser(setup_row) or is_quote_header_milling_laser(run_row):
        return blank
    source = setup_row if is_machining_item_operation(setup_row) else None
    if source is None and is_machining_item_operation(run_row):
        source = run_row
    if source is None:
        return blank
    spec = _ITEM_OPS[_row_code(source).casefold()]
    setup_hours = read_setup_fixedtime_hours(setup_row)
    return {
        "operation_code": _row_code(source).casefold(),
        "equipment": spec["equipment"],
        "operation_name": spec["operation_name"],
        "operation_type": 10,
        "setup_fixedtime_hours": setup_hours,
        "setup_time_min": None if setup_hours is None else setup_hours * 60.0,
        "stored_unit_time_ignored": True,
        "run_perunittime_min": read_run_perunittime_minutes(run_row),
        "shop_rate_per_hour": None,
        "posted": False,
    }

_KIND_ALIASES = {
    "facing": "face",
    "face_mill": "face",
    "facemill": "face",
    "od": "turn",
    "od_turn": "turn",
    "undercut": "groove",
    "under_cut": "groove",
    "keyway": "slot",
    "keyseat": "slot",
    "tapped_hole": "thread",
    "tapped": "thread",
    "partoff": "part_off",
    "part-off": "part_off",
    "parting": "part_off",
    "counter_bore": "counterbore",
    "cb": "counterbore",
    "csk": "countersink",
    "profile": "contour",
    "sheet": "plate",
}

_MILL_KINDS = {"hole", "slot", "pocket", "counterbore", "countersink", "contour"}
_LATHE_KINDS = {"groove", "bore", "part_off", "knurl", "taper", "turn"}
_VOLUME_KEYS = {
    "stock_volume_in3",
    "finished_volume_in3",
    "removal_volume_in3",
    "volume_in3",
    "stock_volume",
    "finished_volume",
}
_MACHINING_FLAG_PREFIX = "needs_info: machining required but missing "


def _blank(value: Any) -> bool:
    return value is None or value == "" or (isinstance(value, str) and not value.strip())


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _inches(value: Any) -> float | None:
    if isinstance(value, bool) or _blank(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    try:
        return float(text)
    except ValueError:
        return _parse_thickness_token(text)


def _cycle(value: Any) -> float | None:
    number = _inches(value) if not isinstance(value, str) else None
    if isinstance(value, str):
        try:
            number = float(value.strip())
        except ValueError:
            number = None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
    if number is None or number < 0:
        return None
    return number


def _dim(feature: dict[str, Any], *names: str) -> Any:
    dims = feature.get("dimensions")
    if not isinstance(dims, dict):
        dims = {}
    for name in names:
        if name in dims and not _blank(dims.get(name)):
            return dims.get(name)
        if name in feature and not _blank(feature.get(name)):
            return feature.get(name)
    return None


def _tool_key(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _row_code(row: dict[str, Any]) -> str:
    for key in ("operation_code", "Operation_code", "OperationCode", "code"):
        if key in row and not _blank(row.get(key)):
            return _text(row.get(key))
    return ""


def _row_equipment(row: dict[str, Any]) -> str:
    for key in ("equipment", "Equipment"):
        if key in row and not _blank(row.get(key)):
            return _text(row.get(key))
    return ""


def _row_name(row: dict[str, Any]) -> str:
    for key in ("name", "OperationName", "Operation", "OperationLabel"):
        if key in row and not _blank(row.get(key)):
            return _text(row.get(key))
    return ""


def is_quote_header_milling_laser(row: dict[str, Any] | None) -> bool:
    """Quote-header Milling on Laser using op_mill. Not an item operation."""
    if not isinstance(row, dict):
        return False
    return (
        _row_name(row).casefold() == "milling"
        and _row_equipment(row).casefold() == "laser"
        and _row_code(row).casefold() == "op_mill"
    )


def is_machining_item_operation(row: dict[str, Any] | None) -> bool:
    """True only for op_mill / op_lathe / op_lathe2 on their real equipment.

    A header row named Milling with equipment Laser and code op_mill is not
    machining, even when OperationType is 10.
    """
    if not isinstance(row, dict) or is_quote_header_milling_laser(row):
        return False
    spec = _ITEM_OPS.get(_row_code(row).casefold())
    if spec is None:
        return False
    return _row_equipment(row).casefold() == spec["equipment"].casefold()


def _family_from_feature(feature: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return (family, ignored_code).

    family is mill, lathe, lathe2, laser, or None. An unknown operation code
    is ignored and returned as the second value so the caller can say so.
    """
    raw_code = _text(feature.get("operation_code") or feature.get("Operation_code"))
    code = raw_code.casefold()
    equipment = _text(feature.get("equipment") or feature.get("Equipment"))
    machine = (
        _text(feature.get("machine"))
        .casefold()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
    )
    ignored = raw_code if code and code not in _ITEM_OPS else None
    if equipment.casefold() == "laser" or machine == "laser":
        return "laser", ignored
    if code == "op_lathe2" or equipment.casefold() == "lathe 2" or machine == "lathe2":
        return "lathe2", ignored
    if code == "op_lathe" or equipment.casefold() == "lathe" or machine in {"lathe", "lathe1"}:
        return "lathe", ignored
    if code == "op_mill" or equipment.casefold() == "cnc mill" or machine in {"mill", "cncmill"}:
        return "mill", ignored
    return None, ignored


def _default_family(kind: str, form: str) -> str | None:
    if kind in _MILL_KINDS or form in {"tap", "thread_mill"}:
        return "mill"
    if kind in _LATHE_KINDS or form == "single_point":
        return "lathe-unspecified"
    return None


def _normalize_form(raw: str) -> str:
    token = raw.casefold().replace(" ", "").replace("-", "_")
    if token in {"tap", "tapped", "die"}:
        return "tap"
    if token in {"thread_mill", "threadmill"}:
        return "thread_mill"
    if token in {"single_point", "singlepoint"}:
        return "single_point"
    return ""


def _normalize_passes(raw: str) -> str:
    token = raw.casefold().replace(" ", "").replace("-", "_")
    if token in {"rough"}:
        return "rough"
    if token in {"finish"}:
        return "finish"
    if token in {"both", "rough_and_finish", "rough+finish"}:
        return "both"
    return ""


def _pass_names(base: str, passes: str) -> list[str] | None:
    if passes == "rough":
        return [f"{base} rough"]
    if passes == "finish":
        return [f"{base} finish"]
    if passes == "both":
        return [f"{base} rough", f"{base} finish"]
    return None


def _plans_for_feature(
    feature: dict[str, Any],
    feature_id: str,
) -> tuple[list[dict[str, Any]], str | None, list[str]]:
    """Return (plans, unresolved_reason, extra_notes)."""
    notes: list[str] = []
    raw_kind = _text(feature.get("kind") or feature.get("feature") or feature.get("type")).casefold()
    raw_kind = raw_kind.replace(" ", "_").replace("-", "_")
    form = _normalize_form(_text(_dim(feature, "thread_form", "form")))
    if raw_kind == "tap" and not form:
        form = "tap"
    kind = _KIND_ALIASES.get(raw_kind, raw_kind)
    family, ignored = _family_from_feature(feature)
    if ignored:
        notes.append(
            f"Operation code {ignored!r} is not a known item operation and was not used."
        )
    if family == "laser":
        return [], None, notes + [
            "Equipment Laser is not an item machining operation."
        ]

    thickness = _inches(_dim(feature, "thickness_in", "thickness"))
    if kind == "plate":
        if thickness is None:
            notes.append("Plate thickness is missing — not counted as a machine operation.")
        elif thickness > PLATE_PURCHASED_OVER_IN:
            notes.append(
                "Plate over 3/4 in stays a purchased component, not a machine operation."
            )
        else:
            notes.append("Plate at or under 3/4 in is not a machine operation.")
        return [], None, notes

    if family is None and feature.get("stated_machine") is not False:
        family = _default_family(kind, form)
    if feature.get("stated_machine") is False and family is None:
        return [], (
            "The sheet does not say lathe, mill, drill, tap, or single-point. "
            "No operation code was added."
        ), notes

    diameter = _inches(_dim(feature, "diameter_in", "diameter"))
    width = _inches(_dim(feature, "width_in", "width"))
    tool = _tool_key(diameter if diameter is not None else width)
    tolerance = _text(_dim(feature, "tolerance")).casefold()
    passes = _normalize_passes(_text(_dim(feature, "passes", "pass")))
    cycle = _cycle(feature.get("cycle_time_min"))

    names: list[str] | None
    reason: str | None = None
    if kind == "hole":
        if tolerance in {"loose", "drill"}:
            names = ["drill"]
        elif tolerance in {"tight", "ream", "bore"}:
            names = ["drill", "bore"]
        else:
            names = None
            reason = (
                "Hole tolerance is missing — cannot tell drill-only from drill and bore."
            )
    elif kind == "face":
        if family in {"mill"}:
            names = ["face mill"]
        elif family in {"lathe", "lathe2", "lathe-unspecified"}:
            names = ["facing"]
        else:
            names = None
            reason = "Face is mill or lathe — machine not supplied, operation count left blank."
    elif kind == "thread":
        if form == "tap":
            names = ["drill", "tap"]
        elif form == "thread_mill":
            names = ["drill", "thread mill"]
        elif form == "single_point":
            if family == "mill":
                names = None
                reason = "Single-point thread is a lathe operation — machine was mill."
            else:
                names = ["thread"]
                if family is None:
                    family = "lathe-unspecified"
        else:
            names = None
            reason = (
                "Thread form is missing — cannot tell tap from single-point, "
                "operation count left blank."
            )
    elif kind == "groove":
        names = ["grooving"]
        if family is None:
            family = "lathe-unspecified"
    elif kind == "slot":
        names = ["slot"]
    elif kind in {"counterbore", "countersink", "contour", "part_off", "knurl", "taper", "bore"}:
        names = [kind.replace("_", "-")]
    elif kind in {"pocket", "turn"}:
        base = "pocket" if kind == "pocket" else "turn"
        names = _pass_names(base, passes)
        if names is None:
            reason = (
                f"{base.capitalize()} rough and finish are separate operations — "
                "passes not supplied, operation count left blank."
            )
    elif kind == "chamfer":
        if family is None:
            names = None
            reason = "Chamfer is mill or lathe — machine not supplied, operation count left blank."
        else:
            names = ["chamfer"]
    elif not kind:
        names = None
        reason = "Feature kind is missing — operation count left blank."
    else:
        names = None
        reason = f"No feature rule for kind {kind!r} — operation count left blank."

    if reason or not names or family is None:
        return [], reason or "Operation count left blank.", notes

    one = len(names) == 1
    plans = [
        {
            "name": name,
            "tool_key": tool if name in {"drill", "bore", "tap", "thread mill", "thread", "slot", "grooving", "counterbore", "countersink", "bore"} else "",
            "family": family,
            "feature_id": feature_id,
            "cycle": cycle if one else None,
            "had_cycle": cycle is not None,
        }
        for name in names
    ]
    if cycle is not None and not one:
        notes.append(CYCLE_NOT_SPLIT_NOTE)
    return plans, None, notes


def _label(name: str, tool_key: str) -> str:
    if tool_key:
        return f"{name} {tool_key} in"
    return name


def _has_volume(feature: dict[str, Any]) -> bool:
    dims = feature.get("dimensions") if isinstance(feature.get("dimensions"), dict) else {}
    keys = set(feature) | set(dims)
    return bool(keys & _VOLUME_KEYS)


def quote_machining_features(
    features: list[dict[str, Any]] | None,
    *,
    operation_cycle_times: dict[str, Any] | None = None,
    needs_machining: bool | None = None,
    features_source: str | None = None,
) -> dict[str, Any]:
    """Return operation count, per-operation run time, and setup time.

    ``quote_done`` is false when machining is required and any of those three
    is missing. Times from a removal rate are never filled in.
    """
    features = [f for f in (features or []) if isinstance(f, dict)]
    overrides = operation_cycle_times or {}
    from_drawing = features_source == "drawing"
    notes: list[str] = [
        DRAWING_READ_NOTE if from_drawing else DRAWING_NOTE,
        SEPARATE_CALC_NOTE,
        NOT_POSTED_NOTE,
    ]
    if from_drawing:
        notes.insert(1, SHARED_DRIVE_NOTE)
    purchased: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    plans: list[dict[str, Any]] = []
    saw_volume = False
    lathe_unspecified = False

    for index, feature in enumerate(features):
        feature_id = _text(feature.get("id")) or f"f{index + 1}"
        if _has_volume(feature):
            saw_volume = True
        feature_plans, reason, extra = _plans_for_feature(feature, feature_id)
        for note in extra:
            if note not in notes:
                notes.append(note)
        kind = _text(feature.get("kind") or feature.get("feature") or feature.get("type"))
        thickness = _inches(_dim(feature, "thickness_in", "thickness"))
        if any("purchased component" in note for note in extra):
            purchased.append(
                {
                    "feature_id": feature_id,
                    "thickness_in": thickness,
                    "reason": "Plate over 3/4 in stays a purchased component, not a machine operation.",
                }
            )
            continue
        if any("not a machine operation" in note or "not an item machining" in note for note in extra):
            excluded.append({"feature_id": feature_id, "kind": kind or "plate"})
            continue
        if reason:
            unresolved.append({"feature_id": feature_id, "kind": kind, "reason": reason})
            if reason not in notes:
                notes.append(reason)
            continue
        plans.extend(feature_plans)

    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    order: list[tuple[str, str, str]] = []
    for plan in plans:
        if plan["family"] == "lathe-unspecified":
            lathe_unspecified = True
        key = (plan["family"], plan["name"], plan["tool_key"])
        bucket = grouped.get(key)
        if bucket is None:
            bucket = {
                "family": plan["family"],
                "name": plan["name"],
                "tool_key": plan["tool_key"],
                "feature_ids": [],
                "cycles": [],
            }
            grouped[key] = bucket
            order.append(key)
        if plan["feature_id"] not in bucket["feature_ids"]:
            bucket["feature_ids"].append(plan["feature_id"])
        if plan["had_cycle"]:
            bucket["cycles"].append(plan["cycle"])

    operations: list[dict[str, Any]] = []
    for key in order:
        bucket = grouped[key]
        family = bucket["family"]
        code = _FAMILY_CODE.get(family)
        spec = _ITEM_OPS.get(code or "")
        op_id = ":".join(part for part in (family, bucket["name"], bucket["tool_key"]) if part)
        override = _cycle(overrides.get(op_id))
        run_time: float | None = None
        source = "missing"
        note = NO_REMOVAL_RATE_NOTE
        if override is not None:
            run_time = override
            source = "cycle_override"
            note = CYCLE_OVERRIDE_NOTE
        elif len(bucket["feature_ids"]) == 1 and len(bucket["cycles"]) == 1 and bucket["cycles"][0] is not None:
            run_time = bucket["cycles"][0]
            source = "cycle_override"
            note = CYCLE_OVERRIDE_NOTE
        operations.append(
            {
                "id": op_id,
                "name": bucket["name"],
                "label": _label(bucket["name"], bucket["tool_key"]),
                "machine": family,
                "operation_code": code,
                "equipment": spec["equipment"] if spec else None,
                "feature_ids": bucket["feature_ids"],
                "run_time_min": run_time,
                "run_time_source": source,
                "note": note,
            }
        )

    by_code: dict[str, list[dict[str, Any]]] = {}
    for op in operations:
        code = op.get("operation_code")
        if code:
            by_code.setdefault(code, []).append(op)

    item_operations: list[dict[str, Any]] = []
    for code in ("op_mill", "op_lathe", "op_lathe2"):
        shop_ops = by_code.get(code) or []
        if not shop_ops:
            continue
        spec = _ITEM_OPS[code]
        run_values = [op["run_time_min"] for op in shop_ops]
        if run_values and all(value is not None for value in run_values):
            item_run: float | None = float(sum(run_values))
            item_source = "typed_cycles" if len(run_values) > 1 else "cycle_override"
        else:
            item_run = None
            item_source = "missing"
        item_operations.append(
            {
                "operation_code": code,
                "equipment": spec["equipment"],
                "operation_name": spec["operation_name"],
                "operation_type": 10,
                "setup": {
                    "calculator": spec["setup_calculator"],
                    "cost_calc_type": 6,
                    "kind": "fixedtime",
                    "time_unit": "hour",
                    "fixedtime_hours": None,
                    "time_min": None,
                    "uses_stored_unit_time": False,
                    "note": NO_SETUP_NOTE,
                },
                "run": {
                    "calculator": spec["run_calculator"],
                    "cost_calc_type": 9,
                    "kind": "perunittime",
                    "field_name": spec["run_field"],
                    "time_min": item_run,
                    "source": item_source,
                },
                "shop_operation_ids": [op["id"] for op in shop_ops],
                "posted": False,
            }
        )

    claimed = bool(operations or unresolved or (needs_machining is True and not purchased and not features))
    if needs_machining is True:
        claimed = True
    if unresolved or (needs_machining is True and not operations):
        operation_count = None
    elif claimed:
        operation_count = len(operations)
    else:
        operation_count = 0

    if lathe_unspecified and LATHE_WHICH_NOTE not in notes:
        notes.append(LATHE_WHICH_NOTE)
    if saw_volume and VOLUME_NOTE not in notes:
        notes.append(VOLUME_NOTE)

    setup_time_min = None
    if len(item_operations) == 1 and not lathe_unspecified:
        setup_time_min = item_operations[0]["setup"]["time_min"]

    needs = bool(claimed or unresolved or operations)
    if needs_machining is False and not operations and not unresolved:
        needs = False
    missing: list[str] = []
    if needs:
        if operation_count is None:
            missing.append("operation_count")
        if (
            operation_count is None
            or not operations
            or any(op["run_time_min"] is None for op in operations)
        ):
            missing.append("run_time")
        setup_incomplete = (
            lathe_unspecified
            or not item_operations
            or any(item["setup"]["time_min"] is None for item in item_operations)
        )
        if setup_incomplete or setup_time_min is None:
            missing.append("setup_time")
        if "run_time" in missing and NO_REMOVAL_RATE_NOTE not in notes:
            notes.append(NO_REMOVAL_RATE_NOTE)
        if any(op["run_time_source"] == "cycle_override" for op in operations):
            if CYCLE_OVERRIDE_NOTE not in notes:
                notes.append(CYCLE_OVERRIDE_NOTE)
        if "setup_time" in missing and NO_SETUP_NOTE not in notes:
            notes.append(NO_SETUP_NOTE)

    quote_done = not missing if needs else True
    return {
        "needs_machining": needs,
        "quote_done": quote_done,
        "operation_count": operation_count,
        "operations": operations,
        "setup_time_min": setup_time_min,
        "setup_time_note": NO_SETUP_NOTE if needs else None,
        "item_operations": item_operations,
        "missing": missing,
        "purchased_components": purchased,
        "excluded_features": excluded,
        "unresolved_features": unresolved,
        "notes": notes,
        "shop_rate_per_hour": None,
        "code_source": {
            "quote_number": CODE_SOURCE_QUOTE,
            "quote_id": CODE_SOURCE_ID,
            "status": CODE_SOURCE_STATUS,
        },
        "reads_drawings": from_drawing,
        "posted": False,
    }


def format_machining_summary(machining: dict[str, Any] | None) -> dict[str, str]:
    """Three display strings that sit next to weld minutes."""
    if not machining:
        return {"operation_count": "—", "run_time": "—", "setup_time": "—"}
    count = machining.get("operation_count")
    ops = machining.get("operations") or []
    if not ops:
        run = "—"
    else:
        parts = []
        for op in ops:
            run_time = op.get("run_time_min")
            shown = "—" if run_time is None else str(run_time)
            parts.append(f"{op.get('label') or op.get('name')}: {shown}")
        run = "; ".join(parts)
    setup = machining.get("setup_time_min")
    return {
        "operation_count": "—" if count is None else str(count),
        "run_time": run,
        "setup_time": "—" if setup is None else str(setup),
    }


def machining_html_items(times: dict[str, Any] | None) -> str:
    summary = format_machining_summary((times or {}).get("machining"))
    return (
        f"<li>Machining operations: {summary['operation_count']}</li>"
        f"<li>Machining run time: {summary['run_time']}</li>"
        f"<li>Machining setup: {summary['setup_time']}</li>"
    )


def machining_blocks_quote(times: dict[str, Any] | None) -> bool:
    machining = (times or {}).get("machining") or {}
    return bool(machining.get("needs_machining") and not machining.get("quote_done"))


def machining_needs_info_flag(result: dict[str, Any] | None) -> str | None:
    if not result or not result.get("needs_machining") or result.get("quote_done"):
        return None
    labels = {
        "operation_count": "operation count",
        "run_time": "run time",
        "setup_time": "setup time",
        "shop_rate": "shop rate",
    }
    missing = [labels.get(item, item) for item in (result.get("missing") or [])]
    detail = ", ".join(missing) if missing else "operation count, run time, or setup time"
    return f"{_MACHINING_FLAG_PREFIX}{detail}"


def sync_machining_flag(flags: list[str], result: dict[str, Any] | None) -> list[str]:
    kept = [flag for flag in flags if not str(flag).startswith(_MACHINING_FLAG_PREFIX)]
    flag = machining_needs_info_flag(result)
    if flag:
        kept.append(flag)
    return kept


def carry_machining_inputs(previous: dict[str, Any] | None, takeoff: dict[str, Any]) -> dict[str, Any]:
    """Keep caller feature lists when takeoff is rebuilt. Does not invent features."""
    out = dict(takeoff)
    for key in (
        "machining_features",
        "machining_features_source",
        "operation_cycle_times",
        "needs_machining",
    ):
        if key in (previous or {}) and key not in out:
            out[key] = (previous or {})[key]
    return out


def process_assignment_with_code(
    assignment: dict[str, Any] | None,
    features: list[dict[str, Any]] | None = None,
    callouts: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Map a justified stock-versus-finished family onto one verified code.

    Turning uses ``op_lathe``. Milling uses ``op_mill``. ``op_lathe2`` is
    applied only when the assignment family is already lathe 2, which the
    stock comparison does not produce. An unjustified comparison keeps the
    stock and finished shape and does not receive an operation code.

    A justified code then takes run time and setup from the machining
    calculator when the stock form is stated plate (mill) or stated bar or
    tube with a finished round (lathe). A stated forging that justifies mill
    does not take a volume from the calculator. The shop rate stays blank.
    """
    if not isinstance(assignment, dict):
        return None
    out = dict(assignment)
    out["run_time_min"] = None
    out["setup_time_min"] = None
    out["shop_rate_per_hour"] = None
    out["posted"] = False
    if assignment.get("operation_justified") is not True:
        out["operation_code"] = None
        return out
    family = (
        _text(assignment.get("family"))
        .casefold()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
    )
    if family == "lathe2":
        code = "op_lathe2"
    else:
        code = _FAMILY_CODE.get(family)
    if not code:
        out["operation_code"] = None
        return out
    out["family"] = "lathe2" if family == "lathe2" else family
    out["operation_code"] = code
    from quote_core.machining_calculator import times_for_justified_operation

    times = times_for_justified_operation(out, features=features, callouts=callouts)
    out["run_time_min"] = times.get("run_time_min")
    out["setup_time_min"] = times.get("setup_time_min")
    out["shop_rate_per_hour"] = None
    out["posted"] = False
    if times.get("run_blank_reason"):
        out["run_blank_reason"] = times["run_blank_reason"]
    if times.get("setup_note"):
        out["setup_note"] = times["setup_note"]
    if times.get("calculator"):
        out["calculator"] = times["calculator"]
    return out


def _apply_calculator_to_quote(result: dict[str, Any], coded: dict[str, Any]) -> None:
    """Copy a justified calculator setup, and run time when it is one number.

    A typed cycle already on an operation is left as the run time. The
    calculator's one cycle is not split across several shop operations.
    """
    code = coded.get("operation_code")
    if not code:
        return
    operations = [op for op in result.get("operations") or [] if op.get("operation_code") == code]
    reason = coded.get("run_blank_reason")
    overrides = [op for op in operations if op.get("run_time_source") == "cycle_override"]
    run_time = coded.get("run_time_min")
    if run_time is not None and operations and not overrides and len(operations) == 1:
        operations[0]["run_time_min"] = run_time
        operations[0]["run_time_source"] = "calculator"
        operations[0]["note"] = CALCULATOR_RUN_NOTE
    elif run_time is not None and len(operations) > 1 and not overrides:
        reason = (
            "Run time left blank. The calculator returns one cycle for the part. "
            "It was not split across operations."
        )
    elif reason and operations and not overrides:
        for op in operations:
            if op.get("run_time_min") is None:
                op["note"] = reason

    for item in result.get("item_operations") or []:
        if item.get("operation_code") != code:
            continue
        shop = [
            op
            for op in (result.get("operations") or [])
            if op.get("id") in (item.get("shop_operation_ids") or [])
        ]
        run_values = [op.get("run_time_min") for op in shop]
        if run_values and all(value is not None for value in run_values):
            item["run"]["time_min"] = float(sum(run_values))
            sources = {op.get("run_time_source") for op in shop}
            item["run"]["source"] = "calculator" if sources == {"calculator"} else "cycle_override"
        setup_min = coded.get("setup_time_min")
        if setup_min is not None:
            item["setup"]["fixedtime_hours"] = setup_min / 60.0
            item["setup"]["time_min"] = setup_min
            item["setup"]["note"] = coded.get("setup_note") or item["setup"].get("note")

    notes = list(result.get("notes") or [])
    setup_values = [
        item["setup"]["time_min"]
        for item in (result.get("item_operations") or [])
        if item.get("operation_code")
    ]
    setup_filled = bool(setup_values) and all(value is not None for value in setup_values)
    if setup_filled:
        notes = [note for note in notes if note != NO_SETUP_NOTE]
        setup_note = coded.get("setup_note")
        if setup_note and setup_note not in notes:
            notes.append(setup_note)
        result["setup_time_note"] = coded.get("setup_note")
    runs_filled = bool(operations) and all(op.get("run_time_min") is not None for op in operations)
    if runs_filled and not (run_time is not None and len(operations) > 1 and not overrides):
        notes = [note for note in notes if note != NO_REMOVAL_RATE_NOTE]
    elif reason:
        notes = [note for note in notes if note != NO_REMOVAL_RATE_NOTE]
        if reason not in notes:
            notes.append(reason)
    result["notes"] = notes
    _recompute_quote_completion(result)


def _recompute_quote_completion(result: dict[str, Any]) -> None:
    """Set missing and quote_done from the operations currently on the result."""
    operations = result.get("operations") or []
    item_operations = result.get("item_operations") or []
    needs = bool(result.get("needs_machining"))
    lathe_unspecified = any(op.get("machine") == "lathe-unspecified" for op in operations)
    operation_count = result.get("operation_count")
    setup_time_min = None
    if len(item_operations) == 1 and not lathe_unspecified:
        setup_time_min = item_operations[0]["setup"]["time_min"]
    result["setup_time_min"] = setup_time_min
    missing: list[str] = []
    if needs:
        if operation_count is None:
            missing.append("operation_count")
        if (
            operation_count is None
            or not operations
            or any(op.get("run_time_min") is None for op in operations)
        ):
            missing.append("run_time")
        setup_incomplete = (
            lathe_unspecified
            or not item_operations
            or any(item["setup"]["time_min"] is None for item in item_operations)
        )
        if setup_incomplete or setup_time_min is None:
            missing.append("setup_time")
        if "run_time" in missing and NO_REMOVAL_RATE_NOTE not in (result.get("notes") or []):
            if not any("Run time left blank" in str(note) for note in result.get("notes") or []):
                result["notes"] = [*(result.get("notes") or []), NO_REMOVAL_RATE_NOTE]
        if "setup_time" in missing and NO_SETUP_NOTE not in (result.get("notes") or []):
            result["notes"] = [*(result.get("notes") or []), NO_SETUP_NOTE]
    result["missing"] = missing
    result["quote_done"] = (not missing) if needs else True
    result["shop_rate_per_hour"] = None
    result["posted"] = False


def attach_machining_times(times: dict[str, Any], takeoff: dict[str, Any] | None) -> dict[str, Any]:
    """Attach a machining result only when features or an explicit need is present."""
    takeoff = takeoff or {}
    features = takeoff.get("machining_features")
    has_features = isinstance(features, list) and len(features) > 0
    marked = takeoff.get("needs_machining") is True
    if not has_features and not marked:
        return times
    result = quote_machining_features(
        list(features) if isinstance(features, list) else [],
        operation_cycle_times=takeoff.get("operation_cycle_times")
        if isinstance(takeoff.get("operation_cycle_times"), dict)
        else None,
        needs_machining=True if marked else None,
        features_source=takeoff.get("machining_features_source")
        if takeoff.get("machining_features_source") == "drawing"
        else None,
    )
    reading = takeoff.get("machining_reading")
    if isinstance(reading, dict):
        coded = process_assignment_with_code(
            reading.get("process_from_stock"),
            features=reading.get("features") if isinstance(reading.get("features"), list) else None,
            callouts=reading.get("callouts") if isinstance(reading.get("callouts"), list) else None,
        )
        if coded:
            result["process_from_stock"] = coded
            evidence = coded.get("evidence")
            if evidence and evidence not in result["notes"]:
                result["notes"] = [*result["notes"], evidence]
            _apply_calculator_to_quote(result, coded)
    out = dict(times)
    out["machining"] = result
    return out


def status_after_review(current: str, requested: str | None, times: dict[str, Any] | None) -> str:
    """Machining required with a missing count, run time, or setup stays not done."""
    if machining_blocks_quote(times):
        return "needs_info"
    if requested:
        return requested
    if current == "error":
        return "review"
    return current
