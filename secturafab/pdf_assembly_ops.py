"""Build a SecturaFAB assembly from component PDFs when STEP is unavailable.

Uses ``quickAddCAD`` with each component PDF (SecturaFAB extracts plate
geometry from the drawing), then links children under an Assembly root.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any

from quote_core.part_materials import PartMaterial, build_part_material_map, lookup_part_material

from .assembly_ops import ensure_assembly_root, relink_assembly_children  # noqa: F401
from .client import SecturaFabApiError, SecturaFabClient
from .component_ops import ensure_purchased_components, find_purchased_part_keys
from .profile_ops import (
    add_cad_plate_part,
    ensure_laser_profile_ops,
    format_hole_sizes,
    hole_sizes_from_takeoff,
    hole_sizes_from_text,
    plate_dims_from_takeoff,
    wait_for_quote_settle,
)
from .qty_ops import apply_bom_quantities, normalize_part_key
from .weld_ops import _desc_token

_ASSEMBLY_TYPE = 300


def _part_base(part_no: str) -> str:
    return re.split(r"[-–—]", str(part_no or ""), maxsplit=1)[0].strip()


def resolve_component_pdf(
    part_no: str,
    *,
    library_folder: Path | str | None,
    related_pdf_names: list[str] | None = None,
) -> Path | None:
    """Locate ``15644.pdf`` / ``15644-1.pdf`` for BOM part ``15644-1``."""
    folder = Path(library_folder) if library_folder else None
    if not folder or not folder.is_dir():
        return None
    base = _part_base(part_no)
    if not base:
        return None
    base_u = base.upper()
    candidates: list[Path] = []
    preferred_names = [
        f"{part_no}.pdf",
        f"{base}.pdf",
        f"{part_no}.dwg.pdf",
        f"{base}.dwg.pdf",
    ]
    for name in preferred_names:
        p = folder / name
        if p.is_file():
            return p
    for name in related_pdf_names or []:
        if base_u in Path(name).stem.upper().replace(" ", ""):
            p = folder / name
            if p.is_file():
                candidates.append(p)
    try:
        for p in folder.iterdir():
            if p.suffix.lower() != ".pdf":
                continue
            stem_u = p.stem.upper().replace(" ", "")
            if stem_u == base_u or stem_u.startswith(base_u + "-") or stem_u.startswith(
                base_u + "."
            ):
                candidates.append(p)
    except OSError:
        pass
    if not candidates:
        return None
    # Prefer exact base.pdf over longer names / duplicates.
    candidates.sort(key=lambda p: (0 if p.stem.upper() == base_u else 1, len(p.name), p.name.lower()))
    return candidates[0]


def create_assembly_shell(
    client: SecturaFabClient,
    quote_id: str,
    *,
    part_key: str,
    qty: int = 1,
    description: str | None = None,
) -> list[str]:
    """Insert a ProductType=Assembly root line when the quote has no items yet."""
    key = (part_key or "").strip()
    if key.upper().startswith("PN "):
        key = key[3:].strip()
    if not key:
        return ["No part key — skipped PDF assembly shell"]

    detail = client.get_json(f"v1/quote/{quote_id}")
    items = list(detail.get("ItemList") or [])
    existing = next(
        (
            it
            for it in items
            if it.get("ProductType") in (_ASSEMBLY_TYPE, "300", "assembly")
            or _desc_token(str(it.get("Description") or "")) == key
        ),
        None,
    )
    if existing:
        return [f"Assembly shell already present ({key})"]

    desc = (description or "").strip() or key
    shell = {
        "ID": str(uuid.uuid4()),
        "Description": desc[:500],
        "Quantity": max(1, int(qty)),
        "ProductType": _ASSEMBLY_TYPE,
        "IsPlate": False,
        "IsPart": False,
        "IsLinear": False,
        "IsAssembly": True,
        "Machine": None,
        "AssemblyLevel": 1,
        "AssemblyID": None,
        "AssemblyQty": 0,
        "OperationCostList": [],
    }
    detail["ItemList"] = items + [shell]
    save = client.request("POST", "v1/quote", json=detail)
    if save.status_code >= 400:
        return [f"Creating assembly shell failed ({save.status_code})"]
    return [f"Created Assembly shell for {key}" + (f" — {desc[:60]}" if desc != key else "")]


def quick_add_component_pdf(
    client: SecturaFabClient,
    *,
    quote_id: str,
    pdf_path: Path,
    material: str,
    thickness: str,
    machine: str = "Laser",
    qty: int = 1,
    memo: str = "",
    length: float | None = None,
    width: float | None = None,
    holes: list[float] | None = None,
) -> Any:
    """Import one component drawing via quickAddCAD (PDF / prt_pdf path).

    Pass length × width × hole sizes when known so Sectura's add-part
    calculators can attach Profile + laser time. Never graft ops after.
    """
    params: dict[str, Any] = {
        "quoteID": quote_id,
        "itemID": "00000000-0000-0000-0000-000000000000",
        "machine": machine,
        "material": material,
        "thickness": re.sub(r"(?i)\s*(inches|inch|in)\s*$", "", str(thickness or "").strip())
        .replace('"', "")
        .replace("″", "")
        .strip()
        or "0.25",
        "thickness_Units": "inch",
        "qty": max(1, int(qty)),
        "units": "inch",
        "memo": (memo or pdf_path.stem)[:240],
        "partMode": "Cad",
        "fileType": "prt_pdf",
    }
    if length:
        params["length"] = float(length)
    if width:
        params["width"] = float(width)
    hole_s = format_hole_sizes(holes)
    if hole_s:
        params["holes"] = hole_s
        params["holeSizes"] = hole_s
    with pdf_path.open("rb") as fh:
        return client.post_multipart(
            "v1/quoteOnline/quickAddCAD",
            files=[("files", (pdf_path.name, fh, "application/pdf"))],
            params=params,
        )


def _rename_imported_descriptions(
    client: SecturaFabClient,
    quote_id: str,
    *,
    part_nos: list[str],
) -> list[str]:
    """
    quickAddCAD names PDF imports like ``15644  - 1/4\" A36 …``.

    Rewrite Description to the BOM part number so qty/material matching works.
    """
    detail = client.get_json(f"v1/quote/{quote_id}")
    items = list(detail.get("ItemList") or [])
    unused = list(part_nos)
    changed = 0
    for it in items:
        if it.get("ProductType") in (_ASSEMBLY_TYPE, "300", "assembly"):
            continue
        token = normalize_part_key(_desc_token(str(it.get("Description") or "")))
        match = None
        for pn in unused:
            base = normalize_part_key(_part_base(pn))
            full = normalize_part_key(pn)
            if token == full or token == base or token.startswith(base):
                match = pn
                break
        if not match:
            continue
        unused.remove(match)
        if str(it.get("Description") or "").strip() != match:
            it["Description"] = match
            changed += 1
    if not changed:
        return []
    from .quote_update import update_item_fields

    ok = update_item_fields(client, quote_id, items, fields=["Description"])
    if not ok:
        return [
            "WARNING: Renaming PDF import descriptions via item-level update failed — "
            "not falling back to POST v1/quote (that wipes Cad Profile)"
        ]
    return [f"Set Description to BOM part number on {changed} PDF-imported item(s)"]


def _bom_description_map(bom_rows: list[dict[str, Any]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in bom_rows or []:
        key = normalize_part_key(row.get("part_no") or row.get("part_number") or "")
        if not key:
            continue
        desc = str(row.get("description") or "").strip()
        if desc:
            out[key] = desc
    return out


def categorize_pdf_imported_items(
    client: SecturaFabClient,
    quote_id: str,
    *,
    bom_rows: list[dict[str, Any]] | None = None,
    library_folder: Path | str | None = None,
    related_pdf_names: list[str] | None = None,
) -> list[str]:
    """
    Lesson 04: Cad (plate) / Linear (tube/bar) / Component (purchased).

    After rename, Description is often bare ``15863-1`` — use BOM description
    text (PIVOT TUBE, …) so Linear classification still works. When BOM text is
    empty, OCR the component PDF title block for TUBE/BAR hints.
    """
    from .push import classify_sectura_item

    detail = client.get_json(f"v1/quote/{quote_id}")
    items = list(detail.get("ItemList") or [])
    if not items:
        return ["No items to categorize"]

    bom_desc = _bom_description_map(list(bom_rows or []))
    # Fill empty BOM descriptions from OCR title text on component PDFs.
    for row in bom_rows or []:
        pn = str(row.get("part_no") or row.get("part_number") or "").strip()
        key = normalize_part_key(pn)
        if not key or bom_desc.get(key):
            continue
        pdf = resolve_component_pdf(
            pn,
            library_folder=library_folder,
            related_pdf_names=related_pdf_names,
        )
        if not pdf:
            continue
        try:
            from quote_core.ocr import ocr_pdf_pages

            ocr = ocr_pdf_pages(pdf, max_pages=1, dpi=180, only_when_sparse=False)
            text = str((ocr or {}).get("text") or "")
        except Exception:  # noqa: BLE001
            continue
        if not text.strip():
            continue
        bom_desc[key] = text[:240]
        upper = text.upper()
        if any(h in upper for h in ("TUBE", "ROUND BAR", "PIPE", "DOM ")):
            # Prefer a short token so classify_sectura_item matches Linear.
            bom_desc[key] = "TUBE " + bom_desc[key]

    counts = {"Cad": 0, "Linear": 0, "Component": 0}
    for it in items:
        if it.get("ProductType") in (_ASSEMBLY_TYPE, "300", "assembly"):
            continue
        token = normalize_part_key(_desc_token(str(it.get("Description") or "")))
        hint = f"{it.get('Description') or ''} {bom_desc.get(token, '')}"
        cat = classify_sectura_item(hint)
        counts[cat] = counts.get(cat, 0) + 1
        it["ItemType"] = cat
        it["Category"] = cat
        if cat == "Linear":
            it["IsLinear"] = True
            it["IsPlate"] = False
            it["IsPart"] = True
            it["Machine"] = None
        elif cat == "Component":
            it["IsLinear"] = False
            it["IsPlate"] = False
            it["IsPart"] = True
        else:
            it["IsLinear"] = False
            it["IsPlate"] = True
            it["IsPart"] = True

    from .quote_update import update_item_fields

    ok = update_item_fields(
        client,
        quote_id,
        items,
        fields=["ItemType", "Category", "IsLinear", "IsPlate", "IsPart"],
    )
    notes = [
        f"Categorized PDF imports — Cad: {counts['Cad']}, Linear: {counts['Linear']}, "
        f"Component: {counts['Component']} (lesson 04)"
    ]
    if not ok:
        notes.append(
            "WARNING: Category save via item-level update failed — "
            "not falling back to POST v1/quote (that wipes Cad Profile)"
        )
    elif counts["Linear"]:
        notes.append(
            "Linear tube/bar rows need stock size (OD/wall/length) reviewed in SecturaFAB"
        )
    return notes


def build_pdf_only_assembly(
    client: SecturaFabClient,
    *,
    quote_id: str,
    part_key: str,
    bom_rows: list[dict[str, Any]],
    library_folder: Path | str | None,
    related_pdf_names: list[str] | None,
    material: str,
    thickness: str,
    machine: str = "Laser",
    qty: int = 1,
    times: dict[str, Any] | None = None,
    extra_pdfs: list[Path] | None = None,
    takeoff: dict[str, Any] | None = None,
) -> list[str]:
    """
    Create assembly + import each BOM component PDF, then link under weldment.

    Mirrors lesson 04: Image/PDF components → New Line → Update Assembly.
    """
    del times  # weld/finalize run in push after this builder
    notes: list[str] = []
    rows = [r for r in bom_rows if int(r.get("qty") or 0) > 0 and (r.get("part_no") or r.get("part_number"))]
    if not rows:
        notes.append("WARNING: No BOM rows with qty>0 — cannot build PDF-only assembly")
        return notes

    notes.extend(create_assembly_shell(client, quote_id, part_key=part_key, qty=qty))

    part_materials = build_part_material_map(
        library_folder=library_folder,
        related_pdf_names=list(related_pdf_names or []),
        extra_pdfs=extra_pdfs,
    )

    imported: list[str] = []
    missing: list[str] = []
    for row in rows:
        part_no = str(row.get("part_no") or row.get("part_number") or "").strip()
        bom_q = max(1, int(row.get("qty") or 1))
        pdf = resolve_component_pdf(
            part_no,
            library_folder=library_folder,
            related_pdf_names=related_pdf_names,
        )
        if not pdf:
            missing.append(part_no)
            continue
        pm = lookup_part_material(part_materials, part_no)
        use_mat = pm.material if pm else material
        use_thk = (pm.thickness_param() if pm else None) or thickness
        row_holes = hole_sizes_from_text(str(row.get("description") or ""))
        if not row_holes and len(rows) == 1:
            row_holes = hole_sizes_from_takeoff(takeoff)
        try:
            quick_add_component_pdf(
                client,
                quote_id=quote_id,
                pdf_path=pdf,
                material=use_mat,
                thickness=use_thk,
                machine=machine,
                qty=bom_q,
                memo=part_no,
                holes=row_holes or None,
            )
            imported.append(f"{part_no}←{pdf.name}×{bom_q}")
        except SecturaFabApiError as exc:
            notes.append(f"WARNING: PDF import failed for {part_no} ({pdf.name}): {exc}")

    if imported:
        notes.append(f"Imported {len(imported)} component PDF(s) via quickAddCAD: {', '.join(imported)}")
        notes.append(
            "SecturaFAB filled flat Length×Width from each PDF plate outline "
            "(lesson 04 Image Files equivalent) — review Linear tubes for stock"
        )
    if missing:
        notes.append(
            "WARNING: Component PDF not found for BOM part(s): " + ", ".join(missing)
        )
    if not imported:
        notes.append("WARNING: No component PDFs imported — assembly has no children")
        return notes

    # Allow CAD geometry to finish before rename / assembly rollup.
    notes.extend(
        wait_for_quote_settle(
            client,
            quote_id,
            timeout_s=90.0,
            stable_s=8.0,
            min_wait_s=12.0,
        )
    )
    notes.extend(
        _rename_imported_descriptions(
            client,
            quote_id,
            part_nos=[str(r.get("part_no") or "") for r in rows],
        )
    )
    # Lesson 04: Cad / Linear / Component before assembly rollup.
    notes.extend(categorize_pdf_imported_items(
        client,
        quote_id,
        bom_rows=rows,
        library_folder=library_folder,
        related_pdf_names=related_pdf_names,
    ))
    # Shell was created before add-part. Do not convert a Cad line to Assembly
    # after quickAddCAD — that rewrite wipes Profile.
    purchased = find_purchased_part_keys(
        library_folder=library_folder,
        related_pdf_names=list(related_pdf_names or []),
        bom_rows=rows,
    )
    notes.extend(
        ensure_purchased_components(client, quote_id, purchased_keys=purchased)
    )
    notes.extend(relink_assembly_children(client, quote_id, part_key=part_key))
    if part_materials:
        notes.append(
            f"Read material/thickness from {len(part_materials)} component PDF(s) "
            f"(seeded on quickAddCAD — skipped UpdateItem_Part after add-part)"
        )
    notes.extend(
        apply_bom_quantities(
            client,
            quote_id,
            bom_rows=rows,
            part_key=part_key,
        )
    )
    notes.extend(
        ensure_laser_profile_ops(
            client,
            quote_id,
            material=material,
            thickness=thickness,
        )
    )
    # Re-link after qty/material settle — CAD rebuild can drop AssemblyID.
    notes.extend(relink_assembly_children(client, quote_id, part_key=part_key))
    notes.append(
        "PDF weldment built per lesson 04 — review Linear tubes/stock and any missing BOM rows"
    )
    return notes


def _apply_item_descriptions(
    client: SecturaFabClient,
    quote_id: str,
    *,
    description: str,
) -> list[str]:
    """Set Description on assembly + child lines from the drawing title."""
    desc = (description or "").strip()
    if not desc:
        return []
    detail = client.get_json(f"v1/quote/{quote_id}")
    items = list(detail.get("ItemList") or [])
    if not items:
        return []
    changed = 0
    for it in items:
        if str(it.get("Description") or "").strip() != desc:
            it["Description"] = desc[:500]
            changed += 1
    if not changed:
        return []
    from .quote_update import update_item_fields

    ok = update_item_fields(client, quote_id, items, fields=["Description"])
    if not ok:
        return [
            "WARNING: Setting item Descriptions via item-level update failed — "
            "not falling back to POST v1/quote (that wipes Cad Profile)"
        ]
    return [f"Set ItemList Description from drawing: {desc[:80]}"]


def build_single_pdf_quote(
    client: SecturaFabClient,
    *,
    quote_id: str,
    part_key: str,
    pdf_path: Path,
    material: str,
    thickness: str,
    machine: str = "Laser",
    qty: int = 1,
    description: str | None = None,
    takeoff: dict[str, Any] | None = None,
    length: float | None = None,
    width: float | None = None,
    holes: list[float] | None = None,
) -> list[str]:
    """
    Single-component PDF job (no STEP / no library BOM): one Cad line via the
    real add-part path (L×W×qty×holes) so Sectura attaches Profile + laser time.

    Falls back to quickAddCAD / prt_pdf when flat size is unknown. Never grafts
    OperationCostList. No Assembly parent row.
    """
    del description  # quote title only; do not overwrite CAD part Description
    notes: list[str] = []
    path = Path(pdf_path)
    if not path.is_file():
        notes.append(f"WARNING: Job PDF missing for single-PDF push: {pdf_path}")
        return notes

    key = (part_key or path.stem or "").strip()
    thk = re.sub(r"(?i)\s*(inches|inch|in)\s*$", "", str(thickness or "").strip())
    thk = thk.replace('"', "").replace("″", "").strip() or "0.25"

    if length is None or width is None:
        tl, tw = plate_dims_from_takeoff(takeoff)
        if length is None:
            length = tl
        if width is None:
            width = tw
    hole_list = list(holes or []) or hole_sizes_from_takeoff(takeoff)

    used_add_part = False
    if length and width:
        notes.extend(
            add_cad_plate_part(
                client,
                quote_id,
                material=material,
                thickness=thk,
                length=float(length),
                width=float(width),
                qty=qty,
                holes=hole_list or None,
                machine=machine,
                memo=key or path.stem,
            )
        )
        used_add_part = True
        notes.append(
            f"PDF add-part used job drawing {path.name} as reference "
            f"(CreateFile already uploaded) — single-part / no Assembly shell"
        )
    else:
        try:
            quick_add_component_pdf(
                client,
                quote_id=quote_id,
                pdf_path=path,
                material=material,
                thickness=thk,
                machine=machine,
                qty=qty,
                memo=key or path.stem,
                holes=hole_list or None,
            )
            notes.append(
                f"Imported job PDF via quickAddCAD/prt_pdf: {path.name} "
                f"({machine}, {material}, {thk}) — single-part / no Assembly shell"
            )
        except SecturaFabApiError as exc:
            notes.append(
                f"WARNING: quickAddCAD failed for job PDF ({path.name}): {exc}"
            )
            return notes

    notes.extend(
        wait_for_quote_settle(
            client,
            quote_id,
            timeout_s=60.0,
            stable_s=6.0,
            min_wait_s=8.0,
        )
    )
    # Verify shop Profile/Laser — never graft OperationCostList.
    notes.extend(
        ensure_laser_profile_ops(
            client,
            quote_id,
            material=material,
            thickness=thk,
            verify=True,
        )
    )
    notes.append(
        "Single-PDF part quote built (no Assembly shell) — confirm Profile + Laser time"
        + (" via add-part" if used_add_part else " via PDF import")
    )
    return notes
