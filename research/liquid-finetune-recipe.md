# Liquid AI Official Fine-Tuning Path — and what it changes

**Source:** Discord channel link to `docs.liquid.ai/examples/customize-models/satellite-vlm`, plus public-search investigation 2026-04-25.

**Key URLs:**
- Tutorial: `https://docs.liquid.ai/examples/customize-models/satellite-vlm`
- Framework repo: `https://github.com/Liquid4All/leap-finetune`
- Cookbook examples: `https://github.com/Liquid4All/cookbook`
- LEAP fine-tuning docs: `https://leap.liquid.ai/docs/lfm2/finetuning`

## Headline

Liquid AI has published an **official** end-to-end satellite-VLM fine-tuning recipe:
- **Model:** `LFM2.5-VL-450M`
- **Dataset:** **VRSBench** (NeurIPS 2024) — 123K VQA pairs, 52K visual-grounding references, 29K captions on satellite imagery
- **Framework:** `Liquid4All/leap-finetune` (built on Ray Train + Accelerate, managed via `uv`)
- **Infrastructure:** **Modal cloud GPUs** (H100 / H200 / B200; $30 free credit, enough for the entire example)
- **Built-in evaluation:** `short_answer` (VQA), `grounding_iou` IoU@0.5 (grounding), `CIDEr` / `BLEU` (captioning) — runs every `eval_steps` automatically

For a Liquid Track submission, **this is the path of least resistance and lowest risk**, and it's what judges will recognise as a clean implementation.

## What this changes about our plan

### 1. Use Modal, not local GPU. Skip the flash-attn pain entirely.

The Discord poster's CUDA / `flash_attn` issue is **platform-specific** (DGX Spark = ARM64 + Blackwell, a brand-new combination with patchy wheel availability). Two implications:

- **For our laptop session:** local fine-tuning is risky regardless of hardware. flash-attn requires matching CUDA + nvcc + Python build tools, and `pip install flash-attn` frequently fails on first try. On Mac it's impossible (no CUDA).
- **The official recipe runs on Modal.** The Modal container is pre-built with all dependencies including flash-attn already resolved. We never touch flash-attn ourselves.

**Decision: use Modal.** Sign up, claim the $30 credit, run training in the cloud. Saves a half-day of debugging at minimum.

### 2. Use the official `leap-finetune` framework. Not raw `transformers + peft`.

The framework is what Liquid AI judges expect to see in a Liquid Track submission. The submission writeup explicitly references `leap-finetune` and the `vrsbench_multitask_modal.yaml` config (or our extended version) and gains credibility for using the supported tooling.

### 3. Switch primary target from LFM2-VL-1.6B to LFM2.5-VL-450M.

Two reasons:
- The official tutorial targets 450M. Path-of-least-resistance.
- The 450M is faster to fine-tune (less wall-clock per epoch), giving us more iteration room within Day 6.
- Sub-250ms edge inference per published benchmarks. Still fits Orin 16GB comfortably.

LFM2-VL-1.6B remains a fallback / "if there's time on Day 6 try the bigger one" option.

### 4. Use VRSBench as the foundation dataset.

VRSBench gives us 200K+ examples of satellite-VLM data. We don't curate 30 examples from scratch.

**Recommended approach: two-stage fine-tune.**
- **Stage 1 — VRSBench multitask SFT.** Use the published config. Improves base model on general remote-sensing VQA / grounding / captioning. The framework's built-in benchmarks measure improvement automatically.
- **Stage 2 (optional, if time permits) — small SatDiff-specific custom set.** ~20–30 hand-written examples of (image-pair, contract-prompt, target-JSON) for tailings monitoring. Continues training from the Stage 1 checkpoint with a lower learning rate. Teaches our contract vocabulary on top of the satellite-VLM uplift.

If Day 6 time runs short, we ship Stage 1 only. Stage 1 alone is a defensible "measurable improvement over base" deliverable backed by VRSBench benchmarks.

### 5. The framework's built-in evals are our submission's measurable-improvement metrics.

Decision A from the fine-tuning primer (designing a metric) is essentially **solved by adopting the framework's evals**:
- VQA short_answer accuracy on VRSBench-VQA test split
- Grounding IoU@0.5 on VRSBench-Grounding test split
- CIDEr / BLEU on VRSBench-Captioning test split

These are recognized benchmarks. Reporting "base LFM2.5-VL-450M scored X / Y / Z; fine-tuned scored A / B / C" with these metrics is exactly what the rubric asks for, and it's reproducible without designing our own eval pipeline.

We can additionally publish a **SatDiff-specific eval** (the held-out tailings-dam custom set) for the community-pool eval-sharing thread on Discord. Two metrics: domain-recognized + domain-specific.

