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

## Formulas (public)

| Name | Formula | Source |
|------|---------|--------|
| RPM | `(SFM × 3.82) / D`  (implemented as `12/π`) | [Harvey Tool](https://www.harveytool.com/resources/general-machining-guidelines), [Kennametal](https://www.kennametal.com/us/en/resources/engineering-calculators/miscellaneous/speed-and-feed.html) |
| Mill feed | `IPM = RPM × IPT × flutes` | Harvey Tool |
| Mill MRR | `DOC × WOC × IPM` | [Kennametal milling formulas](https://www1.mscdirect.com/images/solutions/kennametal/millingTechInfoFormulas.pdf) |
| Mill time | `path / IPM` or `volume / MRR` | same |
| Turning RPM | `n = 12 × SFM / (π × D)` | [MachiningDoctor](https://www.machiningdoctor.com/calculators/turning-calculators-2/) |
| Turning time | `T = L / (n × IPR)` | MachiningDoctor |
| Turning MRR | `12 × SFM × IPR × DOC` | MachiningDoctor |

Sandvik is cited for **method** only (material-family turning practice). Grade-specific `vc` stays on the insert box — we did not scrape paywalled catalogs.

Milling SFM / IPT midpoints come from Harvey Tool’s public carbide end-mill tables. Turning SFM / IPR and all **setup minutes** are labeled **placeholder** in `config/machining.yaml`.

Quoted time:

```
total_min = setup_min + (cut_min × non_cutting_factor × qty)
```

`non_cutting_factor` defaults to 1.20 (placeholder rapids/toolchange). Not a Kannon time study.

## Machine gates (July 27 2026 list)

- 10 CNC lathes (4 Mori Seiki, 3 Okuma, 1 Feeler, 1 Doosan live-tool, 1 Hwacheon): typical ⅜–14" Ø × 12–14" long; chucks to 26"
- 12 CNC mills (1 Mori HMC Cat 50, 6 OKK VMC Cat 50, 1 Fadal Cat 40, 2 Robodrill Cat 30, 1 Doosan Puma Cat 50, 1 Leadwell Cat 40): cube 20×40; 4th-axis to 20" Ø
- Manual: 3 Bridgeports, 1 engine lathe

Out of envelope → flag, `ok_to_quote: false`. Not silently quoted.

## What Kyle should send next

No need to block on these — add them to YAML when they arrive:

1. **Exact machine models** (and any machines missing from the July list), plus HP, max RPM, spindle nose / taper, measured travels, chuck/bar capacity.
2. **Tooling crib** — end mills, inserts, drills actually on the floor (diameter, flutes, grade). Then replace Harvey midpoints / placeholder turning SFM with crib data.
3. **Real SFM tables** or Kennametal / Sandvik **insert-box starting vc** for the grades Kannon buys.
4. **Setup minutes** by machine class (chucker vs live-tool vs Cat 50 vs Robodrill) from time cards or estimator notes.
5. **Which machines have 4th axis / probing / live tooling** if the July list was incomplete.
6. Coating (powder, zinc) is a later slice — `config/machining.yaml` has a stub only.

Paperless Parts / other CAD feature engines stay parked until a scored trial (`references/machining/VENDOR_DECISION.md`).
