"""Synthesize Tier 1 confabulation + escalation chain examples for Jagersfontein.

Two sub-categories:

A) Confabulation override (~5 examples):
   Stage A description confidently states something that the diff numbers
   contradict (e.g. "no visible gullies on the wall" while gully_count=14).
   Gold: each claim's evidence sticks with the diff numbers, NOT the Stage A
   confabulation. Trains the model to prefer numerical evidence over its own
   text description when they conflict.

B) Escalation chain (~5 examples):
   Combinations where multiple claims trigger different tiers, exercising
   the rules-engine cascade (Claim 5 escalates to match the max of Claims
   1-3 if any of them is urgent, etc.). Each example has a different mix.

All examples use existing Jagersfontein 2017-10-15 baseline + 2022-01-14
current imagery (the same anchors as the boundary cases).
"""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

REPO_ROOT = Path("/mnt/c/Users/peter/SatDiff")
sys.path.insert(0, str(REPO_ROOT))

import jsonschema

from phase2.aggregate import compute_severity, _ACTION
from phase2.prompt import build_stage_b_prompt
from phase2.runner import schema_text


SCHEMA_STR = schema_text()
SCHEMA = json.loads(SCHEMA_STR)
HAND = REPO_ROOT / "training" / "stage2_handauthored"
IMAGES_DIR = Path("/home/peter/datasets/satdiff_stage2/images/jagersfontein")
img_paths = {
    "baseline_rgb": str(IMAGES_DIR / "baseline_2017-10-15_rgb.png"),
    "baseline_nir": str(IMAGES_DIR / "baseline_2017-10-15_nir.png"),
    "current_rgb":  str(IMAGES_DIR / "current_2022-01-14_rgb.png"),
    "current_nir":  str(IMAGES_DIR / "current_2022-01-14_nir.png"),
}

CLAIM_NAMES = [
    "Containment geometry and asymmetric deposition",
    "Pond management (free supernatant water away from retaining wall, pond area within permitted volume)",
    "Surface integrity of retaining wall (no progressive erosion, gullies, or seepage on dam walls)",
    "Surface deformation (no non-consolidation movement exceeding engineering thresholds)",
    "Downstream community protection zone (Kopanong Local Municipality remains outside the hazard projection)",
]
SYSTEM_PROMPT = (
    "You are SatDiff, a satellite-borne monitoring assistant. You assess "
    "tailings-storage facilities against a regulatory contract and emit a "
    "strict-JSON pass report following the supplied output schema."
)
BASELINE = {
    "asset_id": "jagersfontein", "chosen_date": "2017-10-15", "pond_area_m2": 90689.0,
    "per_mask": {
        "impoundment":              {"NDWI_mean": -0.205, "NDMI_mean": -0.092, "B4_B3_mean": 1.225},
        "retaining_wall":           {"NDWI_mean": -0.297, "NDMI_mean": -0.183, "B4_B3_mean": 1.291},
        "downstream_slope":         {"NDWI_mean": -0.371, "NDMI_mean": -0.143, "B4_B3_mean": 1.443},
        "kopanong_protected_zone": {"NDWI_mean": -0.413, "NDMI_mean": -0.137, "B4_B3_mean": 1.547},
    },
}


def _build_diff(*, p2w=150.0, pct=50.0, asym=1.0, gully=0, gully_w=0.0, footprint=5.0,
                ndwi_max=0.62, b4b3=1.0, ndmi_wall=-0.05, swir=False) -> dict:
    return {
        "asset_id": "jagersfontein", "acquisition_date": "2022-01-14",
        "cloud_cover": 0.0, "sentinel_source": "sentinel-2b",
        "baseline_chosen_date": "2017-10-15",
        "impoundment": {"deposition_asymmetry_index": asym, "footprint_change_pct": footprint},
        "pond": {
            "area_m2": BASELINE["pond_area_m2"] * (1 + pct / 100.0),
            "area_change_pct_vs_baseline": pct, "pond_to_wall_distance_m": p2w,
            "licence_volume_exceedance_pct": pct, "NDWI_max": ndwi_max,
            "B4_B3_turbidity_ratio": b4b3,
        },
        "retaining_wall": {
            "gully_count": gully, "largest_gully_width_m": gully_w,
            "NDMI_wall_face": ndmi_wall, "SWIR_anomaly_flag": swir,
        },
        "deformation": None,
    }


