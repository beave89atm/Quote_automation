"""Nested LIST OF MATERIAL clips for weldment/assembly children.

Kyle drops only the top-level drawing. If a parent LOM description is a
weldment or assembly, retrieve that child's drawing from the Fort Worth
Engineering Customer Drawings library and clip its LOM too. Recurse.
Extra upload only when the child is not in the library.

Do **not** merge child rows into the parent BOM (later-sheet child tables
on the same PDF are still not this job's takeoff).
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

_NESTED_KIND_RE = re.compile(
    r"\b(?:WELDMENTS?|ASSEMBL(?:Y|IES)|ASSYS?)\b",
    re.IGNORECASE,
)
_MAX_NEST = 6


def is_weldment_or_assembly_desc(description: str | None) -> bool:
    """True when a LOM DESCRIPTION is a nested weldment / assembly."""
    return bool(_NESTED_KIND_RE.search(str(description or "")))


def nested_child_part_key(part_no: str | None) -> str:
    return re.sub(r"[^A-Z0-9-]", "", str(part_no or "").upper()).strip("-")


def nested_child_rows(bom: Any) -> list[Any]:
    """Parent LOM lines whose description is a weldment or assembly."""
    rows = list(getattr(bom, "rows", None) or [])
    out = []
    for row in rows:
        desc = getattr(row, "description", None)
        if desc is None and isinstance(row, dict):
            desc = row.get("description")
        pn = getattr(row, "part_no", None)
        if pn is None and isinstance(row, dict):
            pn = row.get("part_no")
        if is_weldment_or_assembly_desc(desc) and nested_child_part_key(str(pn or "")):
            out.append(row)
    return out


def _row_fields(row: Any) -> tuple[str, str, str]:
    if hasattr(row, "part_no"):
        return (
            str(row.item or ""),
            str(row.part_no or ""),
            str(row.description or ""),
        )
    return (
        str((row or {}).get("item") or ""),
        str((row or {}).get("part_no") or ""),
        str((row or {}).get("description") or ""),
    )


def _safe_pdf_name(part_no: str) -> str:
    token = nested_child_part_key(part_no) or "child"
    return f"{token}.pdf"


def clip_nested_child_loms(
    bom: Any,
    *,
    dest_dir: Path | str | None,
    library_folder: Path | str | None = None,
    related_pdf_names: list[str] | None = None,
    library_roots: list[Path] | None = None,
    nested_seen: set[str] | None = None,
    parent_part: str | None = None,
    depth: int = 0,
) -> Any:
    """Clip child weldment/assembly LOMs from the library. Parent rows stay."""
    from quote_core.drawing_library import find_part_pdf

    dest = Path(dest_dir) if dest_dir else None
    seen = set(nested_seen or [])
    parent_key = nested_child_part_key(parent_part)
    if parent_key:
        seen.add(parent_key)

    children = list(getattr(bom, "nested_children", None) or [])
    notes = list(getattr(bom, "notes", None) or [])
    if dest is None or depth >= _MAX_NEST:
        bom.notes = notes
        bom.nested_children = children
        return bom

    dest.mkdir(parents=True, exist_ok=True)
    for row in nested_child_rows(bom):
        item, part_no, desc = _row_fields(row)
        key = nested_child_part_key(part_no)
        if not key or key in seen:
            continue
        if parent_key and key == parent_key:
            continue
        seen.add(key)
        src = find_part_pdf(
            part_no,
            list(library_roots or []),
            library_folder=library_folder,
            related_pdf_names=related_pdf_names,
        )
        if src is None:
            note = (
                f"Child weldment {part_no} ({desc.strip() or 'WELDMENT'}) "
                f"not in library — extra upload needed"
            )
            if note not in notes:
                notes.append(note)
            children.append(
                {
                    "item": item,
                    "part_no": part_no,
                    "description": desc,
                    "status": "missing_upload",
                    "lom_xlsx": None,
                    "pdf": None,
                }
            )
            continue

        dest_pdf = dest / _safe_pdf_name(part_no)
        try:
            if src.resolve() != dest_pdf.resolve():
                shutil.copy2(src, dest_pdf)
            else:
                dest_pdf = src
        except OSError as exc:
            note = f"Could not copy child drawing {part_no} from library: {exc}"
            if note not in notes:
                notes.append(note)
            children.append(
                {
                    "item": item,
                    "part_no": part_no,
                    "description": desc,
                    "status": "copy_failed",
                    "lom_xlsx": None,
                    "pdf": str(src),
                }
            )
            continue

        from quote_core.bom import extract_bom

        child = extract_bom(
            pdf_path=dest_pdf,
            library_folder=library_folder,
            related_pdf_names=related_pdf_names,
            bom_config="",
            nested_seen=seen,
            nested_depth=depth + 1,
        )
        from quote_core.bom_xlsx import lom_sheet_name, row_as_lom_dict

        child_rows = [row_as_lom_dict(r) for r in (child.rows or [])]
        xlsx_name = child.lom_xlsx
        sheet_name = lom_sheet_name(part_no)
        status = "clipped" if child_rows else "no_lom"
        note = (
            f"Clipped child LOM {part_no} from library"
            if child_rows
            else f"Child {part_no} found in library but has no LIST OF MATERIAL"
        )
        if note not in notes:
            notes.append(note)
        children.append(
            {
                "item": item,
                "part_no": part_no,
                "description": desc,
                "status": status,
                "lom_xlsx": xlsx_name,
                "lom_sheet": sheet_name,
                "rows": child_rows,
                "pdf": dest_pdf.name,
                "piece_count": child.piece_count,
                "part_number_count": child.part_number_count,
                "nested_children": list(getattr(child, "nested_children", None) or []),
            }
        )
        for extra in child.notes:
            if (
                "extra upload" in extra.lower()
                or extra.startswith("Clipped child LOM")
                or extra.startswith("Child ")
            ) and extra not in notes:
                notes.append(extra)

    bom.notes = notes
    bom.nested_children = children
    return bom


def nested_review_notes(notes: list[str] | None) -> list[str]:
    """Job-flag notes for a clipped or missing child LOM."""
    out: list[str] = []
    for note in notes or []:
        text = str(note)
        low = text.lower()
        if (
            "extra upload" in low
            or text.startswith("Clipped child LOM")
            or text.startswith("Child ")
        ):
            out.append(text)
    return out


def notes_from_takeoff(takeoff: dict[str, Any] | None) -> list[str]:
    blob = takeoff or {}
    found: list[str] = []
    drivers = blob.get("fitup_drivers") or {}
    weight = drivers.get("weight_calc") or {}
    for source in (
        weight.get("bom"),
        weight.get("pdf_bom"),
        blob.get("bom"),
        blob.get("pdf_bom"),
    ):
        if isinstance(source, dict):
            found.extend(str(n) for n in (source.get("notes") or []))
    found.extend(str(n) for n in (drivers.get("notes") or []))
    found.extend(str(n) for n in (blob.get("flags") or []))
    return found
