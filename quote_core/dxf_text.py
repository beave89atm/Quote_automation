"""Lightweight DXF text harvest — keywords only, no geometry engine."""

from __future__ import annotations

import re
from pathlib import Path

# ASCII DXF TEXT / MTEXT group code 1 (string value).
_DXF_STRING_RE = re.compile(
    r"(?im)^\s*1\s*\r?\n\s*(.+?)\s*$",
)


def extract_dxf_text(path: Path | str | None, *, max_chars: int = 20000) -> str:
    """
    Read printable strings from an ASCII DXF.

    Binary DXF / unreadable files return \"\" (caller should flag, not invent).
    """
    if not path:
        return ""
    p = Path(path)
    if not p.is_file():
        return ""
    try:
        raw = p.read_bytes()[: 2_000_000]
    except OSError:
        return ""
    if raw[:20].lower().startswith(b"autocad binary"):
        return ""
    try:
        text = raw.decode("latin-1", errors="ignore")
    except Exception:  # noqa: BLE001
        return ""
    hits = [m.group(1).strip() for m in _DXF_STRING_RE.finditer(text)]
    joined = "\n".join(h for h in hits if h and h not in {".", "0", "1"})
    # Also keep a slice of the raw ASCII for note keywords (LAYER names, etc.).
    blob = f"{joined}\n{text[:8000]}"
    return blob[:max_chars]
