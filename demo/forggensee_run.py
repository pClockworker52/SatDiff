"""Demo prep — Stage A free-text describe on a Forggensee Sentinel-2 tile.

Drives the architectural-portability claim in the demo video's 4:00-4:30 segment:
the SatDiff Stage 1 model "looks at" the Forggensee dam in Bavaria and emits
descriptive prose. No contract pipeline is run (the contract schema is
TSF-specific; running it on a regulated water dam would produce misleading
output). The point is: same model, same architecture, different regulator.

Outputs:
    demo/forggensee_rgb.png        — RGB tile the model saw (512×512)
    demo/forggensee_nir.png        — NIR-false-colour tile (512×512)
    demo/forggensee_stage_a.txt    — model's free-text describe + provenance
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from phase1.loader import load_pass  # noqa: E402
from phase2.render import render_pass  # noqa: E402
from phase2.runner import make_vlm  # noqa: E402
from phase2.prompt import build_stage_a_prompt  # noqa: E402

os.environ.setdefault("SATDIFF_INFERENCE", "llama_server")
os.environ.setdefault("LLAMA_SERVER_URL", "http://localhost:8080")

OUT_DIR = REPO / "demo"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CANDIDATE_DATES = [
    "2024-07-15", "2024-08-15", "2024-06-15",
    "2024-07-30", "2024-08-30", "2024-06-30",
    "2023-07-15", "2023-08-15", "2023-06-15",
    "2023-07-30", "2023-08-30",
]


def pick_clean_pass() -> tuple[float, "object", str]:
    best = None
    for d in CANDIDATE_DATES:
        print(f"[forggensee] trying {d}…", flush=True)
        try:
            ds = load_pass("forggensee", d)
        except Exception as e:
            print(f"[forggensee]   error: {e}")
            continue
        if ds is None:
            print(f"[forggensee]   no image available")
            continue
        cc = float(ds.attrs.get("cloud_cover", 100.0))
        print(f"[forggensee]   cloud_cover={cc:.1f}%")
        if best is None or cc < best[0]:
            best = (cc, ds, d)
        if cc < 5.0:
            break
    return best


def main() -> int:
    best = pick_clean_pass()
    if best is None:
        print("[forggensee] no Sentinel-2 imagery found across candidates; aborting.")
        return 1

    cc, ds, date = best
    print(f"[forggensee] picked {date}, cloud_cover={cc:.1f}%")

    images = render_pass(ds)
    rgb, nir = images["rgb"], images["nir"]
    rgb.save(OUT_DIR / "forggensee_rgb.png")
    nir.save(OUT_DIR / "forggensee_nir.png")

    # Stage A normally compares baseline vs current. Forggensee has no SatDiff
    # baseline, so we feed the same imagery in both slots — the model's output
    # is then a description of the present scene without a diff narrative.
    images4 = [rgb, nir, rgb, nir]

    stage_a_prompt = build_stage_a_prompt(baseline_date=date, current_date=date)

    print("[forggensee] loading VLM…", flush=True)
    vlm = make_vlm()
    vlm.load()
    print("[forggensee] running Stage A…", flush=True)
    text, latency = vlm.generate(images4, stage_a_prompt, max_new_tokens=400)
    print(f"[forggensee] Stage A done in {latency:.2f}s")

    out_txt = OUT_DIR / "forggensee_stage_a.txt"
    out_txt.write_text(
        f"Forggensee Sentinel-2 acquisition: {date}\n"
        f"Cloud cover: {cc:.1f}%\n"
        f"Model: WobblyDopamine/SatDiff-LFM2.5-VL-450M-stage1-Q8_0 (via llama-server)\n"
        f"Stage A latency: {latency:.2f} s\n"
        f"\n--- MODEL OUTPUT ---\n{text}\n"
    )
    print(f"[forggensee] wrote demo/forggensee_rgb.png + forggensee_nir.png + forggensee_stage_a.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
