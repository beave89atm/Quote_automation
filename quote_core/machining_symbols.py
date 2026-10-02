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
        "words": ("counterbore", "spotface"),
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
        "words": ("countersink",),
        "meaning": "Placed with the diameter symbol in front of a countersink diameter.",
        "citation": (
            f"{_GENIUM}, paragraph 2.3. {_Y145} "
            "Text encoding of the countersink symbol: U+2335. "
            "Paragraph 1.5: notes use the symbol name in place of the symbol."
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
        "meaning": "The letter R placed in front of a radius value.",
        "citation": f"{_GENIUM}, paragraph 2.11.2. {_Y145}",
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
        "words": ("ra",),
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
        "id": "iso_fit",
        "glyphs": (),
        "words": (),
        "meaning": (
            "A lowercase letter and a grade after a size are an ISO code for "
            "a shaft fit. The letter is the fundamental deviation and the "
            "number is the tolerance grade. The limit values are not calculated."
        ),
        "citation": (
            "ISO 286-1, ISO code system for tolerances on linear sizes. "
            "Part 1 gives the basis of tolerances, deviations and fits."
        ),
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
_RA = re.compile(r"Ra\s*([0-9]*\.?[0-9]+)", re.IGNORECASE)
_THREAD = re.compile(
    r"(?:(\d+)\s*/\s*(\d+)|(\d*\.\d+|\d+))\s*-\s*(\d+)\s*"
    r"(UNC|UNF|UNEF|UNS|UN)(?:\s*-?\s*(\d[AB]))?",
    re.IGNORECASE,
)
_METRIC_THREAD = re.compile(
    r"M(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)",
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
    if _RA.fullmatch(raw):
        return _known(_BY_ID["surface_texture"], raw)
    compact = re.sub(r"\s+", "", raw)
    shaft_fit = re.fullmatch(r"([a-z])(\d{1,2})", compact)
    if shaft_fit and compact == raw.replace(" ", ""):
        return _known(
            _BY_ID["iso_fit"],
            raw,
            deviation=shaft_fit.group(1),
            grade=int(shaft_fit.group(2)),
        )
    if _THREAD.fullmatch(compact) or _THREAD.fullmatch(raw) or _METRIC_THREAD.fullmatch(compact):
        described = _known(_BY_ID["thread"], raw)
        if _METRIC_THREAD.fullmatch(compact):
            described["citation"] = (
                "ASME B1.13M, Metric Screw Threads. "
                "The designation states major diameter and pitch. "
                "It does not say tap or single-point, so the thread process stays blank."
            )
            described["meaning"] = (
                "A metric screw-thread designation states major diameter and pitch. "
                "It does not say tap or single-point, so the thread process stays blank."
            )
        return described
    return _unknown(raw)


def unknown_symbols_in_text(text: str) -> list[dict[str, Any]]:
    """Symbol-like characters that this library does not define.

    Latin letters are skipped. A known glyph is not reported here.
    """
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for char in text or "":
        if ord(char) < 128 or char in KNOWN_GLYPHS or char in seen:
            continue
        if unicodedata_letter(char):
            continue
        seen.add(char)
        found.append(describe_symbol(char))
    return found


def unicodedata_letter(char: str) -> bool:
    import unicodedata

    return unicodedata.category(char).startswith("L")
