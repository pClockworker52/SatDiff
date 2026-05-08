"""Phase 1 physical-diff module — per-mask metrics for one Sentinel-2 pass.

Public surface:
    compute_diff(asset_id, date) -> dict   # the [CURRENT PASS] block

Output shape matches the contract memo verbatim
(`prompts/jagersfontein-contract.md` lines 107-127):

    {
      "impoundment": {
        "deposition_asymmetry_index": float,
        "footprint_change_pct": float,
      },
      "pond": {
        "area_m2": float,
        "area_change_pct_vs_baseline": float,
        "pond_to_wall_distance_m": float,
        "licence_volume_exceedance_pct": float,
        "NDWI_max": float,
        "B4_B3_turbidity_ratio": float,
      },
      "retaining_wall": {
        "gully_count": int,
        "largest_gully_width_m": float,
        "NDMI_wall_face": float,
        "SWIR_anomaly_flag": bool,
      },
      "deformation": null,    # multispectral-only path; SAR sidecar is Brumadinho
    }

All metrics are computed on the dataset's grid; the masks are
rasterised on that grid via shapely.contains_xy. The baseline JSON
(phase1/baseline.py) supplies the reference values.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import xarray as xr
from scipy import ndimage as ndi
from shapely import contains_xy

from phase1.baseline import PIXEL_M2, load_baseline
from phase1.loader import load_pass
from phase1.masks.loader import load_masks

# ----------------------- shared helpers ----------------------- #


def _safe_ratio(num: np.ndarray, den: np.ndarray) -> np.ndarray:
    den = np.where(den == 0, np.nan, den)
    return num / den


def _ndwi(ds: xr.Dataset) -> np.ndarray:
    g = ds["green"].values.astype(np.float64)
    n = ds["nir"].values.astype(np.float64)
    return _safe_ratio(g - n, g + n)


def _ndmi(ds: xr.Dataset) -> np.ndarray:
    n = ds["nir"].values.astype(np.float64)
    s = ds["swir16"].values.astype(np.float64)
    return _safe_ratio(n - s, n + s)


def _b4_b3(ds: xr.Dataset) -> np.ndarray:
    r = ds["red"].values.astype(np.float64)
    g = ds["green"].values.astype(np.float64)
    return _safe_ratio(r, g)


def _rasterize(asset_id: str, ds: xr.Dataset) -> dict[str, np.ndarray]:
    masks = load_masks(asset_id)
    yy, xx = np.meshgrid(ds["y"].values, ds["x"].values, indexing="ij")
    return {mid: contains_xy(poly, xx, yy) for mid, poly in masks.items()}


# --------------------------- pond ------------------------------ #


def _pond_metrics(ds: xr.Dataset, masks: dict[str, np.ndarray],
                  baseline: dict) -> dict[str, float]:
    ndwi = _ndwi(ds)
    pond_pix = masks["impoundment"] & np.isfinite(ndwi) & (ndwi > 0)
    area = float(pond_pix.sum() * PIXEL_M2)

    # Distance from each pond pixel to the nearest wall pixel — minimum gives
    # "closest pond-to-wall metres". distance_transform_edt computes the
    # distance (in pixels) from each True cell of the input to the nearest
    # False cell — so we feed the COMPLEMENT of the wall mask and read the
    # value at pond pixels.
    wall_distance_px = ndi.distance_transform_edt(~masks["retaining_wall"])
    if pond_pix.any():
        # px → m via the geometric mean of x/y resolutions
        m_per_px = math.sqrt(PIXEL_M2)
        pond_to_wall = float(wall_distance_px[pond_pix].min() * m_per_px)
        ndwi_max = float(np.nanmax(ndwi[masks["impoundment"]]))
        b4_b3 = _b4_b3(ds)
        b4b3_pond = float(np.nanmean(b4_b3[pond_pix]))
    else:
        pond_to_wall = float("nan")
        ndwi_max = float("nan")
        b4b3_pond = float("nan")

    base_area = baseline.get("pond_area_m2", 0.0)
    if base_area > 0:
        area_change_pct = 100.0 * (area - base_area) / base_area
    else:
        area_change_pct = float("nan")

    # licence_volume_exceedance_pct: we don't have a licence. The contract
    # memo flags this as needing design-doc calibration. For v0 we use
    # max(0, area_change_pct_vs_baseline) as a proxy — a 70% over-baseline
    # pond area corresponds to the Torres-Cruz reported 2020 over-volume.
    if math.isfinite(area_change_pct):
        licence_exc = max(0.0, area_change_pct)
    else:
        licence_exc = float("nan")

    return {
        "area_m2": round(area, 1),
        "area_change_pct_vs_baseline": round(area_change_pct, 1) if math.isfinite(area_change_pct) else None,
        "pond_to_wall_distance_m": round(pond_to_wall, 1) if math.isfinite(pond_to_wall) else None,
        "licence_volume_exceedance_pct": round(licence_exc, 1) if math.isfinite(licence_exc) else None,
        "NDWI_max": round(ndwi_max, 3) if math.isfinite(ndwi_max) else None,
        "B4_B3_turbidity_ratio": round(b4b3_pond, 3) if math.isfinite(b4b3_pond) else None,
    }


# ------------------------- retaining wall ------------------------- #


def _wall_metrics(ds: xr.Dataset, masks: dict[str, np.ndarray],
                  baseline: dict) -> dict[str, Any]:
    """Edge-density gully proxy + NDMI wall face + SWIR anomaly flag."""
    wall = masks["retaining_wall"]
    if not wall.any():
        return {
            "gully_count": 0,
            "largest_gully_width_m": None,
            "NDMI_wall_face": None,
            "SWIR_anomaly_flag": None,
        }

    # Gully proxy: Sobel edge magnitude on the red band, restricted to the
    # wall mask. Threshold at the 90th percentile of edges within the wall;
    # connected-component count gives gully_count. Largest CC's bounding-
    # box width along the dominant wall direction (~ pixel column count)
    # gives largest_gully_width_m. This is a proxy — Phase 2 / writeup
    # acknowledges this. (Real gully detection wants a higher-res sensor.)
    red = ds["red"].values.astype(np.float64)
    gx = ndi.sobel(red, axis=1)
    gy = ndi.sobel(red, axis=0)
    edge = np.hypot(gx, gy)
    edge_in_wall = np.where(wall, edge, 0.0)
    if edge_in_wall.max() > 0:
        thr = float(np.percentile(edge_in_wall[wall], 90))
        hot = (edge_in_wall > thr) & wall
        labelled, n_components = ndi.label(hot)
        gully_count = int(n_components)
        if n_components > 0:
            sizes = ndi.sum_labels(hot, labelled, range(1, n_components + 1))
            largest_label = int(np.argmax(sizes)) + 1
            ys, xs = np.where(labelled == largest_label)
            width_px = (xs.max() - xs.min() + 1) if xs.size else 0
            largest_gully_width_m = float(width_px * math.sqrt(PIXEL_M2))
        else:
            largest_gully_width_m = 0.0
    else:
        gully_count, largest_gully_width_m = 0, 0.0

    ndmi = _ndmi(ds)
    sel = wall & np.isfinite(ndmi)
    ndmi_wall = float(ndmi[sel].mean()) if sel.any() else float("nan")

    # SWIR anomaly: is current SWIR mean on the wall > baseline + 2σ?
    swir = ds["swir16"].values.astype(np.float64)
    swir_wall_mean = float(swir[wall].mean()) if wall.any() else float("nan")
    base_wall = baseline.get("per_mask", {}).get("retaining_wall", {})
    # We didn't persist a SWIR mean in baseline; use NDMI instead for the
    # anomaly flag — a 2σ deviation in NDMI on the wall face flags abnormal
    # moisture / chemistry. Compute σ from baseline.json's NDMI_mean +
    # an empirical pixel-level σ from the current wall NDMI.
    base_ndmi = base_wall.get("NDMI_mean", math.nan)
    if math.isfinite(base_ndmi) and sel.any():
        sigma_wall = float(ndmi[sel].std())
        swir_anomaly_flag = bool(abs(ndmi_wall - base_ndmi) > 2 * max(sigma_wall, 0.01))
    else:
        swir_anomaly_flag = False

    return {
        "gully_count": gully_count,
        "largest_gully_width_m": round(largest_gully_width_m, 1),
        "NDMI_wall_face": round(ndmi_wall, 3) if math.isfinite(ndmi_wall) else None,
        "SWIR_anomaly_flag": bool(swir_anomaly_flag),
    }


# --------------------------- impoundment ----------------------------- #


def _impoundment_metrics(ds: xr.Dataset, masks: dict[str, np.ndarray],
                         baseline: dict) -> dict[str, Any]:
    imp = masks["impoundment"]
    if not imp.any():
        return {"deposition_asymmetry_index": None, "footprint_change_pct": None}

    ndwi = _ndwi(ds)
    # Dry tailings = NDWI < -0.05 within impoundment.
    dry = imp & np.isfinite(ndwi) & (ndwi < -0.05)

    # Asymmetry: split the impoundment along its centroid's y-axis; ratio of
    # dry-tailings pixel counts in the larger half over the smaller half.
    ys, xs = np.where(imp)
    if ys.size == 0 or not dry.any():
        asymmetry = float("nan")
    else:
        cy = float(ys.mean())
        north_half = (np.arange(ds.sizes["y"])[:, None] < cy)
        north = dry & north_half
        south = dry & ~north_half
        n_n, n_s = north.sum(), south.sum()
        if min(n_n, n_s) == 0:
            asymmetry = float("inf")
        else:
            asymmetry = float(max(n_n, n_s) / min(n_n, n_s))

    # Footprint change: ratio of (current dry-tailings count) to (baseline
    # impoundment-mask pixel count) — captures expansion past the v0 mask
    # if the operator extended deposition. NB: the mask itself is fixed,
    # so this measures fill within the mask, not mask growth.
    base_pixels = baseline.get("per_mask", {}).get("impoundment", {}).get("n_valid_pixels", 0)
    if base_pixels:
        footprint_change_pct = 100.0 * (dry.sum() - base_pixels) / base_pixels
    else:
        footprint_change_pct = float("nan")

    return {
        "deposition_asymmetry_index": round(asymmetry, 3) if math.isfinite(asymmetry) else None,
        "footprint_change_pct": round(footprint_change_pct, 1) if math.isfinite(footprint_change_pct) else None,
    }


# ----------------------------- public ------------------------------ #


def compute_diff(asset_id: str, date: str) -> dict[str, Any] | None:
    """Compute the [CURRENT PASS] Physical-diff summary for one date.

    Returns ``None`` if SimSat reports image_available=False for the date.
    """
    ds = load_pass(asset_id, date)
    if ds is None:
        return None
    baseline = load_baseline(asset_id)
    masks_bool = _rasterize(asset_id, ds)

    return {
        "asset_id": asset_id,
        "acquisition_date": ds.attrs.get("sentinel_datetime", "")[:10] or date,
        "cloud_cover": float(ds.attrs.get("cloud_cover", float("nan"))),
        "sentinel_source": ds.attrs.get("sentinel_source", ""),
        "baseline_chosen_date": baseline.get("chosen_date"),
        "impoundment": _impoundment_metrics(ds, masks_bool, baseline),
        "pond": _pond_metrics(ds, masks_bool, baseline),
        "retaining_wall": _wall_metrics(ds, masks_bool, baseline),
        "deformation": None,  # multispectral-only; SAR sidecar is Brumadinho's concern
    }
