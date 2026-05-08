# Jagersfontein Monitoring Contract — Prompt Source (Phase 0.3 Draft)

**Status:** Draft v0. Synthesised from public sources. Represents the kind of regulatory/insurance monitoring covenant that *should* have existed around the Jagersfontein TSF under a post-GISTM regime.

**Asset:** Jagersfontein Tailings Storage Facility, Free State Province, South Africa. Historic kimberlite (diamond) tailings, re-processing operation 2010s–2022. GISTM Consequence Classification: *Very High* or *Extreme* (retrospectively; was operationally treated as lower).

**Contract type:** For the demo, we frame this as a **regulator's monitoring covenant** rather than an insurer's indemnity — because at Jagersfontein the publicly-documented failure mode was regulatory enforcement, not insurance payout. The contract's counter-party is therefore DWS (Department of Water and Sanitation), the water-use licence holder of record, and the Kopanong Local Municipality as downstream protected party.

This framing lets SatDiff's demo answer a different question than Brumadinho's: *"given machine-generated, time-stamped, claim-framed evidence of license-condition breach, would enforcement have been harder to waive?"*

## Named claim conditions

### Claim 1 — Containment geometry and asymmetric deposition

**Operator warrants:** deposition is symmetric around the impoundment; tailings fill remains within permitted footprint.

**Violation signatures (Sentinel-2 primary):**
- Sustained one-sided filling visible in RGB composites.
- Fill encroaching beyond design footprint polygon.
- Absence of expected tailings beach between pond and retaining wall.

**Preferred sensors:** Sentinel-2 RGB (B2, B3, B4) + B8 NIR; PlanetScope for confirmation.

**Escalation threshold:** deposition asymmetry index (ratio of fill advance rate on dominant side vs. opposite side) > 2.0 sustained over 12 months.

### Claim 2 — Pond management (the Jagersfontein smoking gun)

**Operator warrants:** free supernatant water maintained clear of retaining wall by at least the design buffer; pond area within permitted volume.

**Violation signatures:**
- Pond boundary within [X] metres of retaining-wall crest.
- Pond area increase > permitted licence volume (for Jagersfontein: 70% over-volume was the documented 2020 breach).
- Absence of tailings beach between pond edge and wall.

**Preferred sensors:** Sentinel-2 NDWI (B3, B8), MNDWI (B3, B11); B4/B3 turbidity ratio; Sentinel-1 SAR for cloud-penetrating pond-extent detection.

**Escalation threshold:** pond-to-wall distance measured from NDWI segmentation < design buffer for 2+ consecutive passes → *urgent_inspection*. Pond area > licence volume → *urgent_inspection* + regulatory-escalation flag.

### Claim 3 — Surface integrity of retaining wall (erosion gullies, seepage)

**Operator warrants:** no progressive surface erosion, gullying, or external seepage on dam walls.

