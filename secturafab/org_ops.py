"""Assign SecturaFAB quote Organization (customer dropdown)."""

from __future__ import annotations

import re
from typing import Any

from .client import SecturaFabClient

# Kyle-confirmed Time Manufacturing Waco tenant org (do not search-guess).
TIME_WACO_ORG_ID = "b7dbc294-3fd2-43aa-99be-268a6c4fce14"
TIME_WACO_ORG_NAME = "Time Manufacturing Waco"


def _org_blob(org: dict[str, Any]) -> str:
    return " ".join(
        str(org.get(k) or "")
        for k in ("OrganizationName", "DisplayName", "NameAndLocation", "Name")
    ).casefold()


def list_organizations(client: SecturaFabClient) -> list[dict[str, Any]]:
    """Page every org, then Search=Time/Waco — do not stop after the first page of others."""
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    queries = (
        "v1/organization?PageNumber={page}&PageSize=100",
        "v1/organization?PageNumber={page}&PageSize=100&Search=Time",
        "v1/organization?PageNumber={page}&PageSize=100&Search=Waco",
        "v1/organization?PageNumber={page}&PageSize=100&Search=TIME",
        "v1/organization?PageNumber={page}&PageSize=100&Name=Time",
    )
    for template in queries:
        page = 1
        while page <= 20:
            try:
                data = client.get_json(template.format(page=page))
            except Exception:  # noqa: BLE001 — try the next query shape
                break
            if not isinstance(data, dict):
                break
            batch = list(data.get("Results") or [])
            for org in batch:
                if not isinstance(org, dict) or not org.get("ID"):
                    continue
                oid = str(org["ID"])
                if oid in seen:
                    continue
                seen.add(oid)
                found.append(org)
            if not data.get("HasNext"):
                break
            page += 1
    return found


def _score_organization(org: dict[str, Any], want: str) -> float:
    blob = _org_blob(org)
    if not blob:
        return -1.0
    target = (want or "").strip().casefold()
    if not target:
        return -1.0
    if blob == target:
        return 100.0
    if target in blob:
        return 90.0
    if blob.startswith(target + " ") or blob.startswith(target + "-"):
        return 85.0
    tokens = [t for t in re.findall(r"[a-z0-9]+", target) if len(t) > 2]
    score = 0.0
    for tok in tokens:
        if tok in blob:
            score += 25.0
        if tok == "time" and "time" in blob:
            score += 20.0
        if tok == "waco" and "waco" in blob:
            score += 20.0
    if org.get("Active") is False:
        score -= 40.0
    return score


def find_organization_by_name(
    client: SecturaFabClient, name: str
) -> dict[str, Any] | None:
    """
    Return the tenant Organization that best matches ``name``.

    Live Time tenant does not always expose the display string
    ``Time Manufacturing Waco`` — list orgs and bind Time + Waco / Time Mfg.
    """
    target = (name or "").strip()
    if not target:
        return None
    orgs = list_organizations(client)
    if not orgs:
        return None
    aliases = [target]
    lower = target.casefold()
    if "time" in lower:
        aliases.extend(["Time Waco", "Time Manufacturing", "Time", "Waco", "TIME"])
    best = None
    best_score = -1.0
    for alias in aliases:
        for org in orgs:
            score = _score_organization(org, alias)
            if score > best_score:
                best, best_score = org, score
    if not best or best_score < 40:
        return None
    return best


