# SatDiff

> Compact-report tailings-storage-facility (TSF) monitoring system.
> On-board contract-framed VLM + Python rules engine, producing 2 KB
> structured audit-trail reports per satellite pass.
>
> Submission to the Liquid AI "AI in Space" hackathon — Liquid Track.

## Quick start

The only command required:

```bash
git clone <satdiff-repo-url> judge && cd judge && docker compose up -d
```

That brings up four services on a shared Docker bridge network:

| service | port | purpose |
|---|---:|---|
| `fakesat-dashboard` | 8000 | DPhi SimSat dashboard (telemetry receiver) |
| `fakesat-sim` | 9005 | DPhi SimSat API — Sentinel-2 imagery endpoint |
| `llama-server` | 8080 | llama.cpp HTTP server hosting the Stage 1 GGUF Q8_0 + F16 mmproj pair |
| `satdiff` | — | Pipeline (phase1 physical-diff → phase2 contract VLM → phase3 PDF) |

Initial bring-up is ~60 s for healthchecks (longest is the Django dashboard's 40 s warm-up). Total disk: ~2 GB images.

### Run a pass

```bash
docker compose exec satdiff python -m phase2.cli \
    --asset jagersfontein \
    --date 2022-01-15
```

You'll see schema validation + per-stage latency + the overall severity verdict. The full per-pass JSON lands at `phase2/out/jagersfontein/2022-01-15.json` inside the container (and on the named volume, so re-runs are idempotent).

Bulk over the 17-month Torres-Cruz precursor window:

```bash
docker compose exec satdiff python -m phase2.cli \
    --asset jagersfontein \
    --date-range 2021-06-15,2022-10-15
```

### CPU-only by design

The Docker image runs llama.cpp on CPU. ~20 s/pass on a typical laptop — acceptable for the rubric's correctness verification path, no `nvidia-container-toolkit` required on the host.

The local development path uses CUDA llama.cpp on an RTX 4080 and runs at **2.38 s/pass** (8.4× faster). The demo video shows the CUDA path; this Docker stack is the criterion-3 fresh-clone reproducibility surface.

## Architecture

```
                ┌────────────────────────────────────────────┐
                │             SimSat (vendored)              │
                │   ┌────────────┐       ┌──────────────┐    │
                │   │ dashboard  │◀──────│      sim     │◀────── Sentinel-2 imagery
                │   │  :8000     │       │   :9005      │    │   (Element-84 STAC backend)
                │   └────────────┘       └──────────────┘    │
                └────────────────────────────────────────────┘
                                              ▲
                                              │  GET /data/image/sentinel
                                              │
        ┌─────────────────────────────────────┴─────────────────────┐
        │                       satdiff                             │
        │                                                           │
        │   phase1 ─── physical-diff (NDWI, NDMI, gully, asym.) ────┐│
        │                              │                            ││
        │                              ▼                            ││
        │                          phase1.gate                      ││
        │                              │ (skip cloud / passive)     ││
        │                              ▼                            ││
        │   phase2 ─── 2-stage VLM contract pipeline ───┐           ││
        │                              │                │           ││
        │                              │   POST /v1/chat/completions│
        │                              │                │           ││
        │                              ▼                ▼           ││
        │                    phase2.aggregate   ┌──────────────┐    ││
        │                    (rules engine)     │ llama-server │    ││
        │                              │        │   :8080      │    ││
        │                              │        │ (Stage 1     │    ││
        │                              │        │   Q8_0 GGUF) │    ││
        │                              ▼        └──────────────┘    ││
        │                    phase3 ── per-pass PDF                 ││
        │                                                           │
        └───────────────────────────────────────────────────────────┘
                                              │
                                              ▼
                                  audit-trail JSONs + PDFs
                                  (named docker volumes)
```

## Repository layout

```
SatDiff/
├── docker-compose.yml          # top-level orchestration (run this)
├── Dockerfile.satdiff          # Python pipeline image (~600 MB)
├── Dockerfile.llama-server     # llama.cpp + GGUF pair baked in (~700 MB)
├── inference/                  # GGUF artefacts + quantize tooling
│   ├── gguf/                   # Stage 1 Q8_0 backbone + F16 mmproj
│   ├── quantize.{py,sh}        # build the GGUF pair from the merged ckpt
│   └── llama-server.sh         # local-dev runner (auto-detects CUDA build)
├── phase1/                     # data loader + masks + physical-diff + gate
├── phase2/                     # VLM contract pipeline (transformers + llama-server transports)
├── phase3/                     # PDF report renderer (workstream [1] in progress)
├── spikes/                     # contract schema + Spike 1 evaluation harness
├── training/                   # fine-tune dataset prep + eval (dev box only, not in Docker)
├── research/                   # design memos + spike findings + decisions
└── vendor/SimSat/              # SimSat snapshot — see vendor/SimSat/NOTICE.md
```

For a deeper tour of the design, see `research/`:
- `phase-1-findings.md`, `phase-2-findings.md` — what each phase actually does + measured numbers
- `workstream-6-findings.md` — GGUF quantization + CUDA inference benchmarks
- `phase-0-go-no-go.md` — the Path A primary-case decision (Jagersfontein) + allowed/forbidden pitch claims
- `hackathon-rubric.md` — the verbatim Liquid-Track criteria

## License

Code: MIT (this repository's contributions). SimSat (`vendor/SimSat/`): AGPL-v3, see `vendor/SimSat/LICENSE` and `vendor/SimSat/NOTICE.md` for attribution and source pointers.
