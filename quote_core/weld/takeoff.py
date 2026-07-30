from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

WELD_SIZE_RE = re.compile(
    r"(?<![\d/])(1/2|5/16|3/8|3/16|1/4|1/8)\s*[\"″']?",
    re.IGNORECASE,
)
# Mixed number: 34-3/8" or 34 3/8" ; proper fraction 3/8" ; decimal 32.75"
DIM_MIXED_RE = re.compile(
    r"(?<![\d.])(\d{1,3})\s*-\s*(\d{1,2})/(\d{1,2})\s*[\"″']?",
)
DIM_MIXED_SPACE_RE = re.compile(
    r"(?<![\d.])(\d{1,3})\s+(\d{1,2})/(\d{1,2})\s*[\"″']?",
)
DIM_DECIMAL_RE = re.compile(
    r"(?<![\d.])(\d{1,3}\.\d{1,4})\s*[\"″']?",
)
DIM_WHOLE_RE = re.compile(
    r"(?<![\d./])(\d{2,3})\s*[\"″'](?!\s*/)",
)
FULL_WELD_NOTE_RE = re.compile(r"FULL\s+WELD", re.IGNORECASE)
MIRROR_RE = re.compile(r"MIRROR", re.IGNORECASE)
TRACE_RE = re.compile(r"TRACE\s+WELD", re.IGNORECASE)
ALL_AROUND_HINT_RE = re.compile(r"ALL[\s-]?AROUND|PRE-?HEAT\s+KINGPIN", re.IGNORECASE)
CORNER_1IN_RE = re.compile(
    r"(?:SQUARE\s+)?1/2\".*?(?:CORNER\s+WELDS?).*?(?:TO\s+)?1\s*[\"″']?\s*LENGTH",
    re.IGNORECASE | re.DOTALL,
)
ANGLE_LEN_RE = re.compile(
    r"ANGLE.*?(\d+(?:\.\d+)?)\s*[\"″']?\s*$|X\s*(\d+(?:\.\d+)?)\s*[\"″']?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
WEIGHT_RE = re.compile(
    r"(?<![\d.])(\d{1,4}(?:\.\d+)?)\s*(?:lbm|lbs?|pounds?)\b",
    re.IGNORECASE,
)


@dataclass
class WeldLineItem:
    size: str
    inches: float
    joint_notes: str
    confidence: str  # high | medium | low
    source: str
    page: int | None = None
    needs_review: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WeldTakeoffResult:
    items: list[WeldLineItem] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    sizes_found: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    stp_summary: dict[str, Any] = field(default_factory=dict)

    fitup_drivers: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [i.to_dict() for i in self.items],
            "flags": self.flags,
            "sizes_found": self.sizes_found,
            "notes": self.notes,
            "stp_summary": self.stp_summary,
            "fitup_drivers": self.fitup_drivers,
            "total_inches": sum(i.inches for i in self.items),
        }


def _normalize_size(raw: str) -> str:
    return raw.strip().replace('"', "").replace("″", "").replace("'", "")


def _fraction_to_float(whole: str, num: str, den: str) -> float | None:
    try:
        d = float(den)
        if d == 0:
            return None
        return float(whole) + float(num) / d
    except ValueError:
        return None


def _extract_dimensions_from_text(text: str) -> list[float]:
    # Strip weight/BOM noise that looks like decimal inches (e.g. "37.9 lbm")
    cleaned = re.sub(
        r"\d+(?:\.\d+)?\s*(?:lbm|lbs?|pounds?)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\bWEIGHT\b.*", " ", cleaned, flags=re.IGNORECASE)
    dims: list[float] = []
    for m in DIM_MIXED_RE.finditer(cleaned):
        val = _fraction_to_float(m.group(1), m.group(2), m.group(3))
        if val is not None:
            dims.append(val)
    for m in DIM_MIXED_SPACE_RE.finditer(cleaned):
        val = _fraction_to_float(m.group(1), m.group(2), m.group(3))
        if val is not None:
            dims.append(val)
    for m in DIM_DECIMAL_RE.finditer(cleaned):
        try:
            dims.append(float(m.group(1)))
        except ValueError:
            pass
    for m in DIM_WHOLE_RE.finditer(cleaned):
        try:
            dims.append(float(m.group(1)))
        except ValueError:
            pass
    return [d for d in dims if 6.0 <= d <= 120.0]


