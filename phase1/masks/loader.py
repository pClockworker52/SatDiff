"""Load Phase 1 asset masks (geojson) and rasterize them onto a tile grid.

Public surface (intentionally tiny):
    load_masks(asset_id) -> dict[str, shapely.Polygon]
    rasterize_masks(masks, *, transform, shape) -> dict[str, np.ndarray[bool]]

Polygons are stored in `phase1/masks/<asset_id>.geojson` in WGS84
(CRS84, lon-lat). The contract memo
`prompts/jagersfontein-contract.md` is the source of
truth for the four mask ids: impoundment, retaining_wall,
downstream_slope, and the protected-zone polygon (kopanong_*).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from shapely.geometry import shape

_THIS_DIR = Path(__file__).parent

# Reuse same names the contract memo uses.
EXPECTED_MASK_IDS = {
    "impoundment",
    "retaining_wall",
    "downstream_slope",
}


def load_masks(asset_id: str) -> dict[str, "shapely.geometry.Polygon"]:
    """Read `phase1/masks/<asset_id>.geojson` and return polygons by mask_id.

    All polygons are in WGS84 (CRS84). The protected-zone polygon's
    `mask_id` may be asset-specific (e.g. ``kopanong_protected_zone``);
    that is returned alongside the canonical three.
    """
    path = _THIS_DIR / f"{asset_id}.geojson"
    fc = json.loads(path.read_text())
    if fc.get("type") != "FeatureCollection":
        raise ValueError(f"{path}: expected FeatureCollection, got {fc.get('type')}")
    masks: dict[str, object] = {}
    for feat in fc["features"]:
        mask_id = feat["properties"].get("mask_id")
        if not mask_id:
            raise ValueError(f"{path}: feature missing mask_id")
        if mask_id in masks:
            raise ValueError(f"{path}: duplicate mask_id {mask_id!r}")
        masks[mask_id] = shape(feat["geometry"])
    missing = EXPECTED_MASK_IDS - set(masks)
    if missing:
        raise ValueError(f"{path}: missing required mask_ids {sorted(missing)}")
    if not any(k.endswith("_protected_zone") for k in masks):
        raise ValueError(f"{path}: missing a *_protected_zone mask")
    return masks


def rasterize_masks(
    masks: dict[str, "shapely.geometry.Polygon"],
    *,
    transform,
    shape: tuple[int, int],
) -> dict[str, np.ndarray]:
    """Burn each polygon into a bool array of the given shape.

    `transform` is an affine.Affine taking WGS84 (lon, lat) to (col, row).
    `shape` is (height, width) of the target grid (typically the SimSat
    tile dims).

    Defers the rasterio import — Phase 1 is the first place we need it
    so we want the import error visible at first call, not at module
    load time.
    """
    from rasterio.features import rasterize  # noqa: PLC0415 — see docstring

    out: dict[str, np.ndarray] = {}
    for mask_id, geom in masks.items():
        burned = rasterize(
            [(geom, 1)],
            out_shape=shape,
            transform=transform,
            fill=0,
            dtype="uint8",
        )
        out[mask_id] = burned.astype(bool)
    return out
