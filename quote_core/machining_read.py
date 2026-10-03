"""Read machining callouts from a PDF and geometry from a STEP file.

A feature is added only when the file states it. A diameter, a cylinder,
or a plane by itself is not a hole, a thread, a groove, or a face operation.
Missing values stay blank.

When the sheet does not name mill, lathe, or lathe 2, compare the starting
stock the sheet actually states to the finished solid (Kyle, 2026-10-02).
Stock is bar, plate, tube, or unknown. A missing stock line stays unknown.
The largest finished diameter is not a bar size. A finished round smaller
than a stated round stock can be turning. A finished plate with holes can
be milling. Lathe 2 is not chosen from that comparison. The comparison
does not invent a cycle time or a shop rate. The quote maps a justified
family onto a verified operation code.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from quote_core.machining_quote import SHARED_DRIVE_NOTE
from quote_core.machining_symbols import describe_symbol, unknown_symbols_in_text

_DIAMETER_GAP_IN = 0.001

_NUMBER = r"([0-9]*\.?[0-9]+|\d+\s*/\s*\d+)"
_DIAMETER = re.compile(
    "(?:"
    rf"(?:⌀|Ø|∅)\s*{_NUMBER}"
    rf"|\bDIA\b\s*{_NUMBER}"
    rf"|{_NUMBER}\s*\bDIA\b"
    rf"|\bDIAMETER\b\s*{_NUMBER}"
    rf"|{_NUMBER}\s*\bDIAMETER\b"
    ")",
    re.IGNORECASE,
)
_COUNT = re.compile(r"(?<![\d.])(\d+)X(?![\d.])", re.IGNORECASE)
_DEPTH = re.compile(rf"(?:↧|↓|\bDEPTH\b)\s*{_NUMBER}", re.IGNORECASE)
_THRU = re.compile(r"\bTHRU\b|\bTHROUGH\b", re.IGNORECASE)
_THREAD = re.compile(
    rf"(?<![A-Z0-9])(?:(\d+)\s*/\s*(\d+)|(\d*\.\d+|\d+))\s*-\s*(\d+)\s*"
    rf"(UNC|UNF|UNEF|UNS|UN)\b(?:\s*-?\s*(\d[AB]))?",
    re.IGNORECASE,
)
_METRIC = re.compile(
    r"(?<![A-Z])M(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_GROOVE = re.compile(
    rf"\bGROOVE\b(?:\s+{_NUMBER}\s*WIDE)?(?:\s+X\s+{_NUMBER}\s*DEEP)?",
    re.IGNORECASE,
)
_PLATE = re.compile(rf"\bPLATE\b\s+{_NUMBER}\s*(?:IN(?:CH)?\s*)?THK\b", re.IGNORECASE)
_FACE = re.compile(r"^(?:MACHINE\s+)?FACE$", re.IGNORECASE)
_RA = re.compile(
    rf"(?:\bRa\s*{_NUMBER}|\b{_NUMBER}\s*Ra\b)",
    re.IGNORECASE,
)
_FINISH_NOTE_LINE = re.compile(
    r"(?:SURFACE\s+FINISH|MACHINED\s+SURFACE(?:\s+FINISH(?:ES)?)?)",
    re.IGNORECASE,
)
_RADIUS = re.compile(rf"(?<![A-Z])(?:SR|CR|R)\s*{_NUMBER}", re.IGNORECASE)
_HOLE_PROCESS = re.compile(r"\b(DRILL|REAM|BORE)\b", re.IGNORECASE)
_COUNTERBORE = re.compile(r"⌴|\bCOUNTERBORE\b|\bSPOTFACE\b", re.IGNORECASE)
_COUNTERSINK = re.compile(r"⌵|\bCOUNTERSINK\b", re.IGNORECASE)
_CHAMFER_WORD = re.compile(r"\bCHAMFER\b", re.IGNORECASE)
_MACHINE_WORD = re.compile(r"\b(LATHE\s*2|LATHE2|LATHE|MILL)\b", re.IGNORECASE)
_STEP_RADIUS = re.compile(
    r"(CYLINDRICAL_SURFACE|CIRCLE)\s*\(\s*'[^']*'\s*,\s*#\d+\s*,\s*"
    r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?)\s*\)",
    re.IGNORECASE,
)
_ANGLE = re.compile(
    r"^(\d+(?:\.\d+)?)\s*(?:°|DEGREES?|DEG)$",
    re.IGNORECASE,
)
_LONE_INT = re.compile(r"^\d+$")
_LONE_DECIMAL = re.compile(r"^\d+(?:\.\d+)?$")
_DRILL_SIZE = re.compile(r"\bDRILL\b[^(]*\(\s*([0-9]*\.?[0-9]+)\s*\)", re.IGNORECASE)
_HOLE_QTY = re.compile(r"\(\s*(\d+)\s*\)\s*HOLE\b", re.IGNORECASE)
_PLANE = re.compile(r"\bPLANE\s*\(", re.IGNORECASE)
_STEP_ENTITY = re.compile(r"^#(\d+)\s*=\s*(.+?);\s*$", re.MULTILINE)
_STEP_POINT = re.compile(
    r"CARTESIAN_POINT\s*\(\s*'[^']*'\s*,\s*\(\s*([^)]+)\)",
    re.IGNORECASE,
)
_STEP_VERTEX = re.compile(
    r"VERTEX_POINT\s*\(\s*'[^']*'\s*,\s*#(\d+)",
    re.IGNORECASE,
)
_STEP_DIR = re.compile(
    r"DIRECTION\s*\(\s*'[^']*'\s*,\s*\(\s*([^)]+)\)",
    re.IGNORECASE,
)
_STEP_AXIS = re.compile(
    r"AXIS2_PLACEMENT_3D\s*\(\s*'[^']*'\s*,\s*#(\d+)\s*,\s*#(\d+)",
    re.IGNORECASE,
)
_STEP_CYLINDER = re.compile(
    r"CYLINDRICAL_SURFACE\s*\(\s*'[^']*'\s*,\s*#(\d+)\s*,\s*"
    r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?)\s*\)",
    re.IGNORECASE,
)
# A revolved profile stores vertices in one plane. That is not a plate.
_PROFILE_SPAN_IN = 0.01
# Same gap the callout matcher uses for one diameter.
_DIAMETER_CLUSTER_IN = 0.001
# Origins this close to one axis are the same centerline.
_AXIS_TOL_IN = 0.02
# Plate: thin axis at or under the purchased-plate limit, and thin vs width.
_PLATE_THICK_MAX_IN = 0.75
_PLATE_THIN_RATIO = 0.25
_PROCESS_KINDS = {
    "face",
    "groove",
    "thread",
    "chamfer",
    "countersink",
    "counterbore",
    "hole",
    "slot",
    "pocket",
    "turn",
    "bore",
    "taper",
    "knurl",
    "part_off",
}
_MILL_FEATURE_KINDS = {"hole", "countersink", "counterbore", "plate"}

_CYLINDER_NOTE = (
    "Cylindrical surfaces in the STEP file are not holes. "
    "No hole feature was added from them."
)
_STEP_THREAD_NOTE = "No thread callout in the STEP file — thread left blank."
_STEP_GROOVE_NOTE = "No groove callout in the STEP file — groove left blank."
_PLANE_NOTE = "Plane count is geometry only. It was not read as a face operation."
_NO_PDF_NOTE = "PDF was not supplied — drawing callouts left blank."
_NO_STEP_NOTE = "STEP was not supplied — solid geometry left blank."
_EMPTY_PDF_NOTE = "PDF has no extractable text — callouts left blank."
_PDF_FAIL_NOTE = "PDF text could not be read — callouts left blank."
_STEP_FAIL_NOTE = "STEP text could not be read — geometry left blank."
_SURFACE_RA_NOTE = "Surface texture is a callout. It was not added as an operation."
_SURFACE_VALUE_NOTE = (
    "A machined surface finish value was read. "
    "It is a surface-finish requirement, not a hole and not an operation. "
    "The roughness parameter name is not on the line. "
    "Run time and setup were not added."
)
_SURFACE_WORD_NOTE = (
    "A surface-finish note was read. "
    "It is a requirement, not a hole and not an operation. "
    "Run time and setup were not added."
)


def _diameter_value(line: str) -> float | None:
    match = _DIAMETER.search(line)
    if not match:
        return None
    for group in match.groups():
        if group:
            return _num(group)
    return None


def _num(token: str | None) -> float | None:
    if token is None:
        return None
    text = token.strip().replace(" ", "")
    if not text:
        return None
    if "/" in text:
        num, _, den = text.partition("/")
        try:
            return float(num) / float(den)
        except (TypeError, ValueError, ZeroDivisionError):
            return None
    try:
        return float(text)
    except ValueError:
        return None


def _pdf_text(path: Path) -> str:
    import fitz

    doc = fitz.open(path)
    try:
        return "\n".join(page.get_text("text") for page in doc)
    finally:
        doc.close()


def _blank(field: str, note: str) -> dict[str, str]:
    return {"field": field, "note": note}


def _feature(kind: str, callout: str, **extra: Any) -> dict[str, Any]:
    dimensions = extra.pop("dimensions", {})
    blank = extra.pop("blank_fields", [])
    feature = {
        "kind": kind,
        "dimensions": dimensions,
        "callout": callout.strip(),
        "source": "pdf",
        "blank_fields": blank,
    }
    feature.update(extra)
    return feature


def _surface_finish_callout(text: str, value: Any | None = None) -> dict[str, Any] | None:
    """A finish requirement. Not a hole and not an operation."""
    described = describe_symbol(text)
    if described.get("id") != "surface_texture" or described.get("known") is not True:
        return None
    if value is None and isinstance(described.get("roughness"), float):
        value = described["roughness"]
    if re.search(r"\bRa\b", text, re.IGNORECASE):
        note = _SURFACE_RA_NOTE
    elif value is not None:
        note = _SURFACE_VALUE_NOTE
    else:
        note = _SURFACE_WORD_NOTE
    row: dict[str, Any] = {
        "symbol": "surface_texture",
        "text": text.strip(),
        "feature": False,
        "meaning": described["meaning"],
        "citation": described["citation"],
        "note": note,
    }
    if value is not None:
        row["value"] = value
    return row


def _word_on_the_left(words: list[tuple], anchor: tuple | None, token: str) -> tuple | None:
    if anchor is None:
        return None
    for word in words:
        if str(word[4]).upper() != token:
            continue
        if word[5].x1 > anchor[5].x0 + 2:
            continue
        if _rect_gap(word[5], anchor[5]) > 8:
            continue
        return word
    return None


def _parse_pdf_lines(text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    features: list[dict[str, Any]] = []
    callouts: list[dict[str, Any]] = []
    unreadable: list[str] = []
    lines = [" ".join(raw.split()) for raw in text.splitlines()]
    lines = [line for line in lines if line]
    index = 0
    while index < len(lines):
        line = lines[index]
        thread = _THREAD.search(line)
        metric = None if thread else _METRIC.search(line)
        if thread or metric:
            feature = _thread_feature(line, thread, metric)
            index = _attach_tap_note(feature, lines, index)
            features.append(feature)
            continue
        index += 1
        groove = _GROOVE.search(line)
        if groove:
            features.append(_groove_feature(line, groove))
            continue
        plate = _PLATE.search(line)
        if plate:
            features.append(_plate_feature(line, plate))
            continue
        if _FACE.fullmatch(line):
            features.append(
                _feature(
                    "face",
                    line,
                    blank_fields=[
                        _blank(
                            "machine",
                            "The line does not say mill or lathe — machine left blank.",
                        )
                    ],
                )
            )
            continue
        roughness = _RA.search(line)
        if roughness and not _HOLE_PROCESS.search(line):
            number = roughness.group(1) or roughness.group(2)
            row = _surface_finish_callout(roughness.group(0), number)
            if row is not None:
                callouts.append(row)
                continue
        finish_line = _surface_finish_callout(line)
        if finish_line is not None and line.casefold() != "finish" and (
            "value" in finish_line or _FINISH_NOTE_LINE.fullmatch(line)
        ):
            callouts.append(finish_line)
            continue
        if _COUNTERBORE.search(line):
            if _DIAMETER.search(line) or "⌴" in line:
                features.append(_round_feature("counterbore", line))
            else:
                described = describe_symbol("counterbore")
                callouts.append(
                    {
                        "symbol": described["id"],
                        "text": "COUNTERBORE",
                        "feature": False,
                        "meaning": described["meaning"],
                        "citation": described["citation"],
                        "note": (
                            "The word COUNTERBORE was read. The line has no "
                            "counterbore symbol and no counterbore diameter. "
                            "No counterbore operation was added."
                        ),
                    }
                )
            continue
        if _COUNTERSINK.search(line):
            feature = _countersink_text_feature(line)
            if feature is not None:
                features.append(feature)
            else:
                described = describe_symbol("countersink")
                callouts.append(
                    {
                        "symbol": described["id"],
                        "text": "COUNTERSINK",
                        "feature": False,
                        "meaning": described["meaning"],
                        "citation": described["citation"],
                        "note": (
                            "The word COUNTERSINK was read. The line has no "
                            "countersink symbol and no countersink diameter. "
                            "No countersink operation was added."
                        ),
                    }
                )
            continue
        if _CHAMFER_WORD.search(line):
            features.append(_chamfer_feature(line))
            continue
        if _HOLE_PROCESS.search(line) and _DIAMETER.search(line):
            features.append(_hole_feature(line))
            continue
        found_diameter = _DIAMETER.search(line)
        if found_diameter:
            token = found_diameter.group(0)
            glyph = token[0] if token[:1] in {"⌀", "Ø", "∅"} else "DIA"
            described = describe_symbol(glyph)
            value = _diameter_value(line)
            callouts.append(
                {
                    "symbol": "diameter",
                    "text": line,
                    "value": value,
                    "meaning": described["meaning"],
                    "citation": described["citation"],
                    "feature": False,
                    "note": (
                        "Diameter was read. The file does not say this is a hole — "
                        "no hole feature was added."
                    ),
                }
            )
            unreadable.append(
                "Diameter was read. The file does not say this is a hole — "
                "no hole feature was added."
            )
            continue
        radius = _RADIUS.search(line)
        if radius:
            prefix = re.match(r"[A-Za-z]+", radius.group(0))
            described = describe_symbol(prefix.group(0) if prefix else radius.group(0))
            callouts.append(
                {
                    "symbol": described["id"],
                    "text": radius.group(0),
                    "value": _num(radius.group(1)),
                    "meaning": described["meaning"],
                    "citation": described["citation"],
                    "feature": False,
                    "note": "Radius was read. It was not added as a machining operation.",
                }
            )
            continue
        described_line = describe_symbol(line)
        if described_line.get("id") == "iso_fit" and isinstance(described_line.get("size"), float):
            token = f"{described_line['deviation']}{described_line['grade']}"
            callouts.append(
                {
                    "symbol": described_line["id"],
                    "text": line,
                    "value": described_line["size"],
                    "diameter_mm": described_line["size"],
                    "fit": token,
                    "applies_to": described_line.get("applies_to"),
                    "meaning": described_line["meaning"],
                    "citation": described_line["citation"],
                    "feature": False,
                    "note": (
                        "Diameter and ISO fit were read. The line does not say hole, "
                        "drill, ream, or bore — no hole feature was added. "
                        "Fit limits were not calculated."
                    ),
                }
            )
            continue
        if described_line.get("id") == "plus_minus":
            value = described_line.get("nominal")
            if value is None:
                value = described_line.get("tolerance")
            row = {
                "symbol": described_line["id"],
                "text": line,
                "value": value,
                "feature": False,
                "meaning": described_line["meaning"],
                "citation": described_line["citation"],
                "note": (
                    "A size and a plus-minus value were read. "
                    "They were not added as an operation."
                ),
            }
            if described_line.get("plus_value") is not None:
                row["plus_value"] = described_line["plus_value"]
                row["minus_value"] = described_line["minus_value"]
            callouts.append(row)
            continue
        if (
            described_line.get("id") == "degree"
            and isinstance(described_line.get("angle_deg"), float)
        ):
            callouts.append(
                {
                    "symbol": described_line["id"],
                    "text": line,
                    "value": described_line["angle_deg"],
                    "feature": False,
                    "meaning": described_line["meaning"],
                    "citation": described_line["citation"],
                    "note": "An angle was read. It was not added as an operation.",
                }
            )
            continue
        if re.fullmatch(r"ZINC\s+PLATE", line, re.IGNORECASE):
            callouts.append(
                {
                    "symbol": None,
                    "text": "ZINC PLATE",
                    "feature": False,
                    "outside_process": True,
                    "meaning": None,
                    "citation": None,
                    "note": (
                        "Zinc plate is the finish. It is an outside process, "
                        "not a shop machine operation."
                    ),
                }
            )
            continue
        fraction = re.fullmatch(r"(\d+)\s*/\s*(\d+)", line)
        if fraction:
            callouts.append(
                {
                    "symbol": None,
                    "text": line,
                    "value": _num(f"{fraction.group(1)}/{fraction.group(2)}"),
                    "feature": False,
                    "meaning": None,
                    "citation": None,
                    "note": (
                        "A fraction dimension was read. "
                        "It was not added as an operation."
                    ),
                }
            )
            continue
        mixed = re.fullmatch(r"(\d+)\s+(\d+)", line)
        if (
            mixed
            and index < len(lines)
            and re.fullmatch(r"\d{1,2}", lines[index])
            and lines[index] != "0"
        ):
            denominator = lines[index]
            index += 1
            whole = int(mixed.group(1))
            numerator = int(mixed.group(2))
            callouts.append(
                {
                    "symbol": None,
                    "text": f"{whole} {numerator}/{denominator}",
                    "value": whole + (numerator / int(denominator)),
                    "feature": False,
                    "meaning": None,
                    "citation": None,
                    "note": (
                        "A dimension was read. "
                        "It was not added as an operation."
                    ),
                }
            )
            continue
        if re.fullmatch(r"\d{1,2}", line):
            callouts.append(
                {
                    "symbol": None,
                    "text": line,
                    "value": _num(line),
                    "feature": False,
                    "meaning": None,
                    "citation": None,
                    "note": (
                        "Dimension was read. The file does not say this is a hole — "
                        "no hole feature was added."
                    ),
                }
            )
    joined = " ".join(lines)
    tapped = re.search(
        r"TAPPED\s+HOLE\s+IN\s+(\d+)\s+TO\s+ALIGN\s+WITH\s+DRILLED\s+"
        r"HOLE\s+CENTERLINE\s+IN\s+(\d+)",
        joined,
        re.IGNORECASE,
    )
    if tapped:
        item_tapped = tapped.group(1)
        item_drilled = tapped.group(2)
        callouts.append(
            {
                "symbol": None,
                "text": (
                    f"TAPPED HOLE IN {item_tapped} / "
                    f"DRILLED HOLE IN {item_drilled}"
                ),
                "feature": False,
                "requires_machining": True,
                "meaning": None,
                "citation": None,
                "note": (
                    f"The sheet says a tapped hole in item {item_tapped} and a "
                    f"drilled hole in item {item_drilled}. It does not give a "
                    "diameter or a thread designation, and it does not say "
                    "lathe, mill, drill, tap, or single-point. "
                    "No operation was added."
                ),
            }
        )
    return features, callouts, unreadable


def _attach_tap_note(feature: dict[str, Any], lines: list[str], thread_index: int) -> int:
    """Keep a stated drill and hole count on the tap. Do not name an unlabeled number depth."""
    if feature.get("thread_form") != "tap":
        return thread_index + 1
    unlabeled: list[str] = []
    index = thread_index + 1
    while index < len(lines) and index <= thread_index + 4:
        nxt = lines[index]
        drill = _DRILL_SIZE.search(nxt)
        hole = _HOLE_QTY.search(nxt)
        if _LONE_DECIMAL.fullmatch(nxt):
            unlabeled.append(nxt)
            index += 1
            continue
        if drill:
            value = _num(drill.group(1))
            if value is not None:
                feature.setdefault("dimensions", {})["drill_diameter_mm"] = value
            feature["drill_callout"] = nxt
            index += 1
            continue
        if hole:
            feature.setdefault("dimensions", {})["count"] = int(hole.group(1))
            feature["hole_callout"] = nxt
            number = re.search(r"\d+(?:\.\d+)?", nxt)
            if number and number.group(0) != hole.group(1):
                unlabeled.append(number.group(0))
            index += 1
            continue
        break
    feature["blank_fields"] = [
        row for row in feature.get("blank_fields") or [] if row["field"] != "count"
    ]
    if unlabeled:
        shown = " and ".join(unlabeled)
        verb = "are" if len(unlabeled) > 1 else "is"
        feature["blank_fields"].append(
            _blank(
                "depth_in",
                f"{shown} {verb} on the tap note. "
                "The line does not say depth — depth left blank.",
            )
        )
    return index


def _places(line: str) -> tuple[int | None, list[dict[str, str]]]:
    count = _COUNT.search(line)
    if count:
        return int(count.group(1)), []
    if re.search(r"\bTYP\b|\bTYPICAL\b", line, re.IGNORECASE):
        return None, [
            _blank(
                "count",
                "TYP does not state a count — count left blank.",
            )
        ]
    return None, []


def _depth_fields(line: str) -> tuple[dict[str, Any], list[dict[str, str]]]:
    depth = _DEPTH.search(line)
    if depth:
        value = _num(depth.group(1))
        if value is None:
            return {}, [_blank("depth_in", "Depth symbol is present. The value was not read — left blank.")]
        return {"depth_in": value}, []
    if _THRU.search(line):
        return {}, [
            _blank(
                "depth_in",
                "THRU is on the callout. Numeric depth was not given — depth left blank.",
            )
        ]
    return {}, [_blank("depth_in", "Depth is not in the callout — left blank.")]


def _hole_feature(line: str) -> dict[str, Any]:
    diameter = _diameter_value(line)
    process = _HOLE_PROCESS.search(line).group(1).casefold()
    tolerance = {"drill": "drill", "ream": "ream", "bore": "bore"}[process]
    count, count_blanks = _places(line)
    depths, depth_blanks = _depth_fields(line)
    dimensions: dict[str, Any] = {}
    blanks = list(count_blanks)
    if diameter is None:
        blanks.append(_blank("diameter_in", "Diameter symbol is present. The value was not read — left blank."))
    else:
        dimensions["diameter_in"] = diameter
    dimensions.update(depths)
    if count is not None:
        dimensions["count"] = count
    blanks.extend(depth_blanks)
    return _feature("hole", line, tolerance=tolerance, dimensions=dimensions, blank_fields=blanks)


def _round_feature(kind: str, line: str) -> dict[str, Any]:
    found = _DIAMETER.search(line)
    dimensions: dict[str, Any] = {}
    blanks: list[dict[str, str]] = []
    if found:
        value = _diameter_value(line)
        if value is None:
            blanks.append(_blank("diameter_in", "Diameter was not read — left blank."))
        else:
            dimensions["diameter_in"] = value
    else:
        blanks.append(_blank("diameter_in", "Diameter is not in the callout — left blank."))
    depths, depth_blanks = _depth_fields(line)
    dimensions.update(depths)
    blanks.extend(depth_blanks)
    return _feature(kind, line, dimensions=dimensions, blank_fields=blanks)


def _thread_feature(line: str, unified: re.Match[str] | None, metric: re.Match[str] | None) -> dict[str, Any]:
    dimensions: dict[str, Any] = {}
    blanks = [
        _blank(
            "thread_form",
            "Thread process is not in the designation — form left blank.",
        )
    ]
    count, count_blanks = _places(line)
    blanks.extend(count_blanks)
    if count is not None:
        dimensions["count"] = count
    extra: dict[str, Any] = {}
    if re.search(r"\bTAP\b", line, re.IGNORECASE):
        extra["thread_form"] = "tap"
        blanks = [row for row in blanks if row["field"] != "thread_form"]
    elif re.search(r"\bSINGLE[\s-]*POINT\b", line, re.IGNORECASE):
        extra["thread_form"] = "single_point"
        blanks = [row for row in blanks if row["field"] != "thread_form"]
    if unified:
        if unified.group(1) and unified.group(2):
            major = _num(f"{unified.group(1)}/{unified.group(2)}")
        else:
            major = _num(unified.group(3))
        if major is None:
            blanks.append(_blank("diameter_in", "Thread major diameter was not read — left blank."))
        else:
            dimensions["diameter_in"] = major
        extra["threads_per_inch"] = int(unified.group(4))
        extra["series"] = unified.group(5).upper()
        extra["thread_class"] = (unified.group(6) or "").upper() or None
        if extra["thread_class"] is None:
            blanks.append(_blank("thread_class", "Thread class is not in the designation — left blank."))
    else:
        assert metric is not None
        dimensions["major_diameter_mm"] = _num(metric.group(1))
        extra["pitch_mm"] = _num(metric.group(2))
        blanks.append(
            _blank(
                "diameter_in",
                "Metric designation is in millimetres. Inch diameter left blank.",
            )
        )
        letter = re.search(r"\b([A-Z])\s+TAP\b", line)
        if letter:
            extra["thread_class"] = letter.group(1)
            blanks.append(
                _blank(
                    "thread_grade",
                    "The line says the letter "
                    f"{letter.group(1)}. It does not say a grade — grade left blank.",
                )
            )
        if re.search(r"\bISO\b", line, re.IGNORECASE):
            extra["thread_standard"] = "ISO"
    machine, machine_blanks = _machine_from_line(line)
    if machine.get("stated_machine") is True:
        extra.update(machine)
        blanks.extend(machine_blanks)
    elif extra.get("thread_form"):
        # Tap, thread mill, and single-point do not name the machine.
        extra["stated_machine"] = False
        blanks.append(
            _blank(
                "machine",
                "The line does not say lathe, mill, or lathe 2 — machine left blank.",
            )
        )
    return _feature("thread", line, dimensions=dimensions, blank_fields=blanks, **extra)


def _groove_feature(line: str, match: re.Match[str]) -> dict[str, Any]:
    dimensions: dict[str, Any] = {}
    blanks: list[dict[str, str]] = []
    width = _num(match.group(1))
    depth = _num(match.group(2))
    if width is None:
        blanks.append(_blank("width_in", "Groove width is not in the callout — left blank."))
    else:
        dimensions["width_in"] = width
    if depth is None:
        blanks.append(_blank("depth_in", "Groove depth is not in the callout — left blank."))
    else:
        dimensions["depth_in"] = depth
    blanks.append(
        _blank(
            "machine",
            "The line does not say Lathe or Lathe 2 — machine left blank.",
        )
    )
    return _feature("groove", line, dimensions=dimensions, blank_fields=blanks)


def _machine_from_line(line: str) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Mill, lathe, or lathe 2 only when the line writes that word.

    Drill, tap, ream, bore, and single-point do not choose a machine.
    """
    match = _MACHINE_WORD.search(line)
    if not match:
        return {"stated_machine": False}, [
            _blank(
                "machine",
                "The sheet does not say lathe, mill, drill, tap, or single-point — "
                "machine left blank.",
            )
        ]
    token = re.sub(r"\s+", "", match.group(1)).casefold()
    machine = {"lathe2": "lathe2", "lathe": "lathe"}.get(token, "mill")
    return {"machine": machine, "stated_machine": True}, []


