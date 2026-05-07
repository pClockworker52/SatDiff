"""Spike 1 — LFM2-VL on Jagersfontein Sentinel-2.

Pulls a known-signal Sentinel-2 L2A image pair for the Jagersfontein TSF
(clean baseline 2016-09, pond-at-wall 2021-12), runs LFM2-VL with the
contract prompt, and grades whether the base model can produce
contract-schema JSON that names the right geographic features.

Decision artefact: research/spike-1-findings.md (written separately).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import jsonschema
from PIL import Image

# Geo + STAC imports are deferred to keep --help fast.

# -------------------------- constants -------------------------- #

JAGERSFONTEIN_LAT = -29.756
JAGERSFONTEIN_LON = 25.428
BBOX_KM = 5.0  # square side in km, centred on the TSF
TARGET_PX = 512  # LFM2-VL native input

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
STAC_COLLECTION = "sentinel-2-l2a"

# Baseline target slid from 2016-09 to 2016-11: T35JLH only entered the
# Sentinel-2A revisit cadence reliably from late 2016 (S2B launched 2017).
# Both dates are clean-baseline pre-anomaly per Torres-Cruz timeline (first
# erosion gullies in Feb 2019).
BASELINE_DATE = "2016-11-15"
PRE_FAILURE_DATE = "2021-12-01"
DATE_HALF_WINDOW_DAYS = 30
CLOUD_COVER_MAX = 5

BANDS = ["blue", "green", "red", "nir", "swir16"]  # B2, B3, B4, B8, B11

MODEL_IDS = {
    "450M": "LiquidAI/LFM2.5-VL-450M",
    "1.6B": "LiquidAI/LFM2.5-VL-1.6B",
    # Older series, fallback if LFM2.5 has incompatible processor
    "450M-old": "LiquidAI/LFM2-VL-450M",
    "1.6B-old": "LiquidAI/LFM2-VL-1.6B",
}

REPO_ROOT = Path("/mnt/c/Users/peter/SatDiff")
SPIKE_DIR = REPO_ROOT / "spikes"
DATA_DIR = SPIKE_DIR / "data"
OUT_DIR = SPIKE_DIR / "out"
SCHEMA_PATH = SPIKE_DIR / "schema.json"


# ----------------------- contract prompt ----------------------- #

# Lifted verbatim from research/contract-prompts/jagersfontein-contract.md
# lines 78-149 (system + contract + I/O structure). Physical-diff values are
# placeholder for the spike — Phase 1 builds the diff module that fills these.

CONTRACT_PROMPT = """[SYSTEM]
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

Claim 1 — Containment geometry and asymmetric deposition
  Operator warrants symmetric deposition, fill within permitted footprint.
  Violation signatures: sustained one-sided filling in RGB; fill beyond
  design footprint; absent tailings beach between pond and retaining wall.
  Sensors: Sentinel-2 RGB (B2/B3/B4) + B8 NIR.

Claim 2 — Pond management (Jagersfontein smoking gun)
  Operator warrants free supernatant water clear of retaining wall by the
  design buffer; pond area within permitted volume.
  Violation signatures: pond within design buffer of retaining-wall crest;
  pond area > licence volume; absence of tailings beach between pond and
  wall.
  Sensors: Sentinel-2 NDWI (B3/B8), MNDWI (B3/B11); turbidity ratio
  (B4/B3); Sentinel-1 SAR for cloud-penetrating extent.

Claim 3 — Surface integrity of retaining wall (erosion gullies, seepage)
  Operator warrants no progressive surface erosion, gullying, or external
  seepage on dam walls.
  Violation signatures: erosion gullies > 4 m wide detectable in 10 m
  Sentinel-2; visible wet patches / seepage staining; NDMI/SWIR anomalies
  on wall face.
  Sensors: RGB + B8 for gully morphology; NDMI (B8/B11); SWIR (B11/B12).

