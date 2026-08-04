"""Per-part material / thickness from component PDF title blocks.

Shop drawings typically list a MATERIAL block::

    MATERIAL
    3/16
    A36

or::

    MATERIAL
    5/16
    GR50

Used by SecturaFAB push to call UpdateItem_Part per quote line.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quote_core.weight import _read_pdf_text, detect_material_key, load_materials

# Fraction plate thicknesses (inches).
_FRACTION_MAP: dict[str, float] = {
    "1/8": 0.125,
    "3/16": 0.1875,
    "1/4": 0.25,
    "5/16": 0.3125,
    "3/8": 0.375,
    "7/16": 0.4375,
    "1/2": 0.5,
    "9/16": 0.5625,
    "5/8": 0.625,
    "3/4": 0.75,
    "7/8": 0.875,
    "1": 1.0,
}

# Common sheet gauges → inches (carbon steel approximate).
_GAUGE_IN: dict[str, float] = {
    "10": 0.1345,
    "11": 0.1196,
    "12": 0.1046,
    "14": 0.0747,
    "16": 0.0598,
    "18": 0.0478,
    "20": 0.0359,
    "22": 0.0299,
    "24": 0.0239,
    "26": 0.0179,
}

# Bare grade callouts on MAC drawings (line under thickness).
_BARE_GRADE_KEYS: dict[str, str] = {
    "GR50": "a572_gr50",
    "GR 50": "a572_gr50",
    "GRADE 50": "a572_gr50",
    "G50": "a572_gr50",
    "GR65": "a572_gr65",
    "GR 65": "a572_gr65",
    "GR55": "a572_gr55",
    "GR42": "a572_gr42",
    "GR80": "a656_gr80",
    "GR 80": "a656_gr80",
    "GRADE 80": "a656_gr80",
    "GR70": "a656_gr70",
    "GR60": "a656_gr60",
    "A36": "a36",
    "A572": "a572_gr50",
    "STEEL": "a36",
}

_THICKNESS_LINE_RE = re.compile(
    # Fractions and gauges only — bare "1" is usually a balloon/sheet count, not 1" plate.
    r"^(?P<thk>[0-9]+\s*/\s*[0-9]+|[0-9]+\.[0-9]+|[0-9]+\s*GA(?:UGE)?)$",
    re.IGNORECASE,
)
_GRADE_LINE_RE = re.compile(
    r"^(?P<grade>A\s*572(?:\s*(?:GR|GRADE|G)?\s*\d+)?|A\s*656(?:\s*(?:GR|GRADE|G)?\s*\d+)?|"
    r"A\s*36|A\s*514|A\s*992|GR\s*\d+|GRADE\s*\d+|G\s*\d+|STEEL|GALV(?:ANISED|ANIZED)?)$",
    re.IGNORECASE,
)

# Title-block: MATERIAL (alone on a line) then thickness then optional grade.
# Use [ \t]* (not \s*) after tokens so newlines are not swallowed before grade.
_MATERIAL_BLOCK_RE = re.compile(
    r"(?im)^\s*MATERIAL\s*$"
    r"(?:\r?\n)+"
    r"[ \t]*(?P<thk>[0-9]+\s*/\s*[0-9]+|[0-9]+(?:\.[0-9]+)?[ \t]*[\"″']?|[0-9]+[ \t]*GA(?:UGE)?)[ \t]*"
    r"(?:(?:\r?\n)+[ \t]*(?P<grade>[A-Z][A-Z0-9 \-]{0,24})[ \t]*)?"
)

# Same-line variants: MATERIAL: 3/16 A36
_MATERIAL_INLINE_RE = re.compile(
    r"(?i)\bMATERIAL\b(?!\s*No\.?)\s*[:\-]?\s*"
    r"(?P<thk>[0-9]+\s*/\s*[0-9]+|[0-9]+\s*GA(?:UGE)?)"
    r"\s+"
    r"(?P<grade>A\s*572(?:\s*(?:GR|GRADE)?\s*50)?|A\s*36|GR\s*50|GRADE\s*50|"
    r"GALV(?:ANISED|ANIZED)?|A\s*656(?:\s*(?:GR|GRADE)?\s*\d+)?)"
)

_SKIP_NAME_HINTS = (
    "WELDMENT",
    "ALL DRAWING",
    "ALL DRAWINGS",
    "ASSEMBLY",
)


@dataclass(frozen=True)
class PartMaterial:
    part_key: str
    material_key: str
    material: str  # SecturaFAB UpdateItem_Part material string
    thickness_in: float | None
    source: str
    raw_grade: str = ""
    raw_thickness: str = ""

    def thickness_param(self) -> str | None:
        if self.thickness_in is None or self.thickness_in <= 0:
            return None
        # Prefer compact decimals SecturaFAB accepts (0.1875, 0.3125, …).
        t = self.thickness_in
        if abs(t - round(t, 4)) < 1e-9:
            return f"{t:.4g}"
        return f"{t:.4f}".rstrip("0").rstrip(".")


def _parse_thickness_token(raw: str) -> float | None:
    text = (raw or "").strip().upper().replace('"', "").replace("″", "").replace("'", "")
    text = re.sub(r"\s+", "", text)
    if not text:
        return None
    gauge = re.fullmatch(r"(\d+)GA(?:UGE)?", text)
    if gauge:
        return _GAUGE_IN.get(gauge.group(1))
    frac = re.fullmatch(r"(\d+)/(\d+)", text)
    if frac:
        key = f"{int(frac.group(1))}/{int(frac.group(2))}"
        return _FRACTION_MAP.get(key)
    # "3/16" with spaces already stripped
    if text in _FRACTION_MAP:
        return _FRACTION_MAP[text]
    try:
        val = float(text)
    except ValueError:
        return None
    if 0.01 <= val <= 2.0:
        return val
    return None


def _grade_to_material_key(grade: str) -> str:
    cleaned = re.sub(r"\s+", " ", (grade or "").strip().upper())
    cleaned = cleaned.replace("GRADE", "GR")
    if cleaned in _BARE_GRADE_KEYS:
        return _BARE_GRADE_KEYS[cleaned]
    # "A572 GR50" / "A572 G50" etc.
    compact = cleaned.replace(" ", "")
    for bare, key in _BARE_GRADE_KEYS.items():
        if bare.replace(" ", "") == compact:
            return key
    if "G50" in compact or "GR50" in compact or (compact.startswith("A572") and "50" in compact):
        return "a572_gr50"
    if compact in {"A36", "ASTMA36"}:
        return "a36"
    # Fall back to shared detector on the grade token only (not whole PDF).
    return detect_material_key([grade])


def _sectura_material_string(material_key: str) -> str:
    cfg = load_materials()
    mat = (cfg.get("materials") or {}).get(material_key) or {}
    label = str(mat.get("label") or material_key).strip()
    # UpdateItem_Part accepts short codes; graded A572 needs the grade in the string
    # (Kyle's UI shows "A572 G50" / "A572 Grade 50").
    if material_key.startswith("a572_gr"):
        return label  # e.g. "A572 Grade 50"
    if material_key.startswith("a656_gr"):
        return label
    if material_key == "a36":
        return "A36"
    # First token of label for other steels (A514, A992, …)
    return label.split()[0] if label else "A36"


def parse_material_block(text: str) -> tuple[float | None, str | None, str]:
    """
    Return (thickness_in, material_key, source_note) from drawing text.

    CAD PDFs often emit title-block values out of visual order, so we look for
    adjacent lines ``3/16`` / ``A36`` (or ``5/16`` / ``GR50``) rather than
    requiring them to follow the MATERIAL label.
    """
    if not text or not text.strip():
        return None, None, "empty"

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    pairs: list[tuple[float, str, str]] = []
    for i, ln in enumerate(lines[:-1]):
        tm = _THICKNESS_LINE_RE.fullmatch(ln)
        if not tm:
            continue
        gm = _GRADE_LINE_RE.fullmatch(lines[i + 1])
        if not gm:
            continue
        thk = _parse_thickness_token(tm.group("thk"))
        if thk is None:
            continue
        grade = gm.group("grade").strip()
        key = _grade_to_material_key(grade)
        pairs.append((thk, key, f"lines {ln!r} + {grade!r}"))

    if pairs:
        # Prefer graded HSLA over generic A36/STEEL when multiple pairs exist.
        pairs.sort(key=lambda p: (0 if p[1] not in {"a36", "carbon_steel"} else 1, p[0]))
        thk, key, src = pairs[0]
        return thk, key, src

    m = _MATERIAL_BLOCK_RE.search(text)
    if m:
        thk = _parse_thickness_token(m.group("thk"))
        grade = (m.groupdict().get("grade") or "").strip()
        if not grade or grade.upper().startswith("NO"):
            return thk, "a36", f"MATERIAL block ({m.group('thk').strip()} / default A36)"
        key = _grade_to_material_key(grade)
        return thk, key, f"MATERIAL block ({m.group('thk').strip()} / {grade})"

    m2 = _MATERIAL_INLINE_RE.search(text)
    if m2:
        thk = _parse_thickness_token(m2.group("thk"))
        grade = (m2.group("grade") or "").strip()
        key = _grade_to_material_key(grade)
        return thk, key, f"MATERIAL inline ({m2.group('thk').strip()} / {grade})"

    # Thickness-only line (e.g. 3/16 with no grade neighbor)
    for ln in lines:
        tm = _THICKNESS_LINE_RE.fullmatch(ln)
        if not tm:
            continue
        thk = _parse_thickness_token(tm.group("thk"))
        if thk is not None and thk <= 1.0:
            return thk, "a36", f"thickness line {ln!r} / default A36"

    return None, None, "no_material_block"


def part_key_from_pdf_name(name: str) -> str | None:
    stem = Path(name).stem.strip()
    if not stem:
        return None
    upper = stem.upper()
    if any(h in upper for h in _SKIP_NAME_HINTS):
        # Still allow pure PN stems; skip multi-word weldment packets
        if " " in stem or "-" in stem[4:]:
            # e.g. "73476004 WELDMENT DRAWING" — map assembly PN only
            m = re.match(r"^(\d{5,}(?:-\d+)?)", stem)
            return m.group(1) if m else None
    m = re.match(r"^(\d{5,}(?:-\d+)?)", stem)
    if m:
        return m.group(1)
    # Filename is exactly the part number with junk suffix
    m = re.match(r"^([A-Z0-9][A-Z0-9\-]{3,})", stem, re.I)
    return m.group(1) if m else None


def extract_part_material_from_pdf(pdf_path: Path | str) -> PartMaterial | None:
    path = Path(pdf_path)
    key = part_key_from_pdf_name(path.name)
    if not key:
        return None
    text = _read_pdf_text(path)
    thk, mat_key, source = parse_material_block(text)
    if mat_key is None and thk is None:
        return None
    if mat_key is None:
        mat_key = "a36"
        source = f"{source}; defaulted grade A36"
    return PartMaterial(
        part_key=key,
        material_key=mat_key,
        material=_sectura_material_string(mat_key),
        thickness_in=thk,
        source=source,
        raw_grade=mat_key,
        raw_thickness="" if thk is None else str(thk),
    )


def _is_dedicated_component_pdf(pdf_name: str, part_key: str) -> bool:
    """True when filename is essentially the part number (not a weldment packet)."""
    stem = Path(pdf_name).stem.strip()
    if stem == part_key:
        return True
    # Allow "73000567-1" style, reject "73476004 WELDMENT DRAWING"
    if " " in stem:
        return False
    upper = stem.upper()
    if any(h in upper for h in _SKIP_NAME_HINTS):
        return False
    return stem.startswith(part_key) and len(stem) <= len(part_key) + 3


def build_part_material_map(
    *,
    library_folder: Path | str | None,
    related_pdf_names: list[str] | None = None,
    extra_pdfs: list[Path] | None = None,
) -> dict[str, PartMaterial]:
    """
    Map part number → material/thickness from component PDFs in the library folder.
    """
    out: dict[str, PartMaterial] = {}
    dedicated: set[str] = set()
    folder = Path(library_folder) if library_folder else None
    paths: list[Path] = []
    if folder and folder.is_dir():
        for name in related_pdf_names or []:
            p = folder / name
            if p.is_file():
                paths.append(p)
        if not paths:
            paths.extend(sorted(folder.glob("*.pdf")))
    for p in extra_pdfs or []:
        if p.is_file():
            paths.append(p)

    # Process dedicated PN.pdf files first so weldment packets don't overwrite them.
    paths.sort(key=lambda p: (0 if _is_dedicated_component_pdf(p.name, part_key_from_pdf_name(p.name) or "") else 1, p.name.lower()))

    for path in paths:
        try:
            pm = extract_part_material_from_pdf(path)
        except Exception:  # noqa: BLE001
            continue
        if not pm:
            continue
        is_dedicated = _is_dedicated_component_pdf(path.name, pm.part_key)
        # Weldment / "all drawings" packets mix grades — only trust PN.pdf files.
        if not is_dedicated:
            continue
        prev = out.get(pm.part_key)
        if prev and prev.material_key not in {"a36", "carbon_steel"} and pm.material_key in {
            "a36",
            "carbon_steel",
        }:
            continue
        out[pm.part_key] = pm
        dedicated.add(pm.part_key)
    return out


def lookup_part_material(
    part_materials: dict[str, PartMaterial],
    description: str,
) -> PartMaterial | None:
    token = (description or "").strip().split()[0] if description else ""
    if not token:
        return None
    if token in part_materials:
        return part_materials[token]
    # Normalize dashed BOM style 7300056-7 → try compact
    compact = token.replace("-", "")
    for key, pm in part_materials.items():
        if key.replace("-", "") == compact:
            return pm
    return None


def part_materials_to_dict(part_materials: dict[str, PartMaterial]) -> dict[str, Any]:
    return {
        k: {
            "material": v.material,
            "material_key": v.material_key,
            "thickness_in": v.thickness_in,
            "source": v.source,
        }
        for k, v in part_materials.items()
    }
