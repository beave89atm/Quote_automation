from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RATES_PATH = ROOT / "config" / "shop_rates.yaml"


@dataclass
class FitupRates:
    base_minutes: float = 10.0
    pct_of_weld: float = 0.25
    per_joint_minutes: float = 1.0


@dataclass
class ShopRates:
    shared_password: str = ""
    default_efficiency_pct: float = 85.0
    weld_ipm: dict[str, float] = field(default_factory=dict)
    default_ipm: float = 5.0
    fitup_no_fixture: FitupRates = field(default_factory=FitupRates)
    fitup_with_fixture: FitupRates = field(default_factory=FitupRates)
    always_ask: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    def ipm_for(self, size: str) -> float:
        key = size.strip()
        if key in self.weld_ipm:
            return float(self.weld_ipm[key])
        # normalize odd quotes
        alt = key.replace('"', "").replace("″", "")
        if alt in self.weld_ipm:
            return float(self.weld_ipm[alt])
        return float(self.default_ipm)


def _fitup_from(data: dict[str, Any] | None) -> FitupRates:
    data = data or {}
    return FitupRates(
        base_minutes=float(data.get("base_minutes", 10.0)),
        pct_of_weld=float(data.get("pct_of_weld", 0.25)),
        per_joint_minutes=float(data.get("per_joint_minutes", 1.0)),
    )


def load_shop_rates(path: Path | str | None = None) -> ShopRates:
    rates_path = Path(path) if path else DEFAULT_RATES_PATH
    with rates_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    app = raw.get("app") or {}
    weld = raw.get("weld") or {}
    fitup = raw.get("fitup") or {}
    ipm = {str(k): float(v) for k, v in (weld.get("ipm") or {}).items()}

    return ShopRates(
        shared_password=str(app.get("shared_password") or ""),
        default_efficiency_pct=float(app.get("default_efficiency_pct", 85)),
        weld_ipm=ipm,
        default_ipm=float(weld.get("default_ipm", 5.0)),
        fitup_no_fixture=_fitup_from(fitup.get("no_fixture")),
        fitup_with_fixture=_fitup_from(fitup.get("with_fixture")),
        always_ask=list(raw.get("always_ask") or []),
        raw=raw,
    )
