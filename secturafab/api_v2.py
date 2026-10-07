"""SecturaFAB REST API 2.0 client (spec dated 2026-10-07).

Quote create is ``POST /api/v2/quote`` with ``OrganizationId``. The customer
name is resolved first with ``GET /api/v2/organization/lookup``. Zero matches
and more than one match fail closed. ``POST /api/v2/organization`` is not
called from here — creating an organization is a human decision.

``QuoteResponse`` no longer has ``LocationName``. Add-linear and add-plate
bodies no longer take ``QuoteItemId``.
"""

from __future__ import annotations

from typing import Any

from .client import SecturaFabApiError, SecturaFabClient
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
    """``POST /api/v2/organization`` stays a human decision."""
    raise OrganizationLookupError(
        "FLAG: refusing to create an organization — "
        "POST /api/v2/organization needs a human decision"
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


def resolve_organization_id(
    client: SecturaFabClient,
    *,
    name: str | None = None,
    external_reference: str | None = None,
    known_id: str | None = None,
) -> str:
    """One ``OrganizationId`` from lookup. Zero or many matches raise.

    ``known_id`` is a cross-check (the Time Waco id the shop already uses).
    A different lookup id fails closed. Lookup is not skipped in favor of
    the known id, and a miss does not create an organization.
    """
    label = _flag_name(name, external_reference)
    org_name = _clean(name)
    external = _clean(external_reference)
    if not org_name and not external:
        raise OrganizationLookupError(
            "FLAG: organization lookup needs a customer name — "
            "not creating the quote and not creating an organization"
        )
    params: dict[str, str] = {}
    if org_name:
        params["name"] = org_name
    if external:
        params["externalReference"] = external
    try:
        payload = client.get_json(LOOKUP_PATH, params=params)
    except SecturaFabApiError as exc:
        if exc.status_code == 404:
            raise OrganizationLookupError(
                f"FLAG: organization lookup for {label} matched no organization — "
                "not creating the quote and not creating an organization"
            ) from exc
        raise OrganizationLookupError(
            f"FLAG: organization lookup for {label} failed "
            f"({exc.status_code}) — not creating the quote and not creating "
            "an organization"
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
            f"FLAG: organization lookup for {label} matched {declared}{extra} — "
            "not creating the quote and not creating an organization",
            matches=rows,
        )
    if not rows:
        raise OrganizationLookupError(
            f"FLAG: organization lookup for {label} matched no organization — "
            "not creating the quote and not creating an organization"
        )
    found = _valid_org_id(rows[0].get("OrganizationId"))
    if not found:
        raise OrganizationLookupError(
            f"FLAG: organization lookup for {label} matched no organization — "
            "not creating the quote and not creating an organization"
        )
    want = _valid_org_id(known_id)
    if want and found.casefold() != want.casefold():
        raise OrganizationLookupError(
            f"FLAG: organization lookup for {label} returned {found} which does "
            f"not match known organization id {want} — not creating the quote "
            "and not creating an organization",
            matches=rows,
        )
    return found


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
    if name:
        org_id = resolve_organization_id(
            client,
            name=name,
            known_id=org_id or None,
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
