"""PDF-only bend callouts and a simple flat-pattern calculator.

A formed part is not a flat laser plate. One or two 90° bends with a
stated inside radius can be developed from ``config/press_brake_bends.csv``.
The chart ships with no data rows. There is no K-factor default.
"""

from __future__ import annotations

import csv
import math
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BendRead:
    """What the drawing text actually says about bends. Missing stays None."""

    callout: bool = False
    hem: bool = False
    offset: bool = False
    formed_word: bool = False
    brake: bool = False
    bend_word: bool = False
    up_down: bool = False
    bend_count: int | None = None
    angles: tuple[float, ...] = ()
    radius_in: float | None = None
    radius_ambiguous: bool = False
    conventions: tuple[str, ...] = ()
    legs_in: tuple[float, ...] = ()
    width_in: float | None = None
    view_count: int = 0
    punch_radius_in: float | None = None
    die_opening_in: float | None = None
    count_flag: str | None = None
    count_source: str = ""


_HEM_RE = re.compile(r"(?i)\bHEMS?\b")
_OFFSET_RE = re.compile(r"(?i)\b(?:OFFSETS?|JOGS?|JOGGLES?)\b")
_FORMED_RE = re.compile(r"(?i)\bFORMED\b")
_BRAKE_RE = re.compile(r"(?i)\bBRAKE\b")
_BEND_WORD_RE = re.compile(r"(?i)\bBENDS?\b")
_UP_DOWN_RE = re.compile(r"(?i)(?<![A-Z0-9])(?:UP|DOWN)(?![A-Z0-9])")
_BEND_DIR_RE = re.compile(
    r"(?i)\bBEND\s+(?:UP|DOWN)(?:\s+\d+(?:\.\d+)?\s*(?:°|DEG(?:REE)?S?))?|"
    r"\b(?:UP|DOWN)\s+\d+(?:\.\d+)?\s*(?:°|DEG(?:REE)?S?)|"
    r"\b\d+(?:\.\d+)?\s*(?:°|DEG(?:REE)?S?)\s+(?:UP|DOWN)\b"
)
_COUNT_RE = re.compile(
    r"(?i)(?<!\.)\b(\d+)[ \t]+BENDS?\b(?![ \t]+LINES?\b)"
)
_BEND_LINE_COUNT_RE = re.compile(r"(?i)\b(\d+)\s+BEND\s+LINES?\b")
_BEND_LINE_RE = re.compile(r"(?i)\bBEND\s+LINES?\b")
_ANGLE_RE = re.compile(
    r"(?i)\b(\d+(?:\.\d+)?)\s*(?:°|DEG(?:REE)?S?)\b"
)
_VIEW_RE = re.compile(
    r"(?i)\b(?:FRONT|SIDE|TOP|BOTTOM|LEFT|RIGHT|ISO|FORMED|FLAT)\s+VIEW\b"
)
_LEG_RE = re.compile(
    r"(?i)\bLEG\s+([0-9]+(?:\s*[- ]\s*[0-9]+\s*/\s*[0-9]+|\s*/\s*[0-9]+|\.\d+)?)"
)
_WIDTH_RE = re.compile(
    r"(?i)\bWIDTH\s+([0-9]+(?:\s*[- ]\s*[0-9]+\s*/\s*[0-9]+|\s*/\s*[0-9]+|\.\d+)?)"
)
_RADIUS_RES = (
    re.compile(
        r"(?i)\bINSIDE\s+RADIUS\s+"
        r"([0-9]+(?:\s*[- ]\s*[0-9]+\s*/\s*[0-9]+|\s*/\s*[0-9]+|\.\d+)?)"
    ),
    re.compile(
        r"(?i)\bBEND\s+RADIUS\s+"
        r"([0-9]+(?:\s*[- ]\s*[0-9]+\s*/\s*[0-9]+|\s*/\s*[0-9]+|\.\d+)?)"
    ),
    re.compile(
        r"(?i)\bIR\s*[:=]?\s*"
        r"([0-9]+(?:\s*[- ]\s*[0-9]+\s*/\s*[0-9]+|\s*/\s*[0-9]+|\.\d+)?)"
    ),
)
_PUNCH_RE = re.compile(
    r"(?i)\bPUNCH(?:\s+RADIUS)?\s+"
    r"([0-9]+(?:\s*[- ]\s*[0-9]+\s*/\s*[0-9]+|\s*/\s*[0-9]+|\.\d+)?)"
)
_DIE_RE = re.compile(
    r"(?i)\bDIE(?:\s+OPENING)?\s+"
    r"([0-9]+(?:\s*[- ]\s*[0-9]+\s*/\s*[0-9]+|\s*/\s*[0-9]+|\.\d+)?)"
)
_CONVENTION_RES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("inside", re.compile(r"(?i)\bDIMENSIONS?\s+INSIDE\b|\bINSIDE\s+DIMENSIONS?\b")),
    ("outside", re.compile(r"(?i)\bDIMENSIONS?\s+OUTSIDE\b|\bOUTSIDE\s+DIMENSIONS?\b")),
    (
        "mold-line",
        re.compile(r"(?i)\bDIMENSIONS?\s+MOLD[-\s]?LINE\b|\bMOLD[-\s]?LINE\s+DIMENSIONS?\b"),
    ),
)


