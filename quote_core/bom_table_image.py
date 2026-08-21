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
    expected_letters_for_bands,
    find_time_like_pn,
    flag_unread_qty_column,
    harvest_material_list_lines,
    harvest_ocr_row_strips,
    pick_best_material_list,
    union_sticky_harvest,
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


def _prepare_ocr_strip(row_im, *, scale: float = 1.0, invert: bool = False):
    from PIL import Image, ImageFilter, ImageOps

    im = row_im.convert("L")
    im = ImageOps.autocontrast(im)
    if invert:
        im = ImageOps.invert(im)
    if scale and scale != 1.0:
        w = max(1, int(im.width * scale))
        h = max(1, int(im.height * scale))
        im = im.resize((w, h), Image.Resampling.LANCZOS)
    im = im.filter(ImageFilter.SHARPEN)
    # Tesseract reads a thin strip more reliably with a white border.
    return ImageOps.expand(im, border=6, fill=255)


def _tesseract_string(row_im, *, psm: int) -> str:
    from quote_core.ocr import ocr_available, tesseract_cmd

    if not ocr_available():
        return ""
    import pytesseract

    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd()
    try:
        return pytesseract.image_to_string(row_im, config=f"--oem 3 --psm {psm}") or ""
    except Exception:  # noqa: BLE001
        return ""


def _ocr_row_strip(row_im) -> str:
    """First-pass line OCR. Keep this conservative so a successful band stays sticky."""
    text = _tesseract_string(row_im, psm=7)
    if find_time_like_pn(text):
        return text
    alt = _tesseract_string(row_im, psm=6)
    if find_time_like_pn(alt):
        return alt
    return text or alt


def _ocr_cell_strip(cell_im) -> str:
    h = getattr(cell_im, "height", 16) or 16
    scale = 3.0 if h < 20 else 2.0
    return _tesseract_string(_prepare_ocr_strip(cell_im, scale=scale), psm=8)


def _dedupe_windows(
    windows: list[tuple[int, int]], width: int, *, min_w: int = 8
) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for a, b in windows:
        key = (max(0, a), min(width, max(b, a + min_w)))
        if key in seen or key[1] <= key[0]:
            continue
        seen.add(key)
        out.append(key)
    return out


def left_qty_column_bounds(xs: list[int], width: int) -> list[tuple[int, int]]:
    """Candidate [x0, x1) windows for the left QTY column.

    Live 791587b missed most 1s and the 4/5/6/8s: the qty band is a small
    digit. Keep a thin first band (do not drop it for width < 6).
    """
    xs = sorted({int(x) for x in xs if 0 <= int(x) <= width})
    windows: list[tuple[int, int]] = []
    if not xs:
        return [(0, max(12, int(width * 0.12)))]
    first = xs[0] if xs[0] > 2 else (xs[1] if len(xs) > 1 else max(12, int(width * 0.12)))
    windows.append((0, max(first, 10)))
    if len(xs) >= 2:
        a, b = xs[0], xs[1]
        # Isolated digit OCR must not eat the ITEM column (V/W/AD).
        if 3 <= (b - a) <= 24:
            windows.append((max(0, a), b))
        elif (b - a) > max(36, int(width * 0.12)):
            windows.append((max(0, a), a + max(14, int((b - a) * 0.32))))
    windows.append((0, max(14, int(width * 0.10))))
    return _dedupe_windows(windows, width)


def qty_item_pipe_bounds(xs: list[int], width: int) -> list[tuple[int, int]]:
    """QTY + ITEM (+ start of PN) windows for pipe/glued OCR.

    Isolated single-char OCR misses live 1/2 and synthetic 4/6/8. A clip
    that still contains the item letter reads ``6V432710`` / ``8AD464440``.
    """
    xs = sorted({int(x) for x in xs if 0 <= int(x) <= width})
    windows: list[tuple[int, int]] = []
    if len(xs) >= 2:
        first = xs[0] if xs[0] > 2 else (xs[1] if len(xs) > 1 else 0)
        second = xs[1] if xs[0] > 2 else (xs[2] if len(xs) > 2 else first)
        windows.append((0, max(second, first + 16, 28)))
        if len(xs) >= 3:
            third = xs[2] if xs[0] > 2 else (xs[3] if len(xs) > 3 else second)
            windows.append((0, max(third, 48)))
    windows.append((0, max(36, int(width * 0.22))))
    windows.append((0, max(64, int(width * 0.40))))
    return _dedupe_windows(windows, width, min_w=16)


