"""Route one drawing (no STEP) to Image Files or Long.

Plate/sheet uses Image Files. Tube/bar/angle/channel uses Long.
Thickness, gauge, flat size, and cut length come only from the drawing
text. A missing required field is a FLAG. Nothing is invented.

A missing grade is also a FLAG. Carbon steel with no grade uses the shop
config grade (A36 unless changed) and still pushes. Any other family, or a
drawing that does not name a family, is flagged and not given a grade.

A flat plate with no bend callouts has bend count 0 and no Bend op.
A formed part's bend count comes from the conventions library. The flat
length comes from the press-brake chart (K-factor, allowance, or
deduction). That flat L×W is what Image Files would stamp. The same count
has to be written on the Bend operation as ``NumberOfBends``. Nothing
captured in this repo writes that field, so the push stops before a quote
is created with ``FLAG: bend count``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from quote_core.config import load_shop_rates
from quote_core.drawing_title import extract_title_from_pdf_text
from quote_core.part_materials import _sectura_material_string, parse_material_block

from .bend_op import BEND_COUNT_NOT_SET, BEND_COUNT_WRITE_GAP_NOTE
from .flat_pattern import evaluate_formed
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
    bend_count: int | None = None
    line_note: str = ""
    operations: tuple[str, ...] = ()
    flats_from_chart: bool = False


def _flag(field: str, detail: str) -> str:
    return f"FLAG: {field} — {detail}"


# Parser keys that name a family, not a grade. A36 is a grade only when the
# drawing actually writes A36 — the material parser also uses it as a seed.
_FAMILY_ONLY_KEYS = {"carbon_steel", "stainless_300", "aluminum"}
_LITERAL_GRADES = {
    "A1011",
    "A519",
    "AR400",
    "AR450",
    "AR500",
    "DOMEX/WELDOX",
    "100K",
}
# Specific grades. Family words (CARBON STEEL, STAINLESS, ALUMINUM) are not here.
_NAMED_GRADE_RES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)(?<![A-Z0-9])A\s*[-]?\s*656\b"), "a656_gr80"),
    (re.compile(r"(?i)\bGR(?:ADE)?\s*80\b"), "a656_gr80"),
    (re.compile(r"(?i)\bGR(?:ADE)?\s*70\b"), "a656_gr70"),
    (re.compile(r"(?i)\bGR(?:ADE)?\s*65\b"), "a572_gr65"),
    (re.compile(r"(?i)\bGR(?:ADE)?\s*60\b"), "a656_gr60"),
    (re.compile(r"(?i)\bGR(?:ADE)?\s*55\b"), "a572_gr55"),
    (re.compile(r"(?i)\bGR(?:ADE)?\s*42\b"), "a572_gr42"),
    (
        re.compile(
            r"(?i)(?<![A-Z0-9])A\s*[-]?\s*572\b|\bGR(?:ADE)?\s*50\b|"
            r"\b50\s*K\b|\bG\s*50\b|\bPL0?25(?:\s*-\s*50\s*K)?\b"
        ),
        "a572_gr50",
    ),
    (re.compile(r"(?i)(?<![A-Z0-9])A\s*[-]?\s*516\b"), "a516_gr70"),
    (re.compile(r"(?i)(?<![A-Z0-9])A\s*[-]?\s*514\b"), "a514"),
    (re.compile(r"(?i)(?<![A-Z0-9])A\s*[-]?\s*500\b"), "a500"),
    (re.compile(r"(?i)(?<![A-Z0-9])A\s*[-]?\s*992\b"), "a992"),
    (re.compile(r"(?i)(?<![A-Z0-9])A\s*[-]?\s*1011\b"), "A1011"),
    (re.compile(r"(?i)(?<![A-Z0-9])A\s*[-]?\s*519\b"), "A519"),
    (re.compile(r"(?i)\bAR\s*[-]?\s*500\b"), "AR500"),
    (re.compile(r"(?i)\bAR\s*[-]?\s*450\b"), "AR450"),
    (re.compile(r"(?i)\bAR\s*[-]?\s*400\b"), "AR400"),
    (re.compile(r"(?i)\bDOMEX\b|\bWELDOX\b"), "DOMEX/WELDOX"),
    (re.compile(r"(?i)\b100\s*K\b"), "100K"),
    (re.compile(r"(?i)\b6061(?:\s*-?\s*T6)?\b"), "aluminum_6061"),
    (re.compile(r"(?i)\b5052(?:\s*-?\s*H32)?\b|\bALPL[A-Z0-9\-]*\b"), "aluminum_5052"),
    (
        re.compile(
            r"(?i)\b(?:316\s*(?:SS|STAINLESS)|(?:SS|STAINLESS|TYPE)\s*316|316SS)\b"
        ),
        "stainless_316",
    ),
    (
        re.compile(
            r"(?i)\b(?:304\s*(?:SS|STAINLESS)|(?:SS|STAINLESS|TYPE)\s*304|304SS)\b"
        ),
        "stainless_304",
    ),
    (re.compile(r"(?i)(?<![A-Z0-9])A\s*[-]?\s*36\b"), "a36"),
)
# Explicit carbon-steel family only. Bare STEEL, PLATE, TUBE, HSS, or a
# thickness are not enough — those stay unidentified.
_CARBON_FAMILY_RE = re.compile(
    r"(?i)\b(?:CARBON\s+STEEL|MILD\s+STEEL|HOT[-\s]?ROLLED\s+STEEL|"
    r"COLD[-\s]?ROLLED\s+STEEL|H\.?R\.?\s+STEEL)\b"
)
_OTHER_FAMILIES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("stainless", re.compile(r"(?i)\bSTAINLESS(?:\s+STEEL)?\b")),
    ("aluminum", re.compile(r"(?i)\bALUMIN(?:UM|IUM)\b|\bALUM\b")),
    ("brass", re.compile(r"(?i)\bBRASS\b")),
    ("bronze", re.compile(r"(?i)\bBRONZE\b")),
    ("copper", re.compile(r"(?i)\bCOPPER\b")),
    ("titanium", re.compile(r"(?i)\bTITANIUM\b")),
)


def _carbon_steel_default_grade() -> str:
    grade = str(load_shop_rates().carbon_steel_default_grade or "").strip()
    return grade or "A36"


def _grade_token_material(token: str) -> str:
    if token in _LITERAL_GRADES:
        return token
    return _sectura_material_string(token)


def _named_grade_material(text: str) -> str | None:
    """Sectura grade string when the drawing names one. None if it does not."""
    matched: str | None = None
    for rx, token in _NAMED_GRADE_RES:
        if rx.search(text or ""):
            matched = token
            break
    if matched is None:
        return None
    _thk, key, source = parse_material_block(text)
    defaulted = "default" in str(source or "").lower()
    a36_written = bool(re.search(r"(?i)(?<![A-Z0-9])A\s*[-]?\s*36\b", text or ""))
    if (
        key
        and key not in _FAMILY_ONLY_KEYS
        and not defaulted
        and (key != "a36" or a36_written)
    ):
        parsed = _parsed_grade(key, source)
        if parsed:
            return parsed
    return _grade_token_material(matched)


def _other_family_name(text: str) -> str | None:
    for name, rx in _OTHER_FAMILIES:
        if rx.search(text or ""):
            return name
    return None


@dataclass(frozen=True)
class _GradeDecision:
    material: str | None = None
    flag: str | None = None
    blocks: bool = False


def _grade_decision(text: str) -> _GradeDecision:
    """Named grade, carbon-steel default, or stop with no grade applied."""
    named = _named_grade_material(text)
    if named:
        return _GradeDecision(material=named)
    other = _other_family_name(text)
    if other:
        return _GradeDecision(
            flag=_flag(
                "material grade",
                f"{other} called out with no grade; not defaulting a grade",
            ),
            blocks=True,
        )
    if _CARBON_FAMILY_RE.search(text or ""):
        grade = _carbon_steel_default_grade()
        return _GradeDecision(
            material=grade,
            flag=_flag(
                "material grade",
                f"carbon steel with no grade; defaulted to {grade} "
                "from shop config; confirm the grade",
            ),
        )
    return _GradeDecision(
        flag=_flag(
            "material grade",
            "material family not identified; not defaulting a grade",
        ),
        blocks=True,
    )


def _with_grade(grade: _GradeDecision, *notes: str) -> tuple[str, ...]:
    """Grade note first so a dimension FLAG stays last (that note is the error)."""
    head = (grade.flag,) if grade.flag else ()
    return head + notes


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
    drawings: list | None = None,
) -> PdfOnlyPlan:
    """Decide Image Files vs Long from drawing text. Never invent a dimension."""
    blob, drawing_title = _classify_blob(text, title, part_key)
    plate = _cad_plate_sheet_noun(blob)
    linear = _has_linear_noun(blob)
    thickness_in, _material_key, _source = parse_material_block(text)
    category = classify_sectura_item(blob, thickness_in)
    stock = _stock_lines(text)
    description = _description(drawing_title, stock, title)
    grade = _grade_decision(text)
    material = grade.material

    def _blocked_grade() -> PdfOnlyPlan | None:
        if not grade.blocks:
            return None
        return PdfOnlyPlan(
            route="refuse",
            missing=("material grade",),
            description=description,
            material=None,
            thickness_in=float(thickness_in) if thickness_in is not None else None,
            notes=_with_grade(grade),
        )

    def _apply_formed() -> PdfOnlyPlan | None:
        """Refuse a bend callout, or develop a simple flat from the chart."""
        if linear and not plate:
            return None
        decision = evaluate_formed(
            f"{text}\n{title}",
            material=None if grade.blocks else material,
            thickness_in=float(thickness_in) if thickness_in is not None else None,
            drawings=drawings,
        )
        if decision is None:
            return None
        if decision.flag:
            return PdfOnlyPlan(
                route="refuse",
                missing=(decision.flag_field,),
                description=description,
                material=None if grade.blocks else material,
                thickness_in=float(thickness_in) if thickness_in is not None else None,
                notes=_with_grade(grade, _flag(decision.flag_field, decision.flag)),
            )
        if grade.blocks:
            return _blocked_grade()
        # Flat L×W is computed. NumberOfBends cannot be written, so this
        # is not gold and no quote is created. Image Files would stamp
        # decision.width_in × decision.developed_length_in.
        return PdfOnlyPlan(
            route="refuse",
            missing=("bend count",),
            description=description,
            material=None if grade.blocks else material,
            thickness_in=float(thickness_in) if thickness_in is not None else None,
            width_in=decision.width_in,
            length_in=decision.developed_length_in,
            bend_count=decision.bend_count,
            flats_from_chart=True,
            line_note=decision.line_note,
            notes=_with_grade(
                grade,
                decision.line_note,
                BEND_COUNT_WRITE_GAP_NOTE,
                _flag("bend count", BEND_COUNT_NOT_SET),
            ),
        )

    if not plate and not linear:
        formed = _apply_formed()
        if formed is not None:
            return formed
        return PdfOnlyPlan(route="unclassified")

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
                material=None if grade.blocks else material,
                notes=_with_grade(grade, note),
            )
        blocked = _blocked_grade()
        if blocked is not None:
            return PdfOnlyPlan(
                route="refuse",
                missing=("material grade",),
                description=description,
                material=None,
                cut_length_in=float(cut),
                notes=blocked.notes,
            )
        note = (
            f"PDF-only tube/bar → Long; cut length {cut:g} in from the drawing"
        )
        return PdfOnlyPlan(
            route="long",
            description=description,
            material=material,
            cut_length_in=float(cut),
            notes=_with_grade(grade, note),
        )

    formed = _apply_formed()
    if formed is not None:
        return formed

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
            material=None if grade.blocks else material,
            thickness_in=float(thickness_in),
            notes=_with_grade(grade, note),
        )

    if category == "Cad" or plate:
        missing: list[str] = []
        dim_notes: list[str] = []
        if thickness_in is None:
            missing.append("thickness")
            dim_notes.append(
                _flag(
                    "thickness",
                    "PDF parse did not give a thickness or gauge; "
                    "not inventing a gauge",
                )
            )
        width_in, length_in = parse_plate_flats(text)
        if not (width_in and length_in):
            missing.append("L/W")
            dim_notes.append(
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
                material=None if grade.blocks else material,
                thickness_in=float(thickness_in) if thickness_in is not None else None,
                width_in=width_in,
                length_in=length_in,
                notes=_with_grade(grade, *dim_notes),
            )
        blocked = _blocked_grade()
        if blocked is not None:
            return PdfOnlyPlan(
                route="refuse",
                missing=("material grade",),
                description=description,
                material=None,
                thickness_in=float(thickness_in) if thickness_in is not None else None,
                width_in=width_in,
                length_in=length_in,
                notes=blocked.notes,
            )
        note = (
            "PDF-only plate/sheet → Image Files; "
            f"thickness {float(thickness_in):g} in; "
            f"L/W {float(width_in):g} x {float(length_in):g} in from the drawing"
        )
        count_note = "bend count 0 from no bend callouts"
        return PdfOnlyPlan(
            route="image_files",
            description=description,
            material=material,
            thickness_in=float(thickness_in),
            width_in=float(width_in),
            length_in=float(length_in),
            bend_count=0,
            line_note=count_note,
            notes=_with_grade(grade, note, count_note),
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
    drawings: list | None = None
    if text:
        try:
            import fitz

            doc = fitz.open(str(path))
            try:
                drawings = []
                for page in doc:
                    drawings.extend(page.get_drawings() or [])
            finally:
                doc.close()
        except Exception:  # noqa: BLE001 — text-only when vectors cannot be read
            drawings = None
    return plan_pdf_only_part(
        text=text, title=title, part_key=part_key, drawings=drawings
    )
