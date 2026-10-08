"""PDF-only bend callouts and the flat blank.

The bend count comes from ``quote_core/bend_conventions.yaml``. A printed
flat size is the blank only when it is the FLAT PATTERN view's overall
size: not a chamfer, angle, thread, or tolerance, and plausible next to
the thickness and the part's other dimensions. The source is ``drawing
flat pattern``. Otherwise the length comes from ``secturafab/flat_formula.py``
when no flat view was printed and the legs, thickness, and radius are all
readable. K is the shop setting ``materials.flat_pattern_k_factor`` (0.33).
"""

from __future__ import annotations

import math
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
# Separators stay on the note line. A newline would pull the next dimension in.
_RADIUS_RES = (
    re.compile(rf"(?i)\bINSIDE[ \t]+RADIUS[ \t]+{_INCH_TOKEN}"),
    re.compile(rf"(?i)\bBEND[ \t]+RAD(?:IUS)?[ \t]*[.: \t]+{_INCH_TOKEN}"),
    re.compile(rf"(?i){_INCH_TOKEN}[ \t]+BEND[ \t]+RAD(?:IUS)?\b"),
    re.compile(rf"(?i)\bIR[ \t]*[:=]?[ \t]*{_INCH_TOKEN}"),
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
        for line in blob.splitlines()
        for rx in _RADIUS_RES
        for match in rx.finditer(line)
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


# A printed blank has to be the flat-pattern view's overall size. A chamfer,
# a thread, a tolerance, or an N X angle pair is never that size.
FLAT_SIZE_UNCLEAR = "flat pattern size is not clear"
ROUND_STOCK_BEND_FLAG = "tube or round-stock bend notes are formed evidence"
TEMPLATE_WORDING_FLAG = "template wording only, review"
# Kannon sheet and plate blanks do not exceed 120 in.
_MAX_BLANK_IN = 120.0
_UNSAFE_SIZE_LINE_RE = re.compile(
    r"(?i)\b(?:CHAMFERS?|COUNTERSINK|COUNTER\s*SINK|CSK|THREADS?|"
    r"UNC|UNF|UNEF|NPT|NPS|TAP(?:PED)?|TOL(?:ERANCE)?S?|ANGULAR)\b|[±°º˚]"
)
_DEGREE_WORD_RE = re.compile(r"(?i)\bDEG(?:REE)?S?\b")
_NOT_FLAT_SIZE_LINE_RE = re.compile(
    r"(?i)\b(?:PLATE\s+SIZE|SHEET\s+SIZE|PAGE\s+SIZE|DRAWING\s+SIZE)\b"
)
_STOCK_FOLLOW_RE = re.compile(r"\s*[xX×]")
_ANGLE_LIKE_IN = (15.0, 22.5, 30.0, 45.0, 60.0, 82.0, 90.0)
_BARE_DIM_RE = re.compile(rf"(?i)^{_INCH_TOKEN}\s*(?:\"|″|IN(?:CH(?:ES)?)?)?$")
_OTHER_DIM_RE = re.compile(rf"(?i)(?<![\d.]){_INCH_TOKEN}(?![\d./])")
_ROUND_STOCK_BEND_RE = re.compile(
    r"(?i)\b(?:CLR|C\.L\.R\.|CENTER\s*LINE\s+RADIUS|CENTERLINE\s+RADIUS)\b"
)
_TUBE_R_RE = re.compile(r"(?i)(?<![A-Z0-9])R[ \t]*(\d+\.\d+)")
_TUBE_STOCK_RE = re.compile(r"(?i)\b(?:OD|O\.D\.|WALL|TUBE|PIPE|HSS)\b")
_TEMPLATE_ANGULAR_RE = re.compile(r"(?i)\bALL\s+ANGULAR\s+DIMENSIONS\b")
_DEGREE_MARK_RE = re.compile(r"[°º˚]|(?i:\bDEG(?:REE)?S?\b)")
_TITLE_ANGLE_RE = re.compile(r"(?i)\bBEND\s+ANGLE\s*=|\bANGULAR\s*:")
_TITLE_WORD_RE = re.compile(
    r"(?i)\b(?:SIZE|REV(?:ISION)?|SCALE|DRAWN|CHECKED|TOLERANCES?|GENERAL\s+NOTES?)\b"
)
_STACK_FRACTION_DENS = {2, 4, 8, 16, 32, 64}
_NEAR_LABEL_PT = 480.0
_CLUSTER_PT = 160.0
_DIM_LINE_REACH_PT = 56.0
_ARROW_PT = 14.0


def _degree_marked(text: str) -> bool:
    return bool(_DEGREE_WORD_RE.search(text) or re.search(r"[°º˚]", text))


def _size_line_rejected(line: str) -> bool:
    return bool(_UNSAFE_SIZE_LINE_RE.search(line) or _degree_marked(line))


def _angle_like(value: float) -> bool:
    return any(abs(value - item) <= 0.02 for item in _ANGLE_LIKE_IN)


def _bare_inches(text: str) -> float | None:
    """One overall dimension, not a pair, hole, angle, or note."""
    raw = " ".join(str(text or "").strip().split())
    raw = raw.strip("()[]")
    if not raw or _size_line_rejected(raw) or _NOT_FLAT_SIZE_LINE_RE.search(raw):
        return None
    if re.search(r"[xX×Ø⌀]", raw):
        return None
    if re.search(r"(?i)\b(?:DIA|DIAM|THRU|HOLE|TYP|REF|GAUGE|THK|THICK|WALL)\b", raw):
        return None
    match = _BARE_DIM_RE.fullmatch(raw)
    if not match:
        return None
    return _inches(match.group(1))


def _accepted_size(width: float, length: float, text: str, thickness: float | None) -> bool:
    """True when the pair can be the blank, not a sheet, angle, or scrap."""
    from .item_desc import looks_like_drawing_sheet, looks_like_page_outline

    if width <= 0.25 or length <= 0.25 or max(width, length) > _MAX_BLANK_IN:
        return False
    small, big = (width, length) if width <= length else (length, width)
    if small <= 1.5 and _angle_like(big):
        return False
    if thickness is not None and (width <= thickness or length <= thickness):
        return False
    if looks_like_drawing_sheet(width, length) or looks_like_page_outline(width, length):
        return False
    return not _implausible_vs_part(width, length, text)


def _implausible_vs_part(width: float, length: float, text: str) -> bool:
    """A short side next to a much larger real overall is not the blank."""
    small = min(width, length)
    others: list[float] = []
    for line in str(text or "").splitlines():
        if _size_line_rejected(line):
            continue
        for match in _OTHER_DIM_RE.finditer(line):
            value = _inches(match.group(1))
            if value is None or value < 2.0:
                continue
            if abs(value - width) <= 0.03 or abs(value - length) <= 0.03:
                continue
            others.append(value)
    if not others:
        return False
    return small < 1.0 and max(others) >= 8.0


def _pair_rejected(
    line: str,
    match: re.Match[str],
    width: float,
    length: float,
    thickness: float | None,
) -> bool:
    if _NOT_FLAT_SIZE_LINE_RE.search(line) or _size_line_rejected(line):
        return True
    if _STOCK_FOLLOW_RE.match(line[match.end() :]):
        return True
    small, big = (width, length) if width <= length else (length, width)
    if small <= 1.5 and _angle_like(big):
        return True
    if thickness is not None and (width <= thickness or length <= thickness):
        return True
    if width <= 0.25 or length <= 0.25 or max(width, length) > _MAX_BLANK_IN:
        return True
    return False


def _neighborhood(lines: list[str], index: int, limit: int = 4) -> list[str]:
    """Label line plus a few nearby lines. A double blank ends the view."""
    picked = [lines[index]]

    def walk(step: int) -> None:
        blanks = 0
        content = 0
        cursor = index + step
        while 0 <= cursor < len(lines) and content < limit:
            line = lines[cursor]
            if not line.strip():
                blanks += 1
                if blanks >= 2:
                    break
            else:
                blanks = 0
                picked.append(line)
                content += 1
            cursor += step

    walk(-1)
    walk(1)
    return picked


def _line_marks_flat_view(line: str) -> bool:
    """A bend note or a printed W x L next to the label. A lone number does not.

    Plate stock does not. A template label with a stray title-block number
    next to it is not a flat view.
    """
    if _NOT_FLAT_SIZE_LINE_RE.search(line):
        return False
    if _FLAT_LABEL_RE.search(line) and not _FLAT_PAIR_RE.search(line):
        if not _BEND_NOTE_LINE_RE.search(line):
            return False
    if _BEND_NOTE_LINE_RE.search(line):
        return True
    return bool(_FLAT_PAIR_RE.search(line))


def _as_blocks(text_blocks: list | None) -> list[dict]:
    if not text_blocks:
        return []
    return [block for block in text_blocks if isinstance(block, dict)]


def _bbox(block: dict) -> tuple[float, float, float, float] | None:
    raw = block.get("bbox")
    if not isinstance(raw, (list, tuple)) or len(raw) < 4:
        return None
    try:
        box = (float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3]))
    except (TypeError, ValueError):
        return None
    if box[2] < box[0] or box[3] < box[1]:
        return None
    return box


