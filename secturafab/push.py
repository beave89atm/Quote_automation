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
    is_drawing_boilerplate_title,
    is_child_part_title,
    is_material_callout_title,
    is_nested_child_weldment_title,
    title_from_stp_takeoff,
)

from .browser_session import CHROME_SESSION_REQUIRED, effective_website_cookie
from .item_desc import (
    format_assembly_description,
    format_cad_description,
    format_linear_description,
    format_quote_header_description,
    is_bare_part_number,
    match_bom_part_no,
    normalize_part_token,
    title_from_bom_family,
    title_from_job_title,
    title_from_library_folder,
)
from .linear_ops import bind_linear_product_ids
from .line_item_ops import (
    count_linear_get_misses,
    finish_produced_gold,
    item_has_grafted_saw_tags,
    item_has_laser_pack,
    item_has_pr_tag,
    item_has_saw_pack,
    persist_classified_item_fields,
    retype_linears_to_pt10_keep_persist,
)
from .qa_harness import evaluate_quote_get

from .assembly_ops import (
    ensure_assembly_root,
    needs_assembly_structure,
    relink_assembly_children,
)
from .client import SecturaFabApiError, SecturaFabClient
from .component_ops import ensure_purchased_components, find_purchased_part_keys
from .finalize_ops import finalize_quote_ops
from .imperial_ops import ensure_imperial_item_units
from .org_ops import apply_quote_organization, persist_quote_header
from .profile_ops import ensure_laser_profile_ops  # imported for tests; push no longer grafts
from .qty_ops import apply_bom_quantities, refresh_bom_rows_for_push
from .quotes import QuoteService
from .website import (
    EMPTY_GUID,
    WEBSITE_AUTH_GAP,
    WEBSITE_SESSION_EXPIRED,
    SecturaFabWebsiteAuthError,
    count_cad_product_type,
    is_tenant_guid,
    count_linear_product_type,
    cadimport_filelist_exploded,
    empty_griddxf_explode_miss,
    cadimport_payload_preview,
    client_antiforgery_extracted,
    filelist_has_nested_titles,
    filelist_id_fields_present,
    filelist_is_assembly_only,
    filelist_leaf_noun_names,
    filelist_row_is_leaf_noun,
    is_nested_assembly_name,
    nested_assembly_id_list,
    overlay_filelist_ids,
    inventory_location_from_html,
    filelist_from_cadimport_upload,
    finish_filelist_kids,
    is_raw_step_upload_row,
    linear_add_product_type,
    linear_bind_fields,
    linear_lookup_rows,
    linear_website_product_type,
    overlay_classified_row,
    pick_closest_linear_product,
    quote_item_rows,
    row_name,
)
from .weld_ops import ensure_weld_ops

# CreateFile outage retry (SecturaFAB DB "underlying provider failed on Open").
CREATEFILE_RETRY_INTERVAL_S = 300.0
CREATEFILE_RETRY_MAX_S = 48 * 3600.0
# Nested ASSY/WELDMENT /part/create passes after the first explode (28110-2).
CADIMPORT_EXPLODE_MAX_PASSES = 5


def _log_part_create_payload_empty(notes: list[str], client: Any) -> None:
    """Bind-time /part/create t.List emptiness, form shape, name tokens."""
    idata = getattr(client, "_part_create_internaldata_empty", None)
    img = getattr(client, "_part_create_imagestring_empty", None)
    if isinstance(idata, bool):
        line = "internaldata_empty=" + ("true" if idata else "false")
        if line not in notes:
            notes.append(line)
    if isinstance(img, bool):
        line = "imagestring_empty=" + ("true" if img else "false")
        if line not in notes:
            notes.append(line)
    payload = getattr(client, "_part_create_payload", None)
    if isinstance(payload, dict):
        n = int(payload.get("n") or 0)
        if n:
            notes.append(
                f"internaldata_empty_n={int(payload.get('internaldata_empty_n') or 0)}/{n}"
            )
            notes.append(
                f"imagestring_empty_n={int(payload.get('imagestring_empty_n') or 0)}/{n}"
            )
            notes.append(
                f"internaldata_nonempty_n={int(payload.get('internaldata_nonempty_n') or 0)}"
            )
    shape = getattr(client, "_part_create_form_shape", None)
    if isinstance(shape, dict) and shape:
        notes.append(f"part_create_idlist_shape={shape.get('idlist_shape') or '?'}")
        notes.append(f"part_create_height_type={shape.get('height_type') or '?'}")
        notes.append(f"part_create_width_type={shape.get('width_type') or '?'}")
        notes.append(
            "part_create_height_zero="
            + ("true" if shape.get("height_zero") else "false")
        )
        notes.append(
            "part_create_width_zero="
            + ("true" if shape.get("width_zero") else "false")
        )
    img_hw = getattr(client, "_part_create_img_hw", None)
    if isinstance(img_hw, bool):
        notes.append("part_create_img_hw=" + ("true" if img_hw else "false"))
    via = getattr(client, "_part_create_via", None)
    if isinstance(via, str) and via:
        notes.append(f"part_create_via={via}")
    from_edit = getattr(client, "_part_create_from_edit", None)
    if isinstance(from_edit, bool):
        notes.append(
            "part_create_from_edit=" + ("true" if from_edit else "false")
        )
    af = getattr(client, "_part_create_af_present", None)
    if isinstance(af, bool):
        notes.append("part_create_af_present=" + ("true" if af else "false"))
    tokens = getattr(client, "_part_create_name_tokens", None)
    if isinstance(tokens, dict) and tokens:
        for key in (
            "tlist_name_root_n",
            "tlist_name_jobpn_n",
            "tlist_name_other_n",
            "tlist_partname_root_n",
            "tlist_partname_jobpn_n",
            "tlist_partname_other_n",
            "tlist_filename_root_n",
            "tlist_filename_jobpn_n",
            "tlist_filename_other_n",
        ):
            if key in tokens:
                notes.append(f"{key}={int(tokens.get(key) or 0)}")


def _part_create_fail_note(exc: BaseException) -> str:
    """403 LogOnUrl is not Login; never interpolate cookies or AF tokens."""
    status = getattr(exc, "status_code", None)
    body = getattr(exc, "body", None)
    if isinstance(body, dict) and (
        "LogOnUrl" in body or str(body.get("Error") or "")
    ):
        return (
            f"www {status} LogOnUrl login_redirect={body.get('login_redirect')} "
            f"access_denied={body.get('access_denied')} (not Login; "
            "GetItem_AddView was 200)"
        )
    if status:
        return f"www {status}"
    return type(exc).__name__

ProgressCallback = Callable[[dict[str, Any]], None]


_QUOTE_REV_SUFFIX_RE = re.compile(r"(?i)[\s_-]*R\d{2}$")
# Cummins sheet/rev on a letter PN (EHB3112-1) — not shop 105918-1.
_ALPHA_JOB_SHEET_REV_RE = re.compile(r"^([A-Z]{2,4}\d{3,})-1$", re.I)


def _is_quote_number_token(key: str) -> bool:
    """True for a Sectura QuoteNumber (P001545 / 35145-1), not a weldment title."""
    text = str(key or "").strip()
    if not text or any(ch.isspace() for ch in text):
        return False
    upper = text.upper()
    if any(tok in upper for tok in ("WELDMENT", "ASSEMBLY", "FRAME PLATE")):
        return bool(re.fullmatch(r"[A-Z]{1,3}\d{4,}(?:-[A-Z0-9]+)?", upper))
    return True


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
    # Live EHB3112: drawing/file EHB3112-1 must not become QuoteNumber.
    sheet = _ALPHA_JOB_SHEET_REV_RE.fullmatch(key)
    if sheet:
        return sheet.group(1)
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
    "SLUG",
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
    r"\b(ELBOW|COUPLING|NIPPLE|PLUG|PIPE\s+CAP|FITTING|REDUCER|UNION|FILLER\s*-?\s*NECK)\b",
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


def _plate_thickness_in(description: str) -> float | None:
    """Plate/ring thickness in inches, or None (ignore NPT / angle SKUs)."""
    from quote_core.part_materials import _parse_thickness_token

    text = str(description or "")
    if re.search(r"\bNPT\b", text, re.I):
        return None
    if re.search(r"\bL\d", text, re.I):
        return None
    m = re.search(
        r"(?i)(?:^|[\s-])(\d+(?:\.\d+)?(?:\s+\d+/\d+)?|\d+/\d+)\s*"
        r"(?:\"|IN\b|INCH)?\s+(?:A\d|PLATE|RING|SQ|OUTSOURCE|DOMEX)",
        text,
    )
    if not m:
        return None
    token = re.sub(r"\s+", "", m.group(1))
    return _parse_thickness_token(token)


def _looks_like_formed_plate(description: str) -> bool:
    text = f" {str(description or '').upper()} "
    return any(h in text for h in (" FORMED ", " ROLLED ", " BENT PLATE "))


def _cad_plate_sheet_noun(description: str) -> bool:
    """Laser plate/sheet/gusset/mount/flat. CHANNEL PLATE is Cad, KICK CHANNEL is not.

    Kyle (105918-1): leftover Component is not the rule. TRIANGLE GUSSET is
    not Linear (ANGLE is a substring of TRIANGLE). FLAT BAR stays Linear.
    MOUNT CHANNEL stays Linear (structural channel, not a laser mount plate).
    """
    text = f" {str(description or '').upper()} "
    if re.search(r"\b(PLATE|GUSSET|SHEET)\b", text):
        return True
    if re.search(r"\bFLAT\b", text) and not re.search(r"\bFLAT\s+BAR\b", text):
        return True
    if re.search(r"\bMOUNT\b", text) and not re.search(
        r"\b(CHANNEL|TUBE|PIPE|BARS?|ANGLE|BEAM|HSS)\b", text
    ):
        return True
    return False


def classify_sectura_item(description: str) -> str:
    """
    Map a STEP/BOM description to SecturaFAB item category dropdown values:
    Cad | Linear | Component

    Plate/sheet/gusset/mount/flat = Cad. Tube/bar/angle/channel = Linear.
    Purchased fittings (elbow, coupling, plug, nipple, cap, filler neck) and
    hardware = Component. Component is checked before Linear so ``PIPE CAP``
    is not treated as a Linear pipe.

    Plate over 3/4 in is Component (no invented $). A formed plate that looks
    like an angle is still Cad. Hose guards / structural tube are Linear.

    Job 92 / 1001898-1 child-PDF locks win over LOM nouns (rolled 1001880-2
    is Cad; 14500-1 / 1005966-1 are outsource Component).
    """
    from .locked_1001898 import locked_category

    locked = locked_category(text=description)
    if locked:
        return locked
    text = f" {str(description or '').upper()} "
    # Collapse spaces so "KING PIN" and "KINGPIN" both match.
    compact = text.replace(" ", "").replace("-", "")
    if "HOSEGUARD" in compact or "HOSE GUARD" in text:
        return "Linear"
    if "HINGE" in text and "PLATE" not in text:
        return "Component"
    if (
        "WELDMENT" in text
        or "ASSEMBLY" in text
        or re.search(r"\bASSY\b", text)
        or re.search(r"\bASM\b", text)
        or " ASM," in text
        or " ASM " in text
    ):
        return "Assembly"
    if "KINGPIN" in compact:
        return "Component"
    if "FILLERNECK" in compact:
        return "Component"
    if any(h in text for h in _COMPONENT_HINTS) or _COMPONENT_WORD_RE.search(text):
        return "Component"
    thk = _plate_thickness_in(description)
    if thk is not None and thk > 0.75:
        return "Component"
    if _looks_like_formed_plate(description):
        return "Cad"
    if _cad_plate_sheet_noun(description):
        return "Cad"
    if any(h in text for h in _LINEAR_HINTS):
        return "Linear"
    return "Cad"


_HOLE_NOUN_RE = re.compile(
    r"(?i)(\d+(?:\s+\d+/\d+)?|\d+/\d+|\d+\.\d+)\s*(?:\"|IN)?\s*HOLES?"
)


_GUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _looks_like_product_id(value: str | None) -> bool:
    text = str(value or "").strip()
    return bool(text) and bool(_GUID_RE.fullmatch(text))


def _holes_from_noun(text: str) -> list[dict[str, Any]]:
    """Holes only when the drawing/BOM noun calls them out. Never invent."""
    from quote_core.part_materials import _parse_thickness_token

    holes: list[dict[str, Any]] = []
    for m in _HOLE_NOUN_RE.finditer(str(text or "")):
        dia = _parse_thickness_token(re.sub(r"\s+", "", m.group(1)))
        if dia and 0.1 <= dia <= 6.0:
            holes.append({"diameter": dia, "qty": 1})
    return holes


def _holes_from_takeoff_or_bom(
    takeoff: dict[str, Any] | None,
    bom_rows: list[dict[str, Any]] | None,
) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for row in bom_rows or []:
        pn = str(row.get("part_no") or row.get("part_number") or "").strip()
        noun = str(row.get("description") or "")
        holes = _holes_from_noun(f"{pn} {noun}")
        if pn and holes:
            out[pn] = holes
    for item in (takeoff or {}).get("items") or []:
        if not isinstance(item, dict):
            continue
        notes = str(item.get("joint_notes") or item.get("notes") or "")
        holes = _holes_from_noun(notes)
        if not holes:
            continue
        pn = str(item.get("part_no") or item.get("part_number") or "").strip()
        if pn:
            out.setdefault(pn, holes)
    return out


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


# Live UploadItem_DXFFiles: 20MB and 27MB HTTP 200; 32MB 106384-1 and
# 43MB 106687-1 Cloudflare 502. Do not invent chunked upload. Do not mint
# PDF-only as a SetPartMode stand-in. SetPartMode-on-grid is untested live.
CADIMPORT_UPLOAD_MAX_BYTES = 28 * 1024 * 1024


def cadimport_step_bytes(paths: list[Path] | None) -> int:
    biggest = 0
    for path in paths or []:
        try:
            biggest = max(biggest, int(path.stat().st_size))
        except OSError:
            continue
    return biggest


def cadimport_step_too_large(paths: list[Path] | None) -> bool:
    return cadimport_step_bytes(paths) > CADIMPORT_UPLOAD_MAX_BYTES


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
    if key == "aluminum_5052" or "5052" in label.upper() or "ALPL" in label.upper():
        return "5052-H32"
    if key == "aluminum_6061" or "6061" in label.upper():
        return "6061-T6"
    # Weight heuristics often mis-read title-block boilerplate ("ALUMINUM MATERIALS")
    # as the part material — do not seed SecturaFAB from weak aluminum guesses.
    if key in {"aluminum", "aluminium"} or (
        "aluminum" in label.lower() and "5052" not in label.upper() and "6061" not in label.upper()
    ):
        return "A36"
    if label:
        # SecturaFAB grades are typically bare codes like A36 / A572.
        grade = label.split()[0]
        if "A569" in grade.upper():
            return "A36"
        return grade
    named = _named_grade_from_takeoff(takeoff)
    if named:
        return named
    return "A36"


