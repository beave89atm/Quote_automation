"""PDF-only bend callouts. A formed part is not a flat laser plate.

Hem, offset/jog, a non-90° angle, more than two bends, a missing inside
radius, and an ambiguous dimension convention are refused here. A later
step can still flat-pattern a simple one- or two-bend 90° part from the
press-brake chart. This module does not invent a K-factor.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


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


_HEM_RE = re.compile(r"(?i)\bHEMS?\b")
_OFFSET_RE = re.compile(r"(?i)\b(?:OFFSETS?|JOGS?|JOGGLES?)\b")
_FORMED_RE = re.compile(r"(?i)\bFORMED\b")
_BRAKE_RE = re.compile(r"(?i)\bBRAKE\b")
_BEND_WORD_RE = re.compile(r"(?i)\bBENDS?\b")
_UP_DOWN_RE = re.compile(r"(?i)(?<![A-Z0-9])(?:UP|DOWN)(?![A-Z0-9])")
_BEND_DIR_RE = re.compile(r"(?i)\bBEND\s+(?:UP|DOWN)\b")
_COUNT_RE = re.compile(r"(?i)\b(\d+)\s*BENDS?\b")
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
    counts = [int(match.group(1)) for match in _COUNT_RE.finditer(blob)]
    directions = _BEND_DIR_RE.findall(blob)
    bend_count: int | None
    if counts and len(set(counts)) > 1:
        bend_count = -1
    elif counts and directions and counts[0] != len(directions):
        bend_count = -1
    elif counts:
        bend_count = counts[0]
    elif directions:
        bend_count = len(directions)
    else:
        bend_count = None
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
            bend_count is not None,
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
        bend_count=bend_count,
        angles=angles,
        radius_in=radius,
        radius_ambiguous=radius_ambiguous,
        conventions=tuple(conventions),
        legs_in=legs,
        width_in=width,
        view_count=view_count,
        punch_radius_in=punch,
        die_opening_in=die,
    )


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


def formed_flag(text: str) -> str | None:
    """Reason after ``FLAG: formed part —``, or None when the part is flat.

    Any bend callout is refused. A simple 90° part is still refused until
    the press-brake chart can supply the allowance. Nothing is invented.
    """
    read = read_bends(text)
    if not read.callout:
        return None
    if read.hem:
        return "hem is not a simple bend"
    if read.offset:
        return "offset/jog is not a simple bend"
    if read.bend_count is not None and read.bend_count > 2:
        return "more than two bends"
    if read.bend_count == -1:
        return "bend count is ambiguous"
    if read.angles and any(abs(angle - 90.0) > 0.01 for angle in read.angles):
        return "bend angle is not 90°"
    if read.radius_ambiguous:
        return "inside radius is ambiguous"
    if read.view_count >= 2 and not _specifies_bend(read):
        return "multiple views of a formed shape"
    if _specifies_bend(read) and read.radius_in is None:
        return "inside radius was not on the drawing"
    if len(read.conventions) > 1:
        return "dimension convention is ambiguous"
    if _specifies_bend(read) and not read.conventions:
        return "dimension convention was not stated (inside, outside, or mold-line)"
    return (
        f"bend callout ({_callout_label(read)}); "
        "not quoting it as a flat laser plate"
    )
