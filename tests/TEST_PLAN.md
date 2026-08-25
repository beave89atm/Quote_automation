# Time drawing regression plan

Quote Automation is the only production path. A new drop must not rediscover
bugs we already paid to lock. This suite is table-driven: **one fixture row
per drawing**, not a new code path.

No live Sectura quotes are written by these tests.

## Add a 12th Time weldment

1. Add one `LomGold` row in `tests/fixtures/time_gold.py` with the locked
   `(ITEM, QTY, PART NO)` list. Do not invent PNs.
2. If Kyle has a confirmed `*-LOM.xlsx`, copy it to
   `tests/fixtures/lom/{part_key}-LOM.xlsx`.
3. If classify/desc/org lessons apply, append one row to `CLASSIFY_CASES` /
   `DESC_CASES`.
4. Run `python3 -m tests.fixtures.time_gold` then
   `python3 -m pytest -q tests/test_time_regression_suite.py`.

Each gold test asserts the **set of (part_no, qty)** for dash -1, not just
`len()`. Wrong PN or wrong qty fails CI.

## Locked LOM gold (dash -1 unless noted)

| Drawing | Kyle bar | Fixture identity | Asserted |
|---|---|---|---|
| 102728-1 | 51 / 97 | **full 51-row set** (A=460200 … BB=102727-4×2) | exact `(PN, qty)` |
| 1004747-1 | 14 / 18 | **full 14-row set** | `-2` PNs 1004806-2 / 11694-2 / 25009-2 omitted; title `1004747` uses -1 |
| 28106-1 | 11 / 13 | **full 11-row set** | P/N/L other-dash only |
| 1007922-1 | 6 / 14 | **full 6-row set** | 21750-2 / 21743-2 / 73207 omitted |
| 21727-1 | 11 / 16 | **full 11-row set** | 61358 omitted |
| 33612-1 | 21 / 47 | **named 4**: A 28275-1×1, P 28273-2×4, U 33638-1×4, W 8121-2×4 | 56657 / 97879 omitted. Remaining 17 PNs were not listed |
| 105098-1 | 9 / 9 | **named 2**: A 103603-1 MAIN PLATFORM, H 105097-1 | later-sheet 103603-1 child table ignored |
| 103516 | 27 / 45 | **named 2**: item 20 103535-1×1, item 27 40002-2×1 | empty `103535-1` tab → empty L2. Remaining 25 PNs were not listed |
| P904225-1 | 11 / 23 | **full 11-row set** | header `P904225-1` is not a material row; 89176-1 omitted |
| 1004611-1 | 22 / 66 + 10″ gasket | **named 2**: A 1004611-DWG×1, S S80054-1×1 | V 1004620-2 / U 1004675-1 omitted. Remaining 20 PNs were not listed |
| 1001898-1 | 17 / 27 | **full 17-row set** | other-dash omitted; `20 PLCS` ≠ qty |

Zero count-only / dummy `PN-01` fixtures. Incomplete drawings are identity-locked
on the PNs Kyle named; they are not padded.

Also: prefer existing `*-LOM.xlsx`; empty clip ≠ 1 pc; job 91 `xl/xl` OPC path.

## Classify / push classes (no live Sectura)

| Class | Drawing | Asserted |
|---|---|---|
| PDF no-STEP weldment | 1001898-1 | 5 Cad / 5 Linear / 7 Component; Time org; `1001898-1 - PEDESTAL WELDMENT`; no sheet flats; `attach_profile=False`; no bare PN |
| PDF plate Image Files | 21667-1 | 10×9 × 3/8 100K from drawing math, not 22×28 outline; no graft |
| PDF linear Long | 12689-1 / 12368-2 | ProductID + RCT SKU; decimal-inch length; Machine=Saw; ProductType 10 |
| STEP weldment | 21676-1 / 21678-1 | cookie → Finish; no cookie → Finish skipped, no graft; hose guard = Linear |
| Nested LOM | 103516 / empty-l2 | empty L2 shell noted; MAIN PLATFORM child table not rolled up |
| 1004747 dash trap | 1004747 | bare/`-1` title wins over `-2` folder |

Kyle formats: Cad `{PN} - {thk}" {grade} {W} in x {L} in`; Linear `{PN} - {SKU} - {length}`; Component name only; Assembly `{PN} - {title}`.

## Not on this VM

Kyle Desktop / Fort Worth `*-LOM.xlsx` were not reachable
(`C:\Users\Kyle\OneDrive - Kannon Manufacturing Inc\Desktop`,
`C:\Users\Kyle\Desktop`, Fort Worth Time library). Drop a real sheet onto
`tests/fixtures/lom/{pn}-LOM.xlsx` to replace a list-built fixture.

## Commands

```
python3 -m tests.fixtures.time_gold
python3 -m pytest -q tests/test_time_regression_suite.py
python3 -m pytest -q
```

Full suite must stay green. `tests/test_ocr.py::test_ocr_skips_when_native_text_rich` is skipped when Tesseract is missing.
