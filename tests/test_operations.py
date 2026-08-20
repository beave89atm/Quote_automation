from pathlib import Path

from quote_core.capabilities import load_shop_capabilities
from quote_core.dxf_text import extract_dxf_text
from quote_core.operations import propose_operations


def test_load_shop_capabilities():
    caps = load_shop_capabilities()
    assert caps["outsourced"]["tube_laser"]["times"] == "placeholder"
    assert caps["outsourced"]["powder_coating"]["times"] == "placeholder"
    assert caps["in_house"]["laser"]["machines"]
    assert caps["placeholders"]["bend_setup_minutes"] == 30


def test_propose_always_lists_outsourced():
    proposal = propose_operations(title="plate only", has_pdf=True)
    codes = [o.code for o in proposal.operations]
    assert "tube_laser" in codes
    assert "powder" in codes
    tube = next(o for o in proposal.operations if o.code == "tube_laser")
    powder = next(o for o in proposal.operations if o.code == "powder")
    assert tube.location == "outsourced"
    assert powder.location == "outsourced"
    assert tube.needs_review
    assert powder.needs_review
    assert tube.time_status == "confirm"
    assert powder.time_status == "confirm"


def test_propose_weld_times_from_engine():
    proposal = propose_operations(
        title="weldment",
        has_pdf=True,
        weld_items=[{"size": "1/4", "inches": 60, "joint_notes": "fillet"}],
        times={"total_inches": 60, "weld_minutes": 17.14, "fitup_with_fixture_minutes": 4},
    )
    weld = next(o for o in proposal.operations if o.code == "weld")
    fit = next(o for o in proposal.operations if o.code == "fitup")
    assert weld.detected
    assert weld.time_status == "computed"
    assert weld.run_minutes == 17.14
    assert weld.setup_minutes == 15
    assert fit.detected
    assert fit.run_minutes == 4


def test_propose_dxf_is_laser_candidate():
    proposal = propose_operations(title="nest", has_dxf=True, filenames=["part.dxf"])
    laser = next(o for o in proposal.operations if o.code == "laser")
    assert laser.detected
    assert laser.setup_minutes == 15
    assert laser.run_minutes is None
    assert "DXF" in " ".join(laser.evidence)


def test_propose_powder_and_tube_laser_from_notes():
    proposal = propose_operations(
        title="21679 TUBE",
        pdf_notes=["TUBE LASER CUT SLOTS", "POWDER COAT BLACK"],
        has_pdf=True,
    )
    tube = next(o for o in proposal.operations if o.code == "tube_laser")
    powder = next(o for o in proposal.operations if o.code == "powder")
    assert tube.detected
    assert powder.detected
    assert tube.setup_minutes == 30
    assert powder.setup_minutes == 20


def test_propose_machining_not_in_this_workstream():
    proposal = propose_operations(
        title="housing",
        pdf_notes=["CNC MILL POCKET", "LATHE TURN OD"],
        has_pdf=True,
    )
    codes = [o.code for o in proposal.operations]
    assert "mill" not in codes
    assert "lathe" not in codes
    assert all(o.setup_minutes is None or o.code != "mill" for o in proposal.operations)
    assert any("parallel project" in f for f in proposal.flags)


def test_extract_dxf_text(tmp_path: Path):
    dxf = tmp_path / "note.dxf"
    dxf.write_text("0\nTEXT\n8\n0\n1\nPOWDER COAT\n0\nENDSEC\n", encoding="ascii")
    text = extract_dxf_text(dxf)
    assert "POWDER COAT" in text


def test_extract_dxf_missing():
    assert extract_dxf_text(None) == ""
    assert extract_dxf_text("/no/such.dxf") == ""
