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
        "d2f7b031-a5a8-4020-a6a3-dba8de964ebf",  # 29743-1 #files bind / Cad no PR pack (leave it)
        "b2e12461-442b-436e-9445-772e992644f6",  # 1002323-1 perimeter XHR / CuttingLength 0 (leave it)
        "47c393f8-db59-4b9a-a243-48d572011f77",  # 33819-1 Weight bag / ProductID None (leave it)
        "646a3d98-cd73-4f94-be67-6e40eeb2c309",  # 21681-1 empty bind ProductID skip (leave it)
        "8930f65a-c1e3-44b0-8024-9075b2a5ab80",  # 1007092-1 GET ProductID / empty Tag OCL (leave it)
        "e57633b6-7bfc-4235-80de-a0e3be6cc5cc",  # 33204-1 list0_pack empty Tag/OCL (leave it)
        "8fb3da71-1948-4da2-a70f-8ef06b78cf32",  # 29340-1 API mint / cookie AddView 302 (leave it)
        "14219adc-f7f5-401a-b707-0bf200ef8c74",  # 34603-2 ProductID/org/no-hole Cad (leave it)
        "9be15b62-a824-442c-b911-50ca1016cc5e",  # 21682-1 plate_sku_missing / ProductID null (leave it)
        "c23fba3d-ef02-412b-b06e-f91ffa9076a6",  # 29341-1 ProductID+hole / empty BadgeString (leave it)
        "ad1777be-1951-42b6-9be4-d97c3a42dd94",  # 1007471-1 PR18 e4df7f2 multi-kid PASS — do not remint / PATCH
        "7a631c5f-39ca-40fc-b733-88b2b2d04636",  # 34602-2 PR18 1259cda nested+Component PASS — do not remint / PATCH
        "6bfde652-b65a-41b7-840c-af8f088097d4",  # 1007756-1 PR18 b0305c5 ≥8-kid PASS — do not remint / PATCH
        "87e64b3a-210e-42d9-bfae-1921b1540f16",  # 1001898-4 PR18 b80dff6 angle Linear Saw PASS — do not remint / PATCH
        "5804a001-68ef-4eab-a587-ba2d73718924",  # 1008763-1 PR18 d1fb034 channel Linear Saw PASS — do not remint / PATCH
        "3f3802da-bc11-4a71-83a0-62454b33f69c",  # 1020243-1 PR18 d7c4ea9 RenestLinear 480→240 PASS — do not remint / PATCH
        "8e5f04fa-661c-4624-8047-8d3c8c6b359d",  # 33209-1 PR18 ce2259a Long/Saw PASS — do not remint / PATCH
        "3aae24a8-d619-4906-ab00-6db4d7950d0e",  # 21846-1 PR18 1cc274d Long/Saw angle PASS — do not remint / PATCH
        "2a07e6d0-cb9d-42f6-959f-5f33ea9fb381",  # 20860-1 PR18 2ea5400 Long/Saw PASS — do not remint / PATCH
        "aa55937d-45af-4559-9542-843a144e9865",  # 1002013-1 PR18 85166b4 Cad Image Files PASS — do not remint / PATCH
        "84234fb5-42cb-49a4-b701-931e834c4ca8",  # 25587 PR18 6cea2cc Cad Image Files PASS — do not remint / PATCH
        "4216109a-4603-45ed-a83d-6c2f071a8c6c",  # 21625-1 PR18 593db19 Cad Image Files PASS — do not remint / PATCH
        "8a66e074-1c50-4671-82ff-d2d2d8e82082",  # 15046-1 PR18 01da281 Long/Saw PASS — do not remint / PATCH
        "c71d2096-1cbd-40c8-877e-97f4c86df410",  # 10081-1 PR18 4f4a6fb Long/Saw PASS — do not remint / PATCH
        "30550221-733a-4baf-866a-73396a0d799b",  # 21667-1 PR18 11562dd Cad Image Files PASS — do not remint / PATCH
        "7f768328-1a9a-4498-af74-f2aa78b930ef",  # 21666-1 PR18 769e05a Long/Saw PASS — do not remint / PATCH
        "3ff05f3a-79a3-48f7-add1-0ea8bbf9d884",  # 21674-1 PR18 998a100 Cad Image Files PASS — do not remint / PATCH
        "b15a892e-aca3-47aa-8272-3e436e980468",  # 21671-1 PR18 998a100 Long/Saw PASS — do not remint / PATCH
        "fb3080d8-ad8d-4e8b-9902-c5e155ab6dc1",  # 21675-1 PR18 d766fd5 Cad Image Files PASS — do not remint / PATCH
        "5c245fbb-04aa-4746-9845-4dc59aa2d9fe",  # 1007510-1 PR18 bf6d909 Cad Image Files PASS — do not remint / PATCH
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
        "d2f7b031",  # 29743-1 spent #files bind / Cad no PR pack — do not remint
        "b2e12461",  # 1002323-1 spent perimeter XHR / CuttingLength 0 — do not remint
        "47c393f8",  # 33819-1 spent Weight bag / ProductID None — do not remint
        "646a3d98",  # 21681-1 spent empty bind ProductID skip — do not remint
        "8930f65a",  # 1007092-1 spent GET ProductID / empty Tag OCL — do not remint
        "e57633b6",  # 33204-1 spent list0_pack empty Tag/OCL — do not remint
        "3102870a",  # 1009213-1 spent modal SKU / list0_pack empty — do not remint
        "8fb3da71",  # 29340-1 spent API mint / cookie AddView 302 — do not remint
        "14219adc",  # 34603-2 spent ProductID/org/no-hole Cad — do not remint
        "9be15b62",  # 21682-1 spent plate_sku_missing / ProductID null — do not remint
        "c23fba3d",  # 29341-1 spent ProductID+hole / empty BadgeString — do not remint
        "3e222215",  # 1020250-1 5a231aa form_lw_synced=false / OP=0 — ZZ-DEL
        "f4d94abd",  # 1020250-1 companion ZZ-DEL 2026-09-07 — do not remint
        "b187c0c1",  # 1020250-1 companion ZZ-DEL 2026-09-07 — do not remint
        "c49cebf0",  # 1020250-1 companion ZZ-DEL 2026-09-07 — do not remint
        "1ca884cc",  # 1020250-1 fc94ca9 form_lw_synced + OP, FileList n=0 — ZZ-DEL
        "111633b8",  # 1020250-1 fc94ca9 companion ZZ-DEL — do not remint
        "6150c5c7",  # 1020250-1 77ddb70 FileList n=1 InternalData null — ZZ-DEL
        "bab8f668",  # 1020250-1 55a0294 plate ProductID + InternalData, ProductType=bar — ZZ-DEL
        "c751780e",  # 1020250-1 533ef0f prt_pdf + InternalData Dim1, Contours=0 / no PR — ZZ-DEL
        "2a83a96b",  # 1020250-1 4f68c9d OutsideArea+TrueWeight, MaterialCost empty / Contours=0 — ZZ-DEL
        "9ef2fedd",  # 1020250-1 1b0dd01 empty_materialcost abort blocked Finish — ZZ-DEL
        "97ae3e4f",  # 1020250-1 c213d42 Finish 200 List[0] Data=None ErrorCount=1 / Contours=0 — ZZ-DEL
        "3ac04f8a",  # 1020250-1 PR18 3bacf2a Cad Image Files PASS — do not remint / PATCH
        "6d4373bc",  # 21684-1 PR18 3bacf2a Long/Saw PASS; PrimaryOrganizationID empty GUID after POST 201 — do not remint / PATCH
        "d2ec4357",  # 1007922-3 OUTRIGGER nest+packs PASS (Cad 10099-1 PR + Linear RT2 1/4X0.5-A519 + Copy/Move) — do not remint / PATCH
        "bf4221e8",  # 29743-2 PR18 a1dacc9 weld+nest PASS — do not remint / PATCH
        "ad1777be",  # 1007471-1 PR18 e4df7f2 multi-kid PASS — do not remint / PATCH
        "7a631c5f",  # 34602-2 PR18 1259cda nested+Component PASS — do not remint / PATCH
        "6bfde652",  # 1007756-1 PR18 b0305c5 ≥8-kid PASS — do not remint / PATCH
        "87e64b3a",  # 1001898-4 PR18 b80dff6 angle Linear Saw PASS — do not remint / PATCH
        "5804a001",  # 1008763-1 PR18 d1fb034 channel Linear Saw PASS (20ft/240, no 480 renest) — do not remint / PATCH
        "3f3802da",  # 1020243-1 PR18 d7c4ea9 RenestLinear 480→240 PASS — do not remint / PATCH
        "8e5f04fa",  # 33209-1 PR18 ce2259a Long/Saw PASS (RTD2X0.25-A513 UC 19.59 Time Waco) — do not remint / PATCH
        "3aae24a8",  # 21846-1 PR18 1cc274d Long/Saw angle PASS (L3X3X1/4-A36 UC 17.08 Time Waco) — do not remint / PATCH
        "2a07e6d0",  # 20860-1 PR18 2ea5400 Long/Saw PASS (ST8X0.375-A500 UC 83.53 Time Waco) — do not remint / PATCH
        "aa55937d",  # 1002013-1 PR18 85166b4 Cad Image Files PASS (PL3/8-A572 UC 25.32 Time Laser Bay1) — do not remint / PATCH
        "84234fb5",  # 25587 PR18 6cea2cc Cad Image Files PASS (PL3/8-A572 UC 24.41 Time) — do not remint / PATCH
        "4216109a",  # 21625-1 PR18 593db19 Cad Image Files PASS (PL1/4-A572 UC 25.64 Time Laser Bay1) — do not remint / PATCH
        "8a66e074",  # 15046-1 PR18 01da281 Long/Saw PASS (RTD2 3/4X0.375-A513 UC 16.32 Time Waco) — do not remint / PATCH
        "c71d2096",  # 10081-1 PR18 4f4a6fb Long/Saw PASS (P5-40-A36 UC 22.46 Time Waco) — do not remint / PATCH
        "30550221",  # 21667-1 PR18 11562dd Cad Image Files PASS (PL3/8-A572 UC 26.37 Time Laser Bay1) — do not remint / PATCH
        "7f768328",  # 21666-1 PR18 769e05a Long/Saw PASS (RTD3X0.438-A513 UC 48.21 Time Waco) — do not remint / PATCH
        "3ff05f3a",  # 21674-1 PR18 998a100 Cad Image Files PASS (PL1/4-A572 UC 23.74 Time Laser Bay1) — do not remint / PATCH
        "b15a892e",  # 21671-1 PR18 998a100 Long/Saw PASS (RT2X0.5-A519 UC 9.44 Time Waco) — do not remint / PATCH
        "fb3080d8",  # 21675-1 PR18 d766fd5 Cad Image Files PASS (PL3/16-A572 UC 22.92 Time Laser Bay1) — do not remint / PATCH
        "5c245fbb",  # 1007510-1 PR18 bf6d909 Cad Image Files PASS (PL1/4-A572 UC 24.66 Time Laser Bay1) — do not remint / PATCH
        "d5a6987d",  # 21785-2 Outer Boom STEP @ ab58a96 — InternalData 14/14 empty, ZZ-DEL ARCHIVED — do not remint
        "30f50f96",  # P904272-1 ZZ-DEL before classify @ 0163ffd Login fail — leftover EDIT amtech footer / dead AspNet — do not remint
        "0837ad33",  # P904271-1 @ 0163ffd classify/SetPartMode Cad×3 then InternalData-empty refuse — ZZ-DEL — do not remint
        "1004f017",  # 10289-4 @ 2320c6d PartMode Cad then page Finish skipped filelist_cad_payload_empty / reconstructed 200 GET 0 — ZZ-DEL — do not remint
        "28708035",  # 28768-1 @ f656655 PartMode Cad + page Finish FileList n=1 InternalData null / bar_flat / GET 0 Cad — ZZ-DEL — do not remint
        "c146ce6d",  # 28769-1 leftover empty explode InternalData / CadImport GET empty — ZZ-DEL — do not remint
        "4b8d6ae6",  # 103535-1 leftover @ 8e08f53 — kids stamped via CDP before nest refuse — do not remint / PATCH
        "b1036d7d",  # 33819-2 spent plate_sku_missing — do not remint
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
        "1007756-3",  # spent empty shell — do not remint
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
        "1001898-4",  # spent 87e64b3a angle Linear Saw PASS @ b80dff6 — do not remint
        "1008763-1",  # spent 5804a001 channel Linear Saw PASS @ d1fb034 — do not remint
        "1020243-1",  # spent 3f3802da RenestLinear 480→240 PASS @ d7c4ea9 — do not remint
        "33209-1",  # spent 8e5f04fa Long/Saw PASS @ ce2259a — do not remint
        "21846-1",  # spent 3aae24a8 Long/Saw angle PASS @ 1cc274d — do not remint
        "20860-1",  # spent 2a07e6d0 Long/Saw PASS @ 2ea5400 — do not remint
        "1002013-1",  # spent aa55937d Cad Image Files PASS @ 85166b4 — do not remint
        "25587",  # spent 84234fb5 Cad Image Files PASS @ 6cea2cc — do not remint
        "25587-1",  # occupied sibling — do not remint
        "21625-1",  # spent 4216109a Cad Image Files PASS @ 593db19 — do not remint
        "15046-1",  # spent 8a66e074 Long/Saw PASS @ 01da281 — do not remint
        "10081-1",  # spent c71d2096 Long/Saw PASS @ 4f4a6fb — do not remint
        "21667-1",  # spent 30550221 Cad Image Files PASS @ 11562dd — do not remint
        "21666-1",  # spent 7f768328 Long/Saw PASS @ 769e05a — do not remint
        "21674-1",  # spent 3ff05f3a Cad Image Files PASS @ 998a100 — do not remint
        "21671-1",  # spent b15a892e Long/Saw PASS @ 998a100 — do not remint
        "21675-1",  # spent fb3080d8 Cad Image Files PASS @ d766fd5 — do not remint
        "1007510-1",  # spent 5c245fbb Cad Image Files PASS @ bf6d909 — do not remint
        "103535-1",  # spent bd5c2e3e cookie HTTP / empty #gridPDF — do not remint
        "Q10095",  # spent 103535-1 GATE WELDMENT — do not remint
        "34137-4",  # spent 425587a7 — do not remint
        "1007922-3",  # spent 95b8c186 — do not remint
        "29743-1",  # spent d2f7b031 #files bind / Cad no PR pack — do not remint
        "1002323-1",  # spent b2e12461 perimeter XHR / CuttingLength 0 — do not remint
        "33819-1",  # spent 47c393f8 Weight bag / ProductID None — do not remint
        "21681-1",  # spent 646a3d98 empty bind ProductID skip — do not remint
        "1007092-1",  # spent 8930f65a GET ProductID / empty Tag OCL — do not remint
        "33204-1",  # spent e57633b6 list0_pack empty Tag/OCL — do not remint
        "1009213-1",  # spent 3102870a modal SKU / list0_pack empty — do not remint
        "29340-1",  # spent 8fb3da71 API mint / cookie AddView 302 — do not remint
        "34603-2",  # spent 14219adc child of 34602-2 — do not remint
        "34602-2",  # spent 7a631c5f nested+Component PASS @ 1259cda — do not remint
        "21682-1",  # spent 9be15b62 plate_sku_missing / ProductID null — do not remint
        "29341-1",  # spent c23fba3d ProductID+hole / empty BadgeString — do not remint
        "33819-2",  # spent b1036d7d plate_sku_missing — do not remint
        "1007471-1",  # spent ad1777be multi-kid weld+nest PASS @ e4df7f2 — do not remint
        "1007756-1",  # spent 6bfde652 ≥8-kid PASS @ b0305c5 — do not remint
        "21785-1",  # spent Outer Boom Insulated leftover — /part/create List=0, ZZ-DEL — do not remint
        "21785-2",  # spent d5a6987d Outer Boom STEP @ ab58a96 — ImageString preview, InternalData 14/14 empty, ZZ-DEL ARCHIVED — do not remint
        "21785-3",  # spent Outer Boom Insulated leftover — /part/create List=0, ZZ-DEL — do not remint
        "35145-1",  # Kyle Loom c9d7c05a Q10243 STEP gold look — do not remint / PATCH
        "Q10243",  # Kyle Loom c9d7c05a / 35145-1 — do not remint
        "P904272-1",  # spent 30f50f96 ZZ-DEL before classify @ 0163ffd Login fail — do not remint
        "P904271-1",  # spent 0837ad33 classify/SetPartMode Cad×3 @ 0163ffd then pre-Finish InternalData refuse — ZZ-DEL — do not remint
        "10289-4",  # spent 1004f017 PartMode Cad @ 2320c6d then page Finish skipped filelist_cad_payload_empty — ZZ-DEL — do not remint
        "28768-1",  # spent 28708035 PartMode Cad + page OnAddDXFClick @ f656655 InternalData null / bar_flat / GET 0 Cad — ZZ-DEL — do not remint
        "28769-1",  # spent c146ce6d leftover empty explode InternalData / CadImport Data+CADData empty — ZZ-DEL — do not remint
        # Do not remint 21785-1 / 21785-2 / 21785-3 / 35145-1 / Q10243 / P904272-1 / P904271-1 / 10289-4 / 28768-1 / 28769-1.
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


