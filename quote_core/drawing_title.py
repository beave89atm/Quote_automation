"""Extract the title / description from a top-level assembly drawing PDF."""

from __future__ import annotations

import re
from pathlib import Path

from quote_core.weight import _read_pdf_text

_SKIP_LINE = re.compile(
    r"(?i)^("
    r"THIS DRAWING|MANUFACTURING INC|DUPLICATION|PROHIBITED|MAC$|"
    r"PART\s*(NO|#)|WEIGHT:?|TRAILER MANUFACTURING|DRAWN:?|DATE:?|REVISION:?|"
    r"UNLESS OTHERWISE|ANGLES|PAGE\s+\d|REV\.?$|REASON FOR CHANGE|ECN|"
    r"DO NOT|SCALE|DRAWING$|SHEET\s+\d|TITLE:?|FINISH$|MATERIAL$|"
    r"DIMENSIONS ARE|TOLERANCES|FRACTIONAL|ANGULAR|DECIMAL|PROPRIETARY|"
    r"THE INFORMATION|REPRODUCTION|WITHOUT THE|AMTECH|RELEASED TO|"
    r"BLACK POWDER|N/A$|BY$|ITEM$|QTY|DESCRIPTION$|WEIGHT$|"
    r"DRAWING NUMBER|STOCKCODE|UNITS$|SIZE\s*[A-Z]?$|REV$|"
    r"MINIMUM WELD|K-FACTOR|BREAK SHARP|REMOVE ALL|FLAT PATTERNS|"
    r"THESE DRAWINGS|PART\s+DRAWING|ALL PROJECTED|THIRD ANGLE|"
    r"LINEAR\s+\d|HOLES\s*\+|BENDS\s+|WRAP ALL|VENDOR IS|"
    r"WWW\.|HTTP|ROSEDALE|CANADA\s+V\d|"
    r"CONSMETIC\s+SIDE|COSMETIC\s+SIDE|SECTION\s+[A-Z]-[A-Z]|DETAIL\s+[A-Z]|"
    r"DOWN\s+\d|T\.?S\.?C\.?$|TYP$|REVISIONS?$|CHECKED BY|DRAWN BY|"
    r"DRAWING RELEASED|UPDATED POSITIONS|STEEL MATERIALS|ALUMINUM MATERIALS|"
    r"DRAWING IS THE SOLE|SOLE PROPERTY|"
    r"THREE PLACE DECIMAL|PLACE DECIMAL|"
    r"TEST FIT WELDMENT|"
    r"CHECK OTHER OPTIONS|"
    r"ORDER\s+MATERIAL|"
    r"MARMON\s+KEYSTONE|"
    r"DWG\.?\s*NO\.?:?$|APPROVED:?$|QA$|MFG$|CHECKED$|DRAWN$"
    r")"
)