def _ingest_page_text(
    page_no: int,
    text: str,
    *,
    force_weld_sheet: bool = False,
) -> tuple[list[str], list[str], list[dict[str, Any]], list[float]]:
    """Extract weld sizes / notes / dims from one page of text (native or OCR)."""
    sizes: list[str] = []
    notes: list[str] = []
    page_hits: list[dict[str, Any]] = []
    dimensions = _extract_dimensions_from_text(text)
    lower = text.lower()

    is_weld_sheet = force_weld_sheet or any(
        k in lower
        for k in (
            "fillet",
            "trace weld",
            "corner weld",
            "full weld",
            "weld beads",
            "pre-heat kingpin",
            "preheat kingpin",
            "weldment",
            "weld",
        )
    ) or ("weld" in lower and ("1/4" in lower or "5/16" in lower or "1/2" in lower))

    if is_weld_sheet:
        page_sizes = [_normalize_size(m.group(1)) for m in WELD_SIZE_RE.finditer(text)]
        for s in page_sizes:
            sizes.append(s)
            page_hits.append({"page": page_no, "size": s, "weld_sheet": True})

    for line in text.splitlines():
        if FULL_WELD_NOTE_RE.search(line) or TRACE_RE.search(line) or MIRROR_RE.search(line):
            notes.append(f"p{page_no}: {line.strip()}")
        if ALL_AROUND_HINT_RE.search(line):
            notes.append(f"p{page_no}: {line.strip()}")
        if CORNER_1IN_RE.search(line.replace("\n", " ")):
            notes.append(f"p{page_no}: corner 1/2 x 1in TYP")
        if "ANGLE" in line.upper() and "X" in line.upper():
            parts = re.findall(r"(\d+(?:\.\d+)?)", line)
            for p in parts:
                try:
                    val = float(p)
                except ValueError:
                    continue
                if 10.0 <= val <= 120.0:
                    dimensions.append(val)
                    notes.append(f"p{page_no}: angle length candidate {val}")

    flat = " ".join(text.split())
    if CORNER_1IN_RE.search(flat):
        notes.append(f"p{page_no}: SQUARE 1/2 FILLET CORNER WELDS TO 1\" LENGTH TYP")
    return sizes, notes, page_hits, dimensions


def _parse_pdf_text(
    pdf_path: Path,
) -> tuple[list[str], list[str], list[dict[str, Any]], list[float], dict[str, Any]]:
    import fitz

    from quote_core.ocr import ocr_pdf_pages

    doc = fitz.open(pdf_path)
    sizes: list[str] = []
    notes: list[str] = []
    page_hits: list[dict[str, Any]] = []
    dimensions: list[float] = []
    text_chars = 0
    drawing_count = 0
    name_hint = "weld" in pdf_path.name.lower() or "weldment" in pdf_path.name.lower()

    for i, page in enumerate(doc):
        text = page.get_text("text") or ""
        text_chars += len(text.strip())
        try:
            drawing_count += len(page.get_drawings() or [])
        except Exception:  # noqa: BLE001
            pass
        s, n, h, d = _ingest_page_text(i + 1, text, force_weld_sheet=False)
        sizes.extend(s)
        notes.extend(n)
        page_hits.extend(h)
        dimensions.extend(d)

    page_count = len(doc)
    doc.close()

    vector_heavy = drawing_count >= 500 and text_chars < 200
    ocr_info: dict[str, Any] = {"used": False}
    if vector_heavy or text_chars < 200:
        ocr_info = ocr_pdf_pages(pdf_path, max_pages=min(4, page_count or 1), dpi=220)
        if ocr_info.get("used") and ocr_info.get("text"):
            notes.append("OCR used for low-text / vector PDF pages")
            for page_row in ocr_info.get("pages") or []:
                pno = int(page_row.get("page") or 1)
                otext = str(page_row.get("text") or "")
                s, n, h, d = _ingest_page_text(
                    pno,
                    otext,
                    force_weld_sheet=name_hint or vector_heavy,
                )
                sizes.extend(s)
                notes.extend(n)
                page_hits.extend(h)
                dimensions.extend(d)
            text_chars = max(text_chars, len(str(ocr_info.get("text") or "")))

    counts = Counter(sizes)
    # Vector CAD / OCR packs often only print a size once; keep single hits when text is scarce.
    min_hits = 1 if (vector_heavy or ocr_info.get("used") or text_chars < 400) else 2
    sizes = [s for s in sizes if counts[s] >= min_hits]
    page_hits = [h for h in page_hits if counts.get(h["size"], 0) >= min_hits]
    meta = {
        "page_count": page_count,
        "text_chars": text_chars,
        "drawing_count": drawing_count,
        "vector_heavy": vector_heavy,
        "ocr_used": bool(ocr_info.get("used")),
        "ocr_error": ocr_info.get("error"),
        "ocr_engine": ocr_info.get("engine"),
        "ocr_pages": ocr_info.get("pages_ocrd"),
    }
    return sizes, notes, page_hits, dimensions, meta


