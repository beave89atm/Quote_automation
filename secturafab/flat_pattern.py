"""PDF-only bend callouts and the flat blank.

The bend count comes from ``quote_core/bend_conventions.yaml``. When the
drawing prints a flat-pattern size, that size is the blank and the source
is ``drawing flat pattern``. Otherwise the length comes from
``secturafab/flat_formula.py`` when the legs, thickness, and radius are all
readable. K is the shop setting ``materials.flat_pattern_k_factor`` (0.33).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .flat_formula import Bend, bend_math, configured_k_factor, flat_length_in


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
    thetas: tuple[float, ...] = ()
    angle_flag: str | None = None
    basis: str | None = None
    basis_flag: str | None = None
    radii_in: tuple[float, ...] = ()
    radius_flag: str | None = None
    offset_in: float | None = None
    roll: bool = False
    cone: bool = False
    stretch: bool = False
    unfold: bool = False


_HEM_RE = re.compile(r"(?i)\b(?:HEMS?|FOLDED(?:\s+EDGES?)?)\b")
_OFFSET_RE = re.compile(r"(?i)\b(?:OFFSETS?|JOGS?|JOGGLES?)\b")
_OFFSET_LEN_RE = re.compile(
    r"(?i)\b(?:OFFSETS?|JOGS?|JOGGLES?)\s+"
    r"([0-9]+(?:\s*[- ]\s*[0-9]+\s*/\s*[0-9]+|\s*/\s*[0-9]+|\.\d+)?)"
)
_ROLL_RE = re.compile(
    r"(?i)\b(?:ROLL\s+FORM(?:ED|ING)?|ROLLED\s+(?:SECTION|SHAPE|PART)|LARGE\s+RADIUS)\b"
)
# A bare CYLINDER is a form. MASTER CYLINDER, and any other word in front
# of CYLINDER, is a part name.
_CONE_RE = re.compile(
    r"(?i)\b(?:CONES?|CONICAL|CYLINDRICAL)\b|(?<![A-Za-z][ \t])\bCYLINDERS?\b"
)
_STRETCH_RE = re.compile(
    r"(?i)\b(?:STRETCHED(?:\s+FORM)?|STRETCH\s+FORM|COMPOUND\s+FORM)\b"
)
_UNFOLD_RE = re.compile(
    r"(?i)\b(?:NON[-\s]?PARALLEL|NOT\s+PARALLEL|BOX\s+BENDS?|BENDS?\s+BOX)\b"
)
_BENDISH_RE = re.compile(r"(?i)\b(?:BENDS?|UP|DOWN)\b")
# R.13 = 0.13, R .25 = 0.25, R 3/8 = 0.375, R1/2 = 0.5, R1.5 and R1,5 stay.
_R_TOKEN_RE = re.compile(
    r"(?i)(?<![A-Z0-9])R[ \t]*"
    r"(?:(\d{1,2})[ \t]*/[ \t]*(\d{1,2})|(\.\d+)|(\d+(?:[.,]\d+)?))"
)
_FORMED_RE = re.compile(r"(?i)\bFORMED\b")
_BRAKE_RE = re.compile(r"(?i)\bBRAKE\b")
_BEND_WORD_RE = re.compile(r"(?i)\bBENDS?\b")
_UP_DOWN_RE = re.compile(r"(?i)(?<![A-Z0-9])(?:UP|DOWN)(?![A-Z0-9])")
# No word boundary after °. ° is not a word character, so °\b never matches.
_ANGLE_RE = re.compile(
    r"(?i)(?<![A-Z0-9.])(\d+(?:\.\d+)?)\s*(?:°|º|˚|DEG(?:REE)?S?\b)"
)
_BEND_NOTE_LINE_RE = re.compile(
    r"(?i)(?<![A-Z0-9])(?:UP|DOWN)(?![A-Z0-9])|\bBENDS?\b"
)
_FORMED_EVIDENCE_RE = re.compile(
    r"(?i)\bFLAT\s+PATTERN\b|\bDEVELOPED\s+(?:VIEW|BLANK|LENGTH)\b|\bFORMED\b"
)
_FLAT_LABEL_RE = re.compile(
    r"(?i)\b(?:FLAT\s+PATTERN(?:\s+VIEW)?|DEVELOPED(?:\s+(?:VIEW|BLANK|LENGTH))?|"
    r"FLAT\s+(?:SIZE|BLANK|LAYOUT))\b"
)
_FLAT_PAIR_RE = re.compile(
    r"(?i)(?<![\d.])"
    r"(\d+\s*-\s*\d+\s*/\s*\d+|\d+\s+\d+\s*/\s*\d+|\d+\s*/\s*\d+|\d+\.\d+|\.\d+|\d+)"
    r"\s*[\"″]?\s*[xX×]\s*"
    r"(\d+\s*-\s*\d+\s*/\s*\d+|\d+\s+\d+\s*/\s*\d+|\d+\s*/\s*\d+|\d+\.\d+|\.\d+|\d+)"
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
_INCH_TOKEN = (
    r"(\d+\s*[- ]\s*\d+\s*/\s*\d+|\d+\s*/\s*\d+|\d+\.\d+|\.\d+|\d+)"
)
_RADIUS_RES = (
    re.compile(rf"(?i)\bINSIDE\s+RADIUS\s+{_INCH_TOKEN}"),
    re.compile(rf"(?i)\bBEND\s+RAD(?:IUS)?\s*[.:\s]+{_INCH_TOKEN}"),
    re.compile(rf"(?i){_INCH_TOKEN}\s+BEND\s+RAD(?:IUS)?\b"),
    re.compile(rf"(?i)\bIR\s*[:=]?\s*{_INCH_TOKEN}"),
    re.compile(
        r"(?i)(?<![A-Z0-9])R[ \t]*(\.\d+|\d{1,2}[ \t]*/[ \t]*\d{1,2}|\d+(?:[.,]\d+)?)"
        r"[ \t]+TYP\b"
    ),
)
_CONVENTION_RES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("inside", re.compile(r"(?i)\bDIMENSIONS?\s+INSIDE\b|\bINSIDE\s+DIMENSIONS?\b")),
    ("outside", re.compile(r"(?i)\bDIMENSIONS?\s+OUTSIDE\b|\bOUTSIDE\s+DIMENSIONS?\b|\bOUTSIDE\s+SHARP\b")),
    (
        "mold-line",
        re.compile(r"(?i)\bDIMENSIONS?\s+MOLD[-\s]?LINE\b|\bMOLD[-\s]?LINE\s+DIMENSIONS?\b"),
    ),
    (
        "tangent",
        re.compile(
            r"(?i)\b(?:DIMENSIONS?\s+TANGENT|TANGENT\s+(?:DIMENSIONS?|LENGTHS?)|TO\s+TANGENT)\b"
        ),
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
    plain = re.fullmatch(r"\d+(?:\.\d+)?|\.\d+", text)
    if plain:
        return float(plain.group(0).replace(",", "."))
    return None


def _r_token_inches(match: re.Match[str]) -> float | None:
    """One R token. The leading decimal stays in front of the digits."""
    if match.group(1) and match.group(2):
        denominator = float(match.group(2))
        if denominator == 0:
            return None
        return float(match.group(1)) / denominator
    if match.group(3):
        return float(match.group(3))
    raw = match.group(4)
    if not raw:
        return None
    return _inches(raw.replace(",", "."))


def _unique_inches(values: list[float]) -> tuple[float | None, bool]:
    if not values:
        return None, False
    first = values[0]
    if any(abs(value - first) > 0.0005 for value in values[1:]):
        return None, True
    return first, False


_INCLUDED_ANGLE_RE = re.compile(
    r"(?i)\bINCLUDED(?:\s+ANGLE)?\s+(\d+(?:\.\d+)?)\s*(?:°|DEG(?:REE)?S?)?"
)


def _theta_from_line(line: str) -> tuple[float | None, str | None]:
    """θ from one line, or a flag when the angle convention is not clear.

    A bend callout (BEND / UP / DOWN) states the change from flat.
    INCLUDED states the inside angle, and θ = 180 − included.
    A bare 90° is the same either way. Any other bare angle is a flag.
    """
    included_match = _INCLUDED_ANGLE_RE.search(line)
    if included_match:
        theta = 180.0 - float(included_match.group(1))
        if theta <= 0.0 or theta > 180.0:
            return None, "bend angle is not a change from flat"
        return theta, None
    numbers = [float(match.group(1)) for match in _ANGLE_RE.finditer(line)]
    if not numbers:
        return None, None
    if len(numbers) != 1:
        return None, "angle convention can't be determined"
    number = numbers[0]
    bendish = bool(_BENDISH_RE.search(line))
    if bendish or abs(number - 90.0) <= 0.01:
        theta = number
    else:
        return None, "angle convention can't be determined"
    if theta <= 0.0 or theta > 180.0:
        return None, "bend angle is not a change from flat"
    return theta, None


def _assign_thetas(
    found: list[float],
    bend_count: int | None,
) -> tuple[tuple[float, ...], str | None]:
    if bend_count is None or bend_count < 1:
        return tuple(found), None
    if not found:
        return (), "bend angle was not on the drawing"
    if len(found) == bend_count:
        return tuple(found), None
    if all(abs(angle - found[0]) <= 0.01 for angle in found):
        return tuple(found[0] for _ in range(bend_count)), None
    return (), "angle convention can't be determined"


def _read_angles(text: str, bend_count: int | None) -> tuple[tuple[float, ...], str | None]:
    """θ from bend notes. A tolerance or chamfer on another line is not θ.

    Included angle still counts when the bend note itself has no degrees.
    A bare non-90° is ambiguous only when no bend note stated an angle.
    """
    callout: list[float] = []
    included: list[float] = []
    stray: list[float] = []
    stray_flag: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        bend_note = bool(_BEND_NOTE_LINE_RE.search(line))
        if bend_note:
            theta, flag = _theta_from_line(line)
            if flag:
                return (), flag
            if theta is not None:
                callout.append(theta)
            continue
        if _INCLUDED_ANGLE_RE.search(line):
            theta, flag = _theta_from_line(line)
            if flag:
                return (), flag
            if theta is not None:
                included.append(theta)
            continue
        theta, flag = _theta_from_line(line)
        if flag:
            stray_flag = flag
        elif theta is not None:
            stray.append(theta)
    if callout:
        return _assign_thetas(callout, bend_count)
    if included:
        return _assign_thetas(included, bend_count)
    if stray_flag:
        return (), stray_flag
    return _assign_thetas(stray, bend_count)


def _per_bend_radii(text: str) -> list[float]:
    """R tokens on a bend-direction line. Global 'INSIDE RADIUS' is separate."""
    found: list[float] = []
    for raw in text.splitlines():
        if not _BENDISH_RE.search(raw):
            continue
        for match in _R_TOKEN_RE.finditer(raw):
            value = _r_token_inches(match)
            if value is not None:
                found.append(value)
    return found


def _assign_radii(
    global_radius: float | None,
    per_bend: list[float],
    bend_count: int | None,
    ambiguous: bool,
) -> tuple[tuple[float, ...], str | None]:
    if ambiguous:
        return (), "inside radius is ambiguous"
    count = int(bend_count or 0)
    if count < 1:
        if global_radius is None:
            return (), None
        return (global_radius,), None
    if per_bend and len(per_bend) not in {1, count}:
        return (), "inside radius is ambiguous"
    chosen = per_bend[0] if len(per_bend) == 1 else None
    if len(per_bend) == count:
        if global_radius is not None and any(
            abs(value - global_radius) > 0.0005 for value in per_bend
        ):
            return (), "inside radius is ambiguous"
        return tuple(per_bend), None
    if chosen is not None:
        if global_radius is not None and abs(chosen - global_radius) > 0.0005:
            return (), "inside radius is ambiguous"
        return tuple(chosen for _ in range(count)), None
    if global_radius is None:
        return (), "inside radius was not on the drawing"
    return tuple(global_radius for _ in range(count)), None


def _basis_from(conventions: tuple[str, ...], specified: bool) -> tuple[str | None, str | None]:
    names = set(conventions)
    outside = bool(names & {"outside", "mold-line"})
    tangent = "tangent" in names
    inside = "inside" in names
    if inside and (outside or tangent):
        return None, "dimension basis is ambiguous"
    if tangent and outside:
        return None, "dimension basis is ambiguous"
    if inside:
        return None, "inside dimensions were not converted to tangent or outside"
    if tangent:
        return "tangent", None
    if outside:
        return "outside", None
    if specified:
        return None, "dimension basis was not stated (tangent or outside)"
    return None, None


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


def read_bends(
    text: str,
    drawings: list | None = None,
    text_blocks: list | None = None,
) -> BendRead:
    """Parse bend callouts. Does not guess a radius, angle, or convention.

    ``text_blocks`` is the optional PDF text layer (``text``, ``dir``, ``bbox``).
    Geometry uses it only to corroborate a bend note. See ``detect_bends``.
    """
    from quote_core.bend_conventions import detect_bends, mask_false_positives

    blob = mask_false_positives(str(text or ""))
    detection = detect_bends(
        blob,
        drawings,
        already_masked=True,
        text_blocks=text_blocks,
    )
    angles = tuple(float(match.group(1)) for match in _ANGLE_RE.finditer(blob))
    radii = [
        value
        for rx in _RADIUS_RES
        for match in rx.finditer(blob)
        if (value := _inches(match.group(1).replace(",", "."))) is not None
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
    thetas, angle_flag = _read_angles(blob, counted.count)
    if any(abs(theta - 180.0) <= 0.01 for theta in thetas) and not angle_flag:
        angle_flag = "hem is not a simple bend"
    radii, radius_flag = _assign_radii(
        radius,
        _per_bend_radii(blob),
        counted.count,
        radius_ambiguous,
    )
    basis, basis_flag = _basis_from(tuple(conventions), bool(counted.count))
    offset_lengths = [
        value
        for match in _OFFSET_LEN_RE.finditer(blob)
        if (value := _inches(match.group(1))) is not None
    ]
    offset_in, offset_ambiguous = _unique_inches(offset_lengths)
    if offset_ambiguous:
        offset_in = None
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
    hem = bool(_HEM_RE.search(blob)) or angle_flag == "hem is not a simple bend"
    offset = bool(_OFFSET_RE.search(blob))
    roll = bool(_ROLL_RE.search(blob))
    cone = bool(_CONE_RE.search(blob))
    stretch = bool(_STRETCH_RE.search(blob))
    unfold = bool(_UNFOLD_RE.search(blob))
    formed_word = bool(_FORMED_RE.search(blob))
    brake = bool(_BRAKE_RE.search(blob))
    bend_word = bool(_BEND_WORD_RE.search(blob))
    up_down = bool(_UP_DOWN_RE.search(blob))
    view_count = len(_VIEW_RE.findall(blob))
    callout = any(
        (
            hem,
            offset,
            roll,
            cone,
            stretch,
            unfold,
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
        thetas=() if angle_flag else thetas,
        angle_flag=angle_flag,
        basis=None if basis_flag else basis,
        basis_flag=basis_flag,
        radii_in=() if radius_flag else radii,
        radius_flag=radius_flag,
        offset_in=offset_in,
        roll=roll,
        cone=cone,
        stretch=stretch,
        unfold=unfold,
    )


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
    # ``drawing flat pattern`` when the sheet prints the blank. ``formula``
    # when legs, thickness, and radius were readable and the formula ran.
    length_source: str = ""


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


def _segments(read: BendRead) -> tuple[float, ...] | None:
    """Tangent or outside lengths, including a dimensioned jog straight."""
    count = int(read.bend_count or 0)
    if len(read.legs_in) == count + 1:
        return read.legs_in
    if (
        read.offset
        and read.offset_in is not None
        and count == 2
        and len(read.legs_in) == 2
    ):
        return (read.legs_in[0], read.offset_in, read.legs_in[1])
    return None


def _offset_ready(read: BendRead) -> bool:
    """A jog is usable when both bends exist and the connecting straight is dimensioned."""
    if not read.offset:
        return True
    if read.bend_count is None or read.bend_count < 2:
        return False
    return _segments(read) is not None


def _k_text(k_factor: float) -> str:
    text = f"{k_factor:.6f}".rstrip("0").rstrip(".")
    return f"K={text} assumed"


def _line_note(
    read: BendRead,
    *,
    segments: tuple[float, ...],
    worked: tuple,
    developed: float,
    k_factor: float,
) -> str:
    segment_text = ", ".join(f"{leg:g}" for leg in segments)
    bends = "; ".join(
        (
            f"bend {index} R {item.radius_in:g} in, "
            f"θ {item.angle_deg:g}°, "
            f"T {item.thickness_in:g} in, "
            f"K {item.k_factor:g}, "
            f"BA {item.bend_allowance_in:.6f} in, "
            f"BD {item.bend_deduction_in:.6f} in"
        )
        for index, item in enumerate(worked, start=1)
    )
    cites = ", ".join(read.citations) or read.count_source
    return (
        "flat pattern: "
        f"basis {read.basis}; "
        f"{_k_text(k_factor)}; "
        f"segments {segment_text} in (sum {sum(segments):.6f}); "
        f"{bends}; "
        f"flat length {developed:.6f} in; "
        f"width {read.width_in:g} in from the drawing; "
        f"Bend NumberOfBends = {read.bend_count} "
        f"({cites})"
    )


def _drawing_flat_pair(text: str) -> tuple[float, float] | None:
    """Overall blank printed on a FLAT PATTERN / FLAT / DEVELOPED view.

    The pair is used in the order printed. None when the view is missing,
    the pair is missing, or more than one pair is printed.
    """
    from .item_desc import looks_like_drawing_sheet, looks_like_page_outline

    lines = str(text or "").splitlines()
    found: list[tuple[float, float]] = []
    for index, line in enumerate(lines):
        if not _FLAT_LABEL_RE.search(line):
            continue
        window = "\n".join(lines[max(0, index - 4) : index + 8])
        for match in _FLAT_PAIR_RE.finditer(window):
            width = _inches(match.group(1))
            length = _inches(match.group(2))
            if width is None or length is None:
                continue
            if width <= 0.25 or length <= 0.25 or max(width, length) > 240:
                continue
            if looks_like_drawing_sheet(width, length) or looks_like_page_outline(width, length):
                continue
            pair = (width, length)
            if not any(abs(pair[0] - old[0]) <= 0.0005 and abs(pair[1] - old[1]) <= 0.0005 for old in found):
                found.append(pair)
    if len(found) != 1:
        return None
    return found[0]


def _drawing_flat_note(read: BendRead, width: float, length: float) -> str:
    cites = ", ".join(read.citations) or read.count_source or "bend notes"
    return (
        "flat pattern: source drawing flat pattern; "
        f"flat {width:g} x {length:g} in; "
        f"Bend NumberOfBends = {read.bend_count} "
        f"({cites})"
    )


def _positive_length(value: float) -> float | None:
    if value <= 0 or value != value or value == float("inf"):
        return None
    return value


def _has_formed_evidence(read: BendRead, text: str) -> bool:
    """True when the text says the part is formed, even if the count is missing."""
    if read.callout or read.formed_word or read.bend_word or read.up_down:
        return True
    if read.count_flag or read.plane_flag:
        return True
    if read.bend_count not in (None, 0):
        return True
    return bool(_FORMED_EVIDENCE_RE.search(text or ""))


def evaluate_formed(
    text: str,
    *,
    thickness_in: float | None,
    drawings: list | None = None,
    text_blocks: list | None = None,
) -> FlatPattern | None:
    """None when the drawing is a flat plate. Otherwise a flag or a developed flat.

    A printed FLAT PATTERN size is the blank. Kyle's formula runs only when
    that size is not printed and the legs, thickness, and radius are all
    readable. Hems, rolled sections, cones, compound forms, nonparallel
    bends, a missing radius, an unclear angle, and an inside or mixed
    dimension chain are flagged before the formula runs. A stated bend
    angle of any size is allowed. θ is the change from flat.

    Formed evidence with a bend count of 0 or unknown is a flag. It is not
    a flat plate.
    """
    read = read_bends(text, drawings, text_blocks=text_blocks)
    if read.hem:
        return FlatPattern(flag="hem is not a simple bend")
    if read.roll:
        return FlatPattern(flag="rolled or large-radius section is not a straight bend")
    if read.cone:
        return FlatPattern(flag="cone or cylinder is not a straight-bend flat")
    if read.stretch:
        return FlatPattern(flag="compound or stretched form is not a straight-bend flat")
    if read.unfold:
        return FlatPattern(flag="bend lines are not parallel; needs a 2D unfold")
    if read.plane_flag:
        return FlatPattern(flag=read.plane_flag)
    if read.offset and not _offset_ready(read):
        return FlatPattern(flag="offset/jog is not dimensioned")
    if read.count_flag:
        return FlatPattern(flag=read.count_flag, flag_field="bend count")
    if read.bend_count in (None, 0) and _has_formed_evidence(read, text):
        return FlatPattern(
            flag="formed evidence but the bend count is 0 or unknown",
        )
    if not read.callout:
        return None
    printed = _drawing_flat_pair(text) if read.bend_count and read.bend_count > 0 else None
    if printed is not None:
        if thickness_in is None:
            return FlatPattern(flag="thickness was not on the drawing")
        width, length = printed
        return FlatPattern(
            developed_length_in=length,
            width_in=width,
            bend_count=int(read.bend_count or 0),
            line_note=_drawing_flat_note(read, width, length),
            operations=("Profile", "Bend"),
            length_source="drawing flat pattern",
        )
    if read.angle_flag:
        return FlatPattern(flag=read.angle_flag)
    if read.radius_flag:
        return FlatPattern(flag=read.radius_flag)
    if read.basis_flag:
        return FlatPattern(flag=read.basis_flag)
    if read.bend_count is None or read.bend_count < 1 or not read.basis:
        return FlatPattern(
            flag=(
                f"bend callout ({_callout_label(read)}); "
                "not quoting it as a flat laser plate"
            )
        )
    if len(read.thetas) != read.bend_count or len(read.radii_in) != read.bend_count:
        return FlatPattern(
            flag=(
                f"bend callout ({_callout_label(read)}); "
                "not quoting it as a flat laser plate"
            )
        )
    segments = _segments(read)
    if segments is None:
        return FlatPattern(flag="leg count does not match the bend count")
    if read.width_in is None:
        return FlatPattern(flag="width along the bend was not on the drawing")
    if thickness_in is None:
        return FlatPattern(flag="thickness was not on the drawing")
    k_factor = configured_k_factor()
    bends = tuple(
        Bend(
            radius_in=radius,
            angle_deg=theta,
            thickness_in=float(thickness_in),
            k_factor=k_factor,
        )
        for radius, theta in zip(read.radii_in, read.thetas, strict=True)
    )
    developed = _positive_length(
        flat_length_in(segments, bends, basis=read.basis)
    )
    if developed is None:
        return FlatPattern(flag="flat length is not positive; not inventing a flat")
    worked = tuple(
        bend_math(bend.radius_in, bend.angle_deg, bend.thickness_in, bend.k_factor)
        for bend in bends
    )
    return FlatPattern(
        developed_length_in=developed,
        width_in=float(read.width_in),
        bend_count=int(read.bend_count or 0),
        line_note=_line_note(
            read,
            segments=segments,
            worked=worked,
            developed=developed,
            k_factor=k_factor,
        ),
        operations=("Profile", "Bend"),
        length_source="formula",
    )


def formed_flag(text: str) -> str | None:
    """Reason after ``FLAG: formed part —``, or None when the part is flat."""
    decision = evaluate_formed(text, thickness_in=None)
    if decision is None:
        return None
    return decision.flag
