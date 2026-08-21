"""Force quote line labels/dims to inch after metric STEP imports.

SecturaFAB's STEP importer often keeps millimetre Length/Width even when
quickAddCAD is called with units=inch. Shop standard is imperial, so we
rewrite description dim labels and attempt to store inch Length/Width.
"""

from __future__ import annotations

import json
import re
from typing import Any

from .client import SecturaFabClient

_MM_DIM_RE = re.compile(
    r"([\d.]+)\s*mm\s*[Xx×]\s*([\d.]+)\s*mm",
    re.IGNORECASE,
)
_M_DIM_RE = re.compile(
    r"([\d.]+)\s*m\s*[Xx×]\s*([\d.]+)\s*m\b",
    re.IGNORECASE,
)


def _mm_to_in(val: float) -> float:
    return val / 25.4


def _looks_like_mm(length: float, width: float, units: str) -> bool:
    u = (units or "").strip().lower()
    if u.startswith("mill"):
        return True
    if u in {"meter", "metre", "m"}:
        # Metre values this large are almost always mis-labeled mm coords.
        return length > 1.0 and width > 1.0
    if u in {"inch", "in", "inches"}:
        # Inch label but clearly mm magnitude (e.g. 873 in for a coupler plate).
        return length > 120 and width > 120
    return length > 60 and width > 60


def rewrite_description_dims_to_inch(desc: str) -> str:
    """Convert ``N mm X M mm`` (or metre) dim labels in a Description to inches."""
    if not desc:
        return desc
    if _MM_DIM_RE.search(desc):
        return _MM_DIM_RE.sub(
            lambda m: (
                f"{_mm_to_in(float(m.group(1))):.3f} in X "
                f"{_mm_to_in(float(m.group(2))):.3f} in"
            ),
            desc,
        )
    if _M_DIM_RE.search(desc):
        return _M_DIM_RE.sub(
            lambda m: (
                f"{_mm_to_in(float(m.group(1))):.3f} in X "
                f"{_mm_to_in(float(m.group(2))):.3f} in"
            ),
            desc,
        )
    return desc


def description_has_metric_dims(desc: str) -> bool:
    return bool(_MM_DIM_RE.search(desc or "") or _M_DIM_RE.search(desc or ""))


def ensure_imperial_item_units(
    client: SecturaFabClient,
    quote_id: str,
) -> list[str]:
    """Rewrite mm/m Length/Width + description labels to inch."""
    detail = client.get_json(f"v1/quote/{quote_id}")
    items = list(detail.get("ItemList") or [])
    if not items:
        return ["No items — skipped imperial unit cleanup"]

    changed = 0
    for it in items:
        units = str(it.get("Length_Units") or "")
        try:
            length = float(it.get("Length") or 0)
            width = float(it.get("Width") or 0)
        except (TypeError, ValueError):
            continue
        desc = str(it.get("Description") or "")
        desc_has_mm = description_has_metric_dims(desc)
        dims_mm = _looks_like_mm(length, width, units)
        if not dims_mm and not desc_has_mm:
            if units.lower().startswith("mill") or units.lower() in {"meter", "metre"}:
                it["Length_Units"] = "inch"
                changed += 1
            continue

        # Only scale Length/Width when magnitude/units say mm — avoid double-convert.
        if dims_mm:
            it["Length"] = _mm_to_in(length)
            it["Width"] = _mm_to_in(width)
            it["Length_Units"] = "inch"
        elif units.lower().startswith("mill") or units.lower() in {
            "meter",
            "metre",
            "m",
        }:
            it["Length_Units"] = "inch"

        if desc_has_mm:
            it["Description"] = rewrite_description_dims_to_inch(desc)

        data = it.get("Data")
        if isinstance(data, str) and data.startswith("DataPart:"):
            try:
                payload: dict[str, Any] = json.loads(data.split(":", 1)[1])
            except json.JSONDecodeError:
                payload = {}
            try:
                pl = float(payload.get("PartLength") or 0)
                pw = float(payload.get("PartWidth") or 0)
            except (TypeError, ValueError):
                pl = pw = 0.0
            if _looks_like_mm(pl, pw, str(payload.get("Length_Units") or units)):
                payload["PartLength"] = _mm_to_in(pl)
                payload["PartWidth"] = _mm_to_in(pw)
            payload["Length_Units"] = "inch"
            payload["PartLength_Units"] = "inch"
            payload["Thickness_Units"] = "inch"
            it["Data"] = "DataPart:" + json.dumps(payload, separators=(",", ":"))
        changed += 1

    if not changed:
        return ["Quote items already look imperial"]

    from .quote_update import update_item_fields

    ok = update_item_fields(
        client,
        quote_id,
        items,
        fields=["Length", "Width", "Length_Units", "Description", "Data"],
    )
    if not ok:
        return [
            "WARNING: Imperial unit cleanup via item-level update failed — "
            "not falling back to POST v1/quote (that wipes Cad Profile)"
        ]
    return [f"Normalized {changed} item(s) to inch (imperial) labels/dims"]
