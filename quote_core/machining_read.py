"""Read machining callouts from a PDF and geometry from a STEP file.

A feature is added only when the file states it. A diameter, a cylinder,
or a plane by itself is not a hole, a thread, a groove, or a face operation.
Missing values stay blank.
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
_RA = re.compile(rf"\bRa\s*{_NUMBER}", re.IGNORECASE)
_RADIUS = re.compile(rf"(?<![A-Z])(?:SR|CR|R)\s*{_NUMBER}", re.IGNORECASE)
_HOLE_PROCESS = re.compile(r"\b(DRILL|REAM|BORE)\b", re.IGNORECASE)
_COUNTERBORE = re.compile(r"⌴|\bCOUNTERBORE\b|\bSPOTFACE\b", re.IGNORECASE)
_COUNTERSINK = re.compile(r"⌵|\bCOUNTERSINK\b", re.IGNORECASE)
_STEP_RADIUS = re.compile(
    r"(CYLINDRICAL_SURFACE|CIRCLE)\s*\(\s*'[^']*'\s*,\s*#\d+\s*,\s*"
    r"([+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)\s*\)",
    re.IGNORECASE,
)
_PLANE = re.compile(r"\bPLANE\s*\(", re.IGNORECASE)

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


def _parse_pdf_lines(text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    features: list[dict[str, Any]] = []
    callouts: list[dict[str, Any]] = []
    unreadable: list[str] = []
    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue
        thread = _THREAD.search(line)
        metric = None if thread else _METRIC.search(line)
        if thread or metric:
            features.append(_thread_feature(line, thread, metric))
            continue
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
            described = describe_symbol(roughness.group(0))
            callouts.append(
                {
                    "symbol": described["id"],
                    "text": roughness.group(0),
                    "value": roughness.group(1),
                    "meaning": described["meaning"],
                    "citation": described["citation"],
                    "feature": False,
                    "note": "Surface texture is a callout. It was not added as an operation.",
                }
            )
            continue
        if _COUNTERBORE.search(line):
            features.append(_round_feature("counterbore", line))
            continue
        if _COUNTERSINK.search(line):
            features.append(_round_feature("countersink", line))
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
    return features, callouts, unreadable


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


def _plate_feature(line: str, match: re.Match[str]) -> dict[str, Any]:
    thickness = _num(match.group(1))
    dimensions: dict[str, Any] = {}
    blanks: list[dict[str, str]] = []
    if thickness is None:
        blanks.append(_blank("thickness_in", "Plate thickness was not read — left blank."))
    else:
        dimensions["thickness_in"] = thickness
    return _feature("plate", line, dimensions=dimensions, blank_fields=blanks)


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
    cylinders = []
    circles = []
    for kind, raw in _STEP_RADIUS.findall(text):
        radius = float(raw)
        radius_in = None if scale is None else radius * scale
        row = {
            "radius_file": radius,
            "radius_in": radius_in,
            "diameter_in": None if radius_in is None else radius_in * 2.0,
        }
        if kind.upper().startswith("CYLINDRICAL"):
            cylinders.append(row)
        else:
            circles.append(row)
    return {
        "units": units,
        "cylinders": cylinders,
        "circles": circles,
        "plane_count": len(_PLANE.findall(text)),
        "note": _PLANE_NOTE,
    }


def _match_step(features: list[dict[str, Any]], geometry: dict[str, Any]) -> None:
    diameters = [
        row["diameter_in"]
        for row in (geometry.get("cylinders") or [])
        if isinstance(row.get("diameter_in"), float)
    ]
    for feature in features:
        dims = feature.get("dimensions") or {}
        wanted = dims.get("diameter_in")
        if not isinstance(wanted, (int, float)):
            continue
        hits = [dia for dia in diameters if abs(dia - float(wanted)) <= _DIAMETER_GAP_IN]
        if not hits:
            continue
        feature["step_match"] = {
            "diameter_in": hits[0],
            "matches": len(hits),
            "note": (
                "A STEP cylindrical diameter matches this callout. "
                "It was not added as a second feature."
            ),
        }


_CALLOUT_WORD = re.compile(r"^(?:\d*\.\d+|\d+X|THRU|THROUGH)$", re.IGNORECASE)
_DECIMAL_WORD = re.compile(r"^\d*\.\d+$")
_NX_WORD = re.compile(r"^(\d+)X$", re.IGNORECASE)
_MATERIAL_WORD = re.compile(r"^(?:5052(?:-ALUM)?|ALUM|ALUMINUM|ALEDO)$", re.IGNORECASE)
_TOLERANCE_WORD = re.compile(r"DECIMAL|TOLERANCE|ANGULAR|PLACE", re.IGNORECASE)
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


def _diameter_symbol_rects(page: Any) -> list[Any]:
    """Circle-and-slash geometry placed as the diameter symbol.

    The symbol is drawn, not typed: a small closed curve and a separate
    diagonal line. Genium Drafting Manual Section 6.1 paragraph 2.1 places
    that symbol in front of a diameter value.
    """
    import fitz

    lines = []
    loops = []
    for drawing in page.get_drawings():
        rect = fitz.Rect(drawing["rect"])
        if not (4 <= rect.width <= 25 and 4 <= rect.height <= 25):
            continue
        items = drawing["items"]
        kinds = [item[0] for item in items]
        if kinds == ["l"] and len(items) == 1:
            start, end = items[0][1], items[0][2]
            dx, dy = abs(end.x - start.x), abs(end.y - start.y)
            if dx > 4 and dy > 4 and abs(dx - dy) < max(3.0, 0.45 * max(dx, dy)):
                lines.append(rect)
        elif kinds.count("c") >= 2 and len(items) >= 4:
            loops.append(rect)
    symbols = []
    for line in lines:
        for loop in loops:
            if line.intersects(_grow(loop, 2)):
                symbols.append(line | loop)
                break
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


def _positioned_pdf_callouts(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Read callouts whose words and symbols are placed apart on the sheet."""
    import fitz

    features: list[dict[str, Any]] = []
    callouts: list[dict[str, Any]] = []
    unreadable: list[str] = []
    doc = fitz.open(path)
    try:
        page = doc[0]
        words = []
        for word in page.get_text("words"):
            words.append((word[0], word[1], word[2], word[3], word[4], fitz.Rect(word[:4])))
        symbols = _diameter_symbol_rects(page)
        marked: set[int] = set()
        for symbol in symbols:
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
        described = describe_symbol("⌀")
        for group in groups:
            indexes = [callout_ids[index] for index in group]
            decimals = [index for index in indexes if _DECIMAL_WORD.fullmatch(words[index][4])]
            counts = []
            for index in indexes:
                count_match = _NX_WORD.fullmatch(words[index][4])
                if count_match:
                    counts.append(int(count_match.group(1)))
            thru = any(words[index][4].upper() in {"THRU", "THROUGH"} for index in indexes)
            marked_here = [index for index in decimals if index in marked]
            if marked_here:
                for index in marked_here:
                    used_decimals.add(index)
                    value = _num(words[index][4])
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
                    label_parts = []
                    if len(counts) == 1:
                        label_parts.append(f"{counts[0]}X")
                    if thru:
                        label_parts.append("THRU")
                    label_parts.append(words[index][4])
                    features.append(
                        _feature(
                            "hole",
                            " ".join(label_parts),
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
                callouts.append(
                    {
                        "symbol": "repetition",
                        "text": f"{counts[0]}X {words[decimals[0]][4]}",
                        "value": _num(words[decimals[0]][4]),
                        "meaning": describe_symbol("X")["meaning"],
                        "citation": describe_symbol("X")["citation"],
                        "feature": False,
                        "note": (
                            "Repeated dimension. No diameter symbol is on it — "
                            "no hole was added."
                        ),
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
        plate_values = []
        for index, word in enumerate(words):
            if word[4] != ".125":
                continue
            if _near_word(word[5], words, _MATERIAL_WORD, 16):
                plate_values.append(index)
        if plate_values:
            features.append(
                _feature(
                    "plate",
                    "5052 .125",
                    dimensions={"thickness_in": 0.125},
                    blank_fields=[],
                )
            )
            used_decimals.update(plate_values)
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
            if not finish_values:
                unreadable.append(
                    "FINISH is on the drawing. No finish value was read — left blank."
                )
        for index in callout_ids:
            if index in used_decimals or not _DECIMAL_WORD.fullmatch(words[index][4]):
                continue
            if _near_word(words[index][5], words, _TOLERANCE_WORD, 14):
                continue
            if words[index][4] == ".125" and index in plate_values:
                continue
            callouts.append(
                {
                    "symbol": None,
                    "text": words[index][4],
                    "value": _num(words[index][4]),
                    "meaning": None,
                    "citation": None,
                    "feature": False,
                    "note": (
                        "Dimension read. The file does not say this is a hole, "
                        "thread, groove, or face — no feature was added."
                    ),
                }
            )
    finally:
        doc.close()
    return features, callouts, unreadable


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
    pdf_read = False
    step_read = False

    pdf = Path(pdf_path) if pdf_path else None
    step = Path(stp_path) if stp_path else None
    if pdf is None or not pdf.is_file():
        unreadable.append(_NO_PDF_NOTE)
    else:
        try:
            text = _pdf_text(pdf)
        except Exception:
            unreadable.append(_PDF_FAIL_NOTE)
            text = ""
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
                placed, placed_notes, placed_gaps = _positioned_pdf_callouts(pdf)
            except Exception:
                placed, placed_notes, placed_gaps = [], [], [
                    "Placed callouts could not be read — left blank."
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
            callouts.extend(placed_notes)
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

    for index, feature in enumerate(features, start=1):
        feature["id"] = f"read-{index}"

    return {
        "features": features,
        "callouts": callouts,
        "geometry": geometry,
        "unknown_symbols": unknown,
        "unreadable": unreadable,
        "notes": [SHARED_DRIVE_NOTE],
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
    if found:
        out["machining_features"] = found
        out["machining_features_source"] = "drawing"
    elif source == "drawing":
        out["machining_features"] = []
        out["machining_features_source"] = "drawing"
    return out
