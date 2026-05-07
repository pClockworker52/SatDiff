"""Phase 2 image rendering — xr.Dataset → PIL.Image (RGB + NIR-false-colour).

Public surface:
    render_pass(ds) -> {"rgb": PIL.Image, "nir": PIL.Image}

Lifts the 2-98 percentile per-band stretch from
`spikes/leap-vlm-check.py::stretch` so Phase 1 cache → VLM input
matches the same composite conventions Spike 1 used. Output is 512×512
to match LFM2.5-VL's native input resolution.
"""

from __future__ import annotations

import numpy as np
import xarray as xr
from PIL import Image

TARGET_PX = 512


def _stretch(arr: np.ndarray, lo_pct: float = 2, hi_pct: float = 98) -> np.ndarray:
    """Per-band 2-98 percentile contrast stretch → uint8."""
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return np.zeros_like(arr, dtype=np.uint8)
    lo, hi = np.percentile(finite, [lo_pct, hi_pct])
    if hi <= lo:
        hi = lo + 1
    out = np.clip((arr - lo) / (hi - lo), 0, 1)
    return (out * 255).astype(np.uint8)


def render_pass(ds: xr.Dataset) -> dict[str, Image.Image]:
    """Return RGB + NIR-false-colour PIL images at 512×512.

    RGB = (red, green, blue), NIR = (nir, red, green). Both at TARGET_PX
    via bilinear resize. Phase 1's xr.Dataset stores bands as uint16; we
    cast to float for percentile calcs.
    """
    bands = {b: ds[b].values.astype(np.float64) for b in ("red", "green", "blue", "nir")}
    rgb = np.dstack([_stretch(bands[b]) for b in ("red", "green", "blue")])
    nir = np.dstack([_stretch(bands[b]) for b in ("nir", "red", "green")])
    rgb_im = Image.fromarray(rgb).resize((TARGET_PX, TARGET_PX), Image.BILINEAR)
    nir_im = Image.fromarray(nir).resize((TARGET_PX, TARGET_PX), Image.BILINEAR)
    return {"rgb": rgb_im, "nir": nir_im}
