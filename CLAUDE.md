# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A planning-and-research workspace for **SatDiff**, a submission to the Liquid AI "AI in Space" hackathon (Liquid Track). Submission deadline: **2026-05-08 20:00 EDT** (= 2026-05-09 02:00 CEST). At the time of writing the repo contains **only research memos** under `research/` and a top-level handoff document — no source code, build system, or tests yet. When code lands (data loaders, physical-diff modules, prompt pipelines, fine-tuning configs), update this file with the actual commands.

## Read these first, in order

**For the next session (post-2026-04-28-evening handoff):** start with `~/.claude/plans/let-s-start-with-research-polished-flame.md` — that's the approved Plan v2. Workstream [6] GGUF + llama-server **is now done (CPU-only)**; immediate next action is **workstream [2] Docker compose**, parallelisable with **[1] PDF renderer** and **[3] writeup**. The list below is for deeper context.

1. `~/.claude/plans/let-s-start-with-research-polished-flame.md` — **the approved Plan v2 for final submission deliverables**. Six workstreams; [6] CPU-only landed on 2026-04-28; [2]/[1]/[3] are next.
2. `research/workstream-6-findings.md` — GGUF Q8_0 + llama-server: schema 6/6, evidence 30/30 preserved, 19.88 s/pass CPU mean. CUDA build still TODO (see "Remaining work").
3. `research/session-2026-04-28-handoff.md` — what changed in the 2026-04-28 morning session (Stage 2 closure, plan v2 approval, competitive-landscape skim from Discord).
3. `research/phase-0-go-no-go.md` — the locked Path A verdict (Jagersfontein primary, Brumadinho secondary, fusion). Decision log appended through 2026-04-28.
4. `research/hackathon-rubric.md` — verbatim Liquid-Track criteria and weights.
5. `research/satellite-architecture.md` — compute / hardware / downlink assumptions; Orin 16GB target.
6. `research/simsat-scout.md` — how the DPhi SimSat API works and where we plug in.
7. `research/liquid-finetune-recipe.md` — the official `Liquid4All/leap-finetune` + VRSBench path.
8. `research/contract-prompts/jagersfontein-contract.md` — primary case prompt + JSON output schema.
9. `research/open-questions.md` — unresolved gaps; Section "Underweighted aspects" feeds the submission pitch.
10. `LAPTOP_HANDOFF.md` — older entry point; superseded by Plan v2 but retains historical calendar / spike plan / dev-environment checklist.

## Branch and submission discipline

- Work continues on `claude/hackathon-planning-yOI79` until submission. **Do not push to `main`.**
- The submission must pass a **fresh-clone test**: `git clone <zip> /tmp/judge && cd /tmp/judge && docker compose up` produces a working demo with no manual fix-ups. Criterion 3 ("must run without debugging") disqualifies the submission if it fails.
- When tooling lands, prefer Docker Compose as the canonical entry point — both because the prize platform preloads Docker images and because the rubric expects a one-command run.

## Architecture (target end state)

The pipeline is staged so each component can be developed independently and rejoined later:

```
SimSat API  ──►  Physical-diff module  ──►  Gate (Φ-sat heritage)
(Sentinel-2)     (NDWI, NDMI, gully,         │
                  asymmetry, pond-to-wall)    │ if interesting
                                              ▼
                                  LFM2-VL (LEAP / llama.cpp / MLX / ONNX)
                                  prompted with the contract + diff summary
                                              │
                                              ▼
                                  Structured JSON per pass (~2 KB)
                                              │
                                              ▼
                                  Ground supervisor (Claude/GPT every N passes)
                                              │
                                              ▼
                                  PDF report (jinja over JSON) for human consumers
```

Two cross-cutting commitments that drive design:

- **Imagery ingress must route through the SimSat API** (`GET /data/image/sentinel?lon=&lat=&timestamp=&spectral_bands=&size_km=`) for the final submitted pipeline — that is rubric criterion 1. Element 84 STAC / Microsoft Planetary Computer are fine for scratch debugging only.
- **Contract-prompt schema is the integration boundary** between the physical-diff module and the VLM. The schema in `research/contract-prompts/jagersfontein-contract.md` is the source of truth — match its `claims[]`, `severity_level`, `recommended_action`, `regulatory_escalation_flag` fields exactly.

## Three spikes gate Phase 1 build

**All three spikes passed on 2026-04-25 — Phase 1 build is unblocked.**