def _same_page(left: dict, right: dict) -> bool:
    left_page, right_page = left.get("page"), right.get("page")
    if left_page is None or right_page is None:
        return True
    return left_page == right_page


def _box_gap(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> float:
    dx = max(left[0] - right[2], right[0] - left[2], 0.0)
    dy = max(left[1] - right[3], right[1] - left[3], 0.0)
    return math.hypot(dx, dy)


def _text_axis(block: dict) -> str | None:
    direction = block.get("dir") or ()
    try:
        dx, dy = float(direction[0]), float(direction[1])
    except (TypeError, ValueError, IndexError):
        return None
    if dx == 0.0 and dy == 0.0:
        return None
    angle = math.degrees(math.atan2(dy, dx)) % 180.0
    if min(angle, 180.0 - angle) <= 20.0:
        return "h"
    if abs(angle - 90.0) <= 20.0:
        return "v"
    return None


def _flat_view_is_real(text: str, text_blocks: list | None) -> bool:
    """A FLAT PATTERN label with a dimension or bend note next to it.

    A bare template label, with nothing around it, is not a flat view.
    """
    lines = str(text or "").splitlines()
    for index, line in enumerate(lines):
        if not _FLAT_LABEL_RE.search(line):
            continue
        if any(_line_marks_flat_view(item) for item in _neighborhood(lines, index)):
            return True
    blocks = _as_blocks(text_blocks)
    labels = [
        block
        for block in blocks
        if _bbox(block) and _FLAT_LABEL_RE.search(str(block.get("text") or ""))
    ]
    for label in labels:
        label_box = _bbox(label)
        if label_box is None:
            continue
        for block in blocks:
            if block is label or not _same_page(label, block):
                continue
            box = _bbox(block)
            if box is None or _box_gap(label_box, box) > _NEAR_LABEL_PT:
                continue
            if _line_marks_flat_view(str(block.get("text") or "")):
                return True
    return False


def _unique_pairs(pairs: list[tuple[float, float]]) -> list[tuple[float, float]]:
    found: list[tuple[float, float]] = []
    for pair in pairs:
        if any(abs(pair[0] - old[0]) <= 0.02 and abs(pair[1] - old[1]) <= 0.02 for old in found):
            continue
        found.append(pair)
    return found


def _pairs_compatible(left: tuple[float, float], right: tuple[float, float]) -> bool:
    swapped = (right[1], right[0])
    return any(
        abs(left[0] - other[0]) <= 0.02 and abs(left[1] - other[1]) <= 0.02
        for other in (right, swapped)
    )


def _inline_pairs(text: str, thickness: float | None) -> list[tuple[float, float]]:
    lines = str(text or "").splitlines()
    found: list[tuple[float, float]] = []
    for index, line in enumerate(lines):
        if not _FLAT_LABEL_RE.search(line):
            continue
        for item in _neighborhood(lines, index):
            for match in _FLAT_PAIR_RE.finditer(item):
                width = _inches(match.group(1))
                length = _inches(match.group(2))
                if width is None or length is None:
                    continue
                if _pair_rejected(item, match, width, length, thickness):
                    continue
                if not _accepted_size(width, length, text, thickness):
                    continue
                found.append((width, length))
    return _unique_pairs(found)


def _axis_overall(samples: list[tuple[float, float]]) -> tuple[float | None, bool]:
    """Largest dimension nearest the label. Conflict when two overalls compete."""
    if not samples:
        return None, False
    ordered = sorted(samples, key=lambda item: item[1])
    nearest = ordered[0][1]
    cluster = [value for value, dist in ordered if dist <= nearest + _CLUSTER_PT]
    outside = [value for value, dist in ordered if dist > nearest + _CLUSTER_PT]
    top = max(cluster)
    rivals = [value for value in cluster if abs(value - top) > 0.02]
    if rivals and top < max(rivals) * 1.5:
        return None, True
    if any(value > top + 0.5 for value in outside):
        return None, True
    return top, False


def _point_xy(point: object) -> tuple[float, float] | None:
    try:
        return (float(point.x), float(point.y))  # type: ignore[attr-defined]
    except AttributeError:
        try:
            return (float(point[0]), float(point[1]))  # type: ignore[index]
        except (TypeError, ValueError, IndexError):
            return None


def _as_line(item: object) -> tuple[float, float, float, float] | None:
    if not isinstance(item, (list, tuple)) or len(item) < 3 or item[0] != "l":
        return None
    start, end = _point_xy(item[1]), _point_xy(item[2])
    if start is None or end is None:
        return None
    return (start[0], start[1], end[0], end[1])


def _as_rect(item: object) -> tuple[float, float, float, float] | None:
    if not isinstance(item, (list, tuple)) or not item or item[0] != "re":
        return None
    rect = item[1]
    try:
        box = (float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1))
    except AttributeError:
        try:
            box = (float(rect[0]), float(rect[1]), float(rect[2]), float(rect[3]))
        except (TypeError, ValueError, IndexError):
            return None
    if box[2] < box[0] or box[3] < box[1]:
        return None
    return box


