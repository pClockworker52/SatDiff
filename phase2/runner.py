"""Phase 2 runner — singleton model load + two-stage decode + retry-once.

Public surface:
    VLM(model_id) — context manager that loads the model once.
    run_pass(asset_id, date, *, vlm, prior_reports) -> dict

The two-stage decode addresses Spike 1's parrot-mode failure: Stage A
gives the model its own free-text description of the imagery; Stage B
populates the contract JSON using Stage A's text + the populated
Physical-diff numbers from Phase 1.

Single retry on Stage B if JSON is missing or schema-invalid — the retry
prompt prepends a corrective sentence with the validator error.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import jsonschema
import numpy as np
from PIL import Image

from phase1.baseline import load_baseline
from phase1.loader import load_pass as load_pass_ds
from phase1.physical_diff import compute_diff
from phase2.aggregate import compute_severity, count_corrections, overlay_on_parsed
from phase2.prompt import build_stage_a_prompt, build_stage_b_prompt
from phase2.render import render_pass

REPO_ROOT = Path(os.environ.get("SATDIFF_REPO_ROOT", "/mnt/c/Users/peter/SatDiff"))
SCHEMA_PATH = REPO_ROOT / "spikes" / "schema.json"
DEFAULT_MODEL_ID = "LiquidAI/LFM2.5-VL-450M"


class _Transport(Protocol):
    model_id: str

    def load(self) -> "_Transport": ...
    def generate(self, images: list[Image.Image], prompt: str,
                 max_new_tokens: int = 1024) -> tuple[str, float]: ...


# ---------------------- model wrappers ---------------------- #


@dataclass
class VLM:
    """Transformers / bf16 transport. Default for benchmarking + fallback."""
    model_id: str
    model: Any = None
    processor: Any = None

    def load(self) -> "VLM":
        if self.model is not None:
            return self
        # Imported lazily so the llama-server transport doesn't pull in torch.
        import torch
        from transformers import AutoProcessor, AutoModelForImageTextToText
        self._torch = torch
        self.processor = AutoProcessor.from_pretrained(self.model_id)
        self.model = AutoModelForImageTextToText.from_pretrained(
            self.model_id, device_map="auto", dtype="bfloat16",
        )
        self.model.eval()
        return self

    def generate(self, images: list[Image.Image], prompt: str,
                 max_new_tokens: int = 1024) -> tuple[str, float]:
        torch = self._torch
        content: list[dict] = [{"type": "image", "image": im} for im in images]
        content.append({"type": "text", "text": prompt})
        messages = [{"role": "user", "content": content}]
        inputs = self.processor.apply_chat_template(
            messages, add_generation_prompt=True,
            return_tensors="pt", return_dict=True, tokenize=True,
        ).to(self.model.device)

        torch.cuda.reset_peak_memory_stats(0)
        t0 = time.perf_counter()
        with torch.inference_mode():
            out_ids = self.model.generate(
                **inputs, max_new_tokens=max_new_tokens, do_sample=False,
            )
        latency = time.perf_counter() - t0
        new_tokens = out_ids[0, inputs["input_ids"].shape[1]:]
        text = self.processor.tokenizer.decode(new_tokens, skip_special_tokens=True)
        return text, latency


def make_vlm(model_id: str = DEFAULT_MODEL_ID) -> _Transport:
    """Pick transport by SATDIFF_INFERENCE env var.

    `transformers` (default): in-process bf16 transformers — needs torch + GPU.
    `llama_server`           : HTTP to a running llama.cpp llama-server
                               (LLAMA_SERVER_URL, default http://localhost:8080).
    """
    backend = os.environ.get("SATDIFF_INFERENCE", "transformers").strip().lower()
    if backend == "llama_server":
        from phase2.llama_client import LlamaServerVLM
        return LlamaServerVLM(model_id=model_id)
    if backend == "transformers":
        return VLM(model_id=model_id)
    raise ValueError(f"unknown SATDIFF_INFERENCE={backend!r}; "
                     "expected 'transformers' or 'llama_server'")


# ---------------------- JSON / validation ---------------------- #


_SCHEMA: dict | None = None
_SCHEMA_TEXT: str | None = None


def _schema() -> dict:
    global _SCHEMA
    if _SCHEMA is None:
        _SCHEMA = json.loads(SCHEMA_PATH.read_text())
    return _SCHEMA


def schema_text() -> str:
    global _SCHEMA_TEXT
    if _SCHEMA_TEXT is None:
        _SCHEMA_TEXT = SCHEMA_PATH.read_text()
    return _SCHEMA_TEXT


def _try_parse_json(text: str) -> tuple[Any | None, str | None]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"```\s*$", "", cleaned)
    m = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if m:
        cleaned = m.group(0)
    try:
        return json.loads(cleaned), None
    except json.JSONDecodeError as e:
        return None, str(e)


def _validate_schema(parsed: Any) -> tuple[bool, str | None]:
    try:
        jsonschema.validate(parsed, _schema())
    except jsonschema.ValidationError as e:
        return False, e.message
    return True, None


# ---------------------- evidence regex hits ---------------------- #


_POND_RX = re.compile(r"pond", re.IGNORECASE)


def _evidence_metric_hits(parsed: dict, diff: dict) -> int:
    """Count claims whose evidence cites at least one numerical metric value
    from the Physical-diff summary. Crude regex match — looks for the
    rendered numeric value (rounded) anywhere in the evidence string.
    """
    if not isinstance(parsed, dict):
        return 0
    diff_values: list[str] = []
    for section in ("impoundment", "pond", "retaining_wall"):
        block = diff.get(section) or {}
        for v in block.values():
            if v is None or isinstance(v, bool):
                continue
            if isinstance(v, (int, float)):
                # Match formats like "9.9", "1144.5", "1128638.6", "34"
                diff_values.append(f"{v:g}")
                # Also match rounded integer form for large numbers
                if isinstance(v, float) and abs(v) >= 100:
                    diff_values.append(f"{int(round(v))}")
    if not diff_values:
        return 0
    rx = re.compile(r"\b(?:" + "|".join(re.escape(s) for s in set(diff_values)) + r")\b")

    hits = 0
    for c in parsed.get("claims", []):
        ev = c.get("evidence", "") if isinstance(c, dict) else ""
        if rx.search(ev):
            hits += 1
    return hits


def _evidence_pond_hits(parsed: Any) -> int:
    if not isinstance(parsed, dict):
        return 0
    return sum(
        1 for c in parsed.get("claims", [])
        if isinstance(c, dict) and _POND_RX.search(c.get("evidence", ""))
    )


# ---------------------- pass orchestration ---------------------- #


def _images_for_pass(asset_id: str, baseline_date: str,
                     current_date: str) -> list[Image.Image]:
    """Render baseline RGB+NIR + current RGB+NIR via Phase 1's NetCDF cache."""
    base_ds = load_pass_ds(asset_id, baseline_date)
    cur_ds = load_pass_ds(asset_id, current_date)
    if base_ds is None or cur_ds is None:
        raise RuntimeError(f"missing tile for {asset_id} {baseline_date}/{current_date}")
    base_imgs = render_pass(base_ds)
    cur_imgs = render_pass(cur_ds)
    return [base_imgs["rgb"], base_imgs["nir"], cur_imgs["rgb"], cur_imgs["nir"]]


def run_pass(asset_id: str, date: str, *, vlm: _Transport,
             prior_reports: list[dict] | None = None) -> dict:
    """Two-stage decode for one date. Returns the per-pass record."""
    baseline = load_baseline(asset_id)
    diff = compute_diff(asset_id, date)
    if diff is None:
        return {
            "asset_id": asset_id, "date_target": date,
            "image_available": False, "skipped": "image_unavailable",
        }

    current_date = diff["acquisition_date"]
    pass_id = f"{asset_id}-{current_date}"

    images = _images_for_pass(asset_id, baseline["chosen_date"], date)

    # Stage A — free-text describe
    stage_a_prompt = build_stage_a_prompt(
        baseline_date=baseline["chosen_date"], current_date=current_date,
    )
    stage_a_text, lat_a = vlm.generate(images, stage_a_prompt, max_new_tokens=400)

    # Stage B — contract JSON
    stage_b_prompt = build_stage_b_prompt(
        baseline=baseline,
        diff=diff,
        stage_a_text=stage_a_text,
        prior_reports=prior_reports or [],
        schema_text=schema_text(),
        pass_id=pass_id,
    )
    raw_b, lat_b = vlm.generate(images, stage_b_prompt, max_new_tokens=1024)
    parsed, parse_err = _try_parse_json(raw_b)
    schema_ok, schema_err = (False, parse_err) if parsed is None else _validate_schema(parsed)

    retry_used = False
    if not schema_ok:
        retry_used = True
        retry_prompt = (
            f"Your previous output was invalid: {schema_err or parse_err}. "
            "Output strict JSON only, matching the [OUTPUT SCHEMA] exactly. "
            "No prose, no markdown fences.\n\n"
        ) + stage_b_prompt
        raw_b2, lat_b2 = vlm.generate(images, retry_prompt, max_new_tokens=1024)
        parsed2, parse_err2 = _try_parse_json(raw_b2)
        schema_ok2, schema_err2 = (False, parse_err2) if parsed2 is None else _validate_schema(parsed2)
        if schema_ok2:
            raw_b, parsed, parse_err, schema_ok, schema_err = raw_b2, parsed2, None, True, None
            lat_b += lat_b2
        else:
            # Keep both for diagnostics; report the retry result as authoritative.
            raw_b, parsed, parse_err, schema_ok, schema_err = raw_b2, parsed2, parse_err2, schema_ok2, schema_err2
            lat_b += lat_b2

    # Rules engine: compute severity from diff numbers, overlay onto model output.
    # The model is good at writing evidence; threshold logic is deterministic.
    computed = compute_severity(diff)
    if parsed is not None and schema_ok:
        model_only = parsed
        parsed = overlay_on_parsed(parsed, computed)
        corrections = count_corrections(model_only, computed)
        # Re-validate after overlay (defensive — overlay only swaps enum values).
        ok2, err2 = _validate_schema(parsed)
        if not ok2:
            schema_ok, schema_err = ok2, f"post-overlay schema fail: {err2}"
    else:
        model_only = None
        corrections = {
            "severity_corrections": None,
            "severity_corrections_detail": [],
            "model_overall": None,
            "computed_overall": computed["overall_status"],
            "overall_corrected": None,
        }

    # peak_vram_gb only available for the transformers transport (uses torch.cuda).
    peak_vram_gb: float | None = None
    if isinstance(vlm, VLM) and getattr(vlm, "_torch", None) is not None:
        peak_vram_gb = round(vlm._torch.cuda.max_memory_allocated(0) / 1024**3, 2)

    metrics = {
        "latency_seconds_stage_a": round(lat_a, 2),
        "latency_seconds_stage_b": round(lat_b, 2),
        "peak_vram_gb": peak_vram_gb,
        "json_parses": parsed is not None,
        "schema_valid": bool(schema_ok),
        "schema_error": schema_err,
        "retry_used": retry_used,
        "claims_with_evidence_mentioning_pond": _evidence_pond_hits(parsed),
        "claims_with_evidence_mentioning_metric_value": _evidence_metric_hits(parsed, diff) if parsed else 0,
        **corrections,
    }

    return {
        "asset_id": asset_id,
        "pass_id": pass_id,
        "date_target": date,
        "image_available": True,
        "phase1_diff": diff,
        "stage_a_text": stage_a_text,
        "stage_b_raw": raw_b,
        "stage_b_parsed_model_only": model_only,
        "stage_b_parsed": parsed,
        "rules_engine": computed,
        "metrics": metrics,
        "model_id": vlm.model_id,
    }
