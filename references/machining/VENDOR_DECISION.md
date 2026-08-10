# Vendor decision: mill/lathe geometry engine

**Date:** 2026-08-06  
**Status:** **PARKED** (2026-08-07) — Kyle deferred machining until a better shop plan exists. Do not resume Paperless Parts trial or wire machining into Quote Automation until un-parked.

## Decision

| Question | Answer |
|----------|--------|
| Buy a commercial geometry engine vs thin local feature rules? | **Trial / buy commercial first** when un-parked. |
| Which vendor first? | **Paperless Parts** |
| Wire into this app now? | **No — parked.** |
| Build FreeCAD/CAMotics automation now? | **No** as the estimator. |
| Use Xometry prices as Kannon times? | **No** |

## Why parked

Machining has too many nuances for calibration-from-a-few-parts alone. Current app focus is batch multi-part weld/laser quoting into SecturaFAB.

## Integration gate — when un-parked

- [ ] Explicit Kyle approval to un-park machining
- [ ] Calibration trial scored (`trial_scorecard.csv`)
- [ ] Explicit approval to connect a vendor to this repo

See [PLUGINS_AND_TRIAL.md](PLUGINS_AND_TRIAL.md) and [calibration_jobs.md](calibration_jobs.md) when resumed.
