"""Phase 2 prompt builders — Stage A (free-text describe) + Stage B (contract JSON).

Public surface:
    build_stage_a_prompt(baseline_date, current_date) -> str
    build_stage_b_prompt(baseline, diff, stage_a_text, prior_reports,
                         schema_text, pass_id) -> str

Stage A produces grounded free text the model can later cite. Stage B
populates the contract memo's prompt verbatim
(`prompts/jagersfontein-contract.md` lines 78-149)
with real numbers from `phase1.physical_diff.compute_diff` plus Stage
A's text inlined as a new `[STAGE A OBSERVATIONS]` block.
"""

from __future__ import annotations

import json
from typing import Any

# ----------------------------- Stage A ----------------------------- #


_STAGE_A_TEMPLATE = """You are looking at FOUR satellite images of the same area, in this order:

  Image 1: BASELINE RGB        (date: {baseline_date}; earlier in time)
  Image 2: BASELINE NIR-false-colour
  Image 3: CURRENT RGB         (date: {current_date}; LATER in time, the pass we are assessing)
  Image 4: CURRENT NIR-false-colour

In NIR-false-colour, vegetation appears red, water appears dark/black, bare ground appears in grey/cyan tones.

The site is the Jagersfontein tailings storage facility (a diamond mine in South Africa). Visible features:
  - The impoundment occupies the lower-left of each tile.
  - The pond is a bright water surface inside the impoundment.
  - A retaining wall surrounds the impoundment perimeter.
  - The town of Jagersfontein is centre-right, with an SE residential extension. (No relevant change expected.)

You are being asked to perform a routine monitoring assessment. Do not assume any specific outcome or event has occurred at this site — describe only what you can directly observe in the pixels.

Write your response as TWO short paragraphs (no headings, no numbered lists, no bullets):

PARAGRAPH 1 — describe the BASELINE pair (Image 1 RGB and Image 2 NIR). What is the visible state of the pond (size, position within the impoundment), the tailings beach, the retaining wall, and the downstream slope?

PARAGRAPH 2 — describe the CURRENT pair (Image 3 RGB and Image 4 NIR), and explicitly state which features have changed compared to the baseline pair: has the pond grown or shrunk, has it moved closer to or further from the retaining wall, has the dry beach contracted, are there new erosion streaks or bare patches on the wall or downstream slope, any visible cracks or gullies, etc.

Use concrete spatial language. Do not produce JSON. Do not list sensors or bands."""


def build_stage_a_prompt(baseline_date: str, current_date: str) -> str:
    return _STAGE_A_TEMPLATE.format(baseline_date=baseline_date, current_date=current_date)


# ----------------------------- Stage B ----------------------------- #


# Verbatim from prompts/jagersfontein-contract.md lines 80-87
# + 5 inlined claim definitions (lines 13-75 condensed). Same as Spike 1's
# CONTRACT_PROMPT but with f-string slots for the populated [BASELINE] and
# [CURRENT PASS] blocks Phase 1 supplies.

