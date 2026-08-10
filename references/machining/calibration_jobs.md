# Calibration jobs for mill/lathe estimator trials

**Purpose:** Five real Kannon parts with STEP + PDF used to score commercial geometry engines (ops count, setups, cycle time) against known shop times.

**Rule:** Prefer parts that are actually machined (lathe/mill). Weldments are only useful if you also include a **machined component** STEP/PDF from the same job. Fill **Actual** columns from time cards or estimator notes before scoring a vendor.

## Selected calibration set (from local Quote Automation library)

| # | Role | Part / job seed | Local files | Process mix | Actual setups | Actual cycle (min) | Actual program (min) | Notes |
|---|------|-----------------|-------------|-------------|----------------|--------------------|----------------------|-------|
| 1 | Mill-heavy prismatic | **35145-1** (jobs 32–35) | `35145.pdf` + `35145-1.STEP` | Mill (+ weldment context) | _fill_ | _fill_ | _fill_ | Jib arm family — use machined detail PNs if weldment STEP is assembly-only |
| 2 | Mixed fab + machine | **21678-1** (jobs 38–41) | `21678-1.pdf` + `21678-1.STEP` | Mill / drill | _fill_ | _fill_ | _fill_ | Has STEP — confirm which faces are machined vs weld-only |
| 3 | Plate / coupler family | **73476004** (jobs 42–43) | `73476004.pdf` + `73476004.stp` | Mill / laser plate | _fill_ | _fill_ | _fill_ | Good STEP; separate laser vs mill ops when scoring |
| 4 | Complex multi-body | **80341687** (jobs 49–52) | `80341687.pdf` + `80341687.stp` | Mill + weld | _fill_ | _fill_ | _fill_ | Prefer a **single machined child** STEP if vendor struggles with assemblies |
| 5 | Control (little/no machine) | **MD23-1710LR** (job 55) | `MD23-1710LR.idw.pdf` (no STP yet) | Laser / fab only | **0** | **0** | **0** | Expect vendor ≈ no mill/lathe; attach STEP if available. Baseline for false positives |

### How to use

1. Copy STEP + PDF for each row into a folder `references/machining/calibration/<part>/`.
2. Fill Actual setups / cycle / program from shop history (same qty you will quote in the vendor).
3. Run the vendor trial checklist in [PLUGINS_AND_TRIAL.md](PLUGINS_AND_TRIAL.md).
4. Record results in [trial_scorecard.csv](trial_scorecard.csv).

### Swap rules

If a seed is weld-only and the vendor cannot isolate mill features, replace that row with a pure turned or milled component (bar stock, bored hub, drilled plate) that still has STEP + PDF and known times.
