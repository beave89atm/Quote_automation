# Rule — Nested child LIST OF MATERIAL from the drawing library

- **Date:** 2026-08-21
- **Applies when:** A parent LOM **DESCRIPTION** is a weldment or assembly (example: 103516 item 20 **103535-1 GATE WELDMENT**)
- **Does not apply when:** The description is a piece part (`TUBE, ROUND`, `PLATE`). Later-sheet child tables on the **same** PDF are still not this job’s BOM (105098-1 vs 103603-1).

Kyle still drops **only the top-level file**. Recurse on children. Extra upload only if the child is not in Fort Worth Engineering Customer Drawings.

## Encode into automation

1. After a real LIST OF MATERIAL is clipped to `{stem}-LOM.xlsx` and re-read as the quote BOM, scan parent rows.
2. If **DESCRIPTION** matches weldment / assembly / assy, look up that **PART NO** in Customer Drawings (`drawing_library.roots` / `KANNON_DRAWING_LIBRARY`).
3. Copy the child PDF into the **job** folder (never write into the library). Clip that child’s LOM as an **extra tab** on the parent `{stem}-LOM.xlsx` (example: tab `103535-1` on `103516-LOM.xlsx`). Do **not** emit a separate `{child}-LOM.xlsx`. Child `bom_config` is blank — do not inherit the parent dash.
4. Recurse when a child LOM row is itself a weldment or assembly — each nested LOM is another tab on the **same** parent workbook.
5. If the child drawing is missing: flag `extra upload needed`. Do not invent parent rows.
6. **Do not merge** child LOM rows onto the parent LIST OF MATERIAL tab. 103516 stays 27 PN / 45 pcs with **103535-1** as one parent line.
7. When the quote is imported into SecturaFAB, **every BOM tab** on that workbook must be included so weldment-in-weldment cost is complete.
8. Do not drop LOM.xlsx-as-takeoff or the 102728-1 97-pc qty path. Quote takeoff is still the first tab only.

## Example

| Parent item | Part | Description | Action |
| --- | --- | --- | --- |
| 20 | 103535-1 | GATE WELDMENT | Retrieve `Time/103535-1` and add tab `103535-1` on the parent LOM.xlsx |
| 27 | 40002-2 | *(blank / hardware)* | Leave as a parent line |

## Proof

Synthetic fixtures in `tests/test_nested_lom.py`. No customer PDFs in git.