def _chamfer_feature(line: str) -> dict[str, Any]:
    described = describe_symbol(line)
    if described.get("id") != "chamfer":
        described = describe_symbol("CHAMFER")
    degree = describe_symbol("°")
    machine, blanks = _machine_from_line(line)
    dimensions: dict[str, Any] = {}
    if described.get("angle_deg") is not None:
        dimensions["angle_deg"] = described["angle_deg"]
    else:
        blanks.append(_blank("angle_deg", "Chamfer angle is not in the note — left blank."))
    if described.get("size_in") is not None:
        dimensions["size_in"] = described["size_in"]
    else:
        blanks.append(_blank("size_in", "Chamfer size is not in the note — left blank."))
    extra: dict[str, Any] = {
        "dimensions": dimensions,
        "blank_fields": blanks,
        "meaning": described["meaning"],
        "citation": described["citation"],
    }
    extra.update(machine)
    if described.get("angle_deg") is not None:
        extra["angle_meaning"] = degree["meaning"]
        extra["angle_citation"] = degree["citation"]
    if machine.get("stated_machine") is False:
        extra["note"] = "The word CHAMFER was read. No operation code was added."
    return _feature("chamfer", line, **extra)


def _countersink_text_feature(line: str) -> dict[str, Any] | None:
    """The word or the symbol with a diameter or an included angle.

    The word alone, with no symbol and no size, stays a callout.
    """
    described = describe_symbol(line)
    has_pattern = (
        described.get("id") == "countersink"
        and (
            described.get("countersink_diameter_in") is not None
            or described.get("angle_deg") is not None
            or "⌵" in line
        )
    )
    if not has_pattern and "⌵" in line:
        described = describe_symbol("countersink")
        has_pattern = True
    if not has_pattern:
        return None
    degree = describe_symbol("°")
    machine, blanks = _machine_from_line(line)
    dimensions: dict[str, Any] = {}
    if described.get("countersink_diameter_in") is not None:
        dimensions["countersink_diameter_in"] = described["countersink_diameter_in"]
    else:
        blanks.append(
            _blank("countersink_diameter_in", "Countersink diameter was not read — left blank.")
        )
    if described.get("angle_deg") is not None:
        dimensions["angle_deg"] = described["angle_deg"]
    else:
        blanks.append(_blank("angle_deg", "Countersink angle was not read — left blank."))
    count, count_blanks = _places(line)
    if count is not None:
        dimensions["count"] = count
    blanks.extend(count_blanks)
    if _THRU.search(line):
        blanks.append(
            _blank(
                "depth_in",
                "THRU is on the callout. Numeric depth was not given — depth left blank.",
            )
        )
    extra: dict[str, Any] = {
        "dimensions": dimensions,
        "blank_fields": blanks,
        "meaning": described["meaning"],
        "citation": described["citation"],
    }
    extra.update(machine)
    if described.get("angle_deg") is not None:
        extra["angle_meaning"] = degree["meaning"]
        extra["angle_citation"] = degree["citation"]
    if machine.get("stated_machine") is False:
        if (
            described.get("countersink_diameter_in") is not None
            and described.get("angle_deg") is not None
        ):
            extra["note"] = (
                "Countersink was read from the note. "
                "X between the diameter and the degree is BY. "
                "No operation code was added."
            )
        else:
            extra["note"] = (
                "Countersink was read from the note. No operation code was added."
            )
    return _feature("countersink", line, **extra)


