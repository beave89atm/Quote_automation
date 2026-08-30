"""Finish / CAD Files JS contract; Finish is additive when a website cookie exists."""

from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from secturafab.push import SecturaFabPushService, classify_sectura_item
from secturafab.website import (
    EMPTY_GUID,
    WEBSITE_AUTH_GAP,
    WEBSITE_FINISH_PATHS,
    SecturaFabWebsiteAuthError,
    build_dxf_finish_payload,
    LINEAR_ADD_FIELDS,
    PDF_GETDATA_FIELDS,
    build_linear_add_payload,
    build_pdf_finish_payload,
    build_cadimport_next_payload,
    cadimport_list_is_native_array,
    cadimport_payload_preview,
    filelist_from_cadimport_upload,
    normalize_cadimport_list,
    filter_finish_filelist,
    filter_pdf_filelist,
    linear_website_product_type,
    overlay_classified_row,
    pick_closest_linear_product,
)


def test_quote_order_edit_bundle_cites_do_create_dxf_parts():
    """/bundles/QuoteOrderEdit: createAllParts → DoCreateDXFParts POST /part/create."""
    from secturafab.cadimport_js import (
        CREATE_DXF_PARTS_PATH,
        build_create_dxf_parts_fields,
        create_dxf_parts_xhr,
        explode_xhrs,
        extract_cadimport_xhrs,
        jquery_ajax_form,
    )

    js = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "quote_order_edit_create_parts.js"
    ).read_text()
    xhrs = extract_cadimport_xhrs(js)
    create = next(x for x in xhrs if x.path == CREATE_DXF_PARTS_PATH)
    assert create.function == "DoCreateDXFParts"
    assert create.method == "POST"
    assert create.content_type == "application/x-www-form-urlencoded"
    for key in ("Location", "IDList", "unitList", "OtherFileIDList", "Height", "Width"):
        assert key in create.body_keys
    convert = next(x for x in xhrs if x.path == "/CadImport/ConvertTo")
    assert convert.function == "ConvertTo"
    assert convert.body_keys == ["IDList", "Units"] or "IDList" in convert.body_keys
    nxt = next(x for x in xhrs if x.path == "/CadImport/UpdateDataNext")
    assert nxt.function == "UpdateDXF_LoadNew"
    exploded = explode_xhrs(xhrs)
    assert exploded
    assert exploded[0].path == CREATE_DXF_PARTS_PATH
    assert all("ConvertTo" not in x.path for x in exploded)
    assert all("UpdateDataNext" not in x.path for x in exploded)
    cited = create_dxf_parts_xhr()
    assert "DoCreateDXFParts POST /part/create" in cited.cite()
    fields = build_create_dxf_parts_fields(
        [{"SourceDataID": "src-1", "Units": "inch"}],
        location="",
    )
    form_keys = [k for k, _ in jquery_ajax_form(fields)]
    assert form_keys.count("IDList[]") == 1
    assert "unitList[]" in form_keys
    assert "List" not in form_keys


def test_dxf_finish_payload_js_contract():
    rows = [
        {
            "ErrorStatus": 0,
            "Qty": 1,
            "Machine": "Laser",
            "Material": "100k",
            "Thickness": 0.375,
            "ProductID": None,
            "Name": "21680-1 PLATE",
        },
        {"ErrorStatus": 1, "Qty": 1, "Machine": "Laser", "Name": "bad"},
        {"ErrorStatus": 0, "Qty": 0, "Machine": "Saw", "Name": "zero"},
        {
            "ErrorStatus": 0,
            "Qty": 2,
            "Machine": "Saw",
            "Material": "A519",
            "ProductID": "abc-linear",
            "IsLinear": True,
            "LinearLength": 9.75,
            "Name": "21684 TUBE",
        },
    ]
    payload = build_dxf_finish_payload("quote-id", rows, item_id=None, customer_material=False)
    assert payload["ID"] == "quote-id"
    assert payload["ItemID"] == EMPTY_GUID
    assert payload["customerMaterial"] is False
    assert len(payload["FileList"]) == 2
    assert payload["FileList"][0]["Machine"] == "Laser"
    assert payload["FileList"][0]["Material"] == "100k"
    assert payload["FileList"][0]["Thickness"] == 0.375
    assert payload["FileList"][1]["ProductID"] == "abc-linear"
    assert payload["FileList"][1]["LinearLength"] == 9.75
    assert all(r.get("ErrorStatus") == 0 for r in payload["FileList"])
    assert all(r.get("Qty") > 0 for r in payload["FileList"])


def test_finish_filelist_keeps_cadimport_source_ids():
    rows = [
        {
            "ErrorStatus": 0,
            "Qty": 1,
            "Name": "14500-1",
            "SourceDataID": "src-1",
            "FileID": "file-1",
            "CadType": 0,
            "FileType": ".pdf",
            "Stock_X": 11.0,
            "Stock_Y": 6.25,
            "Stock_Units": "inch",
            "Machine": None,
            "Material": "A572",
        }
    ]
    payload = build_dxf_finish_payload("qid", rows)
    assert payload["FileList"][0]["SourceDataID"] == "src-1"
    assert payload["FileList"][0]["FileID"] == "file-1"
    assert payload["FileList"][0]["Stock_X"] == 11.0
    uploaded = filelist_from_cadimport_upload(
        {"status": "OK", "List": rows, "ListOther": []}
    )
    assert len(uploaded) == 1
    assert uploaded[0]["SourceDataID"] == "src-1"


def test_filelist_from_cadimport_parses_string_and_html_bodies():
    """Live Next/Data returned HTTP 200 with a string; kids must still parse."""
    kids = [
        {
            "SourceDataID": "src-plate",
            "FileID": "file-plate",
            "Name": "1007756-2 GUSSET",
            "Qty": 1,
            "ErrorStatus": 0,
        },
        {
            "SourceDataID": "src-slug",
            "FileID": "file-slug",
            "Name": "1007756-4 SLUG",
            "Qty": 2,
            "ErrorStatus": 0,
        },
    ]
    as_json = json.dumps({"List": kids})
    assert [r["Name"] for r in filelist_from_cadimport_upload(as_json)] == [
        "1007756-2 GUSSET",
        "1007756-4 SLUG",
    ]
    double = json.dumps(as_json)
    assert len(filelist_from_cadimport_upload(double)) == 2
    nested = {"Data": json.dumps({"FileList": kids})}
    assert len(filelist_from_cadimport_upload(nested)) == 2
    html = (
        '<div id="gridDXFParts"></div><script>kendoGrid({data:'
        + json.dumps({"FileList": kids})
        + "});</script>"
    )
    html_rows = filelist_from_cadimport_upload(html)
    assert len(html_rows) == 2
    assert html_rows[0]["SourceDataID"] == "src-plate"
    assert "string" in cadimport_payload_preview(html)


def test_cadimport_next_list_is_json_array_not_python_repr():
    """Live 1002381-1 sent List=str(rows) with single quotes; Next 200 empty."""
    rows = [
        {
            "SourceDataID": "489f2a35-7617-47b2-a973-318a83574665",
            "CadType": 1,
            "PartMode": 0,
            "FileType": ".STEP",
            "PartCount": 4,
            "Name": "1002381-1",
        }
    ]
    py_repr = str(rows)
    assert py_repr.startswith("[{'")
    parsed = normalize_cadimport_list(py_repr)
    assert len(parsed) == 1
    assert parsed[0]["SourceDataID"] == "489f2a35-7617-47b2-a973-318a83574665"
    payload = build_cadimport_next_payload(
        "qid", py_repr, list_other="[]"
    )
    assert cadimport_list_is_native_array(payload)
    assert payload["status"] == "OK"
    assert payload["List"][0]["PartCount"] == 4
    assert payload["ListOther"] == []
    dumped = json.dumps(payload)
    parsed = json.loads(dumped)
    assert isinstance(parsed["List"], list)
    assert parsed["List"][0]["SourceDataID"] == "489f2a35-7617-47b2-a973-318a83574665"


def test_cadimport_update_data_next_posts_native_json_array():
    """Live 34574-1: List must be list_type=list in the JSON body, not str."""
    from secturafab.client import SecturaFabClient

    real = SecturaFabClient.__new__(SecturaFabClient)
    real.config = MagicMock()
    real.config.timeout_seconds = 30
    captured: dict[str, Any] = {}

    def fake_website_request(method, path, **kwargs):
        captured["method"] = method
        captured["path"] = path
        captured["json"] = kwargs.get("json")
        captured["data"] = kwargs.get("data")
        captured["prefer_api_origin"] = kwargs.get("prefer_api_origin")
        captured["www_only"] = kwargs.get("www_only")
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b""
        resp.json.side_effect = ValueError("empty")
        resp.headers = {}
        resp.text = ""
        resp.url = path
        return resp

    real.website_request = fake_website_request  # type: ignore[method-assign]
    real.cadimport_update_data_next(
        {
            "ID": "qid",
            "status": "OK",
            "List": [
                {
                    "SourceDataID": "src-1",
                    "Name": "34574-1",
                    "PartCount": 12,
                }
            ],
            "ListOther": [],
        }
    )
    assert captured["path"] == "/CadImport/UpdateDataNext"
    assert captured["data"] is None
    assert captured["www_only"] is True
    body = captured["json"]
    assert isinstance(body["List"], list)
    assert not isinstance(body["List"], str)
    assert body["List"][0]["SourceDataID"] == "src-1"
    assert body["ListOther"] == []
    assert body["status"] == "OK"
    assert body["ID"] == "qid"


def test_filter_filelist_matches_js_grid_rule():
    kept = filter_finish_filelist(
        [
            {"ErrorStatus": 0, "Qty": 1},
            {"ErrorStatus": 2, "Qty": 4},
            {"ErrorStatus": 0, "Quantity": 0},
        ]
    )
    assert len(kept) == 1
    assert kept[0]["Qty"] == 1


def test_pdf_and_linear_payloads_share_id_itemid():
    pdf = build_pdf_finish_payload(
        "qid",
        [
            {
                "Status": 1,
                "Qty": 1,
                "Machine": "Laser",
                "FileName": "a.pdf",
                "ItemType": "cad",
                "Thickness": 0.25,
                "Length": 6.25,
                "Width": 11.0,
            }
        ],
    )
    assert pdf["ID"] == "qid"
    assert pdf["ItemID"] == EMPTY_GUID
    assert set(pdf.keys()) == {"ID", "ItemID", "FileList"}
    assert "customerMaterial" not in pdf
    assert pdf["FileList"][0]["ItemType"] == "cad"
    assert pdf["FileList"][0]["Machine"] == "Laser - Bay1"
    _lin_extra = {
        "productConfigID": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "productSubType": "bar",
        "dim1": 1,
        "dim2": 0,
        "dim3": 0,
        "dim4": 0,
        "weightLength": 1.2,
    }
    linear = build_linear_add_payload(
        "qid", product_id="pid-1", qty=2, length=10.9, extra=_lin_extra
    )
    assert linear["ID"] == "qid"
    assert linear["productID"] == "pid-1"
    assert linear["qty"] == 2
    assert linear["productType"] == "bar"
    angle = build_linear_add_payload(
        "qid",
        product_id="pid-ang",
        qty=2,
        length=125,
        name="29860-3 PEDESTAL BRACE ANGLE",
        extra={**_lin_extra, "productSubType": "angle"},
    )
    assert angle["productType"] == "structural"
    tube = build_linear_add_payload(
        "qid",
        product_id="pid-tube",
        qty=1,
        length=16,
        name="1001880-2 PEDESTAL TUBE",
        extra={**_lin_extra, "productSubType": "tube"},
    )
    assert tube["productType"] == "tube"
    assert list(linear.keys()) == list(LINEAR_ADD_FIELDS)


def test_pdf_finish_payload_commits_cadimport_newline_fields():
    """CadImport list-only rows (Status=0, Stock_X/Y, Machine Laser) must commit."""
    from secturafab.website import prepare_pdf_newline_fields

    raw = {
        "Status": 0,
        "Qty": 1,
        "Machine": "Laser",
        "FileName": "14501-1.pdf",
        "Name": "14501-1 PEDESTAL TOP PLATE",
        "Stock_X": 11.0,
        "Stock_Y": 6.25,
        "Material": "A572",
        "Thickness": 0.25,
    }
    prepared = prepare_pdf_newline_fields(raw)
    assert prepared["Status"] == 1
    assert prepared["Machine"] == "Laser - Bay1"
    assert prepared["ItemType"] == "cad"
    assert int(prepared["ProductType"]) == 100
    assert prepared["Width"] == 11.0
    assert prepared["Length"] == 6.25
    payload = build_pdf_finish_payload("qid", [raw])
    assert len(payload["FileList"]) == 1
    row = payload["FileList"][0]
    assert row["Status"] == 1
    assert row["Machine"] == "Laser - Bay1"
    assert row["ItemType"] == "cad"
    assert int(row["ProductType"]) == 100
    assert row["Width"] == 11.0
    assert row["Length"] == 6.25
    assert row["Thickness"] == 0.25


def test_cadimport_only_filelist_is_not_additem_pdf_body():
    """CadImport identity without Thickness/Length/Width/ItemType=cad must not POST."""
    from secturafab.website import (
        attachment_pdf_filelist_ready,
        is_cadimport_only_filelist_row,
    )

    cadimport_only = {
        "SourceDataID": "src-1",
        "FileID": "file-1",
        "CadType": 0,
        "Status": 1,
        "Qty": 1,
        "Machine": "Laser",
        "FileName": "32259-1.pdf",
        "Name": "32259-1",
    }
    assert is_cadimport_only_filelist_row(cadimport_only) is True
    assert attachment_pdf_filelist_ready(cadimport_only) is False
    payload = build_pdf_finish_payload("qid", [cadimport_only])
    assert payload["FileList"] == []


def test_linear_payload_rejects_empty_config_guid():
    with pytest.raises(ValueError, match="productConfigID"):
        build_linear_add_payload(
            "qid",
            product_id="aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
            qty=1,
            length=12.5,
            extra={"productConfigID": EMPTY_GUID, "productSubType": "bar"},
        )
    with pytest.raises(ValueError, match="productConfigID"):
        build_linear_add_payload(
            "qid",
            product_id="aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
            qty=1,
            length=12.5,
        )


def test_linear_payload_rejects_config_equal_product_id():
    """productConfigID == productID 500s (live 7a555ac2)."""
    pid = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
    with pytest.raises(ValueError, match="must not equal productID"):
        build_linear_add_payload(
            "qid",
            product_id=pid,
            qty=1,
            length=12.5,
            extra={
                "productConfigID": pid,
                "productSubType": "struct_ang",
                "dim1": 0.5,
                "weightLength": 0.37275,
            },
        )


def test_pick_linear_config_id_reads_value_guid():
    from secturafab.website import pick_linear_config_id

    cfg20 = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    rows = [
        {"ID": EMPTY_GUID, "Text": "24 ft", "Value": "dddddddd-dddd-4ddd-8ddd-dddddddddddd"},
        {"ID": None, "Text": "20 ft", "Value": cfg20},
    ]
    assert pick_linear_config_id(rows) == cfg20
    value_only = [{"Value": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee", "Text": "21 ft"}]
    assert pick_linear_config_id(value_only) == "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
    assert pick_linear_config_id([{"ID": EMPTY_GUID, "Name": "20 ft"}]) is None


def test_linear_bind_uses_20ft_config_and_catalog_dims():
    from secturafab.website import linear_bind_fields, pick_linear_config_id

    cfg20 = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    cfg24 = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
    configs = [
        {"ID": cfg24, "Name": "24 ft"},
        {"ID": EMPTY_GUID, "Name": "20 ft"},
        {"ID": cfg20, "Name": "20 ft"},
    ]
    assert pick_linear_config_id(configs) == cfg20
    bind = linear_bind_fields(
        {
            "ID": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
            "ProductName": "L1/2X1/2X1/8-A36",
            "ProductSubType": "bar",
            "Dim1": 0.5,
            "Dim2": 0.5,
            "Dim3": 0.125,
            "WeightLength": 0.38,
        },
        configs,
    )
    assert bind is not None
    assert bind["productConfigID"] == cfg20
    assert bind["productConfigID"] != EMPTY_GUID
    assert bind["productSubType"] == "bar"
    assert bind["dim1"] == 0.5
    assert bind["weightLength"] == 0.38


def test_linear_bind_does_not_copy_angle_dims_onto_channel_or_tube():
    """C3X4.1 / RT* must not reuse L1/2 struct_ang dim1=0.5 from another SKU."""
    from secturafab.website import build_linear_add_payload, linear_bind_fields

    cfg_ang = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    cfg_ch = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
    cfg_tu = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
    angle_id = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
    channel_id = "bbbbbbbb-bbbb-4ccc-8ddd-eeeeeeeeeeee"
    tube_id = "cccccccc-bbbb-4ccc-8ddd-eeeeeeeeeeee"
    shared = [
        {
            "Value": cfg_ang,
            "Text": "20 ft",
            "productSubType": "struct_ang",
            "dim1": 0.5,
            "dim2": 0.5,
            "dim3": 0.125,
            "weightLength": 0.37275,
        },
        {"Value": cfg_ch, "Text": "20 ft"},
        {"Value": cfg_tu, "Text": "21 ft"},
    ]
    channel = linear_bind_fields(
        {"ID": channel_id, "ProductName": "C3X4.1-A36"},
        shared,
        lookup_scoped=True,
    )
    tube = linear_bind_fields(
        {"ID": tube_id, "ProductName": "RT1/8X0.022-A519"},
        shared,
        lookup_scoped=True,
    )
    angle = linear_bind_fields(
        {
            "ID": angle_id,
            "ProductName": "L1/2X1/2X1/8-A36",
            "ProductSubType": "struct_ang",
            "Dim1": 0.5,
            "WeightLength": 0.37275,
        },
        shared,
        lookup_scoped=True,
    )
    assert channel is not None and tube is not None and angle is not None
    assert channel["productSubType"] != "struct_ang"
    assert float(channel["dim1"]) != 0.5
    assert float(channel["weightLength"]) != 0.37275
    assert float(channel["dim1"]) == 3
    assert tube["productSubType"] != "struct_ang"
    assert float(tube["dim1"]) != 0.5
    assert float(tube["dim1"]) == 0.125
    ch_payload = build_linear_add_payload(
        "qid",
        product_id=channel_id,
        qty=1,
        length=125,
        name="1004740-1 C3X4.1-A36",
        extra={k: v for k, v in channel.items() if k != "sku"},
    )
    tu_payload = build_linear_add_payload(
        "qid",
        product_id=tube_id,
        qty=1,
        length=125,
        name="25060-6 RT1/8X0.022-A519",
        extra={k: v for k, v in tube.items() if k != "sku"},
    )
    assert ch_payload["productType"] == "structural"
    assert tu_payload["productType"] == "tube"
    for payload in (ch_payload, tu_payload):
        assert isinstance(payload["productType"], str)
        assert payload["productType"] not in {10, 30, 40, "10", "30", "40"}


def test_linear_bind_keeps_20ft_value_not_product_id():
    """Live 7a555ac2: product-shaped lookup row must not hide a 20ft Value."""
    from secturafab.website import (
        linear_bind_fields,
        linear_lookup_rows,
        pick_linear_config_id,
    )

    pid = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
    cfg20 = "fd2cc452-aaaa-4bbb-8ccc-dddddddddddd"
    cfg21 = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    product_row = {
        "ID": pid,
        "Value": pid,
        "ProductName": "L1/2X1/2X1/8-A36",
        "productSubType": "struct_ang",
        "dim1": 0.5,
        "dim2": 0.5,
        "dim3": 0.125,
        "weightLength": 0.37275,
    }
    lookup_list = [
        product_row,
        {"Value": cfg20, "Text": "20 ft"},
        {"Value": cfg21, "Text": "21 ft"},
    ]
    assert pick_linear_config_id(lookup_list, product_id=pid) == cfg20
    assert pick_linear_config_id(lookup_list, product_id=pid) != pid

    # Data=product, List=20ft/21ft — Value must not be discarded.
    merged = linear_lookup_rows({"Data": [product_row], "List": lookup_list[1:]})
    assert pick_linear_config_id(merged, product_id=pid) == cfg20
    assert any(str(r.get("Value") or "") == cfg20 for r in merged)

    cases = (
        (
            "32259-1",
            "L1/2X1/2X1/8-A36",
            {
                "ProductSubType": "struct_ang",
                "Dim1": 0.5,
                "Dim2": 0.5,
                "Dim3": 0.125,
                "WeightLength": 0.37275,
            },
            "structural",
        ),
        (
            "1004740-1",
            "C3X4.1-A36",
            {
                "ProductSubType": "channel",
                "Dim1": 3,
                "Dim2": 0.17,
                "Dim3": 1.41,
                "WeightLength": 4.1,
            },
            "structural",
        ),
        (
            "25060-6",
            "RT1/8X0.022-A519",
            {
                "ProductSubType": "tube",
                "Dim1": 0.125,
                "Dim2": 0.022,
                "Dim3": 0,
                "WeightLength": 0.024,
            },
            "tube",
        ),
    )
    for pn, sku, dims, ptype in cases:
        product = {"ID": pid, "ProductName": sku, **dims}
        shaped = {
            "ID": pid,
            "Value": pid,
            "ProductName": sku,
            **{k.lower() if k.startswith("Dim") else k: v for k, v in dims.items()},
        }
        rows = [
            shaped,
            {"Value": cfg20, "Text": "20 ft"},
            {"Value": cfg21, "Text": "21 ft"},
        ]
        bind = linear_bind_fields(product, rows, lookup_scoped=True)
        assert bind is not None, sku
        assert bind["productConfigID"] == cfg20, sku
        assert bind["productConfigID"] != bind["productID"], sku
        payload = build_linear_add_payload(
            "qid",
            product_id=pid,
            qty=1,
            length=12.5,
            name=f"{pn} {sku}",
            extra={k: v for k, v in bind.items() if k != "sku"},
        )
        assert payload["productConfigID"] == cfg20, sku
        assert payload["productConfigID"] != payload["productID"], sku
        assert payload["productType"] == ptype


def test_linear_catalog_bind_sends_distinct_config_guid():
    """A Linear POST must send the 20ft List Value, never Data's productID."""
    from secturafab.website import linear_lookup_rows, pick_linear_config_id

    pid = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
    cfg20 = "fd2cc452-aaaa-4bbb-8ccc-dddddddddddd"
    product = {
        "ID": pid,
        "ProductName": "L1/2X1/2X1/8-A36",
        "ProductSubType": "struct_ang",
        "Dim1": 0.5,
        "Dim2": 0.5,
        "Dim3": 0.125,
        "WeightLength": 0.37275,
    }
    lookup = {
        "Data": [
            {
                "ID": pid,
                "Value": pid,
                "ProductName": "L1/2X1/2X1/8-A36",
                "productSubType": "struct_ang",
                "dim1": 0.5,
                "weightLength": 0.37275,
            }
        ],
        "List": [
            {"Value": cfg20, "Text": "20 ft"},
            {"Value": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", "Text": "21 ft"},
        ],
    }
    rows = linear_lookup_rows(lookup)
    assert pick_linear_config_id(rows, product_id=pid) == cfg20
    client = MagicMock()
    client.read_data_linear_lookup.return_value = lookup
    svc = SecturaFabPushService(client=client)
    bind = svc._linear_catalog_bind(product)
    assert bind is not None
    assert bind["productConfigID"] == cfg20
    assert bind["productConfigID"] != bind["productID"]
    extra = {k: v for k, v in bind.items() if k != "sku"}
    payload = build_linear_add_payload(
        "qid",
        product_id=pid,
        qty=1,
        length=12.5,
        name="32259-1 L1/2X1/2X1/8-A36",
        extra=extra,
    )
    assert payload["productConfigID"] == cfg20
    assert payload["productConfigID"] != payload["productID"]
    assert payload["productType"] == "structural"


def test_linear_add_product_type_is_website_string_not_int():
    from secturafab.website import build_linear_add_payload

    extra = {
        "productConfigID": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "productSubType": "channel",
        "dim1": 3,
        "dim2": 1.41,
        "dim3": 0,
        "dim4": 0,
        "weightLength": 4.1,
        "productType": 40,
    }
    payload = build_linear_add_payload(
        "qid",
        product_id="aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
        qty=1,
        length=125,
        name="1004740-1 MASTER CYLINDER MOUNT CHANNEL",
        extra=extra,
    )
    assert payload["productType"] == "structural"
    assert not isinstance(payload["productType"], int)
    assert payload["productType"] not in {10, 30, 40, "10", "30", "40"}


def test_additem_pdf_filelist_keeps_all_upload_list_keys():
    """FileList must not slim away Upload List calculator keys (SourceDataID may be absent)."""
    from secturafab.website import (
        build_pdf_finish_payload,
        filelist_row_from_attachment_upload,
        jquery_ajax_form,
    )

    upload = {
        "List": [
            {
                "FileID": "file-upload-1",
                "ImageID": "img-1",
                "DataPartID": "dp-keep",
                "ThumbnailID": "th-keep",
                "CadType": 2,
                "ExtraCalcKey": "keep-me",
                "FileName": "1004738-1.pdf",
            }
        ]
    }
    row = filelist_row_from_attachment_upload(
        upload,
        part_name="1004738-1 - 1/4 A36 2 in x 9 in",
        qty=1,
        material="A36",
        thickness=0.25,
        length=9.0,
        width=2.0,
        file_name="1004738-1.pdf",
    )
    payload = build_pdf_finish_payload("qid", [row])
    posted = payload["FileList"][0]
    src = upload["List"][0]
    for key, val in src.items():
        assert key in posted, key
        assert posted[key] == val
    assert posted["Machine"] == "Laser - Bay1"
    form = dict(jquery_ajax_form(payload))
    assert form["FileList[0][DataPartID]"] == "dp-keep"
    assert form["FileList[0][ExtraCalcKey]"] == "keep-me"
    assert form["FileList[0][FileID]"] == "file-upload-1"


def test_linear_bind_uses_lookup_row_subtype_dims_weightlength():
    """(b) AddItem_Linear must copy subtype/dims/weightLength from the lookup row."""
    from secturafab.website import build_linear_add_payload, linear_bind_fields

    cfg20 = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    product = {
        "ID": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
        "ProductName": "C3X4.1-A36",
    }
    lookup = [
        {
            "Value": cfg20,
            "Text": "20 ft",
            "ProductID": product["ID"],
            "productSubType": "channel",
            "dim1": 3,
            "dim2": 1.41,
            "dim3": 0.17,
            "dim4": 0.273,
            "weightLength": 4.1,
        }
    ]
    bind = linear_bind_fields(product, lookup)
    assert bind is not None
    assert bind["productConfigID"] == cfg20
    assert bind["productSubType"] == "channel"
    assert bind["dim1"] == 3
    assert bind["dim2"] == 1.41
    assert bind["dim3"] == 0.17
    assert bind["dim4"] == 0.273
    assert bind["weightLength"] == 4.1
    extra = {k: v for k, v in bind.items() if k != "sku"}
    payload = build_linear_add_payload(
        "qid",
        product_id=product["ID"],
        qty=1,
        length=125,
        machine="Saw",
        name="1004740-1 C3X4.1-A36",
        extra=extra,
    )
    assert payload["productSubType"] == "channel"
    assert payload["dim1"] == 3
    assert payload["dim2"] == 1.41
    assert payload["dim3"] == 0.17
    assert payload["dim4"] == 0.273
    assert payload["weightLength"] == 4.1


def test_filelist_from_upload_keeps_sourcedataid_and_fileid():
    """(c) AddItem_PDFFiles FileList must keep SourceDataID/FileID from the upload List."""
    from secturafab.website import (
        build_pdf_finish_payload,
        filelist_row_from_attachment_upload,
        jquery_ajax_form,
    )

    upload = {
        "List": [
            {
                "SourceDataID": "src-upload-1",
                "FileID": "file-upload-1",
                "ImageID": "img-1",
                "CadType": 0,
                "FileName": "1004738-1.pdf",
                "Stock_X": 2.0,
                "Stock_Y": 9.0,
            }
        ]
    }
    row = filelist_row_from_attachment_upload(
        upload,
        part_name="1004738-1 - 1/4 A36 2 in x 9 in",
        qty=1,
        material="A36",
        thickness=0.25,
        length=9.0,
        width=2.0,
        file_name="1004738-1.pdf",
    )
    assert row["SourceDataID"] == "src-upload-1"
    assert row["FileID"] == "file-upload-1"
    payload = build_pdf_finish_payload("qid", [row])
    posted = payload["FileList"][0]
    assert posted["SourceDataID"] == "src-upload-1"
    assert posted["FileID"] == "file-upload-1"
    form = dict(jquery_ajax_form(payload))
    assert form["FileList[0][SourceDataID]"] == "src-upload-1"
    assert form["FileList[0][FileID]"] == "file-upload-1"


def test_getpdfdata_keeps_status_gt_zero_only():
    kept = filter_pdf_filelist(
        [
            {"Status": 1, "FileName": "ok.pdf", "Qty": 1},
            {"Status": 0, "FileName": "zero.pdf", "Qty": 4},
            {"ErrorStatus": 0, "FileName": "dxf-rule.pdf", "Qty": 1},
        ]
    )
    assert [r["FileName"] for r in kept] == ["ok.pdf"]


def test_website_paths_are_quote_mvc_not_quickadd():
    assert WEBSITE_FINISH_PATHS["add_item_dxf_files"] == "/Quote/AddItem_DXFFiles"
    assert WEBSITE_FINISH_PATHS["add_item_pdf_files"] == "/Quote/AddItem_PDFFiles"
    assert WEBSITE_FINISH_PATHS["add_item_linear"] == "/Quote/AddItem_Linear"
    assert WEBSITE_FINISH_PATHS["add_operation"] == "/Quote/AddOperation"
    assert WEBSITE_FINISH_PATHS["copy_move_to_assembly"] == "/Quote/CopyMoveItemToAssembly"
    assert WEBSITE_FINISH_PATHS["add_feature"] == "/Quote/AddFeature"
    assert WEBSITE_FINISH_PATHS["upload_dxf"] == "/CadImport/UploadItem_DXFFiles"
    assert WEBSITE_FINISH_PATHS["upload_pdf_attachment"] == "/Attachment/UploadItem_PDFFiles"
    assert WEBSITE_FINISH_PATHS["linear_lookup"] == "/Product/Read_DataLinearlookup"
    assert "quickAddCAD" not in str(WEBSITE_FINISH_PATHS)


def test_classify_hose_guard_is_linear():
    assert classify_sectura_item("21689-1 HOSE GUARD") == "Linear"
    assert classify_sectura_item("HOSEGUARD FORMED VIEW") == "Linear"


def test_overlay_linear_sets_saw_and_product():
    row = overlay_classified_row(
        {"Name": "21684 TUBE", "ErrorStatus": 0},
        category="Linear",
        material="A519",
        thickness=0.375,
        product_id="pid",
        sku="RT4X0.375-A519",
        qty=1,
    )
    assert row["Machine"] == "Saw"
    assert row["IsLinear"] is True
    assert row["ProductID"] == "pid"
    assert row["PartMode"] == 1
    assert row["ProductType"] == 30


def test_linear_website_product_type_bar_tube_angle():
    assert linear_website_product_type("29860-3 PEDESTAL BRACE ANGLE") == 40
    assert linear_website_product_type("1001880-2 PEDESTAL TUBE") == 30
    assert linear_website_product_type("10081-2 PEDESTAL HOSE TUBE") == 30
    assert linear_website_product_type("33637-1 1 1/4 RETURN TUBE") == 30
    assert linear_website_product_type("21689-1 HOSE GUARD") == 10
    assert linear_website_product_type("ROUND BAR") == 10
    assert linear_website_product_type("29860-3", sku="L2X1 1/4X1/8-A36") == 40


def test_pick_closest_linear_prefers_rt_over_pipe_sku_for_tube():
    products = [
        {
            "ID": "pipe",
            "ProductName": "P1/8-5-A36",
            "ProductDescription": "Pipe 1/8 A36",
            "ShapeName": "Pipe",
            "MaterialGrade": "A36",
            "Dim1": 0.405,
            "Active": True,
        },
        {
            "ID": "rct",
            "ProductName": "RCT1.25X.120-A513",
            "ProductDescription": "Mechanical Tube 1.25 X .120 A513",
            "ShapeName": "Mechanical Tube",
            "MaterialGrade": "A513",
            "Dim1": 1.25,
            "Active": True,
        },
    ]
    best, _note = pick_closest_linear_product(
        products, description="33637-1 1 1/4 RETURN TUBE", material="A36"
    )
    assert best is not None
    assert best["ID"] == "rct"


def test_pick_closest_linear_prefers_round_bar_for_hose_guard():
    products = [
        {
            "ID": "tube",
            "ProductName": "RT4X0.375-A519",
            "ProductDescription": "Mechanical Tube 4 X 0.375 A519",
            "ShapeName": "Mechanical Tube",
            "MaterialGrade": "A519",
            "Dim1": 4.0,
            "Dim2": 0.375,
            "Active": True,
        },
        {
            "ID": "bar",
            "ProductName": "RB3/8-A36",
            "ProductDescription": "Round Bar 3/8 A36",
            "ShapeName": "Round Bar",
            "MaterialGrade": "A36",
            "Dim1": 0.375,
            "Active": True,
        },
    ]
    best, note = pick_closest_linear_product(
        products, description="21689-1 HOSE GUARD", material="A36"
    )
    assert best is not None
    assert best["ID"] == "bar"
    assert note is None or "mismatch" not in note.lower() or "A36" in (note or "")


def test_finish_cad_files_refuses_oversize_step_no_chunk(tmp_path: Path):
    """Live 106687-1: 43MB Upload 502 — do not POST or invent chunked upload."""
    from secturafab.push import CADIMPORT_UPLOAD_MAX_BYTES

    stp = tmp_path / "106687-1.STEP"
    stp.write_bytes(b"ISO-10303")
    client = MagicMock()
    with patch("secturafab.push.CADIMPORT_UPLOAD_MAX_BYTES", 4):
        notes = SecturaFabPushService(client=client).finish_cad_files(
            quote_id="qid",
            cad_files=[stp],
            material="A36",
            thickness="0.25",
            qty=1,
            takeoff={},
            bom_rows=[],
            library={},
            extra_pdfs=None,
            part_key="106687-1",
        )
    client.upload_item_dxf_files.assert_not_called()
    client.add_item_dxf_files.assert_not_called()
    blob = " ".join(notes)
    assert "not POSTing" in blob
    assert "not chunking" in blob
    assert "not Image Files" in blob
    assert CADIMPORT_UPLOAD_MAX_BYTES == 28 * 1024 * 1024


def test_finish_cad_files_uses_upload_filelist_ids(tmp_path: Path):
    stp = tmp_path / "21678-1.STEP"
    stp.write_bytes(b"ISO")
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {
        "status": "OK",
        "List": [
            {
                "SourceDataID": "src-cad",
                "FileID": "file-cad",
                "FileName": "21678-1.STEP",
                "Name": "21680-1 PLATE",
                "Qty": 1,
                "ErrorStatus": 0,
                "Stock_X": 18.7,
                "Stock_Y": 23.4,
            },
            {
                "SourceDataID": "src-cad-2",
                "FileID": "file-cad-2",
                "FileName": "21681-1.STEP",
                "Name": "21681-1 GUSSET",
                "Qty": 1,
                "ErrorStatus": 0,
            },
        ],
    }
    client.cadimport_data.return_value = {}
    captured: dict[str, Any] = {}

    def _add(**kwargs):
        captured.update(kwargs)
        return {"ok": True}

    client.add_item_dxf_files.side_effect = _add
    service = SecturaFabPushService(client=client)
    notes = service.finish_cad_files(
        quote_id="qid",
        cad_files=[stp],
        material="A36",
        thickness="0.25",
        qty=1,
        takeoff={},
        bom_rows=[],
        library={},
        extra_pdfs=None,
        part_key="21678-1",
    )
    assert captured["file_list"][0]["SourceDataID"] == "src-cad"
    assert captured["file_list"][0]["FileID"] == "file-cad"
    assert any("SourceDataID" in n or "exploded" in n.lower() for n in notes)


def test_raw_step_upload_row_is_not_finish_success(tmp_path: Path):
    """1 STEP upload-row FileList must not be posted as AddItem_DXFFiles success."""
    from secturafab.website import (
        cadimport_filelist_exploded,
        is_raw_step_upload_row,
    )

    raw = {
        "SourceDataID": "src-step",
        "FileID": "file-step",
        "FileName": "1010103-1.STEP",
        "Name": "1010103-1.STEP",
        "Qty": 1,
        "ErrorStatus": 0,
        "PartCount": 10,
    }
    assert is_raw_step_upload_row(
        raw, part_key="1010103-1", cad_filename="1010103-1.STEP"
    )
    assert cadimport_filelist_exploded(
        [raw], part_key="1010103-1", cad_filename="1010103-1.STEP"
    ) is False
    stp = tmp_path / "1010103-1.STEP"
    stp.write_bytes(b"ISO")
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {"status": "OK", "List": [raw]}
    client.cadimport_data.return_value = {"List": [raw]}
    client.cadimport_update_data_next.return_value = {"List": [raw]}
    client.cadimport_get_dxf_data.return_value = {}
    client.get_item_add_view.return_value = {}
    client.quote_item_read.return_value = {"Data": [], "Total": 0}
    client.get_json.return_value = {"ItemList": []}
    notes = SecturaFabPushService(client=client).finish_cad_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000001010",
        cad_files=[stp],
        material="A36",
        thickness="0.25",
        qty=1,
        takeoff={},
        bom_rows=[],
        library={},
        extra_pdfs=None,
        part_key="1010103-1",
        explode_polls=2,
        explode_sleep_s=0,
    )
    client.add_item_dxf_files.assert_not_called()
    client.create_dxf_parts.assert_not_called()
    blob = " ".join(notes)
    assert "raw upload" in blob.lower() or "not explode" in blob.lower()
    assert "not success" in blob.lower() or "not Finishing" in blob
    assert "af_extracted=false" in blob
    assert "has_antiforgery=false" in blob


def test_cadimport_next_exploded_kids_are_finished(tmp_path: Path):
    """DoCreateDXFParts /part/create t.List kids are the Finish FileList, not the STEP row."""
    stp = tmp_path / "1010103-1.STEP"
    stp.write_bytes(b"ISO")
    raw = {
        "SourceDataID": "src-step",
        "FileID": "file-step",
        "FileName": "1010103-1.STEP",
        "Name": "1010103-1",
        "Qty": 1,
        "ErrorStatus": 0,
        "PartCount": 3,
    }
    kids = [
        {
            "SourceDataID": "src-plate",
            "FileID": "file-plate",
            "FileName": "1010104-1",
            "Name": "1010104-1 GUSSET",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        },
        {
            "SourceDataID": "src-slug",
            "FileID": "file-slug",
            "FileName": "1010108-1",
            "Name": "1010108-1 SLUG",
            "Qty": 2,
            "ErrorStatus": 0,
            "Status": 1,
        },
        {
            "SourceDataID": "src-bar",
            "FileID": "file-bar",
            "FileName": "1010109-1",
            "Name": "1010109-1 TUBE",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        },
    ]
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {"status": "OK", "List": [raw]}
    client._request_verification_fields = [("__RequestVerificationToken", "x")]
    client.create_dxf_parts.return_value = {"List": kids}
    client.cadimport_update_data_next.return_value = {"List": [raw]}
    client.cadimport_data.return_value = {"List": kids}
    client.cadimport_get_dxf_data.return_value = {"FileList": kids}
    client.get_item_add_view.return_value = {"FileList": kids}
    client.quote_item_read.return_value = {
        "Data": [
            {"ProductType": 100, "Description": "1010104-1"},
            {"ProductType": 10, "Description": "1010108-1"},
        ],
        "Total": 2,
    }
    captured: dict[str, Any] = {}

    def _add(**kwargs):
        captured.update(kwargs)
        return {"ok": True}

    client.add_item_dxf_files.side_effect = _add
    notes = SecturaFabPushService(client=client).finish_cad_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000001011",
        cad_files=[stp],
        material="A36",
        thickness="0.25",
        qty=1,
        takeoff={},
        bom_rows=[
            {"part_no": "1010104-1", "description": "GUSSET 100K", "qty": 1},
            {"part_no": "1010108-1", "description": "SLUG A519", "qty": 2},
            {"part_no": "1010109-1", "description": "TUBE A1011", "qty": 1},
        ],
        library={},
        extra_pdfs=None,
        part_key="1010103-1",
        explode_polls=2,
        explode_sleep_s=0,
    )
    client.create_dxf_parts.assert_called()
    assert client.create_dxf_parts.call_count == 1
    ids, units = client.create_dxf_parts.call_args.args[:2]
    assert ids == ["src-step"]
    assert units
    client.cadimport_convert_to.assert_not_called()
    client.cadimport_update_data_next.assert_not_called()
    client.add_item_dxf_files.assert_called()
    posted = captured["file_list"]
    assert len(posted) == 3
    names = {str(r.get("Name") or r.get("Description") or "") for r in posted}
    assert any("1010104" in n for n in names)
    assert any("1010108" in n for n in names)
    assert not any(str(r.get("Name") or "").endswith(".STEP") for r in posted)
    cats = {str(r.get("Category") or r.get("ItemType")) for r in posted}
    assert "Cad" in cats
    assert "Linear" in cats
    mats = " ".join(str(r.get("Material") or "") for r in posted)
    assert "A36" not in mats or "100K" in mats or "A519" in mats or "A1011" in mats
    for row in posted:
        assert float(row.get("Status") or 0) > 0
    assert any("exploded" in n.lower() for n in notes)
    blob = " ".join(notes)
    assert "af_extracted=true" in blob
    assert "has_antiforgery=true" in blob


def test_cadimport_next_json_string_body_is_finished(tmp_path: Path):
    """Next 200 with a JSON *string* must still Finish exploded kids."""
    stp = tmp_path / "1007756-1.STEP"
    stp.write_bytes(b"ISO")
    raw = {
        "SourceDataID": "src-step",
        "FileID": "file-step",
        "FileName": "1007756-1.STEP",
        "Name": "1007756-1",
        "Qty": 1,
        "ErrorStatus": 0,
        "PartCount": 2,
    }
    kids = [
        {
            "SourceDataID": "src-plate",
            "FileID": "file-plate",
            "FileName": "1007756-2",
            "Name": "1007756-2 GUSSET",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        },
        {
            "SourceDataID": "src-bar",
            "FileID": "file-bar",
            "FileName": "1007756-4",
            "Name": "1007756-4 TUBE",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        },
    ]
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {"status": "OK", "List": [raw]}
    client._request_verification_fields = [("__RequestVerificationToken", "x")]
    client.create_dxf_parts.return_value = json.dumps({"List": kids})
    client.cadimport_update_data_next.return_value = json.dumps({"List": [raw]})
    client.cadimport_data.return_value = json.dumps({"Data": kids})
    client.cadimport_get_dxf_data.return_value = (
        '<div id="gridDXFParts"></div>' + json.dumps({"FileList": kids})
    )
    client.get_item_add_view.return_value = {"FileList": kids}
    client.quote_item_read.return_value = {
        "Data": [
            {"ProductType": 100, "Description": "1007756-2"},
            {"ProductType": 10, "Description": "1007756-4"},
        ],
        "Total": 2,
    }
    captured: dict[str, Any] = {}

    def _add(**kwargs):
        captured.update(kwargs)
        return {"ok": True}

    client.add_item_dxf_files.side_effect = _add
    notes = SecturaFabPushService(client=client).finish_cad_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000001013",
        cad_files=[stp],
        material="A36",
        thickness="0.25",
        qty=1,
        takeoff={},
        bom_rows=[
            {"part_no": "1007756-2", "description": "GUSSET 100K", "qty": 1},
            {"part_no": "1007756-4", "description": "TUBE A1011", "qty": 1},
        ],
        library={},
        extra_pdfs=None,
        part_key="1007756-1",
        explode_polls=2,
        explode_sleep_s=0,
    )
    client.add_item_dxf_files.assert_called()
    assert len(captured["file_list"]) == 2
    assert not any(
        str(r.get("Name") or "").endswith(".STEP") for r in captured["file_list"]
    )
    assert any("exploded" in n.lower() for n in notes)


def test_step_create_all_parts_posts_part_create_not_convert_to(tmp_path: Path):
    """QuoteOrderEdit createAllParts → DoCreateDXFParts POST /part/create."""
    stp = tmp_path / "34574-1.STEP"
    stp.write_bytes(b"ISO")
    raw = {
        "SourceDataID": "fc29e35e-aaaa-bbbb-cccc-000000003457",
        "FileID": "file-step",
        "FileName": "34574-1.STEP",
        "Name": "34574-1",
        "Qty": 1,
        "ErrorStatus": 0,
        "PartCount": 12,
        "PartMode": 0,
        "FileType": ".STEP",
        "CadType": 1,
        "Units": "inch",
    }
    kids = [
        {
            "SourceDataID": f"src-{i}",
            "FileID": f"file-{i}",
            "Name": f"34574-{i + 2} PLATE",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        }
        for i in range(3)
    ]
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {
        "status": "OK",
        "List": [raw],
        "ListOther": [],
    }
    client._request_verification_fields = [("__RequestVerificationToken", "x")]
    client.create_dxf_parts.return_value = {"List": kids}
    client.cadimport_convert_to.return_value = {"List": []}
    client.cadimport_update_data_next.return_value = {"List": []}
    client.cadimport_data.return_value = {"List": kids}
    client.get_item_add_view.return_value = {"FileList": kids}
    client.quote_item_read.return_value = {
        "Data": [{"ProductType": 100, "Description": "34574-2"}],
        "Total": 1,
    }
    captured: dict[str, Any] = {}

    def _add(**kwargs):
        captured.update(kwargs)
        return {"ok": True}

    client.add_item_dxf_files.side_effect = _add
    notes = SecturaFabPushService(client=client).finish_cad_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000003457",
        cad_files=[stp],
        material="A36",
        thickness="0.25",
        qty=1,
        takeoff={},
        bom_rows=[{"part_no": "34574-2", "description": "PLATE 100K", "qty": 1}],
        library={},
        extra_pdfs=None,
        part_key="34574-1",
        explode_polls=2,
        explode_sleep_s=0,
    )
    client.create_dxf_parts.assert_called()
    ids, units = client.create_dxf_parts.call_args.args[:2]
    assert ids == ["fc29e35e-aaaa-bbbb-cccc-000000003457"]
    assert units == ["inch"]
    client.cadimport_convert_to.assert_not_called()
    client.cadimport_update_data_next.assert_not_called()
    client.cadimport_get_dxf_data.assert_not_called()
    client.add_item_dxf_files.assert_called()
    assert len(captured["file_list"]) == 3
    assert any("DoCreateDXFParts" in n or "exploded" in n.lower() for n in notes)


def test_part_create_fetches_upload_ids_then_binds_grid():
    """Explode = fetch Upload IDs; bind = DoCreateDXFParts success on t.List."""
    from secturafab.client import SecturaFabClient
    from secturafab.config import SecturaFabConfig

    token = "af-secret-token-value"
    client = SecturaFabClient.__new__(SecturaFabClient)
    client.config = SecturaFabConfig(
        base_url="https://api.example.test",
        website_url="https://www.example.test",
        client_id="x",
        client_secret="y",
        website_cookie=".AspNet.ApplicationCookie=boxcookie",
    )
    client._af_source = "chrome_dom"
    client._request_verification_fields = [("__RequestVerificationToken", token)]
    client._request_verification_token = token
    posted: list[list[tuple[str, str]]] = []
    bound: list[list[dict[str, Any]]] = []

    def _fetch(form_pairs, **_k):
        posted.append(list(form_pairs))
        return {
            "has_antiforgery": True,
            "af_names": ["__RequestVerificationToken"],
            "status": 200,
            "body_keys": ["List"],
            "list_len": 2,
            "List": [{"SourceDataID": "kid-1"}, {"SourceDataID": "kid-2"}],
            "via": "chrome_dom_fetch",
        }

    def _bind(rows, **_k):
        bound.append(list(rows))
        return {
            "grid_present": True,
            "has_gridDXFParts": True,
            "grid_dxf_row_count": 2,
            "bound": True,
            "list_len": 2,
            "opened_via": "already",
        }

    client.session = MagicMock()
    with patch(
        "secturafab.chrome_cdp.chrome_quotes_live", return_value=True
    ), patch(
        "secturafab.client.SecturaFabClient.harvest_chrome_antiforgery",
        return_value="chrome_dom",
    ), patch(
        "secturafab.chrome_cdp.post_part_create_from_quotes_tab", side_effect=_fetch
    ), patch(
        "secturafab.chrome_cdp.bind_do_create_dxf_parts_success", side_effect=_bind
    ):
        result = client.create_dxf_parts(["src-1"], ["inch"], location="", quote_id="qid")
    client.session.request.assert_not_called()
    assert posted
    form_map = {k: v for k, v in posted[0]}
    assert form_map.get("IDList[]") == "src-1"
    assert form_map.get("unitList[]") == "inch"
    assert "__RequestVerificationToken" not in form_map
    assert bound[0][0]["SourceDataID"] == "kid-1"
    assert result["List"][0]["SourceDataID"] == "kid-1"
    assert client._part_create_via == "chrome_dom_fetch"
    assert client._part_create_list_len == 2
    assert client._grid_dxf_row_count == 2
    assert token not in json.dumps(result)


def test_request_verification_fields_matches_kendo_selectors():
    """kendo.antiForgeryTokens: input[name^=] + csrf meta; AddView partial empty."""
    from secturafab.website import request_verification_fields

    add_view = (
        "<div id='gridDXF'><input id='InventoryLocation' value='' /></div>"
        + ("x" * 200)
    )
    assert request_verification_fields(add_view) == []

    quote_html = (
        "<!DOCTYPE html><html><head>"
        '<meta name="csrf-param" content="__RequestVerificationToken" />'
        '<meta name="csrf-token" content="meta-token-value" />'
        "</head><body>"
        '<input type="hidden" name="__RequestVerificationToken" '
        'value="af-secret-token-value" />'
        '<input type="hidden" name="afToken" value="af-alt-token" />'
        "</body></html>"
    )
    fields = request_verification_fields(quote_html)
    names = [n for n, _ in fields]
    values = [v for _, v in fields]
    assert "__RequestVerificationToken" in names
    assert "afToken" in names
    assert "af-secret-token-value" in values
    assert "af-alt-token" in values

    prefixed = (
        '<input name="__RequestVerificationToken_Lw__" type="hidden" '
        'value="prefixed-token" />'
    )
    pref = request_verification_fields(prefixed)
    assert pref[0][0].startswith("__RequestVerificationToken")
    assert pref[0][1] == "prefixed-token"


def test_ensure_quote_antiforgery_reads_quote_layout_not_addview():
    """GET /Quote (no XHR) has the token; AddView partial does not."""
    from secturafab.client import SecturaFabClient
    from secturafab.config import SecturaFabConfig
    from secturafab.website import client_antiforgery_extracted

    token = "af-secret-token-value"
    add_view = "<div id='gridDXF'>partial no layout token</div>"
    quote_html = (
        '<!DOCTYPE html><html><body>'
        f'<input type="hidden" name="__RequestVerificationToken" value="{token}" />'
        "</body></html>"
    )
    client = SecturaFabClient.__new__(SecturaFabClient)
    client.config = SecturaFabConfig(
        base_url="https://api.example.test",
        website_url="https://www.example.test",
        client_id="x",
        client_secret="y",
        website_cookie=".AspNet.ApplicationCookie=boxcookie",
    )
    client._token = MagicMock()
    client._token.authorization_header = "Bearer tok"
    client._token.is_expired = False
    client.authenticate = lambda force=False: client._token  # type: ignore[method-assign]
    client._request_verification_token = None
    client._request_verification_fields = []
    client._last_item_add_view_html = add_view
    captured: list[dict[str, Any]] = []

    def _req(method, path, **kwargs):
        captured.append(
            {
                "method": method,
                "path": path,
                "headers": kwargs.get("headers") or {},
                "params": kwargs.get("params"),
            }
        )
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {}
        resp.url = path
        if path in {"/Quote", "/Quote/QuoteOrderEdit"}:
            resp.text = quote_html
            resp.content = quote_html.encode()
        else:
            resp.text = add_view
            resp.content = add_view.encode()
        return resp

    client._af_source = ""
    client.website_request = _req  # type: ignore[method-assign]
    with patch("secturafab.chrome_cdp.chrome_quotes_live", return_value=False), patch(
        "secturafab.chrome_cdp.chrome_debug_base", return_value=None
    ), patch("secturafab.chrome_cdp.scrape_quotes_af_fields", return_value=[]):
        assert client.ensure_quote_antiforgery("qid-new") is False
    assert client._af_source != "cookie_quote_html"
    assert token not in json.dumps(captured)


def test_part_create_not_posted_when_af_extracted_false():
    """Fail closed: empty AF must not POST /part/create."""
    from secturafab.client import SecturaFabApiError, SecturaFabClient
    from secturafab.config import SecturaFabConfig

    client = SecturaFabClient.__new__(SecturaFabClient)
    client.config = SecturaFabConfig(
        base_url="https://api.example.test",
        website_url="https://www.example.test",
        client_id="x",
        client_secret="y",
    )
    client._request_verification_token = None
    client._request_verification_fields = []
    called = []

    def _req(*args, **kwargs):
        called.append((args, kwargs))
        raise AssertionError("website_request must not run when af_extracted=false")

    client.website_request = _req  # type: ignore[method-assign]
    with pytest.raises(SecturaFabApiError, match="af_extracted=false"):
        client.create_dxf_parts(["src-1"], ["inch"], location="")
    assert called == []


def test_explode_skips_part_create_when_quote_html_has_no_token(tmp_path: Path):
    """Quote + AddView both tokenless → no /part/create; Finish withheld."""
    from secturafab.client import SecturaFabClient
    from secturafab.config import SecturaFabConfig
    from secturafab.website import client_antiforgery_extracted

    token = "af-secret-token-value"
    client = SecturaFabClient.__new__(SecturaFabClient)
    client.config = SecturaFabConfig(
        base_url="https://api.example.test",
        website_url="https://www.example.test",
        client_id="x",
        client_secret="y",
    )
    client._request_verification_token = None
    client._request_verification_fields = []
    client._last_item_add_view_html = "<div id='gridDXF'>no token</div>"
    posted: list[str] = []

    def _website_request(method, path, **kwargs):
        posted.append(f"{method} {path}")
        if path == "/part/create":
            raise AssertionError("must not POST /part/create when af_extracted=false")
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {}
        resp.text = "<html><body>quote page without antiforgery</body></html>"
        resp.content = resp.text.encode()
        resp.url = path
        return resp

    client.website_request = _website_request  # type: ignore[method-assign]
    assert client.ensure_quote_antiforgery("qid") is False
    assert client_antiforgery_extracted(client) is False
    assert "/part/create" not in " ".join(posted)

    stp = tmp_path / "34999-1.STEP"
    stp.write_bytes(b"ISO")
    raw = {
        "SourceDataID": "src-step",
        "FileID": "file-step",
        "FileName": "34999-1.STEP",
        "Name": "34999-1",
        "Qty": 1,
        "ErrorStatus": 0,
        "PartCount": 8,
        "Units": "inch",
    }
    mock = MagicMock()
    mock.upload_item_dxf_files.return_value = {"status": "OK", "List": [raw]}
    mock.cadimport_data.return_value = {"List": [raw]}
    mock.get_item_add_view.return_value = {}
    mock.quote_item_read.return_value = {"Data": [], "Total": 0}
    mock.get_json.return_value = {"ItemList": []}
    mock._request_verification_fields = []
    mock._request_verification_token = None
    notes = SecturaFabPushService(client=mock).finish_cad_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000003499",
        cad_files=[stp],
        material="A36",
        thickness="0.25",
        qty=1,
        takeoff={},
        bom_rows=[],
        library={},
        extra_pdfs=None,
        part_key="34999-1",
        explode_polls=1,
        explode_sleep_s=0,
    )
    blob = " ".join(notes)
    assert "af_extracted=false" in blob
    assert "has_antiforgery=false" in blob
    assert token not in blob
    mock.create_dxf_parts.assert_not_called()
    mock.add_item_dxf_files.assert_not_called()


def test_explode_posts_part_create_from_quotes_tab(tmp_path: Path):
    """Fetch /part/create with Upload IDs, then bind t.List onto #gridDXFParts."""
    from secturafab.client import SecturaFabClient
    from secturafab.config import SecturaFabConfig

    stp = tmp_path / "34998-1.STEP"
    stp.write_bytes(b"ISO")
    raw = {
        "SourceDataID": "src-step",
        "FileID": "file-step",
        "FileName": "34998-1.STEP",
        "Name": "34998-1",
        "Qty": 1,
        "ErrorStatus": 0,
        "PartCount": 3,
        "Units": "inch",
    }
    kids = [
        {
            "SourceDataID": "src-a",
            "FileID": "file-a",
            "Name": "34998-2 PLATE",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        },
        {
            "SourceDataID": "src-b",
            "FileID": "file-b",
            "Name": "34998-3 GUSSET",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        },
    ]
    token = "af-secret-token-value"
    client = SecturaFabClient.__new__(SecturaFabClient)
    client.config = SecturaFabConfig(
        base_url="https://api.example.test",
        website_url="https://www.example.test",
        client_id="x",
        client_secret="y",
        website_cookie=".AspNet.ApplicationCookie=boxcookie",
    )
    client._token = MagicMock()
    client._token.authorization_header = "Bearer tok"
    client._token.is_expired = False
    client.authenticate = lambda force=False: client._token  # type: ignore[method-assign]
    client._request_verification_token = token
    client._request_verification_fields = [("__RequestVerificationToken", token)]
    client._af_source = "chrome_dom"
    client._quotes_tab_live = True
    client._last_item_add_view_html = "<div id='gridDXF'>partial</div>"
    posted: list[list[tuple[str, str]]] = []
    bound: list[int] = []

    def _fetch(form_pairs, **_k):
        posted.append(list(form_pairs))
        return {
            "has_antiforgery": True,
            "af_names": ["__RequestVerificationToken"],
            "status": 200,
            "body_keys": ["List"],
            "list_len": 2,
            "List": kids,
            "via": "chrome_dom_fetch",
        }

    def _bind(rows, **_k):
        bound.append(len(rows))
        return {
            "grid_present": True,
            "has_gridDXFParts": True,
            "grid_dxf_row_count": 2,
            "bound": True,
            "list_len": 2,
            "opened_via": "click",
        }

    client.session = MagicMock()

    def _session_req(method, url, **kwargs):
        assert "/part/create" not in str(url)
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {}
        resp.text = "{}"
        resp.content = b"{}"
        resp.url = url
        resp.json.return_value = {}
        return resp

    client.session.request.side_effect = _session_req

    def _upload(*_a, **_k):
        return {"status": "OK", "List": [raw]}

    client.upload_item_dxf_files = _upload  # type: ignore[method-assign]
    client.cadimport_set_units = lambda *a, **k: {}  # type: ignore[method-assign]
    client.get_item_add_view = lambda *a, **k: {}  # type: ignore[method-assign]
    client.cadimport_data = lambda *a, **k: {"List": kids}  # type: ignore[method-assign]
    client.quote_item_read = lambda *a, **k: {  # type: ignore[method-assign]
        "Data": [{"ProductType": 100, "Description": "34998-2"}],
        "Total": 1,
    }
    finish_args: dict[str, Any] = {}

    def _add(**kwargs):
        finish_args.update(kwargs)
        return {"ok": True}

    client.add_item_dxf_files = _add  # type: ignore[method-assign]
    with patch(
        "secturafab.chrome_cdp.chrome_quotes_live", return_value=True
    ), patch(
        "secturafab.client.SecturaFabClient.harvest_chrome_antiforgery",
        return_value="chrome_dom",
    ), patch(
        "secturafab.chrome_cdp.post_part_create_from_quotes_tab", side_effect=_fetch
    ), patch(
        "secturafab.chrome_cdp.bind_do_create_dxf_parts_success", side_effect=_bind
    ):
        notes = SecturaFabPushService(client=client).finish_cad_files(
            quote_id="11111111-aaaa-bbbb-cccc-000000003498",
            cad_files=[stp],
            material="A36",
            thickness="0.25",
            qty=1,
            takeoff={},
            bom_rows=[{"part_no": "34998-2", "description": "PLATE", "qty": 1}],
            library={},
            extra_pdfs=None,
            part_key="34998-1",
            explode_polls=1,
            explode_sleep_s=0,
        )
    blob = " ".join(notes)
    assert "af_extracted=true" in blob
    assert "has_antiforgery=true" in blob
    assert "af_source=chrome_dom" in blob
    assert "part_create_via=chrome_dom_fetch" in blob
    assert "part_create_list_len=2" in blob
    assert "grid_present=true" in blob
    assert "grid_dxf_row_count=2" in blob
    assert token not in blob
    assert posted
    form_map = {k: v for k, v in posted[0]}
    assert form_map.get("IDList[]") == "src-step"
    assert bound == [2]
    assert finish_args.get("file_list")
    assert len(finish_args["file_list"]) == 2


def test_cookie_name_presence_never_includes_values():
    from secturafab.chrome_cdp import (
        compare_cookie_name_presence,
        cookie_names_from_header,
    )

    header = ".AspNet.ApplicationCookie=SECRET; ASP.NET_SessionId=sess"
    names = cookie_names_from_header(header)
    assert names == [".AspNet.ApplicationCookie", "ASP.NET_SessionId"]
    diff = compare_cookie_name_presence(
        header,
        [".AspNet.ApplicationCookie", "ASP.NET_SessionId", "__RequestVerificationToken"],
    )
    blob = json.dumps(diff)
    assert "SECRET" not in blob
    assert "sess" not in blob
    assert diff["chrome_only"] == ["__RequestVerificationToken"]


def test_post_part_create_from_quotes_tab_uses_page_fetch():
    """DoCreateDXFParts is fetch() in the Quotes document, not cookie HTTP."""
    from secturafab.chrome_cdp import post_part_create_from_quotes_tab

    token = "af-secret-token-value"
    tab = {
        "title": "Quotes",
        "url": "https://www.secturafab.com/Quote",
        "webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/page/quotes",
        "type": "page",
    }

    def _call(ws_url, method, params=None, **kwargs):
        assert method == "Runtime.evaluate"
        expr = str((params or {}).get("expression") or "")
        assert "fetch(" in expr
        assert "/part/create" in expr
        assert "credentials" in expr
        assert "same-origin" in expr
        assert params.get("awaitPromise") is True
        assert params.get("returnByValue") is True
        assert token not in expr
        assert kwargs.get("timeout", 0) >= 60
        return {
            "result": {
                "value": {
                    "has_antiforgery": True,
                    "af_names": ["__RequestVerificationToken"],
                    "status": 200,
                    "body_keys": ["List"],
                    "list_len": 2,
                    "List": [{"SourceDataID": "a"}, {"SourceDataID": "b"}],
                }
            }
        }

    with patch("secturafab.chrome_cdp.quotes_tab", return_value=tab), patch(
        "secturafab.chrome_cdp.cdp_call", side_effect=_call
    ):
        result = post_part_create_from_quotes_tab(
            [("IDList[]", "src-1"), ("unitList[]", "inch")]
        )
    assert result["status"] == 200
    assert result["via"] == "chrome_dom_fetch"
    assert result["body_keys"] == ["List"]
    assert result["list_len"] == 2
    assert len(result["List"]) == 2
    blob = json.dumps(result)
    assert token not in blob


def test_add_item_dxf_files_quotes_tab_fetch_not_cookie_http():
    """Finish POST /Quote/AddItem_DXFFiles is fetch in the Quotes document."""
    from secturafab.chrome_cdp import post_add_item_dxf_files_from_quotes_tab

    token = "af-secret-token-value"
    tab = {
        "title": "Quotes",
        "url": "https://www.secturafab.com/Quote",
        "webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/page/quotes",
        "type": "page",
    }

    def _call(ws_url, method, params=None, **kwargs):
        expr = str((params or {}).get("expression") or "")
        assert method == "Runtime.evaluate"
        assert "fetch(" in expr
        assert "/Quote/AddItem_DXFFiles" in expr
        assert "credentials" in expr
        assert "same-origin" in expr
        assert params.get("awaitPromise") is True
        assert token not in expr
        return {
            "result": {
                "value": {
                    "has_antiforgery": True,
                    "af_names": ["__RequestVerificationToken"],
                    "status": 200,
                    "body_keys": ["NewItem"],
                    "body_type": "object",
                    "has_NewItem": True,
                    "has_QuoteItem": False,
                    "list_len": 0,
                    "text_len": 40,
                }
            }
        }

    with patch("secturafab.chrome_cdp.quote_edit_tab", return_value=None), patch(
        "secturafab.chrome_cdp.quotes_tab", return_value=tab
    ), patch("secturafab.chrome_cdp.cdp_call", side_effect=_call):
        result = post_add_item_dxf_files_from_quotes_tab(
            {"ID": "qid", "ItemID": EMPTY_GUID, "customerMaterial": False, "FileList": []}
        )
    assert result["status"] == 200
    assert result["via"] == "chrome_dom_fetch"
    assert result["has_NewItem"] is True
    assert token not in json.dumps(result)


def test_bind_do_create_dxf_parts_success_evaluates_quote_order_edit():
    """Click #but_dxf on /Quote/EDIT, then DoCreateDXFParts success if kendo."""
    from secturafab.chrome_cdp import bind_do_create_dxf_parts_success

    tab = {
        "title": "*Quote-106386-1",
        "url": "https://www.secturafab.com/Quote/EDIT/qid",
        "webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/page/edit",
        "type": "page",
    }

    def _call(ws_url, method, params=None, **kwargs):
        expr = str((params or {}).get("expression") or "")
        if method == "Page.navigate":
            raise AssertionError("grid_present true must not navigate")
        assert method == "Runtime.evaluate"
        assert ws_url.endswith("/edit")
        assert "gridDXFParts" in expr
        assert "grid_present" in expr
        assert "#but_dxf" in expr
        assert "AddNewItemHTML" in expr
        assert "cad files" in expr
        assert "dataSource.data().toJSON().push" in expr
        assert "kendo_row_keys" in expr
        assert "CadType" in expr
        assert "Stock_X" in expr
        assert "innerHTML" not in expr
        assert "cadFilesDialog" not in expr
        assert "createAllParts" not in expr
        assert params.get("awaitPromise") is True
        assert kwargs.get("timeout", 0) >= 60
        assert "af-secret" not in expr
        return {
            "result": {
                "value": {
                    "grid_present": True,
                    "has_gridDXFParts": True,
                    "grid_dxf_row_count": 31,
                    "bound": True,
                    "list_len": 31,
                    "opened_via": "but_dxf",
                }
            }
        }

    kids = [{"SourceDataID": "a"}, {"SourceDataID": "b"}]
    with patch("secturafab.chrome_cdp.quote_edit_tab", return_value=tab), patch(
        "secturafab.chrome_cdp.quotes_tab", return_value=tab
    ), patch("secturafab.chrome_cdp.cdp_call", side_effect=_call):
        result = bind_do_create_dxf_parts_success(kids, quote_id="qid")
    assert result["bound"] is True
    assert result["grid_present"] is True
    assert result["grid_dxf_row_count"] == 31
    assert result["has_gridDXFParts"] is True
    assert result["opened_via"] == "but_dxf"


def test_invoke_page_dxf_finish_evaluates_page_fn():
    """Page Finish reads #gridDXFParts and POSTs /Quote/AddItem_DXFFiles."""
    from secturafab.chrome_cdp import invoke_page_dxf_finish

    tab = {
        "title": "*Quote-106386-1",
        "url": "https://www.secturafab.com/Quote/EDIT/qid",
        "webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/page/edit",
        "type": "page",
    }

    def _call(ws_url, method, params=None, **kwargs):
        expr = str((params or {}).get("expression") or "")
        assert method == "Runtime.evaluate"
        assert "gridDXFParts" in expr
        assert "/Quote/AddItem_DXFFiles" in expr
        assert "OnAddDXFClick" in expr
        assert "fetch(" not in expr
        assert params.get("awaitPromise") is True
        return {
            "result": {
                "value": {
                    "via": "page_fn",
                    "finish_fn": "OnAddDXFClick",
                    "grid_dxf_row_count": 30,
                    "status": 200,
                    "body_keys": ["NewItem"],
                    "body_type": "object",
                    "has_NewItem": True,
                    "has_QuoteItem": False,
                    "text_len": 40,
                }
            }
        }

    with patch("secturafab.chrome_cdp.quote_edit_tab", return_value=tab), patch(
        "secturafab.chrome_cdp.quotes_tab", return_value=tab
    ), patch("secturafab.chrome_cdp.cdp_call", side_effect=_call):
        result = invoke_page_dxf_finish(quote_id="qid")
    assert result["via"] == "page_fn"
    assert result["has_NewItem"] is True
    assert result["grid_dxf_row_count"] == 30
    assert result["edit_quote_id"] == "qid"
    assert result["minted_id"] == "qid"


def test_apply_grid_dxf_part_modes_evaluates_setpartmode_on_edit():
    """QuoteOrderEdit SetPartMode on #gridDXFParts before Finish."""
    from secturafab.chrome_cdp import apply_grid_dxf_part_modes

    tab = {
        "title": "*Quote-105918-1",
        "url": "https://www.secturafab.com/Quote/EDIT/qid",
        "webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/page/edit",
        "type": "page",
    }

    def _call(ws_url, method, params=None, **kwargs):
        expr = str((params or {}).get("expression") or "")
        assert method == "Runtime.evaluate"
        assert ws_url.endswith("/edit")
        assert "/CadImport/SetPartMode" in expr
        assert "gridDXFParts" in expr
        assert "PartMode" in expr
        assert "kendo_row_keys" in expr
        assert "CadType" in expr
        assert "Stock_X" in expr
        assert 'set("FileType"' in expr or "row.FileType = cat" in expr
        assert "AddItem_DXFFiles" not in expr
        assert params.get("awaitPromise") is True
        return {
            "result": {
                "value": {
                    "grid_present": True,
                    "cad": 3,
                    "linear": 2,
                    "assembly": 1,
                    "component": 1,
                    "set_count": 6,
                    "setpartmode_via": "jquery_ajax",
                    "grid_dxf_row_count": 7,
                    "kendo_row_keys": [
                        "CadType",
                        "FileID",
                        "FileType",
                        "ID",
                        "SourceDataID",
                        "Stock_X",
                        "Stock_Y",
                    ],
                }
            }
        }

    rows = [
        {"ID": "a", "SourceDataID": "s1", "Name": "PLATE", "Category": "Cad", "PartMode": 0},
        {"ID": "b", "SourceDataID": "s2", "Name": "TUBE", "Category": "Linear", "PartMode": 1},
    ]
    with patch("secturafab.chrome_cdp.quote_edit_tab", return_value=tab), patch(
        "secturafab.chrome_cdp.cdp_call", side_effect=_call
    ):
        result = apply_grid_dxf_part_modes(rows, quote_id="qid")
    assert result["grid_present"] is True
    assert result["cad"] == 3
    assert result["linear"] == 2
    assert result["setpartmode_via"] == "jquery_ajax"
    assert "CadType" in result["kendo_row_keys"]
    assert "Stock_X" in result["kendo_row_keys"]
    assert "Stock_Y" in result["kendo_row_keys"]


def test_finish_skips_when_grid_classify_cad_is_zero(tmp_path: Path):
    """Live 105918-1: plates still Component on #gridDXFParts → not Finish."""
    stp = tmp_path / "105918-1.STEP"
    stp.write_bytes(b"ISO")
    kids = [
        {
            "SourceDataID": "src-a",
            "FileID": "file-a",
            "Name": "PLATE-1297_30345-19",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        },
        {
            "SourceDataID": "src-b",
            "FileID": "file-b",
            "Name": "TRIANGLE GUSSET",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        },
    ]
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {"status": "OK", "List": kids}
    client._request_verification_fields = [("__RequestVerificationToken", "x")]
    client._af_source = "chrome_dom"
    client.create_dxf_parts.return_value = {"List": kids}
    client.cadimport_data.return_value = {"List": kids}
    client.get_item_add_view.return_value = {}
    client.quote_item_read.return_value = {"Data": [], "Total": 0}
    client.get_json.return_value = {"ItemList": []}
    with patch(
        "secturafab.chrome_cdp.apply_grid_dxf_part_modes",
        return_value={
            "grid_present": True,
            "cad": 0,
            "linear": 0,
            "assembly": 1,
            "component": 61,
            "set_count": 0,
            "setpartmode_via": "",
            "grid_dxf_row_count": 67,
        },
    ):
        notes = SecturaFabPushService(client=client).finish_cad_files(
            quote_id="11111111-aaaa-bbbb-cccc-000000001059",
            cad_files=[stp],
            material="A36",
            thickness="0.25",
            qty=1,
            takeoff={},
            bom_rows=[],
            library={},
            extra_pdfs=None,
            part_key="105918-1",
            explode_polls=1,
            explode_sleep_s=0,
        )
    client.add_item_dxf_files.assert_not_called()
    blob = " ".join(notes)
    assert "grid_classify Cad:0" in blob
    assert "not Finishing" in blob


def test_finish_get_zero_cad_is_not_gold(tmp_path: Path):
    """Live 105918-1: ItemList 66 with 0 Cad is not gold."""
    stp = tmp_path / "105918-1.STEP"
    stp.write_bytes(b"ISO")
    kids = [
        {
            "SourceDataID": "src-a",
            "FileID": "file-a",
            "Name": "PLATE-1297_30345-19",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        },
        {
            "SourceDataID": "src-b",
            "FileID": "file-b",
            "Name": "TRIANGLE GUSSET",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        },
    ]
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {"status": "OK", "List": kids}
    client._request_verification_fields = [("__RequestVerificationToken", "x")]
    client._af_source = "chrome_dom"
    client.create_dxf_parts.return_value = {"List": kids}
    client.cadimport_data.return_value = {"List": kids}
    client.get_item_add_view.return_value = {}
    client.quote_item_read.return_value = {
        "Data": [
            {"ProductType": 300, "Description": "105918-1"},
            {"ProductType": 200, "Description": "PLATE-1297_30345-19"},
        ],
        "Total": 2,
    }
    client.get_json.return_value = {"ItemList": []}
    with patch(
        "secturafab.chrome_cdp.apply_grid_dxf_part_modes",
        return_value={
            "grid_present": True,
            "cad": 2,
            "linear": 0,
            "assembly": 0,
            "component": 0,
            "set_count": 2,
            "setpartmode_via": "jquery_ajax",
            "grid_dxf_row_count": 2,
            "kendo_row_keys": [
                "CadType",
                "FileID",
                "FileType",
                "ID",
                "SourceDataID",
                "Stock_X",
                "Stock_Y",
            ],
        },
    ):
        notes = SecturaFabPushService(client=client).finish_cad_files(
            quote_id="11111111-aaaa-bbbb-cccc-000000001060",
            cad_files=[stp],
            material="A36",
            thickness="0.25",
            qty=1,
            takeoff={},
            bom_rows=[],
            library={},
            extra_pdfs=None,
            part_key="105918-1",
            explode_polls=1,
            explode_sleep_s=0,
        )
    client.add_item_dxf_files.assert_called()
    blob = " ".join(notes)
    assert "grid_classify Cad:2" in blob
    assert "GET 0 Cad" in blob
    assert "not gold" in blob


def test_finish_empty_body_200_is_not_success(tmp_path: Path):
    """Live 34137-1: Finish 200 empty str / no NewItem / GET 0 Cad → not ok."""
    stp = tmp_path / "34996-1.STEP"
    stp.write_bytes(b"ISO")
    kids = [
        {
            "SourceDataID": "src-a",
            "FileID": "file-a",
            "Name": "34996-2 PLATE",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        },
        {
            "SourceDataID": "src-b",
            "FileID": "file-b",
            "Name": "34996-3 GUSSET",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        },
    ]
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {"status": "OK", "List": kids}
    client._request_verification_fields = [("__RequestVerificationToken", "x")]
    client._af_source = "chrome_dom"
    client._finish_via = "chrome_dom_fetch"
    client.add_item_dxf_files.return_value = {
        "status": 200,
        "body_keys": [],
        "body_type": "str",
        "has_NewItem": False,
        "has_QuoteItem": False,
        "text_len": 0,
        "empty_body": True,
        "via": "chrome_dom_fetch",
    }
    client.cadimport_data.return_value = {"List": kids}
    client.get_item_add_view.return_value = {}
    client.quote_item_read.return_value = {"Data": [], "Total": 0}
    client.get_json.return_value = {"ItemList": []}
    notes = SecturaFabPushService(client=client).finish_cad_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000003496",
        cad_files=[stp],
        material="A36",
        thickness="0.25",
        qty=1,
        takeoff={},
        bom_rows=[],
        library={},
        extra_pdfs=None,
        part_key="34996-1",
        explode_polls=1,
        explode_sleep_s=0,
    )
    blob = " ".join(notes)
    assert "finish_via=chrome_dom_fetch" in blob
    assert "empty body" in blob.lower() or "no NewItem" in blob
    assert "0 ItemList" in blob or "not success" in blob.lower()
    client.add_item_dxf_files.assert_called()


def test_finish_skips_root_only_filelist(tmp_path: Path):
    stp = tmp_path / "34995-1.STEP"
    stp.write_bytes(b"ISO")
    rows = [
        {
            "SourceDataID": "src-root",
            "FileID": "file-root",
            "Name": "Root",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        },
        {
            "SourceDataID": "src-step",
            "FileID": "file-step",
            "FileName": "34995-1.STEP",
            "Name": "34995-1.STEP",
            "Qty": 1,
            "ErrorStatus": 0,
            "PartCount": 8,
            "Status": 1,
        },
    ]
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {"status": "OK", "List": rows}
    client._request_verification_fields = [("__RequestVerificationToken", "x")]
    client._af_source = "chrome_dom"
    client.cadimport_data.return_value = {"List": rows}
    client.get_item_add_view.return_value = {}
    client.quote_item_read.return_value = {"Data": [], "Total": 0}
    client.get_json.return_value = {"ItemList": []}
    notes = SecturaFabPushService(client=client).finish_cad_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000003495",
        cad_files=[stp],
        material="A36",
        thickness="0.25",
        qty=1,
        takeoff={},
        bom_rows=[],
        library={},
        extra_pdfs=None,
        part_key="34995-1",
        explode_polls=1,
        explode_sleep_s=0,
    )
    client.add_item_dxf_files.assert_not_called()
    blob = " ".join(notes)
    assert "not Finishing" in blob or "Root" in blob


def test_classify_nested_weldment_hinge_not_a36_plate():
    assert classify_sectura_item(
        "34136-1 Aluminum Platform Weldment_34136-1"
    ) == "Assembly"
    assert classify_sectura_item(
        "34134 ALUMINUM DOOR WELDMENT-4159_34134-1"
    ) == "Assembly"
    assert classify_sectura_item(
        "88010 ALUMINUM HINGE-4209_88010-1 Flexible"
    ) == "Component"
    assert classify_sectura_item("102196-5 PLATE (HINGE PLATE)") == "Cad"
    service = SecturaFabPushService(client=MagicMock())
    rows = [
        {
            "SourceDataID": "a",
            "Name": "34136-1 Aluminum Platform Weldment_34136-1",
            "Qty": 1,
            "ErrorStatus": 0,
        },
        {
            "SourceDataID": "b",
            "Name": "88010 ALUMINUM HINGE-4209_88010-1 Flexible",
            "Qty": 1,
            "ErrorStatus": 0,
        },
        {
            "SourceDataID": "c",
            "Name": "34137-4 GUSSET",
            "Qty": 1,
            "ErrorStatus": 0,
        },
    ]
    classified, notes = service.classify_cadimport_rows(
        rows,
        default_material="A36",
        default_thickness="0.25",
        bom_rows=[],
        library={},
        extra_pdfs=None,
        qty=1,
    )
    cats = {r["Category"] for r in classified}
    assert "Assembly" in cats
    assert "Component" in cats
    assert "Cad" in cats
    weld = next(r for r in classified if r["Category"] == "Assembly")
    assert weld.get("IsPlate") is False
    assert weld.get("Material") in (None, "", weld.get("Material"))
    assert str(weld.get("Material") or "") != "A36"
    hinge = next(r for r in classified if r["Category"] == "Component")
    assert str(hinge.get("Material") or "") != "A36"
    blob = " ".join(notes)
    assert "Assembly:" in blob


def test_classify_job_pn_only_leaves_are_cad():
    """Live 1020249-1: 14× job PN with no WELDMENT sibling → Cad, not Assembly."""
    service = SecturaFabPushService(client=MagicMock())
    rows = [
        {
            "SourceDataID": f"s{i}",
            "Name": "1020249-1",
            "Qty": 1,
            "ErrorStatus": 0,
        }
        for i in range(14)
    ]
    classified, _notes = service.classify_cadimport_rows(
        rows,
        default_material="A36",
        default_thickness="0.25",
        bom_rows=[{"part_no": "99991-1", "description": "FLOOR PLATE", "qty": 1}],
        library={},
        extra_pdfs=None,
        qty=1,
        part_key="1020249-1",
    )
    cats = [str(r.get("Category") or "") for r in classified]
    assert cats
    assert "Assembly" not in cats
    assert cats.count("Cad") == 14


def test_classify_w001544_occurrence_is_assembly_w001531_is_cad():
    """Live P001545: 34× W001544 is the weldment; W001531_* are Cad plates."""
    service = SecturaFabPushService(client=MagicMock())
    rows = (
        [{"SourceDataID": "root", "Name": "Root", "Qty": 1, "ErrorStatus": 0}]
        + [
            {
                "SourceDataID": f"weld-{i}",
                "Name": "W001544",
                "Qty": 1,
                "ErrorStatus": 0,
            }
            for i in range(34)
        ]
        + [
            {
                "SourceDataID": "p2",
                "Name": "W001531_2",
                "Qty": 1,
                "ErrorStatus": 0,
            },
            {
                "SourceDataID": "p3",
                "Name": "W001531_3",
                "Qty": 1,
                "ErrorStatus": 0,
            },
            {
                "SourceDataID": "rev",
                "Name": "P001545 Rev B",
                "Qty": 1,
                "ErrorStatus": 0,
            },
        ]
    )
    classified, _notes = service.classify_cadimport_rows(
        rows,
        default_material="A36",
        default_thickness="0.25",
        bom_rows=[],
        library={},
        extra_pdfs=None,
        qty=1,
        part_key="P001545",
    )
    by_name = {str(r.get("Name") or ""): str(r.get("Category") or "") for r in classified}
    weld_cats = [
        str(r.get("Category") or "")
        for r in classified
        if str(r.get("Name") or "") == "W001544"
    ]
    assert weld_cats.count("Assembly") == 34
    assert by_name.get("W001531_2") == "Cad"
    assert by_name.get("W001531_3") == "Cad"
    assert by_name.get("P001545 Rev B") == "Assembly"


def test_classify_bare_part_key_is_assembly_not_cad():
    """Live 105918-1 root landed Assembly with bare PN desc — keep that type."""
    service = SecturaFabPushService(client=MagicMock())
    rows = [
        {
            "SourceDataID": "root",
            "Name": "105918-1",
            "Qty": 1,
            "ErrorStatus": 0,
        },
        {
            "SourceDataID": "plate",
            "Name": "PLATE-1297_30345-19",
            "Qty": 1,
            "ErrorStatus": 0,
        },
    ]
    classified, _notes = service.classify_cadimport_rows(
        rows,
        default_material="A36",
        default_thickness="0.25",
        bom_rows=[],
        library={},
        extra_pdfs=None,
        qty=1,
        part_key="105918-1",
    )
    by_src = {r["SourceDataID"]: r["Category"] for r in classified}
    assert by_src["root"] == "Assembly"
    assert by_src["plate"] == "Cad"


def test_live_105918_kid_names_are_not_all_component():
    """Live 105918-1 GET: plates/gussets/mounts Cad, channels/tubes Linear."""
    from tests.fixtures.live_105918_classify import LIVE_105918_KID_NAMES

    from secturafab.website import overlay_classified_row, part_mode_int

    rows = [
        {
            "SourceDataID": f"s{i}",
            "ID": f"id-{i}",
            "Name": name,
            "Qty": 1,
            "ErrorStatus": 0,
        }
        for i, (name, _want) in enumerate(LIVE_105918_KID_NAMES)
    ]
    classified, notes = SecturaFabPushService(client=MagicMock()).classify_cadimport_rows(
        rows,
        default_material="A36",
        default_thickness="0.25",
        bom_rows=[],
        library={},
        extra_pdfs=None,
        qty=1,
        part_key="105918-1",
    )
    counts = {"Cad": 0, "Linear": 0, "Assembly": 0, "Component": 0}
    assert len(classified) == len(LIVE_105918_KID_NAMES)
    for row, (name, want) in zip(classified, LIVE_105918_KID_NAMES, strict=True):
        cat = str(row.get("Category") or "")
        assert cat == want, f"{name!r} want {want} got {cat}"
        counts[want] += 1
        if want != "Assembly":
            over = overlay_classified_row({"Name": name}, category=want)
            assert over["PartMode"] == part_mode_int(want)
    assert counts["Cad"] >= 8
    assert counts["Linear"] == 3
    assert counts["Assembly"] == 5
    assert counts["Component"] == 0
    assert "Cad:" in " ".join(notes)


def test_28110_nested_names_are_assembly_only():
    """Live 28110-2 first FileList: ASSY/WELDMENT only — not leaf-exploded."""
    from tests.fixtures.live_28110_nested import LIVE_28110_NESTED_NAMES
    from secturafab.website import (
        filelist_is_assembly_only,
        filelist_leaf_noun_names,
        is_nested_assembly_name,
        nested_assembly_id_list,
    )

    rows = [
        {
            "SourceDataID": f"nest-{i}",
            "ID": f"id-{i}",
            "Name": name,
            "Qty": 1,
            "ErrorStatus": 0,
        }
        for i, name in enumerate(LIVE_28110_NESTED_NAMES)
    ]
    assert filelist_is_assembly_only(
        rows, part_key="28110-2", cad_filename="28110-2.STEP"
    )
    assert filelist_leaf_noun_names(
        rows, part_key="28110-2", cad_filename="28110-2.STEP"
    ) == []
    one = [
        {
            "SourceDataID": "w1",
            "Name": "END WELDMENT",
            "Qty": 1,
            "ErrorStatus": 0,
        }
    ]
    assert filelist_is_assembly_only(one, part_key="28110-2")
    assert is_nested_assembly_name("28109 COMP LINK ASSY WITH INSERT-5997_28109-1")
    assert is_nested_assembly_name(
        "28248 COMPLINK END WELDMENT INSULATED-5994_28248-2"
    )
    ids = [sid for sid, _u in nested_assembly_id_list(
        rows, part_key="28110-2", cad_filename="28110-2.STEP"
    )]
    assert "nest-0" not in ids  # Root
    assert "nest-1" not in ids  # job PN is a leaf, not a nest
    assert "nest-2" in ids  # ASSY
    assert classify_sectura_item("28109 COMP LINK ASSY WITH INSERT") == "Assembly"


def test_107877_shared_sourcedataid_still_builds_pass2_idlist():
    """Live 107877-1: child SourceDataID == pass-1 upload id — use ID/FileID."""
    from tests.fixtures.live_107877_nested import LIVE_107877_NESTED_NAMES
    from secturafab.website import (
        filelist_id_fields_present,
        filelist_is_assembly_only,
        filelist_row_explode_id,
        is_unnamed_step_node,
        nested_assembly_id_list,
        overlay_filelist_ids,
    )

    assert is_unnamed_step_node("-28656")
    assert not is_unnamed_step_node("GATE WELDMENT-2640_103535-1")
    rows = [
        {
            "SourceDataID": "src-step",
            "ID": f"id-{i}",
            "FileID": f"file-{i}",
            "Name": name,
            "Qty": 1,
            "ErrorStatus": 0,
        }
        for i, name in enumerate(LIVE_107877_NESTED_NAMES)
    ]
    assert filelist_is_assembly_only(
        rows, part_key="107877-1", cad_filename="107877-1 without floor.STEP"
    )
    used = {"src-step"}
    nested = nested_assembly_id_list(
        rows,
        part_key="107877-1",
        cad_filename="107877-1 without floor.STEP",
        used_ids=used,
    )
    ids = [sid for sid, _u in nested]
    assert ids
    assert "src-step" not in ids
    assert any(x.startswith("id-") for x in ids)
    assert filelist_row_explode_id(rows[1], used_ids=used) == "id-1"
    blob = filelist_id_fields_present(rows)
    assert "SourceDataID:" in blob and "ID:" in blob
    names_only = [
        {"Name": name, "Qty": 1, "ErrorStatus": 0}
        for name in LIVE_107877_NESTED_NAMES
    ]
    empty = nested_assembly_id_list(
        names_only, part_key="107877-1", used_ids=used
    )
    assert empty == []
    filled = overlay_filelist_ids(names_only, rows)
    recovered = nested_assembly_id_list(
        filled, part_key="107877-1", used_ids=used
    )
    assert [sid for sid, _u in recovered]


def test_1020249_job_pn_kids_are_not_nests():
    """Live 1020249-1: 14× job PN after pass 1 must not build a pass-2 IDList."""
    from tests.fixtures.live_1020249_pn_leaves import LIVE_1020249_PN_LEAF_NAMES
    from secturafab.website import (
        filelist_is_assembly_only,
        is_nested_assembly_row,
        nested_assembly_id_list,
    )

    rows = [
        {
            "SourceDataID": "src-step" if i == 0 else f"id-{i}",
            "ID": f"id-{i}",
            "FileID": f"file-{i}",
            "Name": name,
            "Qty": 1,
            "ErrorStatus": 0,
        }
        for i, name in enumerate(LIVE_1020249_PN_LEAF_NAMES)
    ]
    assert not filelist_is_assembly_only(
        rows, part_key="1020249-1", cad_filename="1020249-1.STEP"
    )
    assert not is_nested_assembly_row(
        rows[1], part_key="1020249-1", cad_filename="1020249-1.STEP"
    )
    nested = nested_assembly_id_list(
        rows,
        part_key="1020249-1",
        cad_filename="1020249-1.STEP",
        used_ids={"src-step"},
    )
    assert nested == []


def test_bb2000_asm_nested_names_build_pass2_idlist():
    """Live BB2000-ASM: *ASM / *-ASM re-explode; job-PN leaves do not."""
    from tests.fixtures.live_bb2000_asm import LIVE_BB2000_ASM_NAMES
    from secturafab.website import (
        filelist_is_assembly_only,
        is_nested_assembly_name,
        is_nested_assembly_row,
        nested_assembly_id_list,
    )

    assert len(LIVE_BB2000_ASM_NAMES) == 19
    assert is_nested_assembly_name("BB1000-ASM")
    assert is_nested_assembly_name("BB1010-ASM")
    assert is_nested_assembly_name("BB2000-ASM")
    assert not is_nested_assembly_name("Root")
    assert not is_nested_assembly_name("PLASMA CUT PLATE")
    rows = [
        {
            "SourceDataID": "src-step" if i == 0 else f"id-{i}",
            "ID": f"id-{i}",
            "FileID": f"file-{i}",
            "Name": name,
            "Qty": 1,
            "ErrorStatus": 0,
        }
        for i, name in enumerate(LIVE_BB2000_ASM_NAMES)
    ]
    assert filelist_is_assembly_only(
        rows, part_key="BB2000-ASM", cad_filename="BB2000-ASM.STEP"
    )
    assert not is_nested_assembly_row(
        {"Name": "BB2000-ASM", "ID": "job-pn"},
        part_key="BB2000-ASM",
        cad_filename="BB2000-ASM.STEP",
    )
    assert is_nested_assembly_row(
        {"Name": "BB1000-ASM", "ID": "nest-a"},
        part_key="BB2000-ASM",
        cad_filename="BB2000-ASM.STEP",
    )
    nested = nested_assembly_id_list(
        rows,
        part_key="BB2000-ASM",
        cad_filename="BB2000-ASM.STEP",
        used_ids={"src-step"},
    )
    ids = [sid for sid, _u in nested]
    names_by_id = {f"id-{i}": name for i, name in enumerate(LIVE_BB2000_ASM_NAMES)}
    nest_names = [names_by_id[sid] for sid in ids]
    assert nest_names.count("BB1000-ASM") == 6
    assert nest_names.count("BB1010-ASM") == 2
    assert "BB2000-ASM" not in nest_names
    assert "Root" not in nest_names
    assert classify_sectura_item("BB1000-ASM") == "Assembly"
    assert classify_sectura_item("BB1010-ASM") == "Assembly"


def test_nested_assy_reexplode_then_finish_leaf_filelist(tmp_path: Path):
    """After /part/create, re-explode ASSY/WELDMENT IDs until plate/tube nouns."""
    from tests.fixtures.live_28110_nested import (
        LIVE_28110_LEAF_NAMES,
        LIVE_28110_NESTED_NAMES,
    )

    stp = tmp_path / "28110-2.STEP"
    stp.write_bytes(b"ISO")
    raw = {
        "SourceDataID": "src-step",
        "FileID": "file-step",
        "FileName": "28110-2.STEP",
        "Name": "28110-2.STEP",
        "Qty": 1,
        "ErrorStatus": 0,
        "PartCount": 15,
    }
    nested = [
        {
            "SourceDataID": f"nest-{i}",
            "FileID": f"file-n{i}",
            "Name": name,
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        }
        for i, name in enumerate(LIVE_28110_NESTED_NAMES)
    ]
    leaves = [
        {
            "SourceDataID": f"leaf-{i}",
            "FileID": f"file-l{i}",
            "Name": name,
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        }
        for i, name in enumerate(LIVE_28110_LEAF_NAMES)
    ]
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {"status": "OK", "List": [raw]}
    client._request_verification_fields = [("__RequestVerificationToken", "x")]
    client._af_source = "chrome_dom"
    client.create_dxf_parts.side_effect = [
        {"List": nested},
        {"List": leaves},
    ]
    client.cadimport_data.return_value = {"List": leaves}
    client.get_item_add_view.return_value = {}
    client.quote_item_read.return_value = {
        "Data": [
            {"ProductType": 100, "Description": "LINK PLATE"},
            {"ProductType": 10, "Description": "END TUBE"},
        ],
        "Total": 2,
    }
    client.get_json.return_value = {
        "ItemList": [
            {"ProductType": 100, "Description": "LINK PLATE"},
            {"ProductType": 10, "Description": "END TUBE"},
        ]
    }
    captured: dict[str, Any] = {}

    def _add(**kwargs):
        captured.update(kwargs)
        return {"body_keys": ["List", "Result"], "has_NewItem": True}

    client.add_item_dxf_files.side_effect = _add
    notes = SecturaFabPushService(client=client).finish_cad_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000002811",
        cad_files=[stp],
        material="A36",
        thickness="0.25",
        qty=1,
        takeoff={},
        bom_rows=[],
        library={},
        extra_pdfs=None,
        part_key="28110-2",
        explode_polls=1,
        explode_sleep_s=0,
    )
    assert client.create_dxf_parts.call_count == 2
    first_ids = client.create_dxf_parts.call_args_list[0].args[0]
    second_ids = client.create_dxf_parts.call_args_list[1].args[0]
    assert first_ids == ["src-step"]
    assert "nest-0" not in second_ids
    assert "nest-1" not in second_ids
    assert "nest-2" in second_ids
    client.add_item_dxf_files.assert_called()
    posted_names = {
        str(r.get("Name") or "") for r in captured.get("file_list") or []
    }
    assert "LINK PLATE" in posted_names
    assert "END TUBE" in posted_names
    blob = " ".join(notes)
    assert "explode_passes=2" in blob
    assert "LINK PLATE" in blob
    assert "leaf_names=" in blob


def test_assembly_only_filelist_does_not_finish(tmp_path: Path):
    """Live 28110-2: still ASSY/WELDMENT after re-explode → no Finish."""
    from tests.fixtures.live_28110_nested import LIVE_28110_NESTED_NAMES

    stp = tmp_path / "28110-2.STEP"
    stp.write_bytes(b"ISO")
    raw = {
        "SourceDataID": "src-step",
        "FileID": "file-step",
        "FileName": "28110-2.STEP",
        "Name": "28110-2.STEP",
        "Qty": 1,
        "ErrorStatus": 0,
        "PartCount": 15,
    }
    nested = [
        {
            "SourceDataID": f"nest-{i}",
            "FileID": f"file-n{i}",
            "Name": name,
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        }
        for i, name in enumerate(LIVE_28110_NESTED_NAMES)
    ]
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {"status": "OK", "List": [raw]}
    client._request_verification_fields = [("__RequestVerificationToken", "x")]
    client._af_source = "chrome_dom"
    client.create_dxf_parts.return_value = {"List": nested}
    client.cadimport_data.return_value = {"List": nested}
    client.get_item_add_view.return_value = {}
    client.quote_item_read.return_value = {"Data": [], "Total": 0}
    client.get_json.return_value = {"ItemList": []}
    notes = SecturaFabPushService(client=client).finish_cad_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000002812",
        cad_files=[stp],
        material="A36",
        thickness="0.25",
        qty=1,
        takeoff={},
        bom_rows=[],
        library={},
        extra_pdfs=None,
        part_key="28110-2",
        explode_polls=1,
        explode_sleep_s=0,
    )
    client.add_item_dxf_files.assert_not_called()
    blob = " ".join(notes)
    assert "assembly-only" in blob.lower() or "ASSY/WELDMENT" in blob
    assert "not Finishing" in blob
    assert "want_cad=0 is not a license" in blob
    assert client.create_dxf_parts.call_count >= 2


def test_finish_get_zero_items_is_not_success(tmp_path: Path):
    """Finish 200 + GET ItemList 0 → not success (leave shell, no remint)."""
    stp = tmp_path / "1020249-1.STEP"
    stp.write_bytes(b"ISO")
    kids = [
        {
            "SourceDataID": "src-a",
            "FileID": "file-a",
            "Name": "LINK PLATE",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        },
        {
            "SourceDataID": "src-b",
            "FileID": "file-b",
            "Name": "END TUBE",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        },
    ]
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {"status": "OK", "List": kids}
    client._request_verification_fields = [("__RequestVerificationToken", "x")]
    client._af_source = "chrome_dom"
    client.create_dxf_parts.return_value = {"List": kids}
    client.cadimport_data.return_value = {"List": kids}
    client.get_item_add_view.return_value = {}
    client.quote_item_read.return_value = {"Data": [], "Total": 0}
    client.get_json.return_value = {"ItemList": []}
    client.add_item_dxf_files.return_value = {
        "body_keys": ["List", "Result"],
        "has_NewItem": False,
    }
    notes = SecturaFabPushService(client=client).finish_cad_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000001020",
        cad_files=[stp],
        material="A36",
        thickness="0.25",
        qty=1,
        takeoff={},
        bom_rows=[],
        library={},
        extra_pdfs=None,
        part_key="1020249-1",
        explode_polls=1,
        explode_sleep_s=0,
    )
    client.add_item_dxf_files.assert_called()
    blob = " ".join(notes)
    assert "item_count=0" in blob
    assert "not success" in blob


def test_107877_shared_parent_id_reexplodes_unnamed_and_weldment(tmp_path: Path):
    """Pass 1 kids share upload SourceDataID — pass 2 IDList is child ID/FileID."""
    from tests.fixtures.live_107877_nested import (
        LIVE_107877_LEAF_NAMES,
        LIVE_107877_NESTED_NAMES,
    )

    stp = tmp_path / "107877-1 without floor.STEP"
    stp.write_bytes(b"ISO")
    raw = {
        "SourceDataID": "src-step",
        "FileID": "file-step",
        "FileName": "107877-1 without floor.STEP",
        "Name": "107877-1 without floor.STEP",
        "Qty": 1,
        "ErrorStatus": 0,
        "PartCount": 65,
    }
    nested = [
        {
            "SourceDataID": "src-step",
            "ID": f"id-{i}",
            "FileID": f"file-{i}",
            "Name": name,
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        }
        for i, name in enumerate(LIVE_107877_NESTED_NAMES)
    ]
    leaves = [
        {
            "SourceDataID": "src-step",
            "ID": f"leaf-{i}",
            "FileID": f"fleaf-{i}",
            "Name": name,
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        }
        for i, name in enumerate(LIVE_107877_LEAF_NAMES)
    ]
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {"status": "OK", "List": [raw]}
    client._request_verification_fields = [("__RequestVerificationToken", "x")]
    client._af_source = "chrome_dom"
    client.create_dxf_parts.side_effect = [
        {"List": nested},
        {"List": leaves},
    ]
    client.cadimport_data.return_value = {"List": leaves}
    client.get_item_add_view.return_value = {}
    client.quote_item_read.return_value = {
        "Data": [
            {"ProductType": 100, "Description": "FLOOR PLATE"},
            {"ProductType": 10, "Description": "GATE TUBE"},
        ],
        "Total": 2,
    }
    client.get_json.return_value = {
        "ItemList": [
            {"ProductType": 100, "Description": "FLOOR PLATE"},
            {"ProductType": 10, "Description": "GATE TUBE"},
        ]
    }
    captured: dict[str, Any] = {}

    def _add(**kwargs):
        captured.update(kwargs)
        return {"body_keys": ["List", "Result"], "has_NewItem": True}

    client.add_item_dxf_files.side_effect = _add
    notes = SecturaFabPushService(client=client).finish_cad_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000001078",
        cad_files=[stp],
        material="A36",
        thickness="0.25",
        qty=1,
        takeoff={},
        bom_rows=[],
        library={},
        extra_pdfs=None,
        part_key="107877-1",
        explode_polls=1,
        explode_sleep_s=0,
    )
    assert client.create_dxf_parts.call_count == 2
    first_ids = client.create_dxf_parts.call_args_list[0].args[0]
    second_ids = client.create_dxf_parts.call_args_list[1].args[0]
    assert first_ids == ["src-step"]
    assert "src-step" not in second_ids
    assert any(str(x).startswith("id-") for x in second_ids)
    blob = " ".join(notes)
    assert "explode_passes=2" in blob
    assert "nested_ids_found=" in blob
    assert "id_fields_present=" in blob
    assert "FLOOR PLATE" in blob or "leaf_names=" in blob
    client.add_item_dxf_files.assert_called()
    posted = {str(r.get("Name") or "") for r in captured.get("file_list") or []}
    assert "FLOOR PLATE" in posted
    assert "GATE TUBE" in posted


def test_1020249_pn_leaves_finish_without_pass2(tmp_path: Path):
    """Root + 14× 1020249-1 → one /part/create, then Finish the 15."""
    from tests.fixtures.live_1020249_pn_leaves import LIVE_1020249_PN_LEAF_NAMES

    stp = tmp_path / "1020249-1.STEP"
    stp.write_bytes(b"ISO")
    raw = {
        "SourceDataID": "src-step",
        "FileID": "file-step",
        "FileName": "1020249-1.STEP",
        "Name": "1020249-1.STEP",
        "Qty": 1,
        "ErrorStatus": 0,
        "PartCount": 15,
    }
    kids = [
        {
            "SourceDataID": f"id-{i}",
            "ID": f"id-{i}",
            "FileID": f"file-{i}",
            "Name": name,
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        }
        for i, name in enumerate(LIVE_1020249_PN_LEAF_NAMES)
    ]
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {"status": "OK", "List": [raw]}
    client._request_verification_fields = [("__RequestVerificationToken", "x")]
    client._af_source = "chrome_dom"
    client.create_dxf_parts.return_value = {"List": kids}
    client.cadimport_data.return_value = {"List": kids}
    client.get_item_add_view.return_value = {}
    client.quote_item_read.return_value = {
        "Data": [{"ProductType": 100, "Description": "1020249-1"}],
        "Total": 1,
    }
    client.get_json.return_value = {
        "ItemList": [{"ProductType": 100, "Description": "1020249-1"}]
    }
    captured: dict[str, Any] = {}

    def _add(**kwargs):
        captured.update(kwargs)
        return {"body_keys": ["List", "Result"], "has_NewItem": True}

    client.add_item_dxf_files.side_effect = _add
    notes = SecturaFabPushService(client=client).finish_cad_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000001020",
        cad_files=[stp],
        material="A36",
        thickness="0.25",
        qty=1,
        takeoff={},
        bom_rows=[{"part_no": "14500-1", "description": "PEDESTAL TOP PLATE", "qty": 1}],
        library={},
        extra_pdfs=None,
        part_key="1020249-1",
        explode_polls=1,
        explode_sleep_s=0,
    )
    assert client.create_dxf_parts.call_count == 1
    client.add_item_dxf_files.assert_called()
    blob = " ".join(notes)
    assert "explode_passes=1" in blob
    posted = captured.get("file_list") or []
    assert len(posted) >= 2
    cats = {str(r.get("Category") or "") for r in posted}
    assert "Assembly" not in cats or any(
        str(r.get("Name") or "") != "1020249-1" for r in posted if r.get("Category") == "Assembly"
    )
    assert any(str(r.get("Category") or "") == "Cad" for r in posted)


def test_empty_pass2_keeps_prior_grid(tmp_path: Path):
    """If pass-2 List=0, keep the 15 kids — not the 34632-2 first-pass abort."""
    from tests.fixtures.live_107877_nested import LIVE_107877_NESTED_NAMES

    stp = tmp_path / "107877-1.STEP"
    stp.write_bytes(b"ISO")
    raw = {
        "SourceDataID": "src-step",
        "FileID": "file-step",
        "FileName": "107877-1.STEP",
        "Name": "107877-1.STEP",
        "Qty": 1,
        "ErrorStatus": 0,
        "PartCount": 15,
    }
    nested = [
        {
            "SourceDataID": f"id-{i}",
            "ID": f"id-{i}",
            "FileID": f"file-{i}",
            "Name": name,
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        }
        for i, name in enumerate(LIVE_107877_NESTED_NAMES)
    ]
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {"status": "OK", "List": [raw]}
    client._request_verification_fields = [("__RequestVerificationToken", "x")]
    client._af_source = "chrome_dom"
    client.create_dxf_parts.side_effect = [
        {"List": nested},
        {"List": []},
    ]
    client.cadimport_data.return_value = {"List": nested}
    client.get_item_add_view.return_value = {}
    client.quote_item_read.return_value = {"Data": [], "Total": 0}
    client.get_json.return_value = {"ItemList": []}
    notes = SecturaFabPushService(client=client).finish_cad_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000001078",
        cad_files=[stp],
        material="A36",
        thickness="0.25",
        qty=1,
        takeoff={},
        bom_rows=[],
        library={},
        extra_pdfs=None,
        part_key="107877-1",
        explode_polls=1,
        explode_sleep_s=0,
    )
    assert client.create_dxf_parts.call_count == 2
    blob = " ".join(notes)
    assert "kept_prior_grid=true" in blob
    assert "34632-2" not in blob


def test_explode_skips_cookie_quote_html_even_when_fields_present(tmp_path: Path):
    """cookie_quote_html is the wrong claims user — no /part/create."""
    stp = tmp_path / "34997-1.STEP"
    stp.write_bytes(b"ISO")
    raw = {
        "SourceDataID": "src-step",
        "FileID": "file-step",
        "FileName": "34997-1.STEP",
        "Name": "34997-1",
        "Qty": 1,
        "ErrorStatus": 0,
        "PartCount": 4,
        "Units": "inch",
    }
    token = "af-secret-token-value"
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {"status": "OK", "List": [raw]}
    client._request_verification_fields = [("__RequestVerificationToken", token)]
    client._request_verification_token = token
    client._af_source = "cookie_quote_html"
    client._quotes_tab_live = True
    client.cadimport_data.return_value = {"List": [raw]}
    client.get_item_add_view.return_value = {}
    client.quote_item_read.return_value = {"Data": [], "Total": 0}
    client.get_json.return_value = {"ItemList": []}
    notes = SecturaFabPushService(client=client).finish_cad_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000003497",
        cad_files=[stp],
        material="A36",
        thickness="0.25",
        qty=1,
        takeoff={},
        bom_rows=[],
        library={},
        extra_pdfs=None,
        part_key="34997-1",
        explode_polls=1,
        explode_sleep_s=0,
    )
    blob = " ".join(notes)
    client.create_dxf_parts.assert_not_called()
    client.add_item_dxf_files.assert_not_called()
    assert "cookie_quote_html is the wrong" in blob
    assert "no cookie HTTP /part/create" in blob
    assert token not in blob


def test_quotes_tab_skips_login_and_claims_mismatch():
    from secturafab.chrome_cdp import quotes_tab

    tabs = [
        {
            "type": "page",
            "title": "Login",
            "url": "https://www.secturafab.com/Account/Login",
            "webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/page/login",
        },
        {
            "type": "page",
            "title": (
                "The provided anti-forgery token was meant for a different "
                "claims-based user than"
            ),
            "url": "https://www.secturafab.com/Quote",
            "webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/page/claims",
        },
        {
            "type": "page",
            "title": "Quotes",
            "url": "https://www.secturafab.com/Quote",
            "webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/page/quotes",
        },
    ]
    with patch("secturafab.chrome_cdp.list_chrome_targets", return_value=tabs):
        tab = quotes_tab("http://127.0.0.1:9224")
    assert tab is not None
    assert tab["title"] == "Quotes"
    assert tab["webSocketDebuggerUrl"].endswith("/quotes")


def test_quote_edit_tab_matches_star_quote_title_and_edit_url():
    """Live a64509d: QuoteOrderEdit is *Quote-{PN} on /Quote/EDIT/{id}."""
    from secturafab.chrome_cdp import (
        chrome_quotes_live,
        quote_edit_tab,
        quotes_tab,
    )

    listing = {
        "type": "page",
        "title": "Quotes",
        "url": "https://www.secturafab.com/Quote",
        "webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/page/quotes",
    }
    edit = {
        "type": "page",
        "title": "*Quote-106386-1",
        "url": (
            "https://www.secturafab.com/Quote/EDIT/"
            "a6ef6891-e080-45de-b57c-1a55fee00c19"
        ),
        "webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/page/edit",
    }
    addview = {
        "type": "page",
        "title": "Quote",
        "url": (
            "https://www.secturafab.com/Quote/GetItem_AddView/"
            "a6ef6891-e080-45de-b57c-1a55fee00c19"
        ),
        "webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/page/addview",
    }
    with patch("secturafab.chrome_cdp.list_chrome_targets", return_value=[listing, edit, addview]):
        assert quotes_tab("http://127.0.0.1:9224")["title"] == "Quotes"
        picked = quote_edit_tab(
            "http://127.0.0.1:9224",
            quote_id="a6ef6891-e080-45de-b57c-1a55fee00c19",
            quote_number="106386-1",
        )
        assert picked is not None
        assert picked["webSocketDebuggerUrl"].endswith("/edit")
        assert picked["title"] == "*Quote-106386-1"


def test_chrome_quotes_live_when_only_quote_edit_tab():
    """Session is live if Kyle has /Quote/EDIT open — do not require title Quotes."""
    from secturafab.chrome_cdp import chrome_quotes_live, quote_edit_tab, quotes_tab

    edit = {
        "type": "page",
        "title": "*Quote-106386-1",
        "url": "https://www.secturafab.com/Quote/EDIT/qid",
        "webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/page/edit",
    }
    with patch("secturafab.chrome_cdp.list_chrome_targets", return_value=[edit]), patch(
        "secturafab.chrome_cdp.chrome_debug_bases", return_value=["http://127.0.0.1:9224"]
    ):
        assert quotes_tab("http://127.0.0.1:9224") is edit
        assert quote_edit_tab("http://127.0.0.1:9224") is edit
        assert chrome_quotes_live("http://127.0.0.1:9224") is True


def test_quote_edit_tab_skips_getitem_addview_and_login():
    from secturafab.chrome_cdp import quote_edit_tab, quotes_tab

    tabs = [
        {
            "type": "page",
            "title": "Login",
            "url": "https://www.secturafab.com/Quote/EDIT/qid",
            "webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/page/login",
        },
        {
            "type": "page",
            "title": "*Quote-106386-1",
            "url": "https://www.secturafab.com/Quote/GetItem_AddView/qid",
            "webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/page/addview",
        },
    ]
    with patch("secturafab.chrome_cdp.list_chrome_targets", return_value=tabs):
        assert quote_edit_tab("http://127.0.0.1:9224") is None
        assert quotes_tab("http://127.0.0.1:9224") is None


def test_bind_evaluates_on_quote_edit_not_list_tab():
    """Bind must use /Quote/EDIT even when the Quotes list tab is also open."""
    from secturafab.chrome_cdp import bind_do_create_dxf_parts_success

    listing = {
        "title": "Quotes",
        "url": "https://www.secturafab.com/Quote",
        "webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/page/quotes",
        "type": "page",
    }
    edit = {
        "title": "*Quote-106386-1",
        "url": "https://www.secturafab.com/Quote/EDIT/qid",
        "webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/page/edit",
        "type": "page",
    }

    def _call(ws_url, method, params=None, **kwargs):
        assert method == "Runtime.evaluate"
        assert ws_url.endswith("/edit")
        assert "/quotes" not in ws_url
        return {
            "result": {
                "value": {
                    "grid_present": True,
                    "has_gridDXFParts": True,
                    "grid_dxf_row_count": 26,
                    "bound": True,
                    "list_len": 26,
                    "opened_via": "but_dxf",
                }
            }
        }

    with patch("secturafab.chrome_cdp.quote_edit_tab", return_value=edit), patch(
        "secturafab.chrome_cdp.quotes_tab", return_value=listing
    ), patch("secturafab.chrome_cdp.cdp_call", side_effect=_call):
        result = bind_do_create_dxf_parts_success(
            [{"SourceDataID": "a"}, {"SourceDataID": "b"}],
            quote_id="qid",
        )
    assert result["grid_present"] is True
    assert result["grid_dxf_row_count"] == 26
    assert result["opened_via"] == "but_dxf"


def test_ensure_quote_edit_navigates_edit_path_not_quote_query():
    """Live a64509d: /Quote?ID= is the list. Open /Quote/EDIT/{id}."""
    from secturafab.chrome_cdp import _ensure_quote_edit_page, _quote_edit_url

    qid = "a6ef6891-e080-45de-b57c-1a55fee00c19"
    listing = {
        "title": "Quotes",
        "url": "https://www.secturafab.com/Quote",
        "webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/page/quotes",
        "type": "page",
    }
    navigated: list[str] = []

    def _call(ws_url, method, params=None, **kwargs):
        if method == "Page.navigate":
            navigated.append(str((params or {}).get("url") or ""))
            return {}
        return {"result": {"value": {"edit_quote_id": qid, "ok": True}}}

    assert _quote_edit_url(qid) == f"https://www.secturafab.com/Quote/EDIT/{qid}"
    with patch("secturafab.chrome_cdp.quote_edit_tab", return_value=None), patch(
        "secturafab.chrome_cdp.quotes_tab", return_value=listing
    ), patch("secturafab.chrome_cdp.cdp_call", side_effect=_call):
        tab = _ensure_quote_edit_page(qid)
    assert tab is not None
    assert tab["webSocketDebuggerUrl"] == listing["webSocketDebuggerUrl"]
    assert tab["url"] == f"https://www.secturafab.com/Quote/EDIT/{qid}"
    assert navigated == [f"https://www.secturafab.com/Quote/EDIT/{qid}"]
    assert "Quote?ID=" not in navigated[0]
    assert "GetItem_AddView" not in navigated[0]


def test_quote_edit_tab_does_not_return_leftover_when_id_requested():
    """Live 5003313-001: leftover /Quote/EDIT/997f1eb7 is not the minted tab."""
    from secturafab.chrome_cdp import edit_tab_quote_id, quote_edit_tab

    minted = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0001"
    leftover_id = "997f1eb7-3eb0-4a76-83f9-4c3439e929b7"
    leftover = {
        "type": "page",
        "title": "*Quote-105918-1",
        "url": f"https://www.secturafab.com/Quote/EDIT/{leftover_id}",
        "webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/page/leftover",
    }
    with patch("secturafab.chrome_cdp.list_chrome_targets", return_value=[leftover]):
        assert quote_edit_tab("http://127.0.0.1:9224", quote_id=minted) is None
        picked = quote_edit_tab("http://127.0.0.1:9224")
        assert picked is leftover
        assert edit_tab_quote_id(picked) == leftover_id


def test_leftover_edit_tab_does_not_bind_or_finish():
    """Minted A, Chrome still EDIT/B → no #but_dxf and no AddItem_DXFFiles POST."""
    from secturafab.chrome_cdp import (
        bind_do_create_dxf_parts_success,
        invoke_page_dxf_finish,
    )

    minted = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0001"
    leftover_id = "997f1eb7-3eb0-4a76-83f9-4c3439e929b7"
    leftover = {
        "type": "page",
        "title": "*Quote-105918-1",
        "url": f"https://www.secturafab.com/Quote/EDIT/{leftover_id}",
        "webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/page/leftover",
    }
    exprs: list[str] = []

    def fake_edit(base=None, quote_id=None, quote_number=None):
        qid = str(quote_id or "").strip().lower()
        if qid and qid in leftover["url"].lower():
            return leftover
        if qid:
            return None
        return leftover

    def _call(ws_url, method, params=None, **kwargs):
        expr = str((params or {}).get("expression") or "")
        exprs.append(expr)
        if method == "Page.navigate":
            return {}
        return {
            "result": {
                "value": {"edit_quote_id": leftover_id, "ok": False}
            }
        }

    kids = [{"SourceDataID": "a", "Name": "5003313-001"}] * 12
    with patch("secturafab.chrome_cdp.quote_edit_tab", side_effect=fake_edit), patch(
        "secturafab.chrome_cdp.quotes_tab", return_value=leftover
    ), patch("secturafab.chrome_cdp.cdp_call", side_effect=_call):
        bound = bind_do_create_dxf_parts_success(kids, quote_id=minted)
        finished = invoke_page_dxf_finish(quote_id=minted)
    assert bound["bound"] is False
    assert bound["grid_present"] is False
    assert bound["edit_quote_id"] == leftover_id
    assert bound["minted_id"] == minted
    assert bound["edit_gate"]
    assert finished["via"] == "skipped"
    assert finished["status"] == 0
    assert finished["edit_quote_id"] == leftover_id
    assert finished["minted_id"] == minted
    blob = "\n".join(exprs)
    assert "#but_dxf" not in blob
    assert "AddItem_DXFFiles" not in blob
    assert "AddNewItemHTML" not in blob


def test_add_item_dxf_files_leftover_edit_does_not_post():
    """add_item_dxf_files must not POST Finish when the tab is still spent EDIT."""
    from secturafab.client import SecturaFabClient

    minted = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0001"
    leftover_id = "997f1eb7-3eb0-4a76-83f9-4c3439e929b7"
    leftover = {
        "type": "page",
        "title": "*Quote-105918-1",
        "url": f"https://www.secturafab.com/Quote/EDIT/{leftover_id}",
        "webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/page/leftover",
    }
    real = SecturaFabClient.__new__(SecturaFabClient)
    real.config = MagicMock()
    real.config.timeout_seconds = 30
    real._af_source = "chrome_dom"
    real._part_create_list_len = 12
    real._grid_present = True
    real._grid_dxf_row_count = 12
    real._stale_grid = False
    real.session = MagicMock()

    def fake_edit(base=None, quote_id=None, quote_number=None):
        qid = str(quote_id or "").strip().lower()
        if qid and qid in leftover["url"].lower():
            return leftover
        if qid:
            return None
        return leftover

    def _call(ws_url, method, params=None, **kwargs):
        expr = str((params or {}).get("expression") or "")
        if "AddItem_DXFFiles" in expr:
            raise AssertionError("must not POST AddItem_DXFFiles on leftover EDIT")
        if method == "Page.navigate":
            return {}
        return {
            "result": {
                "value": {"edit_quote_id": leftover_id, "ok": False}
            }
        }

    with patch(
        "secturafab.chrome_cdp.chrome_quotes_live", return_value=True
    ), patch(
        "secturafab.client.SecturaFabClient.harvest_chrome_antiforgery",
        return_value="chrome_dom",
    ), patch(
        "secturafab.chrome_cdp.quote_edit_tab", side_effect=fake_edit
    ), patch(
        "secturafab.chrome_cdp.quotes_tab", return_value=leftover
    ), patch(
        "secturafab.chrome_cdp.cdp_call", side_effect=_call
    ), patch(
        "secturafab.chrome_cdp.post_add_item_dxf_files_from_quotes_tab",
    ) as fetch_finish:
        result = real.add_item_dxf_files(
            quote_id=minted,
            file_list=[{"Name": "5003313-001", "Qty": 1}] * 12,
        )
    real.session.request.assert_not_called()
    fetch_finish.assert_not_called()
    assert result["via"] == "skipped"
    assert real._finish_via == "skipped"
    assert real._edit_quote_id == leftover_id
    assert real._minted_id == minted


def test_reconstructed_filelist_is_not_page_grid_finish():
    """EDIT-id match + grid==FileList + reconstructed POST → still not success."""
    from secturafab.client import SecturaFabClient

    minted = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0545"
    edit = {
        "title": "*Quote-P001545",
        "url": f"https://www.secturafab.com/Quote/EDIT/{minted}",
        "webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/page/edit",
        "type": "page",
    }
    real = SecturaFabClient.__new__(SecturaFabClient)
    real.config = MagicMock()
    real.config.timeout_seconds = 30
    real._af_source = "chrome_dom"
    real._part_create_list_len = 53
    real._grid_present = True
    real._grid_dxf_row_count = 53
    real._stale_grid = False
    real.session = MagicMock()
    rebuilt = [{"Name": f"W001544-{i}", "Qty": 1, "ErrorStatus": 0} for i in range(52)]

    with patch(
        "secturafab.chrome_cdp.chrome_quotes_live", return_value=True
    ), patch(
        "secturafab.client.SecturaFabClient.harvest_chrome_antiforgery",
        return_value="chrome_dom",
    ), patch(
        "secturafab.chrome_cdp.quote_edit_tab", return_value=edit
    ), patch(
        "secturafab.chrome_cdp.invoke_page_dxf_finish",
        return_value={
            "via": "",
            "finish_fn": "",
            "grid_dxf_row_count": 53,
            "finish_filelist_n": 0,
            "status": 0,
            "body_keys": [],
            "body_type": "empty",
            "has_NewItem": False,
            "has_QuoteItem": False,
            "text_len": 0,
            "List": rebuilt,
        },
    ), patch(
        "secturafab.chrome_cdp.post_add_item_dxf_files_from_quotes_tab",
    ) as fetch_finish:
        result = real.add_item_dxf_files(quote_id=minted, file_list=rebuilt)
    real.session.request.assert_not_called()
    fetch_finish.assert_not_called()
    assert result["via"] == "skipped"
    assert real._finish_via == "skipped"


def test_bb2000_edit_match_skip_finish_fails_fixture():
    """EDIT match + grid==filelist + skip-Finish is a fail — must call page fn."""
    from secturafab.chrome_cdp import (
        _PAGE_FINISH_JS,
        page_finish_skip_after_edit_match_is_fail,
    )
    from secturafab.client import SecturaFabClient

    spent = "a9497a26-cba8-4ec9-a849-cb8bef81cbcc"
    assert page_finish_skip_after_edit_match_is_fail(
        edit_quote_id=spent,
        minted_id=spent,
        grid_n=19,
        filelist_n=19,
        via="skipped",
    ) is True
    js = _PAGE_FINISH_JS
    find_body = js.split("function findFinishName")[1].split("var finishName")[0]
    assert "OnAddDXFClick" in find_body
    assert "typeof window[preferred[i]] === \"function\"" in find_body
    assert "gridDXFParts" not in find_body
    assert "via: \"page_fn\"" in js.split("if (!hit)")[1]
    minted = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa2000"
    real = SecturaFabClient.__new__(SecturaFabClient)
    real.config = MagicMock()
    real.config.timeout_seconds = 30
    real._af_source = "chrome_dom"
    real._part_create_list_len = 19
    real._grid_present = True
    real._grid_dxf_row_count = 19
    real._stale_grid = False
    real.session = MagicMock()
    with patch(
        "secturafab.chrome_cdp.chrome_quotes_live", return_value=True
    ), patch(
        "secturafab.client.SecturaFabClient.harvest_chrome_antiforgery",
        return_value="chrome_dom",
    ), patch(
        "secturafab.chrome_cdp.minted_edit_tab_ready",
        return_value={
            "ok": True,
            "edit_quote_id": minted,
            "minted_id": minted,
            "reason": "",
        },
    ), patch(
        "secturafab.chrome_cdp.invoke_page_dxf_finish",
        return_value={
            "via": "page_fn",
            "finish_fn": "OnAddDXFClick",
            "reads_kendo": False,
            "grid_dxf_row_count": 19,
            "finish_filelist_n": 19,
            "status": 200,
            "body_keys": [],
            "body_type": "empty",
            "has_NewItem": False,
            "has_QuoteItem": False,
            "text_len": 0,
            "empty_body": True,
            "request_keys": ["ID", "ItemID", "customerMaterial", "FileList"],
        },
    ), patch(
        "secturafab.chrome_cdp.post_add_item_dxf_files_from_quotes_tab",
    ) as fetch_finish:
        result = real.add_item_dxf_files(
            quote_id=minted,
            file_list=[{"Name": "PYTHON_REBUILT", "Qty": 1}] * 18,
        )
    real.session.request.assert_not_called()
    fetch_finish.assert_not_called()
    assert result["via"] == "page_fn"
    assert result["finish_fn"] == "OnAddDXFClick"
    assert result["reads_kendo"] is False
    assert result["empty_body"] is True
    assert result["has_NewItem"] is False
    assert not page_finish_skip_after_edit_match_is_fail(
        edit_quote_id=minted,
        minted_id=minted,
        grid_n=19,
        filelist_n=19,
        via=result["via"],
    )
    assert page_finish_skip_after_edit_match_is_fail(
        edit_quote_id=minted,
        minted_id=minted,
        grid_n=1,
        filelist_n=1,
        via="skipped",
    ) is True


def test_page_finish_js_posts_kendo_filelist_with_chrome_dom_af():
    """OnAddDXFClick FileList must be EDIT kendo + chrome_dom AF (live 11796-1)."""
    from secturafab.chrome_cdp import _PAGE_FINISH_JS

    js = _PAGE_FINISH_JS
    assert "if (count < 1)" in js
    assert "count <= 1" not in js
    assert "opts.data.FileList = krows" in js
    assert "dataSource.data()" in js
    assert "r.SourceDataID = id" in js
    assert "sidEmpty(r.SourceDataID)" in js
    assert "attachChromeDomAf" in js
    assert "hasChromeDomAf" in js
    assert "sid_n === n" in js
    assert "filelist_missing_ids" in js
    assert "finish_why" in js
    assert "wrong_document" in js
    assert "empty_dataSource" in js
    assert "filelist_not_kendo" in js
    assert "af_missing_on_document" in js
    assert "af_not_in_request" in js
    assert "orig.apply(this, arguments)" in js.split("attachChromeDomAf(opts.data)")[1]


def test_filelist_row_keys_name_cadimport_identity_miss():
    """Log posted FileList key names. Live 16629-1 miss is FileType (not CadType/Stock)."""
    from secturafab.chrome_cdp import _PAGE_FINISH_JS
    from secturafab.website import (
        filelist_missing_cadimport_identity_keys,
        filelist_missing_compare_keys,
        filelist_posted_row_keys,
    )

    leftover = {
        "ID": "x",
        "FileID": "f",
        "SourceDataID": "x",
        "FileType": "Cad",
        "Name": "OPERATOR PLATFORM LOWER CONTROL MOUNT",
    }
    keys = filelist_posted_row_keys(leftover)
    assert "SourceDataID" in keys
    assert "FileType" in keys
    assert filelist_missing_cadimport_identity_keys(keys) == [
        "CadType",
        "Stock_X",
        "Stock_Y",
    ]
    gold = {
        **leftover,
        "CadType": 0,
        "Stock_X": 11.0,
        "Stock_Y": 6.25,
        "Status": 0,
        "Thickness": 0.105,
        "Material": "A1011",
        "Width": 11.0,
        "Length": 6.25,
    }
    assert filelist_missing_cadimport_identity_keys(filelist_posted_row_keys(gold)) == []
    assert "CadType" not in filelist_missing_compare_keys(filelist_posted_row_keys(gold))
    js = _PAGE_FINISH_JS
    assert "filelist_row_keys" in js
    assert "filelist_missing_keys" in js
    assert "CadType" in js
    assert "Stock_X" in js
    assert "filelist_missing_keys=" in js
    assert "keepIdentity" in js
    assert "persistFileType" in js
    assert "IDENTITY_KEYS" in js


def test_kendo_row_id_copied_to_sourcedataid():
    """Live 11796-2: kendo {ID: x, FileType: Cad} posts SourceDataID x.

    CadType/Stock_* are still required to Finish — ID copy alone is not gold.
    """
    from secturafab.website import kendo_filelist_for_finish

    cap = kendo_filelist_for_finish(
        [{"ID": "x", "FileType": "Cad"}],
        from_datasource=True,
    )
    assert cap["FileList"][0]["SourceDataID"] == "x"
    assert cap["filelist_from_kendo"] is True
    assert cap["filelist_sourcedataid_n"] == 1
    assert cap["filelist_id_n"] == 1
    assert cap["finish_filelist_n"] == 1
    assert cap["should_finish"] is False
    assert cap["finish_why"] == "filelist_missing_keys=CadType+Stock_X+Stock_Y"
    zero = kendo_filelist_for_finish(
        [{"SourceDataID": 0, "FileType": "Cad"}],
        from_datasource=True,
    )
    assert zero["filelist_from_kendo"] is False
    assert zero["filelist_sourcedataid_n"] == 0
    assert zero["should_finish"] is False
    assert zero["finish_why"] == "filelist_missing_ids"


def test_kendo_cadimport_identity_survives_into_filelist():
    """kendo CadType+Stock_X+Stock_Y must remain on the posted FileList."""
    from secturafab.website import (
        copy_cadimport_identity_through,
        kendo_filelist_for_finish,
    )

    src = {
        "ID": "x",
        "FileType": "Cad",
        "CadType": 0,
        "Stock_X": 11.0,
        "Stock_Y": 6.25,
        "Name": "OPERATOR PLATFORM LOWER CONTROL MOUNT",
    }
    cap = kendo_filelist_for_finish([src], from_datasource=True)
    posted = cap["FileList"][0]
    assert posted["SourceDataID"] == "x"
    assert posted["CadType"] == 0
    assert posted["Stock_X"] == 11.0
    assert posted["Stock_Y"] == 6.25
    assert cap["should_finish"] is True
    assert cap["finish_why"] == ""
    assert cap["filelist_missing_identity"] == []
    assert "CadType" in cap["kendo_row_keys"]
    assert "Stock_X" in cap["kendo_row_keys"]
    dropped = {"ID": "x", "FileType": "Cad", "SourceDataID": "x"}
    kept = copy_cadimport_identity_through(src, dropped)
    assert kept["CadType"] == 0
    assert kept["Stock_X"] == 11.0
    assert kept["Stock_Y"] == 6.25
    invented = copy_cadimport_identity_through({"ID": "x", "FileType": "Cad"}, {})
    assert "CadType" not in invented
    assert "Stock_X" not in invented
    assert "Stock_Y" not in invented


def test_setpartmode_filetype_survives_into_filelist():
    """SetPartMode ItemType/Category must become posted FileType. Do not invent Status."""
    from secturafab.website import (
        kendo_filelist_for_finish,
        persist_setpartmode_filetype,
    )

    src = {
        "ID": "x",
        "CadType": 0,
        "Stock_X": 11.0,
        "Stock_Y": 6.25,
        "ItemType": "Cad",
        "Category": "Cad",
        "PartMode": 0,
        "Name": "EAR",
    }
    cap = kendo_filelist_for_finish([src], from_datasource=True)
    posted = cap["FileList"][0]
    assert posted["FileType"] == "Cad"
    assert posted["CadType"] == 0
    assert posted["Stock_X"] == 11.0
    assert "Status" not in posted
    assert cap["should_finish"] is True
    bare = persist_setpartmode_filetype({"CadType": 0, "Stock_X": 1, "Stock_Y": 2})
    assert "FileType" not in bare
    assert "Status" not in bare
    page = persist_setpartmode_filetype(
        {"FileType": "Cad", "ItemType": "Cad", "ProductType": 100}
    )
    assert page["FileType"] == "Cad"
    assert page["FileType"] != "CAD"
    assert page["FileType"] != 100
    assert persist_setpartmode_filetype({"FileType": "Cad"})["FileType"] == "Cad"
    assert "FileType" not in persist_setpartmode_filetype({"ItemType": "CAD"})
    assert persist_setpartmode_filetype({"FileType": 100}).get("FileType") == 100


def test_filelist_errorstatus_qty_and_filetype_value_type():
    """Log posted ErrorStatus/Qty values and FileType value/type — do not invent."""
    from secturafab.chrome_cdp import _PAGE_FINISH_JS
    from secturafab.website import (
        filelist_cad_path_keys,
        filelist_errorstatus_qty,
        filelist_filetype_value_type,
        kendo_filelist_for_finish,
    )

    row = {
        "ID": "x",
        "FileID": "f",
        "SourceDataID": "x",
        "FileType": "Cad",
        "CadType": 0,
        "Stock_X": 11.0,
        "Stock_Y": 6.25,
        "ErrorStatus": 0,
        "Qty": 1,
        "ItemType": "Cad",
        "Name": "PIVOTING FOOT",
    }
    vals = filelist_errorstatus_qty(row)
    assert vals["filelist_errorstatus"] == 0
    assert vals["filelist_qty"] == 1
    ft = filelist_filetype_value_type(row)
    assert ft["filelist_filetype_value"] == "Cad"
    assert ft["filelist_filetype_type"] == "str"
    assert filelist_cad_path_keys(row) == []
    missing = filelist_filetype_value_type({"Qty": 1})
    assert missing["filelist_filetype_type"] == "missing"
    cap = kendo_filelist_for_finish([row], from_datasource=True)
    assert cap["filelist_errorstatus"] == 0
    assert cap["filelist_qty"] == 1
    assert cap["filelist_filetype_value"] == "Cad"
    assert cap["filelist_filetype_type"] == "str"
    assert cap["filelist_cad_path_keys"] == []
    assert cap["should_finish"] is True
    js = _PAGE_FINISH_JS
    assert "filelist_errorstatus" in js
    assert "filelist_qty" in js
    assert "filelist_filetype_value" in js
    assert "filelist_filetype_type" in js
    assert "InternalData" in js
    assert "Unfold" in js


def test_kendo_without_cadimport_identity_skips_finish(tmp_path: Path):
    """kendo without CadType/Stock_* after explode → bind miss, no Finish."""
    stp = tmp_path / "107292-1.STEP"
    stp.write_bytes(b"ISO")
    kids = [
        {
            "SourceDataID": "src-1",
            "FileID": "file-1",
            "ID": "id-1",
            "Name": "OPERATOR PLATFORM LOWER CONTROL MOUNT",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
            "Category": "Cad",
            "FileType": "Cad",
            "PartMode": 0,
        }
    ]
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {"status": "OK", "List": kids}
    client._request_verification_fields = [("__RequestVerificationToken", "x")]
    client._af_source = "chrome_dom"
    client._part_create_list_len = 1
    client._grid_present = True
    client._grid_dxf_row_count = 1
    client._stale_grid = False
    client._kendo_row_keys = ["FileID", "FileType", "ID", "SourceDataID"]
    client._edit_quote_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0002"
    client._edit_gate = ""
    client._finish_via = ""
    client._setpartmode_via = "page_fn"
    client.create_dxf_parts.return_value = {"List": kids}
    client.cadimport_data.return_value = {"List": kids}
    client.get_item_add_view.return_value = {}
    client.quote_item_read.return_value = {"Data": [], "Total": 0}
    client.get_json.return_value = {"ItemList": []}
    with patch(
        "secturafab.chrome_cdp.apply_grid_dxf_part_modes",
        return_value={
            "grid_present": True,
            "cad": 1,
            "linear": 0,
            "assembly": 0,
            "component": 0,
            "set_count": 1,
            "setpartmode_via": "page_fn",
            "grid_dxf_row_count": 1,
            "kendo_row_keys": ["FileID", "FileType", "ID", "SourceDataID"],
        },
    ):
        notes = SecturaFabPushService(client=client).finish_cad_files(
            quote_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0002",
            cad_files=[stp],
            material="A36",
            thickness="0.105",
            qty=1,
            takeoff={},
            bom_rows=[],
            library={},
            extra_pdfs=None,
            part_key="107292-1",
            explode_polls=1,
            explode_sleep_s=0,
        )
    client.add_item_dxf_files.assert_not_called()
    blob = " ".join(notes)
    assert "kendo_row_keys=" in blob
    assert "filelist_missing_keys=CadType,Stock_X,Stock_Y" in blob or (
        "filelist_missing_keys=" in blob
        and "CadType" in blob
        and "Stock_X" in blob
        and "Stock_Y" in blob
    )
    assert "bind miss" in blob
    assert "not Finishing" in blob
    assert "OPERATOR PLATFORM LOWER CONTROL MOUNT" in blob or "107292-1" in blob


def test_empty_griddxf_explode_miss_n1_cad_is_not_34632():
    """1 Cad on EDIT is Finishable; empty/missing #gridDXFParts is the 34632-2 miss."""
    from secturafab.website import empty_griddxf_explode_miss

    assert empty_griddxf_explode_miss(
        grid_present=True, n_grid=1, n_list=1
    ) is False
    assert empty_griddxf_explode_miss(n_grid=1) is False
    assert empty_griddxf_explode_miss(
        grid_present=True, n_grid=0, n_list=0
    ) is True
    assert empty_griddxf_explode_miss(n_list=0) is True
    assert empty_griddxf_explode_miss(
        grid_present=False, n_grid=1, n_list=1
    ) is True


def test_onadddxfclick_without_setpartmode_is_not_success(tmp_path: Path):
    """Live EHB3112: OnAddDXFClick without SetPartMode is not success."""
    stp = tmp_path / "EHB3112.STEP"
    stp.write_bytes(b"ISO")
    kids = [
        {
            "SourceDataID": f"src-{i}",
            "FileID": f"file-{i}",
            "Name": name,
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        }
        for i, name in enumerate(
            ("EHB3111-1", "EHB3111-2", "EHB3111-2", "EHB3112-3")
        )
    ]
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {"status": "OK", "List": kids}
    client._request_verification_fields = [("__RequestVerificationToken", "x")]
    client._af_source = "chrome_dom"
    client._part_create_list_len = 4
    client._grid_present = True
    client._grid_dxf_row_count = 4
    client._stale_grid = False
    client._edit_quote_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa3112"
    client._edit_gate = ""
    client._finish_via = "page_fn"
    client._setpartmode_via = ""
    client.create_dxf_parts.return_value = {"List": kids}
    client.cadimport_data.return_value = {"List": kids}
    client.get_item_add_view.return_value = {}
    client.add_item_dxf_files.return_value = {
        "status": 200,
        "body_keys": [],
        "body_type": "empty",
        "has_NewItem": False,
        "has_QuoteItem": False,
        "text_len": 0,
        "empty_body": True,
        "via": "page_fn",
        "finish_fn": "OnAddDXFClick",
        "finish_filelist_n": 4,
        "grid_dxf_row_count": 4,
        "filelist_from_kendo": True,
        "filelist_sourcedataid_n": 4,
        "filelist_filetype": {
            "Cad": 0,
            "Linear": 0,
            "Assembly": 0,
            "Component": 0,
            "blank": 4,
        },
        "finish_af_present": True,
        "request_keys": ["ID", "ItemID", "customerMaterial", "FileList"],
    }
    client.quote_item_read.return_value = {"Data": [], "Total": 0}
    client.get_json.return_value = {"ItemList": []}
    with patch(
        "secturafab.chrome_cdp.apply_grid_dxf_part_modes",
        return_value={
            "grid_present": False,
            "cad": 0,
            "linear": 0,
            "assembly": 0,
            "component": 0,
            "set_count": 0,
            "setpartmode_via": "",
            "grid_dxf_row_count": 4,
        },
    ):
        notes = SecturaFabPushService(client=client).finish_cad_files(
            quote_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa3112",
            cad_files=[stp],
            material="A36",
            thickness="0.25",
            qty=1,
            takeoff={},
            bom_rows=[],
            library={},
            extra_pdfs=None,
            part_key="EHB3112",
            explode_polls=1,
            explode_sleep_s=0,
        )
    blob = " ".join(notes)
    assert "setpartmode_via=?" in blob
    assert "OnAddDXFClick without SetPartMode" in blob
    assert "not success" in blob
    assert "finish_fn=OnAddDXFClick" in blob
    assert "filelist_from_kendo=true" in blob
    assert "filelist_sourcedataid_n=4" in blob
    client.add_item_dxf_files.assert_called()


def test_page_grid_finish_empty_body_is_not_success(tmp_path: Path):
    """Live P001545: page_fn 200 empty body + GET 0 is not success."""
    stp = tmp_path / "P001545.STEP"
    stp.write_bytes(b"ISO")
    kids = [
        {
            "SourceDataID": f"src-{i}",
            "FileID": f"file-{i}",
            "Name": "W001544" if i < 50 else f"W001531_{i}",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        }
        for i in range(53)
    ]
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {"status": "OK", "List": kids}
    client._request_verification_fields = [("__RequestVerificationToken", "x")]
    client._af_source = "chrome_dom"
    client._part_create_list_len = 53
    client._grid_present = True
    client._grid_dxf_row_count = 53
    client._stale_grid = False
    client._edit_quote_id = "31204345-6c91-4122-a859-09f7d7a3ea9f"
    client._edit_gate = ""
    client._finish_via = "page_fn"
    client.create_dxf_parts.return_value = {"List": kids}
    client.cadimport_data.return_value = {"List": kids}
    client.get_item_add_view.return_value = {}
    client.add_item_dxf_files.return_value = {
        "status": 200,
        "body_keys": [],
        "body_type": "empty",
        "has_NewItem": False,
        "has_QuoteItem": False,
        "text_len": 0,
        "empty_body": True,
        "via": "page_fn",
        "finish_fn": "OnAddDXFClick",
        "finish_filelist_n": 52,
        "grid_dxf_row_count": 53,
        "request_keys": ["ID", "ItemID", "customerMaterial", "FileList"],
    }
    client.quote_item_read.return_value = {"Data": [], "Total": 0}
    client.get_json.return_value = {"ItemList": []}
    notes = SecturaFabPushService(client=client).finish_cad_files(
        quote_id="31204345-6c91-4122-a859-09f7d7a3ea9f",
        cad_files=[stp],
        material="A36",
        thickness="0.25",
        qty=1,
        takeoff={},
        bom_rows=[],
        library={},
        extra_pdfs=None,
        part_key="P001545",
        explode_polls=1,
        explode_sleep_s=0,
    )
    blob = " ".join(notes)
    assert "finish_via=page_fn" in blob
    assert "finish_fn=OnAddDXFClick" in blob
    assert "finish_filelist_n=52" in blob
    assert "grid_dxf_row_count=53" in blob
    assert "empty body" in blob.lower()
    assert "not success" in blob.lower()


def test_stale_grid_65_vs_filelist_12_skips_finish(tmp_path: Path):
    """Live 5003313-001: leftover kendo 65 after bind of List=12 — do not Finish."""
    from secturafab.chrome_cdp import grid_dxf_count_is_stale

    assert grid_dxf_count_is_stale(65, 12) is True
    assert grid_dxf_count_is_stale(15, 15) is False
    assert grid_dxf_count_is_stale(12, 12) is False
    stp = tmp_path / "5003313-001.STEP"
    stp.write_bytes(b"ISO")
    kids = [
        {
            "SourceDataID": f"src-{i}",
            "FileID": f"file-{i}",
            "Name": "5003313-001" if i else "Root",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        }
        for i in range(12)
    ]
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {"status": "OK", "List": kids}
    client._request_verification_fields = [("__RequestVerificationToken", "x")]
    client._af_source = "chrome_dom"
    client._part_create_list_len = 12
    client._grid_present = True
    client._grid_dxf_row_count = 65
    client._stale_grid = True
    client._edit_quote_id = "997f1eb7-3eb0-4a76-83f9-4c3439e929b7"
    client._edit_gate = ""
    client.create_dxf_parts.return_value = {"List": kids}
    client.cadimport_data.return_value = {"List": kids}
    client.get_item_add_view.return_value = {}
    client.quote_item_read.return_value = {"Data": [], "Total": 0}
    client.get_json.return_value = {"ItemList": []}
    notes = SecturaFabPushService(client=client).finish_cad_files(
        quote_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0001",
        cad_files=[stp],
        material="A36",
        thickness="0.25",
        qty=1,
        takeoff={},
        bom_rows=[],
        library={},
        extra_pdfs=None,
        part_key="5003313-001",
        explode_polls=1,
        explode_sleep_s=0,
    )
    client.add_item_dxf_files.assert_not_called()
    blob = " ".join(notes)
    assert "edit_quote_id=997f1eb7-3eb0-4a76-83f9-4c3439e929b7" in blob
    assert "minted_id=aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0001" in blob
    assert "stale" in blob.lower()
    assert "grid_dxf_row_count=65" in blob


def test_scrape_quotes_af_fields_from_cdp_evaluate():
    from secturafab.chrome_cdp import scrape_quotes_af_fields

    token = "af-secret-token-value"
    tab = {
        "url": "https://www.secturafab.com/Quote?ID=x",
        "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/page/q",
        "type": "page",
    }

    def _call(ws_url, method, params=None, **_k):
        assert method == "Runtime.evaluate"
        assert "querySelector" in str((params or {}).get("expression") or "")
        return {
            "result": {
                "value": [{"name": "__RequestVerificationToken", "value": token}]
            }
        }

    with patch("secturafab.chrome_cdp.quote_edit_tab", return_value=None), patch(
        "secturafab.chrome_cdp.quotes_tab", return_value=tab
    ), patch("secturafab.chrome_cdp.cdp_call", side_effect=_call):
        fields = scrape_quotes_af_fields("http://127.0.0.1:9222")
    assert fields == [("__RequestVerificationToken", token)]


def test_ensure_prefers_chrome_dom_over_cookie_quote_html():
    """Live 7b723b9: cookie /Quote 200 AF is the wrong claims user."""
    from secturafab.client import SecturaFabClient
    from secturafab.config import SecturaFabConfig
    from secturafab.website import client_antiforgery_extracted

    token = "af-secret-token-value"
    cookie_token = "cookie-html-wrong-user-token"
    client = SecturaFabClient.__new__(SecturaFabClient)
    client.config = SecturaFabConfig(
        base_url="https://api.example.test",
        website_url="https://www.example.test",
        client_id="x",
        client_secret="y",
        website_cookie=".AspNet.ApplicationCookie=filecookie",
    )
    client._token = MagicMock()
    client._token.authorization_header = "Bearer tok"
    client._token.is_expired = False
    client.authenticate = lambda force=False: client._token  # type: ignore[method-assign]
    client._request_verification_token = cookie_token
    client._request_verification_fields = [
        ("__RequestVerificationToken", cookie_token)
    ]
    client._af_source = "cookie_quote_html"
    client._chrome_user_agent = ""
    client._chrome_cookie_name_diff = {}
    client._cookie_quote_access_denied = False
    client._website_cookie_override = ""
    client._quotes_tab_live = False

    def _req(*_a, **_k):
        raise AssertionError("cookie GET /Quote must not supply AF when Quotes is live")

    client.website_request = _req  # type: ignore[method-assign]
    with patch(
        "secturafab.chrome_cdp.chrome_quotes_live", return_value=True
    ), patch(
        "secturafab.chrome_cdp.chrome_debug_base", return_value="http://127.0.0.1:9224"
    ), patch(
        "secturafab.chrome_cdp.chrome_version_user_agent",
        return_value="Mozilla/5.0 Chrome/120",
    ), patch(
        "secturafab.chrome_cdp.sectura_cookies_from_cdp", return_value=[]
    ), patch(
        "secturafab.chrome_cdp.scrape_quotes_af_fields",
        return_value=[("__RequestVerificationToken", token)],
    ):
        assert client.ensure_quote_antiforgery("qid") is True
    assert client_antiforgery_extracted(client) is True
    assert client._af_source == "chrome_dom"
    assert client._quotes_tab_live is True
    notes = SecturaFabPushService(client=client)._antiforgery_capture_notes()
    blob = " ".join(notes)
    assert "af_extracted=true" in blob
    assert "af_source=chrome_dom" in blob
    assert "cookie_quote_html" not in blob
    assert token not in blob
    assert cookie_token not in blob
    assert "filecookie" not in blob


def test_push_job_does_not_mint_when_af_extracted_false(tmp_path: Path):
    """No AF from cookie or Chrome DOM → no new quote."""
    from secturafab.client import SecturaFabClient
    from secturafab.config import SecturaFabConfig

    stp = tmp_path / "10072-1.STEP"
    stp.write_bytes(b"ISO")
    pdf = tmp_path / "10072-1.pdf"
    pdf.write_bytes(b"%PDF")
    client = SecturaFabClient.__new__(SecturaFabClient)
    client.config = SecturaFabConfig(
        base_url="https://api.example.test",
        website_url="https://www.example.test",
        client_id="x",
        client_secret="y",
        website_cookie=".AspNet.ApplicationCookie=box",
    )
    client._token = MagicMock()
    client._token.authorization_header = "Bearer tok"
    client._token.is_expired = False
    client.authenticate = lambda force=False: client._token  # type: ignore[method-assign]
    client._request_verification_token = None
    client._request_verification_fields = []
    client._last_item_add_view_html = ""
    client._af_source = ""
    client._chrome_user_agent = ""
    client._chrome_cookie_name_diff = {}
    client._cookie_quote_access_denied = False

    def _req(method, path, **kwargs):
        resp = MagicMock()
        resp.status_code = 302
        resp.headers = {"Location": "/Account/AccessDenied"}
        resp.text = ""
        resp.content = b""
        resp.url = path
        return resp

    client.website_request = _req  # type: ignore[method-assign]
    client.get_json = MagicMock(return_value={"ItemList": []})  # type: ignore[method-assign]
    service = SecturaFabPushService(client=client)
    with patch(
        "secturafab.chrome_cdp.chrome_quotes_live", return_value=False
    ), patch(
        "secturafab.chrome_cdp.chrome_debug_base", return_value=None
    ), patch.object(
        service, "upload_drawings_quote_request", return_value="qr"
    ), patch.object(
        service, "create_quote", return_value="must-not-mint"
    ) as create_q, patch.object(
        service, "allocate_quote_number", return_value="10072-1"
    ), patch.object(
        service, "finish_cad_files", return_value=[]
    ) as finish, patch(
        "secturafab.push.refresh_bom_rows_for_push", return_value=([], [])
    ), patch(
        "secturafab.push.extract_assembly_description", return_value="WELDMENT"
    ):
        result = service.push_job(
            title="10072-1",
            pdf_filename="10072-1.pdf",
            pdf_path=pdf,
            stp_path=stp,
            takeoff={"library": {"part_key": "10072-1"}},
            times={},
            job_id=7,
        )
    assert result.ok is False
    create_q.assert_not_called()
    finish.assert_not_called()
    blob = " ".join(result.notes or []) + " " + (result.error or "")
    assert "af_extracted=false" in blob
    assert "not minting" in blob
    assert "must-not-mint" not in blob


def test_part_create_403_logonurl_does_not_finish_raw_step(tmp_path: Path):
    """Live 34639-1: www 403 LogOnUrl is not Login; withhold raw STEP Finish."""
    from secturafab.client import SecturaFabApiError

    stp = tmp_path / "34639-1.STEP"
    stp.write_bytes(b"ISO")
    raw = {
        "SourceDataID": "src-step",
        "FileID": "file-step",
        "FileName": "34639-1.STEP",
        "Name": "34639-1",
        "Qty": 1,
        "ErrorStatus": 0,
        "PartCount": 8,
        "Units": "inch",
    }
    token = "af-secret-token-value"
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {"status": "OK", "List": [raw]}
    client._request_verification_fields = [("__RequestVerificationToken", token)]
    client.create_dxf_parts.side_effect = SecturaFabApiError(
        "API request failed (403) for https://www.secturafab.com/part/create",
        status_code=403,
        body={
            "Error": "denied",
            "LogOnUrl": "/Account/Login",
            "login_redirect": False,
            "access_denied": False,
        },
    )
    client.cadimport_data.return_value = {"List": [raw]}
    client.get_item_add_view.return_value = {}
    client.quote_item_read.return_value = {"Data": [], "Total": 0}
    client.get_json.return_value = {"ItemList": []}
    notes = SecturaFabPushService(client=client).finish_cad_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000003463",
        cad_files=[stp],
        material="A36",
        thickness="0.25",
        qty=1,
        takeoff={},
        bom_rows=[],
        library={},
        extra_pdfs=None,
        part_key="34639-1",
        explode_polls=2,
        explode_sleep_s=0,
    )
    client.add_item_dxf_files.assert_not_called()
    client.cadimport_convert_to.assert_not_called()
    blob = " ".join(notes)
    assert "403" in blob
    assert "LogOnUrl" in blob
    assert "not Login" in blob
    assert token not in blob
    assert "not Finishing" in blob or "raw upload" in blob.lower()


def test_collect_cadimport_grid_skips_get_dxf_data():
    client = MagicMock()
    client.cadimport_data.return_value = {}
    client.get_item_add_view.return_value = {}
    SecturaFabPushService(client=client)._collect_cadimport_grid(quote_id="qid")
    client.cadimport_get_dxf_data.assert_not_called()
    client.cadimport_data.assert_called()


def test_cadimport_explode_routes_use_www():
    """CadImport Next/Data/SetUnits/ConvertTo must hit www, not api first."""
    from secturafab.client import SecturaFabClient

    real = SecturaFabClient.__new__(SecturaFabClient)
    real.config = MagicMock()
    real.config.timeout_seconds = 30
    real.config.website_root = "https://www.secturafab.com"
    real._request_verification_token = "x"
    real._request_verification_fields = [("__RequestVerificationToken", "x")]
    captured: list[dict[str, Any]] = []

    def fake_website_request(method, path, **kwargs):
        captured.append(
            {
                "method": method,
                "path": path,
                "prefer_api_origin": kwargs.get("prefer_api_origin"),
                "www_only": kwargs.get("www_only"),
                "headers": kwargs.get("headers") or {},
                "params": kwargs.get("params"),
                "json": kwargs.get("json"),
                "data": kwargs.get("data"),
            }
        )
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b"{}"
        resp.json.return_value = {}
        resp.headers = {}
        resp.text = "{}"
        resp.url = path
        return resp

    real._af_source = "chrome_dom"
    real.website_request = fake_website_request  # type: ignore[method-assign]
    real.cadimport_data(params={"ID": "qid"})
    real.cadimport_update_data_next({"ID": "qid", "List": [], "ListOther": []})
    real.cadimport_convert_to({"ID": "qid", "List": [], "ListOther": []})
    with patch(
        "secturafab.chrome_cdp.chrome_quotes_live", return_value=True
    ), patch(
        "secturafab.client.SecturaFabClient.harvest_chrome_antiforgery",
        return_value="chrome_dom",
    ), patch(
        "secturafab.chrome_cdp.post_part_create_from_quotes_tab",
        return_value={
            "has_antiforgery": True,
            "af_names": ["__RequestVerificationToken"],
            "status": 200,
            "body_keys": ["List"],
            "list_len": 0,
            "List": [],
            "via": "chrome_dom_fetch",
        },
    ), patch(
        "secturafab.chrome_cdp.bind_do_create_dxf_parts_success",
        return_value={
            "has_gridDXFParts": False,
            "grid_dxf_row_count": 0,
            "bound": False,
            "list_len": 0,
            "opened_via": "",
        },
    ) as bind_fn:
        real.create_dxf_parts(["src-1"], ["inch"], location="")
    bind_fn.assert_not_called()
    real.cadimport_set_units("inch")
    real.get_item_add_view("qid")
    real.upload_item_dxf_files(
        [("files", ("a.step", b"ISO", "application/octet-stream"))],
        quote_id="qid",
    )
    assert captured
    assert all(row["prefer_api_origin"] is False for row in captured)
    assert all(row["www_only"] is True for row in captured)
    assert all(
        row["headers"].get("X-Requested-With") == "XMLHttpRequest" for row in captured
    )
    paths = {row["path"] for row in captured}
    assert "/CadImport/UpdateDataNext" in paths
    assert "/CadImport/ConvertTo" in paths
    assert "/part/create" not in paths
    assert "/CadImport/Data" in paths
    assert "/CadImport/SetUnits" in paths
    assert "/CadImport/GetDXFData" not in paths
    assert "/Quote/GetDXFData" not in paths
    next_row = next(r for r in captured if r["path"] == "/CadImport/UpdateDataNext")
    assert isinstance((next_row.get("json") or {}).get("List"), list)
    assert next_row.get("data") is None
    units = next(r for r in captured if r["path"] == "/CadImport/SetUnits")
    assert units["params"] == {"units": "inch"}
    assert units["json"] is None
    assert "Units" not in (units["params"] or {})


def test_website_request_retries_www_after_api_500():
    """API SetUnits 500 / GetDXFData 404 must fall through to www."""
    from secturafab.client import SecturaFabClient
    from secturafab.config import SecturaFabConfig

    client = SecturaFabClient.__new__(SecturaFabClient)
    client.config = SecturaFabConfig(
        base_url="https://api.example.test",
        website_url="https://www.example.test",
        client_id="x",
        client_secret="y",
    )
    client._token = MagicMock()
    client._token.authorization_header = "Bearer tok"
    client._token.is_expired = False
    client.authenticate = lambda force=False: client._token  # type: ignore[method-assign]
    urls: list[str] = []

    def _req(method, url, **_kwargs):
        urls.append(url)
        resp = MagicMock()
        resp.headers = {}
        resp.text = ""
        resp.content = b""
        resp.url = url
        if "api.example.test" in url:
            resp.status_code = 500 if "SetUnits" in url else 404
            return resp
        resp.status_code = 200
        resp.content = b"{}"
        resp.text = "{}"
        resp.json.return_value = {"ok": True}
        return resp

    session = MagicMock()
    session.request.side_effect = _req
    client.session = session
    resp = client.website_request(
        "POST",
        "/CadImport/SetUnits",
        prefer_api_origin=True,
        require_session=False,
    )
    assert resp.status_code == 200
    assert any("api.example.test" in u for u in urls)
    assert any("www.example.test" in u for u in urls)


def test_cadimport_set_units_www_only_does_not_hit_api():
    """www SetUnits 500 must not fall through to api (live 1002381-1)."""
    from secturafab.client import SecturaFabClient
    from secturafab.config import SecturaFabConfig

    client = SecturaFabClient.__new__(SecturaFabClient)
    client.config = SecturaFabConfig(
        base_url="https://api.example.test",
        website_url="https://www.example.test",
        client_id="x",
        client_secret="y",
    )
    client._token = MagicMock()
    client._token.authorization_header = "Bearer tok"
    client._token.is_expired = False
    client.authenticate = lambda force=False: client._token  # type: ignore[method-assign]
    urls: list[str] = []

    def _req(method, url, **kwargs):
        urls.append(url)
        resp = MagicMock()
        resp.headers = {}
        resp.text = "An item with the same key has already been added."
        resp.content = b"err"
        resp.url = url
        resp.status_code = 500
        resp.json.side_effect = ValueError("not json")
        return resp

    session = MagicMock()
    session.request.side_effect = _req
    client.session = session
    with pytest.raises(Exception, match="500|same key|API request failed"):
        client.cadimport_set_units("inch")
    assert urls
    assert all("www.example.test" in u for u in urls)
    assert not any("api.example.test" in u for u in urls)
    called_params = session.request.call_args.kwargs.get("params") or {}
    assert called_params == {"units": "inch"}
    assert session.request.call_args.kwargs.get("json") is None


def test_step_job_does_not_call_image_files(tmp_path: Path, monkeypatch):
    """Do not use Image Files when a STEP is on the job."""
    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=box")
    pdf = tmp_path / "1010103-1.pdf"
    stp = tmp_path / "1010103-1.STEP"
    pdf.write_bytes(b"%PDF")
    stp.write_bytes(b"ISO")
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "1010104.pdf").write_bytes(b"%PDF")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.get_json.return_value = {
        "QuoteNumber": "1010103-1",
        "ItemCount": 0,
        "ItemList": [],
    }
    client.quote_item_read.return_value = {"Data": [], "Total": 0}
    service = SecturaFabPushService(client=client)
    with patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "create_quote", return_value="11111111-aaaa-bbbb-cccc-000000001012"
    ), patch.object(
        service, "allocate_quote_number", return_value="1010103-1"
    ), patch.object(
        service, "finish_cad_files", return_value=["CadImport exploded 3 FileList row(s)"]
    ) as finish_cad, patch.object(
        service, "finish_pdf_files"
    ) as finish_pdf, patch(
        "secturafab.push.refresh_bom_rows_for_push",
        return_value=(
            [{"part_no": "1010104-1", "qty": 1, "description": "GUSSET"}],
            [],
        ),
    ), patch(
        "secturafab.push.extract_assembly_description", return_value="WELDMENT"
    ), patch(
        "secturafab.push.apply_quote_organization", return_value=[]
    ), patch(
        "secturafab.push.ensure_imperial_item_units", return_value=[]
    ), patch(
        "secturafab.push.apply_bom_quantities", return_value=[]
    ), patch(
        "secturafab.push.ensure_weld_ops", return_value=[]
    ):
        result = service.push_job(
            title="1010103-1",
            pdf_filename="1010103-1.pdf",
            pdf_path=pdf,
            stp_path=stp,
            takeoff={
                "library": {
                    "part_key": "1010103-1",
                    "folder": str(lib),
                    "related_pdfs": ["1010104.pdf"],
                }
            },
            times={},
            job_id=10103,
        )
    finish_cad.assert_called()
    finish_pdf.assert_not_called()
    assert result.ok is False
    err = result.error or ""
    assert "Image Files Finish landed" not in err
    assert "CAD Files" in err or "AddItem_DXFFiles" in err


def test_add_item_dxf_files_sends_js_contract():
    """Finish is the page fn that reads #gridDXFParts (live 34137-2)."""
    from secturafab.client import SecturaFabClient

    real = SecturaFabClient.__new__(SecturaFabClient)
    real.config = MagicMock()
    real.config.timeout_seconds = 30
    real._af_source = "chrome_dom"
    real._grid_dxf_row_count = 3
    real.session = MagicMock()
    edit = {
        "title": "*Quote-x",
        "url": "https://www.secturafab.com/Quote/EDIT/qid",
        "webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/page/edit",
        "type": "page",
    }
    with patch(
        "secturafab.chrome_cdp.chrome_quotes_live", return_value=True
    ), patch(
        "secturafab.client.SecturaFabClient.harvest_chrome_antiforgery",
        return_value="chrome_dom",
    ), patch(
        "secturafab.chrome_cdp.quote_edit_tab", return_value=edit
    ), patch(
        "secturafab.chrome_cdp.invoke_page_dxf_finish",
        return_value={
            "via": "page_fn",
            "finish_fn": "OnAddDXFClick",
            "grid_dxf_row_count": 3,
            "status": 200,
            "body_keys": ["NewItem"],
            "body_type": "object",
            "has_NewItem": True,
            "has_QuoteItem": False,
            "text_len": 80,
            "List": [],
        },
    ), patch(
        "secturafab.chrome_cdp.post_add_item_dxf_files_from_quotes_tab",
    ) as fetch_finish:
        result = real.add_item_dxf_files(
            quote_id="qid",
            file_list=[
                {
                    "ErrorStatus": 0,
                    "Qty": 1,
                    "Machine": "Laser",
                    "Material": "100k",
                    "Thickness": 0.375,
                    "ProductID": None,
                }
            ],
        )
    real.session.request.assert_not_called()
    fetch_finish.assert_not_called()
    assert result["via"] == "page_fn"
    assert result["has_NewItem"] is True
    assert real._finish_via == "page_fn"


def test_add_item_dxf_files_grid_finish_uses_grid_rows_not_python():
    """Live P001545: reconstructed FileList POST is not success — skip it."""
    from secturafab.client import SecturaFabClient

    real = SecturaFabClient.__new__(SecturaFabClient)
    real.config = MagicMock()
    real.config.timeout_seconds = 30
    real._af_source = "chrome_dom"
    real._grid_dxf_row_count = 2
    real.session = MagicMock()
    edit = {
        "title": "*Quote-x",
        "url": "https://www.secturafab.com/Quote/EDIT/qid",
        "webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/page/edit",
        "type": "page",
    }
    grid_rows = [
        {
            "SourceDataID": "grid-a",
            "Name": "FROM_GRID_PLATE",
            "ErrorStatus": 0,
            "Qty": 1,
        },
        {
            "SourceDataID": "grid-b",
            "Name": "FROM_GRID_GUSSET",
            "ErrorStatus": 0,
            "Qty": 1,
        },
    ]
    posted: list[dict[str, Any]] = []

    def _fetch(payload, **_k):
        posted.append(payload)
        return {
            "has_antiforgery": True,
            "af_names": ["__RequestVerificationToken"],
            "status": 200,
            "body_keys": ["NewItem"],
            "body_type": "object",
            "has_NewItem": True,
            "has_QuoteItem": False,
            "text_len": 40,
            "via": "chrome_dom_fetch",
        }

    with patch(
        "secturafab.chrome_cdp.chrome_quotes_live", return_value=True
    ), patch(
        "secturafab.client.SecturaFabClient.harvest_chrome_antiforgery",
        return_value="chrome_dom",
    ), patch(
        "secturafab.chrome_cdp.quote_edit_tab", return_value=edit
    ), patch(
        "secturafab.chrome_cdp.invoke_page_dxf_finish",
        return_value={
            "via": "",
            "finish_fn": "",
            "grid_dxf_row_count": 2,
            "status": 0,
            "body_keys": [],
            "body_type": "empty",
            "has_NewItem": False,
            "has_QuoteItem": False,
            "text_len": 0,
            "List": grid_rows,
        },
    ), patch(
        "secturafab.chrome_cdp.post_add_item_dxf_files_from_quotes_tab",
        side_effect=_fetch,
    ) as fetch_finish:
        result = real.add_item_dxf_files(
            quote_id="qid",
            file_list=[{"Name": "PYTHON_REBUILT", "Machine": "Laser", "Qty": 1}],
        )
    real.session.request.assert_not_called()
    fetch_finish.assert_not_called()
    assert not posted
    assert result["via"] == "skipped"
    assert real._finish_via == "skipped"


def test_grid_dxf_row_count_empty_skips_finish(tmp_path: Path):
    """Fail-closed: #gridDXFParts missing/empty → no Finish, no remint."""
    stp = tmp_path / "34994-1.STEP"
    stp.write_bytes(b"ISO")
    kids = [
        {
            "SourceDataID": "src-a",
            "FileID": "file-a",
            "Name": "34994-2 PLATE",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        },
        {
            "SourceDataID": "src-b",
            "FileID": "file-b",
            "Name": "34994-3 GUSSET",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
        },
    ]
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {"status": "OK", "List": kids}
    client._request_verification_fields = [("__RequestVerificationToken", "x")]
    client._af_source = "chrome_dom"
    client._part_create_list_len = 0
    client._grid_present = True
    client._grid_dxf_row_count = 0
    client.cadimport_data.return_value = {"List": kids}
    client.get_item_add_view.return_value = {}
    client.quote_item_read.return_value = {"Data": [], "Total": 0}
    client.get_json.return_value = {"ItemList": []}
    notes = SecturaFabPushService(client=client).finish_cad_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000003494",
        cad_files=[stp],
        material="A36",
        thickness="0.25",
        qty=1,
        takeoff={},
        bom_rows=[],
        library={},
        extra_pdfs=None,
        part_key="34994-1",
        explode_polls=1,
        explode_sleep_s=0,
    )
    blob = " ".join(notes)
    assert "grid_dxf_row_count=0" in blob
    assert "not Finishing" in blob
    client.add_item_dxf_files.assert_not_called()


def test_n1_cad_on_edit_allows_finish(tmp_path: Path):
    """Live 11796-1: 1 Cad row on EDIT is Finishable (not the 34632-2 miss)."""
    stp = tmp_path / "11796-1.STEP"
    stp.write_bytes(b"ISO")
    kids = [
        {
            "SourceDataID": "src-1",
            "FileID": "file-1",
            "ID": "id-1",
            "Name": "TURRET SIDE PLATE",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
            "Category": "Cad",
            "FileType": "Cad",
            "PartMode": 0,
        }
    ]
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {"status": "OK", "List": kids}
    client._request_verification_fields = [("__RequestVerificationToken", "x")]
    client._af_source = "chrome_dom"
    client._part_create_list_len = 1
    client._grid_present = True
    client._grid_dxf_row_count = 1
    client._stale_grid = False
    client._edit_quote_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa1796"
    client._edit_gate = ""
    client._finish_via = "page_fn"
    client._setpartmode_via = "page_fn"
    client.create_dxf_parts.return_value = {"List": kids}
    client.cadimport_data.return_value = {"List": kids}
    client.get_item_add_view.return_value = {}
    client.add_item_dxf_files.return_value = {
        "status": 200,
        "body_keys": ["NewItem"],
        "body_type": "object",
        "has_NewItem": True,
        "has_QuoteItem": False,
        "text_len": 8,
        "empty_body": False,
        "via": "page_fn",
        "finish_fn": "OnAddDXFClick",
        "finish_filelist_n": 1,
        "grid_dxf_row_count": 1,
        "filelist_from_kendo": True,
        "filelist_sourcedataid_n": 1,
        "filelist_filetype": {"Cad": 1, "Linear": 0, "Assembly": 0, "Component": 0, "blank": 0},
        "finish_af_present": True,
        "finish_why": "",
        "request_keys": [
            "ID",
            "ItemID",
            "customerMaterial",
            "FileList",
            "__RequestVerificationToken",
        ],
    }
    client.quote_item_read.return_value = {
        "Data": [{"ProductType": 100, "Name": "TURRET SIDE PLATE"}],
        "Total": 1,
    }
    client.get_json.return_value = {
        "ItemList": [{"ProductType": 100, "Name": "TURRET SIDE PLATE"}]
    }
    with patch(
        "secturafab.chrome_cdp.apply_grid_dxf_part_modes",
        return_value={
            "grid_present": True,
            "cad": 1,
            "linear": 0,
            "assembly": 0,
            "component": 0,
            "set_count": 1,
            "setpartmode_via": "page_fn",
            "grid_dxf_row_count": 1,
            "kendo_row_keys": [
                "CadType",
                "FileID",
                "FileType",
                "ID",
                "SourceDataID",
                "Stock_X",
                "Stock_Y",
            ],
        },
    ):
        notes = SecturaFabPushService(client=client).finish_cad_files(
            quote_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa1796",
            cad_files=[stp],
            material="A36",
            thickness="0.25",
            qty=1,
            takeoff={},
            bom_rows=[],
            library={},
            extra_pdfs=None,
            part_key="11796-1",
            explode_polls=1,
            explode_sleep_s=0,
        )
    blob = " ".join(notes)
    client.add_item_dxf_files.assert_called()
    assert "empty #gridDXFParts" not in blob
    assert "List=0" not in blob
    assert "filelist_from_kendo=true" in blob
    assert "finish_af_present=true" in blob
    assert "not the 105918-1 path" not in blob


def test_filelist_not_kendo_or_af_missing_is_not_success(tmp_path: Path):
    """Live 11796-1: filelist_from_kendo=false or finish_af_present=false is not gold."""
    stp = tmp_path / "11796-1.STEP"
    stp.write_bytes(b"ISO")
    kids = [
        {
            "SourceDataID": "src-1",
            "FileID": "file-1",
            "Name": "TURRET SIDE PLATE",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
            "Category": "Cad",
            "FileType": "Cad",
            "PartMode": 0,
        }
    ]

    def _run(*, from_kendo: bool, af: bool, why: str, sid_n: int = 0) -> str:
        client = MagicMock()
        client.upload_item_dxf_files.return_value = {"status": "OK", "List": kids}
        client._request_verification_fields = [("__RequestVerificationToken", "x")]
        client._af_source = "chrome_dom"
        client._part_create_list_len = 1
        client._grid_present = True
        client._grid_dxf_row_count = 1
        client._stale_grid = False
        client._edit_quote_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa1796"
        client._edit_gate = ""
        client._finish_via = "page_fn"
        client._setpartmode_via = "page_fn"
        client.create_dxf_parts.return_value = {"List": kids}
        client.cadimport_data.return_value = {"List": kids}
        client.get_item_add_view.return_value = {}
        client.add_item_dxf_files.return_value = {
            "status": 200,
            "body_keys": [],
            "body_type": "empty",
            "has_NewItem": False,
            "has_QuoteItem": False,
            "text_len": 0,
            "empty_body": True,
            "via": "page_fn",
            "finish_fn": "OnAddDXFClick",
            "finish_filelist_n": 1,
            "grid_dxf_row_count": 1,
            "filelist_from_kendo": from_kendo,
            "filelist_sourcedataid_n": sid_n,
            "filelist_id_n": 1 if sid_n else 0,
            "filelist_fileid_n": 0,
            "finish_af_present": af,
            "finish_why": why,
            "request_keys": ["ID", "ItemID", "customerMaterial", "FileList"],
        }
        client.quote_item_read.return_value = {"Data": [], "Total": 0}
        client.get_json.return_value = {"ItemList": []}
        with patch(
            "secturafab.chrome_cdp.apply_grid_dxf_part_modes",
            return_value={
                "grid_present": True,
                "cad": 1,
                "linear": 0,
                "assembly": 0,
                "component": 0,
                "set_count": 1,
                "setpartmode_via": "page_fn",
                "grid_dxf_row_count": 1,
                "kendo_row_keys": [
                    "CadType",
                    "FileID",
                    "FileType",
                    "ID",
                    "SourceDataID",
                    "Stock_X",
                    "Stock_Y",
                ],
            },
        ):
            notes = SecturaFabPushService(client=client).finish_cad_files(
                quote_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa1796",
                cad_files=[stp],
                material="A36",
                thickness="0.25",
                qty=1,
                takeoff={},
                bom_rows=[],
                library={},
                extra_pdfs=None,
                part_key="11796-1",
                explode_polls=1,
                explode_sleep_s=0,
            )
        return " ".join(notes)

    missing_kendo = _run(
        from_kendo=False, af=True, why="filelist_not_kendo", sid_n=1
    )
    assert "filelist_from_kendo=false" in missing_kendo
    assert "not the 105918-1 path" in missing_kendo
    assert "not success" in missing_kendo
    missing_af = _run(
        from_kendo=True, af=False, why="af_missing_on_document", sid_n=1
    )
    assert "finish_af_present=false" in missing_af
    assert "not the 105918-1 path" in missing_af
    assert "not success" in missing_af
    missing_ids = _run(
        from_kendo=False, af=True, why="filelist_missing_ids", sid_n=0
    )
    assert "filelist_sourcedataid_n=0" in missing_ids
    assert "filelist_missing_ids" in missing_ids
    assert "not the 105918-1 path" in missing_ids
    assert "not success" in missing_ids


def test_kendo_af_sid_cad_empty_body_is_not_success(tmp_path: Path):
    """Live 107292-1: checklist green + 200 empty + GET 0 is not gold."""
    stp = tmp_path / "107292-1.STEP"
    stp.write_bytes(b"ISO")
    kids = [
        {
            "SourceDataID": "src-1",
            "FileID": "file-1",
            "ID": "id-1",
            "Name": "OPERATOR PLATFORM LOWER CONTROL MOUNT",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
            "Category": "Cad",
            "FileType": "Cad",
            "PartMode": 0,
        }
    ]
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {"status": "OK", "List": kids}
    client._request_verification_fields = [("__RequestVerificationToken", "x")]
    client._af_source = "chrome_dom"
    client._part_create_list_len = 1
    client._grid_present = True
    client._grid_dxf_row_count = 1
    client._stale_grid = False
    client._edit_quote_id = "d59318c8-9c39-43a2-aef6-cbd28203ee82"
    client._edit_gate = ""
    client._finish_via = "page_fn"
    client._setpartmode_via = "page_fn"
    client.create_dxf_parts.return_value = {"List": kids}
    client.cadimport_data.return_value = {"List": kids}
    client.get_item_add_view.return_value = {}
    client.add_item_dxf_files.return_value = {
        "status": 200,
        "body_keys": [],
        "body_type": "empty",
        "has_NewItem": False,
        "has_QuoteItem": False,
        "text_len": 0,
        "empty_body": True,
        "via": "page_fn",
        "finish_fn": "OnAddDXFClick",
        "finish_filelist_n": 1,
        "grid_dxf_row_count": 1,
        "filelist_from_kendo": True,
        "filelist_sourcedataid_n": 1,
        "filelist_id_n": 1,
        "filelist_fileid_n": 1,
        "filelist_filetype": {"Cad": 1, "Linear": 0, "Assembly": 0, "Component": 0, "blank": 0},
        "filelist_row_keys": ["FileID", "FileType", "ID", "SourceDataID"],
        "filelist_missing_keys": [
            "CadType",
            "Length",
            "Material",
            "Status",
            "Stock_X",
            "Stock_Y",
            "Thickness",
            "Width",
        ],
        "filelist_missing_identity": ["CadType", "Stock_X", "Stock_Y"],
        "finish_af_present": True,
        "finish_why": "filelist_missing_keys=CadType+Stock_X+Stock_Y",
        "request_keys": [
            "ID",
            "ItemID",
            "customerMaterial",
            "FileList",
            "__RequestVerificationToken",
        ],
    }
    client.quote_item_read.return_value = {"Data": [], "Total": 0}
    client.get_json.return_value = {"ItemList": []}
    with patch(
        "secturafab.chrome_cdp.apply_grid_dxf_part_modes",
        return_value={
            "grid_present": True,
            "cad": 1,
            "linear": 0,
            "assembly": 0,
            "component": 0,
            "set_count": 1,
            "setpartmode_via": "page_fn",
            "grid_dxf_row_count": 1,
            "kendo_row_keys": [
                "CadType",
                "FileID",
                "FileType",
                "ID",
                "SourceDataID",
                "Stock_X",
                "Stock_Y",
            ],
        },
    ):
        notes = SecturaFabPushService(client=client).finish_cad_files(
            quote_id="d59318c8-9c39-43a2-aef6-cbd28203ee82",
            cad_files=[stp],
            material="A36",
            thickness="0.105",
            qty=1,
            takeoff={},
            bom_rows=[],
            library={},
            extra_pdfs=None,
            part_key="107292-1",
            explode_polls=1,
            explode_sleep_s=0,
        )
    blob = " ".join(notes)
    assert "filelist_from_kendo=true" in blob
    assert "finish_af_present=true" in blob
    assert "filelist_sourcedataid_n=1" in blob
    assert "Cad:1" in blob
    assert "filelist_row_keys=" in blob
    assert "CadType" in blob and "Stock_X" in blob
    assert "empty body" in blob.lower()
    assert "List,Result" in blob
    assert "not success" in blob
    assert "item_count=0" in blob or "GET item_count=0" in blob


def test_cadtype_stock_without_filetype_empty_body_is_not_success(tmp_path: Path):
    """Live 16629-1: CadType+Stock on kendo/FileList + no FileType/Status is not gold."""
    stp = tmp_path / "16629-1.STEP"
    stp.write_bytes(b"ISO")
    kids = [
        {
            "SourceDataID": "src-1",
            "FileID": "file-1",
            "ID": "id-1",
            "Name": "EAR",
            "Qty": 1,
            "ErrorStatus": 0,
            "CadType": 0,
            "Stock_X": 11.0,
            "Stock_Y": 6.25,
            "Stock_Z": 0.105,
            "Stock_Units": "inch",
            "Width": 11.0,
            "Length": 6.25,
            "Thickness": 0.105,
            "Material": "A1011",
            "ProductType": 100,
            "Category": "Cad",
            "PartMode": 0,
        }
    ]
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {"status": "OK", "List": kids}
    client._request_verification_fields = [("__RequestVerificationToken", "x")]
    client._af_source = "chrome_dom"
    client._part_create_list_len = 1
    client._grid_present = True
    client._grid_dxf_row_count = 1
    client._stale_grid = False
    client._edit_quote_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa6629"
    client._edit_gate = ""
    client._finish_via = "page_fn"
    client._setpartmode_via = "page_fn"
    client.create_dxf_parts.return_value = {"List": kids}
    client.cadimport_data.return_value = {"List": kids}
    client.get_item_add_view.return_value = {}
    client.add_item_dxf_files.return_value = {
        "status": 200,
        "body_keys": [],
        "body_type": "empty",
        "has_NewItem": False,
        "has_QuoteItem": False,
        "text_len": 0,
        "empty_body": True,
        "via": "page_fn",
        "finish_fn": "OnAddDXFClick",
        "finish_filelist_n": 1,
        "grid_dxf_row_count": 1,
        "filelist_from_kendo": True,
        "filelist_sourcedataid_n": 1,
        "filelist_id_n": 1,
        "filelist_fileid_n": 1,
        "filelist_filetype": {"Cad": 1, "Linear": 0, "Assembly": 0, "Component": 0, "blank": 0},
        "filelist_row_keys": [
            "CadType",
            "FileID",
            "ID",
            "Length",
            "Material",
            "ProductType",
            "SourceDataID",
            "Stock_Units",
            "Stock_X",
            "Stock_Y",
            "Stock_Z",
            "Thickness",
            "Width",
        ],
        "filelist_missing_keys": ["FileType", "Status"],
        "filelist_missing_identity": [],
        "finish_af_present": True,
        "finish_why": "filelist_missing_keys=Status+FileType",
        "request_keys": [
            "ID",
            "ItemID",
            "customerMaterial",
            "FileList",
            "__RequestVerificationToken",
        ],
    }
    client.quote_item_read.return_value = {"Data": [], "Total": 0}
    client.get_json.return_value = {"ItemList": []}
    with patch(
        "secturafab.chrome_cdp.apply_grid_dxf_part_modes",
        return_value={
            "grid_present": True,
            "cad": 1,
            "linear": 0,
            "assembly": 0,
            "component": 0,
            "set_count": 1,
            "setpartmode_via": "page_fn",
            "grid_dxf_row_count": 1,
            "kendo_row_keys": [
                "CadType",
                "FileID",
                "ID",
                "SourceDataID",
                "Stock_X",
                "Stock_Y",
            ],
        },
    ):
        notes = SecturaFabPushService(client=client).finish_cad_files(
            quote_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa6629",
            cad_files=[stp],
            material="A36",
            thickness="0.105",
            qty=1,
            takeoff={},
            bom_rows=[],
            library={},
            extra_pdfs=None,
            part_key="16629-1",
            explode_polls=1,
            explode_sleep_s=0,
        )
    blob = " ".join(notes)
    assert "filelist_from_kendo=true" in blob
    assert "CadType" in blob and "Stock_X" in blob
    assert "filelist_missing_keys=" in blob
    assert "FileType" in blob
    assert "posted FileList lacks FileType" in blob
    assert "empty body" in blob.lower()
    assert "not success" in blob
    assert "item_count=0" in blob or "GET item_count=0" in blob
    client.add_item_dxf_files.assert_called()


def test_filetype_cad_empty_body_is_not_success(tmp_path: Path):
    """Live 10098-1: FileType=Cad + CadType+Stock + 200 empty + GET 0 is not gold."""
    stp = tmp_path / "10098-1.STEP"
    stp.write_bytes(b"ISO")
    kids = [
        {
            "SourceDataID": "src-1",
            "FileID": "file-1",
            "ID": "id-1",
            "Name": "PIVOTING FOOT",
            "Qty": 1,
            "ErrorStatus": 0,
            "CadType": 0,
            "Stock_X": 11.0,
            "Stock_Y": 6.25,
            "Stock_Z": 0.105,
            "Width": 11.0,
            "Length": 6.25,
            "Thickness": 0.105,
            "Material": "A1011",
            "ProductType": 100,
            "Category": "Cad",
            "ItemType": "Cad",
            "PartMode": 0,
            "FileType": "Cad",
        }
    ]
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {"status": "OK", "List": kids}
    client._request_verification_fields = [("__RequestVerificationToken", "x")]
    client._af_source = "chrome_dom"
    client._part_create_list_len = 1
    client._grid_present = True
    client._grid_dxf_row_count = 1
    client._stale_grid = False
    client._edit_quote_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0098"
    client._edit_gate = ""
    client._finish_via = "page_fn"
    client._setpartmode_via = "page_fn"
    client.create_dxf_parts.return_value = {"List": kids}
    client.cadimport_data.return_value = {"List": kids}
    client.get_item_add_view.return_value = {}
    client.add_item_dxf_files.return_value = {
        "status": 200,
        "body_keys": [],
        "body_type": "empty",
        "has_NewItem": False,
        "has_QuoteItem": False,
        "text_len": 0,
        "empty_body": True,
        "via": "page_fn",
        "finish_fn": "OnAddDXFClick",
        "finish_filelist_n": 1,
        "grid_dxf_row_count": 1,
        "filelist_from_kendo": True,
        "filelist_sourcedataid_n": 1,
        "filelist_id_n": 1,
        "filelist_fileid_n": 1,
        "filelist_filetype": {
            "Cad": 1,
            "Linear": 0,
            "Assembly": 0,
            "Component": 0,
            "blank": 0,
        },
        "filelist_errorstatus": 0,
        "filelist_qty": 1,
        "filelist_filetype_value": "Cad",
        "filelist_filetype_type": "str",
        "filelist_cad_path_keys": [],
        "filelist_row_keys": [
            "CadType",
            "FileID",
            "FileType",
            "ID",
            "ItemType",
            "Length",
            "Material",
            "ProductType",
            "SourceDataID",
            "Stock_X",
            "Stock_Y",
            "Stock_Z",
            "Thickness",
            "Width",
        ],
        "filelist_missing_keys": ["Status"],
        "filelist_missing_identity": [],
        "finish_af_present": True,
        "finish_why": "filelist_missing_keys=Status",
        "request_keys": [
            "ID",
            "ItemID",
            "customerMaterial",
            "FileList",
            "__RequestVerificationToken",
        ],
    }
    client.quote_item_read.return_value = {"Data": [], "Total": 0}
    client.get_json.return_value = {"ItemList": []}
    with patch(
        "secturafab.chrome_cdp.apply_grid_dxf_part_modes",
        return_value={
            "grid_present": True,
            "cad": 1,
            "linear": 0,
            "assembly": 0,
            "component": 0,
            "set_count": 1,
            "setpartmode_via": "page_fn",
            "grid_dxf_row_count": 1,
            "kendo_row_keys": [
                "CadType",
                "FileID",
                "FileType",
                "ID",
                "SourceDataID",
                "Stock_X",
                "Stock_Y",
            ],
        },
    ):
        notes = SecturaFabPushService(client=client).finish_cad_files(
            quote_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0098",
            cad_files=[stp],
            material="A36",
            thickness="0.105",
            qty=1,
            takeoff={},
            bom_rows=[],
            library={},
            extra_pdfs=None,
            part_key="10098-1",
            explode_polls=1,
            explode_sleep_s=0,
        )
    blob = " ".join(notes)
    ok = (
        "not success" not in blob
        and "item_count=0" not in blob
        and "GET item_count=0" not in blob
        and "empty body" not in blob.lower()
    )
    assert ok is False
    assert "filelist_errorstatus=0" in blob
    assert "filelist_qty=1" in blob
    assert "filelist_filetype_value=Cad" in blob
    assert "filelist_filetype_type=str" in blob
    assert "filelist_cad_path_keys=" in blob
    assert "filelist_missing_keys=" in blob
    assert "Status" in blob
    assert "FileType=Cad persist is not success" in blob
    assert "66 Component" in blob
    assert "empty body" in blob.lower()
    assert "not success" in blob
    assert "item_count=0" in blob or "GET item_count=0" in blob
    client.add_item_dxf_files.assert_called()


def test_part_create_empty_list_skips_bind_and_finish():
    """Live 34632-2: /part/create List=0 → no bind, no Finish, no remint."""
    from secturafab.client import SecturaFabClient
    from secturafab.config import SecturaFabConfig

    client = SecturaFabClient.__new__(SecturaFabClient)
    client.config = SecturaFabConfig(
        base_url="https://api.example.test",
        website_url="https://www.example.test",
        client_id="x",
        client_secret="y",
        website_cookie=".AspNet.ApplicationCookie=boxcookie",
    )
    client._af_source = "chrome_dom"
    client._request_verification_fields = [("__RequestVerificationToken", "x")]
    client.session = MagicMock()
    with patch(
        "secturafab.chrome_cdp.chrome_quotes_live", return_value=True
    ), patch(
        "secturafab.client.SecturaFabClient.harvest_chrome_antiforgery",
        return_value="chrome_dom",
    ), patch(
        "secturafab.chrome_cdp.post_part_create_from_quotes_tab",
        return_value={
            "has_antiforgery": True,
            "af_names": ["__RequestVerificationToken"],
            "status": 200,
            "body_keys": ["List"],
            "list_len": 0,
            "List": [],
            "via": "chrome_dom_fetch",
        },
    ), patch(
        "secturafab.chrome_cdp.bind_do_create_dxf_parts_success",
    ) as bind_fn, patch(
        "secturafab.chrome_cdp.invoke_page_dxf_finish",
    ) as finish_fn:
        result = client.create_dxf_parts(["src-1"], ["inch"], location="")
        finish = client.add_item_dxf_files(quote_id="qid", file_list=[{"Qty": 1}])
    bind_fn.assert_not_called()
    finish_fn.assert_not_called()
    assert result["List"] == []
    assert client._part_create_via == "chrome_dom_fetch"
    assert client._part_create_list_len == 0
    assert client._grid_dxf_row_count == 0
    assert finish["via"] == "skipped"
    assert client._finish_via == "skipped"


def test_part_create_list_1_binds_and_allows_finish():
    """Live 11796-1: List=1 Cad binds and Finish is allowed."""
    from secturafab.client import SecturaFabClient
    from secturafab.config import SecturaFabConfig

    kid = {
        "SourceDataID": "src-1",
        "FileID": "file-1",
        "Name": "TURRET SIDE PLATE",
        "Qty": 1,
        "ErrorStatus": 0,
    }
    client = SecturaFabClient.__new__(SecturaFabClient)
    client.config = SecturaFabConfig(
        base_url="https://api.example.test",
        website_url="https://www.example.test",
        client_id="x",
        client_secret="y",
        website_cookie=".AspNet.ApplicationCookie=boxcookie",
    )
    client._af_source = "chrome_dom"
    client._request_verification_fields = [("__RequestVerificationToken", "x")]
    client._stale_grid = False
    client.session = MagicMock()
    with patch(
        "secturafab.chrome_cdp.chrome_quotes_live", return_value=True
    ), patch(
        "secturafab.client.SecturaFabClient.harvest_chrome_antiforgery",
        return_value="chrome_dom",
    ), patch(
        "secturafab.chrome_cdp.post_part_create_from_quotes_tab",
        return_value={
            "has_antiforgery": True,
            "af_names": ["__RequestVerificationToken"],
            "status": 200,
            "body_keys": ["List"],
            "list_len": 1,
            "List": [kid],
            "via": "chrome_dom_fetch",
        },
    ), patch(
        "secturafab.chrome_cdp.bind_do_create_dxf_parts_success",
        return_value={
            "grid_present": True,
            "has_gridDXFParts": True,
            "grid_dxf_row_count": 1,
            "bound": True,
            "list_len": 1,
            "opened_via": "but_dxf",
            "stale_grid": False,
            "kendo_row_keys": [
                "CadType",
                "FileID",
                "FileType",
                "ID",
                "SourceDataID",
                "Stock_X",
                "Stock_Y",
            ],
        },
    ) as bind_fn, patch(
        "secturafab.chrome_cdp.minted_edit_tab_ready",
        return_value={
            "ok": True,
            "edit_quote_id": "qid",
            "minted_id": "qid",
            "reason": "",
        },
    ), patch(
        "secturafab.chrome_cdp.invoke_page_dxf_finish",
        return_value={
            "via": "page_fn",
            "finish_fn": "OnAddDXFClick",
            "reads_kendo": True,
            "grid_dxf_row_count": 1,
            "finish_filelist_n": 1,
            "filelist_from_kendo": True,
            "finish_af_present": True,
            "finish_why": "",
            "status": 200,
            "body_keys": ["NewItem"],
            "body_type": "object",
            "has_NewItem": True,
            "has_QuoteItem": False,
            "text_len": 8,
            "request_keys": ["ID", "FileList", "__RequestVerificationToken"],
        },
    ) as finish_fn:
        result = client.create_dxf_parts(
            ["src-1"], ["inch"], location="", quote_id="qid"
        )
        finish = client.add_item_dxf_files(quote_id="qid", file_list=[kid])
    bind_fn.assert_called()
    finish_fn.assert_called()
    assert len(result["List"]) == 1
    assert client._part_create_list_len == 1
    assert client._grid_dxf_row_count == 1
    assert finish["via"] == "page_fn"
    assert finish["filelist_from_kendo"] is True
    assert finish["finish_af_present"] is True


def test_add_item_skips_finish_when_kendo_lacks_cadimport_identity():
    """Bind captured kendo without CadType/Stock_* → do not invoke page Finish."""
    from secturafab.client import SecturaFabClient
    from secturafab.config import SecturaFabConfig

    client = SecturaFabClient.__new__(SecturaFabClient)
    client.config = SecturaFabConfig(
        base_url="https://api.example.test",
        website_url="https://www.example.test",
        client_id="x",
        client_secret="y",
        website_cookie=".AspNet.ApplicationCookie=boxcookie",
    )
    client._af_source = "chrome_dom"
    client._request_verification_fields = [("__RequestVerificationToken", "x")]
    client._part_create_list_len = 1
    client._grid_present = True
    client._grid_dxf_row_count = 1
    client._stale_grid = False
    client._kendo_row_keys = ["FileID", "FileType", "ID", "SourceDataID"]
    client.session = MagicMock()
    with patch(
        "secturafab.chrome_cdp.chrome_quotes_live", return_value=True
    ), patch(
        "secturafab.client.SecturaFabClient.harvest_chrome_antiforgery",
        return_value="chrome_dom",
    ), patch(
        "secturafab.chrome_cdp.invoke_page_dxf_finish",
    ) as finish_fn:
        result = client.add_item_dxf_files(
            quote_id="qid",
            file_list=[{"ID": "x", "FileType": "Cad"}],
        )
    finish_fn.assert_not_called()
    assert result["via"] == "skipped"
    assert result["finish_why"] == "filelist_missing_keys=CadType+Stock_X+Stock_Y"
    assert result["filelist_missing_identity"] == ["CadType", "Stock_X", "Stock_Y"]


def test_grid_present_false_skips_bind_and_finish():
    """Live 106386-1: t.List>1 but #gridDXFParts not in Chrome → no Finish."""
    from secturafab.client import SecturaFabClient
    from secturafab.config import SecturaFabConfig

    kids = [
        {"SourceDataID": "a", "Name": "PLATE", "Qty": 1, "ErrorStatus": 0},
        {"SourceDataID": "b", "Name": "GUSSET", "Qty": 1, "ErrorStatus": 0},
    ]
    client = SecturaFabClient.__new__(SecturaFabClient)
    client.config = SecturaFabConfig(
        base_url="https://api.example.test",
        website_url="https://www.example.test",
        client_id="x",
        client_secret="y",
        website_cookie=".AspNet.ApplicationCookie=boxcookie",
    )
    client._af_source = "chrome_dom"
    client._request_verification_fields = [("__RequestVerificationToken", "x")]
    client.session = MagicMock()
    with patch(
        "secturafab.chrome_cdp.chrome_quotes_live", return_value=True
    ), patch(
        "secturafab.client.SecturaFabClient.harvest_chrome_antiforgery",
        return_value="chrome_dom",
    ), patch(
        "secturafab.chrome_cdp.post_part_create_from_quotes_tab",
        return_value={
            "has_antiforgery": True,
            "af_names": ["__RequestVerificationToken"],
            "status": 200,
            "body_keys": ["List"],
            "list_len": 2,
            "List": kids,
            "via": "chrome_dom_fetch",
        },
    ), patch(
        "secturafab.chrome_cdp.bind_do_create_dxf_parts_success",
        return_value={
            "grid_present": False,
            "has_gridDXFParts": False,
            "grid_dxf_row_count": 0,
            "bound": False,
            "list_len": 2,
            "opened_via": "",
        },
    ), patch(
        "secturafab.chrome_cdp.invoke_page_dxf_finish",
    ) as finish_fn:
        result = client.create_dxf_parts(["src-1"], ["inch"], location="", quote_id="qid")
        finish = client.add_item_dxf_files(quote_id="qid", file_list=kids)
    finish_fn.assert_not_called()
    assert len(result["List"]) == 2
    assert client._part_create_list_len == 2
    assert client._grid_present is False
    assert client._grid_dxf_row_count == 0
    assert finish["via"] == "skipped"


def test_add_item_pdf_files_posts_quote_mvc():
    from secturafab.client import SecturaFabClient
    from secturafab.config import SecturaFabConfig

    real = SecturaFabClient.__new__(SecturaFabClient)
    real.config = SecturaFabConfig(website_cookie="ASP.NET_SessionId=fixture")
    captured: dict[str, Any] = {}

    def fake_website_request(method, path, **kwargs):
        captured["method"] = method
        captured["path"] = path
        captured["json"] = kwargs.get("json")
        captured["data"] = kwargs.get("data")
        captured["files"] = kwargs.get("files")
        captured["require_session"] = kwargs.get("require_session")
        captured["prefer_api_origin"] = kwargs.get("prefer_api_origin")
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b"{}"
        resp.json.return_value = {"ok": True}
        resp.headers = {}
        resp.text = "{}"
        resp.url = path
        return resp

    real.website_request = fake_website_request  # type: ignore[method-assign]
    real.add_item_pdf_files(
        quote_id="qid",
        file_list=[
            {
                "Status": 1,
                "Qty": 1,
                "Machine": "Laser",
                "Material": "A36",
                "Thickness": 0.25,
                "Length": 6.25,
                "Width": 11.0,
                "ItemType": "cad",
                "FileName": "14500-1.pdf",
                "Name": "14500-1 PEDESTAL TOP PLATE",
            }
        ],
    )
    assert captured["path"] == "/Quote/AddItem_PDFFiles"
    assert captured["method"] == "POST"
    assert captured["require_session"] is True
    assert captured["prefer_api_origin"] is False
    assert captured["json"] is None
    assert captured["files"] is None
    form = dict(captured["data"])
    assert form["ID"] == "qid"
    assert form["ItemID"] == EMPTY_GUID
    assert form["FileList[0][Machine]"] == "Laser - Bay1"
    assert form["FileList[0][ItemType]"] == "cad"
    assert form["FileList[0][ProductType]"] == "100"
    assert form["FileList[0][Status]"] == "1"
    assert form["FileList[0][Thickness]"] == "0.25"
    assert form["FileList[0][Length]"] == "6.25"
    assert form["FileList[0][Width]"] == "11.0"
    assert form["FileList[0][FileName]"] == "14500-1.pdf"
    assert form["FileList[0][PartName]"] == "14500-1 PEDESTAL TOP PLATE"
    assert "customerMaterial" not in form
    assert "FileList[0][ErrorStatus]" not in form


def test_add_item_linear_posts_quote_mvc():
    from secturafab.client import SecturaFabClient
    from secturafab.config import SecturaFabConfig

    real = SecturaFabClient.__new__(SecturaFabClient)
    real.config = SecturaFabConfig(website_cookie="ASP.NET_SessionId=fixture")
    captured: dict[str, Any] = {}

    def fake_website_request(method, path, **kwargs):
        captured["method"] = method
        captured["path"] = path
        captured["json"] = kwargs.get("json")
        captured["data"] = kwargs.get("data")
        captured["files"] = kwargs.get("files")
        captured["require_session"] = kwargs.get("require_session")
        captured["prefer_api_origin"] = kwargs.get("prefer_api_origin")
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b"{}"
        resp.json.return_value = {"ok": True}
        resp.headers = {}
        resp.text = "{}"
        resp.url = path
        return resp

    real.website_request = fake_website_request  # type: ignore[method-assign]
    real.add_item_linear(
        quote_id="qid",
        product_id="pid-tube",
        qty=2,
        length=10.9,
        material="A500",
        machine="Saw",
        name="1001880-2 TUBE",
        extra={
            "productConfigID": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            "productSubType": "tube",
            "dim1": 2,
            "dim2": 4,
            "dim3": 0.25,
            "dim4": 0,
            "weightLength": 3.1,
        },
    )
    assert captured["path"] == "/Quote/AddItem_Linear"
    assert captured["method"] == "POST"
    assert captured["require_session"] is True
    assert captured["prefer_api_origin"] is False
    assert captured["json"] is None
    assert captured["files"] is None
    body = dict(captured["data"])
    assert list(body.keys()) == list(LINEAR_ADD_FIELDS)
    assert body["ID"] == "qid"
    assert body["ItemID"] == EMPTY_GUID
    assert body["productID"] == "pid-tube"
    assert body["qty"] == "2"
    assert body["length"] == "10.9"
    assert body["productType"] == "tube"
    assert body["machine"] == "Saw"
    assert body["name"] == "1001880-2 TUBE"
    assert body["productConfigID"] == "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    assert body["productConfigID"] != EMPTY_GUID
    assert body["productSubType"] == "tube"
    assert body["dim1"] == "2"
    assert body["weightLength"] == "3.1"
    assert "SKU" not in body
    assert "ProductID" not in body


def test_add_item_pdf_files_fails_closed_without_cookie(monkeypatch):
    from secturafab.client import SecturaFabClient
    from secturafab.config import SecturaFabConfig

    monkeypatch.delenv("SECTURA_WEBSITE_COOKIE", raising=False)
    monkeypatch.delenv("SECTURAFAB_WEBSITE_COOKIE", raising=False)
    real = SecturaFabClient.__new__(SecturaFabClient)
    real.config = SecturaFabConfig(website_cookie="")
    called = {"n": 0}

    def boom(*_a, **_k):
        called["n"] += 1
        raise AssertionError("must not POST without a cookie")

    real.website_request = boom  # type: ignore[method-assign]
    with pytest.raises(SecturaFabWebsiteAuthError, match="SECTURA_WEBSITE_COOKIE|session"):
        real.add_item_pdf_files(
            quote_id="qid",
            file_list=[{"Status": 1, "Qty": 1, "Machine": "Laser"}],
        )
    assert called["n"] == 0


def test_add_item_linear_fails_closed_without_cookie(monkeypatch):
    from secturafab.client import SecturaFabClient
    from secturafab.config import SecturaFabConfig

    monkeypatch.delenv("SECTURA_WEBSITE_COOKIE", raising=False)
    monkeypatch.delenv("SECTURAFAB_WEBSITE_COOKIE", raising=False)
    real = SecturaFabClient.__new__(SecturaFabClient)
    real.config = SecturaFabConfig(website_cookie="")
    called = {"n": 0}

    def boom(*_a, **_k):
        called["n"] += 1
        raise AssertionError("must not POST without a cookie")

    real.website_request = boom  # type: ignore[method-assign]
    with pytest.raises(SecturaFabWebsiteAuthError, match="SECTURA_WEBSITE_COOKIE|session"):
        real.add_item_linear(quote_id="qid", product_id="pid")
    assert called["n"] == 0


def _gold_cad(desc: str = "21680-1 PLATE") -> dict[str, Any]:
    return {
        "Description": desc,
        "ProductType": 100,
        "Category": "Cad",
        "BadgeString": "PR",
        "UnitCost": 12.5,
        "MaterialCost": 1.1,
        "Material": "A36",
        "Thickness": 0.25,
        "Machine": "Laser",
        "OperationCostList": [
            {"OperationName": "Profile", "OperationLabel": "PR", "CalculatorName": "Laser", "UnitTime": 0.03},
            {"OperationName": "Profile", "OperationLabel": "PR", "CalculatorName": "Drafting", "UnitTime": 0.05},
            {"OperationName": "Profile", "OperationLabel": "PR", "CalculatorName": "Laser-Setup", "UnitTime": 0.16},
            {"OperationName": "Profile", "OperationLabel": "PR", "CalculatorName": "Sheet Loading", "UnitTime": 0.05},
            {"OperationName": "Profile", "OperationLabel": "PR", "CalculatorName": "Deburr", "UnitTime": 0.03},
        ],
    }


def _gold_lin(desc: str = "21679-1 TUBE") -> dict[str, Any]:
    return {
        "Description": desc,
        "ProductType": 30,
        "Category": "Linear",
        "IsLinear": True,
        "Machine": "Saw",
        "Length": 16,
        "UnitCost": 7.63,
        "MaterialCost": 0.55,
        "SKU": "RT",
        "BadgeString": "",
        "OperationCostList": [
            {"CalculatorName": "Saw", "OperationName": "Cut"},
            {"CalculatorName": "Saw Setup", "OperationName": "Cut"},
        ],
    }


def test_push_job_no_cookie_fails_without_quickadd(tmp_path: Path):
    pdf = tmp_path / "part.pdf"
    stp = tmp_path / "part.stp"
    pdf.write_bytes(b"%PDF")
    stp.write_bytes(b"ISO")
    client = MagicMock()
    client.config.website_cookie = ""
    client.get_json.return_value = {
        "QuoteNumber": "part",
        "ItemCount": 0,
        "ItemList": [],
    }
    service = SecturaFabPushService(client=client)
    with patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "create_quote", return_value="qid"
    ) as create_q, patch.object(
        service, "allocate_quote_number", return_value="part"
    ), patch.object(
        service, "quick_add_cad", return_value={"ok": True}
    ) as qadd, patch.object(
        service, "finish_cad_files", return_value=[]
    ) as finish, patch.object(
        service, "apply_item_categories", return_value=[]
    ), patch(
        "secturafab.push.refresh_bom_rows_for_push", return_value=([], [])
    ), patch(
        "secturafab.push.extract_assembly_description", return_value=None
    ):
        result = service.push_job(
            title="part",
            pdf_filename="part.pdf",
            pdf_path=pdf,
            stp_path=stp,
            takeoff={"library": {"part_key": "part"}},
            times={},
            job_id=2,
        )
    assert result.ok is False
    create_q.assert_called_once()
    qadd.assert_not_called()
    finish.assert_called()
    blob = " ".join(result.notes or []) + " " + (result.error or "")
    assert "Chrome" in blob or "session" in blob.lower()
    assert "quickAddCAD" not in blob
    assert "falling back" not in blob


def test_push_job_cookie_uses_finish_not_quickadd(tmp_path: Path):
    pdf = tmp_path / "21678-1.pdf"
    stp = tmp_path / "21678-1.STEP"
    pdf.write_bytes(b"%PDF")
    stp.write_bytes(b"ISO")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=test"
    populated = {
        "QuoteNumber": "21678-1",
        "ItemCount": 12,
        "ItemList": [_gold_cad("21680-1 PLATE"), _gold_lin("21679-1 TUBE")],
    }
    _n = {"i": 0}

    def _get_json(_path):
        _n["i"] += 1
        return {"QuoteNumber": "21678-1", "ItemCount": 0, "ItemList": []} if _n["i"] == 1 else populated

    client.get_json.side_effect = _get_json
    service = SecturaFabPushService(client=client)
    finish = MagicMock(return_value=["Finish CAD"])
    with patch.object(service, "finish_cad_files", finish), patch.object(
        service, "nest_after_finish", return_value=["Nest"]
    ), patch.object(
        service, "upload_drawings_quote_request", return_value="qr"
    ), patch.object(
        service, "create_quote", return_value="qid"
    ), patch.object(
        service, "allocate_quote_number", return_value="21678-1"
    ), patch.object(
        service, "quick_add_cad"
    ) as qadd, patch(
        "secturafab.push.ensure_weld_ops", return_value=["Attached Weld"]
    ), patch(
        "secturafab.push.ensure_imperial_item_units", return_value=[]
    ), patch(
        "secturafab.push.apply_bom_quantities", return_value=[]
    ), patch(
        "secturafab.push.refresh_bom_rows_for_push", return_value=([], [])
    ), patch(
        "secturafab.push.extract_assembly_description", return_value="KNUCKLE"
    ):
        result = service.push_job(
            title="21678-1",
            pdf_filename="21678-1.pdf",
            pdf_path=pdf,
            stp_path=stp,
            takeoff={"library": {"part_key": "21678-1"}},
            times={"weld_minutes": 10, "total_inches": 20},
            job_id=1,
        )
    assert result.ok is True
    finish.assert_called_once()
    qadd.assert_not_called()
    import secturafab.push as pushmod

    assert hasattr(pushmod, "ensure_laser_profile_ops")
    assert hasattr(pushmod, "finalize_quote_ops")
    assert hasattr(pushmod, "quick_add_cad") or hasattr(SecturaFabPushService, "quick_add_cad")


def test_push_job_finish_failure_fails_without_quickadd(tmp_path: Path):
    pdf = tmp_path / "part.pdf"
    stp = tmp_path / "part.stp"
    pdf.write_bytes(b"%PDF")
    stp.write_bytes(b"ISO")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=test"
    client.get_json.return_value = {
        "QuoteNumber": "part",
        "ItemCount": 0,
        "ItemList": [],
    }
    service = SecturaFabPushService(client=client)

    def _finish_fail(**kwargs):
        raise SecturaFabWebsiteAuthError(WEBSITE_AUTH_GAP)

    with patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "create_quote", return_value="qid"
    ) as create_q, patch.object(
        service, "allocate_quote_number", return_value="part"
    ), patch.object(
        service, "finish_cad_files", side_effect=_finish_fail
    ), patch.object(
        service, "quick_add_cad", return_value={"ok": True}
    ) as qadd, patch(
        "secturafab.push.refresh_bom_rows_for_push", return_value=([], [])
    ), patch(
        "secturafab.push.extract_assembly_description", return_value=None
    ):
        result = service.push_job(
            title="part",
            pdf_filename="part.pdf",
            pdf_path=pdf,
            stp_path=stp,
            takeoff={"library": {"part_key": "part"}},
            times={},
            job_id=3,
        )
    assert result.ok is False
    create_q.assert_called_once()
    qadd.assert_not_called()
    blob = " ".join(result.notes or []) + " " + (result.error or "")
    assert "Chrome" in blob or "session" in blob.lower()
    assert "falling back" not in blob


def test_push_pdf_only_with_cookie_uses_image_files_finish(tmp_path: Path):
    pdf = tmp_path / "lonely.pdf"
    pdf.write_bytes(b"%PDF")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=test"
    populated = {
        "QuoteNumber": "lonely",
        "ItemCount": 1,
        "ItemList": [_gold_cad("lonely")],
    }
    _n = {"i": 0}

    def _get_json(_path):
        _n["i"] += 1
        return {"QuoteNumber": "lonely", "ItemCount": 0, "ItemList": []} if _n["i"] == 1 else populated

    client.get_json.side_effect = _get_json
    service = SecturaFabPushService(client=client)
    pdf_finish = MagicMock(return_value=["Image Files Finish"])
    with patch.object(service, "finish_pdf_files", pdf_finish), patch.object(
        service, "nest_after_finish", return_value=[]
    ), patch.object(
        service, "upload_drawings_quote_request", return_value="qr"
    ), patch.object(
        service, "create_quote", return_value="qid"
    ) as create_q, patch.object(
        service, "allocate_quote_number", return_value="lonely"
    ), patch.object(
        service, "quick_add_cad"
    ) as qadd, patch(
        "secturafab.pdf_assembly_ops.build_single_pdf_quote"
    ) as old_pdf, patch(
        "secturafab.push.ensure_weld_ops", return_value=[]
    ), patch(
        "secturafab.push.ensure_imperial_item_units", return_value=[]
    ), patch(
        "secturafab.push.apply_bom_quantities", return_value=[]
    ), patch(
        "secturafab.push.refresh_bom_rows_for_push", return_value=([], [])
    ), patch(
        "secturafab.push.extract_assembly_description", return_value=None
    ):
        result = service.push_job(
            title="lonely Title",
            pdf_filename="lonely.pdf",
            pdf_path=pdf,
            stp_path=None,
            takeoff={"library": {}},
            times={},
            job_id=99,
        )
    assert result.ok is True
    pdf_finish.assert_called_once()
    qadd.assert_not_called()
    old_pdf.assert_not_called()
    create_q.assert_called_once()


def test_website_request_login_redirect_is_auth_gap():
    from secturafab.client import SecturaFabClient
    from secturafab.config import SecturaFabConfig

    client = SecturaFabClient.__new__(SecturaFabClient)
    client.config = SecturaFabConfig(client_id="x", client_secret="y")
    client._token = MagicMock()
    client._token.authorization_header = "Bearer tok"
    client._token.is_expired = False
    session = MagicMock()
    resp = MagicMock()
    resp.status_code = 302
    resp.headers = {"Location": "/Account/Login?ReturnUrl=%2FQuote%2FAddItem_DXFFiles"}
    resp.text = ""
    session.request.return_value = resp
    client.session = session
    client.authenticate = lambda force=False: client._token  # type: ignore[method-assign]
    with pytest.raises(SecturaFabWebsiteAuthError, match="Chrome|session"):
        client.website_request("POST", "/Quote/AddItem_DXFFiles", json={})


def test_classify_filelist_restores_dashed_cad_pn():
    service = SecturaFabPushService(client=MagicMock())
    rows = [
        {
            "ErrorStatus": 0,
            "Qty": 1,
            "FileName": "14500.pdf",
            "Name": "14500",
            "SourceDataID": "src-1",
            "FileID": "file-1",
            "Stock_X": 11.0,
        }
    ]
    classified, _notes = service.classify_cadimport_rows(
        rows,
        default_material="A36",
        default_thickness="0.25",
        bom_rows=[{"part_no": "14500-1", "qty": 1, "description": "PEDESTAL TOP PLATE"}],
        library={},
        extra_pdfs=None,
        qty=1,
    )
    assert classified[0]["Name"] == "14500-1"
    assert str(classified[0]["Description"]).startswith("14500-1")
    assert classified[0]["SourceDataID"] == "src-1"
    assert classified[0]["FileID"] == "file-1"


def test_effective_cookie_prefers_config_not_chrome():
    from secturafab.browser_session import effective_website_cookie
    from secturafab.config import SecturaFabConfig

    cfg = SecturaFabConfig(website_cookie="ASP.NET_SessionId=from-env")
    assert effective_website_cookie(cfg) == "ASP.NET_SessionId=from-env"


def test_effective_cookie_reads_sectura_website_cookie_env(monkeypatch):
    from secturafab.browser_session import effective_website_cookie

    monkeypatch.delenv("SECTURAFAB_WEBSITE_COOKIE", raising=False)
    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=from-box")
    assert effective_website_cookie() == "ASP.NET_SessionId=from-box"


def test_effective_cookie_reads_cookie_file(tmp_path: Path, monkeypatch):
    from secturafab.browser_session import effective_website_cookie

    path = tmp_path / "box.cookie"
    path.write_text("ASP.NET_SessionId=box-sess\n", encoding="utf-8")
    monkeypatch.delenv("SECTURAFAB_WEBSITE_COOKIE", raising=False)
    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", str(path))
    assert effective_website_cookie() == "ASP.NET_SessionId=box-sess"


def test_effective_cookie_does_not_call_windows_discover(monkeypatch):
    from secturafab.browser_session import effective_website_cookie
    from secturafab.config import SecturaFabConfig

    monkeypatch.delenv("SECTURA_WEBSITE_COOKIE", raising=False)
    monkeypatch.delenv("SECTURAFAB_WEBSITE_COOKIE", raising=False)
    with patch(
        "secturafab.browser_session.discover_sectura_website_cookie",
        side_effect=AssertionError("Windows unwrap is dead"),
    ) as disc:
        assert effective_website_cookie(SecturaFabConfig()) == ""
        disc.assert_not_called()


def test_public_discover_never_unwraps_windows_chrome(monkeypatch):
    from secturafab import browser_session as bs

    monkeypatch.delenv("SECTURA_WEBSITE_COOKIE", raising=False)
    monkeypatch.delenv("SECTURAFAB_WEBSITE_COOKIE", raising=False)
    with patch.object(
        bs, "_discover_uncached", side_effect=AssertionError("must not unwrap")
    ), patch.object(
        bs, "_memscan_abe_key", side_effect=AssertionError("must not memscan")
    ), patch.object(
        bs, "_discover_windows_chrome", side_effect=AssertionError("must not unwrap")
    ):
        assert bs.discover_sectura_website_cookie(force=True) == ""
    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=box")
    with patch.object(
        bs, "_discover_windows_chrome", side_effect=AssertionError("must not unwrap")
    ):
        assert bs.discover_sectura_website_cookie(force=True) == "ASP.NET_SessionId=box"


def test_finish_pdf_and_linear_never_call_windows_discover(monkeypatch):
    from secturafab.client import SecturaFabClient, SecturaFabWebsiteAuthError
    from secturafab.config import SecturaFabConfig
    from secturafab.push import SecturaFabPushService

    monkeypatch.delenv("SECTURA_WEBSITE_COOKIE", raising=False)
    monkeypatch.delenv("SECTURAFAB_WEBSITE_COOKIE", raising=False)
    client = SecturaFabClient.__new__(SecturaFabClient)
    client.config = SecturaFabConfig(website_cookie="")
    svc = SecturaFabPushService(client=client)
    with patch(
        "secturafab.browser_session._discover_windows_chrome",
        side_effect=AssertionError("must not unwrap"),
    ), patch(
        "secturafab.browser_session._discover_uncached",
        side_effect=AssertionError("must not unwrap"),
    ):
        with pytest.raises(SecturaFabWebsiteAuthError):
            svc.finish_pdf_files(
                quote_id="qid",
                pdf_files=[],
                material="A36",
                thickness="0.25",
                qty=1,
                description="x",
            )
        with pytest.raises(SecturaFabWebsiteAuthError):
            svc.finish_linear_bom_rows(
                quote_id="qid",
                linear_rows=[{"part_no": "29860-3", "description": "ANGLE", "qty": 1}],
                material="A36",
                library={},
                extra_pdfs=[],
            )


def test_discover_cookie_from_sqlite(tmp_path: Path):
    import sqlite3

    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE cookies (host_key TEXT, name TEXT, value TEXT, encrypted_value BLOB)"
    )
    conn.execute(
        "INSERT INTO cookies VALUES (?,?,?,?)",
        (".secturafab.com", ".AspNet.ApplicationCookie", "auth-token", b""),
    )
    conn.execute(
        "INSERT INTO cookies VALUES (?,?,?,?)",
        ("www.secturafab.com", "ASP.NET_SessionId", "sess", b""),
    )
    conn.commit()
    conn.close()
    profile = {
        "label": "test",
        "cookies": db,
        "local_state": tmp_path / "Local State",
    }
    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]):
        header = bs._discover_windows_chrome(force=True)
    assert ".AspNet.ApplicationCookie=auth-token" in header
    assert "ASP.NET_SessionId=sess" in header
    status = bs.discover_status()
    assert status["session_found"] is True
    assert status["source"] == "test"
    assert "auth-token" not in str(status)
    assert status.get("error") in {"", None}


def _write_cookie_db(path: Path, *, host: str = ".secturafab.com") -> None:
    import sqlite3

    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute(
        "CREATE TABLE cookies (host_key TEXT, name TEXT, value TEXT, encrypted_value BLOB)"
    )
    conn.execute(
        "INSERT INTO cookies VALUES (?,?,?,?)",
        (host, ".AspNet.ApplicationCookie", "auth-token", b""),
    )
    conn.execute(
        "INSERT INTO cookies VALUES (?,?,?,?)",
        ("www.secturafab.com", "ASP.NET_SessionId", "sess", b""),
    )
    conn.commit()
    conn.close()


def test_locked_shutil_copy_still_reads_chrome_default(tmp_path: Path):
    """WinError 32 on shutil.copy2 must not hide Chrome Default cookies."""
    from secturafab import browser_session as bs

    db = tmp_path / "Default" / "Network" / "Cookies"
    _write_cookie_db(db)
    profile = {
        "label": "chrome:Default",
        "cookies": db,
        "local_state": tmp_path / "Local State",
        "profile_dir": tmp_path / "Default",
        "history_hit": True,
    }

    def _locked(*_a, **_k):
        raise OSError(32, "The process cannot access the file")

    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]), patch.object(
        bs.shutil, "copy2", side_effect=_locked
    ):
        header = bs._discover_windows_chrome(force=True)
    assert header
    assert bs.session_found() is True
    assert bs.last_discover_source() == "chrome:Default"
    assert "auth-token" not in bs.last_discover_error()


def test_share_copy_when_sqlite_backup_and_copy2_fail(tmp_path: Path):
    import sqlite3

    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    _write_cookie_db(db)
    profile = {
        "label": "chrome:Default",
        "cookies": db,
        "local_state": tmp_path / "Local State",
        "profile_dir": tmp_path,
        "history_hit": True,
    }

    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]), patch.object(
        bs, "_sqlite_backup_nolock", side_effect=sqlite3.Error("locked")
    ), patch.object(bs.shutil, "copy2", side_effect=OSError(32, "locked")):
        header = bs._discover_windows_chrome(force=True)
    assert header
    assert bs.discover_status()["session_found"] is True


def test_chrome_default_ranks_before_profile_1():
    from secturafab.browser_session import _profile_rank

    default = {
        "label": "chrome:Default",
        "cookies": "C:/x/Default/Network/Cookies",
        "history_hit": True,
    }
    profile1 = {
        "label": "chrome:Profile 1",
        "cookies": "C:/x/Profile 1/Network/Cookies",
        "history_hit": False,
    }
    edge = {
        "label": "edge:Default",
        "cookies": "C:/x/Edge/Default/Network/Cookies",
        "history_hit": False,
    }
    ranked = sorted([profile1, edge, default], key=_profile_rank)
    assert ranked[0]["label"] == "chrome:Default"
    assert ranked[1]["label"] == "chrome:Profile 1"


def test_snapshot_uses_lock_bypass_when_share_and_copy2_fail(tmp_path: Path):
    """Exclusive Chrome lock: share-open/copy2 fail; backup/dup/VSS must still copy."""
    import shutil
    import sqlite3

    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    _write_cookie_db(db)
    dest = tmp_path / "snap" / "Cookies"
    dest.parent.mkdir()

    def _bypass(src: Path, dest_path: Path, **_k) -> None:
        shutil.copy2(src, dest_path)

    with patch.object(bs, "_sqlite_backup_nolock", side_effect=sqlite3.Error("locked")), patch.object(
        bs, "_share_copy_with_wal", side_effect=OSError(32, "locked")
    ), patch.object(
        bs, "_shutil_copy_with_wal", side_effect=OSError(32, "locked")
    ), patch.object(bs, "_win_lock_bypass_with_wal", side_effect=_bypass):
        bs._snapshot_sqlite_file(db, dest)
    assert dest.is_file() and dest.stat().st_size > 0


def test_dup_handle_timeout_raises_quickly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from secturafab import browser_session as bs

    monkeypatch.setattr(bs, "_DUP_HANDLE_TIMEOUT_S", 0.35)

    def _hang(*_a, **_k):
        time.sleep(30)

    monkeypatch.setattr(bs, "_win_dup_handle_copy_inner", _hang)
    t0 = time.monotonic()
    with pytest.raises(OSError) as ei:
        bs._win_dup_handle_copy(tmp_path / "Cookies", tmp_path / "out")
    assert "dup_handle_timeout" in str(ei.value)
    assert time.monotonic() - t0 < 3.0


def test_lock_bypass_times_out_dup_then_uses_backup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import shutil

    from secturafab import browser_session as bs

    monkeypatch.setattr(bs, "_DUP_HANDLE_TIMEOUT_S", 0.35)
    monkeypatch.setattr(bs.os, "name", "nt")
    bs._cache["dup_timed_out"] = False
    bs._cache["lock_bypass_pinned"] = False
    bs._cache["lock_bypass"] = ""
    db = tmp_path / "Cookies"
    _write_cookie_db(db)
    dest = tmp_path / "snap" / "Cookies"
    dest.parent.mkdir()

    def _hang(*_a, **_k):
        time.sleep(30)

    def _ok(src: Path, dest_path: Path) -> None:
        shutil.copy2(src, dest_path)

    def _fail(*_a, **_k):
        raise OSError(32, "skip")

    with patch.object(bs, "_win_dup_handle_copy_inner", _hang), patch.object(
        bs, "_win_backup_copy", _ok
    ), patch.object(bs, "_win_ntcreatefile_backup_copy", _fail), patch.object(
        bs, "_win_esentutl_copy", _fail
    ), patch.object(bs, "_win_robocopy_backup_copy", _fail), patch.object(
        bs, "_win_vss_existing_copy", _fail
    ):
        t0 = time.monotonic()
        bs._win_lock_bypass_with_wal(db, dest, allow_vss=False)
    assert dest.is_file() and dest.stat().st_size > 0
    assert bs._cache["lock_bypass"] == "backup_priv"
    assert time.monotonic() - t0 < 4.0


def test_nt_native_path_strips_extended_prefix():
    from secturafab.browser_session import _nt_native_path

    assert _nt_native_path(r"C:\Users\kyle\Cookies") == r"\??\C:\Users\kyle\Cookies"
    assert _nt_native_path(r"\\?\C:\Users\kyle\Cookies") == r"\??\C:\Users\kyle\Cookies"
    assert _nt_native_path(r"\??\C:\Users\kyle\Cookies") == r"\??\C:\Users\kyle\Cookies"


def test_rank_browser_pids_puts_network_first():
    from secturafab import browser_session as bs

    def _cmd(pid: int) -> str:
        return {
            11: r"chrome.exe",
            22: r"chrome.exe --type=utility --utility-sub-type=network.mojom.NetworkService",
            33: r"chrome.exe --type=renderer",
            44: r"chrome.exe --type=utility --utility-sub-type=storage.mojom.StorageService",
        }[pid]

    with patch.object(bs, "_process_command_line", side_effect=_cmd):
        ranked = bs._rank_browser_pids([11, 22, 33, 44])
    assert ranked[0] == 22
    assert ranked[1] == 44
    assert 11 in ranked


def test_lock_bypass_creates_vss_when_allowed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import shutil

    from secturafab import browser_session as bs

    monkeypatch.setattr(bs.os, "name", "nt")
    bs._cache["dup_timed_out"] = False
    bs._cache["lock_bypass_pinned"] = False
    bs._cache["lock_bypass"] = ""
    db = tmp_path / "Cookies"
    _write_cookie_db(db)
    dest = tmp_path / "snap" / "Cookies"
    dest.parent.mkdir()
    order: list[str] = []

    def _fail(name: str):
        def _inner(*_a, **_k):
            order.append(name)
            raise OSError(32, name)

        return _inner

    def _vss(src: Path, dest_path: Path) -> None:
        order.append("vss")
        shutil.copy2(src, dest_path)

    with patch.object(bs, "_win_dup_handle_copy", _fail("dup_handle")), patch.object(
        bs, "_win_backup_copy", _fail("backup_priv")
    ), patch.object(bs, "_win_ntcreatefile_backup_copy", _fail("nt_backup")), patch.object(
        bs, "_win_vss_copy", _vss
    ):
        bs._win_lock_bypass_with_wal(db, dest, allow_vss=True)
    assert dest.is_file()
    assert bs._cache["lock_bypass"] == "vss"
    assert order == ["dup_handle", "backup_priv", "nt_backup", "vss"]


def test_history_snapshot_does_not_scan_handles(tmp_path: Path):
    import sqlite3

    from secturafab import browser_session as bs

    hist = tmp_path / "History"
    conn = sqlite3.connect(str(hist))
    conn.execute("CREATE TABLE urls (url TEXT)")
    conn.commit()
    conn.close()

    def _nope(*_a, **_k):
        raise AssertionError("lock bypass must not run for History")

    with patch.object(bs, "_win_lock_bypass_with_wal", side_effect=_nope):
        assert bs._history_has_sectura(tmp_path) is False


def test_win_paths_match_strips_extended_prefix():
    from secturafab.browser_session import _paths_match

    assert _paths_match(
        r"\\?\C:\Users\kyle\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies",
        r"C:\Users\kyle\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies",
    )
    assert _paths_match(
        r"\Device\HarddiskVolume3\Users\kyle\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies",
        r"D:\unused\Google\Chrome\User Data\Default\Network\Cookies",
    )
    # FileNameInfo is volume-relative (no drive) when GetFinalPathName is empty.
    assert _paths_match(
        r"\Users\kyle\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies",
        r"C:\Users\kyle\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies",
    )


def test_snapshot_failure_reports_bypass_not_bare_oserror(tmp_path: Path):
    import sqlite3

    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    db.write_bytes(b"x")
    profile = {
        "label": "chrome:Default",
        "cookies": db,
        "local_state": tmp_path / "Local State",
        "profile_dir": tmp_path,
        "history_hit": True,
    }

    def _fail(*_a, **_k):
        raise OSError(32, "locked")

    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]), patch.object(
        bs, "_sqlite_backup_nolock", side_effect=sqlite3.Error("locked")
    ), patch.object(bs, "_share_copy_with_wal", side_effect=_fail), patch.object(
        bs, "_shutil_copy_with_wal", side_effect=_fail
    ), patch.object(bs, "_win_lock_bypass_with_wal", side_effect=_fail), patch.object(
        bs.time, "sleep", return_value=None
    ):
        header = bs._discover_windows_chrome(force=True)
    assert header == ""
    status = bs.discover_status()
    assert status["session_found"] is False
    assert status["source"] == "chrome:Default"
    err = status["error"]
    assert "OSError" not in err or "nolock" in err or "lock_bypass" in err
    assert "lock_bypass=" in err
    assert "do not paste" in err.lower()
    assert status["lock_bypass"]
    assert status["lock_bypass"] != ""
    assert status["lock_bypass"]
    assert "open_copy_failed" not in status["lock_bypass"]


def test_localserver32_cmd_uses_console():
    from secturafab.browser_session import _localserver32_cmd

    cmd = _localserver32_cmd(
        Path(r"C:\Program Files\Google\Chrome\Application\151.0.7922.174\elevation_service.exe")
    )
    assert "--console" in cmd
    assert "-Embedding" in cmd
    assert "elevation_service.exe" in cmd


def test_rm_file_pids_empty_off_windows(tmp_path: Path):
    from secturafab.browser_session import _rm_file_pids

    assert _rm_file_pids(tmp_path / "Cookies") == []


def test_unwrap_keeps_helper_timeout_as_chrome_dir():
    from secturafab import browser_session as bs

    b64 = base64.b64encode(b"APPB" + b"\x01" * 40).decode("ascii")

    def _no_elevator(*_a, **_k):
        raise AssertionError("in-process CoCreate must not run")

    with patch.object(
        bs, "_elevator_decrypt_via_chrome_dir", return_value=(None, "helper:timeout")
    ), patch.object(bs, "_elevator_decrypt", side_effect=_no_elevator):
        key, status, hr = bs._unwrap_app_bound_key(b64, v20_sample=b"v20" + b"\x00" * 40)
    assert key is None
    assert status == "chrome_dir"
    assert hr == "helper:timeout"
    assert "CLASSNOTREG" not in hr


def test_hr_label_surfaces_classnotreg():
    from secturafab.browser_session import _hr_label, _label_classnotreg

    assert _hr_label(0x80040154) == "0x80040154:CLASSNOTREG"
    assert _hr_label(-2147221164) == "0x80040154:CLASSNOTREG"
    assert _hr_label(0x80040155) == "0x80040155:IIDNOTREG"
    assert _hr_label(0x80080005) == "0x80080005:SERVER_EXEC_FAILURE"
    assert "CLASSNOTREG" in _label_classnotreg("0x80040154", "no_elevation_service")
    assert "no_elevation_service" in _label_classnotreg("0x80040154", "no_elevation_service")
    assert _hr_label(0) == "0x00000000"


def test_elevation_service_exes_finds_versioned_151(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from secturafab import browser_session as bs

    root = tmp_path / "Google" / "Chrome" / "Application"
    root.mkdir(parents=True)
    (root / "chrome.exe").write_bytes(b"mz")
    ver = root / "151.0.7922.174"
    ver.mkdir()
    (ver / "chrome.exe").write_bytes(b"mz")
    (ver / "elevation_service.exe").write_bytes(b"mz")
    monkeypatch.setenv("PROGRAMFILES", str(tmp_path))
    monkeypatch.delenv("PROGRAMFILES(X86)", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    with patch.object(bs, "_chrome_exe_from_registry", return_value=Path()):
        exes = bs._elevation_service_exes()
        dirs = bs._chrome_helper_dirs()
    assert any(p.name.lower() == "elevation_service.exe" for p in exes)
    assert dirs and dirs[0].name == "151.0.7922.174"


def test_prepare_elevator_without_exe_is_classnotreg_reason():
    from secturafab import browser_session as bs

    with patch.object(bs.os, "name", "nt"), patch.object(
        bs, "_elevation_service_exes", return_value=[]
    ):
        assert bs._prepare_elevator_com() == "no_elevation_service"


def test_unwrap_helper_miss_is_chrome_dir_not_classnotreg():
    from secturafab import browser_session as bs

    b64 = base64.b64encode(b"APPB" + b"\x01" * 40).decode("ascii")

    def _no_elevator(*_a, **_k):
        raise AssertionError("in-process CoCreate must not run")

    with patch.object(
        bs, "_elevator_decrypt_via_chrome_dir", return_value=(None, "csc_missing")
    ), patch.object(bs, "_elevator_decrypt", side_effect=_no_elevator):
        key, status, hr = bs._unwrap_app_bound_key(b64, v20_sample=b"v20" + b"\x00" * 40)
    assert key is None
    assert status == "chrome_dir"
    assert hr == "csc_missing"
    assert "CLASSNOTREG" not in hr
    assert "0x80040154" not in hr


def test_discover_abe_hr_is_chrome_dir(tmp_path: Path):
    import sqlite3

    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE cookies (host_key TEXT, name TEXT, value TEXT, encrypted_value BLOB)"
    )
    conn.execute(
        "INSERT INTO cookies VALUES (?,?,?,?)",
        ("www.secturafab.com", "ASP.NET_SessionId", "", b"v20" + b"\x00" * 40),
    )
    conn.commit()
    conn.close()
    local_state = tmp_path / "Local State"
    local_state.write_text(
        json.dumps(
            {"os_crypt": {"app_bound_encrypted_key": base64.b64encode(b"APPB" + b"\x01" * 40).decode()}}
        ),
        encoding="utf-8",
    )
    profile = {
        "label": "chrome:Default",
        "cookies": db,
        "local_state": local_state,
        "profile_dir": tmp_path,
        "history_hit": True,
    }
    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]), patch.object(
        bs, "_unwrap_app_bound_key", return_value=(None, "chrome_dir", "csc_missing")
    ):
        header = bs._discover_windows_chrome(force=True)
    assert header == ""
    status = bs.discover_status()
    assert status["abe"] == "chrome_dir"
    assert status["abe_hr"] == "csc_missing"
    assert "CLASSNOTREG" not in status["abe_hr"]
    assert "csc_missing" in status["error"]
    assert "do not paste" in status["error"].lower()


def test_app_bound_strips_appb_prefix():
    from secturafab.browser_session import _accept_aes_key, _app_bound_ciphertext

    inner = b"\x01\x02\x03\x04" + (b"\xab" * 20)
    b64 = base64.b64encode(b"APPB" + inner).decode("ascii")
    assert _app_bound_ciphertext(b64) == inner
    assert _accept_aes_key(b"x" * 32) == b"x" * 32
    assert _accept_aes_key(b"x" * 16) == b"x" * 16
    assert _accept_aes_key(b"too-short") is None
    packed = (32).to_bytes(4, "little") + (b"k" * 32) + b"trailer"
    assert _accept_aes_key(packed) == b"k" * 32


def test_v20_cookie_uses_abe_key_never_v10():
    from secturafab.browser_session import _BrowserKeys, _decrypt_cookie_value, _v20_cookie_text

    abe = os.urandom(32)
    v10 = os.urandom(32)
    nonce = os.urandom(12)
    secret = b"sectura-session-value"
    plain = (b"\x11" * 32) + secret
    payload = _aes_gcm_encrypt(plain, abe, nonce)
    blob = b"v20" + nonce + payload
    assert _decrypt_cookie_value(blob, _BrowserKeys(abe=abe, v10=v10)) == secret.decode()
    assert _decrypt_cookie_value(blob, _BrowserKeys(abe=None, v10=abe)) == ""
    assert _v20_cookie_text(plain) == secret.decode()


def test_v20_blobs_fail_closed_without_abe(tmp_path: Path):
    import sqlite3

    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE cookies (host_key TEXT, name TEXT, value TEXT, encrypted_value BLOB)"
    )
    conn.execute(
        "INSERT INTO cookies VALUES (?,?,?,?)",
        (
            "www.secturafab.com",
            "ASP.NET_SessionId",
            "",
            b"v20" + b"\x00" * 40,
        ),
    )
    conn.commit()
    conn.close()
    local_state = tmp_path / "Local State"
    local_state.write_text(
        json.dumps(
            {
                "os_crypt": {
                    "app_bound_encrypted_key": base64.b64encode(b"APPB" + b"\x01" * 40).decode(),
                    "encrypted_key": base64.b64encode(b"DPAPI" + b"\x02" * 40).decode(),
                }
            }
        ),
        encoding="utf-8",
    )
    profile = {
        "label": "chrome:Default",
        "cookies": db,
        "local_state": local_state,
        "profile_dir": tmp_path,
        "history_hit": True,
    }
    fake_v10 = b"V" * 32
    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]), patch.object(
        bs, "_unwrap_app_bound_key", return_value=(None, "failed", "0x80070005")
    ), patch.object(bs, "_v10_os_crypt_key", return_value=fake_v10):
        header = bs._discover_windows_chrome(force=True)
    assert header == ""
    assert bs.session_found() is False
    status = bs.discover_status()
    assert status["session_found"] is False
    assert status["source"] == "chrome:Default"
    assert status["abe"] == "failed"
    assert status["abe_hr"] == "0x80070005"
    assert status["v20_blobs"] == 1
    assert status["v20_ok"] == 0
    assert "0x80070005" in status["error"]
    assert "do not paste" in status["error"].lower()
    assert "auth-token" not in str(status)
    assert fake_v10.hex() not in str(status)


def test_elevator_overflow_does_not_crash_discover(tmp_path: Path):
    """SysFreeString OverflowError must set abe=failed and keep source."""
    import sqlite3

    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE cookies (host_key TEXT, name TEXT, value TEXT, encrypted_value BLOB)"
    )
    conn.execute(
        "INSERT INTO cookies VALUES (?,?,?,?)",
        ("www.secturafab.com", "ASP.NET_SessionId", "", b"v20" + b"\x00" * 40),
    )
    conn.commit()
    conn.close()
    local_state = tmp_path / "Local State"
    local_state.write_text(
        json.dumps(
            {"os_crypt": {"app_bound_encrypted_key": base64.b64encode(b"APPB" + b"\x01" * 40).decode()}}
        ),
        encoding="utf-8",
    )
    profile = {
        "label": "chrome:Default",
        "cookies": db,
        "local_state": local_state,
        "profile_dir": tmp_path,
        "history_hit": True,
    }
    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]), patch.object(
        bs, "_elevator_decrypt_via_chrome_dir",
        side_effect=OverflowError("int too long to convert"),
    ), patch.object(
        bs, "_elevator_decrypt",
        side_effect=AssertionError("in-process CoCreate must not run"),
    ):
        header = bs._discover_windows_chrome(force=True)
    assert header == ""
    status = bs.discover_status()
    assert status["session_found"] is False
    assert status["source"] == "chrome:Default"
    assert status["abe"] == "chrome_dir"
    assert status["abe_hr"] == "OverflowError"
    assert status["v20_blobs"] == 1
    assert status["v20_ok"] == 0
    assert "OverflowError" in status["error"]
    assert "do not paste" in status["error"].lower()


def test_local_free_uses_c_void_p_not_raw_int():
    """Win64 LocalFree must get a pointer-width c_void_p, not a raw int."""
    import ctypes
    from ctypes import c_void_p
    from unittest.mock import Mock

    from secturafab.browser_session import _local_free

    k32 = Mock()
    huge = 0x7FFF_FFFF_ABCD_1234
    _local_free(k32, huge)
    k32.LocalFree.assert_called_once()
    arg = k32.LocalFree.call_args[0][0]
    assert isinstance(arg, c_void_p)
    assert int(arg.value) == huge
    k32.LocalFree.side_effect = ctypes.ArgumentError(
        "argument 1: OverflowError: int too long to convert"
    )
    _local_free(k32, c_void_p(huge))  # must not raise


def test_app_bound_layout_keeps_dpapi_fp_when_unprotect_raises():
    import ctypes

    from secturafab import browser_session as bs

    blob = b"\x01\x00\x00\x00" + os.urandom(636)
    assert len(blob) == 640
    with patch.object(
        bs,
        "_dpapi_unprotect_local",
        side_effect=ctypes.ArgumentError("argument 1: OverflowError: int too long to convert"),
    ):
        fp, views = bs._app_bound_layout_views(blob)
    assert fp.startswith("appb:dpapi:640")
    assert views


def test_v10_os_crypt_key_swallows_localfree_argument_error():
    import ctypes

    from secturafab import browser_session as bs

    b64 = base64.b64encode(b"DPAPI" + b"\x01\x00\x00\x00" + os.urandom(32)).decode("ascii")
    with patch.object(
        bs,
        "_dpapi_unprotect",
        side_effect=ctypes.ArgumentError("argument 1: OverflowError: int too long to convert"),
    ):
        assert bs._v10_os_crypt_key(b64) is None


def test_bstr_free_uses_c_void_p_not_raw_int():
    """Win64 SysFreeString must get a pointer-width c_void_p."""
    import ctypes
    from ctypes import c_void_p
    from unittest.mock import Mock

    from secturafab.browser_session import _bstr_free

    ole = Mock()
    huge = 0x7FFF_FFFF_ABCD_1234
    _bstr_free(ole, huge)
    ole.SysFreeString.assert_called_once()
    arg = ole.SysFreeString.call_args[0][0]
    assert isinstance(arg, c_void_p)
    assert int(arg.value) == huge
    ole.SysFreeString.side_effect = OverflowError("int too long to convert")
    _bstr_free(ole, c_void_p(huge))  # must not raise


def test_discover_outer_catch_writes_abe_after_crash(tmp_path: Path):
    from secturafab import browser_session as bs

    profile = {
        "label": "chrome:Default",
        "cookies": tmp_path / "Cookies",
        "local_state": tmp_path / "Local State",
        "profile_dir": tmp_path,
        "history_hit": True,
    }

    def _boom(*_a, **_k):
        bs._cache["lock_bypass"] = "dup_handle"
        bs._cache["source"] = "chrome:Default"
        raise OverflowError("int too long to convert")

    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]), patch.object(
        bs, "_read_cookie_rows", side_effect=_boom
    ):
        header = bs._discover_windows_chrome(force=True)
    assert header == ""
    status = bs.discover_status()
    assert status["session_found"] is False
    assert status["source"] == "chrome:Default"
    assert status["lock_bypass"] == "dup_handle"
    assert status["abe"] == "failed"
    assert status["abe_hr"] == "OverflowError"


def test_v20_discover_succeeds_with_elevator_key(tmp_path: Path):
    import sqlite3

    from secturafab import browser_session as bs

    abe = os.urandom(32)
    nonce = os.urandom(12)
    secret = b"sess-ok"
    payload = _aes_gcm_encrypt((b"\x22" * 32) + secret, abe, nonce)
    db = tmp_path / "Cookies"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE cookies (host_key TEXT, name TEXT, value TEXT, encrypted_value BLOB)"
    )
    conn.execute(
        "INSERT INTO cookies VALUES (?,?,?,?)",
        ("www.secturafab.com", "ASP.NET_SessionId", "", b"v20" + nonce + payload),
    )
    conn.commit()
    conn.close()
    profile = {
        "label": "chrome:Default",
        "cookies": db,
        "local_state": tmp_path / "Local State",
        "profile_dir": tmp_path,
        "history_hit": True,
    }
    keys = bs._BrowserKeys(abe=abe, status="elevator", hr="0x00000000")
    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]), patch.object(
        bs, "_browser_keys", return_value=keys
    ):
        header = bs._discover_windows_chrome(force=True)
    assert "ASP.NET_SessionId=sess-ok" in header
    status = bs.discover_status()
    assert status["session_found"] is True
    assert status["source"] == "chrome:Default"
    assert status["abe"] == "elevator"
    assert status["v20_ok"] == 1
    assert "sess-ok" not in str(status)


def test_finish_session_error_is_env_cookie_only(monkeypatch):
    from secturafab.push import SecturaFabPushService

    monkeypatch.delenv("SECTURA_WEBSITE_COOKIE", raising=False)
    monkeypatch.delenv("SECTURAFAB_WEBSITE_COOKIE", raising=False)
    svc = SecturaFabPushService(MagicMock())
    msg = svc._finish_session_error()
    assert "session_found=false" in msg
    assert "SECTURA_WEBSITE_COOKIE" in msg
    assert "abe=" not in msg
    assert "abe_hr=" not in msg
    assert "lock_bypass=" not in msg
    assert "vss=" not in msg
    assert "do not paste a cookie" in msg.lower()
    assert "quoting pc" in msg.lower() or "unwrap" in msg.lower()


def test_chrome_default_uses_cached_snapshot_when_live_copy_fails(tmp_path: Path):
    """Chrome-open copy can reuse a Cookies DB that already landed."""
    from secturafab import browser_session as bs

    live = tmp_path / "live" / "Cookies"
    live.parent.mkdir()
    live.write_bytes(b"locked")
    cached = tmp_path / "cache" / "Cookies"
    _write_cookie_db(cached)
    profile = {
        "label": "chrome:Default",
        "cookies": live,
        "local_state": tmp_path / "Local State",
        "profile_dir": tmp_path,
        "history_hit": True,
    }

    def _vss_miss(*_a, **_k):
        return False

    with patch.dict(os.environ, {"KANNON_COOKIE_CACHE": str(tmp_path / "cache")}), patch.object(
        bs, "_browser_cookie_dbs", return_value=[profile]
    ), patch.object(bs, "_try_nolock_copy", return_value=False), patch.object(
        bs, "_try_handle_dup_copy", return_value=False
    ), patch.object(bs, "_try_vss_create_copy", side_effect=_vss_miss), patch.object(
        bs, "_sqlite_backup_nolock", side_effect=OSError(32, "locked")
    ), patch.object(bs, "_share_copy_with_wal", side_effect=OSError(32, "locked")), patch.object(
        bs, "_shutil_copy_with_wal", side_effect=OSError(32, "locked")
    ):
        header = bs._discover_windows_chrome(force=True)
    assert header
    status = bs.discover_status()
    assert "cached" in status["lock_bypass"]
    assert status["session_found"] is True
    assert status["source"] == "chrome:Default"


def test_vss_create_hresult_stays_visible_after_fallback(tmp_path: Path):
    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    _write_cookie_db(db)
    profile = {
        "label": "chrome:Default",
        "cookies": db,
        "local_state": tmp_path / "Local State",
        "profile_dir": tmp_path,
        "history_hit": True,
    }

    def _vss_create(*_a, **_k):
        bs._record_vss("create:5")
        return False

    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]), patch.object(
        bs, "_try_nolock_copy", return_value=False
    ), patch.object(
        bs, "_try_vss_create_copy", side_effect=_vss_create
    ):
        header = bs._discover_windows_chrome(force=True)
    assert header
    status = bs.discover_status()
    assert status["vss"] == "create:5"
    assert status["lock_bypass"].startswith("vss=create:5")


def test_lock_bypass_with_vss_prefixes_create_hresult():
    from secturafab import browser_session as bs

    bs._cache["vss"] = "create:5"
    assert (
        bs._lock_bypass_with_vss("dup_handle_not_found")
        == "vss=create:5;dup_handle_not_found"
    )
    bs._cache["vss"] = "ok"
    assert bs._lock_bypass_with_vss("") == "vss"


def test_later_profile_cannot_wipe_default_vss_pin():
    from secturafab import browser_session as bs

    bs._cache["lock_bypass_pinned"] = False
    bs._cache["vss"] = "ok"
    bs._set_lock_bypass("vss", pin=True)
    bs._set_lock_bypass(
        "dup_handle_not_found;backup_priv:errno 6;vss_existing:errno 1"
    )
    assert bs._cache["lock_bypass"] == "vss"
    assert bs._cache["vss"] == "ok"


def test_chrome_default_records_vss_skip_on_linux(tmp_path: Path):
    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    _write_cookie_db(db)
    profile = {
        "label": "chrome:Default",
        "cookies": db,
        "local_state": tmp_path / "Local State",
        "profile_dir": tmp_path,
        "history_hit": True,
    }
    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]):
        header = bs._discover_windows_chrome(force=True)
    assert header
    status = bs.discover_status()
    assert "nolock" in status["lock_bypass"]
    assert status["session_found"] is True


def test_chrome_default_uses_nolock_before_vss(tmp_path: Path):
    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    _write_cookie_db(db)
    profile = {
        "label": "chrome:Default",
        "cookies": db,
        "local_state": tmp_path / "Local State",
        "profile_dir": tmp_path,
        "history_hit": True,
    }

    def _no_vss(*_a, **_k):
        raise AssertionError("VSS must not run when nolock lands Cookies")

    def _no_dup(*_a, **_k):
        raise AssertionError("handle-dup must not run when nolock lands Cookies")

    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]), patch.object(
        bs, "_try_vss_create_copy", side_effect=_no_vss
    ), patch.object(bs, "_try_handle_dup_copy", side_effect=_no_dup):
        header = bs._discover_windows_chrome(force=True)
    assert header
    status = bs.discover_status()
    assert "nolock" in status["lock_bypass"]
    assert status["session_found"] is True
    assert status["source"] == "chrome:Default"


def test_vss_create_script_uses_cim_not_file_drive_arg():
    from secturafab import browser_session as bs

    script = bs._vss_create_ps1()
    assert "Invoke-CimMethod" in script
    assert "Win32_ShadowCopy" in script
    assert "ClientAccessible" in script
    assert "param($ArgsFile)" in script
    assert "param($Drive,$Rel,$Dest,$Status)" not in script


def test_parse_vssadmin_create_output():
    from secturafab import browser_session as bs

    text = (
        "Successfully created shadow copy for 'C:\\'\n"
        "    Shadow Copy ID: {C7C1D1A0-1111-2222-3333-444444444444}\n"
        "    Shadow Copy Volume Name: "
        "\\\\?\\GLOBALROOT\\Device\\HarddiskVolumeShadowCopy12\n"
    )
    parsed = bs._parse_vss_create_output(text)
    assert parsed is not None
    assert parsed[0] == "{C7C1D1A0-1111-2222-3333-444444444444}"
    assert parsed[1].endswith("HarddiskVolumeShadowCopy12")
    assert bs._parse_vss_create_output("VSS none") is None


def test_parse_vss_list_output_newest_globalroot_first():
    from secturafab import browser_session as bs

    text = (
        "Contents of shadow copy set ID: {AAAAAAAA-1111-2222-3333-444444444444}\n"
        "    Shadow Copy Volume: "
        "\\\\?\\GLOBALROOT\\Device\\HarddiskVolumeShadowCopy2\n"
        "Contents of shadow copy set ID: {BBBBBBBB-1111-2222-3333-444444444444}\n"
        "    Shadow Copy Volume: "
        "\\\\?\\GLOBALROOT\\Device\\HarddiskVolumeShadowCopy7\n"
    )
    devices = bs._parse_vss_list_output(text)
    assert devices[0].endswith("HarddiskVolumeShadowCopy7")
    assert devices[1].endswith("HarddiskVolumeShadowCopy2")
    assert all(d.startswith("\\\\?\\GLOBALROOT\\Device\\HarddiskVolumeShadowCopy") for d in devices)
    assert bs._normalize_shadow_device(r"C:\Users\kyle\Cookies") == ""
    assert bs._normalize_shadow_device("HarddiskVolumeShadowCopy9") == (
        "\\\\?\\GLOBALROOT\\Device\\HarddiskVolumeShadowCopy9"
    )


def test_decode_vssadmin_utf16_lists_globalroot():
    from secturafab import browser_session as bs

    text = (
        "Successfully created shadow copy for 'C:\\'\r\n"
        "    Shadow Copy ID: {C7C1D1A0-1111-2222-3333-444444444444}\r\n"
        "    Shadow Copy Volume Name: "
        "\\\\?\\GLOBALROOT\\Device\\HarddiskVolumeShadowCopy12\r\n"
    )
    raw = text.encode("utf-16-le")
    decoded = bs._decode_vss_output(raw, b"")
    parsed = bs._parse_vss_create_output(decoded)
    assert parsed is not None
    assert parsed[1].endswith("HarddiskVolumeShadowCopy12")
    listed = bs._parse_vss_list_output(decoded)
    assert listed[0].endswith("HarddiskVolumeShadowCopy12")


def test_win_volume_relpath_strips_extended_prefix():
    from secturafab import browser_session as bs

    letter, rel = bs._win_volume_relpath(
        r"\\?\C:\Users\kyle\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies"
    )
    assert letter == "C:"
    assert rel.endswith(r"Default\Network\Cookies")
    assert not rel.startswith("C:")
    assert "?\\" not in rel
    letter2, rel2 = bs._win_volume_relpath(
        r"C:\Users\kyle\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies"
    )
    assert (letter2, rel2) == (letter, rel)


def test_chrome_shadow_cookie_rels_default_cookies_first():
    from secturafab import browser_session as bs

    src = r"C:\Users\Kyle\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies"
    rels = bs._chrome_shadow_cookie_rels(src)
    assert rels[0].replace("/", "\\").endswith(r"Default\Cookies")
    assert not rels[0].lower().endswith(r"network\cookies")
    assert any(r.lower().endswith(r"default\network\cookies") for r in rels)
    assert all(not bs._looks_like_live_dos_path(r) for r in rels)


def test_vss_dest_ok_needs_session_or_26_v20(tmp_path: Path):
    from secturafab import browser_session as bs

    empty = tmp_path / "empty"
    empty.write_bytes(b"x" * 8)
    assert bs._vss_dest_ok(empty) is False
    cookies = tmp_path / "Cookies"
    _write_cookie_db(cookies)
    assert bs._vss_dest_ok(cookies) is True


def test_win_copy_from_shadow_device_uses_globalroot_not_live(tmp_path: Path):
    import inspect

    from secturafab import browser_session as bs

    dest = tmp_path / "Cookies"
    seen: list[str] = []
    rel = r"Users\kyle\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies"

    def fake_raw(src_win: str, out: Path) -> None:
        seen.append(src_win)
        assert "GLOBALROOT" in src_win
        assert "HarddiskVolumeShadowCopy3" in src_win
        assert src_win[1:3] != ":\\"
        if src_win.endswith("Cookies"):
            out.write_bytes(b"sqlite-shadow")
        else:
            raise OSError(2, "no sidecar")

    with patch.object(bs, "_win_copy_raw", side_effect=fake_raw):
        bs._win_copy_from_shadow_device(
            r"\\?\GLOBALROOT\Device\HarddiskVolumeShadowCopy3",
            rel,
            dest,
        )
    assert dest.read_bytes() == b"sqlite-shadow"
    assert seen[0] == (
        r"\\?\GLOBALROOT\Device\HarddiskVolumeShadowCopy3"
        r"\Users\kyle\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies"
    )
    assert any(p.endswith("Cookies-wal") for p in seen)
    assert any(p.endswith("Cookies-shm") for p in seen)
    src = inspect.getsource(bs._win_copy_from_shadow_device)
    assert "cmd.exe" not in src
    assert "_win_copy_raw" in src
    with pytest.raises(OSError):
        bs._win_copy_from_shadow_device(r"C:\Users\kyle\Cookies", rel, dest)


def test_vssadmin_create_rc2_copies_from_listed_shadow(tmp_path: Path):
    import subprocess

    from secturafab import browser_session as bs

    dest = tmp_path / "snap" / "Cookies"
    dest.parent.mkdir()
    rel = r"Users\kyle\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies"
    copied: list[str] = []

    def fake_run(args, **_k):
        argv = [str(a) for a in args]
        if "create" in argv:
            return subprocess.CompletedProcess(argv, 2, "Shadow copy created.\n", "")
        if "list" in argv:
            text = (
                "Contents of shadow copy set ID: {AAAAAAAA-1111-2222-3333-444444444444}\n"
                "    Shadow Copy Volume: "
                "\\\\?\\GLOBALROOT\\Device\\HarddiskVolumeShadowCopy7\n"
            )
            return subprocess.CompletedProcess(argv, 0, text, "")
        return subprocess.CompletedProcess(argv, 1, "", "")

    def fake_raw(src_win: str, out: Path) -> None:
        copied.append(src_win)
        assert "GLOBALROOT" in src_win
        assert "HarddiskVolumeShadowCopy7" in src_win
        assert src_win[1:3] != ":\\"
        if src_win.endswith("Cookies"):
            _write_cookie_db(out)
        else:
            out.write_bytes(b"side")

    with patch.object(bs.subprocess, "run", side_effect=fake_run), patch.object(
        bs, "_win_copy_raw", side_effect=fake_raw
    ), patch.object(bs, "_windows_system32_exe", return_value="vssadmin.exe"):
        bs._cache["vss"] = ""
        bs._win_vss_vssadmin_copy(tmp_path / "Cookies", dest, rel, "C:")
    assert dest.is_file() and dest.stat().st_size > 0
    assert bs._cache["vss"] == "shadow"
    assert any(p.endswith("Cookies") for p in copied)
    assert any("Default\\Cookies" in p.replace("/", "\\") or p.endswith("Cookies") for p in copied)
    assert any(p.endswith("Cookies-wal") for p in copied)
    assert any(p.endswith("Cookies-shm") for p in copied)
    assert not any("delete" in str(a).lower() for a in copied)


def test_prefer_vss_status_keeps_create_returnvalue():
    from secturafab import browser_session as bs

    wrapped = "exc:MethodInvocationException:0x80131501"
    assert bs._prefer_vss_status(wrapped, "create:1") == "create:1"
    assert bs._prefer_vss_status("", wrapped) == wrapped


def test_vss_ps_command_is_args_file_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import subprocess

    from secturafab import browser_session as bs

    dest = tmp_path / "out" / "Cookies"
    dest.parent.mkdir()
    seen: dict[str, list[str]] = {}

    def fake_run(args, **_k):
        seen["args"] = [str(a) for a in args]
        dest.write_bytes(b"sqlite")
        (dest.parent / (dest.name + ".vss-status")).write_text("ok", encoding="ascii")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(bs, "_windows_powershell", lambda: "powershell.exe")
    with patch.object(bs.subprocess, "run", side_effect=fake_run):
        bs._win_vss_ps_create_copy(tmp_path / "Cookies", dest, r"Users\x\Cookies", "C:")
    args = seen["args"]
    assert args[0] == "powershell.exe"
    file_i = args.index("-File")
    assert len(args) == file_i + 3
    assert not any(a == "C:\\" or a.endswith("\\") and a[1:2] == ":" for a in args)
    assert args[-1].endswith(".vss-args")
    assert bs._cache["vss"] == "ok"


def test_win_vss_copy_uses_vssadmin_after_cim_throw(tmp_path: Path):
    import shutil

    from secturafab import browser_session as bs

    real = tmp_path / "Cookies"
    _write_cookie_db(real)
    dest = tmp_path / "snap" / "Cookies"
    dest.parent.mkdir()
    order: list[str] = []

    class _Driven:
        drive = "C:"

        def resolve(self):
            return self

        def __str__(self) -> str:
            return r"C:\Users\kyle\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies"

    def _ps(*_a, **_k):
        order.append("ps")
        bs._record_vss("exc:MethodInvocationException:0x80131501")
        raise OSError(1, "ps")

    def _va(_src: Path, dest_path: Path, rel: str, letter: str) -> None:
        order.append("vssadmin")
        assert letter == "C:"
        assert rel.replace("\\", "/").endswith("Cookies")
        shutil.copy2(real, dest_path)
        bs._record_vss("ok")

    def _ds(*_a, **_k):
        raise AssertionError("diskshadow must not run after vssadmin ok")

    with patch.object(bs, "_win_vss_ps_create_copy", _ps), patch.object(
        bs, "_win_vss_vssadmin_copy", _va
    ), patch.object(bs, "_win_vss_diskshadow_copy", _ds), patch.object(
        bs, "_enable_privilege", lambda *_a, **_k: None
    ):
        bs._cache["vss"] = ""
        bs._win_vss_copy(_Driven(), dest)  # type: ignore[arg-type]
    assert dest.is_file() and dest.stat().st_size > 0
    assert order == ["ps", "vssadmin"]
    assert bs._cache["vss"] == "shadow"


def test_sqlite_has_cookie_table(tmp_path: Path):
    from secturafab.browser_session import _sqlite_has_cookie_table

    missing = tmp_path / "nope"
    assert _sqlite_has_cookie_table(missing) is False
    junk = tmp_path / "junk"
    junk.write_bytes(b"not-sqlite")
    assert _sqlite_has_cookie_table(junk) is False
    other = tmp_path / "other.db"
    import sqlite3

    conn = sqlite3.connect(str(other))
    conn.execute("CREATE TABLE hosts (name TEXT)")
    conn.commit()
    conn.close()
    assert _sqlite_has_cookie_table(other) is False
    cookies = tmp_path / "Cookies"
    _write_cookie_db(cookies)
    assert _sqlite_has_cookie_table(cookies) is True


def test_call_with_timeout_returns_default_on_hang():
    from secturafab import browser_session as bs

    def _hang() -> str:
        time.sleep(8)
        return "late"

    t0 = time.monotonic()
    got = bs._call_with_timeout(_hang, 0.25, (None, "0x80080005:SERVER_EXEC_FAILURE:timeout"))
    elapsed = time.monotonic() - t0
    assert got == (None, "0x80080005:SERVER_EXEC_FAILURE:timeout")
    assert elapsed < 2.0


def test_elevator_decrypt_times_out_with_server_exec_failure():
    from secturafab import browser_session as bs

    def _hang(_blob: bytes):
        time.sleep(8)
        return b"k" * 32, "0x00000000"

    with patch.object(bs.os, "name", "nt"), patch.object(
        bs, "_elevator_decrypt_uncapped", side_effect=_hang
    ):
        t0 = time.monotonic()
        key, hr = bs._elevator_decrypt(b"\x01" * 40)
        elapsed = time.monotonic() - t0
    assert key is None
    assert "0x80080005" in hr
    assert "SERVER_EXEC_FAILURE" in hr
    assert "timeout" in hr
    assert elapsed < 6.0


def test_chrome_open_uses_vss_then_cached_not_dup(tmp_path: Path):
    """Chrome-open: VSS first (create:vssadmin:2), then cached. Do not skip VSS."""
    from secturafab import browser_session as bs

    live = tmp_path / "live" / "Cookies"
    live.parent.mkdir()
    live.write_bytes(b"locked")
    cached = tmp_path / "cache" / "Cookies"
    _write_cookie_db(cached)
    profile = {
        "label": "chrome:Default",
        "cookies": live,
        "local_state": tmp_path / "Local State",
        "profile_dir": tmp_path,
        "history_hit": True,
    }
    order: list[str] = []

    def _vss(*_a, **_k):
        order.append("vss")
        bs._record_vss("create:vssadmin:2")
        return False

    def _no_dup(*_a, **_k):
        order.append("dup")
        raise AssertionError("dup_handle must not run before VSS+cached")

    def _no_live_nolock(*_a, **_k):
        raise AssertionError("nolock must not touch the live Cookies path when Chrome is open")

    sprayed: list[str] = []

    def _spray(name: str):
        def _inner(*_a, **_k):
            sprayed.append(name)
            raise AssertionError(name)

        return _inner

    with patch.dict(os.environ, {"KANNON_COOKIE_CACHE": str(tmp_path / "cache")}), patch.object(
        bs, "_browser_cookie_dbs", return_value=[profile]
    ), patch.object(bs, "_chrome_is_open", return_value=True), patch.object(
        bs, "_try_nolock_copy", side_effect=_no_live_nolock
    ), patch.object(bs, "_sqlite_backup_nolock", side_effect=_no_live_nolock), patch.object(
        bs, "_try_vss_create_copy", side_effect=_vss
    ), patch.object(bs, "_try_handle_dup_copy", side_effect=_no_dup), patch.object(
        bs, "_win_lock_bypass_with_wal", side_effect=_spray("lock_bypass")
    ), patch.object(bs, "_win_backup_copy", side_effect=_spray("backup_priv")), patch.object(
        bs, "_win_ntcreatefile_backup_copy", side_effect=_spray("nt_backup")
    ), patch.object(bs, "_win_esentutl_copy", side_effect=_spray("esentutl")), patch.object(
        bs, "_win_robocopy_backup_copy", side_effect=_spray("robocopy_b")
    ):
        header = bs._discover_windows_chrome(force=True)
    assert header
    status = bs.discover_status()
    assert order == ["vss"]
    assert sprayed == []
    assert status["lock_bypass"].startswith("vss=create:vssadmin:2")
    assert "cached" in status["lock_bypass"]
    assert "dup_handle" not in status["lock_bypass"]
    assert "backup_priv" not in status["lock_bypass"]
    assert "nt_backup" not in status["lock_bypass"]
    assert "esentutl" not in status["lock_bypass"]
    assert "robocopy_b" not in status["lock_bypass"]
    assert "nolock" not in status["lock_bypass"]
    assert "live_path" not in status["lock_bypass"]
    assert "shadow_miss" not in status["lock_bypass"]
    assert status["session_found"] is True
    assert status["source"] == "chrome:Default"


def test_chrome_open_vss_miss_does_not_nolock_live_path(tmp_path: Path):
    from secturafab import browser_session as bs

    live = tmp_path / "live" / "Cookies"
    live.parent.mkdir()
    live.write_bytes(b"locked")
    profile = {
        "label": "chrome:Default",
        "cookies": live,
        "local_state": tmp_path / "Local State",
        "profile_dir": tmp_path,
        "history_hit": True,
    }

    def _vss(*_a, **_k):
        bs._record_vss("create:vssadmin:2")
        return False

    def _no_live(*_a, **_k):
        raise AssertionError("must not open the live Cookies path when Chrome is open")

    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]), patch.object(
        bs, "_chrome_is_open", return_value=True
    ), patch.object(bs, "_try_nolock_copy", side_effect=_no_live), patch.object(
        bs, "_sqlite_backup_nolock", side_effect=_no_live
    ), patch.object(bs, "_try_vss_create_copy", side_effect=_vss), patch.object(
        bs, "_try_live_cookie_sidecar_copy", side_effect=_no_live
    ), patch.object(bs, "_try_handle_dup_copy", side_effect=_no_live):
        header = bs._discover_windows_chrome(force=True)
    assert header == ""
    status = bs.discover_status()
    assert status["session_found"] is False
    assert status["source"] == "chrome:Default"
    assert "nolock" not in status["lock_bypass"]
    assert "live_path" not in status["lock_bypass"]
    assert "shadow_miss" in status["lock_bypass"]
    assert "GLOBALROOT" in status["error"] or "shadow" in status["error"].casefold()


def test_vss_success_does_not_copy_live_sidecars(tmp_path: Path):
    from secturafab import browser_session as bs

    live = tmp_path / "live" / "Cookies"
    live.parent.mkdir()
    live.write_bytes(b"locked")
    profile = {
        "label": "chrome:Default",
        "cookies": live,
        "local_state": tmp_path / "Local State",
        "profile_dir": tmp_path,
        "history_hit": True,
    }

    def _vss(_src: Path, dest: Path) -> bool:
        _write_cookie_db(dest)
        bs._record_vss("create:vssadmin:2")
        return True

    def _no_live(*_a, **_k):
        raise AssertionError("must not copy live Chrome sidecars after a shadow copy")

    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]), patch.object(
        bs, "_chrome_is_open", return_value=True
    ), patch.object(bs, "_try_nolock_copy", side_effect=_no_live), patch.object(
        bs, "_try_vss_create_copy", side_effect=_vss
    ), patch.object(bs, "_copy_cookie_sidecars", side_effect=_no_live):
        header = bs._discover_windows_chrome(force=True)
    assert header
    status = bs.discover_status()
    assert status["source"] == "chrome:Default"
    assert status["lock_bypass"] == "vss=shadow"
    assert "live_path" not in status["lock_bypass"]
    assert "cached" not in status["lock_bypass"]


def test_browser_dbs_omit_edge_when_chrome_default_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from secturafab import browser_session as bs

    local = tmp_path / "Local"
    chrome = local / "Google" / "Chrome" / "User Data" / "Default" / "Network"
    edge = local / "Microsoft" / "Edge" / "User Data" / "Default" / "Network"
    chrome.mkdir(parents=True)
    edge.mkdir(parents=True)
    _write_cookie_db(chrome / "Cookies")
    _write_cookie_db(edge / "Cookies")
    (local / "Google" / "Chrome" / "User Data" / "Local State").write_text("{}", encoding="utf-8")
    (local / "Microsoft" / "Edge" / "User Data" / "Local State").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    dbs = bs._browser_cookie_dbs()
    labels = [str(p["label"]) for p in dbs]
    assert "chrome:Default" in labels
    assert all(not lab.startswith("edge:") for lab in labels)


def test_discover_does_not_read_edge_after_chrome_default(tmp_path: Path):
    from secturafab import browser_session as bs

    chrome_db = tmp_path / "chrome" / "Cookies"
    edge_db = tmp_path / "edge" / "Cookies"
    _write_cookie_db(chrome_db)
    _write_cookie_db(edge_db)
    chrome = {
        "label": "chrome:Default",
        "cookies": chrome_db,
        "local_state": tmp_path / "chrome-state",
        "profile_dir": tmp_path / "chrome",
        "history_hit": True,
    }
    edge = {
        "label": "edge:Default",
        "cookies": edge_db,
        "local_state": tmp_path / "edge-state",
        "profile_dir": tmp_path / "edge",
        "history_hit": False,
    }
    seen: list[str] = []

    real = bs._read_cookie_rows

    def _track(profile):
        seen.append(str(profile.get("label") or ""))
        return real(profile)

    with patch.object(bs, "_browser_cookie_dbs", return_value=[chrome, edge]), patch.object(
        bs, "_read_cookie_rows", side_effect=_track
    ):
        header = bs._discover_windows_chrome(force=True)
    assert header
    assert seen == ["chrome:Default"]
    assert bs.discover_status()["source"] == "chrome:Default"


def test_abe_helper_has_no_cocreate():
    from secturafab import browser_session as bs

    assert bs._ABE_HELPER_TIMEOUT_S <= 8
    cs = bs._ABE_HELPER_CS
    assert "CoCreateInstance" not in cs
    assert "ole32" not in cs
    assert "LocalServer32" not in cs
    assert "elevation_service" not in cs
    assert "CLASSNOTREG" not in cs
    assert "ReadProcessMemory" in cs
    assert "VirtualQueryEx" in cs
    assert "cand=" in cs
    assert "AbePid" in cs
    assert "SkipPid" in cs
    assert "PreferPid" in cs
    assert "--type=" in cs
    assert "MEM_MAPPED" in cs
    assert "KANNON_CHROME_PIDS" in cs
    assert "memscan:no_chrome" in cs
    assert "memscan:no_browser" not in cs
    assert "CryptUnprotectMemory" in cs
    assert "NtQueueApcThread" in cs
    assert "NtTestAlert" in cs
    assert "32, 40, 48" in cs
    import inspect

    memscan = inspect.getsource(bs._memscan_abe_key)
    elev = (
        inspect.getsource(bs._chrome_elevator_abe_key)
        + inspect.getsource(bs._chrome_elevator_decrypt_once)
        + inspect.getsource(bs._chrome_elevator_via_exports)
        + inspect.getsource(bs._queue_special_apc)
        + inspect.getsource(bs._hijack_existing_thread)
        + inspect.getsource(bs._elev_hr_token)
        + inspect.getsource(bs._apc_q_err)
        + inspect.getsource(bs._apc_force_miss_open)
    )
    assert "def consider(" in memscan
    assert "consider_heap" not in memscan
    assert "consider_apc" not in memscan
    assert "consider_appb_apc" not in memscan
    assert "_ABE_HEAP_MARKS" not in memscan
    assert "os_crypt" in memscan
    assert "KeyRing" in memscan
    assert "encryptor" in memscan
    assert "_chrome_browser_pids" in memscan
    assert "_chrome_pids_prioritized" in memscan
    assert "starved tried=145" in memscan
    assert "tried=1080" in memscan
    assert "tried=392" in memscan
    assert "_ABE_HEAP_STRIDE" in memscan
    assert bs._ABE_HEAP_STRIDE == 8
    assert bs._ABE_MEMSCAN_TIMEOUT_S >= 12.0
    assert "_RemoteUnprotect" not in memscan
    assert "apc:key:off=" not in memscan
    assert "heap:hit" in memscan
    assert "memscan:cands=" in memscan
    assert "tried=" in memscan
    assert "no_cand" not in memscan
    assert "20000" in memscan or bs._ABE_MEMSCAN_MAX_CAND == 20000
    assert "tried >= 200" not in memscan
    assert "cands == 200" not in memscan
    assert memscan.index("def consider(") < memscan.index("hit = consider(")
    assert memscan.index("hit = consider(") < memscan.index("nxt = addr + size")
    assert "apc:0" in elev
    assert "apc:hr=" in elev
    assert "apc:key" in elev
    assert "apc:q:err=" in elev
    assert "apc:ran" in elev
    assert "apc:force=miss" in elev
    assert "apc:force=miss:open" in elev
    assert 'return None, "apc:force=miss"' not in elev
    assert 'return None, "apc:force=miss:open"' not in elev
    assert "memmove" in elev
    assert "SleepEx" in elev
    assert "handshake" in elev
    assert "crt:err" not in elev
    assert "CreateRemoteThread" not in elev
    assert "alloc:err" in elev
    assert "elev:len=" in elev
    assert "DecryptData" in elev
    assert "vtable" in elev
    assert "CoCreateInstance" in elev
    assert "CoInitializeEx" in elev
    assert "NtTestAlert" in elev
    assert "NtQueueApcThread" in elev
    assert "QueueUserAPC" in elev
    assert "SetThreadContext" in elev
    assert "CryptUnprotectMemory" not in elev
    assert "CryptUnprotectData" not in elev
    assert bs._ABE_ELEVATOR_TIMEOUT_S <= 3.0
    assert bs._ABE_BROWSER_KEYS_TIMEOUT_S <= 15.0
    assert "_chrome_elevator_via_exports" in inspect.getsource(bs)
    assert "_v20_prove_samples" in inspect.getsource(bs)
    assert "BCrypt first" in inspect.getsource(bs._aes_gcm_decrypt_bytes)
    assert "_aes_key_windows_offs" in inspect.getsource(bs)
    assert "_v20_one_ok" in inspect.getsource(bs)
    assert "try_blobs" not in memscan
    assert "memscan:cands=" in memscan
    assert "tried=" in memscan
    assert memscan.index("_keyring_v20_key_ptrs") < memscan.index(
        "_extract_abe_candidate_ptrs(data)"
    )
    apc = inspect.getsource(bs._RemoteUnprotect._apc)
    assert "CRYPTPROTECTMEMORY_SAME_PROCESS" in apc
    assert "same_process" in apc
    assert "_aes_gcm_decrypt_bcrypt" in inspect.getsource(bs)
    assert "_aes_gcm_decrypt_stdlib" in inspect.getsource(bs)
    assert "_v20_verify_samples" in inspect.getsource(bs)
    assert "_abe_key_from_material" in inspect.getsource(bs)
    assert "_cookie_keys_from_wrap" in inspect.getsource(bs)
    assert "_abe_proves_cookies" in inspect.getsource(bs)
    assert "_aes_gcm_decrypt_layouts" in inspect.getsource(bs)
    assert "_app_bound_layout_views" in inspect.getsource(bs)
    assert "_static_app_bound_cookie_key" in inspect.getsource(bs)
    assert "_dpapi_unprotect_appb" in inspect.getsource(bs)
    assert "_chrome_unprotect_data" in inspect.getsource(bs)
    assert "_chrome_unprotect_data_once" in inspect.getsource(bs)
    assert "_impersonate_chrome_unprotect" in inspect.getsource(bs)
    assert "_cookie_key_from_unprotect_plain" in inspect.getsource(bs)
    chrome_once = inspect.getsource(bs._chrome_unprotect_data_once)
    assert "7th pDataOut @+0x38" in chrome_once
    assert "stack[0x38:0x40]" in chrome_once
    assert "stack[0x30:0x38] = int(out_blob_addr)" not in chrome_once
    assert "ImpersonateLoggedOnUser" in inspect.getsource(bs)
    assert "c_void_p" in inspect.getsource(bs._dpapi_unprotect_ex)
    assert "addressof" in inspect.getsource(bs._dpapi_unprotect_ex)
    assert "_local_free" in inspect.getsource(bs._dpapi_unprotect_ex)
    assert "ArgumentError" in inspect.getsource(bs._dpapi_unprotect_ex)
    assert "entropy is not None" in inspect.getsource(bs._dpapi_unprotect_ex)
    assert "get_last_error" in inspect.getsource(bs._dpapi_unprotect_ex)
    assert "dpapi:ok" in inspect.getsource(bs)
    assert "dpapi:win32=" in inspect.getsource(bs)
    assert "dpapi:len=" in inspect.getsource(bs)
    assert "dpapi:off=" in inspect.getsource(bs)
    assert "dpapi:all13" in inspect.getsource(bs)
    assert "next=chrome_open" in inspect.getsource(bs)
    assert "_abe_all13_appb" in inspect.getsource(bs)
    elevator = inspect.getsource(bs._elevator_decrypt_via_chrome_dir)
    assert "if all13:" in elevator
    assert elevator.index("if pids:") < elevator.index("if all13:")
    assert elevator.index("_memscan_abe_key") < elevator.index("_chrome_elevator_abe_key")
    assert elevator.index("_chrome_elevator_abe_key") < elevator.index("_compiled_abe_helper_exe")
    assert "_call_with_timeout" in elevator
    assert "_ABE_ELEVATOR_TIMEOUT_S" in elevator
    assert "apc:force=miss" in elevator
    assert "apc:force=miss:open" in elevator
    assert "apc:force=miss:open=timeout" in elevator
    assert '(None, "apc:force=miss")' not in elevator
    assert '(None, "apc:force=miss:open")' not in elevator
    keys_src = inspect.getsource(bs._browser_keys)
    assert "_call_with_timeout" in keys_src
    assert "_ABE_BROWSER_KEYS_TIMEOUT_S" in keys_src
    assert "apc:q:err=timeout" in keys_src
    rows_src = inspect.getsource(bs._read_cookie_rows)
    assert rows_src.index("_try_vss_create_copy") < rows_src.index("_try_live_cookie_sidecar_copy")
    assert rows_src.index("_try_live_cookie_sidecar_copy") < rows_src.index("_try_cached_cookie_copy")
    assert rows_src.index("_try_cached_cookie_copy") < rows_src.index("_try_handle_dup_copy")
    assert "allow_lock_bypass=False" in rows_src
    assert "same GLOBALROOT shadow" in rows_src
    assert "_chrome_is_open" in rows_src
    assert "not chrome_open" in rows_src
    assert "_SHADOW_MISS_ERR" in rows_src
    assert "_LIVE_COOKIES_PATH_ERR" not in inspect.getsource(bs)
    assert "live_path" not in rows_src
    assert "vss=shadow" in rows_src
    vssadmin_src = inspect.getsource(bs._win_vss_vssadmin_copy)
    assert "_win_guess_shadow_devices" in vssadmin_src
    assert "_win_copy_from_shadow_src" in vssadmin_src
    assert "_decode_vss_output" in vssadmin_src
    shadow_src = inspect.getsource(bs._win_copy_from_shadow_device)
    assert "cmd.exe" not in shadow_src
    assert "_win_copy_raw" in shadow_src
    assert "_win_copy_raw_nt" in shadow_src
    assert "_COOKIE_SIDECARS" in shadow_src
    assert "_looks_like_live_dos_path" in inspect.getsource(bs._win_copy_raw)
    assert "_host_is_sectura" in inspect.getsource(bs)
    assert "_collect_v20_from_db" in inspect.getsource(bs)
    assert "_cookie_blob_bytes" in inspect.getsource(bs)
    assert "_COOKIE_SIDECARS" in inspect.getsource(bs)
    assert bs._COOKIE_SIDECARS == ("-journal", "-wal", "-shm")
    assert "_DPAPI_WALK_OFFS" in inspect.getsource(bs)
    assert bs._DPAPI_WALK_OFFS == (0, 4, 8, 12, 16, 32, 44)
    assert "_note_dpapi_hr" in inspect.getsource(bs)
    assert "_dpapi_unprotect_local" in inspect.getsource(bs._app_bound_layout_views)
    assert "Chrome not required" in inspect.getsource(bs._dpapi_unprotect_appb)
    assert '_join_abe_hr(["memscan:no_chrome"])' in inspect.getsource(bs._memscan_abe_key)
    assert "kernel32.LocalFree(out_blob.pbData)" not in inspect.getsource(bs)
    assert "UnprotectOnce" in cs
    assert "CryptUnprotectData" in cs
    assert "KANNON_APPB_PATH" in cs
    assert "_abe_proves_cookies" in inspect.getsource(bs._unwrap_app_bound_key)
    assert "return _abe_key_from_material(cand, v20_sample)" not in memscan
    assert "_abe_key_from_material" not in memscan
    assert "keyring_pending" not in memscan
    assert 'unprotect(b"\\x00" * 32)' not in memscan
    assert "_chrome_elevator_abe_key" in inspect.getsource(bs._elevator_decrypt_via_chrome_dir)
    assert "_elevator_decrypt(" not in inspect.getsource(bs._elevator_decrypt_via_chrome_dir)
    assert "public long cbData" in cs
    assert "new IntPtr(32), new IntPtr(0)" in cs
    assert "new IntPtr(32), new IntPtr(1)" not in cs
    assert "idx < 4" not in cs
    assert "bool entropy" not in cs
    assert "aligned_entropy" not in cs
    assert bs._ABE_MEMSCAN_MAX_CAND == 20000
    assert "const int MAX_CAND = 20000" in cs


def test_run_abe_helper_timeout_is_helper_timeout():
    import subprocess

    from secturafab import browser_session as bs

    def _expire(*_a, **_k):
        raise subprocess.TimeoutExpired(cmd="abe", timeout=8)

    with patch.object(bs.subprocess, "run", side_effect=_expire):
        key, hr = bs._run_abe_helper(Path("kannon_quote_abe.exe"), b"v20" + b"\x00" * 40)
    assert key is None
    assert hr == "helper:timeout"
    assert "CLASSNOTREG" not in hr


def test_persist_cookie_snapshot_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from secturafab import browser_session as bs

    monkeypatch.setenv("KANNON_COOKIE_CACHE", str(tmp_path / "cache"))
    src = tmp_path / "Cookies"
    _write_cookie_db(src)
    (tmp_path / "Cookies-wal").write_bytes(b"wal")
    (tmp_path / "Cookies-shm").write_bytes(b"shm")
    (tmp_path / "Cookies-journal").write_bytes(b"jnl")
    bs._persist_cookie_snapshot(src)
    dest = tmp_path / "out" / "Cookies"
    dest.parent.mkdir()
    assert bs._try_cached_cookie_copy(dest) is True
    assert bs._sqlite_has_cookie_table(dest)
    assert (tmp_path / "cache" / "Cookies-wal").read_bytes() == b"wal"
    assert (tmp_path / "cache" / "Cookies-shm").read_bytes() == b"shm"
    assert (tmp_path / "cache" / "Cookies-journal").read_bytes() == b"jnl"


def test_host_is_sectura_contains_domain_not_www_only():
    from secturafab import browser_session as bs

    assert bs._host_is_sectura(".secturafab.com")
    assert bs._host_is_sectura("www.secturafab.com")
    assert bs._host_is_sectura("APP.SECTURAFAB.COM")
    assert bs._host_is_sectura("https://login.secturafab.com/")
    assert not bs._host_is_sectura("www.example.com")
    assert not bs._host_is_sectura("www.secturafab.com.evil.test")


def test_cookie_blob_bytes_coerces_memoryview_and_str():
    from secturafab import browser_session as bs

    raw = b"v20" + b"\x00" * 40
    assert bs._cookie_blob_bytes(memoryview(raw)) == raw
    assert bs._is_v20_prefix(bs._cookie_blob_bytes("v20" + "\x00" * 40))
    assert bs._V20_PREFIX == b"\x76\x32\x30"


def test_collect_v20_counts_every_prefix_and_keeps_a_sample(tmp_path: Path):
    import sqlite3

    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE cookies (host_key TEXT, name TEXT, value TEXT, encrypted_value BLOB)"
    )
    blob = b"v20" + b"\x11" * 40
    conn.execute(
        "INSERT INTO cookies VALUES (?,?,?,?)",
        ("www.example.com", "other", "", blob),
    )
    conn.execute(
        "INSERT INTO cookies VALUES (?,?,?,?)",
        ("www.secturafab.com", "sid", "", blob),
    )
    conn.execute(
        "INSERT INTO cookies VALUES (?,?,?,?)",
        ("www.secturafab.com", "plain", "x", b""),
    )
    conn.commit()
    conn.close()
    n, samples = bs._collect_v20_from_db(db)
    assert n == 2
    assert samples and samples[0] == blob


def test_discover_passes_db_v20_sample_to_chrome_dir(tmp_path: Path):
    import sqlite3

    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE cookies (host_key TEXT, name TEXT, value TEXT, encrypted_value BLOB)"
    )
    sample = b"v20" + b"\x22" * 40
    conn.execute(
        "INSERT INTO cookies VALUES (?,?,?,?)",
        ("www.example.com", "x", "", sample),
    )
    conn.execute(
        "INSERT INTO cookies VALUES (?,?,?,?)",
        ("www.secturafab.com", "sid", "", b""),
    )
    conn.commit()
    conn.close()
    local_state = tmp_path / "Local State"
    local_state.write_text(
        json.dumps(
            {"os_crypt": {"app_bound_encrypted_key": base64.b64encode(b"APPB" + b"\x01" * 40).decode()}}
        ),
        encoding="utf-8",
    )
    profile = {
        "label": "chrome:Default",
        "cookies": db,
        "local_state": local_state,
        "profile_dir": tmp_path,
        "history_hit": True,
    }
    seen: list[bytes | None] = []

    def _unwrap(_b64, v20_sample=None):
        seen.append(v20_sample)
        return None, "chrome_dir", "ok"

    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]), patch.object(
        bs, "_unwrap_app_bound_key", side_effect=_unwrap
    ):
        bs._discover_windows_chrome(force=True)
    status = bs.discover_status()
    assert status["source"] == "chrome:Default"
    assert status["v20_blobs"] == 1
    assert seen and seen[0] == sample
    assert status["abe"] == "chrome_dir"


def test_query_matches_non_www_sectura_host(tmp_path: Path):
    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    _write_cookie_db(db, host="app.secturafab.com")
    rows = bs._query_sectura_cookie_rows(db)
    hosts = {r[0] for r in rows}
    assert "app.secturafab.com" in hosts
    assert "www.secturafab.com" in hosts


def test_empty_chrome_default_keeps_source(tmp_path: Path):
    import sqlite3

    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE cookies (host_key TEXT, name TEXT, value TEXT, encrypted_value BLOB)"
    )
    conn.execute(
        "INSERT INTO cookies VALUES (?,?,?,?)",
        ("www.example.com", "sid", "x", b""),
    )
    conn.commit()
    conn.close()
    profile = {
        "label": "chrome:Default",
        "cookies": db,
        "local_state": tmp_path / "Local State",
        "profile_dir": tmp_path,
        "history_hit": True,
    }
    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]):
        header = bs._discover_windows_chrome(force=True)
    assert header == ""
    assert bs.discover_status()["source"] == "chrome:Default"


def test_cached_without_sectura_rows_is_not_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import sqlite3

    from secturafab import browser_session as bs

    monkeypatch.setenv("KANNON_COOKIE_CACHE", str(tmp_path / "cache"))
    cache = tmp_path / "cache" / "Cookies"
    cache.parent.mkdir()
    conn = sqlite3.connect(str(cache))
    conn.execute(
        "CREATE TABLE cookies (host_key TEXT, name TEXT, value TEXT, encrypted_value BLOB)"
    )
    conn.execute(
        "INSERT INTO cookies VALUES (?,?,?,?)",
        ("www.example.com", "sid", "x", b""),
    )
    conn.commit()
    conn.close()
    dest = tmp_path / "out" / "Cookies"
    dest.parent.mkdir()
    assert bs._try_cached_cookie_copy(dest) is False


def test_copy_dup_handle_bytes_tries_mapview_first():
    import inspect

    from secturafab.browser_session import _copy_dup_handle_bytes

    src = inspect.getsource(_copy_dup_handle_bytes)
    assert "_mapview_handle_to_file" in src
    assert src.index("_mapview_handle_to_file") < src.index("_read_handle_to_file")


def test_unwrap_source_never_cocreates():
    import inspect

    from secturafab import browser_session as bs

    src = inspect.getsource(bs._unwrap_app_bound_key)
    assert "_prepare_elevator_com" not in src
    assert "_elevator_decrypt(" not in src.replace("_elevator_decrypt_via_chrome_dir", "CHROME_DIR")


def test_unwrap_real_path_is_chrome_dir_not_classnotreg():
    from secturafab import browser_session as bs

    b64 = base64.b64encode(b"APPB" + b"\x01" * 40).decode("ascii")
    key, status, hr = bs._unwrap_app_bound_key(b64, v20_sample=b"v20" + b"\x00" * 40)
    assert key is None
    assert status == "chrome_dir"
    assert "CLASSNOTREG" not in hr
    assert "0x80040154" not in hr
    assert "chrome_dir:not_nt" in hr or "csc_missing" in hr or "memscan:not_nt" in hr


def test_unwrap_uses_chrome_dir_helper_first():
    from secturafab import browser_session as bs

    key = os.urandom(32)
    nonce = os.urandom(12)
    cookie_blob = b"v20" + nonce + _aes_gcm_encrypt((b"\x22" * 32) + b"session", key, nonce)
    b64 = base64.b64encode(b"APPB" + b"\x01" * 40).decode("ascii")
    bs._cache["_v20_verify"] = [cookie_blob]

    def _no_elevator(*_a, **_k):
        raise AssertionError("in-process CoCreate must not run when chrome_dir returns a key")

    try:
        with patch.object(
            bs, "_elevator_decrypt_via_chrome_dir", return_value=(key, "0x00000000")
        ), patch.object(bs, "_elevator_decrypt", side_effect=_no_elevator):
            got, status, hr = bs._unwrap_app_bound_key(b64, v20_sample=cookie_blob)
        assert got == key
        assert status == "chrome_dir"
        assert hr == "0x00000000"
    finally:
        bs._cache["_v20_verify"] = []


def test_user_abe_helper_dirs_skips_program_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from secturafab import browser_session as bs

    pf = tmp_path / "Program Files" / "Google" / "Chrome" / "Application" / "151.0.7922.174"
    pf.mkdir(parents=True)
    (pf / "chrome.exe").write_bytes(b"mz")
    local = tmp_path / "Local"
    monkeypatch.setenv("PROGRAMFILES", str(tmp_path / "Program Files"))
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    with patch.object(bs, "_chrome_helper_dirs", return_value=[pf]):
        dirs = bs._user_abe_helper_dirs()
    assert dirs
    assert all("program files" not in str(d).lower() for d in dirs)
    assert any(d.name == "151.0.7922.174" and "Local" in str(d) for d in dirs)
    assert any(d.name == "abe" for d in dirs)


def test_install_abe_helper_writes_localapp_not_program_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from secturafab import browser_session as bs

    helper = tmp_path / "kannon_quote_abe.exe"
    helper.write_bytes(b"mz")
    local = tmp_path / "Local"
    dest_dir = local / "KannonQuote" / "abe"
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    with patch.object(bs, "_user_abe_helper_dirs", return_value=[dest_dir]):
        dests, hr = bs._install_abe_helper(helper)
    assert hr == ""
    assert dests and dests[0].is_file()
    assert "Program Files" not in str(dests[0])


def test_extract_abe_candidate_ptrs_follows_vector():
    import struct

    from secturafab import browser_session as bs

    key_addr = 0x000001A2B3C4D500
    buf = bytearray(48)
    struct.pack_into("<QQQ", buf, 0, key_addr, key_addr + 32, key_addr + 32)
    assert (key_addr, 32) in bs._extract_abe_candidate_ptrs(bytes(buf))


def test_extract_abe_candidate_ptrs_follows_v20_keyring_tag():
    import struct

    from secturafab import browser_session as bs

    key_addr = 0x000001A2B3C4D500
    buf = bytearray(48)
    buf[0:4] = b"v20\x00"
    buf[23:29] = bs._KEYRING_V20_MARK
    struct.pack_into("<Q", buf, 32, key_addr)
    assert (key_addr, 32) in bs._extract_abe_candidate_ptrs(bytes(buf))


def test_extract_abe_size_first_sso_keyring():
    import struct

    from secturafab import browser_session as bs

    key_addr = 0x000001A2B3C4D500
    buf = bytearray(56)
    buf[0] = 6
    buf[1:5] = b"v20\x00"
    struct.pack_into("<QQ", buf, 32, key_addr, key_addr + 32)
    assert (key_addr, 32) in bs._extract_abe_candidate_ptrs(bytes(buf))


def test_extract_abe_optional_key_vector_at_plus_40():
    import struct

    from secturafab import browser_session as bs

    key_addr = 0x000001A2B3C4D500
    buf = bytearray(64)
    buf[0:4] = b"v20\x00"
    struct.pack_into("<QQ", buf, 40, key_addr, key_addr + 32)
    assert (key_addr, 32) in bs._extract_abe_candidate_ptrs(bytes(buf))


def test_extract_abe_msvc_string_v20_vector_at_plus_40():
    import struct

    from secturafab import browser_session as bs

    key_addr = 0x000001A2B3C4D500
    buf = bytearray(64)
    buf[0:4] = b"v20\x00"
    struct.pack_into("<Q", buf, 16, 3)
    struct.pack_into("<Q", buf, 24, 15)
    struct.pack_into("<QQ", buf, 40, key_addr, key_addr + 32)
    assert (key_addr, 32) in bs._extract_abe_candidate_ptrs(bytes(buf))


def test_extract_abe_msvc_string_size3_vector_at_plus_32():
    import struct

    from secturafab import browser_session as bs

    key_addr = 0x000001A2B3C4D500
    buf = bytearray(48)
    buf[0:4] = b"v20\x00"
    struct.pack_into("<Q", buf, 16, 3)
    struct.pack_into("<Q", buf, 24, 15)
    struct.pack_into("<Q", buf, 32, key_addr)
    assert (key_addr, 32) in bs._extract_abe_candidate_ptrs(bytes(buf))


def test_extract_abe_skips_inline_dword_32_spray():
    from secturafab import browser_session as bs

    junk = bytes(range(32))
    assert bs._extract_abe_candidate_ptrs(b"\x20\x00\x00\x00" + junk) == []
    assert bs._aligned_entropy_keys(junk * 4) == []
    loose = bytearray(40)
    loose[0:4] = b"v20\x00"
    assert bs._extract_abe_candidate_ptrs(bytes(loose)) == []


def test_inline_bstr_keys_reads_after_size_t_and_dword():
    from secturafab import browser_session as bs

    junk = bytes(range(32))
    blob = b"\x20\x00\x00\x00\x00\x00\x00\x00" + junk
    assert junk in bs._inline_bstr_keys(blob)
    bstr = b"\x20\x00\x00\x00" + junk
    assert junk in bs._inline_bstr_keys(bstr)


def test_keys_from_key_blob_parses_elevator_layout():
    from secturafab import browser_session as bs

    key = bytes(range(32))
    blob = (8).to_bytes(4, "little") + b"validate" + (32).to_bytes(4, "little") + key
    assert key in bs._keys_from_key_blob(blob)


def test_chrome_abe_cmd_ok_skips_renderer():
    from secturafab import browser_session as bs

    assert bs._chrome_abe_cmd_ok("") is True
    assert bs._chrome_abe_cmd_ok(r"C:\...\chrome.exe") is True
    assert (
        bs._chrome_abe_cmd_ok(r'chrome.exe --utility-sub-type=network.mojom.NetworkService')
        is True
    )
    assert bs._chrome_abe_cmd_ok(r"chrome.exe --type=utility") is True
    assert bs._chrome_abe_cmd_ok(r"chrome.exe --type=renderer") is False
    assert bs._chrome_abe_cmd_ok(r"chrome.exe --type=gpu-process") is False


def test_chrome_pids_prioritized_falls_back_to_running_chrome():
    from secturafab import browser_session as bs

    with patch.object(bs, "_chrome_pids", return_value=[111, 222]), patch.object(
        bs.subprocess, "run", side_effect=OSError("no powershell")
    ):
        assert bs._chrome_pids_prioritized() == [111, 222]


def test_chrome_pids_prioritized_puts_browser_first():
    from secturafab import browser_session as bs

    class _Run:
        stdout = (
            "22\tchrome.exe --type=utility --utility-sub-type=network.mojom.NetworkService\n"
            "11\tchrome.exe\n"
            "33\tchrome.exe --type=renderer\n"
            "44\tchrome.exe --type=utility --utility-sub-type=storage.mojom.StorageService\n"
        )
        returncode = 0

    with patch.object(bs, "_chrome_pids", return_value=[22, 11, 33, 44]), patch.object(
        bs, "_windows_powershell", return_value="powershell"
    ), patch.object(bs.subprocess, "run", return_value=_Run):
        ranked = bs._chrome_pids_prioritized()
        assert bs._chrome_browser_pids() == [11]
    assert ranked[0] == 11
    assert ranked[1] == 22
    assert 44 in ranked
    assert 33 not in ranked


def test_chrome_elevator_abe_key_is_apc_0_off_windows():
    from secturafab import browser_session as bs

    key, hr = bs._chrome_elevator_abe_key(b"v20" + b"\x00" * 40)
    assert key is None
    assert hr == "apc:0"
    stub = bs._elevator_remote_stub_bytes()
    assert stub.startswith(bytes((0xC6, 0x41, 0x18, 0xA1)))
    assert stub.endswith(b"\xc3")
    assert bs._elevator_handshake_stub_bytes() == bytes((0xC6, 0x41, 0x18, 0xA1, 0xC3))
    assert 80 <= len(stub) <= 256


def test_chrome_elevator_reports_apc_q_err_not_crt():
    import inspect

    from secturafab import browser_session as bs

    elev = (
        inspect.getsource(bs._chrome_elevator_abe_key)
        + inspect.getsource(bs._chrome_elevator_decrypt_once)
        + inspect.getsource(bs._chrome_elevator_via_exports)
        + inspect.getsource(bs._apc_force_miss_open)
    )
    assert "crt:err" not in elev
    assert "CreateRemoteThread" not in elev
    assert "PROCESS_CREATE_THREAD" not in elev or "No PROCESS_CREATE_THREAD" in elev
    assert "apc:q:err=" in elev
    assert "_elev_hr_token" in elev
    assert "elev:len=" in elev
    assert "apc:key" in elev
    assert "apc:ran" in elev
    assert "apc:force=miss" in elev
    assert "apc:force=miss:open" in elev
    assert 'return None, "apc:force=miss"' not in elev
    assert 'return None, "apc:force=miss:open"' not in elev
    assert "memmove" in elev
    assert "SleepEx" in elev
    assert "for flag in (1, 0)" in elev
    token = bs._apc_q_err(5)
    assert token == "apc:q:err=5"
    assert "crt:" not in token
    assert bs._apc_q_err(0xC0000022) == "apc:q:err=0xc0000022"
    assert bs._elev_hr_token(0x80040154) == "apc:hr=0x80040154"
    assert bs._apc_force_miss_open(0xC0000001) == "apc:force=miss:open=0xc0000001"
    assert bs._apc_force_miss_open("queued") == "apc:force=miss:open=queued"
    assert bs._apc_force_miss_open("apc:force=miss:open") == "apc:force=miss:open=queued"
    assert bs._apc_force_miss_open("timeout") == "apc:force=miss:open=timeout"
    assert bs._apc_force_miss_open("") == "apc:force=miss:open=queued"


def test_v20_one_ok_is_gcm_success_not_printable_or_longest():
    from secturafab import browser_session as bs

    key = os.urandom(32)
    other = os.urandom(32)
    nonce_long = os.urandom(12)
    nonce_ok = os.urandom(12)
    long_plain = os.urandom(80)
    ok_plain = os.urandom(32) + b"session"
    long_blob = b"v20" + nonce_long + _aes_gcm_encrypt(long_plain, other, nonce_long)
    ok_blob = b"v20" + nonce_ok + _aes_gcm_encrypt(ok_plain, key, nonce_ok)
    assert len(long_blob) > len(ok_blob)
    bs._cache["_v20_verify"] = [long_blob, ok_blob]
    bs._cache["_v20_sectura"] = [ok_blob]
    bs._cache["_v20_prove"] = []
    try:
        assert bs._v20_one_ok(key, long_blob) is True
        assert bs._abe_proves_cookies(key, long_blob) is True
        binary_only = b"\xff" * 48
        nonce_bin = os.urandom(12)
        bin_blob = b"v20" + nonce_bin + _aes_gcm_encrypt(binary_only, key, nonce_bin)
        bs._cache["_v20_verify"] = [bin_blob]
        bs._cache["_v20_sectura"] = [bin_blob]
        assert bs._aes_gcm_decrypt_bytes(bin_blob[3:], key)
        assert bs._v20_one_ok(key, bin_blob) is True
        assert bs._abe_proves_cookies(key, bin_blob) is True
        assert bs._v20_cookie_text(binary_only) == ""
    finally:
        bs._cache["_v20_verify"] = []
        bs._cache["_v20_sectura"] = []
        bs._cache["_v20_prove"] = []


def test_pick_v20_sample_skips_short():
    from secturafab import browser_session as bs

    short = b"v20" + b"\x00" * 10
    long = b"v20" + b"\x00" * 40
    assert bs._pick_v20_sample([("h", "n", "", short)]) is None
    assert bs._pick_v20_sample([("h", "n", "", short), ("h", "n", "", long)]) == long
    assert bs._v20_samples_from_rows([("h", "n", "", short), ("h", "n", "", long)]) == [long]


def test_aes_gcm_stdlib_matches_cryptography():
    from secturafab import browser_session as bs

    key = os.urandom(32)
    nonce = os.urandom(12)
    plain = (b"\x11" * 32) + b"session"
    payload = nonce + _aes_gcm_encrypt(plain, key, nonce)
    assert bs._aes_gcm_decrypt_stdlib(payload, key) == plain
    assert bs._aes_gcm_decrypt_stdlib(payload, os.urandom(32)) == b""


def test_aes_key_windows_takes_offset_32():
    from secturafab import browser_session as bs

    key = bytes(range(32))
    padded = b"\xaa" * 8 + key + b"\xbb" * 8
    assert key in bs._aes_key_windows(padded)
    assert key in bs._aes_key_windows(key)
    flagged = b"\x01" + key + b"\xcc" * 8
    assert key in bs._aes_key_windows(flagged)
    buried = b"\xaa" * 7 + key
    assert key in bs._aes_key_windows(buried)
    offs = {off for off, cand in bs._aes_key_windows_offs(flagged) if cand == key}
    assert 1 in offs


def test_abe_key_from_material_walks_flag_byte_key():
    from secturafab import browser_session as bs

    cookie_key = os.urandom(32)
    cookie_nonce = os.urandom(12)
    cookie_blob = b"v20" + cookie_nonce + _aes_gcm_encrypt(
        (b"\x66" * 32) + b"session", cookie_key, cookie_nonce
    )
    bs._cache["_v20_verify"] = [cookie_blob]
    bs._cache["_abe_hit"] = ""
    bs._cache["_app_bound_blob"] = None
    try:
        assert bs._abe_key_from_material(b"\x01" + cookie_key, cookie_blob) == cookie_key
        assert str(bs._cache.get("_abe_hit") or "").startswith("apc:key:off=1")
        buried = b"\x00" * 7 + cookie_key
        assert bs._abe_key_from_material(buried, cookie_blob) == cookie_key
        assert "off=7" in str(bs._cache.get("_abe_hit") or "")
        assert bs._v20_one_ok(cookie_key, cookie_blob) is True
        assert bs._v20_one_ok(os.urandom(32), cookie_blob) is False
    finally:
        bs._cache["_v20_verify"] = []
        bs._cache["_abe_hit"] = ""


def test_app_bound_layout_fingerprint_dpapi_and_flag():
    from secturafab import browser_session as bs

    dpapi = b"\x01\x00\x00\x00" + os.urandom(80)
    fp, views = bs._app_bound_layout_views(dpapi)
    assert fp.startswith("appb:dpapi:")
    assert dpapi[-60:] in views
    flag = b"\x01" + os.urandom(12) + os.urandom(32) + os.urandom(16)
    fp2, views2 = bs._app_bound_layout_views(flag)
    assert fp2.startswith("appb:flag1:")
    assert flag[1:] in views2


def test_dpapi_640_plain_length_prefix_is_cookie_key():
    from secturafab import browser_session as bs

    cookie_key = os.urandom(32)
    cookie_nonce = os.urandom(12)
    cookie_blob = b"v20" + cookie_nonce + _aes_gcm_encrypt(
        (b"\x55" * 32) + b"session", cookie_key, cookie_nonce
    )
    inner = (0).to_bytes(4, "little") + (32).to_bytes(4, "little") + cookie_key
    blob = b"\x01\x00\x00\x00" + os.urandom(636)
    assert len(blob) == 640
    bs._cache["_app_bound_blob"] = blob
    bs._cache["_v20_verify"] = [cookie_blob]
    bs._cache["_dpapi_hr"] = ""
    try:
        fp, _views = bs._app_bound_layout_views(blob)
        assert fp.startswith("appb:dpapi:640")
        assert bs._cookie_key_from_unprotect_plain(inner, cookie_blob) == cookie_key
        with patch.object(bs, "_dpapi_unprotect_appb", return_value=inner):
            assert bs._static_app_bound_cookie_key(cookie_blob) == cookie_key
    finally:
        bs._cache["_app_bound_blob"] = None
        bs._cache["_v20_verify"] = []
        bs._cache["_appb_views"] = []
        bs._cache["_appb_fp"] = ""
        bs._cache["_dpapi_hr"] = ""


def test_dpapi_640_nested_unprotect_then_length_prefix():
    from secturafab import browser_session as bs

    cookie_key = os.urandom(32)
    cookie_nonce = os.urandom(12)
    cookie_blob = b"v20" + cookie_nonce + _aes_gcm_encrypt(
        (b"\x77" * 32) + b"session", cookie_key, cookie_nonce
    )
    inner = (32).to_bytes(4, "little") + cookie_key
    user_dpapi = b"\x01\x00\x00\x00" + os.urandom(80)
    blob = b"\x01\x00\x00\x00" + os.urandom(636)
    assert len(blob) == 640
    bs._cache["_app_bound_blob"] = blob
    bs._cache["_v20_verify"] = [cookie_blob]
    bs._cache["_dpapi_hr"] = ""
    plains = iter([user_dpapi, inner])

    def _once(current):
        try:
            return next(plains)
        except StopIteration:
            return None

    try:
        with patch.object(bs, "_dpapi_unprotect_local", side_effect=_once), patch.object(
            bs, "_impersonate_chrome_unprotect", return_value=None
        ), patch.object(bs, "_chrome_unprotect_data", return_value=None), patch.object(
            bs, "_chrome_unprotect_memory_blob", return_value=None
        ):
            assert bs._static_app_bound_cookie_key(cookie_blob) == cookie_key
    finally:
        bs._cache["_app_bound_blob"] = None
        bs._cache["_v20_verify"] = []
        bs._cache["_appb_views"] = []
        bs._cache["_appb_fp"] = ""
        bs._cache["_dpapi_hr"] = ""


def test_dpapi_blob_slices_full_then_appb_then_header():
    from secturafab import browser_session as bs

    body = b"\x01\x00\x00\x00" + os.urandom(636)
    raw = b"APPB" + body
    bs._cache["_app_bound_raw"] = raw
    try:
        slices = bs._dpapi_blob_slices(body)
        assert slices[0] == raw
        assert slices[1] == body
        assert slices[2] == body[4:]
        labels = [lab for lab, _part in bs._dpapi_offset_views(body)]
        assert labels[0] == "appb"
        for off in (0, 4, 8, 12, 16, 32, 44):
            assert str(off) in labels
    finally:
        bs._cache["_app_bound_raw"] = None


def test_dpapi_walk_records_winning_offset():
    from secturafab import browser_session as bs

    body = b"\x01\x00\x00\x00" + os.urandom(636)
    bs._cache["_app_bound_raw"] = b"APPB" + body
    bs._cache["_dpapi_hr"] = ""

    def _ex(part: bytes, flags: int = 0, entropy: bytes | None = None):
        del flags, entropy
        if part == body[16:]:
            bs._cache["_dpapi_last_win32"] = 0
            return b"\x22" * 32
        bs._cache["_dpapi_last_win32"] = 13
        return None

    try:
        with patch.object(bs, "_dpapi_unprotect_ex", side_effect=_ex):
            got = bs._dpapi_unprotect_local(body)
        assert got == b"\x22" * 32
        hr = str(bs._cache.get("_dpapi_hr") or "")
        assert "dpapi:ok" in hr
        assert "dpapi:len=32" in hr
        assert "dpapi:off=16" in hr
    finally:
        bs._cache["_app_bound_raw"] = None
        bs._cache["_dpapi_hr"] = ""
        bs._cache["_dpapi_last_win32"] = None


def test_dpapi_walk_all13():
    from secturafab import browser_session as bs

    body = b"\x01\x00\x00\x00" + os.urandom(636)
    bs._cache["_app_bound_raw"] = b"APPB" + body
    bs._cache["_dpapi_hr"] = ""

    def _ex(*_a, **_k):
        bs._cache["_dpapi_last_win32"] = 13
        return None

    try:
        with patch.object(bs, "_dpapi_unprotect_ex", side_effect=_ex):
            assert bs._dpapi_unprotect_local(body) is None
        assert bs._cache["_dpapi_hr"] == "dpapi:all13;next=chrome_open"
        bs._cache["_appb_fp"] = "appb:dpapi:640"
        hr = bs._join_abe_hr(["run:4551"])
        assert hr.startswith("dpapi:all13")
        assert "next=chrome_open" in hr
        assert "appb:dpapi:640" in hr
    finally:
        bs._cache["_app_bound_raw"] = None
        bs._cache["_dpapi_hr"] = ""
        bs._cache["_appb_fp"] = ""
        bs._cache["_dpapi_last_win32"] = None


def test_join_abe_hr_includes_dpapi_win32_and_len():
    from secturafab import browser_session as bs

    bs._cache["_appb_fp"] = "appb:dpapi:640"
    bs._cache["_dpapi_hr"] = "dpapi:ok;dpapi:len=32;dpapi:off=16"
    try:
        hr = bs._join_abe_hr(["run:4551"])
        assert hr.startswith("dpapi:ok")
        assert "appb:dpapi:640" in hr
        assert "dpapi:len=32" in hr
        assert "dpapi:off=16" in hr
    finally:
        bs._cache["_appb_fp"] = ""
        bs._cache["_dpapi_hr"] = ""
    bs._cache["_appb_fp"] = "appb:dpapi:640"
    bs._cache["_dpapi_hr"] = "dpapi:win32=13"
    try:
        hr = bs._join_abe_hr(["run:4551"])
        assert "dpapi:win32=13" in hr
        assert "appb:dpapi:640" in hr
    finally:
        bs._cache["_appb_fp"] = ""
        bs._cache["_dpapi_hr"] = ""


def test_dpapi_ok_plain_after_header_is_cookie_key():
    from secturafab import browser_session as bs

    cookie_key = os.urandom(32)
    cookie_nonce = os.urandom(12)
    cookie_blob = b"v20" + cookie_nonce + _aes_gcm_encrypt(
        (b"\x99" * 32) + b"session", cookie_key, cookie_nonce
    )
    # Successful CryptUnprotect payload after the DPAPI version dword.
    inner = b"\x01\x00\x00\x00" + cookie_key
    blob = b"\x01\x00\x00\x00" + os.urandom(636)
    bs._cache["_app_bound_blob"] = blob
    bs._cache["_v20_verify"] = [cookie_blob]
    try:
        assert bs._cookie_key_from_unprotect_plain(inner, cookie_blob) == cookie_key
    finally:
        bs._cache["_app_bound_blob"] = None
        bs._cache["_v20_verify"] = []


def test_offs_plus_win32_13_is_all13():
    from secturafab import browser_session as bs

    body = b"\x01\x00\x00\x00" + os.urandom(636)
    bs._cache["_app_bound_raw"] = b"APPB" + body
    bs._cache["_appb_fp"] = "appb:dpapi:640"
    bs._cache["_dpapi_hr"] = ""
    n = {"i": 0}

    def _ex(*_a, **_k):
        # First slice 13, later 0 — b3117cb reported win32=13;offs=9 instead of all13.
        n["i"] += 1
        bs._cache["_dpapi_last_win32"] = 13 if n["i"] == 1 else 0
        return None

    try:
        with patch.object(bs, "_dpapi_unprotect_ex", side_effect=_ex):
            assert bs._dpapi_unprotect_local(body) is None
        assert bs._cache["_dpapi_hr"] == "dpapi:all13;next=chrome_open"
        bs._cache["_dpapi_hr"] = "dpapi:win32=13;dpapi:offs=9"
        hr = bs._join_abe_hr(["run:4551"])
        assert hr.startswith("dpapi:all13")
        assert "next=chrome_open" in hr
    finally:
        bs._cache["_app_bound_raw"] = None
        bs._cache["_appb_fp"] = ""
        bs._cache["_dpapi_hr"] = ""


def test_dpapi_unprotect_appb_stops_after_all13():
    from secturafab import browser_session as bs

    blob = b"\x01\x00\x00\x00" + os.urandom(636)
    bs._cache["_dpapi_hr"] = "dpapi:all13;next=chrome_open"
    try:
        with patch.object(
            bs, "_dpapi_unprotect_local", side_effect=AssertionError("all13 must not CryptUnprotect")
        ), patch.object(
            bs, "_impersonate_chrome_unprotect", side_effect=AssertionError("all13 must not CryptUnprotect")
        ), patch.object(
            bs, "_chrome_unprotect_data", side_effect=AssertionError("all13 must not CryptUnprotect")
        ), patch.object(
            bs, "_chrome_unprotect_memory_blob", side_effect=AssertionError("all13 must not CryptUnprotect")
        ):
            assert bs._dpapi_unprotect_appb(blob) is None
    finally:
        bs._cache["_dpapi_hr"] = ""


def test_all13_chrome_open_uses_memscan():
    from secturafab import browser_session as bs

    cookie_key = os.urandom(32)
    cookie_nonce = os.urandom(12)
    cookie_blob = b"v20" + cookie_nonce + _aes_gcm_encrypt(
        (b"\xaa" * 32) + b"session", cookie_key, cookie_nonce
    )
    body = b"\x01\x00\x00\x00" + os.urandom(636)
    bs._cache["_app_bound_blob"] = body
    bs._cache["_app_bound_raw"] = b"APPB" + body
    bs._cache["_v20_verify"] = [cookie_blob]
    bs._cache["_dpapi_hr"] = ""

    def _ex(*_a, **_k):
        bs._cache["_dpapi_last_win32"] = 13
        return None

    try:
        def _no_dpapi(*_a, **_k):
            raise AssertionError("all13 must not retry CryptUnprotect")

        with patch.object(bs, "_dpapi_unprotect_ex", side_effect=_ex), patch.object(
            bs, "_chrome_pids_prioritized", return_value=[4242]
        ), patch.object(
            bs, "_memscan_abe_key", return_value=(cookie_key, "ok")
        ), patch.object(
            bs, "_static_app_bound_cookie_key", side_effect=_no_dpapi
        ), patch.object(
            bs, "_dpapi_unprotect_appb", side_effect=_no_dpapi
        ), patch.object(
            bs, "_impersonate_chrome_unprotect", side_effect=_no_dpapi
        ), patch.object(
            bs, "_chrome_unprotect_data", side_effect=_no_dpapi
        ), patch.object(
            bs,
            "_compiled_abe_helper_exe",
            side_effect=AssertionError("all13 must not CoCreate or retry DPAPI"),
        ):
            key, hr = bs._elevator_decrypt_via_chrome_dir(cookie_blob)
        assert key == cookie_key
        assert hr == "0x00000000"
    finally:
        bs._cache["_app_bound_blob"] = None
        bs._cache["_app_bound_raw"] = None
        bs._cache["_v20_verify"] = []
        bs._cache["_dpapi_hr"] = ""
        bs._cache["_appb_fp"] = ""


def test_all13_skips_helper_and_leads_abe_hr():
    from secturafab import browser_session as bs

    body = b"\x01\x00\x00\x00" + os.urandom(636)
    sample = b"v20" + b"\x00" * 40
    bs._cache["_app_bound_blob"] = body
    bs._cache["_app_bound_raw"] = b"APPB" + body
    bs._cache["_v20_verify"] = [sample]
    bs._cache["_dpapi_hr"] = ""

    def _ex(*_a, **_k):
        bs._cache["_dpapi_last_win32"] = 13
        return None

    try:
        with patch.object(bs, "_dpapi_unprotect_ex", side_effect=_ex), patch.object(
            bs, "_chrome_pids_prioritized", return_value=[]
        ), patch.object(
            bs,
            "_compiled_abe_helper_exe",
            side_effect=AssertionError("all13 must not retry CryptUnprotect"),
        ):
            key, hr = bs._elevator_decrypt_via_chrome_dir(sample)
        assert key is None
        assert hr.startswith("dpapi:all13")
        assert "next=chrome_open" in hr
        assert "appb:dpapi:640" in hr
        assert "run:4551" not in hr
    finally:
        bs._cache["_app_bound_blob"] = None
        bs._cache["_app_bound_raw"] = None
        bs._cache["_v20_verify"] = []
        bs._cache["_dpapi_hr"] = ""
        bs._cache["_appb_fp"] = ""


def test_disk_dpapi_unwrap_succeeds_without_chrome():
    from secturafab import browser_session as bs

    cookie_key = os.urandom(32)
    cookie_nonce = os.urandom(12)
    cookie_blob = b"v20" + cookie_nonce + _aes_gcm_encrypt(
        (b"\x88" * 32) + b"session", cookie_key, cookie_nonce
    )
    inner = (32).to_bytes(4, "little") + cookie_key
    blob = b"\x01\x00\x00\x00" + os.urandom(636)
    bs._cache["_app_bound_blob"] = blob
    bs._cache["_v20_verify"] = [cookie_blob]
    bs._cache["_appb_fp"] = ""
    try:
        with patch.object(bs, "_dpapi_unprotect_local", return_value=inner), patch.object(
            bs, "_chrome_pids_prioritized", return_value=[]
        ), patch.object(
            bs, "_memscan_abe_key", side_effect=AssertionError("disk unwrap must not need memscan")
        ), patch.object(
            bs, "_compiled_abe_helper_exe", side_effect=AssertionError("disk unwrap must not need helper")
        ):
            key, hr = bs._elevator_decrypt_via_chrome_dir(cookie_blob)
        assert key == cookie_key
        assert hr == "0x00000000"
    finally:
        bs._cache["_app_bound_blob"] = None
        bs._cache["_v20_verify"] = []
        bs._cache["_appb_views"] = []
        bs._cache["_appb_fp"] = ""


def test_no_chrome_hr_keeps_appb_fp():
    from secturafab import browser_session as bs

    blob = b"\x01\x00\x00\x00" + os.urandom(636)
    sample = b"v20" + b"\x00" * 40
    bs._cache["_app_bound_blob"] = blob
    bs._cache["_v20_verify"] = [sample]
    bs._cache["_appb_fp"] = ""
    try:
        with patch.object(bs, "_dpapi_unprotect_local", return_value=None), patch.object(
            bs, "_dpapi_unprotect_appb", return_value=None
        ), patch.object(bs, "_chrome_pids_prioritized", return_value=[]), patch.object(
            bs, "_compiled_abe_helper_exe", return_value=(None, "csc_missing")
        ), patch.object(
            bs, "_memscan_abe_key", side_effect=AssertionError("closed Chrome skips memscan")
        ):
            key, hr = bs._elevator_decrypt_via_chrome_dir(sample)
        assert key is None
        assert "appb:dpapi:640" in hr
        assert "CLASSNOTREG" not in hr
    finally:
        bs._cache["_app_bound_blob"] = None
        bs._cache["_v20_verify"] = []
        bs._cache["_appb_views"] = []
        bs._cache["_appb_fp"] = ""


def test_dpapi_640_plain_flag1_inner_is_cookie_key():
    from secturafab import browser_session as bs

    cookie_key = os.urandom(32)
    nonce = os.urandom(12)
    cookie_nonce = os.urandom(12)
    cookie_blob = b"v20" + cookie_nonce + _aes_gcm_encrypt(
        (b"\x66" * 32) + b"session", cookie_key, cookie_nonce
    )
    inner = b"\x01" + nonce + _aes_gcm_encrypt(cookie_key, bs._FLAG1_AES, nonce)
    blob = b"\x01\x00\x00\x00" + os.urandom(636)
    bs._cache["_app_bound_blob"] = blob
    bs._cache["_v20_verify"] = [cookie_blob]
    bs._cache["_dpapi_hr"] = ""
    try:
        with patch.object(bs, "_dpapi_unprotect_appb", return_value=inner):
            assert bs._static_app_bound_cookie_key(cookie_blob) == cookie_key
    finally:
        bs._cache["_app_bound_blob"] = None
        bs._cache["_v20_verify"] = []
        bs._cache["_appb_views"] = []
        bs._cache["_appb_fp"] = ""
        bs._cache["_dpapi_hr"] = ""


def test_flag1_wrap_unwraps_local_state_then_cookie():
    from secturafab import browser_session as bs

    cookie_key = os.urandom(32)
    nonce = os.urandom(12)
    cookie_nonce = os.urandom(12)
    cookie_blob = b"v20" + cookie_nonce + _aes_gcm_encrypt(
        (b"\x44" * 32) + b"session", cookie_key, cookie_nonce
    )
    inner = b"\x01" + nonce + _aes_gcm_encrypt(cookie_key, bs._FLAG1_AES, nonce)
    bs._cache["_app_bound_blob"] = inner
    bs._cache["_v20_verify"] = [cookie_blob]
    bs._cache["_v10_key"] = None
    try:
        assert bs._static_app_bound_cookie_key(cookie_blob) == cookie_key
    finally:
        bs._cache["_app_bound_blob"] = None
        bs._cache["_v20_verify"] = []
        bs._cache["_appb_views"] = []
        bs._cache["_appb_fp"] = ""


def test_abe_wrap_key_unwraps_app_bound_then_cookie():
    from secturafab import browser_session as bs

    wrap = os.urandom(32)
    cookie_key = os.urandom(32)
    nonce = os.urandom(12)
    cookie_nonce = os.urandom(12)
    cookie_plain = (b"\x22" * 32) + b"session"
    cookie_blob = b"v20" + cookie_nonce + _aes_gcm_encrypt(cookie_plain, cookie_key, cookie_nonce)
    app_bound = nonce + _aes_gcm_encrypt(cookie_key, wrap, nonce)
    bs._cache["_app_bound_blob"] = app_bound
    bs._cache["_v20_verify"] = [cookie_blob]
    try:
        assert bs._v20_key_ok(wrap, cookie_blob) is False
        assert bs._abe_key_from_material(wrap, cookie_blob) == cookie_key
        prefixed = b"APPB" + app_bound
        bs._cache["_app_bound_blob"] = prefixed
        assert bs._abe_key_from_material(wrap, cookie_blob) == cookie_key
    finally:
        bs._cache["_app_bound_blob"] = None
        bs._cache["_v20_verify"] = []


def test_abe_wrap_key_unwraps_embedded_and_tag_before_ct():
    """Chrome 151: GCM record is not always the whole APPB body; tag may precede ct."""
    from secturafab import browser_session as bs

    wrap = os.urandom(32)
    cookie_key = os.urandom(32)
    cookie_nonce = os.urandom(12)
    cookie_blob = b"v20" + cookie_nonce + _aes_gcm_encrypt(
        (b"\x33" * 32) + b"session", cookie_key, cookie_nonce
    )
    nonce = os.urandom(12)
    ct_tag = _aes_gcm_encrypt(cookie_key, wrap, nonce)
    ct, tag = ct_tag[:-16], ct_tag[-16:]
    headered = b"\x00" * 40 + nonce + ct_tag
    tag_first = nonce + tag + ct
    flagged = b"\x01" + nonce + ct_tag
    bs._cache["_v20_verify"] = [cookie_blob]
    try:
        bs._cache["_app_bound_blob"] = headered
        assert bs._abe_key_from_material(wrap, cookie_blob) == cookie_key
        bs._cache["_app_bound_blob"] = tag_first
        assert bs._abe_key_from_material(wrap, cookie_blob) == cookie_key
        bs._cache["_app_bound_blob"] = flagged
        assert bs._abe_key_from_material(wrap, cookie_blob) == cookie_key
    finally:
        bs._cache["_app_bound_blob"] = None
        bs._cache["_v20_verify"] = []


def test_unwrap_zero_hr_requires_cookie_text():
    from secturafab import browser_session as bs

    wrap = os.urandom(32)
    b64 = base64.b64encode(b"APPB" + b"\x01" * 40).decode("ascii")
    dummy = b"v20" + b"\x00" * 40
    bs._cache["_v20_verify"] = [dummy]
    try:
        with patch.object(
            bs, "_elevator_decrypt_via_chrome_dir", return_value=(wrap, "0x00000000")
        ), patch.object(
            bs, "_elevator_decrypt", side_effect=AssertionError("no CoCreate")
        ):
            key, status, hr = bs._unwrap_app_bound_key(b64, v20_sample=dummy)
        assert key is None
        assert status == "chrome_dir"
        assert hr != "0x00000000"
        assert "CLASSNOTREG" not in hr
    finally:
        bs._cache["_v20_verify"] = []
        bs._cache["_app_bound_blob"] = None


def test_v20_key_ok_accepts_offset_apc_plain():
    from secturafab import browser_session as bs

    key = os.urandom(32)
    nonce = os.urandom(12)
    plain = (b"\x22" * 32) + b"session"
    blob = b"v20" + nonce + _aes_gcm_encrypt(plain, key, nonce)
    bs._cache["_v20_verify"] = [blob]
    try:
        assert bs._v20_key_ok(b"\xaa" * 8 + key + b"\xbb" * 8, blob) is True
    finally:
        bs._cache["_v20_verify"] = []


def test_v20_key_ok_uses_apc_plain_against_any_of_the_blobs():
    from secturafab import browser_session as bs

    key = os.urandom(32)
    other = os.urandom(32)
    nonce_long = os.urandom(12)
    nonce_ok = os.urandom(12)
    long_plain = (b"\x11" * 32) + (b"x" * 80)
    ok_plain = (b"\x22" * 32) + b"session"
    long_blob = b"v20" + nonce_long + _aes_gcm_encrypt(long_plain, other, nonce_long)
    ok_blob = b"v20" + nonce_ok + _aes_gcm_encrypt(ok_plain, key, nonce_ok)
    assert len(long_blob) > len(ok_blob)
    bs._cache["_v20_verify"] = []
    assert bs._v20_key_ok(key, long_blob) is False
    bs._cache["_v20_verify"] = [long_blob, ok_blob]
    try:
        assert bs._v20_key_ok(key, long_blob) is True
        assert bs._pick_v20_sample([("h", "n", "", long_blob), ("h", "n", "", ok_blob)]) == long_blob
    finally:
        bs._cache["_v20_verify"] = []


def test_chrome_dir_copy_denied_is_not_classnotreg(tmp_path: Path):
    from secturafab import browser_session as bs

    helper = tmp_path / "kannon_quote_abe.exe"
    helper.write_bytes(b"mz")

    def _denied(*_a, **_k):
        exc = OSError(13, "Permission denied")
        raise exc

    with patch.object(bs.os, "name", "nt"), patch.object(
        bs, "_compiled_abe_helper_exe", return_value=(helper, "")
    ), patch.object(
        bs, "_user_abe_helper_dirs", return_value=[tmp_path / "abe"]
    ), patch.object(
        bs.shutil, "copy2", side_effect=_denied
    ), patch.object(
        bs, "_run_abe_helper", return_value=(None, "helper:exit1")
    ), patch.object(
        bs, "_memscan_abe_key", return_value=(None, "memscan:no_key")
    ):
        key, hr = bs._elevator_decrypt_via_chrome_dir(b"v20" + b"\x00" * 40)
    assert key is None
    assert "CLASSNOTREG" not in hr
    assert "copy:errno13" in hr or "helper:exit1" in hr or "memscan:no_key" in hr


def test_key_from_helper_candidates_decrypts_v20():
    from secturafab import browser_session as bs

    key = os.urandom(32)
    nonce = os.urandom(12)
    plain = (b"\x11" * 32) + b"session"
    payload = _aes_gcm_encrypt(plain, key, nonce)
    sample = b"v20" + nonce + payload
    stdout = f"cand={'00' * 32}\ncand={key.hex()}\n".encode("ascii")
    got = bs._key_from_helper_candidates(stdout, sample)
    assert got == key


def test_profile_1_does_not_run_vss_or_lock_bypass(tmp_path: Path):
    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    _write_cookie_db(db)
    profile = {
        "label": "chrome:Profile 1",
        "cookies": db,
        "local_state": tmp_path / "Local State",
        "profile_dir": tmp_path,
        "history_hit": False,
    }

    def _nope(*_a, **_k):
        raise AssertionError("Profile 1 must not CREATE VSS or lock-bypass")

    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]), patch.object(
        bs, "_win_vss_copy", side_effect=_nope
    ), patch.object(bs, "_win_lock_bypass_with_wal", side_effect=_nope):
        header = bs._discover_windows_chrome(force=True)
    assert header
    status = bs.discover_status()
    assert status["vss"] == ""
    assert status["source"] == "chrome:Profile 1"


def _aes_gcm_encrypt(plain: bytes, key: bytes, nonce: bytes) -> bytes:
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        return AESGCM(key).encrypt(nonce, plain, None)
    except Exception:  # noqa: BLE001
        from Crypto.Cipher import AES  # type: ignore[import-untyped]

        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        ct, tag = cipher.encrypt_and_digest(plain)
        return ct + tag
