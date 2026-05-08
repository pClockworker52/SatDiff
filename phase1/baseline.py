"""Phase 1 baseline indices — per-mask reference values for an asset.

Public surface:
    compute_baseline(asset_id, date) -> dict
    load_baseline(asset_id) -> dict
    BASELINE_KEYS — the field names the physical-diff module will subtract from.

The baseline is the ``[BASELINE]`` block the contract memo
(`prompts/jagersfontein-contract.md` lines 95-103)
expects in the VLM prompt:

    Masks: {impoundment, retaining_wall, downstream, protected_zone}
    Baseline indices per mask: <structured>

We compute four per-mask numbers and one impoundment-specific area:

    NDWI_mean    (green - nir) / (green + nir)         — water sensitivity
    NDMI_mean    (nir - swir16) / (nir + swir16)        — moisture sensitivity
    B4_B3_mean   red / green                            — turbidity proxy
    pond_area_m2  count(NDWI > 0 ∩ impoundment) × pixel_m²   — impoundment only

The baseline date is constrained pre-2019-Feb (before Torres-Cruz's earliest
anomaly) and post-2017 (Element 84's ``sentinel-2-l2a`` lacks pre-2017
T35JLH archive). 2017-10-15 is the first try; the helper widens the search
if SimSat returns no tile.
"""

from __future__ import annotations

import json
import math
from datetime import date as _date
from datetime import timedelta
from pathlib import Path
from typing import Iterable

import numpy as np
from shapely import contains_xy

from phase1.loader import ASSETS, DATA_DIR, load_pass
from phase1.masks.loader import load_masks

BASELINE_KEYS = ("NDWI_mean", "NDMI_mean", "B4_B3_mean", "n_valid_pixels")
DEFAULT_TARGET_DATE = "2017-10-15"
DEFAULT_FALLBACK_DATES = (
    "2017-04-15", "2018-04-15", "2018-10-15",
    # Last resort: still pre-Feb-2019 (Torres-Cruz first anomaly)
    "2019-01-15",
)
PIXEL_M2 = 9.85 * 9.90  # ≈97.5 m²/pixel; matches the SimSat tile resolution


def _safe_ratio(num: np.ndarray, den: np.ndarray) -> np.ndarray:
    """Numerator / denominator, NaN where denominator is zero."""
    den = np.where(den == 0, np.nan, den)
    return num / den


def _per_mask_indices(ds, mask_bool: np.ndarray) -> dict[str, float]:
    """NDWI / NDMI / B4_B3 means over the bool mask. Returns NaN for empty masks."""
    if not mask_bool.any():
        return {k: float("nan") for k in BASELINE_KEYS}
    green = ds["green"].values.astype(np.float64)
    red = ds["red"].values.astype(np.float64)
    nir = ds["nir"].values.astype(np.float64)
    swir = ds["swir16"].values.astype(np.float64)

    ndwi = _safe_ratio(green - nir, green + nir)
    ndmi = _safe_ratio(nir - swir, nir + swir)
    b4_b3 = _safe_ratio(red, green)

    sel = mask_bool & np.isfinite(ndwi) & np.isfinite(ndmi) & np.isfinite(b4_b3)
    if not sel.any():
        return {k: float("nan") for k in BASELINE_KEYS}
    return {
        "NDWI_mean": float(ndwi[sel].mean()),
        "NDMI_mean": float(ndmi[sel].mean()),
        "B4_B3_mean": float(b4_b3[sel].mean()),
        "n_valid_pixels": int(sel.sum()),
    }


def _pond_area_m2(ds, impoundment_mask: np.ndarray) -> float:
    """Pixels with NDWI > 0 inside the impoundment, scaled to m²."""
    green = ds["green"].values.astype(np.float64)
    nir = ds["nir"].values.astype(np.float64)
    ndwi = _safe_ratio(green - nir, green + nir)
    sel = impoundment_mask & (np.isfinite(ndwi)) & (ndwi > 0)
    return float(sel.sum() * PIXEL_M2)


def _rasterize_with_dataset_grid(asset_id: str, ds) -> dict[str, np.ndarray]:
    """Rasterize the asset's masks onto the dataset's lat/lon grid."""
    masks = load_masks(asset_id)
    ys, xs = ds["y"].values, ds["x"].values
    yy, xx = np.meshgrid(ys, xs, indexing="ij")
    return {mid: contains_xy(poly, xx, yy) for mid, poly in masks.items()}


def compute_baseline(asset_id: str, *, date: str | None = None,
                     fallback_dates: Iterable[str] = DEFAULT_FALLBACK_DATES) -> dict:
    """Compute baseline indices on the chosen pre-anomaly date.

    Tries `date` (default 2017-10-15) first; on `image_available=False`
    falls through `fallback_dates` in order. Persists the result to
    `phase1/data/<asset_id>/baseline.json` and returns it.
    """
    if asset_id not in ASSETS:
        raise KeyError(f"unknown asset {asset_id!r}")

    candidates: list[str] = [date or DEFAULT_TARGET_DATE, *fallback_dates]
    chosen_date: str | None = None
    ds = None
    for d in candidates:
        ds = load_pass(asset_id, d)
        if ds is not None:
            chosen_date = d
            break
    if ds is None or chosen_date is None:
        raise RuntimeError(
            f"No SimSat baseline tile for {asset_id} across {candidates}. "
            f"Element 84 may need the sentinel-2-pre-c1-l2a fallback for pre-2017 dates."
        )

    masks_bool = _rasterize_with_dataset_grid(asset_id, ds)
    per_mask: dict[str, dict] = {}
    for mid, mask_bool in masks_bool.items():
        per_mask[mid] = _per_mask_indices(ds, mask_bool)

    pond_area = _pond_area_m2(ds, masks_bool["impoundment"])

    out = {
        "asset_id": asset_id,
        "target_date": date or DEFAULT_TARGET_DATE,
        "chosen_date": chosen_date,
        "sentinel_datetime": ds.attrs.get("sentinel_datetime"),
        "sentinel_source": ds.attrs.get("sentinel_source"),
        "cloud_cover": float(ds.attrs.get("cloud_cover", float("nan"))),
        "tile_shape_y_x": [int(ds.sizes["y"]), int(ds.sizes["x"])],
        "pixel_m2": PIXEL_M2,
        "per_mask": per_mask,
        "pond_area_m2": pond_area,
        "comment": (
            "Indices on the masks defined in phase1/masks/jagersfontein.geojson, "
            "computed on the first pre-Feb-2019 SimSat tile that returned imagery. "
            "Used by phase1.physical_diff to compute change relative to baseline."
        ),
    }

    out_dir = DATA_DIR / asset_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "baseline.json").write_text(json.dumps(out, indent=2))
    return out


def load_baseline(asset_id: str) -> dict:
    """Read a previously-persisted baseline; raise if missing."""
    p = DATA_DIR / asset_id / "baseline.json"
    if not p.exists():
        raise FileNotFoundError(f"No baseline at {p}; run compute_baseline first.")
    return json.loads(p.read_text())