_VIEW_LABEL = re.compile(
    r"(?i)^(CONSMETIC|COSMETIC|SECTION|DETAIL|SCALE|VIEW|NOTE)\b"
)
_DIM_ONLY = re.compile(r"^[\d\s\.\-/\"'″×xX±°R,]+$")
_WEIGHT_LBM = re.compile(r"(?i)^\d+(\.\d+)?\s*(lbm|lbs?)\b")
_PART_NUM = re.compile(r"^\d{4,}(?:-\d+)?(?:_R\d+)?$", re.IGNORECASE)
_DATE = re.compile(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$|^\d{4}-\d{2}-\d{2}$")
_STOCK_OR_BOM = re.compile(
    r"(?i)^(GAUGE|P&O|HR\s|PLATE|BOLT|NUT|WASHER|SQ\s*IN)\b"
)
# Product titles like "PLATE - DOUBLER…" are not stock callouts.
_PRODUCT_PLATE_TITLE = re.compile(r"(?i)^PLATE\s*[-–—]")
_DRAWING_NUMBER_LABEL = re.compile(r"(?i)drawing\s*number")
# Title-block DRAWING NUMBER: 1511-5024 or assembly 35145-1
_DRAWING_NUMBER_TOKEN = re.compile(
    r"\b(\d{4}-\d{3,5}|\d{5,}-\d{1,3}[A-Za-z]?|\d{6,10})\b"
)
_TITLE_LABEL = re.compile(r"(?i)^TITLE:?$")
_TITLE_STOP = re.compile(
    r"(?i)^(DWG\s*NO|SIZE|SHEET|SCALE|REV|DRAWN|CHECKED|APPROVED|MATERIAL|"
    r"QTY|DESCRIPTION|UNITS|FINISH|WEIGHT|ITEM)\b"
)
# Cummins / NGFS confidentiality banners — never use as quote Description.
_LEGAL_OR_BANNER = re.compile(
    r"(?i)("
    r"this notice must appear|"
    r"\bconfidential\b|"
    r"proprietary and trade secret|"
    r"natural gas fuel|"
    r"^copyright\b|"
    r"^cummins clean fuel technologies$|"
    r"must be returned to cummins|"
    r"all rights reserved|"
    r"complete or partial reproduction|"
    r"drawing is the sole|"
    r"sole property of|"
    r"this drawing is the property|"
    r"three place decimal|"
    r"place decimal|"
    r"test fit weldment|"
    r"check other options|"
    r"order\s+material|"
    r"marmon\s+keystone|"
    r"dwg\.?\s*no"
    r")"
)


def _normalize_key(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


def extract_drawing_number_from_pdf_text(text: str) -> str | None:
    """Return the title-block DRAWING NUMBER when present (keeps dashes)."""
    if not text or not text.strip():
        return None
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for i, ln in enumerate(lines):
        if not _DRAWING_NUMBER_LABEL.search(ln):
            continue
        m = _DRAWING_NUMBER_TOKEN.search(ln)
        if m and not _DRAWING_NUMBER_LABEL.fullmatch(ln):
            return m.group(1)
        for j in range(i + 1, min(i + 5, len(lines))):
            nxt = lines[j]
            if _DRAWING_NUMBER_LABEL.search(nxt):
                break
            if _PART_NUM.fullmatch(nxt):
                return nxt
            m2 = _DRAWING_NUMBER_TOKEN.fullmatch(nxt)
            if m2:
                return m2.group(1)
            if len(nxt) <= 24:
                m3 = _DRAWING_NUMBER_TOKEN.search(nxt)
                if m3:
                    return m3.group(1)
    return None


def extract_drawing_number_from_pdf(path: Path) -> str | None:
    """Read a PDF and return its title-block DRAWING NUMBER when found."""
    try:
        text = _read_pdf_text(path)
    except Exception:  # noqa: BLE001
        return None
    return extract_drawing_number_from_pdf_text(text)


def _is_noise_line(s: str, *, key: str, key_norm: str, allow_plate_title: bool) -> bool:
    if not s:
        return True
    if _LEGAL_OR_BANNER.search(s):
        return True
    if _SKIP_LINE.match(s):
        return True
    if _VIEW_LABEL.match(s):
        return True
    if _DIM_ONLY.match(s) or _WEIGHT_LBM.match(s) or _DATE.match(s):
        return True
    if _PART_NUM.match(s):
        return True
    if key and (s == key or _normalize_key(s) == key_norm):
        return True
    if _STOCK_OR_BOM.match(s) and not (allow_plate_title and _PRODUCT_PLATE_TITLE.match(s)):
        return True
    if len(s) < 6 or len(s) > 120:
        return True
    return False


def _score_title_candidate(s: str, *, from_title_block: bool) -> tuple[int, int, int]:
    upper = s.upper()
    words = [w for w in re.split(r"\s+", s) if w]
    pts = 0
    if from_title_block:
        pts += 100
    if any(tok in upper for tok in (" ASM", "ASM,", "ASSEMBLY", "WELDMENT", "COUPLER")):
        pts += 50
    if is_nested_child_weldment_title(s):
        pts -= 80
    if is_drawing_boilerplate_title(s) or is_child_part_title(s):
        pts -= 80
    if any(
        tok in upper
        for tok in (
            "GUARD",
            "CHASSIS",
            "TRAILER",
            "FRAME",
            "BRACKET",
            "PLATE",
            "ARM",
            "PANEL",
            "DOUBLER",
            "CLOSEOUT",
            "PLATFORM",
            "DOOR",
        )
    ):
        pts += 30
    if len(words) >= 3:
        pts += 20
    if len(words) >= 4:
        pts += 10
    alpha = sum(1 for c in s if c.isalpha())
    pts += min(20, alpha // 2)
    return (pts, len(words), len(s))


def extract_title_from_pdf_text(text: str, *, part_key: str | None = None) -> str | None:
    """
    Best-effort drawing title (e.g. ``COUPLER ASM, 18-16, PNEUMATIC TANK``
    or ``PANEL - BACK, UPPER, 604 SERIES SM``).

    Prefers the TITLE title-block field over legal notices / BOM material rows.
    """
    if not text or not text.strip():
        return None

    key = (part_key or "").strip()
    key_norm = _normalize_key(key)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    scored: list[tuple[tuple[int, int, int], str]] = []

    i = 0
    while i < len(lines):
        s = lines[i]
        if re.match(r"^ITEM\b", s, re.IGNORECASE):
            i += 1
            continue
        if _TITLE_LABEL.match(s):
            block: list[str] = []
            j = i + 1
            while j < len(lines) and len(block) < 4:
                nxt = lines[j]
                if _TITLE_LABEL.match(nxt) or _TITLE_STOP.match(nxt):
                    break
                if _is_noise_line(nxt, key=key, key_norm=key_norm, allow_plate_title=True):
                    j += 1
                    continue
                if is_nested_child_weldment_title(nxt):
                    j += 1
                    continue
                block.append(nxt)
                j += 1
            has_parent = any(is_weldment_or_assembly_title(line) for line in block)
            parts: list[str] = []
            for nxt in block:
                if has_parent and is_child_part_title(nxt):
                    continue
                parts.append(nxt)
                if len(parts) >= 2:
                    break
            if parts:
                joined = " ".join(parts)
                scored.append((_score_title_candidate(joined, from_title_block=True), joined))
            i = j
            continue
        if _is_noise_line(s, key=key, key_norm=key_norm, allow_plate_title=False):
            i += 1
            continue
        scored.append((_score_title_candidate(s, from_title_block=False), s))
        i += 1

    if not scored:
        return None

    ranked = sorted(scored, key=lambda row: row[0], reverse=True)
    has_parent = any(is_weldment_or_assembly_title(row[1]) for row in scored)
    ranked = [
        row
        for row in ranked
        if not is_drawing_boilerplate_title(row[1])
        and not is_nested_child_weldment_title(row[1])
        and not (has_parent and is_child_part_title(row[1]))
    ]
    if not ranked:
        return None
    best_score, best = ranked[0]
    if best_score[0] < 20 and not any(
        tok in best.upper() for tok in ("ASM", "ASSEMBLY", "WELDMENT", "COUPLER", "PANEL")
    ):
        multi = [c for sc, c in scored if len(c.split()) >= 3]
        if multi:
            return sorted(
                multi,
                key=lambda c: _score_title_candidate(c, from_title_block=False),
                reverse=True,
            )[0][:200]
        return best[:200]
    return best[:200]


def resolve_assembly_drawing_paths(
    *,
    part_key: str,
    pdf_path: Path | None,
    library_folder: Path | str | None,
    related_pdf_names: list[str] | None = None,
) -> list[Path]:
    """Prefer the job PDF, then library PN.pdf / weldment packets."""
    key = (part_key or "").strip()
    if key.upper().startswith("PN "):
        key = key[3:].strip()
    key_norm = _normalize_key(key)
    paths: list[Path] = []
    seen: set[str] = set()

    def add(p: Path | None) -> None:
        if not p or not p.is_file():
            return
        rp = str(p.resolve())
        if rp in seen:
            return
        seen.add(rp)
        paths.append(p)

    folder = Path(library_folder) if library_folder else None
    # Always include the job PDF when present (stem may be 1510-9422_R01 while
    # part_key is 15109422R01).
    if pdf_path and pdf_path.is_file():
        add(pdf_path)
    if folder and folder.is_dir() and key:
        add(folder / f"{key}.pdf")
        # Also try dashed / undashed variants.
        if key_norm:
            try:
                for p in folder.iterdir():
                    if p.suffix.lower() != ".pdf":
                        continue
                    if _normalize_key(p.stem) == key_norm or _normalize_key(p.stem).startswith(
                        key_norm
                    ):
                        add(p)
            except OSError:
                pass
    if folder and folder.is_dir():
        for name in related_pdf_names or []:
            upper = name.upper()
            if key and (
                key in name or key_norm in _normalize_key(name)
            ) and any(h in upper for h in ("WELDMENT", "ALL DRAWING", "ASSEMBLY", "ASM")):
                add(folder / name)
    return paths


def title_from_library_folder(
    folder: Path | str | None,
    *,
    part_key: str | None = None,
) -> str | None:
    """``Pedestal Weldment - 1001898-1`` → ``PEDESTAL WELDMENT``."""
    if not folder:
        return None
    blob = str(folder).replace("\\", "/").rstrip("/")
    name = blob.rsplit("/", 1)[-1].strip()
    if not name:
        return None
    key = (part_key or "").strip()
    if key.upper().startswith("PN "):
        key = key[3:].strip()
    cleaned = name
    if key:
        cleaned = re.sub(
            rf"\s*[-–—]\s*{re.escape(key)}\s*$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        base = key.split("-")[0]
        if base:
            cleaned = re.sub(
                rf"\s*[-–—]\s*{re.escape(base)}\s*$",
                "",
                cleaned,
                flags=re.IGNORECASE,
            )
    cleaned = cleaned.strip(" -")
    if len(cleaned) < 4:
        return None
    if _PART_NUM.fullmatch(cleaned) or (key and _normalize_key(cleaned) == _normalize_key(key)):
        return None
    return re.sub(r"\s+", " ", cleaned).upper()


def is_drawing_boilerplate_title(text: str | None) -> bool:
    """True for title-block legal lines — never a quote Description."""
    s = str(text or "").strip()
    if not s:
        return False
    if _LEGAL_OR_BANNER.search(s):
        return True
    if _SKIP_LINE.match(s):
        return True
    upper = s.upper()
    if re.search(r"DWG\.?\s*NO", upper):
        return True
    return (
        "SOLE PROPERTY" in upper
        or "DRAWING IS THE SOLE" in upper
        or "THREE PLACE DECIMAL" in upper
        or "PLACE DECIMAL" in upper
        or "TEST FIT WELDMENT" in upper
        or upper.startswith("TEST FIT")
        or "CHECK OTHER OPTIONS" in upper
        or "ORDER MATERIAL" in upper
        or "MARMON KEYSTONE" in upper
    )


def is_weldment_or_assembly_title(text: str | None) -> bool:
    """True for a parent weldment/assembly noun — not a leftover plate."""
    if not text or is_nested_child_weldment_title(text):
        return False
    return bool(
        re.search(r"WELDMENT|ASSEMBLY|\bASSY\b|\bASM\b", str(text), re.I)
    )


def is_nested_child_weldment_title(text: str | None) -> bool:
    """True for nested GATE / REST / SUB-WELDMENT — never the quote header.

    Live 107877-1 stamped PLATFORM REST SUB-WELDMENT (child 105094). The
    assembly drawing title is PLATFORM WELDMENT WITHOUT JIB.
    """
    upper = f" {str(text or '').upper()} "
    if "SUB-WELDMENT" in upper or "SUB WELDMENT" in upper:
        return True
    if "WELDMENT" in upper and re.search(r"\b(GATE|REST)\b", upper):
        return True
    return False


def is_child_part_title(text: str | None) -> bool:
    """True for a child plate noun when a parent weldment title exists.

    Live 1020249-1 stamped BASE PLATE, PEDESTAL. Header is PEDESTAL WELDMENT.
    Live 11796-1 leftover: TURRET SIDE PLATE *is* the quote — callers must
    keep ``*PLATE*`` when no parent weldment/assembly title is present.
    Do not reject product titles like ``PLATE - DOUBLER``.
    """
    if is_nested_child_weldment_title(text):
        return True
    upper = f" {str(text or '').upper()} "
    # Live P001545: INNER FRAME PLATE / WELDMENT, FRAME PLATE, INNER is a child.
    # Header is POWER FRAME WELDMENT.
    if re.search(r"\bINNER\b", upper) and re.search(r"\bPLATE\b", upper):
        return True
    if re.search(r"\bWELDMENT\s*,\s*FRAME\s+PLATE\b", upper):
        return True
    if (
        "WELDMENT" in upper
        or "ASSEMBLY" in upper
        or re.search(r"\bASSY\b", upper)
        or re.search(r"\bASM\b", upper)
    ):
        return False
    return bool(
        re.search(
            r"\b(BASE|TOP|BOTTOM|SIDE|END|FLOOR|COVER)\s+PLATE\b",
            upper,
        )
    )


def title_from_exploded_names(names: list[str] | None) -> str | None:
    """Prefer a weldment/assembly noun from STEP / FileList names."""
    best: str | None = None
    best_pts = -1
    for raw in names or []:
        s = re.sub(r"[_\-]+", " ", str(raw or ""))
        s = re.sub(r"\s+", " ", s).strip()
        if not s or s.casefold() == "root" or is_drawing_boilerplate_title(s):
            continue
        s = re.sub(r"^\d{4,}(?:-\d+)?\s+", "", s).strip()
        if not s or is_drawing_boilerplate_title(s):
            continue
        if is_nested_child_weldment_title(s) or is_drawing_boilerplate_title(s):
            continue
        # Bare BB2000 ASM / BB1000-ASM tokens are job-PN or nested ASM, not
        # a bench/weldment header (live BB2000-ASM landed PN + DWG. NO.).
        if re.fullmatch(r"[A-Z0-9]+[\s_\-]+(?:ASM|ASSY)", s.upper()):
            continue
        if is_child_part_title(s):
            continue
        upper = s.upper()
        pts = 0
        if "WELDMENT" in upper:
            pts += 50
        if "ASSEMBLY" in upper or re.search(r"\bASM\b", upper):
            pts += 40
        if "PLATFORM" in upper or "DOOR" in upper:
            pts += 10
        if pts < 40:
            continue
        if pts > best_pts:
            best_pts = pts
            best = re.sub(r"\s+", " ", s).strip()[:200]
    return best


def title_from_stp_takeoff(takeoff: dict | None) -> str | None:
    """Weldment title from parsed STEP solids — not PDF boilerplate."""
    stp = (takeoff or {}).get("stp_summary") or {}
    names: list[str] = []
    for solid in stp.get("top_solids") or []:
        if isinstance(solid, dict):
            names.append(
                str(solid.get("name") or solid.get("part_no") or solid.get("label") or "")
            )
        elif solid:
            names.append(str(solid))
    for key in ("name", "title", "assembly_name"):
        val = stp.get(key)
        if val:
            names.append(str(val))
    return title_from_exploded_names(names)


def extract_assembly_description(
    *,
    part_key: str,
    pdf_path: Path | None = None,
    library_folder: Path | str | None = None,
    related_pdf_names: list[str] | None = None,
) -> str | None:
    """Read the top-level assembly drawing and return its title for quote Description."""
    for path in resolve_assembly_drawing_paths(
        part_key=part_key,
        pdf_path=pdf_path,
        library_folder=library_folder,
        related_pdf_names=related_pdf_names,
    ):
        try:
            text = _read_pdf_text(path)
        except Exception:  # noqa: BLE001
            continue
        title = extract_title_from_pdf_text(text, part_key=part_key)
        if title:
            return title
    return title_from_library_folder(library_folder, part_key=part_key)
