"""Kyle-protected quotes the automation must not write.

Quote-number matching is exact after strip and casefold. These quotes are
listed both as Q10488 and as 10488 so either spelling is refused. Other
Q-numbers stay exact: 10429 is not Q10429.

Write scans also refuse a forbidden id, id-shaped prefix, or quote number
anywhere in a POST/PUT/PATCH/DELETE path, query, or nested body. A prefix
matches only a UUID or a bare 8-hex token.
"""

import socket
from unittest.mock import MagicMock

import pytest

from secturafab.auth import AccessToken
from secturafab.client import SecturaFabApiError, SecturaFabClient
from secturafab.config import SecturaFabConfig
from secturafab.forbidden_quotes import (
    FORBIDDEN_LIVE_QUOTE_ID_PREFIXES,
    FORBIDDEN_LIVE_QUOTE_IDS,
    FORBIDDEN_LIVE_QUOTE_NUMBERS,
    ForbiddenQuoteError,
    is_forbidden_quote_id,
    is_forbidden_quote_number,
    refuse_forbidden_quote_write,
    spent_quote_number_block_reason,
)

# (label, number spellings, full id or None)
PROTECTED = (
    ("Q10488", ("Q10488", "10488", "q10488"), None),
    ("Q10597", ("Q10597", "10597"), None),
    (
        "Q10603",
        ("Q10603", "10603"),
        "337c3af0-6f89-4925-b3b2-1abe482f41d7",
    ),
    (
        "Q10634",
        ("Q10634", "10634"),
        "9d8c8bc9-ec70-4cc4-a2c7-abbaae59a7ef",
    ),
    (
        "Lvtong D203",
        ("2.03.115.100001",),
        "3fa14f86-f4ef-49d6-bb43-1896a0eed92e",
    ),
)

# Q10488 fixture rows are line items, not the quote.
Q10488_ITEM_IDS = (
    "bbe9b8f5-273a-4abe-8f48-845f8f938869",
    "9bfb2898-3db9-4996-8a30-8ed4112da6d7",
)

WRITE_METHODS = ("POST", "PATCH", "DELETE", "PUT")


@pytest.mark.parametrize(
    "label,numbers,quote_id",
    PROTECTED,
    ids=[row[0] for row in PROTECTED],
)
def test_protected_quote_refused_by_number(label, numbers, quote_id):
    del label, quote_id
    for number in numbers:
        assert number in FORBIDDEN_LIVE_QUOTE_NUMBERS or number.casefold() in {
            item.casefold() for item in FORBIDDEN_LIVE_QUOTE_NUMBERS
        }
        assert is_forbidden_quote_number(number)
        assert is_forbidden_quote_number(f"  {number}  ")
        assert spent_quote_number_block_reason(number)
        for method in WRITE_METHODS:
            with pytest.raises(ForbiddenQuoteError, match="forbidden"):
                refuse_forbidden_quote_write(
                    method=method,
                    path="v1/quote",
                    payload={"QuoteNumber": number},
                )
        refuse_forbidden_quote_write(
            method="GET",
            path="v1/quote",
            payload={"QuoteNumber": number},
        )


@pytest.mark.parametrize(
    "label,numbers,quote_id",
    [row for row in PROTECTED if row[2]],
    ids=[row[0] for row in PROTECTED if row[2]],
)
def test_protected_quote_refused_by_id(label, numbers, quote_id):
    del label, numbers
    prefix = quote_id.split("-", 1)[0]
    sibling = f"{prefix}-1111-2222-3333-444444444444"
    assert quote_id in FORBIDDEN_LIVE_QUOTE_IDS
    assert prefix in FORBIDDEN_LIVE_QUOTE_ID_PREFIXES
    assert is_forbidden_quote_id(quote_id)
    assert is_forbidden_quote_id(quote_id.upper())
    assert is_forbidden_quote_id(sibling)
    for method in WRITE_METHODS:
        with pytest.raises(ForbiddenQuoteError, match=prefix):
            refuse_forbidden_quote_write(
                method=method,
                path="v1/quote",
                payload={"ID": quote_id},
            )
        with pytest.raises(ForbiddenQuoteError, match=prefix):
            refuse_forbidden_quote_write(
                method=method,
                path="v1/quote",
                payload={"QuoteID": quote_id},
            )
        with pytest.raises(ForbiddenQuoteError, match=prefix):
            refuse_forbidden_quote_write(
                method=method,
                path=f"v1/quote/{quote_id}",
                payload=None,
            )
    refuse_forbidden_quote_write(
        method="GET",
        path=f"v1/quote/{quote_id}",
        payload=None,
    )
    refuse_forbidden_quote_write(method="HEAD", path=f"v1/quote/{quote_id}")


