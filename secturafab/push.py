"""Push Kannon quote jobs into SecturaFAB (create quote + upload drawings/STEP)."""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from quote_core.customer_org import detect_organization
from quote_core.drawing_library import extract_part_key
from quote_core.drawing_title import (
    extract_assembly_description,
    extract_drawing_number_from_pdf,
)

from .item_desc import (
    format_assembly_description,
    title_from_job_title,
    title_from_library_folder,
)
from .linear_ops import bind_linear_product_ids

from .assembly_ops import (
    ensure_assembly_root,
    needs_assembly_structure,
    relink_assembly_children,
)
from .client import SecturaFabApiError, SecturaFabClient
from .component_ops import ensure_purchased_components, find_purchased_part_keys
from .finalize_ops import finalize_quote_ops
from .imperial_ops import ensure_imperial_item_units
from .org_ops import apply_quote_organization
from .profile_ops import ensure_laser_profile_ops  # imported for tests; push no longer grafts
from .qty_ops import apply_bom_quantities, refresh_bom_rows_for_push
from .quotes import QuoteService
from .website import (
    EMPTY_GUID,
    WEBSITE_AUTH_GAP,
    SecturaFabWebsiteAuthError,
    overlay_classified_row,
    pick_closest_linear_product,
    row_name,
)
from .weld_ops import ensure_weld_ops

# CreateFile outage retry (SecturaFAB DB "underlying provider failed on Open").
CREATEFILE_RETRY_INTERVAL_S = 300.0
CREATEFILE_RETRY_MAX_S = 48 * 3600.0

ProgressCallback = Callable[[dict[str, Any]], None]


_QUOTE_REV_SUFFIX_RE = re.compile(r"(?i)[\s_-]*R\d{2}$")


def _pn_quote_number(part_key: str) -> str:
    """SecturaFAB Quote Number = bare part key (no 'PN ' prefix, no rev suffix)."""
    key = (part_key or "").strip()
    if not key:
        return ""
    if key.upper().startswith("PN "):
        key = key[3:].strip()
    elif key.upper().startswith("PN"):
        key = key[2:].lstrip(" _-")
    key = _QUOTE_REV_SUFFIX_RE.sub("", key).strip(" -_")
    return key


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
    "HOSE GUARD",
    "HOSEGUARD",
    "ROUND BAR",
    "FLAT BAR",
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
    "ELBOW",
    "COUPLING",
    "NIPPLE",
    "PLUG",
    "PIPE CAP",
    "FILLER NECK",
    "STREET ELBOW",
    "HALF COUPLING",
    "FITTING",
    "REDUCER",
    "UNION",
)
_COMPONENT_WORD_RE = re.compile(
    r"\b(ELBOW|COUPLING|NIPPLE|PLUG|CAP|FITTING|REDUCER|UNION)\b",
    re.IGNORECASE,
)


def _row_qty(row: dict[str, Any]) -> float:
    for key in ("Qty", "Quantity", "qty"):
        if key in row and row.get(key) is not None:
            try:
                return float(row.get(key) or 0)
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def classify_sectura_item(description: str) -> str:
    """
    Map a STEP/BOM description to SecturaFAB item category dropdown values:
    Cad | Linear | Component

    Plate/sheet = Cad. Structural tube/bar/angle/channel/hose guard = Linear.
    Purchased fittings (elbow, coupling, plug, nipple, cap, filler neck) and
    hardware = Component. Component is checked before Linear so ``PIPE CAP``
    is not treated as a Linear pipe.
    """
    text = f" {str(description or '').upper()} "
    # Collapse spaces so "KING PIN" and "KINGPIN" both match.
    compact = text.replace(" ", "")
    if "HOSEGUARD" in compact or "HOSE GUARD" in text:
        return "Linear"
    if "KINGPIN" in compact:
        return "Component"
    if any(h in text for h in _COMPONENT_HINTS) or _COMPONENT_WORD_RE.search(text):
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
    """Numeric thickness only — never append 'inch' (SecturaFAB dropdown values are bare)."""
    t = float(val)
    # Prefer four-decimal stock values that match common SF dropdown rows.
    rounded = round(t, 4)
    if abs(rounded - t) < 1e-9 or abs(t - rounded) <= 0.00015:
        text = f"{rounded:.4f}".rstrip("0").rstrip(".")
        if "." not in text:
            text = f"{rounded:.4f}"
        return text
    return f"{t:.4g}"


def _sanitize_thickness_param(raw: str | float | None) -> str:
    """Strip unit suffixes so thickness matches SecturaFAB dropdown values."""
    if raw is None:
        return "0.25"
    if isinstance(raw, (int, float)):
        return _format_thickness(float(raw))
    text = str(raw).strip()
    text = re.sub(r"(?i)\s*(inches|inch|in)\s*$", "", text)
    text = text.replace('"', "").replace("″", "").replace("'", "").strip()
    if not text:
        return "0.25"
    try:
        return _format_thickness(float(text))
    except ValueError:
        # Fraction like 1/4
        from quote_core.part_materials import _parse_thickness_token

        parsed = _parse_thickness_token(text)
        if parsed is not None:
            return _format_thickness(parsed)
        return re.sub(r"(?i)[^0-9./]", "", text) or "0.25"


