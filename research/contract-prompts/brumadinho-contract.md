# Brumadinho Monitoring Contract — Prompt Source (Phase 0.3 Draft)

**Status:** Draft v0. Synthesised from public sources. Not a real contract — a simplified representation of the kind of contract that would exist between a tailings-dam operator (insured) and a reinsurer or regulator, post-GISTM (2020+).

**Asset:** Córrego do Feijão Dam I (Dam B1), Brumadinho, MG, Brazil. Upstream-raised iron-ore tailings dam. GISTM Consequence Classification: *Extreme* (retrospective; pre-2019 Vale categorised it "low risk" — itself part of the story).

**Contract type:** Operator-disclosure-driven indemnity policy with parametric monitoring covenants. Specific to GISTM Principle 7 compliance.

## Named claim conditions

Each condition is expressed as: a named state the operator warrants, the surface/subsurface signatures that would indicate elevated violation risk, and the sensor modalities that can express those signatures.

### Claim 1 — Structural integrity of the containment

**Operator warrants:** no anomalous ground deformation of the dam wall, crest, or tailings beach inconsistent with routine consolidation.

**Violation signatures:**
- Non-consolidation deformation exceeding 10 mm/yr sustained, or any acceleration exceeding 2 mm/month sustained over 30 days.
- Localised deformation hot spots on the dam wall or downstream slope.
- Differential movement between dam wall and adjacent stable terrain.

**Preferred sensors:** Sentinel-1 C-band SAR (ISBAS / SBAS / PSI); TerraSAR-X or COSMO-SkyMed X-band SAR for finer-resolution confirmation; ground-based radar where deployed.

**Escalation threshold:** acceleration regime of the type identified by Grebby et al. 2021 (acceleration beginning ~40 days before collapse) should trigger *urgent inspection* recommendation.

### Claim 2 — Containment area geometry

**Operator warrants:** no unauthorised expansion of the tailings impoundment footprint; no encroachment of active tailings into unpermitted zones.

**Violation signatures:**
- Change in containment polygon area exceeding permitted limits.
- Tailings fill encroaching beyond design crest line.

**Preferred sensors:** Sentinel-2 RGB + NIR (10 m); PlanetScope where available for higher resolution.

**Escalation threshold:** any unpermitted polygon change > 2% sustained across two consecutive passes.

### Claim 3 — Pond management and water level

**Operator warrants:** free water maintained at safe distance from dam crest; no abnormal reduction or expansion of pond area.

**Violation signatures:**
- Pond area shrinking significantly over multi-year horizon (possible drainage into fill → seepage erosion; cf. Silva et al. 2021 Brumadinho multi-year pond evanescence signal).
- Pond water approaching crest line.
- Abnormal turbidity or water-colour change indicating chemistry shift.

**Preferred sensors:** Sentinel-2 NDWI (B3, B8); B4/B3 ratio for turbidity; Sentinel-1 SAR for pond-extent detection through cloud.

**Escalation threshold:** pond area change > 25% across 12 months, or NDWI trajectory departing > 2σ from seasonally-normalised baseline.

### Claim 4 — Downstream slope drainage and seepage

**Operator warrants:** no anomalous seepage, surface saturation, or vegetation stress on the downstream slope indicative of internal drainage failure.

**Violation signatures:**
- Appearance of wet patches or standing water on downstream slope.
- Vegetation stress (NDVI decline, NDMI anomaly) in spatial patterns consistent with seepage.
- Surface moisture anomalies (SWIR reflectance drop, B11/B12) in downstream zones.

**Preferred sensors:** Sentinel-2 NDVI (B4, B8), NDMI (B8, B11), SWIR (B11, B12); Sentinel-1 SAR surface-moisture proxies.

**Escalation threshold:** spatially-clustered ΔNDMI < −0.10 sustained across 2+ passes on the downstream-slope mask.

### Claim 5 — Surrounding vegetation and ecosystem

**Operator warrants:** vegetation and soil condition outside the containment footprint remain consistent with baseline.

**Violation signatures:**
- Unexplained vegetation decline downstream (possible dust, leachate, unreported release).
- Soil colour change indicating deposition or chemistry shift.

