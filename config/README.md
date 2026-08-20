# Shop configuration

## `shop_capabilities.yaml`

In-house equipment + outsourced processes from Kyle’s July 2026 capabilities
doc. Used to propose operations and to always list **tube laser** and
**powder coating** (vendor times are placeholders). Mill/lathe times stay
parked.

## `shop_rates.yaml`

Fill these before trusting quote times:

| Field | Meaning |
|-------|---------|
| `app.shared_password` | Team login for the web app (v1) |
| `app.default_efficiency_pct` | Office/shop efficiency applied to quoted time |
| `weld.ipm` | **Manual** weld effective inches/minute by fillet size |
| `weld.process` | `manual` for now; robot rates TBD |
| `fitup.weight_bands` | Minutes per **piece** by weight band (`per_piece_minutes`) |
| `fitup.default_band_id` | Band used when component weights are unknown |
| `always_ask` | Situations the engine must flag instead of guessing |
| `drawing_library.roots` | Shared-drive folders to search for STP / component PDFs. Weldment mode: drop only the top-level weldment; the app finds BOM children + STP here. Loose-piece batch still auto-attaches that part’s STP only. |
| `drawing_library.auto_attach_stp` | If true, auto-copy matching STP when upload has none. Do not disable for v1. |

Set `KANNON_DRAWING_LIBRARY` to override roots (semicolon-separated) on each office PC.

### Fit-up formula

```
fitup_minutes = sum(per_piece_minutes[band(unit_weight_i)] for each physical piece i)
```

BOM **QTY** is expanded: a part number with qty 2 and weight 37.9 lb contributes two 37.9 lb pieces.

| Piece weight | With fixture | Without fixture |
|------------------|-------------:|----------------:|
| <20 lb | 2 min | 4 min |
| 20–50 lb | 4 min | 6 min |
| 50–200 lb | 7 min | 10 min |
| >200 lb | 10 min | 15 min |

Quoted weld + fit-up time is then divided by `efficiency_pct / 100`.

Piece weights priority:
1. **PDF BOM** rows (`ITEM` / `QTY` / `WEIGHT` lbm) — unit weight per piece × qty
2. Else **calculate**: net area (sq in − holes/cutouts) × lb/ft² from thickness × grade (× STP qty)
3. Open sections without a profile table still use a bbox fill-factor estimate (flagged)

Override weights on the job screen if needed. For true CAD mass, use FreeCAD / SolidWorks mass properties.

### Example

Pieces 12.4, 37.9, 120.4 lb with fixture:

```
fitup = 2 + 4 + 7 = 13 minutes
```
