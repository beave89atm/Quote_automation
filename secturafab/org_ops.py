"""Assign SecturaFAB quote Organization (customer dropdown)."""

from __future__ import annotations

from typing import Any

from .client import SecturaFabClient


def find_organization_by_name(
    client: SecturaFabClient, name: str
) -> dict[str, Any] | None:
    """Return the first active Organization whose name matches ``name`` (case-insensitive)."""
    target = (name or "").strip().casefold()
    if not target:
        return None
    page = 1
    while page <= 20:
        data = client.get_json(f"v1/organization?PageNumber={page}&PageSize=100")
        results = list(data.get("Results") or [])
        for org in results:
            for key in ("OrganizationName", "DisplayName", "NameAndLocation"):
                val = str(org.get(key) or "").strip()
                if val.casefold() == target:
                    return org
                # Allow "Propell - Dallas" style matches on DisplayName.
                if val.casefold().startswith(target + " ") or val.casefold().startswith(
                    target + "-"
                ):
                    return org
        if not data.get("HasNext"):
            break
        page += 1
    return None


def apply_quote_organization(
    client: SecturaFabClient,
    quote_id: str,
    *,
    organization_name: str,
) -> list[str]:
    """
    Set the quote's Existing Organization dropdown.

    Must run **before** Profile/Weld attach — full-quote POST after ops can wipe them.
    """
    notes: list[str] = []
    name = (organization_name or "").strip()
    if not name or not quote_id:
        return notes

    org = find_organization_by_name(client, name)
    if not org or not org.get("ID"):
        notes.append(
            f"WARNING: SecturaFAB Organization '{name}' not found — set dropdown manually"
        )
        return notes

    org_id = str(org["ID"])
    detail = client.get_json(f"v1/quote/{quote_id}")
    entry = {
        "ID": org_id,
        "OrganizationName": org.get("OrganizationName") or name,
        "DisplayName": org.get("DisplayName") or name,
        "NameAndLocation": org.get("NameAndLocation") or name,
        "ParentID": quote_id,
        "Active": True,
    }
    detail["PrimaryOrganizationID"] = org_id
    detail["OrganizationName"] = org.get("OrganizationName") or name
    detail["OrganizationList"] = [entry]
    contact_id = org.get("PrimaryContactID")
    if contact_id and str(contact_id) not in (
        "",
        "00000000-0000-0000-0000-000000000000",
    ):
        detail["PrimaryContactID"] = contact_id

    save = client.request("POST", "v1/quote", json=detail)
    if save.status_code >= 400:
        notes.append(
            f"WARNING: Setting Organization '{name}' failed ({save.status_code})"
        )
        return notes

    check = client.get_json(f"v1/quote/{quote_id}")
    got = str(check.get("OrganizationName") or "").strip()
    if got.casefold() == name.casefold() or got.casefold().startswith(name.casefold()):
        notes.append(f"Set Organization: {got or name}")
    else:
        notes.append(
            f"WARNING: Organization save returned '{got or '(blank)'}' "
            f"(wanted '{name}') — set dropdown manually"
        )
    return notes
