"""Clip a printed Time LIST OF MATERIAL grid to LOM.xlsx, then stop.

Kyle (2026-08-24): the quote reads that sheet — no whole-page OCR/regex as
takeoff truth, no invented folder rows, no default unread qty to 1.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from quote_core.lom_xlsx import find_lom_xlsx, write_lom_xlsx

_LOM_TITLE_RE = re.compile(r"LIST\s+OF\s+MATERIAL", re.IGNORECASE)
_DASH_TOKEN_RE = re.compile(r"^-?[1-4]$")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().upper().replace(".", ""))


def cluster_word_rows(words: list[dict[str, Any]], y_tol: float = 8.0) -> list[list[dict[str, Any]]]:
    if not words:
        return []
    ordered = sorted(words, key=lambda w: (float(w["y0"]), float(w["x0"])))
    rows: list[list[dict[str, Any]]] = []
    cur = [ordered[0]]
    cur_y = float(ordered[0]["y0"])
    for w in ordered[1:]:
        y0 = float(w["y0"])
        if abs(y0 - cur_y) <= y_tol:
            cur.append(w)
            cur_y = (cur_y * (len(cur) - 1) + y0) / len(cur)
        else:
            rows.append(sorted(cur, key=lambda z: float(z["x0"])))
            cur = [w]
            cur_y = y0
    if cur:
        rows.append(sorted(cur, key=lambda z: float(z["x0"])))
    return rows


def merge_row_tokens(words: list[dict[str, Any]], gap: float = 12.0) -> list[dict[str, Any]]:
    """Join horizontally adjacent words (``PART`` + ``NO.`` → ``PART NO.``)."""
    if not words:
        return []
    ordered = sorted(words, key=lambda w: float(w["x0"]))
    out = [dict(ordered[0])]
    for w in ordered[1:]:
        prev = out[-1]
        if float(w["x0"]) - float(prev["x1"]) <= gap:
            prev["text"] = f"{prev['text']} {w['text']}".strip()
            prev["x1"] = max(float(prev["x1"]), float(w["x1"]))
            prev["y1"] = max(float(prev.get("y1") or 0), float(w.get("y1") or 0))
        else:
            out.append(dict(w))
    return out


def _header_score(tokens: list[dict[str, Any]]) -> int:
    score = 0
    texts = [_norm(t.get("text") or "") for t in tokens]
    joined = " ".join(texts)
    if _LOM_TITLE_RE.search(joined):
        score += 2
    for raw in texts:
        if raw in {"ITEM", "PART", "PART NO", "DESCRIPTION", "QTY"}:
            score += 2
    dash_n = sum(1 for t in tokens if _DASH_TOKEN_RE.match((t.get("text") or "").strip()))
    if dash_n >= 2:
        score += 3
    if "ITEM" in texts and any(t.startswith("PART") for t in texts):
        score += 3
    return score


def _is_header_row(tokens: list[dict[str, Any]]) -> bool:
    return _header_score(tokens) >= 4


def words_to_grid(words: list[dict[str, Any]]) -> list[list[str]]:
    """Rebuild the printed LOM cells from positioned words (clip, not page regex)."""
    if not words:
        return []
    clustered = cluster_word_rows(words)
    token_rows = [merge_row_tokens(row) for row in clustered]
    header_idx = None
    best = -1
    for i, tokens in enumerate(token_rows):
        score = _header_score(tokens)
        if score > best:
            best = score
            header_idx = i
    if header_idx is None or best < 4:
        return []
    header = token_rows[header_idx]
    col_xs = [((float(t["x0"]) + float(t["x1"])) / 2.0) for t in header]
    headers = [(t.get("text") or "").strip() for t in header]
    if not col_xs:
        return []

    def _assign(token: dict[str, Any]) -> int:
        cx = (float(token["x0"]) + float(token["x1"])) / 2.0
        return min(range(len(col_xs)), key=lambda i: abs(cx - col_xs[i]))

    grid = [headers]
    for i, tokens in enumerate(token_rows):
        if i == header_idx:
            continue
        if _is_header_row(tokens) or _LOM_TITLE_RE.search(
            " ".join(t.get("text") or "" for t in tokens)
        ):
            continue
        cells = [""] * len(headers)
        for tok in tokens:
            idx = _assign(tok)
            text = (tok.get("text") or "").strip()
            if not text:
                continue
            cells[idx] = f"{cells[idx]} {text}".strip() if cells[idx] else text
        if any(cells):
            grid.append(cells)
    return grid


def page_has_lom_grid_text(text: str | None) -> bool:
    blob = text or ""
    if _LOM_TITLE_RE.search(blob):
        return True
    upper = blob.upper()
    return ("ITEM" in upper and "PART" in upper) and (
        "-1" in blob or "QTY" in upper
    )


def _fitz_words(page) -> list[dict[str, Any]]:
    words: list[dict[str, Any]] = []
    for w in page.get_text("words") or []:
        if len(w) < 5:
            continue
        text = str(w[4] or "").strip()
        if not text:
            continue
        words.append(
            {
                "text": text,
                "x0": float(w[0]),
                "y0": float(w[1]),
                "x1": float(w[2]),
                "y1": float(w[3]),
            }
        )
    return words


def _ocr_words(page, clip) -> list[dict[str, Any]]:
    from quote_core.bom import _ocr_words_in_clip

    return _ocr_words_in_clip(page, clip, dpi=400)


def detect_lom_table_words(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep words in the printed grid; drop left-side paint notes like ``20 PLCS``."""
    if not words:
        return []
    clustered = cluster_word_rows(words)
    token_rows = [merge_row_tokens(row) for row in clustered]
    header = None
    best = -1
    for tokens in token_rows:
        score = _header_score(tokens)
        if score > best:
            best = score
            header = tokens
    if header is None or best < 4:
        title_x = None
        for tokens in token_rows:
            joined = " ".join(t.get("text") or "" for t in tokens)
            if _LOM_TITLE_RE.search(joined):
                title_x = min(float(t["x0"]) for t in tokens)
                break
        if title_x is None:
            return []
        return [w for w in words if float(w["x0"]) >= title_x - 15]
    x0 = min(float(t["x0"]) for t in header) - 18
    x1 = max(float(t["x1"]) for t in header) + 120
    return [w for w in words if float(w["x1"]) >= x0 and float(w["x0"]) <= x1]


