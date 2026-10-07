from __future__ import annotations

from typing import Any

from .client import SecturaFabApiError, SecturaFabClient


class QuoteService:
    """
    Quote helpers with adaptive path probing.

    Exact SecturaFAB controller routes vary by version. Once `discover` confirms
    the live paths, prefer calling those explicitly.
    """

    LIST_CANDIDATES = ("Quotes", "Quote", "quotes")

    def __init__(self, client: SecturaFabClient) -> None:
        self.client = client

    def list_quotes(self, *, top: int | None = 25) -> Any:
        params = {"$top": top} if top is not None else None
        errors: list[str] = []
        for path in self.LIST_CANDIDATES:
            response = self.client.request("GET", path, params=params)
            if response.status_code < 400:
                return self.client._parse_or_raise(response)
            errors.append(f"{path}->{response.status_code}")
        raise SecturaFabApiError(
            "Unable to list quotes via known paths: " + ", ".join(errors)
        )

    def get_quote(self, quote_id: str | int) -> Any:
        errors: list[str] = []
        for root in self.LIST_CANDIDATES:
            path = f"{root}/{quote_id}"
            response = self.client.request("GET", path)
            if response.status_code < 400:
                return self.client._parse_or_raise(response)
            errors.append(f"{path}->{response.status_code}")
        raise SecturaFabApiError(
            f"Unable to fetch quote {quote_id}: " + ", ".join(errors)
        )

    def create_quote(self, payload: dict[str, Any]) -> Any:
        """
        Create a quote on ``POST /api/v2/quote``.

        A customer name is resolved to ``OrganizationId`` through
        ``GET /api/v2/organization/lookup`` first. The body does not send
        ``OrganizationName`` or ``LocationName``.
        """
        from .api_v2 import create_quote_from_payload

        return create_quote_from_payload(self.client, payload)