def _estimate_segments_from_pdf(
    dimensions: list[float],
    notes: list[str],
) -> list[dict[str, Any]]:
    """Estimate weld segments from drawing dims when STP is absent."""
    if not dimensions:
        return []

    uniq = sorted({round(d, 2) for d in dimensions}, reverse=True)
    overall = [d for d in uniq if 20.0 <= d <= 60.0][:3]
    mid = [d for d in uniq if 10.0 <= d < 20.0][:4]
    if not overall and not mid:
        return []

    both_sides = any("BOTH SIDE" in n.upper() or "MIRROR" in n.upper() for n in notes)
    full_weld = any(FULL_WELD_NOTE_RE.search(n) for n in notes)
    sides = 2 if (both_sides or full_weld) else 1

    segments: list[dict[str, Any]] = []
    if len(overall) >= 2:
        length, width = overall[0], overall[1]
        segments.append({"length": length, "qty": 2, "sides": sides, "kind": "long_member"})
        segments.append({"length": width, "qty": 2, "sides": sides, "kind": "end_member"})
        cross = mid[0] if mid else round(min(length, width) * 0.4, 2)
        segments.append({"length": cross, "qty": 4, "sides": sides, "kind": "cross_member"})
    elif overall:
        segments.append(
            {
                "length": overall[0],
                "qty": 4 if (full_weld or both_sides) else 2,
                "sides": sides,
                "kind": "member",
            }
        )
    else:
        for d in mid[:3]:
            segments.append({"length": d, "qty": 2, "sides": sides, "kind": "member"})
    return segments


def _parse_stp_boxes(stp_path: Path) -> dict[str, Any]:
    """Extract solid bounding boxes, assembly qty, and weld-relevant geometry."""
    raw = stp_path.read_text(errors="ignore")
    text = re.sub(r",\s*\n\s*", ",", raw)
    ents = {
        int(m.group(1)): m.group(2).strip()
        for m in re.finditer(r"^#(\d+)\s*=\s*(.+?);\s*$", text, re.M)
    }
    if not ents:
        return {"error": "no entities", "solids": [], "segments": []}

    unit_scale = 1.0
    if re.search(r"CONVERSION_BASED_UNIT\s*\(\s*'INCH'", text, re.I):
        unit_scale = 1.0
    elif "MILLI" in text and "INCH" not in text.upper():
        unit_scale = 1.0 / 25.4

    def refs(body: str) -> list[int]:
        return [int(x) for x in re.findall(r"#(\d+)", body)]

    # Assembly occurrence counts by part id/name
    qty_by_name: Counter[str] = Counter()
    for body in ents.values():
        if body.startswith("NEXT_ASSEMBLY_USAGE_OCCURRENCE"):
            m = re.search(r"NEXT_ASSEMBLY_USAGE_OCCURRENCE\('([^']*)'", body)
            if m and m.group(1):
                qty_by_name[m.group(1)] += 1

    pts: dict[int, tuple[float, float, float]] = {}
    for eid, body in ents.items():
        if body.startswith("CARTESIAN_POINT"):
            m = re.search(r"\(([-0-9.eE+ ,]+)\)\s*\)$", body)
            if m:
                vals = [float(x) for x in m.group(1).split(",")]
                if len(vals) == 3:
                    pts[eid] = (vals[0], vals[1], vals[2])

    vp = {
        eid: refs(body)[0]
        for eid, body in ents.items()
        if body.startswith("VERTEX_POINT") and refs(body)
    }
    edges = {
        eid: (refs(body)[0], refs(body)[1])
        for eid, body in ents.items()
        if body.startswith("EDGE_CURVE") and len(refs(body)) >= 2
    }
    shells = {
        eid: refs(body) for eid, body in ents.items() if body.startswith("CLOSED_SHELL")
    }
    faces = {
        eid: refs(body) for eid, body in ents.items() if body.startswith("ADVANCED_FACE")
    }
    loops = {
        eid: refs(body) for eid, body in ents.items() if body.startswith("EDGE_LOOP")
    }
    bounds = {
        eid: refs(body)[0]
        for eid, body in ents.items()
        if (body.startswith("FACE_BOUND") or body.startswith("FACE_OUTER_BOUND"))
        and refs(body)
    }
    oedges = {
        eid: refs(body)[-1]
        for eid, body in ents.items()
        if body.startswith("ORIENTED_EDGE") and refs(body)
    }

    # Circle radii (inches) for kingpin / all-around
    circle_radii: list[float] = []
    for body in ents.values():
        if body.startswith("CIRCLE(") or body.startswith("CYLINDRICAL_SURFACE"):
            m = re.search(r",\s*([0-9.eE+-]+)\)\s*$", body)
            if m:
                circle_radii.append(float(m.group(1)) * unit_scale)

    # Named shape reps → brep ids when available
    brep_name: dict[int, str] = {}
    for body in ents.values():
        if "ADVANCED_BREP_SHAPE_REPRESENTATION" in body:
            m = re.search(
                r"ADVANCED_BREP_SHAPE_REPRESENTATION\('([^']*)',\(([^)]*)\)", body
            )
            if m:
                name = m.group(1)
                for ref in re.findall(r"#(\d+)", m.group(2)):
                    if name:
                        brep_name[int(ref)] = name

    solids: list[dict[str, Any]] = []
    for eid, body in ents.items():
        if not body.startswith("MANIFOLD_SOLID_BREP"):
            continue
        name_m = re.search(r"MANIFOLD_SOLID_BREP\('([^']*)'", body)
        name = name_m.group(1) if name_m else brep_name.get(eid, "")
        shell_refs = refs(body)
        if not shell_refs:
            continue
        shell = shell_refs[0]
        edge_ids: set[int] = set()
        coords: list[tuple[float, float, float]] = []
        lengths: list[float] = []
        for face in shells.get(shell, []):
            for b in faces.get(face, []):
                if b not in bounds:
                    continue
                for oe in loops.get(bounds[b], []):
                    ec = oedges.get(oe)
                    if ec:
                        edge_ids.add(ec)
        for ec in edge_ids:
            if ec not in edges:
                continue
            v1, v2 = edges[ec]
            p1 = pts.get(vp.get(v1))  # type: ignore[arg-type]
            p2 = pts.get(vp.get(v2))  # type: ignore[arg-type]
            if not p1 or not p2:
                continue
            d = math.dist(p1, p2) * unit_scale
            lengths.append(d)
            coords.extend([p1, p2])
        if not coords:
            continue
        xs = [c[0] * unit_scale for c in coords]
        ys = [c[1] * unit_scale for c in coords]
        zs = [c[2] * unit_scale for c in coords]
        dims = sorted(
            [max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)], reverse=True
        )
        qty = qty_by_name.get(name, 1) if name else 1
        # If unnamed, leave qty=1 (unique solid body already instanced in some exports)
        kind = _classify_solid(dims)
        solids.append(
            {
                "brep": eid,
                "name": name,
                "qty": qty,
                "kind": kind,
                "box": [round(d, 3) for d in dims],
                "long_edges": Counter(round(L, 3) for L in lengths if L >= 2.0).most_common(
                    8
                ),
                "max_edge": round(max(lengths), 3) if lengths else 0.0,
            }
        )

    solids.sort(key=lambda s: s["box"][0] * s["box"][1], reverse=True)
    _assign_quantities(solids, dict(qty_by_name))

    return {
        "unit_scale": unit_scale,
        "solid_count": len(solids),
        "solids": solids[:40],
        "qty_by_name": dict(qty_by_name),
        "circle_diameters": sorted({round(2 * r, 3) for r in circle_radii if r > 0.2}),
    }


