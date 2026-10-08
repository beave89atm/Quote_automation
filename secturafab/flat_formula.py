"""Kannon sheet-metal flat pattern.

T is thickness in inches. R is the inside bend radius after forming, in
inches. θ is the bend angle in degrees: the change in direction from flat.
K is the neutral-axis factor from shop config (0.33 unless that setting
changes).

    BA   = (π × θ / 180) × (R + K × T)
    OSSB = (R + T) × tan(θ / 2)
    BD   = 2 × OSSB − BA

At 90°, tan(θ / 2) is 1, so OSSB = R + T and
BD = 2(R + T) − (π / 2) × (R + K × T).

Tangent lengths:  FL = Σ(segments) + Σ(BA)
Outside corners:  FL = Σ(segments) − Σ(BD)

Each bend is calculated on its own, then the allowances or deductions are
added. An up bend and a down bend both count. They are not cancelled.
The length returned here is full precision. The line note is what gets
rounded for display.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def configured_k_factor() -> float:
    """K from ``config/shop_rates.yaml`` (``materials.flat_pattern_k_factor``)."""
    from quote_core.config import load_shop_rates

    return float(load_shop_rates().flat_pattern_k_factor)


@dataclass(frozen=True)
class Bend:
    """One bend. ``angle_deg`` is θ, the change from flat, not an included angle."""

    radius_in: float
    angle_deg: float
    thickness_in: float
    k_factor: float


@dataclass(frozen=True)
class BendMath:
    """BA, outside setback, and BD for one bend."""

    radius_in: float
    angle_deg: float
    thickness_in: float
    k_factor: float
    bend_allowance_in: float
    outside_setback_in: float
    bend_deduction_in: float


def bend_math(
    radius_in: float,
    angle_deg: float,
    thickness_in: float,
    k_factor: float,
) -> BendMath:
    """One bend. θ is degrees from flat."""
    bend_allowance = (math.pi * angle_deg / 180.0) * (
        radius_in + k_factor * thickness_in
    )
    if abs(angle_deg - 90.0) <= 1e-9:
        # tan(45°) is 1. Keep that exact so a 90° setback is R + T.
        outside_setback = radius_in + thickness_in
    else:
        outside_setback = (radius_in + thickness_in) * math.tan(
            math.radians(angle_deg / 2.0)
        )
    bend_deduction = 2.0 * outside_setback - bend_allowance
    return BendMath(
        radius_in=radius_in,
        angle_deg=angle_deg,
        thickness_in=thickness_in,
        k_factor=k_factor,
        bend_allowance_in=bend_allowance,
        outside_setback_in=outside_setback,
        bend_deduction_in=bend_deduction,
    )


def flat_length_in(
    segments_in: tuple[float, ...],
    bends: tuple[Bend, ...],
    *,
    basis: str,
) -> float:
    """Flat length in inches.

    ``basis`` is ``tangent`` (add each BA) or ``outside`` (subtract each BD).
    ``segments_in`` are already on that basis. Inside or mixed chains are
    not accepted here.
    """
    if basis not in {"tangent", "outside"}:
        raise ValueError(f"basis must be tangent or outside, not {basis!r}")
    worked = tuple(
        bend_math(bend.radius_in, bend.angle_deg, bend.thickness_in, bend.k_factor)
        for bend in bends
    )
    segment_sum = sum(segments_in)
    if basis == "tangent":
        return segment_sum + sum(item.bend_allowance_in for item in worked)
    return segment_sum - sum(item.bend_deduction_in for item in worked)
