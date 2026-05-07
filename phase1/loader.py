"""Phase 1 data loader — pull Sentinel-2 multispectral tiles via SimSat.

Public surface:
    AssetSpec — small registry of (asset_id, lat, lon, size_km).
    load_pass(asset_id, date, *, force=False) -> xr.Dataset | None
        Returns an xarray.Dataset with red/green/blue/nir/swir16 bands at
        ~10 m resolution, or None if SimSat reports image_available=False
        for that date. Caches to phase1/data/<asset_id>/<date>.nc so the
        backtest can rerun without hammering SimSat.

The loader's call shape follows `spikes/archive-pull.py::fetch_simsat_tile`
(localhost:9005, GET /data/image/sentinel) but uses return_type=array so we
get all five bands as raw arrays instead of a 3-band PNG. Unpacks SimSat's
serialize_xarray_dataset format (see SimSat src/sim/api.py:15-29).

Intentionally tiny — no concurrency, no retries beyond a single per-call
timeout. The Phase 2 prompt pipeline calls this once per pass; the bulk
backtest in `phase1/cli.py` walks dates sequentially.
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import requests
import xarray as xr

# -------------------------- constants -------------------------- #

import os

SIM_BASE = os.environ.get("SIMSAT_URL", "http://localhost:9005")
DEFAULT_BANDS = ("red", "green", "blue", "nir", "swir16")

# 30-day SimSat search window — mirrors Spike 2's archive-pull config so any
# tile cache built there is interchangeable with what this loader fetches.
WINDOW_SECONDS = 30 * 24 * 60 * 60

REPO_ROOT = Path(os.environ.get("SATDIFF_REPO_ROOT", "/mnt/c/Users/peter/SatDiff"))
PHASE1_DIR = REPO_ROOT / "phase1"
DATA_DIR = PHASE1_DIR / "data"


# -------------------------- assets ----------------------------- #


@dataclass(frozen=True)
class AssetSpec:
    asset_id: str
    lat: float
    lon: float
    size_km: float = 5.0
    description: str = ""


ASSETS: dict[str, AssetSpec] = {
    "jagersfontein": AssetSpec(
        asset_id="jagersfontein",
        lat=-29.756,
        lon=25.428,
        size_km=5.0,
        # NB: keep these `description` strings outcome-neutral — backtest
        # integrity depends on prompts not leaking known future events. If
        # you ever surface a `description` into a prompt, audit it first.
        # See memory: `feedback_backtest_prompt_integrity.md`.
        description=(
            "Jagersfontein TSF, Free State, South Africa. Centre and 5 km "
            "tile size match Spike 1/2 + the masks in "
            "phase1/masks/jagersfontein.geojson."
        ),
    ),
    # Tier 2 — cross-asset routine reference assets (Stage 2 fine-tuning).
    "aswan": AssetSpec(
        asset_id="aswan",
        lat=23.971, lon=32.877, size_km=10.0,
        description="Aswan High Dam, Egypt. Tier 2 cross-asset reference for SatDiff.",
    ),
    "three_gorges": AssetSpec(
        asset_id="three_gorges",
        lat=30.823, lon=111.003, size_km=10.0,
        description="Three Gorges Dam, Yangtze River, China. Tier 2 cross-asset reference.",
    ),
    "hoover_mead": AssetSpec(
        asset_id="hoover_mead",
        lat=36.016, lon=-114.737, size_km=15.0,
        description="Hoover Dam / Lake Mead, Nevada-Arizona, USA. Tier 2 cross-asset reference.",
    ),
    "kariba": AssetSpec(
        asset_id="kariba",
        lat=-16.522, lon=28.762, size_km=15.0,
        description="Kariba Dam, Zambezi River, Zambia / Zimbabwe. Tier 2 cross-asset reference.",
    ),
    # Tier 3 — cross-asset catastrophic / distress reference assets.
    "brumadinho": AssetSpec(
        asset_id="brumadinho",
        lat=-20.119, lon=-44.122, size_km=10.0,
        description="Córrego do Feijão Mine, Minas Gerais, Brazil. Tier 3 cross-asset reference.",
    ),
    "mariana_fundao": AssetSpec(
        asset_id="mariana_fundao",
        lat=-20.198, lon=-43.469, size_km=10.0,
        description="Germano Mining Complex, Mariana, Minas Gerais, Brazil. Tier 3 cross-asset reference.",
    ),
    "toddbrook": AssetSpec(
        asset_id="toddbrook",
        lat=53.331, lon=-1.984, size_km=2.0,
        description="Toddbrook Reservoir, Whaley Bridge, Derbyshire, UK. Tier 3 cross-asset reference.",
    ),
    "edenville": AssetSpec(
        asset_id="edenville",
        # Centred on Wixom Lake (the impoundment), not the dam crest itself —
        # otherwise the 10 km tile is dominated by farmland with the lake at
        # the edge. This centring catches both the lake AND the dam.
        lat=43.79, lon=-84.43, size_km=10.0,
        description="Edenville Dam + Wixom Lake, Tittabawassee River, Michigan, USA. Tier 3 cross-asset reference.",
    ),
    "nova_kakhovka": AssetSpec(
        asset_id="nova_kakhovka",
        lat=46.778, lon=33.367, size_km=15.0,
        description="Nova Kakhovka Dam, Dnieper River, Ukraine. Tier 3 cross-asset reference.",
    ),
    "derna": AssetSpec(
        asset_id="derna",
        lat=32.760, lon=22.638, size_km=10.0,
        description="Derna dams (Bu Mansour and Al-Bilad), Wadi Derna, Libya. Tier 3 cross-asset reference.",
    ),
    "oroville": AssetSpec(
        asset_id="oroville",
        lat=39.539, lon=-121.485, size_km=5.0,
        description="Oroville Dam, California, USA. Tier 3 cross-asset reference.",
    ),
    "forggensee": AssetSpec(
        asset_id="forggensee",
        lat=47.57, lon=10.74, size_km=6.0,
        description=(
            "Forggensee, regulated dam on the Lech, Bavaria, Germany. Used for "
            "the demo-video sensor-/regulator-agnostic Stage A free-text describe; "
            "no SatDiff contract pipeline is run against this asset."
        ),
    ),
}


# ------------------------ HTTP / decode ------------------------ #


def _http_array_pull(asset: AssetSpec, timestamp: str, bands: tuple[str, ...],
                     timeout: float = 180.0) -> dict[str, Any]:
    """One GET to /data/image/sentinel?return_type=array."""
    params = {
        "lon": asset.lon,
        "lat": asset.lat,
        "timestamp": timestamp,
        "spectral_bands": list(bands),
        "size_km": asset.size_km,
        "window_seconds": WINDOW_SECONDS,
        "return_type": "array",
    }
    t0 = time.perf_counter()
    r = requests.get(f"{SIM_BASE}/data/image/sentinel", params=params, timeout=timeout)
    latency = time.perf_counter() - t0
    if r.status_code != 200:
        raise RuntimeError(
            f"SimSat returned {r.status_code}: {r.text[:300]}"
        )
    body = r.json()
    body["_latency_seconds"] = round(latency, 2)
    return body


def _decode_array_response(body: dict[str, Any], asset: AssetSpec,
                           bands: tuple[str, ...]) -> xr.Dataset | None:
    """Turn SimSat's array-mode response into an xr.Dataset, or None if no image."""
    sentinel_meta = body.get("sentinel_metadata") or {}
    if not sentinel_meta.get("image_available"):
        return None

    image_block = body.get("image") or {}
    img_meta = image_block.get("metadata") or {}
    shape = tuple(img_meta.get("shape", ()))
    dtype = img_meta.get("dtype")
    band_order = list(img_meta.get("bands", []))
    b64 = image_block.get("image")
    if not (shape and dtype and band_order and b64):
        raise RuntimeError(f"Malformed array response from SimSat: {img_meta!r}")

    raw = base64.b64decode(b64)
    arr = np.frombuffer(raw, dtype=np.dtype(dtype)).reshape(shape)
    # arr shape is (n_bands, H, W); band_order tells us which is which.

    # Re-order so columns match the caller's `bands` argument exactly.
    if set(band_order) != set(bands):
        raise RuntimeError(
            f"SimSat returned bands {band_order!r}; expected {list(bands)!r}"
        )
    band_idx = [band_order.index(b) for b in bands]
    arr = arr[band_idx]

    n_b, H, W = arr.shape

    # Pixel-to-WGS84 from the asset's bbox (SimSat returns the array in the
    # bbox we requested, top-left-origin, ~10 m/px).
    half_lat = asset.size_km / 111.0 / 2.0
    half_lon = asset.size_km / (111.0 * np.cos(np.radians(asset.lat))) / 2.0
    lon_w = asset.lon - half_lon
    lon_e = asset.lon + half_lon
    lat_s = asset.lat - half_lat
    lat_n = asset.lat + half_lat
    lons = np.linspace(lon_w, lon_e, W)
    lats = np.linspace(lat_n, lat_s, H)  # north -> south (top -> bottom)

    ds = xr.Dataset(
        data_vars={b: (("y", "x"), arr[i]) for i, b in enumerate(bands)},
        coords={"y": ("y", lats), "x": ("x", lons)},
        attrs={
            "asset_id": asset.asset_id,
            "asset_lat": asset.lat,
            "asset_lon": asset.lon,
            "size_km": asset.size_km,
            "window_seconds": WINDOW_SECONDS,
            "sentinel_datetime": sentinel_meta.get("datetime", ""),
            "sentinel_source": sentinel_meta.get("source", ""),
            "cloud_cover": float(sentinel_meta.get("cloud_cover", 0.0))
                          if sentinel_meta.get("cloud_cover") is not None else float("nan"),
            "footprint_w_s_e_n": list(sentinel_meta.get("footprint") or [lon_w, lat_s, lon_e, lat_n]),
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "loader_latency_seconds": body.get("_latency_seconds", 0.0),
        },
    )
    return ds