def _assign_quantities(solids: list[dict[str, Any]], qty_by_name: dict[str, int]) -> None:
    """Attach assembly occurrence qty to solids."""
    if not solids:
        return
    for s in solids:
        name = s.get("name") or ""
        if name and name in qty_by_name:
            s["qty"] = int(qty_by_name[name])
        else:
            s["qty"] = int(s.get("qty") or 1)

    if not qty_by_name:
        return

    used_names = {s.get("name") for s in solids if s.get("name")}
    remaining = [q for n, q in qty_by_name.items() if n not in used_names]
    if any(s.get("kind") == "plate" for s in solids) and 1 in remaining:
        remaining.remove(1)

    unnamed = [
        s
        for s in solids
        if s.get("kind") in {"angle", "channel", "cover"}
        and not (s.get("name") and s.get("name") in qty_by_name)
    ]
    if not unnamed or not remaining:
        return

    if len(unnamed) != len(remaining):
        # Fallback for coupler-style assemblies: mostly qty 2
        for s in unnamed:
            s["qty"] = 2
        if 1 in remaining:
            shorts = [s for s in unnamed if s.get("kind") == "channel" and s["box"][0] < 20]
            if shorts:
                shorts.sort(key=lambda s: -s["box"][1])
                shorts[0]["qty"] = 1
        return

    unnamed.sort(key=lambda s: (s["box"][0], s["box"][1]), reverse=True)
    ones = [q for q in remaining if q == 1]
    multis = sorted((q for q in remaining if q != 1), reverse=True)
    assigned: set[int] = set()
    for _ in ones:
        candidates = [
            i for i, s in enumerate(unnamed) if i not in assigned and s["box"][0] < 24
        ] or [i for i, _s in enumerate(unnamed) if i not in assigned]
        idx = candidates[0]
        unnamed[idx]["qty"] = 1
        assigned.add(idx)
    for q in multis:
        for i, s in enumerate(unnamed):
            if i not in assigned:
                s["qty"] = q
                assigned.add(i)
                break