_STAGE_B_TEMPLATE = """[SYSTEM]
You are SatDiff, a satellite-borne monitoring assistant. You assess the
Jagersfontein TSF against a named set of regulatory monitoring-covenant claim
conditions. For each claim, produce a structured probability-of-violation
assessment grounded in (a) the baseline image, (b) the current image, (c) a
numerical physical-diff summary, (d) prior-pass reports. Never speculate
beyond what the inputs support. Output is strict JSON.

[CONTRACT]
Asset: Jagersfontein TSF (Free State Province, South Africa)
Operator: Jagersfontein Developments (Pty) Ltd
Regulator: South African Department of Water and Sanitation (DWS)
Consequence Classification: Very High

Claim 1 — Containment geometry and asymmetric deposition.
Claim 2 — Pond management (free supernatant water away from retaining wall, pond area within permitted volume).
Claim 3 — Surface integrity of retaining wall (no progressive erosion, gullies, or seepage on dam walls).
Claim 4 — Surface deformation (no non-consolidation movement exceeding engineering thresholds).
Claim 5 — Downstream community protection zone (Kopanong Local Municipality remains outside the hazard projection).

(Detailed violation thresholds are encoded into the severity_level rules in [OUTPUT INSTRUCTIONS] below, not repeated here. Do not write threshold definitions into your `evidence` strings — write what you observe in the imagery or what the diff numbers say for THIS pass.)

[BASELINE]
Acquisition date: {baseline_date}
Imagery: not shown to you in this turn — see prior-passage description and the per-mask numerical baseline below.
Baseline indices per mask:
  impoundment:        NDWI_mean={base_imp_ndwi:+.3f}  NDMI_mean={base_imp_ndmi:+.3f}  B4/B3={base_imp_b4b3:.3f}
  retaining_wall:     NDWI_mean={base_wall_ndwi:+.3f}  NDMI_mean={base_wall_ndmi:+.3f}  B4/B3={base_wall_b4b3:.3f}
  downstream_slope:   NDWI_mean={base_ds_ndwi:+.3f}  NDMI_mean={base_ds_ndmi:+.3f}  B4/B3={base_ds_b4b3:.3f}
  kopanong_protected: NDWI_mean={base_town_ndwi:+.3f}  NDMI_mean={base_town_ndmi:+.3f}  B4/B3={base_town_b4b3:.3f}
Baseline pond_area_m2: {base_pond_area:.0f}

[CURRENT PASS]
Acquisition date: {current_date}
Cloud cover: {cloud_cover:.1f}%
Imagery: 4 images attached — Image 1: baseline RGB. Image 2: baseline NIR-false-colour. Image 3: current pass RGB. Image 4: current pass NIR-false-colour.

Physical-diff summary (numerical, computed by the on-board diff module):
  impoundment:
    deposition_asymmetry_index: {imp_asym}
    footprint_change_pct: {imp_fp}
  pond:
    area_m2: {pond_area}
    area_change_pct_vs_baseline: {pond_change}
    pond_to_wall_distance_m: {pond_to_wall}
    licence_volume_exceedance_pct: {pond_licence}
    NDWI_max: {pond_ndwi_max}
    B4_B3_turbidity_ratio: {pond_b4b3}
  retaining_wall:
    gully_count: {wall_gullies}
    largest_gully_width_m: {wall_largest_gully}
    NDMI_wall_face: {wall_ndmi}
    SWIR_anomaly_flag: {wall_swir_flag}
  deformation: null    (multispectral-only path; SAR sidecar not available for this asset)

[STAGE A OBSERVATIONS]
A first pass over the same imagery produced this free-text description. Use it as your imagery-grounding source when filling the `evidence` fields below. You may quote or paraphrase from it.

{stage_a_text}

[PRIOR REPORTS]
{prior_reports_json}

[OUTPUT SCHEMA]
{schema_text}

[OUTPUT INSTRUCTIONS]
- Output ONLY the JSON object. No prose, no markdown fences, no explanation.
- Your primary job is the EVIDENCE TEXT for each claim. Severity tiers and aggregate flags will be re-derived from the diff numbers by a downstream rules engine — focus your effort on the words inside `evidence` and `probability_trend`.
- For each claim, the `evidence` field MUST be a SHORT (1-2 sentence) statement that EITHER quotes a specific number from the Physical-diff summary above (e.g. "pond_to_wall_distance_m=9.9 m; pond area +1144% vs baseline") OR paraphrases a concrete observation from the STAGE A OBSERVATIONS paragraph 2 (the change description). Do NOT copy or restate the [CONTRACT] block wording — that text is the prompt, not your evidence. Each claim has its own evidence; do NOT copy "no SAR data available" into anything other than Claim 4.
- Claim-by-claim evidence sourcing:
    * Claim 1 (containment / asymmetry) — cite `deposition_asymmetry_index` and `footprint_change_pct` from the diff.
    * Claim 2 (pond) — cite `pond_to_wall_distance_m`, `pond_area_change_pct_vs_baseline`, and/or `NDWI_max` from the diff.
    * Claim 3 (wall integrity) — cite `gully_count`, `largest_gully_width_m`, and/or `NDMI_wall_face` from the diff. If gully_count >= 1, evidence should say so explicitly (e.g. "gully_count=28 detected on wall mask").
    * Claim 4 (deformation) — fixed evidence: "no SAR data available; multispectral-only path".
    * Claim 5 (downstream zone) — cite a concrete observation from STAGE A's town/downstream description, OR if no change observed, evidence "no observed encroachment of impoundment features into protected zone".
- `probability_trend` MUST be one of: "increased", "decreased", "unchanged". NEVER null. Pick the trend implied by the diff numbers: pond_area_change_pct > 0 → increased; pond_to_wall_distance_m shrinking vs prior reports → increased risk; deposition_asymmetry growing → increased; otherwise "unchanged".
- `severity_level` MUST be one of EXACTLY: "nominal", "elevated", "urgent". (NOT "none" — "none" is a `recommended_action` value, not a severity.) Pick the most plausible tier given the diff. A downstream rules engine will re-derive the canonical value, so don't agonise — but use only the three allowed strings.
- `recommended_action` MUST be one of EXACTLY: "none", "flag_for_review", "urgent_inspection". Map nominal→none, elevated→flag_for_review, urgent→urgent_inspection.
- `overall_status` MUST be one of: "nominal", "elevated", "urgent". `downlink_priority` MUST be one of: "routine", "priority", "immediate". `regulatory_escalation_flag` MUST be a boolean. These three aggregates and the per-claim severity_level / recommended_action will be overridden downstream by the rules engine — produce reasonable values, but the canonical answer comes from the engine.
- Use acquisition_date "{current_date}" and pass_id "{pass_id}".
- Claim 4 (Surface deformation): probability_trend "unchanged"; severity_level "nominal"; recommended_action "none"; evidence "no SAR data available; multispectral-only path".
"""


