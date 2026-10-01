from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RATES_PATH = ROOT / "config" / "shop_rates.yaml"


@dataclass
class FitupBandRates:
    per_piece_minutes: float
    per_joint_minutes: float = 0.0

    @property
    def per_part_minutes(self) -> float:
        """Alias kept for older call sites / configs."""
        return self.per_piece_minutes


@dataclass
class FitupWeightBand:
    id: str
    label: str
    max_lb: float | None  # exclusive upper bound; None = open-ended
    with_fixture: FitupBandRates
    no_fixture: FitupBandRates


@dataclass
class FitupConfig:
    bands: list[FitupWeightBand] = field(default_factory=list)
    default_band_id: str = "20_50"

    def band_for_weight(self, weight_lb: float | None) -> FitupWeightBand:
        if not self.bands:
            raise ValueError("No fitup weight bands configured")
        if weight_lb is None:
            for b in self.bands:
                if b.id == self.default_band_id:
                    return b
            return self.bands[0]
        # Bands ordered low→high. Finite max_lb is exclusive except the last
        # finite band before an open-ended (>max) band, which is inclusive
        # so "50-200" includes 200 and ">200" starts above 200.
        for i, b in enumerate(self.bands):
            if b.max_lb is None:
                return b
            next_is_open = (
                i + 1 < len(self.bands) and self.bands[i + 1].max_lb is None
            )
            if next_is_open:
                if weight_lb <= b.max_lb:
                    return b
            elif weight_lb < b.max_lb:
                return b
        return self.bands[-1]


@dataclass
class ShopRates:
    shared_password: str = ""
    default_efficiency_pct: float = 85.0
    weld_process: str = "manual"  # manual | robot (robot rates TBD)
    weld_ipm: dict[str, float] = field(default_factory=dict)
    default_ipm: float = 5.0
    fitup: FitupConfig = field(default_factory=FitupConfig)
    labor_rate_per_hour: float = 95.0
    labor_placeholder: bool = True
    labor_notes: str = ""
    always_ask: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    def ipm_for(self, size: str) -> float:
        key = size.strip()
        if key in self.weld_ipm:
            return float(self.weld_ipm[key])
        alt = key.replace('"', "").replace("″", "")
        if alt in self.weld_ipm:
            return float(self.weld_ipm[alt])
        return float(self.default_ipm)


def _band_rates(data: dict[str, Any] | None) -> FitupBandRates:
    data = data or {}
    minutes = data.get("per_piece_minutes", data.get("per_part_minutes", 5.0))
    return FitupBandRates(
        per_piece_minutes=float(minutes),
        per_joint_minutes=float(data.get("per_joint_minutes", 0.0)),
    )


def _fitup_from(raw_fitup: dict[str, Any] | None) -> FitupConfig:
    raw_fitup = raw_fitup or {}
    bands: list[FitupWeightBand] = []
    for row in raw_fitup.get("weight_bands") or []:
        bands.append(
            FitupWeightBand(
                id=str(row.get("id") or ""),
                label=str(row.get("label") or row.get("id") or ""),
                max_lb=None if row.get("max_lb") in (None, "", "null") else float(row["max_lb"]),
                with_fixture=_band_rates(row.get("with_fixture")),
                no_fixture=_band_rates(row.get("no_fixture")),
            )
        )
    return FitupConfig(
        bands=bands,
        default_band_id=str(raw_fitup.get("default_band_id") or "20_50"),
    )


def load_shop_rates(path: Path | str | None = None) -> ShopRates:
    rates_path = Path(path) if path else DEFAULT_RATES_PATH
    with rates_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    app = raw.get("app") or {}
    weld = raw.get("weld") or {}
    labor = raw.get("labor") or {}
    ipm = {str(k): float(v) for k, v in (weld.get("ipm") or {}).items()}

    return ShopRates(
        shared_password=str(app.get("shared_password") or ""),
        default_efficiency_pct=float(app.get("default_efficiency_pct", 85)),
        weld_process=str(weld.get("process") or "manual"),
        weld_ipm=ipm,
        default_ipm=float(weld.get("default_ipm", 5.0)),
        fitup=_fitup_from(raw.get("fitup")),
        labor_rate_per_hour=float(labor.get("shop_rate_per_hour", 95.0)),
        labor_placeholder=bool(labor.get("placeholder", True)),
        labor_notes=str(labor.get("notes") or ""),
        always_ask=list(raw.get("always_ask") or []),
        raw=raw,
    )
