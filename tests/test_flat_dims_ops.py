"""Offline tests for flat-pattern Length×Width correction on push."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from secturafab.flat_dims_ops import (
    _dims_need_correction,
    _rewrite_description_flat_dims,
    ensure_flat_pattern_dims,
)


def test_dims_need_correction_when_missing():
    assert _dims_need_correction(0, 0, 26.85, 8.49)
    assert _dims_need_correction(20, 30, 26.85, 8.49)


def test_dims_ok_within_tolerance():
    assert not _dims_need_correction(26.9, 8.5, 26.85, 8.49)


def test_rewrite_description_replaces_trailing_dims():
    desc = 'MD23-1709L - 1/8" 5052 20 in X 30 in'
    out = _rewrite_description_flat_dims(desc, 26.85, 8.49)
    assert "20 in" not in out
    assert "26.85 in X 8.49 in" in out
    assert '1/8"' in out


def test_ensure_flat_corrects_wrong_20x30(tmp_path: Path):
    import fitz

    pdf = tmp_path / "md23.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "FLAT PATTERN\nFOR REFERENCE ONLY\n(26.85)\n(8.49)\n",
        fontsize=11,
    )
    doc.save(pdf)
    doc.close()

    client = MagicMock()
    item = {
        "ID": "p1",
        "Description": 'MD23-1709L - 1/8" 5052 20 in X 30 in',
        "Length": 20.0,
        "Width": 30.0,
        "Length_Units": "inch",
        "IsPart": True,
        "Machine": "Laser",
        "ProductType": 100,
        "OperationCostList": [{"Name": "Bend", "Time": 0.1}],
    }
    detail = {"ItemList": [item]}
    client.get_json.return_value = detail
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save

    notes = ensure_flat_pattern_dims(client, "quote-md23", pdf)
    assert any("26.85" in n and "8.49" in n for n in notes)
    assert item["Length"] == 26.85
    assert item["Width"] == 8.49
    assert item["Length_Units"] == "inch"
    assert item["OperationCostList"] == [{"Name": "Bend", "Time": 0.1}]
    assert "26.85 in X 8.49 in" in item["Description"]
    client.request.assert_called_once()
    posted = client.request.call_args.kwargs.get("json") or client.request.call_args[1].get(
        "json"
    )
    assert posted["ItemList"][0]["OperationCostList"]


def test_ensure_flat_skips_when_already_correct(tmp_path: Path):
    import fitz

    pdf = tmp_path / "ok.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "FLAT PATTERN\n26.85 x 8.49\n", fontsize=11)
    doc.save(pdf)
    doc.close()

    client = MagicMock()
    item = {
        "Description": 'MD23-1709L - 1/8" 5052 26.85 in X 8.49 in',
        "Length": 26.85,
        "Width": 8.49,
        "Length_Units": "inch",
        "IsPart": True,
        "Machine": "Laser",
        "ProductType": 100,
    }
    client.get_json.return_value = {"ItemList": [item]}

    notes = ensure_flat_pattern_dims(client, "quote-ok", pdf)
    assert any("already match" in n for n in notes)
    client.request.assert_not_called()


def test_ensure_flat_match_part_filters(tmp_path: Path):
    import fitz

    pdf = tmp_path / "comp.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "FLAT PATTERN\n7.00 x 3.19\n", fontsize=11)
    doc.save(pdf)
    doc.close()

    client = MagicMock()
    target = {
        "Description": '15644 - 1/4" A36 1 in X 1 in',
        "Length": 1.0,
        "Width": 1.0,
        "Length_Units": "inch",
        "IsPart": True,
        "Machine": "Laser",
        "ProductType": 100,
    }
    other = {
        "Description": '99999 - 1/4" A36 10 in X 10 in',
        "Length": 10.0,
        "Width": 10.0,
        "Length_Units": "inch",
        "IsPart": True,
        "Machine": "Laser",
        "ProductType": 100,
    }
    client.get_json.return_value = {"ItemList": [target, other]}
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save

    notes = ensure_flat_pattern_dims(
        client, "quote-bom", pdf, match_part="15644"
    )
    assert any("7" in n for n in notes)
    assert target["Length"] == 7.0
    assert target["Width"] == 3.19
    assert other["Length"] == 10.0


def test_ensure_flat_no_pdf_dims_leaves_import(tmp_path: Path):
    import fitz

    pdf = tmp_path / "nodims.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "NO FLAT CALL OUT HERE\n", fontsize=11)
    doc.save(pdf)
    doc.close()

    client = MagicMock()
    notes = ensure_flat_pattern_dims(client, "quote-x", pdf)
    assert any("No flat-pattern" in n for n in notes)
    client.get_json.assert_not_called()


def test_push_and_pdf_builders_wire_flat_dims():
    """Push / PDF builders import and call ensure_flat_pattern_dims."""
    import secturafab.pdf_assembly_ops as pdf_mod
    import secturafab.push as push_mod

    assert hasattr(push_mod, "ensure_flat_pattern_dims")
    assert hasattr(pdf_mod, "ensure_flat_pattern_dims")
    push_src = Path(push_mod.__file__).read_text(encoding="utf-8")
    pdf_src = Path(pdf_mod.__file__).read_text(encoding="utf-8")
    assert "ensure_flat_pattern_dims(" in push_src
    assert "ensure_flat_pattern_dims(" in pdf_src
