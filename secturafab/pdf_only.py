"""Route one drawing (no STEP) to Image Files or Long.

Plate/sheet uses Image Files. Tube/bar/angle/channel uses Long.
Thickness, gauge, flat size, and cut length come only from the drawing
text. A missing required field is a FLAG. Nothing is invented.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quote_core.drawing_title import extract_title_from_pdf_text
from quote_core.part_materials import _sectura_material_string, parse_material_block

from .item_desc import parse_plate_flats
from .line_item_ops import parse_cut_length
from .push import (
    _cad_plate_sheet_noun,
    _has_linear_noun,
    classify_sectura_item,
    plate_over_three_quarter,
)


@dataclass(frozen=True)
class PdfOnlyPlan:
    """What a single PDF-only part should do on push.

    ``route`` is ``image_files``, ``long``, ``refuse``, or ``unclassified``.
    Unclassified leaves the existing push path alone (empty or non-stock text).
    """

    route: str
    missing: tuple[str, ...] = ()
    description: str = ""
    material: str | None = None
    thickness_in: float | None = None
    width_in: float | None = None
    length_in: float | None = None
    cut_length_in: float | None = None
    notes: tuple[str, ...] = ()


def _flag(field: str, detail: str) -> str:
    return f"FLAG: {field} — {detail}"


def _stock_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if _cad_plate_sheet_noun(line) or _has_linear_noun(line):
            lines.append(line)
    return lines


def _classify_blob(text: str, title: str, part_key: str) -> tuple[str, str]:
    drawing_title = extract_title_from_pdf_text(text, part_key=part_key or None) or ""
    stock = _stock_lines(text)
    parts = [str(title or "").strip(), drawing_title, *stock]
    blob = " ".join(part for part in parts if part).strip()
    return blob, drawing_title


def _parsed_grade(material_key: str | None, source: str) -> str | None:
    """Grade only when the drawing named one. A defaulted A36 is not a parse."""
    if not material_key:
        return None
    if "default" in str(source or "").lower():
        return None
    return _sectura_material_string(material_key)


def _description(drawing_title: str, stock: list[str], title: str) -> str:
    parts: list[str] = []
    for part in (drawing_title, *stock, str(title or "").strip()):
        text = str(part or "").strip()
        if text and text not in parts:
            parts.append(text)
    return " ".join(parts).strip()


def plan_pdf_only_part(
    *,
    text: str,
    title: str = "",
    part_key: str = "",
) -> PdfOnlyPlan:
    """Decide Image Files vs Long from drawing text. Never invent a dimension."""
    blob, drawing_title = _classify_blob(text, title, part_key)
    plate = _cad_plate_sheet_noun(blob)
    linear = _has_linear_noun(blob)
    if not plate and not linear:
        return PdfOnlyPlan(route="unclassified")

    thickness_in, material_key, source = parse_material_block(text)
    category = classify_sectura_item(blob, thickness_in)
    stock = _stock_lines(text)
    description = _description(drawing_title, stock, title)
    material = _parsed_grade(material_key, source)

    if category == "Linear" or (linear and not plate):
        cut = parse_cut_length(text) or parse_cut_length(title)
        if cut is None:
            note = _flag(
                "cut length",
                "PDF parse did not give a cut length (LG / LENGTH / OAL); "
                "not inventing a length",
            )
            return PdfOnlyPlan(
                route="refuse",
                missing=("cut length",),
                description=description,
                material=material,
                notes=(note,),
            )
        note = (
            f"PDF-only tube/bar → Long; cut length {cut:g} in from the drawing"
        )
        return PdfOnlyPlan(
            route="long",
            description=description,
            material=material,
            cut_length_in=float(cut),
            notes=(note,),
        )

    if plate and thickness_in is not None and plate_over_three_quarter(thickness_in):
        note = _flag(
            "thickness",
            f"{thickness_in:g} in is over 3/4 in — not an Image Files plate "
            "(not inventing a laser cost)",
        )
        return PdfOnlyPlan(
            route="refuse",
            missing=("thickness",),
            description=description,
            material=material,
            thickness_in=float(thickness_in),
            notes=(note,),
        )

    if category == "Cad" or plate:
        missing: list[str] = []
        notes: list[str] = []
        if thickness_in is None:
            missing.append("thickness")
            notes.append(
                _flag(
                    "thickness",
                    "PDF parse did not give a thickness or gauge; "
                    "not inventing a gauge",
                )
            )
        width_in, length_in = parse_plate_flats(text)
        if not (width_in and length_in):
            missing.append("L/W")
            notes.append(
                _flag(
                    "L/W",
                    "PDF parse did not give length and width; not inventing flats",
                )
            )
        if missing:
            return PdfOnlyPlan(
                route="refuse",
                missing=tuple(missing),
                description=description,
                material=material,
                thickness_in=float(thickness_in) if thickness_in is not None else None,
                width_in=width_in,
                length_in=length_in,
                notes=tuple(notes),
            )
        note = (
            "PDF-only plate/sheet → Image Files; "
            f"thickness {float(thickness_in):g} in; "
            f"L/W {float(width_in):g} x {float(length_in):g} in from the drawing"
        )
        return PdfOnlyPlan(
            route="image_files",
            description=description,
            material=material,
            thickness_in=float(thickness_in),
            width_in=float(width_in),
            length_in=float(length_in),
            notes=(note,),
        )

    return PdfOnlyPlan(route="unclassified", description=description)


def plan_pdf_only_file(
    path: Path | None,
    *,
    title: str = "",
    part_key: str = "",
) -> PdfOnlyPlan:
    """Read one PDF. Unreadable bytes stay unclassified (no invented fields)."""
    if path is None or not Path(path).is_file():
        return PdfOnlyPlan(route="unclassified")
    try:
        from quote_core.weight import _read_pdf_text

        text = _read_pdf_text(path) or ""
    except Exception:  # noqa: BLE001 — corrupt test PDFs are not a stock callout
        text = ""
    return plan_pdf_only_part(text=text, title=title, part_key=part_key)
