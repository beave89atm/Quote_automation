from quote_core.config import load_shop_rates
from quote_core.time_engine import compute_weld_times
from quote_core.weld.takeoff import WeldLineItem


def test_load_shop_rates():
    rates = load_shop_rates()
    assert rates.ipm_for("1/4") == 3.5
    assert rates.labor_rate_per_hour == 95.0
    assert rates.labor_placeholder is True
    band = rates.fitup.band_for_weight(75)
    assert band.id == "50_200"
    assert band.with_fixture.per_piece_minutes == 7.0
    assert band.with_fixture.per_part_minutes == 7.0  # alias


def test_fitup_is_sum_of_per_piece_minutes_only():
    rates = load_shop_rates()
    items = [WeldLineItem("1/4", 60.0, "test", "high", "manual")]
    weights = [8.1, 9.4, 12.4, 12.7, 12.9, 37.9, 47.9, 120.4]
    times = compute_weld_times(
        items,
        rates,
        efficiency_pct=100,
        component_weights_lb=weights,
    )
    # <20: 5×2=10; 20-50: 2×4=8; 50-200: 1×7=7 → 25 with fixture
    assert times.fitup_with_fixture_minutes == 25
    # no fixture: 5×4 + 2×6 + 10 = 42
    assert times.fitup_no_fixture_minutes == 42
    assert times.band_counts == {"<20 lbs": 5, "20-50 lbs": 2, "50-200 lbs": 1}
    by_id = {r["id"]: r for r in times.band_breakdown}
    assert by_id["lt_20"]["piece_count"] == 5
    assert by_id["lt_20"]["minutes_per_piece_with_fixture"] == 2.0
    assert by_id["lt_20"]["total_minutes_with_fixture"] == 10
    assert by_id["20_50"]["total_minutes_with_fixture"] == 8
    assert by_id["50_200"]["total_minutes_with_fixture"] == 7
    assert by_id["gt_200"]["piece_count"] == 0


def test_fitup_uses_each_piece_when_qty_expanded():
    """BOM qty 2 → two piece weights, not one part-number weight."""
    rates = load_shop_rates()
    items = [WeldLineItem("1/4", 60.0, "test", "high", "manual")]
    # 80341805 after qty expansion: 13 pieces
    weights = [
        12.4,
        37.9,
        37.9,
        12.9,
        12.9,
        8.1,
        120.4,
        47.9,
        47.9,
        12.7,
        12.7,
        9.4,
        9.4,
    ]
    times = compute_weld_times(
        items,
        rates,
        efficiency_pct=100,
        component_weights_lb=weights,
    )
    # <20: 8×2=16; 20-50: 4×4=16; 50-200: 1×7=7 → 39
    assert times.part_count == 13
    assert times.fitup_with_fixture_minutes == 39
    assert times.fitup_no_fixture_minutes == 66


def test_quoted_labor_uses_shop_rate():
    rates = load_shop_rates()
    items = [WeldLineItem("1/4", 210.0, "test", "high", "manual")]
    times = compute_weld_times(
        items,
        rates,
        efficiency_pct=100,
        component_weights_lb=[25.0],
    )
    payload = times.to_dict()
    # 210 in / 3.5 ipm = 60 weld min + 4 fit-up with fixture = 64 min = 1.07 hr
    assert payload["quoted_with_fixture_hours"] == 1.07
    assert payload["labor_rate_per_hour"] == 95.0
    assert payload["quoted_with_fixture_labor"] == 101.65
    assert payload["labor_placeholder"] is True
