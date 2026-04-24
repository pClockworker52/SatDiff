# Laptop Handoff — Read This First

Written 2026-04-24 after a mobile Phase 0 research session. Everything needed to continue on laptop is in this repo on branch `claude/hackathon-planning-yOI79`.

## 1. Get the repo on laptop

```bash
git clone <your-remote-for-pClockworker52/SatDiff> SatDiff
cd SatDiff
git checkout claude/hackathon-planning-yOI79
git pull
```

That branch contains **everything** from the mobile session — nothing is lost if you never saw those Claude Code sessions in your laptop history. The `research/` directory is the source of truth.

## 2. Read in this order (15 minutes)

1. `research/phase-0-go-no-go.md` — the provisional verdict (Path A: Jagersfontein primary, Brumadinho secondary, fusion pipeline)
2. `research/jagersfontein-memo.md` — why Jagersfontein is the clean Sentinel-2 case
3. `research/brumadinho-memo.md` — why Brumadinho needs SAR as a sidecar
4. `research/insar-gap-assessment.md` — the commercial-InSAR state of play
5. `research/satellite-architecture.md` — what hardware we're claiming is our target
6. `research/simsat-scout.md` — how SimSat works and how we plug in
7. `research/contract-prompts/jagersfontein-contract.md` — the prompt structure we're targeting
8. `research/contract-prompts/brumadinho-contract.md` — the secondary case's prompt
9. `research/open-questions.md` — gaps we didn't close in Phase 0
10. (the original plan) `019dbfdb-plan.md` if still uploaded, or regenerate from memory

## 3. Calendar reality check

- **Today:** 2026-04-24
- **Deadline:** Friday **2026-05-08, 8:00 PM EDT** (= 2026-05-09 02:00 CEST) per Luma event page
- **Remaining:** ~14 days
- Single judging round. **No bi-weekly interim checkpoint** (I assumed wrongly earlier — the event Luma page confirms this is a four-week single-round hackathon).
- 469 registered participants as of 2026-04-24. This is a serious competition.

## 3b. Track selection and the rubric — verbatim criteria received 2026-04-24

Full rubric is saved at `research/hackathon-rubric.md`. Headline weights:

**Liquid Track (our track) — weights:**

| Criterion | Weight | The ask |
|-----------|--------|---------|
| Use of Satellite Imagery (DPhi API) | **10%** | Imagery from SimSat, applied to a real-world domain. |
| Innovation and Problem-Solution Fit | **35%** | Problem is specific and real. LFM2-VL + imagery unlocks something neither could alone. **"A believable path to a product developers would pay to build on."** |
| Technical Implementation | **35%** | App runs without debugging — or it's disqualified. **Fine-tuning LFM2-VL is strongly encouraged and rewarded** with documented methodology, measurable improvement over base, and publicly shared weights + training code. |
| Demo and Communication | **20%** | End-to-end demo of **you (the participant) explaining the whole thing on camera.** "Writing code is easy in 2026; clearly articulating the problem and architecture is not." |

**Liquid Track prize:** $5K cash + space-credits package (see below).
**General Track prize:** space-credits package only (no cash).

**Space-credits package (both tracks):** 5 GPU hours on **NVIDIA Orin 16GB** in orbit, 5 MB upload / 10 MB download, 1 GB in-space storage for 1 month, fisheye-camera historic images, preloaded Docker images + LLMs on the satellite, 7 days of ground-server testing.

**Three things the rubric changes about the plan:**

1. **Innovation (35%) >> Imagery routing (10%).** Get the architectural pitch tight. The Torres-Cruz validation, audit-trail framing over monitoring framing, and GISTM-auditor-as-first-customer thesis (all in `research/open-questions.md`) are now proportionally the most valuable investment.

2. **"Product developers would pay to build on"** is product-market-fit language. The submission writeup must name the buyer (GISTM auditor primary; reinsurer adjacent), the line-item (Principle 7 compliance; retrospective claim defence), and the developer-API angle. Favour framing SatDiff as a per-asset monitoring API, not just a reinsurer report.

3. **Fine-tuning is not optional for scoring.** Required deliverables: documented methodology, measurable improvement vs base, **public HuggingFace weights**, public training code. This is part of the 35% Technical score. Budget 2 days for it.

**The actual prize satellite has a fisheye camera** — not a Sentinel-2 multispectral imager. Our demo uses Sentinel-2 via the DPhi API (which is the hackathon's data, not the prize platform's native sensor). The submission writeup's "production roadmap" section should acknowledge this and argue that SatDiff's contract-prompt architecture is **sensor-agnostic** — a feature, not a bug.

## 4. The two spikes — do these FIRST, before any Phase 1 build

