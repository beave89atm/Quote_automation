"""Read a drawn LIST OF MATERIAL from a rendered page bitmap.

Time (and similar) LOM tables are CAD linework, not extractable PDF text.
Clip-to-Excel means: rasterize → find the printed grid lines → OCR each cell.
"""

from __future__ import annotations

import re
from typing import Any, Callable

from PIL import Image, ImageOps

OcrCell = Callable[[Image.Image], str]

_ITEM_RE = re.compile(r"^[A-Z]{1,2}$")
_PART_RE = re.compile(r"\d{4,7}\s*[-–—]\s*\d{1,3}[A-Za-z]?\b")
_QTY_RE = re.compile(r"^(\d{1,3}|-|—|–)$")
_HEADER_MARK = re.compile(
    r"(ITEM|PART|DESC|QTY|LIST|MATERIAL)",
    re.IGNORECASE,
)


def _ink_mask(im: Image.Image, threshold: int = 165) -> Image.Image:
    gray = ImageOps.autocontrast(im.convert("L"))
    return gray.point(lambda p: 255 if p < threshold else 0)


def _projection_peaks(
    mask: Image.Image,
    *,
    axis: str,
    min_frac: float,
    min_gap: int,
) -> list[int]:
    """Return ink-peak positions along y (horizontal lines) or x (vertical lines)."""
    w, h = mask.size
    pix = mask.load()
    if axis == "y":
        length, other = h, w
    else:
        length, other = w, h
    scores: list[float] = []
    for i in range(length):
        ink = 0
        if axis == "y":
            for x in range(other):
                if pix[x, i] > 0:
                    ink += 1
        else:
            for y in range(other):
                if pix[i, y] > 0:
                    ink += 1
        scores.append(ink / max(1, other))
    peaks: list[int] = []
    i = 0
    while i < length:
        if scores[i] < min_frac:
            i += 1
            continue
        j = i
        best_i, best = i, scores[i]
        while j < length and scores[j] >= min_frac * 0.7:
            if scores[j] > best:
                best, best_i = scores[j], j
            j += 1
        if not peaks or best_i - peaks[-1] >= min_gap:
            peaks.append(best_i)
        i = j
    return peaks


