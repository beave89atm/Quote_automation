# Vendor decision: mill/lathe geometry engine

**Date:** 2026-08-06  
**Updated:** 2026-08-20  
**Status:** **SPLIT**

| Track | Status |
|-------|--------|
| In-app mill/lathe **calculator + machine roster** | **UN-PARKED** (2026-08-20) — Kyle (via Chief of Staff) asked to stand this up as a parallel workstream. See `config/machines.yaml`, `config/machining.yaml`, `quote_core/machining/`, `/machine` UI. |
| Commercial **geometry engine** (Paperless Parts trial) | **Still parked.** Do not resume the PP trial or wire a vendor into this app until Kyle scores `trial_scorecard.csv` and explicitly approves. |
| Inventing mill/lathe minutes from PDF pockets | **Still forbidden.** The calculator is reviewable and feature-input driven. |

This file is kept. It is not deleted: the parked decision was about buying a CAD feature engine, not about refusing machining quoting.

## Decision (geometry engine — unchanged)

| Question | Answer |
|----------|--------|
| Buy a commercial geometry engine vs thin local feature rules? | **Trial / buy commercial first** when that track is un-parked. |
| Which vendor first? | **Paperless Parts** |
| Wire a vendor into this app now? | **No — still parked.** |
| Build FreeCAD/CAMotics automation now? | **No** as the estimator. |
| Use Xometry prices as Kannon times? | **No** |
| Stand up a calculator + Kannon machine list? | **Yes — that is the 2026-08-20 workstream.** |

## Why the geometry engine stayed parked

Machining has too many nuances for calibration-from-a-few-parts alone. A published-formula calculator with human feature inputs is a foundation; it is not a PDF→pockets engine.

## Integration gate — geometry engine (still)

- [x] Explicit Kyle approval to un-park a **calculator / machine model** (2026-08-20 CoS request)
- [ ] Calibration trial scored (`trial_scorecard.csv`)
- [ ] Explicit approval to connect a **vendor** to this repo
- [ ] Explicit approval to auto-push mill/lathe ops into SecturaFAB

See [PLUGINS_AND_TRIAL.md](PLUGINS_AND_TRIAL.md) and [calibration_jobs.md](calibration_jobs.md) when the vendor trial resumes.
