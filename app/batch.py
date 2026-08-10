"""Batch upload helpers — pair unrelated PDFs with optional STEPs by filename stem."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class PairedPart:
    stem: str
    pdf_name: str
    pdf_bytes: bytes
    stp_name: str | None = None
    stp_bytes: bytes | None = None


def file_stem_key(filename: str) -> str:
    """Case-insensitive stem used to pair PDF + STP."""
    return Path(filename).stem.strip().lower()


def pair_upload_files(
    files: list[tuple[str, bytes]],
) -> tuple[list[PairedPart], list[str]]:
    """
    Group multipart uploads by stem.

    Returns (paired_parts, skipped_messages).
    Orphan STPs are skipped (PDF required). Duplicate stems: last PDF/STP wins.
    """
    pdfs: dict[str, tuple[str, bytes]] = {}
    stps: dict[str, tuple[str, bytes]] = {}
    skipped: list[str] = []

    for name, data in files:
        if not name:
            skipped.append("Skipped unnamed upload")
            continue
        lower = name.lower()
        key = file_stem_key(name)
        if lower.endswith(".pdf"):
            pdfs[key] = (name, data)
        elif lower.endswith(".stp") or lower.endswith(".step"):
            stps[key] = (name, data)
        else:
            skipped.append(f"Skipped unsupported file: {name}")

    paired: list[PairedPart] = []
    for key, (pdf_name, pdf_bytes) in sorted(pdfs.items(), key=lambda kv: kv[1][0].lower()):
        stp_name, stp_bytes = (None, None)
        if key in stps:
            stp_name, stp_bytes = stps.pop(key)
        paired.append(
            PairedPart(
                stem=Path(pdf_name).stem,
                pdf_name=pdf_name,
                pdf_bytes=pdf_bytes,
                stp_name=stp_name,
                stp_bytes=stp_bytes,
            )
        )

    for _key, (stp_name, _) in sorted(stps.items(), key=lambda kv: kv[1][0].lower()):
        skipped.append(f"Skipped STP without matching PDF: {stp_name}")

    return paired, skipped


def paired_part_summary(part: PairedPart) -> dict[str, Any]:
    return {
        "stem": part.stem,
        "pdf": part.pdf_name,
        "stp": part.stp_name,
    }