def leading_qty_before_item(text: str) -> str:
    """Leading 1–8 glued to an item letter. Never a PN stem. Never default 1.

    ``6V432710CAP`` / ``6 | V | 432710`` → 6. ``V432710`` / ``432710`` → empty.
    Qty 7 is dimension bleed.
    """
    import re

    raw = str(text or "").upper()
    if not raw.strip():
        return ""
    if "|" in raw:
        cells = [c.strip() for c in raw.split("|")]
        first = cells[0] if cells else ""
        if re.fullmatch(r"[1-8]", first) and first != "7":
            return first
        glued = re.fullmatch(r"([1-8])\s*([A-Z]{1,2})", first)
        if glued and glued.group(1) != "7":
            return glued.group(1)
    compact = re.sub(r"[^0-9A-Z]+", "", raw)
    match = re.match(r"([1-8])([A-Z]{1,2})", compact)
    if not match or match.group(1) == "7":
        return ""
    if match.group(2) in {"I", "O"}:
        return ""
    return match.group(1)


def _tesseract_whitelisted(im, *, psm: int, whitelist: str) -> str:
    from quote_core.ocr import ocr_available, tesseract_cmd

    if not ocr_available():
        return ""
    import pytesseract

    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd()
    try:
        return (
            pytesseract.image_to_string(
                im,
                config=(
                    f"--oem 3 --psm {psm} -c tessedit_char_whitelist={whitelist}"
                ),
            )
            or ""
        )
    except Exception:  # noqa: BLE001
        return _tesseract_string(im, psm=psm)


def _threshold_clip(im, thresh: int = 160):
    from PIL import ImageOps

    gray = ImageOps.autocontrast(im.convert("L"))
    return gray.point(lambda x: 0 if x < thresh else 255).convert("RGB")


def _trim_rule_ink(im):
    """Inset past full-span grid rules so the qty digit is not a black slab."""
    gray = im.convert("L")
    width, height = gray.size
    if width < 4 or height < 4:
        return im
    pix = gray.load()

    def col_frac(x: int) -> float:
        return sum(1 for y in range(height) if pix[x, y] < 128) / max(1, height)

    def row_frac(y: int) -> float:
        return sum(1 for x in range(width) if pix[x, y] < 128) / max(1, width)

    x0, x1, y0, y1 = 0, width, 0, height
    while x0 < width - 3 and col_frac(x0) >= 0.72:
        x0 += 1
    while x1 > x0 + 3 and col_frac(x1 - 1) >= 0.72:
        x1 -= 1
    while y0 < height - 3 and row_frac(y0) >= 0.72:
        y0 += 1
    while y1 > y0 + 3 and row_frac(y1 - 1) >= 0.72:
        y1 -= 1
    if x1 - x0 < 3 or y1 - y0 < 4:
        return im
    return im.crop((x0, y0, x1, y1))


def _ink_bbox(im, *, thresh: int = 150, pad: int = 2):
    gray = im.convert("L")
    width, height = gray.size
    pix = gray.load()
    xs: list[int] = []
    ys: list[int] = []
    for y in range(height):
        for x in range(width):
            if pix[x, y] < thresh:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return (
        max(0, min(xs) - pad),
        max(0, min(ys) - pad),
        min(width, max(xs) + pad + 1),
        min(height, max(ys) + pad + 1),
    )


