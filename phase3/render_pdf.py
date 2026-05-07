"""Phase 3 — Jinja2 + WeasyPrint per-pass PDF report.

Reads `phase2/out/<asset>/<date>.json` and produces a one-page-per-pass PDF
that looks like the audit-trail artefact the GISTM auditor consumes.
Imagery is regenerated from the Phase 1 NetCDF cache + the Phase 2 render
helper (no coupling to the runtime path) and embedded as data URIs so the
PDF is self-contained.

Public surface:
    render_pass_pdf(asset_id, date) -> Path
"""

from __future__ import annotations

import base64
import datetime as _dt
import io
import json
import os
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image
from weasyprint import HTML

from phase1.baseline import load_baseline
from phase1.loader import load_pass as load_pass_ds
from phase2.render import render_pass

REPO_ROOT = Path(os.environ.get("SATDIFF_REPO_ROOT", "/mnt/c/Users/peter/SatDiff"))
PHASE2_OUT = REPO_ROOT / "phase2" / "out"
PHASE3_OUT = REPO_ROOT / "phase3" / "out"
TEMPLATE_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"


# ----------------------------- formatting ----------------------------- #

_SEVERITY_COLOR = {
    "nominal": "#16a34a",   # green
    "elevated": "#ea580c",  # amber-orange
    "urgent":   "#dc2626",  # red
}

_OVERALL_COLOR = {
    "nominal":   "#16a34a",
    "elevated":  "#ea580c",
    "urgent":    "#dc2626",
}

_TREND_GLYPH = {
    "increased":  "▲",
    "unchanged":  "●",
    "decreased":  "▼",
}


def _to_data_uri(image: Image.Image, *, fmt: str = "PNG") -> str:
    """PIL.Image → data:image/png;base64,... URI."""
    if image.mode != "RGB":
        image = image.convert("RGB")
    buf = io.BytesIO()
    image.save(buf, format=fmt)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    mime = f"image/{fmt.lower()}"
    return f"data:{mime};base64,{b64}"


def _fmt_num(v: Any, *, suffix: str = "", precision: int = 1) -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return f"{v}{suffix}"
    if isinstance(v, float):
        if abs(v) >= 1000:
            return f"{int(round(v)):,}{suffix}"
        return f"{v:.{precision}f}{suffix}"
    return str(v)


def _claim_color(severity: str) -> str:
    return _SEVERITY_COLOR.get(severity, "#525252")


def _trend_glyph(trend: str) -> str:
    return _TREND_GLYPH.get(trend, "●")


# ----------------------------- imagery ------------------------------ #


def _images_for_pass(asset_id: str, baseline_date: str,
                     current_date: str) -> dict[str, str]:
    """Return data URIs for baseline + current RGB + NIR composites."""
    base_ds = load_pass_ds(asset_id, baseline_date)
    cur_ds = load_pass_ds(asset_id, current_date)
    if base_ds is None or cur_ds is None:
        raise RuntimeError(
            f"missing imagery for {asset_id} {baseline_date}/{current_date}"
        )
    base_imgs = render_pass(base_ds)
    cur_imgs = render_pass(cur_ds)
    return {
        "baseline_rgb": _to_data_uri(base_imgs["rgb"]),
        "baseline_nir": _to_data_uri(base_imgs["nir"]),
        "current_rgb":  _to_data_uri(cur_imgs["rgb"]),
        "current_nir":  _to_data_uri(cur_imgs["nir"]),
    }


# ----------------------------- main render ------------------------------ #


