"""Phase 3 CLI — single + bulk per-pass PDF rendering.

    python -m phase3 --asset jagersfontein --date 2022-01-15
    python -m phase3 --asset jagersfontein --date-range 2021-06-15,2022-10-15
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from phase3.render_pdf import render_pass_pdf, PHASE2_OUT


def _bulk_dates(asset: str, start: str, end: str) -> list[str]:
    """Pick all phase2 record dates in [start, end] (inclusive)."""
    asset_dir = PHASE2_OUT / asset
    if not asset_dir.is_dir():
        raise FileNotFoundError(
            f"No Phase 2 output dir at {asset_dir}. "
            f"Run `python -m phase2.cli --asset {asset} --date-range ...` first."
        )
    out = []
    for p in sorted(asset_dir.glob("*.json")):
        if p.stem == "summary":
            continue
        if start <= p.stem <= end:
            # only include passes that produced imagery
            try:
                rec = json.loads(p.read_text())
            except Exception:
                continue
            if rec.get("image_available"):
                out.append(p.stem)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset", required=True)
    ap.add_argument("--date", help="YYYY-MM-DD for one PDF")
    ap.add_argument("--date-range", help="START,END for bulk over phase2 outputs")
    args = ap.parse_args(argv)

    if bool(args.date) == bool(args.date_range):
        ap.error("specify exactly one of --date / --date-range")

    if args.date:
        out = render_pass_pdf(args.asset, args.date)
        print(f"[phase3] wrote {out}")
        return 0

    start, end = [s.strip() for s in args.date_range.split(",", 1)]
    dates = _bulk_dates(args.asset, start, end)
    print(f"[phase3] bulk over {len(dates)} passes  {start} → {end}")
    for i, d in enumerate(dates, 1):
        out = render_pass_pdf(args.asset, d)
        print(f"  [{i:>2}/{len(dates)}] {d}  →  {out.name}")
    print(f"[phase3] wrote {len(dates)} PDFs to phase3/out/{args.asset}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