def _isolate_qty_ink(cell_im):
    """Leftmost digit-sized ink only. Stop before the item letter."""
    trimmed = _trim_rule_ink(cell_im)
    gray = trimmed.convert("L")
    width, height = gray.size
    if width < 3 or height < 4:
        return trimmed
    pix = gray.load()
    min_ink = max(2, int(0.12 * height))
    col = [sum(1 for y in range(height) if pix[x, y] < 145) for x in range(width)]
    i = 0
    while i < width and col[i] < min_ink:
        i += 1
    if i >= width:
        return trimmed
    j = i
    while j < width and col[j] >= min_ink:
        j += 1
    k = j
    while k < width and k - j <= 3:
        if col[k] >= min_ink:
            j = k + 1
            while j < width and col[j] >= min_ink:
                j += 1
            k = j
            continue
        k += 1
    if (j - i) <= 2 and max(col[i:j] or [0]) >= 0.80 * height:
        rest = trimmed.crop((j, 0, width, height))
        return _isolate_qty_ink(rest) if rest.size[0] >= 3 else trimmed
    crop = trimmed.crop((max(0, i - 2), 0, min(width, j + 2), height))
    box = _ink_bbox(crop)
    return crop.crop(box) if box else crop


def _accept_qty_token(raw: str) -> str:
    """Single readable 1–8 (9 ok). Drop 0, 7, and 10–20 bleed. Do not invent 1."""
    digits = "".join(ch for ch in str(raw or "") if ch.isdigit())
    if not digits or digits == "0":
        return ""
    # psm 8 often appends a trailing 0 ("20", "40", "80").
    if len(digits) >= 2 and digits[1:] == "0" * (len(digits) - 1) and digits[0] in "12345689":
        digits = digits[0]
    if len(digits) > 1:
        n = int(digits[:2])
        if n == 7 or 10 <= n <= 20:
            return ""
        digits = digits[0]
    if digits == "7":
        return ""
    if digits in "12345689":
        return digits
    return ""


def _ocr_qty_digit(cell_im) -> str:
    """Isolated QTY cell — digits only. Do not default unread to 1."""
    from quote_core.ocr import ocr_available

    if not ocr_available() or cell_im is None:
        return ""
    isolated = _isolate_qty_ink(cell_im)
    if _ink_bbox(isolated) is None:
        return ""
    h = getattr(isolated, "height", 16) or 16
    scale = 8.0 if h < 20 else 5.0
    attempts = (
        (isolated, scale, False, 10),
        (_threshold_clip(isolated, 160), scale, False, 8),
        (isolated, scale, True, 10),
    )
    for src, sc, invert, psm in attempts:
        token = _accept_qty_token(
            _tesseract_whitelisted(
                _prepare_ocr_strip(src, scale=sc, invert=invert),
                psm=psm,
                whitelist="0123456789",
            )
        )
        if not token:
            continue
        if invert and token == "3":
            # Invert-only 3 is the live 8→3 hallucination.
            continue
        return token
    return ""


def _ocr_qty_via_pipe(clip) -> str:
    """QTY|ITEM|PN clip. Take a leading 1–8 only when an item letter follows."""
    import re

    from quote_core.ocr import ocr_available

    if not ocr_available() or clip is None:
        return ""
    whitelist = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-| "
    attempts = (
        (clip, 4.0, 7),
        (_threshold_clip(clip, 160), 5.0, 7),
        (clip, 5.0, 6),
    )
    for src, scale, psm in attempts:
        text = _tesseract_whitelisted(
            _prepare_ocr_strip(src, scale=scale, invert=False),
            psm=psm,
            whitelist=whitelist,
        )
        token = leading_qty_before_item(text)
        if token:
            return token
        compact = re.sub(r"[^0-9A-Z]+", "", str(text or "").upper())
        # Item letter then PN, no qty digit — cell is blank, stop.
        if re.match(r"[A-Z]{1,2}\d{4,}", compact):
            return ""
    return ""


def _crop_windows(im, y0: int, y1: int, bounds: list[tuple[int, int]]):
    width, height = im.size
    out = []
    for a, b in bounds:
        x0 = max(0, a - 2)
        x1 = min(width, b + 2)
        yy0 = max(0, y0 - 2)
        yy1 = min(height, y1 + 2)
        if x1 - x0 >= 3 and yy1 - yy0 >= 4:
            out.append(im.crop((x0, yy0, x1, yy1)))
    return out