1. **LEAP / LFM2-VL on EO imagery** — ✅ **DONE 2026-04-25, viable with caveats.** Base LFM2.5-VL-450M sees Jagersfontein imagery in free-text mode (correctly localises pond + town + impoundment) but under the full contract prompt it parrots the prompt's "Sensors" lines into the `evidence` field instead of describing imagery. Severity grading still plausible (Claim 2 pond-management correctly elevated). Latency 6.5 s, peak VRAM 0.97 GB on RTX 4080. Two consequences: (a) Phase 2 prompt pipeline must use a two-stage decode — free-text scene description first, JSON shaping second — and (b) Spike 3 / Day 6 fine-tuning is now also load-bearing for contract-schema reliability, not just rubric-extra. Full write-up: `research/spike-1-findings.md`. Reproduce: `cd spikes && UV_PROJECT_ENVIRONMENT=/home/peter/.satdiff-venvs/spikes uv run python leap-vlm-check.py`.
2. **SimSat API loop** — ✅ **DONE 2026-04-25, viable.** Stock SimSat against Element 84 returned **4/5** Torres-Cruz milestone dates and **17/17** months in a rolling 2021-06 → 2022-10 Jagersfontein window, median latency **5.02 s** (well under 30 s). The 2022-09 query autonomously surfaced the **2022-09-11 failure day**. The single miss (2016-10-27) is because Element 84's `sentinel-2-l2a` lacks pre-2017 archive for T35JLH — workable since Torres-Cruz signal starts Feb 2019, or fall through to `sentinel-2-pre-c1-l2a`. SimSat-side gotchas (bake into submission image): `.dockerignore` skipping `src/dashboard/frontend/node_modules`, `.env` setting `MAPBOX_ACCESS_TOKEN=anything`, multispectral via `return_type=array` (PNG mode is RGB-or-greyscale only). Full write-up: `research/spike-2-findings.md`. Reproduce: `cd /home/peter/SimSat && docker.exe compose up -d && cd /mnt/c/Users/peter/SatDiff/spikes && UV_PROJECT_ENVIRONMENT=/home/peter/.satdiff-venvs/spikes uv run python archive-pull.py`.
3. **Fine-tune feasibility** — ✅ **DONE 2026-04-25, viable. Day 6 fine-tune runs locally.** `Liquid4All/leap-finetune` smoke job (LFM2.5-VL-450M + LoRA, 16 train samples, 1 epoch) completed in **32 s** on the RTX 4080 with eval_loss 3.22 and a clean merged fp16 checkpoint. `uv sync` cost ~27 min one-time (Python 3.12, torch 2.9.1+cu128, flash-attn 2.8.3 built from source in 1m32s, deepspeed/peft/mpi4py all installed without sudo apt steps). Note: the recipe-mentioned `vrsbench_multitask_modal.yaml` does **not** ship with the repo at HEAD `d01745820e`; build a config from `vlm_sft_example.yaml` instead. Day 6 sub-samples VRSBench for Stage 1 (~5K × 2 epochs ≈ 5–6 h) and adds ~30 SatDiff custom examples for Stage 2. The framework's merged checkpoint loads directly into `spikes/leap-vlm-check.py` — no LEAP-specific tooling needed for inference. Modal stays registered as fallback. Full write-up: `research/spike-3-findings.md`. Reproduce: `cd /home/peter/leap-finetune && UV_PROJECT_ENVIRONMENT=/home/peter/.satdiff-venvs/leap-finetune uv run leap-finetune job_configs/spike3_smoke.yaml`.

## Phase 1 — data + signal-extraction pipeline

Plan: `~/.claude/plans/phase-1-data-pipeline.md`. Four sub-modules (loader, masks, physical-diff, gate) feeding the contract memo's `[BASELINE]` + `[CURRENT PASS]` blocks per `research/contract-prompts/jagersfontein-contract.md` lines 95-127.

