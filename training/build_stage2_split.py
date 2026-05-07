"""Build a clean train/test split for Stage 2 fine-tuning.

The earlier `build_stage2_dataset.py` concatenated everything into one JSONL,
and the framework's internal `test_size: 0.1` did a random split for
eval_loss only. The downstream eval (`eval_finetuned.py`) then re-ran the
Phase 2 backtest over passes the model had already seen during training —
so the eval measured training-data fit, not generalization.

This module splits BEFORE training:
  - 6 of the 16 invoked Phase 2 backtest passes are held out as test data
    (representative across the 17-month trajectory: early/mid/peak/post-peak/
    recovery/post-failure).
  - 5 hand-authored examples (one per sub-category) are held out as test data.

Outputs two files:
  /home/peter/datasets/satdiff_stage2/satdiff_stage2_train.jsonl
  /home/peter/datasets/satdiff_stage2/satdiff_stage2_test.jsonl

Stage 2 training points at the train file. Eval uses the test file only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path("/mnt/c/Users/peter/SatDiff")
sys.path.insert(0, str(REPO_ROOT))

from phase1.baseline import load_baseline
from phase1.loader import load_pass as load_pass_ds
from phase2.prompt import build_stage_b_prompt
from phase2.render import render_pass
from phase2.runner import schema_text

PHASE2_OUT = REPO_ROOT / "phase2" / "out"
HANDAUTHORED_DIR = REPO_ROOT / "training" / "stage2_handauthored"
DATASET_ROOT = Path("/home/peter/datasets/satdiff_stage2")
TRAIN_PATH = DATASET_ROOT / "satdiff_stage2_train.jsonl"
TEST_PATH = DATASET_ROOT / "satdiff_stage2_test.jsonl"
SPLIT_PATH = DATASET_ROOT / "satdiff_stage2_split.json"

SYSTEM_PROMPT = (
    "You are SatDiff, a satellite-borne monitoring assistant. You assess "
    "tailings-storage facilities against a regulatory contract and emit a "
    "strict-JSON pass report following the supplied output schema."
)

# Held-out test set design — picked to be representative across the 17-month
# Jagersfontein trajectory (low-distress / mid / pre-failure peak / post-peak /
# recovery / post-failure spike) so the test measures generalization across
# the full diff-pattern space, not just one regime.
HELD_OUT_BACKTEST_DATES = [
    "2021-08-15",  # early window, low pond_area, mid-asymmetry
    "2021-12-15",  # ramp-up phase, mid pond
    "2022-01-15",  # peak pre-failure (pond 1.9 M m², p2w 0)
    "2022-04-15",  # post-peak, pond reduced
    "2022-07-15",  # quiet recovery period
    "2022-10-15",  # post-failure spike (asym 22.6, p2w 0)
]

# Held-out hand-authored examples — one per sub-category, picked to be the
# most representative case in each.
HELD_OUT_HANDAUTHORED_PASSIDS = {
    "jagersfontein-syn-boundary-p2w_24_urgent",          # tier1 boundary
    "jagersfontein-syn-confab_no_gullies_but_14",        # tier1 confabulation
    "jagersfontein-syn-esc_pond_urgent_to_5",            # tier1 escalation
    "aswan-routine-2017nov-2018jul-rulecurve",           # tier2 routine
    "brumadinho-catastrophic-2019-jan-apr",              # tier3 catastrophic
}


def _save_pass_images(asset_id: str, pass_record: dict) -> tuple[Path, Path, Path, Path]:
    baseline = load_baseline(asset_id)
    baseline_date = baseline["chosen_date"]
    date_target = pass_record["date_target"]
    acquisition_date = pass_record["phase1_diff"]["acquisition_date"]

    base_ds = load_pass_ds(asset_id, baseline_date)
    cur_ds = load_pass_ds(asset_id, date_target)
    base_imgs = render_pass(base_ds)
    cur_imgs = render_pass(cur_ds)

    asset_dir = DATASET_ROOT / "images" / asset_id
    asset_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for tag, img in (
        (f"baseline_{baseline_date}_rgb", base_imgs["rgb"]),
        (f"baseline_{baseline_date}_nir", base_imgs["nir"]),
        (f"current_{acquisition_date}_rgb", cur_imgs["rgb"]),
        (f"current_{acquisition_date}_nir", cur_imgs["nir"]),
    ):
        p = asset_dir / f"{tag}.png"
        if not p.exists():
            img.save(p, format="PNG")
        paths.append(p)
    return tuple(paths)  # type: ignore[return-value]


def _to_messages(image_paths, stage_b_prompt: str, gold_json: dict) -> dict:
    return {
        "messages": [
            {"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]},
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": str(image_paths[0])},
                    {"type": "image", "image": str(image_paths[1])},
                    {"type": "image", "image": str(image_paths[2])},
                    {"type": "image", "image": str(image_paths[3])},
                    {"type": "text", "text": stage_b_prompt},
                ],
            },
            {
                "role": "assistant",
                "content": [{"type": "text", "text": json.dumps(gold_json, indent=2)}],
            },
        ]
    }


def build_auto_examples(asset_id: str = "jagersfontein"):
    """Return (train_examples, test_examples) split by HELD_OUT_BACKTEST_DATES."""
    asset_dir = PHASE2_OUT / asset_id
    if not asset_dir.exists():
        raise FileNotFoundError(asset_dir)
    baseline = load_baseline(asset_id)
    schema = schema_text()

    train, test = [], []
    pass_files = sorted(p for p in asset_dir.glob("*.json")
                        if p.name not in {"summary.json"} and p.name[:4].isdigit())
    print(f"[split] {len(pass_files)} Phase 2 pass files for asset={asset_id}")

    for pf in pass_files:
        rec = json.loads(pf.read_text())
        if not rec.get("image_available"):
            continue
        gold = rec.get("stage_b_parsed")
        diff = rec.get("phase1_diff")
        stage_a_text = rec.get("stage_a_text", "")
        if not (gold and diff and stage_a_text):
            continue

        image_paths = _save_pass_images(asset_id, rec)
        prompt = build_stage_b_prompt(
            baseline=baseline, diff=diff, stage_a_text=stage_a_text,
            prior_reports=[], schema_text=schema, pass_id=rec["pass_id"],
        )
        msg = _to_messages(image_paths, prompt, gold)

        if rec["date_target"] in HELD_OUT_BACKTEST_DATES:
            test.append(msg)
            print(f"  → TEST  {rec['date_target']}  pass_id={rec['pass_id']}")
        else:
            train.append(msg)

    return train, test


def split_handauthored() -> tuple[list[dict], list[dict]]:
    train, test = [], []
    if not HANDAUTHORED_DIR.exists():
        return train, test
    for f in sorted(HANDAUTHORED_DIR.glob("*.jsonl")):
        for line in f.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            row = json.loads(line)
            # Extract pass_id from the gold JSON
            gold_str = row["messages"][2]["content"][0]["text"]
            pass_id = json.loads(gold_str)["pass_id"]
            if pass_id in HELD_OUT_HANDAUTHORED_PASSIDS:
                test.append(row)
                print(f"  → TEST  hand-authored  pass_id={pass_id}  ({f.name})")
            else:
                train.append(row)
    return train, test


def main():
    DATASET_ROOT.mkdir(parents=True, exist_ok=True)

    auto_train, auto_test = build_auto_examples("jagersfontein")
    print(f"[split] auto:  {len(auto_train)} train, {len(auto_test)} test")

    hand_train, hand_test = split_handauthored()
    print(f"[split] hand:  {len(hand_train)} train, {len(hand_test)} test")

    train = auto_train + hand_train
    test = auto_test + hand_test
    print(f"[split] TOTAL: {len(train)} train, {len(test)} test "
          f"({100*len(test)/(len(train)+len(test)):.1f}% held-out)")

    TRAIN_PATH.write_text("\n".join(json.dumps(r) for r in train) + "\n")
    TEST_PATH.write_text("\n".join(json.dumps(r) for r in test) + "\n")
    SPLIT_PATH.write_text(json.dumps({
        "held_out_backtest_dates": HELD_OUT_BACKTEST_DATES,
        "held_out_handauthored_passids": sorted(HELD_OUT_HANDAUTHORED_PASSIDS),
        "n_train": len(train), "n_test": len(test),
    }, indent=2))
    print(f"\nWrote:")
    print(f"  {TRAIN_PATH} ({TRAIN_PATH.stat().st_size/1024:.0f} KB)")
    print(f"  {TEST_PATH}  ({TEST_PATH.stat().st_size/1024:.0f} KB)")
    print(f"  {SPLIT_PATH}")


if __name__ == "__main__":
    main()
