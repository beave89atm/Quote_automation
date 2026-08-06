"""Push Kannon quote jobs into SecturaFAB (create quote + upload drawings/STEP)."""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from quote_core.drawing_library import extract_part_key

from .assembly_ops import ensure_assembly_root, relink_assembly_children
from .client import SecturaFabApiError, SecturaFabClient
from .component_ops import ensure_purchased_components, find_purchased_part_keys
from .finalize_ops import finalize_quote_ops
from .imperial_ops import ensure_imperial_item_units
from .profile_ops import (
    ensure_laser_profile_ops,
)
from .qty_ops import apply_bom_quantities, refresh_bom_rows_for_push
from .quotes import QuoteService
from .weld_ops import ensure_weld_ops
from quote_core.drawing_title import extract_assembly_description

# CreateFile outage retry (SecturaFAB DB "underlying provider failed on Open").
CREATEFILE_RETRY_INTERVAL_S = 300.0
CREATEFILE_RETRY_MAX_S = 48 * 3600.0

ProgressCallback = Callable[[dict[str, Any]], None]


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
    "ROUND BAR",
    "DOM",
    "PIVOT TUBE",
    "BOOM TUBE",
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
    # pushing | retrying_createfile | complete | failed
    status: str | None = None
    attempts: int = 0
    next_retry_at: str | None = None
    last_error: str | None = None

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
            "status": self.status,
            "attempts": self.attempts,
            "next_retry_at": self.next_retry_at,
            "last_error": self.last_error,
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


# Common plate gauges SecturaFAB material tables accept (inches).
_STANDARD_PLATE_THICKNESSES_IN = (
    0.0598,  # 16 ga
    0.0747,  # 14 ga
    0.1046,  # 12 ga
    0.1196,  # 11 ga
    0.1345,  # 10 ga
    0.125,   # 1/8
    0.1875,  # 3/16
    0.25,    # 1/4
    0.3125,  # 5/16
    0.375,   # 3/8
    0.5,     # 1/2
    0.625,   # 5/8
    0.75,    # 3/4
)


def _snap_plate_thickness(raw: float) -> float | None:
    """Snap a candidate thickness to the nearest standard plate gauge, or None."""
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    if val <= 0.04 or val > 0.85:
        # Covers / structural depths (e.g. 0.938") are not laser plate stock.
        return None
    best = min(_STANDARD_PLATE_THICKNESSES_IN, key=lambda t: abs(t - val))
    if abs(best - val) > 0.04:
        return None
    return best


def _format_thickness(val: float) -> str:
    text = f"{val:.4g}"
    return text


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
    """
    Seed thickness for quickAddCAD.

    Prefer a standard plate gauge from STP plate solids — never raw cover/channel
    depths like 0.938", which SecturaFAB material tables reject / choke on.
    """
    del stp_path  # path unused; takeoff already carries stp_summary
    env = os.getenv("SECTURAFAB_DEFAULT_THICKNESS", "").strip()
    if env:
        snapped = _snap_plate_thickness(env) if env.replace(".", "", 1).isdigit() else None
        return _format_thickness(snapped) if snapped is not None else env

    stp = (takeoff or {}).get("stp_summary") or {}
    solids = list(stp.get("top_solids") or [])
    # Prefer classified plates first, then any solid with a plausible thin axis.
    ranked = sorted(
        solids,
        key=lambda s: (
            0 if str(s.get("kind") or "").lower() == "plate" else 1,
            0 if str(s.get("kind") or "").lower() not in {"cover", "channel", "angle"} else 1,
        ),
    )
    for solid in ranked:
        box = solid.get("box") or []
        if len(box) < 3:
            continue
        # Plate thickness is the minimum bbox axis for flat parts.
        axes = sorted(float(x) for x in box[:3])
        for candidate in (axes[0], float(box[2])):
            snapped = _snap_plate_thickness(candidate)
            if snapped is not None:
                return _format_thickness(snapped)

    # Weld size is not plate thickness, but 1/4" is the shop default seed.
    sizes = (takeoff or {}).get("sizes_found") or []
    size_map = {"1/8": 0.125, "3/16": 0.1875, "1/4": 0.25, "5/16": 0.3125, "3/8": 0.375}
    for size in sizes:
        if str(size) in size_map:
            return _format_thickness(size_map[str(size)])
    return "0.25"


