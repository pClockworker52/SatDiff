#!/usr/bin/env bash
# Build the llama-server target inside the same llama.cpp clone that
# quantize.py bootstrapped. Idempotent — skips if the binary is already there.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LLAMA_CPP_DIR="${HERE}/llama.cpp"
BIN="${LLAMA_CPP_DIR}/build/bin/llama-server"

if [[ ! -d "${LLAMA_CPP_DIR}" ]]; then
    echo "llama.cpp not present at ${LLAMA_CPP_DIR}. Run inference/quantize.sh first."
    exit 1
fi

if [[ -x "${BIN}" ]]; then
    echo "llama-server already built at ${BIN}"
    exit 0
fi

cd "${LLAMA_CPP_DIR}"
# build/ already configured by quantize.py
[[ -d build ]] || cmake -B build
cmake --build build --config Release -t llama-server -j "$(nproc)"
echo "Built ${BIN}"