def _crop_qty_windows(im, y0: int, y1: int, v_lines: list[int]):
    xs = [0] + list(v_lines or []) + [im.size[0]]
    return _crop_windows(im, y0, y1, left_qty_column_bounds(xs, im.size[0]))


def _crop_qty_item_windows(im, y0: int, y1: int, v_lines: list[int]):
    xs = [0] + list(v_lines or []) + [im.size[0]]
    return _crop_windows(im, y0, y1, qty_item_pipe_bounds(xs, im.size[0]))


def read_qty_cell(
    im,
    y0: int,
    y1: int,
    v_lines: list[int] | None = None,
    *,
    isolated: bool = True,
) -> str:
    """Read one row's QTY digit. Empty if unread. Never defaults to 1.

    Pipe-delimited QTY|ITEM|PN (digit glued to the item letter) is the
    read that actually recovers live 1/2 and V6/W4/Y4/AA5/AC4/AD8. Isolated
    thin-band OCR is last-pass only — a first-pass 1 must not stick and
    block a later pipe 4. Real 4–8 stay; 7 and 10–20 stay unread.
    """
    lines = list(v_lines or [])
    for clip in _crop_qty_item_windows(im, y0, y1, lines)[:2]:
        token = _ocr_qty_via_pipe(clip)
        if token:
            return token
    if not isolated:
        return ""
    for clip in _crop_qty_windows(im, y0, y1, lines)[:2]:
        token = _accept_qty_token(_ocr_qty_digit(clip))
        if token:
            return token
    return ""


def _expand_band_box(
    box: tuple[int, int, int, int],
    im_size: tuple[int, int],
    *,
    pad_x: int = 0,
    pad_y: int = 4,
) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box
    w, h = im_size
    return (
        max(0, x0 - pad_x),
        max(0, y0 - pad_y),
        min(w, x1 + pad_x),
        min(h, y1 + pad_y),
    )


def _ocr_band_retry(im, box: tuple[int, int, int, int], v_lines: list[int]) -> str:
    """Tight higher-scale clip for a truly empty band. Do not bleed into neighbors."""
    w, h = im.size
    x0, y0, x1, y1 = _expand_band_box(box, (w, h), pad_x=4, pad_y=1)
    clips = [
        im.crop((x0, y0, x1, y1)),
        im.crop((max(0, int(w * 0.28)), y0, x1, y1)),  # PART + DESC
        im.crop((max(0, int(w * 0.12)), y0, min(w, int(w * 0.78)), y1)),
    ]
    best = ""
    for clip in clips:
        for invert in (False, True):
            prepared = _prepare_ocr_strip(clip, scale=4.0, invert=invert)
            for psm in (7, 6, 13):
                text = _tesseract_string(prepared, psm=psm)
                if find_time_like_pn(text):
                    return text
                if len(text.strip()) > len(best.strip()):
                    best = text
    return best