def _default_machine() -> str:
    return os.getenv("SECTURAFAB_DEFAULT_MACHINE", "Laser").strip() or "Laser"


def _default_material(takeoff: dict[str, Any] | None) -> str:
    env = os.getenv("SECTURAFAB_DEFAULT_MATERIAL", "").strip()
    if env:
        return env
    drivers = (takeoff or {}).get("fitup_drivers") or {}
    weight = drivers.get("weight_calc") or {}
    key = str(weight.get("material_key") or "").strip().lower()
    label = str(weight.get("material_label") or "").strip()
    # Weight heuristics often mis-read title-block boilerplate ("ALUMINUM MATERIALS")
    # as the part material — do not seed SecturaFAB from weak aluminum guesses.
    if key in {"aluminum", "aluminium"} or "aluminum" in label.lower():
        return "A36"
    if label:
        # SecturaFAB grades are typically bare codes like A36 / A572.
        return label.split()[0]
    return "A36"


def _resolve_push_material_thickness(
    *,
    takeoff: dict[str, Any] | None,
    stp_path: Path | None,
    pdf_path: Path | None,
) -> tuple[str, str, list[str]]:
    """
    Prefer material/thickness read from the job PDF title block / stock line.
    Returns (material, thickness, notes). Thickness never includes 'inch'.
    """
    notes: list[str] = []
    material = _default_material(takeoff)
    thickness = _sanitize_thickness_param(_default_thickness_in(takeoff, stp_path))
    known_from_pdf = False

    if pdf_path and Path(pdf_path).is_file():
        from quote_core.part_materials import extract_part_material_from_pdf

        try:
            pm = extract_part_material_from_pdf(pdf_path)
        except Exception as exc:  # noqa: BLE001 — corrupt/minimal test PDFs
            notes.append(
                f"WARNING: Could not read material/thickness from PDF ({exc}) — "
                f"seeded {material} @ {thickness}; confirm in SecturaFAB"
            )
            pm = None
        if pm:
            if pm.material:
                material = pm.material
                known_from_pdf = True
                notes.append(
                    f"Material from drawing: {pm.material} ({pm.source})"
                )
            if pm.thickness_in is not None:
                thickness = _sanitize_thickness_param(pm.thickness_param() or pm.thickness_in)
                notes.append(
                    f"Thickness from drawing: {thickness} ({pm.source})"
                )
                known_from_pdf = True
            if pm.material_key in {None, ""} or (
                pm.source.startswith("no_material") or "unknown" in pm.source.lower()
            ):
                notes.append(
                    "WARNING: Drawing material grade not confidently identified — "
                    f"seeded {material}; confirm in SecturaFAB"
                )
        elif not any("Could not read material" in n for n in notes):
            notes.append(
                "WARNING: Could not read material/thickness from PDF title block — "
                f"seeded {material} @ {thickness}; confirm in SecturaFAB"
            )
    elif not known_from_pdf:
        drivers = (takeoff or {}).get("fitup_drivers") or {}
        weight = drivers.get("weight_calc") or {}
        if str(weight.get("material_key") or "").lower() in {"aluminum", "aluminium"}:
            notes.append(
                "WARNING: Takeoff guessed Aluminum from drawing boilerplate — "
                f"using {material} @ {thickness} instead; confirm against the PDF"
            )

    thickness = _sanitize_thickness_param(thickness)
    return material, thickness, notes


