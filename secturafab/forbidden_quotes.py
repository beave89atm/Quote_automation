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
        "9a2bc798-f192-4e4c-9b12-78098305f7cc",  # 34137-1 empty shell (08d7855) — leave it
        "aab44741-1213-470c-b941-d44ccf1068ea",  # 34137-2 empty shell (9a0d895) — leave it
        "069da4fe-5818-4125-983a-197bd4188ed1",  # 34632-2 empty shell (f6ac309) — leave it
        "a6ef6891-e080-45de-b57c-1a55fee00c19",  # 106386-1 empty shell (1fd9b53) — leave it
        "997f1eb7-3eb0-4a76-83f9-4c3439e929b7",  # 105918-1 Finish 66 / 0 Cad (23b96a9) — leave it
        "66a0271f-f2f7-42c1-ac01-cd879f1bfa22",  # 106687-1 Upload 502 43MB (bd4d75e) — leave it
        "75b3a938-ff89-4525-80d9-c6000d055a48",  # 28110-2 Finish 200 / GET 0 (6c02c08) — leave it
        "e2cc0a7d-90fa-4629-b48f-db1e8163557b",  # 107877-1 explode_passes=1 / GET 0 (1e76c96) — leave it
        "e2305b3c-7316-4a96-8c94-7685fca2be54",  # 1020249-1 pass-2 wiped grid (e21bc43) — leave it
        "80eb38af-3721-4049-a0d5-e4026d293a0c",  # 5003313-001 Finish on leftover 105918-1 (526d139) — leave it
        "31204345-6c91-4122-a859-09f7d7a3ea9f",  # P001545 page Finish empty body (9735155) — leave it
        "a9497a26-cba8-4ec9-a849-cb8bef81cbcc",  # BB2000-ASM skip-Finish (ad38881) — leave it
        "a8e1b40e-54c2-4515-9f36-67843a1e5286",  # 11796-1 kendo FileList miss (4c79659) — leave it
        "8de920f0-ea17-442d-898e-9a04367d91de",  # 11796-2 SourceDataID=0 (619ebf2) — leave it
        "d59318c8-9c39-43a2-aef6-cbd28203ee82",  # 107292-1 empty vs List,Result (ce5d2c1) — leave it
        "aab5b3e2-8771-47a2-b625-a3f379c5b0c2",  # 16629-1 leftover EAR empty FileType (76dd572) — leave it
        "6a568912-5b19-4bfd-9e11-d06d7c149746",  # 10098-1 leftover PIVOTING FOOT Cad payload empty (315cb19) — leave it
        "b8a62e76-6439-46d3-b32e-d48de29f389d",  # SC0600 weldment explode InternalData empty (2c29618) — leave it
        "0d4b8a46-cc66-4586-baed-4cad20a07ddb",  # FA Assembly fetch+#img InternalData empty 28/28 (cba5fa2) — leave it
        "5b622a0d-4dab-4099-97e4-d0184df4b770",  # Skin Assembly jquery_ajax+EDIT InternalData empty 8/8 (1a2274f) — leave it
        "491f6387-520f-4eee-aab3-6d20585ee740",  # 1001898-5 reconstructed PDF FileList / Cad no PR (leave it)
        "bd5c2e3e-948d-463d-8844-4366910bb5ec",  # 103535-1 cookie HTTP upload / empty #gridPDF (leave it)
    }
)
# cf8ec36e = EHB3112-1 OnAddDXFClick empty body (83c9200) — prefix only.