def _shop_material(material: str | None) -> str:
    """Grade from the drawing. A36 only when none is called out. Never A569."""
    text = str(material or "").strip()
    if not text or "A569" in text.upper():
        return "A36"
    upper = text.upper()
    if "5052" in upper or upper.startswith("ALPL"):
        return "5052-H32"
    if "A572" in upper or "PL025" in upper:
        # A572 / PL025-50K is a named grade — never overwrite to A36.
        return text if "A572" in upper else "A572 Grade 50"
    if "100K" in upper or upper == "100 K":
        return "100K"
    if "A1011" in upper:
        return text if "A1011" in text.upper() else "A1011"
    if "A519" in upper:
        return text if "A519" in text.upper() else "A519"
    return text


def _named_grade_from_blob(text: str | None) -> str | None:
    """A572 / PL025-50K / 5052-H32 called out on a child drawing or takeoff row."""
    upper = str(text or "").upper()
    if not upper:
        return None
    if "5052" in upper or "ALPL" in upper:
        return "5052-H32"
    if "A572" in upper or "PL025" in upper:
        return "A572 Grade 50"
    if "100K" in upper:
        return "100K"
    if "A1011" in upper:
        return "A1011"
    if "A519" in upper:
        return "A519"
    return None


def _named_grade_from_takeoff(takeoff: dict[str, Any] | None) -> str | None:
    """Named grade from takeoff / LOM child rows. A572 is not a seed."""
    if not isinstance(takeoff, dict):
        return None
    bits: list[str] = []
    drivers = takeoff.get("fitup_drivers") or {}
    if isinstance(drivers, dict):
        weight = drivers.get("weight_calc") or {}
        if isinstance(weight, dict):
            bits.append(str(weight.get("material_key") or ""))
            bits.append(str(weight.get("material_label") or ""))
        for note in drivers.get("notes") or []:
            bits.append(str(note))
    for key in ("notes", "flags"):
        for note in takeoff.get(key) or []:
            bits.append(str(note))
    from .item_desc import iter_takeoff_plate_rows

    for row in iter_takeoff_plate_rows(takeoff):
        bits.append(
            " ".join(
                str(row.get(k) or "")
                for k in (
                    "description",
                    "Description",
                    "material",
                    "Material",
                    "grade",
                    "noun",
                    "notes",
                )
            )
        )
    return _named_grade_from_blob(" ".join(bits))


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
    named = _named_grade_from_takeoff(takeoff) or _named_grade_from_blob(material)
    if named:
        material = named
    thickness = _sanitize_thickness_param(_default_thickness_in(takeoff, stp_path))
    known_from_pdf = False

    if pdf_path and Path(pdf_path).is_file():
        from quote_core.part_materials import extract_part_material_from_pdf

        try:
            pm = extract_part_material_from_pdf(pdf_path)
        except Exception as exc:  # noqa: BLE001 — corrupt/minimal test PDFs
            if named:
                notes.append(
                    f"Parent PDF material unread ({exc}) — using named grade {material} "
                    f"@ {thickness} from child drawings / takeoff"
                )
            else:
                notes.append(
                    f"WARNING: Could not read material/thickness from PDF ({exc}) — "
                    f"seeded {material} @ {thickness}; confirm in SecturaFAB"
                )
            pm = None
        if pm:
            child_named = named or _named_grade_from_blob(pm.material)
            if pm.material:
                if child_named and _shop_material(pm.material) == "A36":
                    material = child_named
                    notes.append(
                        f"Material from child drawings / takeoff: {material} "
                        f"(parent extract was {pm.material})"
                    )
                else:
                    material = pm.material
                known_from_pdf = True
                if not child_named or _shop_material(pm.material) != "A36":
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
                if named:
                    material = named
                    notes.append(
                        f"Material from child drawings / takeoff: {material}"
                    )
                else:
                    notes.append(
                        "WARNING: Drawing material grade not confidently identified — "
                        f"seeded {material}; confirm in SecturaFAB"
                    )
        elif not any("Could not read material" in n for n in notes):
            if named:
                notes.append(
                    f"Material from child drawings / takeoff: {material} @ {thickness}"
                )
            else:
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

    material = _shop_material(material)
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
    strong: list[str] = []
    weak: list[str] = []
    # Title-block DRAWING NUMBER is the search key in SecturaFAB — prefer it.
    if pdf_path:
        p = Path(pdf_path)
        if p.is_file():
            drawn = extract_drawing_number_from_pdf(p)
            if drawn and _is_quote_number_token(drawn):
                strong.append(_pn_quote_number(drawn) or drawn)
    for raw in (
        library.get("part_key"),
        Path(library["folder"]).name if library.get("folder") else None,
        extract_part_key(pdf_filename, title),
        title,
        pdf_filename,
    ):
        if not raw:
            continue
        extracted = extract_part_key(str(raw))
        if extracted and _is_quote_number_token(extracted):
            strong.append(_pn_quote_number(extracted) or extracted)
        stripped = str(raw).strip()
        if not stripped:
            continue
        upper = stripped.upper()
        if any(tok in upper for tok in ("WELDMENT", "ASSEMBLY", "FRAME PLATE")):
            continue
        stem = Path(stripped).stem if "." in stripped else stripped
        if stem:
            weak.append(stem)
    pool = strong or weak
    if not pool:
        return ""
    dashed = [c for c in pool if "-" in c]
    if dashed:
        picked = max(dashed, key=len)
        return _pn_quote_number(picked) or picked
    base = max(pool, key=len)
    dash = normalize_bom_config(bom_config)
    if dash and base and "-" not in base:
        return f"{base}-{dash}"
    return _pn_quote_number(base) or base


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
            desc = str(it.get("Description") or "")
            from secturafab.item_desc import match_bom_part_no

            pn = match_bom_part_no(desc, bom_rows)
            token = _npk(pn or _desc_token(desc))
            hint = f"{desc} {pn or ''} {bom_hint.get(token, '')}"
            cat = classify_sectura_item(hint)
            counts[cat] = counts.get(cat, 0) + 1
            it["ItemType"] = cat
            it["Category"] = cat
            if cat == "Linear":
                it["ProductType"] = linear_website_product_type(hint)
                it["IsLinear"] = True
                it["IsPlate"] = False
                it["IsPart"] = True
                it["Machine"] = "Saw"
            elif cat == "Component":
                it["ProductType"] = 200
                it["IsLinear"] = False
                it["IsPlate"] = False
                it["IsPart"] = True
                it["Machine"] = None
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
        """True when SECTURA_WEBSITE_COOKIE (env/file) is set. No Windows unwrap."""
        cfg = getattr(self.client, "config", None)
        return bool(effective_website_cookie(cfg))

    def _antiforgery_capture_notes(self) -> list[str]:
        """Bools + cookie name presence. Never token/cookie values."""
        notes: list[str] = []
        af = client_antiforgery_extracted(self.client)
        notes.append(f"af_extracted={str(af).lower()}")
        notes.append(f"has_antiforgery={str(af).lower()}")
        source = getattr(self.client, "_af_source", "") or ""
        if isinstance(source, str) and source:
            notes.append(f"af_source={source}")
        if getattr(self.client, "_quotes_tab_live", False) is True:
            notes.append("chrome_quotes_live=true")
        if getattr(self.client, "_cookie_quote_access_denied", False):
            notes.append("cookie_quote_layout=302_AccessDenied")
        diff = getattr(self.client, "_chrome_cookie_name_diff", None) or {}
        chrome_only = diff.get("chrome_only") if isinstance(diff, dict) else None
        if chrome_only:
            notes.append("chrome_cookie_names_only=" + ",".join(chrome_only))
        return notes

    def preflight_step_antiforgery(self, quote_id: str = "") -> list[str]:
        """Harvest AF before mint. Chrome Quotes DOM if cookie GET /Quote 302s."""
        notes: list[str] = []
        ensure_fn = getattr(type(self.client), "ensure_quote_antiforgery", None)
        if callable(ensure_fn):
            try:
                ensure_fn(self.client, quote_id)
            except (SecturaFabApiError, SecturaFabWebsiteAuthError, TypeError):
                pass
        notes.extend(self._antiforgery_capture_notes())
        source = getattr(self.client, "_af_source", "") or ""
        if source != "chrome_dom":
            notes.append(
                "chrome_dom required — not minting "
                "(cookie_quote_html is the wrong claims identity)"
            )
        return notes

    def require_website_finish_auth(self) -> dict[str, Any]:
        """Probe Finish auth. push_job fails closed if Finish 302s / no gold."""
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
        uploaded = filelist_from_cadimport_upload(payload)
        if uploaded:
            return uploaded
        if isinstance(payload, list):
            return [r for r in payload if isinstance(r, dict)]
        if isinstance(payload, dict):
            for key in ("Data", "data", "Results", "Items", "FileList", "rows", "List"):
                val = payload.get(key)
                if isinstance(val, list):
                    return [r for r in val if isinstance(r, dict)]
        return []

    def _dedupe_cadimport_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            from .website import filelist_row_id_fields

            fields = filelist_row_id_fields(row)
            key = str(
                fields.get("ID")
                or fields.get("FileID")
                or row.get("PartID")
                or (
                    f"{row.get('Name') or row.get('Description') or ''}|"
                    f"{fields.get('SourceDataID') or ''}|"
                    f"{id(row)}"
                )
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(row)
        return out

    def _cadimport_quote_query(
        self,
        quote_id: str,
        quote_request_id: str | None = None,
    ) -> dict[str, Any]:
        query: dict[str, Any] = {"ID": quote_id, "quoteID": quote_id}
        if quote_request_id:
            query["quoteRequestID"] = quote_request_id
            query["QuoteRequestID"] = quote_request_id
        return query

    def _collect_cadimport_grid(
        self,
        *,
        quote_id: str,
        upload_rows: list[dict[str, Any]] | None = None,
        quote_request_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """CadImport/Data + GetItem_AddView FileList after explode.

        GetDXFData 404s on www (live 34574-1). Do not poll a missing route.
        """
        bags: list[dict[str, Any]] = []
        query = self._cadimport_quote_query(quote_id, quote_request_id)
        fetchers = [
            lambda: self.client.cadimport_data(params=query),
            lambda: self.client.get_item_add_view(quote_id, item_type="dxf"),
        ]
        for fetch in fetchers:
            try:
                bags.extend(self._cadimport_rows(fetch()))
            except (SecturaFabApiError, SecturaFabWebsiteAuthError, TypeError, ValueError):
                continue
        if upload_rows:
            bags.extend(r for r in upload_rows if isinstance(r, dict))
        return self._dedupe_cadimport_rows(bags)

    def _explode_capture_notes(
        self,
        *,
        explode_passes: int,
        rows: list[dict[str, Any]],
        part_key: str,
        cad_filename: str,
    ) -> list[str]:
        leaves = filelist_leaf_noun_names(
            rows, part_key=part_key, cad_filename=cad_filename
        )
        sample = ",".join(leaves[:20])
        return [
            f"explode_passes={int(explode_passes)}",
            f"leaf_names={sample}",
        ]

    def _post_do_create_dxf_parts(
        self,
        *,
        quote_id: str,
        part_key: str,
        id_list: list[str],
        unit_list: list[str],
        location: str,
        keep_prior_on_empty: bool = False,
        prior_rows: list[dict[str, Any]] | None = None,
    ) -> tuple[list[dict[str, Any]], list[str], bool]:
        """Same DoCreateDXFParts POST /part/create. abort=True → stop exploding."""
        from .cadimport_js import CREATE_DXF_PARTS_FUNCTION, CREATE_DXF_PARTS_PATH

        notes: list[str] = []
        create_fn = getattr(self.client, "create_dxf_parts", None)
        source = getattr(self.client, "_af_source", "")
        af_extracted = client_antiforgery_extracted(self.client)
        if isinstance(source, str) and source == "cookie_quote_html":
            notes.append(
                "DoCreateDXFParts skipped — cookie_quote_html is the wrong "
                "claims identity (no cookie HTTP /part/create)"
            )
            return [], notes, True
        if isinstance(source, str) and source != "chrome_dom":
            notes.append(
                "DoCreateDXFParts skipped — af_extracted=false "
                "(chrome_dom required; no /part/create)"
            )
            return [], notes, True
        if not af_extracted:
            notes.append(
                "DoCreateDXFParts skipped — af_extracted=false "
                "(chrome_dom required; no /part/create)"
            )
            return [], notes, True
        if not (callable(create_fn) and id_list):
            if not id_list:
                notes.append(
                    "QuoteOrderEdit DoCreateDXFParts skipped — row has no "
                    "SourceDataID (IDList)"
                )
            return [], notes, True
        try:
            try:
                result = create_fn(
                    id_list,
                    unit_list,
                    location=location,
                    other_file_ids=[],
                    height=0,
                    width=0,
                    quote_id=quote_id,
                    quote_number=part_key,
                    replace_grid=not keep_prior_on_empty,
                )
            except TypeError:
                result = create_fn(
                    id_list,
                    unit_list,
                    location=location,
                    other_file_ids=[],
                    height=0,
                    width=0,
                )
        except (SecturaFabApiError, SecturaFabWebsiteAuthError, TypeError) as exc:
            from .cadimport_js import create_dxf_parts_xhr

            xhr = create_dxf_parts_xhr()
            notes.append(
                f"WARNING: {xhr.cite()} failed: {_part_create_fail_note(exc)}"
            )
            return [], notes, True
        via = getattr(self.client, "_part_create_via", "") or ""
        if isinstance(via, str) and via:
            notes.append(f"part_create_via={via}")
        exploded = self._cadimport_rows(result)
        if keep_prior_on_empty and (
            not exploded or not cadimport_filelist_exploded(
                exploded, part_key=part_key
            )
        ):
            notes.append("kept_prior_grid=true")
            if prior_rows:
                try:
                    from .chrome_cdp import (
                        bind_do_create_dxf_parts_success,
                        chrome_quotes_live,
                    )

                    if chrome_quotes_live():
                        bind = bind_do_create_dxf_parts_success(
                            prior_rows,
                            quote_id=quote_id or None,
                            quote_number=part_key or None,
                        )
                        if isinstance(bind, dict):
                            present = bool(bind.get("grid_present"))
                            self.client._grid_present = present
                            self.client._grid_dxf_row_count = int(
                                bind.get("grid_dxf_row_count") or 0
                            )
                except (TypeError, ValueError, OSError):
                    pass
            return [], notes, False
        present = getattr(self.client, "_grid_present", None)
        if isinstance(present, bool):
            notes.append(f"grid_present={'true' if present else 'false'}")
            if not present:
                notes.append(
                    "WARNING: #gridDXFParts kendo not on /Quote/EDIT "
                    "(click #but_dxf) — cookie GetItem_AddView is the "
                    "wrong document (live a64509d); not Finishing"
                )
                return exploded, notes, True
        n_list = getattr(self.client, "_part_create_list_len", None)
        if isinstance(n_list, (int, float)):
            notes.append(f"part_create_list_len={int(n_list)}")
        _log_part_create_payload_empty(notes, self.client)
        n_grid = getattr(self.client, "_grid_dxf_row_count", None)
        if isinstance(n_grid, (int, float)):
            notes.append(f"grid_dxf_row_count={int(n_grid)}")
        if empty_griddxf_explode_miss(
            grid_present=present if isinstance(present, bool) else None,
            n_grid=n_grid if isinstance(n_grid, (int, float)) else None,
            n_list=n_list if isinstance(n_list, (int, float)) else None,
        ):
            notes.append(
                "WARNING: empty #gridDXFParts / List=0 — not Finishing "
                "(empty #gridDXF createAllParts is the 34632-2 miss)"
            )
            return exploded, notes, True
        if not cadimport_filelist_exploded(exploded, part_key=part_key):
            notes.append(
                f"{CREATE_DXF_PARTS_FUNCTION} {CREATE_DXF_PARTS_PATH} had no "
                f"kid FileList ({cadimport_payload_preview(result)})"
            )
        return exploded, notes, False

    def _overlay_grid_filelist_ids(
        self,
        rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Fill missing ID/FileID from bound #gridDXFParts (chrome names, Python IDs empty)."""
        try:
            from .chrome_cdp import chrome_quotes_live, grid_dxf_parts_rows_from_quotes_tab

            if not chrome_quotes_live():
                return rows
            grid = grid_dxf_parts_rows_from_quotes_tab()
        except (TypeError, ValueError, OSError):
            return rows
        if not grid:
            return rows
        return overlay_filelist_ids(rows, grid)

    def _reexplode_nested_assemblies(
        self,
        *,
        quote_id: str,
        part_key: str,
        cad_filename: str,
        grid: list[dict[str, Any]],
        used_ids: set[str],
        location: str,
        first_pass: int,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Re-POST /part/create with nested *ASSY*/*WELDMENT* / unnamed IDs."""
        from .cadimport_js import CREATE_DXF_PARTS_FUNCTION, CREATE_DXF_PARTS_PATH

        notes: list[str] = []
        rows = self._overlay_grid_filelist_ids(list(grid))
        seen = set(used_ids)
        extra = 0
        max_extra = max(0, CADIMPORT_EXPLODE_MAX_PASSES - first_pass)
        while (
            filelist_is_assembly_only(
                rows, part_key=part_key, cad_filename=cad_filename
            )
            and extra < max_extra
        ):
            nested = nested_assembly_id_list(
                rows,
                part_key=part_key,
                cad_filename=cad_filename,
                used_ids=seen,
            )
            notes.append(f"nested_ids_found={len(nested)}")
            notes.append(f"used_ids={len(seen)}")
            notes.append(
                "id_fields_present="
                + filelist_id_fields_present(rows)
            )
            if not nested:
                if filelist_has_nested_titles(
                    rows, part_key=part_key, cad_filename=cad_filename
                ):
                    notes.append(
                        "WARNING: GATE WELDMENT / unnamed names present but "
                        "nested_ids_found=0 — FileList ID parse miss"
                    )
                    rows = self._overlay_grid_filelist_ids(rows)
                    nested = nested_assembly_id_list(
                        rows,
                        part_key=part_key,
                        cad_filename=cad_filename,
                        used_ids=seen,
                    )
                    notes.append(f"nested_ids_found={len(nested)}")
                    notes.append(
                        "id_fields_present="
                        + filelist_id_fields_present(rows)
                    )
            if not nested:
                notes.append(
                    "no nested assembly IDs left — FileList still "
                    "ASSY/WELDMENT only (live 28110-2 / 107877-1)"
                )
                break
            id_list = [sid for sid, _units in nested]
            unit_list = [units for _sid, units in nested]
            notes.append(
                f"QuoteOrderEdit {CREATE_DXF_PARTS_FUNCTION} "
                f"{CREATE_DXF_PARTS_PATH} re-explode "
                f"{len(id_list)} nested ASSY/WELDMENT/unnamed ID(s)"
            )
            exploded, pass_notes, abort = self._post_do_create_dxf_parts(
                quote_id=quote_id,
                part_key=part_key,
                id_list=id_list,
                unit_list=unit_list,
                location=location,
                keep_prior_on_empty=True,
                prior_rows=rows,
            )
            notes.extend(pass_notes)
            extra += 1
            seen.update(id_list)
            if abort:
                break
            if exploded:
                rows = self._dedupe_cadimport_rows(
                    list(exploded) + list(rows)
                )
                rows = self._overlay_grid_filelist_ids(rows)
            else:
                if "kept_prior_grid=true" not in " ".join(pass_notes):
                    notes.append("kept_prior_grid=true")
                break
        notes.extend(
            self._explode_capture_notes(
                explode_passes=first_pass + extra,
                rows=rows,
                part_key=part_key,
                cad_filename=cad_filename,
            )
        )
        return rows, notes

    def wait_for_cadimport_explode(
        self,
        *,
        quote_id: str,
        upload_rows: list[dict[str, Any]],
        upload_payload: Any = None,
        part_key: str,
        cad_filename: str,
        quote_request_id: str | None = None,
        polls: int | None = None,
        sleep_s: float | None = None,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Kyle Next: createAllParts → DoCreateDXFParts POST /part/create."""
        notes: list[str] = []
        polls_n = int(
            polls
            if polls is not None
            else os.getenv("SECTURA_CADIMPORT_EXPLODE_POLLS", "20")
        )
        wait = float(
            sleep_s
            if sleep_s is not None
            else os.getenv("SECTURA_CADIMPORT_EXPLODE_SLEEP", "1.5")
        )
        if cadimport_filelist_exploded(
            upload_rows, part_key=part_key, cad_filename=cad_filename
        ) and not filelist_is_assembly_only(
            upload_rows, part_key=part_key, cad_filename=cad_filename
        ):
            notes.append(
                f"CadImport FileList already exploded ({len(upload_rows)} kid row(s))"
            )
            notes.extend(
                self._explode_capture_notes(
                    explode_passes=0,
                    rows=upload_rows,
                    part_key=part_key,
                    cad_filename=cad_filename,
                )
            )
            return upload_rows, notes
        from .cadimport_js import (
            CREATE_DXF_PARTS_CALLER,
            CREATE_DXF_PARTS_FUNCTION,
            CREATE_DXF_PARTS_PATH,
            create_dxf_parts_xhr,
        )

        xhr = create_dxf_parts_xhr()
        notes.append(
            f"QuoteOrderEdit {CREATE_DXF_PARTS_CALLER} → {xhr.cite()} "
            "(success t.List → #gridDXFParts)"
        )
        del upload_payload  # Next JSON List is not the explode body
        html = getattr(self.client, "_last_item_add_view_html", "") or ""
        location = inventory_location_from_html(html)
        ensure_fn = getattr(type(self.client), "ensure_quote_antiforgery", None)
        if callable(ensure_fn):
            try:
                ensure_fn(self.client, quote_id)
            except (SecturaFabApiError, SecturaFabWebsiteAuthError, TypeError):
                pass
        af_extracted = client_antiforgery_extracted(self.client)
        notes.extend(self._antiforgery_capture_notes())
        id_list: list[str] = []
        unit_list: list[str] = []
        for row in upload_rows:
            if not isinstance(row, dict):
                continue
            sid = str(row.get("SourceDataID") or row.get("ID") or "").strip()
            if not sid:
                continue
            id_list.append(sid)
            unit_list.append(
                str(row.get("Units") or row.get("Length_Units") or "inch").strip()
                or "inch"
            )
        create_fn = getattr(self.client, "create_dxf_parts", None)
        source = getattr(self.client, "_af_source", "")
        if isinstance(source, str) and source == "cookie_quote_html":
            notes.append(
                "DoCreateDXFParts skipped — cookie_quote_html is the wrong "
                "claims identity (no cookie HTTP /part/create)"
            )
        elif isinstance(source, str) and source != "chrome_dom":
            notes.append(
                "DoCreateDXFParts skipped — af_extracted=false "
                "(chrome_dom required; no /part/create)"
            )
        elif not af_extracted:
            notes.append(
                "DoCreateDXFParts skipped — af_extracted=false "
                "(chrome_dom required; no /part/create)"
            )
        elif callable(create_fn) and id_list:
            try:
                try:
                    result = create_fn(
                        id_list,
                        unit_list,
                        location=location,
                        other_file_ids=[],
                        height=0,
                        width=0,
                        quote_id=quote_id,
                        quote_number=part_key,
                    )
                except TypeError:
                    result = create_fn(
                        id_list,
                        unit_list,
                        location=location,
                        other_file_ids=[],
                        height=0,
                        width=0,
                    )
                via = getattr(self.client, "_part_create_via", "") or ""
                if isinstance(via, str) and via:
                    notes.append(f"part_create_via={via}")
                present = getattr(self.client, "_grid_present", None)
                if isinstance(present, bool):
                    notes.append(f"grid_present={'true' if present else 'false'}")
                    if not present:
                        notes.append(
                            "WARNING: #gridDXFParts kendo not on /Quote/EDIT "
                            "(click #but_dxf) — cookie GetItem_AddView is the "
                            "wrong document (live a64509d); not Finishing"
                        )
                        result = None
                n_list = getattr(self.client, "_part_create_list_len", None)
                if isinstance(n_list, (int, float)):
                    notes.append(f"part_create_list_len={int(n_list)}")
                _log_part_create_payload_empty(notes, self.client)
                n_grid = getattr(self.client, "_grid_dxf_row_count", None)
                if isinstance(n_grid, (int, float)):
                    notes.append(f"grid_dxf_row_count={int(n_grid)}")
                if empty_griddxf_explode_miss(
                    grid_present=present if isinstance(present, bool) else None,
                    n_grid=n_grid if isinstance(n_grid, (int, float)) else None,
                    n_list=n_list if isinstance(n_list, (int, float)) else None,
                ):
                    notes.append(
                        "WARNING: empty #gridDXFParts / List=0 — not Finishing "
                        "(empty #gridDXF createAllParts is the 34632-2 miss)"
                    )
                    result = None
            except (SecturaFabApiError, SecturaFabWebsiteAuthError, TypeError) as exc:
                notes.append(
                    f"WARNING: {xhr.cite()} failed: "
                    f"{_part_create_fail_note(exc)}"
                )
                result = None
            exploded = self._cadimport_rows(result)
            n_list = getattr(self.client, "_part_create_list_len", None)
            n_grid = getattr(self.client, "_grid_dxf_row_count", None)
            present = getattr(self.client, "_grid_present", None)
            if isinstance(present, bool) and not present:
                notes.extend(
                    self._explode_capture_notes(
                        explode_passes=1,
                        rows=exploded or upload_rows,
                        part_key=part_key,
                        cad_filename=cad_filename,
                    )
                )
                return exploded or upload_rows, notes
            if empty_griddxf_explode_miss(
                grid_present=present if isinstance(present, bool) else None,
                n_grid=n_grid if isinstance(n_grid, (int, float)) else None,
                n_list=n_list if isinstance(n_list, (int, float)) else None,
            ):
                notes.extend(
                    self._explode_capture_notes(
                        explode_passes=1,
                        rows=exploded or upload_rows,
                        part_key=part_key,
                        cad_filename=cad_filename,
                    )
                )
                return exploded or upload_rows, notes
            if cadimport_filelist_exploded(
                exploded, part_key=part_key, cad_filename=cad_filename
            ):
                notes.append(
                    f"CadImport exploded {len(exploded)} FileList row(s) "
                    f"on {CREATE_DXF_PARTS_FUNCTION} {CREATE_DXF_PARTS_PATH}"
                )
                used = {str(x) for x in id_list}
                grid, nest_notes = self._reexplode_nested_assemblies(
                    quote_id=quote_id,
                    part_key=part_key,
                    cad_filename=cad_filename,
                    grid=exploded,
                    used_ids=used,
                    location=location,
                    first_pass=1,
                )
                notes.extend(nest_notes)
                return grid, notes
            notes.append(
                f"{CREATE_DXF_PARTS_FUNCTION} {CREATE_DXF_PARTS_PATH} had no "
                f"kid FileList ({cadimport_payload_preview(result)})"
            )
        elif not id_list:
            notes.append(
                "QuoteOrderEdit DoCreateDXFParts skipped — upload row has no "
                "SourceDataID (IDList)"
            )
        grid = list(upload_rows)
        for attempt in range(max(1, polls_n)):
            if attempt and wait > 0:
                time.sleep(wait)
            grid = self._collect_cadimport_grid(
                quote_id=quote_id,
                upload_rows=None,
                quote_request_id=quote_request_id,
            )
            if cadimport_filelist_exploded(
                grid, part_key=part_key, cad_filename=cad_filename
            ):
                notes.append(
                    f"CadImport exploded {len(grid)} FileList row(s) "
                    f"after {CREATE_DXF_PARTS_PATH} (poll {attempt + 1})"
                )
                used = {str(x) for x in id_list}
                grid, nest_notes = self._reexplode_nested_assemblies(
                    quote_id=quote_id,
                    part_key=part_key,
                    cad_filename=cad_filename,
                    grid=grid,
                    used_ids=used,
                    location=location,
                    first_pass=1,
                )
                notes.extend(nest_notes)
                return grid, notes
        notes.append(
            f"CadImport FileList still {len(grid)} raw upload row(s) "
            f"after {CREATE_DXF_PARTS_FUNCTION} — not Finishing the STEP file row"
        )
        notes.extend(
            self._explode_capture_notes(
                explode_passes=0,
                rows=grid,
                part_key=part_key,
                cad_filename=cad_filename,
            )
        )
        return grid, notes

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
        from .locked_1001898 import locked_linear_bind

        locked = locked_linear_bind(text=description)
        products = self._linear_catalog()
        if locked and locked.get("sku"):
            want = str(locked["sku"]).upper()
            exact = next(
                (
                    p
                    for p in products
                    if str(p.get("ProductName") or p.get("SKU") or "").upper() == want
                ),
                None,
            )
            note = None
            if locked.get("grade_note"):
                note = (
                    f"Linear {description!r} catalog {locked['sku']} "
                    f"({locked['grade_note']})"
                )
            if exact:
                return (
                    str(exact.get("ID") or "") or None,
                    str(exact.get("ProductName") or locked["sku"]),
                    note,
                )
            return None, str(locked["sku"]), note or (
                f"Locked SKU {locked['sku']} not in tenant catalog"
            )
        product, note = pick_closest_linear_product(
            products,
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

    def _match_linear_product(
        self,
        description: str,
        *,
        material: str | None,
        row: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any] | None, str | None, str | None]:
        from .locked_1001898 import locked_linear_bind

        locked = locked_linear_bind(text=description)
        products = self._linear_catalog()
        if locked and locked.get("sku"):
            want = str(locked["sku"]).upper()
            exact = next(
                (
                    p
                    for p in products
                    if str(p.get("ProductName") or p.get("SKU") or "").upper() == want
                ),
                None,
            )
            note = None
            if locked.get("grade_note"):
                note = (
                    f"Linear {description!r} catalog {locked['sku']} "
                    f"({locked['grade_note']})"
                )
            if exact:
                return exact, str(exact.get("ProductName") or locked["sku"]), note
            return None, str(locked["sku"]), note or (
                f"Locked SKU {locked['sku']} not in tenant catalog"
            )
        product, note = pick_closest_linear_product(
            products,
            description=description,
            material=material,
            row=row,
        )
        if not product:
            return None, None, note
        sku = str(
            product.get("ProductName")
            or product.get("SKU")
            or product.get("ProductCode")
            or ""
        ) or None
        return product, sku, note

    def _linear_catalog_bind(
        self,
        product: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not product:
            return None
        pid = str(product.get("ID") or "")
        rows: list[dict[str, Any]] = []
        if pid and hasattr(self.client, "read_data_linear_lookup"):
            try:
                payload = self.client.read_data_linear_lookup(pid)
                rows = linear_lookup_rows(payload)
            except (SecturaFabApiError, SecturaFabWebsiteAuthError, TypeError, ValueError):
                rows = []
        if not rows:
            rows = linear_lookup_rows(product)
        bind = linear_bind_fields(product, rows, lookup_scoped=True)
        if not bind:
            return None
        if str(bind.get("productConfigID") or "") == str(
            product.get("ID") or product.get("ProductID") or ""
        ):
            return None
        return bind

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
        part_key: str = "",
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Cad / Linear / Component / Assembly + closest ProductID/SKU.

        Nested STEP names like Aluminum Platform Weldment are Assembly, not
        Cad plate. Hinge (not hinge plate) is Component. ALUMINUM in the
        name is not A36.
        """
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
        counts = {"Cad": 0, "Linear": 0, "Component": 0, "Assembly": 0}
        sibling_nouns = any(
            is_nested_assembly_name(row_name(r))
            or filelist_row_is_leaf_noun(row_name(r))
            for r in rows
            if isinstance(r, dict)
        )
        name_counts: dict[str, int] = {}
        for r in rows:
            if not isinstance(r, dict):
                continue
            tok = str(row_name(r) or "").strip().upper()
            if tok:
                name_counts[tok] = name_counts.get(tok, 0) + 1
        lom_child_nouns = [
            str(brow.get("description") or "").strip()
            for brow in (bom_rows or [])
            if str(brow.get("description") or "").strip()
            and normalize_part_token(
                str(brow.get("part_no") or brow.get("part_number") or "")
            )
            != normalize_part_token(part_key)
        ]
        for row in rows:
            name = row_name(row)
            stem = Path(str(row.get("FileName") or "")).stem
            dashed = match_bom_part_no(name, bom_rows) or match_bom_part_no(
                stem, bom_rows
            )
            bom_noun = ""
            for brow in bom_rows or []:
                bpn = str(brow.get("part_no") or brow.get("part_number") or "").strip()
                if dashed and (bpn == dashed or bpn == stem):
                    bom_noun = str(brow.get("description") or "")
                    break
            if dashed:
                name = f"{dashed} {bom_noun or name}".strip()
                row["Name"] = dashed
            cat = classify_sectura_item(name)
            token = dashed or (name.split()[0] if name else "")
            stem = str(row.get("Name") or "").strip()
            stem_u = stem.upper()
            # Live P001545: W001531_2 / _3 are Cad plates; W001544 x34 is the
            # weldment occurrence (Assembly). P001545 Rev B is the STEP root.
            if re.fullmatch(r"W\d{4,}_\d+", stem, re.I):
                cat = "Cad"
            elif (
                re.fullmatch(r"W\d{4,}", stem, re.I)
                and name_counts.get(stem_u, 0) >= 2
            ):
                cat = "Assembly"
            elif (
                part_key
                and re.match(rf"^{re.escape(part_key)}\s+rev\b", stem, re.I)
            ):
                cat = "Assembly"
            if (
                part_key
                and normalize_part_token(stem) == normalize_part_token(part_key)
                and is_bare_part_number(stem)
            ):
                if sibling_nouns:
                    cat = "Assembly"
                else:
                    extra = ""
                    idx = len(classified)
                    if idx < len(lom_child_nouns):
                        extra = lom_child_nouns[idx]
                    if extra:
                        cat = classify_sectura_item(f"{stem} {extra}")
                    if cat == "Assembly" and not is_nested_assembly_name(
                        extra or name
                    ):
                        cat = "Cad"
            compact = {k.replace("-", ""): v for k, v in purchased.items()}
            if token in purchased or token.replace("-", "") in compact:
                cat = "Component"
            pm = lookup_part_material(part_materials, name)
            aluminum_named = bool(re.search(r"\bALUMINI?UM\b", name, re.I))
            material = default_material
            thickness: str | float = default_thickness
            if pm and pm.material:
                material = pm.material
            elif aluminum_named:
                material = ""
            elif pm is None and default_material == "A36":
                notes.append(
                    f"A36 on {name[:40]!r} — drawing named no grade"
                )
            if pm and pm.thickness_in is not None:
                thickness = _sanitize_thickness_param(pm.thickness_in)
            product_id = None
            sku = None
            machine = "Laser" if cat == "Cad" else None
            if cat == "Assembly":
                machine = None
            named = _named_grade_from_blob(
                f"{name} {material} {(pm.material if pm else '')}"
            )
            if named:
                material = _shop_material(named)
            if aluminum_named and (not named or _shop_material(material) == "A36"):
                material = ""
            bind: dict[str, Any] | None = None
            if cat == "Linear":
                machine = "Saw"
                product_id, sku, mismatch = self._match_linear_sku(
                    name, material=material, row=row
                )
                if mismatch:
                    notes.append(f"WARNING: {mismatch}")
                product, _sku2, _note2 = self._match_linear_product(
                    name, material=material, row=row
                )
                del _sku2, _note2
                bind = self._linear_catalog_bind(product)
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
            if bind:
                cfg = str(bind.get("productConfigID") or "")
                pid = str(bind.get("productID") or product_id or "")
                if cfg and pid and cfg != pid:
                    overlaid["productConfigID"] = cfg
                    overlaid["productID"] = pid
                elif cfg and not pid:
                    overlaid["productConfigID"] = cfg
            if dashed and cat == "Cad":
                overlaid["Name"] = dashed
                overlaid["Description"] = format_cad_description(
                    dashed,
                    thickness=thickness,
                    grade=material,
                    noun=name,
                )
            elif dashed:
                overlaid["Name"] = dashed
                overlaid["Description"] = dashed
            classified.append(overlaid)
            counts[cat] = counts.get(cat, 0) + 1
            row_id = str(overlaid.get("ID") or overlaid.get("ItemID") or EMPTY_GUID)
            try:
                from .chrome_cdp import chrome_quotes_live

                live_edit = chrome_quotes_live()
                if cat != "Assembly" and "PartMode" in overlaid and not live_edit:
                    self.client.cadimport_set_part_mode(
                        row_id=row_id, part_mode=int(overlaid["PartMode"])
                    )
                if not live_edit:
                    self.client.cadimport_update_data(overlaid)
            except (SecturaFabApiError, SecturaFabWebsiteAuthError) as exc:
                notes.append(
                    f"WARNING: CadImport classify post failed for {name[:40]!r}: {exc}"
                )
        notes.append(
            f"Classified CAD Files kids — Cad: {counts['Cad']}, "
            f"Linear: {counts['Linear']}, Component: {counts['Component']}, "
            f"Assembly: {counts['Assembly']}"
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
        quote_request_id: str | None = None,
        explode_polls: int | None = None,
        explode_sleep_s: float | None = None,
    ) -> list[str]:
        """CAD Files: upload → explode → bind → SetPartMode on #gridDXFParts → Finish.

        After /part/create bind + SetPartMode, log kendo row key names (CadType,
        Stock_*, FileType, SID/FileID/ID) and the same names on posted FileList.
        If kendo has CadType/Stock_*, copy them through — do not invent values.
        If kendo lacks them after explode, that is a /part/create bind miss
        (not a Finish-hook miss): do not Finish.
        Cad leftover Finish no-ops when InternalData/ImageString are empty
        (live 10098-1). Copy those keys through if present; log emptiness
        bools only; skip Finish. Do not invent unfold/geometry.
        """
        notes: list[str] = []
        if cadimport_step_too_large(cad_files):
            n = cadimport_step_bytes(cad_files)
            notes.append(
                f"WARNING: STEP {n} B — Cloudflare Upload 502 at 32MB+ "
                "(live 106384-1 / 106687-1); not POSTing "
                "/CadImport/UploadItem_DXFFiles, not chunking, not Image Files"
            )
            return notes
        try:
            self.client.get_item_add_view(quote_id, item_type="dxf")
            notes.append(
                "GetItem_AddView cookie-HTTP (AF scrape, not the Chrome "
                "CAD Files dialog)"
            )
        except SecturaFabWebsiteAuthError:
            notes.append(
                "GetItem_AddView 302 — continuing CadImport upload / Finish "
                "with bearer (AddItem_DXFFiles still needs a website session)"
            )
        except SecturaFabApiError as exc:
            notes.append(f"WARNING: GetItem_AddView returned {exc}")

        open_files = []
        upload_payload: Any = None
        cad_filename = cad_files[0].name if cad_files else ""
        try:
            form_files = []
            for path in cad_files:
                fh = path.open("rb")
                open_files.append(fh)
                form_files.append(("files", (path.name, fh, _mime_for(path))))
            upload_payload = self.client.upload_item_dxf_files(form_files, quote_id=quote_id)
            notes.append(
                f"Uploaded CAD via /CadImport/UploadItem_DXFFiles: {cad_filename}"
            )
        finally:
            for fh in open_files:
                fh.close()

        try:
            self.client.cadimport_set_units("inch")
        except (SecturaFabApiError, SecturaFabWebsiteAuthError) as exc:
            notes.append(f"WARNING: CadImport SetUnits failed: {exc}")

        upload_rows = filelist_from_cadimport_upload(upload_payload)
        data_rows, explode_notes = self.wait_for_cadimport_explode(
            quote_id=quote_id,
            upload_rows=upload_rows,
            upload_payload=upload_payload,
            part_key=part_key,
            cad_filename=cad_filename,
            quote_request_id=quote_request_id,
            polls=explode_polls,
            sleep_s=explode_sleep_s,
        )
        notes.extend(explode_notes)
        present = getattr(self.client, "_grid_present", None)
        if isinstance(present, bool):
            if f"grid_present={'true' if present else 'false'}" not in " ".join(notes):
                notes.append(f"grid_present={'true' if present else 'false'}")
            if not present:
                edit_id = getattr(self.client, "_edit_quote_id", "")
                edit_gate = getattr(self.client, "_edit_gate", "")
                if isinstance(edit_id, str) or isinstance(edit_gate, str):
                    shown_edit = edit_id if isinstance(edit_id, str) else ""
                    notes.append(
                        f"edit_quote_id={shown_edit} minted_id={quote_id}"
                    )
                if isinstance(edit_gate, str) and edit_gate:
                    notes.append(
                        f"WARNING: Chrome EDIT tab is not the minted quote "
                        f"({edit_gate}) — not Finishing (leave shell, no remint; "
                        f"live 5003313-001 leftover 105918-1)"
                    )
                else:
                    notes.append(
                        "WARNING: #gridDXFParts not in the Chrome Quotes document "
                        "— not Finishing"
                    )
                return notes
        n_list = getattr(self.client, "_part_create_list_len", None)
        if isinstance(n_list, (int, float)):
            if f"part_create_list_len={int(n_list)}" not in " ".join(notes):
                notes.append(f"part_create_list_len={int(n_list)}")
        _log_part_create_payload_empty(notes, self.client)
        n_grid = getattr(self.client, "_grid_dxf_row_count", None)
        if isinstance(n_grid, (int, float)):
            if f"grid_dxf_row_count={int(n_grid)}" not in " ".join(notes):
                notes.append(f"grid_dxf_row_count={int(n_grid)}")
        if empty_griddxf_explode_miss(
            grid_present=present if isinstance(present, bool) else None,
            n_grid=n_grid if isinstance(n_grid, (int, float)) else None,
            n_list=n_list if isinstance(n_list, (int, float)) else None,
        ):
            notes.append(
                "WARNING: empty #gridDXFParts / List=0 — not Finishing "
                "(empty #gridDXF createAllParts is the 34632-2 miss)"
            )
            return notes
        edit_id = getattr(self.client, "_edit_quote_id", "")
        minted = str(quote_id or "")
        if isinstance(edit_id, str) or minted:
            shown_edit = edit_id if isinstance(edit_id, str) else ""
            note = f"edit_quote_id={shown_edit} minted_id={minted}"
            if note not in " ".join(notes):
                notes.append(note)
        edit_gate = getattr(self.client, "_edit_gate", "")
        if isinstance(edit_gate, str) and edit_gate:
            notes.append(
                f"WARNING: Chrome EDIT tab is not the minted quote "
                f"({edit_gate}) — not Finishing (leave shell, no remint; "
                f"live 5003313-001 leftover 105918-1)"
            )
            return notes
        from .chrome_cdp import grid_dxf_count_is_stale

        if getattr(self.client, "_stale_grid", False) is True or (
            isinstance(n_grid, (int, float))
            and isinstance(n_list, (int, float))
            and grid_dxf_count_is_stale(int(n_grid), int(n_list))
        ):
            notes.append(
                "WARNING: stale #gridDXFParts "
                f"grid_dxf_row_count={int(n_grid) if isinstance(n_grid, (int, float)) else 0} "
                f"vs FileList {int(n_list) if isinstance(n_list, (int, float)) else 0} "
                "— leftover kendo, not Finishing "
                "(live 5003313-001 65 vs 12)"
            )
            return notes
        if not cadimport_filelist_exploded(
            data_rows, part_key=part_key, cad_filename=cad_filename
        ):
            notes.append(
                "WARNING: CadImport did not explode STEP into child FileList "
                "rows — not Finishing the raw upload row "
                "(AddItem_DXFFiles 200 with 1 STEP file is not success)"
            )
            return notes
        kids = finish_filelist_kids(
            data_rows, part_key=part_key, cad_filename=cad_filename
        )
        if not kids:
            notes.append(
                "WARNING: Finish FileList empty after dropping Root/raw STEP "
                "— not Finishing"
            )
            return notes
        if len(kids) == 1 and is_raw_step_upload_row(
            kids[0], part_key=part_key, cad_filename=cad_filename
        ):
            notes.append(
                "WARNING: Finish FileList is 1 raw STEP — not Finishing "
                "(need exploded kids, not Root-only)"
            )
            return notes
        if filelist_is_assembly_only(
            kids, part_key=part_key, cad_filename=cad_filename
        ):
            notes.append(
                "WARNING: FileList is assembly-only (ASSY/WELDMENT) after "
                "re-explode — not Finishing an empty stamp "
                "(live 28110-2; want_cad=0 is not a license)"
            )
            return notes
        notes.append(
            f"CadImport FileList using {len(kids)} exploded kid row(s) "
            f"(SourceDataID/FileID for Finish calculators)"
        )
        classified, class_notes = self.classify_cadimport_rows(
            kids,
            default_material=material,
            default_thickness=thickness,
            bom_rows=bom_rows,
            library=library,
            extra_pdfs=extra_pdfs,
            qty=qty,
            part_key=part_key,
        )
        notes.extend(class_notes)
        from .chrome_cdp import apply_grid_dxf_part_modes
        from .website import (
            cad_filelist_payload_blocks_finish,
            filelist_cad_payload_empty_bools,
            filelist_missing_cadimport_identity_keys,
        )

        applied = apply_grid_dxf_part_modes(classified, quote_id=quote_id)
        applied = applied if isinstance(applied, dict) else {}
        set_via = str(applied.get("setpartmode_via") or "")
        self.client._setpartmode_via = set_via
        notes.append(
            f"grid_classify Cad:{int(applied.get('cad') or 0)} "
            f"Linear:{int(applied.get('linear') or 0)} "
            f"Assembly:{int(applied.get('assembly') or 0)} "
            f"Component:{int(applied.get('component') or 0)}"
        )
        notes.append(f"setpartmode_via={set_via or '?'}")
        if not set_via:
            notes.append(
                "WARNING: SetPartMode did not run on this EDIT #gridDXFParts "
                "— OnAddDXFClick empty-body path (live EHB3112)"
            )
        applied_keys = applied.get("kendo_row_keys") if applied.get("grid_present") else None
        if not isinstance(applied_keys, list):
            applied_keys = None
        bind_keys = getattr(self.client, "_kendo_row_keys", None)
        if not isinstance(bind_keys, list):
            bind_keys = None
        kendo_keys = applied_keys if applied_keys is not None else bind_keys
        if isinstance(kendo_keys, list):
            notes.append("kendo_row_keys=" + ",".join(str(k) for k in kendo_keys[:24]))
            if applied_keys is not None:
                self.client._kendo_row_keys = [str(k) for k in applied_keys]
        if applied.get("grid_present"):
            want_cad = sum(
                1 for r in classified if str(r.get("Category") or "") == "Cad"
            )
            want_lin = sum(
                1 for r in classified if str(r.get("Category") or "") == "Linear"
            )
            if want_cad > 0 and int(applied.get("cad") or 0) <= 0:
                notes.append(
                    "WARNING: #gridDXFParts Cad=0 after SetPartMode — laser "
                    "plates still Component; not Finishing (live 105918-1)"
                )
                return notes
            if (
                want_cad <= 0
                and want_lin <= 0
                and filelist_is_assembly_only(
                    classified, part_key=part_key, cad_filename=cad_filename
                )
            ):
                notes.append(
                    "WARNING: FileList Cad=0 Linear=0 after classify — "
                    "assembly-only stamp; not Finishing "
                    "(live 28110-2; want_cad=0 is not a license)"
                )
                return notes
        ready = []
        for r in classified:
            try:
                status = float(r.get("Status") or 0)
                err = int(r.get("ErrorStatus") or 0)
            except (TypeError, ValueError):
                status, err = 0.0, 1
            if status > 0 and err == 0:
                ready.append(r)
        if not ready:
            ready = classified
        ready = finish_filelist_kids(
            ready, part_key=part_key, cad_filename=cad_filename
        )
        if not ready:
            notes.append(
                "WARNING: classified Finish FileList empty — not Finishing"
            )
            return notes
        if len(ready) == 1 and is_raw_step_upload_row(
            ready[0], part_key=part_key, cad_filename=cad_filename
        ):
            notes.append(
                "WARNING: classified Finish FileList is 1 raw STEP — "
                "not Finishing"
            )
            return notes
        if isinstance(kendo_keys, list):
            ident_miss = filelist_missing_cadimport_identity_keys(kendo_keys)
            if ident_miss:
                notes.append("filelist_missing_keys=" + ",".join(ident_miss))
                notes.append(
                    "WARNING: CadImport identity keys missing on EDIT kendo "
                    f"after explode ({'+'.join(ident_miss)}) — /part/create "
                    "bind miss for n=1, not a Finish-hook miss "
                    "(do not invent Stock_X/Y or CadType; not Finishing; "
                    "live 107292-1)"
                )
                return notes
        cad_block = next(
            (r for r in ready if cad_filelist_payload_blocks_finish(r)),
            None,
        )
        if cad_block is not None:
            bools = filelist_cad_payload_empty_bools(cad_block)
            notes.append(
                "filelist_internaldata_empty="
                + ("true" if bools["filelist_internaldata_empty"] else "false")
            )
            notes.append(
                "filelist_imagestring_empty="
                + ("true" if bools["filelist_imagestring_empty"] else "false")
            )
            notes.append(
                "WARNING: Cad FileList InternalData present-and-empty — "
                "required for Cad Finish (OnAddDXFClick copies InternalData; "
                "ImageString is preview). Server never fills InternalData on "
                "explode (Skin Assembly 5b622a0d jquery_ajax+EDIT 8/8, FA "
                "Assembly 0d4b8a46 28/28, SC0600 143/143). #img copy is not "
                "success; ajax-on-EDIT is not success; not Finishing; do not "
                "invent InternalData; not success"
            )
            return notes
        result = self.client.add_item_dxf_files(
            quote_id=quote_id,
            file_list=ready,
            item_id=EMPTY_GUID,
            customer_material=False,
        )
        via = getattr(self.client, "_finish_via", "") or ""
        if isinstance(via, str) and via:
            notes.append(f"finish_via={via}")
        finish_fn = ""
        finish_n = 0
        grid_n = getattr(self.client, "_grid_dxf_row_count", None)
        if isinstance(result, dict):
            finish_fn = str(result.get("finish_fn") or "")
            finish_n = int(result.get("finish_filelist_n") or 0)
            if result.get("grid_dxf_row_count"):
                grid_n = result.get("grid_dxf_row_count")
            if finish_fn:
                notes.append(f"finish_fn={finish_fn}")
            if finish_n or via == "page_fn":
                notes.append(f"finish_filelist_n={finish_n}")
            if isinstance(result, dict) and "reads_kendo" in result:
                notes.append(
                    "reads_kendo="
                    + ("true" if result.get("reads_kendo") else "false")
                )
            if "filelist_from_kendo" in result:
                notes.append(
                    "filelist_from_kendo="
                    + ("true" if result.get("filelist_from_kendo") else "false")
                )
            sid_n = result.get("filelist_sourcedataid_n")
            if sid_n is not None:
                notes.append(f"filelist_sourcedataid_n={int(sid_n)}")
            id_n = result.get("filelist_id_n")
            if id_n is not None:
                notes.append(f"filelist_id_n={int(id_n)}")
            fileid_n = result.get("filelist_fileid_n")
            if fileid_n is not None:
                notes.append(f"filelist_fileid_n={int(fileid_n)}")
            row_keys = [str(k) for k in (result.get("filelist_row_keys") or [])]
            if row_keys:
                notes.append("filelist_row_keys=" + ",".join(row_keys[:24]))
            posted_kendo = [str(k) for k in (result.get("kendo_row_keys") or [])]
            if posted_kendo and f"kendo_row_keys={','.join(posted_kendo[:24])}" not in " ".join(notes):
                notes.append("kendo_row_keys=" + ",".join(posted_kendo[:24]))
            miss_cmp = [str(k) for k in (result.get("filelist_missing_keys") or [])]
            if miss_cmp:
                notes.append("filelist_missing_keys=" + ",".join(miss_cmp))
            if "FileType" in miss_cmp:
                notes.append(
                    "WARNING: posted FileList lacks FileType — SetPartMode "
                    "badge/classify is not the posted key "
                    "(live 16629-1 empty body vs 105918-1 List,Result Component)"
                )
            miss_id = [str(k) for k in (result.get("filelist_missing_identity") or [])]
            if miss_id:
                notes.append(
                    "WARNING: CadImport identity keys missing on posted FileList "
                    f"({'+'.join(miss_id)}) — empty body vs 105918-1 List,Result "
                    "(live 107292-1; FileType Cad is SetPartMode)"
                )
            ft = result.get("filelist_filetype")
            if isinstance(ft, dict) and ft:
                notes.append(
                    "filelist_filetype "
                    + " ".join(
                        f"{k}:{int(ft.get(k) or 0)}"
                        for k in ("Cad", "Linear", "Assembly", "Component", "blank")
                    )
                )
            if result.get("filelist_errorstatus") is not None:
                notes.append(
                    f"filelist_errorstatus={result.get('filelist_errorstatus')}"
                )
            if result.get("filelist_qty") is not None:
                notes.append(f"filelist_qty={result.get('filelist_qty')}")
            ft_val = result.get("filelist_filetype_value")
            ft_typ = result.get("filelist_filetype_type")
            if ft_val not in (None, "") or ft_typ not in (None, ""):
                notes.append(f"filelist_filetype_value={ft_val or ''}")
                notes.append(f"filelist_filetype_type={ft_typ or ''}")
            cad_path = [str(k) for k in (result.get("filelist_cad_path_keys") or [])]
            notes.append("filelist_cad_path_keys=" + ",".join(cad_path))
            if "filelist_internaldata_empty" in result:
                notes.append(
                    "filelist_internaldata_empty="
                    + (
                        "true"
                        if result.get("filelist_internaldata_empty")
                        else "false"
                    )
                )
            if "filelist_imagestring_empty" in result:
                notes.append(
                    "filelist_imagestring_empty="
                    + (
                        "true"
                        if result.get("filelist_imagestring_empty")
                        else "false"
                    )
                )
            if "finish_af_present" in result:
                notes.append(
                    "finish_af_present="
                    + ("true" if result.get("finish_af_present") else "false")
                )
            why = str(result.get("finish_why") or "")
            if why:
                notes.append(f"finish_why={why}")
            sid_n_int = 0
            try:
                sid_n_int = int(result.get("filelist_sourcedataid_n") or 0)
            except (TypeError, ValueError):
                sid_n_int = 0
            if sid_n_int <= 0:
                notes.append(
                    "WARNING: OnAddDXFClick is not the 105918-1 path "
                    f"({why or 'filelist_missing_ids'}) "
                    "— not success (live 11796-2)"
                )
            elif not result.get("filelist_from_kendo") or not result.get(
                "finish_af_present"
            ):
                notes.append(
                    "WARNING: OnAddDXFClick is not the 105918-1 path "
                    f"({why or 'filelist_from_kendo=false or finish_af_present=false'}) "
                    "— not success (live 11796-1)"
                )
            req_keys = [str(k) for k in (result.get("request_keys") or [])]
            if req_keys:
                notes.append("finish_request_keys=" + ",".join(req_keys[:12]))
        notes.append(
            f"Finish POST /Quote/AddItem_DXFFiles "
            f"(page-grid {int(grid_n) if isinstance(grid_n, (int, float)) else 0}"
            f" / classified {len(ready)}) "
            f"— laser/saw packs come from Finish, not grafted Profile"
        )
        empty_finish = False
        if via != "page_fn":
            notes.append(
                "WARNING: reconstructed FileList Finish is the ItemList-0 "
                "path — need page #gridDXFParts Finish; not Finishing"
            )
        if isinstance(result, dict):
            body_type = str(result.get("body_type") or "")
            body_keys = [str(k) for k in (result.get("body_keys") or [])]
            if body_keys:
                notes.append("finish_body_keys=" + ",".join(body_keys[:12]))
            if result.get("empty_body") or (
                body_type in {"empty", "str"}
                and not result.get("has_NewItem")
                and not result.get("has_QuoteItem")
                and not body_keys
            ):
                empty_finish = True
                notes.append(
                    "WARNING: AddItem_DXFFiles HTTP 200 empty body / no NewItem "
                    f"(not List,Result) — finish_fn={finish_fn or '?'} "
                    f"finish_filelist_n={finish_n} "
                    f"grid_dxf_row_count="
                    f"{int(grid_n) if isinstance(grid_n, (int, float)) else 0} "
                    "— FileType=Cad persist is not success "
                    "(live 10098-1 leftover PIVOTING FOOT; 105918-1 "
                    "List,Result was 66 Component / 0 Cad, not Cad gold). "
                    "Cad vs Component is a different AddItem_DXFFiles path "
                    "— do not invent InternalData/unfold/Status"
                )
        if not getattr(self.client, "_setpartmode_via", ""):
            notes.append(
                "WARNING: OnAddDXFClick without SetPartMode — not success "
                "(live EHB3112 empty body vs 105918-1 GET 66)"
            )
        posted = self._read_quote_items(quote_id)
        cad_n = count_cad_product_type(posted)
        lin_n = count_linear_product_type(posted)
        if cad_n <= 0:
            notes.append(
                "WARNING: GET 0 Cad — laser plates still Component is not gold "
                "(live 105918-1)"
            )
        posted_n = len(quote_item_rows(posted))
        if posted_n <= 0:
            notes.append(
                f"WARNING: AddItem_DXFFiles HTTP 200 GET item_count=0 — "
                f"not success (leave shell, no remint; live 28110-2)"
            )
        elif cad_n <= 0 and lin_n <= 0:
            notes.append(
                f"WARNING: AddItem_DXFFiles HTTP 200 with {len(ready)} FileList "
                f"row(s) landed 0 ItemList lines — not success"
            )
        elif empty_finish:
            notes.append(
                "WARNING: Finish body empty even though GET later showed items"
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
        bom_rows: list[dict[str, Any]] | None = None,
        library: dict[str, Any] | None = None,
        extra_pdfs: list[Path] | None = None,
        takeoff: dict[str, Any] | None = None,
    ) -> list[str]:
        """Image Files Finish: upload → stamp page PDF kendo → OnAddPDFClick.

        FileList must be GetPDFData() / #gridPDF rows with Status>0.
        Reconstructed FileList is fail-closed even if GET>0 (live 1001898-5).
        """
        if not self._website_cookie_present():
            raise SecturaFabWebsiteAuthError(WEBSITE_AUTH_GAP)
        from .item_desc import (
            format_cad_description,
            match_bom_part_no,
            resolve_cad_plate_flats,
            takeoff_plate_row,
        )
        from .locked_1001898 import locked_cad_spec
        from quote_core.part_materials import (
            build_part_material_map,
            lookup_part_material,
        )

        notes: list[str] = []
        try:
            self.client.get_item_add_view(quote_id, item_type="pdf")
            notes.append("Opened Image Files dialog (GetItem_AddView ItemType=pdf)")
        except SecturaFabWebsiteAuthError as exc:
            raise SecturaFabWebsiteAuthError(
                f"{WEBSITE_SESSION_EXPIRED} — GetItem_AddView(pdf) 302 ({exc})",
                status_code=getattr(exc, "status_code", None),
                body=getattr(exc, "body", None),
            ) from exc
        except SecturaFabApiError as exc:
            notes.append(f"WARNING: GetItem_AddView(pdf) returned {exc}")

        cad_n = lin_n = comp_n = 0
        for row in bom_rows or []:
            pn = str(row.get("part_no") or row.get("part_number") or "").strip()
            noun = str(row.get("description") or "")
            cat = classify_sectura_item(f"{pn} {noun}")
            if cat == "Cad":
                cad_n += 1
            elif cat == "Linear":
                lin_n += 1
            else:
                comp_n += 1
        if bom_rows:
            notes.append(
                f"BOM classify Cad:{cad_n} Linear:{lin_n} Component:{comp_n}"
            )

        part_materials = build_part_material_map(
            library_folder=(library or {}).get("folder"),
            related_pdf_names=list((library or {}).get("related_pdfs") or []),
            extra_pdfs=extra_pdfs,
        )
        posted_n = 0
        stamp_rows: list[dict[str, Any]] = []
        uploaded_n = 0
        for path in pdf_files:
            stem = path.stem
            pn = match_bom_part_no(stem, bom_rows) or stem
            noun = ""
            matched_row: dict[str, Any] | None = None
            row_qty = max(1, int(qty or 1))
            for brow in bom_rows or []:
                bpn = str(brow.get("part_no") or brow.get("part_number") or "").strip()
                if bpn == pn:
                    matched_row = brow
                    noun = str(brow.get("description") or "")
                    try:
                        row_qty = max(1, int(brow.get("qty") or brow.get("quantity") or qty or 1))
                    except (TypeError, ValueError):
                        row_qty = max(1, int(qty or 1))
                    break
            cat = classify_sectura_item(f"{pn} {noun}")
            if cat != "Cad":
                notes.append(
                    f"Skipped Image Files {path.name} — {cat} goes Long/Component"
                )
                continue
            plat = takeoff_plate_row(takeoff, pn) or takeoff_plate_row(takeoff, stem)
            if plat:
                if matched_row is None:
                    matched_row = dict(plat)
                    noun = noun or str(plat.get("description") or "")
                else:
                    matched_row.setdefault("width_in", plat.get("width_in"))
                    matched_row.setdefault("length_in", plat.get("length_in"))
                    if plat.get("blank") and not matched_row.get("blank"):
                        matched_row["blank"] = plat.get("blank")
            locked = locked_cad_spec(pn) or {}
            pm = lookup_part_material(part_materials, pn) or lookup_part_material(
                part_materials, f"{pn} {noun}"
            )
            named_grade = None
            grade_blob = f"{noun} {pn} {path.name} {material}"
            if plat:
                grade_blob = (
                    f"{grade_blob} {plat.get('description') or ''} "
                    f"{plat.get('material') or ''} {plat.get('grade') or ''}"
                )
            if re.search(r"(?i)5052|ALPL", grade_blob):
                named_grade = "5052-H32"
            elif re.search(r"(?i)A\s*572|PL025", grade_blob):
                named_grade = "A572 Grade 50"
            plate_mat = _shop_material(
                locked.get("grade")
                or (pm.material if pm and pm.material else None)
                or named_grade
                or material
            )
            plate_thk = locked.get("thickness")
            if plate_thk is None and pm and pm.thickness_in:
                plate_thk = pm.thickness_in
            if plate_thk is None:
                plate_thk = thickness
            plate_w, plate_l = resolve_cad_plate_flats(
                pn,
                bom_row=matched_row,
                takeoff=takeoff,
                pdf_path=path,
                noun=noun,
                locked=locked,
            )
            if matched_row is not None and plate_w and plate_l:
                matched_row["width_in"] = plate_w
                matched_row["length_in"] = plate_l
            part_name = format_cad_description(
                pn,
                thickness=plate_thk,
                grade=plate_mat,
                width_in=plate_w,
                length_in=plate_l,
                noun=locked.get("noun") or noun or description,
            )
            try:
                with path.open("rb") as fh:
                    upload = self.client.upload_item_pdf_attachment(
                        [("files", (path.name, fh, _mime_for(path)))],
                        quote_id=quote_id,
                    )
            except (SecturaFabApiError, SecturaFabWebsiteAuthError) as exc:
                notes.append(
                    f"WARNING: Attachment/UploadItem_PDFFiles {path.name}: {exc}"
                )
                continue
            notes.append(
                f"Uploaded Image Files via /Attachment/UploadItem_PDFFiles {path.name}"
            )
            uploaded_n += 1
            if plate_w and plate_l and plate_thk not in (None, "", 0, "0"):
                stamp_rows.append(
                    {
                        "FileName": path.name,
                        "Length": plate_l,
                        "Width": plate_w,
                        "Thickness": plate_thk,
                        "Material": plate_mat,
                        "Machine": "Laser - Bay1",
                        "Status": 1,
                        "ItemType": "cad",
                        "Qty": row_qty,
                        "PartName": part_name,
                        "Description": part_name,
                    }
                )
            else:
                notes.append(
                    f"WARNING: page PDF kendo stamp missing Thickness/Length/Width "
                    f"for {path.name} — not inventing reconstructed FileList"
                )
        from_kendo = False
        if uploaded_n:
            if stamp_rows:
                stamper = getattr(self.client, "stamp_pdf_kendo_flats", None)
                if callable(stamper):
                    stamper(quote_id=quote_id, rows=stamp_rows)
                    notes.append(
                        f"Stamped {len(stamp_rows)} L×W row(s) on page PDF kendo"
                    )
            try:
                result = self.client.add_item_pdf_files(
                    quote_id=quote_id,
                    file_list=[],
                    item_id=EMPTY_GUID,
                    customer_material=False,
                )
                posted_n = 1
            except SecturaFabWebsiteAuthError as exc:
                raise SecturaFabWebsiteAuthError(
                    f"{WEBSITE_SESSION_EXPIRED} — AddItem_PDFFiles 302 ({exc})",
                    status_code=getattr(exc, "status_code", None),
                    body=getattr(exc, "body", None),
                ) from exc
            except SecturaFabApiError as exc:
                notes.append(f"WARNING: AddItem_PDFFiles: {exc}")
                result = {}
            from .website import (
                pdf_finish_from_page_kendo,
                reconstructed_pdf_filelist_is_fail,
            )

            from_kendo = (
                pdf_finish_from_page_kendo(result)
                if isinstance(result, dict)
                else False
            )
            if isinstance(result, dict):
                via = str(result.get("via") or "")
                if via:
                    notes.append(f"finish_via={via}")
                finish_fn = str(result.get("finish_fn") or "")
                if finish_fn:
                    notes.append(f"finish_fn={finish_fn}")
                notes.append(
                    "filelist_from_kendo="
                    + ("true" if result.get("filelist_from_kendo") else "false")
                )
                why = str(result.get("finish_why") or "")
                if why:
                    notes.append(f"finish_why={why}")
            if reconstructed_pdf_filelist_is_fail(
                result if isinstance(result, dict) else None
            ):
                notes.append(
                    "WARNING: reconstructed FileList Image Files is fail-closed "
                    "even if GET>0 (live 1001898-5) — need page GetPDFData / "
                    "#gridPDF OnAddPDFClick"
                )
        posted = self._read_quote_items(quote_id)
        cad_persisted = count_cad_product_type(posted)
        from .line_item_ops import (
            all_cad_kids_image_files_stamped,
            cad_image_files_stamped,
            cad_kids_unitcost_without_pr,
            image_files_dod_pass,
        )

        if cad_kids_unitcost_without_pr(posted):
            notes.append(
                "WARNING: Cad unitcost filled + OperationCostList empty + no PR "
                "— Image Files DoD FAIL (live 1001898-5); Linear saw PASS is "
                "not DoD PASS"
            )
        if not from_kendo:
            if cad_persisted > 0:
                notes.append(
                    "WARNING: GET>0 after reconstructed FileList is not success "
                    "(live 1001898-5)"
                )
            elif uploaded_n:
                notes.append(
                    f"WARNING: AddItem_PDFFiles posted {posted_n} FileList "
                    f"row(s) but item read has 0 ProductType 100 lines "
                    f"(CadImport list is not success)"
                )
        elif cad_persisted <= 0:
            notes.append(
                f"WARNING: AddItem_PDFFiles posted {posted_n} FileList "
                f"row(s) but item read has 0 ProductType 100 lines "
                f"(CadImport list is not success)"
            )
        elif all_cad_kids_image_files_stamped(posted) and image_files_dod_pass(
            posted, expect_cad=True, expect_linear=False
        ):
            notes.append(
                f"Image Files persisted {cad_persisted} Cad ProductType 100 line(s) "
                f"via /Quote/AddItem_PDFFiles"
            )
        else:
            notes.append(
                "WARNING: page kendo Finish did not stamp PR + laser pack on "
                "every Cad kid — not success"
            )
        for it in quote_item_rows(posted):
            try:
                if int(it.get("ProductType") or 0) != 100:
                    continue
            except (TypeError, ValueError):
                continue
            desc = str(it.get("Description") or it.get("Name") or "")
            if cad_image_files_stamped(it):
                notes.append(
                    f"GET Cad {desc} Badge PR + laser pack + UnitCost>0 "
                    "before addplate/update"
                )
            else:
                notes.append(
                    f"WARNING: Cad {desc} missing PR/pack/UnitCost after "
                    "AddItem_PDFFiles — not calling addplate/quoteOnline update"
                )
        notes.append(
            "Image Files Finish POST /Quote/AddItem_PDFFiles: "
            + ", ".join(p.name for p in pdf_files)
        )
        return notes

    def _read_quote_items(self, quote_id: str) -> dict[str, Any]:
        """Prefer QuoteItem_Read; fall back to v1/quote ItemList."""
        if hasattr(self.client, "quote_item_read"):
            try:
                payload = self.client.quote_item_read(quote_id)
            except (SecturaFabApiError, SecturaFabWebsiteAuthError, TypeError, ValueError):
                payload = None
            if isinstance(payload, dict):
                rows = quote_item_rows(payload)
                if rows:
                    return payload
            elif isinstance(payload, list) and payload:
                return {"Data": payload, "ItemList": payload}
        try:
            peek = self.client.get_json(f"v1/quote/{quote_id}")
        except SecturaFabApiError:
            return {"ItemList": [], "Data": []}
        return peek if isinstance(peek, dict) else {"ItemList": []}

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
        if not self._website_cookie_present():
            raise SecturaFabWebsiteAuthError(WEBSITE_AUTH_GAP)
        notes: list[str] = []
        product_id, sku, mismatch = self._match_linear_sku(
            description, material=material
        )
        if mismatch:
            notes.append(f"WARNING: {mismatch}")
        product, sku2, _note2 = self._match_linear_product(
            description, material=material
        )
        del sku2, _note2
        bind = self._linear_catalog_bind(product)
        if not product_id or not bind:
            raise SecturaFabApiError(
                "Loose linear has no matching ProductID/productConfigID in the catalog"
            )
        extra = {k: v for k, v in bind.items() if k != "sku"}
        extra["productType"] = linear_add_product_type(description, sku=sku)
        self.client.add_item_linear(
            quote_id=quote_id,
            product_id=product_id,
            qty=qty,
            length=length,
            material=material,
            machine="Saw",
            name=description,
            extra=extra,
        )
        notes.append(
            f"Long POST /Quote/AddItem_Linear SKU={sku or product_id} "
            f"qty={qty} length={length}"
        )
        return notes

    def _library_cad_pdfs(
        self,
        bom_rows: list[dict[str, Any]] | None,
        library: dict[str, Any] | None,
    ) -> list[Path]:
        from .pdf_assembly_ops import resolve_component_pdf

        folder = (library or {}).get("folder")
        related = list((library or {}).get("related_pdfs") or [])
        out: list[Path] = []
        seen: set[str] = set()
        for row in bom_rows or []:
            pn = str(row.get("part_no") or row.get("part_number") or "").strip()
            noun = str(row.get("description") or "")
            if classify_sectura_item(f"{pn} {noun}") != "Cad":
                continue
            pdf = resolve_component_pdf(
                pn, library_folder=folder, related_pdf_names=related
            )
            if not pdf or not pdf.is_file():
                continue
            key = str(pdf.resolve())
            if key in seen:
                continue
            seen.add(key)
            out.append(pdf)
        return out

    def _library_linear_rows(
        self, bom_rows: list[dict[str, Any]] | None
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for row in bom_rows or []:
            pn = str(row.get("part_no") or row.get("part_number") or "").strip()
            noun = str(row.get("description") or "")
            if classify_sectura_item(f"{pn} {noun}") == "Linear":
                rows.append(row)
        return rows

    def _library_component_rows(
        self, bom_rows: list[dict[str, Any]] | None
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for row in bom_rows or []:
            pn = str(row.get("part_no") or row.get("part_number") or "").strip()
            noun = str(row.get("description") or "")
            if classify_sectura_item(f"{pn} {noun}") == "Component":
                rows.append(row)
        return rows

    def finish_website_weldment(
        self,
        *,
        quote_id: str,
        part_key: str,
        bom_rows: list[dict[str, Any]] | None,
        library: dict[str, Any] | None,
        extra_pdfs: list[Path] | None,
        material: str,
        assembly_description: str | None,
        takeoff: dict[str, Any] | None,
    ) -> list[str]:
        """Components + Copy/Move under assembly + Internal holes (website session)."""
        from .forbidden_quotes import is_forbidden_quote_id
        from .pdf_assembly_ops import _add_component_items, create_assembly_shell

        if is_forbidden_quote_id(quote_id):
            raise SecturaFabApiError(
                f"Refusing to PATCH/reuse forbidden live quote {quote_id}"
            )
        notes: list[str] = []
        if not self._website_cookie_present():
            notes.append(
                "Pack-stamp / Copy-Move / AddFeature fail-closed — no website session"
            )
            return notes
        peek = self._read_quote_items(quote_id)
        cad_n = count_cad_product_type(peek)
        lin_n = count_linear_product_type(peek)
        if cad_n <= 0 and lin_n <= 0:
            notes.append(
                "Skipped empty assembly shell — no Cad/Linear kids landed "
                "(CadImport list / empty shell is not success)"
            )
            return notes
        notes.extend(
            create_assembly_shell(
                self.client,
                quote_id,
                part_key=part_key,
                description=assembly_description,
            )
        )
        components = self._library_component_rows(bom_rows)
        if components:
            notes.extend(
                _add_component_items(self.client, quote_id, components)
            )
        notes.extend(
            relink_assembly_children(self.client, quote_id, part_key=part_key)
        )
        notes.extend(
            self.stamp_cad_holes(
                quote_id=quote_id,
                bom_rows=bom_rows,
                library=library,
                extra_pdfs=extra_pdfs,
                takeoff=takeoff,
            )
        )
        del material  # components do not invent dollars
        return notes

    def stamp_cad_holes(
        self,
        *,
        quote_id: str,
        bom_rows: list[dict[str, Any]] | None,
        library: dict[str, Any] | None,
        extra_pdfs: list[Path] | None,
        takeoff: dict[str, Any] | None,
    ) -> list[str]:
        """Internal / Add Feature when the drawing has holes. Never invent holes."""
        del library, extra_pdfs
        notes: list[str] = []
        holes_by_pn = _holes_from_takeoff_or_bom(takeoff, bom_rows)
        if not holes_by_pn:
            return notes
        if not self._website_cookie_present():
            notes.append("AddFeature holes fail-closed — no website session")
            return notes
        try:
            detail = self.client.get_json(f"v1/quote/{quote_id}")
        except SecturaFabApiError:
            return notes
        from .item_desc import match_bom_part_no

        stamped = 0
        for it in detail.get("ItemList") or []:
            if not isinstance(it, dict):
                continue
            desc = str(it.get("Description") or "")
            pn = match_bom_part_no(desc, bom_rows) or ""
            holes = holes_by_pn.get(pn) or _holes_from_noun(desc)
            if not holes or not it.get("ID"):
                continue
            if classify_sectura_item(desc) != "Cad" and it.get("ProductType") not in (
                100,
                "100",
            ):
                continue
            for hole in holes:
                try:
                    self.client.add_item_feature(
                        quote_id=quote_id,
                        item_id=str(it["ID"]),
                        diameter=float(hole["diameter"]),
                        qty=int(hole.get("qty") or 1),
                    )
                    stamped += 1
                except (SecturaFabWebsiteAuthError, SecturaFabApiError, TypeError, ValueError) as exc:
                    notes.append(f"WARNING: AddFeature Internal {pn or desc[:20]}: {exc}")
                    return notes
        if stamped:
            notes.append(f"AddFeature Internal on {stamped} hole feature(s)")
        return notes

    def finish_linear_bom_rows(
        self,
        *,
        quote_id: str,
        linear_rows: list[dict[str, Any]],
        material: str,
        library: dict[str, Any] | None,
        extra_pdfs: list[Path] | None,
    ) -> list[str]:
        """Long Finish: POST /Quote/AddItem_Linear (10 bar / 30 tube / 40 angle)."""
        if not self._website_cookie_present():
            raise SecturaFabWebsiteAuthError(WEBSITE_AUTH_GAP)
        from .line_item_ops import (
            _length_from_library,
            bom_row_cut_length,
            confirmed_cut_length_in,
            parse_cut_length,
        )

        notes: list[str] = []
        folder = (library or {}).get("folder")
        related = list((library or {}).get("related_pdfs") or [])
        for row in linear_rows:
            pn = str(row.get("part_no") or row.get("part_number") or "").strip()
            noun = str(row.get("description") or "")
            try:
                qty = max(1, int(row.get("qty") or row.get("quantity") or 1))
            except (TypeError, ValueError):
                qty = 1
            from .locked_1001898 import locked_linear_bind

            locked = locked_linear_bind(pn)
            length = (
                (locked or {}).get("length_in")
                or bom_row_cut_length(row)
                or parse_cut_length(noun)
                or _length_from_library(
                    pn,
                    library_folder=folder,
                    related_pdf_names=related,
                    extra_pdfs=extra_pdfs,
                )
                or confirmed_cut_length_in(pn)
            )
            product, sku, mismatch = self._match_linear_product(
                f"{pn} {noun}", material=material, row=row
            )
            if mismatch:
                notes.append(f"WARNING: {mismatch}")
            product_id = str((product or {}).get("ID") or "") or None
            if not product_id:
                notes.append(
                    f"WARNING: Linear {pn} has no catalog ProductID — skipped Finish"
                )
                continue
            bind = self._linear_catalog_bind(product)
            if (
                not bind
                or not is_tenant_guid(bind.get("productConfigID"))
                or str(bind.get("productConfigID") or "") == str(product_id)
            ):
                notes.append(
                    f"WARNING: Linear {pn} has no tenant productConfigID from "
                    "Read_DataLinearlookup — skipped AddItem_Linear "
                    "(empty GUID 500s; productConfigID must not equal productID)"
                )
                continue
            name = format_linear_description(
                pn, sku=sku or bind.get("sku"), length_in=length, noun=noun
            )
            extra = {k: v for k, v in bind.items() if k != "sku"}
            extra["productType"] = linear_add_product_type(
                f"{pn} {noun} {name}", sku
            )
            if not _looks_like_product_id(product_id):
                notes.append(
                    f"WARNING: Linear {pn} ProductID {product_id!r} is not a "
                    "catalog GUID — skipped AddItem_Linear"
                )
                continue
            try:
                length_f = float(length) if length is not None else 0.0
            except (TypeError, ValueError):
                length_f = 0.0
            if length_f <= 0:
                notes.append(
                    f"WARNING: Linear {pn} has no cut length — skipped AddItem_Linear"
                )
                continue
            from .website import build_linear_add_payload, redact_linear_add_keys

            try:
                bag = build_linear_add_payload(
                    quote_id,
                    product_id=product_id,
                    qty=qty,
                    length=length_f,
                    material=material,
                    machine="Saw",
                    name=name,
                    extra=extra,
                )
            except ValueError as exc:
                notes.append(
                    f"WARNING: Linear {pn} AddItem_Linear payload incomplete ({exc})"
                )
                continue
            try:
                self.client.add_item_linear(
                    quote_id=quote_id,
                    product_id=product_id,
                    qty=qty,
                    length=length_f,
                    material=material,
                    machine="Saw",
                    name=name,
                    extra=extra,
                )
            except SecturaFabWebsiteAuthError as exc:
                raise SecturaFabWebsiteAuthError(
                    f"{WEBSITE_SESSION_EXPIRED} — AddItem_Linear 302 ({exc})",
                    status_code=getattr(exc, "status_code", None),
                    body=getattr(exc, "body", None),
                ) from exc
            except Exception as exc:
                notes.append(
                    f"WARNING: Long AddItem_Linear {pn} SKU={sku or product_id} "
                    f"PT={bag.get('productType')} length={length_f} failed ({exc}) "
                    f"form[{redact_linear_add_keys(bag)}] — continuing"
                )
                continue
            notes.append(
                f"Long POST /Quote/AddItem_Linear {pn} SKU={sku or product_id} "
                f"qty={qty} length={length_f} PT={bag.get('productType')}"
            )
        after = count_linear_product_type(self._read_quote_items(quote_id))
        if linear_rows and after <= 0:
            notes.append(
                "WARNING: AddItem_Linear produced 0 Linear ProductType 10/30/40 "
                "lines — not aborting weld/nest"
            )
        return notes

    def _finish_session_error(self, exc: BaseException | None = None) -> str:
        cookie = effective_website_cookie()
        bits = [
            WEBSITE_SESSION_EXPIRED,
            CHROME_SESSION_REQUIRED,
            f"session_found={str(bool(cookie)).lower()}",
        ]
        if cookie:
            bits.append("source=env")
        if exc:
            bits.append(str(exc))
        return " ".join(bits)

    def _fail_push(
        self,
        *,
        msg: str,
        notes: list[str],
        quote_id: str | None,
        quote_number: str | None,
        quote_request_id: str | None,
        uploaded: list[str],
        attempts: int,
        item_count: int | None = None,
    ) -> PushResult:
        if msg not in notes:
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
            item_count=item_count if item_count is not None else (
                self._peek_item_count(quote_id) if quote_id else 0
            ),
            ready=False,
            status="failed",
            last_error=msg,
            attempts=attempts,
        )

    def _verify_gold_anchors(self, quote: dict[str, Any]) -> list[str]:
        notes: list[str] = []
        for it in quote.get("ItemList") or []:
            if not isinstance(it, dict):
                continue
            desc = str(it.get("Description") or "")
            try:
                unit = float(it.get("UnitCost") or 0)
            except (TypeError, ValueError):
                unit = 0.0
            if "14501-1" in desc or desc.startswith("14501"):
                ok = (
                    item_has_pr_tag(it)
                    and item_has_laser_pack(it)
                    and unit > 0
                    and "14501-1" in desc
                )
                notes.append(
                    "GET 14501-1 "
                    + (
                        "PASS PR + laser pack + UnitCost>0"
                        if ok
                        else "FAIL — want PR + Laser/Drafting/Laser-Setup/"
                        "Sheet Loading/Deburr + UnitCost>0 + dashed PN"
                    )
                )
            if "29860-3" in desc:
                try:
                    pt = int(it.get("ProductType"))
                except (TypeError, ValueError):
                    pt = None
                ok = (
                    pt == 40
                    and item_has_saw_pack(it)
                    and unit > 0
                    and not item_has_grafted_saw_tags(it)
                )
                notes.append(
                    "GET 29860-3 "
                    + (
                        "PASS PT 40 + Saw/Saw Setup + UnitCost>0 + no Saw badge"
                        if ok
                        else "FAIL — want PT 40 (angle) + Saw/Saw-Setup CalculatorNames "
                        "+ UnitCost>0 + no Saw badge"
                    )
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
            extra_org_paths = [
                p
                for p in (
                    *list(library.get("searched_roots") or []),
                    library.get("folder"),
                    str(job_pdf.parent) if job_pdf else None,
                    title,
                )
                if p
            ]
            organization_name = detect_organization(
                pdf_path=job_pdf,
                library_folder=library.get("folder"),
                extra_paths=extra_org_paths,
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
            # STEP: no AF → no /part/create → do not mint (live aa86d56).
            # 43MB Upload 502 (live 106687-1) — do not mint, do not chunk.
            if cad:
                if cadimport_step_too_large(cad):
                    n = cadimport_step_bytes(cad)
                    msg = (
                        f"STEP {n} B exceeds CadImport Upload proven size "
                        f"({CADIMPORT_UPLOAD_MAX_BYTES} B; 27MB 200, 32MB+ 502) "
                        "— not minting, not chunking, not Image Files"
                    )
                    notes.append(msg)
                    return PushResult(
                        ok=False,
                        error=msg,
                        notes=notes,
                        status="failed",
                        attempts=createfile_attempts,
                    )
                notes.extend(self.preflight_step_antiforgery())
                if (
                    callable(
                        getattr(type(self.client), "ensure_quote_antiforgery", None)
                    )
                    and getattr(self.client, "_af_source", "") != "chrome_dom"
                ):
                    return PushResult(
                        ok=False,
                        error=(
                            "af_source!=chrome_dom — not minting a new quote "
                            "(cookie_quote_html is the wrong claims identity)"
                        ),
                        notes=notes,
                        status="failed",
                        attempts=createfile_attempts,
                    )
            quote_number = self.allocate_quote_number(part_key)
            raw_title = (
                extract_assembly_description(
                    part_key=part_key,
                    pdf_path=Path(pdf_path) if pdf_path else None,
                    library_folder=library.get("folder"),
                    related_pdf_names=list(library.get("related_pdfs") or []),
                )
                or title_from_stp_takeoff(takeoff)
                or title_from_library_folder(library.get("folder"), part_key=part_key)
                or title_from_library_folder(title, part_key=part_key)
                or title_from_job_title(title, part_key=part_key)
                or title_from_bom_family(bom_rows)
            )
            if (
                is_drawing_boilerplate_title(raw_title)
                or is_nested_child_weldment_title(raw_title)
                or is_material_callout_title(raw_title)
            ):
                if is_nested_child_weldment_title(raw_title):
                    notes.append(
                        "WARNING: rejected child GATE/REST/PLATE quote title "
                        "— use assembly weldment header"
                    )
                if is_material_callout_title(raw_title):
                    notes.append(
                        "WARNING: rejected 12GA/A1011 material quote title "
                        "— use drawing header (live 107292-1)"
                    )
                raw_title = (
                    title_from_stp_takeoff(takeoff)
                    or title_from_library_folder(library.get("folder"), part_key=part_key)
                    or title_from_library_folder(title, part_key=part_key)
                    or title_from_job_title(title, part_key=part_key)
                    or title_from_bom_family(bom_rows)
                )
            elif is_child_part_title(raw_title):
                fallback = (
                    title_from_stp_takeoff(takeoff)
                    or title_from_library_folder(library.get("folder"), part_key=part_key)
                    or title_from_library_folder(title, part_key=part_key)
                    or title_from_job_title(title, part_key=part_key)
                    or title_from_bom_family(bom_rows)
                )
                if fallback and not is_child_part_title(fallback) and re.search(
                    r"WELDMENT|ASSEMBLY|\bASSY\b|\bASM\b",
                    str(fallback),
                    re.I,
                ):
                    notes.append(
                        "WARNING: rejected child GATE/REST/PLATE quote title "
                        "— use assembly weldment header"
                    )
                    raw_title = fallback
            if (
                is_nested_child_weldment_title(raw_title)
                or is_drawing_boilerplate_title(raw_title)
                or is_material_callout_title(raw_title)
            ):
                raw_title = None
            assembly_description = format_assembly_description(part_key, raw_title)
            header_noun = bool(
                bom_rows
                or (
                    raw_title
                    and not is_material_callout_title(raw_title)
                    and re.search(
                        r"WELDMENT|ASSEMBLY|\bASSY\b|\bASM\b|\bPLATE\b|"
                        r"\bPLATFORM\b|\bMOUNT\b",
                        str(raw_title),
                        re.I,
                    )
                )
            )
            if header_noun:
                quote_description = format_quote_header_description(
                    raw_title, part_key=part_key
                )
            else:
                quote_description = format_assembly_description(part_key, raw_title)
            if raw_title:
                desc_note = f"Quote Description from assembly drawing: {quote_description}"
            else:
                desc_note = f"Quote Description from job title: {quote_description}"
            if not quote_description or is_bare_part_number(quote_description, part_key):
                notes.append(
                    "WARNING: Quote Description is still a bare PN — "
                    "need folder / PDF / BOM weldment title"
                )
            quote_id = self.create_quote(
                quote_number=quote_number,
                description=quote_description or "",
                memo="",
                quote_request_id=quote_request_id,
            )
            from .forbidden_quotes import is_forbidden_quote_id

            if is_forbidden_quote_id(quote_id):
                raise SecturaFabApiError(
                    f"Refusing to PATCH/reuse forbidden live quote {quote_id}"
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
                        description=quote_description or None,
                    )
                )

            extra_pdfs = [job_pdf] if has_job_pdf else None
            cad_pdfs = [] if cad else self._library_cad_pdfs(bom_rows, library)
            linear_bom = self._library_linear_rows(bom_rows)
            expect_cad = bool(cad or cad_pdfs or ((drawings or has_job_pdf) and not loose_linear))
            expect_linear = bool(loose_linear or linear_bom)
            items_before_finish = self._peek_item_count(quote_id)
            website_cookie = self._website_cookie_present()
            attempted_pack_stamp = False
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
                            quote_request_id=quote_request_id,
                        )
                    )
                    uploaded.extend(p.name for p in cad)
                    attempted_pack_stamp = True
                elif not website_cookie:
                    notes.append(
                        "Pack-stamp fail-closed — no website session; "
                        "skipped Image Files / Long. Public nest/weld continue."
                    )
                elif loose_linear:
                    notes.extend(
                        self.add_loose_linears(
                            quote_id=quote_id,
                            description=quote_description or title or part_key,
                            material=material,
                            qty=qty,
                        )
                    )
                    attempted_pack_stamp = True
                elif cad_pdfs or linear_bom:
                    if cad_pdfs:
                        try:
                            notes.extend(
                                self.finish_pdf_files(
                                    quote_id=quote_id,
                                    pdf_files=cad_pdfs,
                                    material=material,
                                    thickness=thickness,
                                    qty=qty,
                                    description=quote_description or title,
                                    bom_rows=bom_rows,
                                    library=library,
                                    extra_pdfs=extra_pdfs,
                                    takeoff=takeoff,
                                )
                            )
                            uploaded.extend(p.name for p in cad_pdfs)
                        except SecturaFabWebsiteAuthError as exc:
                            return self._fail_push(
                                msg=self._finish_session_error(exc),
                                notes=notes,
                                quote_id=quote_id,
                                quote_number=quote_number,
                                quote_request_id=quote_request_id,
                                uploaded=uploaded,
                                attempts=createfile_attempts,
                            )
                        except (
                            SecturaFabApiError,
                            ValueError,
                            TypeError,
                            OSError,
                        ) as exc:
                            notes.append(
                                f"WARNING: Image Files Finish failed ({exc}) — "
                                "continuing Linear / weld / nest"
                            )
                    if linear_bom:
                        try:
                            notes.extend(
                                self.finish_linear_bom_rows(
                                    quote_id=quote_id,
                                    linear_rows=linear_bom,
                                    material=material,
                                    library=library,
                                    extra_pdfs=extra_pdfs,
                                )
                            )
                        except SecturaFabWebsiteAuthError as exc:
                            return self._fail_push(
                                msg=self._finish_session_error(exc),
                                notes=notes,
                                quote_id=quote_id,
                                quote_number=quote_number,
                                quote_request_id=quote_request_id,
                                uploaded=uploaded,
                                attempts=createfile_attempts,
                            )
                        except Exception as exc:
                            notes.append(
                                f"WARNING: Long AddItem_Linear failed ({exc}) — "
                                "not aborting weld/nest"
                            )
                    attempted_pack_stamp = True
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
                                bom_rows=bom_rows,
                                library=library,
                                extra_pdfs=extra_pdfs,
                                takeoff=takeoff,
                            )
                        )
                        uploaded.extend(p.name for p in pdfs)
                    attempted_pack_stamp = True
                else:
                    msg = (
                        "No STEP/STP, no library Cad PDFs, and no job PDF — "
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
                if attempted_pack_stamp:
                    peek = self._read_quote_items(quote_id)
                    if expect_cad and count_cad_product_type(peek) <= 0:
                        msg = (
                            "CAD Files / AddItem_DXFFiles Finish landed 0 Cad lines — "
                            "empty assembly shell is not success"
                            if cad
                            else "Image Files Finish landed 0 Cad lines — "
                            "empty assembly shell is not success"
                        )
                        if not website_cookie:
                            msg = f"{msg} {self._finish_session_error()}"
                        return self._fail_push(
                            msg=msg,
                            notes=notes,
                            quote_id=quote_id,
                            quote_number=quote_number,
                            quote_request_id=quote_request_id,
                            uploaded=uploaded,
                            attempts=createfile_attempts,
                            item_count=len(quote_item_rows(peek)),
                        )
                    created = len(quote_item_rows(peek)) > items_before_finish
                    peek_dict = peek if isinstance(peek, dict) else {}
                    gold = finish_produced_gold(
                        peek_dict,
                        expect_cad=expect_cad,
                        expect_linear=expect_linear,
                    )
                    cad_gold = (
                        finish_produced_gold(
                            peek_dict,
                            expect_cad=True,
                            expect_linear=False,
                        )
                        if expect_cad
                        else True
                    )
                    if not created or not gold:
                        fail_closed = False
                        if cad and (not created or not cad_gold):
                            fail_closed = True
                        elif expect_cad and not cad_gold:
                            fail_closed = True
                        extra = (
                            "AddItem_PDFFiles HTTP 200 is not session-expired; "
                            "PR / laser pack / UnitCost did not stamp."
                            if not cad_gold
                            else (
                                ""
                                if fail_closed
                                else "Continuing weld/nest/kids. "
                            )
                        )
                        msg = (
                            "WARNING: Finish did not stamp gold OperationCostList "
                            "CalculatorNames yet (Cad PR + laser pack / Linear "
                            "Saw+Saw-Setup). "
                            + extra
                        )
                        if fail_closed and not website_cookie:
                            msg = f"{msg} {CHROME_SESSION_REQUIRED}"
                        notes.append(msg)
                        if fail_closed:
                            return PushResult(
                                ok=False,
                                error=msg,
                                notes=notes,
                                quote_id=quote_id,
                                quote_number=quote_number,
                                quote_request_id=quote_request_id,
                                created_new_quote=True,
                                uploaded_files=uploaded,
                                item_count=self._peek_item_count(quote_id),
                                status="failed",
                                last_error=msg,
                                attempts=createfile_attempts,
                            )
                    if website_cookie and not cad and bom_rows:
                        notes.extend(
                            self.finish_website_weldment(
                                quote_id=quote_id,
                                part_key=part_key,
                                bom_rows=bom_rows,
                                library=library,
                                extra_pdfs=list(extra_pdfs or []),
                                material=material,
                                assembly_description=assembly_description,
                                takeoff=takeoff,
                            )
                        )
            except SecturaFabWebsiteAuthError as exc:
                return self._fail_push(
                    msg=self._finish_session_error(exc),
                    notes=notes,
                    quote_id=quote_id,
                    quote_number=quote_number,
                    quote_request_id=quote_request_id,
                    uploaded=uploaded,
                    attempts=createfile_attempts,
                )
            except (
                SecturaFabApiError,
                ValueError,
                TypeError,
                OSError,
            ) as exc:
                msg = f"WARNING: Image Files / Long raised ({exc})"
                notes.append(msg)
                if cad:
                    return self._fail_push(
                        msg=msg,
                        notes=notes,
                        quote_id=quote_id,
                        quote_number=quote_number,
                        quote_request_id=quote_request_id,
                        uploaded=uploaded,
                        attempts=createfile_attempts,
                    )
                notes.append(
                    "WARNING: Image Files / Long raised — not aborting weld/nest"
                )
                if website_cookie and not cad and bom_rows:
                    try:
                        notes.extend(
                            self.finish_website_weldment(
                                quote_id=quote_id,
                                part_key=part_key,
                                bom_rows=bom_rows,
                                library=library,
                                extra_pdfs=list(extra_pdfs or []),
                                material=material,
                                assembly_description=assembly_description,
                                takeoff=takeoff,
                            )
                        )
                    except (
                        SecturaFabApiError,
                        SecturaFabWebsiteAuthError,
                        ValueError,
                        TypeError,
                        OSError,
                    ) as weldment_exc:
                        notes.append(f"WARNING: website weldment continue failed: {weldment_exc}")

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
            if not website_cookie and not cad and (expect_cad or expect_linear):
                msg = (
                    "Pack-stamp fail-closed — Image Files / Long not run. "
                    + self._finish_session_error()
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
                    item_count=self._peek_item_count(quote_id),
                    status="failed",
                    last_error=msg,
                    attempts=createfile_attempts,
                )
            notes.extend(ensure_imperial_item_units(self.client, quote_id))
            notes.append(
                "Skipped grafted Profile / quickAddCAD fallback — "
                "CadImport FileList + Finish write Primary Costs"
            )

            notes.extend(
                persist_classified_item_fields(
                    self.client,
                    quote_id,
                    bom_rows=bom_rows,
                    default_material=material,
                    default_thickness=thickness,
                    library_folder=library.get("folder"),
                    related_pdf_names=list(library.get("related_pdfs") or []),
                    persist_cad=not website_cookie,
                    persist_linear=False,
                )
            )
            notes.append(
                "Skipped grafted Laser/Drafting/Saw packs — "
                "Finish / New Line Item write Primary Costs "
                "(addplate/addLinear only persist Material/Length/UnitCost)"
            )
            extra_pdfs = list(drawings or [])
            folder = library.get("folder")
            if folder and Path(folder).is_dir():
                extra_pdfs.extend(
                    p
                    for p in Path(folder).iterdir()
                    if p.is_file() and p.suffix.lower() == ".pdf"
                )
            lin_kwargs = dict(
                bom_rows=bom_rows,
                default_material=material,
                default_thickness=thickness,
                library_folder=library.get("folder"),
                related_pdf_names=list(library.get("related_pdfs") or []),
                extra_pdfs=extra_pdfs,
                persist_cad=False,
                persist_linear=True,
                retry_linear=True,
            )
            notes.extend(
                persist_classified_item_fields(self.client, quote_id, **lin_kwargs)
            )
            notes.extend(
                persist_quote_header(
                    self.client,
                    quote_id,
                    organization_name=organization_name,
                    description=quote_description,
                )
            )
            notes.extend(retype_linears_to_pt10_keep_persist(self.client, quote_id))
            peek = self.client.get_json(f"v1/quote/{quote_id}")
            cad_wiped = False
            for it in peek.get("ItemList") or []:
                if not isinstance(it, dict):
                    continue
                if str(it.get("Category") or it.get("ItemType") or "") != "Cad":
                    continue
                if it.get("ProductType") not in (100, "100"):
                    continue
                mat = str(it.get("Material") or it.get("MaterialGrade") or "").strip()
                try:
                    thk = float(it.get("Thickness") or 0)
                except (TypeError, ValueError):
                    thk = 0.0
                if not mat or thk <= 0:
                    cad_wiped = True
                    break
            if cad_wiped or count_linear_get_misses(peek, bom_rows):
                if website_cookie:
                    notes.append(
                        "GET persist fields empty after PT 10 overlay — "
                        "website session: skip re-addplate (wipes Image Files packs); "
                        "re-addLinear only"
                    )
                    notes.extend(
                        persist_classified_item_fields(self.client, quote_id, **lin_kwargs)
                    )
                else:
                    notes.append(
                        "GET persist fields empty after PT 10 overlay — "
                        "re-addplate + re-addLinear, no further quote POST"
                    )
                    notes.extend(
                        persist_classified_item_fields(
                            self.client,
                            quote_id,
                            bom_rows=bom_rows,
                            default_material=material,
                            default_thickness=thickness,
                            library_folder=library.get("folder"),
                            related_pdf_names=list(library.get("related_pdfs") or []),
                            persist_linear=False,
                        )
                    )
                    notes.extend(
                        persist_classified_item_fields(self.client, quote_id, **lin_kwargs)
                    )

            detail = self.client.get_json(f"v1/quote/{quote_id}")
            notes.extend(self._verify_gold_anchors(detail if isinstance(detail, dict) else {}))
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
                return self._fail_push(
                    msg=(
                        "SecturaFAB quote has 0 line items after import — "
                        "push marked failed (empty ItemList)"
                    ),
                    notes=notes,
                    quote_id=quote_id,
                    quote_number=stored_number,
                    quote_request_id=quote_request_id,
                    uploaded=uploaded,
                    attempts=createfile_attempts,
                    item_count=0,
                )
            cad_landed = count_cad_product_type(detail)
            lin_landed = count_linear_product_type(detail)
            if expect_cad and cad_landed <= 0:
                return self._fail_push(
                    msg=(
                        "CAD Files / AddItem_DXFFiles Finish landed 0 Cad lines — "
                        "empty assembly shell is not success"
                        if cad
                        else "Image Files Finish landed 0 Cad lines — "
                        "empty assembly shell is not success"
                    ),
                    notes=notes,
                    quote_id=quote_id,
                    quote_number=stored_number,
                    quote_request_id=quote_request_id,
                    uploaded=uploaded,
                    attempts=createfile_attempts,
                    item_count=final_count,
                )
            if (expect_cad or expect_linear) and cad_landed <= 0 and lin_landed <= 0:
                return self._fail_push(
                    msg=(
                        f"item_count={final_count} assembly shell only is not success"
                    ),
                    notes=notes,
                    quote_id=quote_id,
                    quote_number=stored_number,
                    quote_request_id=quote_request_id,
                    uploaded=uploaded,
                    attempts=createfile_attempts,
                    item_count=final_count,
                )

            strict_qa = bool(organization_name) or bool(bom_rows)
            qa = evaluate_quote_get(
                detail,
                part_key=part_key,
                expected_org=organization_name,
                expected_header=(
                    quote_description
                    if strict_qa
                    and quote_description
                    and not is_bare_part_number(quote_description, part_key)
                    else None
                ),
                expected_assembly_title=(
                    assembly_description
                    if strict_qa
                    and assembly_description
                    and not is_bare_part_number(assembly_description, part_key)
                    else None
                ),
                bom_rows=bom_rows,
                require_org=bool(organization_name),
            )
            notes.extend(f"QA: {n}" for n in qa.notes)
            if not qa.ok:
                msg = "Live GET QA failed: " + "; ".join(qa.failures)
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
                    item_count=final_count,
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
