"""Exact DevTools capture Kyle must grab for STEP Finish Contours.

No live ``/part/create`` ``t.List`` has yet arrived with nonempty
InternalData **and** ImageString. Leftover STEPs (35136-1 / 28769-1 /
21785-2 / 14327-5 / 14327-8 / 14327-3 / 21841-1 / 14327-1)
were keys-present / values-empty. Q10333 / H.6.38 / b5f56ac3 is a
Contours PASS protect (Cad / Contours=1 / 8 bends + Profile /
Laser Bay1 / UC 176.96) — never remint / PATCH / ZZ-DEL. Q10336 /
f73dd116 and Q10339 / 76cecc73 Cad→Finish leftovers match Q10333
finished Contours (NumberOfContours=1 / OCC=0 expected / bends=8)
— protect; soft-pass labels were stage notes. Q10344 / 55f12530
is the Kyle UI control leftover (Cad + 0.1875 inch → Contours
fill → Finish) — never remint / PATCH / ZZ-DEL. invent=false.
Q10346 / d859a239 / B80510901 Sprout main plate is a Contours PASS
outside H.6.38 (Cad + 0.0598 inch → Contours fill → Finish) —
never remint / PATCH. invent=false. Q10348 / 1defeed8 / H.16.70
Safe Cave is a Contours PASS outside H.6.38 (Cad + 0.1875 inch →
Contours fill → Finish) — never remint / PATCH. invent=false.
Q10349 / c4394006 / D.H.30.96 Safe Cave is a Contours PASS
outside H.6.38 (Cad + 0.1875 inch → Contours fill → Finish) —
never remint / PATCH. invent=false.
Q10351 / 0c62fce9 / H.8.38 Safe Cave is a Contours PASS
outside H.6.38 (Cad + inches → Contours fill → Finish) —
never remint / PATCH. invent=false.
Q10354 / 7881d4b3 / D.H.38.96 Safe Cave is a Contours FAIL
leftover (Cad + 0.1875 in set, finished ProductType part;
NumberOfContours unavailable / Contours PASS not proven) —
same empty-InternalData Contours-FAIL class as Q10334 / Q10335.
Never remint / PATCH. invent=false. Not Q10349 / D.H.30.96 PASS.
Q10356 / 05bee105 / V.20.78 Safe Cave is a Contours FAIL
leftover (Cad + 0.1875 in set, finished ProductType part;
NumberOfContours missing / Contours PASS not proven) —
same Contours-FAIL class as Q10354 / D.H.38.96.
Never remint / PATCH. invent=false.
Q10365 / 7801ab99 / H.10.38 Safe Cave is a Contours FAIL
leftover (mouse Cad + 0.1875 in set, finished ProductType part;
no Contours/InternalData fill; fill_xhr=null) —
same Contours-FAIL class as Q10354 / Q10356.
Never remint / PATCH. invent=false.
Q10359 / 34328-FFE CoS leftover (tip ffe210e): keep-grid live +
Cad+inches + copied_n=0 InternalData empty → EXEC_FAIL. UpdateData /
editor Done is not a safe multi-kid fill. Never remint / PATCH.
invent=false. Do not forbid 34328-1.
Q10368 / 5e0ce1df / 34328-1 remint (tip 8d4626a): keep-grid
Material worked; Contours 0/1/0 after Cad+A36+inches. Never remint
Q10368. Do not forbid 34328-1. invent=false.
Q10372 / d62e2ad1 / 34328-1 remint (tip d2616fc): EXEC_FAIL;
Complete Quote NOT DONE. HOOK 31454-1 Contours=0 (RD BAR CR 1018
1/2 DIA, not A36/.50 plate); 34329 Contours=1 at A36/.25.
Contours≥1 Laser gate is plate/sheet Cad; RD BAR Contours=0 with
Material+thickness set is expected until Profile/Saw/bar path
exists. invent=false. Never remint Q10372. Do not forbid 34328-1.
Q10373 / 523d8328 / 34328-1 remint (tip 1650cf5): mixed classify
PASS leftover. Complete Quote NOT DONE. OPEN-NEW draft.
Plate 34329 Cad A36 .25-1/4" gauge Laser NumberOfContours≥1.
HOOK 31454-1 Long/Linear Hot Rolled Round Bar CRS (closest to
RD BAR CR 1018) 0.5" × 4.375" Saw; no Contours path.
invent=false. Never remint Q10373. Do not forbid 34328-1.
Q10374 / beb20d22 / 1008399-1 coverage remint (tip e604229):
FAIL-CLOSE leftover. STEP uploaded; plate 1008400 gauge
unverified (no local drawing / SharePoint unreachable).
invent=false stop before Contours. Complete Quote NOT DONE.
Never remint Q10374. Do not forbid 1008399-1.
Q10375 / 60de939f / 1008399-1 remint (tip 6a4f536):
EXEC_FAIL leftover. Cad/A572 G50/.375-3/8 plate + Linear
Saw bar + Component hardware set. Contours≥1 not verified
(blank CAD editor). invent=false. Complete Quote NOT DONE.
Never remint Q10375. Do not forbid 1008399-1.
Q10377 / 12bd2530 / 1008399-1 remint (tip 8f5d17c): mixed
classify PASS leftover. Complete Quote NOT DONE.
Cad Contours + Long/Linear + Component. Plate 1008400-1
Cad A572 G50 .375-3/8" NumberOfContours=1 (Finish→tree
verify). Bar 31454-1 Long/Linear Saw IsLinear=true.
Hardware 40003/40006 IsComponent=true. invent=false.
Never remint Q10377. Do not forbid 1008399-1.
Q10379 / 70e69d9c / 11643-1 remint (tip d34b5b4): mixed
classify PASS leftover. Complete Quote NOT DONE.
OPEN-NEW draft (CAD Finish ≠ Complete Quote).
Plate Cad Contours + tube/slug
Long/Linear. Plate 11640-1 Cad A572 G50 /.25
NumberOfContours=1. Plate 11642-2 Cad A36 /.375
NumberOfContours=1. Tube 11641-1 Long/Linear tube_round
IsLinear A513 2.00×1.50×7.4375. Slug 32070-1 Long/Linear
bar_round IsLinear C1018 2.00×0.45. invent=false.
Never remint Q10379. Do not forbid 11643-1.
Q10380 / 754089f2 / 16630-1 remint (tip 937b19c): mixed
classify PASS leftover. Complete Quote NOT DONE.
OPEN-NEW draft (CAD Finish ≠ Complete Quote).
Plate Cad Contours + CT/ring Long/Linear. Plate 16629-1
EAR Cad A36 /.5-1/2" NumberOfContours=1 qty 2. Ring
16628-1 Long/Linear tube IsLinear A513 7.25 OD × 6.0 ID
× 1.69 L wall 0.625 qty 1. invent=false.
Never remint Q10380. Do not forbid 16630-1.
Q10381 / bb31a132 / 1001093-1 remint (tip 6fefaac): mixed
classify PASS leftover. Complete Quote NOT DONE.
OPEN-NEW draft (CAD Finish ≠ Complete Quote).
3 plate Cad Contours + RD BAR Long/Linear. Plates
1000480/1001090/1001091 Cad A572 G50 /.1875-3/16
NumberOfContours=1 each. Bar 1001092-1 Long/Linear
IsLinear CRS/CR1018 .188 × 5.5625. invent=false.
Never remint Q10381. Do not forbid 1001093-1.
Q10382 / 2d42dcc3 / 35146-1 remint (tip 86906b7): mixed
classify PASS leftover. Complete Quote NOT DONE.
OPEN-NEW draft (CAD Finish ≠ Complete Quote).
2 plate Cad Contours + CT Long/Linear. Plates
35123/.1875 DOMEX + 35125/10GA DOMEX NumberOfContours=1
each. Tube 35124 Long/Linear IsLinear A513 4.25×3.75×6.25.
invent=false.
Never remint Q10382. Do not forbid 35146-1.
Q10383 / 9d7cc06e / 21641-1 remint (tip f7e689d):
EXEC_FAIL leftover. Complete Quote NOT DONE.
OPEN-NEW leftover from 21641-1 TIP SLEEVE remint
attempt 2026-09-14. Contours=0 all plate Cad kids
after Finish. CadImport InternalData empty.
PrimaryOrganizationID lost mid CAD wizard. Kids
not per-PN classified (all named 21641-1 @ 0.25).
invent=false.
Never remint Q10383. Do not forbid 21641-1.
Q10399 / 039d8464 / 21641-1 remint (tip 6a26835):
EXEC_FAIL leftover. Complete Quote NOT DONE.
OPEN-NEW leftover from hardened 21641 remint
2026-09-14. Dig checklist gates 1–4 PASS. Gate5
InternalData empty after explode refused
AddItem_DXFFiles. Contours never filled.
invent=false.
Never remint Q10399. Do not forbid 21641-1.
Q10420 / 4054443b / 35146-1 remint (tip c08c47b):
EXEC_FAIL leftover. Complete Quote NOT DONE.
OPEN-NEW leftover from tip-prove 35146 remint
2026-09-15. chrome_cdp skipped page Finish on empty
InternalData despite tip refuse-relax
(cad_material_inches_recipe_complete). Contours never
filled. invent=false.
Never remint Q10420. Do not forbid 35146-1.
Q10407 / d796cdbe Safe Cave List=[] leftover.
Never remint Q10407.
Q10408 / 09bae33d Safe Cave List=[] leftover.
Never remint Q10408.
Do not gate unlock
on OCC≥1. Kyle HAR leftover
35136-1 / 8973f890: Upload → CadImport/Data OpenContourCount=0 →
/part/create 3× bar InternalData empty → AddItem_DXFFiles InternalData
empty bar_flat. Live 14327-5 / c5cd8689 flat plate: /part/create n=1
InternalData empty, ImageString preview-only, ProductType null,
CadImport Data/CADData bindable=false, OpenContourCount empty/null.
QuoteOrderEdit ``createAllParts`` has no intervening CadImport/UI XHR.
Exact missing call: ``POST /part/create t.List InternalData+ImageString``.
Contours never filled. Alternate-path hunt (UpdateData / Data / CADData /
ConvertTo / Unfold / ``/part/PartImage`` / PDFGetData) is exhausted —
see ``step_contours_fill_hunt``. Unlock remains Kyle Contours≥1 capture
or Sectura support naming the fill. Do not invent Contours. Plate
matches bar — no silent graft.

Kyle Loom: Component→Cad on Adjust Properties is required for plate
STEP Contours (Q10333 / H.6.38 Safe Cave PASS: Cad / Contours=1 /
8 bends + Profile / Laser Bay1 / UC 176.96 — never remint / PATCH /
ZZ-DEL). Automation sets Cad via API/kendo
ProductType=100 + SetPartMode 0 plus POST /Part/UpdateItemType
ItemType=Cad (Q10335 mouse dropdown classify XHR), not a UI click.
Cad classify ≠ Contours fill (H638-CADPLATE / 5e7bfc0b, Q10334 /
e2683a3f, Q10335 / bcff1a24 Contours 0; QuoteItem_Read Data:[]
lost CAD row before Finish — ZZ-DEL). Still fail-close if Contours
empty. UpdateItemType is classify; Contours fill may still need
Finish or further calls.

On a **fresh unused** Time STEP whose green Finish shows Contours
(GET ``DataPartPDF.NumberOfContours`` ≥ 1), save the windows below —
key names and emptiness bools only. Never remint spent leftovers.
"""

