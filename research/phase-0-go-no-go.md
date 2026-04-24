# Phase 0 Go/No-Go Assessment — FINAL

**Status:** Final after Brumadinho + Jagersfontein research.
**Date:** 2026-04-24

## Verdict

> **PROCEED — with Path A (fusion pipeline, Jagersfontein as primary, Brumadinho as secondary/contrast).**

## Summary of evidence

### Brumadinho (`research/brumadinho-memo.md`)
- **Sentinel-2 alone is insufficient.** Pre-failure NDVI was flat-to-rising. Expert-panel drone confirmed no visual distress 7 days before collapse.
- **Primary pre-failure satellite signal is Sentinel-1 SAR deformation** (Grebby et al. 2021, ~40-day lead via ISBAS InSAR).
- Commercial InSAR + GISTM Principle 7 have largely closed the "detect tailings deformation" gap for this class of asset.

### Jagersfontein (`research/jagersfontein-memo.md`)
- **Sentinel-2 is load-bearing and has a clean multi-year precursor story.** Torres-Cruz & O'Donovan 2023 (Wits, *Scientific Reports*): erosion gullies (Feb 2019), persistent pond against wall, asymmetric deposition, absent beach — all detectable in public Sentinel-2 + Landsat 8 imagery from 2015 onwards.
- Pre-failure horizon: **~3.5 years of machine-detectable anomalies** before the 11 Sep 2022 failure.
- Official forensic verdict (UP + Wits, publicly released Nov 2025): **"foreseeable and preventable."**
- Failure mode was regulatory enforcement, not signal absence. DWS issued a cease-deposition directive Dec 2020 then overturned it May 2021 despite unmet conditions.

### Gap assessment (`research/insar-gap-assessment.md`)
Commercial satellite monitoring exists at scale (TRE Altamira × Glencore; Insight Terra × Synspective) and is GISTM-aligned. The defensible SatDiff gap is **not** "detect signals InSAR misses" but three other things:

- **A. Interpretation layer** — translating physical signals into contract-framed, claim-indexed outputs.
- **B. Multispectral + SAR fusion** — no deployed service unifies these into a single per-asset per-claim narrative.
- **C. On-satellite inference for portfolio scale** — the emerging architecture Liquid AI/LEAP is pushing; nothing deployed today does this on-orbit.

## Why Path A wins

Path A (fusion pipeline with Jagersfontein primary, Brumadinho secondary) is the honest fit for what the evidence supports:

1. **Jagersfontein justifies the Sentinel-2 commitment.** A ~3.5-year multi-spectral precursor record is the backtest signal the plan assumes.
2. **Brumadinho justifies the SAR commitment.** If the pipeline claims to work on tailings dams generally, it must handle the case where the signal is deformation-dominant, not multispectral-dominant.
3. **The two cases together make the architectural point.** Modality-agnostic fusion → VLM interpretation → contract-framed output → on-satellite compact report. Two cases with opposite sensor-signal profiles is a stronger architectural demonstration than two cases of the same type.
4. **The counterfactual is defensible for Jagersfontein without the institutional overclaim Brumadinho forces.** At Jagersfontein the satellite signal was public; the enforcement record was the failure. "Machine-generated, time-stamped, contract-framed evidence would have made enforcement waiver harder" is a much more defensible claim than "better monitoring would have saved 270 lives at Brumadinho" (where Vale's institutional response was the real failure mode).
5. **GISTM alignment is natural.** Both cases sit in the direct post-Brumadinho regulatory evolution; the submission writeup can position SatDiff as the VLM-enabled next step after GISTM Principle 7.

## Scope commitments (what Path A requires)

| Commitment | Scope impact |
|------------|--------------|
| Sentinel-1 SAR ingest (at least for Brumadinho Claim 1) | Medium. Plan for the hackathon: use **published ISBAS time series from Grebby et al.** as structured input rather than doing our own ISBAS processing. If time permits, add a simple SBAS/PSI processing of the Sentinel-1 archive. |
| Jagersfontein pond-to-wall geometry computation | Low. NDWI segmentation + distance-transform against retaining-wall polygon. |
| Gully-detection proxy | Low-medium. Simple: change-detection on RGB + NIR edge responses on the wall mask. Deep enough to show "non-zero gully count, widest feature width" for the VLM. |
| Asymmetric-deposition index | Low. Time-series differencing of fill-advance rate per sector. |
| Contract-prompt package with 5 claims | Already drafted (`research/contract-prompts/*`). Needs refinement in Phase 2. |
| On-satellite VLM inference spike (LEAP + LFM2) | Must be done early — Phase 1 or start of Phase 2 — not Phase 2.5. If LFM2 vision capability is insufficient for multi-image + structured-JSON output, Path A needs reassessment. |

## What the submission writeup must NOT claim (applies under any path)

- Not: "SatDiff would have detected Brumadinho from Sentinel-2 alone."
- Not: "SatDiff would have prevented the loss of life at Brumadinho / Jagersfontein." (Monitoring ≠ enforcement ≠ action.)
- Not: "SatDiff replaces commercial InSAR services." (It doesn't; it complements them at the interpretation + on-edge layer.)

What it *can* claim with evidence:

- "At Jagersfontein, public Sentinel-2 + Landsat imagery carried a multi-year precursor signal (Torres-Cruz & O'Donovan 2023, *Scientific Reports*). SatDiff demonstrates how that signal becomes machine-generated, time-stamped, contract-framed output at the moment of acquisition on-orbit."
- "At Brumadinho, Sentinel-1 SAR deformation carried a ~40-day precursor signal (Grebby et al. 2021, *Communications Earth & Environment*). SatDiff demonstrates the fusion-and-interpretation architecture that turns such signals into insurer/regulator-ready per-claim assessments."
- "The architectural pattern — on-satellite physical-diff + VLM + ground-supervisor — enables portfolio-scale continuous monitoring at a marginal downlink cost that current deployed services cannot match. Liquid AI's LEAP + LFM2 is the enabling technology for this pattern."

## Next steps (Phase 1 and the LEAP spike)

Per the plan's pre-Phase-0 commitments, two spikes should happen before serious Phase 1 build:

1. **LEAP + LFM2 access spike** (laptop). Goal: confirm `inference on (2 images, structured text, prior context) → structured JSON` works at acceptable latency. Output: a working notebook + a go/no-go on LFM2 vision capability for this task.
2. **Sentinel-2 + Sentinel-1 archive-pull spike** (laptop). Goal: pull a test slice for Jagersfontein (say, a 6-month window) via Microsoft Planetary Computer STAC API. Confirm tile identification, cloud-cover filtering, co-registration path. Output: a working data-loader + first visual sanity-check of the Torres-Cruz pond-against-wall signal in our own pull of the archive.

If both spikes succeed, Phase 1 begins with Jagersfontein as primary. If the LEAP spike fails (LFM2 vision insufficient), the whole programme needs reassessment per the plan's Phase-2.5 kill criterion escalated to Phase 0.

## Decision log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-24 | Brumadinho memo drafted. Provisional: Sentinel-2-only path not defensible for this case. | Grebby 2021 uses Sentinel-1 ISBAS; Sentinel-2 NDVI shows no pre-failure signal. |
| 2026-04-24 | Jagersfontein memo drafted. Clean Sentinel-2 case. | Torres-Cruz & O'Donovan 2023 documents 3.5 years of public multispectral precursors; official forensic report calls failure "foreseeable and preventable." |
| 2026-04-24 | **PATH A confirmed: fusion pipeline, Jagersfontein primary, Brumadinho secondary.** | Two cases with opposite sensor-signal profiles is the strongest architectural demonstration the evidence supports. |
| 2026-04-24 | Next: LEAP/LFM2 access spike + data-pull spike. Hold on Phase 1 build work until both succeed. | Plan's pre-Phase-0 commitments. |