def _api_error_detail(exc: SecturaFabApiError) -> str:
    """Pull ExceptionMessage / Cloudflare detail out of a failed API response."""
    body = exc.body
    if isinstance(body, dict):
        for key in ("ExceptionMessage", "detail", "Message", "title", "error_name"):
            val = body.get(key)
            if val:
                return str(val).strip()
    if isinstance(body, str) and body.strip():
        return body.strip()[:300]
    return str(exc)


def _is_retryable_cad_error(exc: SecturaFabApiError) -> bool:
    if exc.status_code in {429, 502, 503, 504}:
        return True
    detail = _api_error_detail(exc).lower()
    return any(
        token in detail
        for token in (
            "outofmemory",
            "out of memory",
            "bad gateway",
            "timeout",
            "temporar",
            "retryable",
        )
    )


def is_transient_secturafab_error(exc: BaseException) -> bool:
    """True for CreateFile / API outages that should be retried (not auth/4xx)."""
    if not isinstance(exc, SecturaFabApiError):
        return False
    code = exc.status_code
    if code is not None and code >= 500:
        return True
    if code == 429:
        return True
    detail = _api_error_detail(exc).lower()
    blob = f"{exc} {detail}".lower()
    return any(
        token in blob
        for token in (
            "underlying provider failed",
            "entityexception",
            "bad gateway",
            "service unavailable",
            "timeout",
            "temporar",
        )
    )


