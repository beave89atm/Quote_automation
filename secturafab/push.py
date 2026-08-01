"""Push Kannon quote jobs into SecturaFAB (create quote + upload drawings/STEP)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quote_core.drawing_library import extract_part_key

from .client import SecturaFabApiError, SecturaFabClient
from .quotes import QuoteService


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
) -> str:
    """Prefer dashed assembly keys (35145-1) over bare numeric stems (35145)."""
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
    return max(candidates, key=len)


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
        """
        Every push creates a new quote. Use the bare part number when free;
        otherwise part-YYYYMMDD / part-YYYYMMDD-2 (never a job-id suffix).
        SecturaFAB QuoteNumber values must be unique.
        """
        if not self.find_quote_by_number(part_key):
            return part_key
        day = datetime.now(timezone.utc).strftime("%Y%m%d")
        dated = f"{part_key}-{day}"
        if not self.find_quote_by_number(dated):
            return dated
        for n in range(2, 100):
            candidate = f"{dated}-{n}"
            if not self.find_quote_by_number(candidate):
                return candidate
        raise SecturaFabApiError(f"Could not allocate a free QuoteNumber for {part_key}")

    def create_quote(
        self,
        *,
        quote_number: str,
        description: str = "",
        memo: str = "",
        quote_request_id: str | None = None,
    ) -> str:
        # Match manual SecturaFAB quotes: part number only, blank description.
        # OPEN-DRAFT (not OPEN-NEW) is what gets Profile ops applied after quickAddCAD.
        payload: dict[str, Any] = {
            "QuoteNumber": quote_number,
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
        return quote_id

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
                "partMode": "Part",
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
            )
            if not part_key:
                return PushResult(
                    ok=False,
                    error="Could not determine top-level part number for QuoteNumber",
                )

            library = (takeoff or {}).get("library") or {}
            drawings, cad = collect_job_files(
                pdf_path=Path(pdf_path) if pdf_path else None,
                stp_path=Path(stp_path) if stp_path else None,
                library=library,
            )
            if not drawings and not cad:
                return PushResult(ok=False, error="No PDF or STEP files found to push")

            memo = _weld_memo(times, takeoff)
            material = _default_material(takeoff)
            thickness = _default_thickness_in(takeoff, Path(stp_path) if stp_path else None)
            machine = _default_machine()

            quote_request_id = None
            if drawings:
                quote_request_id = self.upload_drawings_quote_request(drawings, memo=memo)
                uploaded.extend(p.name for p in drawings)
                notes.append(
                    f"Uploaded {len(drawings)} drawing file(s) as Quote Request attachments"
                )

            # Always create a brand-new quote (same part next day = new quote).
            # QuoteNumber must be unique in SecturaFAB, so reuse gets a date suffix
            # — never a Kannon job id.
            quote_number = self.allocate_quote_number(part_key)
            if quote_number != part_key:
                notes.append(
                    f"{part_key} already used — new quote numbered {quote_number}"
                )
            quote_id = self.create_quote(
                quote_number=quote_number,
                description="",
                memo="",
                quote_request_id=quote_request_id,
            )
            notes.append(f"Created SecturaFAB quote {quote_number}")

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
                    f"Imported CAD via quickAddCAD ({machine}, {material}, {thickness}\")"
                )
            else:
                notes.append("No STEP/STP on job — quote created with drawings only")

            detail = self.client.get_json(f"v1/quote/{quote_id}")
            item_count = detail.get("ItemCount")
            if item_count is None:
                item_count = len(detail.get("ItemList") or [])

            return PushResult(
                ok=True,
                quote_id=quote_id,
                quote_number=str(detail.get("QuoteNumber") or quote_number),
                quote_request_id=quote_request_id,
                created_new_quote=True,
                uploaded_files=uploaded,
                item_count=int(item_count) if item_count is not None else None,
                notes=notes,
            )
        except (SecturaFabApiError, ValueError, OSError) as exc:
            return PushResult(ok=False, error=str(exc), notes=notes, uploaded_files=uploaded)