def _ocr_first_pass_lines(im, seg: dict[str, Any], notes: list[str]) -> list[str]:
    """Conservative per-band OCR. A non-empty strip is sticky."""
    v_lines = seg.get("v_lines") or []
    use_cells = len(v_lines) >= 4
    lines: list[str] = []
    for x0, y0, x1, y1 in seg["row_bands"]:
        pad = 1
        strip = im.crop((x0, max(0, y0 - pad), x1, min(im.height, y1 + pad)))
        if use_cells:
            parts: list[str] = []
            xs = [0] + list(v_lines) + [im.width]
            xs = sorted({x for x in xs if 0 <= x <= im.width})
            first_cell = True
            for a, b in zip(xs, xs[1:]):
                # Live 791587b: thin QTY band was skipped (b-a < 6) and the
                # item letter became the "qty" cell. Keep the leftmost band.
                if b - a < 6 and not first_cell:
                    continue
                cell = im.crop((a, max(0, y0), max(b, a + 8), min(im.height, y1)))
                if first_cell:
                    first_cell = False
                    # Never put a letter/junk token in the QTY slot (that
                    # shipped live 0s as unread, or a defaulted 1). Blank
                    # stays blank until read_qty_cell sees a real digit.
                    parts.append(
                        read_qty_cell(im, y0, y1, v_lines, isolated=False)
                    )
                    continue
                parts.append(_ocr_cell_strip(cell).strip())
            # Keep empty QTY so parse sees a blank cell, not a default 1.
            text = " | ".join(parts)
            if not find_time_like_pn(text):
                blob = _ocr_row_strip(strip)
                if find_time_like_pn(blob):
                    text = blob
        else:
            text = _ocr_row_strip(strip)
            digit = read_qty_cell(im, y0, y1, v_lines, isolated=False)
            if digit:
                glued = leading_qty_before_item(text)
                if not glued:
                    text = f"{digit} | {text}" if text else digit
        lines.append((text or "").strip())
    notes.append(
        f"OCR'd {sum(1 for t in lines if t)}/{len(lines)} row strips "
        f"(empty bands kept as sequence holes)"
    )
    return lines


def _reread_qty_from_page(
    page,
    im,
    y0: int,
    y1: int,
    clip: dict[str, float],
) -> str:
    """Higher-DPI qty+item sliver from the PDF. Do not default unread to 1."""
    height = max(1, im.height)
    top = float(clip.get("top_frac", 0.03))
    bot = float(clip.get("bottom_frac", 0.92))
    left = float(clip.get("left_frac", 0.68))
    y0_frac = top + (y0 / height) * (bot - top)
    y1_frac = top + (y1 / height) * (bot - top)
    band = render_page_qty_item_band(
        page,
        y0_frac=y0_frac,
        y1_frac=y1_frac,
        dpi=420.0,
        left_frac=left,
    )
    return _ocr_qty_via_pipe(band) or _accept_qty_token(_ocr_qty_digit(band))


def _reread_unread_qty_cells(
    im,
    seg: dict[str, Any],
    lines: list[str],
    notes: list[str],
    *,
    retry_page: Any | None = None,
    retry_clip: dict[str, float] | None = None,
) -> list[str]:
    """Re-read QTY when the row has a PN but no clear qty digit.

    Isolate + threshold + higher-DPI / pipe QTY|ITEM|PN. Unread stays 0.
    """
    from quote_core.bom_table import parse_ocr_row_strip

    v_lines = seg.get("v_lines") or []
    out = list(lines)
    reread = 0
    still_unread = 0
    for i, text in enumerate(out):
        if not str(text or "").strip() or i >= len(seg.get("row_bands") or []):
            continue
        parsed = parse_ocr_row_strip(text)
        if not parsed:
            continue
        if parsed.get("qty_clear") and int(parsed.get("qty") or 0) > 0:
            continue
        _x0, y0, _x1, y1 = seg["row_bands"][i]
        digit = read_qty_cell(im, y0, y1, v_lines)
        if not digit and retry_page is not None:
            digit = _reread_qty_from_page(retry_page, im, y0, y1, retry_clip or {})
            if digit:
                notes.append(f"Re-read qty cell band {i} at 420 DPI: {digit}")
        digit = _accept_qty_token(digit)
        if not digit:
            still_unread += 1
            continue
        n = int(digit)
        if " | " in text:
            cells = text.split(" | ")
            cells[0] = str(n)
            out[i] = " | ".join(cells)
        else:
            out[i] = f"{n} {text}"
        notes.append(f"Re-read qty cell band {i}: {n}")
        reread += 1
    if reread:
        notes.append(f"Re-read {reread} unread QTY cell(s)")
    if still_unread:
        notes.append(
            f"{still_unread} QTY cell(s) still unread after re-read — "
            f"takeoff FAIL until digits match the grid (do not default to 1)"
        )
    return out


