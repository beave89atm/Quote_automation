# Bend-line conventions

The detector loads `quote_core/bend_conventions.yaml`. Each bend it accepts cites the convention id that matched. High-confidence signals can set the count. Medium signals count only when they agree with that count. Low-confidence signals and conflicts stop the quote with `FLAG: bend count — <reason>`. Nothing is guessed.

## STEP wins

A STEP file is the bend count and the flat pattern for that part. SecturaFAB unfolds the STEP, and that result is what the quote uses.

Reading bends off the PDF is only a fallback for a PDF-only quote: no usable STEP for that part. If a STEP is present, the PDF reader does not run. Its flags do not run either. It does not replace the STEP bend count, it does not replace the STEP flat pattern, and it does not stop the quote. A PDF count that does not match the STEP can be written in the notes as a warning. That warning is not a flag and it does not block the push. The push does not run the reader just to make that note. The STEP count comes from SecturaFAB after the file is unfolded, and the PDF is not consulted for it.

## What changed for a real drawing

These are the rules the reader uses now.

- `UP 90° R.13` and `DOWN 90° R 1/8` are bend notes. The degree sign is read. `R.13` is 0.13 in, `R .25` is 0.25 in, and `R 3/8` is 3/8 in. The angle comes from that note. A tolerance, a chamfer, or a REF angle on another line is not the bend angle.
- A hole centerline or a symmetry centerline is not a bend. Geometry can only agree with a bend the text already named. It cannot add a bend, cancel one, or by itself say the part is not flat.
- `1/4 BEND RADIUS` is a radius, not 4 bends. `-1 BEND` and `-2 BEND` are dash labels. When both are on the sheet they are separate options, not one combined count. `(BEND LINE)` on a dimension is not a bend. `BEND ANGLE = 90°` and `ANGULAR: BEND 1°` are title-block notes. `MASTER CYLINDER` is a part name, not a rolled cylinder.
- A scanned page, or a page whose text comes out as one character per line, is `FLAG: drawing text — unreadable, needs human review`. It does not go through as a flat plate.
- A radius is read from the same line as the bend note. A dimension on the next line is not the radius.
- A bend note written vertically is still one plane. Rotated text is not a second bend direction. `HORIZONTAL BEND` and `VERTICAL BEND` still mean two planes. Bend notes that sit on lines about 90° apart are two planes, even when extra hole centerlines are on the sheet. Parallel bend lines stay one plane. A short even dash is a bend line when a note sits on it. Notes on two of those directions are `bends in two planes, review`. The count and a printed blank can be written in the note. The part is not pushed.
- If the drawing prints a flat size on a FLAT PATTERN, FLAT, or DEVELOPED view, that size is the blank only when it is clearly that view's overall size. A chamfer, a thread, a tolerance, or a pair like `3/8 X 45°` is never the blank. The size also has to make sense next to the thickness and the part's other dimensions, and a sheet or plate blank over 120 in is not used. A short side of about 1 in is still the blank when the dimension matches the part outline and the sheet scale. The older 1 in check stays for a CAD page outline such as 1×2 or 1×16 that was not measured on the part. The view is the part outline above the FLAT PATTERN label, not the sheet frame. An overall is two collinear dimension halves with an arrowhead at each outer end, or one unbroken line with an arrowhead at both ends. The tip-to-tip distance is the size, and the two sides have to share the sheet scale. Dimension text is horizontal even on a vertical dimension. A stacked fraction (a whole number, with the numerator over the denominator and a fraction-bar line between them) is one size. The push path reads each PDF span, so the whole number and the numerator stay separate when they share a line. REF or TYP next to that overall is still the blank. Title-block, revision-block, and general-notes numbers are not the blank. A FLAT PATTERN label on a page with no dimension arrows is `template wording only, review`. If the size is not clear, the quote flags and does not push. The line note says `source drawing flat pattern` when the size is used. Kyle's formula (K = 0.33 from shop config) runs only when that view was not printed and the legs, thickness, and radius are all readable.
- An unclear angle or an ambiguous radius is checked before a printed size is accepted. A missing angle or radius does not throw away a size that already passed those checks.
- If the text shows a formed part (a FLAT PATTERN view that has a size or a bend note next to it, a bend note, the word FORMED, or a formed view) and the bend count is 0 or unknown, the quote flags. It is never pushed as a flat plate. A blank title-block line that only says `FLAT PATTERN VIEW`, with nothing next to it, does not make a flat plate into a formed part. Template wording alone (`FLAT PATTERN VIEW` next to a stray number, or `ALL ANGULAR DIMENSIONS 90°` with no bend note) is `template wording only, review`. That is not a claim that the part is formed.
- `CLR`, `centerline radius`, a degree mark next to a tube leg, the word BEND with an OD or wall callout, or a tube bend table (angle, rotation, and length) means the tube or bar is formed. An `R` with a decimal counts only together with tube, OD, wall, or CLR text, or when the stock is over 1 in (or a diameter over 1 in) and the sheet has no flat-pattern view. A corner radius on a flat plate does not, even when a 1.000 dimension is on the sheet. The quote flags a formed tube. It is not a straight cut. `ANGULAR: BEND` in the title block is not that signal.

