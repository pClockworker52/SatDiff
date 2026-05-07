"""Stage 2 hand-author helper — interactive scaffold for messages-format JSONL.

Two modes (one tier each):

    Tier 1 — clone a Jagersfontein pass:
        python training/author_helper.py --asset jagersfontein \
            --scaffold-from-pass 2022-01-15 \
            --tier tier1 --tag boundary_p2w_24_5

    Tier 2/3 — fresh cross-asset example:
        python training/author_helper.py --asset aswan \
            --scaffold-blank --tier tier2 --tag seasonal_drawdown \
            --baseline-date 2018-01-15 --current-date 2018-07-15

Workflow:
    1. Helper either clones a pass record (Tier 1) or fetches+renders fresh
       imagery via SimSat (Tier 2/3) and stages an editable JSON file in
       /tmp/satdiff_author_<tag>.json.
    2. Helper opens the file in $EDITOR (default `vi`).
    3. User edits the diff / stage_a_text / gold_assistant_json fields,
       saves, exits the editor.
    4. Helper re-builds the Stage B prompt with the edited inputs, validates
       gold_assistant_json against spikes/schema.json, assembles the
       leap-finetune messages-format dict, and appends one JSONL line to
       training/stage2_handauthored/<tier>_<asset>_<tag>.jsonl.

The user only edits one file. The helper handles all messages-format
plumbing, prompt assembly, and image-path bookkeeping.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

REPO_ROOT = Path("/mnt/c/Users/peter/SatDiff")
sys.path.insert(0, str(REPO_ROOT))

import jsonschema

from phase1.loader import ASSETS, load_pass as load_pass_ds
from phase2.prompt import build_stage_b_prompt
from phase2.render import render_pass
from phase2.runner import schema_text

PHASE2_OUT = REPO_ROOT / "phase2" / "out"
HANDAUTHORED_DIR = REPO_ROOT / "training" / "stage2_handauthored"
DATASET_ROOT = Path("/home/peter/datasets/satdiff_stage2")
IMAGES_DIR = DATASET_ROOT / "images"
SCHEMA_PATH = REPO_ROOT / "spikes" / "schema.json"

SYSTEM_PROMPT = (
    "You are SatDiff, a satellite-borne monitoring assistant. You assess "
    "tailings-storage facilities against a regulatory contract and emit a "
    "strict-JSON pass report following the supplied output schema."
)

ZERO_BASELINE: dict[str, Any] = {
    "chosen_date": "TODO_baseline_date",
    "pond_area_m2": 0.0,
    "per_mask": {
        "impoundment":              {"NDWI_mean": 0.0, "NDMI_mean": 0.0, "B4_B3_mean": 0.0},
        "retaining_wall":           {"NDWI_mean": 0.0, "NDMI_mean": 0.0, "B4_B3_mean": 0.0},
        "downstream_slope":         {"NDWI_mean": 0.0, "NDMI_mean": 0.0, "B4_B3_mean": 0.0},
        "kopanong_protected_zone": {"NDWI_mean": 0.0, "NDMI_mean": 0.0, "B4_B3_mean": 0.0},
    },
}

ZERO_DIFF: dict[str, Any] = {
    "asset_id": "TODO_asset",
    "acquisition_date": "TODO_current_date",
    "cloud_cover": 0.0,
    "sentinel_source": "sentinel-2",
    "baseline_chosen_date": "TODO_baseline_date",
    "impoundment": {
        "deposition_asymmetry_index": None,
        "footprint_change_pct": None,
    },
    "pond": {
        "area_m2": None,
        "area_change_pct_vs_baseline": None,
        "pond_to_wall_distance_m": None,
        "licence_volume_exceedance_pct": None,
        "NDWI_max": None,
        "B4_B3_turbidity_ratio": None,
    },
    "retaining_wall": {
        "gully_count": None,
        "largest_gully_width_m": None,
        "NDMI_wall_face": None,
        "SWIR_anomaly_flag": False,
    },
    "deformation": None,
}

PLACEHOLDER_GOLD: dict[str, Any] = {
    "pass_id": "TODO_pass_id",
    "acquisition_date": "TODO_current_date",
    "claims": [
        {"id": 1, "name": "Containment geometry and asymmetric deposition",
         "probability_trend": "unchanged", "severity_level": "nominal",
         "evidence": "TODO", "recommended_action": "none"},
        {"id": 2, "name": "Pond management (free supernatant water away from retaining wall, pond area within permitted volume)",
         "probability_trend": "unchanged", "severity_level": "nominal",
         "evidence": "TODO", "recommended_action": "none"},
        {"id": 3, "name": "Surface integrity of retaining wall (no progressive erosion, gullies, or seepage on dam walls)",
         "probability_trend": "unchanged", "severity_level": "nominal",
         "evidence": "TODO", "recommended_action": "none"},
        {"id": 4, "name": "Surface deformation (no non-consolidation movement exceeding engineering thresholds)",
         "probability_trend": "unchanged", "severity_level": "nominal",
         "evidence": "no SAR data available; multispectral-only path",
         "recommended_action": "none"},
        {"id": 5, "name": "Downstream community protection zone (Kopanong Local Municipality remains outside the hazard projection)",
         "probability_trend": "unchanged", "severity_level": "nominal",
         "evidence": "TODO", "recommended_action": "none"},
    ],
    "overall_status": "nominal",
    "downlink_priority": "routine",
    "regulatory_escalation_flag": False,
}

HELP_BLOCK = [
    "Edit `baseline`, `diff`, `stage_a_text`, `pass_id`, and `gold_assistant_json` below.",
    "DO NOT edit `image_paths` or `_meta` — the helper writes those.",
    "When you save and exit, the helper re-builds the Stage B prompt, validates",
    "gold_assistant_json against spikes/schema.json, and appends one JSONL line",
    "to training/stage2_handauthored/<tier>_<asset>_<tag>.jsonl.",
    "",
    "Tip: gold_assistant_json must list 5 claims with id 1..5 and use the strict",
    "enums (severity_level: nominal|elevated|urgent; recommended_action:",
    "none|flag_for_review|urgent_inspection; probability_trend: increased|",
    "decreased|unchanged).",
]


# --------------------------- imagery helpers --------------------------- #


def _render_to_disk(asset_id: str, baseline_date: str, current_date: str,
                    *, force: bool = False) -> dict[str, str]:
    """Fetch tiles via phase1.loader, render PNGs, return their absolute paths.

    Image filenames follow the convention used by the auto-portion of
    build_stage2_dataset.py:
        baseline_<baseline_date>_{rgb,nir}.png
        current_<current_acquisition_date>_{rgb,nir}.png
    """
    base_ds = load_pass_ds(asset_id, baseline_date)
    cur_ds = load_pass_ds(asset_id, current_date)
    if base_ds is None or cur_ds is None:
        raise RuntimeError(
            f"SimSat returned no image for {asset_id} {baseline_date} or "
            f"{current_date}. Either Docker/SimSat is down, or the date is "
            f"outside the archive window."
        )
    cur_acq = cur_ds.attrs.get("sentinel_datetime", current_date)[:10] or current_date
    base_imgs = render_pass(base_ds)
    cur_imgs = render_pass(cur_ds)

    asset_dir = IMAGES_DIR / asset_id
    asset_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    for tag, img in (
        (f"baseline_{baseline_date}_rgb", base_imgs["rgb"]),
        (f"baseline_{baseline_date}_nir", base_imgs["nir"]),
        (f"current_{cur_acq}_rgb", cur_imgs["rgb"]),
        (f"current_{cur_acq}_nir", cur_imgs["nir"]),
    ):
        p = asset_dir / f"{tag}.png"
        if force or not p.exists():
            img.save(p, format="PNG")
        # Map symbolic name → absolute path for the editable file's image_paths.
        symbolic = "baseline_rgb" if tag.startswith("baseline_") and tag.endswith("rgb") \
            else "baseline_nir" if tag.startswith("baseline_") and tag.endswith("nir") \
            else "current_rgb" if tag.startswith("current_") and tag.endswith("rgb") \
            else "current_nir"
        paths[symbolic] = str(p)
    return paths


# --------------------------- scaffolds --------------------------- #


def _scaffold_from_pass(asset_id: str, pass_date: str, tag: str, tier: str) -> dict[str, Any]:
    """Tier 1 scaffold — clone an existing Phase 2 pass record."""
    pass_path = PHASE2_OUT / asset_id / f"{pass_date}.json"
    if not pass_path.exists():
        raise FileNotFoundError(f"No Phase 2 pass at {pass_path}.")
    rec = json.loads(pass_path.read_text())
    if not rec.get("image_available"):
        raise RuntimeError(f"Pass {pass_date} was image_unavailable; can't scaffold from it.")

    # Reuse the existing rendered PNGs from the Stage 2 image dir if present.
    # The auto-portion of build_stage2_dataset.py already wrote them.
    asset_dir = IMAGES_DIR / asset_id
    cur_acq = rec["phase1_diff"]["acquisition_date"]
    from phase1.baseline import load_baseline
    baseline = load_baseline(asset_id)
    base_date = baseline["chosen_date"]
    image_paths = {
        "baseline_rgb": str(asset_dir / f"baseline_{base_date}_rgb.png"),
        "baseline_nir": str(asset_dir / f"baseline_{base_date}_nir.png"),
        "current_rgb": str(asset_dir / f"current_{cur_acq}_rgb.png"),
        "current_nir": str(asset_dir / f"current_{cur_acq}_nir.png"),
    }
    for k, p in image_paths.items():
        if not Path(p).exists():
            raise FileNotFoundError(
                f"Expected PNG missing at {p}. Run "
                f"`python training/build_stage2_dataset.py --auto-only` first to "
                f"render the per-pass PNGs."
            )

    return {
        "_meta": {"tier": tier, "tag": tag, "scaffold": "from_pass",
                  "scaffold_pass": pass_date},
        "_help": HELP_BLOCK,
        "asset": asset_id,
        "tier": tier,
        "tag": tag,
        "image_paths": image_paths,
        "baseline": baseline,
        "diff": deepcopy(rec["phase1_diff"]),
        "stage_a_text": rec.get("stage_a_text", ""),
        "pass_id": f"{asset_id}-syn-{tag}",
        "gold_assistant_json": deepcopy(rec.get("stage_b_parsed") or PLACEHOLDER_GOLD),
    }


def _scaffold_blank(asset_id: str, baseline_date: str, current_date: str,
                    tag: str, tier: str, force_render: bool) -> dict[str, Any]:
    """Tier 2/3 scaffold — fresh cross-asset example."""
    if asset_id not in ASSETS:
        raise KeyError(f"Unknown asset {asset_id!r}; add it to phase1/loader.py first.")

    image_paths = _render_to_disk(asset_id, baseline_date, current_date,
                                   force=force_render)

    baseline = deepcopy(ZERO_BASELINE)
    baseline["chosen_date"] = baseline_date

    diff = deepcopy(ZERO_DIFF)
    diff["asset_id"] = asset_id
    diff["acquisition_date"] = current_date
    diff["baseline_chosen_date"] = baseline_date

    gold = deepcopy(PLACEHOLDER_GOLD)
    gold["pass_id"] = f"{asset_id}-syn-{tag}"
    gold["acquisition_date"] = current_date

    return {
        "_meta": {"tier": tier, "tag": tag, "scaffold": "blank"},
        "_help": HELP_BLOCK + [
            "",
            "BLANK SCAFFOLD: fill `baseline.per_mask`, `baseline.pond_area_m2`,",
            "all numeric fields under `diff.impoundment`, `diff.pond`,",
            "`diff.retaining_wall` from the source paper. Replace stage_a_text",
            "with a 2-paragraph description grounded in the visible imagery.",
            "Replace each claim's `evidence` with the diff metric (or paper",
            "narrative) appropriate to that claim — see phase2/prompt.py's",
            "claim-by-claim sourcing rules.",
        ],
        "asset": asset_id,
        "tier": tier,
        "tag": tag,
        "image_paths": image_paths,
        "baseline": baseline,
        "diff": diff,
        "stage_a_text": "TODO: paragraph 1 (BASELINE pair) — describe what is "
                         "visible in the baseline RGB+NIR pair. paragraph 2 "
                         "(CURRENT pair) — describe the visible change vs the "
                         "baseline pair.",
        "pass_id": f"{asset_id}-syn-{tag}",
        "gold_assistant_json": gold,
    }


# --------------------------- assembly --------------------------- #


_SCHEMA: dict | None = None


def _schema() -> dict:
    global _SCHEMA
    if _SCHEMA is None:
        _SCHEMA = json.loads(SCHEMA_PATH.read_text())
    return _SCHEMA


def _open_in_editor(path: Path) -> None:
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vi"
    print(f"[author_helper] opening {path} in {editor}…")
    print(f"[author_helper] save and exit when done. Ctrl-C aborts without saving.")
    subprocess.run([editor, str(path)], check=True)


def _assemble_messages(edited: dict, schema_text_str: str) -> dict:
    """Re-build the Stage B prompt from the edited inputs and assemble the
    leap-finetune messages-format dict.
    """
    prompt = build_stage_b_prompt(
        baseline=edited["baseline"],
        diff=edited["diff"],
        stage_a_text=edited["stage_a_text"],
        prior_reports=[],
        schema_text=schema_text_str,
        pass_id=edited["pass_id"],
    )
    gold = edited["gold_assistant_json"]
    jsonschema.validate(gold, _schema())  # raises on invalid
    img = edited["image_paths"]
    return {
        "messages": [
            {"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]},
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": img["baseline_rgb"]},
                    {"type": "image", "image": img["baseline_nir"]},
                    {"type": "image", "image": img["current_rgb"]},
                    {"type": "image", "image": img["current_nir"]},
                    {"type": "text", "text": prompt},
                ],
            },
            {"role": "assistant",
             "content": [{"type": "text", "text": json.dumps(gold, indent=2)}]},
        ]
    }


def _append_jsonl(messages_record: dict, tier: str, asset: str, tag: str) -> Path:
    HANDAUTHORED_DIR.mkdir(parents=True, exist_ok=True)
    out = HANDAUTHORED_DIR / f"{tier}_{asset}_{tag}.jsonl"
    line = json.dumps(messages_record)
    with out.open("a") as f:
        f.write(line + "\n")
    return out


# --------------------------- CLI --------------------------- #


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Stage 2 hand-author helper.")
    ap.add_argument("--asset", required=True)
    ap.add_argument("--tier", required=True, choices=["tier1", "tier2", "tier3"])
    ap.add_argument("--tag", required=True,
                    help="Short scenario tag (e.g. boundary_p2w_24_5).")
    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("--scaffold-from-pass", metavar="DATE",
                     help="Tier 1 mode: clone an existing Jagersfontein pass record.")
    grp.add_argument("--scaffold-blank", action="store_true",
                     help="Tier 2/3 mode: fresh cross-asset scaffold.")
    ap.add_argument("--baseline-date", help="Tier 2/3 only: baseline date.")
    ap.add_argument("--current-date", help="Tier 2/3 only: current date.")
    ap.add_argument("--force-render", action="store_true",
                    help="Tier 2/3: overwrite existing PNGs.")
    args = ap.parse_args(argv)

    if args.scaffold_blank:
        if not (args.baseline_date and args.current_date):
            ap.error("--scaffold-blank requires --baseline-date and --current-date.")
        scaffold = _scaffold_blank(
            args.asset, args.baseline_date, args.current_date,
            args.tag, args.tier, args.force_render,
        )
    else:
        scaffold = _scaffold_from_pass(
            args.asset, args.scaffold_from_pass, args.tag, args.tier,
        )

    # Stage the editable file in /tmp.
    tmp = Path(tempfile.gettempdir()) / f"satdiff_author_{args.tier}_{args.asset}_{args.tag}.json"
    tmp.write_text(json.dumps(scaffold, indent=2))
    print(f"[author_helper] scaffold staged at {tmp}")
    print(f"[author_helper]   asset={args.asset}  tier={args.tier}  tag={args.tag}")
    if args.scaffold_blank:
        print(f"[author_helper]   PNGs at /home/peter/datasets/satdiff_stage2/images/{args.asset}/")

    _open_in_editor(tmp)

    edited = json.loads(tmp.read_text())
    schema_str = schema_text()

    try:
        messages_record = _assemble_messages(edited, schema_str)
    except jsonschema.ValidationError as e:
        print(f"[author_helper] ✗ gold_assistant_json failed schema validation:")
        print(f"    {e.message}")
        print(f"[author_helper] file preserved at {tmp}; re-run with the same args after fixing")
        return 2
    except KeyError as e:
        print(f"[author_helper] ✗ scaffold missing required field: {e}")
        return 3

    out = _append_jsonl(messages_record, args.tier, args.asset, args.tag)
    print(f"[author_helper] ✓ appended 1 line to {out}")
    print(f"[author_helper]   prompt length: {len(messages_record['messages'][1]['content'][-1]['text'])} chars")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
