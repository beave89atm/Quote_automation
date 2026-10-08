"""Bend count from the conventions table, not from a guess.

Text conventions live in ``bend_conventions.yaml``. Geometry conventions in
that file describe PyMuPDF dash patterns (center and phantom). Hidden-line
dashes and solid strokes are not bend lines. A PDF does not carry the CAD
layer name, so a dash pattern only corroborates a bend the text already
named. Hole and symmetry centerlines do not create a bend, do not disagree
with the text count, and do not by themselves say the bends are in two planes.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_LIBRARY = Path(__file__).with_name("bend_conventions.yaml")
_MIN_BEND_LINE_PT = 72.0  # 1 inch. Shorter centerlines are hole marks.


@dataclass(frozen=True)
class Convention:
    id: str
    confidence: str
    layer: str
    role: str
    pattern: re.Pattern[str] | None
    flag: str
    note: str
    min_matches: int
    axis: str
    dash: str
    sources: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class DetectedBend:
    convention_id: str
    confidence: str
    evidence: str
    corroboration: tuple[str, ...] = ()


@dataclass(frozen=True)
class BendDetection:
    count: int | None
    flag: str | None
    bends: tuple[DetectedBend, ...]
    plane_flag: str | None = None
    geometry_count: int | None = None


@dataclass(frozen=True)
class _Hit:
    convention_id: str
    span: tuple[int, int]
    line: str
    value: int | None
    evidence: str


def _compile(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern)


@lru_cache(maxsize=1)
def load_conventions(path: str | None = None) -> tuple[Convention, ...]:
    """Load the conventions table. ``path`` bypasses the cache when tests pass one."""
    src = Path(path) if path else _LIBRARY
    raw = yaml.safe_load(src.read_text(encoding="utf-8")) or {}
    rows = raw.get("conventions") or []
    loaded: list[Convention] = []
    for row in rows:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        pattern = str(row.get("pattern") or "")
        sources = tuple(
            {"title": str(item.get("title") or ""), "url": str(item.get("url") or "")}
            for item in (row.get("sources") or [])
            if isinstance(item, dict)
        )
        loaded.append(
            Convention(
                id=str(row["id"]),
                confidence=str(row.get("confidence") or "low"),
                layer=str(row.get("layer") or "text"),
                role=str(row.get("role") or ""),
                pattern=_compile(pattern) if pattern else None,
                flag=str(row.get("flag") or ""),
                note=str(row.get("note") or ""),
                min_matches=int(row.get("min_matches") or 1),
                axis=str(row.get("axis") or ""),
                dash=str(row.get("dash") or ""),
                sources=sources,
            )
        )
    return tuple(loaded)


def convention_ids() -> tuple[str, ...]:
    return tuple(item.id for item in load_conventions())


_PAREN_BEND_LINE_RE = re.compile(r"(?i)\(\s*BEND\s+LINES?\s*\)")
_STACK_NUM_RE = re.compile(r"^(\d{1,2})$")
_STACK_DEN_RE = re.compile(r"^(\d{1,2})(.*)$")
_STACK_DENS = {2, 4, 8, 16, 32, 64}
_STACK_REST_RE = re.compile(r"(?i)^\s*BENDS?(?:\s+RAD(?:IUS)?)?\s*$")


def normalize_stacked_fractions(text: str) -> str:
    """Join a stacked inch fraction so ``1`` / ``4 BEND RADIUS`` is not ``4 BENDS``."""
    lines = str(text or "").splitlines()
    out: list[str] = []
    index = 0
    while index < len(lines):
        current = lines[index].strip()
        num_match = _STACK_NUM_RE.fullmatch(current)
        if num_match and index + 1 < len(lines):
            numerator = int(num_match.group(1))
            nxt = lines[index + 1].strip()
            den_match = _STACK_DEN_RE.fullmatch(nxt)
            if den_match:
                denominator = int(den_match.group(1))
                rest = den_match.group(2)
                if (
                    denominator in _STACK_DENS
                    and 0 < numerator < denominator
                    and _STACK_REST_RE.match(rest)
                ):
                    out.append(f"{numerator}/{denominator}{rest}")
                    index += 2
                    continue
            if (
                _STACK_NUM_RE.fullmatch(nxt)
                and index + 2 < len(lines)
                and _STACK_REST_RE.match(lines[index + 2].strip())
            ):
                denominator = int(nxt)
                if denominator in _STACK_DENS and 0 < numerator < denominator:
                    out.append(f"{numerator}/{denominator} {lines[index + 2].strip()}")
                    index += 3
                    continue
        out.append(lines[index])
        index += 1
    return "\n".join(out)


def mask_false_positives(text: str, conventions: tuple[Convention, ...] | None = None) -> str:
    """Blank lines that are edge breaks, chamfers, countersinks, or title words."""
    library = conventions if conventions is not None else load_conventions()
    patterns = [item.pattern for item in library if item.role == "false_positive" and item.pattern]
    normalized = normalize_stacked_fractions(text)
    normalized = _PAREN_BEND_LINE_RE.sub(lambda match: " " * len(match.group(0)), normalized)
    kept: list[str] = []
    for line in normalized.splitlines():
        if any(pattern.search(line) for pattern in patterns):
            kept.append(" " * len(line))
        else:
            kept.append(line)
    return "\n".join(kept)


def _overlaps(span: tuple[int, int], occupied: list[tuple[int, int]]) -> bool:
    start, end = span
    return any(not (end <= left or start >= right) for left, right in occupied)


def _line_at(text: str, index: int) -> str:
    start = text.rfind("\n", 0, index) + 1
    end = text.find("\n", index)
    if end < 0:
        end = len(text)
    return text[start:end]


def _hits(text: str, convention: Convention, occupied: list[tuple[int, int]]) -> list[_Hit]:
    if convention.pattern is None:
        return []
    found: list[_Hit] = []
    for match in convention.pattern.finditer(text):
        span = (match.start(), match.end())
        if _overlaps(span, occupied):
            continue
        value: int | None = None
        if match.groups():
            token = match.group(1)
            if token and token.isdigit():
                value = int(token)
        found.append(
            _Hit(
                convention_id=convention.id,
                span=span,
                line=_line_at(text, match.start()),
                value=value,
                evidence=" ".join(match.group(0).split()),
            )
        )
    return found


def _multiplier(line: str, conventions: tuple[Convention, ...]) -> int | None:
    values: list[int] = []
    for item in conventions:
        if item.role != "multiplier" or item.pattern is None:
            continue
        for match in item.pattern.finditer(line):
            try:
                values.append(int(match.group(1)))
            except (IndexError, TypeError, ValueError):
                continue
    unique = {value for value in values if value >= 1}
    if len(unique) == 1:
        return unique.pop()
    if len(unique) > 1:
        return -1
    return None


def _classify_dash(dashes: Any) -> str:
    text = str(dashes or "")
    bracket = re.search(r"\[([^\]]*)\]", text)
    if bracket is None:
        return "solid" if text.strip() in {"", "[] 0", "[]0"} else "unknown"
    nums = [float(part) for part in bracket.group(1).split() if _is_float(part)]
    if not nums:
        return "solid"
    if len(nums) == 2:
        long, gap = nums
        if min(long, gap) <= 0:
            return "dashed"
        if max(long, gap) / min(long, gap) < 2.5:
            return "hidden"
        return "dashed"
    if len(nums) == 4 and nums[0] > nums[2] * 1.8:
        return "center"
    if len(nums) >= 6 and nums[0] > max(nums[2], nums[4]) * 1.8:
        return "phantom"
    return "dashed"


def _is_float(token: str) -> bool:
    try:
        float(token)
    except ValueError:
        return False
    return True


def _segment(item: Any) -> tuple[tuple[float, float], tuple[float, float]] | None:
    if not isinstance(item, (list, tuple)) or len(item) < 3 or item[0] != "l":
        return None
    start, end = item[1], item[2]
    try:
        return ((float(start.x), float(start.y)), (float(end.x), float(end.y)))
    except AttributeError:
        try:
            return (
                (float(start[0]), float(start[1])),
                (float(end[0]), float(end[1])),
            )
        except (TypeError, ValueError, IndexError):
            return None


_NOTE_AXIS_RE = re.compile(
    r"(?i)(?<![A-Z0-9])(?:UP|DOWN)[ \t]+\d|\bBEND[ \t]+(?:UP|DOWN)\b"
)
_DASH_BEND_RE = re.compile(r"(?i)(?:^|[\s(])[-–—]\s*(\d+)\s+BEND\b")


def _point_segment_distance(
    px: float,
    py: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> float:
    dx, dy = x2 - x1, y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq <= 0:
        return math.hypot(px - x1, py - y1)
    ratio = ((px - x1) * dx + (py - y1) * dy) / length_sq
    ratio = max(0.0, min(1.0, ratio))
    return math.hypot(px - (x1 + ratio * dx), py - (y1 + ratio * dy))


def _note_anchors(
    text_blocks: list[dict[str, Any]] | None,
) -> list[tuple[float, float]] | None:
    """Centers of bend-note text, or None when positions were not supplied.

    None means "do not filter". An empty list means positions exist and no
    bend note is sitting on a line, so no line is bend geometry.
    """
    if not text_blocks:
        return None
    anchors: list[tuple[float, float]] = []
    saw_box = False
    for block in text_blocks:
        if not isinstance(block, dict):
            continue
        bbox = block.get("bbox")
        if not isinstance(bbox, (list, tuple)) or len(bbox) < 4:
            continue
        saw_box = True
        if not _NOTE_AXIS_RE.search(str(block.get("text") or "")):
            continue
        try:
            x0, y0, x1, y1 = (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
        except (TypeError, ValueError):
            continue
        anchors.append(((x0 + x1) / 2.0, (y0 + y1) / 2.0))
    if not saw_box:
        return None
    return anchors


def _dash_option_flag(text: str) -> str | None:
    """``-1 BEND`` and ``-2 BEND`` are separate dash options, not one count."""
    dashes = {match.group(1) for match in _DASH_BEND_RE.finditer(text)}
    if len(dashes) >= 2:
        return "dash bend notes are separate options, not one bend count"
    return None


def _geometry(
    drawings: list[dict[str, Any]] | None,
    anchors: list[tuple[float, float]] | None = None,
) -> tuple[int | None, bool, tuple[str, ...], int]:
    """Long center/phantom lines.

    Returns (dominant count or None, perpendicular, style ids, total lines).
    When ``anchors`` is a list, a line counts only if a bend note sits near it.
    """
    if not drawings:
        return None, False, (), 0
    seen: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    lines: list[tuple[float, str]] = []
    for drawing in drawings:
        if not isinstance(drawing, dict):
            continue
        kind = _classify_dash(drawing.get("dashes"))
        if kind not in {"center", "phantom"}:
            continue
        style_id = "geom_center_line" if kind == "center" else "geom_phantom_line"
        for item in drawing.get("items") or []:
            seg = _segment(item)
            if seg is None:
                continue
            (x1, y1), (x2, y2) = seg
            if anchors is not None and not any(
                _point_segment_distance(px, py, x1, y1, x2, y2) <= 48.0
                for px, py in anchors
            ):
                continue
            key = tuple(sorted(((round(x1, 1), round(y1, 1)), (round(x2, 1), round(y2, 1)))))
            if key in seen:
                continue
            seen.add(key)  # type: ignore[arg-type]
            length = math.hypot(x2 - x1, y2 - y1)
            if length < _MIN_BEND_LINE_PT:
                continue
            angle = math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180.0
            lines.append((angle, style_id))
    if not lines:
        return None, False, (), 0
    families: list[list[tuple[float, str]]] = []
    for angle, style_id in lines:
        placed = False
        for family in families:
            if _undirected_delta(angle, family[0][0]) <= 8.0:
                family.append((angle, style_id))
                placed = True
                break
        if not placed:
            families.append([(angle, style_id)])
    families.sort(key=len, reverse=True)
    dominant = families[0]
    styles = tuple(dict.fromkeys(style for _angle, style in dominant))
    perpendicular = False
    for other in families[1:]:
        if _near_perpendicular(dominant[0][0], other[0][0]):
            perpendicular = True
            break
    return len(dominant), perpendicular, styles, len(lines)


def _undirected_delta(left: float, right: float) -> float:
    delta = abs(left - right) % 180.0
    return min(delta, 180.0 - delta)


def _near_perpendicular(left: float, right: float) -> bool:
    return abs(_undirected_delta(left, right) - 90.0) <= 12.0


def _drawing_segments(
    drawings: list[dict[str, Any]] | None,
) -> list[tuple[float, float, float, float, float, str]]:
    """Long strokes as (x1, y1, x2, y2, length, dash kind).

    Short even dashes (hidden-line style) stay in. A bend note has to sit
    on one before it counts, so a hole mark with no note does not.
    """
    found: list[tuple[float, float, float, float, float, str]] = []
    for drawing in drawings or []:
        if not isinstance(drawing, dict):
            continue
        kind = _classify_dash(drawing.get("dashes"))
        for item in drawing.get("items") or []:
            seg = _segment(item)
            if seg is None:
                continue
            (x1, y1), (x2, y2) = seg
            length = math.hypot(x2 - x1, y2 - y1)
            if length < 36.0:
                continue
            found.append((x1, y1, x2, y2, length, kind))
    return found


def _anchored_bend_axes_perpendicular(
    drawings: list[dict[str, Any]] | None,
    text_blocks: list[dict[str, Any]] | None,
) -> str | None:
    """Flag when bend notes sit on lines that are about 90° apart.

    The line under the note is the signal. The direction the note is written
    is not. One rotated note, or two notes on parallel lines, stays one plane.
    Center and phantom strokes win over a nearby solid edge. A short-dash
    bend line wins over a solid edge too. Extra hole centerlines do not
    count unless a note is actually sitting on them.

    Centerline directions keep ``bends are not in a single plane``. A
    short-dash or mixed pair (a box bent on two directions) is
    ``bends in two planes, review``.
    """
    if not drawings or not text_blocks:
        return None
    notes: list[tuple[float, float]] = []
    for block in text_blocks:
        if not isinstance(block, dict):
            continue
        if not _NOTE_AXIS_RE.search(str(block.get("text") or "")):
            continue
        bbox = block.get("bbox")
        if not isinstance(bbox, (list, tuple)) or len(bbox) < 4:
            continue
        try:
            x0, y0, x1, y1 = (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
        except (TypeError, ValueError):
            continue
        notes.append(((x0 + x1) / 2.0, (y0 + y1) / 2.0))
    if len(notes) < 2:
        return None
    segments = _drawing_segments(drawings)
    if not segments:
        return None
    axes: list[tuple[str, float]] = []
    for px, py in notes:
        ranked: list[tuple[float, str, float]] = []
        for x1, y1, x2, y2, _length, kind in segments:
            dist = _point_segment_distance(px, py, x1, y1, x2, y2)
            if dist > 36.0:
                continue
            angle = math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180.0
            ranked.append((dist, kind, angle))
        if not ranked:
            continue
        preferred = [item for item in ranked if item[1] in {"center", "phantom"}]
        if not preferred:
            preferred = [item for item in ranked if item[1] in {"dashed", "hidden"}]
        pool = preferred or ranked
        pool.sort(key=lambda item: item[0])
        axes.append((pool[0][1], pool[0][2]))
    if len(axes) < 2:
        return None
    # Do not mix a centerline with a solid border. A border is used only
    # when no note is sitting on a center, phantom, or short-dash stroke.
    if any(kind in {"center", "phantom"} for kind, _angle in axes):
        axes = [(kind, angle) for kind, angle in axes if kind in {"center", "phantom"}]
    if len(axes) < 2:
        return None
    families: list[list[float]] = []
    for _kind, angle in axes:
        placed = False
        for family in families:
            if _undirected_delta(angle, family[0]) <= 12.0:
                family.append(angle)
                placed = True
                break
        if not placed:
            families.append([angle])
    perpendicular = False
    for index, left in enumerate(families):
        for right in families[index + 1 :]:
            if _near_perpendicular(left[0], right[0]):
                perpendicular = True
                break
        if perpendicular:
            break
    if not perpendicular:
        return None
    if any(kind in {"dashed", "hidden"} for kind, _angle in axes):
        return "bends in two planes, review"
    return "bends are not in a single plane"


def _plane_flag(
    text: str,
    conventions: tuple[Convention, ...],
    perpendicular: bool,
) -> str | None:
    for item in conventions:
        if item.role == "not_single_plane" and item.pattern and item.pattern.search(text):
            return item.flag or "bends are not in a single plane"
    axes = {
        item.axis
        for item in conventions
        if item.role == "axis" and item.axis and item.pattern and item.pattern.search(text)
    }
    if "horizontal" in axes and "vertical" in axes:
        return "bends are not in a single plane"
    if perpendicular:
        geom = next((item for item in conventions if item.id == "geom_perpendicular_families"), None)
        return (geom.flag if geom and geom.flag else "bends are not in a single plane")
    return None


def _bends_for(hits: list[_Hit], convention_id: str, confidence: str, times: int) -> list[DetectedBend]:
    evidence = hits[0].evidence if hits else convention_id
    return [
        DetectedBend(convention_id=convention_id, confidence=confidence, evidence=evidence)
        for _ in range(times)
    ]


def detect_bends(
    text: str,
    drawings: list[dict[str, Any]] | None = None,
    *,
    already_masked: bool = False,
    conventions: tuple[Convention, ...] | None = None,
    text_blocks: list[dict[str, Any]] | None = None,
) -> BendDetection:
    """Count bends. Low confidence and conflicts flag. Nothing is guessed.

    ``text_blocks`` is optional. Each item may carry ``text``, ``dir``
    ``(dx, dy)``, and ``bbox`` ``(x0, y0, x1, y1)`` from the PDF text layer.
    A centerline counts only when a bend note sits on it. The direction the
    note is written is not a bend plane. Notes that sit on bend lines about
    90° apart are two planes. Geometry never creates a bend and never
    overrides the text count.
    """
    library = conventions if conventions is not None else load_conventions()
    blob = text if already_masked else mask_false_positives(text, library)
    anchors = _note_anchors(text_blocks)
    geom_count, perpendicular, geom_styles, geom_total = _geometry(drawings, anchors)
    plane = _plane_flag(blob, library, False)
    dash_flag = _dash_option_flag(blob)
    if dash_flag:
        return BendDetection(
            count=None,
            flag=dash_flag,
            bends=(),
            plane_flag=plane,
            geometry_count=geom_count,
        )
    occupied: list[tuple[int, int]] = []
    explicit: list[_Hit] = []
    each: list[tuple[_Hit, int]] = []
    table: list[_Hit] = []
    low: list[tuple[Convention, list[_Hit]]] = []

    for item in library:
        if item.layer != "text" or item.pattern is None:
            continue
        hits = _hits(blob, item, occupied)
        if item.role == "explicit_count":
            kept = [hit for hit in hits if hit.value is not None and hit.value >= 1]
            explicit.extend(kept)
            occupied.extend(hit.span for hit in kept)
        elif item.role == "count_each":
            for hit in hits:
                factor = _multiplier(hit.line, library)
                if factor == -1:
                    return BendDetection(
                        count=None,
                        flag="bend multiplier on one line disagrees with itself",
                        bends=(),
                        plane_flag=plane,
                        geometry_count=geom_count,
                    )
                times = factor or 1
                each.append((hit, times))
                occupied.append(hit.span)
        elif item.role == "table_row":
            table.extend(hits)
            occupied.extend(hit.span for hit in hits)
        elif item.role in {"insufficient", "shared_note", "view_tally"}:
            low.append((item, _hits(blob, item, occupied)))

    groups: list[tuple[str, int, list[DetectedBend]]] = []
    if explicit:
        values = {hit.value for hit in explicit}
        if len(values) != 1:
            detail = ", ".join(f"{hit.convention_id}={hit.value}" for hit in explicit)
            return BendDetection(
                count=None,
                flag=f"signals conflict ({detail})",
                bends=(),
                plane_flag=plane,
                geometry_count=geom_count,
            )
        count = int(explicit[0].value or 0)
        ident = explicit[0].convention_id
        groups.append((ident, count, _bends_for(explicit, ident, "high", count)))
    if each:
        total = sum(times for _hit, times in each)
        made = [
            DetectedBend(hit.convention_id, "high", hit.evidence)
            for hit, times in each
            for _ in range(times)
        ]
        label = ",".join(dict.fromkeys(bend.convention_id for bend in made))
        groups.append((label, total, made))
    if table:
        ident = table[0].convention_id
        groups.append((ident, len(table), _bends_for(table, ident, "high", len(table))))

    counts = {count for _label, count, _bends in groups}
    if len(counts) > 1:
        detail = ", ".join(f"{label}={count}" for label, count, _bends in groups)
        return BendDetection(
            count=None,
            flag=f"signals conflict ({detail})",
            bends=(),
            plane_flag=plane,
            geometry_count=geom_count,
        )
    if groups:
        count = groups[0][1]
        bends = list(groups[0][2])
        extra = tuple(dict.fromkeys(label for label, _count, _bends in groups[1:]))
        # Geometry corroborates a text count. It does not add one and it does
        # not disagree. A perpendicular flag needs the lines to be the bends.
        if geom_count is not None and geom_count == count:
            extra = tuple(dict.fromkeys((*extra, *geom_styles)))
        if (
            plane is None
            and perpendicular
            and geom_total == count
            and count > 0
        ):
            geom = next(
                (item for item in library if item.id == "geom_perpendicular_families"),
                None,
            )
            plane = geom.flag if geom and geom.flag else "bends are not in a single plane"
        if plane is None:
            anchored = _anchored_bend_axes_perpendicular(drawings, text_blocks)
            if anchored:
                plane = anchored
        if extra:
            bends = [
                DetectedBend(
                    bend.convention_id,
                    bend.confidence,
                    bend.evidence,
                    corroboration=extra,
                )
                for bend in bends
            ]
        return BendDetection(
            count=count,
            flag=None,
            bends=tuple(bends),
            plane_flag=plane,
            geometry_count=geom_count,
        )
    for item, hits in low:
        if item.role == "view_tally" and len(hits) >= item.min_matches:
            return BendDetection(None, item.flag, (), plane, geom_count)
        if item.role != "view_tally" and hits:
            return BendDetection(None, item.flag or "bend callout does not give a count", (), plane, geom_count)
    return BendDetection(count=0, flag=None, bends=(), plane_flag=plane, geometry_count=geom_count)
