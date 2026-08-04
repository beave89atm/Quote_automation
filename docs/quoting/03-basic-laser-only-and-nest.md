# Lesson 03 — Basic laser-only plate + nest / remnant

- **Date:** 2026-08-03
- **Loom:** *(paste link if available)*
- **Transcript file:** `03-basic-laser-only-and-nest.txt`
- **Video file (optional):** `videos/03-basic-laser-only-and-nest.mp4`
- **Applies when:** PDF/drawing-only plate; **laser cut only** (no bends, no weld); nesting and remnant decision matter
- **Does not apply when:** STEP import; formed parts (bends); weldments / assemblies

## Goal

Quote a simple laser-only plate from a PDF: material/thickness/qty/flat size, Profile only, set customer, then nest and decide **Keep Remnant** vs charging the whole sheet.

## Steps (from Kyle’s transcript)

1. **New Quote**.
2. No STEP — open **Image Files** and drag-drop the **PDF**.
3. Laser-only part: **no bends** (transcript ASR: “bins”), no weld.
4. Read dimensions from the drawing:
   - Thickness **5/8"**
   - Length **2.88"** × width **2.5"**
5. **Quantity:** **192**.
6. **Material:** **A572 Grade 50** (not A36 — denser/harder).
7. Quote number = **part number** from the drawing (always).
8. **Description** from drawing (example: **lift log gusset** — even if the title block text is long).
9. **Holes:** none on this drawing — leave blank.
10. Set **customer** via Existing Organization (example: **American Completion Tools**).
11. Click **New Line Item** so the line actually appears (qty, material cost placeholder).
12. Material **unit cost** often needs a manual update (online lookup today; Cursor should do this later).
13. Open the part → **Nest** → **Nest item** to see how many fit on a sheet.
14. Remnant rule:
    - Small % of sheet + material used often → check **Keep Remnant**.
    - Large % of sheet → may charge the customer for the **entire** sheet → uncheck Keep Remnant (“KeepRAM off”).
15. **Stop here for automation for now** — nest + Keep Remnant is the far edge Cursor should reach on this path.

## Key values from this example

| Field | Value |
| --- | --- |
| Quote number | Part number from drawing |
| Customer | American Completion Tools |
| Description | Lift log gusset |
| Material / thickness | A572 GR50, 5/8 in |
| Qty | 192 |
| Flat size (L × W) | 2.88 × 2.5 in |
| Holes | None |
| Primary op | Profile (laser) |
| Bend / weld | **None** |
| Nest | Nest item — maximize pieces on sheet |
| Keep Remnant | **On** (common stock, small footprint) |

## Shop rules to remember

- Quote number **always** = part number.
- PDF/image path when there is **no STEP**.
- Laser-only → Profile only; do not add Bend or Weld.
- Grade 50 ≠ A36 — pick the correct denser stock.
- Line item does not exist until **New Line Item** is clicked.
- Nest to judge sheet usage before pricing remnant.
- **Keep Remnant on** = shop keeps leftover (common material, small part).
- **Keep Remnant off** = customer may pay for the whole sheet (large footprint).
- Material $/lb (or sheet cost) lookup is a future Cursor task — not required at this lesson’s stop point.

## Encode into automation?

- [ ] Yes — PDF-only laser plate path (dims, material, qty, PN, description, Profile)
- [ ] Yes — later: material cost lookup from grade/thickness
- [ ] Yes — later: nest + Keep Remnant heuristic (sheet fill % + “common stock”)
- [x] Reference only for now — Kyle’s stop line: “as far as I want Cursor to take it right now” = through Keep Remnant decision, not beyond
- Notes: Complements lesson 01 (PDF + bends). This lesson has **no bends**. Nest/remnant is new shop logic not yet in API push.

## Screenshots

- (optional) drop under `screens/03-*.png`

## Transcript

Full captions are in `03-basic-laser-only-and-nest.txt` (saved from Loom).