def _plate_feature(line: str, match: re.Match[str]) -> dict[str, Any]:
    thickness = _num(match.group(1))
    dimensions: dict[str, Any] = {}
    blanks: list[dict[str, str]] = []
    if thickness is None:
        blanks.append(_blank("thickness_in", "Plate thickness was not read — left blank."))
    else:
        dimensions["thickness_in"] = thickness
    return _feature("plate", line, dimensions=dimensions, blank_fields=blanks)


def _step_floats(blob: str) -> list[float]:
    return [float(token) for token in blob.split(",") if token.strip()]


def _step_geometry(text: str) -> dict[str, Any]:
    if re.search(r"CONVERSION_BASED_UNIT\s*\(\s*'INCH'", text, re.IGNORECASE):
        scale = 1.0
        units = "inch"
    elif "MILLI" in text.upper() and "INCH" not in text.upper():
        scale = 1.0 / 25.4
        units = "millimetre"
    else:
        scale = None
        units = None
    entities = {
        int(match.group(1)): match.group(2)
        for match in _STEP_ENTITY.finditer(text)
    }
    points: dict[int, list[float]] = {}
    directions: dict[int, list[float]] = {}
    axes: dict[int, tuple[int, int]] = {}
    for eid, body in entities.items():
        point = _STEP_POINT.search(body)
        if point and scale is not None:
            vals = _step_floats(point.group(1))
            if len(vals) >= 3:
                points[eid] = [vals[0] * scale, vals[1] * scale, vals[2] * scale]
        direction = _STEP_DIR.search(body)
        if direction:
            vals = _step_floats(direction.group(1))
            if len(vals) >= 3:
                directions[eid] = vals[:3]
        axis = _STEP_AXIS.search(body)
        if axis:
            axes[eid] = (int(axis.group(1)), int(axis.group(2)))
    cylinders = []
    for match in _STEP_CYLINDER.finditer(text):
        radius = float(match.group(2))
        radius_in = None if scale is None else radius * scale
        row: dict[str, Any] = {
            "radius_file": radius,
            "radius_in": radius_in,
            "diameter_in": None if radius_in is None else radius_in * 2.0,
        }
        placement = axes.get(int(match.group(1)))
        if placement:
            origin = points.get(placement[0])
            direction = directions.get(placement[1])
            if origin:
                row["axis_origin_in"] = origin
            if direction:
                row["axis_direction"] = direction
        cylinders.append(row)
    circles = []
    for kind, raw in _STEP_RADIUS.findall(text):
        if kind.upper().startswith("CYLINDRICAL"):
            continue
        radius = float(raw)
        radius_in = None if scale is None else radius * scale
        circles.append(
            {
                "radius_file": radius,
                "radius_in": radius_in,
                "diameter_in": None if radius_in is None else radius_in * 2.0,
            }
        )
    return {
        "units": units,
        "cylinders": cylinders,
        "circles": circles,
        "plane_count": len(_PLANE.findall(text)),
        "vertex_box_in": _vertex_box_in(points, entities),
        "note": _PLANE_NOTE,
    }


def _vertex_box_in(
    points: dict[int, list[float]],
    entities: dict[int, str],
) -> list[float] | None:
    """Sorted length, width, thickness from VERTEX_POINT only.

    A zero span means the vertices are a revolved profile, not a plate.
    """
    coords = []
    for body in entities.values():
        found = _STEP_VERTEX.search(body)
        if not found:
            continue
        point = points.get(int(found.group(1)))
        if point:
            coords.append(point)
    if len(coords) < 2:
        return None
    spans = []
    for axis in range(3):
        values = [point[axis] for point in coords]
        spans.append(max(values) - min(values))
    if min(spans) < _PROFILE_SPAN_IN:
        return None
    return sorted(spans, reverse=True)


