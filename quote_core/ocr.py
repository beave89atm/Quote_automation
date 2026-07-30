"""OCR helpers for CAD/vector PDFs with little extractable text."""

from __future__ import annotations

import os
import shutil
from functools import lru_cache
from pathlib import Path
from typing import Any


def _candidate_tesseract_bins() -> list[Path]:
    env = os.environ.get("TESSERACT_CMD") or os.environ.get("KANNON_TESSERACT")
    out: list[Path] = []
    if env:
        out.append(Path(env))
    which = shutil.which("tesseract")
    if which:
        out.append(Path(which))
    out.extend(
        [
            Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        ]
    )
    # Deduplicate
    seen: set[str] = set()
    uniq: list[Path] = []
    for p in out:
        key = str(p).lower()
        if key not in seen:
            seen.add(key)
            uniq.append(p)
    return uniq


@lru_cache(maxsize=1)
def tesseract_cmd() -> str | None:
    for path in _candidate_tesseract_bins():
        if path.is_file():
            return str(path)
    return None


def ocr_available() -> bool:
    return tesseract_cmd() is not None


def ocr_pdf_pages(
    pdf_path: Path | str,
    *,
    max_pages: int = 4,
    dpi: int = 200,
    only_when_sparse: bool = True,
    sparse_text_chars: int = 200,
) -> dict[str, Any]:
    """
    Rasterize early PDF pages and OCR them.

    Returns:
      text: concatenated OCR text
      pages: per-page OCR snippets
      used: whether OCR ran
      error: optional error string
      engine: tesseract path when used
    """
    import fitz

    cmd = tesseract_cmd()
    if not cmd:
        return {
            "text": "",
            "pages": [],
            "used": False,
            "error": "Tesseract OCR not installed",
            "engine": None,
        }

    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        return {
            "text": "",
            "pages": [],
            "used": False,
            "error": f"OCR Python deps missing: {exc}",
            "engine": cmd,
        }

    pytesseract.pytesseract.tesseract_cmd = cmd
    pdf_path = Path(pdf_path)
    doc = fitz.open(str(pdf_path))
    try:
        native_chars = sum(len((page.get_text("text") or "").strip()) for page in doc)
        if only_when_sparse and native_chars >= sparse_text_chars:
            return {
                "text": "",
                "pages": [],
                "used": False,
                "error": None,
                "engine": cmd,
                "skipped": "native text sufficient",
                "native_text_chars": native_chars,
            }

        page_texts: list[dict[str, Any]] = []
        chunks: list[str] = []
        limit = min(len(doc), max(1, int(max_pages)))
        zoom = max(1.0, float(dpi) / 72.0)
        matrix = fitz.Matrix(zoom, zoom)
        for i in range(limit):
            page = doc[i]
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            config = "--oem 3 --psm 6"
            try:
                text = pytesseract.image_to_string(img, config=config) or ""
            except Exception:  # noqa: BLE001
                text = pytesseract.image_to_string(img) or ""
            text = text.strip()
            if text:
                page_texts.append({"page": i + 1, "text": text})
                chunks.append(f"--- OCR p{i+1} ---\n{text}")
        return {
            "text": "\n".join(chunks),
            "pages": page_texts,
            "used": bool(chunks),
            "error": None,
            "engine": cmd,
            "native_text_chars": native_chars,
            "pages_ocrd": limit,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "text": "",
            "pages": [],
            "used": False,
            "error": str(exc),
            "engine": cmd,
        }
    finally:
        doc.close()
