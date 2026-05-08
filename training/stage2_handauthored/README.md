# Stage 2 — hand-authored examples

This directory holds the manually-curated examples that teach the LFM2.5-VL-450M model the **multi-tier severity rules**, **routine-vs-distress discrimination across multiple assets**, and **catastrophic-failure recognition beyond Jagersfontein**. Stage 2 fine-tuning resumes from the Stage 1 (VRSBench-mix) checkpoint and trains over these JSONLs.

Stage 2 was a methodologically clean **negative result** — see `WRITEUP.md` for why the Stage 1 checkpoint ships and Stage 2 does not.

## Three tiers, twelve assets

Each example is one line in a `<tier>_<asset>_<tag>.jsonl` file in this directory.

### Tier 1 — Jagersfontein severity-tier teaching (~20 examples)

All authored against existing PNGs in `/home/peter/datasets/satdiff_stage2/images/jagersfontein/`.

- **Boundary-of-tier (~10):** synthetic diffs at threshold cliffs.
  - `pond_to_wall_distance_m=24.5` → urgent; `=25.5` → elevated.
  - `gully_count=9` → elevated; `=10` → urgent.
  - `pond_area_change_pct=+99` → elevated; `+101` → elevated; `+501` → urgent.
  - `deposition_asymmetry_index=1.4` → nominal; `=1.6` → elevated; `=5.1` → urgent.
- **Confabulation override (~5):** Stage A says "no visible gullies" but the diff shows `gully_count=14`. Gold cites the number.
- **Multi-claim escalation chain (~5):** Claim 2 urgent → Claim 5 must escalate via the rules-engine cascade.

### Tier 2 — cross-asset routine / negative examples (~7-10 examples)

Routine operational change that should produce `overall_status="nominal"`. Direct counter to "everything is urgent." Four assets:

| asset | grade | paper | scenario |
|---|:-:|---|---|
| aswan | A | Miky 2019 | Seasonal cycle low↔high water. |
| three_gorges | A | Wang 2011 | Cyclic concrete-dam mm-scale routine. |
| hoover_mead | A | Tseng 2016 | Multi-decadal optical decline. |
| kariba | **B** | | Basin-wide LULC correlation (lower-density paper). |

### Tier 3 — cross-asset catastrophic / distress examples (~8-12 examples)

Catastrophic / precursor signatures DIFFERENT from Jagersfontein. Seven assets:

| asset | grade | paper | scenario |
|---|:-:|---|---|
| brumadinho | A | Syifa 2019 | Sudden tailings runout into Paraopeba River. |
| mariana_fundao | A | Da Silva Junior 2018 | TSF historical precedent (vegetation displacement, sediment plume). |
| toddbrook | A | Heidarzadeh 2022 | Concrete spillway with vegetation → seepage. |
| nova_kakhovka | A | Monti 2024 | Reservoir destruction + 490 km² downstream flooding. |
| derna | A | Shults 2025 | Cascading embankment failure + 600+ buildings collapsed. |
| edenville (optical-only) | **B** | Thomas 2024 | SMI saturation precursor (drop the SAR side). |
| oroville | **B** | Koskinas 2019 | Concrete spillway hydraulic erosion. |

**Hard exclusions** — failed quality gate Q2 (SAR-only):
- Mosul, Datengxia, Brumadinho-pre, Edenville-SAR-side. SatDiff is optical-only.

## Quality gate (the user's caveat)

Before authoring any cross-asset example:

- **Q1.** Does the source paper provide ≥2 concrete quantitative descriptors that map cleanly onto SatDiff diff fields without forcing? ("13.02% vegetation loss" → `footprint_change_pct`. "68.57% pond reduction" → `pond_area_change_pct`.)
- **Q2.** Does the failure / routine signature live in the optical+multispectral domain? (SAR-only → fail.)

A-grade assets pass both. B-grade assets are marginal on one — author 1 example, decide on the spot whether to keep. Drops go to `skipped.md` with one-line reason.

## Authoring workflow (per example)

The `training/author_helper.py` script handles all of the messages-format plumbing, prompt assembly, and image-path bookkeeping. You only edit ONE file per example — a JSON staging file in `/tmp/` with placeholders for the inputs you need to fill in.

### Tier 1 — clone an existing pass and tweak it

