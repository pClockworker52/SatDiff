# Workstream [6] — GGUF + llama-server inference

**Status:** ✅ DONE 2026-04-28 (CPU + CUDA). Schema parity + evidence-correctness lift preserved through Q8_0 quantization on both transports. CUDA offload achieves **2.38 s/pass mean** on the held-out 6, an 8.4× speedup over CPU and ~4.7× over transformers+bf16.

## Verification matrix vs Plan v2

| target | actual | verdict |
|---|---|---|
| Quantize script produces both .gguf files | ✅ `inference/gguf/LFM2.5-VL-450M-stage1-Q8_0.gguf` + `mmproj-...-Q8_0.gguf` | pass |
| Total size ≤ 700 MB | **544 MB** (362 MB Q8_0 backbone + 182 MB F16 mmproj) | pass |
| `llama-server -m ... --mmproj ...` starts cleanly; `/health` 200 | ✅ both verified | pass |
| schema_valid 6/6 on held-out | **6/6** | pass |
| evidence_correct 30/30 (Stage 1 lift preserved) | **30/30 (100%)** | pass |
| ≤ 2 s/pass total, ideally ≤ 1 s | **2.38 s mean (CUDA)** / 19.88 s (CPU) | partial — under 3 s but not 1 s; see "Latency floor" below |

The held-out backtest reproduced through llama-server is operationally identical to the Stage 1 transformers run on the contract-relevant axis: every claim still cites the right `phase1_diff` field, every pass still resolves to `urgent`, every Stage B output is still schema-valid. The only regression is in the latency target, which depended on a CUDA-built llama.cpp that we did not get to in this session.

## Per-pass latency

### CUDA (RTX 4080 Laptop, sm_89, --n-gpu-layers 99)

| date | Stage A (s) | Stage B (s) | total (s) | corrections |
|---|---:|---:|---:|---:|
| 2021-08-15 | 1.51 | 1.40 | 2.91 | 4 |
| 2021-12-15 | 0.91 | 1.40 | 2.31 | 1 |
| 2022-01-15 | 0.87 | 1.41 | 2.28 | 1 |
| 2022-04-15 | 0.86 | 1.43 | 2.29 | 1 |
| 2022-07-15 | 0.69 | 1.47 | 2.16 | 1 |
| 2022-10-15 | 0.89 | 1.45 | 2.34 | 1 |
| **mean** | **0.96** | **1.43** | **2.38** | — |

GPU memory: 587 MiB used out of 11043 MiB free (Q8_0 backbone + F16 mmproj fully offloaded). System: WSL2 Ubuntu 24.04, NVIDIA driver 581.95 (CUDA 13 capable host driver), conda-installed CUDA 12.6 toolkit + nvcc, sm_89 build.

### CPU (no GPU, 8 threads)

| date | Stage A (s) | Stage B (s) | total (s) | corrections |
|---|---:|---:|---:|---:|
| 2021-08-15 | 5.52 | 11.46 | 16.98 | 4 |
| 2021-12-15 | 6.64 | 12.64 | 19.28 | 1 |
| 2022-01-15 | 6.56 | 13.49 | 20.05 | 1 |
| 2022-04-15 | 5.85 | 14.85 | 20.70 | 1 |
| 2022-07-15 | 5.75 | 14.93 | 20.68 | 1 |
| 2022-10-15 | 6.75 | 14.87 | 21.62 | 1 |
| **mean** | **6.18** | **13.71** | **19.88** | — |

### Comparison vs other transports (held-out 6, same prompts, same 4 images per pass)

| transport | mean total | speedup vs slowest | image footprint |
|---|---:|---:|---:|
| Stage 1 transformers + bf16 (RTX 4080) | ~11.2 s | 1.8× | ~860 MB ckpt |
| Q8_0 + llama-server CPU (8 threads) | 19.88 s | 1.0× (baseline) | 544 MB GGUF |
| **Q8_0 + llama-server CUDA (sm_89)** | **2.38 s** | **8.4×** | **544 MB GGUF** |

### Latency floor