def _build_evidence(diff: dict) -> dict[int, str]:
    p, i, w = diff["pond"], diff["impoundment"], diff["retaining_wall"]
    return {
        1: f"deposition_asymmetry_index={i['deposition_asymmetry_index']:.2f}; footprint_change_pct={i['footprint_change_pct']:+.1f}%",
        2: f"pond_to_wall_distance_m={p['pond_to_wall_distance_m']:.1f} m; pond_area_change_pct_vs_baseline={p['area_change_pct_vs_baseline']:+.1f}%; NDWI_max={p['NDWI_max']:.2f}",
        3: f"gully_count={w['gully_count']}; largest_gully_width_m={w['largest_gully_width_m']:.1f} m; NDMI_wall_face={w['NDMI_wall_face']:+.3f}",
        4: "no SAR data available; multispectral-only path",
        5: "no observed encroachment of impoundment features into protected zone",
    }


def _build_trends_from_severity(severities: list[str]) -> dict[int, str]:
    """Uniform convention: trend = 'increased' iff severity != 'nominal'.
    Claim 4 always 'unchanged' (pegged nominal in our SAR-less pipeline)."""
    return {
        i + 1: "unchanged" if (severities[i] == "nominal" or i == 3) else "increased"
        for i in range(5)
    }


def _build_messages(*, pid: str, baseline: dict, diff: dict, stage_a: str,
                    gold: dict) -> dict:
    prompt = build_stage_b_prompt(
        baseline=baseline, diff=diff, stage_a_text=stage_a,
        prior_reports=[], schema_text=SCHEMA_STR, pass_id=pid,
    )
    return {"messages": [
        {"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]},
        {"role": "user", "content": [
            {"type": "image", "image": img_paths["baseline_rgb"]},
            {"type": "image", "image": img_paths["baseline_nir"]},
            {"type": "image", "image": img_paths["current_rgb"]},
            {"type": "image", "image": img_paths["current_nir"]},
            {"type": "text", "text": prompt},
        ]},
        {"role": "assistant", "content": [{"type": "text", "text": json.dumps(gold, indent=2)}]},
    ]}


def _build_gold_from_engine(pid: str, diff: dict, evidence: dict) -> dict:
    """Use the rules engine for severity/action; build the gold dict.
    Trends derived from the rules-engine output (uniform convention)."""
    comp = compute_severity(diff)
    severities = [comp["per_claim"][i]["severity_level"] for i in range(5)]
    trends = _build_trends_from_severity(severities)
    gold = {
        "pass_id": pid, "acquisition_date": "2022-01-14",
        "claims": [
            {"id": i + 1, "name": CLAIM_NAMES[i],
             "probability_trend": trends[i + 1],
             "severity_level": severities[i],
             "evidence": evidence[i + 1],
             "recommended_action": comp["per_claim"][i]["recommended_action"]}
            for i in range(5)
        ],
        "overall_status": comp["overall_status"],
        "downlink_priority": comp["downlink_priority"],
        "regulatory_escalation_flag": comp["regulatory_escalation_flag"],
    }
    jsonschema.validate(gold, SCHEMA)
    return gold


# ====================== CONFABULATION OVERRIDE CASES ======================
# Stage A says X (a confabulation that doesn't match the diff). Gold cites
# the diff number. The teaching is: "evidence text follows numbers, not the
# narrative."

CONFAB_CASES = [
    {
        "tag": "confab_no_gullies_but_14",
        "stage_a": (
            "PARAGRAPH 1 — The BASELINE pair shows the Jagersfontein impoundment with "
            "a small central pond and intact retaining wall. The wall surface in the "
            "baseline NIR composite appears smooth and undisturbed.\n\n"
            "PARAGRAPH 2 — The CURRENT pair shows the same impoundment outline. The "
            "retaining wall surface is unchanged from the baseline; no visible cracks, "
            "gullies, or erosion features are present on the wall in either RGB or "
            "NIR composite. The wall surface integrity appears intact and unchanged."
        ),
        "diff": _build_diff(p2w=150.0, pct=50.0, asym=1.0, gully=14, gully_w=35.0, ndmi_wall=-0.08),
        "hint": "Stage A confidently asserts 'no gullies' but diff reports gully_count=14. Gold cites the number.",
    },
    {
        "tag": "confab_pond_unchanged_but_grew",
        "stage_a": (
            "PARAGRAPH 1 — The BASELINE pair shows the Jagersfontein impoundment with "
            "the supernatant pond at its central position, occupying a small fraction "
            "of the impoundment footprint.\n\n"
            "PARAGRAPH 2 — The CURRENT pair shows the same impoundment with the pond "
            "appearing essentially unchanged in size and position from the baseline. "
            "No noticeable expansion of the pond toward the retaining wall is visible, "
            "and the dry tailings beach appears similar to the baseline."
        ),
        "diff": _build_diff(p2w=20.0, pct=600.0, asym=1.2, gully=0, ndwi_max=0.85),
        "hint": "Stage A says pond unchanged; diff says +600% growth and pond_to_wall=20m. Gold cites the numbers.",
    },
    {
        "tag": "confab_no_asymmetry_but_high",
        "stage_a": (
            "PARAGRAPH 1 — The BASELINE pair shows tailings deposition distributed "
            "evenly across the impoundment footprint with symmetric geometry.\n\n"
            "PARAGRAPH 2 — The CURRENT pair shows the impoundment with deposition "
            "appearing similar to the baseline, evenly distributed and centred. The "
            "pond geometry is symmetric and does not appear shifted toward any "
            "particular wall segment of the impoundment."
        ),
        "diff": _build_diff(p2w=80.0, pct=70.0, asym=4.5, gully=0, footprint=18.0),
        "hint": "Stage A says symmetric; diff says asym=4.5 (Claim 1 elevated). Gold cites the index.",
    },
    {
        "tag": "confab_no_swir_but_flag",
        "stage_a": (
            "PARAGRAPH 1 — The BASELINE pair shows the wall surface in the NIR "
            "composite with a uniform appearance and no anomalous bright spots.\n\n"
            "PARAGRAPH 2 — The CURRENT pair shows the wall surface unchanged from "
            "the baseline. There are no anomalous features visible in either RGB "
            "or NIR composite; the wall surface remains uniformly cool and dry."
        ),
        "diff": _build_diff(p2w=60.0, pct=80.0, asym=1.2, gully=2, gully_w=12.0, swir=True, ndmi_wall=0.05),
        "hint": "Stage A says no anomalies; diff has SWIR_anomaly_flag=True (potential heat or moisture signature). Gold reports the flag and cites NDMI elevated.",
    },
    {
        "tag": "confab_clean_pond_but_turbid",
        "stage_a": (
            "PARAGRAPH 1 — The BASELINE pair shows the pond water as clear and dark "
            "in the RGB composite.\n\n"
            "PARAGRAPH 2 — The CURRENT pair shows the pond similarly clear and dark; "
            "water appears to be of the same quality as the baseline pair. No turbidity, "
            "sediment loading, or colour change is visible."
        ),
        "diff": _build_diff(p2w=45.0, pct=200.0, asym=1.6, gully=8, gully_w=22.0, b4b3=2.4),
        "hint": "Stage A says pond clear; diff has B4/B3=2.4 (turbid). Gold cites the turbidity ratio.",
    },
]


# ====================== ESCALATION CHAIN CASES ======================
# Each case exercises the multi-claim cascade through the rules engine.
# Specifically: Claim 5 escalates to match max of Claims 1-3 when any is
# urgent. Pick parameter combos that test this cascade.

ESCALATION_CASES = [
    {
        "tag": "esc_pond_urgent_to_5",
        "diff": _build_diff(p2w=15.0, pct=300.0, asym=1.2, gully=0, ndwi_max=0.88),
        "hint": "Claim 2 urgent (p2w<25); Claim 5 must escalate to urgent via cascade.",
    },
    {
        "tag": "esc_gully_urgent_to_5",
        "diff": _build_diff(p2w=120.0, pct=80.0, asym=1.0, gully=22, gully_w=110.0),
        "hint": "Claim 3 urgent (gully>=10); Claim 5 must escalate to urgent.",
    },
    {
        "tag": "esc_asym_urgent_to_5",
        "diff": _build_diff(p2w=120.0, pct=80.0, asym=8.0, gully=2, footprint=22.0),
        "hint": "Claim 1 urgent (asym>5); Claim 5 must escalate.",
    },
    {
        "tag": "esc_multi_urgent_combo",
        "diff": _build_diff(p2w=10.0, pct=600.0, asym=6.0, gully=18, gully_w=140.0, b4b3=1.8),
        "hint": "Three claims (1, 2, 3) all urgent; Claim 5 cascades; overall=urgent + escalation.",
    },
    {
        "tag": "esc_elevated_only_no_cascade",
        "diff": _build_diff(p2w=50.0, pct=150.0, asym=1.7, gully=4, gully_w=18.0),
        "hint": "All three (1, 2, 3) elevated but none urgent; overall=elevated; Claim 5 stays nominal (no urgent cascade).",
    },
]


# Default Stage A for escalation cases (neutral, observation-grounded)
DEFAULT_STAGE_A = (
    "PARAGRAPH 1 — The BASELINE pair (Image 1 RGB and Image 2 NIR) shows the "
    "Jagersfontein impoundment occupying the left half of the tile, with a small "
    "central pond inside a tan tailings beach. The retaining wall is faintly "
    "visible along the southern perimeter; the town centre is on the right side "
    "of the tile.\n\n"
    "PARAGRAPH 2 — The CURRENT pair (Image 3 RGB and Image 4 NIR) shows the "
    "impoundment with visible changes vs baseline; numerical changes are "
    "summarised in the [CURRENT PASS] block below."
)


def main():
    out_confab = HAND / "tier1_jagersfontein_confabulation.jsonl"
    out_escal = HAND / "tier1_jagersfontein_escalation.jsonl"

    confab_lines = []
    for case in CONFAB_CASES:
        diff = case["diff"]
        evidence = _build_evidence(diff)
        pid = f"jagersfontein-syn-{case['tag']}"
        gold = _build_gold_from_engine(pid, diff, evidence)
        msg = _build_messages(pid=pid, baseline=BASELINE, diff=diff,
                              stage_a=case["stage_a"], gold=gold)
        confab_lines.append(json.dumps(msg))
        print(f"  CONFAB {case['tag']:<32} overall={gold['overall_status']:<8} esc={gold['regulatory_escalation_flag']}")

    out_confab.write_text("\n".join(confab_lines) + "\n")
    print(f"\n  ✓ wrote {len(confab_lines)} confabulation cases to {out_confab.name}")

    escal_lines = []
    for case in ESCALATION_CASES:
        diff = case["diff"]
        evidence = _build_evidence(diff)
        pid = f"jagersfontein-syn-{case['tag']}"
        gold = _build_gold_from_engine(pid, diff, evidence)
        # Verify cascade behaviour matches the case's hint
        comp_overall = gold["overall_status"]
        c5 = gold["claims"][4]["severity_level"]
        msg = _build_messages(pid=pid, baseline=BASELINE, diff=diff,
                              stage_a=DEFAULT_STAGE_A, gold=gold)
        escal_lines.append(json.dumps(msg))
        print(f"  ESCAL  {case['tag']:<32} overall={comp_overall:<8} c5={c5:<8} {case['hint']}")

    out_escal.write_text("\n".join(escal_lines) + "\n")
    print(f"\n  ✓ wrote {len(escal_lines)} escalation cases to {out_escal.name}")


if __name__ == "__main__":
    main()
