from pathlib import Path
from unittest.mock import MagicMock

from quote_core.customer_org import (
    detect_organization,
    detect_organization_from_folder,
    detect_organization_from_pdf,
    detect_organization_from_text,
)
from secturafab.org_ops import apply_quote_organization, find_organization_by_name


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


def test_apply_quote_organization_sets_primary_and_list():
    client = MagicMock()
    client.get_json.side_effect = [
        {
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
        },
        {"ID": "qid", "ItemList": []},
        {
            "ID": "qid",
            "OrganizationName": "Propell",
            "PrimaryOrganizationID": "org-1",
            "OrganizationList": [{"OrganizationName": "Propell"}],
        },
    ]
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
