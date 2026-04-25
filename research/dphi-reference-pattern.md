# DPhi Reference Pattern — Agentic VLM for EO

**Source:** DPhi Space Discord post 2026-04-24/25, hackathon channel.
**Published artefact:** `github.com/DPhi-Space/agentic-vlm-maritime-monitoring` — proof-of-concept demonstrating the host's preferred VLM-on-satellite pattern.

## What it shows

DPhi Space (the hackathon host) released a reference implementation: an **agentic VLM for maritime traffic monitoring** validated on the **Ever Given grounding incident (March 2021)** in the Suez Canal.

**The agent's behaviour pattern:**
1. Detect an anomaly (unusual vessel accumulation in the bay south of the canal).
2. Autonomously investigate the surrounding area without human prompting.
3. Identify the root cause (the grounded 400m container ship blocking the waterway).

**Stack:** Sentinel-2 imagery via the DPhi/SimSat API + a vision-language model + an agent orchestration loop.

**Stated future direction:** SimSat integration to run the same pipeline on the simulated satellite.

## Implications for SatDiff

### Confirmations (we're on-pattern)

- **Historical case-study approach is endorsed.** Our Jagersfontein and Brumadinho backtests fit this template.
- **Sentinel-2 via DPhi/SimSat is the expected data path.** Our existing architecture is correct.
- **VLM + EO is the application class** the host wants to see. We are not building something orthogonal to their interests.

### Gap (we need to close)

Our current on-board loop is **single-pass**: each Sentinel-2 pass → physical-diff → VLM produces structured JSON → done. The supervisory loop is on the ground.

DPhi's reference pattern is **multi-step agentic**: the VLM reasons, requests additional context, refines its assessment, all on-board. The single keyword is *agentic*.

If a judge places SatDiff next to DPhi's reference, our on-board loop looks one-shot by comparison. We should add a focused agentic step.

## The proposed addition: Phase 2.5b — Agentic follow-up loop

A small, scoped extension to the on-board pipeline. Not a rewrite.

### Trigger
Fires only when an initial-pass VLM output contains any claim with `severity_level: elevated` or `urgent`. Routine `nominal` passes skip the agentic step entirely (preserves compute budget and downlink economics).

### Agent action primitives
A bounded action set the VLM can invoke (capped at 2–3 follow-up queries):

- `request_band(band_name)` — fetch a specific Sentinel-2 band combination (e.g., NDMI, SWIR composite) for the same tile.
- `request_historical(months_ago)` — fetch the same tile from N months prior for seasonal comparison.
- `request_adjacent(direction)` — fetch the neighbouring tile in a named direction (e.g., downstream).
- `request_baseline_comparison()` — fetch the original baseline tile for direct comparison.

Each action is a SimSat API call. The VLM's structured output specifies which action to take next; the orchestration loop executes it and feeds the result back into the next VLM invocation.

### Termination
- Max 3 follow-up queries per pass (prevents runaway loops; respects the ~25W compute envelope).
- Or VLM emits `action: finalize` with refined assessment.

### Output
A single refined per-claim JSON, plus a brief audit-log of which actions the agent took and why (1–2 sentences per action). This lands in the structured report alongside the standard fields.

### Concrete Jagersfontein example

> **First pass (2020-12-15):** "Pond appears to extend toward retaining wall on northern face." Severity elevated.
> 
> **Agent action 1 — `request_historical(12)`:** fetches 2019-12 same scene.
> **VLM:** "Pond extent has grown 38% over 12 months."
> 
> **Agent action 2 — `request_band(NDMI)`:** fetches NDMI composite for current pass.
> **VLM:** "Northern wall face shows ΔNDMI = +0.14 vs baseline, consistent with surface saturation."
> 
> **Final assessment:** Severity escalated to **urgent**. Evidence cites both pond growth and wall-face saturation. Recommended action: `urgent_inspection`. `regulatory_escalation_flag: true`.

That's the agentic narrative DPhi's pattern endorses, applied to our case.

## What we should NOT do

- **Don't pivot to maritime.** Phase 0 is done; restarting it costs us 2+ days.
- **Don't copy their exact agent architecture.** Maritime traffic monitoring has different action primitives (vessel tracking, trajectory analysis) than ours (contract-claim assessment).
- **Don't burn a day studying their codebase.** Skim for orchestration patterns and prompt structure; don't try to mirror their implementation.
- **Don't make the agentic step heavyweight.** 2–3 follow-up actions max, capped tokens, capped time. Anything more eats Phase 1 budget.

## Implementation cost estimate

- Orchestration loop: ~half a day (Python loop + SimSat API calls + VLM re-invocation).
- Prompt design for action selection: ~half a day (similar to contract-prompt design — finite action vocabulary).
- Eval addition: agentic-pass success rate (does the refined assessment improve over the first-pass assessment in our held-out set?). Can be added to the existing eval framework.

Net: **~1 day of additional build time**, fits within the existing Day 7–8 Phase 2 budget.

## Submission writeup language

In the architecture section:

> "When SatDiff's first-pass VLM assessment flags any claim as elevated or urgent, the on-board agent autonomously issues up to three follow-up queries — additional spectral bands, historical comparisons, or adjacent-tile context — before finalising the report. This agentic loop, modelled on the pattern demonstrated by DPhi Space's maritime monitoring reference, allows the VLM to investigate flagged anomalies in the same way a human analyst would: gather context, reason, then commit. The refined assessment downlinks alongside an audit-log of actions taken."

This explicitly names DPhi's reference pattern (credibility) and applies it to our problem (originality).