def _default_thickness_in(takeoff: dict[str, Any] | None, stp_path: Path | None) -> str:
    """
    Seed thickness for CAD Files Finish / Image Files.

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
    pdf_path: str | Path | None = None,
) -> str:
    """Prefer dashed drawing/assembly keys (1511-5024 / 35145-1) over bare stems."""
    from quote_core.bom_config import normalize_bom_config

    library = library or {}
    candidates: list[str] = []
    # Title-block DRAWING NUMBER is the search key in SecturaFAB — prefer it.
    if pdf_path:
        p = Path(pdf_path)
        if p.is_file():
            drawn = extract_drawing_number_from_pdf(p)
            if drawn:
                candidates.append(drawn)
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
            candidates.append(_pn_quote_number(key) or key)
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
        """Display QuoteNumber: bare part key (no PN prefix, no date/job/rev suffix)."""
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
        Create a new SecturaFAB quote that displays as the bare part number only.

        SecturaFAB requires uniqueness for create, so we mint a temporary
        RevNumber then immediately clear it — otherwise re-pushes would either
        reuse the old quote or show a revision suffix in the UI.
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

        # Strip revision so the Quote Number field is exactly the part key.
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

    def apply_item_categories(
        self,
        quote_id: str,
        *,
        bom_rows: list[dict[str, Any]] | None = None,
    ) -> list[str]:
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

        bom_hint: dict[str, str] = {}
        for row in bom_rows or []:
            key = str(row.get("part_no") or row.get("part_number") or "").strip()
            if key:
                from .qty_ops import normalize_part_key as _npk

                bom_hint[_npk(key)] = str(row.get("description") or "")
        counts = {"Cad": 0, "Linear": 0, "Component": 0}
        for it in items:
            from .qty_ops import normalize_part_key as _npk
            from .weld_ops import _desc_token

            if it.get("ProductType") in (300, "300", "assembly") or it.get("IsAssembly"):
                continue
            token = _npk(_desc_token(str(it.get("Description") or "")))
            hint = f"{it.get('Description') or ''} {bom_hint.get(token, '')}"
            cat = classify_sectura_item(hint)
            counts[cat] = counts.get(cat, 0) + 1
            it["ItemType"] = cat
            it["Category"] = cat
            if cat == "Linear":
                it["ProductType"] = 10
                it["IsLinear"] = True
                it["IsPlate"] = False
                it["IsPart"] = True
                it["Machine"] = "Saw"
                it["OperationCostList"] = []
                it["PrimaryTime"] = 0.0
                it["UnitPrimaryTime"] = 0.0
            elif cat == "Component":
                it["ProductType"] = 200
                it["IsLinear"] = False
                it["IsPlate"] = False
                it["IsPart"] = True
                it["Machine"] = None
                it["OperationCostList"] = []
                it["PrimaryTime"] = 0.0
                it["UnitPrimaryTime"] = 0.0
            else:
                it["ProductType"] = 100
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
        organization: str | None = None,
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
        org_name = (organization or "").strip() or os.getenv(
            "SECTURAFAB_ORGANIZATION", "Kannon Manufacturing"
        ).strip() or "Kannon Manufacturing"

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
                    "Organization": org_name,
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
                    "thickness": _sanitize_thickness_param(thickness),
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

    def _website_cookie_present(self) -> bool:
        """True only for a real non-empty SECTURAFAB_WEBSITE_COOKIE string."""
        cfg = getattr(self.client, "config", None)
        raw = getattr(cfg, "website_cookie", "") if cfg is not None else ""
        return isinstance(raw, str) and bool(raw.strip())

    def require_website_finish_auth(self) -> dict[str, Any]:
        """Diagnostic probe only. push_job never refuses for a missing cookie."""
        probe = self.client.probe_website_finish_auth()
        if isinstance(probe, dict) and probe.get("can_finish") is True:
            return probe
        raise SecturaFabWebsiteAuthError(
            (probe.get("gap") if isinstance(probe, dict) else None) or WEBSITE_AUTH_GAP
        )

    def _peek_item_count(self, quote_id: str) -> int:
        try:
            peek = self.client.get_json(f"v1/quote/{quote_id}")
        except SecturaFabApiError:
            return 0
        if not isinstance(peek, dict):
            return 0
        return len(list(peek.get("ItemList") or []))

    def _cadimport_rows(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [r for r in payload if isinstance(r, dict)]
        if isinstance(payload, dict):
            for key in ("Data", "data", "Results", "Items", "FileList", "rows"):
                val = payload.get(key)
                if isinstance(val, list):
                    return [r for r in val if isinstance(r, dict)]
        return []

    def _linear_catalog(self) -> list[dict[str, Any]]:
        cached = getattr(self, "_linear_product_cache", None)
        if cached is not None:
            return cached
        products: list[dict[str, Any]] = []
        try:
            page = 1
            while page <= 40:
                data = self.client.get_json(
                    f"v1/product/linear?pageNumber={page}&pageSize=200"
                )
                if isinstance(data, list):
                    products.extend(r for r in data if isinstance(r, dict))
                    break
                if not isinstance(data, dict):
                    break
                batch = list(data.get("Results") or [])
                products.extend(r for r in batch if isinstance(r, dict))
                if not data.get("HasNext"):
                    break
                page += 1
        except SecturaFabApiError:
            products = []
        self._linear_product_cache = products
        return products

    def _match_linear_sku(
        self,
        description: str,
        *,
        material: str | None,
        row: dict[str, Any] | None = None,
    ) -> tuple[str | None, str | None, str | None]:
        product, note = pick_closest_linear_product(
            self._linear_catalog(),
            description=description,
            material=material,
            row=row,
        )
        if not product:
            return None, None, note
        pid = str(product.get("ID") or "") or None
        sku = str(
            product.get("ProductName")
            or product.get("SKU")
            or product.get("ProductCode")
            or ""
        ) or None
        return pid, sku, note

    def classify_cadimport_rows(
        self,
        rows: list[dict[str, Any]],
        *,
        default_material: str,
        default_thickness: str,
        bom_rows: list[dict[str, Any]] | None,
        library: dict[str, Any] | None,
        extra_pdfs: list[Path] | None,
        qty: int = 1,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Cad / Linear / Component + closest ProductID/SKU. A36 only if no grade."""
        from quote_core.part_materials import (
            build_part_material_map,
            lookup_part_material,
        )

        notes: list[str] = []
        library = library or {}
        purchased = find_purchased_part_keys(
            library_folder=library.get("folder"),
            related_pdf_names=list(library.get("related_pdfs") or []),
            bom_rows=bom_rows,
        )
        part_materials = build_part_material_map(
            library_folder=library.get("folder"),
            related_pdf_names=list(library.get("related_pdfs") or []),
            extra_pdfs=extra_pdfs,
        )
        classified: list[dict[str, Any]] = []
        counts = {"Cad": 0, "Linear": 0, "Component": 0}
        for row in rows:
            name = row_name(row)
            cat = classify_sectura_item(name)
            token = name.split()[0] if name else ""
            compact = {k.replace("-", ""): v for k, v in purchased.items()}
            if token in purchased or token.replace("-", "") in compact:
                cat = "Component"
            pm = lookup_part_material(part_materials, name)
            material = default_material
            thickness: str | float = default_thickness
            if pm and pm.material:
                material = pm.material
            elif pm is None and default_material == "A36":
                notes.append(
                    f"A36 on {name[:40]!r} — drawing named no grade"
                )
            if pm and pm.thickness_in is not None:
                thickness = _sanitize_thickness_param(pm.thickness_in)
            product_id = None
            sku = None
            machine = "Laser" if cat == "Cad" else None
            if cat == "Linear":
                machine = "Saw"
                product_id, sku, mismatch = self._match_linear_sku(
                    name, material=material, row=row
                )
                if mismatch:
                    notes.append(f"WARNING: {mismatch}")
            row_qty = _row_qty(row)
            if row_qty <= 0:
                row_qty = max(1, int(qty or 1))
            overlaid = overlay_classified_row(
                row,
                category=cat,
                material=material,
                thickness=thickness,
                product_id=product_id,
                sku=sku,
                qty=row_qty,
                machine=machine,
            )
            classified.append(overlaid)
            counts[cat] = counts.get(cat, 0) + 1
            row_id = str(overlaid.get("ID") or overlaid.get("ItemID") or EMPTY_GUID)
            try:
                self.client.cadimport_set_part_mode(
                    row_id=row_id, part_mode=int(overlaid["PartMode"])
                )
                self.client.cadimport_update_data(overlaid)
            except (SecturaFabApiError, SecturaFabWebsiteAuthError) as exc:
                notes.append(
                    f"WARNING: CadImport classify post failed for {name[:40]!r}: {exc}"
                )
        notes.append(
            f"Classified CAD Files kids — Cad: {counts['Cad']}, "
            f"Linear: {counts['Linear']}, Component: {counts['Component']}"
        )
        return classified, notes

    def seed_cadimport_rows(
        self,
        *,
        cad_files: list[Path],
        takeoff: dict[str, Any] | None,
        bom_rows: list[dict[str, Any]] | None,
        part_key: str,
        qty: int,
    ) -> list[dict[str, Any]]:
        """Build grid rows when CadImport/Data is empty (no live import session)."""
        rows: list[dict[str, Any]] = []
        stp = (takeoff or {}).get("stp_summary") or {}
        solids = list(stp.get("top_solids") or [])
        if solids:
            for solid in solids:
                desc = str(
                    solid.get("name")
                    or solid.get("part_no")
                    or solid.get("label")
                    or part_key
                )
                rows.append(
                    {
                        "ErrorStatus": 0,
                        "Qty": max(1, int(solid.get("qty") or qty or 1)),
                        "Name": desc,
                        "Description": desc,
                        "FileName": cad_files[0].name if cad_files else "",
                    }
                )
        if not rows and bom_rows:
            for bom in bom_rows:
                desc = str(
                    bom.get("description")
                    or bom.get("part_no")
                    or bom.get("part")
                    or ""
                )
                try:
                    bqty = int(float(bom.get("qty") or bom.get("quantity") or qty or 1))
                except (TypeError, ValueError):
                    bqty = max(1, int(qty or 1))
                if not desc:
                    continue
                rows.append(
                    {
                        "ErrorStatus": 0,
                        "Qty": max(1, bqty),
                        "Name": desc,
                        "Description": desc,
                        "FileName": cad_files[0].name if cad_files else "",
                    }
                )
        if not rows:
            name = part_key or (cad_files[0].stem if cad_files else "part")
            rows.append(
                {
                    "ErrorStatus": 0,
                    "Qty": max(1, int(qty or 1)),
                    "Name": name,
                    "Description": name,
                    "FileName": cad_files[0].name if cad_files else "",
                }
            )
        return rows

    def finish_cad_files(
        self,
        *,
        quote_id: str,
        cad_files: list[Path],
        material: str,
        thickness: str,
        qty: int,
        takeoff: dict[str, Any] | None,
        bom_rows: list[dict[str, Any]] | None,
        library: dict[str, Any] | None,
        extra_pdfs: list[Path] | None,
        part_key: str,
    ) -> list[str]:
        """CAD Files: dialog → upload STEP → classify kids → Finish."""
        notes: list[str] = []
        try:
            self.client.get_item_add_view(quote_id, item_type="dxf")
            notes.append("Opened CAD Files dialog (GetItem_AddView ItemType=dxf)")
        except SecturaFabWebsiteAuthError:
            raise
        except SecturaFabApiError as exc:
            notes.append(f"WARNING: GetItem_AddView returned {exc}")

        open_files = []
        try:
            form_files = []
            for path in cad_files:
                fh = path.open("rb")
                open_files.append(fh)
                form_files.append(("files", (path.name, fh, _mime_for(path))))
            self.client.upload_item_dxf_files(form_files, quote_id=quote_id)
            notes.append(
                f"Uploaded CAD via /CadImport/UploadItem_DXFFiles: {cad_files[0].name}"
            )
        finally:
            for fh in open_files:
                fh.close()

        try:
            self.client.cadimport_set_units("inch")
        except (SecturaFabApiError, SecturaFabWebsiteAuthError) as exc:
            notes.append(f"WARNING: CadImport SetUnits failed: {exc}")

        data_rows = self._cadimport_rows(self.client.cadimport_data())
        if not data_rows:
            data_rows = self.seed_cadimport_rows(
                cad_files=cad_files,
                takeoff=takeoff,
                bom_rows=bom_rows,
                part_key=part_key,
                qty=qty,
            )
            notes.append(
                "CadImport/Data was empty — seeded FileList from STEP/BOM names"
            )
        classified, class_notes = self.classify_cadimport_rows(
            data_rows,
            default_material=material,
            default_thickness=thickness,
            bom_rows=bom_rows,
            library=library,
            extra_pdfs=extra_pdfs,
            qty=qty,
        )
        notes.extend(class_notes)
        self.client.add_item_dxf_files(
            quote_id=quote_id,
            file_list=classified,
            item_id=EMPTY_GUID,
            customer_material=False,
        )
        notes.append(
            f"Finish POST /Quote/AddItem_DXFFiles ({len(classified)} FileList row(s)) "
            f"— laser/saw packs come from Finish, not grafted Profile"
        )
        return notes

    def finish_pdf_files(
        self,
        *,
        quote_id: str,
        pdf_files: list[Path],
        material: str,
        thickness: str,
        qty: int,
        description: str,
    ) -> list[str]:
        """Image Files Finish: POST /Quote/AddItem_PDFFiles."""
        notes: list[str] = []
        try:
            self.client.get_item_add_view(quote_id, item_type="pdf")
            notes.append("Opened Image Files dialog (GetItem_AddView ItemType=pdf)")
        except SecturaFabWebsiteAuthError:
            raise
        except SecturaFabApiError as exc:
            notes.append(f"WARNING: GetItem_AddView(pdf) returned {exc}")

        file_list = []
        open_files = []
        try:
            form_files = []
            for path in pdf_files:
                fh = path.open("rb")
                open_files.append(fh)
                form_files.append(("files", (path.name, fh, _mime_for(path))))
                file_list.append(
                    {
                        "ErrorStatus": 0,
                        "Qty": max(1, int(qty or 1)),
                        "Name": description or path.stem,
                        "FileName": path.name,
                        "Machine": "Laser",
                        "Material": material,
                        "Thickness": thickness,
                        "Thickness_Units": "inch",
                    }
                )
            self.client.add_item_pdf_files(
                quote_id=quote_id,
                file_list=file_list,
                item_id=EMPTY_GUID,
                customer_material=False,
                files=form_files,
            )
        finally:
            for fh in open_files:
                fh.close()
        notes.append(
            "Image Files Finish POST /Quote/AddItem_PDFFiles: "
            + ", ".join(p.name for p in pdf_files)
        )
        return notes

    def add_loose_linears(
        self,
        *,
        quote_id: str,
        description: str,
        material: str,
        qty: int,
        length: float | None = None,
    ) -> list[str]:
        """Long: POST /Quote/AddItem_Linear for a job that is itself a linear."""
        notes: list[str] = []
        product_id, sku, mismatch = self._match_linear_sku(
            description, material=material
        )
        if mismatch:
            notes.append(f"WARNING: {mismatch}")
        if not product_id:
            raise SecturaFabApiError(
                "Loose linear has no matching ProductID/SKU in the catalog"
            )
        self.client.add_item_linear(
            quote_id=quote_id,
            product_id=product_id,
            qty=qty,
            length=length,
            material=material,
            machine="Saw",
            name=description,
        )
        notes.append(
            f"Long POST /Quote/AddItem_Linear SKU={sku or product_id} "
            f"qty={qty} length={length}"
        )
        return notes

    def nest_after_finish(self, quote_id: str, *, item_count: int) -> list[str]:
        """UI nest first; documented public Nest API if the website nest 302s."""
        notes: list[str] = []
        nest_type = "single" if item_count <= 1 else "multi"
        try:
            self.client.nest_quote_edit(quote_id)
            notes.append("Nest POST /Quote/NestQuote_Edit")
        except SecturaFabWebsiteAuthError:
            try:
                self.client.nest_quote_api(quote_id, nest_type=nest_type)
                notes.append(
                    f"Nest POST /api/v1/Nest/quote/{quote_id}/{nest_type} "
                    "(website NestQuote_Edit needs session — used documented public nest)"
                )
            except SecturaFabApiError as exc:
                notes.append(f"WARNING: Nest failed: {exc}")
                return notes
        except SecturaFabApiError as exc:
            notes.append(f"WARNING: NestQuote_Edit failed: {exc}")
            try:
                self.client.nest_quote_api(quote_id, nest_type=nest_type)
                notes.append(f"Nest POST /api/v1/Nest/quote/{quote_id}/{nest_type}")
            except SecturaFabApiError as exc2:
                notes.append(f"WARNING: Public nest failed: {exc2}")
                return notes
        notes.extend(self._renest_linear_stock_240(quote_id))
        return notes

    def _renest_linear_stock_240(self, quote_id: str) -> list[str]:
        """240 vs 480 is StockList.StockLength / stock Length — not a nest POST field."""
        notes: list[str] = []
        try:
            nests = self.client.get_json(f"v1/Nest?quoteID={quote_id}&pageSize=50")
        except SecturaFabApiError:
            return notes
        results = nests.get("Results") if isinstance(nests, dict) else nests
        stock_ids: list[str] = []
        if isinstance(results, list):
            for task in results:
                if not isinstance(task, dict):
                    continue
                for key in ("StockID", "StockList", "ProductID"):
                    val = task.get(key)
                    if isinstance(val, str) and val:
                        stock_ids.append(val)
        saw_480 = False
        try:
            quote = self.client.get_json(f"v1/quote/{quote_id}")
        except SecturaFabApiError:
            quote = {}
        stock_list = []
        if isinstance(quote, dict):
            stock_list = list(quote.get("StockList") or [])
        for stock in stock_list:
            if not isinstance(stock, dict):
                continue
            length = stock.get("StockLength", stock.get("Length"))
            try:
                length_f = float(length)
            except (TypeError, ValueError):
                continue
            if abs(length_f - 480.0) < 0.5:
                saw_480 = True
                stock["StockLength"] = 240
                stock["Length"] = 240
                sid = stock.get("ID")
                if sid:
                    try:
                        self.client.request(
                            "POST",
                            f"v1/stock/{sid}",
                            json={**stock, "Length": 240, "StockLength": 240},
                        )
                    except SecturaFabApiError as exc:
                        notes.append(f"WARNING: Could not write stock 240: {exc}")
        if saw_480:
            try:
                self.client.nest_quote_multipart_renest(quote_id)
                notes.append(
                    "Linear stock was 480 — set 240 and POST /Quote/NestQuoteMultiPart_Renest"
                )
            except (SecturaFabWebsiteAuthError, SecturaFabApiError) as exc:
                notes.append(
                    f"WARNING: Stock was 480; renest to 240 failed ({exc}). "
                    "240 vs 480 is StockList.StockLength, not a nest POST field"
                )
        return notes

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
        quote_id: str | None = None
        quote_number: str | None = None
        quote_request_id: str | None = None
        try:
            part_key = _resolve_part_key(
                title=title,
                pdf_filename=pdf_filename,
                library=(takeoff or {}).get("library") or {},
                bom_config=(takeoff or {}).get("bom_config"),
                pdf_path=pdf_path,
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

            job_pdf = Path(pdf_path) if pdf_path else None
            has_job_pdf = bool(job_pdf and job_pdf.is_file())
            can_populate_items = bool(cad) or (
                bool(bom_rows) and bool(library.get("folder"))
            ) or has_job_pdf
            if not can_populate_items:
                msg = (
                    "Cannot push: no STEP/STP, no library BOM path, and no job PDF "
                    "on disk to build ItemList."
                )
                notes.append(msg)
                return PushResult(
                    ok=False,
                    error=msg,
                    notes=notes,
                    status="failed",
                    last_error=msg,
                )

            memo = _weld_memo(times, takeoff)
            material, thickness, mat_notes = _resolve_push_material_thickness(
                takeoff=takeoff,
                stp_path=stp,
                pdf_path=job_pdf,
            )
            notes.extend(mat_notes)
            machine = _default_machine()
            thickness = _sanitize_thickness_param(thickness)
            loose_linear = (not cad) and classify_sectura_item(
                title or part_key or ""
            ) == "Linear"
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
            # TYCROP → Propell; Cummins Clean Fuel → Cummins Clean Fuel Technologies.
            organization_name = detect_organization(
                pdf_path=job_pdf,
                library_folder=library.get("folder"),
                extra_paths=list(library.get("searched_roots") or []),
            )
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
                    organization=organization_name,
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

            # Always create a brand-new quote. Display number is bare part key
            # (no "PN " prefix; temp RevNumber is cleared so the UI stays clean).
            quote_number = self.allocate_quote_number(part_key)
            raw_title = (
                extract_assembly_description(
                    part_key=part_key,
                    pdf_path=Path(pdf_path) if pdf_path else None,
                    library_folder=library.get("folder"),
                    related_pdf_names=list(library.get("related_pdfs") or []),
                )
                or title_from_library_folder(title, part_key=part_key)
                or title_from_job_title(title, part_key=part_key)
            )
            quote_description = format_assembly_description(part_key, raw_title)
            if raw_title:
                desc_note = f"Quote Description from assembly drawing: {quote_description}"
            else:
                desc_note = f"Quote Description from job title: {quote_description}"
            quote_id = self.create_quote(
                quote_number=quote_number,
                description=quote_description or "",
                memo="",
                quote_request_id=quote_request_id,
            )
            notes.append(f"Created SecturaFAB quote {quote_number}")
            notes.append(desc_note)
            # Organization before CAD/Profile — later full-quote POSTs can wipe ops.
            if organization_name:
                notes.extend(
                    apply_quote_organization(
                        self.client,
                        quote_id,
                        organization_name=organization_name,
                    )
                )

            extra_pdfs = [job_pdf] if has_job_pdf else None
            used_finish = False
            used_step = False
            used_pdf_shell = False
            # Default = working main push (quickAddCAD). Finish is additive
            # only when a real website cookie is present.
            if self._website_cookie_present():
                try:
                    if cad:
                        notes.extend(
                            self.finish_cad_files(
                                quote_id=quote_id,
                                cad_files=cad,
                                material=material,
                                thickness=thickness,
                                qty=qty,
                                takeoff=takeoff,
                                bom_rows=bom_rows,
                                library=library,
                                extra_pdfs=extra_pdfs,
                                part_key=part_key,
                            )
                        )
                        uploaded.extend(p.name for p in cad)
                    elif loose_linear:
                        notes.extend(
                            self.add_loose_linears(
                                quote_id=quote_id,
                                description=quote_description or title or part_key,
                                material=material,
                                qty=qty,
                            )
                        )
                    elif drawings or has_job_pdf:
                        pdfs = list(drawings) if drawings else []
                        if has_job_pdf and job_pdf not in pdfs:
                            pdfs.insert(0, job_pdf)
                        if pdfs:
                            notes.extend(
                                self.finish_pdf_files(
                                    quote_id=quote_id,
                                    pdf_files=pdfs,
                                    material=material,
                                    thickness=thickness,
                                    qty=qty,
                                    description=quote_description or title,
                                )
                            )
                            uploaded.extend(p.name for p in pdfs)
                    if self._peek_item_count(quote_id) > 0:
                        used_finish = True
                    else:
                        notes.append(
                            "WARNING: Finish produced 0 ItemList lines — "
                            "falling back to working push"
                        )
                except (
                    SecturaFabApiError,
                    SecturaFabWebsiteAuthError,
                    ValueError,
                    OSError,
                ) as exc:
                    if self._peek_item_count(quote_id) > 0:
                        notes.append(
                            f"WARNING: Finish errored after creating items ({exc}); "
                            "keeping Finish quote"
                        )
                        used_finish = True
                    else:
                        notes.append(
                            f"WARNING: Finish failed ({exc}); "
                            "falling back to working push"
                        )
            else:
                notes.append(
                    "Website cookie not set — using working Sectura push (quickAddCAD)"
                )

            if used_finish:
                notes.extend(ensure_imperial_item_units(self.client, quote_id))
                notes.extend(
                    apply_bom_quantities(
                        self.client,
                        quote_id,
                        bom_rows=bom_rows,
                        part_key=part_key,
                    )
                )
                peek_count = self._peek_item_count(quote_id)
                notes.extend(
                    self.nest_after_finish(quote_id, item_count=peek_count or 1)
                )
                notes.extend(
                    ensure_weld_ops(
                        self.client,
                        quote_id,
                        times=times,
                        part_key=part_key,
                    )
                )
                notes.extend(ensure_imperial_item_units(self.client, quote_id))
            else:
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
                    notes.extend(self.apply_item_categories(quote_id, bom_rows=bom_rows))
                    notes.extend(
                        bind_linear_product_ids(
                            self.client,
                            quote_id,
                            material=material,
                            bom_rows=bom_rows,
                        )
                    )
                    step_detail = self.client.get_json(f"v1/quote/{quote_id}")
                    step_items = list(step_detail.get("ItemList") or [])
                    use_assembly = needs_assembly_structure(step_items, bom_rows)
                    if use_assembly:
                        notes.extend(
                            ensure_assembly_root(
                                self.client,
                                quote_id,
                                part_key=part_key,
                                description=quote_description,
                            )
                        )
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
                        notes.extend(
                            relink_assembly_children(
                                self.client, quote_id, part_key=part_key
                            )
                        )
                        notes.append(
                            f"Skipped UpdateItem_Part on STEP assembly (seed {material} @ "
                            f"{thickness}\") — avoids delayed CAD wipe of ItemList"
                        )
                    else:
                        notes.append(
                            "Single-solid STEP — left as Part (no Assembly conversion)"
                        )
                        notes.append(
                            f"Skipped UpdateItem_Part on single-part STEP (seed {material} @ "
                            f"{thickness}\") — no grafted Profile"
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
                    notes.append(
                        "Skipped grafted Profile — laser pack left unset "
                        "(Finish / Image Files only)"
                    )
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
                            assembly_description=quote_description,
                        )
                    )
                elif has_job_pdf:
                    from .pdf_assembly_ops import build_single_pdf_quote

                    used_pdf_shell = True
                    notes.append(
                        "Building single-PDF quote (no STEP / no library BOM) from "
                        f"{job_pdf.name}"
                    )
                    notes.extend(
                        build_single_pdf_quote(
                            self.client,
                            quote_id=quote_id,
                            part_key=part_key,
                            pdf_path=job_pdf,
                            material=material,
                            thickness=thickness,
                            machine=machine,
                            qty=qty,
                            description=quote_description or title,
                        )
                    )
                    uploaded.append(job_pdf.name)
                else:
                    msg = (
                        "No STEP/STP, no BOM/library PDF assembly, and no job PDF — "
                        "refusing empty drawings-only quote"
                    )
                    notes.append(msg)
                    return PushResult(
                        ok=False,
                        error=msg,
                        notes=notes,
                        quote_id=quote_id,
                        quote_number=quote_number,
                        quote_request_id=quote_request_id,
                        created_new_quote=True,
                        uploaded_files=uploaded,
                        item_count=0,
                        status="failed",
                        last_error=msg,
                        attempts=createfile_attempts,
                    )

                notes.extend(
                    ensure_weld_ops(
                        self.client,
                        quote_id,
                        times=times,
                        part_key=part_key,
                    )
                )
                if used_step or used_pdf_shell or (bom_rows and library.get("folder")):
                    try:
                        notes.extend(
                            finalize_quote_ops(
                                self.client,
                                quote_id,
                                material=material,
                                thickness=thickness,
                                times=times,
                                part_key=part_key,
                                bom_rows=bom_rows,
                                attach_profile=False,
                            )
                        )
                    except SecturaFabApiError as exc:
                        if exc.status_code in {502, 503, 504}:
                            notes.append(
                                f"WARNING: Finalize hit transient {exc.status_code}; "
                                "re-checking quote ItemList"
                            )
                        else:
                            raise
                if used_pdf_shell or used_step or (bom_rows and library.get("folder")):
                    notes.append(
                        "Skipped grafted Profile — laser pack left unset "
                        "(Finish / Image Files only)"
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

            final_count = (
                int(item_count)
                if item_count is not None
                else (len(item_list) if item_list else 0)
            )
            if final_count <= 0:
                msg = (
                    "SecturaFAB quote has 0 line items after import — "
                    "push marked failed (empty ItemList)"
                )
                notes.append(msg)
                return PushResult(
                    ok=False,
                    error=msg,
                    notes=notes,
                    quote_id=quote_id,
                    quote_number=stored_number,
                    quote_request_id=quote_request_id,
                    created_new_quote=True,
                    uploaded_files=uploaded,
                    item_count=0,
                    ready=False,
                    status="failed",
                    last_error=msg,
                    attempts=createfile_attempts,
                )

            return PushResult(
                ok=True,
                quote_id=quote_id,
                quote_number=stored_number,
                quote_request_id=quote_request_id,
                created_new_quote=True,
                uploaded_files=uploaded,
                item_count=final_count,
                notes=notes,
                ready=ready,
                status="complete",
                attempts=createfile_attempts,
            )
        except (SecturaFabApiError, SecturaFabWebsiteAuthError, ValueError, OSError) as exc:
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
                        "quote_id": quote_id,
                        "quote_number": quote_number,
                    }
                )
            return PushResult(
                ok=False,
                error=err,
                notes=notes,
                uploaded_files=uploaded,
                quote_id=quote_id,
                quote_number=quote_number,
                quote_request_id=quote_request_id,
                created_new_quote=bool(quote_id),
                status="failed",
                attempts=createfile_attempts,
                last_error=err,
            )
