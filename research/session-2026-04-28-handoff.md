# Session handoff — 2026-04-28

This document captures the state at the end of the 2026-04-28 working session so a fresh session can continue with minimal information loss. Token budget that day: ~700K, hence the handoff. **No implementation was started this session** beyond the Stage 2 fine-tune work and the plan; all six remaining workstreams are pending.

## TL;DR

- **Stage 1 fine-tune is the deliverable.** Stage 2 is closed as a methodologically-clean negative result that validates the rules-engine architecture pattern.
- **Plan v2 is approved.** Six workstreams in `~/.claude/plans/let-s-start-with-research-polished-flame.md`. Critical path: **[6] → [2] → [4]**.
- **Next session starts at workstream [6]** — GGUF Q8_0 + F16-mmproj quantization of the Stage 1 merged ckpt + llama-server inference. Verification: schema-valid + 100% evidence-correct on held-out 6 passes, latency ≤ 1 s/pass.

## What changed this session

### 1. Stage 2 hand-authored dataset built (29 examples)

Designed against the user's literature survey at `research/Satellite Dam Monitoring Data Request.txt`. Scoping:

| tier | examples | content |
|---|---:|---|
| 1 — Jagersfontein severity teaching | 21 | 11 boundary cliffs (rotating imagery across 8 pass dates) + 5 confabulation overrides + 5 multi-claim escalation chains |
| 2 — cross-asset routine | 4 | Aswan, Three Gorges, Hoover/Mead, Kariba — imagery-derived NDWI metrics + paper-cited rule-curve narratives |
| 3 — cross-asset catastrophic | 4 | Brumadinho, Toddbrook, Derna, Nova Kakhovka — paper-cited quantitatives + manual severity overrides for non-Jagersfontein asset classes |
| skipped (B-grade or quality-gate fail) | 3 | Mariana (redundant with Brumadinho), Oroville (no clean S2 distress imagery), Edenville (S2 tile-boundary + Wixom Lake didn't pass NDWI) |

All 29 reviewed via a custom HTML review homepage at `/home/peter/datasets/satdiff_stage2/review.html` (built by `training/build_review_page.py`). User caught two issues during review (cloudy `asym_5_1_urgent` imagery; Edenville unclear) — both fixed.

Files:
- `training/stage2_handauthored/{tier1,tier2,tier3}_*.jsonl` (11 files, 29 examples)
- `training/stage2_handauthored/skipped.md` — drop justifications
- `training/build_tier1_boundary.py`, `training/build_tier1_confab_escalation.py`, `training/build_cross_asset_examples.py` — synthesisers
- `training/build_review_page.py` + `/home/peter/datasets/satdiff_stage2/review.html` — review UI

### 2. Held-out evaluation methodology fixed mid-session

The first Stage 2 eval was contaminated — the eval set was the same 16 Phase 2 backtest passes whose gold outputs were in the training data (the auto-generated portion). Result hid a real regression. After the user pushed for a "proper fix":

- `training/build_stage2_split.py` — produces `satdiff_stage2_train.jsonl` (35 examples) and `satdiff_stage2_test.jsonl` (11 held-out: 6 backtest dates + 5 hand-authored pass IDs)
- `training/eval_finetuned.py --held-out-only` — restricts evaluation to the held-out backtest dates

Held-out dates picked to span the trajectory: 2021-08-15 (early/low), 2021-12-15 (ramp-up), 2022-01-15 (peak pre-failure), 2022-04-15 (post-peak), 2022-07-15 (recovery), 2022-10-15 (post-failure spike).

Held-out hand-authored: one per sub-category — boundary p2w_24_urgent, confab_no_gullies_but_14, esc_pond_urgent_to_5, aswan-routine, brumadinho-catastrophic.

### 3. Stage 2 fine-tune completed (negative result)

Retrain on the 35-example train split: 1m 37s, train_loss 0.246, eval_loss 0.115 (in-training validation). Apples-to-apples held-out comparison:

| metric (held-out 6 backtest passes) | base | Stage 1 | Stage 2 (clean retrain) |
|---|---:|---:|---:|
| evidence_correct claims | 0/30 (0%) | 30/30 (100%) | 30/30 (100%) |
| severity_corrections | 5 | 5 | **9 (worse)** |

Stage 2 preserved Stage 1's evidence-sourcing lift but **worsened** severity adherence. Synthetic boundary cliffs in training (p2w=24/26) didn't transfer to held-out real-data input distributions (p2w=9.9 throughout). LoRA at 35 train × 3 epochs = ~31 effective steps cannot reshape multi-tier threshold reasoning at this scale. **Confirms the rules-engine architecture: VLM as evidence-text writer; Python `phase2/aggregate.py` as authoritative threshold engine.**

Memory saved: `~/.claude/projects/-mnt-c-Users-peter-SatDiff/memory/feedback_eval_holdout_discipline.md` — always hold out a clean test set BEFORE fine-tune evaluation; otherwise the metric measures memorisation, not generalization.

### 4. Plan v1 → v2 (after Liquid wildfire-prevention review + Discord skim)

User asked me to check Liquid's published reference at `https://docs.liquid.ai/examples/customize-models/wildfire-prevention` and skim the official Discord channel before finalising the plan. Both yielded directional changes:

**From the wildfire-prevention example:**
- Canonical Orin-deploy pattern is **GGUF Q8_0 backbone + F16 mmproj + llama-server HTTP API**, NOT Python transformers + bf16.
- Cited inference latency: 0.59 s/pass (vs our current ~7 s with transformers + bf16) — 10× improvement.
- Image footprint: ~500 MB GGUF pair vs ~860 MB fp16 ckpt.

**From the Discord skim (2026-04-19 to 2026-04-28):**
- DPhi (the data provider) published their own reference using **agentic** maritime monitoring (Ever Given grounding) at `github.com/DPhi-Space/agentic-vlm-maritime-monitoring`. SatDiff is deliberately **non-agentic / contract-framed** — explicit positioning needed in the writeup.
- 5ch4um1's half-time preview sets the demo production-quality bar (3-second image loop, on-screen overlays).
- Multiple competitors publishing specialised Sentinel-2 datasets — we don't compete on dataset size, we compete on contract-framed task framing.
- No rule changes / deadline changes / new deliverable format requirements.

Memory saved: `feedback_check_canonical_sources.md` — always check vendor canonical refs + competitor channels before finalising plans.

Plan v2 added workstream **[6] GGUF + llama-server** before [2] Docker compose. Total effort estimate ~4.5 days vs v1's ~4 days; ~6.5 days slack remaining (deadline 2026-05-08 20:00 EDT).

## Where the next session starts

**Workstream [6] — GGUF + llama-server.** Verbatim from plan v2:

1. Source ckpt: `/home/peter/leap-finetune/outputs/satdiff_stage1/LFM2.5-VL-450M-vlm_sft-satdiff_st-all-lr1em05-w0p2-lora_a-20260426_221338/LFM2.5-VL-450M-vlm_sft-satdiff_st-all-lr1em05-w0p2-lora_m-20260426_221338` (861 MB, fp16).
2. Quantize → produce `inference/gguf/LFM2.5-VL-450M-stage1-Q8_0.gguf` (~500 MB) and `inference/gguf/mmproj-LFM2.5-VL-450M-stage1-F16.gguf` (F16 always). Use `llama.cpp/convert_hf_to_gguf.py` for the language model + the mmproj converter from the wildfire-prevention example.
3. Stand up `llama-server` on port 8080. Verify `/v1/chat/completions` accepts the existing chat-template prompts.
4. Build `phase2/llama_client.py` (~80 LoC HTTP client). Refactor `phase2/runner.py`'s `VLM` class behind a transport interface; add `LlamaServerVLM` alongside the existing transformers-based one. Pick by env var `SATDIFF_INFERENCE=transformers|llama_server`.
5. Verification:
   - `curl http://localhost:8080/health` returns 200
   - Run held-out 6 passes through the new transport: schema_valid 6/6, evidence_correct 30/30 (Stage 1 lift preserved), latency ≤ 1 s/pass
   - Side-by-side latency comparison vs the existing transformers run; record numbers for the writeup [3] + demo [4]

**Optional pre-work**: watch Pau Labarta Bajo's YouTube recording (https://www.youtube.com/watch?v=LOIDYl5fdb8, ~25 min) for any LFM2.5-VL-specific quantization nuances. Non-blocking.

## Key file paths (fresh-session orientation)

| what | where |
|---|---|
| Approved plan | `~/.claude/plans/let-s-start-with-research-polished-flame.md` |
| This handoff | `research/session-2026-04-28-handoff.md` |
| Persistent project doc | `CLAUDE.md` (top-level) |
| Decision log | `research/phase-0-go-no-go.md` (rows through 2026-04-28) |
| Stage 1 merged ckpt | `/home/peter/leap-finetune/outputs/satdiff_stage1/LFM2.5-VL-450M-...-lora_m-20260426_221338` |
| Stage 2 train/test JSONLs | `/home/peter/datasets/satdiff_stage2/satdiff_stage2_{train,test}.jsonl` |
| Stage 2 split spec | `/home/peter/datasets/satdiff_stage2/satdiff_stage2_split.json` |
| Phase 2 backtest outputs (used by [1] PDF renderer) | `phase2/out/jagersfontein/*.json` |
| Rendered PNGs (4 per pass; used by [1]) | `/home/peter/datasets/satdiff_stage2/images/jagersfontein/*.png` |
| Schema (source of truth) | `spikes/schema.json` |
| Eval baseline summaries | `training/out/eval_stage1.json` (full 16 passes) and the per-pass dir at `phase2/out/jagersfontein_eval_{stage1,stage2_heldout}/` |
| SimSat | `/home/peter/SimSat/` (start with `cd /home/peter/SimSat && docker.exe compose up -d`) |
| Spikes venv | `/home/peter/.satdiff-venvs/spikes` |
| leap-finetune venv | `/home/peter/.satdiff-venvs/leap-finetune` |

## Open questions parked

| | what | impact |
|---|---|---|
| 1 | Multiple-entry hackathon rule (SF asked in Discord, no answer) | Default assumption: one entry per person. Worth a quick user check if they want to change strategy. |
| 2 | Pau YouTube recording not yet watched | May contain LFM2.5-VL-specific quantization nuances. Non-blocking but worth checking before [6] kickoff (~25 min). |
| 3 | Stage 2 ckpt path retained but not promoted | Sits at `/home/peter/leap-finetune/outputs/satdiff_stage2/...lora_m-20260428_164537`. Not uploaded to HF (would confuse model-card story). Can be deleted post-submission; for now kept for traceability. |

## Memory entries (~/.claude/projects/-mnt-c-Users-peter-SatDiff/memory/)

Indexed in `MEMORY.md`:
- `feedback_paper_fetching.md` (older) — paywalled papers: ask user after first failed try
- `feedback_backtest_prompt_integrity.md` (older) — historical-monitoring prompts must not leak future events
- `feedback_eval_holdout_discipline.md` (new this session) — always hold out a clean test set BEFORE fine-tune evaluation
- `feedback_check_canonical_sources.md` (new this session) — check vendor canonical refs + competitor channels before finalising plans