def _classify_solid(box: list[float]) -> str:
    L, W, T = box[0], box[1], box[2]
    if L < 8 and W < 8 and T < 0.2:
        return "skip"
    # Main plate: large footprint, modest thickness or bowed thickness
    if L >= 24 and W >= 24 and T <= 4.0:
        return "plate"
    # Angle: long with ~equal small legs
    if L >= 12 and 1.5 <= W <= 4.0 and 1.5 <= T <= 4.0 and abs(W - T) <= 1.25:
        return "angle"
    # Cover / flat strip
    if L >= 12 and T <= 1.25 and W <= 4.0:
        return "cover"
    # Channel / gusset rib
    if L >= 10 and 2.0 <= W <= 10.0 and 0.15 <= T <= 4.0:
        return "channel"
    # Kingpin-ish
    if L <= 10 and W <= 8:
        return "kingpin"
    return "other"


def _weld_segments_from_stp(
    stp_summary: dict[str, Any],
    notes: list[str],
) -> list[dict[str, Any]]:
    """Build weld segments from classified STP solids + assembly qty."""
    solids = stp_summary.get("solids") or []
    if not solids:
        return []

    full_weld = any(FULL_WELD_NOTE_RE.search(n) for n in notes)
    both_sides = any("BOTH SIDE" in n.upper() or "MIRROR" in n.upper() for n in notes)
    sides = 2 if (full_weld or both_sides) else 2  # structural fillet default both toes/sides
    # Cover plates are omitted from the primary total unless the weld note names them.
    include_covers = any("COVER" in n.upper() for n in notes)

    segments: list[dict[str, Any]] = []
    cover_segments: list[dict[str, Any]] = []
    qty_by_name = stp_summary.get("qty_by_name") or {}

    for solid in solids:
        kind = solid.get("kind")
        box = solid.get("box") or [0, 0, 0]
        L, W, T = box[0], box[1], box[2] if len(box) > 2 else 0
        name = solid.get("name") or ""
        qty = int(solid.get("qty") or 1)
        if name and name in qty_by_name:
            qty = int(qty_by_name[name])

        if kind == "plate" or kind == "skip":
            continue
        if kind == "kingpin":
            continue
        if kind == "cover" and L >= 6:
            cover_seg = {
                "length": float(L),
                "qty": qty,
                "sides": sides,
                "kind": "cover",
                "width": float(W),
                "name": name,
            }
            cover_segments.append(cover_seg)
            if include_covers:
                segments.append(cover_seg)
            continue
        if kind in {"angle", "channel", "other"} and L >= 6:
            # both flanges / both sides along length
            segments.append(
                {
                    "length": float(L),
                    "qty": qty,
                    "sides": sides,
                    "kind": kind or "member",
                    "width": float(W),
                    "name": name,
                }
            )
            # End closures for channels/angles when FULL WELD
            if full_weld and kind in {"channel", "angle"} and W > 0:
                end_len = float(min(W, T)) if T > 0.2 else float(W)
                segments.append(
                    {
                        "length": end_len,
                        "qty": qty * 2,  # two ends
                        "sides": 1,
                        "kind": f"{kind}_end",
                        "name": name,
                    }
                )

    # Kingpin all-around: prefer ~8" if present (common SAE coupler), else largest 3-10"
    dias = [d for d in (stp_summary.get("circle_diameters") or []) if 2.5 <= d <= 10.0]
    if dias:
        # Prefer exactly 8 if close, else max in range
        preferred = min(dias, key=lambda d: abs(d - 8.0))
        if abs(preferred - 8.0) <= 1.0 or preferred >= 7.0:
            king_d = preferred if abs(preferred - 8.0) <= 1.5 else max(dias)
        else:
            king_d = max(dias)
        # If 8 exists use it
        for d in dias:
            if abs(d - 8.0) < 0.05:
                king_d = d
                break
        segments.append(
            {
                "length": math.pi * float(king_d),
                "qty": 1,
                "sides": 1,
                "kind": "kingpin_all_around",
                "diameter": float(king_d),
            }
        )
    elif any("KINGPIN" in n.upper() or "KING PIN" in n.upper() for n in notes):
        segments.append(
            {
                "length": math.pi * 8.0,
                "qty": 1,
                "sides": 1,
                "kind": "kingpin_all_around",
                "diameter": 8.0,
            }
        )

    # Stash cover alternate so the UI can warn with a concrete inch total.
    stp_summary["cover_segments"] = cover_segments
    stp_summary["cover_inches"] = round(_segments_total_inches(cover_segments), 2)
    stp_summary["covers_included_in_total"] = include_covers
    return segments


def _segments_total_inches(segments: list[dict[str, Any]]) -> float:
    return sum(
        float(s["length"]) * int(s.get("qty") or 1) * int(s.get("sides") or 1)
        for s in segments
    )


