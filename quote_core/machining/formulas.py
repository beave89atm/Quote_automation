"""Published imperial machining formulas (no shop-specific rates).

Sources (public pages, not paywalled catalogs):
- Kennametal Speeds and Feeds Calculator
  https://www.kennametal.com/us/en/resources/engineering-calculators/miscellaneous/speed-and-feed.html
  RPM = (SFM × 3.82) / D
  Mill feed = RPM × chip load × teeth
  Turning SFM = 0.262 × part diameter × RPM
- CNC Optimization — CNC cutting speed & feed formulas
  https://www.cncoptimization.com/resources/guides/cnc-cutting-speed-feed-formulas/
  RPM = (SFM × 3.82) / diameter
  Feed rate = RPM × flutes × chip load
  MRR (mill) = ap × ae × vf  →  WOC × DOC × IPM
- Harvey Tool General Machining Guidelines (same RPM / mill IPM)
  https://www.harveytool.com/resources/general-machining-guidelines
"""

from __future__ import annotations

import math
from typing import Iterable

# Kennametal / CNC Optimization / Harvey publish 3.82 (shop rounding of 12/π).
RPM_SFM_FACTOR = 3.82
# Kennametal turning check: SFM = 0.262 × part diameter × RPM  (≈ 1/3.82).
SFM_FROM_RPM_FACTOR = 0.262


def rpm_from_sfm(sfm: float, diameter_in: float) -> float:
    """Spindle speed. RPM = (SFM × 3.82) / D.

    D is tool diameter (mill) or workpiece diameter (turn).
    """
    if diameter_in <= 0:
        raise ValueError("diameter_in must be > 0")
    if sfm <= 0:
        raise ValueError("sfm must be > 0")
    return (sfm * RPM_SFM_FACTOR) / diameter_in


def sfm_from_rpm(diameter_in: float, rpm: float) -> float:
    """Turning SFM check. Kennametal: SFM = 0.262 × part diameter × RPM."""
    if diameter_in <= 0:
        raise ValueError("diameter_in must be > 0")
    if rpm <= 0:
        raise ValueError("rpm must be > 0")
    return SFM_FROM_RPM_FACTOR * diameter_in * rpm


def clamp_rpm(rpm: float, max_rpm: float | None) -> tuple[float, bool]:
    """Cap RPM at machine max. Returns (rpm, was_clamped)."""
    if max_rpm is None or max_rpm <= 0:
        return rpm, False
    if rpm > max_rpm:
        return float(max_rpm), True
    return rpm, False


def milling_ipm(rpm: float, ipt: float, flutes: int) -> float:
    """Mill table feed. IPM = RPM × flutes × chip load."""
    if flutes <= 0:
        raise ValueError("flutes must be > 0")
    if ipt <= 0:
        raise ValueError("ipt must be > 0")
    if rpm <= 0:
        raise ValueError("rpm must be > 0")
    return rpm * flutes * ipt


def turning_ipm(rpm: float, ipr: float) -> float:
    """Turn feed. IPM = RPM × IPR (no flute multiply)."""
    if rpm <= 0 or ipr <= 0:
        raise ValueError("rpm and ipr must be > 0")
    return rpm * ipr


def milling_mrr(doc_in: float, woc_in: float, ipm: float) -> float:
    """Mill metal removal rate in³/min. MRR = WOC × DOC × IPM."""
    if doc_in <= 0 or woc_in <= 0 or ipm <= 0:
        raise ValueError("doc_in, woc_in, and ipm must be > 0")
    return woc_in * doc_in * ipm


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
    """One turning pass. T = L / IPM with IPM = RPM × IPR."""
    return time_from_path(length_in, turning_ipm(rpm, ipr))


def turning_time_from_sfm(length_in: float, diameter_in: float, sfm: float, ipr: float) -> float:
    """One turning pass from SFM via published RPM = (SFM × 3.82) / D."""
    rpm = rpm_from_sfm(sfm, diameter_in)
    return turning_time_min(length_in, rpm, ipr)


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
