# Phase 2 findings — LFM2.5-VL prompt pipeline + first backtest

**Status:** ✅ viable. The two-stage prompt + Python rules engine produces a contract-schema-valid JSON report for every Phase-1-invoked pass over the 17-month Jagersfontein window, at ~11 s wall-clock per pass on the RTX 4080.

## Setup

- Model: `LiquidAI/LFM2.5-VL-450M`, bf16, RTX 4080 12 GB, ~0.97-1.11 GB peak VRAM.
- Pipeline: `phase2.runner.run_pass(asset, date)` calls Phase 1's loader + baseline + diff, then issues two model passes:
  - **Stage A** — free-text describe (4 images: baseline RGB+NIR, current RGB+NIR), max_new_tokens=400.
  - **Stage B** — populate the contract JSON, max_new_tokens=1024, retry-once on schema fail.
- After Stage B parses, the **rules engine** (`phase2.aggregate.compute_severity`) computes severity_level / recommended_action / overall_status / downlink_priority / regulatory_escalation_flag from the diff numbers and overlays them onto the model's output. The model's pre-overlay severity is preserved as `stage_b_parsed_model_only` for the audit trail.
- Backtest: 16 passes over 2021-06-15 → 2022-10-15 selected from `phase1/out/jagersfontein/summary.json` (`invoke_vlm=true` rows).
- Run: `cd /mnt/c/Users/peter/SatDiff && UV_PROJECT_ENVIRONMENT=/home/peter/.satdiff-venvs/spikes PYTHONPATH=/mnt/c/Users/peter/SatDiff uv run python -m phase2.cli --asset jagersfontein --date-range 2021-06-15,2022-10-15`.

## Quantitative results

| metric | value |
|---|---|
| passes attempted | 16 |
| schema_valid | **16/16** |
| pond_mention ≥1 (after regex fix) | 17/17 incl. smoke pass |
| metric-value cited in evidence ≥1 | 16/16 (8/16 cited ≥4 distinct values) |
| overall_status="urgent" | 16/16 |
| regulatory_escalation_flag=true | 16/16 |
| mean Stage A latency | 3.95 s |
| mean Stage B latency | 7.24 s |
| total per-pass wall clock | ~11.2 s (well under the 30 s budget) |
| peak VRAM | 1.11 GB |
| total severity corrections by rules engine | 12 across 16 passes (model agreed in 8/16 passes) |

The "16/16 urgent" result is honest, not a stuck classifier — it reflects that on every Phase-1-passed pass between 2021-06 and 2022-10, **at least one** of (pond_to_wall_distance_m < 25 m, pond_area_change_pct_vs_baseline > +500%, gully_count ≥ 10) was true per the diff. That matches Torres-Cruz's finding that the asset was in continuous covenant violation throughout this window.

## Trajectory captured by the diff (informational, since severity is binary-pegged to "urgent")

| date | pond area (m²) | p2w (m) | asymmetry | gully_count | rules-engine corrections |
|---|---:|---:|---:|---:|---:|
| 2021-06-15 | 483,576 | 9.9 | 1.38 | 36 | 4 |
| 2021-07-15 | 474,995 | 9.9 | 1.40 | 24 | 0 |
| 2021-08-15 | 127,354 | 9.9 | 1.19 | 46 | 0 |
| 2021-09-15 | 198,833 | 9.9 | 1.08 | 31 | 0 |
| 2021-10-15 | 334,964 | 9.9 | 1.33 | 30 | 0 |
| 2021-11-15 |     975 | 39.5 | 1.09 | 14 | 1 |
| 2021-12-15 | 637,845 | 9.9 | 1.61 | 28 | 1 |
| **2022-01-15** | **1,896,959** | **0.0** | 1.75 | 14 | 2 |
| 2022-02-15 | 797,282 | 9.9 | 1.53 | 37 | 0 |
| 2022-03-15 | 900,843 | 9.9 | 1.51 | 33 | 0 |
| 2022-04-15 | 635,505 | 9.9 | 1.37 | 39 | 1 |
| 2022-05-15 | 275,772 | 9.9 | 1.16 | 30 | 1 |
| 2022-06-15 | 243,982 | 9.9 | 1.26 | 28 | 1 |
| 2022-07-15 | 236,571 | 9.9 | 1.17 | 32 | 0 |
| 2022-08-15 | 195,517 | 9.9 | 1.21 | 32 | 0 |
| **2022-10-15** | **3,272,213** | **0.0** | **22.57** | 26 | 1 |

The 2022-09-11 catastrophic failure pass itself is not in this set — Phase 1's gate skipped 2022-09-15 at 68% cloud cover (known defect; needs an extreme-metric override or SAR sidecar). The 2022-10-15 post-failure pass shows the signature: pond_to_wall_distance_m=0 (water meets failure scarp) and asymmetry index spiking to 22.57 (the lobe-shaped runout dominates the impoundment-mask centroid offset).