def spent_quote_number_block_reason(
    quote_number: str | None,
    *,
    existing_id: str | None = None,
) -> str | None:
    """Fail-close reason before mint / kid stamps, or None if the number is free.

    Live 103535-1 @ 8e08f53: create mint POSTs QuoteNumber without ID, so the
    old ID+number gate let CDP stamp kids before nest POST refused.
    """
    qn = str(quote_number or "").strip()
    if not qn:
        return None
    if is_forbidden_quote_number(qn):
        return (
            f"QuoteNumber {qn} is forbidden — not minting, not stamping kids"
        )
    eid = str(existing_id or "").strip()
    if eid:
        return (
            f"QuoteNumber {qn} already spent ({eid}) — not minting, not stamping kids"
        )
    return None


def refuse_forbidden_quote_write(
    *,
    method: str,
    path: str,
    payload: Any = None,
) -> None:
    """Raise if a write would PATCH/reuse a forbidden live quote.

    GET is allowed. New quotes with an unused job PN are allowed. A forbidden
    QuoteNumber is refused even without ID so create mint cannot stamp kids first.
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
    qn = str(blob.get("QuoteNumber") or "").strip()
    if is_forbidden_quote_number(qn):
        suffix = f" ({qid})" if qid else ""
        raise ForbiddenQuoteError(
            f"Refusing to PATCH/reuse forbidden live quote {qn}{suffix}"
        )