- **Masks** — ✅ **DONE 2026-04-25 (v1.1, Torres-Cruz cross-referenced).** Four polygons in `phase1/masks/jagersfontein.geojson`, traced from the SimSat 2021-12 RGB and validated against Torres-Cruz & O'Donovan 2023 (Scientific Reports, DOI 10.1038/s41598-023-31633-5) Figure 2 panel (h) 2021-02-09 — the panel that labels Breaches A and B on the SE wall. Areas: `impoundment` 4.48 km² (17.8% of tile), `retaining_wall` 0.16 km² (thin S-perimeter strip on the failure side), `downstream_slope` 0.79 km² (run-out wedge), `kopanong_protected_zone` 4.76 km² (town + SE residential extension). Pairwise overlaps < 0.07% of tile. Loader at `phase1/masks/loader.py` (`load_masks`, `rasterize_masks`). Sanity overlay at `phase1/data/sanity_jagersfontein_masks.png`. Edge accuracy ~±20 m (2 pixels at 9.85 m/px). Quality is **v1.1 sufficient for trend analysis**; absolute-number reporting (km², metre offsets) should refine via a QGIS digitisation against higher-resolution imagery.
- **Loader (data)** — ✅ **DONE 2026-04-25.** `phase1/loader.py::load_pass(asset_id, date) -> xr.Dataset | None` calls SimSat at `localhost:9005/data/image/sentinel?return_type=array`, decodes the base64 multispectral payload (red/green/blue/nir/swir16, uint16, 506×509), and caches to `phase1/data/<asset>/<date>.nc` via h5netcdf. Cold fetch ~6 s, cache hit ~190 ms (33× speedup), NetCDF cache ~1.6 MB/pass. `AssetSpec` registry keyed by asset_id. Returns `None` for `image_available=False` and writes a `.miss` marker so dead-date polls are also cached. Window 30 days (matches Spike 2 cache).
- **Baseline indices** — ✅ **DONE 2026-04-25.** `phase1/baseline.py::compute_baseline` chose 2017-10-15 (Sentinel-2A, 5.5% cloud); pond area 90,689 m². Per-mask NDWI/NDMI/B4_B3 means persisted to `phase1/data/jagersfontein/baseline.json`. Tries 2017-10-15 → 2017-04-15 → 2018-04-15 → 2018-10-15 → 2019-01-15 fall-through.
- **Physical-diff module** — ✅ **DONE 2026-04-25.** `phase1/physical_diff.py::compute_diff(asset, date) -> dict` emits the contract memo's `[CURRENT PASS]` block exactly: `impoundment.{deposition_asymmetry_index, footprint_change_pct}`, `pond.{area_m2, area_change_pct_vs_baseline, pond_to_wall_distance_m, licence_volume_exceedance_pct, NDWI_max, B4_B3_turbidity_ratio}`, `retaining_wall.{gully_count, largest_gully_width_m, NDMI_wall_face, SWIR_anomaly_flag}`, `deformation: null`. Pond-to-wall via `scipy.ndimage.distance_transform_edt`; gullies via Sobel + 90th-percentile + connected-components. Numbers match Torres-Cruz qualitatively (over-counts gullies; trends correct).
- **Gate** — ✅ **DONE 2026-04-25.** `phase1/gate.py::decide(diff, *, prior_passes_since_vlm, force) -> GateDecision`. Φ-sat-heritage cloud-skip at 50%, plus immediate-priority on pond-to-wall <75 m, priority on pond-area>+100% / gully ≥1 / asymmetry >1.5, heartbeat every 6 passes. **Known defect: skipped the 2022-09-11 failure-day pass at 68% cloud** — mitigations (extreme-metric override; SAR sidecar) belong in the writeup's production-roadmap section.
- **CLI + sanity check** — ✅ **DONE 2026-04-25.** `python -m phase1 --asset jagersfontein --date YYYY-MM-DD` and `--date-range START,END` (mid-month polls). Bulk run over 17 cached SimSat months produced 17/17 diffs and 16/17 VLM invocations. Trajectory matches Torres-Cruz: pond grows 90 k → 1.9 M m² (peak 2022-01) → 3.3 M m² post-failure; asymmetry spikes 1.5 → 22.6 across the failure month. Verdict in `research/phase-1-findings.md`.

**Phase 1 is viable. Phase 2 (LFM2.5-VL prompt pipeline) is unblocked.** Run command: `cd /mnt/c/Users/peter/SatDiff/spikes && UV_PROJECT_ENVIRONMENT=/home/peter/.satdiff-venvs/spikes PYTHONPATH=/mnt/c/Users/peter/SatDiff uv run python -m phase1 --asset jagersfontein --date-range 2021-06-15,2022-10-15`.

## Phase 2 — LFM2.5-VL prompt pipeline + first backtest

**✅ DONE 2026-04-26, viable.** `phase2/runner.py::run_pass(asset, date)` issues a two-stage decode (Stage A free-text describe → Stage B contract JSON), then a deterministic Python rules engine in `phase2/aggregate.py::compute_severity` overlays severity_level / recommended_action / overall_status / downlink_priority / regulatory_escalation_flag onto the model's parsed output. The model's pre-overlay severity is preserved as `stage_b_parsed_model_only` for the audit trail.

Backtest over the 16 Phase-1-invoked passes 2021-06-15 → 2022-10-15: **16/16 schema valid**, 16/16 evidence cited at least one diff metric value, 17/17 (incl. smoke) had pond mention ≥ 1, 16/16 overall=urgent (matches Torres-Cruz: continuous covenant violation). Latencies: Stage A 3.95 s mean, Stage B 7.24 s mean, total ~11.2 s/pass; peak VRAM 1.11 GB. Total severity_corrections (model vs rules engine): 12 across 16 passes, model agreed on every claim in 8/16 passes — the canonical gap is the 450M's chained threshold logic (pond_to_wall<25→urgent, gully_count≥10→urgent), which is the exact brief for Day 6 fine-tune.

Trajectory captured in `phase2/out/jagersfontein/summary.json`: pond peaks at 1.9 M m² in 2022-01 (pre-failure), and at 2022-10-15 (post-failure) the asymmetry index spikes from ~1.2 baseline to **22.57** with pond_to_wall=0 m — the lobe-shaped runout signature. Full write-up: `research/phase-2-findings.md`. Reproduce: `cd /mnt/c/Users/peter/SatDiff && UV_PROJECT_ENVIRONMENT=/home/peter/.satdiff-venvs/spikes PYTHONPATH=/mnt/c/Users/peter/SatDiff uv run python -m phase2.cli --asset jagersfontein --date-range 2021-06-15,2022-10-15`.

