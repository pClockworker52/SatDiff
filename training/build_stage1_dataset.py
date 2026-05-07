"""Stage 1 dataset converter: VRSBench → leap-finetune VLM SFT JSONL.

VRSBench ships 142K conversation records over 20K unique remote-sensing
images, tagged `[caption]`, `[refer]`, `[vqa]` in the human turn. We
exclude `[refer]` (bbox-coord output, not useful for SatDiff) and emit a
balanced mix of captions + VQA in the leap-finetune messages format
(see leap-finetune README "Expected Dataset Formats — VLM SFT").

Output:
    /home/peter/datasets/vrsbench/satdiff_stage1.jsonl
        ~5K examples; 50/50 caption/VQA mix; absolute image paths into
        the unzipped Images_train/ directory.

Run after Images_train.zip has been extracted under
/home/peter/datasets/vrsbench/Images_train/.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter
from pathlib import Path

DATA_DIR = Path("/home/peter/datasets/vrsbench")
ANNOT_PATH = DATA_DIR / "VRSBench_train.json"
IMAGES_DIR = DATA_DIR / "Images_train"
OUT_PATH = DATA_DIR / "satdiff_stage1.jsonl"

TAG_RX = re.compile(r"\[([a-z]+)\]")
SYSTEM_PROMPT = (
    "You are a remote-sensing vision assistant. Answer questions about the "
    "given satellite image, or describe its visible features when asked."
)


def _strip_tag_and_image_marker(text: str) -> str:
    """Remove '<image>' marker and '[task]' tag from the human turn.

    Original: "<image>\n[caption] Describe the image in detail."
    Returns:  "Describe the image in detail."
    """
    t = text.replace("<image>", "")
    t = TAG_RX.sub("", t, count=1)
    return t.strip()


def _to_messages(image_path: Path, user_text: str, assistant_text: str) -> dict:
    return {
        "messages": [
            {"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]},
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": str(image_path)},
                    {"type": "text", "text": user_text},
                ],
            },
            {"role": "assistant", "content": [{"type": "text", "text": assistant_text}]},
        ]
    }


def _classify(record: dict) -> str | None:
    """Return one of 'caption' / 'refer' / 'vqa' / None for the record."""
    if not record.get("conversations"):
        return None
    first = record["conversations"][0]["value"]
    m = TAG_RX.search(first)
    return m.group(1) if m else None


def build(*, n_caption: int, n_vqa: int, seed: int, out_path: Path,
          require_image_exists: bool) -> None:
    print(f"Loading {ANNOT_PATH}…")
    records = json.loads(ANNOT_PATH.read_text())
    print(f"  {len(records)} records")

    # Bucket by task
    buckets: dict[str, list[dict]] = {"caption": [], "vqa": [], "refer": []}
    for r in records:
        cls = _classify(r)
        if cls in buckets:
            buckets[cls].append(r)
    print(f"  caption={len(buckets['caption'])}  vqa={len(buckets['vqa'])}  refer={len(buckets['refer'])} (skipped)")

    rng = random.Random(seed)
    sampled_caption = rng.sample(buckets["caption"], min(n_caption, len(buckets["caption"])))
    sampled_vqa = rng.sample(buckets["vqa"], min(n_vqa, len(buckets["vqa"])))
    print(f"  sub-sampled: {len(sampled_caption)} captions + {len(sampled_vqa)} vqa = {len(sampled_caption)+len(sampled_vqa)}")

    out_lines: list[str] = []
    skipped_missing = 0
    for r in sampled_caption + sampled_vqa:
        img_path = IMAGES_DIR / r["image"]
        if require_image_exists and not img_path.exists():
            skipped_missing += 1
            continue
        convs = r["conversations"]
        if len(convs) < 2 or convs[0]["from"] != "human" or convs[1]["from"] != "gpt":
            continue
        user_text = _strip_tag_and_image_marker(convs[0]["value"])
        assistant_text = convs[1]["value"].strip()
        if not user_text or not assistant_text:
            continue
        out_lines.append(json.dumps(_to_messages(img_path, user_text, assistant_text)))

    rng.shuffle(out_lines)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(out_lines) + "\n")
    print(f"\nWrote {len(out_lines)} examples to {out_path}")
    if skipped_missing:
        print(f"  (skipped {skipped_missing} records whose images were not found on disk)")
    print(f"  size: {out_path.stat().st_size / 1024 / 1024:.1f} MB")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-caption", type=int, default=2500)
    ap.add_argument("--n-vqa", type=int, default=2500)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, default=OUT_PATH)
    ap.add_argument("--no-image-check", action="store_true",
                    help="Don't verify image files exist (use before unzip is done)")
    args = ap.parse_args(argv)
    build(
        n_caption=args.n_caption,
        n_vqa=args.n_vqa,
        seed=args.seed,
        out_path=args.out,
        require_image_exists=not args.no_image_check,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
