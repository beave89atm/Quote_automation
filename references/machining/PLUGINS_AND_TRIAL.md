# Mill / lathe plug-ins and vendor trial protocol

Machining time needs **features + setups + stock + material + tolerance**. There is no free drop-in that turns a PDF into shop-grade lathe/mill minutes. Use this catalog, then run the **Paperless Parts** trial on the [calibration jobs](calibration_jobs.md).

## Layer 1 — Local helpers (not full estimators)

| Tool | Helps with | Plug into Quote Automation? |
|------|------------|------------------------------|
| FreeCAD + CAM | Open STEP; measure; mill toolpath experiments | Manual / later scripts |
| CAMotics | G-code simulation → runtime | Needs G-code first |
| HSMAdvisor / FSWizard / Machining Doctor | Speeds & feeds for a **known** op | Not drawing readers |
| PDF-XChange / EasyPDFTakeoff | Measure dims on PDF | Manual |

See also [../../tools/README.md](../../tools/README.md) and [OPS_WORKFLOW.md](OPS_WORKFLOW.md).

## Layer 2 — Commercial CAD → features → time (trial targets)

| Product | Strength | Trial priority |
|---------|----------|----------------|
| [Paperless Parts](https://www.paperlessparts.com/processes/cnc-machining/) | US shop quoting SaaS; STEP analysis; setups; holes/pockets/volume; DFM; API | **Primary trial** |
| [Quotation Factory](https://www.quotationfactory.com/en/segments/cnc-machining) | Feature recognition + GD&T; time vs your machines | Backup if PP weak on turn |
| [QuoteForge (Gridex)](https://gridex.ai/quoteforge/en) | STEP + 2D PDF notes; credit compute | Backup / API-style |
| [Oroox](https://oroox.com/en-us/solutions/cnc-machining-quoting-software) | STEP features + cycle/setup | Optional |
| [Machine Research](https://machineresearch.com/estimating-and-quoting-software/) | ML on **your** historical times | Later, if time-card history exists |

**Not a shop plug-in:** [Xometry Instant Quoting](https://www.xometry.com/machine-learning-for-manufacturing/) — prices their network, not Kannon rates (sanity check only).

**CAM-side:** CloudNC CAM Assist, Mastercam/Fusion toolpath time — strong cycle times after a toolpath exists; heavier than quoting.

## Layer 3 — Still owned by Quote Automation

Even after a plug-in: Kannon machine list, setup minutes, efficiency, weld/laser/machine routing, human review (**do not invent** when STEP/PDF lack data), SecturaFAB op push.

```text
PDF + STEP → geometry engine → ops/setups/volume
                ↓
         Kannon shop rates → review UI → SecturaFAB
```

## Paperless Parts trial protocol (primary)

Complete this on the five [calibration jobs](calibration_jobs.md). Live account login is Kyle’s; this repo holds the scorecard and pass/fail rules.

### Before upload

1. Fill **Actual** columns in `calibration_jobs.md` (or leave blank and note “estimate only”).
2. Stage files: one folder per part with STEP + PDF.
3. Record material, qty, and whether the part is mill / lathe / mill-turn / laser-only.

### Per part in Paperless Parts

1. Create/open a quote; upload STEP (required) and PDF (for threads/tol notes).
2. Capture vendor outputs:
   - Suggested process (mill vs turn)
   - Setup count
   - Feature list / op breakdown (holes, pockets, etc.)
   - Cycle or run time (minutes)
   - Programming / engineering time if shown
   - DFM warnings
3. Paste numbers into [trial_scorecard.csv](trial_scorecard.csv).

### Pass / fail (per part)

| Check | Pass if |
|-------|---------|
| Control part MD23 | Vendor mill/lathe cycle ≈ 0 or clearly “no CNC” / sheet-only |
| Setup count | Within ±1 of Actual (or estimator judgment if Actual blank) |
| Cycle time | Within ±30% of Actual when Actual is known |
| Op list | Readable and matches shop intent (no invented welds-as-machine) |
| Export | Can get numbers out (UI copy, CSV, or API) for later integration |

### Trial outcome (record here after runs)

| Field | Value |
|-------|--------|
| Trial date | _pending Kyle login_ |
| Vendor | Paperless Parts (primary) |
| Parts scored | 0 / 5 |
| Pass count | _ |
| Fail notes | _ |
| Recommend integrate? | See [VENDOR_DECISION.md](VENDOR_DECISION.md) |

Until the live trial is scored, treat outcome as **not yet validated** — decision doc still chooses PP as first vendor and **blocks vendor wiring**. The in-app calculator + machine roster (2026-08-20) is a separate track.
