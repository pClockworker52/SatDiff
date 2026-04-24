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

## 3b. Track selection and judging — confirmed from the Luma page

**Two tracks. We should enter the Liquid Track.**

| Track | Prize | Constraint |
|-------|-------|------------|
| **Liquid Track** (recommended) | ~$15K space-server credits + **$5K cash** | Must use LFM2-VL or LFM2.5-VL. **Fine-tuning on domain-specific satellite data is strongly encouraged.** |
| General AI Track | ~$15K space-server credits | Any AI approach. Preference for solutions designed for space-compute realities (limited downlink, continuous streams, on-board inference). |

Liquid Track fits SatDiff directly and adds $5K cash. Fine-tuning becomes a concrete new deliverable (see §4 and §5).

**Four judging criteria (treat as the rubric):**
1. **Use of satellite imagery from the DPhi API** (= SimSat) — explicit. Our pipeline's imagery input path **must** go through SimSat's API for the submission to score on criterion 1. We cannot just hit Element 84 STAC directly in the final submission.
2. **Innovation and problem-solution fit** — SatDiff's contract-framed VLM interpretation layer is our innovation. The Jagersfontein counterfactual is the fit.
3. **Technical implementation — "your app must run without debugging"** — Docker-compose-up or equivalent must Just Work for the judges. No local paths, no API keys they don't have, no manual fix-up steps.
4. **Demo walk-through end-to-end.** Video + live walkthrough both carry weight.

We should fetch the "Judging Criteria and Prizes document" from the Discord server and log it to `research/` when you're on laptop — it likely has weightings.

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

### Spike 3 (new, Liquid-track specific) — LFM2-VL fine-tuning feasibility

**Goal:** determine whether we can realistically fine-tune LFM2-VL-450M (or the 1.6B) on a tiny curated tailings-dam image set within the remaining time, because the Liquid Track "strongly encourages" fine-tuning on domain-specific satellite data.

**How to run:**
1. Check LEAP docs for the fine-tuning path. LFM2 is described as supporting LoRA-style adaptation; confirm this for the VL variant.
2. Curate a tiny labelled set (say 20–50 examples) of Sentinel-2 patches labelled with free-form descriptions like *"impoundment with pond against retaining wall; erosion gullies visible on northern wall"* — use the Torres-Cruz paper's findings as the label style. Jagersfontein over 2018–2022 plus 2–3 other TSFs from public imagery gives us diversity.
3. Run a short LoRA fine-tune. If wall-clock + compute cost is tolerable on laptop (i.e., a few hours not days), fine-tuning is a viable deliverable.

**Decision:** if LFM2-VL fine-tuning is feasible in a day or two, **do it** — it is a scoring differentiator for the Liquid Track. If infeasible (too slow, doesn't converge, breaks structured output), drop it and lean harder on prompt engineering; the submission writeup should acknowledge that we left fine-tuning as future work with the dataset curated.

Budget: **half a day** for the feasibility check; **one extra day** later for a real fine-tune if feasible.

### Spike outputs

Suggested: commit a notebook or short Python script to `spikes/leap-vlm-check.ipynb` and `spikes/archive-pull.ipynb` (or `.py`). Update `research/phase-0-go-no-go.md` with the spike results. If both pass, tick the "Path A confirmed post-spike" line; proceed to Phase 1.

## 5. If the spikes pass: Phase 1 execution plan

Budget the remaining ~14 days roughly as:

- **Days 1–2 (spike days):** Spike 1 (LEAP/LFM2-VL on EO imagery), Spike 2 (SimSat API loop), Spike 3 (fine-tuning feasibility).
- **Days 3–5:** Phase 1 build — data loader consuming the **SimSat API**, mask definition (impoundment / retaining_wall / downstream / pond polygons for Jagersfontein), physical-diff module, gate. Sanity-check signals match Torres-Cruz findings.
- **Day 6:** if Spike 3 said fine-tuning is feasible — run the LoRA fine-tune on the curated Jagersfontein + adjacent TSF label set. Otherwise skip and go straight to Day 7.
- **Days 7–8:** Phase 2 build — LFM2 prompt pipeline (using fine-tuned weights if available), first backtest pass over the Jagersfontein archive via SimSat. Save structured JSON per pass.
- **Days 9–10:** Phase 3 — supervisory loop (Claude or GPT on the ground reviewing rolling windows). Phase 4 — counterfactual write-up with real dates. Add Brumadinho as secondary case using published Grebby ISBAS time series as SAR sidecar.
- **Days 11–12:** Phase 5 — demo video. Wire SimSat for the aesthetic (plan §363) — this is also criterion 1 of the rubric, so it doubles as scoring. Script + voiceover. Make sure the submission zip runs docker-compose-up clean on a fresh machine (criterion 3).
- **Day 13:** submission assembly. README, assumptions section, limits section, PDF-report-from-JSON template for the "workflow integration" last mile. **Fresh-clone test of the zip** — judge perspective.
- **Day 14 (May 8):** buffer. Submit before 8:00 PM EDT (= 2026-05-09 02:00 CEST).

Keep `research/open-questions.md` open in a tab and reference the "underweighted aspects" section when writing the submission — those three framings (Torres-Cruz as validation, audit-trail over monitoring, GISTM as wedge) materially strengthen the pitch.

## 6. Dev environment checklist

Before the spikes, confirm on laptop:

- [ ] Python 3.11+ with a fresh virtualenv or conda env
- [ ] Docker + Docker Compose (for SimSat; optional for spike 1)
- [ ] LEAP SDK installed and `from leap import ...` importable (or whatever the actual API is — check `liquid.ai` docs)
- [ ] Either `planetary-computer` + `pystac-client` + `odc-stac` (Microsoft PC route) or just `pystac-client` + `odc-stac` + AWS creds disabled (Element 84 is public)
- [ ] `rasterio`, `numpy`, `matplotlib` / `rioxarray` for quick visualisation
- [ ] Optional: `arosics` for co-registration if your initial check fails
- [ ] Claude API or OpenAI API key for the supervisory-loop role (Phase 3)
- [ ] Mapbox token only if you want the demo-visual high-res overlays; not required for the backtest

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
