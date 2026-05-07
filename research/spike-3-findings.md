# Spike 3 — leap-finetune feasibility smoke test

**Date:** 2026-04-25.
**Verdict:** **VIABLE — Day 6 fine-tune runs locally on the RTX 4080. Modal stays as registered fallback for the published reproducible run.**

This spike confirms the official Liquid AI fine-tuning toolchain
(`Liquid4All/leap-finetune`) compiles a venv on this machine, loads
LFM2.5-VL-450M, runs LoRA SFT, and saves a merged checkpoint without
errors. The end-to-end smoke job (data load → train → save) completed
in **~72 s wall clock** on a 50-example example dataset capped to 16
train + 4 eval samples.

Quality of the smoke fine-tune is irrelevant to the verdict — the
spike is about whether the toolchain works. It does. Day 6 swaps the
dataset path to a domain corpus (VRSBench Stage 1, then SatDiff custom
Stage 2) and removes the limit cap.

## Setup

| Field | Value |
|-------|-------|
| Repo | `https://github.com/Liquid4All/leap-finetune.git` |
| Commit | `d01745820e2d25a2bee8f3523b12d22ab43bb169` |
| Local clone | `/home/peter/leap-finetune` (ext4) |
| Venv | `/home/peter/.satdiff-venvs/leap-finetune` (ext4) |
| `uv sync` total time | **~27 min** (one-time; subsequent runs are warm-cache) |
| Python | 3.12.3 (uv installed automatically; `pyproject.toml` says `requires-python = ">=3.12"`) |
| `transformers` version | 5.2.0 |
| `torch` version | 2.9.1+cu128 (note: **cu128**, distinct from spike-1 venv's torch 2.11+cu13) |
| `flash-attn` | 2.8.3 — **built from source in 1m32s** (was the worry; built clean) |
| `deepspeed` / `peft` / `mpi4py` | 0.18.3 / 0.18.0 / 4.1.1 — all installed without manual sudo apt steps |
| Hardware | RTX 4080 Laptop, 12 GB; WSL2 Ubuntu 24.04 |
| Smoke config | `/home/peter/leap-finetune/job_configs/spike3_smoke.yaml` |
| Model | `LiquidAI/LFM2.5-VL-450M` (already cached locally from Spike 1, no re-download) |
| Dataset | `alay2shah/example-vlm-sft-dataset` (the example dataset from `vlm_sft_example.yaml`), `limit: 50` (yields 16 train + 4 eval after image-validity filtering) |
| Training type | `vlm_sft` extending `DEFAULT_VLM_SFT` |
| PEFT | `DEFAULT_VLM_LORA`: r=8, alpha=16 |

## Smoke-test result

| Field | Value |
|-------|-------|
| Schema validation | ✓ passed (10/10 samples) |
| Dataset prepared | ✓ 16 train + 4 eval samples after VLM-image-validity filter |
| Training started | ✓ Ray local cluster, single GPU |
| Train steps | 4 (epoch 0.25, 0.5, 0.75, 1.0) |
| `train_runtime` | **12.00 s** (just the optimizer steps) |
| `train_samples_per_second` | 1.33 |
| `train_steps_per_second` | 0.33 |
| `train_loss` (final) | 3.316 |
| `eval_loss` | 3.221 |
| Total wall clock | **32 s** training iteration; ~72 s including data prep + Ray spin-up |
| Checkpoint | ✓ merged PEFT model saved to `/home/peter/leap-finetune/outputs/spike3_smoke/LFM2.5-VL-450M-vlm_sft-example-vl-50-lr1em05-w0p2-lora_m-20260425_121029` despite `save_strategy: "no"` (framework merges LoRA → fp16 at end of training automatically) |
| Errors / OOM | none |
| Exit code | 0 |

Loss numbers are uninteresting (4 steps at LR 1e-5 with batch size 1 barely move a 450M model). The point is that gradients flowed, eval ran, the checkpoint persisted — the pipeline functions.

## Decision

**VIABLE.** Path A continues. Day 6 fine-tune runs locally on the RTX 4080.

- ≥1 epoch completed without error ✓
- Train loss + grad norm finite ✓ (loss 3.13–3.65, grad norm 0.13–0.19)
- Eval loss computed automatically ✓
- Checkpoint produced ✓
- Wall clock < 30 min on 50 examples ✓ (was 32 s — 50×–100× faster than the budget allowance)

Modal stays as registered fallback per the recipe — useful for the *published reproducible run* if we want a standardized H100 trace for the model card. Not required for the demo.

## Implications for Day 6

1. **Compute envelope is comfortable.** 32 s for 16 train samples × 1 epoch ≈ 2 s/sample including overhead. VRSBench's multitask SFT split is ~123K examples; one epoch at 2 s/sample is ~70 hours — too long for a hackathon day. **Use a sub-sample** (e.g. 5K examples × 2 epochs ≈ 5–6 hours) for Stage 1; that lands well under a day budget while producing measurable improvement on the framework's built-in benchmarks. The published Modal config (if we use it for reproducibility) can run the full epoch.
2. **The framework writes a *merged* fp16 checkpoint at end of training** even when `save_strategy: "no"` is set. Good news — that means the Spike 1 inference path (`spikes/leap-vlm-check.py`) can load the Day 6 output by pointing `model_id` at the local checkpoint dir without any LEAP-specific tooling.
3. **`leap-bundle create <ckpt>`** is the framework's documented "next step" for producing a LEAP-deployable artifact (mentioned in the smoke-test output). Use this for the optional satellite-deployment path; not needed for the local demo.
4. **Stage 2 (SatDiff custom)** is what the recipe's `~/.claude/plans/let-s-start-with-research-polished-flame.md` and `research/liquid-finetune-recipe.md` already scoped. The custom dataset format must match `vlm_sft` schema — the framework's `validate_loader.py` does this check. Curate ~30 `(image-pair, prompt, target-JSON)` examples in HF messages format.
5. **Custom evals.** The framework supports user-supplied benchmark JSONL via the `benchmarks:` section of the YAML config. Phase 1 / Day 6 should plug in:
   - The Spike 1 `evaluate()` harness from `spikes/leap-vlm-check.py` as the SatDiff-specific eval (JSON schema validity + claim-evidence regex hits).
   - A small held-out Jagersfontein subset for the "measurable improvement over base" rubric deliverable.

## Surprises / notes

- **`vrsbench_multitask_modal.yaml` does not ship with the repo at HEAD `d01745820e`.** The official tutorial referenced in `research/liquid-finetune-recipe.md` (docs.liquid.ai/examples/customize-models/satellite-vlm) presumably either ships this file or generates it via the tutorial walkthrough; the cloned repo here only has generic example configs. We wrote our own `spike3_smoke.yaml` based on the shipped `vlm_sft_example.yaml`. **For Day 6:** start from `job_configs/sft_with_lora_example.yaml` or `vlm_sft_example.yaml` and add a `dataset.path` for VRSBench (`Vision-CAIR/VRSBench` or similar) plus the `benchmarks:` section — no need to wait for an official VRSBench config.
- **`flash-attn` built from source in 1m32s.** The recipe warned this could be 30–60 min; in practice the C++/CUDA compile finished much faster than feared. Don't budget more for it.
- **`mpi4py` installed without `libopenmpi-dev`.** Either WSL2 ships an MPI lib already or `mpi4py`'s wheel doesn't link until import. Either way, no sudo apt was required. (For multi-node training we'd need real MPI — irrelevant here, single GPU.)
- **CUDA version split between venvs is fine.** Spike 1 venv has torch 2.11+cu13; spike 3 venv has torch 2.9.1+cu128. Both work because the NVIDIA driver (581.95) supports both CUDA toolkit versions. Don't try to merge the venvs.
- **Dataset filtering dropped 30/50 samples.** The example dataset's image URLs are partially stale; `is_valid_vlm_sft` filtered 16 train + 4 eval out of 50. For Stage 2 SatDiff curation, all images are local — no URL flake risk.
- **HF rate-limit warning** on each unauthenticated call. For Day 6 set `HF_TOKEN` from the `WobblyDopamine` account so model + dataset downloads aren't rate-limited.
- **Ray local cluster** spin-up adds ~10–15 s overhead per job. Acceptable for Day 6's single-job run; would matter if we did many short jobs.

## Reproduce

```bash
git clone https://github.com/Liquid4All/leap-finetune.git /home/peter/leap-finetune
export UV_PROJECT_ENVIRONMENT=/home/peter/.satdiff-venvs/leap-finetune
uv sync --directory /home/peter/leap-finetune              # ~27 min first time
cd /home/peter/leap-finetune
uv run leap-finetune job_configs/spike3_smoke.yaml          # ~72 s
```

Smoke config: `/home/peter/leap-finetune/job_configs/spike3_smoke.yaml`.

Checkpoint: `/home/peter/leap-finetune/outputs/spike3_smoke/.../LFM2.5-VL-450M-vlm_sft-example-vl-50-lr1em05-w0p2-lora_m-<timestamp>/`.

## Artefacts referenced

- Recipe (pre-spike): `research/liquid-finetune-recipe.md`
- Spike 1 (cached LFM2.5-VL-450M weights, evaluation harness): `research/spike-1-findings.md`
- Spike 2 (no dependency, but the WSL2 venv-on-ext4 lesson re-applies): `research/spike-2-findings.md`
- Smoke config: `/home/peter/leap-finetune/job_configs/spike3_smoke.yaml`
- Spike 3 checkpoint: `/home/peter/leap-finetune/outputs/spike3_smoke/.../LFM2.5-VL-450M-vlm_sft-example-vl-50-lr1em05-w0p2-lora_m-20260425_121029/`
