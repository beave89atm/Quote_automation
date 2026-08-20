# Machining decision

**Date:** 2026-08-06  
**Updated:** 2026-08-20  
**Status:** **UN-PARKED** for the in-app mill/lathe calculator and machine roster.

Kyle (via Chief of Staff, while Kyle is away) asked to run mill/lathe quoting. Do **not** treat machining as PARKED.

| Track | Status |
|-------|--------|
| In-app mill/lathe **calculator + machine roster** | **UN-PARKED** (2026-08-20). Named v0 roster is in `config/machines.yaml` from the Mills and Lathes Equipment.xlsx (plus asset-list Hwacheon / Victor). July 2026 envelopes remain **shop-level gates**. Travels / max RPM still empty — do not invent. |
| Commercial **geometry engine** (Paperless Parts trial) | Still not wired. Do not resume the PP trial or connect a vendor until Kyle scores `trial_scorecard.csv` and explicitly approves. |
| Inventing mill/lathe minutes from PDF pockets | Still forbidden. Calculator is reviewable and feature-input driven. |
| Auto-push mill/lathe into SecturaFAB | Not in v0. |

## v0 named roster + July 2026 shop gates

Names from the xlsx / asset list. Shop gates (not measured travels): lathe ⅜–14″ Ø × 12–14″ long, chucks to 26″; mill cube 20×40; 4th-axis to 20″.

- CNC lathes: Okuma L1060, Mori Seiki SL-65 ×2, Puma GT3100LM (live tool, 25 HP), SKK 769 ×2, Duraturn 1530, SL250A, Feeler FTC200L (25 HP), Hwacheon (Mansfield).
- CNC mills: OKK MCV660, MCV660 Fanuc 4-axis, Mori Seiki SH-630 (85 kVA), OKK VM-7, PUMA DNM750/50 II (15 HP), RoboDrill D21LiB5 ×2, Fadal 906 4020HT, OKK VM511, MCV660 blue, Leadwell V-50.
- Manual: Victor 174OT. Bridgeport names TBD (July list had 3; not on the xlsx).

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
- [x] Named machine models from the xlsx / asset list (v0)
- [ ] Travels, max RPM, remaining HP, 6th OKK / Bridgeport names
- [ ] Tooling crib + real SFM tables (current bands are placeholders, not Kannon-tooling-validated)
- [ ] Calibration trial scored (`trial_scorecard.csv`) if a vendor engine is reconsidered
- [ ] Explicit approval to auto-push mill/lathe ops into SecturaFAB

See [PLUGINS_AND_TRIAL.md](PLUGINS_AND_TRIAL.md) and [calibration_jobs.md](calibration_jobs.md) only for the vendor-engine track.
