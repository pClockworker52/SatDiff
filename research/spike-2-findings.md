# Spike 2 — SimSat archive loop

**Date:** 2026-04-25.
**Plan:** `~/.claude/plans/spike-2-simsat-archive-loop.md`.
**Verdict:** **VIABLE — Path A's criterion-1 (DPhi API ingress) confirmed. No SimSat patch needed.**

This spike validates rubric criterion 1 ("Use of satellite imagery from the
DPhi API", 10%): the final pipeline must consume Sentinel-2 through SimSat's
`GET /data/image/sentinel`, not via direct STAC. The earlier worry that
Element 84 STAC was empty was retracted in `research/spike-1-findings.md`
Surprises (the "empty" result was a malformed GET `query=` against the v1
stac-server; `pystac-client`, which SimSat uses internally, returns tiles
cleanly via POST). Spike 2 confirmed this end-to-end: stock SimSat returns
Jagersfontein tiles for 4 of 5 Torres-Cruz milestone dates and 17 of 17
months in a rolling 2021-06 → 2022-10 window, with median latency 5.02 s.

## Setup

| Field | Value |
|-------|-------|
| SimSat repo | `https://github.com/DPhi-Space/SimSat.git` |
| SimSat commit | `52f5619330c1edbb2e330b2961a1a551bebc0d69` |
| Local clone | `/home/peter/SimSat` (ext4) |
| Patch needed | **NO** — stock SimSat works |
| Local additions | `/home/peter/SimSat/.dockerignore` (skips `src/dashboard/frontend/node_modules` to dodge a BuildKit `unknown file mode` checksum error on a committed `acorn` symlink) and `/home/peter/SimSat/.env` (sets `MAPBOX_ACCESS_TOKEN=spike2-dummy-not-used` because `api.py` initialises `MapboxlProvider` eagerly and crashes if the env var is absent — Mapbox itself is never called). Both are local-only, not upstreamed |
| Docker | Docker Desktop 28.2.2 on Windows, called from WSL via `docker.exe` |
| Containers | `fakesat-dashboard` (port 8000, healthy), `fakesat-sim` (port 9005) |
| Asset | Jagersfontein TSF, lat=-29.756, lon=25.428, 5 km bbox |
| Bands tested | red, green, blue (3-band PNG; SimSat's `image_to_png` only accepts 1 or 3 bands. Multispectral 5-band path remains via Spike 1's MSPC cache and the `return_type=array` API mode for Phase 1) |
| Window seconds | 2,592,000 (30 days, widened from SimSat's 10-day default for parity with Spike 1) |
| Spike runner | `spikes/archive-pull.py` |

## Step 2 — gating test

Outcome **B** per the plan: backend healthy, one date missed (window/cloud edge case).

| Date target | image_available | cloud cover | datetime returned | latency |
|-------------|-----------------|-------------|-------------------|---------|
| 2021-12-30 | yes | 27.6% | 2021-12-25T08:28:21Z | 6.55 s |
| 2016-10-27 | **no** | – | – | 0.52 s |
| 2022-09-15 | yes | 68.4% | 2022-09-11T08:28:28Z (failure day!) | 5.46 s |

Step 2b (MSPC patch) **was not** triggered.

## Step 3 — curated Torres-Cruz milestone dates

| Date target | Milestone | image_available | cloud | datetime returned | latency |
|-------------|-----------|-----------------|-------|-------------------|---------|
| 2016-10-27 | Spike 1 baseline | **no** | – | – | 0.51 s |
| 2019-02-15 | First erosion gully | yes | 9.9% | 2019-02-14 | 6.42 s |
| 2020-12-15 | DWS cease-deposition directive | yes | 15.5% | 2020-12-10 | 6.24 s |
| 2021-12-30 | Spike 1 pre-failure (pond at wall) | yes | 27.6% | 2021-12-25 | 5.02 s |
| 2022-09-15 | Post-failure | yes | 68.4% | **2022-09-11 (collapse day)** | 3.85 s |

4 of 5 hit. The single miss (2016-10-27) is the same one that missed in step 2 — see "Surprises" below.

## Step 4 — rolling hit-rate window (2021-06 → 2022-10)

**17 / 17 months returned tiles.** Mean cloud cover 12.0%; the only seriously-cloudy month was 2022-09 (68.4% — and that month's tile is the 2022-09-11 failure day itself).

| Month | datetime | cloud | latency |
|-------|----------|-------|---------|
| 2021-06 | 2021-06-13 | 0.9% | 5.21 s |
| 2021-07 | 2021-07-13 | 23.7% | 5.18 s |
| 2021-08 | 2021-08-12 | 0.6% | 5.26 s |
| 2021-09 | 2021-09-11 | 0.005% | 9.37 s |
| 2021-10 | 2021-10-11 | 3.0% | 7.02 s |
| 2021-11 | 2021-11-05 | 31.5% | 4.70 s |
| 2021-12 | 2021-12-10 | 0.6% | 4.68 s |
| 2022-01 | 2022-01-14 | 22.6% | 5.69 s |
| 2022-02 | 2022-02-13 | 0.15% | 5.01 s |
| 2022-03 | 2022-03-10 | 9.5% | 4.88 s |
| 2022-04 | 2022-04-14 | 0.02% | 4.69 s |
| 2022-05 | 2022-05-14 | 1.7% | 4.95 s |
| 2022-06 | 2022-06-13 | 12.9% | 5.18 s |
| 2022-07 | 2022-07-13 | 0.015% | 5.16 s |
| 2022-08 | 2022-08-12 | 9.7% | 5.10 s |
| 2022-09 | **2022-09-11 (failure day)** | 68.4% | 4.17 s |
| 2022-10 | 2022-10-11 | 18.8% | 7.87 s |

Effective revisit ≈ monthly with 1 high-cloud month in 17. Median latency 5.02 s — well under the 30 s viability threshold.

## Step 3 cross-check vs Spike 1 MSPC cache

| Date target | SimSat (Element 84) | MSPC (Spike 1 cache) | Same scene? |
|-------------|---------------------|----------------------|-------------|
| 2016-10-27 | no tile | 2016-10-27, 0.02% cloud, `S2A_MSIL2A_20161027T080022_R035_T35JLH` | **no — Element 84 lacks the 2016 archive** |
| 2021-12-30 | 2021-12-25, 27.6% cloud, sentinel-2b | 2021-12-30, 0.007% cloud, `S2A_MSIL2A_20211230T080331_R035_T35JLH` | **different acquisition dates** within the same window |

Both differences are explained below in "Surprises". Neither is a SimSat bug; both are properties of the underlying STAC archive.

## Decision

**Viable.** Specifically:

- ≥4/5 known-signal dates returned tiles ✓ (4/5)
- Rolling window hit-rate ≥60% ✓ (17/17 = 100%)
- Median latency <30 s ✓ (5.02 s)
- Stock SimSat works as-shipped — no Element 84 → MSPC patch needed ✓
- The 2022-09 query autonomously surfaced the **exact failure day** (2022-09-11) — encouraging signal that the SimSat path will be useful for the demo's "scar" frame

Path A continues. Spike 3 (`leap-finetune` smoke test) is the next gating step.

## Surprises / notes

1. **Element 84's `sentinel-2-l2a` does not index pre-2017 archive for T35JLH.**
   Both the gating call and the Step 3 baseline call for 2016-10-27 returned
   `image_available=false` in 0.5 s (fast = no items in the search response,
   not an error). MSPC found that exact tile via the same `pystac-client` +
   bbox call. Element 84 splits the early Sentinel-2 archive into a separate
   collection: `sentinel-2-pre-c1-l2a`. **Implication for Phase 1's
   backtest:** if a pre-2017 baseline is needed, either (a) extend
   `SentinelProvider` to fall back to `sentinel-2-pre-c1-l2a` when
   `sentinel-2-l2a` returns nothing, or (b) start the Jagersfontein backtest
   from a 2017 or later baseline. Option (b) is fine — Torres-Cruz's
   load-bearing signal starts Feb 2019, and a 2017 or 2018 baseline is
   pre-anomaly. No demo-blocking issue.

2. **SimSat's window is backwards-only**, not centred on the timestamp.
   `build_stac_datetime_window(timestamp, window_seconds)` returns
   `[timestamp − window, timestamp]`. So the timestamp parameter is the END
   of the search window. For `timestamp=2021-12-30` the search covers
   2021-11-30 to 2021-12-30 inclusive, and SimSat picks the **newest** tile
   in that window. **Implication:** when scripting a backtest, the timestamp
   is always the right edge of acceptable acquisition dates, not the centre.
   Document this in Phase 1's data loader.

3. **Different STAC providers index different snapshots of the ESA archive.**
   For 2021-12, MSPC has 2021-12-30 indexed but Element 84 only has
   2021-12-25. Both are real Sentinel-2-B acquisitions; the 5-day
   difference is just provider freshness. SimSat's "newest in window" pick
   reflects what Element 84 has, which can lag MSPC. For Phase 1's backtest
   this is a non-issue (a few-day acquisition jitter is well within the
   monthly cadence we plan for).

4. **SimSat's `image_to_png` rejects multispectral.**
   It accepts only 1 band (greyscale) or exactly 3 bands (RGB). Pulling 5
   bands through `return_type=png` returns HTTP 500. The Phase 1 pipeline
   that needs NDWI / NDMI / SWIR composites must call SimSat with
   `return_type=array` to get the multi-band xarray, then compute indices
   on the client side. This was already the implicit plan.

5. **MapboxProvider is initialised eagerly at sim startup.**
   `api.py` instantiates `MapboxlProvider()` at import time (note the typo
   in the class name — `MapboxlProvider`, with an extra `l`), and the
   constructor raises if `MAPBOX_ACCESS_TOKEN` is unset. This breaks `docker
   compose up` for any user who doesn't have a Mapbox account. Workaround:
   set `MAPBOX_ACCESS_TOKEN=anything` in `.env`. **Implication for Day 13
   submission:** the submission's Docker image must ship a non-empty
   `MAPBOX_ACCESS_TOKEN` value (any string works since we never call the
   Mapbox endpoint). Bake this into the submission's compose file or `.env`.

6. **Committed `node_modules/`** in `src/dashboard/frontend/` blocks
   BuildKit's tar checksum on a symlinked `acorn` binary. The Dockerfile
   does its own `npm ci` inside the container, so a `.dockerignore`
   excluding `src/dashboard/frontend/node_modules` is the clean fix. The
   submission's Docker image build flow needs this dockerignore.

7. **`docker.exe` (Windows binary called from WSL) reaches WSL paths
   via UNC** (`\\wsl.localhost\Ubuntu\home\peter\SimSat`) when WSL
   integration is not enabled in Docker Desktop. Builds and volumes work,
   but performance is moderate. Enabling Docker Desktop's WSL integration
   would speed things up; not required.

## Reproduce

```bash
# One-time setup:
git clone https://github.com/DPhi-Space/SimSat.git /home/peter/SimSat
cat > /home/peter/SimSat/.dockerignore <<'EOF'
src/dashboard/frontend/node_modules
**/__pycache__
*.pyc
.git
db.sqlite3
EOF
cat > /home/peter/SimSat/.env <<'EOF'
MAPBOX_ACCESS_TOKEN=spike2-dummy-not-used
EOF
cd /home/peter/SimSat && docker.exe compose up -d --build

# Run the spike:
export UV_PROJECT_ENVIRONMENT=/home/peter/.satdiff-venvs/spikes
cd /mnt/c/Users/peter/SatDiff/spikes
uv run python archive-pull.py            # full run (~2 min)
uv run python archive-pull.py --gating-only   # quick smoke (~15 s)
```

Outputs:
- `spikes/data/simsat-tiles/<label>.json` — raw response per call (metadata + base64 PNG)
- `spikes/data/png/<label>_simsat.png` — RGB PNG per available tile
- `spikes/out/simsat-archive-summary.json` — full summary table

## Artefacts referenced

- Plan: `~/.claude/plans/spike-2-simsat-archive-loop.md`
- Spike 1 (capability + MSPC cache used for cross-check): `research/spike-1-findings.md`
- Phase-0 verdict (will gain a 2026-04-25 row): `research/phase-0-go-no-go.md`
- Spike script: `spikes/archive-pull.py`
- SimSat scout memo: `research/simsat-scout.md`
- SimSat-side local edits: `/home/peter/SimSat/.dockerignore`, `/home/peter/SimSat/.env`