**Violation signatures:**
- Erosion gullies detectable in 10 m Sentinel-2 imagery (Torres-Cruz & O'Donovan documented 4–5 m gullies at Jagersfontein — above 10 m Sentinel-2 effective detectability for elongated features).
- Visible wet patches / seepage staining on external wall face.
- NDMI / SWIR anomalies on wall face indicating saturation.

**Preferred sensors:** Sentinel-2 RGB + B8 for gully morphology; NDMI (B8, B11) for saturation; SWIR (B11, B12) for chemistry changes. PlanetScope (3 m) recommended as escalation confirmation.

**Escalation threshold:** detected gully features > 4 m width sustained across 2+ passes → *flag_for_review*. New gully clusters on previously-clean wall sections → *urgent_inspection*.

### Claim 4 — Surface deformation

**Operator warrants:** no non-consolidation deformation exceeding engineering thresholds.

**Violation signatures:**
- Non-consolidation deformation exceeding 10 mm/yr sustained.
- Outward bulging of dam wall (east/west displacement vectors at Jagersfontein).
- Localised subsidence with adjacent uplift (material stress redistribution).

**Preferred sensors:** Sentinel-1 SAR SBAS/PSI; TerraSAR-X / COSMO-SkyMed where available.

**Escalation threshold:** sustained outward vector > 5 mm/yr on crest, or any acceleration > 2 mm/month over 30 days.

### Claim 5 — Downstream community protection zone

**Operator warrants:** no indication that a containment failure would exceed defined run-out envelope; downstream protected zone (Kopanong Local Municipality boundaries) remains outside hazard projection.

**Violation signatures:**
- Any change to upstream conditions (pond volume, dam wall integrity) that would expand the modelled run-out envelope.
- Indicators of residents or infrastructure within modelled high-consequence zone.

**Preferred sensors:** Sentinel-2 + population/infrastructure overlays (auxiliary, not real-time sensor-derived).

**Escalation threshold:** any Claim 1–4 *urgent_inspection* automatically triggers Claim 5 re-evaluation of run-out envelope.

## Prompt structure for on-satellite LFM2

```
[SYSTEM]
You are SatDiff, a satellite-borne monitoring assistant. You assess the
Jagersfontein TSF against a named set of regulatory monitoring-covenant claim
conditions. For each claim, produce a structured probability-of-violation
assessment grounded in (a) the baseline image, (b) the current image, (c) a
numerical physical-diff summary, (d) prior-pass reports. Never speculate
beyond what the inputs support. Output is strict JSON.

[CONTRACT]
Asset: Jagersfontein TSF
Operator: Jagersfontein Developments (Pty) Ltd
Regulator: South African Department of Water and Sanitation
Consequence Classification: Very High
Claim conditions: [1..5 as defined above, inlined]

[BASELINE]
Baseline tile acquisition: <earliest clean pre-failure date, e.g. 2016-2017>
RGB tile: <image>
Diagnostic-band tiles: <NIR, NDWI, SWIR composites>
Baseline indices per mask: <structured>
Masks: {impoundment_polygon, retaining_wall_polygon, downstream_slope_polygon,
        kopanong_protected_zone_polygon}

[CURRENT PASS]
Acquisition date: <date>
RGB tile: <image>
Diagnostic-band tiles: <image>
Physical-diff summary:
  impoundment:
    deposition_asymmetry_index: ...
    footprint_change_pct: ...
  pond:
    area_m2: ...
    area_change_pct_vs_baseline: ...
    pond_to_wall_distance_m: ...
    licence_volume_exceedance_pct: ...
    NDWI_max: ...
    B4_B3_turbidity_ratio: ...
  retaining_wall:
    gully_count: ...
    largest_gully_width_m: ...
    NDMI_wall_face: ...
    SWIR_anomaly_flag: ...
  deformation (Sentinel-1 SAR sidecar):
    crest_rate_mm_per_month: ...
    outward_bulge_vector_mm_yr: ...
    accel_flag: ...

[PRIOR REPORTS]
Last N structured reports: <JSON list>

[OUTPUT SCHEMA]
{
  "pass_id": "...",
  "acquisition_date": "YYYY-MM-DD",
  "claims": [
    {
      "id": 1, "name": "Containment geometry and asymmetric deposition",
      "probability_trend": "increased"|"decreased"|"unchanged",
      "severity_level": "nominal"|"elevated"|"urgent",
      "evidence": "<=3 sentences",
      "recommended_action": "none"|"flag_for_review"|"urgent_inspection"
    },
    // ...claims 2..5
  ],
  "overall_status": "nominal"|"elevated"|"urgent",
  "downlink_priority": "routine"|"priority"|"immediate",
  "regulatory_escalation_flag": true|false
}
```

## Expected backtest profile

Based on Torres-Cruz & O'Donovan findings, we expect the pipeline to produce:

- **2015–2018:** Claim 1 (asymmetric deposition) elevated early. Claim 2 (pond management) elevated when pond nears wall. Other claims nominal.
- **Feb 2019 onwards:** Claim 3 (surface integrity, erosion gullies) escalates to *flag_for_review* then *urgent_inspection*.
- **Dec 2020:** Claim 2 escalates to *urgent_inspection* + `regulatory_escalation_flag: true` (matches DWS directive date — we expect our pipeline to independently raise the same flag DWS raised).
- **May 2021 onwards:** directive lifted; claims remain elevated in SatDiff output despite operator resumption — demonstrates the enforcement-vs-evidence divergence.
- **Sep 2022:** failure. Post-failure passes show catastrophic change across all claims.

The demo narrative writes itself: "SatDiff would have produced a continuous, time-stamped, machine-generated stream of elevated claim states from 2019 forward. The DWS directive matches what SatDiff would have flagged. The May 2021 reversal occurred anyway — but would have been harder to justify against a machine-produced evidence record."

## Known limits of this prompt

1. **Pond-to-wall distance and gully width** are quantitative thresholds that require calibration. A real contract would source these from design docs; we'll use the Torres-Cruz paper's observed values as approximations.
2. **Run-out-envelope modelling** for Claim 5 is out of scope for the VLM — it's a pre-computed overlay, not a VLM-derived output.
3. **"Regulatory escalation flag"** is our framing for demo purposes. A real contract would use jurisdiction-specific language (e.g., "breach of §21(g) water use licence conditions").
4. **Thresholds should be historically calibrated**, not lifted from the retrospective paper. Acknowledge in submission writeup.
