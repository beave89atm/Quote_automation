"""Apply drawing flat-pattern Length × Width onto sheet/plate quote lines.

SecturaFAB ``quickAddCAD`` often fills Length/Width from STEP unbend or PDF
outline — sometimes wrongly (e.g. 20×30 vs drawing 26.85×8.49). When the job
PDF has a clear flat-pattern callout, correct plate items before Profile attach.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from quote_core.flat_pattern import extract_flat_pattern_dims

from .client import SecturaFabClient
from .profile_ops import _is_laser_plate
from .weld_ops import _desc_token

# Existing imperial / metric dim suffix on CAD Descriptions.
_DESC_DIM_RE = re.compile(
    r"([\d.]+)\s*(?:mm|in|inches?)?\s*[Xx×]\s*([\d.]+)\s*(?:mm|in|inches?)?\s*$",
    re.IGNORECASE,
)

# Relative tolerance: correct when either axis diverges more than this.
_DIVERGE_FRAC = 0.10


def _item_matches_part(it: dict[str, Any], part_key: str | None) -> bool:
    if not part_key:
        return True
    key = str(part_key).strip()
    if key.upper().startswith("PN "):
        key = key[3:].strip()
    if not key:
        return True
    token = _desc_token(str(it.get("Description") or ""))
    if token == key:
        return True
    desc = str(it.get("Description") or "")
    return desc.upper().startswith(key.upper())


def _dims_need_correction(
    length: float,
    width: float,
    flat_l: float,
    flat_w: float,
) -> bool:
    if length <= 0 or width <= 0:
        return True
    cur = sorted((float(length), float(width)), reverse=True)
    want = (float(flat_l), float(flat_w))
    for c, w in zip(cur, want):
        if w <= 0:
            return True
        if abs(c - w) / w > _DIVERGE_FRAC:
            return True
    return False


def _rewrite_description_flat_dims(desc: str, length: float, width: float) -> str:
    """Replace trailing L×W suffix with inch flat dims; leave prefix alone."""
    if not desc:
        return desc
    label = f"{length:g} in X {width:g} in"
    if _DESC_DIM_RE.search(desc):
        return _DESC_DIM_RE.sub(label, desc)
    return desc.rstrip() + f" {label}"


def _apply_flat_to_item(it: dict[str, Any], length: float, width: float) -> bool:
    """Mutate one ItemList row. Returns True if anything changed."""
    try:
        cur_l = float(it.get("Length") or 0)
        cur_w = float(it.get("Width") or 0)
    except (TypeError, ValueError):
        cur_l = cur_w = 0.0

    if not _dims_need_correction(cur_l, cur_w, length, width):
        return False

    it["Length"] = length
    it["Width"] = width
    it["Length_Units"] = "inch"
    desc = str(it.get("Description") or "")
    new_desc = _rewrite_description_flat_dims(desc, length, width)
    if new_desc != desc:
        it["Description"] = new_desc

    data = it.get("Data")
    if isinstance(data, str) and data.startswith("DataPart:"):
        try:
            payload: dict[str, Any] = json.loads(data.split(":", 1)[1])
        except json.JSONDecodeError:
            payload = {}
        payload["PartLength"] = length
        payload["PartWidth"] = width
        payload["Length_Units"] = "inch"
        payload["PartLength_Units"] = "inch"
        payload["Thickness_Units"] = "inch"
        it["Data"] = "DataPart:" + json.dumps(payload, separators=(",", ":"))
    # OperationCostList left untouched on the item dict.
    return True


def ensure_flat_pattern_dims(
    client: SecturaFabClient,
    quote_id: str,
    pdf_path: Path | str | None,
    *,
    match_part: str | None = None,
) -> list[str]:
    """
    Set plate ItemList Length/Width from PDF flat-pattern callouts when needed.

    Call **before** Profile attach (full-quote POST can wipe ops if run later).
    If the PDF has no parseable flat dims, leave SecturaFAB's import dims alone.

    When ``match_part`` is set (BOM component PN), only that Description is updated.
    """
    if not pdf_path:
        return ["No PDF — skipped flat-pattern dim correction"]
    path = Path(pdf_path)
    if not path.is_file():
        return [f"PDF missing for flat-pattern dims: {path.name}"]

    flat = extract_flat_pattern_dims(path)
    if not flat:
        return [
            f"No flat-pattern L×W on {path.name} — kept SecturaFAB import dims"
        ]
    flat_l, flat_w = flat

    detail = client.get_json(f"v1/quote/{quote_id}")
    items = list(detail.get("ItemList") or [])
    if not items:
        return ["No items — skipped flat-pattern dim correction"]

    changed = 0
    for it in items:
        if not _is_laser_plate(it):
            continue
        if not _item_matches_part(it, match_part):
            continue
        if _apply_flat_to_item(it, flat_l, flat_w):
            changed += 1

    if not changed:
        scope = f" for {match_part}" if match_part else ""
        return [
            f"Plate dims already match flat pattern "
            f"{flat_l:g}\" × {flat_w:g}\" from {path.name}{scope}"
        ]

    # Preserve OperationCostList (and everything else) via full-quote POST of
    # the mutated detail we just read — same pattern as imperial_ops.
    save = client.request("POST", "v1/quote", json=detail)
    if save.status_code >= 400:
        return [f"Flat-pattern dim save failed ({save.status_code})"]
    return [
        f"Set flat-pattern Length×Width to {flat_l:g}\" × {flat_w:g}\" "
        f"on {changed} plate item(s) from {path.name}"
    ]
