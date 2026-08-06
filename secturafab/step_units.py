"""Convert metric STEP files to inch units before SecturaFAB import."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

_MM_UNIT_ENTITY_RE = re.compile(
    r"(#(?P<id>\d+)\s*=\s*\(\s*"
    r"LENGTH_UNIT\s*\(\s*\)\s*"
    r"NAMED_UNIT\s*\(\s*\*\s*\)\s*"
    r"SI_UNIT\s*\(\s*\.MILLI\.\s*,\s*\.METRE\.\s*\)\s*"
    r"\)\s*;)",
    re.IGNORECASE | re.DOTALL,
)
_MM_SI_ONLY_RE = re.compile(
    r"SI_UNIT\s*\(\s*\.MILLI\.\s*,\s*\.METRE\.\s*\)",
    re.IGNORECASE,
)
_CARTESIAN_POINT_RE = re.compile(
    r"(CARTESIAN_POINT\s*\(\s*'[^']*'\s*,\s*\()"
    r"([^)]+)"
    r"(\))",
    re.IGNORECASE,
)
_LENGTH_MEASURE_RE = re.compile(
    r"(LENGTH_MEASURE\s*\(\s*)([-+0-9.Ee]+)(\s*\))",
    re.IGNORECASE,
)
_ENTITY_ID_RE = re.compile(r"#(\d+)\s*=")

_MM_TO_IN = 1.0 / 25.4


def step_uses_millimetres(text: str) -> bool:
    return bool(_MM_SI_ONLY_RE.search(text or ""))


def _scale_number_list(raw: str, factor: float) -> str:
    parts: list[str] = []
    for token in raw.split(","):
        token_stripped = token.strip()
        if not token_stripped:
            parts.append(token)
            continue
        try:
            val = float(token_stripped)
        except ValueError:
            parts.append(token)
            continue
        scaled = val * factor
        parts.append("0." if abs(scaled) < 1e-12 else f"{scaled:.10g}")
    return ",".join(parts)


def _next_entity_ids(text: str, count: int = 2) -> list[int]:
    ids = [int(x) for x in _ENTITY_ID_RE.findall(text)]
    start = (max(ids) + 1) if ids else 90000
    return list(range(start, start + count))


def convert_step_text_mm_to_inch(text: str) -> tuple[str, bool]:
    """
    Return (converted_text, changed).

    Scales CARTESIAN_POINT / LENGTH_MEASURE from mm to inch and rewrites the
    length unit entity to CONVERSION_BASED_UNIT('INCH', …).
    """
    if not step_uses_millimetres(text):
        return text, False

    def _scale_points(match: re.Match[str]) -> str:
        return match.group(1) + _scale_number_list(match.group(2), _MM_TO_IN) + match.group(3)

    def _scale_length(match: re.Match[str]) -> str:
        try:
            val = float(match.group(2))
        except ValueError:
            return match.group(0)
        return f"{match.group(1)}{(val * _MM_TO_IN):.10g}{match.group(3)}"

    out = _CARTESIAN_POINT_RE.sub(_scale_points, text)
    out = _LENGTH_MEASURE_RE.sub(_scale_length, out)

    metre_id, inch_factor_id = _next_entity_ids(out, 2)
    match = _MM_UNIT_ENTITY_RE.search(out)
    if match:
        unit_id = match.group("id")
        replacement = (
            f"#{metre_id}=(LENGTH_UNIT()NAMED_UNIT(*)SI_UNIT($,.METRE.));\n"
            f"#{inch_factor_id}=LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(0.0254),#{metre_id});\n"
            f"#{unit_id}=("
            f"CONVERSION_BASED_UNIT('INCH',#{inch_factor_id})"
            f"LENGTH_UNIT()"
            f"NAMED_UNIT(*)"
            f");"
        )
        out = out[: match.start()] + replacement + out[match.end() :]
    else:
        # Fallback: coords already scaled; drop milli prefix so values read as metres
        # only if entity rewrite failed — still better than leaving mm labels on inch nums.
        out = _MM_SI_ONLY_RE.sub("SI_UNIT($,.METRE.)", out, count=1)

    return out, True


def prepare_step_for_imperial_import(stp_path: Path | str) -> tuple[Path, list[str]]:
    """
    Return a STEP path safe to upload (possibly a temp inch-converted copy).

    Caller should delete temp files when finished uploading.
    """
    path = Path(stp_path)
    notes: list[str] = []
    if not path.is_file():
        return path, [f"STEP not found: {path}"]
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1")
    converted, changed = convert_step_text_mm_to_inch(text)
    if not changed:
        notes.append(f"STEP {path.name} already non-metric (no mm length unit rewrite)")
        return path, notes

    tmp = tempfile.NamedTemporaryFile(
        prefix=f"{path.stem}_inch_",
        suffix=path.suffix or ".stp",
        delete=False,
    )
    tmp_path = Path(tmp.name)
    tmp.close()
    tmp_path.write_text(converted, encoding="ascii", errors="replace", newline="\n")
    notes.append(
        f"Converted {path.name} mm→inch for SecturaFAB import (temp {tmp_path.name})"
    )
    return tmp_path, notes
