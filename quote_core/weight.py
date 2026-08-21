"""Part / assembly weight: prefer PDF BOM lbs, else net area × thickness × grade."""

from __future__ import annotations

import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATERIALS_PATH = ROOT / "config" / "materials.yaml"

_THICKNESS_RE = re.compile(
    r"(?<![\d/])(1/2|5/16|3/8|3/16|1/4|1/8|7/16|9/16|5/8|3/4|7/8|1)\s*[\"″']?",
    re.IGNORECASE,
)
_THICKNESS_MAP = {
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

# Title-block total: WEIGHT: 261.8 lbm
_TITLE_WEIGHT_RE = re.compile(
    r"\bWEIGHT\s*:\s*(\d{1,4}(?:\.\d+)?)\s*(?:lbm|lbs?)\b",
    re.IGNORECASE,
)
# Any mass callout
_LBM_RE = re.compile(
    r"(?<![\d.])(\d{1,4}(?:\.\d+)?)\s*(?:lbm|lbs?)\b",
    re.IGNORECASE,
)
# MAC BOM layout A (older): ITEM / QTY / PART / DESCRIPTION / WEIGHT
_BOM_ROW_ITEM_QTY_PART_RE = re.compile(
    r"(?ms)^\s*(\d{1,3})\s*\n\s*(\d{1,4})\s*\n\s*([A-Z0-9][\w\-]{4,})\s*\n(.+?)\n\s*"
    r"(\d{1,4}(?:\.\d+)?)\s*lbm\b",
    re.IGNORECASE,
)
# MAC BOM layout B (common): ITEM / PART / DESCRIPTION / QTY / WEIGHT
_BOM_ROW_ITEM_PART_QTY_RE = re.compile(
    r"(?ms)^\s*(\d{1,3})\s*\n\s*([A-Z0-9][\w\-]{4,})\s*\n(.+?)\n\s*(\d{1,4})\s*\n\s*"
    r"(\d{1,4}(?:\.\d+)?)\s*lbm\b",
    re.IGNORECASE,
)
_BOM_HEADER_RE = re.compile(
    r"(?is)Item\s*\n\s*Part\s*Number\s*\n\s*Description\s*\n\s*Qty\s*\n\s*Weight\b"
)


def _bom_section_text(text: str) -> str:
    """Prefer text after the MAC BOM column header so balloon callouts don't match."""
    if not text:
        return ""
    m = _BOM_HEADER_RE.search(text)
    if m:
        return text[m.end() :]
    return text


def _looks_like_part_no(token: str) -> bool:
    raw = re.sub(r"[^A-Z0-9\-]", "", str(token or "").upper())
    if len(raw) < 5:
        return False
    digits = sum(ch.isdigit() for ch in raw)
    return digits >= 5


def _bom_rows_from_text(text: str) -> list[dict[str, Any]]:
    section = _bom_section_text(text or "")
    rows_by_item: dict[int, dict[str, Any]] = {}

    for m in _BOM_ROW_ITEM_PART_QTY_RE.finditer(section):
        item = int(m.group(1))
        part = m.group(2).strip()
        if not _looks_like_part_no(part):
            continue
        qty = max(1, int(m.group(4)))
        unit = round(float(m.group(5)), 2)
        if unit <= 0 or unit > 20000:
            continue
        rows_by_item[item] = {
            "item": item,
            "qty": qty,
            "part_no": part,
            "description": " ".join(m.group(3).split()),
            "unit_weight_lb": unit,
        }

    # Layout A only if layout B didn't populate (avoid double-matching).
    if not rows_by_item:
        for m in _BOM_ROW_ITEM_QTY_PART_RE.finditer(section):
            item = int(m.group(1))
            part = m.group(3).strip()
            if not _looks_like_part_no(part):
                continue
            qty = max(1, int(m.group(2)))
            unit = round(float(m.group(5)), 2)
            if unit <= 0 or unit > 20000:
                continue
            rows_by_item[item] = {
                "item": item,
                "qty": qty,
                "part_no": part,
                "description": " ".join(m.group(4).split()),
                "unit_weight_lb": unit,
            }

    return [rows_by_item[k] for k in sorted(rows_by_item)]


def _bom_rows_from_pdf_blocks(pdf_path: Path | str) -> list[dict[str, Any]]:
    """Parse BOM from full page text (MAC tables often span one text stream)."""
    import fitz

    doc = fitz.open(str(pdf_path))
    try:
        raw = "\n".join((page.get_text("text") or "") for page in doc)
    finally:
        doc.close()
    return _bom_rows_from_text(raw)


@lru_cache(maxsize=4)
def load_materials(path: str | None = None) -> dict[str, Any]:
    materials_path = Path(path) if path else DEFAULT_MATERIALS_PATH
    with materials_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _alias_pattern(alias: str) -> re.Pattern[str]:
    cleaned = alias.strip().upper().replace("GRADE", "GR")
    parts = [p for p in re.split(r"[\s\-_/]+", cleaned) if p]
    body = r"[\s\-_/]*".join(re.escape(p) for p in parts)
    body = body.replace(r"GR", r"(?:GR|GRADE)")
    return re.compile(rf"(?<![A-Z0-9]){body}(?![A-Z0-9])", re.IGNORECASE)


def detect_material_key(notes: list[str], config: dict[str, Any] | None = None) -> str:
    cfg = config or load_materials()
    text = " ".join(notes or [])
    materials = cfg.get("materials") or {}
    order = list(cfg.get("detect_order") or materials.keys())
    for key in order:
        mat = materials.get(key) or {}
        aliases = list(mat.get("aliases") or []) + [str(mat.get("label") or key)]
        for alias in aliases:
            if alias and _alias_pattern(str(alias)).search(text):
                return key
    return str(cfg.get("default_material") or "a36")


def extract_plate_thicknesses_in(notes: list[str]) -> list[float]:
    found: list[float] = []
    for text in notes or []:
        for m in _THICKNESS_RE.finditer(text or ""):
            key = m.group(1).replace('"', "").replace("″", "")
            if key in _THICKNESS_MAP:
                found.append(_THICKNESS_MAP[key])
    return found


def _title_weights_from_lines(lines: list[str]) -> list[float]:
    title_vals: list[float] = []
    for i, ln in enumerate(lines):
        inline = re.search(
            r"\bWEIGHT\s*:\s*(\d{1,4}(?:\.\d+)?)\s*(?:lbm|lbs?)\b",
            ln,
            re.IGNORECASE,
        )
        if inline:
            title_vals.append(float(inline.group(1)))
            continue
        if re.fullmatch(r"WEIGHT\s*:", ln, re.IGNORECASE):
            for j in range(i + 1, min(i + 5, len(lines))):
                m = _LBM_RE.search(lines[j])
                if m:
                    title_vals.append(float(m.group(1)))
                    break
    return title_vals


def _pieces_from_bom_rows(rows: list[dict[str, Any]]) -> list[float]:
    """One weight entry per physical piece (qty × unit weight)."""
    pieces: list[float] = []
    for row in rows:
        unit = float(row["unit_weight_lb"])
        qty = max(1, int(row["qty"]))
        pieces.extend([unit] * qty)
    return pieces


def extract_pdf_bom_weights(pdf_path: Path | str | None = None, text: str | None = None) -> dict[str, Any]:
    """
    Pull title-block total and per-piece weights from PDF BOM.

    Prefer structured BOM rows (ITEM / QTY / PART / WEIGHT). Fit-up uses one
    entry per piece: unit weight repeated QTY times.
    Falls back to raw lbm callouts (1 piece each) when QTY rows are absent.
    """
    from collections import Counter

    raw = text or ""
    bom_rows: list[dict[str, Any]] = []
    if pdf_path:
        try:
            bom_rows = _bom_rows_from_pdf_blocks(pdf_path)
        except Exception:  # noqa: BLE001
            bom_rows = []
        if not raw:
            import fitz

            doc = fitz.open(str(pdf_path))
            raw = "\n".join((page.get_text("text") or "") for page in doc)
            doc.close()
    if not bom_rows and raw:
        bom_rows = _bom_rows_from_text(raw)

    lines = [ln.strip() for ln in raw.splitlines()]
    title_vals = _title_weights_from_lines(lines)

    if bom_rows:
        pieces = _pieces_from_bom_rows(bom_rows)
        assembly_total = round(float(title_vals[0]), 2) if title_vals else round(sum(pieces), 2)
        return {
            "assembly_weight_lb": assembly_total,
            "component_weights_lb": pieces,
            "bom_rows": bom_rows,
            "piece_count": len(pieces),
            "part_number_count": len(bom_rows),
            "method": "pdf_bom_qty",
            "title_weight_hits": [round(float(v), 2) for v in title_vals],
            "raw_lbm_hits": [
                round(float(m.group(1)), 2) for m in _LBM_RE.finditer(raw)
            ][:40],
        }

    all_hits = [
        round(float(m.group(1)), 2)
        for m in _LBM_RE.finditer(raw)
        if 0.05 <= float(m.group(1)) <= 20000
    ]
    counts = Counter(all_hits)
    for total in title_vals:
        key = round(float(total), 2)
        if counts[key] > 0:
            counts[key] -= 1

    components: list[float] = []
    for value, n in counts.items():
        if n > 0:
            components.extend([float(value)] * int(n))
    components.sort(reverse=True)

    assembly_total = round(float(title_vals[0]), 2) if title_vals else None
    if assembly_total is None and components:
        # Heaviest value that equals the sum of the others → treat as total
        for candidate in sorted(set(components), reverse=True):
            trial = list(components)
            trial.remove(candidate)
            if trial and abs(sum(trial) - candidate) <= max(1.0, 0.03 * candidate):
                assembly_total = candidate
                components = trial
                break
    if assembly_total is None and components:
        assembly_total = round(sum(components), 2)

    return {
        "assembly_weight_lb": assembly_total,
        "component_weights_lb": components,
        "bom_rows": [],
        "piece_count": len(components),
        "part_number_count": len(components),
        "method": "pdf_bom" if components else None,
        "title_weight_hits": [round(float(v), 2) for v in title_vals],
        "raw_lbm_hits": all_hits[:40],
    }


def _plate_thickness(box_t: float, note_thicknesses: list[float]) -> float:
    if 0 < box_t <= 1.0:
        return box_t
    plate_notes = [t for t in note_thicknesses if t <= 1.0]
    if plate_notes:
        return max(plate_notes)
    return 0.3125


def _nearest_plate_psf(thickness: float, table: dict[str, float], psf_per_inch: float) -> float:
    if thickness <= 0:
        return 0.0
    if table:
        best_key = None
        best_dist = 1e9
        for key, psf in table.items():
            try:
                t = float(key)
            except ValueError:
                continue
            dist = abs(t - thickness)
            if dist < best_dist:
                best_dist = dist
                best_key = key
        if best_key is not None and best_dist <= 0.04:
            return float(table[best_key])
    return thickness * float(psf_per_inch)


def _net_area_in2(length: float, width: float, hole_dias: list[float]) -> float:
    """Gross rectangle area minus circular cutouts that fit on the blank."""
    area = max(0.0, length) * max(0.0, width)
    min_side = min(length, width) if length > 0 and width > 0 else 0.0
    removed = 0.0
    for d in hole_dias or []:
        if d <= 0 or d >= min_side:
            continue
        removed += math.pi * (d / 2.0) ** 2
    # Don't remove more than 60% of blank (guards against mis-assigned holes)
    removed = min(removed, area * 0.6)
    return max(area - removed, area * 0.4)


def unit_weight_lb(
    solid: dict[str, Any],
    *,
    density: float,
    psf_per_inch: float,
    fill_factors: dict[str, float],
    plate_psf: dict[str, float],
    note_thicknesses: list[float] | None = None,
    hole_dias: list[float] | None = None,
) -> dict[str, Any]:
    """
    Weight of one instance from net area × thickness × grade (plates/covers),
    or bbox × fill × density (open sections) when BOM weight is absent.
    """
    box = solid.get("box") or [0, 0, 0]
    if len(box) < 3:
        return {"weight_lb": 0.0, "method": "none"}
    L, W, T = float(box[0]), float(box[1]), float(box[2])
    kind = str(solid.get("kind") or "other")
    factor = float(fill_factors.get(kind, fill_factors.get("other", 0.55)))
    if factor <= 0 or L <= 0 or W <= 0 or T <= 0:
        return {"weight_lb": 0.0, "method": "none"}

    if kind in {"plate", "cover"}:
        thick = _plate_thickness(T, note_thicknesses or [])
        psf = _nearest_plate_psf(thick, plate_psf, psf_per_inch)
        net_in2 = _net_area_in2(L, W, hole_dias or [])
        weight = (net_in2 / 144.0) * psf
        return {
            "weight_lb": weight,
            "method": "net_area_x_psf",
            "thickness_in": thick,
            "net_area_in2": round(net_in2, 2),
            "psf": psf,
        }

    # Angles / channels / other: still approximate until profile tables or FreeCAD volume
    weight = L * W * T * density * factor
    return {"weight_lb": weight, "method": "bbox_fill_factor", "fill_factor": factor}


def _read_pdf_text(pdf_path: Path | str | None) -> str:
    if not pdf_path:
        return ""
    import fitz

    doc = fitz.open(str(pdf_path))
    try:
        return "\n".join((page.get_text("text") or "") for page in doc)
    finally:
        doc.close()


def estimate_assembly_weight(
    solids: list[dict[str, Any]],
    notes: list[str] | None = None,
    materials_path: Path | str | None = None,
    hole_dias: list[float] | None = None,
    pdf_path: Path | str | None = None,
    pdf_text: str | None = None,
    library_folder: Path | str | None = None,
    related_pdf_names: list[str] | None = None,
    bom_config: str | None = None,
) -> dict[str, Any]:
    """
    Prefer PDF BOM component weights when present.
    Otherwise calculate: net sq-in × thickness × grade (plates), bbox fill (open sections).
    OCR Time-style BOMs may supply piece counts without unit weights.
    """
    from quote_core.bom import bom_from_lom_xlsx, extract_bom

    cfg = load_materials(str(materials_path) if materials_path else None)
    raw_pdf = pdf_text if pdf_text is not None else _read_pdf_text(pdf_path)
    # Weld takeoff notes are filtered (weld callouts only). Material grades usually
    # live in the title block / BOM, so always scan full PDF text too.
    mat_key = detect_material_key([*(notes or []), raw_pdf], cfg)
    materials = cfg.get("materials") or {}
    mat = materials.get(mat_key) or materials.get("a36") or materials.get("carbon_steel") or {}
    density = float(mat.get("density_lb_in3") or 0.2836)
    psf_per_inch = float(mat.get("psf_per_inch") or 40.8)
    family = str(mat.get("family") or "")
    fill = dict(cfg.get("bbox_fill_factor") or {})
    plate_psf = {
        str(k): float(v)
        for k, v in (cfg.get("plate_psf_carbon_steel") or {}).items()
    }
    if family != "carbon_steel":
        plate_psf = {}
    note_thicknesses = extract_plate_thicknesses_in(notes or [])

    # Clip writes {stem}-LOM.xlsx. The quote is that workbook — no second parser.
    clipped = extract_bom(
        pdf_path=pdf_path,
        text=raw_pdf or None,
        library_folder=library_folder,
        related_pdf_names=related_pdf_names,
        bom_config=bom_config,
    )
    bom = clipped
    if pdf_path:
        from quote_core.bom_xlsx import bom_tabs_for_import, lom_xlsx_path_for_pdf

        xlsx = lom_xlsx_path_for_pdf(pdf_path)
        if xlsx.is_file():
            bom = bom_from_lom_xlsx(xlsx, prior=clipped)
            tabs = bom_tabs_for_import(xlsx)
            if tabs:
                note = (
                    f"Quote read {xlsx.name} "
                    f"({len(tabs)} tab(s) for Sectura import: "
                    f"{', '.join(name for name, _rows in tabs)})"
                )
                if note not in bom.notes:
                    bom.notes.append(note)
    pdf_bom = bom.to_dict()
    # Keep legacy lbm-hit fallback when structured BOM rows are absent.
    # Once a LIST OF MATERIAL exists, do not run a second parser.
    if not bom.rows:
        from quote_core.bom_table import (
            looks_like_time_material_list,
            material_list_header_seen,
        )

        if not (
            looks_like_time_material_list(raw_pdf) or material_list_header_seen(bom)
        ):
            pdf_bom = extract_pdf_bom_weights(pdf_path=pdf_path, text=raw_pdf or None)

    comps = [float(w) for w in (pdf_bom.get("component_weights_lb") or [])]
    bom_rows = list(pdf_bom.get("bom_rows") or [])
    if comps:
        if bom_rows and all(r.get("unit_weight_lb") is not None for r in bom_rows):
            part_weights = [
                {
                    "name": row.get("description") or row.get("part_no") or f"BOM item {row.get('item')}",
                    "kind": "pdf_bom",
                    "qty": int(row.get("qty") or 0),
                    "unit_weight_lb": float(row["unit_weight_lb"]),
                    "weight_lb": round(float(row["unit_weight_lb"]) * int(row.get("qty") or 0), 2),
                    "part_no": row.get("part_no"),
                }
                for row in bom_rows
            ]
        else:
            part_weights = [
                {
                    "name": f"BOM piece {i+1}",
                    "kind": "pdf_bom",
                    "qty": 1,
                    "unit_weight_lb": w,
                    "weight_lb": w,
                }
                for i, w in enumerate(comps)
            ]
        return {
            "assembly_weight_lb": pdf_bom.get("assembly_weight_lb") or round(sum(comps), 2),
            "component_weights_lb": comps,
            "piece_count": int(pdf_bom.get("piece_count") or len(comps)),
            "part_number_count": int(pdf_bom.get("part_number_count") or len(bom_rows) or len(comps)),
            "material_key": mat_key,
            "material_label": mat.get("label") or mat_key,
            "material_family": family,
            "density_lb_in3": density,
            "part_weights": part_weights,
            "method": pdf_bom.get("method") or "pdf_bom",
            "pdf_bom": pdf_bom,
            "bom": pdf_bom,
        }

    # Structured BOM without unit weights: still return piece/part counts for fit-up.
    if bom_rows and int(pdf_bom.get("piece_count") or 0) > 0:
        part_weights = [
            {
                "name": row.get("description") or row.get("part_no") or f"BOM item {row.get('item')}",
                "kind": "pdf_bom",
                "qty": int(row.get("qty") or 0),
                "unit_weight_lb": None,
                "weight_lb": None,
                "part_no": row.get("part_no"),
            }
            for row in bom_rows
        ]
        bom_only = {
            "assembly_weight_lb": pdf_bom.get("assembly_weight_lb"),
            "component_weights_lb": [],
            "piece_count": int(pdf_bom.get("piece_count") or 0),
            "part_number_count": int(pdf_bom.get("part_number_count") or len(bom_rows)),
            "material_key": mat_key,
            "material_label": mat.get("label") or mat_key,
            "material_family": family,
            "density_lb_in3": density,
            "part_weights": part_weights,
            "method": pdf_bom.get("method") or "pdf_bom_qty_only",
            "pdf_bom": pdf_bom,
            "bom": pdf_bom,
        }
        # Fall through to geometry weights below, but keep BOM counts as authority.
        # Stash for merge after calc.
        bom_piece_override = bom_only
    else:
        bom_piece_override = None

    # Hole cutouts: ignore kingpin-scale diameters for plate blanking
    holes = [d for d in (hole_dias or []) if 0.2 <= d <= 3.0]

    lines: list[dict[str, Any]] = []
    component_weights: list[float] = []
    total = 0.0
    for solid in solids or []:
        detail = unit_weight_lb(
            solid,
            density=density,
            psf_per_inch=psf_per_inch,
            fill_factors=fill,
            plate_psf=plate_psf,
            note_thicknesses=note_thicknesses,
            hole_dias=holes if solid.get("kind") in {"plate", "cover"} else None,
        )
        unit = float(detail.get("weight_lb") or 0)
        if unit <= 0:
            continue
        qty = max(1, int(solid.get("qty") or 1))
        line_total = unit * qty
        total += line_total
        lines.append(
            {
                "name": solid.get("name") or solid.get("kind"),
                "kind": solid.get("kind"),
                "qty": qty,
                "box": solid.get("box") or [],
                "unit_weight_lb": round(unit, 2),
                "weight_lb": round(line_total, 2),
                "calc": {k: v for k, v in detail.items() if k != "weight_lb"},
            }
        )
        component_weights.extend([round(unit, 2)] * qty)

    result = {
        "assembly_weight_lb": round(total, 2) if total > 0 else None,
        "component_weights_lb": component_weights,
        "material_key": mat_key,
        "material_label": mat.get("label") or mat_key,
        "material_family": family,
        "density_lb_in3": density,
        "part_weights": sorted(lines, key=lambda r: r["weight_lb"], reverse=True)[:40],
        "method": "net_area_or_bbox_calc",
        "pdf_bom": pdf_bom,
        "bom": pdf_bom,
    }
    if bom_piece_override is not None:
        # BOM piece/part counts win over STEP solid count for fit-up.
        result["piece_count"] = bom_piece_override["piece_count"]
        result["part_number_count"] = bom_piece_override["part_number_count"]
        result["part_weights"] = bom_piece_override["part_weights"]
        result["method"] = bom_piece_override["method"]
        if not component_weights:
            result["assembly_weight_lb"] = bom_piece_override.get("assembly_weight_lb")
            result["component_weights_lb"] = []
        # Keep geometry weights as estimates when available, but annotate method.
        elif component_weights:
            result["method"] = f"{bom_piece_override['method']}+geometry_weight_est"
    return result
