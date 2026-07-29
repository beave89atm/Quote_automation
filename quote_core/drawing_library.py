"""Locate STP/STEP and related drawings on the office shared drive."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Prefer longer numeric tokens (job / assembly numbers).
_PART_TOKEN_RE = re.compile(r"\d{5,}")
_NOISE_RE = re.compile(
    r"(?i)[\s_-]*(fab\s*packet|for\s*quoting|rev\s*[a-z0-9]+|drawing|dwg)$"
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
    # Prefer longest purely numeric token (typical Kannon/MAC job numbers).
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
    if name.startswith(part_key):
        return 80
    if part_key in name:
        return 60
    return 0


def _pick_stp(folder: Path, part_key: str) -> Path | None:
    steps = [
        p
        for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in {".stp", ".step"}
    ]
    if not steps:
        return None
    exact = [
        p
        for p in steps
        if p.stem == part_key or p.stem.lower().startswith(part_key.lower())
    ]
    pool = exact or steps
    # Prefer .stp over .step when tied; then shorter name.
    pool.sort(key=lambda p: (0 if p.suffix.lower() == ".stp" else 1, len(p.name), p.name.lower()))
    return pool[0]


def _related_pdfs(folder: Path, primary_pdf_name: str | None = None) -> list[Path]:
    pdfs = sorted(
        (
            p
            for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() == ".pdf"
        ),
        key=lambda p: p.name.lower(),
    )
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

    candidates: list[tuple[int, Path]] = []
    for root in existing_roots:
        # Exact / near-exact folders one level under customer folders:
        # Customer Drawings / {Customer} / {Part}
        try:
            for customer in root.iterdir():
                if not customer.is_dir():
                    # Loose files at root — skip for folder match
                    continue
                # Case: root/part
                if _folder_score(customer, part_key) >= 60:
                    candidates.append((_folder_score(customer, part_key), customer))
                try:
                    for child in customer.iterdir():
                        if child.is_dir():
                            score = _folder_score(child, part_key)
                            if score >= 60:
                                candidates.append((score, child))
                except OSError:
                    continue
        except OSError as exc:
            match.notes.append(f"Could not read {root}: {exc}")
            continue

        # Also: files named {part}.stp sitting under a customer folder (no part subfolder)
        try:
            for customer in root.iterdir():
                if not customer.is_dir():
                    continue
                for p in customer.iterdir():
                    if (
                        p.is_file()
                        and p.suffix.lower() in {".stp", ".step"}
                        and (p.stem == part_key or p.stem.lower().startswith(part_key.lower()))
                    ):
                        # Treat parent as the match folder
                        candidates.append((70, customer))
                        break
        except OSError:
            continue

    if not candidates:
        match.notes.append(f"No folder or STP found for {part_key} under drawing library")
        return match

    candidates.sort(key=lambda t: (-t[0], str(t[1]).lower()))
    folder = candidates[0][1]
    match.folder = folder
    match.stp_path = _pick_stp(folder, part_key)
    match.related_pdfs = _related_pdfs(folder, primary_pdf_name=primary_pdf_name)
    if match.stp_path:
        match.notes.append(f"Found STP on shared drive: {match.stp_path.name}")
    else:
        match.notes.append(f"Found folder {folder.name} but no STP/STEP inside")
    if match.related_pdfs:
        match.notes.append(f"{len(match.related_pdfs)} related PDF(s) in same folder")
    return match