from __future__ import annotations

from typing import Any

from secturafab.website import kyle_step_contours_devtools_capture

# Spent leftovers — do not remint / PATCH. Capture must be a new PN.
STEP_CONTOURS_CAPTURE_NEVER_REMINT = (
    "35136-1",
    "14327-5",
    "14327-8",
    "Q10329",
    "14327-3",
    "Q10330",
    "21841-1",
    "Q10331",
    "14327-1",
    "Q10332",
    "Q10333",
    "Q10336",
    "Q10339",
    "Q10344",
    "Q10346",
    "B80510901",
    "Q10348",
    "H.16.70",
    "Q10349",
    "D.H.30.96",
    "Q10351",
    "H.8.38",
    "Q10354",
    "D.H.38.96",
    "Q10356",
    "V.20.78",
    "Q10365",
    "H.10.38",
    "Q10358",
    "Q10359",
    "Q10368",
    "Q10372",
    "Q10373",
    "Q10374",
    "Q10375",
    "Q10377",
    "Q10379",
    "Q10380",
    "Q10381",
    "Q10382",
    "Q10383",
    "Q10399",
    "Q10420",
    "Q10407",
    "Q10408",
    "H638-CADPLATE",
    "Q10334",
    "Q10335",
    "28898-1",
    "28772-1",
    "14327-18",
    "15911-9",
    "21839-1",
    "GSB20570006",
    "28769-1",
    "28768-1",
    "10289-4",
    "P904271-1",
    "P904272-1",
    "21785-1",
    "21785-2",
    "21785-3",
    "35145-1",
    "11796-1",
)

# Bind source we still need: POST /part/create t.List with both fields nonempty.
STEP_CONTOURS_EXPECTED_BIND = {
    "method": "POST",
    "path": "/part/create",
    "bindable_when": "InternalData nonempty AND ImageString nonempty",
}


def step_contours_kyle_capture() -> dict[str, Any]:
    """Read-only recipe. Same contract as kyle_step_contours_devtools_capture."""
    recipe = kyle_step_contours_devtools_capture()
    recipe["never_remint"] = list(STEP_CONTOURS_CAPTURE_NEVER_REMINT)
    recipe["expected_bind"] = dict(STEP_CONTOURS_EXPECTED_BIND)
    return recipe
