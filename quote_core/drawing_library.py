"""Locate STP/STEP and related drawings on the office shared drive."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Job / assembly numbers: 80341805 or dashed 35145-1
_PART_TOKEN_RE = re.compile(r"\d{5,}(?:-\d+)?")
_NOISE_RE = re.compile(
    r"(?i)[\s_-]*(fab\s*packet|for\s*quoting|rev\s*[a-z0-9]+|drawing|dwg|all\s*drawings.*)$"
)


@dataclass
class DrawingMatch:
    part_key: str
    folder: Path | None = None
    stp_path: Path | None = None
    related_pdfs: list[Path] = field(default_factory=list)
    searched_roots: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "part_key": self.part_key,
            "folder": str(self.folder) if self.folder else None,
            "stp_path": str(self.stp_path) if self.stp_path else None,
            "stp_filename": self.stp_path.name if self.stp_path else None,
            "related_pdfs": [p.name for p in self.related_pdfs[:40]],
            "related_pdf_count": len(self.related_pdfs),
            "searched_roots": self.searched_roots,
            "notes": self.notes,
        }


def extract_part_key(*names: str | None) -> str | None:
    """Pull a part/assembly number from filenames or titles."""
    candidates: list[str] = []
    for raw in names:
        if not raw:
            continue
        stem = Path(str(raw)).stem
        stem = _NOISE_RE.sub("", stem).strip(" -_")
        for m in _PART_TOKEN_RE.finditer(stem):
            candidates.append(m.group(0))
        # Also accept bare alphanumeric stems like A078X022
        compact = re.sub(r"[^A-Za-z0-9]", "", stem)
        if len(compact) >= 5 and any(ch.isdigit() for ch in compact):
            candidates.append(compact)
    if not candidates:
        return None
    # Prefer dashed keys (35145-1) over bare (35145), then longer numeric.
    dashed = [c for c in candidates if "-" in c]
    if dashed:
        return max(dashed, key=len)
    numeric = [c for c in candidates if c.isdigit()]
    if numeric:
        return max(numeric, key=len)
    return max(candidates, key=len)


def _default_office_roots() -> list[Path]:
    """Guess the synced SharePoint path on each office PC."""
    home = Path.home()
    relative = Path("Fort Worth - Documents") / "Engineering" / "Customer Drawings"
    return [
        home / "Kannon Manufacturing Inc" / relative,
        home / "OneDrive - Kannon Manufacturing Inc" / relative,
    ]


def library_roots_from_config(raw_config: dict[str, Any] | None) -> list[Path]:
    roots: list[Path] = []
    env = os.environ.get("KANNON_DRAWING_LIBRARY")
    if env:
        for part in env.split(";"):
            part = part.strip()
            if part:
                roots.append(Path(part))
    lib = (raw_config or {}).get("drawing_library") or {}
    for item in lib.get("roots") or []:
        if item:
            roots.append(Path(str(item)))
    # Always consider standard synced locations so other PCs work without editing YAML.
    roots.extend(_default_office_roots())
    # Deduplicate while preserving order
    seen: set[str] = set()
    out: list[Path] = []
    for r in roots:
        key = str(r).lower()
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def _folder_score(folder: Path, part_key: str) -> int:
    name = folder.name
    if name == part_key:
        return 100
    if name.lower() == part_key.lower():
        return 95
    if name.startswith(part_key + "-") or name.startswith(part_key + " "):
        return 85
    if name.startswith(part_key):
        return 80
    if part_key in name:
        return 60
    # Bare key matches dashed folder: 35145 vs 35145-1
    base = part_key.split("-")[0]
    if base != part_key and (name == base or name.startswith(base + "-") or name.startswith(base)):
        return 75
    return 0


def _stp_name_matches(path: Path, part_key: str) -> bool:
    stem = path.stem
    if stem == part_key or stem.lower() == part_key.lower():
        return True
    if stem.lower().startswith(part_key.lower()):
        return True
    base = part_key.split("-")[0]
    if base and (stem == base or stem.lower().startswith(base.lower())):
        return True
    return False


def _list_stp_files(folder: Path) -> list[Path]:
    try:
        return [
            p
            for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in {".stp", ".step"}
        ]
    except OSError:
        return []


def _pick_stp(folder: Path, part_key: str) -> Path | None:
    steps = _list_stp_files(folder)
    if not steps:
        return None
    exact = [p for p in steps if _stp_name_matches(p, part_key)]
    pool = exact or steps
    # Prefer .stp over .step when tied; then shorter name.
    pool.sort(key=lambda p: (0 if p.suffix.lower() == ".stp" else 1, len(p.name), p.name.lower()))
    return pool[0]


def _find_stp_near_folder(folder: Path, part_key: str) -> Path | None:
    """
    Prefer STP inside the part folder; else matching STP in the parent
    (common Time layout: Time/35145-1.STEP next to Time/35145-1/*.pdf).
    """
    inside = _pick_stp(folder, part_key)
    if inside:
        return inside
    parent = folder.parent
    if not parent or not parent.exists():
        return None
    siblings = [p for p in _list_stp_files(parent) if _stp_name_matches(p, part_key)]
    if not siblings:
        return None
    siblings.sort(key=lambda p: (0 if p.suffix.lower() == ".stp" else 1, len(p.name), p.name.lower()))
    return siblings[0]


def _related_pdfs(folder: Path, primary_pdf_name: str | None = None) -> list[Path]:
    try:
        pdfs = sorted(
            (
                p
                for p in folder.iterdir()
                if p.is_file() and p.suffix.lower() == ".pdf"
            ),
            key=lambda p: p.name.lower(),
        )
    except OSError:
        return []
    if primary_pdf_name:
        primary = primary_pdf_name.lower()
        pdfs = [p for p in pdfs if p.name.lower() != primary]
    return pdfs


def find_drawings(
    part_key: str,
    roots: list[Path],
    *,
    primary_pdf_name: str | None = None,
) -> DrawingMatch:
    match = DrawingMatch(
        part_key=part_key,
        searched_roots=[str(r) for r in roots],
    )
    if not part_key:
        match.notes.append("No part number extracted from filename")
        return match

    existing_roots = [r for r in roots if r.exists()]
    if not existing_roots:
        match.notes.append("Drawing library path not found on this PC (check OneDrive sync)")
        return match

    # (score, folder, optional known stp)
    candidates: list[tuple[int, Path, Path | None]] = []
    for root in existing_roots:
        # Exact / near-exact folders one level under customer folders:
        # Customer Drawings / {Customer} / {Part}
        try:
            for customer in root.iterdir():
                if not customer.is_dir():
                    continue
                # Case: root/part
                score = _folder_score(customer, part_key)
                if score >= 60:
                    candidates.append((score, customer, None))
                try:
                    for child in customer.iterdir():
                        if child.is_dir():
                            score = _folder_score(child, part_key)
                            if score >= 60:
                                candidates.append((score, child, None))
                except OSError:
                    continue
        except OSError as exc:
            match.notes.append(f"Could not read {root}: {exc}")
            continue

        # Loose STEP files under a customer folder (Time/35145-1.STEP)
        try:
            for customer in root.iterdir():
                if not customer.is_dir():
                    continue
                for p in _list_stp_files(customer):
                    if not _stp_name_matches(p, part_key):
                        continue
                    # Prefer pairing with a matching subfolder when present
                    paired = None
                    try:
                        for child in customer.iterdir():
                            if child.is_dir() and _folder_score(child, part_key) >= 60:
                                paired = child
                                break
                    except OSError:
                        paired = None
                    if paired is not None:
                        # High score: folder + known sibling/parent STP
                        candidates.append((110, paired, p))
                    else:
                        candidates.append((105, customer, p))
        except OSError:
            continue

    if not candidates:
        match.notes.append(f"No folder or STP found for {part_key} under drawing library")
        return match

    # Prefer candidates that resolve to an STP, then higher score, then more PDFs.
    ranked: list[tuple[int, int, int, Path, Path | None]] = []
    for score, folder, known_stp in candidates:
        stp = known_stp or _find_stp_near_folder(folder, part_key)
        has_stp = 1 if stp else 0
        pdf_n = len(_related_pdfs(folder, primary_pdf_name=primary_pdf_name))
        ranked.append((has_stp, score, pdf_n, folder, stp))
    ranked.sort(key=lambda t: (-t[0], -t[1], -t[2], str(t[3]).lower()))
    _has_stp, _score, _pdf_n, folder, stp = ranked[0]

    match.folder = folder
    match.stp_path = stp
    # Merge component PDFs from all decent candidate folders (STP may live in a
    # short "Knuckle Weldment" folder while 21689.pdf sits in 21678-1).
    pdf_by_name: dict[str, Path] = {}
    for score, cand_folder, _known in candidates:
        if score < 60:
            continue
        for p in _related_pdfs(cand_folder, primary_pdf_name=primary_pdf_name):
            pdf_by_name.setdefault(p.name.lower(), p)
    match.related_pdfs = sorted(pdf_by_name.values(), key=lambda p: p.name.lower())
    if match.stp_path:
        where = "in folder" if match.stp_path.parent == folder else "beside folder"
        match.notes.append(f"Found STP on shared drive: {match.stp_path.name} ({where})")
    else:
        match.notes.append(f"Found folder {folder.name} but no STP/STEP inside or beside it")
    if match.related_pdfs:
        match.notes.append(f"{len(match.related_pdfs)} related PDF(s) in same folder")
    return match
