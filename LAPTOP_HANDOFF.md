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
- **Deadline:** 2026-05-08, 8:00 PM EDT
- **Remaining:** ~14 days
- Confirm bi-weekly prize structure on `hackathons.liquid.ai` — if there's an interim judging checkpoint you might want to aim at it with a minimum-viable submission and iterate.

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

### Spike 2 — Sentinel-2 archive data pull

**Goal:** confirm we can pull the Jagersfontein archive at the scale needed for the backtest.

**How to run:**
1. Pick one of these STAC endpoints:
   - `https://earth-search.aws.element84.com/v1` (what SimSat uses)
   - `https://planetarycomputer.microsoft.com/api/stac/v1` (Microsoft, often faster, requires SAS token signing via `planetary-computer` Python package)
2. Pull all Sentinel-2 L2A scenes for the Jagersfontein bbox, 2016-01-01 → 2022-10-01, with `eo:cloud_cover < 60`.
3. Expected count: hundreds of scenes after cloud filter. If you get <50 or >5000, something is wrong.
4. For a sanity check, load three scenes (known-clean 2016, pre-failure 2021, post-failure 2022-09-15) and render RGB + NDWI composites. Confirm visually that:
   - The impoundment is visible
   - The 2021 pond-at-wall is visible
   - The 2022-09 post-failure scar is visible

Budget: **a couple of hours** including a first-pass co-registration check.

### Spike outputs

Suggested: commit a notebook or short Python script to `spikes/leap-vlm-check.ipynb` and `spikes/archive-pull.ipynb` (or `.py`). Update `research/phase-0-go-no-go.md` with the spike results. If both pass, tick the "Path A confirmed post-spike" line; proceed to Phase 1.

## 5. If the spikes pass: Phase 1 execution plan

Budget the remaining ~12 days roughly as:

- **Days 1–2 (spike days):** above.
- **Days 3–5:** Phase 1 build — data loader, mask definition (impoundment / retaining_wall / downstream / pond polygons for Jagersfontein), physical-diff module, gate. Sanity-check signals match Torres-Cruz findings.
- **Days 6–7:** Phase 2 build — LFM2 prompt pipeline, first backtest pass over the Jagersfontein archive. Save structured JSON per pass.
- **Days 8–9:** Phase 3 — supervisory loop (Claude or GPT on the ground reviewing rolling windows). Phase 4 — counterfactual write-up with real dates. Add Brumadinho as secondary case using published Grebby ISBAS time series as SAR sidecar.
- **Days 10–11:** Phase 5 — demo video. Wire SimSat for the aesthetic (plan §363). Script + voiceover.
- **Days 12–13:** submission assembly. README, assumptions section, limits section, PDF-report-from-JSON template for the "workflow integration" last mile.
- **Day 14 (May 8):** buffer. Submit before 8:00 PM EDT.

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
- **Don't try to run a full InSAR processing chain from scratch.** Use published Grebby ISBAS time series as structured SAR input for Brumadinho. If you can't find the paper's data, a hand-transcribed version of their published time-series figure is acceptable for a hackathon — document the source in the writeup.
- **Don't reframe Brumadinho as the primary case.** Jagersfontein is the multispectral-load-bearing case. Keep Brumadinho as secondary/contrast.
- **Don't claim "we detect Brumadinho from Sentinel-2 alone."** It's false per the peer-reviewed record.
- **Don't create documentation files the submission doesn't need.** The submission wants a video, source zip, and a tight README with assumptions + limits. Everything else is internal.
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
