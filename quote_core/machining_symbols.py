"""Machining-symbol meanings from published drafting standards.

Meanings are short restatements of the cited paragraphs. A token that is
not in this library is unknown: its meaning stays blank.
"""

from __future__ import annotations

import re
from typing import Any

_GENIUM = (
    "Genium Publishing Drafting Manual, Section 6.1 "
    "(Bruce A. Wilson; based on ASME Y14.5M-1994), "
    "https://brlcad.org/design/drafting/Drafting_Manual_DimensioningAndTolerancingSymbols_6-1.pdf"
)
_Y145 = "ASME Y14.5-2018 continues this symbol (it replaces ASME Y14.5-2009)."

# id, glyphs, words, meaning, citation
_ENTRIES: tuple[dict[str, Any], ...] = (
    {
        "id": "diameter",
        "glyphs": ("⌀", "Ø", "∅"),
        "words": ("dia", "diameter"),
        "meaning": "Placed in front of a value that is a diameter.",
        "citation": (
            f"{_GENIUM}, paragraph 2.1. {_Y145} "
            "Text encodings of that symbol: U+2300, U+00D8, U+2205. "
            "Paragraph 1.5: notes use the symbol name in place of the symbol."
        ),
    },
    {
        "id": "counterbore",
        "glyphs": ("⌴",),
        "words": ("counterbore", "spotface", "cb"),
        "meaning": (
            "Placed with the diameter symbol in front of a counterbore "
            "or spotface diameter."
        ),
        "citation": (
            f"{_GENIUM}, paragraph 2.2. {_Y145} "
            "Text encoding of the counterbore symbol: U+2334. "
            "Paragraph 1.5: notes use the symbol name in place of the symbol."
        ),
    },
    {
        "id": "countersink",
        "glyphs": ("⌵",),
        "words": ("countersink", "csk"),
        "meaning": (
            "Placed with the diameter symbol in front of a countersink diameter. "
            "The common callout writes that diameter, then X, then the included angle. "
            "A space on each side of X means BY."
        ),
        "citation": (
            f"{_GENIUM}, paragraph 2.3. {_Y145} "
            "Text encoding of the countersink symbol: U+2335. "
            "Paragraph 1.5: notes use the symbol name in place of the symbol. "
            "The included angle uses the degree sign. "
            "X with a space on each side is BY (paragraph 2.11.1)."
        ),
    },
    {
        "id": "depth",
        "glyphs": ("↓", "↧"),
        "words": ("depth",),
        "meaning": "A downward-pointing arrow placed in front of a depth value.",
        "citation": (
            f"{_GENIUM}, paragraph 2.4. {_Y145} "
            "Text encodings of that symbol: U+2193, U+21A7."
        ),
    },
    {
        "id": "repetition",
        "glyphs": (),
        "words": ("x",),
        "meaning": (
            "The letter X with no space after a number is how many times "
            "or places a feature is repeated. A space on each side of X "
            "between two values means BY, not a count."
        ),
        "citation": (
            f"{_GENIUM}, paragraph 2.11.1. "
            "The counted example there is 3X before a thread designation. "
            "The BY example is .125 X .750."
        ),
    },
    {
        "id": "radius",
        "glyphs": (),
        "words": ("r", "radius"),
        "meaning": (
            "The letter R placed in front of a radius value. "
            "MAX or MIN on that value is a limiting radius. "
            "It does not state a place count."
        ),
        "citation": (
            f"{_GENIUM}, paragraph 2.11.2. {_Y145} "
            "ASME Y14.5 limiting practice: MAX or MIN on a radius is a limit, "
            "not a count."
        ),
    },
    {
        "id": "controlled_radius",
        "glyphs": (),
        "words": ("cr",),
        "meaning": "CR placed in front of a controlled-radius value.",
        "citation": (
            f"{_GENIUM}, paragraph 2.11.3. "
            "Defined in the 1994 standard, not in the 1982 standard."
        ),
    },
    {
        "id": "spherical_radius",
        "glyphs": (),
        "words": ("sr",),
        "meaning": "SR placed in front of a spherical-radius value.",
        "citation": f"{_GENIUM}, paragraph 2.11.4. {_Y145}",
    },
    {
        "id": "spherical_diameter",
        "glyphs": ("S⌀", "SØ", "S∅"),
        "words": (),
        "meaning": "The letter S and the diameter symbol placed in front of a spherical diameter.",
        "citation": f"{_GENIUM}, paragraph 2.11.5. {_Y145}",
    },
    {
        "id": "square",
        "glyphs": ("□",),
        "words": ("square",),
        "meaning": (
            "Placed in front of a dimension for a square feature. "
            "One dimension is enough for that square."
        ),
        "citation": f"{_GENIUM}, paragraph 2.6.",
    },
    {
        "id": "reference",
        "glyphs": (),
        "words": (),
        "meaning": "Parentheses around a dimension value mark that value as reference.",
        "citation": f"{_GENIUM}, paragraph 2.7.",
    },
    {
        "id": "typical",
        "glyphs": (),
        "words": ("typ", "typical"),
        "meaning": (
            "No place count is stated. The count stays blank unless the "
            "callout also uses the nX form (X with no space after the number)."
        ),
        "citation": (
            f"{_GENIUM}, paragraph 2.11.1, is the published repetition count. "
            "That paragraph does not give TYP or TYPICAL a count."
        ),
    },
    {
        "id": "surface_texture",
        "glyphs": (),
        "words": ("ra", "finish", "surface finish", "machined surface"),
        "meaning": (
            "A surface-texture parameter that the drawing requires on a surface. "
            "The parameter definition is in ASME B46.1 and is not restated here."
        ),
        "citation": (
            "ASME Y14.36-2018, paragraph 4.2: the basic surface texture symbol "
            "denotes the surface texture parameters required for a surface. "
            "Parameter definitions: ASME B46.1."
        ),
    },
    {
        "id": "thread",
        "glyphs": (),
        "words": (),
        "meaning": (
            "A unified inch screw-thread designation states major diameter, "
            "threads per inch, and series. UNC, UNF, and UNEF are the coarse, "
            "fine, and extra-fine series names. The class suffix is kept as "
            "written. The designation does not say tap or single-point, so "
            "the thread process stays blank."
        ),
        "citation": (
            "ASME B1.1, Unified Inch Screw Threads. "
            f"{_GENIUM}, paragraph 2.11.1, shows the designation after a place count "
            "(example form 3X .250-20UNC-3A)."
        ),
    },
    {
        "id": "chamfer",
        "glyphs": (),
        "words": ("chamfer",),
        "meaning": (
            "The word CHAMFER names a chamfer. "
            "An angle written with the degree sign on that note is the chamfer angle. "
            "A linear size written on the note is the chamfer size. "
            "A size that is not written stays blank."
        ),
        "citation": (
            "ASME Y14.5-2018, figure 4-41 (45° chamfer). "
            f"{_GENIUM}. "
            "Paragraph 1.5: notes use the symbol name in place of a symbol."
        ),
    },
    {
        "id": "degree",
        "glyphs": ("°",),
        "words": ("deg", "degree", "degrees"),
        "meaning": "Placed after a value that is an angle in degrees.",
        "citation": (
            f"{_GENIUM}, paragraph 3.3.3, writes this sign on an angle (30°). "
            "ASME Y14.5-2018, figure 4-41 (45° chamfer) and figure 5-20 "
            "(an angular surface). Text encoding: U+00B0. "
            "Paragraph 1.5: a note may write DEG in place of the sign."
        ),
    },
    {
        "id": "plus_minus",
        "glyphs": ("±",),
        "words": (),
        "meaning": (
            "Placed with a size to show a tolerance that applies in both "
            "directions. The limit values are not calculated."
        ),
        "citation": (
            "ASME Y14.5-2018, figure 5-2, Plus and Minus Tolerancing. "
            f"{_Y145} Text encoding: U+00B1. "
            "A plus sign, a slash, and a minus sign write that same tolerance "
            "when the single glyph is not used."
        ),
    },
    {
        "id": "iso_fit",
        "glyphs": (),
        "words": (),
        "meaning": (
            "A letter and a grade after a size are an ISO tolerance code for "
            "a shaft or a hole. A lowercase letter is a shaft. An uppercase "
            "letter is a hole. The letter is the fundamental deviation and the "
            "number is the tolerance grade. The limit values are not calculated."
        ),
        "citation": (
            "ISO 286-1, ISO code system for tolerances on linear sizes. "
            "Part 1 gives the basis of tolerances, deviations and fits."
        ),
    },
    {
        "id": "position",
        "glyphs": ("\u2316",),
        "words": ("position",),
        "meaning": (
            "A position tolerance. The tolerance and the datum letters stay "
            "as written. The callout is not a hole count."
        ),
        "citation": "ASME Y14.5, position. Text encoding of the symbol: U+2316.",
    },
    {
        "id": "parallelism",
        "glyphs": ("//", "\u2225"),
        "words": ("parallelism",),
        "meaning": "Parallelism to a datum. The tolerance stays as written.",
        "citation": (
            "ASME Y14.5, parallelism. "
            "Text forms: two slashes, or U+2225."
        ),
    },
    {
        "id": "perpendicularity",
        "glyphs": ("\u22a5",),
        "words": ("perpendicularity", "perpendicular"),
        "meaning": "Perpendicularity to a datum. The tolerance stays as written.",
        "citation": "ASME Y14.5, perpendicularity. Text encoding: U+22A5.",
    },
    {
        "id": "flatness",
        "glyphs": ("\u25ad",),
        "words": ("flatness",),
        "meaning": (
            "Flatness of a surface. The tolerance stays as written. "
            "It is not a hole."
        ),
        "citation": "ASME Y14.5, flatness. Text encoding of the frame used here: U+25AD.",
    },
    {
        "id": "basic",
        "glyphs": (),
        "words": ("basic",),
        "meaning": (
            "A basic dimension. The drawing boxes the value. "
            "Limits are not calculated."
        ),
        "citation": "ASME Y14.5, basic dimension.",
    },
    {
        "id": "thru",
        "glyphs": (),
        "words": ("thru", "through"),
        "meaning": (
            "The feature passes through. This word does not state a numeric depth "
            "and does not state a place count. It may stand with a diameter."
        ),
        "citation": "Common drawing practice. THRU names a through feature.",
    },
    {
        "id": "near_side",
        "glyphs": (),
        "words": ("near side", "ns"),
        "meaning": "The feature is on the near face of the view. It does not supply a place count.",
        "citation": "Common drawing practice.",
    },
    {
        "id": "bolt_circle",
        "glyphs": (),
        "words": ("b.c.", "bolt circle"),
        "meaning": (
            "A bolt-circle diameter. The features lie on that circle. "
            "It is not a hole count."
        ),
        "citation": "Common drawing practice. The abbreviation on the sheet is B.C.",
    },
    {
        "id": "datum",
        "glyphs": (),
        "words": ("datum",),
        "meaning": "A datum feature letter, kept as written. It is not a hole.",
        "citation": "ASME Y14.5, datum feature.",
    },
    {
        "id": "composite_position",
        "glyphs": (),
        "words": ("composite position",),
        "meaning": (
            "Two stacked position frames. Each frame stays as written. "
            "One position frame is not composite."
        ),
        "citation": "ASME Y14.5, composite position tolerancing.",
    },
    {
        "id": "third_angle",
        "glyphs": (),
        "words": ("third angle",),
        "meaning": "Third-angle projection. It names the view method. It is not a feature.",
        "citation": "ASME Y14.3, third-angle projection.",
    },
)

