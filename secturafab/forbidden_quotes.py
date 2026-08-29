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
        "f703b928-3475-45c2-ade5-fcce97e1709e",  # 1010103-1 STEP drop (f1a7cc9) — leave it
        "12239b72-c82c-4493-b226-c51a98eb4fb5",  # 1007756-3 empty shell (adf610a) — leave it
        "593d9450-530f-4ade-a137-9d195714ac73",  # 1002381-1 empty shell (e7dd028) — leave it
        "b8be3545-1628-4176-b93a-804ad5575bc3",  # 34574-1 empty shell (40507e7) — leave it
        "0e892c8f-93ee-49fa-90c9-3bb4bbf91c22",  # 34887-1 empty shell (227dff0) — leave it
        "ed8cfcda-68e4-4655-a240-79cce4280d7e",  # 34639-1 empty shell (743c5ee) — leave it
        "ba7730a0-0848-42d2-8579-dc18f86ec27f",  # 11791-2 empty shell (3bf75f8) — leave it
        "30940f1d-d262-4562-bfd3-1b17575dc83c",  # 10072-1 empty shell (7b723b9) — leave it
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
        "1007756-3",  # spent empty shell — next unused is 1007756-1
        "1002381-1",  # spent empty shell (e7dd028)
        "34574-1",  # spent empty shell (40507e7)
        "34887-1",  # spent empty shell (227dff0)
        "34639-1",  # spent empty shell (743c5ee)
        "11791-2",  # spent empty shell (3bf75f8)
        "10072-1",  # spent empty shell (7b723b9)
        "10107-1",  # occupied — do not remint
        "14284-2",  # occupied — do not remint
        "21807-1",  # occupied — do not remint
        "1007830-1",  # occupied — do not remint
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
