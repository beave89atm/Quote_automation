"""Push Kannon quote jobs into SecturaFAB (create quote + upload drawings/STEP)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quote_core.drawing_library import extract_part_key

from .assembly_ops import ensure_assembly_root, relink_assembly_children
from .client import SecturaFabApiError, SecturaFabClient
from .component_ops import ensure_purchased_components, find_purchased_part_keys
from .finalize_ops import finalize_quote_ops
from .profile_ops import (
    apply_part_materials,
    ensure_laser_profile_ops,
    wait_for_quote_settle,
)
from .qty_ops import apply_bom_quantities, extract_bom_rows
from .quotes import QuoteService
from .weld_ops import ensure_weld_ops
from quote_core.drawing_title import extract_assembly_description
from quote_core.part_materials import build_part_material_map


def _pn_quote_number(part_key: str) -> str:
    """SecturaFAB quote number as 'PN {part}' with no revision suffix."""
    key = (part_key or "").strip()
    if not key:
        return ""
    if key.upper().startswith("PN "):
        return f"PN {key[3:].strip()}"
    return f"PN {key}"


_LINEAR_HINTS = (
    "TUBE",
    "PIPE",
    "CHANNEL",
    "BAR",
    "BEAM",
    "ANGLE",
    "RECT TUBE",
    "HSS",
    "STRUCTURAL",
)
_COMPONENT_HINTS = (
    "BOLT",
    "SCREW",
    "NUT",
    "WASHER",
    "HARDWARE",
    "FASTENER",
    "RIVET",
    "CLAMP",
    "KINGPIN",
    "KING PIN",
    "COTTER",
    "BUSHING",
    "BEARING",
    "PURCHASED",
    "BUYOUT",
    "BUY OUT",
)


def classify_sectura_item(description: str) -> str:
    """
    Map a STEP/BOM description to SecturaFAB item category dropdown values:
    Cad | Linear | Component

    Component = purchased / not made in-house (hardware, king pins, …).
    """
    text = f" {str(description or '').upper()} "
    # Collapse spaces so "KING PIN" and "KINGPIN" both match.
    compact = text.replace(" ", "")
    if "KINGPIN" in compact:
        return "Component"
    if any(h in text for h in _COMPONENT_HINTS):
        return "Component"
    if any(h in text for h in _LINEAR_HINTS):
        return "Linear"
    return "Cad"


@dataclass
class PushResult:
    ok: bool
    quote_id: str | None = None
    quote_number: str | None = None
    quote_request_id: str | None = None
    created_new_quote: bool = False
    uploaded_files: list[str] = field(default_factory=list)
    item_count: int | None = None
    notes: list[str] = field(default_factory=list)
    error: str | None = None
    # True when Profile/Weld/qty finalize finished without WARNING notes.
    ready: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "quote_id": self.quote_id,
            "quote_number": self.quote_number,
            "quote_request_id": self.quote_request_id,
            "created_new_quote": self.created_new_quote,
            "uploaded_files": self.uploaded_files,
            "item_count": self.item_count,
            "notes": self.notes,
            "error": self.error,
            "ready": self.ready,
        }


def _mime_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "application/pdf"
    if suffix in {".stp", ".step"}:
        return "application/octet-stream"
    if suffix in {".dxf", ".dwg"}:
        return "application/octet-stream"
    return "application/octet-stream"


def _default_machine() -> str:
    return os.getenv("SECTURAFAB_DEFAULT_MACHINE", "Laser").strip() or "Laser"


def _default_material(takeoff: dict[str, Any] | None) -> str:
    env = os.getenv("SECTURAFAB_DEFAULT_MATERIAL", "").strip()
    if env:
        return env
    drivers = (takeoff or {}).get("fitup_drivers") or {}
    weight = drivers.get("weight_calc") or {}
    label = str(weight.get("material_label") or weight.get("material_key") or "").strip()
    if label:
        # SecturaFAB grades are typically bare codes like A36 / A572.
        return label.split()[0]
    return "A36"


def _default_thickness_in(takeoff: dict[str, Any] | None, stp_path: Path | None) -> str:
    env = os.getenv("SECTURAFAB_DEFAULT_THICKNESS", "").strip()
    if env:
        return env
    # Prefer thin plate member thickness from STP summary when present.
    stp = (takeoff or {}).get("stp_summary") or {}
    for solid in stp.get("top_solids") or []:
        box = solid.get("box") or []
        if len(box) >= 3 and 0.05 <= float(box[2]) <= 1.0:
            return f"{float(box[2]):.4g}"
    return "0.25"


def _weld_memo(times: dict[str, Any] | None, takeoff: dict[str, Any] | None) -> str:
    times = times or {}
    takeoff = takeoff or {}
    parts = [
        "Pushed from Kannon Quote Automation",
        f"Weld inches: {times.get('total_inches', takeoff.get('total_inches', '—'))}",
        f"Weld minutes: {times.get('weld_minutes', '—')}",
    ]
    sizes = takeoff.get("sizes_found") or [
        i.get("size") for i in (takeoff.get("items") or []) if i.get("size")
    ]
    if sizes:
        parts.append("Sizes: " + ", ".join(str(s) for s in sizes if s))
    return " | ".join(parts)


def _resolve_part_key(
    *,
    title: str,
    pdf_filename: str | None,
    library: dict[str, Any] | None,
    bom_config: str | None = None,
) -> str:
    """Prefer dashed assembly keys (35145-1) over bare numeric stems (35145)."""
    from quote_core.bom_config import normalize_bom_config

    library = library or {}
    candidates: list[str] = []
    for raw in (
        library.get("part_key"),
        Path(library["folder"]).name if library.get("folder") else None,
        extract_part_key(pdf_filename, title),
        title,
        pdf_filename,
    ):
        if not raw:
            continue
        key = extract_part_key(str(raw)) or str(raw).strip()
        if key:
            candidates.append(key)
    if not candidates:
        return ""
    dashed = [c for c in candidates if "-" in c]
    if dashed:
        return max(dashed, key=len)
    base = max(candidates, key=len)
    dash = normalize_bom_config(bom_config)
    if dash and base and "-" not in base:
        return f"{base}-{dash}"
    return base


def _resolve_related_pdf(folder: Path, name: str) -> Path | None:
    """Find a related PDF in the primary folder or sibling part folders."""
    direct = folder / name
    if direct.is_file():
        return direct
    parent = folder.parent
    if not parent.exists():
        return None
    # Related PDFs may live in 21678-1 while STP is under "Knuckle Weldment - 21678-1".
    try:
        siblings = [p for p in parent.iterdir() if p.is_dir()]
    except OSError:
        return None
    # Prefer folders whose names share the part token.
    token = None
    for m in re.finditer(r"\d{5,}(?:-\d+)?", folder.name):
        token = m.group(0)
    ranked = sorted(
        siblings,
        key=lambda p: (
            0 if token and token in p.name else 1,
            0 if p.name.startswith(str(token or "")) else 1,
            p.name.lower(),
        ),
    )
    for sib in ranked:
        candidate = sib / name
        if candidate.is_file():
            return candidate
    return None


def collect_job_files(
    *,
    pdf_path: Path | None,
    stp_path: Path | None,
    library: dict[str, Any] | None = None,
) -> tuple[list[Path], list[Path]]:
    """Return (drawing_pdfs, cad_files)."""
    drawings: list[Path] = []
    cad: list[Path] = []
    seen: set[str] = set()
    skip_stems = {"CT", "PL", "BOM", "NOTES", "REV", "RD"}

    def add(path: Path | None, bucket: list[Path]) -> None:
        if not path or not path.exists() or not path.is_file():
            return
        if path.suffix.lower() == ".pdf" and path.stem.upper().split()[0] in skip_stems:
            return
        key = str(path.resolve()).lower()
        if key in seen:
            return
        seen.add(key)
        bucket.append(path)

    add(pdf_path, drawings)
    add(stp_path, cad)

    folder = Path(library["folder"]) if library and library.get("folder") else None
    if folder and folder.exists():
        for name in library.get("related_pdfs") or []:
            add(_resolve_related_pdf(folder, str(name)), drawings)
        if not cad:
            for p in folder.iterdir():
                if p.suffix.lower() in {".stp", ".step"}:
                    add(p, cad)
                    break
        if not cad and folder.parent.exists():
            for p in folder.parent.glob(f"{folder.name}.*"):
                if p.suffix.lower() in {".stp", ".step"}:
                    add(p, cad)

    return drawings, cad


class SecturaFabPushService:
    def __init__(self, client: SecturaFabClient | None = None) -> None:
        self.client = client or SecturaFabClient()
        self.quotes = QuoteService(self.client)

    def find_quote_by_number(self, quote_number: str) -> dict[str, Any] | None:
        response = self.client.request("GET", f"v1/quote/byName/{quote_number}")
        if response.status_code >= 400:
            return None
        payload = self.client._parse_or_raise(response)
        if isinstance(payload, dict) and payload.get("ID"):
            return payload
        return None

    def allocate_quote_number(self, part_key: str) -> str:
        """Display QuoteNumber: always 'PN {part}' (no date/job/rev suffix)."""
        return _pn_quote_number(part_key)

    def create_quote(
        self,
        *,
        quote_number: str,
        description: str = "",
        memo: str = "",
        quote_request_id: str | None = None,
    ) -> str:
        """
        Create a new SecturaFAB quote that displays as `PN {part}` only.

        SecturaFAB requires uniqueness for create, so we mint a temporary
        RevNumber then immediately clear it — otherwise re-pushes would either
        reuse the old quote or show PN 21678-1-576 in the UI.
        """
        display = _pn_quote_number(quote_number)
        temp_rev = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        payload: dict[str, Any] = {
            "QuoteNumber": display,
            "RevNumber": temp_rev,
            "QuoteStatus": "OPEN-DRAFT",
        }
        if description:
            payload["Description"] = description[:500]
        if memo:
            payload["Memo"] = memo[:900]
        if quote_request_id:
            payload["QuoteRequestID"] = quote_request_id
        response = self.client.request("POST", "v1/quote", json=payload)
        if response.status_code >= 400:
            raise SecturaFabApiError(
                f"Create quote failed ({response.status_code})",
                status_code=response.status_code,
                body=response.text[:500],
            )
        quote_id = self.client._parse_or_raise(response)
        if not isinstance(quote_id, str) or not quote_id:
            raise SecturaFabApiError(f"Create quote returned unexpected body: {quote_id}")

        # Strip revision so the Quote Number field is exactly PN {part}.
        strip_payload: dict[str, Any] = {
            "ID": quote_id,
            "QuoteNumber": display,
            "RevNumber": None,
            "QuoteAndRevNumber": display,
        }
        if description:
            strip_payload["Description"] = description[:500]
        strip = self.client.request(
            "POST",
            "v1/quote",
            json=strip_payload,
        )
        if strip.status_code >= 400:
            raise SecturaFabApiError(
                f"Could not clear quote revision ({strip.status_code})",
                status_code=strip.status_code,
                body=strip.text[:500],
            )
        return quote_id

    def apply_item_categories(self, quote_id: str) -> list[str]:
        """
        After STEP import, classify each line as Cad / Linear / Component.

        SecturaFAB's UI dropdown maps roughly to IsLinear / plate-vs-part flags.
        Persistence via API is limited; we set the fields that accept updates and
        return notes for what was classified.
        """
        detail = self.client.get_json(f"v1/quote/{quote_id}")
        items = list(detail.get("ItemList") or [])
        if not items:
            return ["No items to categorize"]

        counts = {"Cad": 0, "Linear": 0, "Component": 0}
        for it in items:
            cat = classify_sectura_item(str(it.get("Description") or ""))
            counts[cat] = counts.get(cat, 0) + 1
            it["ItemType"] = cat
            it["Category"] = cat
            if cat == "Linear":
                it["IsLinear"] = True
                it["IsPlate"] = False
                it["IsPart"] = True
            elif cat == "Component":
                it["IsLinear"] = False
                it["IsPlate"] = False
                it["IsPart"] = True
            else:
                it["IsLinear"] = False
                it["IsPlate"] = True
                it["IsPart"] = True

        # Best-effort save (Sectura may ignore some flags on API-created drafts).
        save = self.client.request("POST", "v1/quote", json=detail)
        notes = [
            f"Categorized items — Cad: {counts['Cad']}, Linear: {counts['Linear']}, "
            f"Component: {counts['Component']}"
        ]
        if save.status_code >= 400:
            notes.append(
                f"Category save returned {save.status_code}; set Cad/Linear/Component "
                f"manually in SecturaFAB if the dropdown is still blank"
            )
        else:
            # Verify one linear flag if we expected any
            check = self.client.get_json(f"v1/quote/{quote_id}")
            linear_ok = sum(
                1 for it in (check.get("ItemList") or []) if it.get("IsLinear")
            )
            if counts["Linear"] and not linear_ok:
                notes.append(
                    "SecturaFAB kept items as Cad after save — open each Linear row "
                    "(tube/bar/channel) and set the category dropdown manually"
                )
        return notes

    def upload_drawings_quote_request(self, files: list[Path], *, memo: str = "") -> str:
        if not files:
            raise ValueError("No drawing files to upload")
        open_files = []
        try:
            form_files = []
            for path in files:
                fh = path.open("rb")
                open_files.append(fh)
                form_files.append(("files", (path.name, fh, _mime_for(path))))
            params = {
                "FirstName": os.getenv("SECTURAFAB_CONTACT_FIRST", "Kannon").strip() or "Kannon",
                "LastName": os.getenv("SECTURAFAB_CONTACT_LAST", "QuoteAutomation").strip()
                or "QuoteAutomation",
                "Email": os.getenv("SECTURAFAB_CONTACT_EMAIL", "").strip(),
                "Organization": os.getenv("SECTURAFAB_ORGANIZATION", "Kannon Manufacturing").strip()
                or "Kannon Manufacturing",
            }
            # Drop empty optional query params
            params = {k: v for k, v in params.items() if v}
            qr_id = self.client.post_multipart(
                "v1/quoteRequest/CreateFile",
                files=form_files,
                params=params,
            )
        finally:
            for fh in open_files:
                fh.close()
        if not isinstance(qr_id, str) or not qr_id:
            raise SecturaFabApiError(f"CreateFile returned unexpected body: {qr_id}")
        return qr_id

    def quick_add_cad(
        self,
        *,
        quote_id: str,
        cad_files: list[Path],
        material: str,
        thickness: str,
        machine: str,
        memo: str,
        qty: int = 1,
    ) -> Any:
        if not cad_files:
            raise ValueError("No CAD files to upload")
        open_files = []
        try:
            form_files = []
            for path in cad_files:
                fh = path.open("rb")
                open_files.append(fh)
                form_files.append(("files", (path.name, fh, _mime_for(path))))
            params = {
                "quoteID": quote_id,
                "itemID": "00000000-0000-0000-0000-000000000000",
                "machine": machine,
                "material": material,
                "thickness": thickness,
                "thickness_Units": "inch",
                "qty": int(qty),
                "units": "inch",
                "memo": memo[:240],
                "partMode": "Cad",
            }
            return self.client.post_multipart(
                "v1/quoteOnline/quickAddCAD",
                files=form_files,
                params=params,
            )
        finally:
            for fh in open_files:
                fh.close()

    def push_job(
        self,
        *,
        title: str,
        pdf_filename: str | None,
        pdf_path: Path | None,
        stp_path: Path | None,
        takeoff: dict[str, Any] | None,
        times: dict[str, Any] | None,
        qty: int = 1,
        job_id: int | None = None,
    ) -> PushResult:
        notes: list[str] = []
        uploaded: list[str] = []
        try:
            part_key = _resolve_part_key(
                title=title,
                pdf_filename=pdf_filename,
                library=(takeoff or {}).get("library") or {},
                bom_config=(takeoff or {}).get("bom_config"),
            )
            if not part_key:
                return PushResult(
                    ok=False,
                    error="Could not determine top-level part number for QuoteNumber",
                )

            library = (takeoff or {}).get("library") or {}
            stp = Path(stp_path) if stp_path else None
            drawings, cad = collect_job_files(
                pdf_path=Path(pdf_path) if pdf_path else None,
                stp_path=stp,
                library=library,
            )
            # STEP/STP is the CAD source of truth for SecturaFAB part import.
            if stp and stp.exists():
                cad = [stp]
            elif cad:
                # Library may have found a STEP beside the drawings.
                cad = [cad[0]]
            if not drawings and not cad:
                return PushResult(ok=False, error="No PDF or STEP files found to push")
            if stp and stp.exists() and not cad:
                return PushResult(
                    ok=False,
                    error=f"STEP is on the job ({stp.name}) but could not be prepared for upload",
                )

            memo = _weld_memo(times, takeoff)
            material = _default_material(takeoff)
            thickness = _default_thickness_in(takeoff, stp)
            machine = _default_machine()

            quote_request_id = None
            if drawings:
                quote_request_id = self.upload_drawings_quote_request(drawings, memo=memo)
                uploaded.extend(p.name for p in drawings)
                notes.append(
                    f"Uploaded {len(drawings)} drawing file(s) as Quote Request attachments"
                )

            # Always create a brand-new quote. Display number is PN {part} only
            # (temp RevNumber is cleared so the UI does not show PN 21678-1-576).
            quote_number = self.allocate_quote_number(part_key)
            quote_description = extract_assembly_description(
                part_key=part_key,
                pdf_path=Path(pdf_path) if pdf_path else None,
                library_folder=library.get("folder"),
                related_pdf_names=list(library.get("related_pdfs") or []),
            )
            quote_id = self.create_quote(
                quote_number=quote_number,
                description=quote_description or "",
                memo="",
                quote_request_id=quote_request_id,
            )
            notes.append(f"Created SecturaFAB quote {quote_number}")
            if quote_description:
                notes.append(f"Quote Description from assembly drawing: {quote_description}")
            else:
                notes.append(
                    "No assembly drawing title found — left Quote Description blank"
                )

            if cad:
                self.quick_add_cad(
                    quote_id=quote_id,
                    cad_files=cad,
                    material=material,
                    thickness=thickness,
                    machine=machine,
                    memo=memo,
                    qty=qty,
                )
                uploaded.extend(p.name for p in cad)
                notes.append(
                    f"Imported STEP/STP via quickAddCAD: {cad[0].name} "
                    f"({machine}, {material}, {thickness}\")"
                )
                notes.extend(self.apply_item_categories(quote_id))
                # Root STEP solid must be Assembly (not a plate/part) — lesson 02.
                notes.extend(
                    ensure_assembly_root(self.client, quote_id, part_key=part_key)
                )
                # Purchased hardware / king pins → Component (no laser Profile).
                bom_rows = extract_bom_rows(takeoff)
                purchased = find_purchased_part_keys(
                    library_folder=library.get("folder"),
                    related_pdf_names=list(library.get("related_pdfs") or []),
                    bom_rows=bom_rows,
                )
                notes.extend(
                    ensure_purchased_components(
                        self.client, quote_id, purchased_keys=purchased
                    )
                )
                # Component conversion can drop links — re-attach children under assembly.
                notes.extend(
                    relink_assembly_children(self.client, quote_id, part_key=part_key)
                )
                # Per-part material/thickness from component PDF title blocks (lesson 02).
                part_materials = build_part_material_map(
                    library_folder=library.get("folder"),
                    related_pdf_names=list(library.get("related_pdfs") or []),
                    extra_pdfs=[Path(pdf_path)] if pdf_path else None,
                )
                if part_materials:
                    notes.append(
                        f"Read material/thickness from {len(part_materials)} component PDF(s)"
                    )
                # UpdateItem_Part MUST finish (and settle) before Profile/Weld/BOM qty —
                # otherwise CAD recalc wipes those fields.
                notes.extend(
                    apply_part_materials(
                        self.client,
                        quote_id,
                        material=material,
                        thickness=thickness,
                        part_materials=part_materials,
                        bom_rows=bom_rows,
                    )
                )
                # UpdateItem_Part CAD recalc finishes ~30–60s after HTTP 200 and
                # will wipe Profile/Weld if we attach too soon. Wait it out.
                # BOM qty is baked into UpdateItem_Part so it survives that rebuild.
                notes.extend(
                    wait_for_quote_settle(
                        self.client,
                        quote_id,
                        timeout_s=120.0,
                        stable_s=15.0,
                        min_wait_s=45.0,
                    )
                )
                # Safety net for any lines UpdateItem skipped (e.g. Components).
                notes.extend(
                    apply_bom_quantities(
                        self.client,
                        quote_id,
                        bom_rows=bom_rows,
                        part_key=part_key,
                    )
                )
                # quickAddCAD computes cut time in DataPart but only attaches Bend.
                notes.extend(
                    ensure_laser_profile_ops(
                        self.client,
                        quote_id,
                        material=material,
                        thickness=thickness,
                    )
                )
            else:
                bom_rows = extract_bom_rows(takeoff)
                if bom_rows and library.get("folder"):
                    from .pdf_assembly_ops import build_pdf_only_assembly

                    notes.append(
                        "No STEP/STP — building assembly from BOM component PDFs"
                    )
                    notes.extend(
                        build_pdf_only_assembly(
                            self.client,
                            quote_id=quote_id,
                            part_key=part_key,
                            bom_rows=bom_rows,
                            library_folder=library.get("folder"),
                            related_pdf_names=list(library.get("related_pdfs") or []),
                            material=material,
                            thickness=thickness,
                            machine=machine,
                            qty=qty,
                            times=times,
                            extra_pdfs=[Path(pdf_path)] if pdf_path else None,
                        )
                    )
                    # Weld is applied below; finalize already ran inside PDF assembly.
                else:
                    notes.append(
                        "No STEP/STP on job — quote created with drawings only "
                        "(no BOM rows / library folder for PDF assembly)"
                    )

            # Lesson 02: Weld is not auto-added by STEP — push Cursor weld + fit-up minutes.
            notes.extend(
                ensure_weld_ops(
                    self.client,
                    quote_id,
                    times=times,
                    part_key=part_key,
                )
            )

            # Late CAD recalcs can wipe Profile/Weld/Qty after first attach — verify
            # and re-apply until stable (no more UpdateItem_Part here).
            if cad or (bom_rows and library.get("folder") and not cad):
                notes.extend(
                    finalize_quote_ops(
                        self.client,
                        quote_id,
                        material=material,
                        thickness=thickness,
                        times=times,
                        part_key=part_key,
                        bom_rows=bom_rows,
                    )
                )
            detail = self.client.get_json(f"v1/quote/{quote_id}")
            item_count = detail.get("ItemCount")
            if item_count is None:
                item_count = len(detail.get("ItemList") or [])
            stored_number = str(detail.get("QuoteNumber") or quote_number)
            # Prefer the cleaned display form without revision suffix.
            and_rev = str(detail.get("QuoteAndRevNumber") or stored_number)
            if detail.get("RevNumber"):
                notes.append(
                    f"Warning: quote still has RevNumber={detail.get('RevNumber')!r} "
                    f"(display {and_rev})"
                )

            ready = not any(n.startswith("WARNING:") for n in notes)

            return PushResult(
                ok=True,
                quote_id=quote_id,
                quote_number=stored_number,
                quote_request_id=quote_request_id,
                created_new_quote=True,
                uploaded_files=uploaded,
                item_count=int(item_count) if item_count is not None else None,
                notes=notes,
                ready=ready,
            )
        except (SecturaFabApiError, ValueError, OSError) as exc:
            return PushResult(ok=False, error=str(exc), notes=notes, uploaded_files=uploaded)