def _fmt_in(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _cluster_diameters(values: list[float]) -> list[float]:
    """One entry per finished diameter. Pairs inside 0.001 in are one size."""
    ordered = sorted(value for value in values if isinstance(value, float))
    groups: list[list[float]] = []
    for value in ordered:
        if not groups or value - groups[-1][-1] > _DIAMETER_CLUSTER_IN:
            groups.append([value])
        else:
            groups[-1].append(value)
    return [max(group) for group in groups]


def _unit_direction(values: list[float]) -> tuple[float, float, float] | None:
    mag = (values[0] ** 2 + values[1] ** 2 + values[2] ** 2) ** 0.5
    if mag < 1e-12:
        return None
    return (values[0] / mag, values[1] / mag, values[2] / mag)


def _axes_share_one_centerline(rows: list[dict[str, Any]]) -> bool:
    """True when every cylinder axis is the same line.

    Parallel hole axes spaced across a plate are not this. A turned OD and
    the bore inside it are.
    """
    placed = []
    for row in rows:
        origin = row.get("axis_origin_in")
        direction = row.get("axis_direction")
        if not origin or not direction or len(origin) < 3 or len(direction) < 3:
            return False
        unit = _unit_direction(direction)
        if unit is None:
            return False
        placed.append((origin, unit))
    if len(placed) < 2:
        return False
    origin, direction = placed[0]
    for other_origin, other_direction in placed[1:]:
        aligned = abs(
            direction[0] * other_direction[0]
            + direction[1] * other_direction[1]
            + direction[2] * other_direction[2]
        )
        if aligned < 0.99:
            return False
        delta = (
            other_origin[0] - origin[0],
            other_origin[1] - origin[1],
            other_origin[2] - origin[2],
        )
        cross = (
            delta[1] * direction[2] - delta[2] * direction[1],
            delta[2] * direction[0] - delta[0] * direction[2],
            delta[0] * direction[1] - delta[1] * direction[0],
        )
        distance = (cross[0] ** 2 + cross[1] ** 2 + cross[2] ** 2) ** 0.5
        if distance > _AXIS_TOL_IN:
            return False
    return True


def _sheet_claims_machining(
    features: list[dict[str, Any]],
    callouts: list[dict[str, Any]],
) -> bool:
    if any(feature.get("kind") in _PROCESS_KINDS for feature in features):
        return True
    return any(
        callout.get("requires_machining") or callout.get("symbol") == "diameter"
        for callout in callouts
    )


def _one_machined_part(assembly: dict[str, Any] | None) -> bool:
    """An assembly of several leaves is not one turned or milled part."""
    leaves = list((assembly or {}).get("leaf_parts") or [])
    return len(leaves) <= 1


def _plate_box(geometry: dict[str, Any]) -> list[float] | None:
    box = geometry.get("vertex_box_in")
    if not isinstance(box, list) or len(box) < 3:
        return None
    length, width, thick = (float(box[0]), float(box[1]), float(box[2]))
    if thick < _PROFILE_SPAN_IN or width <= 0:
        return None
    if thick > _PLATE_THICK_MAX_IN:
        return None
    if thick / width > _PLATE_THIN_RATIO:
        return None
    return [length, width, thick]


_BAR_WORD = re.compile(
    r"\b(?:RD\.?\s*BAR|ROUND\s+BAR|BAR\s+ROUND|FLAT\s+BAR|BAR)\b",
    re.IGNORECASE,
)
_TUBE_WORD = re.compile(r"\bTUB(?:E|ING)\b", re.IGNORECASE)
_PLATE_WORD = re.compile(r"\bPLATE\b", re.IGNORECASE)
_ZINC_PLATE = re.compile(r"\bZINC\s+PLATE\b", re.IGNORECASE)
_UNKNOWN_STOCK = {
    "form": "unknown",
    "stated": False,
    "guessed": False,
    "evidence": "The sheet does not state bar, plate, or tube.",
}


def _stated_number(token: str | None) -> float | None:
    return _num(token)


def _unique_sizes(values: list[float]) -> list[float]:
    kept: list[float] = []
    for value in values:
        if any(abs(value - prior) <= _DIAMETER_CLUSTER_IN for prior in kept):
            continue
        kept.append(value)
    return kept


def read_stated_stock(text: str | None) -> dict[str, Any]:
    """Stock form the sheet or title block writes: bar, plate, tube, or unknown.

    A size is kept only when the same stock words state it. The finished
    solid is not a source. ``guessed`` is always false.
    """
    if not text or not str(text).strip():
        return dict(_UNKNOWN_STOCK)
    lines: list[str] = []
    for raw in str(text).splitlines():
        line = " ".join(raw.split())
        if not line or _ZINC_PLATE.fullmatch(line):
            continue
        line = _ZINC_PLATE.sub("", line).strip()
        if line:
            lines.append(line)
    blob = "\n".join(lines)
    forms: list[str] = []
    if _BAR_WORD.search(blob):
        forms.append("bar")
    if _TUBE_WORD.search(blob):
        forms.append("tube")
    if _PLATE_WORD.search(blob):
        forms.append("plate")
    if len(forms) != 1:
        return dict(_UNKNOWN_STOCK)
    form = forms[0]
    word = {"bar": _BAR_WORD, "tube": _TUBE_WORD, "plate": _PLATE_WORD}[form]
    quotes = [line for line in lines if word.search(line)]
    stock: dict[str, Any] = {
        "form": form,
        "stated": True,
        "guessed": False,
        "evidence": " ".join(quotes),
    }
    if form == "plate":
        thickness = _stated_plate_thickness(blob)
        if thickness is not None:
            stock["thickness_in"] = thickness
        for line in lines:
            if line in quotes:
                continue
            if re.search(r"(?i)A\s*572|\bW:\s*[0-9]", line):
                quotes.append(line)
        stock["evidence"] = " ".join(quotes)
    else:
        diameter = _stated_round_diameter(blob)
        if diameter is not None:
            stock["diameter_in"] = diameter
    return stock


def _stated_plate_thickness(blob: str) -> float | None:
    """Thickness written with the plate words. Not a finished envelope."""
    found: list[float] = []
    patterns = (
        rf"\bPLATE\s+{_NUMBER}\s*(?:IN(?:CH)?\s*)?THK\b",
        rf"{_NUMBER}\s*[\"″]\s*(?:HR\s+)?PLATE\b",
        rf"\bW:\s*{_NUMBER}\s*[\"″]",
        rf"(?<![\d.]){_NUMBER}\s*[\"″]\s*A\s*572\b",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, blob, re.IGNORECASE):
            value = _stated_number(match.group(1))
            if value is not None:
                found.append(value)
    sizes = _unique_sizes(found)
    if len(sizes) == 1:
        return sizes[0]
    return None


def _stated_round_diameter(blob: str) -> float | None:
    """Diameter written on the bar or tube line. A bare finished size is not stock."""
    found: list[float] = []
    patterns = (
        rf"(?:⌀|Ø|∅)\s*{_NUMBER}\s*(?:DIA(?:METER)?)?\s*(?:ROUND\s+|RD\.?\s+|FLAT\s+)?(?:BAR|TUB(?:E|ING))\b",
        rf"\b(?:ROUND\s+BAR|RD\.?\s*BAR|BAR\s+ROUND|FLAT\s+BAR|BAR|TUB(?:E|ING))\b"
        rf"[^\n]{{0,40}}?(?:⌀|Ø|∅|\bDIA(?:METER)?\b)\s*{_NUMBER}",
        rf"{_NUMBER}\s*[\"″]\s*(?:DIA(?:METER)?\s*)?(?:ROUND\s+|RD\.?\s+)?(?:BAR|TUB(?:E|ING))\b",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, blob, re.IGNORECASE):
            value = _stated_number(match.group(1))
            if value is not None:
                found.append(value)
    sizes = _unique_sizes(found)
    if len(sizes) == 1:
        return sizes[0]
    return None


def _accept_stated_stock(stated: dict[str, Any] | None) -> dict[str, Any]:
    """Drop a stock record that was not taken from the sheet."""
    if not isinstance(stated, dict):
        return dict(_UNKNOWN_STOCK)
    if stated.get("guessed") is True or stated.get("stated") is not True:
        return dict(_UNKNOWN_STOCK)
    form = str(stated.get("form") or "").casefold()
    if form not in {"bar", "plate", "tube"}:
        return dict(_UNKNOWN_STOCK)
    out: dict[str, Any] = {
        "form": form,
        "stated": True,
        "guessed": False,
        "evidence": str(stated.get("evidence") or form),
    }
    if form == "plate" and isinstance(stated.get("thickness_in"), (int, float)) and not isinstance(
        stated.get("thickness_in"), bool
    ):
        out["thickness_in"] = float(stated["thickness_in"])
    if form in {"bar", "tube"} and isinstance(stated.get("diameter_in"), (int, float)) and not isinstance(
        stated.get("diameter_in"), bool
    ):
        out["diameter_in"] = float(stated["diameter_in"])
    return out


def _hole_features(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        feature
        for feature in features
        if feature.get("kind") in {"hole", "countersink", "counterbore"}
        or feature.get("thread_form") in {"tap", "thread_mill"}
    ]


def _finished_shape(
    geometry: dict[str, Any],
    features: list[dict[str, Any]],
    cylinders: list[dict[str, Any]],
    distinct: list[float],
) -> dict[str, Any]:
    """Finished solid from the STEP file. This is not starting stock."""
    box = _plate_box(geometry)
    axes_known = bool(cylinders) and all(
        row.get("axis_direction") and row.get("axis_origin_in") for row in cylinders
    )
    concentric = bool(
        axes_known and len(cylinders) >= 2 and _axes_share_one_centerline(cylinders)
    )
    holes = _hole_features(features)
    if box and not concentric:
        shape = "plate"
    elif distinct and (
        concentric or (box is None and not holes and len(distinct) >= 2)
    ):
        shape = "round"
    else:
        shape = "unknown"
    finished: dict[str, Any] = {
        "shape": shape,
        "diameters_in": distinct,
        "concentric": concentric,
    }
    if box:
        finished["envelope_in"] = box
    if not axes_known and shape == "round":
        finished["axes_placed"] = False
    return finished


def _diameter_list(geometry: dict[str, Any], diameters: list[float]) -> str:
    if not diameters:
        return "none read"
    if geometry.get("units") == "millimetre":
        return ", ".join(
            f"{_fmt_in(value * 25.4)} mm ({_fmt_in(value)} in)" for value in diameters
        )
    return ", ".join(f"{_fmt_in(value)} in" for value in diameters)


def compare_stock_to_finished(
    geometry: dict[str, Any] | None,
    features: list[dict[str, Any]] | None = None,
    callouts: list[dict[str, Any]] | None = None,
    assembly: dict[str, Any] | None = None,
    stated_stock: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Choose lathe or mill only from stated stock versus the finished part.

    Kyle, 2026-10-02: when the drawing does not name lathe or mill, the
    difference between the starting material and the finished part may
    decide the machining. Shop rates are not part of this comparison.

    Starting stock comes from the sheet or title block: bar, plate, tube,
    or unknown. A size the sheet does not write is left off. The largest
    finished diameter is not used as a bar. A guessed stock record is
    refused.

    Turning is justified when the finished solid is round and smaller than
    a stated round stock. Milling is justified when the finished solid is
    a plate with holes. Lathe 2 is never chosen here. Nothing here writes
    a run time, a setup time, or a dollar rate.

    Several leaf parts are not one machined part. A machine the sheet
    already names is left to the caller.
    """
    features = [row for row in (features or []) if isinstance(row, dict)]
    callouts = [row for row in (callouts or []) if isinstance(row, dict)]
    geometry = geometry or {}
    if any(feature.get("stated_machine") is True for feature in features):
        return None
    if not _one_machined_part(assembly):
        return None
    if not _sheet_claims_machining(features, callouts):
        return None
    cylinders = [
        row
        for row in (geometry.get("cylinders") or [])
        if isinstance(row, dict) and isinstance(row.get("diameter_in"), float)
    ]
    distinct = _cluster_diameters([row["diameter_in"] for row in cylinders])
    stock = _accept_stated_stock(stated_stock)
    finished = _finished_shape(geometry, features, cylinders, distinct)
    holes = _hole_features(features)
    family: str | None = None
    justified = False
    if (
        stock["form"] in {"bar", "tube"}
        and isinstance(stock.get("diameter_in"), float)
        and finished["shape"] == "round"
        and distinct
        and max(distinct) < stock["diameter_in"] - _DIAMETER_CLUSTER_IN
    ):
        family = "lathe"
        justified = True
        difference = (
            "The finished round is smaller than the stated round stock, "
            "so the difference is turning."
        )
    elif finished["shape"] == "plate" and holes:
        family = "mill"
        justified = True
        kinds = ", ".join(dict.fromkeys(feature.get("kind") or "feature" for feature in holes))
        difference = (
            f"The finished part is a plate with {kinds}. "
            "That difference is milling, not turning."
        )
    else:
        difference = (
            "The stated stock and the finished solid do not justify turning or milling. "
            "Turning needs a finished round smaller than a stated round stock. "
            "Milling needs a finished plate with holes."
        )
    shown = _diameter_list(geometry, distinct)
    if stock["form"] == "unknown":
        stock_sentence = (
            "The sheet does not state bar, plate, or tube. "
            "Stock is unknown. A bar size was not guessed."
        )
    else:
        stock_sentence = f"The sheet states {stock['form']} stock"
        if "thickness_in" in stock:
            stock_sentence += f" {_fmt_in(stock['thickness_in'])} in thick"
        if "diameter_in" in stock:
            stock_sentence += f" {_fmt_in(stock['diameter_in'])} in round"
        quote = stock.get("evidence") or ""
        if quote:
            stock_sentence += f" ({quote})"
        stock_sentence += "."
    if finished["concentric"]:
        shape_sentence = (
            "The finished solid is round. "
            "The cylinder axes in the STEP file are one centerline."
        )
    elif finished["shape"] == "round":
        shape_sentence = (
            "The finished solid is round. "
            "The STEP file does not place the cylinder axes."
        )
    elif finished["shape"] == "plate":
        length, width, thick = finished["envelope_in"]
        shape_sentence = (
            f"The finished solid is a plate {_fmt_in(length)} x {_fmt_in(width)} x "
            f"{_fmt_in(thick)} in."
        )
    else:
        shape_sentence = "The finished solid was not classified as a round or a plate."
    if justified and family == "lathe":
        decision = "The family is lathe. Lathe 2 was not chosen."
    elif justified and family == "mill":
        decision = "The family is mill. Lathe 2 was not chosen."
    else:
        decision = "No operation was justified. Lathe 2 was not chosen."
    evidence = (
        "The sheet does not name mill, lathe, or lathe 2. "
        f"{stock_sentence} {shape_sentence} "
        f"Finished diameters are {shown}. {difference} {decision} "
        "This comparison does not supply a run time or a setup time."
    )
    return {
        "family": family,
        "stated_on_sheet": False,
        "operation_justified": justified,
        "stock": stock,
        "finished": finished,
        "difference": difference,
        "evidence": evidence,
    }


def _apply_process_from_stock(
    features: list[dict[str, Any]],
    assignment: dict[str, Any] | None,
) -> None:
    """Fill a machine the sheet left blank. Do not mark it as written on the sheet."""
    if not assignment or assignment.get("operation_justified") is not True:
        return
    family = assignment.get("family")
    evidence = assignment.get("evidence") or ""
    if family not in {"lathe", "mill"}:
        return
    for feature in features:
        if feature.get("kind") not in _PROCESS_KINDS:
            continue
        if feature.get("stated_machine") is True or feature.get("machine"):
            continue
        feature["machine"] = family
        feature["machine_source"] = "stock_vs_finished"
        feature["process_evidence"] = evidence
        note = str(feature.get("note") or "")
        if "No operation code was added" in note:
            feature["note"] = (
                "The sheet does not name mill, lathe, or lathe 2. "
                f"Stock versus finished geometry assigns {family}. "
                "No cycle time was calculated."
            )


def _cylinder_inches(geometry: dict[str, Any]) -> list[float]:
    return [
        row["diameter_in"]
        for row in (geometry.get("cylinders") or [])
        if isinstance(row.get("diameter_in"), float)
    ]


def _inch_hits(wanted_in: float, diameters: list[float]) -> list[float]:
    return [dia for dia in diameters if abs(dia - wanted_in) <= _DIAMETER_GAP_IN]


def _match_step(features: list[dict[str, Any]], geometry: dict[str, Any]) -> None:
    diameters = _cylinder_inches(geometry)
    millimetre = geometry.get("units") == "millimetre"
    for feature in features:
        dims = feature.get("dimensions") or {}
        wanted = dims.get("diameter_in")
        if isinstance(wanted, (int, float)):
            hits = _inch_hits(float(wanted), diameters)
            if hits:
                feature["step_match"] = {
                    "diameter_in": hits[0],
                    "matches": len(hits),
                    "note": (
                        "A STEP cylindrical diameter matches this callout. "
                        "It was not added as a second feature."
                    ),
                }
        if not millimetre:
            continue
        for key, label in (
            ("major_diameter_mm", "major diameter"),
            ("drill_diameter_mm", "drill diameter"),
        ):
            mm = dims.get(key)
            if not isinstance(mm, (int, float)):
                continue
            hits = _inch_hits(float(mm) / 25.4, diameters)
            if not hits:
                continue
            slot = "step_match" if key == "major_diameter_mm" else "drill_step_match"
            feature[slot] = {
                "diameter_mm": float(mm),
                "matches": len(hits),
                "note": (
                    f"A STEP cylindrical diameter matches this {label}. "
                    "It was not added as a second feature."
                ),
            }


def _match_step_callouts(callouts: list[dict[str, Any]], geometry: dict[str, Any]) -> None:
    if geometry.get("units") != "millimetre":
        return
    diameters = _cylinder_inches(geometry)
    for callout in callouts:
        if callout.get("symbol") == "diameter" and callout.get("unit") == "inch":
            value = callout.get("value")
            if isinstance(value, (int, float)):
                hits = _inch_hits(float(value), diameters)
                if hits:
                    closest = min(hits, key=lambda dia: abs(dia - float(value)))
                    callout["step_match"] = {
                        "diameter_in": closest,
                        "matches": len(hits),
                        "note": (
                            "A STEP cylindrical diameter matches this callout. "
                            "It was not added as a feature."
                        ),
                    }
        mm = callout.get("diameter_mm")
        if not isinstance(mm, (int, float)):
            continue
        hits = _inch_hits(float(mm) / 25.4, diameters)
        if not hits:
            continue
        callout["step_match"] = {
            "diameter_mm": float(mm),
            "matches": len(hits),
            "note": (
                "A STEP cylindrical diameter matches this callout. "
                "It was not added as a feature."
            ),
        }


_CALLOUT_WORD = re.compile(r"^(?:\d*\.\d+|\d+X|THRU|THROUGH)$", re.IGNORECASE)
_DEGREE_WORD = re.compile(r"^DEG(?:REES?)?$", re.IGNORECASE)
_DECIMAL_WORD = re.compile(r"^\d*\.\d+$")
_INCH_QUOTED = re.compile(r'^(\d*\.\d+)"$')
_NX_WORD = re.compile(r"^(\d+)X$", re.IGNORECASE)
_MATERIAL_WORD = re.compile(r"^(?:5052(?:-ALUM)?|ALUM|ALUMINUM|ALEDO)$", re.IGNORECASE)
_TOLERANCE_WORD = re.compile(r"DECIMAL|TOLERANCE|ANGULAR|PLACE", re.IGNORECASE)
_PART_WORD = re.compile(r"^BB\d{4}(?:-ASM)?$", re.IGNORECASE)
_RADIUS_WORD = re.compile(r"^(?:SR|CR|R)\d*\.\d+$", re.IGNORECASE)
_STOCK_WORD = re.compile(r"^(?:\.125|\.25|0\.125|0\.25)$")
_SHEET_NO = re.compile(r"SHEET\s+(\d+)\s+OF\s+\d+", re.IGNORECASE)
_CLUSTER_MARGIN = 8.0


def _rect_gap(left: Any, right: Any) -> float:
    dx = 0.0 if left.x0 <= right.x1 and right.x0 <= left.x1 else min(
        abs(left.x0 - right.x1), abs(right.x0 - left.x1)
    )
    dy = 0.0 if left.y0 <= right.y1 and right.y0 <= left.y1 else min(
        abs(left.y0 - right.y1), abs(right.y0 - left.y1)
    )
    return dx + dy


def _grow(rect: Any, margin: float) -> Any:
    return type(rect)(rect.x0 - margin, rect.y0 - margin, rect.x1 + margin, rect.y1 + margin)


def _polyline_diameter_rects(page: Any) -> list[Any]:
    """A diameter mark drawn as short lines around one long slash.

    Some sheets stroke the circle instead of using curve operators.
    """
    import fitz

    found = []
    for drawing in page.get_drawings():
        items = drawing["items"]
        if len(items) < 16 or any(item[0] != "l" for item in items):
            continue
        rect = fitz.Rect(drawing["rect"])
        if not (6 <= rect.width <= 20 and 6 <= rect.height <= 20):
            continue
        size = max(rect.width, rect.height)
        lengths = []
        for item in items:
            start, end = item[1], item[2]
            lengths.append(((end.x - start.x) ** 2 + (end.y - start.y) ** 2) ** 0.5)
        longest = max(lengths)
        middle = sorted(lengths)[len(lengths) // 2]
        if longest < 0.8 * size or middle > 0.25 * size:
            continue
        found.append(rect)
    return found


def _countersink_chevron_rects(page: Any) -> list[Any]:
    """Two lines that meet in a V, the drawn countersink mark."""
    import fitz

    found = []
    for drawing in page.get_drawings():
        items = drawing["items"]
        if len(items) != 2 or any(item[0] != "l" for item in items):
            continue
        first = (items[0][1], items[0][2])
        second = (items[1][1], items[1][2])

        def _near(left: Any, right: Any) -> bool:
            return abs(left.x - right.x) <= 0.6 and abs(left.y - right.y) <= 0.6

        vertex = None
        if _near(first[1], second[0]):
            vertex = first[1]
        elif _near(first[0], second[1]):
            vertex = first[0]
        elif _near(first[0], second[0]):
            vertex = first[0]
        elif _near(first[1], second[1]):
            vertex = first[1]
        if vertex is None:
            continue
        rect = fitz.Rect(drawing["rect"])
        if rect.width < 4 or rect.height < 3 or rect.width > 24 or rect.height > 24:
            continue
        if vertex.y + 0.5 < max(first[0].y, first[1].y, second[0].y, second[1].y):
            continue
        found.append(rect)
    return found


def _countersink_from_sheet(
    words: list[tuple],
    symbols: list[Any],
    chevrons: list[Any],
) -> tuple[set[int], list[dict[str, Any]]]:
    """A countersink mark in front of a diameter, then X and a degree."""
    consumed: set[int] = set()
    features: list[dict[str, Any]] = []
    described = describe_symbol("countersink")
    degree = describe_symbol("°")
    for chevron in chevrons:
        symbol = None
        symbol_gap = None
        for candidate in symbols:
            if candidate.x0 + 1 < chevron.x1:
                continue
            gap = _rect_gap(chevron, candidate)
            if gap > 14:
                continue
            if symbol_gap is None or gap < symbol_gap:
                symbol = candidate
                symbol_gap = gap
        if symbol is None:
            continue
        sink_index = None
        sink_gap = None
        for index, word in enumerate(words):
            if not _DECIMAL_WORD.fullmatch(word[4]):
                continue
            if word[5].x0 + 1 < symbol.x1:
                continue
            gap = _rect_gap(symbol, word[5])
            if gap > 10:
                continue
            if sink_gap is None or gap < sink_gap:
                sink_index = index
                sink_gap = gap
        if sink_index is None:
            continue
        angle_index = None
        saw_by = False
        sink_word = words[sink_index]
        for index, word in enumerate(words):
            if word[5].x0 <= sink_word[5].x1:
                continue
            if _rect_gap(sink_word[5], word[5]) > 28:
                continue
            if word[4].upper() == "X":
                saw_by = True
                continue
            if saw_by and _ANGLE.fullmatch(word[4]):
                angle_index = index
                break
        if angle_index is None:
            continue
        thru_index = None
        for index, word in enumerate(words):
            if index == sink_index or not _DECIMAL_WORD.fullmatch(word[4]):
                continue
            if word[5].y0 >= sink_word[5].y0 - 4:
                continue
            if sink_word[5].y0 - word[5].y0 > 24:
                continue
            if abs(word[5].x0 - sink_word[5].x0) > 20:
                continue
            if not any(
                other[4].upper() in {"THRU", "THROUGH"} and _rect_gap(word[5], other[5]) <= 16
                for other in words
            ):
                continue
            thru_index = index
            break
        count = None
        count_word = sink_word
        if thru_index is not None:
            count_word = words[thru_index]
        for word in words:
            places = _NX_WORD.fullmatch(word[4])
            if not places:
                continue
            if _rect_gap(count_word[5], word[5]) > 36:
                continue
            count = int(places.group(1))
            break
        sink_value = _num(words[sink_index][4])
        angle_value = _num(_ANGLE.fullmatch(words[angle_index][4]).group(1))
        thru_value = _num(words[thru_index][4]) if thru_index is not None else None
        label_parts = []
        if count is not None and thru_value is not None:
            label_parts.append(f"{count}X {words[thru_index][4]} THRU")
        label_parts.append(f"{words[sink_index][4]} X {words[angle_index][4]}")
        dimensions: dict[str, Any] = {}
        blanks = [
            _blank(
                "machine",
                "The sheet does not say lathe, mill, drill, tap, or single-point — "
                "machine left blank.",
            )
        ]
        if thru_value is None:
            blanks.append(_blank("diameter_in", "Thru diameter was not read — left blank."))
        else:
            dimensions["diameter_in"] = thru_value
        if sink_value is None:
            blanks.append(
                _blank("countersink_diameter_in", "Countersink diameter was not read — left blank.")
            )
        else:
            dimensions["countersink_diameter_in"] = sink_value
        if angle_value is None:
            blanks.append(_blank("angle_deg", "Countersink angle was not read — left blank."))
        else:
            dimensions["angle_deg"] = angle_value
        if count is None:
            blanks.append(_blank("count", "Place count was not read — left blank."))
        else:
            dimensions["count"] = count
        if thru_index is not None:
            blanks.append(
                _blank(
                    "depth_in",
                    "THRU is on the callout. Numeric depth was not given — depth left blank.",
                )
            )
        consumed.add(sink_index)
        if thru_index is not None:
            consumed.add(thru_index)
        features.append(
            _feature(
                "countersink",
                " / ".join(label_parts),
                dimensions=dimensions,
                blank_fields=blanks,
                stated_machine=False,
                meaning=described["meaning"],
                citation=described["citation"],
                angle_meaning=degree["meaning"],
                angle_citation=degree["citation"],
                note=(
                    "Countersink symbol was read in front of the diameter. "
                    "X between the diameter and the degree is BY. "
                    "No operation code was added."
                ),
            )
        )
    return consumed, features


def _diameter_symbol_rects(page: Any) -> list[Any]:
    """Circle-and-slash geometry placed as the diameter symbol.

    The symbol is drawn, not typed: a small closed curve and a line through
    it. Genium Drafting Manual Section 6.1 paragraph 2.1 places that symbol
    in front of a diameter value. The line is not required to sit at 45
    degrees in page space — a rotated sheet draws it shallow.
    """
    import fitz

    lines = []
    loops = []
    for drawing in page.get_drawings():
        rect = fitz.Rect(drawing["rect"])
        items = drawing["items"]
        kinds = [item[0] for item in items]
        if (
            6 <= rect.width <= 20
            and 6 <= rect.height <= 20
            and kinds.count("c") >= 2
            and len(items) <= 12
        ):
            loops.append(rect)
        if kinds == ["l"] and len(items) == 1:
            start, end = items[0][1], items[0][2]
            length = ((end.x - start.x) ** 2 + (end.y - start.y) ** 2) ** 0.5
            if 4 <= length <= 30:
                lines.append((rect, length))
    symbols = []
    used: set[int] = set()
    for loop in loops:
        size = max(loop.width, loop.height)
        for index, (rect, length) in enumerate(lines):
            if index in used:
                continue
            if not (0.6 * size <= length <= 1.8 * size):
                continue
            if rect.intersects(_grow(loop, 1.5)):
                symbols.append(loop | rect)
                used.add(index)
                break
    for rect in _polyline_diameter_rects(page):
        if any(_rect_gap(rect, have) <= 1 for have in symbols):
            continue
        symbols.append(rect)
    return symbols


def _cluster_indexes(rects: list[Any], margin: float) -> list[list[int]]:
    parent = list(range(len(rects)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    grown = [_grow(rect, margin) for rect in rects]
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            if grown[i].intersects(grown[j]):
                left, right = find(i), find(j)
                if left != right:
                    parent[right] = left
    groups: dict[int, list[int]] = {}
    for index in range(len(rects)):
        groups.setdefault(find(index), []).append(index)
    return list(groups.values())


def _near_word(rect: Any, words: list[tuple], pattern: re.Pattern[str], margin: float) -> bool:
    for word in words:
        if pattern.search(word[4]) and _grow(rect, margin).intersects(word[5]):
            return True
    return False


def _part_names(words: list[tuple]) -> list[str]:
    seen: list[str] = []
    for word in words:
        if _PART_WORD.fullmatch(word[4]) and word[4] not in seen:
            seen.append(word[4])
    return seen


def _drawing_number(parts_by_page: list[list[str]]) -> str | None:
    counts: dict[str, int] = {}
    for parts in parts_by_page:
        for part in dict.fromkeys(parts):
            counts[part] = counts.get(part, 0) + 1
    if not counts:
        return None
    best = max(counts.values())
    tied = [part for part, count in counts.items() if count == best]
    tied.sort(key=lambda part: (0 if part.upper().endswith("-ASM") else 1, part.upper()))
    return tied[0]


def _sheet_number(text: str, fallback: int) -> int:
    match = _SHEET_NO.search(text or "")
    if not match:
        return fallback
    try:
        return int(match.group(1))
    except ValueError:
        return fallback


def _unassigned_sentence(sheet: int, parts: list[str]) -> str:
    listed = ", ".join(parts)
    return (
        f" Sheet {sheet} has more than one part ({listed}), so it was not assigned "
        "to a part and was not added as an operation."
    )


def _symbol_font_diameter_rects(page: Any) -> list[Any]:
    """Diameter mark stored as the letter O in a symbol font.

    Solid Edge draws that glyph from its ANSI symbol font. A letter O in a
    text font is not this mark.
    """
    import fitz

    found = []
    data = page.get_text("dict")
    for block in data.get("blocks") or []:
        if block.get("type") != 0:
            continue
        for line in block.get("lines") or []:
            for span in line.get("spans") or []:
                font = str(span.get("font") or "")
                if "symbol" not in font.casefold():
                    continue
                if span.get("text") != "O":
                    continue
                found.append(fitz.Rect(span["bbox"]))
    return found


def _positioned_pdf_callouts(
    path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str], dict[str, Any]]:
    """Read callouts whose words and symbols are placed apart on the sheet.

    A hole becomes a feature only when the sheet has one part, or none besides
    the drawing number. A sheet with several parts keeps the callout and does
    not turn it into an operation.
    """
    import fitz

    features: list[dict[str, Any]] = []
    callouts: list[dict[str, Any]] = []
    unreadable: list[str] = []
    pages: list[dict[str, Any]] = []
    doc = fitz.open(path)
    try:
        for index, page in enumerate(doc):
            words = []
            for word in page.get_text("words"):
                words.append((word[0], word[1], word[2], word[3], word[4], fitz.Rect(word[:4])))
            pages.append(
                {
                    "words": words,
                    "symbols": _diameter_symbol_rects(page),
                    "font_diameters": _symbol_font_diameter_rects(page),
                    "chevrons": _countersink_chevron_rects(page),
                    "parts": _part_names(words),
                    "sheet": _sheet_number(page.get_text("text"), index + 1),
                }
            )
    finally:
        doc.close()

    drawing = _drawing_number([page["parts"] for page in pages])
    file_parts: list[str] = []
    for page in pages:
        for part in page["parts"]:
            if part not in file_parts:
                file_parts.append(part)
    single_file = len(file_parts) <= 1
    described = describe_symbol("⌀")
    finish_blank = False
    saw_finish_value = False
    saw_outsource = False

    for page in pages:
        words = page["words"]
        sheet = page["sheet"]
        other = [part for part in page["parts"] if drawing is None or part.upper() != drawing.upper()]
        multi = len(other) > 1
        marked: set[int] = set()
        for symbol in page["symbols"]:
            best: tuple[float, int] | None = None
            for index, word in enumerate(words):
                if not _DECIMAL_WORD.fullmatch(word[4]):
                    continue
                gap = _rect_gap(symbol, word[5])
                if gap > 8:
                    continue
                if best is None or gap < best[0]:
                    best = (gap, index)
            if best is not None:
                marked.add(best[1])
        callout_ids = [
            index for index, word in enumerate(words) if _CALLOUT_WORD.fullmatch(word[4])
        ]
        groups = _cluster_indexes([words[index][5] for index in callout_ids], _CLUSTER_MARGIN)
        used_decimals: set[int] = set()
        consumed_sinks, sink_features = _countersink_from_sheet(
            words, page["symbols"], page.get("chevrons") or []
        )
        features.extend(sink_features)
        used_decimals.update(consumed_sinks)
        for group in groups:
            indexes = [callout_ids[index] for index in group]
            decimals = [index for index in indexes if _DECIMAL_WORD.fullmatch(words[index][4])]
            counts = []
            for index in indexes:
                count_match = _NX_WORD.fullmatch(words[index][4])
                if count_match:
                    counts.append(int(count_match.group(1)))
            thru = any(words[index][4].upper() in {"THRU", "THROUGH"} for index in indexes)
            marked_in_group = [index for index in decimals if index in marked]
            if marked_in_group and all(index in consumed_sinks for index in marked_in_group):
                continue
            marked_here = [index for index in marked_in_group if index not in consumed_sinks]
            if marked_here:
                for index in marked_here:
                    used_decimals.add(index)
                    value = _num(words[index][4])
                    label_parts = []
                    if len(counts) == 1:
                        label_parts.append(f"{counts[0]}X")
                    if thru:
                        label_parts.append("THRU")
                    label_parts.append(words[index][4])
                    label = " ".join(label_parts)
                    if multi:
                        callouts.append(
                            {
                                "symbol": "diameter",
                                "text": label,
                                "value": value,
                                "count": counts[0] if len(counts) == 1 else None,
                                "thru": thru,
                                "sheet": sheet,
                                "parts_on_sheet": list(other),
                                "assigned_part": None,
                                "meaning": described["meaning"],
                                "citation": described["citation"],
                                "feature": False,
                                "unassigned_hole": True,
                                "note": (
                                    "Diameter symbol was read next to this value. "
                                    "The callout does not say drill, ream, or bore. "
                                    + _unassigned_sentence(sheet, other)
                                ),
                            }
                        )
                        continue
                    blanks = [
                        _blank(
                            "tolerance",
                            "The callout does not say drill, ream, or bore — tolerance left blank.",
                        )
                    ]
                    dimensions: dict[str, Any] = {}
                    if value is None:
                        blanks.append(_blank("diameter_in", "Diameter value was not read — left blank."))
                    else:
                        dimensions["diameter_in"] = value
                    if len(counts) == 1:
                        dimensions["count"] = counts[0]
                    else:
                        blanks.append(_blank("count", "Place count was not read — left blank."))
                    if thru:
                        blanks.append(
                            _blank(
                                "depth_in",
                                "THRU is on the callout. Numeric depth was not given — depth left blank.",
                            )
                        )
                    else:
                        blanks.append(_blank("depth_in", "Depth is not in the callout — left blank."))
                    features.append(
                        _feature(
                            "hole",
                            label,
                            dimensions=dimensions,
                            blank_fields=blanks,
                            diameter_symbol={
                                "known": True,
                                "meaning": described["meaning"],
                                "citation": described["citation"],
                                "note": "Drawn as a circle and a slash next to the value.",
                            },
                        )
                    )
                continue
            if len(counts) == 1 and len(decimals) == 1:
                used_decimals.add(decimals[0])
                note = (
                    "Repeated dimension. No diameter symbol is on it — "
                    "no hole was added."
                )
                if multi:
                    note += _unassigned_sentence(sheet, other)
                callouts.append(
                    {
                        "symbol": "repetition",
                        "text": f"{counts[0]}X {words[decimals[0]][4]}",
                        "value": _num(words[decimals[0]][4]),
                        "meaning": describe_symbol("X")["meaning"],
                        "citation": describe_symbol("X")["citation"],
                        "feature": False,
                        "sheet": sheet,
                        "parts_on_sheet": list(other),
                        "assigned_part": None if multi else (other[0] if other else drawing),
                        "note": note,
                    }
                )
                continue
            tolerance_ids = [
                index
                for index in decimals
                if _near_word(words[index][5], words, _TOLERANCE_WORD, 14)
            ]
            if tolerance_ids and len(tolerance_ids) == len(decimals):
                used_decimals.update(decimals)
                callouts.append(
                    {
                        "symbol": None,
                        "text": " ".join(words[index][4] for index in decimals),
                        "value": None,
                        "meaning": None,
                        "citation": None,
                        "feature": False,
                        "note": (
                            "Title-block tolerance values were read. "
                            "They were not added as operations."
                        ),
                    }
                )
        claimed_inch: set[int] = set()
        for symbol in page.get("font_diameters") or []:
            best: tuple[float, int] | None = None
            for index, word in enumerate(words):
                if index in claimed_inch or not _INCH_QUOTED.fullmatch(word[4]):
                    continue
                gap = _rect_gap(symbol, word[5])
                if gap > 8:
                    continue
                if best is None or gap < best[0]:
                    best = (gap, index)
            if best is None:
                continue
            index = best[1]
            claimed_inch.add(index)
            value = _num(_INCH_QUOTED.fullmatch(words[index][4]).group(1))
            callouts.append(
                {
                    "symbol": "diameter",
                    "text": f"⌀{words[index][4]}",
                    "value": value,
                    "unit": "inch",
                    "feature": False,
                    "requires_machining": True,
                    "meaning": described["meaning"],
                    "citation": described["citation"],
                    "note": (
                        "A symbol-font diameter mark was read next to this value. "
                        "The file does not say drill, ream, or bore — no hole feature was added. "
                        "The sheet does not say lathe, mill, drill, tap, ream, bore, or single-point. "
                        "No operation code was added."
                    ),
                }
            )
        for index, word in enumerate(words):
            if index in claimed_inch or not _INCH_QUOTED.fullmatch(word[4]):
                continue
            callouts.append(
                {
                    "symbol": None,
                    "text": word[4],
                    "value": _num(word[4][:-1]),
                    "unit": "inch",
                    "feature": False,
                    "note": (
                        "Dimension read. No diameter symbol is on it. "
                        "The file does not say this is a hole, thread, groove, or face — "
                        "no feature was added."
                    ),
                }
            )
        for word in words:
            token = word[4]
            described_plus = describe_symbol(token)
            if described_plus.get("id") != "plus_minus":
                continue
            if (
                described_plus.get("nominal") is None
                and described_plus.get("tolerance") is None
                and described_plus.get("plus_value") is None
            ):
                continue
            citation = described_plus["citation"]
            if "°" in token:
                citation = f"{citation} {describe_symbol('°')['citation']}"
            value = described_plus.get("nominal")
            if value is None:
                value = described_plus.get("tolerance")
            row = {
                "symbol": described_plus["id"],
                "text": token,
                "value": value,
                "feature": False,
                "meaning": described_plus["meaning"],
                "citation": citation,
                "note": (
                    "A title-block plus-minus tolerance was read. "
                    "Limits were not calculated. It was not added as an operation."
                ),
            }
            if described_plus.get("plus_value") is not None:
                row["plus_value"] = described_plus["plus_value"]
                row["minus_value"] = described_plus["minus_value"]
            callouts.append(row)
        for word in words:
            described_degree = describe_symbol(word[4])
            if described_degree.get("id") != "degree" or not isinstance(
                described_degree.get("angle_deg"), float
            ):
                continue
            callouts.append(
                {
                    "symbol": "degree",
                    "text": word[4],
                    "value": described_degree["angle_deg"],
                    "feature": False,
                    "meaning": described_degree["meaning"],
                    "citation": described_degree["citation"],
                    "note": "An angle was read. It was not added as an operation.",
                }
            )
        for word in words:
            if not _DEGREE_WORD.fullmatch(word[4]):
                continue
            number_word = None
            number_gap = None
            for other in words:
                if not re.fullmatch(r"\d+(?:\.\d+)?", other[4]):
                    continue
                if other[5].x1 > word[5].x0 + 2:
                    continue
                gap = _rect_gap(other[5], word[5])
                if gap > 14:
                    continue
                if number_gap is None or gap < number_gap:
                    number_word = other
                    number_gap = gap
            if number_word is None:
                continue
            text = f"{number_word[4]} {word[4]}"
            described_degree = describe_symbol(text)
            if described_degree.get("id") != "degree":
                continue
            callouts.append(
                {
                    "symbol": "degree",
                    "text": text,
                    "value": described_degree.get("angle_deg"),
                    "feature": False,
                    "meaning": described_degree["meaning"],
                    "citation": described_degree["citation"],
                    "note": "An angle was read. It was not added as an operation.",
                }
            )
        for index, word in enumerate(words):
            if not _RADIUS_WORD.fullmatch(word[4]):
                continue
            count = None
            for other_word in words:
                count_match = _NX_WORD.fullmatch(other_word[4])
                if count_match and _rect_gap(word[5], other_word[5]) <= 8:
                    count = int(count_match.group(1))
                    break
            prefix = re.match(r"[A-Za-z]+", word[4])
            described_radius = describe_symbol(prefix.group(0) if prefix else word[4])
            text = f"{count}X {word[4]}" if count is not None else word[4]
            note = "Radius was read. It was not added as a machining operation."
            if multi:
                note += _unassigned_sentence(sheet, other)
            callouts.append(
                {
                    "symbol": described_radius["id"],
                    "text": text,
                    "value": _num(re.sub(r"^[A-Za-z]+", "", word[4])),
                    "meaning": described_radius["meaning"],
                    "citation": described_radius["citation"],
                    "feature": False,
                    "sheet": sheet,
                    "parts_on_sheet": list(other),
                    "assigned_part": None if multi else (other[0] if len(other) == 1 else drawing),
                    "note": note,
                }
            )
        plate_values = [
            index
            for index, word in enumerate(words)
            if word[4] == ".125" and _near_word(word[5], words, _MATERIAL_WORD, 16)
        ]
        if plate_values and single_file:
            features.append(
                _feature(
                    "plate",
                    "5052 .125",
                    dimensions={"thickness_in": 0.125},
                    blank_fields=[],
                )
            )
            used_decimals.update(plate_values)
        stock_ids = [
            index
            for index, word in enumerate(words)
            if _STOCK_WORD.fullmatch(word[4]) and _near_word(word[5], words, _MATERIAL_WORD, 4)
        ]
        if stock_ids and not single_file:
            used_decimals.update(stock_ids)
            values = []
            for index in stock_ids:
                value = _num(words[index][4])
                if value is not None and value not in values:
                    values.append(value)
            shown = ", ".join(f"{value:g}" for value in values)
            if len(other) == 1:
                callouts.append(
                    {
                        "symbol": None,
                        "text": f"{other[0]} {shown}",
                        "value": values[0] if len(values) == 1 else None,
                        "meaning": None,
                        "citation": None,
                        "feature": False,
                        "sheet": sheet,
                        "parts_on_sheet": list(other),
                        "assigned_part": other[0],
                        "note": (
                            f"Stock thickness {shown} in was read on {other[0]}. "
                            "It is not over 3/4 in, so it was not added as a machine operation."
                        ),
                    }
                )
            elif multi:
                callouts.append(
                    {
                        "symbol": None,
                        "text": f"sheet {sheet} stock {shown}",
                        "value": None,
                        "meaning": None,
                        "citation": None,
                        "feature": False,
                        "sheet": sheet,
                        "parts_on_sheet": list(other),
                        "assigned_part": None,
                        "note": (
                            f"Stock thickness {shown} in sits next to a material word. "
                            + _unassigned_sentence(sheet, other)
                        ),
                    }
                )
        if any(word[4].upper() == "OUTSOURCE" for word in words):
            saw_outsource = True
        consumed_finish: set[int] = set()
        ra_value_ids: set[int] = set()
        for index, word in enumerate(words):
            if word[4].casefold() != "ra":
                continue
            for other_index, other in enumerate(words):
                if not re.fullmatch(r"\d+(?:\.\d+)?", other[4]):
                    continue
                if _rect_gap(word[5], other[5]) > 8:
                    continue
                ra_value_ids.add(other_index)
        if any(word[4].upper() == "FINISH" for word in words):
            finish = next(word for word in words if word[4].upper() == "FINISH")
            finish_values = [
                word
                for word in words
                if _DECIMAL_WORD.fullmatch(word[4])
                and _grow(finish[5], 12).intersects(word[5])
                and not (
                    word[4] == ".125" and _near_word(word[5], words, _MATERIAL_WORD, 16)
                )
            ]
            zinc_near = any(
                word[4].upper() in {"ZINC", "PLATE"} and _rect_gap(finish[5], word[5]) <= 16
                for word in words
            )
            if zinc_near:
                finish_blank = False
            elif not finish_values:
                finish_blank = True
            if not zinc_near:
                for nearby_index, nearby in enumerate(words):
                    if nearby_index in consumed_finish:
                        continue
                    if not re.fullmatch(r"\d+(?:\.\d+)?", nearby[4]):
                        continue
                    if nearby[4] == ".125" and _near_word(nearby[5], words, _MATERIAL_WORD, 16):
                        continue
                    if nearby[5].x0 + 1 < finish[5].x1:
                        continue
                    if _rect_gap(finish[5], nearby[5]) > 8:
                        continue
                    surface = _word_on_the_left(words, finish, "SURFACE")
                    machined = _word_on_the_left(words, surface, "MACHINED")
                    if machined is not None:
                        label = f"MACHINED SURFACE {nearby[4]}"
                    elif surface is not None:
                        label = f"SURFACE FINISH {nearby[4]}"
                    else:
                        label = f"FINISH {nearby[4]}"
                    row = _surface_finish_callout(label, _num(nearby[4]))
                    if row is None:
                        continue
                    callouts.append(row)
                    consumed_finish.add(nearby_index)
                    saw_finish_value = True
        for word in words:
            if not str(word[4]).upper().startswith("FINISHES"):
                continue
            surface = _word_on_the_left(words, word, "SURFACE")
            machined = _word_on_the_left(words, surface, "MACHINED")
            for nearby_index, nearby in enumerate(words):
                if nearby_index in consumed_finish:
                    continue
                if not re.fullmatch(r"\d+(?:\.\d+)?", nearby[4]):
                    continue
                if nearby[5].x0 + 1 < word[5].x1:
                    continue
                if _rect_gap(word[5], nearby[5]) > 8:
                    continue
                if machined is not None and surface is not None:
                    label = f"MACHINED SURFACE FINISHES= {nearby[4]}"
                else:
                    label = f"FINISH {nearby[4]}"
                row = _surface_finish_callout(label, _num(nearby[4]))
                if row is None:
                    continue
                callouts.append(row)
                consumed_finish.add(nearby_index)
                saw_finish_value = True
        for index in callout_ids:
            if index in used_decimals or index in consumed_finish or index in ra_value_ids:
                continue
            if not _DECIMAL_WORD.fullmatch(words[index][4]):
                continue
            if _near_word(words[index][5], words, _TOLERANCE_WORD, 14):
                continue
            if words[index][4] == ".125" and index in plate_values:
                continue
            note = (
                "Dimension read. The file does not say this is a hole, "
                "thread, groove, or face — no feature was added."
            )
            if multi:
                note += _unassigned_sentence(sheet, other)
            callouts.append(
                {
                    "symbol": None,
                    "text": words[index][4],
                    "value": _num(words[index][4]),
                    "meaning": None,
                    "citation": None,
                    "feature": False,
                    "sheet": sheet,
                    "parts_on_sheet": list(other),
                    "assigned_part": None if multi else (other[0] if other else drawing),
                    "note": note,
                }
            )

    if finish_blank and not saw_finish_value:
        unreadable.append("FINISH is on the drawing. No finish value was read — left blank.")
    if saw_outsource:
        unreadable.append(
            "OUTSOURCE is on the drawing. No shop operation was added from that label."
        )
    kept: list[dict[str, Any]] = []
    seen_tolerance: set[str] = set()
    for callout in callouts:
        if str(callout.get("note") or "").startswith("Title-block"):
            token = str(callout.get("text") or "")
            if token in seen_tolerance:
                continue
            seen_tolerance.add(token)
        kept.append(callout)
    return features, kept, unreadable, {
        "drawing_number": drawing,
        "part_numbers": file_parts,
        "parts_by_sheet": {page["sheet"]: page["parts"] for page in pages},
    }


def _step_assembly(text: str) -> dict[str, Any]:
    """Separate assembly nodes from leaf product names. Solids are not parts."""
    products: dict[str, str] = {}
    for match in re.finditer(r"#(\d+)\s*=\s*PRODUCT\s*\(\s*'([^']*)'", text):
        products[match.group(1)] = match.group(2)
    formations: dict[str, str] = {}
    for match in re.finditer(
        r"#(\d+)\s*=\s*PRODUCT_DEFINITION_FORMATION(?:_WITH_SPECIFIED_SOURCE)?"
        r"\s*\(\s*'[^']*'\s*,\s*'[^']*'\s*,\s*#(\d+)",
        text,
    ):
        formations[match.group(1)] = match.group(2)
    definitions: dict[str, str] = {}
    for match in re.finditer(
        r"#(\d+)\s*=\s*PRODUCT_DEFINITION\s*\(\s*'[^']*'\s*,\s*'[^']*'\s*,\s*#(\d+)",
        text,
    ):
        definitions[match.group(1)] = match.group(2)

    def _name(definition_id: str) -> str | None:
        formation = definitions.get(definition_id)
        product_id = formations.get(formation) if formation else None
        if product_id is None:
            return None
        return products.get(product_id)

    children: dict[str, dict[str, int]] = {}
    for match in re.finditer(
        r"NEXT_ASSEMBLY_USAGE_OCCURRENCE\s*\(\s*'[^']*'\s*,\s*'[^']*'\s*,\s*'[^']*'\s*,\s*#(\d+)\s*,\s*#(\d+)",
        text,
    ):
        parent = _name(match.group(1))
        child = _name(match.group(2))
        if not parent or not child:
            continue
        bucket = children.setdefault(parent, {})
        bucket[child] = bucket.get(child, 0) + 1
    assemblies = sorted(children)
    leaves = sorted(name for name in products.values() if name not in children)
    return {
        "products": sorted(products.values()),
        "assemblies": assemblies,
        "leaf_parts": leaves,
        "occurrences": {
            parent: dict(sorted(kids.items())) for parent, kids in sorted(children.items())
        },
    }


def read_machining_requirements(
    pdf_path: str | Path | None = None,
    stp_path: str | Path | None = None,
) -> dict[str, Any]:
    """List machining requirements that are actually in the PDF and STEP file."""
    features: list[dict[str, Any]] = []
    callouts: list[dict[str, Any]] = []
    unreadable: list[str] = []
    unknown: list[dict[str, Any]] = []
    geometry: dict[str, Any] | None = None
    assembly: dict[str, Any] | None = None
    placed_sheets: dict[str, Any] = {}
    pdf_read = False
    step_read = False

    pdf = Path(pdf_path) if pdf_path else None
    step = Path(stp_path) if stp_path else None
    pdf_text = ""
    if pdf is None or not pdf.is_file():
        unreadable.append(_NO_PDF_NOTE)
    else:
        try:
            text = _pdf_text(pdf)
        except Exception:
            unreadable.append(_PDF_FAIL_NOTE)
            text = ""
        pdf_text = text
        pdf_read = True
        if not text.strip():
            unreadable.append(_EMPTY_PDF_NOTE)
        else:
            found, notes, gaps = _parse_pdf_lines(text)
            features.extend(found)
            callouts.extend(notes)
            for gap in gaps:
                if gap not in unreadable:
                    unreadable.append(gap)
            unknown.extend(unknown_symbols_in_text(text))
            try:
                placed, placed_notes, placed_gaps, placed_sheets = _positioned_pdf_callouts(pdf)
            except Exception:
                placed, placed_notes, placed_gaps, placed_sheets = [], [], [
                    "Placed callouts could not be read — left blank."
                ], {}
            radius_texts = [
                str(callout.get("text") or "")
                for callout in placed_notes
                if callout.get("symbol") == "radius" and callout.get("text")
            ]
            if radius_texts:
                callouts = [
                    callout
                    for callout in callouts
                    if callout.get("symbol") != "radius"
                    or not any(
                        str(callout.get("text") or "") and str(callout.get("text")) in bigger
                        for bigger in radius_texts
                    )
                ]
            have = {
                (
                    feature.get("kind"),
                    (feature.get("dimensions") or {}).get("diameter_in"),
                    (feature.get("dimensions") or {}).get("thickness_in"),
                )
                for feature in features
            }
            for feature in placed:
                key = (
                    feature.get("kind"),
                    (feature.get("dimensions") or {}).get("diameter_in"),
                    (feature.get("dimensions") or {}).get("thickness_in"),
                )
                if key in have:
                    continue
                features.append(feature)
                have.add(key)
            # A full text line and the same placed word are one callout.
            already = {
                (callout.get("symbol"), callout.get("text"))
                for callout in callouts
                if callout.get("symbol") in {"degree", "plus_minus", "iso_fit", "surface_texture"}
            }
            for callout in placed_notes:
                key = (callout.get("symbol"), callout.get("text"))
                if key[0] in {"degree", "plus_minus", "iso_fit", "surface_texture"} and key in already:
                    continue
                callouts.append(callout)
                if key[0] in {"degree", "plus_minus", "iso_fit", "surface_texture"}:
                    already.add(key)
            for gap in placed_gaps:
                if gap not in unreadable:
                    unreadable.append(gap)
            if not any(feature.get("kind") == "face" for feature in features):
                unreadable.append("No face callout in the PDF — face left blank.")
            if not any(feature.get("kind") == "thread" for feature in features):
                unreadable.append("No thread designation in the PDF — thread left blank.")
            if not any(feature.get("kind") == "groove" for feature in features):
                unreadable.append("No groove callout in the PDF — groove left blank.")

    if step is None or not step.is_file():
        unreadable.append(_NO_STEP_NOTE)
    else:
        try:
            raw = step.read_text(errors="ignore")
        except OSError:
            unreadable.append(_STEP_FAIL_NOTE)
            raw = ""
        step_read = True
        text = re.sub(r",\s*\n\s*", ",", raw)
        geometry = _step_geometry(text)
        unreadable.append(_CYLINDER_NOTE)
        if not re.search(r"\bTHREAD\b|\bSCREW_THREAD\b", text, re.IGNORECASE):
            unreadable.append(_STEP_THREAD_NOTE)
        if not re.search(r"\bGROOVE\b", text, re.IGNORECASE):
            unreadable.append(_STEP_GROOVE_NOTE)
        unreadable.append(_PLANE_NOTE)
        if geometry["units"] is None and (geometry["cylinders"] or geometry["circles"]):
            unreadable.append(
                "STEP length unit was not read — cylinder sizes left blank."
            )
        _match_step(features, geometry)
        _match_step_callouts(callouts, geometry)
        assembly = _step_assembly(text)
        step_names = {name.upper() for name in assembly["products"]}
        pdf_only = []
        if step_names:
            pdf_only = [
                name
                for name in (placed_sheets.get("part_numbers") or [])
                if name.upper() not in step_names
            ]
        assembly["pdf_only_parts"] = pdf_only
        assembly["drawing_number"] = placed_sheets.get("drawing_number")
        assembly["parts_by_sheet"] = placed_sheets.get("parts_by_sheet") or {}
        if pdf_only:
            unreadable.append(
                f"{', '.join(pdf_only)} is on the PDF and not in the STEP."
            )

    if any(callout.get("unassigned_hole") for callout in callouts):
        unreadable.append(
            "Hole callouts were read on a sheet with more than one part. "
            "They were not assigned and were not added as operations. "
            "Run time and setup stay blank."
        )

    for index, feature in enumerate(features, start=1):
        feature["id"] = f"read-{index}"

    notes = [SHARED_DRIVE_NOTE]
    if assembly and assembly.get("assemblies"):
        notes.append(
            f"STEP separates {len(assembly['leaf_parts'])} leaf parts. "
            f"{', '.join(assembly['assemblies'])} are assemblies and were not "
            "treated as one machined part."
        )
    needs_machining = any(
        feature.get("kind") in {"hole", "countersink", "counterbore"}
        or feature.get("thread_form") in {"tap", "single_point"}
        for feature in features
    ) or any(
        callout.get("unassigned_hole") or callout.get("requires_machining")
        for callout in callouts
    )
    # The sheet's own machine word wins. Stock versus finished fills only a blank.
    process_from_stock = None
    if not any(feature.get("stated_machine") is True for feature in features):
        process_from_stock = compare_stock_to_finished(
            geometry,
            features,
            callouts,
            assembly,
            read_stated_stock(pdf_text),
        )
        _apply_process_from_stock(features, process_from_stock)
    if process_from_stock and process_from_stock.get("evidence"):
        notes.append(process_from_stock["evidence"])

    return {
        "features": features,
        "callouts": callouts,
        "geometry": geometry,
        "assembly": assembly,
        "unknown_symbols": unknown,
        "unreadable": unreadable,
        "notes": notes,
        "needs_machining": needs_machining,
        "process_from_stock": process_from_stock,
        "pdf_read": pdf_read,
        "step_read": step_read,
        "practiced_on_shared_drive": False,
    }


def apply_drawing_reading(
    takeoff: dict[str, Any] | None,
    pdf_path: str | Path | None = None,
    stp_path: str | Path | None = None,
) -> dict[str, Any]:
    """Store the reading. Fill features only when the job has none typed."""
    out = dict(takeoff or {})
    reading = read_machining_requirements(pdf_path, stp_path)
    out["machining_reading"] = reading
    current = out.get("machining_features")
    source = out.get("machining_features_source")
    typed = isinstance(current, list) and len(current) > 0 and source != "drawing"
    if typed:
        if not source:
            out["machining_features_source"] = "typed"
        return out
    found = [row for row in reading.get("features") or [] if isinstance(row, dict)]
    claimed = bool(reading.get("needs_machining"))
    if found:
        out["machining_features"] = found
        out["machining_features_source"] = "drawing"
    elif claimed or source == "drawing":
        out["machining_features"] = []
        out["machining_features_source"] = "drawing"
    if claimed and "needs_machining" not in out:
        out["needs_machining"] = True
    return out
