"""Run minutes and setup hours from Kyle's machining quote calculator.

Source workbook: ``Kannon-machining-quote-calculator.xlsx`` (Quote, Feeds,
and Allowances). Machines is a menu the quote does not pick from. Rates
dollar-per-hour cells are empty and are not read. No shop rate is returned.

Quote tab, green cells, as written:

- Cubic inches removed (E6). Blank unless stock size and finished size are
  both present (B11, B12, B14, B15). Bar uses two cylinders,
  ``pi/4 * OD^2 * length``. Anything that is not the word Bar uses a box,
  ``thickness * length * height``, and a blank height copies the thickness.
- Material factor (E7). Exact lookup of the grade on Feeds column A,
  returning the roughing factor (column B). A miss uses 1.
- Cut minutes (E8). Bar (part type Lathe): cubic inches * factor / Feeds!B17.
  Mill: cubic inches * factor / Feeds!B18. Feeds!B17 is 4 cubic inches per
  minute (1018 lathe rough). Feeds!B18 is 3 (1018 mill rough, 50 taper).
  The 40-taper 1.5 and 30-taper 0.4 rates are on the Feeds tab and are not
  used. The workbook says the quote does not pick a machine row, so a 30
  taper and a 50 taper share the mill rate.
- Allowance minutes (E9), added to the cut, not to setup:
  rapid and approach 0.15 min per operation (Allowances!B3),
  finish-pass share 0.25 of cut minutes when tight or a finish callout
  (B4), tight share 0.35 of cut minutes when tight (B5),
  deburr 4 min per part (B6), in-process inspection 2 min per part (B8).
  Tool-change seconds (B2) and first-article minutes (B7) are not in this
  formula and are not added.
- Cycle minutes (E10): ``(cut + allowances) * 1.15``. The 1.15 pad is
  Allowances!B12.
- Setup hours for the lot (E11). Repeat job Yes: 0.25 h per operation
  (B14). Anything that is not Yes, including a blank repeat cell: new setup
  0.75 h (B15) plus prove-out 0.5 h (B11), per operation.
- Program hours (E12) are a separate line: 0 on a repeat, 1.5 h for a new
  lathe program (B9), 2 h for a new mill program (B10). They are not setup
  hours and are not returned as setup.

Operation count in the workbook is lathe chuckings or mill setups, plus one
only when an outside process is stated. It does not count each tool. The
drawing rarely states that count. One justified operation code is counted
as one chucking or one mill setup. An outside process is not invented from
a blank cell (the sample workbook says None; a blank cell in Excel would
add one, and that is not used here).

A typed cycle time replaces run minutes only. The workbook would still add
allowances and the 1.15 pad on top of a Mastercam time. That is not done
here.

Holes, threads, grooves, and deep bores have no minute rows. The Quote tab
says they need their own rows or a STEP reader. When the stock box and the
finished box are the same size, cubic inches removed are 0 and run time
stays blank. The flat deburr and inspection minutes are not used as a run
time by themselves. A stated size and a finished size within 0.01 in are
the same size (a title of 9.63 in and a solid of 9.625 in).

Tube is round stock for the lathe or lathe-2 decision, but the cubic-inch
formula applies only when the stock form is Bar. Tube run time stays blank.
"""

from __future__ import annotations

import math
from typing import Any

# Feeds!B17 and Feeds!B18. The quote formula divides by these cells.
LATHE_ROUGH_IN3_PER_MIN = 4.0
MILL_ROUGH_IN3_PER_MIN = 3.0
# On the Feeds tab, and not selected by Quote!E8.
_MILL_40_TAPER_IN3_PER_MIN = 1.5
_MILL_30_TAPER_IN3_PER_MIN = 0.4

# Allowances column B, in the units the sheet names.
RAPID_MIN_PER_OPERATION = 0.15
FINISH_PASS_SHARE = 0.25
TIGHT_SHARE = 0.35
DEBURR_MIN_PER_PART = 4.0
IN_PROCESS_MIN_PER_PART = 2.0
PROVE_OUT_HOURS_PER_OPERATION = 0.5
CONFIDENCE_PAD = 1.15
TIGHT_CUTOFF_IN = 0.005
REPEAT_SETUP_HOURS_PER_OPERATION = 0.25
NEW_SETUP_HOURS_PER_OPERATION = 0.75
NEW_PROGRAM_LATHE_HOURS = 1.5
NEW_PROGRAM_MILL_HOURS = 2.0

