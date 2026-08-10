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

from .assembly_ops import ensure_assembly_root, relink_assembly_children
from .client import SecturaFabApiError, SecturaFabClient
from .component_ops import ensure_purchased_components, find_purchased_part_keys
from .profile_ops import apply_part_materials, ensure_laser_profile_ops, wait_for_quote_settle
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
) -> Any:
    """Import one component drawing via quickAddCAD (works with PDF as well as STEP)."""
    params = {
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
    }
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
    save = client.request("POST", "v1/quote", json=detail)
    if save.status_code >= 400:
        return [f"Renaming PDF import descriptions failed ({save.status_code})"]
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

    save = client.request("POST", "v1/quote", json=detail)
    notes = [
        f"Categorized PDF imports — Cad: {counts['Cad']}, Linear: {counts['Linear']}, "
        f"Component: {counts['Component']} (lesson 04)"
    ]
    if save.status_code >= 400:
        notes.append(
            f"Category save returned {save.status_code}; set Cad/Linear/Component "
            f"manually in SecturaFAB if needed"
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
    notes.extend(ensure_assembly_root(client, quote_id, part_key=part_key))

    purchased = find_purchased_part_keys(
        library_folder=library_folder,
        related_pdf_names=list(related_pdf_names or []),
        bom_rows=rows,
    )
    notes.extend(
        ensure_purchased_components(client, quote_id, purchased_keys=purchased)
    )
    # Same as UI "Update Assembly" — children under top-level weldment.
    notes.extend(relink_assembly_children(client, quote_id, part_key=part_key))

    if part_materials:
        notes.append(f"Read material/thickness from {len(part_materials)} component PDF(s)")
    notes.extend(
        apply_part_materials(
            client,
            quote_id,
            material=material,
            thickness=thickness,
            part_materials=part_materials,
            bom_rows=rows,
        )
    )
    notes.extend(
        wait_for_quote_settle(
            client,
            quote_id,
            timeout_s=120.0,
            stable_s=15.0,
            min_wait_s=45.0,
        )
    )
    # UpdateItem_Part CAD rebuild resets Description to ``15644  - 1/4" A36 …``
    # — restore BOM PNs / categories / assembly links before qty + Profile.
    notes.extend(
        _rename_imported_descriptions(
            client,
            quote_id,
            part_nos=[str(r.get("part_no") or "") for r in rows],
        )
    )
    notes.extend(
        categorize_pdf_imported_items(
            client,
            quote_id,
            bom_rows=rows,
            library_folder=library_folder,
            related_pdf_names=related_pdf_names,
        )
    )
    notes.extend(relink_assembly_children(client, quote_id, part_key=part_key))
    notes.extend(
        apply_bom_quantities(
            client,
            quote_id,
            bom_rows=rows,
            part_key=part_key,
        )
    )
    # Profile last — do NOT relink/full-quote POST after this (wipes OperationCostList).
    notes.extend(
        ensure_laser_profile_ops(
            client,
            quote_id,
            material=material,
            thickness=thickness,
        )
    )
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
    save = client.request("POST", "v1/quote", json=detail)
    if save.status_code >= 400:
        return [f"Setting item Descriptions failed ({save.status_code})"]
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
) -> list[str]:
    """
    Single-component PDF job (no STEP / no library BOM): one part line via
    quickAddCAD — lesson 01/03 Image Files path. No Assembly parent row.

    Leave CAD Description on the part (e.g. ``PN - 12 Ga A36 …``). Quote-level
    Description is set separately in push.create_quote.
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
        )
        notes.append(
            f"Imported job PDF via quickAddCAD: {path.name} "
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
    # Profile last — never relink/POST structure after this (wipes ops).
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
        "Single-PDF part quote built (no Assembly shell) — confirm Profile + dims"
    )
    return notes