def apply_quote_organization(
    client: SecturaFabClient,
    quote_id: str,
    *,
    organization_name: str,
    description: str | None = None,
) -> list[str]:
    """
    Set the quote's Existing Organization dropdown.

    Must run **before** Profile/Weld attach — full-quote POST after ops can wipe them.
    Re-run at the end of push so later ItemList POSTs cannot leave Organization null.
    """
    notes: list[str] = []
    name = (organization_name or "").strip()
    if not name or not quote_id:
        return notes

    org = find_organization_by_name(client, name)
    want_time_waco = "time" in name.casefold() and "waco" in name.casefold()
    if want_time_waco:
        org = {
            "ID": TIME_WACO_ORG_ID,
            "OrganizationName": (org or {}).get("OrganizationName") or TIME_WACO_ORG_NAME,
            "DisplayName": (org or {}).get("DisplayName") or TIME_WACO_ORG_NAME,
            "NameAndLocation": (org or {}).get("NameAndLocation") or TIME_WACO_ORG_NAME,
            "PrimaryContactID": (org or {}).get("PrimaryContactID"),
        }
    if not org or not org.get("ID"):
        listed = list_organizations(client)
        sample = ", ".join(
            (
                str(o.get("OrganizationName") or o.get("DisplayName") or o.get("ID") or "")
                for o in listed[:8]
            )
        )
        notes.append(
            f"WARNING: SecturaFAB Organization '{name}' not found in "
            f"{len(listed)} tenant org(s)"
            + (f" (e.g. {sample})" if sample else "")
            + " — set dropdown manually"
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
    actual_name = (
        org.get("OrganizationName")
        or org.get("DisplayName")
        or org.get("NameAndLocation")
        or name
    )
    detail["PrimaryOrganizationID"] = org_id
    detail["OrganizationID"] = org_id
    detail["OrganizationName"] = actual_name
    detail["Organization"] = entry
    detail["OrganizationList"] = [entry]
    if description:
        detail["Description"] = str(description)[:500]
    contact_id = org.get("PrimaryContactID")
    if contact_id and str(contact_id) not in (
        "",
        "00000000-0000-0000-0000-000000000000",
    ):
        detail["PrimaryContactID"] = contact_id

    from .website import v1_quote_body_without_itemlist

    save = client.request("POST", "v1/quote", json=v1_quote_body_without_itemlist(detail))
    try:
        status = int(getattr(save, "status_code", 200) or 200)
    except (TypeError, ValueError):
        status = 200
    if status >= 400:
        notes.append(
            f"WARNING: Setting Organization '{name}' failed ({status})"
        )
        return notes

    check = client.get_json(f"v1/quote/{quote_id}")
    got = str(check.get("OrganizationName") or "").strip()
    got_id = str(check.get("PrimaryOrganizationID") or "").strip()
    if got_id == org_id or (
        got
        and (
            got.casefold() == str(actual_name).casefold()
            or "time" in got.casefold()
        )
    ):
        notes.append(f"Set Organization: {got or actual_name} ({org_id})")
    else:
        notes.append(
            f"WARNING: Organization save returned name={got or '(blank)'} "
            f"id={got_id or '(blank)'} (bound {actual_name} {org_id})"
        )
    return notes


def persist_quote_header(
    client: SecturaFabClient,
    quote_id: str,
    *,
    organization_name: str | None = None,
    description: str | None = None,
) -> list[str]:
    """Re-apply org + Description after ItemList POSTs so a live GET is not blank/PN."""
    notes: list[str] = []
    if organization_name:
        notes.extend(
            apply_quote_organization(
                client,
                quote_id,
                organization_name=organization_name,
                description=description,
            )
        )
        return notes
    desc = (description or "").strip()
    if not desc or not quote_id:
        return notes
    detail = client.get_json(f"v1/quote/{quote_id}")
    if str(detail.get("Description") or "").strip() == desc:
        return notes
    detail["Description"] = desc[:500]
    from .website import v1_quote_body_without_itemlist

    save = client.request("POST", "v1/quote", json=v1_quote_body_without_itemlist(detail))
    try:
        status = int(getattr(save, "status_code", 200) or 200)
    except (TypeError, ValueError):
        status = 200
    if status >= 400:
        notes.append(f"WARNING: Setting quote Description failed ({status})")
    else:
        notes.append(f"Persisted quote Description: {desc[:80]}")
    return notes
