"""Spike 2 — SimSat archive loop.

Pulls Sentinel-2 tiles for Jagersfontein through the SimSat sim API
(localhost:9005), validating that the criterion-1 path works end-to-end
and the stock Element 84 backend is healthy.

Steps:
  1. Gating test: pull 3 known-good dates, expect at least one to return
     image_available=true.
  2. Curated 5-date pull aligned with Torres-Cruz milestones.
  3. Rolling 16-month hit-rate window (2021-06 -> 2022-10).
  4. Compare 2016-10-27 + 2021-12-30 SimSat-pulled tiles against the
     Spike 1 MSPC cache.
  5. (Stretch) NDWI render of the 2021-12-30 tile.

Outputs:
  spikes/data/simsat-tiles/<label>.json   metadata + base64 PNG bytes
  spikes/data/png/<label>_simsat_rgb.png  rendered RGB tile (sim API output)
  spikes/data/png/pre_failure_simsat_ndwi.png   if step 5 ran
  spikes/out/simsat-archive-summary.json  full hit-rate table
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import requests
from PIL import Image

# -------------------------- constants -------------------------- #

JAGERSFONTEIN_LAT = -29.756
JAGERSFONTEIN_LON = 25.428
SIZE_KM = 5.0
SIM_BASE = "http://localhost:9005"

# SimSat default window is 10 days. Widen to 30 days to mirror Spike 1's
# pull windows so SimSat-vs-MSPC comparisons see the same archive coverage.
WINDOW_SECONDS = 30 * 24 * 60 * 60

REPO_ROOT = Path("/mnt/c/Users/peter/SatDiff")
SPIKE_DIR = REPO_ROOT / "spikes"
DATA_DIR = SPIKE_DIR / "data"
OUT_DIR = SPIKE_DIR / "out"
SIMSAT_TILES_DIR = DATA_DIR / "simsat-tiles"
PNG_DIR = DATA_DIR / "png"
MSPC_CACHE_DIR = DATA_DIR / "tiles"  # Spike 1's MSPC cache for cross-check

# Step-2 gating dates — at least one is expected to return.
GATING_DATES = [
    ("2021-12-30T08:00:00", "gating_pre_failure"),
    ("2016-10-27T08:00:00", "gating_baseline"),
    ("2022-09-15T08:00:00", "gating_post_failure"),
]

# Step-3 curated Torres-Cruz milestone dates.
CURATED_DATES = [
    ("2016-10-27T08:00:00", "baseline_2016_10"),
    ("2019-02-15T08:00:00", "torres_cruz_first_gully_2019_02"),
    ("2020-12-15T08:00:00", "dws_directive_2020_12"),
    ("2021-12-30T08:00:00", "pre_failure_pond_at_wall_2021_12"),
    ("2022-09-15T08:00:00", "post_failure_2022_09"),
]

# Step-4 rolling window: monthly polls 2021-06 -> 2022-10 inclusive.
def rolling_window_dates() -> list[tuple[str, str]]:
    out = []
    d = datetime(2021, 6, 15, 8, 0, 0)
    end = datetime(2022, 10, 15, 8, 0, 0)
    while d <= end:
        ts = d.strftime("%Y-%m-%dT%H:%M:%S")
        label = f"rolling_{d.strftime('%Y_%m')}"
        out.append((ts, label))
        d = (d.replace(day=1) + timedelta(days=32)).replace(day=15, hour=8)
    return out


# Bands for the SimSat ingress test. PNG mode in SimSat's image_to_png
# only accepts 1 or 3 bands, so we test RGB through the API. The
# 5-band multispectral that Phase 1 needs goes through return_type=array
# (exercised once in render_ndwi as a roundtrip check) — the full
# multispectral pipeline reads from Spike 1's MSPC cache for now.
BANDS = ["red", "green", "blue"]


# ---------------------------- HTTP ----------------------------- #


def fetch_simsat_tile(timestamp: str, bands: list[str] = BANDS,
                      size_km: float = SIZE_KM, return_type: str = "png",
                      timeout: float = 120.0) -> dict[str, Any]:
    """Call SimSat /data/image/sentinel and return parsed result + metadata.

    For return_type='png', metadata is in the `sentinel_metadata` header
    (JSON). For 'array', metadata is in the response body.
    """
    params = {
        "lon": JAGERSFONTEIN_LON,
        "lat": JAGERSFONTEIN_LAT,
        "timestamp": timestamp,
        "spectral_bands": bands,
        "size_km": size_km,
        "window_seconds": WINDOW_SECONDS,
        "return_type": return_type,
    }
    t0 = time.perf_counter()
    try:
        r = requests.get(f"{SIM_BASE}/data/image/sentinel", params=params, timeout=timeout)
    except requests.RequestException as e:
        return {"ok": False, "error": str(e), "latency_seconds": time.perf_counter() - t0}
    latency = time.perf_counter() - t0

    if r.status_code != 200:
        return {"ok": False, "status": r.status_code, "body": r.text[:500],
                "latency_seconds": latency}

    if return_type == "png":
        try:
            meta = json.loads(r.headers.get("sentinel_metadata", "{}"))
        except json.JSONDecodeError:
            meta = {}
        return {
            "ok": True,
            "metadata": meta,
            "image_bytes": r.content,
            "latency_seconds": latency,
        }
    else:
        body = r.json()
        return {
            "ok": True,
            "metadata": body.get("sentinel_metadata", {}),
            "image": body.get("image"),
            "latency_seconds": latency,
        }


# --------------------------- helpers --------------------------- #


def save_tile(label: str, result: dict[str, Any]) -> dict[str, Any]:
    """Persist tile bytes + metadata. Returns a summary record."""
    SIMSAT_TILES_DIR.mkdir(parents=True, exist_ok=True)
    PNG_DIR.mkdir(parents=True, exist_ok=True)

    rec: dict[str, Any] = {
        "label": label,
        "ok": result.get("ok", False),
        "latency_seconds": round(result.get("latency_seconds", 0.0), 2),
        "image_available": False,
        "cloud_cover": None,
        "datetime": None,
        "source": None,
        "bytes": 0,
    }
    if not result.get("ok"):
        rec["error"] = result.get("error") or result.get("body", f"HTTP {result.get('status')}")
        return rec

    meta = result.get("metadata", {}) or {}
    rec["image_available"] = bool(meta.get("image_available"))
    rec["cloud_cover"] = meta.get("cloud_cover")
    rec["datetime"] = meta.get("datetime")
    rec["source"] = meta.get("source")

    img_bytes = result.get("image_bytes") or b""
    rec["bytes"] = len(img_bytes)

    # Persist the raw response so we can replay later without re-hitting the API.
    tile_meta_path = SIMSAT_TILES_DIR / f"{label}.json"
    tile_meta_path.write_text(json.dumps({
        "metadata": meta,
        "image_b64": base64.b64encode(img_bytes).decode("ascii") if img_bytes else "",
    }))

    if rec["image_available"] and img_bytes:
        png_path = PNG_DIR / f"{label}_simsat.png"
        png_path.write_bytes(img_bytes)

    return rec


def compare_to_mspc(label: str, mspc_label: str) -> dict[str, Any]:
    """For 2016-10-27 and 2021-12-30, compare SimSat tile to Spike 1's MSPC cache."""
    simsat_meta = SIMSAT_TILES_DIR / f"{label}.json"
    mspc_npz = MSPC_CACHE_DIR / f"{mspc_label}.npz"
    out: dict[str, Any] = {"simsat_label": label, "mspc_label": mspc_label}

    if not simsat_meta.exists():
        out["error"] = "simsat tile missing"
        return out
    if not mspc_npz.exists():
        out["error"] = "mspc cache missing"
        return out

    simsat = json.loads(simsat_meta.read_text())
    smeta = simsat.get("metadata", {})
    out["simsat_datetime"] = smeta.get("datetime")
    out["simsat_cloud"] = smeta.get("cloud_cover")
    out["simsat_source"] = smeta.get("source")

    with np.load(mspc_npz, allow_pickle=True) as z:
        m_meta = z["__meta__"].item()
    out["mspc_datetime"] = m_meta.get("chosen_date")
    out["mspc_cloud"] = m_meta.get("cloud_cover")
    out["mspc_item"] = m_meta.get("item_id")

    # Strict byte comparison would need both pulled as arrays in the same
    # CRS/resolution — out of scope for the spike. Comparing acquisition
    # metadata is enough to confirm "same underlying scene".
    out["same_acquisition_date"] = (
        out["simsat_datetime"] is not None
        and out["mspc_datetime"] is not None
        and out["simsat_datetime"][:10] == out["mspc_datetime"][:10]
    )
    return out


