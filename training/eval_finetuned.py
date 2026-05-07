"""Evaluate a fine-tuned LFM2.5-VL checkpoint on the SatDiff Phase 2 backtest.

Re-runs phase2/cli.py over the same 16 invoked Jagersfontein passes using
the fine-tuned model id (a local merged-fp16 checkpoint dir from
leap-finetune outputs/), then compares against the base-model baseline
saved at phase2/out/jagersfontein/summary.json.

Headline metric: `severity_corrections` per pass (lower = model applied
the contract thresholds correctly without rules-engine override). The
Phase 2 baseline is 0.75 mean corrections/pass; Stage 1 + Stage 2 should
push that toward 0.

Usage:
    python training/eval_finetuned.py \
        --model /home/peter/leap-finetune/outputs/satdiff_stage2/<job-tag>/ \
        --label stage2

Writes:
    phase2/out/jagersfontein_eval_<label>/  (the per-pass JSONs)
    training/out/eval_<label>.json          (delta-vs-baseline summary)
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import re

REPO_ROOT = Path("/mnt/c/Users/peter/SatDiff")
sys.path.insert(0, str(REPO_ROOT))

from phase2.cli import _bulk_dates_from_phase1
from phase2.runner import make_vlm, run_pass

PHASE2_BASELINE_SUMMARY = REPO_ROOT / "phase2" / "out" / "jagersfontein" / "summary.json"
EVAL_OUT_ROOT = REPO_ROOT / "training" / "out"

# Per-claim evidence-correctness rules — match the per-claim sourcing
# guidance baked into phase2/prompt.py's [OUTPUT INSTRUCTIONS]:
#   c1 → asymmetry / footprint
#   c2 → pond_to_wall / area_change / NDWI_max
#   c3 → gully / NDMI_wall_face
#   c4 → "no SAR data"
#   c5 → "no observed encroachment" / town / downstream
EVIDENCE_RX = {
    1: re.compile(r"asymmetry|footprint", re.I),
    2: re.compile(r"pond_to_wall|area_change|NDWI_max|pond.*chang", re.I),
    3: re.compile(r"gully|NDMI_wall|wall_face", re.I),
    4: re.compile(r"no SAR", re.I),
    5: re.compile(r"no.*encroach|protected.zone|town|kopanong|downstream", re.I),
}


def _grade_evidence(per_pass_dir: Path) -> dict:
    files = sorted(p for p in per_pass_dir.glob("*.json")
                   if p.name != "summary.json" and p.name[:4].isdigit())
    n_correct = 0
    n_total = 0
    for f in files:
        d = json.loads(f.read_text())
        if not d.get("image_available"):
            continue
        for c in (d.get("stage_b_parsed") or {}).get("claims", []):
            cid = c.get("id")
            ev = c.get("evidence", "")
            if cid in EVIDENCE_RX:
                n_total += 1
                if EVIDENCE_RX[cid].search(ev):
                    n_correct += 1
    return {
        "evidence_correct_claims": n_correct,
        "evidence_total_claims": n_total,
        "evidence_correct_rate": (n_correct / n_total) if n_total else 0.0,
    }


def _baseline_metrics(held_out_only: bool = False) -> dict:
    s = json.loads(PHASE2_BASELINE_SUMMARY.read_text())
    rows = s["rows"]
    if held_out_only:
        split_path = Path("/home/peter/datasets/satdiff_stage2/satdiff_stage2_split.json")
        held_dates = set(json.loads(split_path.read_text())["held_out_backtest_dates"])
        rows = [r for r in rows if r["date_target"] in held_dates]
    n = len(rows)
    total_corr = sum((r["metrics"].get("severity_corrections") or 0) for r in rows)
    overall_urgent = sum(1 for r in rows if r.get("overall_status") == "urgent")
    schema_valid = sum(1 for r in rows if r["metrics"].get("schema_valid"))
    # Grade evidence on the appropriate subset
    base_dir = REPO_ROOT / "phase2" / "out" / "jagersfontein"
    if held_out_only:
        split_path = Path("/home/peter/datasets/satdiff_stage2/satdiff_stage2_split.json")
        held_dates = set(json.loads(split_path.read_text())["held_out_backtest_dates"])
        ev = _grade_evidence_filtered(base_dir, held_dates)
    else:
        ev = _grade_evidence(base_dir)
    return {
        "n_passes": n,
        "schema_valid": schema_valid,
        "total_severity_corrections": total_corr,
        "mean_severity_corrections": total_corr / max(n, 1),
        "overall_urgent_count": overall_urgent,
        **ev,
    }


def _grade_evidence_filtered(per_pass_dir: Path, held_dates: set) -> dict:
    files = sorted(p for p in per_pass_dir.glob("*.json")
                   if p.name != "summary.json" and p.name[:4].isdigit()
                   and p.stem in held_dates)
    n_correct = 0
    n_total = 0
    for f in files:
        d = json.loads(f.read_text())
        if not d.get("image_available"):
            continue
        for c in (d.get("stage_b_parsed") or {}).get("claims", []):
            cid = c.get("id")
            ev = c.get("evidence", "")
            if cid in EVIDENCE_RX:
                n_total += 1
                if EVIDENCE_RX[cid].search(ev):
                    n_correct += 1
    return {
        "evidence_correct_claims": n_correct,
        "evidence_total_claims": n_total,
        "evidence_correct_rate": (n_correct / n_total) if n_total else 0.0,
    }


def run_eval(model_id: str, label: str, asset: str = "jagersfontein",
             start: str = "2021-06-15", end: str = "2022-10-15",
             held_out_only: bool = False) -> dict:
    dates = _bulk_dates_from_phase1(asset, start, end)
    if held_out_only:
        # Restrict to the held-out backtest dates from build_stage2_split.py
        # — measures clean generalization on inputs the model didn't train on.
        split_path = Path("/home/peter/datasets/satdiff_stage2/satdiff_stage2_split.json")
        if not split_path.exists():
            raise FileNotFoundError(
                f"--held-out-only requires {split_path} (generated by "
                f"training/build_stage2_split.py)."
            )
        held_dates = set(json.loads(split_path.read_text())["held_out_backtest_dates"])
        dates = [d for d in dates if d in held_dates]
        print(f"[eval] HELD-OUT-ONLY mode: {len(dates)} of {len(set(_bulk_dates_from_phase1(asset, start, end)))} backtest passes")
    print(f"[eval] {len(dates)} passes  model={model_id}")

    vlm = make_vlm(model_id=model_id).load()

    out_dir = REPO_ROOT / "phase2" / "out" / f"{asset}_eval_{label}"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    rows = []
    prior: list[dict] = []
    for i, d in enumerate(dates, 1):
        rec = run_pass(asset, d, vlm=vlm, prior_reports=prior)
        rec_path = out_dir / f"{d}.json"
        rec_path.write_text(json.dumps(rec, indent=2, default=str))
        rows.append(rec)
        parsed = rec.get("stage_b_parsed")
        if parsed:
            prior = (prior + [parsed])[-3:]
        m = rec.get("metrics") or {}
        print(f"  [{i:>2}/{len(dates)}] {d}  schema={m.get('schema_valid')} "
              f"corr={m.get('severity_corrections')} overall={(rec.get('stage_b_parsed') or {}).get('overall_status')}")

    n = len(rows)
    total_corr = sum((r["metrics"].get("severity_corrections") or 0) for r in rows)
    overall_urgent = sum(1 for r in rows if (r.get("stage_b_parsed") or {}).get("overall_status") == "urgent")
    schema_valid = sum(1 for r in rows if r["metrics"].get("schema_valid"))

    ev = _grade_evidence(out_dir)
    finetuned = {
        "n_passes": n,
        "schema_valid": schema_valid,
        "total_severity_corrections": total_corr,
        "mean_severity_corrections": total_corr / max(n, 1),
        "overall_urgent_count": overall_urgent,
        **ev,
    }
    baseline = _baseline_metrics(held_out_only=held_out_only)
    delta = {
        "severity_corrections_delta": baseline["total_severity_corrections"] - finetuned["total_severity_corrections"],
        "mean_severity_corrections_delta": baseline["mean_severity_corrections"] - finetuned["mean_severity_corrections"],
        "evidence_correct_rate_delta": finetuned["evidence_correct_rate"] - baseline["evidence_correct_rate"],
    }
    summary = {
        "label": label,
        "model": model_id,
        "baseline": baseline,
        "finetuned": finetuned,
        "delta": delta,
    }

    EVAL_OUT_ROOT.mkdir(parents=True, exist_ok=True)
    (EVAL_OUT_ROOT / f"eval_{label}.json").write_text(json.dumps(summary, indent=2))
    print(f"\n[eval] severity_corrections: baseline={baseline['total_severity_corrections']} "
          f"finetuned={finetuned['total_severity_corrections']}  "
          f"Δ={delta['severity_corrections_delta']:+d}")
    print(f"[eval] evidence_correct_rate: baseline={baseline['evidence_correct_rate']:.1%} "
          f"finetuned={finetuned['evidence_correct_rate']:.1%}  "
          f"Δ={delta['evidence_correct_rate_delta']:+.1%}")
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="HF id or local checkpoint path")
    ap.add_argument("--label", required=True, help="short tag like 'stage1' or 'stage2'")
    ap.add_argument("--asset", default="jagersfontein")
    ap.add_argument("--start", default="2021-06-15")
    ap.add_argument("--end", default="2022-10-15")
    ap.add_argument("--held-out-only", action="store_true",
                    help="Restrict eval to the held-out backtest dates "
                         "from build_stage2_split.py — measures clean "
                         "generalization on inputs the model didn't train on.")
    args = ap.parse_args(argv)
    run_eval(args.model, args.label, args.asset, args.start, args.end,
             held_out_only=args.held_out_only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
