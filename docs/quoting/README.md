# Quoting training library

Drop Loom lessons here so the agent can learn Kannon’s SecturaFAB quoting process.

## Preferred formats

| Asset | Preferred | Also OK | Avoid |
| --- | --- | --- | --- |
| Transcript / steps | **Markdown (`.md`)** | `.txt` | PDF (readable but awkward to edit/diff) |
| Video (optional) | `.mp4` in `videos/` | Loom link in the `.md` | Embed-only with no transcript |
| Screenshots (optional) | `.png` / `.jpg` in `screens/` | — | — |

**Best workflow:** Loom → copy transcript → paste into a new `.md` from `_templates/lesson.md` → fill the “Encode into automation” section.

## Layout

```
docs/quoting/
  README.md                 ← this file
  _templates/lesson.md      ← copy for each new Loom
  01-basic-bend-ops.md      ← PDF plate + bends (no weld)
  02-73476004-manual-quote.md ← STEP assembly + weld from Cursor
  03-basic-laser-only-and-nest.md ← PDF laser-only + nest / Keep Remnant
  04-entering-weldment-components-from-pdfs.md ← no-STEP weldment from component PDFs
  videos/                   ← optional MP4 downloads
  screens/                  ← optional stills (name like 01-step-03-bends.png)
```

## Naming

- `01-short-slug.md`, `02-…` (order = curriculum order)
- Match video: `videos/01-short-slug.mp4`
- Match screens: `screens/01-…png`

## Lessons

| # | File | Focus |
| --- | --- | --- |
| 01 | `01-basic-bend-ops.md` | PDF-only; Profile + Bend |
| 02 | `02-73476004-manual-quote.md` | STEP assembly; Component; Weld from Cursor |
| 03 | `03-basic-laser-only-and-nest.md` | PDF laser-only; nest; Keep Remnant |
| 04 | `04-entering-weldment-components-from-pdfs.md` | No STEP; Image/PDF components → Assembly |
