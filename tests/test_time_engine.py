from quote_core.config import load_shop_rates
from quote_core.time_engine import compute_weld_times
from quote_core.weld.takeoff import WeldLineItem


def test_load_shop_rates():
    rates = load_shop_rates()
    assert rates.ipm_for("1/4") == 6.0
    assert rates.default_efficiency_pct == 85.0


def test_compute_weld_times():
    rates = load_shop_rates()
    items = [
        WeldLineItem("1/4", 60.0, "test", "high", "manual"),
        WeldLineItem("5/16", 30.0, "test", "high", "manual"),
    ]
    times = compute_weld_times(items, rates, efficiency_pct=100)
    assert round(times.weld_minutes, 2) == round(60 / 6 + 30 / 5, 2)
    assert times.quoted_no_fixture_minutes > times.weld_minutes
    assert times.fitup_with_fixture_minutes < times.fitup_no_fixture_minutes