def _segment_length(segment: tuple[float, float, float, float]) -> float:
    return math.hypot(segment[2] - segment[0], segment[3] - segment[1])


def _point_segment_distance(
    px: float,
    py: float,
    segment: tuple[float, float, float, float],
) -> float:
    x1, y1, x2, y2 = segment
    dx, dy = x2 - x1, y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq <= 0:
        return math.hypot(px - x1, py - y1)
    ratio = ((px - x1) * dx + (py - y1) * dy) / length_sq
    ratio = max(0.0, min(1.0, ratio))
    return math.hypot(px - (x1 + ratio * dx), py - (y1 + ratio * dy))


def _drawings_on_page(drawings: list | None, page: object) -> list[dict]:
    found: list[dict] = []
    for drawing in drawings or []:
        if not isinstance(drawing, dict):
            continue
        drawing_page = drawing.get("page")
        if page is not None and drawing_page is not None and drawing_page != page:
            continue
        found.append(drawing)
    return found


def _page_rect(drawings: list[dict]) -> tuple[float, float, float, float] | None:
    for drawing in drawings:
        raw = drawing.get("page_rect")
        if not isinstance(raw, (list, tuple)) or len(raw) < 4:
            continue
        try:
            box = (float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3]))
        except (TypeError, ValueError):
            continue
        if box[2] > box[0] and box[3] > box[1]:
            return box
    return None


