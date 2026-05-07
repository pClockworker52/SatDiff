"""Tier 1 boundary cases — re-build with rotating Jagersfontein imagery.

The earlier version used the same (2017-10-15, 2022-01-14) image pair for all
11 examples. That risks teaching the model 'imagery is decorrelated from the
gold severity, follow the diff blindly.' This rebuild rotates through 8
rendered Jagersfontein pass dates, picking the imagery whose distress level
roughly matches each scenario's synthetic diff:

  - High-distress diffs (urgent severities) → distressed-pass imagery
    (2022-01-14, 2022-10-11, 2021-12-25 — when pond was at peak)
  - Mid-distress diffs (elevated)            → mid-distress imagery
    (2021-12-10, 2022-03-10, 2022-04-14)
  - Low-distress diffs (nominal)             → least-distressed imagery
    (2021-08-12 — pond_area 127k m², closest to baseline 90k)

Probability_trend convention applied uniformly: 'increased' iff the metric
trend implies probability of contract violation has gone up vs baseline.
"""

from __future__ import annotations

import json
import sys
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
IMG = Path("/home/peter/datasets/satdiff_stage2/images/jagersfontein")

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


# 11 boundary scenarios with imagery picked to match the synthetic diff's
# distress level. Imagery dates are rendered Jagersfontein passes that
# correspond approximately to the diff's tier:
#   urgent diffs → late-2021/peak-2022 imagery (high pond, high asym)
#   elevated diffs → mid-cycle imagery
#   nominal → 2021-08-12 (lowest pond_area in cached set, ~127k m²)
SCENARIOS = [
    # (tag, p2w, pct, asym, gully, fp, current_image_date)
    ("p2w_24_urgent",            24.0,  50.0, 1.0,  0,  5.0,  "2022-01-14"),  # peak distress era
    ("p2w_26_elevated",          26.0,  50.0, 1.0,  0,  5.0,  "2021-12-10"),
    ("p2w_74_elevated",          74.5,  50.0, 1.0,  0,  5.0,  "2022-03-10"),
    ("p2w_76_nominal",           76.0,  50.0, 1.0,  0,  5.0,  "2021-08-12"),  # cleanest available
    ("pond_change_101_elevated", 150.0, 101.0, 1.0,  0,  5.0,  "2021-12-10"),
    ("pond_change_501_urgent",   150.0, 501.0, 1.0,  0,  5.0,  "2022-01-14"),  # actually high pond era
    ("gully_9_elevated",         150.0,  50.0, 1.0,  9,  5.0,  "2022-04-14"),
    ("gully_10_urgent",          150.0,  50.0, 1.0, 10,  5.0,  "2021-09-11"),  # gully count was 31 here
    ("asym_1_6_elevated",        150.0,  50.0, 1.6,  0,  5.0,  "2022-02-13"),
    ("asym_5_1_urgent",          150.0,  50.0, 5.1,  0,  5.0,  "2023-01-14"),  # 4-mo post-failure, fully clean (0.0% cloud); lobe-shaped runout scar visible, consistent with high asymmetry
    ("all_nominal",              150.0,  50.0, 1.0,  0,  5.0,  "2021-08-12"),  # least-distressed pass
]

STAGE_A_TEMPLATE = (
    "PARAGRAPH 1 — The BASELINE pair (Image 1 RGB and Image 2 NIR) shows the "
    "Jagersfontein impoundment occupying the left half of the tile, with a small "
    "central pond inside a tan tailings beach. The retaining wall is faintly "
    "visible along the southern perimeter; the town centre is on the right.\n\n"
    "PARAGRAPH 2 — The CURRENT pair (Image 3 RGB and Image 4 NIR), acquired "
    "{current_date}, shows the impoundment with visible changes vs baseline; "
    "numerical changes are summarised in the [CURRENT PASS] block below."
)


