"""Batch upload helpers — pair PDF / DXF / STP by filename stem."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class PairedPart:
    stem: str
    pdf_name: str | None = None
    pdf_bytes: bytes | None = None
    dxf_name: str | None = None
    dxf_bytes: bytes | None = None
    stp_name: str | None = None
    stp_bytes: bytes | None = None


def file_stem_key(filename: str) -> str:
    """Case-insensitive stem used to pair PDF + DXF + STP."""
    return Path(filename).stem.strip().lower()


def _kind(name: str) -> str | None:
    lower = name.lower()
    if lower.endswith(".pdf"):
        return "pdf"
    if lower.endswith(".dxf"):
        return "dxf"
    if lower.endswith(".stp") or lower.endswith(".step"):
        return "stp"
    return None


def pair_upload_files(
    files: list[tuple[str, bytes]],
) -> tuple[list[PairedPart], list[str]]:
    """
    Group multipart uploads by stem.

    A job is created for each stem that has at least one of PDF / DXF / STP.
    Duplicate stems: last file of that kind wins.
    """
    by_key: dict[str, PairedPart] = {}
    skipped: list[str] = []

    for name, data in files:
        if not name:
            skipped.append("Skipped unnamed upload")
            continue
        kind = _kind(name)
        if kind is None:
            skipped.append(f"Skipped unsupported file: {name}")
            continue
        key = file_stem_key(name)
        part = by_key.get(key)
        if part is None:
            part = PairedPart(stem=Path(name).stem)
            by_key[key] = part
        if kind == "pdf":
            part.pdf_name = name
            part.pdf_bytes = data
        elif kind == "dxf":
            part.dxf_name = name
            part.dxf_bytes = data
        else:
            part.stp_name = name
            part.stp_bytes = data

    paired = sorted(by_key.values(), key=lambda p: p.stem.lower())
    return paired, skipped


def paired_part_summary(part: PairedPart) -> dict[str, Any]:
    return {
        "stem": part.stem,
        "pdf": part.pdf_name,
        "dxf": part.dxf_name,
        "stp": part.stp_name,
    }
