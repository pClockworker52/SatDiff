"""Phase 1 CLI — load → diff → gate for one or many passes.

    python -m phase1 --asset jagersfontein --date 2021-12-30
    python -m phase1 --asset jagersfontein --date-range 2021-06-15,2022-10-15

Per-pass JSON outputs land in phase1/out/<asset>/<date>.json (the
contract memo's [CURRENT PASS] block plus a gate decision). For
date-range mode, also writes a top-level summary table.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date as _date
from datetime import timedelta
from pathlib import Path

from phase1.baseline import compute_baseline, load_baseline
from phase1.gate import decide
from phase1.loader import ASSETS, PHASE1_DIR
from phase1.physical_diff import compute_diff

OUT_DIR = PHASE1_DIR / "out"


def run_one(asset_id: str, date: str, prior_skips: int, force: bool) -> dict:
    diff = compute_diff(asset_id, date)
    gate = decide(diff, prior_passes_since_vlm=prior_skips, force=force)
    record = {
        "asset_id": asset_id,
        "date_target": date,
        "image_available": diff is not None,
        "diff": diff,
        "gate": gate.as_dict(),
    }
    out_dir = OUT_DIR / asset_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{date}.json").write_text(json.dumps(record, indent=2))
    return record


def monthly_dates(start: str, end: str) -> list[str]:
    """Mid-month dates between start and end (inclusive)."""
    s = _date.fromisoformat(start)
    e = _date.fromisoformat(end)
    out: list[str] = []
    cur = s.replace(day=15)
    while cur <= e:
        out.append(cur.isoformat())
        nxt_month = (cur.replace(day=1) + timedelta(days=32)).replace(day=15)
        cur = nxt_month
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--asset", required=True, choices=sorted(ASSETS))
    p.add_argument("--date", help="YYYY-MM-DD for a single pass")
    p.add_argument("--date-range", help="START,END (mid-month polls between, inclusive)")
    p.add_argument("--baseline-date", help="If set, recompute baseline using this date.")
    p.add_argument("--force", action="store_true", help="Bypass the gate.")
    args = p.parse_args(argv)

    # Ensure baseline exists; recompute if asked.
    try:
        baseline = load_baseline(args.asset)
    except FileNotFoundError:
        baseline = compute_baseline(args.asset, date=args.baseline_date)
    if args.baseline_date and args.baseline_date != baseline.get("target_date"):
        baseline = compute_baseline(args.asset, date=args.baseline_date)
    print(f"[phase1] baseline date: {baseline['chosen_date']} (cloud {baseline['cloud_cover']:.1f}%)")

    if args.date and args.date_range:
        p.error("specify exactly one of --date / --date-range")

    if args.date:
        rec = run_one(args.asset, args.date, prior_skips=0, force=args.force)
        gate = rec["gate"]
        avail = "y" if rec["image_available"] else "n"
        print(f"  {args.date}: avail={avail}  invoke_vlm={gate['invoke_vlm']}  "
              f"severity={gate['severity_hint']}  reason={gate['reason']}")
        return 0

    if args.date_range:
        start, end = [s.strip() for s in args.date_range.split(",", 1)]
        dates = monthly_dates(start, end)
        print(f"[phase1] {len(dates)} monthly polls {dates[0]} → {dates[-1]}")
        rows = []
        skip_streak = 0
        for d in dates:
            rec = run_one(args.asset, d, prior_skips=skip_streak, force=args.force)
            rows.append(rec)
            if rec["gate"]["invoke_vlm"]:
                skip_streak = 0
            else:
                skip_streak += 1
            avail = "y" if rec["image_available"] else "n"
            cloud = (rec.get("diff") or {}).get("cloud_cover")
            cloud_s = f"{cloud:5.1f}%" if cloud is not None else "  -  "
            pond = (rec.get("diff") or {}).get("pond") or {}
            wall = (rec.get("diff") or {}).get("retaining_wall") or {}
            imp = (rec.get("diff") or {}).get("impoundment") or {}
            area_m2 = pond.get("area_m2")
            p2w = pond.get("pond_to_wall_distance_m")
            asym = imp.get("deposition_asymmetry_index")
            gully = wall.get("gully_count")
            print(f"  {d}  avail={avail}  cloud={cloud_s}  "
                  f"pond_m2={area_m2 if area_m2 is not None else '   -   ':>9}  "
                  f"pond2wall_m={p2w if p2w is not None else '  -  ':>5}  "
                  f"asym={asym if asym is not None else '  -  ':>5}  "
                  f"gully={gully if gully is not None else '-':>3}  "
                  f"invoke={rec['gate']['invoke_vlm']}  ({rec['gate']['severity_hint']})")
        # Summary
        n_avail = sum(1 for r in rows if r["image_available"])
        n_invoke = sum(1 for r in rows if r["gate"]["invoke_vlm"])
        summary = {
            "asset_id": args.asset,
            "baseline": {"date": baseline["chosen_date"], "pond_area_m2": baseline.get("pond_area_m2")},
            "n_polls": len(rows),
            "n_image_available": n_avail,
            "n_vlm_invoked": n_invoke,
            "rows": [
                {
                    "date_target": r["date_target"],
                    "image_available": r["image_available"],
                    "cloud_cover": (r.get("diff") or {}).get("cloud_cover"),
                    "pond_area_m2": ((r.get("diff") or {}).get("pond") or {}).get("area_m2"),
                    "pond_to_wall_m": ((r.get("diff") or {}).get("pond") or {}).get("pond_to_wall_distance_m"),
                    "deposition_asymmetry_index": ((r.get("diff") or {}).get("impoundment") or {}).get("deposition_asymmetry_index"),
                    "gully_count": ((r.get("diff") or {}).get("retaining_wall") or {}).get("gully_count"),
                    "invoke_vlm": r["gate"]["invoke_vlm"],
                    "severity_hint": r["gate"]["severity_hint"],
                    "reason": r["gate"]["reason"],
                }
                for r in rows
            ],
        }
        out = OUT_DIR / args.asset / "summary.json"
        out.write_text(json.dumps(summary, indent=2))
        print(f"\n[phase1] summary: {n_avail}/{len(rows)} tiles available; {n_invoke}/{len(rows)} VLM invoked")
        print(f"[phase1] wrote {out}")
        return 0

    p.error("must specify --date or --date-range")
    return 2


if __name__ == "__main__":
    sys.exit(main())
