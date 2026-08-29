"""Live Sectura quotes this automation must never PATCH or reuse."""

from __future__ import annotations

from typing import Any

# Kyle-confirmed + leftover + human Time quotes. Create NEW quotes only.
FORBIDDEN_LIVE_QUOTE_IDS = frozenset(
    {
        "a7dc46bf-836a-4250-b038-9331cc0595a7",  # Kyle-confirmed 1001898-1
        "ee8a3b59-616f-44e1-94c7-175892b15256",  # leftover incomplete
        "8bcc226b-6bd9-4149-a7bb-aa830ce63a5d",
        "a7d6ca50-efec-409d-bd32-e68012e710c3",  # Q10056 / 21678-1
        "5e111cd2-73d1-44e1-9602-f2a4a3de2fb4",  # empty 1004747-1 draft
        "936b5c6c-2fc5-4b28-a8f6-015db289cb4f",  # empty 1004747-1 draft (2nd drop)
        "9354f680-ef91-47d9-af42-8dd65b75473f",  # empty 1004747-1 draft (3rd drop)
        "f61c033a-48f2-4b11-9a10-96bc5c70716c",  # 1004747-1 OPEN-DRAFT (6fa74ba)
        "a522d863-1805-4206-85d1-36841dd107d2",  # 1004747-1 OPEN-DRAFT (51e017e)
        "7a555ac2-2a77-4bd9-a936-bf8a64eb60e7",  # 1004747-1 OPEN-DRAFT (1de052c)
        "8f87fbae-d2ef-40ee-abd4-47a8755ce19f",  # 1001775-1 empty shell (3325361)
        "804172ea-f507-42fe-87ae-1b91d2cc0d29",  # 1007049-1 live drop (a44790a) — leave it
    }
)

# Partial ids from live notes when the full GUID was not restated.
FORBIDDEN_LIVE_QUOTE_ID_PREFIXES = frozenset(
    {
        "280f4dcb",
    }
)

FORBIDDEN_LIVE_QUOTE_NUMBERS = frozenset(
    {
        "Q10056",
        "21678-1",
        "28106-1",
        "28106-2",
        "1007922-1",
        "21727-1",
    }
)


def is_forbidden_quote_id(quote_id: str | None) -> bool:
    raw = str(quote_id or "").strip().casefold()
    if not raw:
        return False
    if raw in {x.casefold() for x in FORBIDDEN_LIVE_QUOTE_IDS}:
        return True
    return any(raw.startswith(p.casefold()) for p in FORBIDDEN_LIVE_QUOTE_ID_PREFIXES)


def is_forbidden_quote_number(quote_number: str | None) -> bool:
    raw = str(quote_number or "").strip().casefold()
    return raw in {x.casefold() for x in FORBIDDEN_LIVE_QUOTE_NUMBERS}


class ForbiddenQuoteError(RuntimeError):
    """Write targeted a Kyle-confirmed or human Time quote."""


def refuse_forbidden_quote_write(
    *,
    method: str,
    path: str,
    payload: Any = None,
) -> None:
    """Raise if a write would PATCH/reuse a forbidden live quote.

    GET is allowed. New quotes (empty / new UUID + a job PN) are allowed.
    """
    if str(method or "GET").upper() in {"GET", "HEAD", "OPTIONS"}:
        return
    blob = payload if isinstance(payload, dict) else {}
    qid = str(blob.get("ID") or blob.get("QuoteID") or "").strip()
    path_l = str(path or "").casefold()
    if not qid:
        for part in path_l.replace("\\", "/").split("/"):
            if is_forbidden_quote_id(part):
                qid = part
                break
    if is_forbidden_quote_id(qid):
        raise ForbiddenQuoteError(
            f"Refusing to PATCH/reuse forbidden live quote {qid}"
        )
    # Updating an existing Q10056 / 21678-1 / human Time quote by number + ID.
    qn = str(blob.get("QuoteNumber") or "").strip()
    if qid and is_forbidden_quote_number(qn):
        raise ForbiddenQuoteError(
            f"Refusing to PATCH/reuse forbidden live quote {qn} ({qid})"
        )