_BY_GLYPH: dict[str, dict[str, Any]] = {}
_BY_WORD: dict[str, dict[str, Any]] = {}
_BY_ID: dict[str, dict[str, Any]] = {}
for _entry in _ENTRIES:
    _BY_ID[_entry["id"]] = _entry
    for _glyph in _entry["glyphs"]:
        _BY_GLYPH[_glyph] = _entry
    for _word in _entry["words"]:
        _BY_WORD[_word] = _entry

_NX = re.compile(r"(\d+)[Xx]")
# Ra before the value, or the value before Ra. A bare number is not a finish.
_RA = re.compile(
    r"^(?:Ra\s*(?P<a>[0-9]*\.?[0-9]+)|(?P<b>[0-9]*\.?[0-9]+)\s*Ra)$",
    re.IGNORECASE,
)
_FINISH_PHRASE = re.compile(
    r"^(?:"
    r"(?P<lead>[0-9]*\.?[0-9]+)\s+"
    r"(?P<left>MACHINED\s+SURFACE(?:\s+FINISH(?:ES)?)?|SURFACE\s+FINISH|FINISH)"
    r"|"
    r"(?P<right>MACHINED\s+SURFACE(?:\s+FINISH(?:ES)?)?|SURFACE\s+FINISH|FINISH)"
    r"(?:\s*=\s*|\s+)(?P<trail>[0-9]*\.?[0-9]+)"
    r"|"
    r"(?P<uos>MACHINED\s+SURFACE(?:\s+FINISH(?:ES)?)?|SURFACE\s+FINISH|FINISH)"
    r"(?:\s*\(\s*UOS\s*\)|\s+UOS)\s+(?P<uos_val>[0-9]*\.?[0-9]+)"
    r"|"
    r"(?P<bare>MACHINED\s+SURFACE(?:\s+FINISH(?:ES)?)?|SURFACE\s+FINISH)"
    r")$",
    re.IGNORECASE,
)
_THREAD = re.compile(
    r"(?:(\d+)\s*/\s*(\d+)|(\d*\.\d+|\d+))\s*-\s*(\d+)\s*"
    r"(UNC|UNF|UNEF|UNS|UN)(?:\s*-?\s*(\d[AB]))?",
    re.IGNORECASE,
)
_METRIC_THREAD = re.compile(
    r"^M(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)"
    r"(?:\s*-\s*(\d?[A-H]))?"
    r"(?:\s+ISO)?"
    r"(?:\s*-\s*([A-H]))?"
    r"(?:\s+TAP)?$",
    re.IGNORECASE,
)
_NPT_THREAD = re.compile(
    r"^(?:(\d+)\s*/\s*(\d+)|(\d+(?:\.\d+)?))\s*-?\s*NPT$",
    re.IGNORECASE,
)
_NOTE_NUMBER = r"([0-9]*\.?[0-9]+|\d+\s*/\s*\d+)"
_CHAMFER_WORD = re.compile(r"\bCHAMFER\b", re.IGNORECASE)
_COUNTERSINK_WORD = re.compile(r"\bCOUNTERSINK\b|\bCSK\b", re.IGNORECASE)
_COUNTERBORE_WORD = re.compile(r"\bCOUNTERBORE\b|\bSPOTFACE\b|\bCB\b|⌴", re.IGNORECASE)
# DEGREE before DEG so the longer word is the one that matches.
_ANGLE_UNIT = r"(?:°|DEGREES?|DEG)"
_DEGREE_VALUES = re.compile(
    rf"(\d+(?:\.\d+)?)\s*{_ANGLE_UNIT}(?![A-Za-z])",
    re.IGNORECASE,
)
_CHAMFER_LEG = re.compile(
    rf"{_NOTE_NUMBER}\s+X\s+(\d+(?:\.\d+)?)\s*{_ANGLE_UNIT}"
    rf"|(\d+(?:\.\d+)?)\s*{_ANGLE_UNIT}\s+X\s+{_NOTE_NUMBER}",
    re.IGNORECASE,
)
_COUNTERSINK_CALLOUT = re.compile(
    rf"(?:⌀|Ø|∅)?\s*(?P<dia>{_NOTE_NUMBER})"
    rf"(?:\s*±\s*(?P<tol>{_NOTE_NUMBER}))?"
    rf"\s*[xX×]\s*(?P<ang>\d+(?:\.\d+)?)\s*{_ANGLE_UNIT}",
    re.IGNORECASE,
)
# Size and angle with no space around X. A spaced X is BY, not a chamfer.
_TIGHT_CHAMFER = re.compile(
    rf"^(?:(?P<count>\d+)X\s+)?"
    rf"(?P<size>{_NOTE_NUMBER})[xX×](?P<ang>\d+(?:\.\d+)?)\s*{_ANGLE_UNIT}$",
    re.IGNORECASE,
)
_DEGREE_CALLOUT = re.compile(
    rf"^(\d+(?:\.\d+)?)\s*{_ANGLE_UNIT}$",
    re.IGNORECASE,
)
_RADIUS_VALUE = re.compile(
    r"^(SR|CR|R)\s*([0-9]*\.?[0-9]+)\s*(MAX|MIN)?$",
    re.IGNORECASE,
)
_SURFACE_CHECK = re.compile(r"^[✓✔√]\s*([0-9]*\.?[0-9]+)$")
_DEPTH_RANGE = re.compile(
    rf"^(?:↧|↓)\s*(?P<a>{_NOTE_NUMBER})\s*/\s*(?P<b>{_NOTE_NUMBER})$",
    re.IGNORECASE,
)
_DEPTH_ONE = re.compile(rf"^(?:↧|↓)\s*(?P<v>{_NOTE_NUMBER})$", re.IGNORECASE)
_DIA_VALUE = re.compile(
    rf"^(?:⌀|Ø|∅)\s*(?P<nom>{_NOTE_NUMBER})(?:\s*±\s*(?P<tol>{_NOTE_NUMBER}))?$"
)
_REFERENCE_DIM = re.compile(
    rf"^\(\s*(?P<dia>⌀|Ø|∅)?\s*(?P<val>{_NOTE_NUMBER})\s*\)$"
)
_BASIC_LINE = re.compile(
    r"^(?:BASIC(?:\s+(?P<a>[0-9]*\.?[0-9]+))?|(?P<b>[0-9]*\.?[0-9]+)\s+BASIC)$",
    re.IGNORECASE,
)
_FLAT_LINE = re.compile(
    r"^(?:▭\s*)?(?:(?P<a>[0-9]*\.?[0-9]+)\s+)?FLATNESS(?:\s+(?P<b>[0-9]*\.?[0-9]+))?$"
    r"|^(?:▭)\s*(?P<c>[0-9]*\.?[0-9]+)$",
    re.IGNORECASE,
)
_POSITION_LINE = re.compile(rf"^⌖\s*(?P<val>[0-9]*\.?[0-9]+)?(?:\s*\|.*)?$")
_PARALLEL_LINE = re.compile(rf"^(?://|∥)\s*(?P<val>[0-9]*\.?[0-9]+)?(?:\s*\|.*)?$")
_PERP_LINE = re.compile(rf"^⊥\s*(?P<val>[0-9]*\.?[0-9]+)?(?:\s*\|.*)?$")
_DATUM_LINE = re.compile(r"^DATUM\s+([A-Z])$", re.IGNORECASE)
_BOLT_CIRCLE_LINE = re.compile(
    rf"^(?:(?:⌀|Ø|∅)\s*)?(?P<val>[0-9]*\.?[0-9]+)\s+B\.C\.?$",
    re.IGNORECASE,
)
_CHECK_GLYPHS = frozenset("✓✔√")
# ISO 286-1 fundamental deviations. i, l, o, q, and w are not used.
_ISO_SHAFT_DEVIATIONS = frozenset(
    {
        "a", "b", "c", "cd", "d", "e", "ef", "f", "fg", "g", "h",
        "js", "j", "k", "m", "n", "p", "r", "s", "t", "u", "v",
        "x", "y", "z", "za", "zb", "zc",
    }
)
_ISO_HOLE_DEVIATIONS = frozenset(item.upper() for item in _ISO_SHAFT_DEVIATIONS)
_ISO_FIT_TOKEN = re.compile(
    r"^(?:(?P<size>\d+(?:\.\d+)?)\s*)?(?P<dev>[A-Za-z]{1,2})(?P<grade>\d{1,2})$"
)
_TOL_TOKEN = r"(?:[0-9]*\.?[0-9]+|\d+\s*/\s*\d+)"
_MINUS_MARK = "[-\u2212]"
_PM_BILATERAL = re.compile(
    rf"^\+\s*(?P<up>{_TOL_TOKEN})\s*/\s*{_MINUS_MARK}\s*(?P<down>{_TOL_TOKEN})$"
)
_PM_SLASH = re.compile(
    rf"^(?:(?P<nom>[0-9]*\.?[0-9]+)\s*)?\+\s*/\s*{_MINUS_MARK}"
    rf"(?:\s*(?P<tol>{_TOL_TOKEN}))?$"
)
_PM_GLYPH = re.compile(
    rf"^(?:(?P<nom>[0-9]*\.?[0-9]+)\s*)?±\s*(?P<tol>{_TOL_TOKEN})(?P<deg>°)?$"
)
_PLUS_MINUS_CHAR_SPAN = re.compile(rf"\+\s*/\s*{_MINUS_MARK}")
_DIAMETER_MARK = re.compile(
    rf"(?:⌀|Ø|∅)\s*{_NOTE_NUMBER}",
    re.IGNORECASE,
)