**Preferred sensors:** Sentinel-2 NDVI, NDMI, NBR (B8, B12); natural-colour composites.

**Escalation threshold:** mask-aggregate ΔNDVI < −0.05 on non-asset vegetation zone, sustained 3+ passes.

## Prompt structure for on-satellite LFM2

Each pass triggers (conditional on gating) an LFM2 invocation. The structured prompt:

```
[SYSTEM]
You are SatDiff, a satellite-borne monitoring assistant. You assess a tailings
dam against a named set of contractual claim conditions. For each claim, you
produce a structured probability-of-violation assessment grounded in (a) the
baseline image, (b) the current image, (c) a numerical physical-diff summary,
(d) prior-pass reports. Never speculate beyond what the inputs support.
Output is strict JSON — no prose outside the JSON envelope.

[CONTRACT]
Asset: Córrego do Feijão Dam I (Dam B1)
Operator: Vale S.A.
Consequence Classification: Extreme
Claim conditions: [1..5 as defined above, inlined]

[BASELINE]
RGB tile: <image>
Diagnostic-band tile: <image>
Acquisition date: <date>
Physical indices at baseline: <structured>

[CURRENT PASS]
RGB tile: <image>
Diagnostic-band tile: <image>
Acquisition date: <date>
Physical-diff summary (per mask):
  containment:  ΔNDVI=..., ΔNDWI=..., ΔNBR=..., ΔSWIR=...
  downstream:   ΔNDVI=..., ΔNDMI=..., ΔSWIR=...
  vegetation:   ΔNDVI=..., ΔNBR=...
  pond:         ΔNDWI=..., B4/B3=..., area_change_pct=...
  deformation (from Sentinel-1 SAR sidecar):
    crest:       rate_mm_per_month=..., accel_flag=...
    wall:        rate_mm_per_month=..., accel_flag=...
    beach:       rate_mm_per_month=..., accel_flag=...

[PRIOR REPORTS]
Last N structured reports: <JSON list, bounded>

[OUTPUT SCHEMA]
{
  "pass_id": "<tile-id>",
  "acquisition_date": "<YYYY-MM-DD>",
  "claims": [
    {
      "id": 1,
      "name": "Structural integrity of containment",
      "probability_trend": "increased" | "decreased" | "unchanged",
      "severity_level": "nominal" | "elevated" | "urgent",
      "evidence": "<=3 sentences, grounded in physical-diff summary and images>",
      "recommended_action": "none" | "flag_for_review" | "urgent_inspection"
    },
    // ... claims 2..5
  ],
  "overall_status": "nominal" | "elevated" | "urgent",
  "downlink_priority": "routine" | "priority" | "immediate"
}
```

## Known limits of this prompt (to be acknowledged in submission)

1. **SAR sidecar assumption.** The prompt embeds a Sentinel-1 deformation summary as input. The on-satellite pipeline would need to either (a) carry Sentinel-1-derived products uplinked from the ground-based InSAR processor, or (b) do on-board lightweight deformation proxies. Pure-Sentinel-2 cannot honestly assess Claim 1 at Brumadinho.
2. **Thresholds are placeholders.** Real numbers require calibration on the archive (Phase 1.4/1.5) and on expert review.
3. **Claim 1 threshold lifted from Grebby et al.** The acceleration regime is retrospective knowledge. In production, thresholds come from site-specific engineering study, not a retrospective paper.
4. **GISTM alignment is nominal.** A real contract would cross-reference GISTM Principle 7 auditable requirements by number. This draft is structurally compatible but not GISTM-audited.
5. **No supervisory-loop prompt here.** The ground-based supervisor prompt (Phase 3) is a separate artefact and will be drafted when Phase 3 begins.

## Feasibility check

- **Can this prompt be produced from public sources?** Yes — the structure above is assembled from the Robertson Expert Panel report, Grebby et al. 2021, GISTM Principle 7 public text, and standard Sentinel-2 index definitions.
- **Can LFM2 plausibly execute it?** Requires verification. Key risks: multi-image visual comparison capability, structured JSON compliance, prompt-length fit. This is the Phase 2.5 integration spike and should happen on laptop.
- **Does it fit "compact downlink"?** Output JSON is ~1–2 KB per pass. Compatible with bandwidth-constrained downlink.
