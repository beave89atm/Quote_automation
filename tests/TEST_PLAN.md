# Time drawing regression plan

Quote Automation is the only production path. A new drop must not rediscover
bugs we already paid to lock. This suite is table-driven: **one fixture row
per drawing**, not a new code path.

No live Sectura quotes are written by these tests.

## Add a 12th Time weldment

1. Add one `LomGold` row in `tests/fixtures/time_gold.py` (PN/pcs, title, dash).
2. If Kyle has a confirmed `*-LOM.xlsx`, copy it to
   `tests/fixtures/lom/{part_key}-LOM.xlsx` (replace the count-locked sheet).
3. If classify/desc/org lessons apply, append one row to `CLASSIFY_CASES` /
   `DESC_CASES`.
4. Run `python3 -m tests.fixtures.time_gold` (or the suite — it rebuilds
   generated workbooks) then `python3 -m pytest -q tests/test_time_regression_suite.py`.

## Locked LOM gold (dash -1 unless noted)

| Drawing | PN / pcs | Fixture | Asserted |
|---|---|---|---|
| 102728-1 | 51 / 97 | count-locked xlsx | dash -1; empty/`-` omitted |
| 1004747-1 | 14 / 18 | count-locked xlsx | title `1004747` or `1004747-1` uses **-1**, never folder `-2` |
| 28106-1 | 11 / 13 | count-locked xlsx | dash -1 |
| 1007922-1 | 6 / 14 | count-locked xlsx | Desktop sheet not on this VM — replace when available |
| 21727-1 | 11 / 16 | count-locked xlsx | same |
| 33612-1 | 21 / 47 | count-locked xlsx | same |
| 105098-1 | 9 / 9 | count-locked + ignored `103603-1` tab | **parent LOM only** |
| 103516 | 27 / 45 | count-locked + `103535-1` GATE WELDMENT tab | nested children roll up; empty L2 is flagged |
| P904225-1 | 11 / 23 | count-locked xlsx | `P904225-1` letter-prefix PN ok |
| 1004611-1 | 22 / 66 | count-locked + `S 80054-1` 10″ gasket | gasket line present |
| 1001898-1 | 17 / 27 | **locked rows** (live GET / Desktop LOM) | other-dash letters omitted; `20 PLCS` paint ≠ qty |

Also: prefer existing `*-LOM.xlsx`; empty clip ≠ 1 pc; job 91 `xl/xl` OPC path.

## Classify / push classes (no live Sectura)

| Class | Drawing | Asserted |
|---|---|---|
| PDF no-STEP weldment | 1001898-1 | 5 Cad / 5 Linear / 7 Component; Time org; `1001898-1 - PEDESTAL WELDMENT`; no sheet flats; `attach_profile=False`; no bare PN |
| PDF plate Image Files | 21667-1 | 10×9 × 3/8 100K from drawing math, not 22×28 outline; no graft |
| PDF linear Long | 12689-1 / 12368-2 | ProductID + RCT SKU; decimal-inch length; Machine=Saw; ProductType 10 |
| STEP weldment | 21676-1 / 21678-1 | cookie → Finish; no cookie → Finish skipped, no graft; hose guard = Linear |
| Nested LOM | 103516 / empty-l2 | children roll up; empty L2 shell noted |
| 1004747 dash trap | 1004747 | bare/`-1` title wins over `-2` folder |

Kyle formats: Cad `{PN} - {thk}" {grade} {W} in x {L} in`; Linear `{PN} - {SKU} - {length}`; Component name only; Assembly `{PN} - {title}`.

## Not on this VM (replace later)

Kyle Desktop / Fort Worth `*-LOM.xlsx` for 1007922-1, 21727-1, 33612-1, 105098-1, 103516, P904225-1, 1004611-1. Count-locked workbooks protect the **parser and dash rules** until those files are copied in. 1001898-1 is the only locked **part identity** list.

## Commands

```
python3 -m pytest -q tests/test_time_regression_suite.py
python3 -m pytest -q
```

Full suite must stay green except `tests/test_ocr.py::test_ocr_skips_when_native_text_rich` when Tesseract is missing.
