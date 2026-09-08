from pathlib import Path
from unittest.mock import MagicMock, patch

from quote_core.customer_org import (
    detect_organization,
    detect_organization_from_folder,
    detect_organization_from_pdf,
    detect_organization_from_text,
)
from secturafab.org_ops import (
    TIME_WACO_ORG_ID,
    TIME_WACO_ORG_NAME,
    apply_quote_organization,
    find_organization_by_name,
    leftover_org_empty_guid_after_bind_post_201_is_fail,
    org_autocomplete_search_only_is_fail,
    org_empty_guid_after_bind_post_is_fail,
    org_empty_guid_is_fail,
    time_waco_org_entry,
    time_waco_org_id_for_name,
)
from secturafab.website import EMPTY_GUID


def test_detect_tycrop_maps_to_propell():
    text = """
TYCROP MANUFACTURING LTD.
DRAWING NUMBER
1505-6000
WEB REAR BASE
"""
    assert detect_organization_from_text(text) == "Propell"
    assert detect_organization_from_text("MAC TRAILER PART NO") is None


def test_detect_cummins_clean_fuel_maps_to_org():
    text = """
CUMMINS CLEAN FUEL TECHNOLOGIES
DWG NO
MC31-1699
TITLE
PANEL - BACK, UPPER, 604 SERIES SM, 60
"""
    assert detect_organization_from_text(text) == "Cummins Clean Fuel Technologies"
    assert (
        detect_organization_from_text(
            "CONFIDENTIAL AND TRADE SECRET INFORMATION OF NATURAL GAS FUEL SYSTEMS, LLC"
        )
        == "Cummins Clean Fuel Technologies"
    )


def test_detect_time_manufacturing_waco():
    folder = (
        r"C:\Users\Kyle\Kannon Manufacturing Inc\Fort Worth - Documents"
        r"\Engineering\Customer Drawings\Time\Pedestal Weldment - 1001898-1"
    )
    assert detect_organization_from_folder(folder) == "Time Manufacturing Waco"
    assert detect_organization_from_text("TIME MANUFACTURING\n1001898") == (
        "Time Manufacturing Waco"
    )
    assert detect_organization(
        library_folder="Pedestal Weldment - 1001898-1",
        extra_paths=[folder],
    ) == "Time Manufacturing Waco"


def test_detect_organization_from_library_folder():
    folder = (
        r"C:\Users\Kyle\Kannon Manufacturing Inc\Fort Worth - Documents"
        r"\Engineering\Customer Drawings\Cummins Clean Fuel Technologies"
        r"\604-50L-LU01-02CA00XX00-A"
    )
    assert detect_organization_from_folder(folder) == "Cummins Clean Fuel Technologies"
    assert (
        detect_organization(pdf_path=None, library_folder=folder)
        == "Cummins Clean Fuel Technologies"
    )


def test_detect_organization_from_pdf_reads_text(tmp_path: Path):
    # Without a real PDF, missing file returns None; fixture text path covered above.
    missing = tmp_path / "nope.pdf"
    assert detect_organization_from_pdf(missing) is None
    assert detect_organization_from_pdf(None) is None


def test_find_organization_by_name_matches_display():
    client = MagicMock()
    client.get_json.return_value = {
        "HasNext": False,
        "Results": [
            {
                "ID": "abc",
                "OrganizationName": "Propell",
                "DisplayName": "Propell",
            }
        ],
    }
    org = find_organization_by_name(client, "propell")
    assert org is not None
    assert org["ID"] == "abc"


def test_find_organization_fuzzy_time_waco_when_display_differs():
    client = MagicMock()
    client.get_json.return_value = {
        "HasNext": False,
        "Results": [
            {
                "ID": "time-real",
                "OrganizationName": "Time Mfg - Waco",
                "DisplayName": "Time Mfg - Waco",
                "Active": True,
            },
            {
                "ID": "other",
                "OrganizationName": "Propell",
                "DisplayName": "Propell",
                "Active": True,
            },
        ],
    }
    org = find_organization_by_name(client, "Time Manufacturing Waco")
    assert org is not None
    assert org["ID"] == "time-real"


