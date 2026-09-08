"""Assign SecturaFAB quote Organization (customer dropdown)."""

from __future__ import annotations

import re
from typing import Any

from .client import SecturaFabClient
from .website import EMPTY_GUID

# Kyle-confirmed Time Manufacturing Waco tenant org (do not search-guess).
TIME_WACO_ORG_ID = "b7dbc294-3fd2-43aa-99be-268a6c4fce14"
TIME_WACO_ORG_NAME = "Time Manufacturing Waco"


def org_empty_guid_is_fail(org_id: str | None) -> bool:
    """PrimaryOrganizationID blank / empty GUID is FAIL (live 34603-2)."""
    raw = str(org_id or "").strip()
    return raw in ("", EMPTY_GUID)


def time_waco_org_id_for_name(name: str | None) -> str | None:
    """Known Time Waco ID only — do not search-guess (live 34603-2)."""
    blob = str(name or "").casefold()
    if "time" in blob and "waco" in blob:
        return TIME_WACO_ORG_ID
    return None


def leftover_org_empty_guid_after_bind_post_201_is_fail(
    dump: dict[str, Any] | None,
) -> bool:
    """6d4373bc: org bind + POST 201 still PrimaryOrganizationID empty GUID.

    Linear DoD (Saw + Saw-Setup / UC) can still PASS. Org header is separate.
    Do not remint/PATCH 6d4373bc. Cad 3ac04f8a is a separate PASS.
    """
    if not isinstance(dump, dict):
        return False
    live = dump.get("live_6d4373bc") if isinstance(dump.get("live_6d4373bc"), dict) else {}
    if not live:
        return False
    if live.get("linear_dod_pass") is not True:
        return False
    try:
        if int(live.get("post_status") or 0) != 201:
            return False
    except (TypeError, ValueError):
        return False
    if not org_empty_guid_is_fail(live.get("primary_organization_id")):
        return False
    if str(live.get("want_org_id") or "") != TIME_WACO_ORG_ID:
        return False
    return True


def org_empty_guid_after_bind_post_is_fail(
    got_id: str | None,
    *,
    post_status: int | None = None,
) -> bool:
    """True when persist returned 2xx and GET PrimaryOrganizationID is empty.

    Live 6d4373bc POST 201. Older callers without a persist status pass through
    only when got_id is already a real GUID.
    """
    if not org_empty_guid_is_fail(got_id):
        return False
    if post_status is None:
        return True
    try:
        return 200 <= int(post_status) < 300
    except (TypeError, ValueError):
        return True


def org_autocomplete_search_only_is_fail(result: dict[str, Any] | None) -> bool:
    """Time Waco autocomplete 0 hits is not a Quotes UI bind (live 34603-2)."""
    if not isinstance(result, dict):
        return False
    if result.get("search") is True:
        return True
    via = str(result.get("via") or "").lower()
    if "search" in via or "autocomplete" in via:
        return True
    return org_empty_guid_is_fail(result.get("org_id") or result.get("PrimaryOrganizationID"))


def time_waco_org_entry() -> dict[str, Any]:
    """Quotes UI Time Waco — known ID, not an org-list search."""
    return {
        "ID": TIME_WACO_ORG_ID,
        "OrganizationName": TIME_WACO_ORG_NAME,
        "DisplayName": TIME_WACO_ORG_NAME,
        "NameAndLocation": TIME_WACO_ORG_NAME,
    }


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

    want_time_waco = "time" in name.casefold() and "waco" in name.casefold()
    if want_time_waco:
        # Quotes UI binds Time Waco by known ID. Autocomplete search
        # returned 0 hits on live 34603-2 and left an empty GUID.
        org = time_waco_org_entry()
        try:
            from .chrome_cdp import bind_quote_organization, chrome_edit_signed_in

            if chrome_edit_signed_in():
                page = bind_quote_organization(
                    quote_id=quote_id,
                    org_id=TIME_WACO_ORG_ID,
                    org_name=TIME_WACO_ORG_NAME,
                )
                if org_autocomplete_search_only_is_fail(page):
                    notes.append(
                        "WARNING: org autocomplete search-only is FAIL "
                        "(live 34603-2 Time Waco 0 hits)"
                    )
                if isinstance(page, dict) and page.get("via"):
                    notes.append(f"org_picker={page.get('via')}")
        except Exception:  # noqa: BLE001 — API POST still binds the known ID
            pass
    else:
        org = find_organization_by_name(client, name)
    if not org or not org.get("ID") or org_empty_guid_is_fail(str(org.get("ID") or "")):
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
    got_id = str(check.get("PrimaryOrganizationID") or check.get("OrganizationID") or "").strip()
    if org_empty_guid_after_bind_post_is_fail(got_id, post_status=status):
        slim = {
            "ID": quote_id,
            "PrimaryOrganizationID": org_id,
            "OrganizationID": org_id,
            "OrganizationName": actual_name,
            "Organization": entry,
            "OrganizationList": [entry],
        }
        retry = client.request("POST", "v1/quote", json=slim)
        try:
            status = int(getattr(retry, "status_code", status) or status)
        except (TypeError, ValueError):
            pass
        check = client.get_json(f"v1/quote/{quote_id}")
        got = str(check.get("OrganizationName") or "").strip()
        got_id = str(
            check.get("PrimaryOrganizationID") or check.get("OrganizationID") or ""
        ).strip()
    if org_empty_guid_after_bind_post_is_fail(got_id, post_status=status):
        notes.append(
            f"WARNING: PrimaryOrganizationID empty GUID ({got_id!r}) "
            f"after org bind/POST {status} (live 6d4373bc) — Time Waco "
            f"{TIME_WACO_ORG_ID} did not stick on mint — Linear/Cad pack "
            "is separate — org header FAIL"
        )
        return notes
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
    from .item_desc import quote_description_is_blank

    desc = (description or "").strip()
    if quote_description_is_blank(desc) or not quote_id:
        if quote_description_is_blank(desc):
            notes.append(
                "Quote Description is blank after mint/header — not persisting"
            )
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