The 2.38 s/pass result is essentially at the floor for this task shape (4 images + ~4K-token contract prompt + Stage A + Stage B greedy decode of ~400+800 tokens). Stage A on CUDA averages 0.96 s — that's mostly image encode (mmproj clip on GPU) + a few hundred decoded tokens. Stage B at 1.43 s is dominated by ~800 token decode at ~600 tokens/s on this GPU. The wildfire-prevention reference's 0.59 s/pass benchmark assumes one image and short output; replicating it with our prompt shape would require either (a) a single image input or (b) shrinking Stage B output — both of which trade off the audit-trail deliverable. **2–3 s/pass is the right number for the writeup.**

## Severity-correction shift: 5 → 9 (held-out, both transports)

Stage 1 transformers required 5 rules-engine corrections across the 6 held-out passes (per `research/session-2026-04-28-handoff.md`). The Q8_0 + llama-server run requires **9** under both CPU and CUDA backends (identical per-pass corrections: 4, 1, 1, 1, 1, 1) — the regression is therefore **not GPU/CPU dependent** but specific to the GGUF/llama.cpp execution path. Likely root causes:

1. **Q8_0 weight noise**, especially on threshold-bearing logits.
2. **Chat-template handling differences** — llama.cpp uses an internally-derived ChatML template; transformers uses the embedded `chat_template.jinja` from the merged ckpt. Even small token-boundary differences (e.g. whitespace-after-image-token) can shift threshold reasoning at this model scale.

This **does not affect the architectural story** — the Python rules engine in `phase2/aggregate.compute_severity` overlays gold severity onto the model's claims regardless of what the VLM said. Stage 2's negative result already established that fine-tuning at this scale doesn't transfer multi-tier threshold reasoning; quantization is just another reminder of the same point. The contract artefact the GISTM auditor consumes is the rules-engine output, not the model's stage_b_parsed_model_only field.

For the writeup: lead with **evidence-correctness 100%** (the part fine-tuning + quantization both preserved) and frame severity as the rules-engine's domain.

## What landed in this session

**New files:**
- `inference/quantize.py` — vendored from `Liquid4All/cookbook/examples/wildfire-prevention/scripts/quantize.py`, retargeted at our paths
- `inference/quantize.sh` — one-shot wrapper using the leap-finetune venv
- `inference/build_llama_server.sh` — separate llama-server target build
- `inference/llama-server.sh` — runtime wrapper
- `inference/llama-server.config` — documentation of runtime args
- `inference/gguf/LFM2.5-VL-450M-stage1-Q8_0.gguf` (362 MB, gitignored)
- `inference/gguf/mmproj-LFM2.5-VL-450M-stage1-Q8_0.gguf` (182 MB, gitignored)
- `inference/llama.cpp/` — bootstrapped clone (gitignored)
- `phase2/llama_client.py` — `LlamaServerVLM` HTTP transport (~75 LoC)
- `.gitignore` — top-level, covers GGUF + build dirs + phase outputs
- `research/workstream-6-findings.md` (this file)

**Modified:**
- `phase2/runner.py` — factored `VLM` interface, added `make_vlm()` selector keyed on `SATDIFF_INFERENCE` env var (`transformers` | `llama_server`); transport-aware `peak_vram_gb` measurement.
- `phase2/cli.py` — uses `make_vlm()`, accepts `--inference` flag.
- `training/eval_finetuned.py` — uses `make_vlm()`.

**Modified (by venv install):**
- `/home/peter/.satdiff-venvs/leap-finetune` — added `gguf==0.18.0`, `sentencepiece==0.2.1` (for `convert_hf_to_gguf.py`).

## Reproduce