**Phase 2 is viable. Phase 3 (PDF rendering / demo wiring + Day 6 fine-tune) is unblocked.**

## Day 6 fine-tune — Stage 1

**✅ DONE 2026-04-26, headline result.** Stage 1 = 5,000 VRSBench (caption + VQA, no `[refer]`) examples × 2 epochs of LoRA SFT on LFM2.5-VL-450M, ran in **38m 15s** on the RTX 4080. Final eval_loss **1.41** (down from base ~3.21, −56%). Merged fp16 checkpoint at `/home/peter/leap-finetune/outputs/satdiff_stage1/.../LFM2.5-VL-450M-vlm_sft-satdiff_st-all-lr1em05-w0p2-lora_m-20260426_221338` (861 MB).

Eval re-ran the Phase 2 backtest over the 16 invoked Jagersfontein passes with the fine-tuned weights and graded each claim's `evidence` against the per-claim sourcing rules baked into `phase2/prompt.py`'s `[OUTPUT INSTRUCTIONS]`:

| metric | base LFM2.5-VL-450M | Stage 1 fine-tune | Δ |
|---|---:|---:|---:|
| schema_valid | 16/16 | 16/16 | — |
| **evidence-correct claims** | **4/85 (4.7%)** | **80/80 (100%)** | **+95.3 pp** |
| severity_corrections (rules engine vs model) | 12 | 12 | 0 |
| overall=urgent | 16/16 | 16/16 | — |

