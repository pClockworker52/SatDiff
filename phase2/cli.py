"""Phase 2 CLI — single + bulk passes.

    python -m phase2 --asset jagersfontein --date 2021-12-30
    python -m phase2 --asset jagersfontein --date-range 2021-06-15,2022-10-15
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from phase2.runner import DEFAULT_MODEL_ID, make_vlm, run_pass

REPO_ROOT = Path(os.environ.get("SATDIFF_REPO_ROOT", "/mnt/c/Users/peter/SatDiff"))
PHASE2_OUT = REPO_ROOT / "phase2" / "out"
PHASE1_SUMMARY = REPO_ROOT / "phase1" / "out"
N_PRIOR_REPORTS = 3


def _persist(rec: dict) -> Path:
    asset = rec["asset_id"]
    out_dir = PHASE2_OUT / asset
    out_dir.mkdir(parents=True, exist_ok=True)
    name = rec["date_target"]
    p = out_dir / f"{name}.json"
    p.write_text(json.dumps(rec, indent=2, default=str))
    return p


def _bulk_dates_from_phase1(asset: str, start: str, end: str) -> list[str]:
    """Use phase1's summary.json to pick invoke_vlm=true rows in date range."""
    p = PHASE1_SUMMARY / asset / "summary.json"
    if not p.exists():
        raise FileNotFoundError(
            f"No phase1 summary at {p}. Run `python -m phase1 --asset {asset} "
            f"--date-range {start},{end}` first."
        )
    summary = json.loads(p.read_text())
    out = []
    for row in summary.get("rows", []):
        if not row.get("invoke_vlm"):
            continue
        d = row.get("date_target")
        if d and start <= d <= end:
            out.append(d)
    return sorted(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset", required=True)
    ap.add_argument("--date", help="YYYY-MM-DD for one pass")
    ap.add_argument("--date-range", help="START,END for bulk over phase1 invoked rows")
    ap.add_argument("--model", default=DEFAULT_MODEL_ID, help="HF model id or local path")
    ap.add_argument("--inference", choices=("transformers", "llama_server"), default=None,
                    help="Inference transport. Overrides SATDIFF_INFERENCE.")
    args = ap.parse_args(argv)

    if bool(args.date) == bool(args.date_range):
        ap.error("specify exactly one of --date / --date-range")

    if args.inference:
        os.environ["SATDIFF_INFERENCE"] = args.inference
    backend = os.environ.get("SATDIFF_INFERENCE", "transformers")
    print(f"[phase2] loading model {args.model} via {backend}…")
    vlm = make_vlm(model_id=args.model).load()
    print(f"[phase2] model ready.")

    if args.date:
        rec = run_pass(args.asset, args.date, vlm=vlm, prior_reports=[])
        out = _persist(rec)
        m = rec.get("metrics") or {}
        if rec.get("image_available", False):
            parsed = rec.get("stage_b_parsed") or {}
            print(f"  {args.date}: schema_valid={m.get('schema_valid')} "
                  f"latency_a={m.get('latency_seconds_stage_a')}s "
                  f"latency_b={m.get('latency_seconds_stage_b')}s "
                  f"pond_mentions={m.get('claims_with_evidence_mentioning_pond')} "
                  f"metric_hits={m.get('claims_with_evidence_mentioning_metric_value')} "
                  f"overall={parsed.get('overall_status')!r} "
                  f"escalation={parsed.get('regulatory_escalation_flag')}")
        else:
            print(f"  {args.date}: skipped — {rec.get('skipped')}")
        print(f"[phase2] wrote {out}")
        return 0

    # Bulk
    start, end = [s.strip() for s in args.date_range.split(",", 1)]
    dates = _bulk_dates_from_phase1(args.asset, start, end)
    print(f"[phase2] bulk over {len(dates)} phase1-invoked passes  {start} → {end}")
    rows: list[dict] = []
    prior: list[dict] = []
    for i, d in enumerate(dates, 1):
        print(f"[phase2] {i}/{len(dates)} {d}")
        rec = run_pass(args.asset, d, vlm=vlm, prior_reports=prior)
        _persist(rec)
        rows.append(rec)
        # Roll the prior-reports buffer with the parsed Stage B output, if any.
        parsed = rec.get("stage_b_parsed")
        if parsed:
            prior = (prior + [parsed])[-N_PRIOR_REPORTS:]
        m = rec.get("metrics") or {}
        if rec.get("image_available"):
            parsed = rec.get("stage_b_parsed") or {}
            print(f"    schema_valid={m.get('schema_valid')} "
                  f"lat_a={m.get('latency_seconds_stage_a')}s "
                  f"lat_b={m.get('latency_seconds_stage_b')}s "
                  f"pond={m.get('claims_with_evidence_mentioning_pond')} "
                  f"metric_hit={m.get('claims_with_evidence_mentioning_metric_value')} "
                  f"overall={parsed.get('overall_status')!r}")
        else:
            print(f"    skipped: {rec.get('skipped')}")

    # Aggregate stats
    n_avail = sum(1 for r in rows if r.get("image_available"))
    n_valid = sum(1 for r in rows if (r.get("metrics") or {}).get("schema_valid"))
    n_pond = sum(1 for r in rows if (r.get("metrics") or {}).get("claims_with_evidence_mentioning_pond", 0) >= 1)
    n_metric = sum(1 for r in rows if (r.get("metrics") or {}).get("claims_with_evidence_mentioning_metric_value", 0) >= 1)
    summary = {
        "asset_id": args.asset,
        "model_id": args.model,
        "n_passes": len(rows),
        "n_image_available": n_avail,
        "n_schema_valid": n_valid,
        "n_pond_mentions_ge1": n_pond,
        "n_metric_value_hits_ge1": n_metric,
        "schema_valid_rate": round(n_valid / max(n_avail, 1), 3),
        "rows": [
            {
                "date_target": r["date_target"],
                "schema_valid": (r.get("metrics") or {}).get("schema_valid"),
                "overall_status": (r.get("stage_b_parsed") or {}).get("overall_status"),
                "regulatory_escalation_flag": (r.get("stage_b_parsed") or {}).get("regulatory_escalation_flag"),
                "claim_severities": [
                    (c.get("id"), c.get("severity_level"))
                    for c in ((r.get("stage_b_parsed") or {}).get("claims") or [])
                    if isinstance(c, dict)
                ],
                "metrics": r.get("metrics"),
                "phase1_diff_summary": {
                    "pond_area_m2": ((r.get("phase1_diff") or {}).get("pond") or {}).get("area_m2"),
                    "pond_to_wall_distance_m": ((r.get("phase1_diff") or {}).get("pond") or {}).get("pond_to_wall_distance_m"),
                    "deposition_asymmetry_index": ((r.get("phase1_diff") or {}).get("impoundment") or {}).get("deposition_asymmetry_index"),
                    "gully_count": ((r.get("phase1_diff") or {}).get("retaining_wall") or {}).get("gully_count"),
                },
            }
            for r in rows
        ],
    }
    out_path = PHASE2_OUT / args.asset / "summary.json"
    out_path.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\n[phase2] {n_valid}/{n_avail} schema valid; {n_pond}/{n_avail} pond-mentions≥1; "
          f"{n_metric}/{n_avail} metric-value-hits≥1")
    print(f"[phase2] wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