# Partial ids from live notes when the full GUID was not restated.
FORBIDDEN_LIVE_QUOTE_ID_PREFIXES = frozenset(
    {
        "280f4dcb",
        "a484ba3b",  # 106384-1 spent (32MB Upload 502) — do not remint
        "66a0271f",  # 106687-1 spent (43MB Upload 502) — do not remint
        "75b3a938",  # 28110-2 spent (Finish 200 / GET 0) — do not remint
        "e2cc0a7d",  # 107877-1 spent (explode_passes=1 / GET 0) — do not remint
        "e2305b3c",  # 1020249-1 spent (pass-2 List=0 wiped grid) — do not remint
        "80eb38af",  # 5003313-001 spent (Finish on leftover 105918-1) — do not remint
        "31204345",  # P001545 spent (page Finish empty body / GET 0) — do not remint
        "a9497a26",  # BB2000-ASM spent (skip-Finish / GET 0) — do not remint
        "cf8ec36e",  # EHB3112-1 spent (OnAddDXFClick empty body) — do not remint
        "a8e1b40e",  # 11796-1 spent (kendo FileList / AF miss) — do not remint
        "8de920f0",  # 11796-2 spent (SourceDataID=0) — do not remint
        "d59318c8",  # 107292-1 spent (empty body vs List,Result) — do not remint
        "aab5b3e2",  # 16629-1 spent leftover EAR (CadType+Stock, no FileType) — do not remint
        "6a568912",  # 10098-1 spent leftover PIVOTING FOOT (InternalData/ImageString empty) — do not remint
        "b8a62e76",  # SC0600 spent weldment explode InternalData empty 143/143 — do not remint
        "0d4b8a46",  # FA Assembly spent fetch+#img InternalData empty 28/28 — do not remint
        "5b622a0d",  # Skin Assembly spent jquery_ajax+EDIT InternalData empty 8/8 — do not remint
        "491f6387",  # 1001898-5 spent reconstructed PDF FileList / Cad no PR — do not remint
        "bd5c2e3e",  # 103535-1 spent cookie HTTP / empty #gridPDF — do not remint
        "425587a7",  # 34137-4 — do not open / PATCH / remint
        "95b8c186",  # 1007922-3 — do not open / PATCH / remint
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
        "34137-1",  # spent empty shell (08d7855 explode-ok / Finish miss)
        "34137-2",  # spent empty shell (9a0d895 fetch Finish miss) — leave it
        "34632-2",  # spent empty shell (f6ac309 page_fn List=0) — leave it
        "106384-1",  # spent 20MB+ Upload 502 — do not remint
        "105918-1",  # spent 23b96a9 Finish 66 / 0 Cad — do not PATCH or remint
        "106386-1",  # spent empty shell (1fd9b53 explode-ok / bind miss) — leave it
        "106687-1",  # spent bd4d75e Upload 502 43MB — do not remint or chunk
        "10107-1",  # occupied — do not remint
        "14284-2",  # occupied — do not remint
        "21807-1",  # occupied — do not remint
        "1007830-1",  # occupied — do not remint
        "28110-2",  # spent 6c02c08 Finish 200 / GET 0 — do not PATCH or remint
        "107877-1",  # spent 1e76c96 explode_passes=1 / GET 0 — do not PATCH or remint
        "1020249-1",  # spent e21bc43 pass-2 wiped grid — do not PATCH or remint
        "5003313-001",  # spent 526d139 Finish on leftover 105918-1 — do not PATCH or remint
        "P001545",  # spent 9735155 page Finish empty body — do not PATCH or remint
        "BB2000-ASM",  # spent ad38881 skip-Finish / GET 0 — do not PATCH or remint
        "EHB3112",  # spent 83c9200 OnAddDXFClick empty body — do not remint
        "EHB3112-1",  # spent 83c9200 QuoteNumber auto -1 — do not remint
        "11796-1",  # spent 4c79659 kendo FileList / AF miss — do not remint
        "11796-2",  # spent 619ebf2 SourceDataID=0 / 200 empty — do not remint
        "107292-1",  # spent ce5d2c1 empty body vs List,Result — do not remint
        "16629-1",  # spent 76dd572 leftover EAR — CadType+Stock, no FileType — do not remint
        "10098-1",  # spent 315cb19 leftover PIVOTING FOOT — Cad InternalData/ImageString empty — do not remint
        "SC0600",  # spent 2c29618 weldment explode InternalData empty 143/143 — do not remint
        "FA Assembly",  # spent 0d4b8a46 fetch+#img InternalData empty 28/28 — do not remint
        "Skin Assembly",  # spent 5b622a0d jquery_ajax+EDIT InternalData empty 8/8 — do not remint
        "1001898-1",  # Kyle-confirmed gold a7dc46bf — do not remint
        "1001898-5",  # spent 491f6387 reconstructed PDF FileList / Cad no PR — do not remint
        "103535-1",  # spent bd5c2e3e cookie HTTP / empty #gridPDF — do not remint
        "Q10095",  # spent 103535-1 GATE WELDMENT — do not remint
        "34137-4",  # spent 425587a7 — do not remint
        "1007922-3",  # spent 95b8c186 — do not remint
        # Do not mint. Server never fills InternalData on explode.
        # Do not invent payload. Next mint only after a new named persist.
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