def _page_geometry(
    drawings: list | None,
    page: object,
) -> tuple[list[tuple[float, float, float, float]], list[tuple[float, float, float, float]], tuple | None]:
    segments: list[tuple[float, float, float, float]] = []
    rects: list[tuple[float, float, float, float]] = []
    chosen = _drawings_on_page(drawings, page)
    for drawing in chosen:
        for item in drawing.get("items") or []:
            segment = _as_line(item)
            if segment is not None:
                segments.append(segment)
                continue
            rect = _as_rect(item)
            if rect is not None:
                rects.append(rect)
    return segments, rects, _page_rect(chosen)


def _arrow_at(
    x: float,
    y: float,
    shorts: list[tuple[float, float, float, float]],
) -> bool:
    for segment in shorts:
        if (
            math.hypot(segment[0] - x, segment[1] - y) <= 3.5
            or math.hypot(segment[2] - x, segment[3] - y) <= 3.5
        ):
            return True
    return False


def _dimension_lines(
    segments: list[tuple[float, float, float, float]],
) -> list[tuple[float, float, float, float]]:
    """Long lines with an arrowhead at each end. Those measure the extent."""
    longs = [segment for segment in segments if _segment_length(segment) >= 20.0]
    shorts = [segment for segment in segments if _segment_length(segment) < _ARROW_PT]
    found: list[tuple[float, float, float, float]] = []
    for segment in longs:
        if _arrow_at(segment[0], segment[1], shorts) and _arrow_at(segment[2], segment[3], shorts):
            found.append(segment)
    return found


def _segment_axis(segment: tuple[float, float, float, float]) -> str | None:
    angle = math.degrees(math.atan2(segment[3] - segment[1], segment[2] - segment[0])) % 180.0
    if min(angle, 180.0 - angle) <= 20.0:
        return "h"
    if abs(angle - 90.0) <= 20.0:
        return "v"
    return None


def _geometry_axis(
    box: tuple[float, float, float, float],
    dim_lines: list[tuple[float, float, float, float]],
) -> tuple[str | None, tuple[float, float, float, float] | None]:
    """Axis of the arrowheaded dimension line next to this number.

    Two different axes equally close means the geometry is not conclusive.
    """
    cx = (box[0] + box[2]) / 2.0
    cy = (box[1] + box[3]) / 2.0
    ranked: list[tuple[float, str, tuple[float, float, float, float]]] = []
    for segment in dim_lines:
        axis = _segment_axis(segment)
        if axis is None:
            continue
        dist = _point_segment_distance(cx, cy, segment)
        if dist <= _DIM_LINE_REACH_PT:
            ranked.append((dist, axis, segment))
    if not ranked:
        return None, None
    ranked.sort(key=lambda item: item[0])
    best = ranked[0]
    for dist, axis, _segment in ranked[1:]:
        if dist <= best[0] + 8.0 and axis != best[1]:
            return None, None
    return best[1], best[2]


def _view_outline(
    rects: list[tuple[float, float, float, float]],
    segments: list[tuple[float, float, float, float]],
    dim_lines: list[tuple[float, float, float, float]],
    label_box: tuple[float, float, float, float],
    page_rect: tuple[float, float, float, float] | None,
) -> tuple[float, float, float, float] | None:
    """The flat-pattern profile near the view label, not the dimension lines."""
    near_rects = [
        rect
        for rect in rects
        if _box_gap(rect, label_box) <= _NEAR_LABEL_PT and (rect[2] - rect[0]) * (rect[3] - rect[1]) >= 400.0
    ]
    if near_rects:
        return max(near_rects, key=lambda rect: (rect[2] - rect[0]) * (rect[3] - rect[1]))
    dim_keys = {tuple(round(value, 2) for value in segment) for segment in dim_lines}
    boxes: list[tuple[float, float, float, float]] = []
    for segment in segments:
        if tuple(round(value, 2) for value in segment) in dim_keys:
            continue
        if _segment_length(segment) < 30.0 or _on_page_border(segment, page_rect):
            continue
        box = (
            min(segment[0], segment[2]),
            min(segment[1], segment[3]),
            max(segment[0], segment[2]),
            max(segment[1], segment[3]),
        )
        if _box_gap(box, label_box) <= _NEAR_LABEL_PT:
            boxes.append(box)
    if not boxes:
        return None
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def _on_page_border(
    segment: tuple[float, float, float, float],
    page_rect: tuple[float, float, float, float] | None,
) -> bool:
    if page_rect is None:
        return False
    x0, y0, x1, y1 = page_rect

    def _edge(x: float, y: float) -> bool:
        return min(x - x0, x1 - x, y - y0, y1 - y) <= 8.0

    return _edge(segment[0], segment[1]) and _edge(segment[2], segment[3])