def _inches(token: str | None) -> float | None:
    text = " ".join(str(token or "").strip().split())
    if not text:
        return None
    mixed = re.fullmatch(
        r"(\d+)\s*[- ]\s*(\d+)\s*/\s*(\d+)",
        text,
    )
    if mixed:
        whole, num, den = (float(mixed.group(i)) for i in (1, 2, 3))
        if den == 0:
            return None
        return whole + num / den
    frac = re.fullmatch(r"(\d+)\s*/\s*(\d+)", text)
    if frac:
        num, den = float(frac.group(1)), float(frac.group(2))
        if den == 0:
            return None
        return num / den
    plain = re.fullmatch(r"\d+(?:\.\d+)?", text)
    if plain:
        return float(plain.group(0))
    return None


def _unique_inches(values: list[float]) -> tuple[float | None, bool]:
    if not values:
        return None, False
    first = values[0]
    if any(abs(value - first) > 0.0005 for value in values[1:]):
        return None, True
    return first, False


@dataclass(frozen=True)
class BendCount:
    """A bend count taken from the drawing, or a flag when it would be a guess."""

    count: int | None = None
    flag: str | None = None
    source: str = ""


# Captured Bend rows (q10488, q10504) are labeled FieldName "Number of Bends",
# but Value, InitValue, and UnitTime on those rows are hours, and Quantity is
# 1 on every sample. AddOperation in this repo writes a weld, not a bend.
# There is no Bend-op field to set the count in, so the count stays on the line.
BEND_OP_COUNT_FIELD = None


def _bend_line_count(text: str) -> int | None:
    """How many bend lines the text layer names. None when it names none."""
    numbered = [int(match.group(1)) for match in _BEND_LINE_COUNT_RE.finditer(text)]
    if numbered:
        if len(set(numbered)) > 1:
            return -1
        return numbered[0]
    bare = []
    for match in _BEND_LINE_RE.finditer(text):
        prefix = text[max(0, match.start() - 8):match.start()]
        if re.search(r"\d+\s+$", prefix):
            continue
        bare.append(match)
    if not bare:
        return None
    return len(bare)


def _uncertain_count_reason(text: str) -> str:
    if _UP_DOWN_RE.search(text):
        return "UP/DOWN callout has no angle and no count"
    if _ANGLE_RE.search(text):
        return "a bend angle does not give a count"
    if any(rx.search(text) for rx in _RADIUS_RES):
        return "a bend radius does not give a count"
    if _FORMED_RE.search(text):
        return "FORMED does not give a count"
    if _BRAKE_RE.search(text):
        return "a press brake note does not give a count"
    if _BEND_WORD_RE.search(text):
        return "BEND does not give a count"
    return "bend callout does not give a count"


