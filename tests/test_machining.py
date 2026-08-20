"""Mill / lathe calculators — published formulas, envelopes, roster."""

from __future__ import annotations

import math

import pytest

from quote_core.machining import (
    LatheQuoteInput,
    MillQuoteInput,
    load_machine_roster,
    load_machining_config,
    quote_lathe,
    quote_mill,
)
from quote_core.machining.formulas import (
    RPM_SFM_FACTOR,
    interpolate_ipt,
    milling_ipm,
    milling_mrr,
    rpm_from_sfm,
    time_from_path,
    time_from_volume,
    turning_mrr,
    turning_time_from_sfm,
    turning_time_min,
)


def test_roster_july_27_counts():
    roster = load_machine_roster()
    assert len(roster.cnc_lathes()) == 10
    assert len(roster.cnc_mills()) == 12
    assert sum(1 for m in roster.mills() if m.class_name == "manual_mill") == 3
    assert sum(1 for m in roster.lathes() if m.class_name == "manual_lathe") == 1
    assert sum(1 for m in roster.cnc_lathes() if m.live_tooling) == 1
    assert roster.by_id("doosan_lathe_live_1").live_tooling
    assert roster.by_id("mori_seiki_hmc_1").taper == "Cat 50"
    env = roster.shop_envelopes["cnc_lathe"]
    assert env.max_diameter_in == 14.0
    assert env.max_length_in == 14.0
    assert env.max_chuck_diameter_in == 26.0
    mill_env = roster.shop_envelopes["cnc_mill"]
    assert mill_env.x_in == 40.0
    assert mill_env.y_in == 20.0
    assert mill_env.fourth_axis_diameter_in == 20.0


def test_harvey_rpm_formula():
    # Harvey / Kennametal publish RPM = (SFM × 3.82) / D
    # Implementation uses 12/π (the exact factor 3.82 approximates).
    rpm = rpm_from_sfm(200, 0.5)
    assert rpm == pytest.approx((200 * 12) / (math.pi * 0.5))
    harvey = (200 * 3.82) / 0.5
    assert rpm == pytest.approx(harvey, rel=0.001)
    assert RPM_SFM_FACTOR == pytest.approx(3.82, rel=0.001)


def test_milling_ipm_and_mrr_formulas():
    rpm = rpm_from_sfm(200, 0.5)
    ipm = milling_ipm(rpm, 0.003, 4)
    assert ipm == pytest.approx(rpm * 0.003 * 4)
    mrr = milling_mrr(0.125, 0.25, ipm)
    assert mrr == pytest.approx(0.125 * 0.25 * ipm)
    assert time_from_path(10, 20) == 0.5
    assert time_from_volume(10, 5) == 2.0


def test_turning_formulas_machiningdoctor():
    # T = L / (n × Fn); also T = (L × π × D) / (12 × Fn × Vc)
    n = rpm_from_sfm(400, 4.0)
    t = turning_time_min(6.0, n, 0.012)
    t2 = turning_time_from_sfm(6.0, 4.0, 400, 0.012)
    assert t == pytest.approx(t2, rel=1e-9)
    assert turning_mrr(400, 0.012, 0.100) == pytest.approx(12 * 400 * 0.012 * 0.100)


def test_ipt_interpolates_harvey_table():
    cfg = load_machining_config()
    steel = cfg.materials["carbon_steel"]
    assert interpolate_ipt(0.5, steel.ipt_by_diameter_in) == 0.003
    mid = interpolate_ipt(0.4375, steel.ipt_by_diameter_in)
    assert 0.002 < mid < 0.003


def test_mill_in_envelope_quote():
    result = quote_mill(
        MillQuoteInput(
            material="a36",
            qty=10,
            length_in=8,
            width_in=6,
            height_in=1.5,
            face_area_in2=48,
            hole_count=4,
            hole_diameter_in=0.375,
            hole_depth_in=1.5,
        )
    )
    assert result["ok_to_quote"] is True
    assert result["outside_envelope"] is False
    assert result["material"]["key"] == "carbon_steel"
    assert result["times"]["setup_placeholder"] is True
    assert result["placeholder"] is True
    assert result["times"]["run_minutes_total"] == pytest.approx(
        result["times"]["run_minutes_each"] * 10, abs=0.01
    )
    assert result["times"]["total_minutes"] == pytest.approx(
        result["times"]["setup_minutes"] + result["times"]["run_minutes_total"],
        abs=0.01,
    )
    assert result["coating"]["quoted"] is False
    assert any(op["op"] == "face" for op in result["ops"])
    assert any(op["op"] == "drill" for op in result["ops"])
    assert any(f["code"] == "RATES_PLACEHOLDER" for f in result["flags"])
    blocking = [f for f in result["flags"] if f["blocking"]]
    assert blocking == []


