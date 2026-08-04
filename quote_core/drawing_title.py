"""Extract the title / description from a top-level assembly drawing PDF."""

from __future__ import annotations

import re
from pathlib import Path

from quote_core.weight import _read_pdf_text

_SKIP_LINE = re.compile(
    r"(?i)^("
    r"THIS DRAWING|MANUFACTURING INC|DUPLICATION|PROHIBITED|MAC$|"
    r"PART\s*(NO|#)|WEIGHT:?|TRAILER MANUFACTURING|DRAWN:?|DATE:?|REVISION:?|"
    r"UNLESS OTHERWISE|ANGLES|PAGE\s+\d|REV\.?$|REASON FOR CHANGE|ECN|"
    r"DO NOT|SCALE|DRAWING$|SHEET\s+\d|TITLE:?|FINISH$|MATERIAL$|"
    r"DIMENSIONS ARE|TOLERANCES|FRACTIONAL|ANGULAR|DECIMAL|PROPRIETARY|"
    r"THE INFORMATION|REPRODUCTION|WITHOUT THE|AMTECH|RELEASED TO|"
    r"BLACK POWDER|N/A$|BY$|ITEM$|QTY|DESCRIPTION$|WEIGHT$"
    r")"
)

_DIM_ONLY = re.compile(r"^[\d\s\.\-/\"'″×xX±°R,]+$")
_WEIGHT_LBM = re.compile(r"(?i)^\d+(\.\d+)?\s*(lbm|lbs?)\b")
_PART_NUM = re.compile(r"^\d{5,}(?:-\d+)?$")
_DATE = re.compile(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$")


def extract_title_from_pdf_text(text: str, *, part_key: str | None = None) -> str | None:
    """
    Best-effort drawing title (e.g. ``COUPLER ASM, 18-16, PNEUMATIC TANK``).

    Prefers lines with ASM / ASSEMBLY / WELDMENT; otherwise the first
    substantial non-boilerplate line before the BOM ``ITEM`` header.
    """
    if not text or not text.strip():
        return None

    key = (part_key or "").strip()
    candidates: list[str] = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        if re.match(r"^ITEM\b", s, re.IGNORECASE):
            break
        if _SKIP_LINE.match(s):
            continue
        if _DIM_ONLY.match(s) or _WEIGHT_LBM.match(s) or _DATE.match(s):
            continue
        if _PART_NUM.match(s):
            continue
        if key and s == key:
            continue
        if len(s) < 6:
            continue
        candidates.append(s)

    if not candidates:
        return None

    for s in candidates:
        upper = s.upper()
        if any(tok in upper for tok in (" ASM", "ASM,", "ASSEMBLY", "WELDMENT", "COUPLER")):
            return s[:200]
    # First solid title-like line
    return candidates[0][:200]


def resolve_assembly_drawing_paths(
    *,
    part_key: str,
    pdf_path: Path | None,
    library_folder: Path | str | None,
    related_pdf_names: list[str] | None = None,
) -> list[Path]:
    """Prefer the top-level PN.pdf, then weldment / all-drawing packets."""
    key = (part_key or "").strip()
    if key.upper().startswith("PN "):
        key = key[3:].strip()
    paths: list[Path] = []
    seen: set[str] = set()

    def add(p: Path | None) -> None:
        if not p or not p.is_file():
            return
        rp = str(p.resolve())
        if rp in seen:
            return
        seen.add(rp)
        paths.append(p)

    folder = Path(library_folder) if library_folder else None
    # 1) Job primary PDF if it matches the assembly PN
    if pdf_path and pdf_path.is_file():
        stem = pdf_path.stem.strip()
        if stem == key or stem.startswith(key):
            add(pdf_path)
    # 2) Library PN.pdf
    if folder and folder.is_dir() and key:
        add(folder / f"{key}.pdf")
    # 3) Weldment / assembly packets named with the PN
    if folder and folder.is_dir():
        for name in related_pdf_names or []:
            upper = name.upper()
            if key and key in name and any(
                h in upper for h in ("WELDMENT", "ALL DRAWING", "ASSEMBLY", "ASM")
            ):
                add(folder / name)
    return paths


def extract_assembly_description(
    *,
    part_key: str,
    pdf_path: Path | None = None,
    library_folder: Path | str | None = None,
    related_pdf_names: list[str] | None = None,
) -> str | None:
    """Read the top-level assembly drawing and return its title for quote Description."""
    for path in resolve_assembly_drawing_paths(
        part_key=part_key,
        pdf_path=pdf_path,
        library_folder=library_folder,
        related_pdf_names=related_pdf_names,
    ):
        try:
            text = _read_pdf_text(path)
        except Exception:  # noqa: BLE001
            continue
        title = extract_title_from_pdf_text(text, part_key=part_key)
        if title:
            return title
    return None
