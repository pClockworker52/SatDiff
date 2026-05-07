#!/usr/bin/env bash
# Start llama-server hosting the Stage 1 GGUF Q8_0 backbone + F16 mmproj.
#
#   bash inference/llama-server.sh           # foreground
#   bash inference/llama-server.sh --port 8080 --threads 6 ...
#
# Defaults match inference/llama-server.config — keep them in sync.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Prefer the CUDA build; fall back to the CPU build.
if [[ -x "${HERE}/llama.cpp/build-cuda/bin/llama-server" ]]; then
    BIN="${HERE}/llama.cpp/build-cuda/bin/llama-server"
    : "${N_GPU_LAYERS:=99}"
else
    BIN="${HERE}/llama.cpp/build/bin/llama-server"
fi
MODEL="${HERE}/gguf/LFM2.5-VL-450M-stage1-Q8_0.gguf"
MMPROJ="${HERE}/gguf/mmproj-LFM2.5-VL-450M-stage1-Q8_0.gguf"

PORT="${LLAMA_SERVER_PORT:-8080}"
HOST="${LLAMA_SERVER_HOST:-0.0.0.0}"
CTX_SIZE="${LLAMA_SERVER_CTX:-8192}"
THREADS="${LLAMA_SERVER_THREADS:-$(nproc)}"

if [[ ! -x "${BIN}" ]]; then
    echo "llama-server not built. Run: bash inference/build_llama_server.sh"
    exit 1
fi
if [[ ! -f "${MODEL}" || ! -f "${MMPROJ}" ]]; then
    echo "GGUF pair missing under ${HERE}/gguf/. Run: bash inference/quantize.sh"
    exit 1
fi

GPU_ARGS=()
if [[ -n "${N_GPU_LAYERS:-}" ]]; then
    GPU_ARGS+=(--n-gpu-layers "${N_GPU_LAYERS}")
fi

exec "${BIN}" \
    --model "${MODEL}" \
    --mmproj "${MMPROJ}" \
    --host "${HOST}" \
    --port "${PORT}" \
    --ctx-size "${CTX_SIZE}" \
    --threads "${THREADS}" \
    "${GPU_ARGS[@]}" \
    "$@"
