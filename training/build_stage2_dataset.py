"""Stage 2 dataset converter: SatDiff Phase 2 backtest passes → vlm_sft JSONL.

Why this exists: Phase 2's rules engine documented exactly which severity
tiers the base LFM2.5-VL-450M gets wrong (`severity_corrections` metric).
Stage 2 fine-tunes on (image-pair, Stage-B prompt, rules-engine-correct
JSON) so the model internalises the threshold logic and can ship the
canonical contract output without the rules-engine overlay.

Sources:
    Auto: phase2/out/<asset>/*.json — every Phase-1-invoked pass already
        has its rendered images, the populated Stage B prompt input, and
        a verified-correct overlay JSON.
    Hand-authored: training/stage2_handauthored/*.jsonl — the user drops
        manually-curated edge-case examples here. The combiner appends
        them after the auto-generated set.

Output: /home/peter/datasets/satdiff_stage2/satdiff_stage2.jsonl

Run order:
    1. python -m phase2.cli --asset jagersfontein --date-range … (already done)
    2. python training/build_stage2_dataset.py --rebuild-images
    3. (user hand-authors files into training/stage2_handauthored/)
    4. python training/build_stage2_dataset.py --combine

The image render step writes 4 PNGs per pass (baseline RGB+NIR, current
RGB+NIR) to /home/peter/datasets/satdiff_stage2/images/ at the same 512×512
size phase2/render.py uses, so the fine-tune sees imagery identical to
what phase2/runner.py shows the model at inference time.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running this script without PYTHONPATH gymnastics.
sys.path.insert(0, "/mnt/c/Users/peter/SatDiff")

from phase1.baseline import load_baseline
from phase1.loader import load_pass as load_pass_ds
from phase2.prompt import build_stage_b_prompt
from phase2.render import render_pass
from phase2.runner import schema_text

REPO_ROOT = Path("/mnt/c/Users/peter/SatDiff")
PHASE2_OUT = REPO_ROOT / "phase2" / "out"
HANDAUTHORED_DIR = REPO_ROOT / "training" / "stage2_handauthored"
DATASET_ROOT = Path("/home/peter/datasets/satdiff_stage2")
IMAGES_DIR = DATASET_ROOT / "images"
JSONL_PATH = DATASET_ROOT / "satdiff_stage2.jsonl"

SYSTEM_PROMPT = (
    "You are SatDiff, a satellite-borne monitoring assistant. You assess "
    "tailings-storage facilities against a regulatory contract and emit a "
    "strict-JSON pass report following the supplied output schema."
)


def _save_pass_images(asset_id: str, pass_record: dict) -> tuple[Path, Path, Path, Path]:
    """Render baseline + current RGB + NIR PNGs to disk; return absolute paths.

    Note: phase1.loader.load_pass keys its NetCDF cache on the *target* date
    (the date you ask for), not the SimSat-returned acquisition_date. The
    Phase 2 record's `date_target` field is the right key here.
    """
    baseline = load_baseline(asset_id)
    baseline_date = baseline["chosen_date"]
    date_target = pass_record["date_target"]
    acquisition_date = pass_record["phase1_diff"]["acquisition_date"]

    base_ds = load_pass_ds(asset_id, baseline_date)
    cur_ds = load_pass_ds(asset_id, date_target)
    base_imgs = render_pass(base_ds)
    cur_imgs = render_pass(cur_ds)

    asset_dir = IMAGES_DIR / asset_id
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


def _to_messages(image_paths: tuple[Path, Path, Path, Path],
                 stage_b_prompt: str, gold_json: dict) -> dict:
    """leap-finetune VLM SFT messages format: system + user(images+text) + assistant."""
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


def build_auto_examples(asset_id: str = "jagersfontein") -> list[dict]:
    """One messages-format example per Phase-2-invoked pass.

    Each example pairs the exact Stage B prompt that phase2/runner.py would
    have shown the model with the rules-engine-corrected output (the JSON
    that lives in `stage_b_parsed` after the overlay). This is gold by
    construction because Stage 2's whole point is to teach the model what
    the rules engine knows.
    """
    asset_dir = PHASE2_OUT / asset_id
    if not asset_dir.exists():
        raise FileNotFoundError(
            f"No Phase 2 outputs at {asset_dir} — run `python -m phase2.cli "
            f"--asset {asset_id} --date-range …` first."
        )

    baseline = load_baseline(asset_id)
    schema = schema_text()

    examples: list[dict] = []
    pass_files = sorted(p for p in asset_dir.glob("*.json")
                        if p.name not in {"summary.json"} and p.name[:4].isdigit())
    print(f"[stage2] {len(pass_files)} Phase 2 pass files for asset={asset_id}")

    for pf in pass_files:
        rec = json.loads(pf.read_text())
        if not rec.get("image_available"):
            continue
        gold = rec.get("stage_b_parsed")
        diff = rec.get("phase1_diff")
        stage_a_text = rec.get("stage_a_text", "")
        if not (gold and diff and stage_a_text):
            print(f"  skipping {pf.name}: missing gold / diff / stage_a")
            continue

        image_paths = _save_pass_images(asset_id, rec)
        prompt = build_stage_b_prompt(
            baseline=baseline,
            diff=diff,
            stage_a_text=stage_a_text,
            prior_reports=[],
            schema_text=schema,
            pass_id=rec["pass_id"],
        )
        examples.append(_to_messages(image_paths, prompt, gold))

    print(f"[stage2] built {len(examples)} auto examples")
    return examples


def load_handauthored() -> list[dict]:
    """Concatenate every JSONL in training/stage2_handauthored/."""
    if not HANDAUTHORED_DIR.exists():
        return []
    rows: list[dict] = []
    for f in sorted(HANDAUTHORED_DIR.glob("*.jsonl")):
        for line in f.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            rows.append(json.loads(line))
    print(f"[stage2] loaded {len(rows)} hand-authored examples from {HANDAUTHORED_DIR}")
    return rows


def write_dataset(rows: list[dict]) -> None:
    DATASET_ROOT.mkdir(parents=True, exist_ok=True)
    JSONL_PATH.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    print(f"[stage2] wrote {len(rows)} examples to {JSONL_PATH}")
    print(f"[stage2]   size: {JSONL_PATH.stat().st_size / 1024 / 1024:.1f} MB")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset", default="jagersfontein")
    ap.add_argument("--auto-only", action="store_true",
                    help="Skip hand-authored examples (build from Phase 2 outputs only).")
    args = ap.parse_args(argv)

    auto = build_auto_examples(args.asset)
    if args.auto_only:
        rows = auto
    else:
        manual = load_handauthored()
        rows = auto + manual
    write_dataset(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
