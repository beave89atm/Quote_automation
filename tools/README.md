# Measurement / takeoff & machining tools

Free tools to support weld takeoff and mill/lathe quoting.

## Installed / available

| Tool | Use for |
|------|---------|
| **PDF-XChange Editor** | Calibrated distance measure on PDF drawings |
| **Meazure** | On-screen ruler calibrated to a known dimension |
| **FreeCAD** (+ CAM workbench) | Open STP/STEP; measure edges; mill toolpath experiments |
| **EasyPDFTakeoff** | PDF linear takeoff � `tools\EasyPdfTakeoff.exe` |
| **CAMotics** | 3-axis G-code simulation + runtime � `tools\camotics_1.2.0_AMD64.exe` (run to install) |

### Web calculators (no install)
- FSWizard: https://zero-divide.net/fswizard
- Speed & feed / cycle time: https://www.speedcalculator.net/speed-and-feed-calculator/
- HSMAdvisor trial (download from site): https://hsmadvisor.com/download
- Machining Doctor: https://www.machiningdoctor.com/calculators/

## Weld inches workflow

1. Interpret weld symbols first (continuous / stitch / one-side / both-sides / plug).
2. Measure missing lengths with PDF-XChange or EasyPDFTakeoff (calibrate to a known dim).
3. Prefer STP in FreeCAD when the print lacks edge lengths.
4. If still incomplete, stop and request component drawings or STP � do not guess.

## Mill / lathe workflow

See `references/machining/OPS_WORKFLOW.md`.

1. Identify features ? operations (and setup/op count).
2. Then estimate times (MRR / path / feeds).
3. Match to Kannon machine list when provided.
4. Missing material, stock, tol, or dims ? stop and ask.

**Plug-ins / commercial engines:** see `references/machining/PLUGINS_AND_TRIAL.md`.  
**Calibration set + scorecard:** `references/machining/calibration_jobs.md`, `trial_scorecard.csv`.  
**Buy-vs-build decision:** `references/machining/VENDOR_DECISION.md` (Paperless Parts trial first; do not auto-wire yet).

## Reference library

| File | Content |
|------|---------|
| `references/miller-welding-symbol-chart.pdf` | AWS weld symbol shop chart |
| `references/machining/OPS_WORKFLOW.md` | Feature?op map, time rules, machine placeholder |
| `references/machining/PLUGINS_AND_TRIAL.md` | Commercial plug-in catalog + Paperless Parts trial protocol |
| `references/machining/calibration_jobs.md` | Five calibration parts for vendor scoring |
| `references/machining/trial_scorecard.csv` | Trial results template |
| `references/machining/VENDOR_DECISION.md` | Do not integrate until trial passes |
| `references/machining/nims-turning-level-I.pdf` | Turning ops / process fundamentals |
| `references/machining/manual-process-planning.pdf` | Manual process planning / feature ops |
