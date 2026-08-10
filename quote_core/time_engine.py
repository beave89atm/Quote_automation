from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any

from .config import ShopRates
from .weld.takeoff import WeldLineItem


@dataclass
class SizeTime:
    size: str
    inches: float
    ipm: float
    weld_minutes: float


@dataclass
class TimeBreakdown:
    by_size: list[SizeTime]
    total_inches: float
    weld_minutes: float
    part_count: int
    joint_count: int
    assembly_weight_lb: float | None
    component_weights_lb: list[float]
    weight_band_id: str
    weight_band_label: str
    band_counts: dict[str, int]
    band_breakdown: list[dict[str, Any]]
    minutes_per_part: dict[str, float]
    fitup_no_fixture_minutes: float
    fitup_with_fixture_minutes: float
    efficiency_pct: float
    total_no_fixture_minutes: float
    total_with_fixture_minutes: float
    quoted_no_fixture_minutes: float
    quoted_with_fixture_minutes: float
    fitup_notes: list[str]

    def to_dict(self) -> dict:
        return {
            "by_size": [asdict(s) for s in self.by_size],
            "total_inches": self.total_inches,
            "weld_minutes": self.weld_minutes,
            "part_count": self.part_count,
            "joint_count": self.joint_count,
            "assembly_weight_lb": self.assembly_weight_lb,
            "component_weights_lb": self.component_weights_lb,
            "weight_band_id": self.weight_band_id,
            "weight_band_label": self.weight_band_label,
            "band_counts": self.band_counts,
            "band_breakdown": self.band_breakdown,
            "minutes_per_part": self.minutes_per_part,
            "fitup_no_fixture_minutes": self.fitup_no_fixture_minutes,
            "fitup_with_fixture_minutes": self.fitup_with_fixture_minutes,
            "efficiency_pct": self.efficiency_pct,
            "total_no_fixture_minutes": self.total_no_fixture_minutes,
            "total_with_fixture_minutes": self.total_with_fixture_minutes,
            "quoted_no_fixture_minutes": self.quoted_no_fixture_minutes,
            "quoted_with_fixture_minutes": self.quoted_with_fixture_minutes,
            "quoted_no_fixture_hours": round(self.quoted_no_fixture_minutes / 60.0, 2),
            "quoted_with_fixture_hours": round(self.quoted_with_fixture_minutes / 60.0, 2),
            "fitup_notes": self.fitup_notes,
        }


def _band_breakdown(
    band_counts: dict[str, int],
    rates: ShopRates,
) -> list[dict[str, Any]]:
    """Ordered rows for each configured weight band with piece counts and minutes."""
    rows: list[dict[str, Any]] = []
    for band in rates.fitup.bands:
        count = int(band_counts.get(band.label, 0))
        no_min = float(band.no_fixture.per_piece_minutes)
        with_min = float(band.with_fixture.per_piece_minutes)
        rows.append(
            {
                "id": band.id,
                "label": band.label,
                "max_lb": band.max_lb,
                "piece_count": count,
                "minutes_per_piece_no_fixture": no_min,
                "minutes_per_piece_with_fixture": with_min,
                "total_minutes_no_fixture": round(count * no_min, 2),
                "total_minutes_with_fixture": round(count * with_min, 2),
                # Backward-compatible aliases
                "part_count": count,
                "minutes_per_part_no_fixture": no_min,
                "minutes_per_part_with_fixture": with_min,
            }
        )
    return rows


def _fitup_from_component_weights(
    component_weights: list[float],
    rates: ShopRates,
    fixture: str,
) -> tuple[float, Counter]:
    """fitup = sum(per-piece minutes for each physical piece by its weight band)."""
    notes_counter: Counter = Counter()
    if not component_weights:
        band = rates.fitup.band_for_weight(None)
        attr = band.with_fixture if fixture == "with" else band.no_fixture
        notes_counter[band.label] += 1
        return float(attr.per_piece_minutes), notes_counter

    total = 0.0
    for w in component_weights:
        band = rates.fitup.band_for_weight(float(w))
        attr = band.with_fixture if fixture == "with" else band.no_fixture
        total += attr.per_piece_minutes
        notes_counter[band.label] += 1
    return total, notes_counter