KNOWN_GLYPHS = frozenset(_BY_GLYPH)


def symbol_library() -> list[dict[str, Any]]:
    """Every symbol this library will describe, with its citation."""
    out = []
    for entry in _ENTRIES:
        out.append(
            {
                "id": entry["id"],
                "glyphs": list(entry["glyphs"]),
                "words": list(entry["words"]),
                "meaning": entry["meaning"],
                "citation": entry["citation"],
            }
        )
    return out


def _known(entry: dict[str, Any], token: str, **extra: Any) -> dict[str, Any]:
    found = {
        "symbol": token,
        "id": entry["id"],
        "known": True,
        "meaning": entry["meaning"],
        "citation": entry["citation"],
        "note": None,
    }
    found.update(extra)
    return found


def _unknown(token: str) -> dict[str, Any]:
    return {
        "symbol": token,
        "id": None,
        "known": False,
        "meaning": None,
        "citation": None,
        "note": "Not in the library. Meaning was not guessed.",
    }


def _note_number(token: str | None) -> float | None:
    if not token:
        return None
    text = token.strip().replace(" ", "")
    if not text:
        return None
    if "/" in text:
        num, _, den = text.partition("/")
        try:
            return float(num) / float(den)
        except (ValueError, ZeroDivisionError):
            return None
    try:
        return float(text)
    except ValueError:
        return None