def _build_context(asset_id: str, date: str, *, persist_images: bool = True) -> dict:
    """Assemble the Jinja render context from a per-pass JSON + Phase 1 imagery."""
    rec_path = PHASE2_OUT / asset_id / f"{date}.json"
    if not rec_path.exists():
        raise FileNotFoundError(
            f"No Phase 2 record at {rec_path}. "
            f"Run `python -m phase2.cli --asset {asset_id} --date {date}` first."
        )
    rec = json.loads(rec_path.read_text())
    if not rec.get("image_available", False):
        raise RuntimeError(
            f"{rec_path}: image_available=False (skipped pass — nothing to render)"
        )

    baseline = load_baseline(asset_id)
    images = _images_for_pass(asset_id, baseline["chosen_date"],
                              rec["phase1_diff"]["acquisition_date"])

    parsed = rec["stage_b_parsed"]
    diff = rec["phase1_diff"]
    rules = rec["rules_engine"]

    claims = []
    for c in parsed["claims"]:
        claims.append({
            **c,
            "color":      _claim_color(c["severity_level"]),
            "trend_glyph": _trend_glyph(c["probability_trend"]),
        })

    return {
        # header
        "asset_id":            rec["asset_id"],
        "pass_id":             rec["pass_id"],
        "acquisition_date":    diff["acquisition_date"],
        "baseline_date":       baseline["chosen_date"],
        "sentinel_source":     diff.get("sentinel_source", "—"),
        "cloud_cover_pct":     _fmt_num(diff.get("cloud_cover"), suffix="%"),
        "regulator":           "GISTM (Global Industry Standard on Tailings Management)",

        # severity badges
        "overall_status":      parsed["overall_status"],
        "overall_color":       _OVERALL_COLOR.get(parsed["overall_status"], "#525252"),
        "downlink_priority":   parsed["downlink_priority"],
        "regulatory_escalation_flag": parsed["regulatory_escalation_flag"],

        # imagery
        **images,

        # narrative
        "stage_a_text":        rec["stage_a_text"],

        # claims
        "claims":              claims,

        # phase1 diff numbers (the contract-relevant metrics)
        "phase1_diff":         {
            "deposition_asymmetry_index":      _fmt_num(diff["impoundment"].get("deposition_asymmetry_index"), precision=2),
            "footprint_change_pct":            _fmt_num(diff["impoundment"].get("footprint_change_pct"), suffix="%"),
            "pond_area_m2":                    _fmt_num(diff["pond"].get("area_m2"), suffix=" m²", precision=0),
            "pond_area_change_pct":            _fmt_num(diff["pond"].get("area_change_pct_vs_baseline"), suffix="%"),
            "pond_to_wall_distance_m":         _fmt_num(diff["pond"].get("pond_to_wall_distance_m"), suffix=" m"),
            "licence_volume_exceedance_pct":   _fmt_num(diff["pond"].get("licence_volume_exceedance_pct"), suffix="%"),
            "ndwi_max":                        _fmt_num(diff["pond"].get("NDWI_max"), precision=3),
            "b4_b3_turbidity_ratio":           _fmt_num(diff["pond"].get("B4_B3_turbidity_ratio"), precision=3),
            "gully_count":                     _fmt_num(diff["retaining_wall"].get("gully_count")),
            "largest_gully_width_m":           _fmt_num(diff["retaining_wall"].get("largest_gully_width_m"), suffix=" m"),
            "ndmi_wall_face":                  _fmt_num(diff["retaining_wall"].get("NDMI_wall_face"), precision=3),
            "swir_anomaly_flag":               diff["retaining_wall"].get("SWIR_anomaly_flag"),
        },

        # rules-engine inputs (for the audit trail)
        "rule_inputs":         rules.get("rule_inputs", {}),

        # footer
        "model_id":            rec.get("model_id", "—"),
        "pipeline_version":    "SatDiff 0.1 (LFM2.5-VL-450M Stage 1, Q8_0)",
        "rendered_at":         _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "stage_a_latency_s":   rec["metrics"].get("latency_seconds_stage_a"),
        "stage_b_latency_s":   rec["metrics"].get("latency_seconds_stage_b"),
    }


def render_pass_pdf(asset_id: str, date: str) -> Path:
    """Render one pass-report PDF. Returns the output path."""
    ctx = _build_context(asset_id, date)

    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("pass_report.html.j2")
    html_str = template.render(**ctx)

    out_dir = PHASE3_OUT / asset_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{date}.pdf"
    HTML(string=html_str, base_url=str(STATIC_DIR)).write_pdf(out_path)
    return out_path