def _weld_memo(times: dict[str, Any] | None, takeoff: dict[str, Any] | None) -> str:
    times = times or {}
    takeoff = takeoff or {}

    def _fmt(val: Any) -> str:
        try:
            return f"{float(val):.2f}"
        except (TypeError, ValueError):
            return str(val if val is not None else "—")

    parts = [
        "Pushed from Kannon Quote Automation",
        f"Weld inches: {_fmt(times.get('total_inches', takeoff.get('total_inches')))}",
        f"Weld minutes: {_fmt(times.get('weld_minutes'))}",
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
            # Non-fatal: quote exists; UI may briefly show a temp rev suffix.
            # Aborting here used to block pushes during SecturaFAB 5xx blips.
            pass
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

    def upload_drawings_quote_request(
        self,
        files: list[Path],
        *,
        memo: str = "",
        on_progress: ProgressCallback | None = None,
        sleep_fn: Callable[[float], None] | None = None,
        retry_interval_s: float = CREATEFILE_RETRY_INTERVAL_S,
        retry_max_s: float = CREATEFILE_RETRY_MAX_S,
    ) -> str:
        if not files:
            raise ValueError("No drawing files to upload")
        sleep = sleep_fn or time.sleep
        started = time.monotonic()
        attempt = 0
        last_exc: SecturaFabApiError | None = None

        while True:
            attempt += 1
            open_files = []
            try:
                form_files = []
                for path in files:
                    fh = path.open("rb")
                    open_files.append(fh)
                    form_files.append(("files", (path.name, fh, _mime_for(path))))
                params = {
                    "FirstName": os.getenv("SECTURAFAB_CONTACT_FIRST", "Kannon").strip()
                    or "Kannon",
                    "LastName": os.getenv("SECTURAFAB_CONTACT_LAST", "QuoteAutomation").strip()
                    or "QuoteAutomation",
                    "Email": os.getenv("SECTURAFAB_CONTACT_EMAIL", "").strip(),
                    "Organization": os.getenv(
                        "SECTURAFAB_ORGANIZATION", "Kannon Manufacturing"
                    ).strip()
                    or "Kannon Manufacturing",
                }
                # Drop empty optional query params
                params = {k: v for k, v in params.items() if v}
                qr_id = self.client.post_multipart(
                    "v1/quoteRequest/CreateFile",
                    files=form_files,
                    params=params,
                )
            except SecturaFabApiError as exc:
                last_exc = exc
                if not is_transient_secturafab_error(exc):
                    raise
                elapsed = time.monotonic() - started
                if elapsed >= retry_max_s:
                    raise SecturaFabApiError(
                        f"CreateFile still failing after {retry_max_s / 3600:.0f}h "
                        f"({attempt} attempts): {_api_error_detail(exc)}",
                        status_code=exc.status_code,
                        body=exc.body,
                    ) from exc
                wait_s = max(1.0, float(retry_interval_s))
                next_at = datetime.now(timezone.utc) + timedelta(seconds=wait_s)
                detail = _api_error_detail(exc)
                if on_progress:
                    on_progress(
                        {
                            "ok": False,
                            "status": "retrying_createfile",
                            "attempts": attempt,
                            "last_error": detail,
                            "next_retry_at": next_at.isoformat(),
                            "notes": [
                                f"CreateFile attempt {attempt} failed (transient): "
                                f"{detail} — retrying in {int(wait_s / 60)} min"
                            ],
                        }
                    )
                sleep(wait_s)
                continue
            finally:
                for fh in open_files:
                    fh.close()

            if not isinstance(qr_id, str) or not qr_id:
                raise SecturaFabApiError(f"CreateFile returned unexpected body: {qr_id}")
            if on_progress and attempt > 1:
                on_progress(
                    {
                        "ok": False,
                        "status": "pushing",
                        "attempts": attempt,
                        "last_error": None,
                        "next_retry_at": None,
                        "notes": [
                            f"CreateFile succeeded on attempt {attempt} — continuing push"
                        ],
                    }
                )
            return qr_id

        # Unreachable; keeps type checkers happy if loop exits oddly.
        raise last_exc or SecturaFabApiError("CreateFile failed with no exception")

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
        retries: int = 3,
    ) -> Any:
        if not cad_files:
            raise ValueError("No CAD files to upload")
        import time

        last_exc: SecturaFabApiError | None = None
        for attempt in range(1, max(1, retries) + 1):
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
            except SecturaFabApiError as exc:
                last_exc = exc
                if attempt >= retries or not _is_retryable_cad_error(exc):
                    raise SecturaFabApiError(
                        f"{exc} — {_api_error_detail(exc)}",
                        status_code=exc.status_code,
                        body=exc.body,
                    ) from exc
                # Cloudflare / Eyeshot OOM — back off before retry.
                time.sleep(min(90.0, 15.0 * attempt))
            finally:
                for fh in open_files:
                    fh.close()
        assert last_exc is not None
        raise last_exc

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
        on_progress: ProgressCallback | None = None,
        createfile_sleep_fn: Callable[[float], None] | None = None,
        createfile_retry_interval_s: float = CREATEFILE_RETRY_INTERVAL_S,
        createfile_retry_max_s: float = CREATEFILE_RETRY_MAX_S,
    ) -> PushResult:
        notes: list[str] = []
        uploaded: list[str] = []
        createfile_attempts = 0
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
                    status="failed",
                )

            library = (takeoff or {}).get("library") or {}
            # Dash-config BOM must be filtered before PDF assembly import.
            bom_rows, bom_refresh_notes = refresh_bom_rows_for_push(
                takeoff,
                title=title,
                pdf_path=pdf_path,
            )
            notes.extend(bom_refresh_notes)
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
                return PushResult(
                    ok=False,
                    error="No PDF or STEP files found to push",
                    status="failed",
                )
            if stp and stp.exists() and not cad:
                return PushResult(
                    ok=False,
                    error=f"STEP is on the job ({stp.name}) but could not be prepared for upload",
                    status="failed",
                )

            memo = _weld_memo(times, takeoff)
            material = _default_material(takeoff)
            thickness = _default_thickness_in(takeoff, stp)
            machine = _default_machine()

            if on_progress:
                on_progress(
                    {
                        "ok": False,
                        "status": "pushing",
                        "attempts": 0,
                        "notes": ["SecturaFAB push started"],
                    }
                )

            quote_request_id = None
            if drawings:

                def _createfile_progress(info: dict[str, Any]) -> None:
                    nonlocal createfile_attempts
                    createfile_attempts = int(info.get("attempts") or createfile_attempts)
                    if info.get("notes"):
                        notes.extend(str(n) for n in info["notes"])
                    if on_progress:
                        merged = dict(info)
                        merged["notes"] = list(notes)
                        on_progress(merged)

                quote_request_id = self.upload_drawings_quote_request(
                    drawings,
                    memo=memo,
                    on_progress=_createfile_progress,
                    sleep_fn=createfile_sleep_fn,
                    retry_interval_s=createfile_retry_interval_s,
                    retry_max_s=createfile_retry_max_s,
                )
                uploaded.extend(p.name for p in drawings)
                notes.append(
                    f"Uploaded {len(drawings)} drawing file(s) as Quote Request attachments"
                )
                if on_progress:
                    on_progress(
                        {
                            "ok": False,
                            "status": "pushing",
                            "attempts": createfile_attempts or 1,
                            "notes": list(notes),
                        }
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

            used_step = False
            if cad:
                try:
                    self.quick_add_cad(
                        quote_id=quote_id,
                        cad_files=cad,
                        material=material,
                        thickness=thickness,
                        machine=machine,
                        memo=memo,
                        qty=qty,
                    )
                    used_step = True
                    uploaded.extend(p.name for p in cad)
                    notes.append(
                        f"Imported STEP/STP via quickAddCAD: {cad[0].name} "
                        f"({machine}, {material}, {thickness}\", units=inch)"
                    )
                except SecturaFabApiError as exc:
                    detail = _api_error_detail(exc)
                    notes.append(
                        f"WARNING: STEP import failed ({exc.status_code}): {detail}"
                    )
                    if bom_rows and library.get("folder"):
                        notes.append(
                            "Falling back to lesson 04 PDF component assembly "
                            "(SecturaFAB could not load the STEP)"
                        )
                    else:
                        raise SecturaFabApiError(
                            f"STEP quickAddCAD failed and no BOM/library for PDF "
                            f"fallback — {detail}",
                            status_code=exc.status_code,
                            body=exc.body,
                        ) from exc

            if used_step:
                notes.extend(self.apply_item_categories(quote_id))
                # Root STEP solid must be Assembly (not a plate/part) — lesson 02.
                notes.extend(
                    ensure_assembly_root(self.client, quote_id, part_key=part_key)
                )
                # Purchased hardware / king pins → Component (no laser Profile).
                # bom_rows already refreshed above for dash config.
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
                # Do NOT call UpdateItem_Part on STEP assemblies.
                # On multi-body welds (e.g. 80341687) its delayed CAD rebuild can wipe
                # the entire ItemList ~1–2 minutes later. Seed material/thickness comes
                # from quickAddCAD; BOM qty is applied below without UpdateItem_Part.
                notes.append(
                    f"Skipped UpdateItem_Part on STEP assembly (seed {material} @ "
                    f"{thickness}\") — avoids delayed CAD wipe of ItemList"
                )
                notes.extend(ensure_imperial_item_units(self.client, quote_id))
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
                # Profile/Weld quote POSTs can reset child Qty to 1 — re-apply now.
                notes.extend(
                    apply_bom_quantities(
                        self.client,
                        quote_id,
                        bom_rows=bom_rows,
                        part_key=part_key,
                    )
                )
                notes.extend(ensure_imperial_item_units(self.client, quote_id))
            elif bom_rows and library.get("folder"):
                from .pdf_assembly_ops import build_pdf_only_assembly

                notes.append(
                    "Building assembly from BOM component PDFs "
                    f"({len(bom_rows)} BOM rows / lesson 04)"
                    + (" — STEP unavailable/failed" if cad else " — no STEP on job")
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
            if used_step or (bom_rows and library.get("folder")):
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
            item_list = list(detail.get("ItemList") or [])
            item_count = detail.get("ItemCount")
            # SecturaFAB often reports ItemCount=1 for assemblies while ItemList
            # holds the root + every child — prefer the real line count.
            if item_list and (
                item_count is None or int(item_count) < len(item_list)
            ):
                item_count = len(item_list)
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
                status="complete",
                attempts=createfile_attempts,
            )
        except (SecturaFabApiError, ValueError, OSError) as exc:
            err = str(exc)
            if on_progress:
                on_progress(
                    {
                        "ok": False,
                        "status": "failed",
                        "error": err,
                        "last_error": err,
                        "notes": list(notes),
                        "attempts": createfile_attempts,
                    }
                )
            return PushResult(
                ok=False,
                error=err,
                notes=notes,
                uploaded_files=uploaded,
                status="failed",
                attempts=createfile_attempts,
                last_error=err,
            )
