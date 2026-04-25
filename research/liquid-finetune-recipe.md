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

### 1. Local primary on WSL2 + RTX 4080; Modal as registered fallback.

User's laptop: Alienware m18 R2, i9-14900HX, 32 GB RAM, **RTX 4080 mobile 12 GB**, Windows 11 + WSL2 Ubuntu. This is genuinely capable for 450M LoRA (~4–6 GB VRAM at batch 4) and feasible for 1.6B LoRA with QLoRA (~5 GB VRAM at batch 1).

The Discord poster's flash-attn issue does **not** apply: they were on DGX Spark (ARM64 + Blackwell, brand-new platform with patchy wheel availability). User is on x86_64 + Ada Lovelace, which flash-attn ships prebuilt wheels for.

**Recommended split:**

| Phase | Where | Why |
|-------|-------|-----|
| Spike 3 smoke test | Local WSL2 | Fast iteration, no Modal setup blocks progress |
| Prompt engineering / eval design | Local WSL2 | CPU/lightweight; Modal would be overkill |
| Stage 1 VRSBench fine-tune (first runs) | Local WSL2 | Iterate hyperparameters fast |
| Final published training run (weights uploaded to HF) | Either — Modal if we want a maximally reproducible artefact, local otherwise | Reproducibility vs convenience tradeoff |
| Stage 2 SatDiff custom | Local WSL2 | Tiny dataset; lower LR; continues from Stage 1 |
| Optional 1.6B experiment | Modal H100 | More VRAM headroom; only if Stage 1 went well |

**Plan: register Modal anyway.** $30 free credit costs nothing to claim. Lives as insurance + as the published-final-run option. Don't gate Day 6 on being signed up — register now, in calm weather.

### 2. WSL2 setup gotchas to anticipate (Day 1)

Common failure modes and the order that minimises pain:

1. `wsl --update` from PowerShell — get latest WSL2.
2. `wsl --install -d Ubuntu-24.04` — fresh Ubuntu.
3. **Update NVIDIA driver on Windows host** (Game Ready or Studio, late-April-2026 release). CUDA-on-WSL2 uses the Windows driver — do **not** install an `nvidia-*` driver inside WSL2 (will break passthrough).
4. Verify inside WSL2: `nvidia-smi` lists the RTX 4080. If not → driver issue on Windows host.
5. Install CUDA *toolkit* inside WSL2 (need `nvcc` for flash-attn from source). Pick the version matching PyTorch's bundled CUDA (likely 12.4 or 12.6).
6. Install Python 3.11, `uv`, `uv sync` the leap-finetune repo.
7. `pip install flash-attn --no-build-isolation`. Prebuilt wheel = instant. Source build = ~30–60 min compile, ~16 GB RAM peak.
8. If flash-attn refuses after a reasonable attempt: set `attn_implementation="eager"` (slower but works) **or** switch that run to Modal.

Most likely failure: PyTorch ↔ CUDA toolkit version mismatch. Symptom: `torch.cuda.is_available()` returns `False` despite `nvidia-smi` working. Diagnosis: compare `python -c "import torch; print(torch.version.cuda)"` against `nvcc --version`. Should match within a minor version.

### 3. Use the official `leap-finetune` framework. Not raw `transformers + peft`.

The framework is what Liquid AI judges expect to see in a Liquid Track submission. The submission writeup explicitly references `leap-finetune` and the `vrsbench_multitask_modal.yaml` config (or our extended version) and gains credibility for using the supported tooling.

### 4. Switch primary target from LFM2-VL-1.6B to LFM2.5-VL-450M.

Two reasons:
- The official tutorial targets 450M. Path-of-least-resistance.
- The 450M is faster to fine-tune (less wall-clock per epoch), giving us more iteration room within Day 6.
- Sub-250ms edge inference per published benchmarks. Still fits Orin 16GB comfortably.

LFM2-VL-1.6B remains a fallback / "if there's time on Day 6 try the bigger one" option.

### 5. Use VRSBench as the foundation dataset.

VRSBench gives us 200K+ examples of satellite-VLM data. We don't curate 30 examples from scratch.

