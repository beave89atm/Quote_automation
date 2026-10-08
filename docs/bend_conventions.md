# Bend-line conventions

The detector loads `quote_core/bend_conventions.yaml`. Each bend it accepts cites the convention id that matched. High-confidence signals can set the count. Medium signals count only when they agree with that count. Low-confidence signals and conflicts stop the quote with `FLAG: bend count — <reason>`. Nothing is guessed.

The flat length is not a bend count. It comes from `secturafab/flat_formula.py`. See `docs/flat_pattern_formulas.md`. K is `materials.flat_pattern_k_factor` in `config/shop_rates.yaml` (0.33).

## What is text-only

These are read from the PDF text layer. PyMuPDF's text extract is the input. The patterns are in the yaml file.

| Id | Confidence | What it matches |
| --- | --- | --- |
| `explicit_n_bends` | high | `3 BENDS`, `1 BEND`. A decimal such as `6.00` on the previous line is not a count. |
| `explicit_n_bend_lines` | high | `3 BEND LINES` |
| `callout_bend_up_down` | high | `BEND UP` / `BEND DOWN`, with an optional angle and `R` radius (`R.06`, `R1.5`, `R1,5`) |
| `callout_sw_up_angle_radius` | high | SolidWorks-style note with no word BEND: `UP 90° R.06` |
| `label_bend_line` | high | Each `BEND LINE` label. Not used when an explicit `N BEND LINES` already gave the count. |
| `table_row_direction` | high | One bend-table data row: id, `UP`/`DOWN`, angle. Headers are not rows. |
| `multiplier_nx` | high | `2X` or `3X` on the same line as a bend callout |
| `multiplier_n_places` | high | `2 PLACES` on the same line as a bend callout |
| `note_all_bends` | medium | `ALL BENDS …` shares a radius or angle and does not set a count |
| `low_bare_up_down` | low | Bare `UP` or `DOWN` |
| `low_bare_angle` | low | A degree dimension or `∠` with no count |
| `low_bend_radius` | low | `INSIDE RADIUS`, `BEND RADIUS`, or `IR` |
| `low_formed_word` | low | `FORMED` |
| `low_press_brake` | low | `PRESS BRAKE` |
| `low_bend_word` | low | Bare `BEND` |
| `low_formed_views` | low | Two or more named views and no bend count |
| `not_single_plane_note` | high | `COMPOUND BEND`, `TWO PLANES`, `NOT A SINGLE PLANE` |
| `axis_horizontal_bend` + `axis_vertical_bend` | high | Both directions named. The part is not one plane. |
| `fp_break_sharp_edges` | ignore | `BREAK SHARP EDGES`, `DEBURR`. Not a bend. |
| `fp_chamfer_countersink` | ignore | `CHAMFER`, `COUNTERSINK`, `CSK`. A 45° or 82° on that line is not a bend angle. |
| `fp_bendable_title` | ignore | `BENDABLE`, `BENDER`, `UNBEND` |

`2 X 2` tube stock is not a multiplier. The `2X` pattern runs only on a line that already has a bend callout.

## What is geometry-aware

`plan_pdf_only_file` also reads vector strokes with PyMuPDF `page.get_drawings()`. The dash array is on the stroke. The PDF does not keep the CAD layer name.

| Id | Dash array | Meaning |
| --- | --- | --- |
| `geom_center_line` | four numbers, long then short (`[12 3 2 3]`) | Centerline style. Counted only if the stroke is at least 1 inch long. |
| `geom_phantom_line` | six numbers, long then two shorts (`[12 2 2 2 2 2]`) | Phantom style. Same length rule. |
| `geom_perpendicular_families` | two of those directions about 90° apart | Not a single plane. |

Solid strokes and hidden-line dashes (`[4 2]`, short even dashes) are not bend lines. A short centerline is treated as a hole mark and ignored.

Geometry does not set the count by itself. If the long center or phantom lines are parallel and the number equals the text count, each bend cites `geom_center_line` or `geom_phantom_line` as corroboration. If the numbers disagree, the result is `FLAG: bend count — signals conflict`. If the lines are the only evidence, the result is `FLAG: bend count — center or phantom lines are not a bend count without a callout`.

## Sources

- SOLIDWORKS bend table columns are inner radii, angles, directions, and tags. Bend notes and a bend table are not both placed. [SOLIDWORKS Help, Bend Tables (2019)](https://help.solidworks.com/2019/english/SolidWorks/sldworks/c_bend_tables.htm).
- The default flat-pattern note is direction, angle, and radius, from `bendnoteformat.txt` (`<bend-direction> <bend-angle> R<bend-radius>`), which prints like `UP 90° R3`. [SOLIDWORKS bend note formatting](https://www.cati.com/blog/solidworks-bend-note-formatting/) and [CADMES on bendnoteformat.txt](https://support.cadmes.com/fr/personnalisation-du-texte-des-notes-de-pliage). Up and down bend lines are separate drawing styles. [SOLIDWORKS sheet metal document properties](https://my.solidworks.com/reader/onlinehelp/2021%252Fenglish%252Fswconnected%252Fswdotworks%252Fhidd_options_sheetmetal_dpp.htm/document-properties-sheet-metal).
- Inventor drawing bend tables default to Bend ID, Bend Direction, Bend Angle, and Bend Radius. Bend K-factor is an optional column. Bend notes sit on bend centerlines. [Inventor API](https://help.autodesk.com/cloudhelp/2024/ENU/Inventor-API/files/CustomTables_AddBendTableWithOptions.htm) and [Inventor sheet metal annotations](https://help.autodesk.com/cloudhelp/2023/ENU/Inventor-Help/files/GUID-29BEB900-C220-49DB-B11D-4F69DEC211E7.htm).
- ASME Y14.2-2014 defines hidden lines (short even dashes), center lines (long dash, short dash), and phantom lines (long dash, two short dashes). Phantom lines in that standard are alternate positions, reference parts, and repeated detail. They are not defined there as sheet-metal bend lines. [ASME Y14.2-2014](https://www.asme.org/codes-standards/find-codes-standards/y14-2-line-conventions-lettering/2014).
- ASME Y14.5 is the dimensioning standard behind `2X` and `N PLACES`. It does not define a bend count. A degree dimension on a formed view can be a bend, a chamfer, or a countersink. Chamfer and countersink lines are masked before angles are read.
- `BREAK SHARP EDGES` removes a burr. It is not a bend. [GD&T Basics](https://www.gdandtbasics.com/break-edges-note/). Countersink angles such as 82° and 90° are hole seats, not press-brake bends. [Machinist Guides](https://www.machinistguides.com/chamfers/).
- Bends whose axes are not parallel are not one developed strip. [Xometry sheet metal guide](https://cdn2.hubspot.net/hubfs/340051/Design_Guides/Xometry_DesignGuide_SheetMetal.pdf) tells designers to keep bends in the same plane.

## Flat pattern after the count

For N 90° bends in one plane, with N+1 dimensioned legs and one inside radius:

- Inside dimensions: flat length = sum of legs + N × bend allowance.
- Outside or mold-line: flat length = sum of legs − N × bend deduction.
- 90° bend allowance = (π/2) × (inside radius + K × thickness) when the chart method is `k`.
- Bend deduction = 2 × (inside radius + thickness) − bend allowance.

The chart row supplies K, the allowance, or the deduction. There is no default K. Hems, jogs, non-90° angles, a missing radius, an ambiguous inside/outside/mold-line note, no chart row, more than one chart row, and bends that are not in one plane flag and do not develop a flat.