def render_ndwi(label: str = "pre_failure_pond_at_wall_2021_12") -> dict[str, Any]:
    """Step 6 stretch: pull green+nir as 'array' return_type and compute NDWI."""
    bands = ["green", "nir"]
    timestamp, _ = next((t, l) for t, l in CURATED_DATES if l == label)
    res = fetch_simsat_tile(timestamp, bands=bands, return_type="array")
    if not res.get("ok"):
        return {"ok": False, "error": res.get("error") or "fetch failed"}

    meta = res.get("metadata", {}) or {}
    if not meta.get("image_available"):
        return {"ok": False, "error": "image_available false"}

    arr_blob = res.get("image")  # serialized xarray
    # The serializer is custom in SimSat (serialize_xarray_dataset). We can
    # decode here if needed; for the spike, we just confirm the array path
    # roundtrips and skip rendering when serializer details are unclear.
    return {
        "ok": True,
        "datetime": meta.get("datetime"),
        "cloud_cover": meta.get("cloud_cover"),
        "note": "array roundtripped; NDWI render deferred to local computation from MSPC cache (Phase 1).",
    }


# ---------------------------- main ---------------------------- #


def smoke_check() -> bool:
    """Confirm SimSat is reachable before touching the imagery endpoint."""
    try:
        r = requests.get(f"{SIM_BASE}/data/current/position", timeout=10)
    except requests.RequestException as e:
        print(f"[smoke] sim API unreachable: {e}")
        return False
    if r.status_code != 200:
        print(f"[smoke] sim API HTTP {r.status_code}: {r.text[:300]}")
        return False
    print(f"[smoke] sim API ok: {r.json()}")
    return True