# Title-block hundredths versus a solid measured to thousandths.
_SAME_SIZE_IN = 0.01

# Feeds column A, roughing factor (column B). Lookup is exact aside from case.
_ROUGHING_FACTORS = {
    "1018": 1.0,
    "1045": 1.15,
    "4140 annealed": 1.25,
    "4140 ht": 1.6,
    "a36": 1.1,
    "304": 1.8,
    "316": 2.0,
    "17-4": 1.7,
    "6061-t6": 0.45,
    "7075-t6": 0.5,
    "c360": 0.35,
    "delrin": 0.4,
}

_HOLE_KINDS = {"hole", "countersink", "counterbore", "thread", "groove", "bore"}


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _same(left: float, right: float) -> bool:
    return abs(left - right) <= _SAME_SIZE_IN


def roughing_factor(grade: str | None) -> tuple[float, str]:
    """Feeds roughing factor. A grade that is not on the tab uses 1."""
    text = " ".join(str(grade or "").casefold().split())
    if not text:
        return 1.0, "No grade was passed. The lookup miss uses 1."
    factor = _ROUGHING_FACTORS.get(text)
    if factor is None:
        return 1.0, f"{grade} is not on the Feeds tab. The lookup miss uses 1."
    return factor, f"Feeds roughing factor for {grade} is {factor}."


def _bar_cubic_inches(diameter: float, length: float) -> float:
    return math.pi / 4.0 * diameter * diameter * length


def _finished_plate_axes(
    envelope: list[Any],
    thickness: float,
) -> tuple[float, float, float] | None:
    values = [_num(item) for item in envelope[:3]]
    if any(item is None for item in values) or len(values) < 3:
        return None
    numbers = [float(item) for item in values if item is not None]
    index = min(range(3), key=lambda slot: abs(numbers[slot] - thickness))
    thick = numbers[index]
    plan = sorted(numbers[slot] for slot in range(3) if slot != index)
    return thick, plan[0], plan[1]


def cubic_inches_removed(stock: dict[str, Any], finished: dict[str, Any]) -> tuple[float | None, str | None]:
    """Quote!E6. None means a required size is missing.

    The reason is None when a volume was computed, including zero.
    """
    form = str(stock.get("form") or "").casefold()
    finished = finished or {}
    if form == "bar":
        diameter = _num(stock.get("diameter_in"))
        length = _num(stock.get("length_in"))
        finished_diameters = [
            value
            for value in (finished.get("diameters_in") or [])
            if _num(value) is not None
        ]
        finished_diameter = max(finished_diameters) if finished_diameters else _num(
            finished.get("diameter_in")
        )
        finished_length = _num(finished.get("length_in"))
        if diameter is None or length is None or finished_diameter is None or finished_length is None:
            return None, (
                "Run time left blank. Bar cubic inches need a stock diameter, "
                "a stock length, a finished diameter, and a finished length. "
                "A missing one of those was not guessed."
            )
        removed = _bar_cubic_inches(diameter, length) - _bar_cubic_inches(
            finished_diameter, finished_length
        )
        return max(0.0, removed), None
    if form == "tube":
        return None, (
            "Run time left blank. The round volume formula applies when stock "
            "form is Bar. Tube has no volume formula in the calculator."
        )
    if form != "plate":
        return None, "Run time left blank. Stock form is not bar or plate."
    thickness = _num(stock.get("thickness_in"))
    length = _num(stock.get("length_in"))
    width = _num(stock.get("width_in"))
    envelope = finished.get("envelope_in")
    if thickness is None or length is None or width is None or not isinstance(envelope, list):
        return None, (
            "Run time left blank. Plate cubic inches need stock thickness, "
            "stock length, stock width, and the finished envelope. "
            "A missing one of those was not guessed."
        )
    axes = _finished_plate_axes(envelope, thickness)
    if axes is None:
        return None, (
            "Run time left blank. The finished envelope does not have three sizes."
        )
    finished_thickness, finished_width, finished_length = axes
    if (
        _same(thickness, finished_thickness)
        and _same(min(length, width), finished_width)
        and _same(max(length, width), finished_length)
    ):
        return 0.0, None
    stock_volume = thickness * length * width
    finished_volume = finished_thickness * finished_width * finished_length
    return max(0.0, stock_volume - finished_volume), None


def _op_count_phrase(count: float) -> str:
    shown = f"{count:g}"
    word = "operation" if count == 1 else "operations"
    return f"{shown} {word}"


