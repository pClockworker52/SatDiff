# Open Questions — Gaps from Phase 0 Research

Questions the Phase 0 research identified but did not answer. Logged here so they don't get lost and so the laptop spikes can be shaped around the important ones.

Ordered by impact on the hackathon submission. Items in **bold** are likely to change the pitch if answered unfavourably.

## Gaps that could change the pitch

### 1. **LFM2-VL performance on top-down multispectral imagery** (SLEEPER RISK)
Published LFM2-VL benchmarks (IFEval, GSM8K, etc.) are all standard VLM suites. There is no public evaluation on nadir-view Sentinel-2 imagery. A model trained predominantly on internet image corpora may generalise poorly to the top-down multispectral perspective.

**How to close:** this is the LEAP spike. Give LFM2-VL-450M and LFM2-VL-1.6B a pair of Jagersfontein tiles (say, 2018 clean + 2021 pond-at-wall) and ask it to describe the difference. Evaluate:
- Does it recognise the impoundment / pond / dam geometry at all?
- Does it name pond-to-wall proximity unprompted?
- Does it produce valid JSON against the contract schema?
- Latency on laptop hardware.

If strongly no, Path A needs rescoping (possibly narrow claim or more aggressive prompt engineering; worst case a smaller demonstration).

### 2. **Per-asset-year economics**
We establish the compute envelope but never compute $/asset-year. Without this the "low marginal cost for portfolio-scale monitoring" claim is unquantified.

**Rough bounds to work with:**
- Unibap iX10 unit cost ≈ €200K–€500K (trade press, not listed).
- LEO launch ≈ $3–6K/kg; iX10 ≈ 1.4 kg; bus + integration adds most of the mass/cost.
- A single LEO EO smallsat mission amortised over 5-year life + 100–1000 assets monitored → rough order of magnitude $500–$5000/asset/year for the space segment alone.
- Commercial InSAR tailings-dam service reported anecdotally at $20K–$100K/year/TSF.
- Sentinel-2 ground-segment data is free.

**How to close:** one or two back-of-envelope slides for the submission. Doesn't need to be rigorous — just honest bounds.

### 3. **Commercial InSAR pricing**
TRE Altamira, Insight Terra, SatSense list no public prices. Without this we claim a gap of unknown width.

**How to close:** a LinkedIn / industry-press dig or an hour on relevant analyst reports. For the hackathon this is nice-to-have — not gating — but it materially strengthens the submission writeup.

### 4. **First customer thesis**
Plan says "reinsurers, environmental regulators, infrastructure operators." Never picks one. Our Jagersfontein contract-prompt actually fits a **GISTM independent auditor** much better than a reinsurer — GISTM Principle 7 compliance is hard-dollar procurement; reinsurance premium reduction is soft.

**How to close:** pick one primary buyer for the submission writeup's commercial section. Recommendation: **GISTM audit support** (Principle 7) as primary, reinsurer portfolio monitoring as adjacent. The forensic report's Nov 2025 recommendation explicitly calls for "mandatory independent audits" — that's a named, growing market.

### 5. **Workflow-integration reality**
DWS, reinsurers, and GISTM auditors consume **PDFs**, not JSON. Our pipeline outputs JSON.

**How to close:** cheap. The submission writeup should note that the supervisory loop emits both structured JSON (for machine integration) and a per-asset PDF report (for institutional consumers). A 5-minute jinja template suffices for the demo.

## Gaps that affect implementation realism

### 6. Cloud-cover effective revisit
Jagersfontein (semi-arid, Free State) ≈ 3–5 day effective cadence once clouds are filtered. Brumadinho (tropical, MG) ≈ 10–15 days in wet season. Plan treats Sentinel-2 as "continuous"; it isn't.

**How to close:** run the cloud-cover filter on the actual archive during Phase 1 data pull, report effective cadence per site. Document in submission as a known limit.

### 7. Co-registration error budget
Sentinel-2 L2A nominal geolocation is <8 m at 95% confidence. Asset-scale change detection at 10 m pixel size requires careful sub-pixel co-registration. Plan handwaves "use existing Python libraries."

**How to close:** during Phase 1 data pull, pick a known-stable reference (e.g., a road intersection or building within a few km of the TSF) and verify co-registration error is sub-pixel. If not, add a co-registration step (e.g., `arosics` library or similar). Low-risk, standard EO engineering.