def _fmt(v: Any) -> str:
    """Render a possibly-None numeric metric for the prompt."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return f"{v:.3g}"
    return str(v)


def build_stage_b_prompt(
    *,
    baseline: dict,
    diff: dict,
    stage_a_text: str,
    prior_reports: list[dict],
    schema_text: str,
    pass_id: str,
) -> str:
    base_per_mask = baseline.get("per_mask", {})
    imp_b = base_per_mask.get("impoundment", {})
    wall_b = base_per_mask.get("retaining_wall", {})
    ds_b = base_per_mask.get("downstream_slope", {})
    town_b = base_per_mask.get("kopanong_protected_zone", {})

    imp = diff.get("impoundment") or {}
    pond = diff.get("pond") or {}
    wall = diff.get("retaining_wall") or {}

    return _STAGE_B_TEMPLATE.format(
        baseline_date=baseline.get("chosen_date", "unknown"),
        current_date=diff.get("acquisition_date", "unknown"),
        cloud_cover=float(diff.get("cloud_cover") or 0.0),
        # Baseline per-mask
        base_imp_ndwi=imp_b.get("NDWI_mean", 0.0),
        base_imp_ndmi=imp_b.get("NDMI_mean", 0.0),
        base_imp_b4b3=imp_b.get("B4_B3_mean", 0.0),
        base_wall_ndwi=wall_b.get("NDWI_mean", 0.0),
        base_wall_ndmi=wall_b.get("NDMI_mean", 0.0),
        base_wall_b4b3=wall_b.get("B4_B3_mean", 0.0),
        base_ds_ndwi=ds_b.get("NDWI_mean", 0.0),
        base_ds_ndmi=ds_b.get("NDMI_mean", 0.0),
        base_ds_b4b3=ds_b.get("B4_B3_mean", 0.0),
        base_town_ndwi=town_b.get("NDWI_mean", 0.0),
        base_town_ndmi=town_b.get("NDMI_mean", 0.0),
        base_town_b4b3=town_b.get("B4_B3_mean", 0.0),
        base_pond_area=float(baseline.get("pond_area_m2", 0.0)),
        # Current diff
        imp_asym=_fmt(imp.get("deposition_asymmetry_index")),
        imp_fp=_fmt(imp.get("footprint_change_pct")),
        pond_area=_fmt(pond.get("area_m2")),
        pond_change=_fmt(pond.get("area_change_pct_vs_baseline")),
        pond_to_wall=_fmt(pond.get("pond_to_wall_distance_m")),
        pond_licence=_fmt(pond.get("licence_volume_exceedance_pct")),
        pond_ndwi_max=_fmt(pond.get("NDWI_max")),
        pond_b4b3=_fmt(pond.get("B4_B3_turbidity_ratio")),
        wall_gullies=_fmt(wall.get("gully_count")),
        wall_largest_gully=_fmt(wall.get("largest_gully_width_m")),
        wall_ndmi=_fmt(wall.get("NDMI_wall_face")),
        wall_swir_flag=_fmt(wall.get("SWIR_anomaly_flag")),
        # Inlined Stage A + prior reports + schema
        stage_a_text=stage_a_text.strip(),
        prior_reports_json=json.dumps(prior_reports, indent=2) if prior_reports else "[]",
        schema_text=schema_text,
        pass_id=pass_id,
    )
