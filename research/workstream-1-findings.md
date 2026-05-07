# Workstream [1] — PDF audit-trail renderer

**Status:** ✅ DONE 2026-04-28. Per-pass PDF renderer wired through Docker; 17 PDFs rendered for the Jagersfontein 2021-06 → 2022-10 backtest. Hero pass for the demo: **2022-10-15** (post-failure, lobe runout visible).

## What it does

`phase3.render_pass_pdf(asset_id, date)` reads `phase2/out/<asset>/<date>.json`, regenerates the 4-image grid via the existing `phase1.loader.load_pass` + `phase2.render.render_pass` helpers (no coupling to the runtime path), and produces a polished one-page-per-pass PDF that looks like an artefact a GISTM auditor would file with a regulator.

Layout (top-to-bottom, A4 portrait, 12mm margins):

1. **Header** — SatDiff brand block + 3-row metadata grid (asset / acquisition / source / cloud · pass-id / baseline · regulator). Fixed-width brand on the left, flex-grow metadata on the right; doesn't truncate even with long pass-IDs.
2. **Severity badges** — overall_status (color-coded green/amber/red), downlink_priority, regulatory_escalation_flag (with a CSS-rendered "!" icon — emoji glyphs don't survive the Liberation/DejaVu fallback chain WeasyPrint pulls).
3. **4-image grid** — baseline RGB + NIR + current RGB + NIR, embedded as base64 data URIs so the PDF is self-contained. Caption strip beneath each image.
4. **Phase 1 physical-diff metrics panel** — 12-cell grid (4 columns × 3 rows) showing the contract-relevant diff numbers (asymmetry, footprint Δ, pond area, pond Δ, pond-to-wall, licence exceedance, NDWI max, B4/B3, gully count, largest gully width, NDMI wall face, SWIR anomaly).
5. **Per-claim assessment** — one card per Stage B claim, color-coded left border + severity badge. Trend glyph (▲ / ● / ▼), recommended action, and the model's evidence string.
6. **Stage A scene observations** — the model's free-text describe block, paragraphs preserved.
7. **Footer** — pipeline version, model id, render timestamp, per-stage latency, signature placeholder.

## Files added

- `phase3/__init__.py`, `phase3/__main__.py`, `phase3/cli.py` — `python -m phase3 --asset <a> --date <d>` and `--date-range START,END`.
- `phase3/render_pdf.py` — ~150 LoC. JSON → context dict → Jinja → WeasyPrint → PDF.
- `phase3/templates/pass_report.html.j2` — semantic HTML, autoescaped.
- `phase3/static/style.css` — corporate-audit aesthetic: black-on-white Helvetica, severity colours (#16a34a / #ea580c / #dc2626), tabular-nums for metrics.
- `phase3/out/jagersfontein/*.pdf` — 17 rendered pass reports (gitignored; regenerable via `python -m phase3 --asset jagersfontein --date-range 2021-06-15,2022-10-15`).

## Files modified

- `Dockerfile.satdiff` — added `COPY phase3/ /app/phase3/`. WeasyPrint runtime libs (Cairo, Pango, GDK-Pixbuf, fontconfig) were already pre-installed in [2].
- `Dockerfile.satdiff.requirements.txt` — already had `jinja2 + weasyprint`; no changes.

## Verification

```bash
$ docker compose exec satdiff python -m phase3 --asset jagersfontein --date 2022-10-15
[phase3] wrote /app/phase3/out/jagersfontein/2022-10-15.pdf

$ docker compose exec satdiff python -m phase3 --asset jagersfontein --date-range 2021-06-15,2022-10-15
[phase3] bulk over 17 passes  2021-06-15 → 2022-10-15
  [ 1/17] 2021-06-15  → 2021-06-15.pdf
  ...
  [17/17] 2022-10-15  → 2022-10-15.pdf
[phase3] wrote 17 PDFs to phase3/out/jagersfontein/
```

Rendering speed: ~3–4 s per PDF on the satdiff container (CPU-only Docker). Mostly Phase 1 NetCDF cache reads + the per-band percentile stretch in phase2.render — WeasyPrint itself is sub-second per page.

## Demo recommendations

After eyeballing all 17 PDFs:

| pass | cloud | sky readability | physical signal | demo verdict |
|---|---:|---|---|---|
| **2022-10-15** (post-failure) | 18.8% | clear, lobe runout visible | asym 22.57, pond 3.27 M m², gullies 26 | **hero** — the dramatic reveal |
| 2021-09-15 (early monitoring) | 0.0% | crisp | asym 1.08 (pre-precursor) | nominal-state contrast (if needed) |
| 2022-01-15 | 22.6% | thick cloud | pond peak 1.9 M m² | **skip for video** — clouded |
| 2022-04-15 | 0.0% (claimed) | dark/hazy | gully count 39 | skip — render stretch makes it dark |

The 2-98 percentile stretch in `phase2/render._stretch` exaggerates haze on low-dynamic-range scenes. That's a known artifact upstream of the renderer; don't try to fix it in phase3 since the imagery feeding the VLM is the contract — the PDF should show what the model saw.

## Known limitations / follow-ons

1. **Evidence strings are base-model output.** The current `phase2/out/jagersfontein/*.json` records were generated during the Phase 2 backtest with the *base* `LiquidAI/LFM2.5-VL-450M`, not the Stage 1 fine-tune. Per the model_id field, evidence strings parrot prompt content (e.g. "NDWI_mean=-0.212 NDMI_mean=-0.158 B4/B3=1.278") instead of citing the right per-claim diff fields. After Stage 1, evidence-correct rate is 100% on held-out. To regenerate the demo PDFs with crisp evidence: re-run `python -m phase2.cli --asset jagersfontein --date-range 2021-06-15,2022-10-15` against the Stage 1 GGUF llama-server and re-render. ~2.4 s/pass × 17 + ~3 s/pass × 17 ≈ 90 s on CUDA. Worth doing before [3] writeup quotes a specific PDF.
2. **No multi-pass timeline PDF yet.** Plan v2 [1] mentioned an optional timeline PDF (one row per pass over the 17-month window). Not built; would be ~50 LoC of additional Jinja template + Python. Could be useful for the writeup but per-pass PDFs already convey the trajectory if you flip through them.
3. **No "compare to previous pass" view.** The audit-trail framing benefits from showing trend explicitly. Each PDF stands alone right now. If the writeup wants a "month-over-month" delta panel, ~30 min of Jinja work to add it (we have the prior pass JSONs to diff against).
4. **Page 3 has a lot of empty space.** Stage A text + footer almost always fits on page 2 with room to spare; page 3 typically just contains the tail of paragraph 2 + the footer. Could compact by setting `page-break-before: avoid` on the footer or reducing Stage A font size. Not urgent — the doc reads fine.
