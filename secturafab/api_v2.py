"""SecturaFAB REST API 2.0 client (spec dated 2026-10-07).

Quote create is ``POST /api/v2/quote`` with ``OrganizationId``. A customer
name is an exact Sectura organization name. Lookup is
``GET /api/v2/organization/lookup`` with exactly one of ``name`` or
``externalReference``. Zero matches and more than one match fail closed.
Time Waco is not looked up by name: it is
``GET /api/v2/organization/{id}`` for the known id. This module never
creates an organization or customer. v2 has no customer endpoint.

``QuoteResponse.QuoteStatus`` is text and carries values such as
``OPEN-NEW``. ``Status`` is a separate field. ``LocationName`` is gone.
Add-linear and add-plate bodies no longer take ``QuoteItemId``.
"""

from __future__ import annotations

from typing import Any

from .client import SecturaFabApiError, SecturaFabClient, sectura_error_detail
from .website import EMPTY_GUID

LOOKUP_PATH = "v2/organization/lookup"
QUOTE_PATH = "v2/quote"

# CreateQuoteRequestBody after 2026-10-07. OrganizationName and LocationName
# are gone. None of these keys are required by the spec.
_CREATE_QUOTE_KEYS = ("OrganizationId", "Description", "ExternalReference")


class OrganizationLookupError(SecturaFabApiError):
    """Lookup found no organization, or more than one. Do not create one."""

    def __init__(self, message: str, *, matches: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.matches = list(matches or [])


def refuse_create_organization(*_args: Any, **_kwargs: Any) -> None:
    """No API version and no website path may create an organization."""
    raise OrganizationLookupError(
        "FLAG: refusing to create an organization or customer. "
        "A lookup miss stops the push. Not creating an organization."
    )


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _valid_org_id(value: Any) -> str:
    raw = _clean(value)
    if not raw or raw.casefold() == EMPTY_GUID.casefold():
        return ""
    return raw


def _paging_total(payload: dict[str, Any]) -> int | None:
    paging = payload.get("Paging")
    if not isinstance(paging, dict) or paging.get("Total") in (None, ""):
        return None
    try:
        return int(paging["Total"])
    except (TypeError, ValueError):
        return None


def organization_matches(payload: Any) -> tuple[list[dict[str, Any]], int]:
    """Rows that carry ``OrganizationId``, and how many matches the lookup declared.

    The spec types ``Data`` as one ``OrganizationResponse``. A list, or
    ``Paging.Total`` greater than the rows returned, is more than one match.
    """
    if not isinstance(payload, dict):
        return [], 0
    envelope = any(key in payload for key in ("Data", "Error", "Paging"))
    data = payload.get("Data") if envelope else payload
    rows: list[dict[str, Any]] = []
    if isinstance(data, list):
        candidates = [row for row in data if isinstance(row, dict)]
    elif isinstance(data, dict):
        candidates = [data]
        for key in ("Results", "Organizations", "Items"):
            nested = data.get(key)
            if isinstance(nested, list):
                candidates = [row for row in nested if isinstance(row, dict)]
                break
    else:
        candidates = []
    for row in candidates:
        if _valid_org_id(row.get("OrganizationId")):
            rows.append(row)
    total = _paging_total(payload) if envelope else None
    if total == 0:
        return [], 0
    count = len(rows)
    if total is not None:
        count = max(count, total)
    return rows, count


def _flag_name(name: str | None, external_reference: str | None) -> str:
    if _clean(name):
        return repr(_clean(name))
    if _clean(external_reference):
        return f"externalReference { _clean(external_reference)!r}"
    return "(no name)"


_EXACT_NAME = (
    "Use the exact Sectura organization name. "
    "Partial names and 'Name - Location' forms do not match."
)
_NO_CREATE = "Not creating the quote and not creating an organization."


def _error_suffix(exc: SecturaFabApiError) -> str:
    detail = sectura_error_detail(getattr(exc, "body", None))
    if detail:
        return f" — {detail}"
    return ""


def resolve_organization_id(
    client: SecturaFabClient,
    *,
    name: str | None = None,
    external_reference: str | None = None,
    known_id: str | None = None,
) -> str:
    """One ``OrganizationId`` from lookup. Zero or many matches raise.

    The live lookup accepts exactly one of ``name`` or ``externalReference``.
    ``known_id`` is a cross-check. A different id fails closed. A miss does
    not create an organization. Time Waco does not use this function.
    """
    label = _flag_name(name, external_reference)
    org_name = _clean(name)
    external = _clean(external_reference)
    if bool(org_name) == bool(external):
        raise OrganizationLookupError(
            "FLAG: organization lookup must send exactly one of name or "
            "externalReference. Provide exactly one of name or externalReference. "
            f"{_NO_CREATE}"
        )
    params = {"name": org_name} if org_name else {"externalReference": external}
    try:
        payload = client.get_json(LOOKUP_PATH, params=params)
    except SecturaFabApiError as exc:
        if exc.status_code == 404:
            detail = sectura_error_detail(getattr(exc, "body", None))
            extra = f"{detail}. " if detail else ""
            raise OrganizationLookupError(
                f"FLAG: organization lookup for {label} matched no organization. "
                f"{extra}{_EXACT_NAME} {_NO_CREATE}"
            ) from exc
        raise OrganizationLookupError(
            f"FLAG: organization lookup for {label} failed "
            f"({exc.status_code}){_error_suffix(exc)}. {_NO_CREATE}"
        ) from exc
    rows, count = organization_matches(payload)
    if count > 1 or len(rows) > 1:
        shown = ", ".join(
            _clean(row.get("Name")) or _valid_org_id(row.get("OrganizationId"))
            for row in rows
        )
        extra = f" ({shown})" if shown else ""
        declared = f"{count} organizations" if count != len(rows) else f"{len(rows)} organizations"
        raise OrganizationLookupError(
            f"FLAG: organization lookup for {label} matched {declared}{extra}. "
            f"{_EXACT_NAME} {_NO_CREATE}",
            matches=rows,
        )
    if not rows:
        raise OrganizationLookupError(
            f"FLAG: organization lookup for {label} matched no organization. "
            f"{_EXACT_NAME} {_NO_CREATE}"
        )
    found = _valid_org_id(rows[0].get("OrganizationId"))
    if not found:
        raise OrganizationLookupError(
            f"FLAG: organization lookup for {label} matched no organization. "
            f"{_EXACT_NAME} {_NO_CREATE}"
        )
    got_name = _clean(rows[0].get("Name"))
    if org_name and got_name and got_name.casefold() != org_name.casefold():
        raise OrganizationLookupError(
            f"FLAG: organization lookup for {label} returned {got_name!r}, "
            f"which is not an exact name match. {_EXACT_NAME} {_NO_CREATE}",
            matches=rows,
        )
    want = _valid_org_id(known_id)
    if want and found.casefold() != want.casefold():
        raise OrganizationLookupError(
            f"FLAG: organization lookup for {label} returned {found} which does "
            f"not match known organization id {want}. {_NO_CREATE}",
            matches=rows,
        )
    return found


def fetch_organization_by_id(
    client: SecturaFabClient, organization_id: str
) -> dict[str, Any]:
    """``GET /api/v2/organization/{id}``. Does not create an organization."""
    oid = _valid_org_id(organization_id)
    if not oid:
        raise OrganizationLookupError(
            f"FLAG: organization id is missing. {_NO_CREATE}"
        )
    path = f"v2/organization/{oid}"
    try:
        payload = client.get_json(path)
    except SecturaFabApiError as exc:
        raise OrganizationLookupError(
            f"FLAG: GET /api/v2/organization/{oid} failed "
            f"({exc.status_code}){_error_suffix(exc)}. {_NO_CREATE}"
        ) from exc
    rows, count = organization_matches(payload)
    if count != 1 or len(rows) != 1:
        raise OrganizationLookupError(
            f"FLAG: GET /api/v2/organization/{oid} matched no organization. "
            f"{_EXACT_NAME} {_NO_CREATE}"
        )
    return rows[0]


def organization_id_for_new_quote(
    client: SecturaFabClient,
    *,
    name: str | None = None,
    organization_id: str | None = None,
) -> tuple[str, str]:
    """``(organization id, exact name)`` for a new quote.

    Time Waco always uses ``GET /api/v2/organization/{known id}``. The name
    ``Time Manufacturing Waco`` is refused before any HTTP. Other customers
    are an exact-name lookup with one parameter. An empty name and empty id
    returns ``("", "")``.
    """
    from .org_ops import (
        TIME_WACO_ORG_ID,
        TIME_WACO_ORG_NAME,
        rejected_time_org_name,
        time_waco_org_id_for_name,
    )

    org_name = _clean(name)
    org_id = _valid_org_id(organization_id)
    if rejected_time_org_name(org_name):
        raise OrganizationLookupError(
            f"FLAG: {org_name!r} is not an exact Sectura organization name. "
            f"Time Waco is {TIME_WACO_ORG_NAME!r} ({TIME_WACO_ORG_ID}), "
            "resolved by GET /api/v2/organization/{id}, never by name lookup. "
            f"{_EXACT_NAME} {_NO_CREATE}"
        )
    time_name = bool(time_waco_org_id_for_name(org_name))
    time_id = bool(org_id) and org_id.casefold() == TIME_WACO_ORG_ID.casefold()
    if time_name or time_id:
        if org_name and not time_name:
            raise OrganizationLookupError(
                f"FLAG: organization id {TIME_WACO_ORG_ID} is "
                f"{TIME_WACO_ORG_NAME!r}, not {org_name!r}. {_EXACT_NAME} {_NO_CREATE}"
            )
        if org_id and not time_id:
            raise OrganizationLookupError(
                f"FLAG: {TIME_WACO_ORG_NAME!r} is organization {TIME_WACO_ORG_ID}, "
                f"not {org_id}. {_NO_CREATE}"
            )
        row = fetch_organization_by_id(client, TIME_WACO_ORG_ID)
        found = _valid_org_id(row.get("OrganizationId"))
        got_name = _clean(row.get("Name"))
        if found.casefold() != TIME_WACO_ORG_ID.casefold():
            raise OrganizationLookupError(
                f"FLAG: GET /api/v2/organization/{TIME_WACO_ORG_ID} returned "
                f"{found or '(blank)'}. {_NO_CREATE}"
            )
        if got_name.casefold() != TIME_WACO_ORG_NAME.casefold():
            raise OrganizationLookupError(
                f"FLAG: GET /api/v2/organization/{TIME_WACO_ORG_ID} returned "
                f"name {got_name!r}. Time Waco is the exact Sectura organization "
                f"name {TIME_WACO_ORG_NAME!r}. {_NO_CREATE}"
            )
        return found, TIME_WACO_ORG_NAME
    if not org_name:
        return org_id, ""
    resolved = resolve_organization_id(
        client,
        name=org_name,
        known_id=org_id or None,
    )
    return resolved, org_name


def build_create_quote_body(
    *,
    organization_id: str | None = None,
    description: str | None = None,
    external_reference: str | None = None,
) -> dict[str, str]:
    """``CreateQuoteRequestBody``. Never sends ``OrganizationName`` or ``LocationName``."""
    body: dict[str, str] = {}
    org_id = _valid_org_id(organization_id)
    if org_id:
        body["OrganizationId"] = org_id
    text = _clean(description)
    if text:
        body["Description"] = text[:500]
    ref = _clean(external_reference)
    if ref:
        body["ExternalReference"] = ref
    unexpected = set(body) - set(_CREATE_QUOTE_KEYS)
    if unexpected:
        raise OrganizationLookupError(
            "FLAG: create-quote body has fields the v2 spec dropped: "
            + ", ".join(sorted(unexpected))
        )
    return body


def quote_id_from_create_response(payload: Any) -> str:
    """``EnvelopeOfQuoteIdResponse`` → ``Data.QuoteId``."""
    if not isinstance(payload, dict):
        return ""
    data = payload.get("Data") if isinstance(payload.get("Data"), dict) else payload
    if not isinstance(data, dict):
        return ""
    return _clean(data.get("QuoteId") or data.get("quote_id"))


def discard_quote_created_this_run(client: SecturaFabClient, quote_id: str) -> str:
    """Delete the quote id this run's ``POST /api/v2/quote`` just returned.

    v2 has ``DELETE /api/v2/quote/{quoteId}`` and no operation that sets
    Status to Archived. When the editor for this id is already open, the
    shop archive prefix is applied first (``ZZ-DEL-`` plus the id). A
    forbidden id is left alone. An empty id means this run did not create
    a quote.
    """
    from .forbidden_quotes import is_forbidden_quote_id

    qid = _clean(quote_id)
    if not qid:
        return "no quote id from this POST — nothing discarded"
    if is_forbidden_quote_id(qid):
        return f"refusing to discard forbidden quote {qid}"
    archive_note = ""
    try:
        from .chrome_cdp import minted_edit_tab_ready
        from .page_weld import set_page_quote_number

        gate = minted_edit_tab_ready(qid, navigate=False)
        if isinstance(gate, dict) and gate.get("ok"):
            notes = set_page_quote_number(qid, f"ZZ-DEL-{qid[:8]}")
            if notes and not any("WARNING" in note for note in notes):
                archive_note = "archived as ZZ-DEL; "
            else:
                archive_note = "ZZ-DEL rename did not stick; "
    except Exception as exc:
        archive_note = f"ZZ-DEL rename skipped ({exc}); "
    try:
        client.delete_json(f"v2/quote/{qid}")
    except Exception as exc:
        return (
            f"ORPHAN quote {qid} — {archive_note}"
            f"DELETE /api/v2/quote/{qid} failed ({exc}). "
            "Clean this id up by hand."
        )
    return f"{archive_note}deleted {qid} via DELETE /api/v2/quote/{qid}"


def post_create_quote(
    client: SecturaFabClient,
    *,
    organization_id: str | None = None,
    description: str | None = None,
    external_reference: str | None = None,
) -> Any:
    """``POST /api/v2/quote``. Does not create an organization."""
    body = build_create_quote_body(
        organization_id=organization_id,
        description=description,
        external_reference=external_reference,
    )
    return client.post_json(QUOTE_PATH, body)


def create_quote_from_payload(client: SecturaFabClient, payload: dict[str, Any] | None) -> Any:
    """Legacy create payload → lookup, then the v2 body.

    ``OrganizationName`` is the lookup key. ``LocationName`` is ignored.
    An ``OrganizationId`` already on the payload is a cross-check, not a
    reason to skip lookup when a name is present.
    """
    raw = payload if isinstance(payload, dict) else {}
    name = _clean(raw.get("OrganizationName") or raw.get("Name"))
    org_id = _valid_org_id(raw.get("OrganizationId"))
    # Quote ExternalReference is the shop number, not an organization key.
    if name or org_id:
        org_id, _resolved_name = organization_id_for_new_quote(
            client,
            name=name,
            organization_id=org_id,
        )
    return post_create_quote(
        client,
        organization_id=org_id,
        description=_clean(raw.get("Description")),
        external_reference=_clean(raw.get("ExternalReference")),
    )


def without_quote_item_id(body: dict[str, Any] | None) -> dict[str, Any]:
    """Add-linear, add-plate, and add-cad no longer accept ``QuoteItemId``."""
    if not isinstance(body, dict):
        return {}
    return {key: value for key, value in body.items() if key != "QuoteItemId"}


def build_add_linear_item_body(fields: dict[str, Any] | None) -> dict[str, Any]:
    return without_quote_item_id(fields)


def build_add_plate_item_body(fields: dict[str, Any] | None) -> dict[str, Any]:
    return without_quote_item_id(fields)


def build_add_cad_form(fields: dict[str, Any] | None) -> dict[str, Any]:
    """Multipart add-cad fields. ``QuoteItemId`` is gone. ``FixedPrice`` is optional.

    A missing price is omitted. This does not invent one.
    """
    body = without_quote_item_id(fields)
    if body.get("FixedPrice") in (None, ""):
        body.pop("FixedPrice", None)
    return body


def add_linear_item(
    client: SecturaFabClient, quote_id: str, body: dict[str, Any]
) -> Any:
    cleaned = build_add_linear_item_body(body)
    return client.post_json(f"v2/quote/{quote_id}/add-linear-item", cleaned)


def add_plate_item(
    client: SecturaFabClient, quote_id: str, body: dict[str, Any]
) -> Any:
    cleaned = build_add_plate_item_body(body)
    return client.post_json(f"v2/quote/{quote_id}/add-plate-item", cleaned)


_MANUAL_FIELDS = (
    "Description",
    "Quantity",
    "PartName",
    "Memo",
    "UnitCost",
    "MarginMarkup",
    "UnitPrice",
    "HasFixedPrice",
    "UnitWeight",
    "WeightUnits",
    "MinValue",
)


def build_manual_component_body(
    *,
    quantity: int,
    description: str | None = None,
    part_name: str | None = None,
    memo: str | None = None,
    unit_cost: float | None = None,
    margin_markup: float | None = None,
    unit_price: float | None = None,
    has_fixed_price: bool | None = None,
    unit_weight: float | None = None,
    weight_units: str | None = None,
    min_value: float | None = None,
) -> dict[str, Any]:
    """``AddManualItemRequestBody``. Quantity is the only required field.

    Cost, price, and weight are included only when the caller already has
    them. They are not defaulted to zero.
    """
    body: dict[str, Any] = {"Quantity": int(quantity)}
    text = _clean(description)
    if text:
        body["Description"] = text[:500]
    part = _clean(part_name)
    if part:
        body["PartName"] = part
    note = _clean(memo)
    if note:
        body["Memo"] = note
    optional = {
        "UnitCost": unit_cost,
        "MarginMarkup": margin_markup,
        "UnitPrice": unit_price,
        "HasFixedPrice": has_fixed_price,
        "UnitWeight": unit_weight,
        "WeightUnits": _clean(weight_units) or None,
        "MinValue": min_value,
    }
    for key, value in optional.items():
        if value is not None and value != "":
            body[key] = value
    return body


def add_manual_component_item(
    client: SecturaFabClient,
    quote_id: str,
    body: dict[str, Any],
) -> Any:
    """``POST /api/v2/quote/{quoteId}/add-manual-component-item``."""
    allowed = {key: body[key] for key in _MANUAL_FIELDS if key in body}
    if "Quantity" not in allowed:
        raise SecturaFabApiError(
            "FLAG: add-manual-component-item requires Quantity — not inventing one"
        )
    return client.post_json(
        f"v2/quote/{quote_id}/add-manual-component-item",
        allowed,
    )


def customer_name_from_quote_response(payload: dict[str, Any] | None) -> str:
    """``OrganizationName`` on ``QuoteResponse``. ``LocationName`` was removed."""
    if not isinstance(payload, dict):
        return ""
    return _clean(payload.get("OrganizationName"))


def primary_organization_id_from_quote_response(payload: dict[str, Any] | None) -> str:
    """v2 ``PrimaryOrganizationId``, with the v1 spelling as a fallback."""
    if not isinstance(payload, dict):
        return ""
    return _clean(
        payload.get("PrimaryOrganizationId")
        or payload.get("PrimaryOrganizationID")
        or payload.get("OrganizationID")
    )
