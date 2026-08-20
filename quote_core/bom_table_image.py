"""Bitmap LIST OF MATERIAL: segment grid lines, then OCR each row/cell.

Whole-page Tesseract on Time vector CAD returns SECTION B-B / dimensions and
0 BOM rows. A human can read the right-side render; this module finds the
horizontal/vertical grid on that bitmap and OCRs one row (or cell) at a time.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quote_core.bom_table import (
    SHORT_TABLE_REJECT,
    TALL_TABLE_MIN_ROWS,
    harvest_material_list_lines,
    harvest_ocr_row_strips,
    pick_best_material_list,
)

# Desktop / API crop saved next to the job PDF (not committed customer files).
TABLE_CROP_FILENAME = "bom_table_crop.png"


def resolve_table_crop(
    pdf_path: Path | str | None = None,
    table_image: Path | str | None = None,
) -> Path | None:
    """Explicit crop path, else ``{pdf.parent}/bom_table_crop.png`` if present."""
    if table_image:
        path = Path(table_image)
        if path.is_file():
            return path
    if pdf_path:
        sibling = Path(pdf_path).parent / TABLE_CROP_FILENAME
        if sibling.is_file():
            return sibling
    return None


def _as_pil(image: Any):
    from PIL import Image

    if isinstance(image, Image.Image):
        return image.convert("RGB")
    path = Path(image)
    return Image.open(path).convert("RGB")


def _binary(im, threshold: int = 150):
    from PIL import ImageOps

    gray = ImageOps.autocontrast(im.convert("L"))
    return gray.point(lambda x: 0 if x < threshold else 255)


def _projection_line_centers(
    binary,
    *,
    axis: str,
    min_frac: float,
    step: int = 2,
) -> list[int]:
    """axis='h' → y centers of horizontal rules; axis='v' → x centers of vertical rules."""
    w, h = binary.size
    pix = binary.load()
    if axis == "h":
        length = h
        span = max(1, len(range(0, w, step)))

        def dark_frac(i: int) -> float:
            return sum(1 for x in range(0, w, step) if pix[x, i] < 128) / span

    else:
        length = w
        span = max(1, len(range(0, h, step)))

        def dark_frac(i: int) -> float:
            return sum(1 for y in range(0, h, step) if pix[i, y] < 128) / span

    scores = [dark_frac(i) for i in range(length)]
    in_run = False
    run_start = 0
    centers: list[int] = []
    for i, s in enumerate(scores):
        if s >= min_frac and not in_run:
            in_run = True
            run_start = i
        elif s < min_frac and in_run:
            centers.append((run_start + i - 1) // 2)
            in_run = False
    if in_run:
        centers.append((run_start + length - 1) // 2)
    # Merge lines that are 1–2 px apart
    merged: list[int] = []
    for c in centers:
        if merged and c - merged[-1] <= 2:
            merged[-1] = (merged[-1] + c) // 2
        else:
            merged.append(c)
    return merged


def segment_table_bands(
    image: Any,
    *,
    min_row_px: int = 8,
    max_row_px: int = 64,
) -> dict[str, Any]:
    """
    Find table row (and optional column) bands from grid lines on a bitmap.

    Returns row boxes (x0, y0, x1, y1) in image pixels. Does not OCR.
    """
    im = _as_pil(image)
    bw = _binary(im)
    w, h = bw.size
    # Detect on a bounded copy so huge D-size strips stay cheap.
    scale = 1.0
    work = bw
    if w > 900:
        scale = 900.0 / w
        work = bw.resize((900, max(1, int(h * scale))))
    ww, wh = work.size
    y_lines = _projection_line_centers(work, axis="h", min_frac=0.42, step=2)
    x_lines = _projection_line_centers(work, axis="v", min_frac=0.38, step=2)

    def unscale_y(y: int) -> int:
        return int(round(y / scale)) if scale != 1.0 else y

    def unscale_x(x: int) -> int:
        return int(round(x / scale)) if scale != 1.0 else x

    row_bands: list[tuple[int, int, int, int]] = []
    min_gap = max(6, int(min_row_px * scale))
    max_gap = max(min_gap + 1, int(max_row_px * scale))
    for a, b in zip(y_lines, y_lines[1:]):
        gap = b - a
        if min_gap <= gap <= max_gap:
            y0 = unscale_y(a + 1)
            y1 = unscale_y(b)
            if y1 - y0 >= min_row_px:
                row_bands.append((0, y0, w, y1))

    col_xs = [unscale_x(x) for x in x_lines]
    return {
        "width": w,
        "height": h,
        "row_bands": row_bands,
        "h_lines": [unscale_y(y) for y in y_lines],
        "v_lines": col_xs,
        "grid_row_count": len(row_bands),
        "grid_col_count": max(0, len(col_xs) - 1),
    }


def _ocr_row_strip(row_im) -> str:
    from quote_core.ocr import ocr_available, tesseract_cmd

    if not ocr_available():
        return ""
    import pytesseract

    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd()
    # psm 7 = single text line (one BOM row).
    try:
        return pytesseract.image_to_string(row_im, config="--oem 3 --psm 7") or ""
    except Exception:  # noqa: BLE001
        try:
            return pytesseract.image_to_string(row_im, config="--oem 3 --psm 6") or ""
        except Exception:  # noqa: BLE001
            return ""


def _ocr_cell_strip(cell_im) -> str:
    from quote_core.ocr import ocr_available, tesseract_cmd

    if not ocr_available():
        return ""
    import pytesseract

    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd()
    try:
        return pytesseract.image_to_string(cell_im, config="--oem 3 --psm 8") or ""
    except Exception:  # noqa: BLE001
        return ""


def extract_bom_from_table_image(
    image: Any,
    *,
    bom_config: str | None = None,
    row_texts: list[str] | None = None,
) -> Any:
    """
    Segment a rendered LIST OF MATERIAL crop, then OCR each row (or use row_texts).

    ``row_texts`` is for fixtures when Tesseract is not installed: the segmenter
    still counts grid bands; the texts prove cell-line harvest (BB / 102727-4).
    """
    from quote_core.bom import BomResult

    im = _as_pil(image)
    seg = segment_table_bands(im)
    notes = [
        f"Bitmap table: {seg['grid_row_count']} row bands, "
        f"{seg['grid_col_count']} column bands"
    ]
    lines: list[str] = []
    if row_texts is not None:
        lines = [str(t) for t in row_texts if str(t).strip()]
        notes.append("Used supplied row texts (table-image fixture / desktop crop)")
    else:
        from quote_core.ocr import ocr_available

        if ocr_available() and seg["row_bands"]:
            v_lines = seg["v_lines"]
            use_cells = len(v_lines) >= 4
            for x0, y0, x1, y1 in seg["row_bands"]:
                pad = 1
                strip = im.crop((x0, max(0, y0 - pad), x1, min(im.height, y1 + pad)))
                if use_cells:
                    parts: list[str] = []
                    xs = [0] + v_lines + [im.width]
                    xs = sorted({x for x in xs if 0 <= x <= im.width})
                    for a, b in zip(xs, xs[1:]):
                        if b - a < 6:
                            continue
                        cell = im.crop((a + 1, max(0, y0), b, min(im.height, y1)))
                        parts.append(_ocr_cell_strip(cell).strip())
                    text = " ".join(p for p in parts if p)
                    if not text:
                        text = _ocr_row_strip(strip)
                else:
                    text = _ocr_row_strip(strip)
                if text and text.strip():
                    lines.append(text.strip())
            notes.append(f"OCR'd {len(lines)} row strips (not a whole-page dump)")
        elif not ocr_available():
            notes.append(
                "Tesseract unavailable — grid segmented but cells not read. "
                "Feed a table image crop via POST /api/jobs/{id}/bom-table-crop "
                "or POST /api/bom/table-image"
            )

    parsed = harvest_ocr_row_strips(lines, bom_config=bom_config)
    if not parsed.rows and lines:
        blob = "LIST OF MATERIAL\nQTY ITEM PART NO. DESCRIPTION\n" + "\n".join(lines)
        parsed = harvest_material_list_lines(blob, bom_config=bom_config)
    parsed.grid_row_count = int(seg["grid_row_count"])
    parsed.notes = notes + list(parsed.notes)
    if parsed.rows:
        parsed.method = "table_material_list_image"
    elif parsed.grid_row_count >= SHORT_TABLE_REJECT:
        parsed.method = "table_material_list_image"
        parsed.notes.append(
            f"Tall grid ({parsed.grid_row_count} bands) but cells unread — "
            f"flag review; do not use a nested 3-row LOM"
        )
    return parsed if (parsed.rows or parsed.grid_row_count) else BomResult(
        method=None,
        confidence=0.0,
        notes=notes or ["No table grid on image"],
        grid_row_count=int(seg["grid_row_count"]),
    )


def extract_bom_from_table_images(
    images: list[Any],
    *,
    bom_config: str | None = None,
    row_texts_by_image: list[list[str] | None] | None = None,
) -> Any:
    """Parse several rendered page clips and pick the tallest credible LOM."""
    from quote_core.bom import BomResult

    cands = []
    for i, im in enumerate(images):
        texts = None
        if row_texts_by_image and i < len(row_texts_by_image):
            texts = row_texts_by_image[i]
        one = extract_bom_from_table_image(im, bom_config=bom_config, row_texts=texts)
        one.notes = [f"Rendered table image {i + 1}/{len(images)}", *list(one.notes)]
        cands.append(one)
    best = pick_best_material_list(cands)
    if best is None:
        return BomResult(method=None, confidence=0.0, notes=["No table images parsed"])
    if len(best.rows) < TALL_TABLE_MIN_ROWS:
        best.notes.append(
            f"Best table-image hit has {len(best.rows)} parsed rows / "
            f"{best.grid_row_count} grid bands — do not claim a full 51-row live read"
        )
    return best


def render_page_right_strip(page, *, dpi: float = 220.0, left_frac: float = 0.68):
    """High-DPI right-side render (table lives on the weldment sheet)."""
    import fitz
    from PIL import Image

    rect = page.rect
    clip = fitz.Rect(
        rect.width * left_frac,
        rect.height * 0.03,
        rect.width * 0.998,
        rect.height * 0.92,
    )
    pix = page.get_pixmap(
        matrix=fitz.Matrix(dpi / 72.0, dpi / 72.0), clip=clip, alpha=False
    )
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def extract_bom_from_pdf_page_renders(
    pdf_path: Path | str,
    *,
    bom_config: str | None = None,
    dpi: float = 220.0,
) -> Any:
    """Render the right side of every page and pick the tallest grid."""
    import fitz

    from quote_core.bom import BomResult

    doc = fitz.open(str(pdf_path))
    images = []
    try:
        for page in doc:
            images.append(render_page_right_strip(page, dpi=dpi))
    finally:
        doc.close()
    if not images:
        return BomResult(method=None, confidence=0.0, notes=["PDF has no pages to render"])
    return extract_bom_from_table_images(images, bom_config=bom_config)
