from __future__ import annotations

from dataclasses import asdict, dataclass

from .config import FitupRates, ShopRates
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
    joint_count: int
    fitup_no_fixture_minutes: float
    fitup_with_fixture_minutes: float
    efficiency_pct: float
    total_no_fixture_minutes: float
    total_with_fixture_minutes: float
    quoted_no_fixture_minutes: float
    quoted_with_fixture_minutes: float

    def to_dict(self) -> dict:
        return {
            "by_size": [asdict(s) for s in self.by_size],
            "total_inches": self.total_inches,
            "weld_minutes": self.weld_minutes,
            "joint_count": self.joint_count,
            "fitup_no_fixture_minutes": self.fitup_no_fixture_minutes,
            "fitup_with_fixture_minutes": self.fitup_with_fixture_minutes,
            "efficiency_pct": self.efficiency_pct,
            "total_no_fixture_minutes": self.total_no_fixture_minutes,
            "total_with_fixture_minutes": self.total_with_fixture_minutes,
            "quoted_no_fixture_minutes": self.quoted_no_fixture_minutes,
            "quoted_with_fixture_minutes": self.quoted_with_fixture_minutes,
            "quoted_no_fixture_hours": round(self.quoted_no_fixture_minutes / 60.0, 2),
            "quoted_with_fixture_hours": round(self.quoted_with_fixture_minutes / 60.0, 2),
        }


def _fitup_minutes(weld_minutes: float, joint_count: int, rates: FitupRates) -> float:
    return (
        rates.base_minutes
        + (weld_minutes * rates.pct_of_weld)
        + (joint_count * rates.per_joint_minutes)
    )


def compute_weld_times(
    items: list[WeldLineItem],
    rates: ShopRates,
    efficiency_pct: float | None = None,
    ipm_overrides: dict[str, float] | None = None,
) -> TimeBreakdown:
    eff = float(efficiency_pct if efficiency_pct is not None else rates.default_efficiency_pct)
    if eff <= 0:
        eff = 100.0
    overrides = ipm_overrides or {}

    # Aggregate inches by size
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

    joint_count = len([i for i in items if i.inches > 0])
    fit_no = _fitup_minutes(weld_minutes, joint_count, rates.fitup_no_fixture)
    fit_yes = _fitup_minutes(weld_minutes, joint_count, rates.fitup_with_fixture)
    total_no = weld_minutes + fit_no
    total_yes = weld_minutes + fit_yes
    factor = 100.0 / eff

    return TimeBreakdown(
        by_size=by_size,
        total_inches=total_inches,
        weld_minutes=weld_minutes,
        joint_count=joint_count,
        fitup_no_fixture_minutes=fit_no,
        fitup_with_fixture_minutes=fit_yes,
        efficiency_pct=eff,
        total_no_fixture_minutes=total_no,
        total_with_fixture_minutes=total_yes,
        quoted_no_fixture_minutes=total_no * factor,
        quoted_with_fixture_minutes=total_yes * factor,
    )
