#!/usr/bin/env bash
# One-shot: merged Stage 1 fp16 ckpt → GGUF Q8_0 backbone + F16 mmproj.
#
# Outputs (in ./inference/gguf/):
#   LFM2.5-VL-450M-stage1-Q8_0.gguf
#   mmproj-LFM2.5-VL-450M-stage1-Q8_0.gguf
#
# Reuses the leap-finetune venv (gguf, transformers, torch, numpy, sentencepiece, protobuf).
# First run clones + builds llama.cpp under ./inference/llama.cpp/ (gitignored).

set -euo pipefail

CKPT="${SATDIFF_STAGE1_CKPT:-/home/peter/leap-finetune/outputs/satdiff_stage1/LFM2.5-VL-450M-vlm_sft-satdiff_st-all-lr1em05-w0p2-lora_a-20260426_221338/LFM2.5-VL-450M-vlm_sft-satdiff_st-all-lr1em05-w0p2-lora_m-20260426_221338}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="${HERE}/gguf/LFM2.5-VL-450M-stage1-Q8_0.gguf"

UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-/home/peter/.satdiff-venvs/leap-finetune}" \
    uv run --directory /home/peter/leap-finetune \
        python "${HERE}/quantize.py" \
        --checkpoint "${CKPT}" \
        --output "${OUT}" \
        --quant Q8_0
