# Lesson 01 — Basic quoting and bend operations

- **Date:** 2026-08-03
- **Loom:** https://www.loom.com/share/a4faf8f706c24388bf6b3742558a17bc
- **Transcript file:** `01-basic-bend-ops.srt.txt`
- **Video file (optional):** `videos/01-basic-bend-ops.mp4`
- **Applies when:** PDF/drawing-only plate quote (no STEP); simple formed part with bends on the drawing; **no welding** on this part
- **Does not apply when:** STEP/CAD import (preferred path — software reads dimensions); weldments / parts that need weld ops

## Goal

Create a SecturaFAB quote from a drawing: part number as quote number, material/qty, flat pattern size, Profile (laser), then Bend with shop times (and a second operator when the part is long).

## Steps (from Kyle’s transcript)

1. **New Quote**.
2. Upload files: **STEP preferred** (CAD files). If no STEP, use **Image files** and drop the **PDF**.
3. Without STEP, fill everything manually from the drawing.
4. Set **thickness** and **material** from the drawing (example: **22 gauge**, **GALV / galvanized**).
5. Enter **quantity** (example: **24**).
6. Copy the **part number** from the drawing into the **quote number** (always = part number; easier to find later).
7. Fill the **description** from the drawing (engineers sometimes put dims in the description instead of a name).
8. **Length × width** = **flat pattern** dims only (example: **85.42 × 7.78** in). Not formed size.
9. Add **holes** only if the drawing has them (example: none).
10. Click next — confirm Profile = laser cut.
11. Add **Bend** operation: count bends from flat-pattern **dotted lines** (or formed views) — example: **2 bends**.
12. If the part is **over ~4 ft long**, add a **second bend operator** (two people).
13. For a long part (~85 in): about **90 seconds per bend**; **30 min setup** is fine.
14. Add the operation. Material cost comes later.

## Key values from this example

| Field | Value |
| --- | --- |
| Quote number | Part number from drawing |
| Material / thickness | GALV, 22 gauge |
| Qty | 24 |
| Flat size (L × W) | 85.42 × 7.78 in |
| Holes | None |
| Primary op | Profile (laser) |
| Bend count | 2 |
| Bend operators | 2 (because part &gt; 4 ft) |
| Bend time | ~90 sec / bend |
| Bend setup | 30 min |
| Welding | **None** — this part has no weld ops |

## Shop rules to remember

- Quote number **always** = part number.
- STEP first; PDF/image only when no STEP.
- Length/width = **flat pattern**, inches.
- Profile = laser.
- Bend count from dotted lines on flat pattern.
- Long parts (&gt; ~4 ft): second bend operator + slower time per bend.
- This example has **no welding** — stop after Profile + Bend (+ material cost later). Do not add weld ops.

## Encode into automation?

- [x] Yes — partially (when we build PDF-only / no-STEP quote path)
- [ ] Full auto for bend count/time — needs drawing read of flat pattern + bend lines
- Notes: Aligns with existing “PN = quote number” and “STEP preferred” push rules. Bend timing and 2nd operator rules are new for a future PDF-only path.

## Screenshots

- (optional) drop under `screens/01-*.png`

## Transcript

Full captions are in `01-basic-bend-ops.srt.txt` (saved from Loom via Notepad).