# -------------------------- public ----------------------------- #


def load_pass(asset_id: str, date: str, *, bands: tuple[str, ...] = DEFAULT_BANDS,
              force: bool = False) -> xr.Dataset | None:
    """Fetch (or load from cache) a multispectral tile for the asset on `date`.

    Args:
        asset_id: key into ASSETS (e.g. ``"jagersfontein"``).
        date: ``YYYY-MM-DD`` (interpreted as 08:00 UTC, matching Spike 2).
        bands: tuple of SimSat band aliases. Default is the 5-band stack
            Phase 1 needs for NDWI / NDMI / B4_B3 / SWIR.
        force: re-fetch even if a cached NetCDF exists.

    Returns:
        xarray.Dataset with one variable per band, ``y`` (lat) and ``x``
        (lon) coords, plus metadata in ``ds.attrs``. ``None`` if SimSat
        reports ``image_available=False`` for the date+window.
    """
    if asset_id not in ASSETS:
        raise KeyError(f"unknown asset {asset_id!r}; available: {sorted(ASSETS)}")
    asset = ASSETS[asset_id]

    cache_dir = DATA_DIR / asset_id
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{date}.nc"
    miss_marker = cache_dir / f"{date}.miss"

    if not force:
        if cache_path.exists():
            return xr.open_dataset(cache_path)
        if miss_marker.exists():
            return None

    timestamp = f"{date}T08:00:00"
    body = _http_array_pull(asset, timestamp, bands)
    ds = _decode_array_response(body, asset, bands)
    if ds is None:
        miss_marker.write_text(
            json.dumps({"date": date, "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
                        "sentinel_metadata": body.get("sentinel_metadata", {})})
        )
        return None

    # Persist with a small encoding hint — uint16 reflectance + tiny variants
    # compress well with zlib level 4.
    enc = {b: {"zlib": True, "complevel": 4} for b in bands}
    ds.to_netcdf(cache_path, encoding=enc)
    return ds