## Stage A — qualitative

Stage A produces grounded two-paragraph imagery descriptions (one for baseline pair, one for current pair). Sample from 2021-12-30 (smoke pass):

> PARAGRAPH 2 — The CURRENT pair (Image 3 RGB and Image 4 NIR) reveals significant changes compared to the baseline pair. The pond has grown in size, extending beyond the confines of the impoundment. It is now a large, irregularly shaped body of water, indicating a substantial increase in water volume. The tailings beach has moved further from the retaining wall, suggesting that the tailings material has been deposited in a new location. The dry beach appears to have contracted, likely due to the increased water volume. […]

The base 450M model picks up the pond growth and beach contraction — exactly the load-bearing 2021-12 signal Torres-Cruz called out. It also confabulates ("There are no visible cracks or gullies on the retaining wall […], indicating that the area has been stabilized") in tension with what Phase 1's gully detector finds at 9.85 m/px. This is fine for the v1 pipeline because Stage B's evidence sourcing rule pins each claim to a specific diff field, so Stage A confabulation can't propagate into the contract output.

## Stage B — Rules-engine-vs-model gap (the fine-tuning brief)

`severity_corrections` counts claims where the model's chosen severity tier disagreed with the deterministic rules engine. Total: **12 across 16 passes**, mean 0.75/pass. The model agreed with the rules engine on every claim in 8/16 passes and on at least one claim in all of them. Where it disagreed, the canonical pattern was **under-grading**:

- pond_to_wall_distance_m=9.9 m (rule: < 25 → urgent) — model returned "elevated"
- gully_count=34 (rule: ≥ 10 → urgent) — model returned "nominal"
- Claim 5 escalation when claims 1-3 are urgent — model defaults to "nominal"

This is consistent with what one expects from a 450M-parameter VLM doing chained threshold logic. The Day 6 fine-tune (VRSBench Stage 1 + a small SatDiff custom set Stage 2) targets exactly this class of multi-step conditional reasoning. Pre-fine-tune the rules-engine overlay covers it; the fine-tuned model should close the gap and let us drop or relax the overlay over time.

## Architectural decision: Python rules engine, not all-in-one prompt

We hit a clear capability ceiling on the 450M with multi-tier severity rules in the prompt. Rather than fight it with longer prompts (which we tried — see Stage B prompt evolution in `phase2/prompt.py`), we moved threshold logic to deterministic Python:

- **VLM responsibilities:** scene description (Stage A), evidence sentences citing specific diff fields, probability_trend.
- **Python rules engine (`phase2/aggregate.py`):** severity_level, recommended_action, overall_status, downlink_priority, regulatory_escalation_flag.
- **Audit trail:** `stage_b_parsed_model_only` preserves what the model emitted; `metrics.severity_corrections` tracks the gap.

This matches how production audit systems already separate "writer" from "rules engine" and is honest about the v1 model's reasoning ceiling. The on-board pipeline is **still** VLM-driven: imagery → Stage A grounding → Stage B contract evidence is what justifies running a VLM at all (vs. shipping just diff numbers). The rules engine sits between the model and the downlinked report — same place a deterministic post-processor would in any audit-grade system.

## Known issues / production-roadmap items

1. **2022-09-11 failure-day skip.** Phase 1 gate at 50% cloud cover misses the failure pass. Mitigations: extreme-metric override (force VLM if pond_area or asymmetry above absolute thresholds regardless of cloud); SAR sidecar; lower the gate threshold during a "rising-risk" window. Not yet implemented.
2. **Trajectory under-served by the binary "urgent"-since-2021-06 output.** Every pass is urgent because at least one rule fires. Useful for "this asset needs inspection" but flat as a story. Future: add a `risk_index` numeric in the contract output that ranks 0-1 across passes (combine pond growth, p2w shrinkage, gully delta, asymmetry slope). Out of scope for v1.
3. **`evidence_pond_mentions` regex** had a word-boundary bug; a literal substring match is correct because the diff field names use underscores (`pond_to_wall_distance_m`). Fixed in `phase2/runner.py`. Re-running is unnecessary — the saved outputs already contain "pond" hits when the regex is recomputed.
4. **Stage A confabulation** ("no visible gullies") is filtered by Stage B's per-claim evidence-sourcing rules, but it's a known weakness of the base 450M model on EO. Day 6 fine-tune should reduce it.

## Verdict

**Phase 2 is viable.** The system produces a schema-valid, evidence-grounded, urgency-correct contract JSON for every Phase-1-invoked pass at ~11 s/pass on the target hardware, with a clean rules-engine separation that makes the fine-tuning brief specific (`severity_corrections` is the metric to drive down). Phase 3 (PDF rendering / demo wiring + Day 6 fine-tune) is unblocked.
