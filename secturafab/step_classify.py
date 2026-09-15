"""STEP stock classify: thin-sheet plate vs bar (flat or round).

Uses VERTEX_POINT coords or opposing-PLANE separations — never the span of
every CARTESIAN_POINT (hole-axis placements inflate that bbox and used to
false-positive ``strong_plate`` / Cad Contours). invent=false; this module
does not invent Contours or InternalData.

Kyle / CoS 2026-09-14: RD BAR / round bar / diameter stock is Long/Linear,
never Cad Contours. Plate/sheet stays Cad Contours. Ambiguous stock
fail-closes away from the Laser Contours plate path.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any, Iterable

STOCK_STRONG_PLATE = "strong_plate"
STOCK_FLAT_BAR = "flat_bar"
STOCK_ROUND_BAR = "round_bar"
STOCK_OTHER = "other"
STOCK_BAR_KINDS = frozenset({STOCK_FLAT_BAR, STOCK_ROUND_BAR})

# Shop / LOM / PDF: RD BAR CR 1018 / 1/2 DIA → Linear, not Cad Contours.
_RD_BAR_RE = re.compile(
    r"(?i)(?:\bRD\.?\s*BAR\b|\bRDBAR\b|\bROUND\s+BAR\b|\bBAR\s+ROUND\b|"
    r"\bROUND\s+STOCK\b|\bBAR\s+STOCK\b)"
)
# Diameter stock (not a plate hole callout by itself).
_DIA_STOCK_RE = re.compile(
    r"(?i)(?:\b\d+(?:\s+\d+/\d+|\.\d+|/\d+)?\s*(?:IN(?:CH(?:ES)?)?)?\s*"
    r"DIA(?:METER)?\b|\bDIA(?:METER)?\s*\d)"
)
_PLATE_SHEET_RE = re.compile(r"(?i)\b(?:PLATE|SHEET|GUSSET)\b")
_HOLE_DIA_RE = re.compile(r"(?i)\b(?:HOLE|HOLES|DRILL|C'?BORE|THRU)\b")

# Laser plate: one dim << the other two, thickness in sheet/plate class.
_LASER_THICKNESS_MAX_IN = 0.75
_THIN_SHEET_RATIO = 0.20
# Flat-bar Linear: thickness in the 1–2 in class, not a thin sheet.
_BAR_THICKNESS_MIN_IN = 0.76
_BAR_THICKNESS_MAX_IN = 2.5
_BAR_WIDTH_MAX_IN = 8.0
_BAR_ELONGATION = 3.0
_BAR_MIN_LENGTH_IN = 10.0
_BAR_THICK_TO_WIDTH = 0.20
# Round bar: two similar small axes (diameter) + elongation. 1/2 DIA is 0.5 in.
_ROUND_DIA_MIN_IN = 0.1875
_ROUND_DIA_MAX_IN = 2.5
_ROUND_SECTION_RATIO = 0.25
_ROUND_ELONGATION = 2.5

_ENTITY_RE = re.compile(r"^#(\d+)\s*=\s*(.+?);\s*$", re.M)
_CARTESIAN_RE = re.compile(
    r"CARTESIAN_POINT\s*\(\s*'[^']*'\s*,\s*\(\s*([^)]+?)\s*\)",
    re.I,
)
_VERTEX_RE = re.compile(r"VERTEX_POINT\s*\(\s*'[^']*'\s*,\s*#(\d+)", re.I)
_PLANE_RE = re.compile(r"PLANE\s*\(\s*'[^']*'\s*,\s*#(\d+)", re.I)
_AXIS_RE = re.compile(
    r"AXIS2_PLACEMENT_3D\s*\(\s*'[^']*'\s*,\s*#(\d+)\s*,\s*#(\d+)",
    re.I,
)
_DIRECTION_RE = re.compile(
    r"DIRECTION\s*\(\s*'[^']*'\s*,\s*\(\s*([^)]+?)\s*\)",
    re.I,
)
_NUM_RE = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")


def _floats(blob: str) -> list[float]:
    return [float(x) for x in _NUM_RE.findall(blob or "")]


def _unit_scale(text: str) -> float:
    if re.search(r"CONVERSION_BASED_UNIT\s*\(\s*'INCH'", text, re.I):
        return 1.0
    if re.search(r"SI_UNIT\s*\(\s*\.MILLI\.\s*,\s*\.METRE\.", text, re.I):
        return 1.0 / 25.4
    if "MILLI" in text.upper() and "INCH" not in text.upper():
        return 1.0 / 25.4
    return 1.0


def _sorted_box(dims: Iterable[float]) -> tuple[float, float, float] | None:
    vals = [float(x) for x in dims if x is not None]
    if len(vals) < 3:
        return None
    a, b, c = sorted(abs(v) for v in vals[:3])
    if a <= 0 and b <= 0 and c <= 0:
        return None
    return (c, b, a)  # L >= W >= T


def _bbox_from_points(points: Iterable[tuple[float, float, float]]) -> tuple[float, float, float] | None:
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    for p in points:
        if not p or len(p) != 3:
            continue
        xs.append(p[0])
        ys.append(p[1])
        zs.append(p[2])
    if not xs:
        return None
    return _sorted_box((max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)))


def _parse_entities(text: str) -> dict[int, str]:
    compact = re.sub(r",\s*\n\s*", ",", text or "")
    return {
        int(m.group(1)): m.group(2).strip()
        for m in _ENTITY_RE.finditer(compact)
    }


def _cartesian_points(ents: dict[int, str], scale: float) -> dict[int, tuple[float, float, float]]:
    pts: dict[int, tuple[float, float, float]] = {}
    for eid, body in ents.items():
        m = _CARTESIAN_RE.search(body)
        if not m:
            continue
        vals = _floats(m.group(1))
        if len(vals) >= 3:
            pts[eid] = (vals[0] * scale, vals[1] * scale, vals[2] * scale)
    return pts


def _vertex_points(
    ents: dict[int, str],
    pts: dict[int, tuple[float, float, float]],
) -> list[tuple[float, float, float]]:
    out: list[tuple[float, float, float]] = []
    for body in ents.values():
        m = _VERTEX_RE.search(body)
        if not m:
            continue
        p = pts.get(int(m.group(1)))
        if p:
            out.append(p)
    return out


def _directions(ents: dict[int, str]) -> dict[int, tuple[float, float, float]]:
    dirs: dict[int, tuple[float, float, float]] = {}
    for eid, body in ents.items():
        m = _DIRECTION_RE.search(body)
        if not m:
            continue
        vals = _floats(m.group(1))
        if len(vals) < 3:
            continue
        mag = math.sqrt(vals[0] ** 2 + vals[1] ** 2 + vals[2] ** 2)
        if mag <= 1e-12:
            continue
        dirs[eid] = (vals[0] / mag, vals[1] / mag, vals[2] / mag)
    return dirs


def _plane_placements(
    ents: dict[int, str],
    pts: dict[int, tuple[float, float, float]],
    dirs: dict[int, tuple[float, float, float]],
) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
    """(origin, unit normal) for each PLANE → AXIS2_PLACEMENT_3D."""
    axes: dict[int, tuple[int, int]] = {}
    for eid, body in ents.items():
        m = _AXIS_RE.search(body)
        if m:
            axes[eid] = (int(m.group(1)), int(m.group(2)))
    planes: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
    for body in ents.values():
        m = _PLANE_RE.search(body)
        if not m:
            continue
        axis = axes.get(int(m.group(1)))
        if not axis:
            continue
        origin = pts.get(axis[0])
        normal = dirs.get(axis[1])
        if origin and normal:
            planes.append((origin, normal))
    return planes


def _opposing_plane_box(
    planes: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
) -> tuple[float, float, float] | None:
    """Separations between parallel opposite PLANEs (thickness / width / length)."""
    if len(planes) < 2:
        return None
    used: set[int] = set()
    seps: list[float] = []
    for i, (o1, n1) in enumerate(planes):
        if i in used:
            continue
        best_j: int | None = None
        best_sep = 0.0
        for j, (o2, n2) in enumerate(planes):
            if j <= i or j in used:
                continue
            align = abs(n1[0] * n2[0] + n1[1] * n2[1] + n1[2] * n2[2])
            if align < 0.98:
                continue
            delta = (o2[0] - o1[0], o2[1] - o1[1], o2[2] - o1[2])
            sep = abs(delta[0] * n1[0] + delta[1] * n1[1] + delta[2] * n1[2])
            if sep > best_sep:
                best_sep = sep
                best_j = j
        if best_j is not None and best_sep > 1e-6:
            used.add(i)
            used.add(best_j)
            seps.append(best_sep)
    if len(seps) < 3:
        return None
    seps.sort(reverse=True)
    return _sorted_box(seps[:3])


def all_cartesian_bbox(
    text: str,
    *,
    scale: float | None = None,
) -> tuple[float, float, float] | None:
    """Inflated span of every CARTESIAN_POINT — do not use for stock classify."""
    ents = _parse_entities(text)
    unit = _unit_scale(text) if scale is None else scale
    return _bbox_from_points(_cartesian_points(ents, unit).values())


def robust_step_bbox(text: str) -> dict[str, Any]:
    """Vertex or opposing-PLANE bbox. All-CARTESIAN span is recorded, not used."""
    ents = _parse_entities(text)
    scale = _unit_scale(text)
    pts = _cartesian_points(ents, scale)
    vertex = _bbox_from_points(_vertex_points(ents, pts))
    plane = _opposing_plane_box(_plane_placements(ents, pts, _directions(ents)))
    all_pts = _bbox_from_points(pts.values())
    box = plane or vertex
    source = "plane" if plane else ("vertex" if vertex else None)
    return {
        "box": list(box) if box else None,
        "vertex_box": list(vertex) if vertex else None,
        "plane_box": list(plane) if plane else None,
        "all_cartesian_box": list(all_pts) if all_pts else None,
        "source": source,
        "unit_scale": scale,
    }


def looks_like_round_bar_stock(text: str | None) -> bool:
    """True for RD BAR / ROUND BAR / diameter stock — Long/Linear, not Cad.

    Plate/sheet nouns with hole-DIA callouts stay plate (not this). A bare
    ``1/2 DIA`` / ``RD BAR CR 1018`` material string is bar. invent=false.
    """
    blob = str(text or "").strip()
    if not blob:
        return False
    if _RD_BAR_RE.search(blob):
        return True
    if not _DIA_STOCK_RE.search(blob):
        return False
    # Plate/sheet + DIA is usually a hole callout — stay plate.
    # Bare DIA / CR 1018 / 1/2 DIA with no plate noun is diameter stock.
    if _PLATE_SHEET_RE.search(blob) and not _RD_BAR_RE.search(blob):
        return False
    if _HOLE_DIA_RE.search(blob) and not _RD_BAR_RE.search(blob):
        return False
    return True


def row_looks_like_round_bar_stock(row: dict[str, Any] | None) -> bool:
    """True when a CadImport / GET row's LOM/PDF/name blob is round bar."""
    if not isinstance(row, dict):
        return False
    blob = " ".join(
        str(row.get(key) or "")
        for key in (
            "Name",
            "Description",
            "FileName",
            "Material",
            "MaterialGrade",
            "SKU",
            "stock_text",
            "stock_kind",
            "noun",
        )
    )
    kind = str(row.get("stock_kind") or "").strip().casefold()
    if kind in STOCK_BAR_KINDS:
        return True
    return looks_like_round_bar_stock(blob)