```bash
UV_PROJECT_ENVIRONMENT=/home/peter/.satdiff-venvs/spikes \
  uv run --directory /mnt/c/Users/peter/SatDiff/spikes \
  python /mnt/c/Users/peter/SatDiff/training/author_helper.py \
    --asset jagersfontein --tier tier1 --tag boundary_p2w_24_5 \
    --scaffold-from-pass 2022-01-15
```

The helper:
1. Clones the existing Phase-2 record for 2022-01-15 (its diff, Stage A text, and gold JSON).
2. Stages the editable file at `/tmp/satdiff_author_tier1_jagersfontein_boundary_p2w_24_5.json`.
3. Opens it in `$EDITOR`. **Edit the diff fields you want to test (e.g. `pond.pond_to_wall_distance_m: 24.5`) and re-derive the gold severities.**
4. On save+exit, validates the gold JSON against `spikes/schema.json` and appends one JSONL line to `tier1_jagersfontein_boundary_p2w_24_5.jsonl`.

### Tier 2/3 — fresh cross-asset scaffold

```bash
UV_PROJECT_ENVIRONMENT=/home/peter/.satdiff-venvs/spikes \
  uv run --directory /mnt/c/Users/peter/SatDiff/spikes \
  python /mnt/c/Users/peter/SatDiff/training/author_helper.py \
    --asset aswan --tier tier2 --tag seasonal_drawdown \
    --scaffold-blank --baseline-date 2018-01-15 --current-date 2018-07-15
```

The helper:
1. Fetches imagery via `phase1.loader.load_pass` for both dates (cached if previously pulled).
2. Renders the 4 PNGs to `/home/peter/datasets/satdiff_stage2/images/aswan/`.
3. Stages a blank-template editable file with TODO markers for `baseline.per_mask`, `diff.*`, `stage_a_text`, and `gold_assistant_json`.
4. Opens it in `$EDITOR`. **Fill in paper-derived numbers, write a 2-paragraph Stage A description grounded in the visible imagery, author the gold assistant JSON.**
5. On save+exit, builds the Stage B prompt from your edits, validates the gold JSON, and appends one JSONL line to `tier2_aswan_seasonal_drawdown.jsonl`.

If imagery fetch fails (SimSat down, archive miss), the helper prints an actionable error. Run `training/stage2_probe_simsat.py` first to confirm availability.

## Per-example author time goal

**5-10 minutes**, not "wrestle with messages-format JSON for an hour."

## Validating the dataset before training

Run `training/build_stage2_dataset.py` (without `--auto-only`) — it concatenates the auto-generated Phase 2 examples with everything in this directory and writes the combined JSONL at `/home/peter/datasets/satdiff_stage2/satdiff_stage2.jsonl`. Then either:

```bash
# Smoke fine-tune with limit:5
UV_PROJECT_ENVIRONMENT=/home/peter/.satdiff-venvs/leap-finetune \
  uv run --directory /home/peter/leap-finetune leap-finetune \
  /mnt/c/Users/peter/SatDiff/training/satdiff_stage2.yaml --override dataset.limit=5
```

… or just kick off the full Stage 2 run (~30-60 min on RTX 4080, resuming from the Stage 1 checkpoint).

## Pre-flight: the SimSat availability probe

`training/stage2_probe_simsat.py` queries SimSat's metadata endpoint for each candidate (asset, baseline_date, current_date). Run it once before authoring; it writes:

- `availability_probe.json` — per-pair record of `image_available`, cloud cover, sentinel datetime + source.
- An entry to `skipped.md` for any pair that fails the cloud ceiling (50%) or returns no image.

Use the probe output to substitute alternative dates (e.g. ±30 days) for any failing pair before authoring.

## Priority order (the stop-anywhere sequence)

If you run out of time, finish in this order:

1. Tier 1 boundary cases (~10 ex). **Always finish first** — these are why Stage 2 exists.
2. Tier 2 Aswan + Three Gorges. Defensible Stage 2 after this point.
3. Tier 1 confabulation + escalation, then Tier 2 Hoover + Tier 3 Brumadinho + Mariana.
4. Tier 3 Toddbrook + Nova Kakhovka + Derna.
5. B-grade marginals: Tier 2 Kariba, Tier 3 Edenville-optical, Tier 3 Oroville.

Time markers (rough):
- After 2 h: Tier 1 boundary done. Useful but minimal.
- After 4 h: + Aswan + TGD. Defensible.
- After 6 h: + Tier 1 confab/escalation, Hoover, Brumadinho, Mariana. Comfortable.
- After 8-10 h: + Tier 3 A-grade variety. Comprehensive.
- B-grades only if everything above is done.