Claim 4 — Surface deformation
  Operator warrants no non-consolidation deformation exceeding engineering
  thresholds.
  Violation signatures: deformation > 10 mm/yr sustained; outward bulging
  of dam wall; localised subsidence with adjacent uplift.
  Sensors: Sentinel-1 SAR SBAS/PSI; TerraSAR-X / COSMO-SkyMed.

Claim 5 — Downstream community protection zone
  Operator warrants no indication that a containment failure would exceed
  the run-out envelope; downstream protected zone (Kopanong Local
  Municipality) remains outside hazard projection.
  Violation signatures: changes in upstream conditions that expand
  modelled run-out; residents/infrastructure within high-consequence zone.
  Sensors: Sentinel-2 + population/infrastructure overlays.

[BASELINE]
Acquisition date: {baseline_date}
Imagery: RGB + NIR-false-colour composites of the impoundment, retaining
wall, pond, downstream slope, and protected-zone polygons. (Image 1: RGB.
Image 2: NIR-false-colour, B8/B4/B3 channel mapping.)

[CURRENT PASS]
Acquisition date: {current_date}
Imagery: RGB + NIR-false-colour composites of the same scene. (Image 3:
RGB. Image 4: NIR-false-colour, B8/B4/B3 channel mapping.)

Physical-diff summary (numerical): null — not provided in this spike;
ground all claim assessments in the imagery alone.

[PRIOR REPORTS]
[]

[OUTPUT SCHEMA]
{schema_block}