def _extract_bend_count(text: str) -> BendCount:
    """Count bends from callouts and text-layer bend lines. Do not guess."""
    explicit = [int(match.group(1)) for match in _COUNT_RE.finditer(text)]
    directions = list(_BEND_DIR_RE.finditer(text))
    bend_lines = _bend_line_count(text)
    if explicit and len(set(explicit)) > 1:
        return BendCount(flag="explicit bend counts disagree")
    if bend_lines == -1:
        return BendCount(flag="bend line counts disagree")
    candidates: list[tuple[str, int]] = []
    if explicit:
        candidates.append(("explicit count", explicit[0]))
    if directions:
        candidates.append(("UP/DOWN callouts", len(directions)))
    if bend_lines:
        candidates.append(("bend lines", bend_lines))
    if candidates:
        counts = {count for _name, count in candidates}
        if len(counts) != 1:
            detail = ", ".join(f"{name}={count}" for name, count in candidates)
            return BendCount(flag=f"signals conflict ({detail})")
        source = " and ".join(name for name, _count in candidates)
        return BendCount(count=candidates[0][1], source=source)
    if len(_VIEW_RE.findall(text)) >= 2:
        return BendCount(flag="view-only shape has no bend callouts")
    if any(
        (
            _HEM_RE.search(text),
            _OFFSET_RE.search(text),
            _FORMED_RE.search(text),
            _BRAKE_RE.search(text),
            _BEND_WORD_RE.search(text),
            _UP_DOWN_RE.search(text),
            _ANGLE_RE.search(text),
            any(rx.search(text) for rx in _RADIUS_RES),
        )
    ):
        return BendCount(flag=_uncertain_count_reason(text))
    return BendCount(count=0, source="no bend callouts")


def read_bends(text: str) -> BendRead:
    """Parse bend callouts. Does not guess a radius, angle, or convention."""
    blob = str(text or "")
    angles = tuple(float(match.group(1)) for match in _ANGLE_RE.finditer(blob))
    radii = [
        value
        for rx in _RADIUS_RES
        for match in rx.finditer(blob)
        if (value := _inches(match.group(1))) is not None
    ]
    radius, radius_ambiguous = _unique_inches(radii)
    counted = _extract_bend_count(blob)
    conventions: list[str] = []
    for name, rx in _CONVENTION_RES:
        if rx.search(blob) and name not in conventions:
            conventions.append(name)
    legs = tuple(
        value
        for match in _LEG_RE.finditer(blob)
        if (value := _inches(match.group(1))) is not None
    )
    widths = [
        value
        for match in _WIDTH_RE.finditer(blob)
        if (value := _inches(match.group(1))) is not None
    ]
    width, width_ambiguous = _unique_inches(widths)
    if width_ambiguous:
        width = None
    punches = [
        value
        for match in _PUNCH_RE.finditer(blob)
        if (value := _inches(match.group(1))) is not None
    ]
    dies = [
        value
        for match in _DIE_RE.finditer(blob)
        if (value := _inches(match.group(1))) is not None
    ]
    punch, _punch_ambiguous = _unique_inches(punches)
    die, _die_ambiguous = _unique_inches(dies)
    hem = bool(_HEM_RE.search(blob))
    offset = bool(_OFFSET_RE.search(blob))
    formed_word = bool(_FORMED_RE.search(blob))
    brake = bool(_BRAKE_RE.search(blob))
    bend_word = bool(_BEND_WORD_RE.search(blob))
    up_down = bool(_UP_DOWN_RE.search(blob))
    view_count = len(_VIEW_RE.findall(blob))
    callout = any(
        (
            hem,
            offset,
            formed_word,
            brake,
            bend_word,
            up_down,
            bool(angles),
            radius is not None or radius_ambiguous,
            view_count >= 2,
            counted.count not in (None, 0),
        )
    )
    return BendRead(
        callout=callout,
        hem=hem,
        offset=offset,
        formed_word=formed_word,
        brake=brake,
        bend_word=bend_word,
        up_down=up_down,
        bend_count=counted.count,
        angles=angles,
        radius_in=radius,
        radius_ambiguous=radius_ambiguous,
        conventions=tuple(conventions),
        legs_in=legs,
        width_in=width,
        view_count=view_count,
        punch_radius_in=punch,
        die_opening_in=die,
        count_flag=counted.flag,
        count_source=counted.source,
    )