def _fill_empty_band_texts(
    im,
    seg: dict[str, Any],
    lines: list[str],
    notes: list[str],
    *,
    known_parts: set[str] | None = None,
) -> list[str]:
    """Re-clip truly empty bands only. Do not overwrite a harvested strip."""
    from quote_core.bom_table import parse_ocr_row_strip

    known = set(known_parts or ())
    v_lines = seg.get("v_lines") or []
    header_idxs = set()
    for i, raw in enumerate(lines):
        blob = str(raw or "").upper()
        if "PART" in blob and ("NO" in blob or "DESC" in blob or "TEM" in blob):
            header_idxs.add(i)
    expected = expected_letters_for_bands(
        len(lines), bottom_is_a=True, header_idxs=header_idxs
    )
    out = list(lines)
    retried = 0
    for i, text in enumerate(out):
        if str(text or "").strip() or i in header_idxs:
            continue
        retry = (_ocr_band_retry(im, seg["row_bands"][i], v_lines) or "").strip()
        letter = expected[i] or "?"
        parsed = parse_ocr_row_strip(retry) if retry else None
        pn = str(parsed.get("part_no") or "") if parsed else ""
        if pn and pn in known:
            notes.append(
                f"Re-OCR band {i} letter={letter}: ignored neighbor PN {pn} raw={retry}"
            )
            continue
        notes.append(f"Re-OCR band {i} letter={letter}: raw={retry or '(empty)'}")
        if retry:
            out[i] = retry
            retried += 1
            if pn:
                known.add(pn)
    if retried:
        notes.append(f"Re-clipped {retried} empty band(s) at higher scale")
    return out


def _retry_empty_bands_from_page(
    page,
    im,
    seg: dict[str, Any],
    lines: list[str],
    notes: list[str],
    *,
    top_frac: float = 0.03,
    bottom_frac: float = 0.92,
    known_parts: set[str] | None = None,
) -> list[str]:
    """Re-render truly empty bands from the PDF. Do not overwrite a sticky strip."""
    from quote_core.bom_table import parse_ocr_row_strip

    known = set(known_parts or ())
    h = max(1, im.height)
    header_idxs = set()
    for i, raw in enumerate(lines):
        blob = str(raw or "").upper()
        if "PART" in blob and ("NO" in blob or "DESC" in blob or "TEM" in blob):
            header_idxs.add(i)
    expected = expected_letters_for_bands(
        len(lines), bottom_is_a=True, header_idxs=header_idxs
    )
    for i, text in enumerate(lines):
        if str(text or "").strip() or i in header_idxs:
            continue
        if i >= len(seg["row_bands"]):
            continue
        _x0, y0, _x1, y1 = seg["row_bands"][i]
        y0_frac = top_frac + (y0 / h) * (bottom_frac - top_frac)
        y1_frac = top_frac + (y1 / h) * (bottom_frac - top_frac)
        band_im = render_page_row_band(
            page, y0_frac=y0_frac, y1_frac=y1_frac, dpi=320.0, left_frac=0.58
        )
        retry = (_ocr_band_retry(band_im, (0, 0, band_im.width, band_im.height), []) or "").strip()
        letter = expected[i] or "?"
        parsed = parse_ocr_row_strip(retry) if retry else None
        pn = str(parsed.get("part_no") or "") if parsed else ""
        if pn and pn in known:
            notes.append(
                f"Page re-clip band {i} letter={letter}: ignored neighbor PN {pn} raw={retry}"
            )
            continue
        notes.append(f"Page re-clip band {i} letter={letter}: raw={retry or '(empty)'}")
        if find_time_like_pn(retry):
            lines[i] = retry
            if pn:
                known.add(pn)
    return lines