def find_grid_lines(
    im: Image.Image,
    *,
    min_h: int = 6,
    min_v: int = 5,
) -> dict[str, Any]:
    """Detect a drawn table. Returns h_lines, v_lines in image pixels."""
    mask = _ink_mask(im)
    w, h = mask.size
    h_lines = _projection_peaks(mask, axis="y", min_frac=0.28, min_gap=max(6, h // 80))
    v_lines = _projection_peaks(mask, axis="x", min_frac=0.22, min_gap=max(6, w // 90))
    return {
        "h_lines": h_lines,
        "v_lines": v_lines,
        "found": len(h_lines) >= min_h and len(v_lines) >= min_v,
    }


def _crop_cell(im: Image.Image, x0: int, y0: int, x1: int, y1: int, pad: int = 2) -> Image.Image:
    box = (
        min(im.size[0], max(0, x0 + pad)),
        min(im.size[1], max(0, y0 + pad)),
        min(im.size[0], max(0, x1 - pad)),
        min(im.size[1], max(0, y1 - pad)),
    )
    if box[2] <= box[0] or box[3] <= box[1]:
        return Image.new("L", (8, 8), 255)
    return im.crop(box)


def default_ocr_cell(im: Image.Image) -> str:
    from quote_core.ocr import ocr_available, tesseract_cmd

    if not ocr_available():
        return ""
    import pytesseract

    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd()
    cfg = "--oem 3 --psm 7"
    try:
        text = pytesseract.image_to_string(im, config=cfg) or ""
    except Exception:  # noqa: BLE001
        return ""
    return re.sub(r"\s+", " ", text).strip()


def cells_from_lines(
    im: Image.Image,
    h_lines: list[int],
    v_lines: list[int],
    *,
    ocr_cell: OcrCell | None = None,
) -> list[list[str]]:
    """OCR each printed cell between consecutive grid lines."""
    read = ocr_cell or default_ocr_cell
    rows: list[list[str]] = []
    for ri in range(len(h_lines) - 1):
        row: list[str] = []
        for ci in range(len(v_lines) - 1):
            cell = _crop_cell(im, v_lines[ci], h_lines[ri], v_lines[ci + 1], h_lines[ri + 1])
            row.append(read(cell))
        if any(row):
            rows.append(row)
    return rows


def _col_kind(values: list[str]) -> str:
    nonempty = [v.strip() for v in values if v and v.strip()]
    if not nonempty:
        return "empty"
    item_n = sum(1 for v in nonempty if _ITEM_RE.match(v.upper()))
    part_n = sum(1 for v in nonempty if _PART_RE.search(v))
    qty_n = sum(1 for v in nonempty if _QTY_RE.match(v.strip()))
    header_n = sum(1 for v in nonempty if _HEADER_MARK.search(v))
    n = len(nonempty)
    if part_n >= max(2, n * 0.4):
        return "part"
    if item_n >= max(2, n * 0.4):
        return "item"
    if qty_n >= max(2, n * 0.5) and part_n == 0:
        return "qty"
    if header_n and part_n == 0 and item_n == 0:
        return "headerish"
    return "desc"


def _looks_like_header(row: list[str]) -> bool:
    joined = " ".join(row).upper()
    hits = sum(1 for key in ("ITEM", "PART", "DESC", "QTY") if key in joined)
    dashes = sum(1 for c in row if re.fullmatch(r"-?\s*[1-9]", (c or "").strip()))
    return hits >= 2 or (hits >= 1 and dashes >= 2)


def infer_lom_headers(rows: list[list[str]]) -> list[str]:
    """Build ``-N … -1 | ITEM | PART NO | DESCRIPTION`` when slanted headers fail."""
    if not rows:
        return []
    width = max(len(r) for r in rows)
    padded = [r + [""] * (width - len(r)) for r in rows]
    kinds = [_col_kind([padded[r][c] for r in range(len(padded))]) for c in range(width)]
    qty_idxs = [i for i, k in enumerate(kinds) if k == "qty"]
    headers = [""] * width
    if qty_idxs:
        # Rightmost qty column is dash -1 (Time multi-dash).
        for offset, idx in enumerate(reversed(qty_idxs)):
            headers[idx] = f"-{offset + 1}"
    for i, k in enumerate(kinds):
        if headers[i]:
            continue
        if k == "item":
            headers[i] = "ITEM"
        elif k == "part":
            headers[i] = "PART NO"
        elif k == "desc" or k == "headerish" or k == "empty":
            headers[i] = "DESCRIPTION"
    if "ITEM" not in headers:
        for i, k in enumerate(kinds):
            if k == "item" or (
                not headers[i].startswith("-") and i == (qty_idxs[-1] + 1 if qty_idxs else 0)
            ):
                headers[i] = "ITEM"
                break
    if "PART NO" not in headers:
        for i, k in enumerate(kinds):
            if k == "part":
                headers[i] = "PART NO"
                break
    return headers


def normalize_grid_with_header(rows: list[list[str]]) -> list[list[str]]:
    """Put a header row first. Time prints ITEM A (or 1) at the bottom."""
    if not rows:
        return []
    header_idx = None
    if _looks_like_header(rows[-1]):
        header_idx = len(rows) - 1
    elif _looks_like_header(rows[0]):
        header_idx = 0
    if header_idx is None:
        headers = infer_lom_headers(rows)
        if not headers or "PART NO" not in headers:
            return []
        return [headers] + rows
    header = rows[header_idx]
    data = [r for i, r in enumerate(rows) if i != header_idx]
    # If the printed header tokens are unreadable, still infer dash names.
    if not any(re.fullmatch(r"-?\s*[1-9]", (c or "").strip()) for c in header):
        inferred = infer_lom_headers(data)
        if inferred and "PART NO" in inferred:
            header = inferred
    return [header] + data


def read_lom_grid_from_bitmap(
    im: Image.Image,
    *,
    ocr_cell: OcrCell | None = None,
) -> tuple[list[list[str]], dict[str, Any]]:
    """Return (grid including header, meta). Grid is empty when no table lines."""
    info = find_grid_lines(im)
    meta = {
        "grid_found": bool(info["found"]),
        "h_lines": list(info["h_lines"]),
        "v_lines": list(info["v_lines"]),
    }
    if not info["found"]:
        return [], meta
    raw = cells_from_lines(im, info["h_lines"], info["v_lines"], ocr_cell=ocr_cell)
    grid = normalize_grid_with_header(raw)
    meta["raw_rows"] = len(raw)
    return grid, meta


def render_page_region(page, clip, *, dpi: int = 220) -> Image.Image:
    import fitz

    pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72.0, dpi / 72.0), clip=clip, alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def candidate_lom_clips(page) -> list[Any]:
    """Time LOM sits in the title-block / right side. Try a few windows."""
    import fitz

    rect = page.rect
    return [
        fitz.Rect(rect.width * 0.50, rect.height * 0.22, rect.width * 0.999, rect.height * 0.99),
        fitz.Rect(rect.width * 0.55, rect.height * 0.35, rect.width * 0.999, rect.height * 0.99),
        fitz.Rect(rect.width * 0.48, 0, rect.width * 0.999, rect.height),
        fitz.Rect(rect.width * 0.35, rect.height * 0.40, rect.width * 0.999, rect.height * 0.99),
    ]


def clip_drawn_lom_from_page(
    page,
    *,
    ocr_cell: OcrCell | None = None,
    dpi: int = 220,
) -> tuple[list[list[str]], list[str], bool]:
    """
    Render the likely LOM region and read printed cells.

    Returns (grid, notes, grid_found). ``grid_found`` is True when table
    lines exist even if every cell OCR'd empty.
    """
    notes: list[str] = []
    saw_grid = False
    best: list[list[str]] = []
    for clip in candidate_lom_clips(page):
        im = render_page_region(page, clip, dpi=dpi)
        grid, meta = read_lom_grid_from_bitmap(im, ocr_cell=ocr_cell)
        if meta.get("grid_found"):
            saw_grid = True
        if grid and len(grid) > 1:
            notes.append(
                f"Clipped LIST OF MATERIAL from rendered grid "
                f"({len(meta.get('h_lines') or [])} H × {len(meta.get('v_lines') or [])} V lines)"
            )
            return grid, notes, True
        if len(grid) > len(best):
            best = grid
    if saw_grid:
        notes.append(
            "LIST OF MATERIAL grid lines found on the rendered page "
            "but cell OCR produced no usable rows"
        )
    return best, notes, saw_grid