The base model was citing wrong diff fields for 95% of claims (e.g. Claim 2 cited baseline NDWI instead of pond_to_wall; Claim 4 didn't say "no SAR data"; Claim 5 cited unrelated indices). Stage 1 alone — without any SatDiff-specific contract examples — taught the model to follow the per-claim evidence sourcing rules from the prompt at 100%. The 5K VRSBench mix (captions + VQA on nadir EO imagery) lifts the model's *instruction-following on EO imagery* enough that the prompt rules become reliable.

`severity_corrections` did not move; that's expected — Stage 1 targets generic EO grounding, not multi-tier threshold logic. Stage 2 (~30-50 SatDiff examples with rules-engine-correct severities as gold targets) is what should close the threshold-reasoning gap.

Reproducible: `cd /home/peter/leap-finetune && UV_PROJECT_ENVIRONMENT=/home/peter/.satdiff-venvs/leap-finetune uv run leap-finetune job_configs/satdiff_stage1.yaml`. Eval: `UV_PROJECT_ENVIRONMENT=/home/peter/.satdiff-venvs/spikes PYTHONPATH=/mnt/c/Users/peter/SatDiff uv run --directory /mnt/c/Users/peter/SatDiff/spikes python training/eval_finetuned.py --model <ckpt> --label stage1`. Summary: `training/out/eval_stage1.json`.

Stage 2 prep (auto-generated examples + scaffolding for hand-authored edge cases) is at `training/build_stage2_dataset.py`, `training/satdiff_stage2.yaml`, `training/stage2_handauthored/`. Run on demand once edge-case examples are added.

## Day 6 fine-tune — Stage 2 (closed, negative result; Stage 1 ships)

**✅ DONE 2026-04-28, methodologically clean negative result.** 29 hand-authored examples (11 Tier 1 boundary + 5 confab + 5 escalation + 4 Tier 2 routine + 4 Tier 3 catastrophic; Mariana + Oroville + Edenville skipped per quality gate, see `training/stage2_handauthored/skipped.md`) combined with 17 auto-generated examples from Phase 2 backtest passes — split cleanly into 35 train / 11 test (24% held-out via `training/build_stage2_split.py`). Held-out test set: 6 Phase 2 dates (2021-08, 2021-12, 2022-01, 2022-04, 2022-07, 2022-10) + 5 hand-authored pass IDs spanning all sub-categories.

Stage 2 fine-tune ran in **1m 37s** on the train-only split (lr 5e-6, 3 epochs, LoRA rank 8, resumed from Stage 1 ckpt). Held-out evaluation:

| metric (held-out 6 backtest passes) | base | Stage 1 | Stage 2 (clean retrain) |
|---|---:|---:|---:|
| evidence_correct claims | 0/30 (0%) | 30/30 (100%) | 30/30 (100%) |
| severity_corrections | 5 | 5 | **9 (worse)** |

Stage 2 preserved Stage 1's evidence-sourcing lift but actively **worsened** severity adherence on out-of-distribution real data. Synthetic boundary cliffs (e.g. p2w=24.0/26.0 in training) didn't transfer to real-data input distributions (held-out passes had p2w=9.9 throughout, varying asymmetries). LoRA at this scale (35 train examples × 3 epochs ≈ 31 effective steps) cannot reshape multi-tier threshold reasoning.

**Strongly validates the rules-engine architecture pattern**: VLM as evidence-text writer (the part fine-tuning lifts) + Python `phase2.aggregate.compute_severity` as authoritative threshold engine (the part fine-tuning can't fix at this scale). Honest pitch story: "fine-tuning lifts the writer; the engine is authoritative."

**Decision: Stage 1 model ships, not Stage 2.** Full write-up: `research/session-2026-04-28-handoff.md` + saved memory `feedback_eval_holdout_discipline.md` (lesson: always hold out a clean test set BEFORE fine-tune evaluation, otherwise the metric measures memorisation not generalization). Stage 2 ckpt NOT uploaded to HF — would confuse the model-card story.

Reproduce: `cd /mnt/c/Users/peter/SatDiff && UV_PROJECT_ENVIRONMENT=/home/peter/.satdiff-venvs/spikes PYTHONPATH=/mnt/c/Users/peter/SatDiff uv run --directory spikes python training/build_stage2_split.py && cd /home/peter/leap-finetune && UV_PROJECT_ENVIRONMENT=/home/peter/.satdiff-venvs/leap-finetune uv run leap-finetune job_configs/satdiff_stage2.yaml && cd /mnt/c/Users/peter/SatDiff && uv run --directory spikes python training/eval_finetuned.py --model <stage2_ckpt> --label stage2_heldout --held-out-only`.

## Plan v2 — final submission deliverables (approved 2026-04-28)

Full plan at `~/.claude/plans/let-s-start-with-research-polished-flame.md`. **Six workstreams** with critical path **[6] → [2] → [4]**:

| | workstream | est. | status |
|---|---|---|---|
| **[6]** | GGUF Q8_0 + F16-mmproj quantize + llama-server inference | 0.5 day | ✅ **DONE 2026-04-28 (CPU + CUDA)**. CUDA build at `inference/llama.cpp/build-cuda/`; 2.38 s/pass on RTX 4080. |
| **[2]** | Top-level Docker compose (simsat + llama-server + satdiff) | 1 day | ✅ **DONE 2026-04-28 (CPU-only by design)**. Stack builds + comes up healthy + runs a contract pass end-to-end at 25.53 s/pass in Docker. See `research/workstream-2-findings.md`. Pre-submission: cross-machine fresh-clone validation + GGUF distribution decision (LFS vs HF-pull). |
| **[1]** | PDF report renderer (Jinja2 + WeasyPrint) | 0.5 day | ✅ **DONE 2026-04-28**. 17 PDFs rendered through Docker. Hero pass = 2022-10-15. See `research/workstream-1-findings.md`. |
| **[3]** | Pitch / writeup (`WRITEUP.md`, GISTM auditor wedge) | 0.5 day | ✅ **DONE 2026-05-07 (~2000 words)**. Honest-technical tone, adjacent-only positioning vs DPhi/Liquid, no Brumadinho. 9 sections. Hero artefact: `phase3/out/jagersfontein/2022-10-15.pdf`. **All 17 PDFs regenerated through Stage 1 GGUF** (CUDA llama-server) so evidence strings are 100% citation-correct, not base-model parrot. Forggensee = demo opener only (one-line nod in §6). |
| **[4]** | Demo video (5 min, presenter on camera, 5ch4um1-quality bar) | 1.5 days | blocked on [2] |
| **[5]** | HF upload (Stage 1 fp16 + GGUF pair to `WobblyDopamine/SatDiff-LFM2.5-VL-450M-stage1`) | 0.5 day | ✅ **DONE 2026-05-07**. Public at https://huggingface.co/WobblyDopamine/SatDiff-LFM2.5-VL-450M-stage1. Single-repo layout: fp16 transformers ckpt at root + GGUF pair under `gguf/`. Model card covers Stage 1 headline, Stage 2 negative result, repro, license inheritance from LFM2.5-VL. Total 1.4 GB. |

Total ~4.5 working days; ~6.5 days slack (deadline 2026-05-08 20:00 EDT).

**Key v2 directional decision**: adopting **GGUF + llama-server** (matching Liquid's wildfire-prevention reference at `https://docs.liquid.ai/examples/customize-models/wildfire-prevention`) rather than Python transformers + bf16. Cited latency improvement 7 s → ~0.6 s per pass; image footprint 860 MB → ~500 MB; demonstrates Orin-readiness via real artefact rather than claim. See plan v2 "Context" section for full rationale.

**Competitive landscape from Discord skim (2026-04-19 to 2026-04-28)** — informs writeup positioning:
- DPhi's own reference uses *agentic* maritime monitoring (Ever Given grounding); SatDiff is deliberately **non-agentic / contract-framed** because the GISTM auditor's required artefact is per-claim gold-standard, not investigation transcript. Position explicitly in writeup [3].
- 5ch4um1's half-time preview sets the demo production bar (3-second image loop, on-screen overlays) — [4] aims to match.
- Multiple competitors publishing specialised Sentinel-2 datasets — we don't compete on dataset *size*, we compete on **task framing**.

## Workstream [6] — GGUF + llama-server inference (CPU + CUDA)

**✅ DONE 2026-04-28.** Stage 1 merged fp16 ckpt → 362 MB Q8_0 backbone + 182 MB F16 mmproj GGUF pair (544 MB total, ≤700 MB cap). Both transports verified on the held-out 6 passes:

| transport | mean total/pass | speedup | schema | evidence | sev_corrections |
|---|---:|---:|---:|---:|---:|
| transformers + bf16 (RTX 4080) | ~11.2 s | (reference) | 6/6 | 30/30 | 5 |
| Q8_0 + llama-server CPU (8 threads) | 19.88 s | 0.6× | 6/6 | 30/30 | 9 |
| **Q8_0 + llama-server CUDA (sm_89)** | **2.38 s** | **4.7×** | **6/6** | **30/30** | **9** |

CUDA path uses `inference/llama.cpp/build-cuda/bin/llama-server` with `--n-gpu-layers 99`; 587 MiB of 11 GiB VRAM, the entire 450M backbone + mmproj is on-GPU. Stage A 0.96 s, Stage B 1.43 s. The 5 → 9 severity_corrections regression is identical CPU and CUDA — confirms it's the GGUF/llama.cpp execution path (chat-template + Q8_0 weight noise), not hardware. Rules engine corrects all 9 to gold, on-thesis with the architecture story. Plan v2 verification: schema 6/6 ✅, evidence 30/30 ✅, ≤2 s/pass partial (under 3 s, can't quite hit 1 s — image-encode floor for the 4-image + 4K-token shape). Full write-up: `research/workstream-6-findings.md`.

**Reproduce CUDA path:** `cd /mnt/c/Users/peter/SatDiff && bash inference/quantize.sh && LD_LIBRARY_PATH=/home/peter/miniconda3/lib bash inference/llama-server.sh --threads 4 &` then in a second shell `SATDIFF_INFERENCE=llama_server LLAMA_SERVER_URL=http://127.0.0.1:8080 UV_PROJECT_ENVIRONMENT=/home/peter/.satdiff-venvs/spikes PYTHONPATH=/mnt/c/Users/peter/SatDiff uv run --directory spikes python /mnt/c/Users/peter/SatDiff/training/eval_finetuned.py --model "WobblyDopamine/SatDiff-LFM2.5-VL-450M-stage1-Q8_0" --label stage1_q8_0_cuda_heldout --held-out-only`. The wrapper auto-detects `build-cuda/` and adds `--n-gpu-layers 99`.

**WSL2 + conda CUDA setup gotchas** (saved to memory `feedback_wsl2_conda_cuda.md`): (1) `cuda-toolkit=12.6` metapackage may pull `cuda-nvcc=12.4` — explicitly pin nvcc=12.6; (2) install `cuda-cudart-static` (default install ships only dynamic; CMake compiler-id needs static); (3) symlink `ln -s lib /home/peter/miniconda3/lib64` so CMake's FindCUDAToolkit (which only searches `lib64/`) picks up cudart.

## Where the next session starts

**Workstream [4] — Demo video** is the immediate next action. Approved storyboard at `~/.claude/plans/modular-hopping-shamir.md`. ~5 min, PIP-presenter (small webcam circle) over full-screen visualisations, OBS Studio + DaVinci Resolve. **Pre-recording prep tasks 1 + 2 done 2026-05-07 evening:**
- ✅ Forggensee Stage A run (2024-06-30, 8.7% cloud, 8.51 s on llama-server CPU). Outputs: `demo/forggensee_rgb.png`, `demo/forggensee_nir.png`, `demo/forggensee_stage_a.txt`. The model's output uses TSF vocabulary ("tailings beach") because we feed it the TSF-trained Stage A prompt — frame this in the voice-over as the schema-vs-architecture point ("plug a different contract prompt in, get the right vocabulary").
- ✅ Jagersfontein 17-tile time-lapse rendered to `demo/jagersfontein_timelapse.mp4` (1024×1024, 1 fps, final frame held 8 s, ~25 s total).
- ✅ Forggensee opener cut at `forggensee_open.mp4` (26.5 s, stream-copied from PXL source).

**Pre-recording prep tasks remaining:**
- ✅ Task 3 (architecture SVG) — done 2026-05-07 evening. `docs/architecture.svg` + `docs/architecture.png` (1920×1080, layered with semantic group IDs `#node-*` for DaVinci reveal animation, palette matches phase3 PDF style). Reveal order documented in the SVG header comment.
- ✅ Task 4 (VO script) — done 2026-05-07 evening. `demo/script.md` covers all 8 segments with sync-vs-VO labelling, on-screen overlay cue timing, recording order recommendation, vocal pronunciation notes. ~840 words, breaks to 5:00 at 150 wpm.
- ⏳ Task 5 (OBS scenes, ~30 min): set up presenter cam + screen capture + PIP composite. Script.md cue points are ready.
- ⏳ Task 6 (live-demo screen recording, ~30 min via OBS): `demo/script.md` §2:30-3:30 lists exact terminal commands + on-screen overlay timing.
- ⏳ Task 7 (presenter intro + close shots, ~30 min): `demo/script.md` §0:50-1:20 (intro, ~85w) + §4:30-5:00 (close, ~90w).
- ⏳ Task 8 (VO recording, ~45 min): script.md §0:25-0:50 + §1:20-2:30 + §2:30-3:30 + §3:30-4:00 + §4:00-4:30. Recording order: all VO back-to-back first to minimise mic/room resets.
- ⏳ Edit (~3 h) in DaVinci Resolve. Aim 4:50–4:58 final cut. Plan v2 storyboard at `~/.claude/plans/modular-hopping-shamir.md`.

**Workstream [5] — HF upload** ✅ **DONE 2026-05-07**. Public at https://huggingface.co/WobblyDopamine/SatDiff-LFM2.5-VL-450M-stage1. Pushed: model card (~7 KB), fp16 transformers ckpt at repo root (model.safetensors 856 MB + config/tokenizer/chat_template), GGUF pair under `gguf/` (Q8_0 backbone 362 MB + F16 mmproj 181 MB). License declared as `lfm-1.0` inherited from `LiquidAI/LFM2.5-VL-450M`.

**Pre-submission gates**:
- ✅ **GGUF distribution decision** — DONE 2026-05-07. `Dockerfile.llama-server` now `RUN curl`s the Q8_0 + mmproj GGUF pair from `WobblyDopamine/SatDiff-LFM2.5-VL-450M-stage1` at Docker build time (no git-LFS, no baked-in GGUF). Rebuilt + smoke-tested: schema_valid=True, overall=urgent, escalation=True on 2022-10-15. `.dockerignore` excludes `inference/gguf/` from the build context.
- ✅ **Simulated fresh-clone Docker test** — DONE 2026-05-07. Snapshot of `git ls-files --cached --others --exclude-standard` → `/home/peter/satdiff-fresh-test/` (191 MB), `docker compose build && up -d` succeeded clean, phase2 + phase3 pass on 2022-01-15 produced schema_valid + urgent + escalation + a valid PDF with no manual intervention. The pipeline survives a fresh checkout.
- 🔴 **TOP PRIORITY 2026-05-08: commit + push to GitHub.** GitHub HEAD currently only has `LAPTOP_HANDOFF.md` + `research/` — every other working-tree item is untracked (`phase{1,2,3}/`, `inference/`, `vendor/SimSat/`, `Dockerfile.*`, `docker-compose.yml`, `WRITEUP.md`, `README.md`, `demo/{forggensee_run,timelapse,script}.{py,md}`, `docs/architecture.svg`). Without the commit + push, a real `git clone` test gives the judge nothing. After commit, run a real fresh-clone test against the GitHub URL to validate. NB: `forggensee_open.mp4` + `PXL_*.mp4` are gitignored and stay local; the demo video assets travel via the submission upload, not via GitHub.

Open questions parked:
- Multiple-entry hackathon rule: SF asked in Discord, no answer. Default assumption = one entry per person.
- Pau Labarta Bajo's YouTube recording (https://www.youtube.com/watch?v=LOIDYl5fdb8): not watched; not blocking.

## Fine-tuning — committed path

- Framework: **`Liquid4All/leap-finetune`** (Ray Train + Accelerate, managed via `uv`). Not raw `transformers + peft`.
- Model: **`LFM2.5-VL-450M`** primary; `LFM2-VL-1.6B` only if Stage 1 finishes early.
- Dataset: **VRSBench** (NeurIPS 2024) for Stage 1; small SatDiff-specific custom set for Stage 2 if time permits.
- Compute: local **WSL2 + RTX 4080 12GB** primary; **Modal** ($30 free credit) registered as fallback for the published reproducible run.
- Evals: framework's built-in VRSBench `short_answer` / `grounding_iou@0.5` / `CIDEr` / `BLEU`. These are the "measurable improvement over base" deliverable — do not invent a custom metric just to have one.
- Required outputs: public HuggingFace weights + model card, training code in-repo (e.g. `training/`), reproducible eval script.

## Rubric-driven priorities (Liquid Track weights)

| Criterion | Weight | What it implies for our work |
|-----------|--------|------------------------------|
| Use of Satellite Imagery (DPhi API) | 10% | Final pipeline must consume via SimSat. |
| Innovation and Problem-Solution Fit | **35%** | Pitch tightness > extra code. Name the buyer (GISTM auditor primary), the line-item (Principle 7 compliance), and the developer-API angle. |
| Technical Implementation | **35%** | Fresh-clone Docker run must work. Fine-tuning deliverables count here. |
| Demo and Communication | 20% | Presenter-on-camera explaining the architecture, intercut with diagrams + live pipeline output. Webcam + decent mic. |

When ranking work, favour what moves the 35% Innovation score (architectural framing, audit-trail-over-monitoring narrative, Torres-Cruz validation, GISTM wedge) before what moves the 10% imagery score.

## Pitch claims — what is and isn't allowed

`research/phase-0-go-no-go.md` locks these. Do not let drafts drift away from them.

**Allowed (evidence-backed):**
- "Public Sentinel-2 + Landsat carried a multi-year precursor signal at Jagersfontein (Torres-Cruz & O'Donovan 2023, *Scientific Reports*). SatDiff productises that signal as machine-generated, time-stamped, contract-framed output at acquisition."
- "Sentinel-1 SAR carried a ~40-day precursor at Brumadinho (Grebby et al. 2021). SatDiff fuses such signals into per-claim assessments."
- "The on-satellite physical-diff + VLM + ground-supervisor pattern enables portfolio-scale monitoring at marginal downlink cost."

**Forbidden (will be challenged):**
- "SatDiff would have detected Brumadinho from Sentinel-2 alone." (False — see `research/brumadinho-memo.md`.)
- "SatDiff would have prevented loss of life." (Monitoring ≠ enforcement ≠ action.)
- "SatDiff replaces commercial InSAR services." (It complements, at the interpretation + on-edge layer.)

The contract-prompt architecture is **sensor-agnostic** — the prize platform's actual sensor is a fisheye camera, not Sentinel-2. The production-roadmap section of the writeup must own this gap rather than hide it.

## Dev environment notes

- The user runs **Windows 11 + WSL2 Ubuntu**, with an **RTX 4080 Laptop 12GB** for local fine-tuning. NVIDIA driver 581.95 (supports CUDA 13). Per the user's global CLAUDE.md, run shell commands via PowerShell wrappers when targeting Windows tools; use `wsl bash -c "..."` (or operate inside WSL at `/mnt/c/...`) for Linux tooling. CUDA-on-WSL2 uses the Windows host driver — do **not** install an `nvidia-*` driver inside WSL2.
- Python 3.11 is the committed version per the plan (matches SimSat and `leap-finetune`). uv currently defaults to the system 3.13 unless forced; the active spikes/ venv uses 3.13 and works fine for `transformers==5.6.2 / torch==2.11.0+cu130`. For Spike 3, force 3.11 if `leap-finetune` requires it.
- **WSL2 venv gotcha (verified in Spike 1):** never put a Python venv on `/mnt/c` — pip-style small-file installs run >20× slower over the 9p mount than on native ext4. Set `UV_PROJECT_ENVIRONMENT=/home/peter/.satdiff-venvs/<project>` (or equivalent) so `.venv` lands on `/home/...`. The project pyproject/lockfile can stay on `/mnt/c`.
- The user's HuggingFace account is **WobblyDopamine** — Spike 3's fine-tuned weights publish there.
- `sudo` commands: per the user's instruction, ask the user to run them rather than running yourself.
- When research documents change, the agents responsible for related downstream work (plans, prompts, submission writeup) need to review and reconcile — research memos are upstream of code decisions.

## When you start writing code

What exists now:

- `spikes/leap-vlm-check.py` — Spike 1 entry point. Pulls Sentinel-2 tiles via MS Planetary Computer, renders RGB + NIR composites, runs LFM2.5-VL with the Jagersfontein contract prompt, validates output against `spikes/schema.json`. Reusable evaluation harness for Phase 1 backtest passes.
- `spikes/schema.json` — JSON Schema for the contract output. Source of truth for downstream phases; do not redefine.
- `spikes/pyproject.toml` + `uv.lock` — pinned env (`transformers==5.6.2`, `torch==2.11.0+cu130`, `odc-stac`, `pystac-client`, `planetary-computer`, `rasterio`, `jsonschema`, `torchvision`).
- `spikes/data/{tiles,png}/` and `spikes/out/` — gitignored runtime artefacts.

What is still missing (suggested locations match the spike memos):

- `spikes/archive-pull.py` (Spike 2 — SimSat archive loop).
- `training/` — `leap-finetune` configs + eval script (Spike 3 / Day 6).
- Top-level `docker-compose.yml` orchestrating the demo (rubric requires one-command run for the submission).

Common run command for Spike 1 (see `research/spike-1-findings.md` for caveats):

```bash
export UV_PROJECT_ENVIRONMENT=/home/peter/.satdiff-venvs/spikes
cd /mnt/c/Users/peter/SatDiff/spikes
uv run python leap-vlm-check.py        # default model: LiquidAI/LFM2.5-VL-450M
uv run python leap-vlm-check.py --skip-vlm   # tile pull + composite render only
```

Command-level guidance for Spike 3 / fine-tune lives in `research/liquid-finetune-recipe.md` until it lands as code.