def test_mill_over_20x40_is_flagged_not_silent():
    result = quote_mill(
        MillQuoteInput(
            material="carbon_steel",
            qty=1,
            length_in=45,
            width_in=25,
            height_in=2,
            face_area_in2=100,
        )
    )
    assert result["outside_envelope"] is True
    assert result["ok_to_quote"] is False
    codes = {f["code"] for f in result["flags"] if f["blocking"]}
    assert "MILL_OVER_TABLE" in codes


def test_mill_4th_axis_over_20_flagged():
    result = quote_mill(
        MillQuoteInput(
            material="carbon_steel",
            qty=1,
            length_in=10,
            width_in=8,
            height_in=4,
            face_area_in2=80,
            needs_4th_axis=True,
            fourth_axis_diameter_in=22,
        )
    )
    assert result["ok_to_quote"] is False
    assert any(f["code"] == "MILL_4TH_AXIS_OVER_DIAMETER" for f in result["flags"])


def test_mill_fits_40x20_cube():
    # 30 × 18 × 2 fits 40 × 20
    result = quote_mill(
        MillQuoteInput(
            material="aluminum",
            qty=2,
            length_in=30,
            width_in=18,
            height_in=2,
            contour_length_in=96,
        )
    )
    assert result["ok_to_quote"] is True
    assert result["material"]["key"] == "aluminum"


def test_lathe_in_envelope_quote():
    result = quote_lathe(
        LatheQuoteInput(
            material="carbon_steel",
            qty=5,
            diameter_in=3.0,
            length_in=6.0,
            stock_diameter_in=3.5,
        )
    )
    assert result["ok_to_quote"] is True
    assert result["outside_envelope"] is False
    assert result["machine"]["suggested_class"] == "cnc_lathe"
    assert result["times"]["setup_minutes"] == 20
    assert any(op["op"] == "rough_turn" for op in result["ops"])
    assert any(op["op"] == "face" for op in result["ops"])
    # 0.25" radial / 0.100" DOC → 3 rough passes
    rough = next(op for op in result["ops"] if op["op"] == "rough_turn")
    assert rough["passes"] == 3


def test_lathe_over_14_diameter_flagged():
    result = quote_lathe(
        LatheQuoteInput(material="a36", qty=1, diameter_in=16.0, length_in=8.0)
    )
    assert result["ok_to_quote"] is False
    assert any(f["code"] == "LATHE_OVER_TYPICAL_DIAMETER" for f in result["flags"])


def test_lathe_over_14_length_flagged():
    result = quote_lathe(
        LatheQuoteInput(material="a36", qty=1, diameter_in=4.0, length_in=18.0)
    )
    assert result["ok_to_quote"] is False
    assert any(f["code"] == "LATHE_OVER_LENGTH" for f in result["flags"])


def test_lathe_over_chuck_26_flagged():
    result = quote_lathe(
        LatheQuoteInput(material="a36", qty=1, diameter_in=28.0, length_in=6.0)
    )
    assert result["ok_to_quote"] is False
    assert any(f["code"] == "LATHE_OVER_CHUCK" for f in result["flags"])


def test_lathe_live_tooling_selects_doosan():
    result = quote_lathe(
        LatheQuoteInput(
            material="stainless_304",
            qty=1,
            diameter_in=2.0,
            length_in=4.0,
            needs_live_tooling=True,
        )
    )
    assert result["machine"]["suggested"]["id"] == "doosan_lathe_live_1"
    assert result["times"]["setup_key"] == "cnc_lathe_live_tooling"
    assert result["material"]["key"] == "stainless"


def test_unknown_material_raises():
    with pytest.raises(KeyError, match="Unknown machining material"):
        quote_mill(
            MillQuoteInput(
                material="unobtainium",
                qty=1,
                length_in=2,
                width_in=2,
                height_in=1,
                face_area_in2=4,
            )
        )


def test_machining_config_sources_are_public():
    cfg = load_machining_config()
    assert cfg.placeholder is True
    urls = [s.get("url") for s in cfg.sources]
    assert any("harveytool.com" in (u or "") for u in urls)
    assert any("machiningdoctor.com" in (u or "") for u in urls)
    assert any("kennametal" in (u or "").lower() for u in urls)
    assert cfg.coating.get("status") == "stub"
    assert cfg.coating.get("enabled") is False