def _named_feature_note(raw: str) -> dict[str, Any] | None:
    """A chamfer note, or a countersink note that carries a size or an angle.

    The bare words are handled by the word list. A BY dimension with no
    countersink word and no countersink symbol is not a countersink.
    """
    if _COUNTERSINK_WORD.search(raw) or "⌵" in raw:
        extra: dict[str, Any] = {}
        callout = _COUNTERSINK_CALLOUT.search(raw)
        if callout:
            diameter = _note_number(callout.group("dia"))
            angle = _note_number(callout.group("ang"))
            tolerance = _note_number(callout.group("tol"))
            if diameter is not None:
                extra["countersink_diameter_in"] = diameter
            if angle is not None:
                extra["angle_deg"] = angle
            if tolerance is not None:
                extra["tolerance"] = tolerance
        else:
            marked = _DIAMETER_MARK.search(raw)
            if marked:
                diameter = _note_number(marked.group(1))
                if diameter is not None:
                    extra["countersink_diameter_in"] = diameter
            angles = _DEGREE_VALUES.findall(raw)
            if len(angles) == 1:
                angle = _note_number(angles[0])
                if angle is not None:
                    extra["angle_deg"] = angle
        if not extra:
            return None
        return _known(_BY_ID["countersink"], raw, **extra)
    tight = _TIGHT_CHAMFER.fullmatch(raw.strip())
    if tight and not _COUNTERSINK_WORD.search(raw) and "⌵" not in raw:
        extra = {}
        size = _note_number(tight.group("size"))
        angle = _note_number(tight.group("ang"))
        if size is not None:
            extra["size_in"] = size
        if angle is not None:
            extra["angle_deg"] = angle
        if tight.group("count"):
            extra["count"] = int(tight.group("count"))
        return _known(_BY_ID["chamfer"], raw, **extra)
    if not _CHAMFER_WORD.search(raw) or raw.casefold() == "chamfer":
        return None
    extra = {}
    leg = _CHAMFER_LEG.search(raw)
    if leg:
        size = _note_number(leg.group(1) or leg.group(4))
        angle = _note_number(leg.group(2) or leg.group(3))
        if size is not None:
            extra["size_in"] = size
        if angle is not None:
            extra["angle_deg"] = angle
    else:
        angles = _DEGREE_VALUES.findall(raw)
        if len(angles) == 1:
            angle = _note_number(angles[0])
            if angle is not None:
                extra["angle_deg"] = angle
    return _known(_BY_ID["chamfer"], raw, **extra)