def _line_bounds_view(
    segment: tuple[float, float, float, float],
    axis: str,
    outline: tuple[float, float, float, float] | None,
) -> bool:
    """True when this dimension line spans the view's horizontal or vertical extent."""
    if outline is None:
        return False
    length = _segment_length(segment)
    if axis == "h":
        span = outline[2] - outline[0]
        start, end = sorted((segment[0], segment[2]))
        overlap = min(end, outline[2]) - max(start, outline[0])
    else:
        span = outline[3] - outline[1]
        start, end = sorted((segment[1], segment[3]))
        overlap = min(end, outline[3]) - max(start, outline[1])
    if span <= 1.0:
        return False
    return length >= 0.45 * span and overlap >= 0.45 * span


def _near_title_word(block: dict, blocks: list[dict]) -> bool:
    """A number sitting on the title, revision, or tolerance block."""
    box = _bbox(block)
    if box is None:
        return False
    if _TITLE_WORD_RE.search(str(block.get("text") or "")):
        return True
    for other in blocks:
        if other is block or not _same_page(block, other):
            continue
        if not _TITLE_WORD_RE.search(str(other.get("text") or "")):
            continue
        other_box = _bbox(other)
        if other_box is not None and _box_gap(box, other_box) <= 72.0:
            return True
    return False


def _in_title_corner(
    box: tuple[float, float, float, float],
    page_rect: tuple[float, float, float, float] | None,
) -> bool:
    if page_rect is None:
        return False
    width = page_rect[2] - page_rect[0]
    height = page_rect[3] - page_rect[1]
    if width < 10.0 or height < 10.0:
        return False
    cx = (box[0] + box[2]) / 2.0
    cy = (box[1] + box[3]) / 2.0
    return cx >= page_rect[0] + 0.62 * width and cy >= page_rect[1] + 0.70 * height


def _fraction_den(text: str) -> int | None:
    match = re.fullmatch(r"(?:/\s*)?(\d{1,2})(?:\s*/)?", text.strip())
    if match is None:
        return None
    value = int(match.group(1))
    if value not in _STACK_FRACTION_DENS:
        return None
    return value


def _stack_parts(text: str) -> tuple[int | None, int | None]:
    raw = " ".join(text.split())
    mixed = re.fullmatch(r"(\d+)\s+(\d{1,2})", raw)
    if mixed:
        return int(mixed.group(1)), int(mixed.group(2))
    bare = re.fullmatch(r"(\d{1,2})", raw)
    if bare:
        return None, int(bare.group(1))
    return None, None


def _pure_fraction(text: str) -> tuple[int, int] | None:
    match = re.fullmatch(r"(\d{1,2})\s*/\s*(\d{1,2})", " ".join(text.split()))
    if match is None:
        return None
    numerator, denominator = int(match.group(1)), int(match.group(2))
    if denominator in _STACK_FRACTION_DENS and 0 < numerator < denominator:
        return numerator, denominator
    return None


def _join_stacked_fraction_blocks(blocks: list[dict]) -> list[dict]:
    """Join ``44`` ``1`` ``/`` ``16`` into one 44 1/16 dimension.

    The pieces can sit on separate PDF spans, including a vertical offset.
    A denominator with no numerator above it stays a normal dimension.
    """
    rows: list[tuple[int, dict, tuple[float, float, float, float] | None, str]] = []
    for index, block in enumerate(blocks):
        rows.append(
            (
                index,
                block,
                _bbox(block),
                " ".join(str(block.get("text") or "").split()),
            )
        )
    used: set[int] = set()
    made: list[dict] = []

    def _add(text: str, source: dict, boxes: list[tuple[float, float, float, float]], consumed: list[int]) -> None:
        made.append(
            {
                "text": text,
                "dir": source.get("dir") or (1, 0),
                "bbox": (
                    min(box[0] for box in boxes),
                    min(box[1] for box in boxes),
                    max(box[2] for box in boxes),
                    max(box[3] for box in boxes),
                ),
                "page": source.get("page"),
            }
        )
        used.update(consumed)

    for index, block, box, text in rows:
        if box is None or index in used:
            continue
        fraction = _pure_fraction(text)
        if fraction is not None:
            numerator, denominator = fraction
            for other_index, other, other_box, other_text in rows:
                if other_index == index or other_box is None or other_index in used:
                    continue
                if not re.fullmatch(r"\d+", other_text):
                    continue
                gap = box[0] - other_box[2]
                same_band = abs(((box[1] + box[3]) / 2.0) - ((other_box[1] + other_box[3]) / 2.0)) <= 14.0
                if same_band and -4.0 <= gap <= 28.0:
                    whole = int(other_text)
                    _add(
                        f"{whole} {numerator}/{denominator}",
                        block,
                        [box, other_box],
                        [index, other_index],
                    )
                    break
            continue
        denominator = _fraction_den(text)
        if denominator is None:
            continue
        numerator_row = None
        for other_index, other, other_box, other_text in rows:
            if other_index == index or other_box is None or other_index in used:
                continue
            whole, numerator = _stack_parts(other_text)
            if numerator is None or not 0 < numerator < denominator:
                continue
            gap = box[1] - other_box[3]
            if gap < -4.0 or gap > 16.0:
                continue
            overlap = min(other_box[2], box[2]) - max(other_box[0], box[0])
            centers = abs((other_box[0] + other_box[2]) / 2.0 - (box[0] + box[2]) / 2.0)
            right = abs(other_box[2] - box[2])
            if overlap <= 0 and centers > 22.0 and right > 22.0:
                continue
            numerator_row = (other_index, other, other_box, whole, numerator)
            break
        if numerator_row is None:
            continue
        other_index, other, other_box, whole, numerator = numerator_row
        consumed = [index, other_index]
        boxes = [box, other_box]
        for slash_index, _slash, slash_box, slash_text in rows:
            if slash_box is None or slash_index in consumed:
                continue
            if slash_text not in {"/", "⁄"}:
                continue
            if slash_box[1] >= min(other_box[1], box[1]) - 6.0 and slash_box[3] <= max(other_box[3], box[3]) + 6.0:
                consumed.append(slash_index)
                boxes.append(slash_box)
                break
        if whole is None:
            stack_top = min(other_box[1], box[1])
            stack_bottom = max(other_box[3], box[3])
            for whole_index, _whole_block, whole_box, whole_text in rows:
                if whole_box is None or whole_index in consumed:
                    continue
                if not re.fullmatch(r"\d+", whole_text):
                    continue
                mid = (whole_box[1] + whole_box[3]) / 2.0
                if not (stack_top - 8.0 <= mid <= stack_bottom + 8.0):
                    continue
                gap = other_box[0] - whole_box[2]
                if -4.0 <= gap <= 28.0:
                    whole = int(whole_text)
                    consumed.append(whole_index)
                    boxes.append(whole_box)
                    break
        label = f"{whole} {numerator}/{denominator}" if whole is not None else f"{numerator}/{denominator}"
        _add(label, other, boxes, consumed)
    kept = [block for index, block in enumerate(blocks) if index not in used]
    kept.extend(made)
    return kept