def clip_lom_grid_from_page(page) -> tuple[list[list[str]], list[str]]:
    """Return a LOM cell grid from one PDF page (native words, else OCR of the clip)."""
    notes: list[str] = []
    words = _fitz_words(page)
    table = detect_lom_table_words(words)
    grid = words_to_grid(table) if table else []
    if grid:
        notes.append("Clipped LIST OF MATERIAL grid from native PDF words")
        return grid, notes

    rect = page.rect
    # Time LOM is the right-side title-block table (headers often at the bottom).
    import fitz

    clips = [
        fitz.Rect(rect.width * 0.52, rect.height * 0.28, rect.width * 0.995, rect.height * 0.97),
        fitz.Rect(rect.width * 0.58, rect.height * 0.38, rect.width * 0.995, rect.height * 0.96),
    ]
    from quote_core.ocr import ocr_available

    if not ocr_available():
        if page_has_lom_grid_text(page.get_text("text") or ""):
            notes.append(
                "LIST OF MATERIAL title found but native words were too sparse "
                "to clip, and Tesseract is not installed"
            )
        return [], notes
    for clip in clips:
        ocr_words = _ocr_words(page, clip)
        table = detect_lom_table_words(ocr_words)
        grid = words_to_grid(table) if table else words_to_grid(ocr_words)
        if grid and len(grid) > 1:
            notes.append("Clipped LIST OF MATERIAL grid from OCR of the printed table")
            return grid, notes
    return [], notes


def pdf_has_lom_grid(pdf_path: Path | str | None) -> bool:
    if not pdf_path:
        return False
    path = Path(pdf_path)
    if not path.is_file():
        return False
    try:
        import fitz

        doc = fitz.open(str(path))
    except Exception:  # noqa: BLE001
        return False
    try:
        for page in doc:
            text = page.get_text("text") or ""
            if page_has_lom_grid_text(text):
                return True
            words = _fitz_words(page)
            if detect_lom_table_words(words):
                return True
    finally:
        doc.close()
    return False


def clip_lom_grid_from_pdf(pdf_path: Path | str) -> tuple[list[list[str]], list[str]]:
    import fitz

    path = Path(pdf_path)
    doc = fitz.open(str(path))
    notes: list[str] = []
    try:
        for page in doc:
            grid, page_notes = clip_lom_grid_from_page(page)
            notes.extend(page_notes)
            if grid and len(grid) > 1:
                return grid, notes
    finally:
        doc.close()
    return [], notes


def _safe_part_stem(part_key: str | None, pdf_path: Path | None) -> str:
    raw = (part_key or "").strip() or (pdf_path.stem if pdf_path else "drawing")
    raw = re.sub(r"[^\w.\-]+", "-", raw).strip("-") or "drawing"
    return raw


def ensure_lom_xlsx(
    pdf_path: Path | str | None,
    *,
    library_folder: Path | str | None = None,
    part_key: str | None = None,
    bom_config: str | None = None,
) -> tuple[Path | None, list[str]]:
    """
    First BOM step: reuse a Kyle ``*LOM.xlsx`` or clip the printed grid to one.

    ``bom_config`` is unused here — the workbook keeps every dash column; the
    reader selects ``-1`` later.
    """
    del bom_config
    notes: list[str] = []
    pdf = Path(pdf_path) if pdf_path else None
    extra = pdf.parent if pdf and pdf.exists() else None
    existing = find_lom_xlsx(library_folder, extra, part_key=part_key)
    if existing:
        notes.append(f"Using Kyle-confirmed LOM workbook {existing.name}")
        return existing, notes
    if not pdf or not pdf.is_file():
        return None, notes
    try:
        grid, clip_notes = clip_lom_grid_from_pdf(pdf)
    except Exception as exc:  # noqa: BLE001
        notes.append(f"WARNING: LOM grid clip failed: {exc}")
        return None, notes
    notes.extend(clip_notes)
    if not grid or len(grid) < 2:
        if pdf_has_lom_grid(pdf):
            notes.append(
                "LIST OF MATERIAL grid exists but clip produced no rows — "
                "refusing whole-page OCR as takeoff truth"
            )
        return None, notes
    dest_dir = extra if extra and extra.is_dir() else pdf.parent
    dest = dest_dir / f"{_safe_part_stem(part_key, pdf)}-LOM.xlsx"
    try:
        write_lom_xlsx(dest, grid)
    except OSError as exc:
        notes.append(f"WARNING: Could not write {dest.name}: {exc}")
        return None, notes
    notes.append(f"Wrote clipped LIST OF MATERIAL grid to {dest.name}")
    return dest, notes
