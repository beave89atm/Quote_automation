"""Weldment pushes fill weld and fit-up from the existing calculator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from quote_core.config import load_shop_rates
from secturafab.push import SecturaFabPushService, _push_needs_weld_calculator
from secturafab.quote_qc import WELD_CALCULATOR_NO_LENGTH
from secturafab.weld_ops import ensure_weld_ops, fill_weld_times_for_push


def _takeoff_inches(size: str, inches: float, weights: list[float]) -> dict:
    return {
        "items": [
            {
                "size": size,
                "inches": inches,
                "joint_notes": "fillet symbols",
                "confidence": "high",
                "source": "symbols",
            }
        ],
        "flags": [],
        "fitup_drivers": {
            "part_count": len(weights),
            "joint_count": max(0, len(weights) - 1),
            "assembly_weight_lb": sum(weights),
            "component_weights_lb": weights,
        },
    }


def test_fill_converts_takeoff_inches_with_shop_rates_only():
    rates = load_shop_rates()
    size = "1/4"
    inches = 70.0
    weights = [10.0, 40.0]
    times, _takeoff, notes = fill_weld_times_for_push(
        None, _takeoff_inches(size, inches, weights)
    )
    assert notes == []
    assert times["total_inches"] == inches
    assert times["weld_minutes"] == inches / rates.ipm_for(size)
    fit = rates.fitup.band_for_weight(weights[0]).with_fixture.per_piece_minutes
    fit += rates.fitup.band_for_weight(weights[1]).with_fixture.per_piece_minutes
    assert times["fitup_with_fixture_minutes"] == fit


def test_unknown_fillet_uses_default_ipm_only():
    rates = load_shop_rates()
    size = "9/16"
    assert size not in rates.weld_ipm
    inches = 30.0
    times, _takeoff, notes = fill_weld_times_for_push(
        None,
        _takeoff_inches(size, inches, [10.0]),
    )
    assert notes == []
    assert times["weld_minutes"] == inches / rates.default_ipm


def test_existing_weld_minutes_are_kept():
    existing = {
        "weld_minutes": 12.5,
        "total_inches": 40.0,
        "fitup_with_fixture_minutes": 4.0,
    }
    times, _takeoff, notes = fill_weld_times_for_push(
        existing,
        _takeoff_inches("1/4", 999.0, [10.0]),
    )
    assert notes == []
    assert times["weld_minutes"] == 12.5
    assert times["total_inches"] == 40.0


def test_no_symbols_does_not_invent_length_or_post_weld():
    takeoff = {
        "items": [],
        "flags": [
            "No weld symbols — weld and fit-up left at 0 (add fillet sizes manually if needed)"
        ],
        "fitup_drivers": {
            "part_count": 0,
            "notes": ["No weld symbols — weld and fit-up left at 0"],
        },
    }
    times, filled, notes = fill_weld_times_for_push(None, takeoff)
    assert float(times["weld_minutes"]) == 0.0
    assert float(times["total_inches"]) == 0.0
    assert notes == [WELD_CALCULATOR_NO_LENGTH]
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    posted = ensure_weld_ops(client, "qid", times=times, takeoff=filled)
    client.add_operation.assert_not_called()
    client.get_json.assert_not_called()
    assert any("No weld minutes" in note for note in posted)


def test_symbols_without_inches_do_not_invent_a_length():
    takeoff = {
        "items": [
            {
                "size": "1/4",
                "inches": 0,
                "source": "pdf_size_only",
                "joint_notes": "Size found on drawing; enter inches after review",
            }
        ],
        "flags": ["Could not estimate weld lengths from STP or PDF dimensions"],
        "fitup_drivers": {"part_count": 0},
    }
    times, filled, notes = fill_weld_times_for_push(None, takeoff)
    assert float(times["weld_minutes"]) == 0.0
    assert float(times["total_inches"]) == 0.0
    assert WELD_CALCULATOR_NO_LENGTH not in notes
    client = MagicMock()
    posted = ensure_weld_ops(client, "qid", times=times, takeoff=filled)
    client.add_operation.assert_not_called()
    assert any(note.startswith("needs_info:") for note in posted)


def test_filled_times_post_as_weld_and_fitup_hours():
    rates = load_shop_rates()
    inches = 70.0
    times, takeoff, notes = fill_weld_times_for_push(
        None, _takeoff_inches("1/4", inches, [10.0, 40.0])
    )
    assert notes == []
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.add_operation.return_value = {"ok": True, "via": "page_fn"}
    client.get_json.return_value = {
        "ItemList": [
            {
                "ID": "asm-1",
                "Description": "A-11949-000",
                "ProductType": 300,
                "IsAssembly": True,
                "Quantity": 1,
                "OperationCostList": [],
            },
            {
                "ID": "cad-1",
                "Description": "PLATE",
                "ProductType": 100,
                "Quantity": 1,
                "OperationCostList": [],
            },
        ]
    }
    posted = ensure_weld_ops(
        client, "qid", times=times, takeoff=takeoff, part_key="A-11949-000"
    )
    client.add_operation.assert_called_once()
    kwargs = client.add_operation.call_args.kwargs
    assert kwargs["weld_inches"] == inches
    assert kwargs["weld_hours"] == times["weld_minutes"] / 60.0
    assert kwargs["fitup_hours"] == times["fitup_with_fixture_minutes"] / 60.0
    assert kwargs["weld_hours"] == (inches / rates.ipm_for("1/4")) / 60.0
    assert any("min weld" in note and "min fit-up" in note for note in posted)


def test_step_only_weldment_does_not_invent_a_length():
    times, _takeoff, notes = fill_weld_times_for_push(
        None,
        {"library": {}},
        stp_path=Path("missing.stp"),
    )
    assert "weld_minutes" not in times or float(times.get("weld_minutes") or 0) == 0
    assert notes == [WELD_CALCULATOR_NO_LENGTH]


def test_weldment_gate_skips_linear_only():
    assert _push_needs_weld_calculator(
        title="A-11949-000",
        part_key="A-11949-000",
        pdf_filename="A-11949-000.pdf",
        cad=[Path("A-11949-000.stp")],
        bom_rows=[],
        loose_linear=False,
        confident_linears=[],
    )
    assert not _push_needs_weld_calculator(
        title="TUBE-1",
        part_key="TUBE-1",
        pdf_filename=None,
        cad=[Path("TUBE-1.stp")],
        bom_rows=[],
        loose_linear=False,
        confident_linears=[],
    )
    assert not _push_needs_weld_calculator(
        title="1020243-1",
        part_key="1020243-1",
        pdf_filename=None,
        cad=[],
        bom_rows=[{"part_no": "1020243-1", "description": "1 X 1 TUBE", "qty": 1}],
        loose_linear=True,
        confident_linears=[{"part_no": "1020243-1"}],
    )


def test_push_job_posts_calculator_times_when_caller_passes_none(tmp_path: Path):
    from tests.test_secturafab_website import _gold_cad, _gold_lin

    pdf = tmp_path / "21678-1.pdf"
    stp = tmp_path / "21678-1.STEP"
    pdf.write_bytes(b"%PDF")
    stp.write_bytes(b"ISO")
    rates = load_shop_rates()
    inches = 70.0
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=test"
    org = {
        "OrganizationName": "Safe Cave",
        "PrimaryOrganizationID": "11111111-1111-4111-8111-111111111111",
    }
    populated = {
        "QuoteNumber": "21678-1",
        "Description": "KNUCKLE",
        "ItemCount": 12,
        "ItemList": [_gold_cad("21680-1 PLATE"), _gold_lin("21679-1 TUBE")],
        **org,
    }
    client.get_json.return_value = populated
    service = SecturaFabPushService(client=client)
    with patch.object(service, "finish_cad_files", return_value=["Finish CAD"]), patch.object(
        service, "nest_after_finish", return_value=["Nest"]
    ), patch.object(
        service, "upload_drawings_quote_request", return_value="qr"
    ), patch.object(
        service, "create_quote", return_value="qid"
    ), patch.object(
        service, "allocate_quote_number", return_value="remint-ok"
    ), patch.object(
        service, "quick_add_cad"
    ), patch(
        "secturafab.push.ensure_weld_ops", return_value=["Attached Weld"]
    ) as weld, patch(
        "secturafab.push.ensure_imperial_item_units", return_value=[]
    ), patch(
        "secturafab.push.apply_bom_quantities", return_value=[]
    ), patch(
        "secturafab.push.refresh_bom_rows_for_push", return_value=([], [])
    ), patch(
        "secturafab.push.extract_assembly_description", return_value="KNUCKLE"
    ), patch(
        "secturafab.push.apply_quote_organization",
        return_value=["Set Organization: Safe Cave"],
    ), patch.object(
        service, "_peek_item_count", return_value=0
    ):
        result = service.push_job(
            title="21678-1",
            pdf_filename="21678-1.pdf",
            pdf_path=pdf,
            stp_path=stp,
            takeoff=_takeoff_inches("1/4", inches, [10.0, 40.0]),
            times=None,
            job_id=1,
            organization="Safe Cave",
        )
    if not result.ok:
        raise AssertionError("\n".join(result.notes or []) + "\n" + str(result.error))
    assert result.ok is True
    weld.assert_called()
    posted = weld.call_args.kwargs["times"]
    assert posted["weld_minutes"] == inches / rates.ipm_for("1/4")
    assert posted["fitup_with_fixture_minutes"] == (
        rates.fitup.band_for_weight(10).with_fixture.per_piece_minutes
        + rates.fitup.band_for_weight(40).with_fixture.per_piece_minutes
    )
    assert WELD_CALCULATOR_NO_LENGTH not in (result.notes or [])
