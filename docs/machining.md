# Mill / lathe quoting (v0)

Parallel workstream to weld / fit-up / SecturaFAB. Reviewable calculator + Kannon machine list. Does **not** auto-push mill/lathe lines into SecturaFAB. Does **not** require SecturaFAB keys.

## How to try it

1. Start the API (`uvicorn app.main:app`) and open the app.
2. Log in (password from `config/shop_rates.yaml`).
3. Go to **Machine**.
4. Mill tab: enter envelope (in) + whatever features you have from the drawing (face area, pocket volume, contour length, holes). Calculate.
5. Lathe tab: finish Ø, length, stock Ø. Calculate.
6. If the part is outside the July 27 envelope, the page shows **Out of envelope — do not silent-quote** and `ok_to_quote` is false. Minutes are still shown for review.

API (same auth header `X-App-Token`):

```http
GET  /api/machines
GET  /api/machining
POST /api/machining/mill
POST /api/machining/lathe
```

Example mill body:

```json
{
  "material": "a36",
  "qty": 10,
  "length_in": 8,
  "width_in": 6,
  "height_in": 1.5,
  "face_area_in2": 48,
  "hole_count": 4,
  "hole_diameter_in": 0.375,
  "hole_depth_in": 1.5
}
```

Example lathe body:

```json
{
  "material": "carbon_steel",
  "qty": 5,
  "diameter_in": 3,
  "length_in": 6,
  "stock_diameter_in": 3.5
}
```

## Formulas (public — do not invent shop-specific SFM)

Implemented exactly as published (imperial). D = tool Ø for mill, workpiece Ø for turn.

| Name | Formula | Source |
|------|---------|--------|
| RPM | `RPM = (SFM × 3.82) / D` | [Kennametal Speeds and Feeds](https://www.kennametal.com/us/en/resources/engineering-calculators/miscellaneous/speed-and-feed.html), [CNC Optimization](https://www.cncoptimization.com/resources/guides/cnc-cutting-speed-feed-formulas/) |
| Mill feed | `IPM = RPM × flutes × chip load` | same two pages |
| Turn feed | `IPM = RPM × IPR` (no flute multiply) | Kennametal / same chain |
| Mill MRR | `WOC × DOC × IPM` | CNC Optimization (ap × ae × vf); Kennametal mill MRR |
| Turning SFM check | `SFM = 0.262 × part diameter × RPM` | Kennametal |
| Time | mill: `path / IPM` or `volume / MRR`; turn: `L / IPM` | same |

No paywalled catalogs were scraped.

**Placeholder SFM bands** (not Kannon-tooling-validated; midpoint used until Kyle sends crib data):

| Material | SFM |
|----------|-----|
| 1018 / mild steel | 300–400 |
| 6061 | 800–1000 |
| 304 | 200–300 |
| Titanium | 100–150 |

Quoted time:

```
total_min = setup_min + (cut_min × non_cutting_factor × qty)
```

`non_cutting_factor` defaults to 1.20 (placeholder rapids/toolchange). Not a Kannon time study.

## Named roster (xlsx) + shop gates (July 2026)

Named machines are in `config/machines.yaml` from *Mills and Lathes Equipment.xlsx* (plus Hwacheon / Victor from the asset list). **Travels / OD / length / max RPM were empty in that workbook and are left null.** Shop-level gates still apply:

- Lathe work: ⅜–14" Ø × 12–14" long; chucks to 26"
- Mill cube 20×40; 4th-axis to 20" Ø

CNC mills (11 named): OKK MCV660, OKK MCV660 Fanuc 4-axis, Mori Seiki SH-630 (85 kVA), OKK VM-7, PUMA DNM750/50 II (15 HP), Fanuc RoboDrill D21LiB5 ×2, Fadal 906 4020HT, OKK VM511, OKK MCV660 blue, Leadwell V-50.

CNC lathes (10): Okuma L1060, Mori Seiki SL-65 ×2, Puma GT3100LM live-tool 25 HP, SKK 769 ×2, Duraturn 1530, SL250A, Feeler FTC200L 25 HP, Hwacheon (Mansfield). Manual: Victor 174OT.

Out of shop envelope → flag, `ok_to_quote: false`. Not silently quoted.

STALE 2021 Sectura book (optional default only): mill $90/hr sell, mill setup 20 min, PowderCoat-Setup $5/hr. No lathe op in Sectura. No powder/zinc $/ft².

## What Kyle should send next

Named roster is now in `config/machines.yaml`. Still needed — do not invent:

1. **Travels / OD / length** per machine (xlsx columns were empty)
2. **Max RPM**
3. **Tooling crib** and **real SFM / IPT tables** (current bands are placeholders, not Kannon-tooling-validated)
4. **Per-machine setup minutes** and **2026 burden rates** (2021 Sectura $90/hr + 20 min mill setup is STALE)
5. Confirm the 6th OKK if July 2026 counted six; name the 3 Bridgeports if they are still on the floor
6. Coating $/ft² (powder / zinc) — only a $5/hr PowderCoat-Setup stub exists

Paperless Parts / other CAD feature engines stay parked until a scored trial (`references/machining/VENDOR_DECISION.md`).