def _largest_overall(values: list[float]) -> tuple[float | None, bool]:
    """Largest overall. Two close sizes on the same axis are not conclusive."""
    if not values:
        return None, False
    top = max(values)
    rivals = [value for value in values if abs(value - top) > 0.05 and value >= top * 0.7]
    if rivals:
        return None, True
    return top, False


def _scale_disagrees(
    horizontal: float,
    vertical: float,
    outline: tuple[float, float, float, float] | None,
) -> bool:
    """The two overalls should share the view's drawn scale, when it is known."""
    if outline is None:
        return False
    drawn_w = (outline[2] - outline[0]) / 72.0
    drawn_h = (outline[3] - outline[1]) / 72.0
    if drawn_w < 0.4 or drawn_h < 0.4:
        return False
    scale_w = horizontal / drawn_w
    scale_h = vertical / drawn_h
    if min(scale_w, scale_h) <= 0:
        return False
    return max(scale_w, scale_h) / min(scale_w, scale_h) > 3.0


def _position_pair(
    text: str,
    text_blocks: list | None,
    thickness: float | None,
    drawings: list | None = None,
) -> tuple[tuple[float, float] | None, bool]:
    """Largest horizontal and vertical overalls of one flat-pattern view.

    Arrowheaded dimension lines say which way a number measures. Unidirectional
    text is not a vertical dimension. Title-block numbers are not overalls.
    The bool is True when those overalls conflict or are not a safe blank.
    """
    blocks = _join_stacked_fraction_blocks(_as_blocks(text_blocks))
    have_drawings = bool(drawings)
    labels: list[tuple[dict, tuple[float, float, float, float]]] = []
    dims: list[tuple[dict, tuple[float, float, float, float], float]] = []
    for block in blocks:
        box = _bbox(block)
        if box is None:
            continue
        raw = str(block.get("text") or "")
        if _FLAT_LABEL_RE.search(raw):
            labels.append((block, box))
            continue
        value = _bare_inches(raw)
        if value is None or value < 1.0 or value > _MAX_BLANK_IN:
            continue
        dims.append((block, box, value))
    if not labels or not dims:
        return None, False
    pairs: list[tuple[float, float]] = []
    conflict = False
    for label, label_box in labels:
        segments, rects, page_rect = _page_geometry(drawings, label.get("page"))
        dim_lines = _dimension_lines(segments) if have_drawings else []
        outline = (
            _view_outline(rects, segments, dim_lines, label_box, page_rect)
            if have_drawings
            else None
        )
        grouped: dict[str, list[tuple[float, float]]] = {"h": [], "v": []}
        for block, box, value in dims:
            if not _same_page(label, block):
                continue
            if _box_gap(label_box, box) > _NEAR_LABEL_PT:
                continue
            geom_axis, dim_line = (_geometry_axis(box, dim_lines) if have_drawings else (None, None))
            if geom_axis is not None:
                axis = geom_axis
            elif not have_drawings:
                axis = _text_axis(block)
            elif _text_axis(block) == "v":
                axis = "v"
            else:
                axis = None
            if axis is None:
                continue
            bounds = bool(dim_line is not None and _line_bounds_view(dim_line, axis, outline))
            titled = _near_title_word(block, blocks) or _in_title_corner(box, page_rect)
            if titled and not bounds:
                continue
            if outline is not None and not bounds and _box_gap(box, outline) > 180.0:
                continue
            if have_drawings and geom_axis is not None and outline is not None and not bounds:
                continue
            grouped[axis].append((value, _box_gap(label_box, box)))
        if have_drawings:
            horizontal, horizontal_bad = _largest_overall([value for value, _gap in grouped["h"]])
            vertical, vertical_bad = _largest_overall([value for value, _gap in grouped["v"]])
        else:
            horizontal, horizontal_bad = _axis_overall(grouped["h"])
            vertical, vertical_bad = _axis_overall(grouped["v"])
        if horizontal_bad or vertical_bad:
            conflict = True
            continue
        if horizontal is None or vertical is None:
            continue
        if _scale_disagrees(horizontal, vertical, outline):
            conflict = True
            continue
        if not _accepted_size(horizontal, vertical, text, thickness):
            conflict = True
            continue
        pairs.append((horizontal, vertical))
    unique = _unique_pairs(pairs)
    if len(unique) == 1 and not conflict:
        return unique[0], False
    if len(unique) > 1 or conflict:
        return None, True
    return None, False


