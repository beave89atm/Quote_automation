"""Quote domain services — weld/fit-up plus a parallel mill/lathe calculator."""

from .config import ShopRates, load_shop_rates
from .time_engine import TimeBreakdown, compute_weld_times
from .weld.takeoff import WeldLineItem, WeldTakeoffResult, run_weld_takeoff

__all__ = [
    "ShopRates",
    "load_shop_rates",
    "TimeBreakdown",
    "compute_weld_times",
    "WeldLineItem",
    "WeldTakeoffResult",
    "run_weld_takeoff",
]