[OUTPUT INSTRUCTIONS]
- For each claim, the `evidence` field MUST describe a specific observation
  you made by comparing the baseline and current-pass imagery (e.g.
  "pond extends to the south-west wall in the 2021 image; baseline 2016
  shows ~150 m of dry tailings beach between pond and wall"). Do NOT
  restate which sensors or bands are used — the contract already says that.
  If you cannot see a feature in the imagery, the evidence must say so
  explicitly (e.g. "no SAR data available; severity nominal by default").
- `probability_trend` MUST be one of: "increased", "decreased", "unchanged".
- `severity_level` MUST be one of: "nominal", "elevated", "urgent".
- `recommended_action` MUST be one of: "none", "flag_for_review",
  "urgent_inspection". No other strings, no capitalisation.
- `overall_status` MUST be one of: "nominal", "elevated", "urgent".
- `downlink_priority` MUST be one of: "routine", "priority", "immediate".

Output ONLY the JSON object. No prose, no markdown fences. Use
acquisition_date "{current_date}" and pass_id "{pass_id}".
"""


# ------------------------- data classes ------------------------ #


@dataclass
class TileSet:
    label: str  # "baseline" or "pre_failure"
    target_date: str
    chosen_date: str
    cloud_cover: float
    item_id: str
    arrays: dict[str, np.ndarray] = field(default_factory=dict)  # band -> 2D array


# ---------------------------- STAC ----------------------------- #


def km_to_deg(km: float, lat: float) -> tuple[float, float]:
    """Approx degrees-of-lon/lat for a square of side ``km`` km at latitude ``lat``."""
    dlat = km / 111.0
    dlon = km / (111.0 * np.cos(np.radians(lat)))
    return dlon, dlat


def search_window(target_date: str, half_days: int = DATE_HALF_WINDOW_DAYS) -> str:
    from datetime import datetime, timedelta

    d = datetime.fromisoformat(target_date)
    start = (d - timedelta(days=half_days)).date().isoformat()
    end = (d + timedelta(days=half_days)).date().isoformat()
    return f"{start}/{end}"


def pull_tile(label: str, target_date: str) -> TileSet:
    from pystac_client import Client
    import odc.stac
    import planetary_computer

    cache = DATA_DIR / "tiles" / f"{label}.npz"
    if cache.exists():
        with np.load(cache, allow_pickle=True) as z:
            arrays = {b: z[b] for b in BANDS}
            meta = z["__meta__"].item()
        return TileSet(
            label=label,
            target_date=target_date,
            chosen_date=meta["chosen_date"],
            cloud_cover=meta["cloud_cover"],
            item_id=meta["item_id"],
            arrays=arrays,
        )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "tiles").mkdir(parents=True, exist_ok=True)

    dlon, dlat = km_to_deg(BBOX_KM, JAGERSFONTEIN_LAT)
    bbox = (
        JAGERSFONTEIN_LON - dlon / 2,
        JAGERSFONTEIN_LAT - dlat / 2,
        JAGERSFONTEIN_LON + dlon / 2,
        JAGERSFONTEIN_LAT + dlat / 2,
    )

    cli = Client.open(STAC_URL, modifier=planetary_computer.sign_inplace)

    def _search(window_days: int) -> Any:
        return cli.search(
            collections=[STAC_COLLECTION],
            bbox=bbox,
            datetime=search_window(target_date, window_days),
            query={"eo:cloud_cover": {"lt": CLOUD_COVER_MAX}},
            limit=20,
        )

    items = list(_search(DATE_HALF_WINDOW_DAYS).items())
    if not items:
        # Widen
        items = list(_search(60).items())
    if not items:
        raise RuntimeError(
            f"No cloud-free Sentinel-2 L2A tile found for {label} window around {target_date}"
        )

    items.sort(key=lambda it: it.properties.get("eo:cloud_cover", 100))
    chosen = items[0]
    print(
        f"[pull_tiles] {label}: chose {chosen.id} "
        f"({chosen.properties.get('datetime')[:10]}) "
        f"cloud={chosen.properties.get('eo:cloud_cover'):.1f}%"
    )

    # Load in the item's native UTM CRS at 10 m resolution. bbox is in
    # WGS84; odc-stac reprojects the bbox into the output CRS for cropping.
    # MSPC band names: B02..B12; map our band names accordingly.
    mspc_bands = {
        "blue": "B02", "green": "B03", "red": "B04",
        "nir": "B08", "swir16": "B11",
    }
    ds = odc.stac.load(
        [chosen],
        bands=list(mspc_bands.values()),
        bbox=bbox,
        resolution=10,
        chunks=None,
    )

    arrays: dict[str, np.ndarray] = {}
    for our_name, mspc_name in mspc_bands.items():
        arr = ds[mspc_name].isel(time=0).to_numpy()
        arrays[our_name] = arr.astype(np.float32)

    meta = {
        "chosen_date": chosen.properties["datetime"][:10],
        "cloud_cover": float(chosen.properties.get("eo:cloud_cover", 0.0)),
        "item_id": chosen.id,
    }
    np.savez_compressed(cache, **arrays, __meta__=meta)

    return TileSet(
        label=label,
        target_date=target_date,
        chosen_date=meta["chosen_date"],
        cloud_cover=meta["cloud_cover"],
        item_id=meta["item_id"],
        arrays=arrays,
    )


def pull_tiles() -> dict[str, TileSet]:
    return {
        "baseline": pull_tile("baseline", BASELINE_DATE),
        "pre_failure": pull_tile("pre_failure", PRE_FAILURE_DATE),
    }


# ----------------------- composite render ---------------------- #


def stretch(arr: np.ndarray, lo_pct: float = 2, hi_pct: float = 98) -> np.ndarray:
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return np.zeros_like(arr, dtype=np.uint8)
    lo, hi = np.percentile(finite, [lo_pct, hi_pct])
    if hi <= lo:
        hi = lo + 1
    out = np.clip((arr - lo) / (hi - lo), 0, 1)
    return (out * 255).astype(np.uint8)


def render_composites(tiles: dict[str, TileSet]) -> dict[str, Path]:
    png_dir = DATA_DIR / "png"
    png_dir.mkdir(parents=True, exist_ok=True)
    out: dict[str, Path] = {}

    for label, tile in tiles.items():
        rgb = np.dstack(
            [stretch(tile.arrays[b]) for b in ("red", "green", "blue")]
        )
        nir = np.dstack(
            [stretch(tile.arrays[b]) for b in ("nir", "red", "green")]
        )
        rgb_im = Image.fromarray(rgb).resize((TARGET_PX, TARGET_PX), Image.BILINEAR)
        nir_im = Image.fromarray(nir).resize((TARGET_PX, TARGET_PX), Image.BILINEAR)
        rgb_path = png_dir / f"{label}_rgb.png"
        nir_path = png_dir / f"{label}_nir.png"
        rgb_im.save(rgb_path)
        nir_im.save(nir_path)
        out[f"{label}_rgb"] = rgb_path
        out[f"{label}_nir"] = nir_path
        print(f"[render] {label}: wrote {rgb_path.name} {nir_path.name}")

    return out


# --------------------------- prompt ---------------------------- #


def build_prompt(baseline: TileSet, current: TileSet) -> tuple[str, str]:
    pass_id = f"jagersfontein-{current.chosen_date}"
    schema_block = SCHEMA_PATH.read_text()
    text = CONTRACT_PROMPT.format(
        baseline_date=baseline.chosen_date,
        current_date=current.chosen_date,
        pass_id=pass_id,
        schema_block=schema_block,
    )
    return text, pass_id


# --------------------------- model ----------------------------- #


@dataclass
class RunResult:
    raw_text: str
    parsed: Any | None
    parse_error: str | None
    latency_seconds: float
    peak_vram_gb: float
    model_id: str


def run_vlm(prompt: str, png_paths: dict[str, Path], model_id: str) -> RunResult:
    import torch
    from transformers import AutoProcessor, AutoModelForImageTextToText

    print(f"[run_vlm] loading {model_id} on cuda (bf16)...")
    processor = AutoProcessor.from_pretrained(model_id)
    model = AutoModelForImageTextToText.from_pretrained(
        model_id,
        device_map="auto",
        dtype="bfloat16",
    )
    model.eval()

    images = [
        Image.open(png_paths["baseline_rgb"]).convert("RGB"),
        Image.open(png_paths["baseline_nir"]).convert("RGB"),
        Image.open(png_paths["pre_failure_rgb"]).convert("RGB"),
        Image.open(png_paths["pre_failure_nir"]).convert("RGB"),
    ]

    # LFM2.5-VL conversation format embeds the PIL image objects directly
    # in the content list (not as `{"type": "image"}` markers + separate
    # images= arg). See https://huggingface.co/LiquidAI/LFM2.5-VL-450M README.
    image_labels = [
        "baseline RGB", "baseline NIR-false-colour",
        "current pass RGB", "current pass NIR-false-colour",
    ]
    content: list[dict] = []
    for label, image in zip(image_labels, images):
        content.append({"type": "image", "image": image})
    content.append({"type": "text", "text": prompt})
    messages = [{"role": "user", "content": content}]

    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        return_tensors="pt",
        return_dict=True,
        tokenize=True,
    ).to(model.device)

    torch.cuda.reset_peak_memory_stats(0)
    t0 = time.perf_counter()
    with torch.inference_mode():
        out_ids = model.generate(
            **inputs,
            max_new_tokens=1024,
            do_sample=False,
        )
    latency = time.perf_counter() - t0
    peak_vram = torch.cuda.max_memory_allocated(0) / 1024**3

    new_tokens = out_ids[0, inputs["input_ids"].shape[1]:]
    text = processor.tokenizer.decode(new_tokens, skip_special_tokens=True)

    parsed, err = _try_parse_json(text)

    return RunResult(
        raw_text=text,
        parsed=parsed,
        parse_error=err,
        latency_seconds=latency,
        peak_vram_gb=peak_vram,
        model_id=model_id,
    )


# ---------------------- output validation --------------------- #


def _try_parse_json(text: str) -> tuple[Any | None, str | None]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"```\s*$", "", cleaned)
    # Take the first {...} block if there's prose around it.
    m = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if m:
        cleaned = m.group(0)
    try:
        return json.loads(cleaned), None
    except json.JSONDecodeError as e:
        return None, str(e)


def evaluate(result: RunResult) -> dict[str, Any]:
    schema = json.loads(SCHEMA_PATH.read_text())
    summary: dict[str, Any] = {
        "model_id": result.model_id,
        "latency_seconds": round(result.latency_seconds, 2),
        "peak_vram_gb": round(result.peak_vram_gb, 2),
        "json_parses": result.parsed is not None,
        "parse_error": result.parse_error,
        "schema_valid": False,
        "schema_error": None,
        "claims_count": 0,
        "claims_with_evidence_mentioning_pond": 0,
        "claims_with_evidence_mentioning_impoundment_or_dam": 0,
        "claims_evidence": [],
    }

    if result.parsed is None:
        return summary

    try:
        jsonschema.validate(result.parsed, schema)
        summary["schema_valid"] = True
    except jsonschema.ValidationError as e:
        summary["schema_error"] = e.message

    claims = result.parsed.get("claims") if isinstance(result.parsed, dict) else None
    if isinstance(claims, list):
        summary["claims_count"] = len(claims)
        pond_re = re.compile(r"\bpond(s|ed|ing)?\b", re.IGNORECASE)
        imp_re = re.compile(
            r"\b(impoundment|impound(ed|ing)?|dam(s|wall|-wall|\swall)?|tailings)\b",
            re.IGNORECASE,
        )
        for c in claims:
            ev = c.get("evidence", "") if isinstance(c, dict) else ""
            summary["claims_evidence"].append(
                {
                    "id": c.get("id") if isinstance(c, dict) else None,
                    "name": c.get("name") if isinstance(c, dict) else None,
                    "severity_level": c.get("severity_level") if isinstance(c, dict) else None,
                    "evidence": ev,
                }
            )
            if pond_re.search(ev):
                summary["claims_with_evidence_mentioning_pond"] += 1
            if imp_re.search(ev):
                summary["claims_with_evidence_mentioning_impoundment_or_dam"] += 1
    return summary


def print_report(summary: dict[str, Any]) -> None:
    print("\n" + "=" * 60)
    print("SPIKE 1 — LFM2-VL JAGERSFONTEIN RUN SUMMARY")
    print("=" * 60)
    for k in (
        "model_id",
        "latency_seconds",
        "peak_vram_gb",
        "json_parses",
        "parse_error",
        "schema_valid",
        "schema_error",
        "claims_count",
        "claims_with_evidence_mentioning_pond",
        "claims_with_evidence_mentioning_impoundment_or_dam",
    ):
        print(f"  {k}: {summary[k]}")
    print("\nClaim evidence dump:")
    for c in summary["claims_evidence"]:
        print(f"  [{c['id']}] {c['name']} -> {c['severity_level']}")
        print(f"      {c['evidence']}")


# ---------------------------- main ---------------------------- #


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", choices=list(MODEL_IDS.keys()), default="450M")
    p.add_argument("--skip-vlm", action="store_true",
                   help="Pull tiles + render only; skip model load")
    args = p.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("[main] step 1: pull Sentinel-2 tiles")
    tiles = pull_tiles()
    for t in tiles.values():
        print(f"  {t.label}: {t.chosen_date} cloud={t.cloud_cover:.1f}% id={t.item_id}")

    print("[main] step 2: render composites")
    pngs = render_composites(tiles)

    if args.skip_vlm:
        print("[main] --skip-vlm; stopping after composites")
        return 0

    print("[main] step 3: build prompt")
    prompt, pass_id = build_prompt(tiles["baseline"], tiles["pre_failure"])

    print("[main] step 4: run LFM2-VL")
    result = run_vlm(prompt, pngs, MODEL_IDS[args.model])

    print("[main] step 5: evaluate")
    summary = evaluate(result)
    print_report(summary)

    ts = time.strftime("%Y%m%dT%H%M%S")
    safe_model = args.model.replace(".", "_")
    raw_path = OUT_DIR / f"{safe_model}_{ts}.txt"
    raw_path.write_text(result.raw_text)
    summary_path = OUT_DIR / f"{safe_model}_{ts}.summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"\n[main] wrote {raw_path.name} and {summary_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
