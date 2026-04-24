# SimSat Scout Memo

**Source:** `github.com/DPhi-Space/SimSat` (cloned, shallow, inspected). Roughly 950 lines of Python across sim + dashboard.

## What SimSat actually is

SimSat is a **data-access simulator**, not a **compute-environment simulator**. Two Docker services:

1. **`sim`** (FastAPI on port 9005 → 8000 inside container)
   - Uses `pyorbital.Orbital` to propagate a TLE → computes satellite lon/lat/alt as a function of simulation time.
   - Provides REST endpoints to fetch imagery *as if* the satellite had just flown over that ground point.
   - Does NOT model compute budgets, memory limits, power, thermal, radiation, or bandwidth.
   - Default altitude per the example metadata is ~800 km (typical LEO, close to Sentinel-2's 786 km sun-sync orbit).

2. **`dashboard`** (Django + React/Vite on port 8000)
   - Web UI to start / pause / reset the sim.
   - Visualises orbit and provides a control API (POST `http://localhost:8000/api/commands/`).
   - Contains a sqlite DB — used for telemetry persistence.

## Imaging providers (the important part)

### `SentinelProvider` (`src/sim/ImagingProviders/sentinel_provider.py`)
- Backing store: **Element 84's public STAC endpoint** (`earth-search.aws.element84.com/v1`, collection `sentinel-2-l2a`).
- Uses `pystac-client` + `odc.stac` to fetch real Sentinel-2 Level-2A tiles.
- Accepts spectral-band list (default RGB; we'll pass multispectral).
- Default image size: 5 km × 5 km bbox around the sim's current lon/lat. Configurable via `size_km`.
- Default time window: 10 days — returns the *newest* S2 scene within (current_sim_time − 10 days, current_sim_time).
- Returns PNG or raw array + metadata (cloud_cover, platform, datetime, footprint).
- **Caveat from the README:** "The Sentinel-2 API is quite slow." Expect seconds per fetch.

### `MapboxProvider` (`src/sim/ImagingProviders/mapbox_provider.py`)
- High-resolution RGB static imagery (10–30 cm) via Mapbox static-images API.
- **Cloud-free, static, no timestamp, no radiometric accuracy.** Useful for visual demo aesthetics; useless for the backtest.
- Requires `MAPBOX_ACCESS_TOKEN` env var (free tier available).

## API surface

| Endpoint | Purpose | For SatDiff |
|----------|---------|-------------|
| `GET /data/current/position` | Current lon/lat/alt + timestamp | Used to check which asset the sim is over. |
| `GET /data/current/image/sentinel` | Sentinel-2 tile for the *simulated current* position | Gating: if sim is over Jagersfontein tile, trigger pipeline. |
| `GET /data/current/image/mapbox` | Mapbox RGB for current position | Demo visual only. |
| `GET /data/image/sentinel?lon=&lat=&timestamp=&spectral_bands=&size_km=` | **Sentinel-2 tile for arbitrary lon/lat/time** | **Crucial for backtest:** we can fast-forward the sim or just call this endpoint directly for each historical Jagersfontein pass. |
| `GET /data/image/mapbox?lon_target=&lat_target=&lon_satellite=...` | Mapbox RGB for arbitrary position | Demo visual only. |
| `POST /api/commands/` (on dashboard) | start / pause / reset / set speed / set start_time | Scriptable — we can drive the whole backtest programmatically. |

## How SatDiff plugs in

The clean integration pattern:

```
┌──────────────────┐      HTTP      ┌──────────────────────┐
│  SatDiff pipeline│ ─────────────► │  SimSat /data/...    │
│  (our code)      │ ◄───────────── │  (Sentinel-2, pos.)  │
└──────────────────┘   images+meta  └──────────────────────┘
        │
        ▼
┌──────────────────┐
│ Physical-diff    │  Python, same process or separate
│ module           │
└──────────────────┘
        │
        ▼
┌──────────────────┐
│  Gate            │
└──────────────────┘
        │
        ▼
┌──────────────────┐
│  LFM2-VL via LEAP│  SDK call, local
│  (conditional)   │
└──────────────────┘
        │
        ▼
┌──────────────────┐
│  Structured JSON │ ─► Published to dashboard telemetry
│  report          │   (or our own log)
└──────────────────┘
```

Two usage modes:

1. **Backtest mode** — call `GET /data/image/sentinel?lon=-25.428&lat=-29.756&timestamp=...` in a loop over the Jagersfontein study period (2015–2022). SimSat fetches each historical tile from Element 84. We run our full pipeline on each tile. Fast — bounded by STAC fetch latency, not orbit propagation.
2. **Aesthetic mode** — for the demo video, boot SimSat normally, let the orbit propagator run, watch the satellite "pass over" Jagersfontein, see the pipeline fire. This is what plan §363 calls for.

## What SimSat does NOT provide

- **No Sentinel-1 SAR.** We need to side-load SAR. Options: (a) Microsoft Planetary Computer STAC for Sentinel-1 GRD; (b) use published Grebby ISBAS time series as a structured summary only (no images); (c) ignore SAR for Jagersfontein primary case (multispectral is sufficient there) and only invoke it for the Brumadinho secondary case.
- **No compute constraints.** We run inference on whatever hardware the host has. The "on-satellite compute realism" framing is something we impose in our architectural narrative, not something SimSat enforces. (See `research/satellite-architecture.md` for the realism assumptions.)
- **No bandwidth or downlink model.** We self-impose a per-pass report size budget (<10 KB).
- **No radiation / fault model.** Out of scope; not relevant for hackathon demo.
- **No L2A atmospheric correction surprises.** SimSat fetches L2A directly, which means surface reflectance is pre-computed by Copernicus. Our physical-diff module can assume L2A inputs.

## Dev ergonomics

- Python 3.11, Docker Compose up-and-running.
- Dependencies are standard EO stack: `pystac-client`, `odc.stac`, `rasterio` (via GDAL, hence the Dockerfile expat link workaround), `numpy`, `matplotlib`, `fastapi`, `uvicorn`, `pyorbital`, `cartopy`.
- `scripts/api_test.py` is the reference client.
- Dashboard has a sqlite DB persisted in a Docker volume.

## Recommendation for laptop spike

When you get to laptop:

1. `docker compose up` and verify dashboard + sim API responsive.
2. Run `scripts/api_test.py sentinel_multispectral` to confirm multi-band fetch works.
3. Call `/data/image/sentinel` directly for Jagersfontein coords (`lat=-29.756, lon=-25.428`, approx) at a known-clean pre-failure date (e.g., 2019-03-01) — confirm we can retrieve the 2019 erosion-gully signal visually.
4. Then wire SatDiff's pipeline into it. No need to modify SimSat itself.

## One pragmatic note

SimSat's Sentinel-2 backend (Element 84 STAC) is the same source we'd use independently via Planetary Computer or earth-search. **There is no advantage to routing backtest fetches through SimSat versus hitting Element 84 directly**, except for (a) grading rubric alignment if the judges want us to use SimSat, and (b) the demo-video visual sequence.

Suggested split:
- **Backtest processing:** hit Element 84 directly (or Microsoft Planetary Computer) from our own code. Faster, scriptable, parallelisable.
- **Demo video sequence:** run the final Jagersfontein backtest *through* SimSat so the dashboard shows the satellite passing over, images rendering, pipeline reports appearing. This is the plan §363 aesthetic.

Both hit the same underlying archive; SimSat is for the narrative, not the compute.

## Sources

- [DPhi-Space/SimSat GitHub](https://github.com/DPhi-Space/SimSat)
- [Element 84 earth-search STAC](https://earth-search.aws.element84.com/v1)
- [Microsoft Planetary Computer (alternative STAC)](https://planetarycomputer.microsoft.com/)
- [pyorbital library](https://github.com/pytroll/pyorbital)
- [odc-stac library](https://github.com/opendatacube/odc-stac)