`detect_bends(text, drawings)` is unchanged. An optional `text_blocks` argument can carry each PDF span's `text`, `dir`, and `bbox`. The push path keeps one block per span so a stacked fraction is not joined into one line. The direction the note is written does not change the bend plane. A centerline counts only when one of those notes sits on it. Notes sitting on lines about 90° apart are not one plane. Short-dash lines count the same way when a note sits on them.

The flat length is not a bend count. On a PDF-only quote, a printed flat size wins over the formula. When the part has a STEP, the STEP flat pattern wins and this reader does not replace it. The formula in `secturafab/flat_formula.py` is the PDF-only fallback when the sheet did not print a clear blank. See `docs/flat_pattern_formulas.md`. K is `materials.flat_pattern_k_factor` in `config/shop_rates.yaml` (0.33).

## What is text-only

These are read from the PDF text layer. PyMuPDF's text extract is the input. The patterns are in the yaml file.

| Id | Confidence | What it matches |
| --- | --- | --- |
| `explicit_n_bends` | high | `3 BENDS`, `1 BEND`. Not `1/4 BEND RADIUS`, not `-1 BEND`, and not a decimal such as `6.00`. |
| `explicit_n_bend_lines` | high | `3 BEND LINES` |
| `callout_bend_up_down` | high | `BEND UP` / `BEND DOWN`, with an optional angle and `R` radius (`R.13`, `R .25`, `R 1/8`, `R1.5`, `R1,5`) |
| `callout_sw_up_angle_radius` | high | SolidWorks-style note with no word BEND: `UP 90° R.13`, `DOWN 90° R 1/8`, or `UP 90°` |
| `label_bend_line` | high | Each `BEND LINE` label. `(BEND LINE)` on a dimension is not a bend. Not used when an explicit `N BEND LINES` already gave the count. |
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
| `fp_title_bend_angle` | ignore | `BEND ANGLE = 90°` and `ANGULAR: BEND 1°`. Title-block and tolerance notes. |

`2 X 2` tube stock is not a multiplier. The `2X` pattern runs only on a line that already has a bend callout.

## What is geometry-aware

`plan_pdf_only_file` also reads vector strokes with PyMuPDF `page.get_drawings()`. The dash array is on the stroke. The PDF does not keep the CAD layer name.

| Id | Dash array | Meaning |
| --- | --- | --- |
| `geom_center_line` | four numbers, long then short (`[12 3 2 3]`) | Centerline style. A stroke at least 1 inch long can corroborate a text bend. It cannot create one. |
| `geom_phantom_line` | six numbers, long then two shorts (`[12 2 2 2 2 2]`) | Phantom style. Same rule. |
| `geom_perpendicular_families` | two of those directions about 90° apart | Not a single plane when those lines are the bends, or when bend notes sit on two directions about 90° apart. Extra hole centerlines do not trip this. Rotated note text does not. |

A short centerline is treated as a hole mark and ignored. A short even dash (`[4 2]`) is not a bend line by itself. It counts when a bend note sits on it. Two of those directions about 90° apart are `bends in two planes, review`.

Geometry does not set the count. If the long center or phantom lines are parallel and the number equals the text count, each bend cites `geom_center_line` or `geom_phantom_line` as corroboration. If the numbers disagree, the text count stands. Hole centerlines and symmetry centerlines are not bend evidence. When PDF text positions are available, a line counts only if a bend note sits on it.