def _build_items_from_signals(
    sizes: list[str],
    notes: list[str],
    page_hits: list[dict[str, Any]],
    stp_summary: dict[str, Any],
    pdf_name: str,
    pdf_dimensions: list[float] | None = None,
) -> tuple[list[WeldLineItem], list[str]]:
    items: list[WeldLineItem] = []
    flags: list[str] = []
    pdf_dimensions = pdf_dimensions or []

    weld_sheet_sizes = Counter(h["size"] for h in page_hits if h.get("weld_sheet"))
    size_counts = Counter(sizes)
    full_weld = any(FULL_WELD_NOTE_RE.search(n) for n in notes)
    both_sides = any("BOTH SIDE" in n.upper() or "MIRROR" in n.upper() for n in notes)
    mirror = any(MIRROR_RE.search(n) for n in notes)

    if weld_sheet_sizes:
        dominant_size, dominant_count = weld_sheet_sizes.most_common(1)[0]
        # On FULL WELD prints, fillet callouts are usually one primary size;
        # thinner counts are often plate thickness / BOM noise (e.g. 5/16 plate, 3/8 kingpin).
        if full_weld and dominant_count >= 4:
            primary_sizes = [dominant_size]
        else:
            primary_sizes = [
                s
                for s, c in weld_sheet_sizes.items()
                if c >= max(2, int(dominant_count * 0.5))
            ]
    else:
        primary_sizes = list(size_counts.keys())

    segments = _weld_segments_from_stp(stp_summary, notes)
    length_source = "stp_assembly"
    if not segments:
        segments = _estimate_segments_from_pdf(pdf_dimensions, notes)
        length_source = "pdf_dims"

    if not primary_sizes:
        flags.append("No weld size callouts detected in PDF text — manual takeoff required")
        total_path = _segments_total_inches(segments) if segments else 0.0
        joint = "No weld sizes found; review drawing"
        if total_path > 0:
            joint = (
                f"Length ~{round(total_path, 2)}\" from {length_source}; "
                "enter fillet size (PDF has no readable size text)"
            )
            flags.append(
                f"Weld path length estimated at {round(total_path, 2)}\" from geometry — "
                "enter fillet size to finish takeoff"
            )
        items.append(
            WeldLineItem(
                size="unknown",
                inches=round(total_path, 2),
                joint_notes=joint,
                confidence="low",
                source=length_source if total_path > 0 else "pdf",
                needs_review=True,
            )
        )
        return items, flags

    if not segments:
        flags.append(
            "Could not estimate weld lengths from STP or PDF dimensions — enter inches manually"
        )
        for size in sorted(set(primary_sizes)):
            items.append(
                WeldLineItem(
                    size=size,
                    inches=0.0,
                    joint_notes="Size found on drawing; enter inches after review",
                    confidence="low",
                    source="pdf_size_only",
                    needs_review=True,
                )
            )
        if any("CORNER" in n.upper() and "1/2" in n for n in notes):
            items.append(
                WeldLineItem(
                    size="1/2",
                    inches=8.0,
                    joint_notes='SQUARE 1/2" corner welds to 1" length TYP (assumed 8 corners)',
                    confidence="medium",
                    source="pdf_note",
                    needs_review=True,
                )
            )
        return items, flags

    dominant = primary_sizes[0]
    if weld_sheet_sizes:
        dominant = weld_sheet_sizes.most_common(1)[0][0]
        if dominant not in primary_sizes:
            dominant = primary_sizes[0]

    total_path = _segments_total_inches(segments)
    note_bits = []
    if full_weld:
        note_bits.append("FULL WELD note")
    if both_sides or mirror:
        note_bits.append("both-sides/mirror")
    kinds = Counter(s.get("kind", "member") for s in segments)
    note_bits.append(
        f"{len(segments)} segments via {length_source} ({', '.join(f'{k}×{v}' for k,v in kinds.items())})"
    )
    for s in segments:
        if s.get("kind") == "kingpin_all_around":
            note_bits.append(f"kingpin Ø{s.get('diameter', '?')}\" all-around")

    confidence = "medium" if length_source == "stp_assembly" else "low"
    items.append(
        WeldLineItem(
            size=dominant,
            inches=round(total_path, 2),
            joint_notes="; ".join(note_bits),
            confidence=confidence,
            source=f"{length_source}+pdf_size",
            needs_review=True,
        )
    )

    # Keep explicitly noted corner welds even if size filtered out
    if any("CORNER" in n.upper() for n in notes) and not any(i.size == "1/2" for i in items):
        items.append(
            WeldLineItem(
                size="1/2",
                inches=8.0,
                joint_notes='Corner welds 1" TYP × 8 (assumed)',
                confidence="medium",
                source="pdf_note",
                needs_review=True,
            )
        )

    if length_source == "pdf_dims":
        flags.append(
            "Lengths estimated from PDF dimensions (no STP) — attach STP for better accuracy"
        )
    cover_inches = float(stp_summary.get("cover_inches") or 0)
    covers_included = bool(stp_summary.get("covers_included_in_total"))
    if cover_inches > 0 and not covers_included:
        with_covers = round(total_path + cover_inches, 2)
        flags.append(
            f"Cover plates found in STP but not named in weld notes — excluded from total. "
            f"If cover edges are welded both sides: +{cover_inches:g}\" -> about {with_covers:g}\" overall"
        )
    elif cover_inches > 0 and covers_included:
        flags.append(f"Cover plate welds included (+{cover_inches:g}\")")
    if any(s.get("kind") == "kingpin_all_around" for s in segments):
        flags.append("Confirm kingpin weld diameter")
    else:
        flags.append("kingpin_diameter_if_not_dimensioned")
    flags.append(f"Auto takeoff from {pdf_name} — confirm before accepting")

    # Expose segment detail for review/debug
    stp_summary["weld_segments"] = segments
    stp_summary["weld_inches_calc"] = round(total_path, 2)

    return items, flags