def test_apply_quote_organization_sets_primary_and_list():
    client = MagicMock()

    def _get(path: str):
        if "organization" in str(path).lower():
            return {
                "HasNext": False,
                "Results": [
                    {
                        "ID": "org-1",
                        "OrganizationName": "Propell",
                        "DisplayName": "Propell",
                        "NameAndLocation": "Propell",
                        "PrimaryContactID": "00000000-0000-0000-0000-000000000000",
                    }
                ],
            }
        if "PrimaryOrganizationID" in str(client.request.call_args):
            return {
                "ID": "qid",
                "OrganizationName": "Propell",
                "PrimaryOrganizationID": "org-1",
                "OrganizationList": [{"OrganizationName": "Propell"}],
            }
        return {"ID": "qid", "ItemList": []}

    client.get_json.side_effect = _get
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save

    notes = apply_quote_organization(client, "qid", organization_name="Propell")
    assert any("Set Organization: Propell" in n for n in notes)
    payload = client.request.call_args.kwargs["json"]
    assert payload["PrimaryOrganizationID"] == "org-1"
    assert payload["OrganizationName"] == "Propell"
    assert payload["OrganizationList"][0]["ID"] == "org-1"
    assert payload["OrganizationList"][0]["ParentID"] == "qid"


def test_org_empty_guid_is_fail():
    assert org_empty_guid_is_fail("") is True
    assert org_empty_guid_is_fail(None) is True
    assert org_empty_guid_is_fail(EMPTY_GUID) is True
    assert org_empty_guid_is_fail(TIME_WACO_ORG_ID) is False
    assert org_autocomplete_search_only_is_fail({"search": True, "hits": 0}) is True
    assert org_autocomplete_search_only_is_fail(
        {"via": "autocomplete", "org_id": ""}
    ) is True
    assert org_autocomplete_search_only_is_fail(
        {"via": "#PrimaryOrganizationID", "org_id": TIME_WACO_ORG_ID, "search": False}
    ) is False
    assert time_waco_org_entry()["ID"] == TIME_WACO_ORG_ID


def test_apply_time_waco_binds_known_id_without_org_search():
    client = MagicMock()

    def _get(path: str):
        assert "organization" not in str(path).lower()
        return {
            "ID": "qid",
            "OrganizationName": TIME_WACO_ORG_NAME,
            "PrimaryOrganizationID": TIME_WACO_ORG_ID,
            "ItemList": [],
        }

    client.get_json.side_effect = _get
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save

    with patch("secturafab.chrome_cdp.chrome_edit_signed_in", return_value=False):
        notes = apply_quote_organization(
            client, "qid", organization_name="Time Manufacturing Waco"
        )
    assert any("Set Organization:" in n and TIME_WACO_ORG_ID in n for n in notes)
    payload = client.request.call_args.kwargs["json"]
    assert payload["PrimaryOrganizationID"] == TIME_WACO_ORG_ID
    assert payload["OrganizationList"][0]["ID"] == TIME_WACO_ORG_ID


def test_apply_time_waco_empty_guid_is_fail():
    client = MagicMock()
    n = {"i": 0}

    def _get(path: str):
        n["i"] += 1
        if n["i"] == 1:
            return {"ID": "qid", "ItemList": []}
        return {
            "ID": "qid",
            "OrganizationName": TIME_WACO_ORG_NAME,
            "PrimaryOrganizationID": EMPTY_GUID,
        }

    client.get_json.side_effect = _get
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save

    with patch("secturafab.chrome_cdp.chrome_edit_signed_in", return_value=False):
        notes = apply_quote_organization(
            client, "qid", organization_name="Time Manufacturing Waco"
        )
    blob = " ".join(notes)
    assert "empty GUID" in blob
    assert "FAIL" in blob
    assert "6d4373bc" in blob
    assert "Set Organization:" not in blob
    assert client.request.call_count == 2


