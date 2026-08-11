"""Dash-exact component PDF resolve + BOM description rename."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from secturafab.pdf_assembly_ops import (
    _rename_imported_descriptions,
    resolve_component_pdf,
)


def test_resolve_rejects_different_dash_sibling(tmp_path: Path):
    (tmp_path / "25060-8.pdf").write_bytes(b"%PDF-1.4")
    assert resolve_component_pdf(
        "25060-5", library_folder=tmp_path, related_pdf_names=["25060-8.pdf"]
    ) is None


def test_resolve_exact_dash_and_bare_base(tmp_path: Path):
    (tmp_path / "25060-5.pdf").write_bytes(b"%PDF-1.4")
    (tmp_path / "25060-8.pdf").write_bytes(b"%PDF-1.4")
    got = resolve_component_pdf("25060-5", library_folder=tmp_path)
    assert got is not None and got.name == "25060-5.pdf"

    bare = tmp_path / "lib2"
    bare.mkdir()
    (bare / "15644.pdf").write_bytes(b"%PDF-1.4")
    got2 = resolve_component_pdf("15644-1", library_folder=bare)
    assert got2 is not None and got2.name == "15644.pdf"


def test_rename_exact_then_unique_base_no_cross_label():
    client = MagicMock()
    items = [
        {
            "ID": "a",
            "ProductType": 100,
            "Description": '25060-5  - 1/4" A36 10 in X 2 in',
        },
        {
            "ID": "b",
            "ProductType": 100,
            "Description": '25060-8  - tube',
        },
        {
            "ID": "c",
            "ProductType": 100,
            "Description": '15644  - 3/16" A36 1 in X 1 in',
        },
    ]
    client.get_json.return_value = {"ItemList": items}
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save

    notes = _rename_imported_descriptions(
        client,
        "q1",
        part_nos=["25060-5", "25060-8", "15644-1"],
    )
    assert any("Set Description" in n for n in notes)
    assert items[0]["Description"] == "25060-5"
    assert items[1]["Description"] == "25060-8"
    assert items[2]["Description"] == "15644-1"


def test_rename_ambiguous_base_left_alone_when_two_dashes_unused():
    """Two CAD lines both start with bare 25060 and two BOM dashes → no guess."""
    client = MagicMock()
    items = [
        {"ID": "a", "ProductType": 100, "Description": "25060  - first"},
        {"ID": "b", "ProductType": 100, "Description": "25060  - second"},
    ]
    client.get_json.return_value = {"ItemList": items}
    notes = _rename_imported_descriptions(
        client, "q1", part_nos=["25060-5", "25060-8"]
    )
    assert notes == []
    assert items[0]["Description"].startswith("25060")
    assert items[1]["Description"].startswith("25060")