## Sources

- SOLIDWORKS bend table columns are inner radii, angles, directions, and tags. Bend notes and a bend table are not both placed. [SOLIDWORKS Help, Bend Tables (2019)](https://help.solidworks.com/2019/english/SolidWorks/sldworks/c_bend_tables.htm).
- The default flat-pattern note is direction, angle, and radius, from `bendnoteformat.txt` (`<bend-direction> <bend-angle> R<bend-radius>`), which prints like `UP 90° R3`. [SOLIDWORKS bend note formatting](https://www.cati.com/blog/solidworks-bend-note-formatting/) and [CADMES on bendnoteformat.txt](https://support.cadmes.com/fr/personnalisation-du-texte-des-notes-de-pliage). Up and down bend lines are separate drawing styles. [SOLIDWORKS sheet metal document properties](https://my.solidworks.com/reader/onlinehelp/2021%252Fenglish%252Fswconnected%252Fswdotworks%252Fhidd_options_sheetmetal_dpp.htm/document-properties-sheet-metal).
- Inventor drawing bend tables default to Bend ID, Bend Direction, Bend Angle, and Bend Radius. Bend K-factor is an optional column. Bend notes sit on bend centerlines. [Inventor API](https://help.autodesk.com/cloudhelp/2024/ENU/Inventor-API/files/CustomTables_AddBendTableWithOptions.htm) and [Inventor sheet metal annotations](https://help.autodesk.com/cloudhelp/2023/ENU/Inventor-Help/files/GUID-29BEB900-C220-49DB-B11D-4F69DEC211E7.htm).
- ASME Y14.2-2014 defines hidden lines (short even dashes), center lines (long dash, short dash), and phantom lines (long dash, two short dashes). Phantom lines in that standard are alternate positions, reference parts, and repeated detail. They are not defined there as sheet-metal bend lines. [ASME Y14.2-2014](https://www.asme.org/codes-standards/find-codes-standards/y14-2-line-conventions-lettering/2014).
- ASME Y14.5 is the dimensioning standard behind `2X` and `N PLACES`. It does not define a bend count. A degree dimension on a formed view can be a bend, a chamfer, or a countersink. Chamfer and countersink lines are masked before angles are read.
- `BREAK SHARP EDGES` removes a burr. It is not a bend. [GD&T Basics](https://www.gdandtbasics.com/break-edges-note/). Countersink angles such as 82° and 90° are hole seats, not press-brake bends. [Machinist Guides](https://www.machinistguides.com/chamfers/).
- Bends whose axes are not parallel are not one developed strip. [Xometry sheet metal guide](https://cdn2.hubspot.net/hubfs/340051/Design_Guides/Xometry_DesignGuide_SheetMetal.pdf) tells designers to keep bends in the same plane.

## Flat pattern after the count

If the drawing prints the blank on a FLAT PATTERN, FLAT, or DEVELOPED view, that pair is the flat size when it is the view's overall size. The line note says `source drawing flat pattern`. An inline pair is used in the order printed. Separate overalls are the tip-to-tip dimensions on the outline above that label. A stacked fraction is one of those dimensions, and REF or TYP beside it still counts. A number in the title block, the revision block, or the general notes is not. A blank over 120 in is not used. A chamfer, thread, tolerance, or `N X` angle is not the blank. If that size is not clear, the quote flags.

Kyle's formula is the fallback, and only when the legs, the thickness, and the radius are all readable. K is 0.33 from shop config unless that setting changes. For N bends in one plane, with N+1 dimensioned legs:

- Inside dimensions are not converted. The quote flags.
- Outside or mold-line: flat length = sum of legs − N × bend deduction.
- Tangent lengths: flat length = sum of legs + N × bend allowance.
- Bend allowance = (π × θ / 180) × (inside radius + K × thickness).
- At 90°, bend deduction = 2 × (inside radius + thickness) − bend allowance.

Hems, jogs that are not dimensioned, a missing radius, an ambiguous inside/outside note, bends that are not in one plane, and a formed part whose bend count is 0 or unknown all flag. They do not become a flat plate. A scanned or unreadable page flags the same way.