def test_time_waco_org_id_for_name_and_leftover_6d4373bc():
    assert time_waco_org_id_for_name("Time Manufacturing Waco") == TIME_WACO_ORG_ID
    assert time_waco_org_id_for_name("TIME WACO") == TIME_WACO_ORG_ID
    assert time_waco_org_id_for_name("Propell") is None
    assert org_empty_guid_after_bind_post_is_fail(EMPTY_GUID, post_status=201) is True
    assert org_empty_guid_after_bind_post_is_fail(TIME_WACO_ORG_ID, post_status=201) is False
    dump = {
        "live_6d4373bc": {
            "quote_id_prefix": "6d4373bc",
            "quote_number": "21684-1",
            "linear_dod_pass": True,
            "post_status": 201,
            "primary_organization_id": EMPTY_GUID,
            "want_org_id": TIME_WACO_ORG_ID,
            "machine": "Saw",
            "product_type": 30,
            "sku": "RTD4X0.375-A513",
            "unit_cost": 9.52,
        }
    }
    assert leftover_org_empty_guid_after_bind_post_201_is_fail(dump) is True
    ok = dict(dump)
    ok["live_6d4373bc"] = dict(dump["live_6d4373bc"])
    ok["live_6d4373bc"]["primary_organization_id"] = TIME_WACO_ORG_ID
    assert leftover_org_empty_guid_after_bind_post_201_is_fail(ok) is False
    assert leftover_org_empty_guid_after_bind_post_201_is_fail(None) is False
    assert leftover_org_empty_guid_after_bind_post_201_is_fail({"linear_dod_pass": True}) is False


def test_apply_time_waco_retry_slim_post_sticks():
    client = MagicMock()
    n = {"i": 0}

    def _get(path: str):
        n["i"] += 1
        if n["i"] < 3:
            return {"ID": "qid", "ItemList": [], "PrimaryOrganizationID": EMPTY_GUID}
        return {
            "ID": "qid",
            "OrganizationName": TIME_WACO_ORG_NAME,
            "PrimaryOrganizationID": TIME_WACO_ORG_ID,
        }

    client.get_json.side_effect = _get
    save = MagicMock()
    save.status_code = 201
    client.request.return_value = save

    with patch("secturafab.chrome_cdp.chrome_edit_signed_in", return_value=False):
        notes = apply_quote_organization(
            client, "qid", organization_name="Time Manufacturing Waco"
        )
    assert any("Set Organization:" in n and TIME_WACO_ORG_ID in n for n in notes)
    assert client.request.call_count == 2
    slim = client.request.call_args_list[1].kwargs["json"]
    assert slim["PrimaryOrganizationID"] == TIME_WACO_ORG_ID
    assert slim["ID"] == "qid"
    assert "ItemList" not in slim


def test_create_quote_stamps_time_waco_on_mint_and_strip():
    from secturafab.push import SecturaFabPushService

    client = MagicMock()
    minted = MagicMock()
    minted.status_code = 201
    minted.text = ""
    strip = MagicMock()
    strip.status_code = 200
    strip.text = ""
    client.request.side_effect = [minted, strip]
    client._parse_or_raise.return_value = "new-qid"
    notes = SecturaFabPushService(client=client).create_quote(
        quote_number="21684-1",
        description="TUBE, CYLINDER ANCHOR",
        organization_name="Time Manufacturing Waco",
    )
    assert notes == "new-qid"
    mint_body = client.request.call_args_list[0].kwargs["json"]
    strip_body = client.request.call_args_list[1].kwargs["json"]
    assert mint_body["PrimaryOrganizationID"] == TIME_WACO_ORG_ID
    assert mint_body["OrganizationID"] == TIME_WACO_ORG_ID
    assert strip_body["PrimaryOrganizationID"] == TIME_WACO_ORG_ID
    assert strip_body["ID"] == "new-qid"


def test_persist_quote_header_blank_description_is_fail_close():
    from secturafab.org_ops import persist_quote_header

    client = MagicMock()
    notes = persist_quote_header(client, "qid", description="  ")
    assert any("Description is blank" in n for n in notes)
    client.get_json.assert_not_called()
    client.request.assert_not_called()
