# Spike 1 — LFM2-VL on Jagersfontein Sentinel-2

The sleeper-risk gating spike for Path A. Pulls a known-signal Sentinel-2 image pair for the Jagersfontein TSF, runs LFM2-VL with the contract prompt, and grades whether the base model can produce contract-schema JSON that names the right geographic features.

## Run

```bash
cd /mnt/c/Users/peter/SatDiff/spikes
uv run python leap-vlm-check.py
```

Optional: `--model 1.6B` to use `LiquidAI/LFM2-VL-1.6B` instead of the default 450M.

Outputs land in `out/` (gitignored). Cached Sentinel-2 tiles and rendered PNGs land in `data/` (gitignored).

## What this is gating

The spike's verdict gates the Phase 1 build: *viable* unblocks the data + signal-extraction pipeline.
