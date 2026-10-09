"""Kyle-protected quotes the automation must not write.

Quote-number matching is exact after strip and casefold. These quotes are
listed both as Q10488 and as 10488 so either spelling is refused. Other
Q-numbers stay exact: 10429 is not Q10429.
"""

import pytest

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