def extract_bom_from_table_image(
    image: Any,
    *,
    bom_config: str | None = None,
    row_texts: list[str] | None = None,
    retry_page: Any | None = None,
    retry_clip: dict[str, float] | None = None,
    page_text: str | None = None,
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
    parsed = None
    if row_texts is not None:
        lines = [str(t or "") for t in row_texts]
        notes.append("Used supplied row texts (table-image fixture / desktop crop)")
        parsed = harvest_ocr_row_strips(lines, bom_config=bom_config, page_text=page_text)
    else:
        from quote_core.ocr import ocr_available

        if ocr_available() and seg["row_bands"]:
            first_lines = _ocr_first_pass_lines(im, seg, notes)
            first_lines = _reread_unread_qty_cells(
                im,
                seg,
                first_lines,
                notes,
                retry_page=retry_page,
                retry_clip=retry_clip,
            )
            first = harvest_ocr_row_strips(
                first_lines, bom_config=bom_config, page_text=page_text
            )
            known = {str(r.part_no) for r in first.rows if r.part_no}
            filled = _fill_empty_band_texts(
                im, seg, first_lines, notes, known_parts=known
            )
            if retry_page is not None:
                clip = retry_clip or {}
                filled = _retry_empty_bands_from_page(
                    retry_page,
                    im,
                    seg,
                    filled,
                    notes,
                    top_frac=float(clip.get("top_frac", 0.03)),
                    bottom_frac=float(clip.get("bottom_frac", 0.92)),
                    known_parts=known,
                )
            filled = _reread_unread_qty_cells(
                im,
                seg,
                filled,
                notes,
                retry_page=retry_page,
                retry_clip=retry_clip,
            )
            second = harvest_ocr_row_strips(
                filled, bom_config=bom_config, page_text=page_text
            )
            parsed = union_sticky_harvest(first, second)
            lines = filled
        else:
            if not ocr_available():
                notes.append(
                    "Tesseract unavailable — grid segmented but cells not read. "
                    "Feed a table image crop via POST /api/jobs/{id}/bom-table-crop "
                    "or POST /api/bom/table-image"
                )
            parsed = harvest_ocr_row_strips(
                lines, bom_config=bom_config, page_text=page_text
            )
    if not parsed.rows and lines:
        blob = "LIST OF MATERIAL\nQTY ITEM PART NO. DESCRIPTION\n" + "\n".join(lines)
        parsed = harvest_material_list_lines(blob, bom_config=bom_config)
    parsed.grid_row_count = int(seg["grid_row_count"])
    parsed.notes = notes + list(parsed.notes)
    parsed = flag_unread_qty_column(parsed)
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


def render_page_right_strip(
    page,
    *,
    dpi: float = 220.0,
    left_frac: float = 0.68,
    top_frac: float = 0.03,
    bottom_frac: float = 0.92,
):
    """High-DPI right-side render (table lives on the weldment sheet)."""
    import fitz
    from PIL import Image

    rect = page.rect
    clip = fitz.Rect(
        rect.width * left_frac,
        rect.height * top_frac,
        rect.width * 0.998,
        rect.height * bottom_frac,
    )
    pix = page.get_pixmap(
        matrix=fitz.Matrix(dpi / 72.0, dpi / 72.0), clip=clip, alpha=False
    )
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def render_page_qty_item_band(
    page,
    *,
    y0_frac: float,
    y1_frac: float,
    dpi: float = 420.0,
    left_frac: float = 0.68,
    right_frac: float = 0.86,
) -> Any:
    """High-DPI qty+item sliver. Used only to re-read an unread QTY cell."""
    import fitz
    from PIL import Image

    rect = page.rect
    pad = 0.002
    clip = fitz.Rect(
        rect.width * left_frac,
        rect.height * max(0.0, y0_frac - pad),
        rect.width * min(0.998, right_frac),
        rect.height * min(1.0, y1_frac + pad),
    )
    pix = page.get_pixmap(
        matrix=fitz.Matrix(dpi / 72.0, dpi / 72.0), clip=clip, alpha=False
    )
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def render_page_row_band(
    page,
    *,
    y0_frac: float,
    y1_frac: float,
    dpi: float = 320.0,
    left_frac: float = 0.58,
) -> Any:
    """Higher-DPI, slightly wider clip of one table band (P–Y holes)."""
    import fitz
    from PIL import Image

    rect = page.rect
    pad = 0.003
    clip = fitz.Rect(
        rect.width * left_frac,
        rect.height * max(0.0, y0_frac - pad),
        rect.width * 0.998,
        rect.height * min(1.0, y1_frac + pad),
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