def _drawing_flat_decision(
    text: str,
    thickness_in: float | None,
    text_blocks: list | None,
    drawings: list | None = None,
) -> tuple[tuple[float, float] | None, str | None]:
    """Trusted blank, or a flag when a real flat view has no safe size.

    An inline ``W x L`` is used in the order printed. Separate overalls are
    the largest horizontal and vertical dimensions whose arrowheads bound the
    flat-pattern view. Text direction is used only when the PDF has no vectors.
    A bare template label is ignored. Anything unsure is a flag.
    """
    if not _FLAT_LABEL_RE.search(text or ""):
        return None, None
    if not _flat_view_is_real(text, text_blocks):
        return None, None
    inline = _inline_pairs(text, thickness_in)
    position, conflict = _position_pair(text, text_blocks, thickness_in, drawings)
    if conflict or len(inline) > 1:
        return None, FLAT_SIZE_UNCLEAR
    if len(inline) == 1 and position is not None and not _pairs_compatible(inline[0], position):
        return None, FLAT_SIZE_UNCLEAR
    if len(inline) == 1:
        return inline[0], None
    if position is not None:
        return position, None
    return None, FLAT_SIZE_UNCLEAR


def _sheet_radius_line(line: str) -> bool:
    return bool(
        re.search(r"(?i)\b(?:UP|DOWN|INSIDE\s+RADIUS|BEND\s+RADIUS)\b", line)
        or re.search(r"(?i)\b(?:TYP|DIA|DIAM|HOLE|THRU)\b", line)
    )


def round_stock_bend_evidence(text: str) -> bool:
    """Tube or round stock that is formed, not a straight cut.

    CLR, a centerline radius, an ``R`` plus a decimal such as ``R5.91``,
    a bend table, a degree mark next to a tube leg, or the word BEND with an
    OD or wall callout. ``ANGULAR: BEND`` and ``BEND ANGLE =`` are title-block
    notes, not a bend.
    """
    blob = str(text or "")
    if _ROUND_STOCK_BEND_RE.search(blob):
        return True
    lines = blob.splitlines()
    for index in range(len(lines)):
        window = " ".join(lines[index : index + 3])
        if (
            re.search(r"(?i)\bANGLE\b", window)
            and re.search(r"(?i)\bROTATION\b", window)
            and re.search(r"(?i)\bLENGTH\b", window)
        ):
            return True
    for line in lines:
        if _sheet_radius_line(line) or _TITLE_ANGLE_RE.search(line):
            continue
        for match in _TUBE_R_RE.finditer(line):
            try:
                radius = float(match.group(1))
            except ValueError:
                continue
            if radius >= 1.0:
                return True
    kept = [line for line in lines if not _TITLE_ANGLE_RE.search(line)]
    kept_blob = "\n".join(kept)
    has_bend_word = bool(re.search(r"(?i)(?<![A-Z])BENDS?\b", kept_blob))
    has_wall = bool(re.search(r"(?i)\b(?:OD|O\.D\.|WALL)\b", kept_blob))
    if has_bend_word and has_wall:
        return True
    for index, line in enumerate(kept):
        if _sheet_radius_line(line) or _TEMPLATE_ANGULAR_RE.search(line):
            continue
        if not _DEGREE_MARK_RE.search(line):
            continue
        window = " ".join(kept[max(0, index - 2) : index + 3])
        if _TUBE_STOCK_RE.search(window):
            return True
    return False


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


def _degree_lines(text: str) -> list[str]:
    return [
        line
        for line in str(text or "").splitlines()
        if _DEGREE_MARK_RE.search(line)
    ]