def _describe_surface_finish(raw: str) -> dict[str, Any] | None:
    """Ra with a value, or a finish note. A bare number is not a finish.

    FINISH, SURFACE FINISH, and MACHINED SURFACE name the requirement.
    The value may sit on either side of Ra, or beside that note.
    The parameter limits in ASME B46.1 are not calculated here.
    """
    text = re.sub(r"\s+", " ", raw.strip())
    check = _SURFACE_CHECK.fullmatch(text)
    if check:
        value = _note_number(check.group(1))
        extra = {}
        if value is not None:
            extra["roughness"] = value
        return _known(_BY_ID["surface_texture"], raw, **extra)
    rough = _RA.fullmatch(text)
    if rough:
        value = _note_number(rough.group("a") or rough.group("b"))
        extra: dict[str, Any] = {}
        if value is not None:
            extra["roughness"] = value
        return _known(_BY_ID["surface_texture"], raw, **extra)
    phrase = _FINISH_PHRASE.fullmatch(text)
    if not phrase:
        return None
    token = phrase.group("lead") or phrase.group("trail")
    if token is None and "uos_val" in phrase.groupdict():
        token = phrase.group("uos_val")
    extra = {}
    if token:
        value = _note_number(token)
        if value is None:
            return None
        extra["roughness"] = value
    return _known(_BY_ID["surface_texture"], raw, **extra)


