# Lesson 04 — Entering weldment components from PDFs (no STEP)

- **Date:** 2026-08-03
- **Loom:** https://www.loom.com/share/a4faf8f706c24388bf6b3742558a17bc
- **Transcript file:** `04-Entering-Weldment-Components-from-PDFs.txt`
- **Example job:** Time **28106-1** Lower Boom Weldment (multi-option BOM; quote the **-1** column)
- **Applies when:** Weldment / assembly quote with **no STEP** — each child comes from a component PDF
- **Does not apply when:** Full assembly STEP is available (use lesson 02 / `quickAddCAD` STEP path)

> Note: This Loom ID was also used earlier for lesson 01 (bend ops). The **transcript file above** is the weldment PDF walkthrough (28106 components). If the Loom page title still shows bend ops, trust the transcript / this lesson for the no-STEP assembly path.

## Goal

Build a SecturaFAB **Assembly** (top-level weldment) by adding every BOM component from its PDF, setting material / thickness / qty / size (or Linear stock), then rolling each line under the top-level weldment.

## Steps (from Kyle’s transcript)

1. Work in a quote that already has the **top-level weldment** (assembly) started — **no STEP**.
2. Open **Image Files** and drop the next component **PDF** from the shared drawing folder.
3. Walk the **Bill of Materials** (correct dash column, e.g. **-1**) and add each missing component.
4. For each PDF part:
   - Confirm **Product Type**:
     - Purchased hardware → **Component**
     - Plate / flat laser → **Cad** (Image/plate path)
     - Tube / round bar / long stock → **Linear**
   - Set **thickness** and **material** from the drawing (example: **1/4"** + **A572 Grade 50**, or **A36**).
   - Set **quantity** from the BOM (example: **2** of 15864-2).
   - Set the **part name / dash** correctly (example: **15864-2** — dashes are different configs).
   - Enter **length × width** (and **holes** if shown) from the drawing when the image import does not fill them.
   - Click **New Line Item**.
5. Roll the new line into the assembly:
   - Open the **top-level weldment** → **Edit Properties**
   - Move / copy the new component **under** the assembly
   - Click **Update Assembly**
   - (OK to batch this at the end instead of after every line.)
6. **Linear example (pivot tube 15863):** use Long / Linear, match stock (DOM / RT / OD / wall), set **length** and qty **1**. Machining ops can be added later.
7. Continue until every BOM row for that dash is on the quote and under the assembly.

## Key values from this example (28106-1)

| Item | Qty (-1) | Part No. | Description |
| --- | --- | --- | --- |
| A | 1 | 16697-2 | LOWER BOOM TUBE 91 1/8 LG. |
| B | 1 | 26732-1 | CYLINDER MOUNT PLATE W/ 3/8 HOLES |
| C | 1 | 26732-2 | CYLINDER MOUNT PLATE |
| D | 1 | 15644-1 | STIFFENER, CYLINDER MOUNT |
| E | 1 | 16694-1 | STIFFENER, CUTOUT |
| F | 1 | 15890-1 | END CAP, BOOM |
| G | **2** | 15891-1 | HOSE GUARD |
| H | 1 | 10187-1 | HOSE RETAINER |
| J | **2** | 15864-2 | STIFFENER, BOOM PIVOT |
| K | 1 | 15863-1 | PIVOT TUBE, LOWER BOOM |
| M | 1 | 15654-1 | STIFFENER PLATE |

**11 unique part numbers · 13 pieces** (G and J at qty 2). Other boom tubes (16697-1/3/4) are for dashes -2/-3/-4 only.


## Shop rules to remember

- **No STEP** → **Image Files** + component PDFs, not CAD STEP import.
- Always use the correct **BOM dash column** (-1 / -2 / …).
- Part name must include the **dash** when the drawing has one.
- **Cad** = laser plate; **Linear** = tube/bar; **Component** = purchased.
- After **New Line Item**, the part is **not** in the weldment until **Update Assembly**.
- Material grades matter (A36 vs A572 GR50) — read each component PDF.
- Tube machining can wait until after the structure is built.

## Encode into automation?

- [x] Yes — BOM dash config on upload (`bom_config` / title `28106-1`)
- [x] Yes — when no STP, push imports BOM component PDFs and links under Assembly (`secturafab/pdf_assembly_ops.py`)
- [x] Yes — purchased → Component; per-PDF material/thickness when readable
- [ ] Later — full Linear stock picker (DOM / RT / wall) from tube drawings
- [ ] Later — hole dims + machining ops from PDF
- Notes: API uses `quickAddCAD` with PDFs (same plate geometry result as Image Files for many plates). Assembly link matches **Update Assembly**. Review Linear tubes / missed OCR BOM rows before accepting.

## Screenshots

- (optional) `screens/04-*.png`

## Transcript

Full captions: `04-Entering-Weldment-Components-from-PDFs.txt`.