def _template_degree_only(text: str) -> bool:
    """True when every degree line is title-block boilerplate, including ALL ANGULAR DIMENSIONS."""
    lines = _degree_lines(text)
    if not any(_TEMPLATE_ANGULAR_RE.search(line) for line in lines):
        return False
    return all(
        _TEMPLATE_ANGULAR_RE.search(line)
        or _TITLE_ANGLE_RE.search(line)
        or _UNSAFE_SIZE_LINE_RE.search(line)
        for line in lines
    )


def _stray_numbers_near_flat_label(text: str, text_blocks: list | None) -> bool:
    """A bare number near a FLAT PATTERN label, with no bend note and no W x L."""
    lines = str(text or "").splitlines()
    for index, line in enumerate(lines):
        if not _FLAT_LABEL_RE.search(line):
            continue
        for item in _neighborhood(lines, index):
            if item == line:
                continue
            value = _bare_inches(item)
            if value is not None and value >= 1.0:
                return True
    for label in _as_blocks(text_blocks):
        if not _FLAT_LABEL_RE.search(str(label.get("text") or "")):
            continue
        label_box = _bbox(label)
        if label_box is None:
            continue
        for block in _as_blocks(text_blocks):
            if block is label or not _same_page(label, block):
                continue
            box = _bbox(block)
            if box is None or _box_gap(label_box, box) > _NEAR_LABEL_PT:
                continue
            value = _bare_inches(str(block.get("text") or ""))
            if value is not None and value >= 1.0:
                return True
    return False


def _template_wording_review(text: str, read: BendRead, text_blocks: list | None) -> bool:
    """Template boilerplate is a review flag, not a claim that the part is formed."""
    if read.bend_count not in (None, 0):
        return False
    if any(
        (
            read.hem,
            read.offset,
            read.roll,
            read.cone,
            read.stretch,
            read.unfold,
            read.formed_word,
            read.brake,
            read.bend_word,
            read.up_down,
            read.plane_flag,
        )
    ):
        return False
    if read.count_flag == "a bend angle does not give a count" and _template_degree_only(text):
        return True
    if read.count_flag or read.radius_in is not None or read.radius_ambiguous:
        return False
    if not _FLAT_LABEL_RE.search(text or ""):
        return False
    if _flat_view_is_real(text, text_blocks):
        return False
    return _stray_numbers_near_flat_label(text, text_blocks)


def _has_formed_evidence(
    read: BendRead,
    text: str,
    text_blocks: list | None = None,
) -> bool:
    """True when the text says the part is formed, even if the count is missing.

    A bare FLAT PATTERN template label, with no dimension or bend note next
    to it, does not count.
    """
    if read.callout or read.formed_word or read.bend_word or read.up_down:
        return True
    if read.count_flag or read.plane_flag:
        return True
    if read.bend_count not in (None, 0):
        return True
    if round_stock_bend_evidence(text):
        return True
    if _flat_view_is_real(text, text_blocks):
        return True
    return bool(re.search(r"(?i)\bFORMED\b", text or ""))


def evaluate_formed(
    text: str,
    *,
    thickness_in: float | None,
    drawings: list | None = None,
    text_blocks: list | None = None,
) -> FlatPattern | None:
    """None when the drawing is a flat plate. Otherwise a flag or a developed flat.

    A printed FLAT PATTERN size is the blank only when it is a clear overall
    on that view: not a chamfer, angle, thread, or tolerance, and plausible
    next to the thickness and the part's other dimensions. An unclear angle
    or an ambiguous radius is flagged before that size is accepted. A missing
    angle or radius does not block a size that already passed. Kyle's formula
    runs only when no flat view was printed and the legs, thickness, and
    radius are all readable. Hems, rolled sections, cones, compound forms,
    nonparallel bends, and an inside or mixed dimension chain are flagged
    before the formula runs. A stated bend angle of any size is allowed.
    θ is the change from flat.

    Formed evidence with a bend count of 0 or unknown is a flag. It is not
    a flat plate. A bare template label is not formed evidence.
    """
    read = read_bends(text, drawings, text_blocks=text_blocks)
    if round_stock_bend_evidence(text):
        return FlatPattern(flag=ROUND_STOCK_BEND_FLAG)
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
    if _template_wording_review(text, read, text_blocks):
        return FlatPattern(flag=TEMPLATE_WORDING_FLAG, flag_field="review")
    if read.count_flag:
        return FlatPattern(flag=read.count_flag, flag_field="bend count")
    if read.bend_count in (None, 0) and _has_formed_evidence(read, text, text_blocks):
        return FlatPattern(
            flag="formed evidence but the bend count is 0 or unknown",
        )
    if not read.callout:
        return None
    # An unclear angle or radius has to win before any printed size.
    if read.angle_flag and read.angle_flag != "bend angle was not on the drawing":
        return FlatPattern(flag=read.angle_flag)
    if read.radius_flag and read.radius_flag != "inside radius was not on the drawing":
        return FlatPattern(flag=read.radius_flag)
    if read.bend_count and read.bend_count > 0:
        printed, size_flag = _drawing_flat_decision(
            text, thickness_in, text_blocks, drawings
        )
        if size_flag:
            return FlatPattern(flag=size_flag)
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