def compute_weld_times(
    items: list[WeldLineItem],
    rates: ShopRates,
    efficiency_pct: float | None = None,
    ipm_overrides: dict[str, float] | None = None,
    part_count: int | None = None,
    joint_count: int | None = None,
    assembly_weight_lb: float | None = None,
    component_weights_lb: list[float] | None = None,
) -> TimeBreakdown:
    eff = float(efficiency_pct if efficiency_pct is not None else rates.default_efficiency_pct)
    if eff <= 0:
        eff = 100.0
    overrides = ipm_overrides or {}
    notes: list[str] = []

    inches_by_size: dict[str, float] = {}
    for item in items:
        if item.inches <= 0:
            continue
        inches_by_size[item.size] = inches_by_size.get(item.size, 0.0) + float(item.inches)

    by_size: list[SizeTime] = []
    weld_minutes = 0.0
    total_inches = 0.0
    for size, inches in sorted(inches_by_size.items(), key=lambda kv: kv[0]):
        ipm = float(overrides.get(size, rates.ipm_for(size)))
        if ipm <= 0:
            ipm = rates.default_ipm
        mins = inches / ipm
        by_size.append(SizeTime(size=size, inches=inches, ipm=ipm, weld_minutes=mins))
        weld_minutes += mins
        total_inches += inches

    components = [float(w) for w in (component_weights_lb or []) if float(w) > 0]
    # Explicit 0 means no fit-up (laser-only / no weld symbols). Do not default to 1.
    if part_count is not None:
        parts = max(0, int(part_count))
    else:
        parts = len(components) or (1 if by_size else 0)
    joints = int(joint_count) if joint_count is not None else 0

    if parts <= 0 and not by_size:
        notes.append("No weld takeoff — weld and fit-up left at 0")
        return TimeBreakdown(
            by_size=[],
            total_inches=0.0,
            weld_minutes=0.0,
            part_count=0,
            joint_count=0,
            assembly_weight_lb=(
                float(assembly_weight_lb) if assembly_weight_lb is not None else None
            ),
            component_weights_lb=[],
            weight_band_id="none",
            weight_band_label="none",
            band_counts={},
            band_breakdown=[],
            minutes_per_part={"no_fixture": 0.0, "with_fixture": 0.0},
            fitup_no_fixture_minutes=0.0,
            fitup_with_fixture_minutes=0.0,
            efficiency_pct=eff,
            total_no_fixture_minutes=0.0,
            total_with_fixture_minutes=0.0,
            quoted_no_fixture_minutes=0.0,
            quoted_with_fixture_minutes=0.0,
            fitup_notes=notes,
        )

    if components and part_count is not None and len(components) != parts:
        # Explicit piece count (e.g. OCR BOM) wins over a mismatched STEP weight list.
        notes.append(
            f"Piece count ({parts}) differs from weighed pieces ({len(components)}) — "
            "fit-up uses piece count with default band for unknown weights"
        )
        components = []

    if not components and parts > 0:
        default_band = rates.fitup.band_for_weight(None)
        synth = 35.0 if default_band.id == "20_50" else 10.0
        components = [synth] * parts
        notes.append(
            f"Piece weights unknown — using default {default_band.label} band for all {parts} pieces"
        )

    fit_no, _counts_no = _fitup_from_component_weights(components, rates, "no")
    fit_yes, counts_yes = _fitup_from_component_weights(components, rates, "with")
    band_counts = {k: int(v) for k, v in counts_yes.items()}
    label = ", ".join(f"{v}× {k}" for k, v in sorted(band_counts.items(), key=lambda kv: -kv[1]))
    if not label:
        label = "per-piece"

    weight = float(assembly_weight_lb) if assembly_weight_lb is not None else None

    total_no = weld_minutes + fit_no
    total_yes = weld_minutes + fit_yes
    factor = 100.0 / eff

    top_band_label = max(band_counts, key=band_counts.get) if band_counts else rates.fitup.default_band_id
    top_band = next((b for b in rates.fitup.bands if b.label == top_band_label), None)
    if top_band is None:
        top_band = rates.fitup.band_for_weight(None)

    notes.append("Fit-up = sum of per-piece minutes by each physical piece's weight band")
    breakdown = _band_breakdown(band_counts, rates)
    return TimeBreakdown(
        by_size=by_size,
        total_inches=total_inches,
        weld_minutes=weld_minutes,
        part_count=parts,
        joint_count=joints,
        assembly_weight_lb=weight,
        component_weights_lb=components,
        weight_band_id="per_piece",
        weight_band_label=label or top_band.label,
        band_counts=band_counts,
        band_breakdown=breakdown,
        minutes_per_part={
            "no_fixture": top_band.no_fixture.per_piece_minutes,
            "with_fixture": top_band.with_fixture.per_piece_minutes,
        },
        fitup_no_fixture_minutes=round(fit_no, 2),
        fitup_with_fixture_minutes=round(fit_yes, 2),
        efficiency_pct=eff,
        total_no_fixture_minutes=total_no,
        total_with_fixture_minutes=total_yes,
        quoted_no_fixture_minutes=total_no * factor,
        quoted_with_fixture_minutes=total_yes * factor,
        fitup_notes=notes,
    )
