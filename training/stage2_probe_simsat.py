"""SimSat availability probe — confirm which (asset, target_date) pairs
return imagery before we waste author time on dead pulls.

Hits SimSat at localhost:9005/data/image/sentinel?return_type=json for each
candidate (asset, baseline_date, current_date) pair, with a small ±15-day
SimSat search window. Writes a json summary plus a markdown skip log.

Date pairs are seeded from the research papers' cited timeframes, deliberately
choosing windows that should be cleanly available in the Sentinel-2 archive
(2017+ for full S2A+S2B coverage, 2015+ for S2A-only).

Output:
    training/stage2_handauthored/availability_probe.json — per-pair record:
        {asset, role: 'baseline'|'current', target_date, image_available,
         cloud_cover, sentinel_datetime, sentinel_source}
    training/stage2_handauthored/skipped.md — line-per-skip with reason

Run:
    UV_PROJECT_ENVIRONMENT=/home/peter/.satdiff-venvs/spikes \
      uv run --directory /mnt/c/Users/peter/SatDiff/spikes \
      python /mnt/c/Users/peter/SatDiff/training/stage2_probe_simsat.py

Estimated runtime: ~2-5 min for 12 assets × 2 dates each.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path("/mnt/c/Users/peter/SatDiff")
sys.path.insert(0, str(REPO_ROOT))

from phase1.loader import ASSETS, SIM_BASE, WINDOW_SECONDS

OUT_DIR = REPO_ROOT / "training" / "stage2_handauthored"
PROBE_PATH = OUT_DIR / "availability_probe.json"
SKIPPED_PATH = OUT_DIR / "skipped.md"

# Cloud-cover ceiling we accept as "usable" (matches Phase 1 gate's permissive
# bound — we just need imagery the user can SEE the asset in).
CLOUD_CEILING = 60.0


# Candidate (asset, role, target_date) probes. Two probes per asset: one
# baseline (earlier in time) and one "current" (later, the date the example
# narrates). Dates are picked to maximise S2 archive availability and align
# with the source paper's described phenomenon.
CANDIDATES: list[tuple[str, str, str]] = [
    # Tier 2 — routine. Initial dates updated based on first-probe findings.
    # Aswan: seasonal cycle (Miky 2019 cites "2017 and 2018 datasets").
    ("aswan",          "baseline", "2018-01-15"),  # low water — confirmed 9.7% cloud ✓
    ("aswan",          "current",  "2018-07-15"),  # high water — confirmed 0.1% ✓
    # Three Gorges: subtropical mountainous Hubei is persistently cloudy.
    # Winter dry-season is the ONLY consistently clear window.
    ("three_gorges",   "baseline", "2021-01-15"),  # mid-winter dry
    ("three_gorges",   "current",  "2023-01-15"),  # 2-year cyclic, mid-winter
    # Hoover/Mead: arid US Southwest, very low cloud generally.
    ("hoover_mead",    "baseline", "2017-09-15"),  # confirmed 15.5% ✓
    ("hoover_mead",    "current",  "2022-11-15"),  # autumn (post wildfire-smoke season)
    # Kariba: Bucket C "Low-Moderate" — basin-wide LULC.
    ("kariba",         "baseline", "2018-10-15"),  # confirmed 0.3% ✓
    ("kariba",         "current",  "2020-04-15"),  # confirmed 0.0% ✓

    # Tier 3 — catastrophic / distress
    # Brumadinho: Jan 25, 2019 collapse. First-probe: baseline ok, current cloudy.
    ("brumadinho",     "baseline", "2019-01-15"),  # confirmed 22.7% ✓
    ("brumadinho",     "current",  "2019-04-15"),  # 2.5 months post-collapse, drier
    # Mariana / Fundão: Nov 5, 2015. SE Brazil dry season is May-Sept.
    ("mariana_fundao", "baseline", "2017-07-15"),  # confirmed 25.0% ✓
    ("mariana_fundao", "current",  "2019-08-15"),  # later dry-season comparison
    # Toddbrook: August 2019.
    ("toddbrook",      "baseline", "2019-05-15"),  # confirmed 25.4% ✓
    ("toddbrook",      "current",  "2019-08-15"),  # confirmed 46.8% ✓ (just under ceiling)
    # Edenville: May 2020. Michigan dry windows are autumn (Sept-Oct).
    ("edenville",      "baseline", "2019-10-15"),  # mid-autumn, drier
    ("edenville",      "current",  "2020-05-15"),  # confirmed 8.6% ✓
    # Nova Kakhovka: June 6, 2023 destruction. Eastern Ukraine clearest in
    # late winter / early spring before vegetation greens up.
    ("nova_kakhovka",  "baseline", "2023-02-15"),  # late winter, drier
    ("nova_kakhovka",  "current",  "2023-08-15"),  # confirmed 2.4% ✓
    # Derna: September 2023.
    ("derna",          "baseline", "2023-07-15"),  # confirmed 0.0% ✓
    ("derna",          "current",  "2023-09-15"),  # confirmed 9.4% ✓
    # Oroville: Feb 2017 incident. Pre-event 2016 sparse + Sept California
    # often has wildfire smoke. Use late-summer / autumn dates that are
    # historically drier and clearer in N California.
    ("oroville",       "baseline", "2018-10-15"),  # mid-autumn (after summer fires)
    ("oroville",       "current",  "2019-07-15"),  # mid-summer post-repair, drier
]


def _probe_one(asset_id: str, target_date: str, timeout: float = 90.0) -> dict[str, Any]:
    asset = ASSETS[asset_id]
    timestamp = f"{target_date}T08:00:00"
    # SimSat's API requires `return_type` ∈ {array, png}. Single-band array is
    # the cheapest probe — we only read the metadata, never the payload.
    params = {
        "lon": asset.lon,
        "lat": asset.lat,
        "timestamp": timestamp,
        "spectral_bands": ["red"],
        "size_km": asset.size_km,
        "window_seconds": WINDOW_SECONDS,
        "return_type": "array",
    }
    t0 = time.perf_counter()
    try:
        r = requests.get(f"{SIM_BASE}/data/image/sentinel", params=params, timeout=timeout)
    except requests.RequestException as e:
        return {"error": f"request failed: {e}", "latency_seconds": time.perf_counter() - t0}
    latency = time.perf_counter() - t0
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text[:200]}",
                "latency_seconds": round(latency, 2)}
    body = r.json()
    sm = body.get("sentinel_metadata") or {}
    return {
        "image_available": bool(sm.get("image_available")),
        "cloud_cover": sm.get("cloud_cover"),
        "sentinel_datetime": sm.get("datetime"),
        "sentinel_source": sm.get("source"),
        "footprint": sm.get("footprint"),
        "latency_seconds": round(latency, 2),
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[probe] {len(CANDIDATES)} (asset, role, date) candidates")
    print(f"[probe] cloud_ceiling={CLOUD_CEILING}%")

    rows: list[dict[str, Any]] = []
    skipped: list[str] = []
    by_asset: dict[str, dict[str, dict[str, Any]]] = {}

    for asset_id, role, target_date in CANDIDATES:
        result = _probe_one(asset_id, target_date)
        avail = result.get("image_available", False)
        cc = result.get("cloud_cover")
        cc_str = f"{cc:.1f}%" if isinstance(cc, (int, float)) else "n/a"
        status_tag = "✓" if avail and (cc is None or cc <= CLOUD_CEILING) else "✗"
        print(f"  {status_tag} {asset_id:<16} {role:<8} {target_date}  "
              f"available={avail}  cloud={cc_str}  source={result.get('sentinel_source')}")
        row = {"asset": asset_id, "role": role, "target_date": target_date, **result}
        rows.append(row)
        by_asset.setdefault(asset_id, {})[role] = row

        if not avail:
            skipped.append(f"- **{asset_id} {role} {target_date}** — no image_available "
                           f"({result.get('error', 'SimSat returned image_available=False')})")
        elif isinstance(cc, (int, float)) and cc > CLOUD_CEILING:
            skipped.append(f"- **{asset_id} {role} {target_date}** — cloud {cc:.1f}% > "
                           f"ceiling {CLOUD_CEILING}%")

    summary = {
        "n_probed": len(rows),
        "n_available": sum(1 for r in rows if r.get("image_available")),
        "cloud_ceiling": CLOUD_CEILING,
        "rows": rows,
        "by_asset": by_asset,
    }
    PROBE_PATH.write_text(json.dumps(summary, indent=2))
    print(f"\n[probe] wrote {PROBE_PATH}")

    # Append-only skipped log; if the file already exists, preserve prior
    # human-authored skips and add today's automated section.
    header = "# Stage 2 — skipped scenarios\n\n"
    section = ["## Availability probe " + time.strftime("%Y-%m-%d %H:%M") + "\n"]
    if skipped:
        section.extend(skipped)
    else:
        section.append("- (no skips — all probed pairs available within cloud ceiling)")
    section.append("\n")
    if SKIPPED_PATH.exists():
        prev = SKIPPED_PATH.read_text()
        SKIPPED_PATH.write_text(prev.rstrip() + "\n\n" + "\n".join(section))
    else:
        SKIPPED_PATH.write_text(header + "\n".join(section))
    print(f"[probe] wrote {SKIPPED_PATH}")
    print(f"[probe] {summary['n_available']}/{summary['n_probed']} pairs available")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
