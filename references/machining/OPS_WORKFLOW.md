# Mill & Lathe Quoting Workflow

**Rule:** Identify operations from the drawing first. Estimate time second. If dimensions, material, tolerance, or finish needed for time are missing � stop and ask for component drawings or STP.

Later: match ops to Kannon machine list/capabilities (to be provided).

## 1. Read the drawing (before any time math)

Capture:
- Material / condition (e.g. 1018 CRS, 304 SS, 6061-T6)
- Stock size or blank (bar, plate, casting, weldment)
- Critical tolerances and surface finish (Ra / RMS)
- Datums and setup implications
- Notes (heat treat, plating, inspection)

## 2. Classify features ? operations

### Lathe / turning (rotational)
| Feature on drawing | Typical ops |
|--------------------|-------------|
| Face / overall length | Facing |
| OD cylinder / steps | Rough turn, finish turn |
| Taper / contour | Taper / profile turn |
| Groove / undercut | Grooving |
| Part-off | Parting |
| Bore / ID steps | Drill, bore (rough/finish) |
| Threads (OD/ID) | Single-point thread or die/tap |
| Knurl | Knurling |
| Center drill / chamfer | Center, chamfer |

### Mill / machining center (prismatic)
| Feature on drawing | Typical ops |
|--------------------|-------------|
| Flat faces / pads | Face mill |
| Perimeter / profile | Contour mill |
| Pocket / cavity | Pocket mill (rough + finish) |
| Slot / keyway | Slot mill / keyseat |
| Hole (loose tol) | Drill (� spot) |
| Hole (tight tol) | Drill ? bore/ream |
| Counterbore / countersink | CB / CSK |
| Tapped hole | Drill ? tap (or thread mill) |
| Chamfer / edge break | Chamfer mill |
| 3D surface | 3D finish / ball mill |

### Op count (setups matter)
Count **operations** as distinct machine steps that change tool, fixture, or side:
1. Each **setup** (flip, re-clamp, tombstone face) is a setup cost + handling time
2. Within a setup, each **tool** or major feature family is usually one op (or rough+finish = 2)
3. Hole patterns: often 1 drill op (all same size), separate ops for different sizes/taps
4. Do **not** merge mill and lathe into one op � different machines unless mill-turn

## 3. Estimate time (after symbols/features are clear)

Rough quoting formula (refine with shop rates later):

```
Cycle time ? cutting time + non-cutting (rapids, toolchange) + dwell
Cutting time ? volume removed / MRR   or   path length / feed rate
Quoted machine time ? (cycle � qty) + setup + programming allowance (shop policy)
```

Speeds/feeds helpers (free):
- FSWizard (web): https://zero-divide.net/fswizard
- SpeedCalculator.net (web): https://www.speedcalculator.net/speed-and-feed-calculator/
- HSMAdvisor (desktop trial in `tools/`)
- FreeCAD CAM (installed) � mill toolpaths from STP when available
- CAMotics � simulate G-code runtime (mill)

**Stitch / intermittent / special notes:** apply the same discipline as welding � read the callout before totaling inches or minutes.

## 4. Missing data � stop and ask

Ask for more info when any of these are missing and needed for time:
- Material
- Stock size / starting blank
- Missing linear dims for cut length or depth
- Tolerance that forces ream/bore/grind vs drill-only
- Surface finish that forces extra finish passes
- Qty (setup amortization)
- Which faces are as-sawed vs machined

Prefer: component drawings, STP/STEP, or a marked-up print.

## 5. Machine capability match (named roster + July 2026 shop gates)

Named machines live in `config/machines.yaml`. Shop gates (xlsx travels were empty — do not invent):

- Lathe: 3/8–14" diameter × 12–14" long; chucks to 26"
- Mill: cube 20" × 40"; 4th-axis to 20" diameter

The reviewable calculator is `/machine` (API: `POST /api/machining/mill` and `/lathe`). Out-of-envelope parts are flagged and `ok_to_quote` is false.

Still TBD (no inventing):
- Per-machine travels / OD / length / max RPM
- Tooling crib / real SFM tables
- Per-machine setup and 2026 burden rates

## 6. Commercial plug-ins (geometry engines)

Do **not** invent mill/lathe times from PDF geometry alone. Use the calculator with drawing metadata + human feature inputs. Commercial geometry engines stay parked — see [VENDOR_DECISION.md](VENDOR_DECISION.md).

See:
- [PLUGINS_AND_TRIAL.md](PLUGINS_AND_TRIAL.md) � vendors and Paperless Parts trial protocol
- [calibration_jobs.md](calibration_jobs.md) � five calibration parts
- [VENDOR_DECISION.md](VENDOR_DECISION.md) � trial before any app integration
