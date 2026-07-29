# Shop configuration

## `shop_rates.yaml`

Fill these before trusting quote times:

| Field | Meaning |
|-------|---------|
| `app.shared_password` | Team login for the web app (v1) |
| `app.default_efficiency_pct` | Office/shop efficiency applied to quoted time |
| `weld.ipm` | Effective inches/minute by fillet size |
| `fitup.no_fixture` | Fit-up minutes without a fixture |
| `fitup.with_fixture` | Fit-up minutes with a fixture |
| `always_ask` | Situations the engine must flag instead of guessing |
| `drawing_library.roots` | Shared-drive folders to search for STP / component PDFs |
| `drawing_library.auto_attach_stp` | If true, auto-copy matching STP when upload has none |

Set `KANNON_DRAWING_LIBRARY` to override roots (semicolon-separated) on each office PC.

### Fit-up formula

```
fitup_minutes = base_minutes
              + (weld_minutes * pct_of_weld)
              + (joint_count * per_joint_minutes)
```

Quoted weld+fitup time is then divided by `efficiency_pct / 100`.