def run_step(name: str, dates: list[tuple[str, str]]) -> list[dict[str, Any]]:
    print(f"\n=== {name} ({len(dates)} dates) ===")
    rows: list[dict[str, Any]] = []
    for ts, label in dates:
        print(f"[fetch] {label}  ts={ts}")
        res = fetch_simsat_tile(ts)
        rec = save_tile(label, res)
        avail = "y" if rec["image_available"] else "n"
        cc = f"{rec['cloud_cover']:.1f}%" if isinstance(rec["cloud_cover"], (int, float)) else "-"
        dt = rec["datetime"] or "-"
        print(f"  -> available={avail}  cloud={cc}  datetime={dt}  "
              f"bytes={rec['bytes']}  latency={rec['latency_seconds']}s")
        rows.append(rec)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-rolling", action="store_true",
                    help="Skip the 16-month rolling hit-rate window (step 4).")
    ap.add_argument("--gating-only", action="store_true",
                    help="Only run step 1 + step 2 (smoke + gating test).")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not smoke_check():
        print("[main] sim API not reachable; abort.", file=sys.stderr)
        return 1

    summary: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "sim_base": SIM_BASE,
        "lat": JAGERSFONTEIN_LAT, "lon": JAGERSFONTEIN_LON,
        "size_km": SIZE_KM, "window_seconds": WINDOW_SECONDS,
        "gating": [],
        "curated": [],
        "rolling": [],
        "comparisons": [],
    }

    summary["gating"] = run_step("Step 2 — gating test", GATING_DATES)
    avail_count = sum(1 for r in summary["gating"] if r["image_available"])
    print(f"\n[gating] {avail_count}/{len(GATING_DATES)} known-good dates returned tiles")
    if avail_count == 0:
        print("[gating] ALL THREE FAILED — escalate to step 2b (tail-risk MSPC patch).",
              file=sys.stderr)
        # We still write the partial summary so the failure is documented.
        (OUT_DIR / "simsat-archive-summary.json").write_text(json.dumps(summary, indent=2))
        return 2

    if args.gating_only:
        (OUT_DIR / "simsat-archive-summary.json").write_text(json.dumps(summary, indent=2))
        print("[main] --gating-only set; stopping after gating.")
        return 0

    summary["curated"] = run_step("Step 3 — curated Torres-Cruz dates", CURATED_DATES)

    if not args.skip_rolling:
        summary["rolling"] = run_step("Step 4 — rolling 16-month window",
                                       rolling_window_dates())
    else:
        print("[main] --skip-rolling; skipping step 4")

    # Step 3 cross-check vs Spike 1 MSPC cache.
    print("\n=== SimSat vs MSPC acquisition-date cross-check ===")
    for simsat_label, mspc_label in [
        ("baseline_2016_10", "baseline"),
        ("pre_failure_pond_at_wall_2021_12", "pre_failure"),
    ]:
        cmp = compare_to_mspc(simsat_label, mspc_label)
        summary["comparisons"].append(cmp)
        print(f"  {simsat_label} <-> {mspc_label}: same_date={cmp.get('same_acquisition_date')} "
              f"simsat={cmp.get('simsat_datetime')} mspc={cmp.get('mspc_datetime')}")

    # Aggregate stats.
    avail_curated = sum(1 for r in summary["curated"] if r["image_available"])
    avail_rolling = sum(1 for r in summary["rolling"] if r["image_available"])
    summary["stats"] = {
        "gating_hit_rate": f"{avail_count}/{len(summary['gating'])}",
        "curated_hit_rate": f"{avail_curated}/{len(summary['curated'])}",
        "rolling_hit_rate": (f"{avail_rolling}/{len(summary['rolling'])}"
                              if summary["rolling"] else "skipped"),
        "median_latency_seconds_curated": (
            float(np.median([r["latency_seconds"] for r in summary["curated"]]))
            if summary["curated"] else None
        ),
    }
    print("\n=== Summary ===")
    for k, v in summary["stats"].items():
        print(f"  {k}: {v}")

    out_path = OUT_DIR / "simsat-archive-summary.json"
    out_path.write_text(json.dumps(summary, indent=2))
    print(f"[main] wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