def build_diff(p2w, pct, asym, gully, fp):
    return {
        "asset_id": "jagersfontein", "acquisition_date": "{}",  # filled at format time
        "cloud_cover": 0.0, "sentinel_source": "sentinel-2b",
        "baseline_chosen_date": "2017-10-15",
        "impoundment": {"deposition_asymmetry_index": asym, "footprint_change_pct": fp},
        "pond": {
            "area_m2": BASELINE["pond_area_m2"] * (1 + pct / 100.0),
            "area_change_pct_vs_baseline": pct, "pond_to_wall_distance_m": p2w,
            "licence_volume_exceedance_pct": pct, "NDWI_max": 0.62,
            "B4_B3_turbidity_ratio": 1.0,
        },
        "retaining_wall": {
            "gully_count": gully, "largest_gully_width_m": 25.0 if gully > 0 else 0.0,
            "NDMI_wall_face": -0.05, "SWIR_anomaly_flag": False,
        },
        "deformation": None,
    }


def build_evidence(diff):
    p, i, w = diff["pond"], diff["impoundment"], diff["retaining_wall"]
    return {
        1: f"deposition_asymmetry_index={i['deposition_asymmetry_index']:.2f}; footprint_change_pct={i['footprint_change_pct']:+.1f}%",
        2: f"pond_to_wall_distance_m={p['pond_to_wall_distance_m']:.1f} m; pond_area_change_pct_vs_baseline={p['area_change_pct_vs_baseline']:+.1f}%; NDWI_max={p['NDWI_max']:.2f}",
        3: f"gully_count={w['gully_count']}; largest_gully_width_m={w['largest_gully_width_m']:.1f} m; NDMI_wall_face={w['NDMI_wall_face']:+.3f}",
        4: "no SAR data available; multispectral-only path",
        5: "no observed encroachment of impoundment features into protected zone",
    }


def build_trends_from_severity(severities):
    """Uniform convention: trend = 'increased' iff severity != 'nominal'.
    Claim 4 always 'unchanged' (pegged nominal in our SAR-less pipeline)."""
    return {
        i + 1: "unchanged" if (severities[i] == "nominal" or i == 3) else "increased"
        for i in range(5)
    }


def main():
    out = HAND / "tier1_jagersfontein_boundary.jsonl"
    lines = []
    for tag, p2w, pct, asym, gully, fp, current_date in SCENARIOS:
        diff = build_diff(p2w, pct, asym, gully, fp)
        diff["acquisition_date"] = current_date
        comp = compute_severity(diff)
        pid = f"jagersfontein-syn-boundary-{tag}"
        ev = build_evidence(diff)
        sevs = [comp["per_claim"][i]["severity_level"] for i in range(5)]
        tr = build_trends_from_severity(sevs)
        gold = {
            "pass_id": pid, "acquisition_date": current_date,
            "claims": [
                {"id": i + 1, "name": CLAIM_NAMES[i],
                 "probability_trend": tr[i + 1],
                 "severity_level": sevs[i],
                 "evidence": ev[i + 1],
                 "recommended_action": comp["per_claim"][i]["recommended_action"]}
                for i in range(5)
            ],
            "overall_status": comp["overall_status"],
            "downlink_priority": comp["downlink_priority"],
            "regulatory_escalation_flag": comp["regulatory_escalation_flag"],
        }
        jsonschema.validate(gold, SCHEMA)
        prompt = build_stage_b_prompt(
            baseline=BASELINE, diff=diff,
            stage_a_text=STAGE_A_TEMPLATE.format(current_date=current_date),
            prior_reports=[], schema_text=SCHEMA_STR, pass_id=pid,
        )
        img_paths = {
            "baseline_rgb": str(IMG / "baseline_2017-10-15_rgb.png"),
            "baseline_nir": str(IMG / "baseline_2017-10-15_nir.png"),
            "current_rgb":  str(IMG / f"current_{current_date}_rgb.png"),
            "current_nir":  str(IMG / f"current_{current_date}_nir.png"),
        }
        for p in img_paths.values():
            assert Path(p).exists(), f"missing: {p}"
        msg = {"messages": [
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
        lines.append(json.dumps(msg))
        print(f"  {tag:<28} img={current_date}  overall={comp['overall_status']:<9} esc={comp['regulatory_escalation_flag']}")

    out.write_text("\n".join(lines) + "\n")
    print(f"\n✓ Re-wrote {len(lines)} examples to {out.name}")


if __name__ == "__main__":
    main()
