# Workstream [2] — Top-level Docker compose

**Status:** ✅ DONE 2026-04-28. Four-service stack builds, comes up healthy, runs a contract pass end-to-end. The rubric's criterion-3 fresh-clone test surface is in place; an actual cross-machine fresh-clone validation is the pre-submission gate but is no longer architecturally blocked.

## What runs

```
                ┌──────────────── docker compose up -d ────────────────┐
                │                                                       │
   ┌────────────┼─ fakesat-dashboard :8000  (SimSat Django dashboard)   │
   │            ├─ fakesat-sim       :9005  (SimSat FastAPI imagery)    │
   │            ├─ llama-server      :8080  (llama.cpp + Stage 1 GGUF)  │
   │            └─ satdiff           (Python pipeline, no host port)    │
   │                                                                   │
   └─ docker compose exec satdiff python -m phase2.cli ...             │
       │                                                                │
       ▼                                                                │
   /app/phase2/out/<asset>/<date>.json   ← persisted on a named volume │
                                                                       │
                                              audit-trail JSON artefact ┘
```

## Verification (in-place; full fresh-clone test is the pre-submission gate)

```bash
$ docker compose build      # ~6 min cold (llama.cpp compile dominates), ~10s cached
$ docker compose up -d      # ~70 s to all-healthy (dashboard 40 s start_period)
$ docker compose ps
NAME                   STATUS                        PORTS
fakesat-dashboard      Up 1m (healthy)               0.0.0.0:8000->8000/tcp
fakesat-sim            Up 1m (healthy)               0.0.0.0:9005->8000/tcp
satdiff-llama-server   Up 1m (healthy)               0.0.0.0:8080->8080/tcp
satdiff                Up 1m

$ docker compose exec satdiff python -m phase2.cli --asset jagersfontein --date 2022-01-15
[phase2] loading model LiquidAI/LFM2.5-VL-450M via llama_server…
[phase2] model ready.
  2022-01-15: schema_valid=True latency_a=8.91s latency_b=16.62s
              pond_mentions=1 metric_hits=2 overall='urgent' escalation=True
[phase2] wrote /app/phase2/out/jagersfontein/2022-01-15.json
```

The Stage B JSON inside that file:

```
overall_status               : urgent
regulatory_escalation_flag   : True
downlink_priority            : immediate
claims (5):
  c1:  elevated  trend=increased  action=flag_for_review
  c2:    urgent  trend=increased  action=urgent_inspection
  c3:    urgent  trend=unchanged  action=urgent_inspection
  c4:   nominal  trend=unchanged  action=none
  c5:    urgent  trend=unchanged  action=urgent_inspection
schema_valid                 : True
```

— matches the rules-engine output we verified locally on CUDA at the same date.

## Latency in Docker

| transport | host | mean total/pass | image footprint | notes |
|---|---|---:|---|---|
| **CPU llama.cpp + Docker** | WSL2 docker | **25.53 s** | 1.4 GB total | Docker overhead ~5 s vs native CPU's 19.88 s |
| native CPU llama.cpp | WSL2 host | 19.88 s | n/a | reference |
| native CUDA llama.cpp | WSL2 host | 2.38 s | n/a | reference; demo-video path |

The Docker run is the rubric's correctness verification surface — judges who run `docker compose up` on a laptop without `nvidia-container-toolkit` get a working pipeline; the demo video carries the latency story. CPU-in-Docker overhead (~5 s/pass) is from WSL2 9p mount + Docker filesystem, not from llama.cpp itself.

## Files added

- `docker-compose.yml` — top-level orchestration, 4 services, shared `satdiff-network` bridge, named volumes for tile cache + per-pass outputs + dashboard DB.
- `Dockerfile.satdiff` — Python 3.11-slim base, manylinux wheels for numpy/scipy/shapely/rasterio/h5netcdf (no GDAL/GEOS apt-install), WeasyPrint runtime libs (Cairo/Pango/GDK-Pixbuf), entrypoint that seeds the named volume from `/app/phase1/data-seed/` on first run.
- `Dockerfile.satdiff.requirements.txt` — pinned `>=` deps; no torch/transformers (we use the `llama_server` transport).
- `Dockerfile.llama-server` — multi-stage build: ubuntu:24.04 builder compiles llama.cpp at SHA `5d56effdeea49413da226d4815db58f515832ead` (target `llama-server`), runtime image carries the binary + .so libs + the 544 MB GGUF pair baked at `/models`.
- `.dockerignore` — top-level, excludes regeneratable artefacts (research/papers, inference/llama.cpp/, training/, phase outputs, .venv) but explicitly keeps `phase1/data/*/baseline.json` so the volume can be seeded.
- `README.md` — quick-start, architecture diagram, repository-layout map, license note.
- `vendor/SimSat/` — vendored snapshot at SHA `52f5619330c1edbb2e330b2961a1a551bebc0d69` plus our spike-2 `.dockerignore` + `.env`. AGPL-compliant (LICENSE preserved + NOTICE.md attribution at `vendor/SimSat/NOTICE.md`).

## Files modified (made env-driven for Docker)

- `phase1/loader.py` — `SIM_BASE` reads `SIMSAT_URL` env (default `http://localhost:9005`); `REPO_ROOT` reads `SATDIFF_REPO_ROOT`.
- `phase2/runner.py` — `REPO_ROOT` reads `SATDIFF_REPO_ROOT`.
- `phase2/cli.py` — `REPO_ROOT` reads `SATDIFF_REPO_ROOT`.

The hardcoded `/mnt/c/Users/peter/SatDiff` defaults remain so local dev is unchanged. Training scripts (`training/`) keep the old hardcoded paths — they only run on the dev box.

## Known issues / pre-submission TODOs

1. **Cross-machine fresh-clone test** — verifying the build works on a clean machine (no Docker BuildKit cache, no apt cache, no pip cache) is the actual rubric test. Run `docker system prune -a` then build from a `git clone` to validate.
2. **GGUF distribution** — currently the Dockerfile.llama-server `COPY`s from `inference/gguf/` (gitignored, generated by `inference/quantize.sh`). For the submission we need to either (a) commit the GGUF pair via git-LFS, or (b) swap the COPY for a `RUN curl -L ...` against the Hugging Face URL once workstream [5] uploads them. Plan v2 favors option (b).
3. **MAPBOX_ACCESS_TOKEN** — the `fakesat-sim` service expects it. We default to `judge-dummy-not-used` via `${MAPBOX_ACCESS_TOKEN:-judge-dummy-not-used}` in compose. The dummy is sufficient for the Sentinel-only path; document this in the README if a judge questions the variable.
4. **Container restart resilience** — if `llama-server` is restarted, satdiff picks up the new connection on the next request thanks to `requests` re-resolving DNS. No keep-alive bug observed in testing.