def _extract_weights_lb(texts: list[str]) -> list[float]:
    found: list[float] = []
    for text in texts:
        for m in WEIGHT_RE.finditer(text or ""):
            try:
                val = float(m.group(1))
            except ValueError:
                continue
            if 0.5 <= val <= 5000:
                found.append(val)
    return found


def estimate_fitup_drivers(
    stp_summary: dict[str, Any],
    notes: list[str],
    pdf_path: Path | str | None = None,
    library_folder: Path | str | None = None,
) -> dict[str, Any]:
    """
    Estimate parts / joints / component weights for fit-up tables.
    Prefer PDF BOM component weights; else calculate from net area × thickness × grade.
    BOM piece counts (including OCR) override STEP solid counts.
    """
    from quote_core.weight import estimate_assembly_weight

    notes_out: list[str] = []
    solids = list(stp_summary.get("solids") or [])
    segments = list(stp_summary.get("weld_segments") or [])

    part_count = 0
    for solid in solids:
        kind = str(solid.get("kind") or "")
        if kind in {"fastener", "hardware", "skip"}:
            continue
        part_count += int(solid.get("qty") or 1)
    if part_count <= 0:
        part_count = int(stp_summary.get("solid_count") or 0)
    defaulted_part_count = False
    if part_count <= 0:
        part_count = 1
        defaulted_part_count = True

    skip_kinds = {"kingpin_all_around", "angle_end", "channel_end"}
    joint_count = sum(1 for s in segments if str(s.get("kind") or "") not in skip_kinds)
    joint_estimated = False
    if joint_count <= 0:
        joint_count = max(1, part_count - 1)
        joint_estimated = True

    weight_info = estimate_assembly_weight(
        solids,
        notes,
        hole_dias=list(stp_summary.get("circle_diameters") or []),
        pdf_path=pdf_path,
        library_folder=library_folder,
    )
    assembly_weight = weight_info.get("assembly_weight_lb")
    component_weights = list(weight_info.get("component_weights_lb") or [])
    method = str(weight_info.get("method") or "")
    bom_piece_count = int(weight_info.get("piece_count") or 0)
    bom_part_numbers = int(weight_info.get("part_number_count") or 0)

    if method.startswith("pdf_bom") or method.startswith("ocr_time") or method.startswith("native_mac"):
        if bom_piece_count > 0:
            part_count = bom_piece_count
            defaulted_part_count = False
        if component_weights and "geometry_weight_est" not in method and method != "ocr_time":
            note = (
                f"Using PDF BOM piece weights ({part_count} pieces"
                + (f" across {bom_part_numbers} part numbers" if bom_part_numbers else "")
                + f", total {assembly_weight:g} lb, {weight_info.get('material_label')})"
            )
            notes_out.append(note)
        elif bom_piece_count > 0:
            # BOM qty/part rows without unit weights: do NOT use a shorter STEP
            # solid weight list — that under-counts pieces (e.g. 4 solids vs 11 BOM).
            if "geometry_weight_est" in method or (
                component_weights and len(component_weights) != bom_piece_count
            ):
                notes_out.append(
                    f"Using PDF BOM piece count ({part_count} pieces"
                    + (f" across {bom_part_numbers} part numbers" if bom_part_numbers else "")
                    + ") — unit weights not on drawing; STEP solid weights ignored for fit-up count"
                )
                component_weights = []
                assembly_weight = weight_info.get("assembly_weight_lb")
            else:
                notes_out.append(
                    f"Using PDF BOM piece count ({part_count} pieces"
                    + (f" across {bom_part_numbers} part numbers" if bom_part_numbers else "")
                    + ") — unit weights not on drawing; enter weights or confirm STEP estimate"
                )
    elif component_weights:
        part_count = max(part_count, len(component_weights))
        defaulted_part_count = False
        notes_out.append(
            f"Component weights calculated (net area × thickness × grade / section factors): "
            f"{len(component_weights)} pieces, total {assembly_weight:g} lb "
            f"({weight_info.get('material_label')})"
        )
        notes_out.append(
            "Calculated weights are estimates — confirm against scale weight or FreeCAD mass props"
        )
    else:
        notes_out.append("Component weights unknown — enter weights or attach PDF/STP with BOM")

    if bom_piece_count > 0 and (
        method.startswith("pdf_bom")
        or method.startswith("ocr_time")
        or method.startswith("native_mac")
        or "qty_only" in method
    ):
        part_count = bom_piece_count
        defaulted_part_count = False

    if defaulted_part_count:
        notes_out.insert(0, "Part count defaulted to 1 — enter actual part count")
    if joint_estimated and bom_piece_count <= 0:
        notes_out.append("Joint count estimated from part count (parts - 1)")
    elif joint_estimated and bom_piece_count > 0:
        # Recompute joint estimate from BOM piece count when no weld segments exist.
        joint_count = max(1, part_count - 1)
        notes_out.append("Joint count estimated from BOM piece count (pieces - 1)")

    return {
        "part_count": part_count,
        "piece_count": bom_piece_count
        if bom_piece_count > 0
        else (len(component_weights) if component_weights else part_count),
        "joint_count": joint_count,
        "assembly_weight_lb": assembly_weight,
        "component_weights_lb": component_weights,
        "weight_calc": weight_info,
        "pdf_weight_lb": (weight_info.get("pdf_bom") or {}).get("assembly_weight_lb"),
        "source": "auto",
        "notes": notes_out,
    }