def _operations_for_setup(part_type: str, stated_operations: float | None) -> float:
    if stated_operations is not None and stated_operations >= 0:
        return stated_operations
    # One justified code. Not one per tool.
    return 1.0


def setup_hours(
    part_type: str,
    *,
    repeat: bool = False,
    operations: float | None = None,
    outside_process: bool = False,
) -> tuple[float, str]:
    """Quote!E11, in hours. Program hours are not included."""
    count = _operations_for_setup(part_type, operations)
    if outside_process:
        count += 1.0
    if repeat:
        hours = REPEAT_SETUP_HOURS_PER_OPERATION * count
        note = (
            f"Repeat setup is {REPEAT_SETUP_HOURS_PER_OPERATION} h times "
            f"{_op_count_phrase(count)}."
        )
    else:
        hours = (NEW_SETUP_HOURS_PER_OPERATION + PROVE_OUT_HOURS_PER_OPERATION) * count
        note = (
            f"Repeat was not Yes, so setup is {NEW_SETUP_HOURS_PER_OPERATION} h "
            f"plus prove-out {PROVE_OUT_HOURS_PER_OPERATION} h, times "
            f"{_op_count_phrase(count)}. Programming hours are not included."
        )
    return hours, note


def program_hours(part_type: str, *, repeat: bool = False) -> float:
    """Quote!E12. Reported so it is not mistaken for setup."""
    if repeat:
        return 0.0
    if part_type == "Lathe":
        return NEW_PROGRAM_LATHE_HOURS
    if part_type == "Mill":
        return NEW_PROGRAM_MILL_HOURS
    return NEW_PROGRAM_LATHE_HOURS + NEW_PROGRAM_MILL_HOURS


def _allowance_minutes(
    cut_minutes: float,
    operations: float,
    *,
    tight: bool,
    finish: bool,
) -> float:
    extra = 0.0
    if tight or finish:
        extra += FINISH_PASS_SHARE * cut_minutes
    if tight:
        extra += TIGHT_SHARE * cut_minutes
    return (
        RAPID_MIN_PER_OPERATION * operations
        + extra
        + DEBURR_MIN_PER_PART
        + IN_PROCESS_MIN_PER_PART
    )


def cycle_minutes(
    removed_in3: float,
    *,
    part_type: str,
    factor: float,
    operations: float,
    tight: bool = False,
    finish: bool = False,
) -> tuple[float, float]:
    """Return (cycle minutes, cut minutes) from Quote!E8 and E10."""
    rate = LATHE_ROUGH_IN3_PER_MIN if part_type == "Lathe" else MILL_ROUGH_IN3_PER_MIN
    cut = removed_in3 * factor / rate
    allowances = _allowance_minutes(cut, operations, tight=tight, finish=finish)
    return (cut + allowances) * CONFIDENCE_PAD, cut


def _part_type(operation_code: str | None) -> str | None:
    if operation_code == "op_mill":
        return "Mill"
    if operation_code in {"op_lathe", "op_lathe2"}:
        return "Lathe"
    return None


def _skipped_feature_kinds(features: list[dict[str, Any]] | None) -> list[str]:
    found: list[str] = []
    for feature in features or []:
        if not isinstance(feature, dict):
            continue
        kind = str(feature.get("kind") or "").casefold().replace(" ", "_").replace("-", "_")
        if kind in _HOLE_KINDS or feature.get("thread_form"):
            label = kind or "thread"
            if label not in found:
                found.append(label)
    return found


def _tight_from_callouts(callouts: list[dict[str, Any]] | None) -> bool:
    """Inch tolerance tighter than Allowances!B13. Degrees and fit codes are not inches."""
    for callout in callouts or []:
        if not isinstance(callout, dict):
            continue
        if callout.get("symbol") not in {"plus_minus", None} and callout.get("unit") != "inch":
            continue
        if callout.get("symbol") == "degree" or callout.get("unit") == "degree":
            continue
        if callout.get("symbol") != "plus_minus":
            continue
        if str(callout.get("unit") or "").casefold() in {"degree", "deg"}:
            continue
        value = _num(callout.get("value"))
        if value is not None and 0 < value < TIGHT_CUTOFF_IN:
            return True
    return False


def _finish_called(callouts: list[dict[str, Any]] | None) -> bool:
    return any(
        isinstance(callout, dict) and callout.get("symbol") == "surface_texture"
        for callout in (callouts or [])
    )


