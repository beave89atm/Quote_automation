# Flat pattern formulas

Kyle's sheet-metal guide, built into `secturafab/flat_formula.py`. The bend count still comes from `quote_core/bend_conventions.yaml`. This page is only the flat length.

If the drawing prints a flat size on a FLAT PATTERN, FLAT, or DEVELOPED view, that size is the blank when it is clearly that view's overall size. A chamfer, thread, tolerance, or degree pair is not the blank. The view is the part outline above the FLAT PATTERN label, not the sheet frame. An overall is two collinear halves with an arrowhead on each outer end, or one unbroken line with an arrowhead on both ends. The tip-to-tip distance is the size, and both sides share the sheet scale. Dimension text stays horizontal, including on a vertical dimension. A stacked fraction with a fraction-bar line is one size. REF or TYP beside that overall is still the blank. Title-block numbers are not the blank, and a sheet or plate side over 120 in is not used. The line note says `source drawing flat pattern`, and this formula does not run. The formula is the fallback when that view was not printed and the legs, thickness, and radius are all readable. If a flat view is printed and the size is not clear, the quote flags and this formula does not run.

K is `materials.flat_pattern_k_factor` in `config/shop_rates.yaml`. The shop setting is **0.33**. Every formed line note says `K=0.33 assumed` (or the configured value, if that setting is changed).

T is thickness in inches. R is the inside bend radius after forming, in inches. θ is the change in direction from flat, in degrees. An included angle of 135° is θ = 45° (θ = 180 − included).

```
BA   = (π × θ / 180) × (R + K × T)
OSSB = (R + T) × tan(θ / 2)
BD   = 2 × OSSB − BA
```

At 90°, tan(θ / 2) = 1, so OSSB = R + T and BD = 2(R + T) − (π / 2) × (R + K × T).

- Tangent lengths: flat length = sum of the tangent segments + sum of BA.
- Outside sharp corners (outside or mold-line dimensions): flat length = sum of the outside segments − sum of BD.
- Each bend uses its own R, T, θ, and K. Up and down bends both count. They are not cancelled.
- The math keeps full precision. The line note shows six decimal places.

The flat width is the width on the drawing. Parallel bends on a constant-width part make a rectangular blank. That width and the flat length go on the Image Files line. The bend count is `NumberOfBends` in the line note. Nothing captured in this repo writes that operation field.

## Worked checks

One 90° bend, outside legs 2.000 and 3.000, T = 0.125, R = 0.125, K = 0.33:

- BA = 0.261145
- OSSB = 0.250000
- BD = 0.238855
- flat length = 4.761145

Four identical 90° bends, outside chain total 12.000, same T, R, and K:

- total BD = 0.955420
- flat length = 11.044580 (11.045 to three decimals)

## FLAG before a flat is calculated

- Hem or folded edge, including a 180° bend
- Rolled or large-radius section
- Cone or cylinder
- Compound or stretched form
- Bend lines that are not parallel, not in one plane, or a box that needs a 2D unfold
- Inside dimensions, or a mix of inside / tangent / outside, when they cannot be converted confidently. BD is never applied to an unconverted chain
- Angle convention not determined (a bare angle that is not 90°, or included and bend angles that disagree)
- Bend with no stated angle
- Missing or ambiguous inside radius. An ambiguous radius is flagged even when a flat size is also printed. A missing radius does not block a flat size that is already clear.
- Printed flat size that is a chamfer, angle, thread, tolerance, or not a clear overall on the flat-pattern view
- Tube or round-stock bend notes (`CLR`, centerline radius, a bend table of angle, rotation, and length, or a large `R` on stock over 1 in with no flat-pattern view)
- Offset or joggle when both bends and the connecting straight are not dimensioned

An offset or joggle is calculated when both bends and the connecting straight are dimensioned. Any stated bend angle is allowed. A missing angle is not.