**Recommended approach: two-stage fine-tune.**
- **Stage 1 — VRSBench multitask SFT.** Use the published config. Improves base model on general remote-sensing VQA / grounding / captioning. The framework's built-in benchmarks measure improvement automatically.
- **Stage 2 (optional, if time permits) — small SatDiff-specific custom set.** ~20–30 hand-written examples of (image-pair, contract-prompt, target-JSON) for tailings monitoring. Continues training from the Stage 1 checkpoint with a lower learning rate. Teaches our contract vocabulary on top of the satellite-VLM uplift.

If Day 6 time runs short, we ship Stage 1 only. Stage 1 alone is a defensible "measurable improvement over base" deliverable backed by VRSBench benchmarks.

### 6. The framework's built-in evals are our submission's measurable-improvement metrics.

Decision A from the fine-tuning primer (designing a metric) is essentially **solved by adopting the framework's evals**:
- VQA short_answer accuracy on VRSBench-VQA test split
- Grounding IoU@0.5 on VRSBench-Grounding test split
- CIDEr / BLEU on VRSBench-Captioning test split

These are recognized benchmarks. Reporting "base LFM2.5-VL-450M scored X / Y / Z; fine-tuned scored A / B / C" with these metrics is exactly what the rubric asks for, and it's reproducible without designing our own eval pipeline.

We can additionally publish a **SatDiff-specific eval** (the held-out tailings-dam custom set) for the community-pool eval-sharing thread on Discord. Two metrics: domain-recognized + domain-specific.

### 7. The Discord poster's flash-attn problem isn't ours.

DGX Spark (ARM64 + Blackwell) has patchy wheel availability. WSL2 + RTX 4080 (x86_64 + Ada Lovelace) is a mainstream, well-supported combination. flash-attn ships prebuilt wheels for it.

Fallback if local flash-attn refuses: `attn_implementation="eager"` (slower, works) or switch the run to Modal.

## Updated Spike 3 procedure (local primary, Modal fallback)

1. **Sign up for HuggingFace** with write access (we'll publish weights). ~5 min.
2. **Sign up for Modal** and claim $30 credit. Don't run anything yet — this is insurance. ~5 min.
3. **WSL2 setup** per §2 above (driver, WSL2 update, Ubuntu 24.04, CUDA toolkit, Python 3.11, `uv`). ~30–60 min depending on driver state.
4. **`huggingface-cli login`** so credentials are available.
5. **Clone `leap-finetune`:** `git clone https://github.com/Liquid4All/leap-finetune.git && cd leap-finetune && uv sync`. ~5 min.
6. **Verify CUDA in PyTorch:** `uv run python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"`. Should print `True`, `NVIDIA GeForce RTX 4080 Laptop GPU`.
7. **Install flash-attn:** `uv pip install flash-attn --no-build-isolation` (or whatever the leap-finetune config requires). If a wheel exists, instant. If source build, 30–60 min in the background while you prep data.
8. **Run a tiny smoke-test config** locally — same as the official VRSBench config but with `limit: 50` on training and eval datasets so it finishes in 10–15 min. Confirms end-to-end pipeline works.
9. **If smoke test passes locally:** Day 6 runs locally. Reserve Modal as the published-final-run option for reproducibility.
10. **If smoke test fails after reasonable debugging (~2 hours):** switch the smoke test to Modal: `uv run leap-finetune job_configs/vrsbench_multitask_modal.yaml`. Modal container has flash-attn pre-installed.

After smoke test: run benchmarks (built into the framework) on base vs the smoke-test fine-tuned to confirm the eval pipeline produces sensible numbers.

Expected Spike 3 outcome: **a fine-tuned LFM2.5-VL-450M with documented VRSBench improvement, published to HuggingFace, with reproducible training code in the submission repo.** That alone hits most of the rubric's fine-tuning requirements.

If we have remaining time on Day 6: continue with Stage 2 (SatDiff-specific) custom training on top.

## Decision: confirmed

**User hardware:** Alienware m18 R2, i9-14900HX, 32 GB RAM, RTX 4080 12 GB, Win11 + WSL2.
**Plan:** local primary, Modal as registered fallback. Sign up for Modal to claim $30 credit; don't run anything there yet.

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