def _describe_radius_value(raw: str) -> dict[str, Any] | None:
    """R, CR, or SR with a value. A bare R5 is a radius, not an ISO hole code."""
    match = _RADIUS_VALUE.fullmatch(raw.strip())
    if not match:
        return None
    prefix = match.group(1).casefold()
    value = _note_number(match.group(2))
    extra: dict[str, Any] = {}
    if value is not None:
        extra["value"] = value
    if match.group(3):
        extra["limit"] = match.group(3).casefold()
    return _known(_BY_WORD[prefix], raw, **extra)


def _describe_iso_fit(raw: str) -> dict[str, Any] | None:
    """A size plus an ISO 286 code, or the code alone. Limits stay uncalculated.

    A lowercase code is a shaft. An uppercase code is a hole. The callout is
    not a hole operation. A bare M and a grade is left unknown so a metric
    thread designation is not read as a fit.
    """
    match = _ISO_FIT_TOKEN.fullmatch(raw.strip())
    if not match:
        return None
    dev = match.group("dev")
    if dev in _ISO_SHAFT_DEVIATIONS:
        applies = "shaft"
    elif dev in _ISO_HOLE_DEVIATIONS:
        applies = "hole"
    else:
        return None
    try:
        grade = int(match.group("grade"))
    except ValueError:
        return None
    if grade < 1 or grade > 18:
        return None
    size_token = match.group("size")
    if size_token is None and dev == "M":
        return None
    extra: dict[str, Any] = {
        "deviation": dev,
        "grade": grade,
        "applies_to": applies,
    }
    if size_token:
        size = _note_number(size_token)
        if size is None:
            return None
        extra["size"] = size
    return _known(_BY_ID["iso_fit"], raw, **extra)


def _describe_degree(raw: str) -> dict[str, Any] | None:
    match = _DEGREE_CALLOUT.fullmatch(raw.strip())
    if not match:
        return None
    angle = _note_number(match.group(1))
    if angle is None:
        return None
    return _known(_BY_ID["degree"], raw, angle_deg=angle)


