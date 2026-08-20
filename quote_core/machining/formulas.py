"""Published imperial machining formulas (no shop-specific rates).

Sources (public pages, not paywalled catalogs):
- Harvey Tool: RPM = (3.82 × SFM) / D ; IPM = RPM × IPT × T
  https://www.harveytool.com/resources/general-machining-guidelines
- Kennametal: MRR = DOC × WOC × IPM
  https://www1.mscdirect.com/images/solutions/kennametal/millingTechInfoFormulas.pdf
- MachiningDoctor turning: n = 12×Vc/(π×d) ; T = L/(n×Fn) ; Q = 12×Vc×Fn×ap
  https://www.machiningdoctor.com/calculators/turning-calculators-2/

3.82 is the shop rounding of 12/π.
"""

from __future__ import annotations

import math
from typing import Iterable

RPM_SFM_FACTOR = 12.0 / math.pi  # ≈ 3.8197; Harvey/Kennametal publish 3.82


def rpm_from_sfm(sfm: float, diameter_in: float) -> float:
    """Spindle speed. Harvey Tool / Kennametal: RPM = (SFM × 3.82) / D."""
    if diameter_in <= 0:
        raise ValueError("diameter_in must be > 0")
    if sfm <= 0:
        raise ValueError("sfm must be > 0")
    return (sfm * RPM_SFM_FACTOR) / diameter_in


def clamp_rpm(rpm: float, max_rpm: float | None) -> tuple[float, bool]:
    """Cap RPM at machine max. Returns (rpm, was_clamped)."""
    if max_rpm is None or max_rpm <= 0:
        return rpm, False
    if rpm > max_rpm:
        return float(max_rpm), True
    return rpm, False


def milling_ipm(rpm: float, ipt: float, flutes: int) -> float:
    """Table feed. Harvey Tool: IPM = RPM × IPT × T."""
    if flutes <= 0:
        raise ValueError("flutes must be > 0")
    if ipt <= 0:
        raise ValueError("ipt must be > 0")
    if rpm <= 0:
        raise ValueError("rpm must be > 0")
    return rpm * ipt * flutes


def milling_mrr(doc_in: float, woc_in: float, ipm: float) -> float:
    """Metal removal rate in³/min. Kennametal: MRR = DOC × WOC × IPM."""
    if doc_in <= 0 or woc_in <= 0 or ipm <= 0:
        raise ValueError("doc_in, woc_in, and ipm must be > 0")
    return doc_in * woc_in * ipm


def time_from_path(length_in: float, ipm: float) -> float:
    """Cutting minutes from path length. T = L / IPM."""
    if ipm <= 0:
        raise ValueError("ipm must be > 0")
    if length_in < 0:
        raise ValueError("length_in must be >= 0")
    return length_in / ipm


def time_from_volume(volume_in3: float, mrr: float) -> float:
    """Cutting minutes from stock volume. T = V / MRR."""
    if mrr <= 0:
        raise ValueError("mrr must be > 0")
    if volume_in3 < 0:
        raise ValueError("volume_in3 must be >= 0")
    return volume_in3 / mrr


def turning_time_min(length_in: float, rpm: float, ipr: float) -> float:
    """One turning pass. MachiningDoctor: T = L / (n × Fn)."""
    if rpm <= 0 or ipr <= 0:
        raise ValueError("rpm and ipr must be > 0")
    if length_in < 0:
        raise ValueError("length_in must be >= 0")
    return length_in / (rpm * ipr)


def turning_time_from_sfm(length_in: float, diameter_in: float, sfm: float, ipr: float) -> float:
    """One turning pass from SFM. MachiningDoctor: T = (L × π × D) / (12 × Fn × Vc)."""
    if diameter_in <= 0 or sfm <= 0 or ipr <= 0:
        raise ValueError("diameter_in, sfm, and ipr must be > 0")
    if length_in < 0:
        raise ValueError("length_in must be >= 0")
    return (length_in * math.pi * diameter_in) / (12.0 * ipr * sfm)


def turning_mrr(sfm: float, ipr: float, doc_in: float) -> float:
    """Turning MRR in³/min. MachiningDoctor: Q = 12 × Vc × Fn × ap."""
    if sfm <= 0 or ipr <= 0 or doc_in <= 0:
        raise ValueError("sfm, ipr, and doc_in must be > 0")
    return 12.0 * sfm * ipr * doc_in


def interpolate_ipt(diameter_in: float, table: dict[float, float] | Iterable[tuple[float, float]]) -> float:
    """Linear interpolate chip load (IPT) vs cutter diameter."""
    if isinstance(table, dict):
        pairs = sorted((float(k), float(v)) for k, v in table.items())
    else:
        pairs = sorted((float(k), float(v)) for k, v in table)
    if not pairs:
        raise ValueError("empty IPT table")
    if diameter_in <= pairs[0][0]:
        return pairs[0][1]
    if diameter_in >= pairs[-1][0]:
        return pairs[-1][1]
    for (d0, i0), (d1, i1) in zip(pairs, pairs[1:]):
        if d0 <= diameter_in <= d1:
            if d1 == d0:
                return i0
            t = (diameter_in - d0) / (d1 - d0)
            return i0 + t * (i1 - i0)
    return pairs[-1][1]


def passes_for_stock(stock_in: float, doc_in: float) -> int:
    """Whole number of equal-or-shallower passes to remove stock_in at doc_in."""
    if stock_in <= 0:
        return 0
    if doc_in <= 0:
        raise ValueError("doc_in must be > 0")
    return max(1, int(math.ceil(stock_in / doc_in - 1e-12)))