@dataclass(frozen=True)
class BendChartRow:
    """One press-brake chart row. Values come from the shop file, not from guesses."""

    material: str
    thickness_in: float
    inside_radius_in: float
    punch_radius_in: float
    die_opening_in: float
    method: str
    value: float


@dataclass(frozen=True)
class FlatPattern:
    """A refuse reason, or a developed flat. ``flag`` None and no length means unused."""

    flag: str | None = None
    flag_field: str = "formed part"
    developed_length_in: float | None = None
    width_in: float | None = None
    bend_count: int | None = None
    bend_allowance_in: float | None = None
    bend_deduction_in: float | None = None
    line_note: str = ""
    operations: tuple[str, ...] = ()


CHART_COLUMNS = (
    "material",
    "thickness_in",
    "inside_radius_in",
    "punch_radius_in",
    "die_opening_in",
    "method",
    "value",
)
CHART_METHODS = ("k", "ba", "bd")
CHART_NAME = "config/press_brake_bends.csv"


def chart_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config" / "press_brake_bends.csv"


def load_bend_chart(path: Path | None = None) -> tuple[BendChartRow, ...]:
    """Data rows only. Blank lines and ``#`` comments are never chart data."""
    src = path or chart_path()
    if not src.is_file():
        return ()
    rows: list[BendChartRow] = []
    header: list[str] | None = None
    with src.open(newline="", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            cells = [cell.strip() for cell in next(csv.reader([line]))]
            if header is None:
                header = cells
                continue
            if header != list(CHART_COLUMNS) or len(cells) != len(CHART_COLUMNS):
                continue
            material, thickness, radius, punch, die, method, value = cells
            method_name = method.casefold()
            if method_name not in CHART_METHODS or not material:
                continue
            try:
                row = BendChartRow(
                    material=material,
                    thickness_in=float(thickness),
                    inside_radius_in=float(radius),
                    punch_radius_in=float(punch),
                    die_opening_in=float(die),
                    method=method_name,
                    value=float(value),
                )
            except ValueError:
                continue
            if row.thickness_in <= 0 or row.inside_radius_in < 0 or row.value <= 0:
                continue
            rows.append(row)
    if header != list(CHART_COLUMNS):
        return ()
    return tuple(rows)


def _norm_material(value: str | None) -> str:
    return " ".join(str(value or "").casefold().split())


def matching_bend_rows(
    rows: tuple[BendChartRow, ...] | list[BendChartRow],
    *,
    material: str | None,
    thickness_in: float,
    inside_radius_in: float,
    punch_radius_in: float | None = None,
    die_opening_in: float | None = None,
) -> tuple[BendChartRow, ...]:
    """Chart rows for this material, thickness, radius, and any stated tooling."""
    want = _norm_material(material)
    if not want:
        return ()
    found: list[BendChartRow] = []
    for row in rows:
        if _norm_material(row.material) != want:
            continue
        if abs(row.thickness_in - thickness_in) > 0.0005:
            continue
        if abs(row.inside_radius_in - inside_radius_in) > 0.0005:
            continue
        if punch_radius_in is not None and abs(row.punch_radius_in - punch_radius_in) > 0.0005:
            continue
        if die_opening_in is not None and abs(row.die_opening_in - die_opening_in) > 0.0005:
            continue
        found.append(row)
    return tuple(found)


def allowance_and_deduction(
    row: BendChartRow,
    *,
    thickness_in: float,
    inside_radius_in: float,
) -> tuple[float, float]:
    """90° bend allowance and bend deduction from a chart row. No default K."""
    if row.method == "k":
        allowance = (math.pi / 2.0) * (inside_radius_in + row.value * thickness_in)
        deduction = 2.0 * (inside_radius_in + thickness_in) - allowance
    elif row.method == "ba":
        allowance = row.value
        deduction = 2.0 * (inside_radius_in + thickness_in) - allowance
    else:
        deduction = row.value
        allowance = 2.0 * (inside_radius_in + thickness_in) - deduction
    return allowance, deduction


def _specifies_bend(read: BendRead) -> bool:
    """True when the drawing is trying to state a bend, not only a view name."""
    if read.bend_count in (1, 2):
        return True
    return bool(read.bend_word and read.angles)


def _callout_label(read: BendRead) -> str:
    labels: list[str] = []
    if read.up_down:
        labels.append("UP/DOWN")
    if read.angles:
        labels.append("bend angle")
    if read.radius_in is not None:
        labels.append("bend radius")
    if read.formed_word:
        labels.append("FORMED")
    if read.bend_word:
        labels.append("BEND")
    if read.brake:
        labels.append("press brake")
    if read.view_count >= 2:
        labels.append("multiple views")
    return ", ".join(labels) or "bend"


def _blocking_reason(read: BendRead) -> str | None:
    """A formed part the calculator must not develop. None if it is flat or simple."""
    if not read.callout:
        return None
    if read.hem:
        return "hem is not a simple bend"
    if read.offset:
        return "offset/jog is not a simple bend"
    if read.bend_count is not None and read.bend_count > 2:
        return "more than two bends"
    if read.angles and any(abs(angle - 90.0) > 0.01 for angle in read.angles):
        return "bend angle is not 90°"
    if read.count_flag:
        return None
    if read.radius_ambiguous:
        return "inside radius is ambiguous"
    if _specifies_bend(read) and read.radius_in is None:
        return "inside radius was not on the drawing"
    if len(read.conventions) > 1:
        return "dimension convention is ambiguous"
    if _specifies_bend(read) and not read.conventions:
        return "dimension convention was not stated (inside, outside, or mold-line)"
    return None


def _ready_for_chart(read: BendRead) -> bool:
    if read.bend_count not in (1, 2):
        return False
    if not read.angles or any(abs(angle - 90.0) > 0.01 for angle in read.angles):
        return False
    if read.radius_in is None or len(read.conventions) != 1:
        return False
    return True


def _developed_length(
    read: BendRead,
    *,
    allowance: float,
    deduction: float,
) -> float:
    legs = sum(read.legs_in)
    count = int(read.bend_count or 0)
    if read.conventions == ("inside",):
        return legs + allowance * count
    return legs - deduction * count


def _line_note(
    read: BendRead,
    row: BendChartRow,
    *,
    thickness_in: float,
    allowance: float,
    deduction: float,
    developed: float,
) -> str:
    legs = ", ".join(f"{leg:g}" for leg in read.legs_in)
    return (
        "flat pattern: "
        f"legs {legs} in; "
        f"convention {read.conventions[0]}; "
        f"thickness {thickness_in:g} in; "
        f"inside radius {read.radius_in:g} in; "
        f"bend allowance {allowance:.6g} in; "
        f"bend deduction {deduction:.6g} in; "
        f"source {CHART_NAME} "
        f"material={row.material} "
        f"thickness_in={row.thickness_in:g} "
        f"inside_radius_in={row.inside_radius_in:g} "
        f"punch_radius_in={row.punch_radius_in:g} "
        f"die_opening_in={row.die_opening_in:g} "
        f"method={row.method} "
        f"value={row.value:g}; "
        f"developed length {developed:.6g} in; "
        f"width {read.width_in:g} in; "
        f"ops Profile, Bend; "
        f"bend count {read.bend_count} from {read.count_source}"
    )


def evaluate_formed(
    text: str,
    *,
    material: str | None,
    thickness_in: float | None,
    chart: tuple[BendChartRow, ...] | list[BendChartRow] | None = None,
) -> FlatPattern | None:
    """None when the drawing is a flat plate. Otherwise a flag or a developed flat.

    Flat length is the sum of the legs plus one bend allowance per bend
    (inside dimensions) or minus one bend deduction per bend (outside or
    mold-line). Mold-line means the outside mold line. The allowance or
    deduction comes only from a chart row.
    """
    read = read_bends(text)
    if read.hem:
        return FlatPattern(flag="hem is not a simple bend")
    if read.offset:
        return FlatPattern(flag="offset/jog is not a simple bend")
    if read.angles and any(abs(angle - 90.0) > 0.01 for angle in read.angles):
        return FlatPattern(flag="bend angle is not 90°")
    if read.count_flag:
        return FlatPattern(flag=read.count_flag, flag_field="bend count")
    if not read.callout:
        return None
    blocked = _blocking_reason(read)
    if blocked:
        return FlatPattern(flag=blocked)
    if not _ready_for_chart(read):
        return FlatPattern(
            flag=(
                f"bend callout ({_callout_label(read)}); "
                "not quoting it as a flat laser plate"
            )
        )
    if len(read.legs_in) != int(read.bend_count or 0) + 1:
        return FlatPattern(flag="leg count does not match the bend count")
    if read.width_in is None:
        return FlatPattern(flag="width along the bend was not on the drawing")
    if thickness_in is None:
        return FlatPattern(flag="thickness was not on the drawing; no bend chart lookup")
    rows = tuple(chart) if chart is not None else load_bend_chart()
    found = matching_bend_rows(
        rows,
        material=material,
        thickness_in=float(thickness_in),
        inside_radius_in=float(read.radius_in or 0),
        punch_radius_in=read.punch_radius_in,
        die_opening_in=read.die_opening_in,
    )
    shown = material or "this material"
    if len(found) > 1:
        return FlatPattern(
            flag=(
                f"more than one press brake chart row for {shown} at "
                f"{float(thickness_in):g} in, inside radius "
                f"{float(read.radius_in or 0):g} in; not picking a tooling row"
            )
        )
    if not found:
        return FlatPattern(
            flag=(
                f"no press brake chart row for {shown} at {float(thickness_in):g} in, "
                f"inside radius {float(read.radius_in or 0):g} in"
            )
        )
    row = found[0]
    allowance, deduction = allowance_and_deduction(
        row,
        thickness_in=float(thickness_in),
        inside_radius_in=float(read.radius_in or 0),
    )
    developed = _developed_length(read, allowance=allowance, deduction=deduction)
    if developed <= 0 or read.width_in <= 0:
        return FlatPattern(flag="flat length is not positive; not inventing a flat")
    return FlatPattern(
        developed_length_in=developed,
        width_in=float(read.width_in),
        bend_count=int(read.bend_count or 0),
        bend_allowance_in=allowance,
        bend_deduction_in=deduction,
        line_note=_line_note(
            read,
            row,
            thickness_in=float(thickness_in),
            allowance=allowance,
            deduction=deduction,
            developed=developed,
        ),
        operations=("Profile", "Bend"),
    )


def formed_flag(text: str) -> str | None:
    """Reason after ``FLAG: formed part —``, or None when the part is flat."""
    decision = evaluate_formed(text, material=None, thickness_in=None)
    if decision is None:
        return None
    return decision.flag