def _describe_plus_minus(raw: str) -> dict[str, Any] | None:
    """±, +/−, or a written plus and minus. Limit values are not calculated."""
    text = raw.strip()
    bilateral = _PM_BILATERAL.fullmatch(text)
    if bilateral:
        up = _note_number(bilateral.group("up"))
        down = _note_number(bilateral.group("down"))
        if up is None or down is None:
            return None
        return _known(
            _BY_ID["plus_minus"],
            raw,
            plus_value=up,
            minus_value=down,
        )
    slash = _PM_SLASH.fullmatch(text)
    if slash:
        extra: dict[str, Any] = {}
        if slash.group("nom"):
            nominal = _note_number(slash.group("nom"))
            if nominal is not None:
                extra["nominal"] = nominal
        if slash.group("tol"):
            tolerance = _note_number(slash.group("tol"))
            if tolerance is not None:
                extra["tolerance"] = tolerance
        return _known(_BY_ID["plus_minus"], raw, **extra)
    glyph = _PM_GLYPH.fullmatch(text)
    if not glyph:
        return None
    extra = {}
    if glyph.group("nom"):
        nominal = _note_number(glyph.group("nom"))
        if nominal is not None:
            extra["nominal"] = nominal
    if glyph.group("tol"):
        tolerance = _note_number(glyph.group("tol"))
        if tolerance is not None:
            extra["tolerance"] = tolerance
    return _known(_BY_ID["plus_minus"], raw, **extra)


def _describe_thread(raw: str) -> dict[str, Any] | None:
    """UNC, metric, or NPT. The process stays blank unless the line says otherwise."""
    compact = re.sub(r"\s+", "", raw)
    unified = _THREAD.fullmatch(compact) or _THREAD.fullmatch(raw)
    if unified:
        described = _known(_BY_ID["thread"], raw, series=unified.group(5).upper())
        if unified.group(6):
            described["thread_class"] = unified.group(6).upper()
        tpi = unified.group(4)
        if tpi:
            described["threads_per_inch"] = int(tpi)
        return described
    metric = _METRIC_THREAD.fullmatch(raw.strip()) or _METRIC_THREAD.fullmatch(compact)
    if metric:
        described = _known(_BY_ID["thread"], raw)
        described["citation"] = (
            "ASME B1.13M, Metric Screw Threads. "
            "The designation states major diameter and pitch. "
            "It does not say tap or single-point, so the thread process stays blank."
        )
        described["meaning"] = (
            "A metric screw-thread designation states major diameter and pitch. "
            "It does not say tap or single-point, so the thread process stays blank."
        )
        described["major_diameter_mm"] = _note_number(metric.group(1))
        described["pitch_mm"] = _note_number(metric.group(2))
        fit = metric.group(3) or metric.group(4)
        if fit:
            described["thread_class"] = fit.upper()
        if re.search(r"\bTAP\b", raw, re.IGNORECASE):
            described["thread_form"] = "tap"
            described["meaning"] = (
                "A metric screw-thread designation states major diameter and pitch. "
                "The line says TAP. It does not name lathe or mill."
            )
        if re.search(r"\bISO\b", raw, re.IGNORECASE):
            described["thread_standard"] = "ISO"
        return described
    npt = _NPT_THREAD.fullmatch(raw.strip()) or _NPT_THREAD.fullmatch(compact)
    if npt or raw.casefold() == "npt":
        described = _known(_BY_ID["thread"], raw, series="NPT")
        described["citation"] = (
            "ASME B1.20.1, Pipe Threads, General Purpose (Inch). "
            "The callout is the NPT designation as written. "
            "It does not say tap or single-point, so the thread process stays blank."
        )
        described["meaning"] = (
            "An NPT designation is a National Pipe Taper thread. "
            "It does not say tap or single-point, so the thread process stays blank."
        )
        if npt and (npt.group(1) or npt.group(3)):
            size = _note_number(
                f"{npt.group(1)}/{npt.group(2)}" if npt.group(1) else npt.group(3)
            )
            if size is not None:
                described["size_in"] = size
        return described
    return None


def _describe_counterbore(raw: str) -> dict[str, Any] | None:
    """CB or the counterbore symbol with a diameter. The bare word stays on the word list."""
    if raw.casefold() in {"cb", "counterbore", "spotface"}:
        return None
    if not _COUNTERBORE_WORD.search(raw):
        return None
    marked = _DIAMETER_MARK.search(raw)
    if not marked and "⌴" not in raw:
        return None
    extra: dict[str, Any] = {}
    if marked:
        diameter = _note_number(marked.group(1))
        if diameter is not None:
            extra["diameter_in"] = diameter
    tolerance = re.search(rf"±\s*{_NOTE_NUMBER}", raw)
    if tolerance:
        value = _note_number(tolerance.group(1))
        if value is not None:
            extra["tolerance"] = value
    if not extra and "⌴" not in raw:
        return None
    return _known(_BY_ID["counterbore"], raw, **extra)


def _with_value(entry_id: str, raw: str, value: float | None) -> dict[str, Any]:
    extra: dict[str, Any] = {}
    if value is not None:
        extra["value"] = value
    return _known(_BY_ID[entry_id], raw, **extra)


