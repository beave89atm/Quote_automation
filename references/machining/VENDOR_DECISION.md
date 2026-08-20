# Machining decision

**Date:** 2026-08-06  
**Updated:** 2026-08-20  
**Status:** **UN-PARKED** for the in-app mill/lathe calculator and machine roster.

Kyle (via Chief of Staff, while Kyle is away) asked to run mill/lathe quoting. Do **not** treat machining as PARKED.

| Track | Status |
|-------|--------|
| In-app mill/lathe **calculator + machine roster** | **UN-PARKED** (2026-08-20). v0 roster is the **July 27 2026 capabilities list** in `config/machines.yaml`. Kyle will send a fuller list later (exact models, HP, max RPM, tooling crib). Do not block. |
| Commercial **geometry engine** (Paperless Parts trial) | Still not wired. Do not resume the PP trial or connect a vendor until Kyle scores `trial_scorecard.csv` and explicitly approves. |
| Inventing mill/lathe minutes from PDF pockets | Still forbidden. Calculator is reviewable and feature-input driven. |
| Auto-push mill/lathe into SecturaFAB | Not in v0. |

## v0 machine roster (July 2026)

Starting list only — fuller list coming from Kyle:

- 10 CNC lathes: 4 Mori Seiki, 3 Okuma, 1 Feeler, 1 Doosan (live tooling), 1 Hwacheon. Typical ⅜–14″ Ø × 12–14″ long; chucks to 26″.
- 12 CNC mills: 1 Mori Seiki HMC Cat 50, 6 OKK VMC Cat 50, 1 Fadal Cat 40, 2 Robodrill Cat 30, 1 Doosan Puma Cat 50, 1 Leadwell Cat 40. Cube 20×40; 4th-axis to 20″ Ø.
- Manual: 3 Bridgeports, 1 engine lathe.

Code: `config/machines.yaml`, `config/machining.yaml`, `quote_core/machining/`, `/machine` UI.

## Geometry engine (not this workstream)

| Question | Answer |
|----------|--------|
| Buy a commercial geometry engine vs thin local feature rules? | Later, after a scored trial. |
| Which vendor first if that trial resumes? | Paperless Parts |
| Wire a vendor into this app now? | No |
| Use Xometry prices as Kannon times? | No |
| Stand up a calculator + Kannon machine list? | **Yes — un-parked.** |

## Gates

- [x] Explicit approval to un-park a **calculator / machine model** (2026-08-20 CoS request; Kyle asked CoS to run with it)
- [ ] Fuller machine list from Kyle (models, HP, RPM, travels)
- [ ] Tooling crib + real SFM tables (current bands are placeholders, not Kannon-tooling-validated)
- [ ] Calibration trial scored (`trial_scorecard.csv`) if a vendor engine is reconsidered
- [ ] Explicit approval to auto-push mill/lathe ops into SecturaFAB

See [PLUGINS_AND_TRIAL.md](PLUGINS_AND_TRIAL.md) and [calibration_jobs.md](calibration_jobs.md) only for the vendor-engine track.