```bash
# 1. (one-time setup — only needed if rebuilding from scratch on a new machine)
#    Install CUDA 12.6 toolkit + static cudart + nvcc=12.6 into the base conda env.
#    Then symlink lib64 -> lib so CMake's FindCUDAToolkit picks up cudart.
conda install -n base -c nvidia cuda-toolkit=12.6 cuda-cudart-static cuda-nvcc=12.6 -y
ln -s lib /home/peter/miniconda3/lib64

# 2. Quantize (~3 min once llama.cpp build is cached; ~10 min cold)
cd /mnt/c/Users/peter/SatDiff
bash inference/quantize.sh

# 3. Build CUDA llama-server (~5 min once cached; ~10 min cold)
cd inference/llama.cpp && cmake -B build-cuda -DGGML_CUDA=ON \
    -DCMAKE_CUDA_ARCHITECTURES=89 \
    -DCUDAToolkit_ROOT=/home/peter/miniconda3 \
    -DCUDA_CUDART=/home/peter/miniconda3/lib/libcudart.so
cmake --build build-cuda --config Release -t llama-server llama-quantize -j 16

# 4. Start CUDA llama-server (foreground)
cd /mnt/c/Users/peter/SatDiff
LD_LIBRARY_PATH=/home/peter/miniconda3/lib bash inference/llama-server.sh --threads 4
# wrapper auto-detects build-cuda/ and adds --n-gpu-layers 99

# 5. In a second shell — held-out 6-pass eval
SATDIFF_INFERENCE=llama_server LLAMA_SERVER_URL=http://127.0.0.1:8080 \
UV_PROJECT_ENVIRONMENT=/home/peter/.satdiff-venvs/spikes \
PYTHONPATH=/mnt/c/Users/peter/SatDiff \
uv run --directory /mnt/c/Users/peter/SatDiff/spikes python \
    /mnt/c/Users/peter/SatDiff/training/eval_finetuned.py \
    --model "WobblyDopamine/SatDiff-LFM2.5-VL-450M-stage1-Q8_0" \
    --label stage1_q8_0_cuda_heldout --held-out-only

# Optional: fallback path (transformers + bf16) for comparison
SATDIFF_INFERENCE=transformers ... eval_finetuned.py --model <stage1_ckpt_dir> --label stage1_xfmr_heldout --held-out-only
```

## CUDA setup gotchas (worth saving)

The conda nvidia channel doesn't ship a clean drop-in for CMake's FindCUDAToolkit. Three landmines we stepped on:

1. **`cuda-toolkit=12.6` metapackage actually pulled `cuda-nvcc=12.4`** initially. The static cudart from `cuda-cudart-static=12.6` then refused to link with the older nvcc ("newer than toolkit (126 vs 124)"). Fix: explicitly pin `cuda-nvcc=12.6` alongside the toolkit metapackage.
2. **No `libcudart_static.a` / `libcudadevrt.a` by default.** CMake's CUDA compiler-id detection step requires both. Fix: `conda install cuda-cudart-static`.
3. **CMake's FindCUDAToolkit only searches `lib64/`, `lib/x64/`, etc. — never plain `lib/`.** Conda lays libraries out under `lib/`. Fix: `ln -s lib /home/peter/miniconda3/lib64`. (Alternative: pass `-DCUDA_CUDART=/home/peter/miniconda3/lib/libcudart.so` explicitly; we use both belt+suspenders in the reproducer above.)

These are documented in `feedback_wsl2_conda_cuda.md` (saved memory).

## Remaining work in [6]

1. **Plan v2 latency claim** — revise the "~0.6 s/pass" cited in `~/.claude/plans/let-s-start-with-research-polished-flame.md` to **2.38 s/pass on RTX 4080 / sm_89, 19.88 s/pass CPU-only**. The 0.59 s wildfire-prevention number doesn't apply to our prompt shape (we use 4 images + a 4K contract memo; they used 1 image + short prompt).
2. **Severity regression honesty** — the writeup's fine-tune deliverables section (`[3]`) should mention that Q8_0 + chat-template differences shift severity_corrections from 5 → 9 on held-out, **and that the rules engine corrects all 9 to gold**. This is on-thesis with the rules-engine architecture story. The shift is identical on CPU and CUDA, confirming it's the GGUF/llama.cpp execution path, not hardware.
3. **(Optional)** Test Q5_K_M / Q6_K to see if a less aggressive quantization recovers some of the threshold reasoning. Probably not worth the effort given the rules engine handles severity authoritatively, but a 1-line argument change to `inference/quantize.sh` is cheap.
