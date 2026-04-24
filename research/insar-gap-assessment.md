# State-of-the-Art Gap Assessment (Phase 0.2)

**Question:** Does operational satellite monitoring of tailings dams already produce the actionable, contract-framed outputs SatDiff proposes to produce, in the same institutional register, with better physical fidelity?

If yes → **SatDiff's Sentinel-2 + on-satellite-VLM pitch collapses** and we pivot or abandon.
If no → identify the specific gap(s) and calibrate SatDiff's claim to them.

## 1. Deployed commercial services (as of 2025)

### 1.1 TRE Altamira (CLS Group)
- **Product:** SqueeSAR / PSInSAR tailings monitoring; millimetre-accuracy ground displacement; delivery cadence from quarterly up to weekly.
- **Reference deployment:** Glencore partnership (2024) to expand satellite monitoring across Glencore's entire TSF portfolio.
- **Output form:** deformation time series and persistent scatterer maps. Engineering deliverable, not insurance/contract deliverable.
- **20+ years of operation.** This is the market-standard reference.

### 1.2 Insight Terra × Synspective
- **Product:** Tailings Insight — IoT platform fused with Synspective StriX-constellation SAR analytics.
- **Explicit compliance framing:** marketed as GISTM Principle 7 monitoring solution.
- **Deployment:** announced 2023, live with multiple global mining companies.
- **Output form:** near-real-time alerts on ground-movement risk indicators, integrated with ground instrument data.

### 1.3 Terra Motion (U. Nottingham spin-out)
- **Product:** ISBAS InSAR — the technique behind Grebby 2021 Brumadinho retrospective.
- **Edge:** works over vegetated terrain where conventional PSI/SBAS fails.
- **Operational:** UK public-procurement framework contracts for national infrastructure monitoring; mining-sector offerings exist.

### 1.4 Other notable players
- **SatSense** — UK-based InSAR monitoring, ground-motion services.
- **CGG (Satellite Mapping / GeoSoftware)** — established SAR-services provider.
- **ASTERRA** — broader earth-observation analytics.
- **XR Tech Group, Geofem** — reseller / systems-integrator layer for tailings-dam InSAR.
- **ESA Geohazards Exploitation Platform (GEP)** — Copernicus-funded cloud platform for SAR-based hazard processing, increasingly used by operational services.

## 2. Regulatory driver: GISTM

Published August 2020 by ICMM / UNEP / PRI Global Tailings Review — direct post-Brumadinho industry response.

- **15 principles, 77 auditable requirements.**
- **Principle 7** mandates a comprehensive monitoring system supporting the Observational Method.
- **De-facto norm:** TSFs with *Extreme* or *Very High* Consequence Classification are InSAR-monitored. This is now common contract language in reinsurance underwriting and mining-operator sustainability disclosures.
- Vale itself (post-Brumadinho) discloses GISTM implementation progress publicly.

**Implication:** commercial, operational, GISTM-aligned satellite monitoring of high-consequence tailings dams is already the standard, not an aspiration.

## 3. What the incumbent stack does and doesn't produce

### Does produce
- Millimetre-scale deformation time series, per-persistent-scatterer maps.
- InSAR-based anomaly alerts against engineering thresholds.
- Some GISTM-compliance reports for Principle 7.
- Integration with IoT / piezometer / inclinometer streams (Insight Terra).

### Does not produce
- **Contract/claim-framed outputs.** No incumbent service publishes a feed like "Claim 2 of the monitoring contract — containment integrity — probability of violation elevated; recommended action: inspection dispatch."
- **Cross-modality (SAR + multispectral) narrative synthesis.** Deformation tells you movement; multispectral tells you vegetation/water/seepage context; no deployed service fuses these into a unified per-asset per-claim narrative.
- **On-satellite / edge inference.** All current offerings are downlink-then-cloud-process. The "satellites cannot call frontier APIs" constraint that SatDiff frames as load-bearing is not yet a constraint in deployed practice because nothing yet runs on-orbit.
- **Portfolio-scale automatic monitoring of non-GISTM assets.** InSAR services are priced per-asset and contracted; a reinsurer wanting to passively monitor 800 insured sites without operator cooperation cannot do so at low marginal cost today.
- **Seepage / water-contamination / pond-chemistry monitoring.** Explicitly acknowledged as outside InSAR's physics — requires multispectral / hyperspectral and/or in-situ.

## 4. The gap, stated precisely

SatDiff is **not** a replacement for commercial InSAR tailings-dam monitoring. That would be a losing pitch.

SatDiff's defensible gap claim is narrower and has three parts:

**Gap A — Interpretation layer.** Converting physical signals (deformation time series, multispectral indices) into institution-ready, contract-framed outputs is still a human-analyst task. A VLM that produces per-claim probability assessments directly from standardised physical-diff inputs and a contract-derived prompt closes this gap. This is orthogonal to the sensor question.

**Gap B — Multispectral + SAR fusion into a single narrative.** InSAR sees deformation; Sentinel-2 multispectral sees vegetation/water/seepage/thermal context; Sentinel-1 SAR sees surface moisture and coarse deformation. No deployed service synthesises these into a unified per-asset per-claim report. A VLM with multimodal inputs can.

**Gap C — On-satellite inference for portfolio-scale monitoring.** If a reinsurer wants to monitor 800 insured sites at low marginal cost, routing all raw pixels to the ground is bandwidth-prohibitive. On-satellite VLM inference enables a "baseline-anchored diff + local assessment + compact downlink" pattern. This gap is real *for the emerging architecture Liquid AI is pushing* — it is not a gap in today's deployed operations because nobody is doing on-orbit inference yet.

## 5. Kill-criterion decision for Phase 0.2

**Criterion:** "If operational InSAR services already produce the same actionable outputs we're proposing — in the same institutional register, with better physical fidelity — we stop."

**Finding:** they produce actionable physical-fidelity outputs (InSAR deformation) but **not** the contract-framed institutional register outputs SatDiff proposes. Therefore the gap is real **if we scope SatDiff to Gaps A + B + C above** and do not overclaim we are "detecting what InSAR misses."

**Required scope adjustments to proceed honestly:**

1. **Add Sentinel-1 SAR ingest to the pipeline.** A Sentinel-2-only pipeline cannot honestly backtest Brumadinho, because the published precursor signal at Brumadinho is SAR-deformation, not multispectral. Without SAR, the backtest will either fail or be dishonestly narrated.
2. **Reframe the pitch.** From "we detect pre-failure signals" → "we translate detected signals (ours + published SAR) into contract-framed per-claim outputs, runnable on-satellite at portfolio scale."
3. **Pick at least one case where multispectral is load-bearing** (candidates: Jagersfontein surface-change narrative; or a backup case from Section 383 of the plan — EUDR deforestation, flaring, illegal mining). This justifies the Sentinel-2 component as more than decorative.
4. **Acknowledge GISTM explicitly.** The submission's framing should position SatDiff as consistent with GISTM Principle 7 evolution, not as an alternative standard.

**Provisional Phase 0.2 verdict: PROCEED — with scope adjustments.** Confirm after Jagersfontein research memo.