def score_step_stock(dims: Iterable[float] | None) -> str:
    """Rank robust dims: thin-sheet plate vs flat-bar vs round-bar."""
    box = _sorted_box(dims or [])
    if not box:
        return STOCK_OTHER
    length, width, thick = box
    thin_sheet = (
        0 < thick <= _LASER_THICKNESS_MAX_IN + 1e-9
        and width > 0
        and length > 0
        and thick / width <= _THIN_SHEET_RATIO
        and thick / length <= _THIN_SHEET_RATIO
    )
    elongated = width > 0 and length / width >= _BAR_ELONGATION
    bar_class = (
        _BAR_THICKNESS_MIN_IN <= thick <= _BAR_THICKNESS_MAX_IN
        and 0 < width <= _BAR_WIDTH_MAX_IN
        and (
            elongated
            or (
                length >= _BAR_MIN_LENGTH_IN
                and thick / width >= _BAR_THICK_TO_WIDTH
            )
        )
    )
    # Circular section: two similar small axes + elongation (1/2 DIA hook).
    section_span = max(width, thick)
    round_section = (
        section_span > 0
        and abs(width - thick) / section_span <= _ROUND_SECTION_RATIO
        and _ROUND_DIA_MIN_IN <= section_span <= _ROUND_DIA_MAX_IN
        and length / section_span >= _ROUND_ELONGATION
    )
    if round_section:
        return STOCK_ROUND_BAR
    if bar_class:
        return STOCK_FLAT_BAR
    if thin_sheet:
        return STOCK_STRONG_PLATE
    return STOCK_OTHER