def test_other_quotes_keep_exact_number_matching():
    """Bare digits match only the quotes listed that way."""
    assert is_forbidden_quote_number("Q10429")
    assert not is_forbidden_quote_number("10429")
    assert is_forbidden_quote_number("Q10435")
    assert not is_forbidden_quote_number("10435")
    assert not is_forbidden_quote_number("Q10487")
    assert not is_forbidden_quote_number("Q10489")
    assert not is_forbidden_quote_number("Q10596")
    assert not is_forbidden_quote_number("Q10604")
    assert spent_quote_number_block_reason("Q10487") is None
    refuse_forbidden_quote_write(
        method="POST",
        path="v1/quote",
        payload={"QuoteNumber": "Q10487"},
    )
    for item_id in Q10488_ITEM_IDS:
        assert not is_forbidden_quote_id(item_id)
        refuse_forbidden_quote_write(
            method="PATCH",
            path="v1/quote",
            payload={"ID": item_id},
        )


Q10603 = "337c3af0-6f89-4925-b3b2-1abe482f41d7"
SAFE_ID = "11111111-2222-3333-4444-555555555555"


@pytest.fixture(autouse=True)
def _block_network(monkeypatch):
    """These tests must not open a socket to SecturaFAB or Chrome."""

    def _refuse(*_args, **_kwargs):
        raise AssertionError("network connect blocked")

    monkeypatch.setattr(socket.socket, "connect", _refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", _refuse)


def _quiet_client():
    session = MagicMock()
    response = MagicMock()
    response.status_code = 200
    response.content = b""
    response.text = ""
    response.headers = {}
    response.url = "https://example.invalid/api/v1/quote"
    session.request.return_value = response
    session.post.return_value = response
    client = SecturaFabClient(
        config=SecturaFabConfig(
            base_url="https://example.invalid",
            token_url_override="https://example.invalid/token",
            client_id="test",
            client_secret="test",
        ),
        session=session,
    )
    client._token = AccessToken(access_token="test-token")
    return client, session


def test_quote_online_update_list_body_is_refused():
    """PUT quoteOnline/update sends a list; ParentID is not a top-level dict key."""
    client, session = _quiet_client()
    body = [
        {
            "ParamName": "UnitCost",
            "Value": "1",
            "ID": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "ParentID": Q10603,
        }
    ]
    with pytest.raises(SecturaFabApiError, match="337c3af0"):
        client.request("PUT", "v1/quoteOnline/update", json=body)
    session.request.assert_not_called()
    session.post.assert_not_called()


def test_update_item_part_query_quote_id_is_refused():
    client, session = _quiet_client()
    with pytest.raises(SecturaFabApiError, match="337c3af0"):
        client.request(
            "POST",
            "v1/quoteOnline/UpdateItem_Part",
            params={
                "quoteID": Q10603,
                "itemID": "00000000-0000-0000-0000-000000000000",
            },
        )
    session.request.assert_not_called()


def test_post_multipart_quick_add_cad_calls_the_guard():
    client, session = _quiet_client()
    with pytest.raises(SecturaFabApiError, match="337c3af0"):
        client.post_multipart(
            "v1/quoteOnline/quickAddCAD",
            files=[("files", ("part.pdf", b"%PDF", "application/pdf"))],
            params={"quoteID": Q10603},
        )
    session.post.assert_not_called()
    session.request.assert_not_called()


def test_quote_id_key_case_variants_are_refused():
    for key in ("QuoteId", "quoteId", "QUOTEID", "quoteid"):
        with pytest.raises(ForbiddenQuoteError, match="337c3af0"):
            refuse_forbidden_quote_write(
                method="POST",
                path="v1/quote",
                payload={key: Q10603},
            )


def test_nested_dict_and_list_ids_are_refused():
    nested = {
        "rows": [
            {"meta": {"quoteId": Q10603}},
            {"note": "untouched"},
        ]
    }
    with pytest.raises(ForbiddenQuoteError, match="337c3af0"):
        refuse_forbidden_quote_write(method="PATCH", path="v1/quote", payload=nested)
    with pytest.raises(ForbiddenQuoteError, match="Q10488"):
        refuse_forbidden_quote_write(
            method="PUT",
            path="v1/quote",
            payload=[{"child": {"QuoteNumber": "see Q10488 today"}}],
        )


def test_quote_id_in_url_path_or_query_is_refused():
    with pytest.raises(ForbiddenQuoteError, match="337c3af0"):
        refuse_forbidden_quote_write(
            method="DELETE",
            path=f"v1/quoteOnline/UpdateItem_Part?quoteId={Q10603}",
        )
    client, session = _quiet_client()
    with pytest.raises(SecturaFabApiError, match="337c3af0"):
        client.website_request(
            "POST",
            "/Quote/AddFeature",
            params={"quoteId": Q10603},
        )
    session.request.assert_not_called()


def test_quotes_tab_fetch_calls_the_guard_before_chrome(monkeypatch):
    import secturafab.chrome_cdp as cdp

    def _boom(*_args, **_kwargs):
        raise AssertionError("chrome tab lookup")

    monkeypatch.setattr(cdp, "quotes_tab", _boom)
    monkeypatch.setattr(cdp, "_quotes_or_edit_tab", _boom)
    with pytest.raises(ForbiddenQuoteError, match="337c3af0"):
        cdp.quotes_tab_fetch(
            path="/Quote/EDIT",
            json_body={"quoteId": Q10603},
        )
    with pytest.raises(ForbiddenQuoteError, match="Q10634"):
        cdp.quotes_tab_fetch(
            path="/part/create",
            query={"quoteId": "Q10634"},
            form_pairs=[("ID", "not-a-quote")],
        )


def test_prefix_matches_only_id_shaped_values():
    prose = {
        "note": "a24c6896 leftover note is not an id",
        "code": "a24c6896extra",
        "almost": "a24c6896-not-a-uuid",
    }
    refuse_forbidden_quote_write(method="POST", path="v1/quote", payload=prose)
    assert not is_forbidden_quote_id("a24c6896 leftover note is not an id")
    assert not is_forbidden_quote_id("a24c6896extra")
    with pytest.raises(ForbiddenQuoteError, match="a24c6896"):
        refuse_forbidden_quote_write(
            method="POST",
            path="v1/quote",
            payload={"ID": "a24c6896"},
        )
    with pytest.raises(ForbiddenQuoteError, match="a24c6896"):
        refuse_forbidden_quote_write(
            method="POST",
            path="v1/quote",
            payload={"ID": "a24c6896-1111-2222-3333-444444444444"},
        )
    refuse_forbidden_quote_write(
        method="POST",
        path="v1/quote",
        payload={"QuoteNumber": "Q104880"},
    )
    refuse_forbidden_quote_write(
        method="POST",
        path="v1/quote",
        payload={"QuoteNumber": "104880"},
    )


def test_normal_write_to_other_quote_is_allowed():
    client, session = _quiet_client()
    response = client.request(
        "POST",
        "v1/quote",
        json={"ID": SAFE_ID, "QuoteNumber": "Q99999", "note": "a24c6896 leftover"},
    )
    assert response.status_code == 200
    session.request.assert_called_once()
    refuse_forbidden_quote_write(method="GET", path=f"v1/quote/{Q10603}")
    refuse_forbidden_quote_write(method="HEAD", path=f"v1/quote?quoteId={Q10603}")
    refuse_forbidden_quote_write(
        method="OPTIONS",
        path="v1/quote",
        payload={"quoteId": Q10603},
    )


def test_page_assembly_writes_refuse_before_chrome(monkeypatch):
    import secturafab.chrome_cdp as cdp
    import secturafab.page_weld as weld

    def _boom(*_args, **_kwargs):
        raise AssertionError("chrome tab lookup")

    monkeypatch.setattr(cdp, "minted_edit_tab_ready", _boom)
    with pytest.raises(ForbiddenQuoteError, match="337c3af0"):
        weld.add_page_assembly(quote_id=Q10603, name="BRACKET", description="Side plate")
    with pytest.raises(ForbiddenQuoteError, match="337c3af0"):
        weld.update_existing_assembly_name(
            quote_id=Q10603,
            description="Side plate assembly",
        )
