# Lesson 02 — 73476004 manual STEP quote + weld from Cursor

- **Date:** 2026-08-03
- **Loom:** https://www.loom.com/share/81175a9876f54256986876e8c16ca8ab
- **Transcript file:** `02-73476004-manual-quote-with-adding-weld-time-from-cursor.srt.txt`
- **Part:** 73476004 (same assembly the API just pushed)
- **Applies when:** Quoting an assembly from **STEP**; verifying each line from component PDFs; adding **Weld** from Quote Automation times
- **Does not apply when:** PDF-only / no STEP (see lesson 01)

## Goal

Import STEP → **root line = Assembly** (components roll up) → classify each child (Cad / Linear / Component) → fix material & thickness from drawings → finish → add **Weld** on the assembly using Cursor weld + fit-up minutes.

## Steps (from Kyle’s transcript)

1. **New Quote** → **CAD files** (STEP path, not Image/PDF).
2. Drag/drop the STEP. Keep **component drawings** open on a second screen to verify material & thickness.
3. **Root / top row = Assembly** (category Assembly, not Part/plate). Child qtys roll up with assembly qty (example: set assembly to 10 → children scale). Description is the **part number only** — not plate L×W.
4. For each **component** solid (not the assembly root):
   - **Sheet/plate (laser)** → set category to **Cad**. Confirm thickness (often 3/16 already correct). Confirm material vs PDF (**A36** may show oddly; Grade 50 → **A572 Grade 50**).
   - Red thickness warning → re-pick the same thickness (e.g. 3/16) to clear it.
   - **Angle with holes** → **Linear**; pick stock (e.g. **L 3×3×3/16 A36**). Length comes from STEP.
   - **Purchased part** (kingpin — not made in-house) → leave **Component**.
5. **Finish** import — assembly + components appear; qtys follow assembly multiplier.
6. **Weld is not auto-added.** Add Weld on the **assembly** line (secondary ops), not on a plate child.
7. Enter times from Cursor Quote Automation:
   - Weld time ≈ **200.5 minutes** (from app).
   - Fit-up **with fixture** ≈ **35 minutes**.
   - Leave weld setup at **15** (as shown).
8. **Add operation**.

## Shop rules to remember

- Quote header **Description** = title from the **top-level assembly drawing** (e.g. `COUPLER ASM, 18-16, PNEUMATIC TANK`), not blank.
- All fabricatable / purchased components **roll up** under that assembly.
- STEP preferred; verify **per-line** material/thickness from PDFs (don’t trust a single assembly-wide guess).
- **Cad** = laser plate/sheet; **Linear** = angle/tube/bar stock; **Component** = purchased / not fabricated in-house.
- **King pins and hardware** are purchased (~99%) → always **Component** (no laser Profile / Bend).
- **Tube laser** parts are often **outsourced** (flag for later; ERP will help identify buy vs make).
- Angle inventory names start with **L** (looks like the angle).
- Assembly qty multiplies all children.
- **Weld** is a manual secondary op on the **assembly**, fed by Cursor minutes (weld + fit-up).

## Gaps vs current API push

| Manual (this video) | API push |
| --- | --- |
| Root = **Assembly** (bare PN, no plate dims) | `ensure_assembly_root` |
| Children roll up under parent (assembly editor right pane) | `_attach_children` / `relink_assembly_children` (`AssemblyID`, Level 2) |
| Kingpin / hardware = **Component** (buy) | `ensure_purchased_components` (PDF title / BOM / name hints) |
| Per-part Cad / Linear | Linear still weak |
| Per-part material (A36 vs A572 GR50) | From component PDFs on push |
| Linear angle → L 3×3×3/16 stock | Not mapped to inventory shape |
| Weld on assembly from Cursor | `weld_ops` |
| Profile on Cad children only | `profile_ops` (skips Assembly + Component) |

## Encode into automation?

- [x] Yes — root line = **Assembly** (`secturafab/assembly_ops.py`)
- [x] Yes — attach children under assembly (`AssemblyID` / Level 2; re-link after Component convert)
- [x] Yes — purchased king pin / hardware = **Component** (`secturafab/component_ops.py`)
- [x] Yes — push **Weld** (+ fit-up with fixture) from job times onto the assembly line
- [x] Yes — per-part material/thickness from component PDFs
- [ ] Later — outsourced tube-laser detection (ERP buy list will help)
- [ ] Later — Linear angle → inventory stock codes
- [ ] Later — assembly qty rollup UX

## Transcript

Full captions: `02-73476004-manual-quote-with-adding-weld-time-from-cursor.srt.txt`