def _describe_geometric(raw: str) -> dict[str, Any] | None:
    """GD&T and drawing notes that are callouts, not operations."""
    text = raw.strip()
    if text.count("\u2316") >= 2:
        return _known(_BY_ID["composite_position"], raw, frames=text.count("\u2316"))
    position = _POSITION_LINE.fullmatch(text)
    if position:
        return _with_value("position", raw, _note_number(position.group("val")))
    parallel = _PARALLEL_LINE.fullmatch(text)
    if parallel:
        return _with_value("parallelism", raw, _note_number(parallel.group("val")))
    perp = _PERP_LINE.fullmatch(text)
    if perp:
        return _with_value("perpendicularity", raw, _note_number(perp.group("val")))
    flat = _FLAT_LINE.fullmatch(text)
    if flat:
        value = _note_number(flat.group("a") or flat.group("b") or flat.group("c"))
        return _with_value("flatness", raw, value)
    basic = _BASIC_LINE.fullmatch(text)
    if basic and text.casefold() != "basic":
        return _with_value("basic", raw, _note_number(basic.group("a") or basic.group("b")))
    reference = _REFERENCE_DIM.fullmatch(text)
    if reference:
        extra: dict[str, Any] = {}
        value = _note_number(reference.group("val"))
        if value is not None:
            extra["value"] = value
        if reference.group("dia"):
            extra["diameter"] = True
        return _known(_BY_ID["reference"], raw, **extra)
    datum = _DATUM_LINE.fullmatch(text)
    if datum:
        return _known(_BY_ID["datum"], raw, datum_letter=datum.group(1).upper())
    circle = _BOLT_CIRCLE_LINE.fullmatch(text)
    if circle:
        return _with_value("bolt_circle", raw, _note_number(circle.group("val")))
    depth_range = _DEPTH_RANGE.fullmatch(text)
    if depth_range:
        first = _note_number(depth_range.group("a"))
        second = _note_number(depth_range.group("b"))
        limits = [item for item in (first, second) if item is not None]
        return _known(_BY_ID["depth"], raw, depth_limits=limits)
    depth = _DEPTH_ONE.fullmatch(text)
    if depth:
        return _with_value("depth", raw, _note_number(depth.group("v")))
    diameter = _DIA_VALUE.fullmatch(text)
    if diameter:
        extra = {}
        nominal = _note_number(diameter.group("nom"))
        if nominal is not None:
            extra["value"] = nominal
        tolerance = _note_number(diameter.group("tol"))
        if tolerance is not None:
            extra["tolerance"] = tolerance
            extra["citation"] = (
                f"{_BY_ID['diameter']['citation']} {_BY_ID['plus_minus']['citation']}"
            )
        described = _known(_BY_ID["diameter"], raw, **extra)
        if tolerance is not None:
            described["citation"] = extra["citation"]
        return described
    return None


def describe_symbol(token: str) -> dict[str, Any]:
    """Return the cited meaning, or unknown with a blank meaning."""
    raw = (token or "").strip()
    if not raw:
        return _unknown(raw)
    if raw in _BY_GLYPH:
        return _known(_BY_GLYPH[raw], raw)
    folded = raw.casefold()
    if folded in _BY_WORD:
        return _known(_BY_WORD[folded], raw)
    places = _NX.fullmatch(raw)
    if places:
        return _known(_BY_ID["repetition"], raw, count=int(places.group(1)))
    finish = _describe_surface_finish(raw)
    if finish is not None:
        return finish
    radius_value = _describe_radius_value(raw)
    if radius_value is not None:
        return radius_value
    thread = _describe_thread(raw)
    if thread is not None:
        return thread
    fit = _describe_iso_fit(raw)
    if fit is not None:
        return fit
    named = _named_feature_note(raw)
    if named is not None:
        return named
    bore = _describe_counterbore(raw)
    if bore is not None:
        return bore
    geometric = _describe_geometric(raw)
    if geometric is not None:
        return geometric
    degree = _describe_degree(raw)
    if degree is not None:
        return degree
    plus = _describe_plus_minus(raw)
    if plus is not None:
        return plus
    return _unknown(raw)


def unknown_symbols_in_text(text: str) -> list[dict[str, Any]]:
    """Symbol-like characters that this library does not define.

    Latin letters are skipped. A known glyph is not reported here.
    """
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    covered: set[int] = set()
    for match in _PLUS_MINUS_CHAR_SPAN.finditer(text or ""):
        covered.update(range(match.start(), match.end()))
    for index, char in enumerate(text or ""):
        if index in covered or ord(char) < 128 or char in KNOWN_GLYPHS or char in seen:
            continue
        if unicodedata_letter(char):
            continue
        if char in _CHECK_GLYPHS and re.match(r"\s*[0-9]", (text or "")[index + 1 : index + 8]):
            continue
        seen.add(char)
        found.append(describe_symbol(char))
    return found


def unicodedata_letter(char: str) -> bool:
    import unicodedata

    return unicodedata.category(char).startswith("L")