def run_weld_takeoff(
    pdf_path: Path | str,
    stp_path: Path | str | None = None,
    library_folder: Path | str | None = None,
) -> WeldTakeoffResult:
    pdf_path = Path(pdf_path)
    sizes, notes, page_hits, pdf_dimensions, pdf_meta = _parse_pdf_text(pdf_path)
    stp_summary: dict[str, Any] = {}
    if stp_path:
        try:
            stp_summary = _parse_stp_boxes(Path(stp_path))
        except Exception as exc:  # noqa: BLE001 — surface to flags
            stp_summary = {"error": str(exc)}
            notes.append(f"STP parse error: {exc}")

    items, flags = _build_items_from_signals(
        sizes=sizes,
        notes=notes,
        page_hits=page_hits,
        stp_summary=stp_summary,
        pdf_name=pdf_path.name,
        pdf_dimensions=pdf_dimensions,
    )
    if pdf_meta.get("ocr_used"):
        flags.insert(0, "OCR used to read weld callouts from vector PDF pages")
    elif pdf_meta.get("vector_heavy"):
        msg = (
            "PDF is mostly CAD vector graphics with little extractable text — "
            "weld symbols/sizes may need manual entry."
        )
        if pdf_meta.get("ocr_error"):
            msg += f" OCR unavailable: {pdf_meta.get('ocr_error')}"
        else:
            msg += " Attach STEP for geometry/fit-up when available."
        flags.insert(0, msg)
    fitup_drivers = estimate_fitup_drivers(
        stp_summary,
        notes,
        pdf_path=pdf_path,
        library_folder=library_folder,
    )
    for n in fitup_drivers.get("notes") or []:
        if n not in flags:
            flags.append(n)

    return WeldTakeoffResult(
        items=items,
        flags=flags,
        sizes_found=sorted(set(sizes)),
        notes=notes[:40],
        fitup_drivers=fitup_drivers,
        stp_summary={
            "solid_count": stp_summary.get("solid_count", 0),
            "unit_scale": stp_summary.get("unit_scale"),
            "error": stp_summary.get("error"),
            "top_solids": (stp_summary.get("solids") or [])[:8],
            "pdf_dimension_count": len(pdf_dimensions),
            "pdf_dimensions_sample": sorted(set(round(d, 2) for d in pdf_dimensions), reverse=True)[
                :12
            ],
            "cover_inches": stp_summary.get("cover_inches"),
            "covers_included_in_total": stp_summary.get("covers_included_in_total"),
            "weld_inches_calc": stp_summary.get("weld_inches_calc"),
            "pdf_text_chars": pdf_meta.get("text_chars"),
            "pdf_drawing_count": pdf_meta.get("drawing_count"),
            "pdf_vector_heavy": pdf_meta.get("vector_heavy"),
            "ocr_used": pdf_meta.get("ocr_used"),
            "ocr_error": pdf_meta.get("ocr_error"),
        },
    )
