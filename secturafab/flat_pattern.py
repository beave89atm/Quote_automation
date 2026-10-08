"""PDF-only bend callouts and the flat-pattern formula hook.

The bend count comes from ``quote_core/bend_conventions.yaml``. The flat
length comes only from ``secturafab/flat_formula.py`` (``flat_length_in``).
That function ships unset. There is no K-factor default and no fallback
math. The flat width is the drawing width.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .flat_formula import flat_length_in


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
    count_flag: str | None = None
    count_source: str = ""
    citations: tuple[str, ...] = ()
    plane_flag: str | None = None


_HEM_RE = re.compile(r"(?i)\bHEMS?\b")
_OFFSET_RE = re.compile(r"(?i)\b(?:OFFSETS?|JOGS?|JOGGLES?)\b")
_FORMED_RE = re.compile(r"(?i)\bFORMED\b")
_BRAKE_RE = re.compile(r"(?i)\bBRAKE\b")
_BEND_WORD_RE = re.compile(r"(?i)\bBENDS?\b")
_UP_DOWN_RE = re.compile(r"(?i)(?<![A-Z0-9])(?:UP|DOWN)(?![A-Z0-9])")
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


def _extract_bend_count(text: str) -> BendCount:
    """Count bends from the conventions library. Do not guess."""
    from quote_core.bend_conventions import detect_bends

    found = detect_bends(text)
    if found.flag:
        return BendCount(flag=found.flag)
    if found.plane_flag and found.count not in (None, 0):
        return BendCount(count=found.count, flag=found.plane_flag)
    ids = list(dict.fromkeys(
        [bend.convention_id for bend in found.bends]
        + [item for bend in found.bends for item in bend.corroboration]
    ))
    source = ", ".join(ids) if ids else "no bend callouts"
    return BendCount(count=0 if found.count is None else found.count, source=source)


def read_bends(text: str, drawings: list | None = None) -> BendRead:
    """Parse bend callouts. Does not guess a radius, angle, or convention."""
    from quote_core.bend_conventions import detect_bends, mask_false_positives

    blob = mask_false_positives(str(text or ""))
    detection = detect_bends(blob, drawings, already_masked=True)
    angles = tuple(float(match.group(1)) for match in _ANGLE_RE.finditer(blob))
    radii = [
        value
        for rx in _RADIUS_RES
        for match in rx.finditer(blob)
        if (value := _inches(match.group(1))) is not None
    ]
    radius, radius_ambiguous = _unique_inches(radii)
    counted = BendCount(
        count=None if detection.flag else detection.count,
        flag=detection.flag,
        source=", ".join(dict.fromkeys(
            [bend.convention_id for bend in detection.bends]
            + [item for bend in detection.bends for item in bend.corroboration]
        )),
    )
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
            bool(detection.flag),
            bool(detection.plane_flag),
        )
    )
    citations = tuple(dict.fromkeys(
        [bend.convention_id for bend in detection.bends]
        + [item for bend in detection.bends for item in bend.corroboration]
    ))
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
        count_flag=counted.flag,
        count_source=counted.source,
        citations=citations,
        plane_flag=detection.plane_flag,
    )


FORMULA_NOT_SET = "flat pattern formula not set"


@dataclass(frozen=True)
class FlatPattern:
    """A refuse reason, or a developed flat. ``flag`` None and no length means unused."""

    flag: str | None = None
    flag_field: str = "formed part"
    developed_length_in: float | None = None
    width_in: float | None = None
    bend_count: int | None = None
    line_note: str = ""
    operations: tuple[str, ...] = ()


def _specifies_bend(read: BendRead) -> bool:
    """True when the drawing is trying to state a bend, not only a view name."""
    if read.bend_count is not None and read.bend_count >= 1:
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
    if read.plane_flag:
        return read.plane_flag
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


def _ready_for_formula(read: BendRead) -> bool:
    if read.bend_count is None or read.bend_count < 1:
        return False
    if not read.angles or any(abs(angle - 90.0) > 0.01 for angle in read.angles):
        return False
    if read.radius_in is None or len(read.conventions) != 1:
        return False
    return True


def _line_note(
    read: BendRead,
    *,
    thickness_in: float,
    developed: float,
) -> str:
    legs = ", ".join(f"{leg:g}" for leg in read.legs_in)
    cites = ", ".join(read.citations) or read.count_source
    return (
        "flat pattern: "
        f"legs {legs} in; "
        f"convention {read.conventions[0]}; "
        f"thickness {thickness_in:g} in; "
        f"inside radius {read.radius_in:g} in; "
        f"bend count {read.bend_count}; "
        f"flat length {developed:.6g} in; "
        f"width {read.width_in:g} in from the drawing; "
        f"Bend NumberOfBends = {read.bend_count} "
        f"({cites})"
    )


def _positive_length(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    length = float(value)
    if length <= 0 or length != length or length == float("inf"):
        return None
    return length


def evaluate_formed(
    text: str,
    *,
    thickness_in: float | None,
    drawings: list | None = None,
) -> FlatPattern | None:
    """None when the drawing is a flat plate. Otherwise a flag or a developed flat.

    Hems, offsets, non-90° bends, a missing or ambiguous radius, an
    ambiguous dimension convention, and bends that are not in one plane
    are flagged before ``flat_length_in`` is called. The flat length is
    whatever that function returns. The width is the drawing width.
    """
    read = read_bends(text, drawings)
    if read.hem:
        return FlatPattern(flag="hem is not a simple bend")
    if read.offset:
        return FlatPattern(flag="offset/jog is not a simple bend")
    if read.plane_flag:
        return FlatPattern(flag=read.plane_flag)
    if read.angles and any(abs(angle - 90.0) > 0.01 for angle in read.angles):
        return FlatPattern(flag="bend angle is not 90°")
    if read.count_flag:
        return FlatPattern(flag=read.count_flag, flag_field="bend count")
    if not read.callout:
        return None
    blocked = _blocking_reason(read)
    if blocked:
        return FlatPattern(flag=blocked)
    if not _ready_for_formula(read):
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
        return FlatPattern(flag="thickness was not on the drawing")
    raw = flat_length_in(
        read.legs_in,
        float(thickness_in),
        float(read.radius_in or 0),
        int(read.bend_count or 0),
    )
    if raw is None:
        return FlatPattern(flag=FORMULA_NOT_SET)
    developed = _positive_length(raw)
    if developed is None:
        return FlatPattern(flag="flat length is not positive; not inventing a flat")
    return FlatPattern(
        developed_length_in=developed,
        width_in=float(read.width_in),
        bend_count=int(read.bend_count or 0),
        line_note=_line_note(
            read,
            thickness_in=float(thickness_in),
            developed=developed,
        ),
        operations=("Profile", "Bend"),
    )


def formed_flag(text: str) -> str | None:
    """Reason after ``FLAG: formed part —``, or None when the part is flat."""
    decision = evaluate_formed(text, thickness_in=None)
    if decision is None:
        return None
    return decision.flag
