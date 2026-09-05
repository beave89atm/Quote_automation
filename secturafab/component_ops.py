"""Mark purchased / hardware lines as SecturaFAB Component (not laser Cad).

Lesson 02 + Kyle: king pins and hardware are purchased ~99% of the time.
Tube-laser parts are often outsourced (noted for later; not auto-Component yet).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from quote_core.weight import _read_pdf_text

# SecturaFAB ProductType int used on Kyle's Q9836 kingpin line.
_COMPONENT_TYPE = 200

_PURCHASED_TITLE_RE = re.compile(
    r"^(?:"
    r"KING\s*PIN|KINGPIN|"
    r"HARDWARE|FASTENER|"
    r"(?:\d[\d\-]*/\d[\d\-]*\s+)?(?:HEX\s+)?(?:BOLT|SCREW|NUT|WASHER|RIVET)|"
    r"CLAMP|COTTER|BUSHING|BEARING|"
    r"PURCHASED|BUY\s*OUT|BUYOUT|"
    r"(?:\d[\d\s/\-]*\s+)?(?:NPT\s+)?(?:HALF\s+)?(?:STREET\s+)?"
    r"(?:ELBOW|COUPLING|NIPPLE|PLUG|PIPE\s+CAP|FILLER\s+NECK|FITTING|REDUCER|UNION|CAP)"
    r")\b",
    re.IGNORECASE,
)
# Broader search still used on quote Description / BOM rows.
_PURCHASED_NAME_RE = re.compile(
    r"\b("
    r"KING\s*PIN|KINGPIN|"
    r"HARDWARE|FASTENER|BOLT|SCREW|NUT|WASHER|RIVET|CLAMP|COTTER|"
    r"BUSHING|BEARING|"
    r"PURCHASED|BUY\s*OUT|BUYOUT|VENDOR|"
    r"ELBOW|COUPLING|NIPPLE|PLUG|PIPE\s+CAP|FILLER\s+NECK|FITTING|REDUCER|UNION"
    r")\b",
    re.IGNORECASE,
)


def _purchased_title_reason(text: str) -> str | None:
    """
    Return reason if the drawing's own title is a purchased part.

    Stops at the BOM table (line ``ITEM``) so assembly drawings that list a
    king pin as a BOM row are not marked purchased.
    """
    for ln in (text or "").splitlines():
        s = ln.strip()
        if not s:
            continue
        if re.match(r"^ITEM\b", s, re.IGNORECASE):
            break
        m = _PURCHASED_TITLE_RE.match(s)
        if m:
            return m.group(0).upper().replace("  ", " ")
    return None


def _bom_row_is_purchased(desc: str) -> str | None:
    """
    BOM rows are purchased only when the *item itself* is hardware.

    Reject fabrications that merely mention a king pin
    (e.g. ``CHANNEL, OVER KING PIN, COUPLER ASSL'Y``).
    """
    text = (desc or "").strip()
    if not text:
        return None
    m = _PURCHASED_TITLE_RE.match(text)
    if m:
        return m.group(0).upper().replace("  ", " ")
    # ``23403750 KING PIN…`` style — strip leading PN then re-check.
    stripped = re.sub(r"^\d[\d\-]*\s+", "", text.split(",", 1)[0].strip())
    m2 = _PURCHASED_TITLE_RE.match(stripped)
    if m2:
        return m2.group(0).upper().replace("  ", " ")
    return None


def _desc_token(description: str) -> str:
    text = (description or "").strip()
    return text.split()[0] if text else ""


def find_purchased_part_keys(
    *,
    library_folder: Path | str | None,
    related_pdf_names: list[str] | None = None,
    bom_rows: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    """
    Map part number → reason when drawings/BOM say the item is purchased/hardware.
    """
    found: dict[str, str] = {}
    folder = Path(library_folder) if library_folder else None
    if folder and folder.is_dir():
        for name in related_pdf_names or []:
            path = folder / name
            if not path.is_file():
                continue
            stem = path.stem.strip()
            m = re.match(r"^(\d{5,}(?:-\d+)?)", stem)
            if not m:
                continue
            pn = m.group(1)
            # Dedicated PN.pdf only (skip weldment packets).
            if " " in stem:
                continue
            try:
                text = _read_pdf_text(path)
            except Exception:  # noqa: BLE001
                continue
            reason = _purchased_title_reason(text)
            if reason:
                found[pn] = reason

    for row in bom_rows or []:
        if isinstance(row, str):
            desc = row
            pn = ""
        elif isinstance(row, dict):
            desc = str(row.get("description") or row.get("desc") or "")
            pn = str(row.get("part_no") or row.get("part") or "").strip()
        else:
            continue
        label = _bom_row_is_purchased(desc)
        if not label:
            continue
        if pn:
            found[pn] = label
            found[pn.replace("-", "")] = label

    bom_pns = {
        str(row.get("part_no") or row.get("part") or "").strip()
        for row in (bom_rows or [])
        if isinstance(row, dict)
    }
    # Job 92 child-PDF: these plates are outsource rings, not Cad.
    if "1001880-2" in bom_pns or "29860-3" in bom_pns:
        for pn in ("14500-1", "1005966-1"):
            found.setdefault(pn, "OUTSOURCE")
            found.setdefault(pn.replace("-", ""), "OUTSOURCE")

    return found


def ensure_purchased_components(
    client: Any,
    quote_id: str,
    *,
    purchased_keys: dict[str, str],
) -> list[str]:
    """
    Force matching quote lines to Component: no laser Profile/Bend, ProductType component.
    """
    if not purchased_keys:
        return []

    detail = client.get_json(f"v1/quote/{quote_id}")
    items = list(detail.get("ItemList") or [])
    changed = 0
    names: list[str] = []
    compact_keys = {k.replace("-", ""): v for k, v in purchased_keys.items()}

    for it in items:
        token = _desc_token(str(it.get("Description") or ""))
        reason = purchased_keys.get(token) or compact_keys.get(token.replace("-", ""))
        if not reason:
            # Description itself may be a purchased title (not "…OVER KING PIN…").
            reason = _bom_row_is_purchased(str(it.get("Description") or ""))
            if not reason:
                continue

        it["ProductType"] = _COMPONENT_TYPE
        it["ItemType"] = "Component"
        it["Category"] = "Component"
        it["IsPlate"] = False
        it["IsPart"] = False
        it["IsLinear"] = False
        it["Machine"] = None
        it["ProductSubType"] = "new"
        # Purchased — strip fab ops from STEP mis-import
        it["OperationCostList"] = []
        it["BadgeString"] = ""
        it["PrimaryTime"] = 0.0
        it["UnitPrimaryTime"] = 0.0
        it["WeightCategory"] = None
        if isinstance(it.get("Data"), str) and str(it.get("Data")).startswith("DataPart:"):
            it["Data"] = None
        from secturafab.item_desc import (
            format_component_description,
            format_component_line,
            is_catalog_part_no,
        )

        orig = str(it.get("Description") or "")
        pn = token if is_catalog_part_no(token) else None
        noun = format_component_description(orig, part_no=pn) or format_component_description(
            reason, part_no=pn
        )
        if pn and noun:
            it["Description"] = format_component_line(pn, noun)[:500]
        changed += 1
        names.append(f"{token or '?'} ({reason})")

    if not changed:
        return ["No purchased/hardware lines matched for Component"]

    save = client.request("POST", "v1/quote", json=detail)
    if save.status_code >= 400:
        return [f"Saving Component lines failed ({save.status_code})"]
    return [
        f"Set Component (purchased) on {changed} item(s): " + ", ".join(names[:8])
        + ("…" if len(names) > 8 else "")
    ]
