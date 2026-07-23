# Measurement / takeoff tools

Free tools installed to help measure weld lengths from drawings.

## Installed

| Tool | Use for |
|------|---------|
| **PDF-XChange Editor** | Calibrated distance measure on PDF drawings |
| **Meazure** | On-screen ruler calibrated to a known dimension |
| **FreeCAD** | Open STP/STEP and measure 3D edge/joint lengths |
| **EasyPDFTakeoff** | PDF quantity takeoff (linear measure + totals) — run `EasyPdfTakeoff.exe` in this folder |

## Workflow (weld inches)

1. Interpret weld symbols first (continuous / stitch / one-side / both-sides / plug).
2. Measure missing lengths with PDF-XChange or EasyPDFTakeoff (calibrate to a known dim).
3. Prefer STP in FreeCAD when the print lacks edge lengths.
4. If still incomplete, stop and request component drawings or STP — do not guess.