def step_stock_category(kind: str | None) -> str | None:
    """Cad Contours only for ``strong_plate``. Bar stock is Long/Linear."""
    if kind in STOCK_BAR_KINDS:
        return "Linear"
    if kind == STOCK_STRONG_PLATE:
        return "Cad"
    return None


def contours_path_allowed(kind: str | None) -> bool:
    """False for bar Linear stock — do not route to Cad Contours."""
    return kind not in STOCK_BAR_KINDS


def classify_step_text(text: str) -> dict[str, Any]:
    parsed = robust_step_bbox(text)
    box = parsed.get("box")
    kind = score_step_stock(box)
    parsed["kind"] = kind
    parsed["category"] = step_stock_category(kind)
    parsed["contours_path_allowed"] = contours_path_allowed(kind)
    return parsed


def classify_step_file(path: Path | str | None) -> dict[str, Any] | None:
    if path is None:
        return None
    stp = Path(path)
    if not stp.is_file():
        return None
    try:
        try:
            text = stp.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = stp.read_text(encoding="latin-1")
    except OSError:
        return None
    return classify_step_text(text)


def first_step_stock(cad_files: list[Path] | None) -> dict[str, Any] | None:
    for path in cad_files or []:
        if path is None:
            continue
        p = Path(path)
        if p.suffix.lower() not in {".stp", ".step", ".p21"}:
            continue
        hit = classify_step_file(p)
        if hit:
            return hit
    return None
