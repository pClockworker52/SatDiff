# Phase 0 Go/No-Go Assessment — PROVISIONAL (Brumadinho only)

**Status:** Provisional after Brumadinho research. Final decision deferred until Jagersfontein research memo is complete.

**Date:** 2026-04-24

## Summary

After Phase 0.1 and 0.2 research on the Brumadinho case, the honest provisional verdict is:

> **PROCEED with scope adjustments, or pivot to backup cases.** Do not proceed under the plan as written (pure Sentinel-2 + VLM).

The binary "abandon vs. proceed" does not fit the evidence. The evidence says: the Sentinel-2-only story is not defensible at Brumadinho, but three adjusted framings are defensible. Pick one before building.

## What the Brumadinho research actually says

1. **The only robust published pre-failure satellite precursor is Sentinel-1 SAR deformation** (Grebby et al. 2021, ~40-day lead time via ISBAS InSAR).
2. **Sentinel-2 NDVI shows no pre-failure signal** at Brumadinho. Pre-failure NDVI was *higher* in 2018 than 2017. The NDVI collapse in 2019 is post-event impact.
3. A weak, multi-year Sentinel-2 surface-moisture / pond-evanescence signal exists (Silva et al. 2021) but operates on a 12–60 month horizon — not a 40-day acute precursor.
4. The Robertson Expert Panel finding that *"no apparent signs of distress"* were visible 7 days pre-failure (drone-confirmed) further constrains what RGB-band imagery could have shown.
5. Commercial, operational satellite tailings-dam monitoring exists at scale (TRE Altamira + Glencore, Insight Terra + Synspective, Terra Motion, ESA GEP) and is increasingly mandated via GISTM Principle 7 for Extreme / Very High consequence TSFs.

See `research/brumadinho-memo.md` and `research/insar-gap-assessment.md` for full detail.

## The three honest paths forward

### Path A — Fusion pipeline (recommended)
Add Sentinel-1 SAR ingest. Pipeline fuses:
- **Sentinel-1 SAR deformation summary** (published ISBAS time series or our own SBAS processing) → feeds Claim 1 (structural integrity)
- **Sentinel-2 multispectral indices** (NDVI, NDWI, NDMI, NBR, B4/B3) → feeds Claims 2–5 (geometry, pond, seepage, ecosystem)
- **VLM interprets the fused physical-diff summary against the contract-derived prompt** and produces per-claim, contract-framed output.

Justification: this is the architecture an honest production system would have. Reframes the SatDiff pitch from "detect" to "synthesise + interpret on-edge for portfolio-scale monitoring." The LFM2/LEAP on-satellite story remains load-bearing because the *fusion + interpretation layer* is what runs on orbit, regardless of which sensor streams are ingested.

Cost: expanded scope (SAR processing code, co-registration, interferogram chain or a simplified deformation proxy). Likely uses published ISBAS time series directly for the hackathon rather than doing our own InSAR.

### Path B — Narrow-claim Brumadinho
Keep Brumadinho as a case but narrow the claim. Don't pretend to "detect"; demonstrate the *interpretation architecture*. Input: published ISBAS deformation time series (from Grebby et al.) as structured signal. Output: VLM-generated contract-framed escalation timeline. Compare against known failure date and Vale's actual (inadequate) response.

Justification: honest; demo-able; minimal scope expansion. Weaker visual "wow" factor.

Cost: less visually compelling demo. Still requires SAR data or surrogate.

### Path C — Pivot Brumadinho
Use Brumadinho as motivating context in the submission writeup but make the primary demo case a different one where Sentinel-2 is naturally load-bearing. Candidates (from plan §383):

1. **EUDR deforestation compliance** — Sentinel-2 NDVI/NBR is the natural sensor; contracts are explicit (EU Deforestation Regulation in effect since end-2024, with cutoff date December 2020); documented case studies exist.
2. **Flaring monitoring** (World Bank Zero Routine Flaring commitments) — Sentinel-2 SWIR B12 captures flaring thermal signature; contracts are explicit (operator commitments to the World Bank).
3. **Illegal artisanal mining in concession boundaries** — Sentinel-2 visible + NDWI + turbidity index; contracts explicit (mining-concession perimeter).
4. **Jagersfontein** — pending Phase 0 research. May be multispectral-accessible given its diamond-tailings chemistry and downstream mud plume; to be assessed separately.

Justification: puts Sentinel-2 + VLM in its strongest possible light; matches plan's "problem-first" principle.

Cost: abandons the dramatic Brumadinho-counterfactual framing. Re-runs Phase 0 for the new primary case (per plan §391).

## Recommended direction (provisional)

**Complete Jagersfontein research first.** If Jagersfontein has visible multispectral precursors (mud plume, pond change, drainage anomalies that were detectable pre-failure in Sentinel-2), then **Path A** is strongly supported: two cases, both handled by the fusion pipeline, with multispectral load-bearing for at least one claim.

If Jagersfontein is also SAR-dominant, **Path C** gains strength — pick one backup case where Sentinel-2 is the natural modality and keep Brumadinho only as context.

**Do not proceed with the plan as originally written.** The "pure Sentinel-2 backtest of Brumadinho" demo would require either dishonest narration or a null result.

## What the submission writeup must NOT claim (regardless of path chosen)

- "SatDiff would have detected Brumadinho from Sentinel-2 alone." — false per the peer-reviewed record.
- "SatDiff would have prevented the loss of life." — institutional response failed at Vale; monitoring alone would not have saved the day without cultural/regulatory change.
- "SatDiff replaces commercial InSAR services." — it doesn't. It complements them at the interpretation/synthesis/on-edge layer.

What it *can* claim, with evidence:
- "The architectural pattern — on-satellite physical-diff + VLM + ground-supervisor — can translate physical signals into contract-framed probability assessments for any named claim condition. We demonstrate this on historical cases where published retrospective analyses (Grebby et al. 2021; [Jagersfontein ref TBD]) identified signals that existed in the archive at the time."
- "On-satellite inference enables portfolio-scale monitoring at marginal downlink cost that current deployed services cannot match — Liquid AI's LEAP + LFM2 is the enabling technology for this pattern, not a convenience."

## Decision log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-24 | **Provisional: PROCEED with scope review pending Jagersfontein.** Default to Path A unless Jagersfontein argues for Path C. | Brumadinho research identifies a real gap but the plan's Sentinel-2-only framing is indefensible. |
| 2026-04-24 | **Hold on code/build work until Phase 0 complete.** | Plan's commitment to problem-first qualification. |

Next artefact: `research/jagersfontein-memo.md`.