Both are small and gating. If either fails, Path A needs reassessment.

### Spike 1 — LEAP + LFM2-VL on satellite imagery (the sleeper risk)

**Goal:** confirm LFM2-VL-450M (and 1.6B if it fits) can reason about top-down Sentinel-2 multispectral imagery well enough to produce structured JSON against our contract schema.

**Why it's critical:** LFM2-VL has no published benchmarks on nadir-view EO imagery. If it can't describe an erosion gully or pond-at-wall from a Sentinel-2 patch, the whole VLM-interpretation-layer claim rests on prompt engineering, not model capability.

**How to run:**
1. Install LEAP SDK per Liquid AI's official docs. Verify you can invoke LFM2-VL locally.
2. Manually pull two Jagersfontein tiles from Element 84 STAC (or Microsoft Planetary Computer) for a known-signal pair:
   - Clean baseline: Sentinel-2 tile covering `lat=-29.756, lon=25.428` (Jagersfontein TSF, South Africa), date circa **2016-09** (cloud-free austral spring).
   - Pre-failure: same location, date circa **2021-12** (pond-at-wall visible per Torres-Cruz & O'Donovan).
3. Crop to a ~3-5 km bbox around the TSF. Save as PNG RGB + a false-colour (e.g., NIR-Red-Green) version.
4. Prompt LFM2-VL with both images + the Jagersfontein contract (from `research/contract-prompts/jagersfontein-contract.md`) + the required JSON schema.
5. Evaluate:
   - Does it identify the impoundment geometry?
   - Does it name pond-to-wall proximity or erosion-gully features unprompted?
   - Does the output validate against the JSON schema?
   - Wall-clock latency on laptop?

**Decision:** if the VLM produces roughly correct structured output, Path A is viable. If it produces hallucinations or refuses to engage with EO imagery, we have a real problem — document in `research/open-questions.md` updates, then decide whether to (a) prompt-engineer harder, (b) fine-tune / few-shot, or (c) rescope to a narrower claim.

Budget for this spike: **half a day, max.** If it takes longer, something is wrong with the stack setup.

### Spike 2 — DPhi/SimSat API data pull

**Goal:** confirm we can pull the Jagersfontein archive **through the DPhi/SimSat API** (criterion 1 of the rubric) at the cadence needed for the backtest.

**Why SimSat specifically:** judging criterion 1 is *"Use of satellite imagery from the DPhi API."* Our submission's imagery ingress must route through `GET /data/image/sentinel?lon=&lat=&timestamp=&spectral_bands=&size_km=` (see `research/simsat-scout.md`). Hitting Element 84 STAC directly is fine for scratch / side-by-side debugging, but the final pipeline must consume through SimSat.

**How to run:**
1. `git clone https://github.com/DPhi-Space/SimSat.git && cd SimSat && docker compose up` — verify dashboard at `http://localhost:8000` and sim API at `http://localhost:9005`.
2. Run `python scripts/api_test.py sentinel_multispectral` to confirm multiband fetch works.
3. Script a loop calling `GET /data/image/sentinel` for the Jagersfontein bbox at e.g. monthly cadence 2016-01 → 2022-10, with `spectral_bands=red,green,blue,nir,swir16`. This exercises the exact path the final pipeline uses.
4. Expected: most months return data; some return `image_available=False` (cloud or gap). Log the hit rate.
5. Load three known-signal scenes (2016 clean, 2021 pond-at-wall, 2022-09 post-failure) and render RGB + NDWI composites via SimSat. Confirm visually:
   - The impoundment is visible
   - The 2021 pond-at-wall is visible
   - The 2022-09 post-failure scar is visible
6. **Caveat from SimSat README:** "The Sentinel-2 API is quite slow." Expect seconds per fetch. That's fine for the backtest if we checkpoint; but for the demo video, consider pre-caching to speed playback.

Budget: **a couple of hours** including a first-pass co-registration check.

### Spike 3 — LFM2-VL fine-tuning feasibility (scoring-critical)

**Why this matters:** the Liquid Track rubric says fine-tuning "**will be rewarded**" with three concrete deliverables: documented methodology, measurable improvement over base, publicly shared weights and training code. This is part of the 35% Technical Implementation score, plausibly ~10–15% of total. Skip at your peril.

**Goal of the spike:** confirm the tooling chain works end-to-end and we can realistically fine-tune LFM2-VL-450M (fallback) or LFM2-VL-1.6B (preferred) within ~1 day of actual training time.

**How to run:**
1. Check LEAP / HuggingFace docs for LFM2-VL LoRA / QLoRA support. The LFM2 Technical Report (arXiv 2511.23404) describes adaptation; confirm LFM2-VL variant has equivalent path. llama.cpp, MLX, ONNX are all rubric-acceptable runtimes.
2. Curate a tiny labelled set (say 30–100 examples) of Sentinel-2 patches with free-form descriptions in the style *"impoundment with pond against retaining wall; erosion gullies visible on northern wall; asymmetric deposition from north-east"*. Label style should match the Torres-Cruz paper's language. Source images:
   - Jagersfontein 2018–2022 (positive class: visible anomalies)
   - Jagersfontein 2014–2017 (negative class: stable baseline)
   - 2–3 other TSFs from public imagery for diversity (e.g., Mount Polley pre-2014, Samarco pre-2015, other GISTM-listed extremes)
3. Run a short LoRA fine-tune. Time it. Evaluate on held-out set with a simple metric (e.g., JSON-schema compliance rate + a few specific claim-assessment correctness checks).
4. Plan the HuggingFace model-card template: methodology, dataset description, eval numbers, licence.

**Decision:** if one LoRA epoch on 30–100 examples completes in a few hours with improved JSON-schema compliance over base, fine-tuning is a viable deliverable — reserve Day 6 for the real run. If training takes >1 day per run or outputs break structure, downgrade to "documented attempt" in the writeup and lean on prompt engineering for the main demo.

**Fine-tuning non-negotiables for the submission:**
- Model card on HuggingFace with clear licence
- Training code checked into the submission repo at `training/` or similar
- Eval script that reproduces the "base vs fine-tuned" comparison
- Short write-up in the README explaining what improved and by how much

Budget: **half a day for the spike; up to 1.5 days for the real fine-tune + evaluation + HF upload if Spike 3 passes.**

### Spike outputs

Suggested: commit a notebook or short Python script to `spikes/leap-vlm-check.ipynb` and `spikes/archive-pull.ipynb` (or `.py`). Update `research/phase-0-go-no-go.md` with the spike results. If both pass, tick the "Path A confirmed post-spike" line; proceed to Phase 1.

## 5. If the spikes pass: Phase 1 execution plan

Budget the remaining ~14 days roughly as:

- **Days 1–2 (spike days):** Spike 1 (LEAP/LFM2-VL on EO imagery), Spike 2 (SimSat API loop), Spike 3 (fine-tuning feasibility).
- **Days 3–5:** Phase 1 build — data loader consuming the **SimSat API**, mask definition (impoundment / retaining_wall / downstream / pond polygons for Jagersfontein), physical-diff module, gate. Sanity-check signals match Torres-Cruz findings.
- **Day 6:** if Spike 3 said fine-tuning is feasible — run the LoRA fine-tune on the curated Jagersfontein + adjacent TSF label set. Otherwise skip and go straight to Day 7.
- **Days 7–8:** Phase 2 build — LFM2 prompt pipeline (using fine-tuned weights if available), first backtest pass over the Jagersfontein archive via SimSat. Save structured JSON per pass.
- **Days 9–10:** Phase 3 — supervisory loop (Claude or GPT on the ground reviewing rolling windows). Phase 4 — counterfactual write-up with real dates. Add Brumadinho as secondary case using published Grebby ISBAS time series as SAR sidecar.
- **Days 11–12:** Phase 5 — demo video with **you on camera** (Demo/Communication 20% — rubric literally says "end-to-end demo of you explaining the whole thing"). Script the pitch around Torres-Cruz-validated signal / audit-trail framing / GISTM-auditor first-customer. Intercut with architecture diagram and live pipeline output. Use SimSat for the satellite-passing-overhead shot. Target 3–5 minutes unless Discord announces a hard cap.
- **Day 13:** submission assembly. README (assumptions, limits, buyer/line-item, fine-tuning results), PDF-report-from-JSON template, HuggingFace model card. **Fresh-clone test: `git clone <zip> /tmp/judge-sim && cd /tmp/judge-sim && docker compose up`** on a laptop profile with only Docker + standard tools installed. If any step fails, fix before submitting.
- **Day 14 (May 8):** buffer. Submit before 8:00 PM EDT (= 2026-05-09 02:00 CEST).

Keep `research/open-questions.md` open in a tab and reference the "underweighted aspects" section when writing the submission — those three framings (Torres-Cruz as validation, audit-trail over monitoring, GISTM as wedge) materially strengthen the pitch.

## 6. Dev environment checklist

Before the spikes, confirm on laptop:

- [ ] Python 3.11+ with a fresh virtualenv or conda env
- [ ] Docker + Docker Compose (for SimSat; also how the submission will ship per criterion 3)
- [ ] LFM2-VL access: HuggingFace (`LiquidAI/LFM2-VL-450M`, `LFM2-VL-1.6B`) and a runtime of your choice — llama.cpp / MLX / ONNX all rubric-acceptable. LEAP SDK is recommended by the hackathon but not mandated.
- [ ] HuggingFace write-enabled account (for publishing fine-tuned weights — fine-tune deliverables require **public** weights).
- [ ] A LoRA / QLoRA training framework (e.g., `peft` + `transformers`, or LEAP's native training path if it offers one).
- [ ] `pystac-client` + `odc-stac` for scratch debugging outside SimSat (Element 84 or Microsoft Planetary Computer). **Not for the final pipeline** — final pipeline goes through SimSat.
- [ ] `rasterio`, `numpy`, `matplotlib` / `rioxarray` for quick visualisation.
- [ ] Optional: `arosics` for co-registration if your initial check fails.
- [ ] Claude or OpenAI API key for the supervisory-loop role (Phase 3).
- [ ] Webcam + decent mic for the demo video (Day 11–12). Quiet room.
- [ ] Mapbox token only if you want demo-visual high-res overlays; not required.

SimSat bootstrap (when you want it):

```bash
git clone https://github.com/DPhi-Space/SimSat.git
cd SimSat
docker compose up
# Dashboard: http://localhost:8000
# Sim API:   http://localhost:9005
# Quick test: python scripts/api_test.py sentinel_multispectral
```

## 7. What NOT to do

- **Don't start Phase 1 build before the LEAP spike succeeds.** The sleeper risk is real.
- **Don't bypass SimSat in the final pipeline.** Criterion 1 of the rubric is "use of satellite imagery from the DPhi API." Scratch debugging against Element 84 STAC is fine, but the submission's pipeline must consume via SimSat's API.
- **Don't enter the General Track.** Liquid Track has +$5K cash for the same core work, and LFM2-VL is already our VLM.
- **Don't try to run a full InSAR processing chain from scratch.** Use published Grebby ISBAS time series as structured SAR input for Brumadinho. If you can't find the paper's data, a hand-transcribed version of their published time-series figure is acceptable for a hackathon — document the source in the writeup.
- **Don't reframe Brumadinho as the primary case.** Jagersfontein is the multispectral-load-bearing case. Keep Brumadinho as secondary/contrast.
- **Don't claim "we detect Brumadinho from Sentinel-2 alone."** It's false per the peer-reviewed record.
- **Don't create documentation files the submission doesn't need.** The submission wants a video, source zip, and a tight README with assumptions + limits. Everything else is internal.
- **Don't forget the fresh-clone run test.** Criterion 3 is "must run without debugging." On Day 13 (or earlier), clone the submission zip into a fresh directory on a clean machine profile and verify `docker compose up` (or equivalent) produces a working demo with no manual fix-ups.
- **Don't push to main.** All work continues on `claude/hackathon-planning-yOI79` until submission.

## 8. Key coordinates and dates (for quick reference)

| Item | Value |
|------|-------|
| Jagersfontein TSF | approx. `lat = -29.756, lon = 25.428` (confirm during Spike 2) |
| Jagersfontein failure | 2022-09-11 |
| Jagersfontein first Sentinel-2 erosion-gully signal (per Torres-Cruz) | ~2019-02 |
| Jagersfontein DWS directive (cease deposition) | 2020-12 |
| Jagersfontein DWS directive lifted | 2021-05 |
| Brumadinho Córrego do Feijão Dam I | approx. `lat = -20.119, lon = -44.121` (confirm) |
| Brumadinho failure | 2019-01-25 |
| Brumadinho ISBAS precursor (Grebby et al.) | acceleration from ~2018-10-21, ~40-day lead |
| Hackathon deadline | 2026-05-08 20:00 EDT |

## 9. Starting a new Claude Code session on laptop

If you want Claude Code to continue this work on laptop, point it at the repo and this file. A good first prompt:

> I'm continuing the SatDiff hackathon work from a mobile session. Read LAPTOP_HANDOFF.md and research/phase-0-go-no-go.md first, then help me run Spike 1 (the LEAP/LFM2-VL spike). I've got LEAP SDK access set up already.

That drops the session into the right context with minimal re-orientation.

## 10. One action to do on mobile before laptop

Join the **Liquid AI Discord** (`#ai-in-space-hackathon` channel) if you haven't already. The "Judging Criteria and Prizes document" referenced on the Luma page lives there. Download it, save it somewhere, and when you're on laptop copy it into `research/hackathon-rubric.md` so we can check our submission against the exact weightings. Also keep an eye for announcements / rule clarifications during the hackathon — judges sometimes post crucial details there that aren't on the Luma page.
