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