### 8. Supervisory-loop compute cost at scale
Plan's Phase 3 uses "Claude or GPT on the ground" every 20 passes. For 800 assets × (passes/20) × frontier-API cost, this has a monthly bill.

**How to close:** rough order-of-magnitude in submission writeup. Mention that for production, supervisor could itself be a smaller model (LFM2-8B class or similar), not a frontier API. Hackathon demo can use Claude/GPT freely without committing to it as the production plan.

### 9. LEAP deployment targets
LFM2-VL exists; does LEAP actually compile / export to Hailo-8 or Myriad X? Or only to generic CPU/GPU?

**How to close:** during the LEAP access spike. Even if it doesn't target Hailo-8 today, we can claim the architectural pattern is target-agnostic; not a pitch-killer, but worth knowing.

## Gaps to acknowledge openly in the submission writeup

### 10. SAR sidecar is ground-precomputed in v0
We use published Grebby ISBAS time series (or similar) as structured SAR input. Production would co-locate SAR processing on-satellite or on a peer satellite. Explicit in writeup.

### 11. No on-board radiation/fault modelling
SimSat doesn't model it; neither do we. Out of scope for the hackathon; acknowledged.

### 12. LFM2-VL vision modality was not trained on Sentinel-2
Even if the spike works, the model has not been fine-tuned on Earth observation. Production would want domain-specific fine-tuning (LoRA or full) on a curated EO corpus. Out of scope; acknowledged.

### 13. The "on-satellite" claim is architectural, not deployed
We do not fly anything. We demonstrate the pattern that could be flown. SatDiff v0 runs the pipeline on laptop/container hardware; the compute envelope is claimed as feasible per the `satellite-architecture.md` memo, not proven by flight.

## Underweighted aspects from existing research (to use in the submission)

### 14. Torres-Cruz & O'Donovan 2023 already proved the signal exists
Our architecture is not discovering; it is **productising** a discovery that two academics already made retrospectively using the same public data we'll use. This is a much stronger pitch than "we can detect things."

### 15. Audit-trail framing beats monitoring framing
At Brumadinho, monitoring existed and warnings were ignored (inclinometer data "worthless"; email-flagged sensor problems two days out). At Jagersfontein, a DWS directive was waived against unmet conditions. **The failure mode is signal deniability, not signal absence.** A machine-generated, time-stamped, supervisory-loop-signed report stream creates an audit trail that's harder to paper over.

### 16. GISTM Principle 7 is the procurement lever
GISTM is now ~4 years old, audit-driven, increasingly enforced. Post-Brumadinho reinsurance re-pricing made it compulsory via contract terms. Every "Extreme"/"Very High" TSF is now obliged to maintain Principle-7-compliant monitoring. That's the line-item we fit into.

### 17. Phi-sat-1's 30% bandwidth saving is the direct precedent
Our "compact report" pitch is descended directly from Φ-sat-1's cloud-discard logic. Mentioning Φ-sat-1 as heritage (not novelty) positions SatDiff as "next step" not "moonshot."

### 18. Phi-sat-2's NanoSat MO Framework is the supervisory-loop precedent
Open-source ESA framework for in-orbit AI app deployment and update. Our "upload new prompt" pattern maps onto it directly. Cite it to ground the claim in flying reality.

### 19. Loft Orbital Ultimate Edge is the commercial precedent
Customer-iterable ML in orbit is already a commercial offering. SatDiff is a specific application of this commercial pattern, not a speculative future.

## Future-work candidates (not for hackathon)

### 20. EUDR deforestation compliance as a stronger primary case
Plan §383 lists it as backup. On reflection, EUDR has:
- A regulation with named compliance conditions (in force since late 2024)
- A portfolio of every EU importer of covered commodities
- Sentinel-2 as the natural sensor (NBR, NDVI for deforestation)
- Established peer-reviewed detection literature
- Active commercial interest (importers need due-diligence attestations)

This is arguably a cleaner SatDiff first-market than tailings. For the hackathon we commit to Path A (Jagersfontein primary); EUDR is a "Phase 6 / future work" candidate in the submission writeup.

### 21. Flaring monitoring against Zero Routine Flaring
Sentinel-2 SWIR B12 captures flaring thermal signature. Contracts are explicit. Another candidate for second application.

### 22. Real-time contract-language evolution
A supervisory loop that doesn't just update thresholds but evolves the contract language itself (e.g., proposes new claim conditions based on observed failure modes). Interesting research direction; out of scope.