def times_for_justified_operation(
    assignment: dict[str, Any],
    *,
    features: list[dict[str, Any]] | None = None,
    callouts: list[dict[str, Any]] | None = None,
    repeat: bool | None = None,
    stated_operations: float | None = None,
    outside_process: bool = False,
    material_grade: str | None = None,
) -> dict[str, Any]:
    """Fill run and setup only when this workbook can.

    ``shop_rate_per_hour`` is always None. A zero-removal part does not get
    a run time. A typed cycle is applied by the caller and is not padded.
    """
    blank = {
        "run_time_min": None,
        "setup_time_min": None,
        "shop_rate_per_hour": None,
        "run_blank_reason": None,
        "setup_blank_reason": None,
        "calculator": None,
    }
    if assignment.get("operation_justified") is not True:
        blank["run_blank_reason"] = "No operation was justified, so the calculator was not applied."
        blank["setup_blank_reason"] = blank["run_blank_reason"]
        return blank
    code = assignment.get("operation_code")
    part_type = _part_type(code if isinstance(code, str) else None)
    stock = assignment.get("stock") if isinstance(assignment.get("stock"), dict) else {}
    finished = assignment.get("finished") if isinstance(assignment.get("finished"), dict) else {}
    form = str(stock.get("form") or "")
    stated = stock.get("stated") is True and stock.get("guessed") is not True
    allowed = stated and (
        (code == "op_mill" and form == "plate")
        or (
            code in {"op_lathe", "op_lathe2"}
            and form in {"bar", "tube"}
            and finished.get("shape") == "round"
        )
    )
    if part_type is None or not allowed:
        reason = (
            "Run time and setup left blank. The calculator runs for op_mill "
            "when the sheet states plate, and for op_lathe or op_lathe2 when "
            "the sheet states bar or tube and the finished part is round."
        )
        blank["run_blank_reason"] = reason
        blank["setup_blank_reason"] = reason
        return blank

    is_repeat = repeat is True
    hours, setup_note = setup_hours(
        part_type,
        repeat=is_repeat,
        operations=stated_operations,
        outside_process=outside_process,
    )
    removed, volume_reason = cubic_inches_removed(stock, finished)
    factor, factor_note = roughing_factor(material_grade)
    operations = _operations_for_setup(part_type, stated_operations)
    if outside_process:
        operations += 1.0
    detail: dict[str, Any] = {
        "part_type": part_type,
        "operations": operations,
        "repeat_job": is_repeat,
        "cubic_inches_removed": removed,
        "material_factor": factor,
        "material_factor_note": factor_note,
        "cut_minutes": None,
        "cycle_minutes": None,
        "setup_hours": hours,
        "program_hours_not_setup": program_hours(part_type, repeat=is_repeat),
        "shop_rate_per_hour": None,
        "removal_in3_per_min": (
            MILL_ROUGH_IN3_PER_MIN if part_type == "Mill" else LATHE_ROUGH_IN3_PER_MIN
        ),
        # Quote!E8 does not divide by the 40-taper or 30-taper rates.
        "taper_rates_not_used_in3_per_min": {
            "40": _MILL_40_TAPER_IN3_PER_MIN,
            "30": _MILL_30_TAPER_IN3_PER_MIN,
        },
    }
    run_time: float | None = None
    run_reason: str | None = volume_reason
    if removed == 0:
        skipped = _skipped_feature_kinds(features)
        feature_sentence = (
            f" The features include {', '.join(skipped)}. "
            "The workbook has no minute row for a hole, countersink, counterbore, "
            "thread, groove, or bore."
            if skipped
            else ""
        )
        run_reason = (
            "Run time left blank. Stock and the finished envelope are the same size, "
            "so cubic inches removed are 0."
            + feature_sentence
            + " Deburr and inspection minutes were not used as a run time by themselves."
        )
    elif removed is not None and removed > 0:
        cycle, cut = cycle_minutes(
            removed,
            part_type=part_type,
            factor=factor,
            operations=operations,
            tight=_tight_from_callouts(callouts),
            finish=_finish_called(callouts),
        )
        run_time = cycle
        run_reason = None
        detail["cut_minutes"] = cut
        detail["cycle_minutes"] = cycle
    result = {
        "run_time_min": run_time,
        "setup_time_min": hours * 60.0,
        "shop_rate_per_hour": None,
        "run_blank_reason": run_reason,
        "setup_blank_reason": None,
        "setup_note": setup_note,
        "calculator": detail,
    }
    return result
