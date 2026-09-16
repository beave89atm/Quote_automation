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
        "2db59f00-bc2f-4dc3-a740-683d60799943",  # 1007578-1 PR18 d96c096 Cad Image Files PASS — do not remint / PATCH
        "cf656d2a-a432-46c4-9ad2-439807194442",  # 1010110-1 PR18 d96c096 Cad Image Files PASS — do not remint / PATCH
        "50c6d543-05e4-4b76-a507-4b6b7a19d6b4",  # 1004711-1 PR18 632c721 Cad Image Files PASS — do not remint / PATCH
        "aae055fe-46c7-4fc7-bc12-f10d4de30f54",  # 25009-1 PR18 fc7344d Cad Image Files PASS — do not remint / PATCH
        "46eed794-257d-4987-ae48-98c7d6c7dd07",  # 25009-2 PR18 72d7665 Cad Image Files PASS — do not remint / PATCH
        "f300ecea-ccf3-4c5e-adaf-db73bdfb80fb",  # 1010106-1 PR18 6289d3c Cad Image Files PASS — do not remint / PATCH
        "5dc50b55-f546-449f-9f23-7f7ddf67772b",  # 1010111-1 PR18 26bedc4 Cad Image Files PASS — do not remint / PATCH
        "8973f890-b2a1-48fb-b6be-3530caeb1819",  # 35136-1 Kyle STEP leftover — OpenContourCount=0 / 3× bar InternalData empty / AddItem_DXFFiles bar_flat empty — fail-close; do not remint / PATCH
        "c5cd8689-fed4-44d6-b2f5-f96bda8af424",  # 14327-5 flat-plate STEP leftover @ 7b59ff0 — /part/create list_len=1 InternalData empty 1/1, ImageString preview-only, CadImport Data/CADData bindable=false, OpenContourCount empty/null, ProductType null, Finish refused, invented=false; ZZ-DEL-14327-5 — do not remint / PATCH
        "1cd941c6-9167-41e9-ac93-b7268f18f282",  # 14327-8 leftover @ 7b59ff0 — same empty-InternalData Contours FAIL as 14327-5/c5cd8689; invented=false; ZZ-DEL-14327-8 — do not remint / PATCH
        "75f07c2b-b000-47f4-9caa-c14520e2b068",  # Q10329 / 14327-3 L-angle Contours UI leftover — Adjust Properties Contours column absent; Finish never clicked; invented=false; ZZ-DEL-Q10329-14327-3-contours-ui — do not remint / PATCH
        "aed89628-b018-4b11-852f-bfed5bf8b964",  # Q10330 / 21841-1 angle/channel Contours UI leftover — Contours column absent; Finish never clicked; invented=false; ZZ-DEL-Q10330-21841-1-contours-ui — do not remint / PATCH
        "5e72fe39-edc1-467c-925d-f1c8d74cc5d3",  # Q10331 / 14327-1 flat-looking Contours UI leftover — Contours column absent; Finish never clicked; invented=false; ZZ-DEL-Q10331-14327-1-contours-ui — do not remint / PATCH
        "b5f56ac3-326d-48e9-b82d-1e09a7897107",  # Q10333 / Safe Cave / H.6.38 Contours PASS — ProductType Cad / Contours=1 / 8 bends + Profile / Laser Bay1 / UC 176.96; unlock Component→Cad then inches; never remint / PATCH / ZZ-DEL
        "f73dd116-f33e-485f-947c-f5662633d23a",  # Q10336 / Safe Cave / H.6.38 Cad+Laser Finish leftover — finished NumberOfContours=1 matches Q10333; OCC=0 expected; bends=8; Laser Bay1 / UC 64.25; never remint / PATCH / ZZ-DEL
        "76cecc73-257e-4fa7-91b7-ed15a4c90caa",  # Q10339 / Safe Cave / H.6.38 Cad+Laser Finish leftover — finished NumberOfContours=1 matches Q10333; OCC=0 expected; Laser Bay1 / UC 64.25 / unit price 176.96; invented=false; never remint / PATCH / ZZ-DEL
        "55f12530-e97b-40cc-8e7f-e799d9d6b234",  # Q10344 / Safe Cave / H.6.38 Kyle UI control PASS leftover — ProductType Cad + thickness 0.1875 inch → Contours fill → Finish; invent=false; never remint / PATCH / ZZ-DEL
        "d859a239-a811-4b23-a812-29921956e880",  # Q10346 / Safe Cave Sprout B80510901 Contours PASS (outside H.6.38) — ProductType Cad + thickness 0.0598 inch → Contours fill → Finish; invent=false; never remint / PATCH
        "1defeed8-d95d-4939-b2fd-0a1774e56c6e",  # Q10348 / Safe Cave H.16.70 Contours PASS (outside H.6.38) — ProductType Cad + thickness 0.1875 inch → Contours fill → Finish; invent=false; never remint / PATCH
        "c4394006-667f-4bf6-a9b0-aa4b1722160a",  # Q10349 / Safe Cave D.H.30.96 Contours PASS (outside H.6.38) — ProductType Cad + thickness 0.1875 inch → Contours fill → Finish; invent=false; never remint / PATCH
        "0c62fce9-d56a-434e-a33a-372ddb12a2b4",  # Q10351 / Safe Cave H.8.38 Contours PASS (outside H.6.38) — ProductType Cad + thickness inches → Contours fill → Finish; invent=false; never remint / PATCH
        "7881d4b3-5408-4ff4-ab18-6490170e6331",  # Q10354 / Safe Cave D.H.38.96 Contours FAIL leftover — Cad selector + 0.1875 in set but finished ProductType rendered part; NumberOfContours unavailable / Contours PASS not proven; same empty-InternalData Contours-FAIL class as Q10334/Q10335; invent=false; never remint / PATCH
        "05bee105-824c-4100-9bc8-f66727fa5681",  # Q10356 / Safe Cave V.20.78 Contours FAIL leftover — Cad selector + 0.1875 in set but finished ProductType rendered part; NumberOfContours missing / Contours PASS not proven; same Contours-FAIL class as Q10354 / D.H.38.96; invent=false; never remint / PATCH
        "7801ab99-13af-4efc-b996-897daf8e677a",  # Q10365 / Safe Cave H.10.38 Contours FAIL leftover — mouse Cad + 0.1875 in set but finished ProductType rendered part; no Contours/InternalData fill; fill_xhr=null; same Contours-FAIL class as Q10354 / Q10356; invent=false; never remint / PATCH
        "fd0b6e45-d508-4b01-bbc0-45b338cd966d",  # Q10366 / Safe Cave / H.6.38 Contours PASS — invent=false; never remint / PATCH
        "4c9c25d4-439f-42be-8f6f-7444e5f05497",  # Q10367 / 10289-5 Contours PASS @ 6e8a2c3 — Cad+A36+0.1875→Finish; NumberOfContours=14; ProductType 100; invent=false; never remint / PATCH
        "82c28793-96e8-457b-9559-979c2b761d4e",  # Q10369 / 34328-1 Contours FAIL leftover — multi-kid Cad+Material+inches on one kid wiped #gridDXFParts; second kid Material/thickness blank → Contours=0 while configured kid Contours=1; invent=false; never remint / PATCH (do not forbid 34328-1 — PO may remint the PN)
        "5e0ce1df-e18b-4118-945a-8be85378069e",  # Q10368 / 34328-1 Contours FAIL leftover @ 8d4626a — keep-grid Material worked; 3 Cad kids all A36 + thickness through Finish; Contours 0/1/0; PASS 34329 BOOM SUPPORT A36 0.25in Contours=1; FAIL two HOOK BOOM REST-7742_31454-1 A36 0.5in Contours=0; invent=false; never remint / PATCH (do not forbid 34328-1 — PO may remint the PN)
        "67472e72-d01b-48e2-8040-1db505659d26",  # Q10371 / 34328-1 Contours FAIL leftover @ 22e327f — remint EXEC_FAIL; 31454-1 Contours=1 @0.5in; 34329 red thickness @0.25 Contours blocked (PR47 gate); invent=false; never remint / PATCH (do not forbid 34328-1 — PO may remint the PN)
        "d62e2ad1-7324-4034-a44e-cbd7a3acee9d",  # Q10372 / 34328-1 Time weldment Contours remint EXEC_FAIL leftover @ d2616fc — invent=false; Complete Quote NOT DONE; HOOK 31454-1 Contours=0 (mistreated as A36/.50 plate; drawing=RD BAR CR 1018 1/2 DIA, not plate); 34329 Contours=1 at A36/.25 gauge-list; never remint / PATCH (do not forbid 34328-1 — PO may remint the PN)
        "523d8328-f310-434d-a502-00502c987dd2",  # Q10373 / 34328-1 Time weldment mixed classify PASS leftover @ 1650cf5 — invent=false; Complete Quote NOT DONE; OPEN-NEW draft; plate 34329 Cad A36 .25-1/4" gauge Laser NumberOfContours≥1; HOOK 31454-1 Long/Linear Hot Rolled Round Bar CRS (closest to RD BAR CR 1018) 0.5" × 4.375" Saw no Contours path; never remint / PATCH (do not forbid 34328-1 — PO may remint the PN)
        "beb20d22-173a-4b0d-be8d-c1263538cdb5",  # Q10374 / 1008399-1 coverage remint FAIL-CLOSE leftover @ e604229 — STEP uploaded; plate 1008400 gauge unverified (no local drawing / SharePoint unreachable); invent=false stop before Contours; Complete Quote NOT DONE; never remint / PATCH (do not forbid 1008399-1 — PN remints remain ALLOWED)
        "60de939f-85f0-4f1a-9412-39c29211ad30",  # Q10375 / 1008399-1 remint EXEC_FAIL leftover @ 6a4f536 — Cad/A572 G50/.375-3/8 plate + Linear Saw bar + Component hardware set; Contours≥1 not verified (blank CAD editor); invent=false; Complete Quote NOT DONE; never remint / PATCH (do not forbid 1008399-1 — PN remints remain ALLOWED)
        "12bd2530-e6ed-4792-9e47-bdd20fff1e70",  # Q10377 / 1008399-1 Time Boom Rest NEW remint PASS leftover @ 8f5d17c — invent=false; Complete Quote NOT DONE; Cad Contours + Long/Linear + Component; plate 1008400-1 Cad A572 G50 .375-3/8" NumberOfContours=1 (Finish→tree verify); bar 31454-1 Long/Linear Saw IsLinear=true; hardware 40003/40006 IsComponent=true; never remint / PATCH (do not forbid 1008399-1 — PN remints remain ALLOWED)
        "70e69d9c-9d9f-4b2e-b7f1-7ac9ae80da9e",  # Q10379 / 11643-1 Platform Mount NEW remint PASS leftover @ d34b5b4 — invent=false; Complete Quote NOT DONE; OPEN-NEW draft (CAD Finish ≠ Complete Quote); plate Cad Contours + tube/slug Long/Linear; plate 11640-1 Cad A572 G50 /.25 NumberOfContours=1; plate 11642-2 Cad A36 /.375 NumberOfContours=1; tube 11641-1 Long/Linear tube_round IsLinear A513 2.00×1.50×7.4375; slug 32070-1 Long/Linear bar_round IsLinear C1018 2.00×0.45; never remint / PATCH (do not forbid 11643-1 — PN remints remain ALLOWED)
        "754089f2-fd55-4e3d-865c-8dffa63181fa",  # Q10380 / 16630-1 Rotation Top Stop NEW remint PASS leftover @ 937b19c — invent=false; Complete Quote NOT DONE; OPEN-NEW draft (CAD Finish ≠ Complete Quote); plate Cad Contours + CT/ring Long/Linear; plate 16629-1 EAR Cad A36 /.5-1/2" NumberOfContours=1 qty 2; ring 16628-1 Long/Linear tube IsLinear A513 7.25 OD × 6.0 ID × 1.69 L wall 0.625 qty 1; never remint / PATCH (do not forbid 16630-1 — PN remints remain ALLOWED)
        "bb31a132-c93a-4c21-84f3-7a83c62cead6",  # Q10381 / 1001093-1 Hose Guide NEW remint PASS leftover @ 6fefaac — invent=false; Complete Quote NOT DONE; OPEN-NEW draft (CAD Finish ≠ Complete Quote); 3 plate Cad Contours + RD BAR Long/Linear; plates 1000480/1001090/1001091 Cad A572 G50 /.1875-3/16 NumberOfContours=1 each; bar 1001092-1 Long/Linear IsLinear CRS/CR1018 .188 × 5.5625; never remint / PATCH (do not forbid 1001093-1 — PN remints remain ALLOWED)
        "2d42dcc3-76e3-439b-be02-32c2f1b3c9a2",  # Q10382 / 35146-1 Jib Turret NEW remint PASS leftover @ 86906b7 — invent=false; Complete Quote NOT DONE; OPEN-NEW draft (CAD Finish ≠ Complete Quote); 2 plate Cad Contours + CT Long/Linear; plates 35123/.1875 DOMEX + 35125/10GA DOMEX NumberOfContours=1 each; tube 35124 Long/Linear IsLinear A513 4.25×3.75×6.25; never remint / PATCH (do not forbid 35146-1 — PN remints remain ALLOWED)
        "9d7cc06e-0c7a-4393-a49f-498a1f484c31",  # Q10383 / 21641-1 TIP SLEEVE remint EXEC_FAIL leftover @ f7e689d — invent=false; Complete Quote NOT DONE; OPEN-NEW leftover from 21641-1 TIP SLEEVE remint attempt 2026-09-14; Contours=0 all plate Cad kids after Finish; CadImport InternalData empty; PrimaryOrganizationID lost mid CAD wizard; kids not per-PN classified (all named 21641-1 @ 0.25); never remint / PATCH (do not forbid 21641-1 — PN remints remain ALLOWED)
        "039d8464-6fe1-424a-a120-a31e59964e7e",  # Q10399 / 21641-1 hardened remint EXEC_FAIL leftover @ 6a26835 — invent=false; Complete Quote NOT DONE; OPEN-NEW leftover from hardened 21641 remint 2026-09-14; dig checklist gates 1–4 PASS; gate5 InternalData empty after explode refused AddItem_DXFFiles; Contours never filled; never remint / PATCH (do not forbid 21641-1 — PN remints remain ALLOWED)
        "4054443b-bc2a-47f4-95b1-b0ed037868c9",  # Q10420 / 35146-1 tip-prove EXEC_FAIL leftover @ c08c47b — invent=false; Complete Quote NOT DONE; OPEN-NEW leftover 2026-09-15; chrome_cdp skipped page Finish on empty InternalData despite tip refuse-relax (cad_material_inches_recipe_complete); Contours never filled; never remint / PATCH (do not forbid 35146-1 — PN remints remain ALLOWED)
        "1d59ef4a-5b75-49e7-89fe-02e125830162",  # Q10450 leftover after PR62 CDP prove — invent=false 2026-09-15; Contours never landed; live QN drifted toward forbid Q10408 label; OPEN-DRAFT; never remint / PATCH (do not forbid 35146-1 — PN remints remain ALLOWED)
        "a24c6896-ac5c-4d52-9ac6-1c208440940c",  # Q10429 / Safe Cave H.6.38 Kyle UI Finish 2026-09-15 Contours PASS leftover — NumberOfContours=1 OPEN-NEW invent=false; never remint / PATCH (do not forbid H.6.38 — PN remints remain ALLOWED)
        "eb9a17c4-c28b-4fc1-8bda-3d50d6ee2d3b",  # Q10475 / Safe Cave H.8.38 tip-prove EXEC_FAIL leftover — Contours=0; AddItem empty; meter thickness vs .1875; OPEN-NEW invent=false 2026-09-15; never remint / PATCH (do not forbid H.8.38 — PN remints remain ALLOWED)
        "d667c6f2-6075-4ff1-8688-3ac9671f9bd6",  # Q10476 / Safe Cave H.10.38 tip-prove inch-force EXEC_FAIL leftover — thickness stayed meter not PDF .1875 inch; Finish aborted invent=false OPEN-NEW 2026-09-15; never remint / PATCH (do not forbid H.10.38 — PN remints remain ALLOWED)
        "e0990112-d127-4db3-8276-3e80bee233ee",  # Q10479 / Safe Cave H.10.38 tip-prove after PR68 leftover — inch 0.1875 stuck PROVED; Contours=0 AddItem empty body land-miss; OPEN-NEW invent=false 2026-09-15; never remint / PATCH (do not forbid H.10.38 — PN remints remain ALLOWED)
        "e7e4abd1-bb4f-4b6e-be18-269b2d17e2bf",  # Q10480 / Safe Cave H.10.38 after PR68 leftover — inch 0.1875 PROVED; Contours=0 AddItem empty land-miss; OPEN-NEW invent=false 2026-09-15; never remint / PATCH (do not forbid H.10.38 — PN remints remain ALLOWED)
        "eb6c48b8-36b5-4f8d-85b2-ce964fd9e8f4",  # Q10350 / 21843-1 Time Waco Long/Linear PASS — Hot Rolled Round Bar Ø0.625 × 28.0843 Finish; invent=false; not a Contours leftover; bar/Linear path; never remint / PATCH
        "4902c597-2ad6-4ebf-b577-dd6cf20a7d87",  # Q10338 / CROSSDRAIN-12X7X60 PR18 Cad Image Files PASS — AIM Cross Drain / Time Waco / PL14 Ga-SS316 / 69.875×25.875 / Laser Bay1 / Contours=1 / Finish UC 100.45 + PR laser pack / bends_count=8 shop PDF / UpdateItemType Cad 200; post-pass bend-API dabble may show live UC 3.25 — Finish snapshot UC 100.45 is PASS basis; invented=false; never remint / PATCH
        "5e7bfc0b-ecf9-46cf-8851-d61062141ce7",  # H638-CADPLATE Cad-for-plate leftover — SetPartMode 0 + ProductType 100 Cad:1 classify OK, InternalData empty, Finish refuse; invented=false; ZZ-DEL-H638-CADPLATE — do not remint / PATCH
        "e2683a3f-daf5-49ff-83c1-79aed35207a1",  # Q10334 Cad-for-plate leftover — Chrome kendo Cad/100 + 0.1875 in + Laser-Bay1, Contours still empty; invented=false; ZZ-DEL-Q10334 — do not remint / PATCH
        "ef865b0f-66d2-404e-bff2-9ed1e7bf00ea",  # 15911-9 Time STEP leftover @ 62f7a92 — UpdateItemType Cad OK, InternalData empty after explode, Finish refused invent=false; CadImport/Data + PartImage + GetBorderSize not observed vs H.6.38; ZZ-DEL-15911-9 — do not remint / PATCH
        "1994392f-54a5-4245-80ee-a947fb07e3a7",  # 21839-1 Time STEP leftover @ bb4998a+ — UpdateItemType Cad OK, InternalData empty after explode, full CadImport/Data+GetBorderSize+PartImage trail still empty, Finish refused invent=false; ZZ-DEL-21839-1 — do not remint / PATCH
        "afee7458-6651-447e-ba1b-62c1c9c90ce8",  # GSB20570006 Sprout 1.1 leftover (CoS hold) — empty InternalData after full Cad+wizard mid-wizard (11 parts), Finish refused invent=false; Sectura-side empty-InternalData outside H.6.38 / Time pick; ZZ-DEL-GSB20570006 — do not remint / PATCH
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
        "2db59f00",  # 1007578-1 PR18 d96c096 Cad Image Files PASS (PL3/8-A572 UC 24.08 Time Laser Bay1) — do not remint / PATCH
        "cf656d2a",  # 1010110-1 PR18 d96c096 Cad Image Files PASS (PL3/16-A572 UC 22.44 Time Laser Bay1) — do not remint / PATCH
        "50c6d543",  # 1004711-1 PR18 632c721 Cad Image Files PASS (PL1/4-A572 UC 23.69 Time Laser Bay1) — do not remint / PATCH
        "aae055fe",  # 25009-1 PR18 fc7344d Cad Image Files PASS (PL1/2-A572 UC 25.99 Time Laser Bay1) — do not remint / PATCH
        "46eed794",  # 25009-2 PR18 72d7665 Cad Image Files PASS (PL1/2-A572 UC 27.32 Time Laser Bay1) — do not remint / PATCH
        "f300ecea",  # 1010106-1 PR18 6289d3c Cad Image Files PASS (PL3/8-A572 UC 79.99 Time Laser Bay1) — do not remint / PATCH
        "5dc50b55",  # 1010111-1 PR18 26bedc4 Cad Image Files PASS (PL3/8-A572 UC 56.07 Time Laser Bay1) — do not remint / PATCH
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
        "8973f890",  # 35136-1 leftover (kids 35137/35138) — Upload→CadImport/Data OpenContourCount=0→/part/create 3× bar empty→AddItem_DXFFiles empty bar_flat — Contours never filled; do not remint
        "c5cd8689",  # 14327-5 leftover — mint→ZZ-DEL-14327-5 @ 7b59ff0; /part/create n=1 InternalData empty; Data/CADData bindable=false; OpenContourCount empty/null; ProductType null; no extra CadImport/UI fill XHR; do not remint
        "1cd941c6",  # 14327-8 leftover — mint→ZZ-DEL-14327-8 @ 7b59ff0; same empty InternalData Contours FAIL as 14327-5; invented=false; do not remint
        "75f07c2b",  # Q10329 / 14327-3 Contours UI leftover — Contours column absent; Finish never; ZZ-DEL-Q10329-14327-3-contours-ui — do not remint
        "aed89628",  # Q10330 / 21841-1 Contours UI leftover — Contours column absent; Finish never; ZZ-DEL-Q10330-21841-1-contours-ui — do not remint
        "5e72fe39",  # Q10331 / 14327-1 Contours UI leftover — Contours column absent; Finish never; ZZ-DEL-Q10331-14327-1-contours-ui — do not remint
        "b5f56ac3",  # Q10333 / Safe Cave / H.6.38 Contours PASS — Cad / Contours=1 / 8 bends + Profile / Laser Bay1 / UC 176.96; never remint / PATCH / ZZ-DEL
        "f73dd116",  # Q10336 / Safe Cave / H.6.38 Cad+Laser Finish leftover — finished NumberOfContours=1 matches Q10333; OCC=0 expected; bends=8; Laser Bay1 / UC 64.25; never remint / PATCH / ZZ-DEL
        "76cecc73",  # Q10339 / Safe Cave / H.6.38 Cad+Laser Finish leftover — finished NumberOfContours=1 matches Q10333; OCC=0 expected; Laser Bay1 / UC 64.25 / unit price 176.96; invented=false; never remint / PATCH / ZZ-DEL
        "55f12530",  # Q10344 / Safe Cave / H.6.38 Kyle UI control PASS leftover — ProductType Cad + thickness 0.1875 inch → Contours fill → Finish; invent=false; never remint / PATCH / ZZ-DEL
        "d859a239",  # Q10346 / Safe Cave Sprout B80510901 Contours PASS (outside H.6.38) — Cad + 0.0598 inch → Contours fill → Finish; invent=false; never remint / PATCH
        "1defeed8",  # Q10348 / Safe Cave H.16.70 Contours PASS (outside H.6.38) — Cad + 0.1875 inch → Contours fill → Finish; invent=false; never remint / PATCH
        "c4394006",  # Q10349 / Safe Cave D.H.30.96 Contours PASS (outside H.6.38) — Cad + 0.1875 inch → Contours fill → Finish; invent=false; never remint / PATCH
        "0c62fce9",  # Q10351 / Safe Cave H.8.38 Contours PASS (outside H.6.38) — Cad + inches → Contours fill → Finish; invent=false; never remint / PATCH
        "7881d4b3",  # Q10354 / Safe Cave D.H.38.96 Contours FAIL leftover — Cad + 0.1875 in set, finished ProductType part; NumberOfContours unavailable / Contours PASS not proven; empty-InternalData Contours-FAIL class; invent=false; never remint / PATCH
        "05bee105",  # Q10356 / Safe Cave V.20.78 Contours FAIL leftover — Cad + 0.1875 in set, finished ProductType part; NumberOfContours missing / Contours PASS not proven; same Contours-FAIL class as Q10354 / D.H.38.96; invent=false; never remint / PATCH
        "7801ab99",  # Q10365 / Safe Cave H.10.38 Contours FAIL leftover — mouse Cad + 0.1875 in set, finished ProductType part; no Contours/InternalData fill; fill_xhr=null; same Contours-FAIL class as Q10354 / Q10356; invent=false; never remint / PATCH
        "fd0b6e45",  # Q10366 / Safe Cave / H.6.38 Contours PASS — invent=false; never remint / PATCH
        "4c9c25d4",  # Q10367 / 10289-5 Contours PASS @ 6e8a2c3 — Cad+A36+0.1875→Finish; NumberOfContours=14; ProductType 100; invent=false; never remint / PATCH
        "82c28793",  # Q10369 / 34328-1 Contours FAIL leftover — multi-kid Cad+Material+inches on one kid wiped #gridDXFParts; second kid Material/thickness blank → Contours=0; invent=false; never remint / PATCH
        "5e0ce1df",  # Q10368 / 34328-1 Contours FAIL leftover @ 8d4626a — keep-grid Material worked; Contours 0/1/0; invent=false; never remint / PATCH
        "67472e72",  # Q10371 / 34328-1 Contours FAIL leftover @ 22e327f — remint EXEC_FAIL; 31454-1 Contours=1 @0.5in; 34329 red thickness @0.25 Contours blocked (PR47 gate); invent=false; never remint / PATCH
        "d62e2ad1",  # Q10372 / 34328-1 Time weldment Contours remint EXEC_FAIL leftover @ d2616fc — HOOK 31454-1 Contours=0 (RD BAR CR 1018 1/2 DIA, not plate); 34329 Contours=1 A36/.25; invent=false; Complete Quote NOT DONE; never remint / PATCH
        "523d8328",  # Q10373 / 34328-1 Time weldment mixed classify PASS leftover @ 1650cf5 — plate 34329 Cad A36 .25 Laser NumberOfContours≥1; HOOK 31454-1 Long/Linear Hot Rolled Round Bar CRS 0.5" × 4.375" Saw no Contours path; invent=false; Complete Quote NOT DONE; OPEN-NEW draft; never remint / PATCH
        "beb20d22",  # Q10374 / 1008399-1 coverage remint FAIL-CLOSE leftover @ e604229 — STEP uploaded; plate 1008400 gauge unverified (no local drawing / SharePoint unreachable); invent=false stop before Contours; Complete Quote NOT DONE; never remint / PATCH
        "60de939f",  # Q10375 / 1008399-1 remint EXEC_FAIL leftover @ 6a4f536 — Cad/A572 G50/.375-3/8 plate + Linear Saw bar + Component hardware set; Contours≥1 not verified (blank CAD editor); invent=false; Complete Quote NOT DONE; never remint / PATCH
        "12bd2530",  # Q10377 / 1008399-1 Time Boom Rest NEW remint PASS leftover @ 8f5d17c — plate 1008400-1 Cad A572 G50 .375-3/8" NumberOfContours=1 (Finish→tree verify); bar 31454-1 Long/Linear Saw IsLinear=true; hardware 40003/40006 IsComponent=true; invent=false; Complete Quote NOT DONE; never remint / PATCH
        "70e69d9c",  # Q10379 / 11643-1 Platform Mount NEW remint PASS leftover @ d34b5b4 — plate 11640-1 Cad A572 G50 /.25 NumberOfContours=1; plate 11642-2 Cad A36 /.375 NumberOfContours=1; tube 11641-1 Long/Linear tube_round IsLinear A513 2.00×1.50×7.4375; slug 32070-1 Long/Linear bar_round IsLinear C1018 2.00×0.45; invent=false; Complete Quote NOT DONE; OPEN-NEW draft (CAD Finish ≠ Complete Quote); never remint / PATCH
        "754089f2",  # Q10380 / 16630-1 Rotation Top Stop NEW remint PASS leftover @ 937b19c — plate 16629-1 EAR Cad A36 /.5-1/2" NumberOfContours=1 qty 2; ring 16628-1 Long/Linear tube IsLinear A513 7.25 OD × 6.0 ID × 1.69 L wall 0.625 qty 1; invent=false; Complete Quote NOT DONE; OPEN-NEW draft (CAD Finish ≠ Complete Quote); never remint / PATCH
        "bb31a132",  # Q10381 / 1001093-1 Hose Guide NEW remint PASS leftover @ 6fefaac — plates 1000480/1001090/1001091 Cad A572 G50 /.1875-3/16 NumberOfContours=1 each; bar 1001092-1 Long/Linear RD BAR IsLinear CRS/CR1018 .188 × 5.5625; invent=false; Complete Quote NOT DONE; OPEN-NEW draft (CAD Finish ≠ Complete Quote); never remint / PATCH
        "2d42dcc3",  # Q10382 / 35146-1 Jib Turret NEW remint PASS leftover @ 86906b7 — plates 35123/.1875 DOMEX + 35125/10GA DOMEX NumberOfContours=1 each; tube 35124 Long/Linear CT IsLinear A513 4.25×3.75×6.25; invent=false; Complete Quote NOT DONE; OPEN-NEW draft (CAD Finish ≠ Complete Quote); never remint / PATCH
        "9d7cc06e",  # Q10383 / 21641-1 TIP SLEEVE remint EXEC_FAIL leftover @ f7e689d — Contours=0 all plate Cad kids after Finish; CadImport InternalData empty; PrimaryOrganizationID lost mid CAD wizard; kids not per-PN classified (all named 21641-1 @ 0.25); invent=false; Complete Quote NOT DONE; OPEN-NEW leftover from 21641-1 TIP SLEEVE remint attempt 2026-09-14; never remint / PATCH
        "039d8464",  # Q10399 / 21641-1 hardened remint EXEC_FAIL leftover @ 6a26835 — dig checklist gates 1–4 PASS; gate5 InternalData empty after explode refused AddItem_DXFFiles; Contours never filled; invent=false; Complete Quote NOT DONE; OPEN-NEW leftover from hardened 21641 remint 2026-09-14; never remint / PATCH
        "4054443b",  # Q10420 / 35146-1 tip-prove EXEC_FAIL leftover @ c08c47b — chrome_cdp skipped page Finish on empty InternalData despite tip refuse-relax (cad_material_inches_recipe_complete); Contours never filled; invent=false; Complete Quote NOT DONE; OPEN-NEW leftover 2026-09-15; never remint / PATCH
        "1d59ef4a",  # Q10450 leftover after PR62 CDP prove — Contours never landed; live QN drifted toward forbid Q10408 label; OPEN-DRAFT; invent=false 2026-09-15; never remint / PATCH
        "a24c6896",  # Q10429 / Safe Cave H.6.38 Kyle UI Finish 2026-09-15 Contours PASS leftover — NumberOfContours=1 OPEN-NEW invent=false; never remint / PATCH
        "eb9a17c4",  # Q10475 / Safe Cave H.8.38 tip-prove EXEC_FAIL leftover — Contours=0; AddItem empty; meter thickness vs .1875; OPEN-NEW invent=false 2026-09-15; never remint / PATCH
        "d667c6f2",  # Q10476 / Safe Cave H.10.38 tip-prove inch-force EXEC_FAIL leftover — thickness stayed meter not PDF .1875 inch; Finish aborted invent=false OPEN-NEW 2026-09-15; never remint / PATCH
        "e0990112",  # Q10479 / Safe Cave H.10.38 tip-prove after PR68 leftover — inch 0.1875 stuck PROVED; Contours=0 AddItem empty body land-miss; OPEN-NEW invent=false 2026-09-15; never remint / PATCH
        "e7e4abd1",  # Q10480 / Safe Cave H.10.38 after PR68 leftover — inch 0.1875 PROVED; Contours=0 AddItem empty land-miss; OPEN-NEW invent=false 2026-09-15; never remint / PATCH
        "38fa25fc",  # prior burn Q10421→Q10407 drift leftover — full UUID not found in repo/logs/Dropbox; never remint / PATCH that UUID (do not forbid 35146-1 — PN remints remain ALLOWED)
        "d796cdbe",  # Q10407 Safe Cave List=[] leftover — never remint / PATCH
        "09bae33d",  # Q10408 Safe Cave List=[] leftover — never remint / PATCH
        "eb6c48b8",  # Q10350 / 21843-1 Time Waco Long/Linear PASS — Hot Rolled Round Bar Ø0.625 × 28.0843 Finish; invent=false; not a Contours leftover; bar/Linear path; never remint / PATCH
        "4902c597",  # Q10338 / CROSSDRAIN-12X7X60 PR18 Cad Image Files PASS (PL14 Ga-SS316 UC 100.45 Time Waco Laser Bay1) — post-pass bend-API dabble may show live UC 3.25; Finish snapshot UC 100.45 is PASS basis; never remint / PATCH
        "5e7bfc0b",  # H638-CADPLATE leftover — SetPartMode 0 + ProductType 100 Cad:1, InternalData empty, Finish refuse; ZZ-DEL-H638-CADPLATE — do not remint
        "e2683a3f",  # Q10334 leftover — kendo Cad/100 + 0.1875 in + Laser-Bay1, Contours empty; ZZ-DEL-Q10334 — do not remint
        "bcff1a24",  # Q10335 leftover — mouse UpdateItemType 200 Component→Cad, Contours 0 before Finish; QuoteItem_Read Data:[] lost CAD row before Finish; invented=false; ZZ-DEL-Q10335 — do not remint
        "ef865b0f",  # 15911-9 Time STEP leftover @ 62f7a92 — UpdateItemType Cad OK, InternalData empty, Finish refused invent=false; ZZ-DEL-15911-9 — do not remint
        "1994392f",  # 21839-1 Time STEP leftover @ bb4998a+ — UpdateItemType Cad OK, InternalData empty, full CadImport/Data+GetBorderSize+PartImage trail still empty, Finish refused invent=false; ZZ-DEL-21839-1 — do not remint
        "afee7458",  # GSB20570006 Sprout 1.1 leftover (CoS hold) — empty InternalData after full Cad+wizard mid-wizard (11 parts), Finish refused invent=false; outside H.6.38 / Time pick; ZZ-DEL-GSB20570006 — do not remint
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
        "1007578-1",  # spent 2db59f00 Cad Image Files PASS @ d96c096 — do not remint
        "1010110-1",  # spent cf656d2a Cad Image Files PASS @ d96c096 — do not remint
        "1004711-1",  # spent 50c6d543 Cad Image Files PASS @ 632c721 — do not remint
        "25009-1",  # spent aae055fe Cad Image Files PASS @ fc7344d — do not remint
        "25009-2",  # spent 46eed794 Cad Image Files PASS @ 72d7665 — do not remint
        "1010106-1",  # spent f300ecea Cad Image Files PASS @ 6289d3c — do not remint
        "1010111-1",  # spent 5dc50b55 Cad Image Files PASS @ 26bedc4 — do not remint
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
        "35136-1",  # spent 8973f890 Kyle STEP leftover — OpenContourCount=0 / 3× bar InternalData empty / AddItem_DXFFiles bar_flat empty — fail-close; do not remint
        "14327-5",  # spent c5cd8689 flat-plate STEP leftover @ 7b59ff0 — empty InternalData after /part/create; CadImport GET bindable=false; Finish refused; do not remint
        "14327-8",  # spent 1cd941c6 leftover @ 7b59ff0 — same empty-InternalData Contours FAIL as 14327-5; invented=false; ZZ-DEL-14327-8 — do not remint
        "Q10329",  # spent 75f07c2b / 14327-3 Contours UI leftover — Contours column absent; Finish never clicked; invented=false; ZZ-DEL-Q10329-14327-3-contours-ui — do not remint
        "14327-3",  # spent 75f07c2b Q10329 L-angle Contours UI leftover — Contours column absent; Finish never; do not remint
        "Q10330",  # spent aed89628 / 21841-1 Contours UI leftover — Contours column absent; Finish never clicked; invented=false; ZZ-DEL-Q10330-21841-1-contours-ui — do not remint
        "21841-1",  # spent aed89628 Q10330 angle/channel Contours UI leftover — Contours column absent; Finish never; do not remint
        "Q10331",  # spent 5e72fe39 / 14327-1 Contours UI leftover — Contours column absent; Finish never clicked; invented=false; ZZ-DEL-Q10331-14327-1-contours-ui — do not remint
        "14327-1",  # spent 5e72fe39 Q10331 flat-looking Contours UI leftover — Contours column absent; Finish never; do not remint
        "Q10332",  # spent wrong-org Time mint — renamed ZZ-DEL-wrong-org-Time; quote ID not restated in recent notes (repo / PR 18 / prior leftover transcript / Dropbox); description-only forbid; do not remint
        "ZZ-DEL-wrong-org-Time",  # Q10332 rename; quote ID unknown; do not remint
        "Q10333",  # spent b5f56ac3 / Safe Cave / H.6.38 Contours PASS — Cad / Contours=1 / 8 bends + Profile / Laser Bay1 / UC 176.96; never remint / PATCH / ZZ-DEL
        "Q10336",  # spent f73dd116 / Safe Cave / H.6.38 Cad+Laser Finish leftover — finished NumberOfContours=1 matches Q10333; OCC=0 expected; bends=8; Laser Bay1 / UC 64.25; never remint / PATCH / ZZ-DEL
        "Q10339",  # spent 76cecc73 / Safe Cave / H.6.38 Cad+Laser Finish leftover — finished NumberOfContours=1 matches Q10333; OCC=0 expected; Laser Bay1 / UC 64.25 / unit price 176.96; invented=false; never remint / PATCH / ZZ-DEL
        "Q10344",  # spent 55f12530 / Safe Cave / H.6.38 Kyle UI control PASS leftover — ProductType Cad + thickness 0.1875 inch → Contours fill → Finish; invent=false; never remint / PATCH / ZZ-DEL
        "Q10346",  # spent d859a239 / Safe Cave Sprout B80510901 Contours PASS (outside H.6.38) — ProductType Cad + thickness 0.0598 inch → Contours fill → Finish; invent=false; never remint / PATCH
        "B80510901",  # spent d859a239 Q10346 Sprout main plate Contours PASS (outside H.6.38) — Cad + 0.0598 inch → Contours fill → Finish; invent=false; never remint / PATCH
        "Q10348",  # spent 1defeed8 / Safe Cave H.16.70 Contours PASS (outside H.6.38) — ProductType Cad + thickness 0.1875 inch → Contours fill → Finish; invent=false; never remint / PATCH
        "H.16.70",  # spent 1defeed8 Q10348 Safe Cave H.16.70 Contours PASS (outside H.6.38) — Cad + 0.1875 inch → Contours fill → Finish; invent=false; never remint / PATCH
        "Q10349",  # spent c4394006 / Safe Cave D.H.30.96 Contours PASS (outside H.6.38) — ProductType Cad + thickness 0.1875 inch → Contours fill → Finish; invent=false; never remint / PATCH
        "D.H.30.96",  # spent c4394006 Q10349 Safe Cave D.H.30.96 Contours PASS (outside H.6.38) — Cad + 0.1875 inch → Contours fill → Finish; invent=false; never remint / PATCH
        "Q10351",  # spent 0c62fce9 / Safe Cave H.8.38 Contours PASS (outside H.6.38) — ProductType Cad + thickness inches → Contours fill → Finish; invent=false; never remint / PATCH
        "H.8.38",  # spent 0c62fce9 Q10351 Safe Cave H.8.38 Contours PASS (outside H.6.38) — Cad + inches → Contours fill → Finish; invent=false; never remint / PATCH
        "Q10354",  # spent 7881d4b3 / Safe Cave D.H.38.96 Contours FAIL leftover — Cad selector + 0.1875 in set, finished ProductType part; NumberOfContours unavailable / Contours PASS not proven; empty-InternalData Contours-FAIL class; invent=false; never remint / PATCH
        "D.H.38.96",  # spent 7881d4b3 Q10354 Safe Cave D.H.38.96 Contours FAIL leftover — Cad + 0.1875 in, finished ProductType part; NumberOfContours unavailable; not D.H.30.96 / Q10349 PASS; invent=false; never remint / PATCH
        "Q10356",  # spent 05bee105 / Safe Cave V.20.78 Contours FAIL leftover — Cad selector + 0.1875 in set, finished ProductType part; NumberOfContours missing / Contours PASS not proven; same Contours-FAIL class as Q10354 / D.H.38.96; invent=false; never remint / PATCH
        "V.20.78",  # spent 05bee105 Q10356 Safe Cave V.20.78 Contours FAIL leftover — Cad + 0.1875 in, finished ProductType part; NumberOfContours missing; not PASS; invent=false; never remint / PATCH
        "Q10365",  # spent 7801ab99 / Safe Cave H.10.38 Contours FAIL leftover — mouse Cad + 0.1875 in set, finished ProductType part; no Contours/InternalData fill; fill_xhr=null; same Contours-FAIL class as Q10354 / Q10356; invent=false; never remint / PATCH
        "H.10.38",  # spent 7801ab99 Q10365 Safe Cave H.10.38 Contours FAIL leftover — mouse Cad + 0.1875 in, finished ProductType part; no Contours/InternalData fill; fill_xhr=null; not PASS; invent=false; never remint / PATCH
        "Q10366",  # spent fd0b6e45 / Safe Cave / H.6.38 Contours PASS — invent=false; never remint / PATCH
        "H.6.38",  # spent fd0b6e45 Q10366 Safe Cave H.6.38 Contours PASS — invent=false; never remint / PATCH
        "Q10367",  # spent 4c9c25d4 / 10289-5 Contours PASS @ 6e8a2c3 — Cad+A36+0.1875→Finish; NumberOfContours=14; ProductType 100; invent=false; never remint / PATCH
        "10289-5",  # spent 4c9c25d4 Q10367 Contours PASS @ 6e8a2c3 — Cad+A36+0.1875→Finish; NumberOfContours=14; ProductType 100; invent=false; never remint / PATCH
        "Q10369",  # spent 82c28793 / 34328-1 Contours FAIL leftover — multi-kid Cad+Material+inches on one kid wiped #gridDXFParts; second kid Material/thickness blank → Contours=0 while configured kid Contours=1; invent=false; never remint / PATCH (do not forbid 34328-1 — PO may remint the PN)
        "Q10368",  # spent 5e0ce1df / 34328-1 Contours FAIL leftover @ 8d4626a — keep-grid Material worked; 3 Cad kids all A36 + thickness through Finish; Contours 0/1/0; PASS 34329 BOOM SUPPORT A36 0.25in Contours=1; FAIL two HOOK BOOM REST-7742_31454-1 A36 0.5in Contours=0; invent=false; never remint / PATCH (do not forbid 34328-1 — PO may remint the PN)
        "Q10371",  # spent 67472e72 / 34328-1 Contours FAIL leftover @ 22e327f — remint EXEC_FAIL; 31454-1 Contours=1 @0.5in; 34329 red thickness @0.25 Contours blocked (PR47 gate); invent=false; never remint / PATCH (do not forbid 34328-1 — PO may remint the PN)
        "Q10372",  # spent d62e2ad1 / 34328-1 Time weldment Contours remint EXEC_FAIL leftover @ d2616fc — invent=false; Complete Quote NOT DONE; HOOK 31454-1 Contours=0 (mistreated as A36/.50 plate; drawing=RD BAR CR 1018 1/2 DIA, not plate); 34329 Contours=1 at A36/.25 gauge-list; never remint / PATCH (do not forbid 34328-1 — PO may remint the PN)
        "Q10373",  # spent 523d8328 / 34328-1 Time weldment mixed classify PASS leftover @ 1650cf5 — invent=false; Complete Quote NOT DONE; OPEN-NEW draft; plate 34329 Cad A36 .25-1/4" gauge Laser NumberOfContours≥1; HOOK 31454-1 Long/Linear Hot Rolled Round Bar CRS (closest to RD BAR CR 1018) 0.5" × 4.375" Saw no Contours path; never remint / PATCH (do not forbid 34328-1 — PO may remint the PN)
        "Q10374",  # spent beb20d22 / 1008399-1 coverage remint FAIL-CLOSE leftover @ e604229 — STEP uploaded; plate 1008400 gauge unverified (no local drawing / SharePoint unreachable); invent=false stop before Contours; Complete Quote NOT DONE; never remint / PATCH (do not forbid 1008399-1 — PN remints remain ALLOWED)
        "Q10375",  # spent 60de939f / 1008399-1 remint EXEC_FAIL leftover @ 6a4f536 — Cad/A572 G50/.375-3/8 plate + Linear Saw bar + Component hardware set; Contours≥1 not verified (blank CAD editor); invent=false; Complete Quote NOT DONE; never remint / PATCH (do not forbid 1008399-1 — PN remints remain ALLOWED)
        "Q10377",  # spent 12bd2530 / 1008399-1 Time Boom Rest NEW remint PASS leftover @ 8f5d17c — invent=false; Complete Quote NOT DONE; Cad Contours + Long/Linear + Component; plate 1008400-1 Cad A572 G50 .375-3/8" NumberOfContours=1 (Finish→tree verify); bar 31454-1 Long/Linear Saw IsLinear=true; hardware 40003/40006 IsComponent=true; never remint / PATCH (do not forbid 1008399-1 — PN remints remain ALLOWED)
        "Q10379",  # spent 70e69d9c / 11643-1 Platform Mount NEW remint PASS leftover @ d34b5b4 — invent=false; Complete Quote NOT DONE; OPEN-NEW draft (CAD Finish ≠ Complete Quote); plate Cad Contours + tube/slug Long/Linear; plate 11640-1 Cad A572 G50 /.25 NumberOfContours=1; plate 11642-2 Cad A36 /.375 NumberOfContours=1; tube 11641-1 Long/Linear tube_round IsLinear A513 2.00×1.50×7.4375; slug 32070-1 Long/Linear bar_round IsLinear C1018 2.00×0.45; never remint / PATCH (do not forbid 11643-1 — PN remints remain ALLOWED)
        "Q10380",  # spent 754089f2 / 16630-1 Rotation Top Stop NEW remint PASS leftover @ 937b19c — invent=false; Complete Quote NOT DONE; OPEN-NEW draft (CAD Finish ≠ Complete Quote); plate Cad Contours + CT/ring Long/Linear; plate 16629-1 EAR Cad A36 /.5-1/2" NumberOfContours=1 qty 2; ring 16628-1 Long/Linear tube IsLinear A513 7.25 OD × 6.0 ID × 1.69 L wall 0.625 qty 1; never remint / PATCH (do not forbid 16630-1 — PN remints remain ALLOWED)
        "Q10381",  # spent bb31a132 / 1001093-1 Hose Guide NEW remint PASS leftover @ 6fefaac — invent=false; Complete Quote NOT DONE; OPEN-NEW draft (CAD Finish ≠ Complete Quote); 3 plate Cad Contours + RD BAR Long/Linear; plates 1000480/1001090/1001091 Cad A572 G50 /.1875-3/16 NumberOfContours=1 each; bar 1001092-1 Long/Linear IsLinear CRS/CR1018 .188 × 5.5625; never remint / PATCH (do not forbid 1001093-1 — PN remints remain ALLOWED)
        "Q10382",  # spent 2d42dcc3 / 35146-1 Jib Turret NEW remint PASS leftover @ 86906b7 — invent=false; Complete Quote NOT DONE; OPEN-NEW draft (CAD Finish ≠ Complete Quote); 2 plate Cad Contours + CT Long/Linear; plates 35123/.1875 DOMEX + 35125/10GA DOMEX NumberOfContours=1 each; tube 35124 Long/Linear IsLinear A513 4.25×3.75×6.25; never remint / PATCH (do not forbid 35146-1 — PN remints remain ALLOWED)
        "Q10383",  # spent 9d7cc06e / 21641-1 TIP SLEEVE remint EXEC_FAIL leftover @ f7e689d — invent=false; Complete Quote NOT DONE; OPEN-NEW leftover from 21641-1 TIP SLEEVE remint attempt 2026-09-14; Contours=0 all plate Cad kids after Finish; CadImport InternalData empty; PrimaryOrganizationID lost mid CAD wizard; kids not per-PN classified (all named 21641-1 @ 0.25); never remint / PATCH (do not forbid 21641-1 — PN remints remain ALLOWED)
        "Q10399",  # spent 039d8464 / 21641-1 hardened remint EXEC_FAIL leftover @ 6a26835 — invent=false; Complete Quote NOT DONE; OPEN-NEW leftover from hardened 21641 remint 2026-09-14; dig checklist gates 1–4 PASS; gate5 InternalData empty after explode refused AddItem_DXFFiles; Contours never filled; never remint / PATCH (do not forbid 21641-1 — PN remints remain ALLOWED)
        "Q10420",  # spent 4054443b / 35146-1 tip-prove EXEC_FAIL leftover @ c08c47b — invent=false; Complete Quote NOT DONE; OPEN-NEW leftover 2026-09-15; chrome_cdp skipped page Finish on empty InternalData despite tip refuse-relax (cad_material_inches_recipe_complete); Contours never filled; never remint / PATCH (do not forbid 35146-1 — PN remints remain ALLOWED)
        "Q10450",  # spent 1d59ef4a leftover after PR62 CDP prove — invent=false 2026-09-15; Contours never landed; live QN drifted toward forbid Q10408 label; OPEN-DRAFT; never remint / PATCH (do not forbid 35146-1 — PN remints remain ALLOWED)
        "Q10429",  # spent a24c6896 / Safe Cave H.6.38 Kyle UI Finish 2026-09-15 Contours PASS leftover — NumberOfContours=1 OPEN-NEW invent=false; never remint / PATCH (do not forbid H.6.38 — PN remints remain ALLOWED)
        "Q10475",  # spent eb9a17c4 / Safe Cave H.8.38 tip-prove EXEC_FAIL leftover — Contours=0; AddItem empty; meter thickness vs .1875; OPEN-NEW invent=false 2026-09-15; never remint / PATCH (do not forbid H.8.38 — PN remints remain ALLOWED)
        "Q10476",  # spent d667c6f2 / Safe Cave H.10.38 tip-prove inch-force EXEC_FAIL leftover — thickness stayed meter not PDF .1875 inch; Finish aborted invent=false OPEN-NEW 2026-09-15; never remint / PATCH (do not forbid H.10.38 — PN remints remain ALLOWED)
        "Q10479",  # spent e0990112 / Safe Cave H.10.38 tip-prove after PR68 leftover — inch 0.1875 stuck PROVED; Contours=0 AddItem empty body land-miss; OPEN-NEW invent=false 2026-09-15; never remint / PATCH (do not forbid H.10.38 — PN remints remain ALLOWED)
        "Q10480",  # spent e7e4abd1 / Safe Cave H.10.38 after PR68 leftover — inch 0.1875 PROVED; Contours=0 AddItem empty land-miss; OPEN-NEW invent=false 2026-09-15; never remint / PATCH (do not forbid H.10.38 — PN remints remain ALLOWED)
        "Q10470",  # spent H.8.38 remint leftover shell Contours=0 — UUID not found in live-H838-remint-kyle-path.txt / Dropbox / remint logs; description-only; never remint / PATCH; do not invent UUID or Contours (do not forbid H.8.38 — PN remints remain ALLOWED)
        "Q10471",  # spent H.8.38 remint leftover shell Contours=0 — UUID not found in live-H838-remint-kyle-path.txt / Dropbox / remint logs; description-only; never remint / PATCH; do not invent UUID or Contours (do not forbid H.8.38 — PN remints remain ALLOWED)
        "Q10472",  # spent H.8.38 remint leftover shell Contours=0 — UUID not found in live-H838-remint-kyle-path.txt / Dropbox / remint logs; description-only; never remint / PATCH; do not invent UUID or Contours (do not forbid H.8.38 — PN remints remain ALLOWED)
        "Q10473",  # spent H.8.38 remint leftover shell Contours=0 — UUID not found in live-H838-remint-kyle-path.txt / Dropbox / remint logs; description-only; never remint / PATCH; do not invent UUID or Contours (do not forbid H.8.38 — PN remints remain ALLOWED)
        "Q10474",  # spent H.8.38 remint leftover shell Contours=0 — UUID not found in live-H838-remint-kyle-path.txt / Dropbox / remint logs; description-only; never remint / PATCH; do not invent UUID or Contours (do not forbid H.8.38 — PN remints remain ALLOWED)
        "Q10421",  # spent 38fa25fc prior burn Q10421→Q10407 drift — full UUID not found in repo/logs; never remint / PATCH that UUID (do not forbid 35146-1 — PN remints remain ALLOWED)
        "Q10407",  # spent d796cdbe Safe Cave List=[] leftover — never remint / PATCH
        "Q10408",  # spent 09bae33d Safe Cave List=[] leftover — never remint / PATCH
        "Q10358",  # spent 34328-1 Time keep-grid prove leftover @ 4cc4481 — keep_grid_via=live, Cad×3, inches on kids, FileList InternalData empty after explode, Finish refused invent=false; ZZ-DEL-Q10358; ID unknown; description-only; do not remint Q10358 (do not forbid 34328-1 — PO may remint the PN)
        "Q10359",  # spent 34328-FFE Time CoS leftover @ ffe210e — keep_grid_via=live, Cad×3, inches-on-kids, re-GET CadImport/Data copied_n=0, InternalData empty 2/2, Finish refused invent=false; UpdateData/editor Done not a safe multi-kid fill; blocked-on-Sectura; ZZ-DEL-Q10359; ID unknown; description-only; do not remint Q10359 (do not forbid 34328-1)
        "Q10350",  # spent eb6c48b8 / 21843-1 Time Waco Long/Linear PASS — Hot Rolled Round Bar Ø0.625 × 28.0843 Finish; invent=false; not a Contours leftover; bar/Linear path; never remint / PATCH
        "21843-1",  # spent eb6c48b8 Q10350 Time Waco Long/Linear PASS — Hot Rolled Round Bar Ø0.625 × 28.0843 Finish; invent=false; not a Contours leftover; bar/Linear path; never remint / PATCH
        "Q10338",  # spent 4902c597 Cad Image Files PASS — AIM Cross Drain CROSSDRAIN-12X7X60 / Time Waco / PL14 Ga-SS316 / Finish UC 100.45 + PR laser pack; post-pass bend-API dabble may show live UC 3.25 — Finish snapshot is PASS basis; never remint / PATCH
        "CROSSDRAIN-12X7X60",  # spent 4902c597 Q10338 Cad Image Files PASS — do not remint
        "H638-CADPLATE",  # spent 5e7bfc0b Cad-for-plate leftover — SetPartMode 0 + ProductType 100 Cad:1, InternalData empty, Finish refuse; invented=false; ZZ-DEL-H638-CADPLATE — do not remint
        "ZZ-DEL-H638-CADPLATE",  # 5e7bfc0b H638-CADPLATE rename — do not remint
        "Q10334",  # spent e2683a3f Cad-for-plate leftover — Chrome kendo Cad/100 + 0.1875 in + Laser-Bay1, Contours empty; invented=false; ZZ-DEL-Q10334 — do not remint
        "ZZ-DEL-Q10334",  # e2683a3f Q10334 rename — do not remint
        "Q10335",  # spent bcff1a24 mouse UpdateItemType leftover — POST /Part/UpdateItemType 200 Component→Cad; /part/PartImage + /Quote/GetBorderSize on thickness; Contours 0 before Finish; QuoteItem_Read Data:[] lost CAD row before Finish; invented=false; ZZ-DEL-Q10335 — do not remint
        "ZZ-DEL-Q10335",  # bcff1a24 Q10335 rename — do not remint
        "28898-1",  # Time STEP explode leftover — UpdateItemType Cad OK, InternalData empty, Finish refused; ID unknown; description-only forbid; invented=false; do not remint
        "28772-1",  # Time STEP explode leftover — UpdateItemType Cad OK, InternalData empty, Finish refused; ID unknown; description-only forbid; invented=false; do not remint
        "14327-18",  # Time STEP explode leftover — UpdateItemType Cad OK, InternalData empty, Finish refused; ID unknown; description-only forbid; invented=false; do not remint
        "15911-9",  # Time STEP explode leftover @ 62f7a92 — UpdateItemType Cad OK, InternalData empty, Finish refused invent=false; ef865b0f-66d2-404e-bff2-9ed1e7bf00ea; CadImport/Data + PartImage + GetBorderSize not observed vs H.6.38; ZZ-DEL-15911-9 — do not remint
        "ZZ-DEL-15911-9",  # ef865b0f 15911-9 rename — do not remint
        "21839-1",  # Time STEP explode leftover @ bb4998a+ — UpdateItemType Cad OK, InternalData empty after explode, Finish refused invent=false; 1994392f-54a5-4245-80ee-a947fb07e3a7; full CadImport/Data+GetBorderSize+PartImage trail still empty; ZZ-DEL-21839-1 — do not remint
        "ZZ-DEL-21839-1",  # 1994392f 21839-1 rename — do not remint
        "GSB20570006",  # Sprout 1.1 leftover (CoS hold) @ 2f6d74f+ — empty InternalData after full Cad+wizard mid-wizard (11 parts), Finish refused invent=false; afee7458-6651-447e-ba1b-62c1c9c90ce8; Sectura-side empty-InternalData outside H.6.38 / Time pick; ZZ-DEL-GSB20570006 — do not remint
        "ZZ-DEL-GSB20570006",  # afee7458 GSB20570006 rename — do not remint
        # Do not remint 21785-1 / 21785-2 / 21785-3 / 35145-1 / Q10243 / P904272-1 / P904271-1 / 10289-4 / 10289-5 / 28768-1 / 28769-1 / 35136-1 / 14327-5 / 14327-8 / Q10329 / 14327-3 / Q10330 / 21841-1 / Q10331 / 14327-1 / Q10332 / Q10333 / Q10336 / Q10339 / Q10344 / Q10346 / B80510901 / Q10348 / H.16.70 / Q10349 / D.H.30.96 / Q10351 / H.8.38 / Q10354 / D.H.38.96 / Q10356 / V.20.78 / Q10365 / H.10.38 / Q10366 / H.6.38 / Q10367 / Q10369 / Q10368 / Q10371 / Q10372 / Q10373 / Q10374 / Q10375 / Q10377 / Q10379 / Q10380 / Q10381 / Q10382 / Q10383 / Q10399 / Q10420 / Q10450 / Q10429 / Q10475 / Q10476 / Q10479 / Q10480 / Q10470 / Q10471 / Q10472 / Q10473 / Q10474 / Q10421 / Q10407 / Q10408 / Q10358 / Q10359 / Q10350 / 21843-1 / Q10338 / CROSSDRAIN-12X7X60 / H638-CADPLATE / Q10334 / Q10335 / 28898-1 / 28772-1 / 14327-18 / 15911-9 / 21839-1 / GSB20570006.
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