### 6. The Discord poster's flash-attn problem is not our problem if we use Modal.

If we use Modal, flash-attn is irrelevant — it's pre-installed in the container. The only flash-attn risk we'd face is if we tried to do everything locally on the user's laptop.

If for some reason we end up needing local development (e.g., to iterate on prompts without paying Modal per run):
- **Linux + NVIDIA GPU:** prefer `pip install flash-attn --no-build-isolation` after PyTorch is correctly matched to CUDA version
- **Mac (Apple Silicon):** flash-attn is not available; use eager-attention fallback (slower, but works) — set `attn_implementation="eager"` in the model loading config
- **Windows:** WSL2 + Linux instructions
- **In all cases:** if local fails, fallback to Modal

## Updated Spike 3 procedure

Replacing the old Spike 3 procedure with the official-recipe-aligned version:

1. **Sign up for Modal** (`modal setup`); claim $30 free credit. ~10 min.
2. **Sign up for HuggingFace** with write access (we need to publish weights). ~5 min.
3. **`huggingface-cli login`** locally so Modal can pass credentials.
4. **Clone `leap-finetune`:** `git clone https://github.com/Liquid4All/leap-finetune.git && cd leap-finetune && uv sync`. ~5 min.
5. **Run the official VRSBench config on Modal:** `uv run leap-finetune job_configs/vrsbench_multitask_modal.yaml` (or whatever the exact path is — verify in repo). Container build ~5 min first time, then training. ~15-30 min for a small sub-set; ~few hours for full.
6. **Pull the checkpoint:** `modal volume get <volume> <path>`.
7. **Run benchmarks** on base vs fine-tuned using the framework's built-in eval. The numbers are our measurable improvement.

Expected Spike 3 outcome: **a fine-tuned LFM2.5-VL-450M with documented VRSBench improvement, published to HuggingFace, with reproducible training code in the submission repo.** That alone hits most of the rubric's fine-tuning requirements.

If we have remaining time on Day 6: continue with Stage 2 (SatDiff-specific) custom training on top.

## Decision points for the laptop session

The user needs to confirm one thing before Spike 3:

- **What hardware is the laptop?** Mac / Linux + NVIDIA / Windows?
   - Mac → Modal is mandatory (which is fine).
   - Linux + NVIDIA → Modal preferred for reproducibility; local possible if NVIDIA + CUDA + matching PyTorch is already configured.
   - Windows → Modal preferred; WSL2 if local.

In all cases, **Modal is the recommended path** because (a) it sidesteps flash-attn, (b) it's the published recipe, (c) judges will trust the result more, (d) the $30 free credit covers our needs.

## Risks remaining

- **Modal $30 credit might run out** if we iterate aggressively. Solution: short configs, limit eval samples (the framework's `limit: 500` field for eval datasets), pull checkpoints early.
- **The published Modal config may have changed** between the tutorial and now. Verify by reading the config file before running.
- **VRSBench license / redistribution** terms — check before publishing weights, ensure our HF model card credits VRSBench appropriately.
- **Stage 2 (SatDiff-specific) might destabilize** the Stage 1 weights if learning rate is too high. Use a fraction of Stage 1 LR (e.g., 1e-5 if Stage 1 was 5e-5).

## Net effect on the day budget

Day 6 (fine-tune day) becomes much cleaner:
- Morning: Stage 1 VRSBench SFT on Modal, monitor benchmarks.
- Afternoon: Stage 2 SatDiff-specific (if Stage 1 finishes early) OR finalize Stage 1 outputs.
- End of day: HuggingFace upload + model card.

Spike 3 (feasibility) on Day 1–2 becomes **smoke-test the official recipe end-to-end with a tiny config** — confirm we can launch a Modal job, get a checkpoint back, run a benchmark. If that smoke test passes, Day 6 is execution.

## What to commit to in the submission writeup

A short paragraph in the README / submission text:

> "SatDiff fine-tunes LFM2.5-VL-450M using Liquid AI's official `leap-finetune` framework on Modal cloud GPUs. Stage 1 trains on the VRSBench multitask dataset (NeurIPS 2024) for general remote-sensing VLM capability. Stage 2 (optional) continues training on a curated SatDiff-specific dataset of N tailings-dam image-pair / contract-prompt / target-JSON examples. Improvement is measured on VRSBench's published VQA / grounding / captioning benchmarks (built into the framework) plus a SatDiff-specific held-out test set. Training code and weights are public at `<HuggingFace URL>` and `<repo>/training/`."

That paragraph hits every fine-tuning rubric requirement: methodology, measurable improvement, public weights, public code.
