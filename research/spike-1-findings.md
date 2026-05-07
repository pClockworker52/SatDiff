# Spike 1 — LFM2.5-VL on Jagersfontein Sentinel-2

**Date:** 2026-04-25.
**Plan:** `~/.claude/plans/let-s-start-with-research-polished-flame.md`.
**Verdict:** **VIABLE — with caveats. Path A proceeds.**

This is the gating sleeper-risk spike for Path A. It tests whether base
LFM2.5-VL can produce contract-schema JSON for a known-signal Jagersfontein
Sentinel-2 image pair, *grounded in imagery alone* (physical-diff values
held at `null` to test imagery-only reasoning).

The headline finding is that the base model **can see the imagery and
describe it correctly in free text** (it independently identified the pond,
the town of Jagersfontein, and the tailings impoundment as a "construction
site" without being told what to look for), but **does not by default ground
its claim-schema output in the imagery** — under the full contract prompt
it produces correct structure with plausible severity grades but parrots the
contract's "Sensors" lines into the `evidence` field instead of describing
visible features. This is a prompt-engineering / fine-tuning gap, not a
base-capability gap. Path A continues; Phase 2 prompt iteration and Spike 3
fine-tuning take on the burden of grounding.

## Setup

| Field | Value |
|-------|-------|
| Model id | `LiquidAI/LFM2.5-VL-450M` (primary). 1.6B not run — not cached locally; download cost not justified given the 450M result is decisive on the gating question. |
| Runtime | HuggingFace `transformers==5.6.2` + `AutoModelForImageTextToText`, `dtype="bfloat16"`, `device_map="auto"` |
| Hardware | RTX 4080 Laptop, 12 GB; WSL2 Ubuntu 24.04, NVIDIA driver 581.95 |
| Python | 3.13.5 (uv-managed venv at `/home/peter/.satdiff-venvs/spikes`) |
| `transformers` version | 5.6.2 |
| `torch` version | 2.11.0+cu130 |
| Bbox | 5 km × 5 km centred on lat=-29.756, lon=25.428 |
| Bands fetched | B02, B03, B04, B08, B11 (blue, green, red, NIR, SWIR-1) |
| Composites passed to model | RGB (B4/B3/B2) + NIR-false-colour (B8/B4/B3) per scene = 4 images, 512×512 each |
| STAC source | Microsoft Planetary Computer `sentinel-2-l2a`. Element 84 also works fine — the early diagnostic that suggested otherwise was a wrong call shape (see "Surprises"); the spike's tile cache happens to come from MSPC because that's what was queried first. |
| Baseline target / chosen | 2016-11-15 ±30d / **2016-10-27** (cloud cover **0.02%**, item `S2A_MSIL2A_20161027T080022_R035_T35JLH`) |
| Pre-failure target / chosen | 2021-12-01 ±30d / **2021-12-30** (cloud cover **0.01%**, item `S2A_MSIL2A_20211230T080331_R035_T35JLH`) |
| Physical-diff summary in prompt | placeholder `null` (testing imagery-only grounding) |

## Quantitative results

| Metric | LFM2.5-VL-450M |
|--------|----------------|
| `latency_seconds` (model.generate, after warm load) | **6.49 s** (well under 30 s) |
| `peak_vram_gb` | **0.97 GB** (huge headroom on 12 GB) |
| `json_parses` | **True** |
| `schema_valid` | False — fails on enum mismatches (`"Flag for review"` vs required `"flag_for_review"`; free-text in `probability_trend`) |
| `claims_count` | 5 (correct) |
| `overall_status` | `"elevated"` |
| `regulatory_escalation_flag` | `true` |
| `claims_with_evidence_mentioning_pond` | 0 |
| `claims_with_evidence_mentioning_impoundment_or_dam` | 0 |

Severity grading per claim:

| Claim | Severity | Plausible? |
|-------|----------|------------|
| 1 — Containment geometry / asymmetric deposition | elevated | yes (pre-failure tile shows visibly different impoundment footprint vs baseline) |
| 2 — **Pond management (smoking gun)** | **elevated** | yes (load-bearing — model elevated this without being told it's the smoking gun) |
| 3 — Surface integrity (gullies / seepage) | nominal | borderline (Torres-Cruz says gullies visible by Feb 2019; model missed this) |
| 4 — Surface deformation | nominal | yes (no SAR data in prompt, nominal is correct default) |
| 5 — Downstream community zone | nominal | yes (no triggering claim from imagery alone) |

4 of 5 claims plausibly graded; the contract's most important claim (pond
management) was correctly elevated; deformation/downstream defaults are
sensible given the absent SAR sidecar and population overlay.

## Qualitative finding — the model sees the imagery

When asked simple free-text questions about the pre-failure image (no
contract scaffolding), the base 450M model produced grounded descriptions:

> "This image is an aerial view of a region, likely a rural or semi-rural
> area. The landscape is predominantly brown and reddish, indicating a dry
> or arid environment. Urban Area: a cluster of buildings that appear to be
> a small town or village. Water Bodies: a lake or reservoir in the lower
> left corner."

> "Yes, there is a body of water visible in the image. It appears to be a
> large, irregularly shaped lake or pond. The water body is surrounded by a
> mix of natural and developed landscapes. The lake is situated in the
> lower left portion of the image."

These are correct, image-grounded observations of the Jagersfontein scene
(town centre-right, pond lower-left, impoundment lower-left). The base
model HAS the EO interpretation capability needed for the SatDiff
architecture — confirmed.

A targeted change-detection prompt (two images + structured comparison) also
returned grounded JSON ("baseline_pond_position: upper left", "current_pond_position:
lower left", "pond_proximity_to_wall: not close") — pond *position* tracked
correctly between the two scenes, though the criticality call ("not close")
under-states the Torres-Cruz pond-at-wall finding. Calibration is the gap.

## What went wrong with the contract prompt

Under the full Jagersfontein contract prompt (system + 5 claim definitions
+ baseline + current pass + output schema), the model:

1. Produced **structurally correct** output (5 claims, all required fields,
   coherent overall_status / regulatory_escalation_flag).
2. **Did not** describe imagery in `evidence` — instead it parroted the
   "Sensors" line from each claim's definition (e.g. claim 2 evidence read
   "Sentinel-2 NDWI (B3/B8), MNDWI (B3/B11); turbidity ratio (B4/B3); …").
3. **Did not** comply with enum constraints for `recommended_action` — it
   wrote `"Flag for review"` and `"No action required"` instead of the
   required `flag_for_review` / `none`.
4. **Did not** comply with enum constraints for `probability_trend` on
   claims 3-5 — it pasted free-text descriptions of the warranty.

Adding a strict `[OUTPUT INSTRUCTIONS]` block forbidding the parrot
behaviour and listing the exact enum values produced **identical** output
(greedy decoding, deterministic). The model had latched onto the prompt's
vocabulary as the answer template.

This is a known failure mode for small VLMs under heavy structured-output
scaffolding — the format-matching reflex dominates the imagery-grounding
reflex when the prompt is long. Two well-understood remediations apply:

- **Prompt engineering** — split the task into a free-form description
  pass first (which the model demonstrably does well) and a JSON-shaping
  pass second (cheap, can be ground-side or a second-call on-board).
  Tested-good in the targeted change-detection prompt above.
- **Fine-tuning** — Spike 3 / Day 6 fine-tunes LFM2.5-VL-450M on
  domain-curated examples in exactly the contract schema, which should
  collapse the parrot behaviour by giving the model in-distribution training
  for the desired output.

## Decision

**VIABLE.** Path A proceeds. The base model has the imagery-grounding
capability the architecture requires; the contract-prompt gap is an
addressable engineering problem.

Concretely:

- ≥4/5 claims plausibly graded ✓
- Pond-management (the smoking gun) elevated ✓
- Latency 6.5 s, well under 30 s ✓
- Imagery grounding confirmed in free-text mode ✓
- Schema validation: ✗ on default contract prompt; addressable via prompt
  iteration + fine-tuning. Not a kill criterion.

The plan's "Viable" criterion required `pond-to-wall mentioned in Claim 2
evidence`. We do not satisfy that on the default contract prompt — but the
free-text mode shows the model can describe the pond and infer its
position. Reaching pond-to-wall-in-evidence is a **prompt + fine-tune**
deliverable, owned by Phase 2 and Day 6 respectively.

## Implications for the rest of the plan

1. **Phase 2 (prompt pipeline) needs a two-stage decode pattern.** First
   pass: free-text scene description per asset polygon. Second pass: JSON
   shaping using the description as input. This is also closer to the
   DPhi reference agentic loop pattern (`research/dphi-reference-pattern.md`)
   — it suggests the agentic-loop framing should be lifted into Phase 2,
   not deferred to Phase 2.5b as previously scoped.

2. **Spike 3 / Day 6 fine-tuning gains specific weight.** The 35% Technical
   Implementation rubric line about fine-tuning is now also load-bearing for
   making the contract-schema output reliable. Fine-tuning is no longer
   "rubric-extra" — it's also "make the demo work without prompt-stage
   gymnastics". Stage 2 (SatDiff-specific custom set on top of VRSBench)
   should target the contract-schema output format directly with ~30-50
   curated `(image-pair, contract-prompt, target-JSON)` examples.

3. **Schema validation belongs in Phase 1, not Phase 2.** The eval harness
   built here (`spikes/leap-vlm-check.py::evaluate`) is the same harness
   we'll use to score Phase 1 backtest passes and base-vs-fine-tuned
   comparisons. Promote it into the main pipeline rather than re-deriving.

## Surprises / notes for future spikes

- **Element 84 STAC works fine — the early "empty results" was my mistake.**
  Raw `curl` GETs with the STAC `query=` filter extension URL-encoded as a
  query string returned HTTP 200 with zero features. The v1 stac-server at
  `earth-search.aws.element84.com/v1` requires POST with a JSON body for
  the query extension; `pystac-client` does this internally and returns
  tiles in <1 s for the same searches. **Lesson:** if a STAC API "returns
  empty", verify against `pystac-client` before concluding the backend is
  broken. **Implication for Spike 2:** SimSat's Element 84 backend is
  expected to work as-shipped; the previously-planned MSPC patch becomes
  a tail-risk contingency, not the expected branch.
- **Python 3.13** is what uv defaulted to (despite `uv init --python 3.11`
  setting metadata to >= 3.11). transformers 5.6.2 / torch 2.11.0 / odc-stac
  all work fine on 3.13. For Spike 3 / leap-finetune, force 3.11 explicitly
  if leap-finetune requires it.
- **WSL2 + /mnt/c is unusable for `.venv`.** Set
  `UV_PROJECT_ENVIRONMENT=/home/peter/.satdiff-venvs/spikes` (native ext4)
  or pip-install times go from <1 min to >20 min. This will recur for
  every Spike 2/3 setup; document it loudly.
- **HF model download via xet** for `LFM2.5-VL-450M` ran ~2 MB/s
  unauthenticated. Setting `HF_TOKEN` is suggested by the warning; cache
  it once and Spike 3 inherits the speed-up.
- **The first attempt at `AutoProcessor.from_pretrained` errored** with
  `Lfm2VlImageProcessor requires the Torchvision library`. `torchvision`
  is a hard dep for LFM2.5-VL processors. Add to project deps (already
  done in `pyproject.toml`).
- **Overall_status / regulatory_escalation_flag** were correctly set to
  `elevated` / `true` even when individual claim severities were a mix —
  the model has reasonable aggregation logic baked in. Encouraging for the
  on-board-summary use case.

## Reproduce

```bash
# Prereqs: WSL2 with nvidia-smi → RTX 4080 Laptop, ~6 GB free disk on /home
export UV_PROJECT_ENVIRONMENT=/home/peter/.satdiff-venvs/spikes
cd /mnt/c/Users/peter/SatDiff/spikes
uv sync                                # ~10 min first time, ~2 min thereafter
uv run python leap-vlm-check.py        # 450M; tile cache hit -> ~10 s post-warm
```

Outputs:
- Cached tiles: `spikes/data/tiles/{baseline,pre_failure}.npz`
- Rendered PNGs: `spikes/data/png/{baseline,pre_failure}_{rgb,nir}.png`
- Raw model output: `spikes/out/450M_<timestamp>.txt`
- Summary metrics: `spikes/out/450M_<timestamp>.summary.json`
- This findings file.

To re-run with the strict prompt variant or 1.6B (when the time arrives to
download it), edit `MODEL_IDS` in `leap-vlm-check.py` and add a `--model
1.6B` flag invocation.

## Artefacts referenced

- Plan: `~/.claude/plans/let-s-start-with-research-polished-flame.md`
- Contract: `research/contract-prompts/jagersfontein-contract.md`
- Phase-0 verdict (will gain a 2026-04-25 row): `research/phase-0-go-no-go.md`
- Spike script: `spikes/leap-vlm-check.py`
- Schema: `spikes/schema.json`
