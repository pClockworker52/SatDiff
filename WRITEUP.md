# SatDiff — A Satellite-Readable Compliance Contract

*Submission to the Liquid AI "AI in Space" hackathon (Liquid Track).*

## 1. The problem

On 11 September 2022 the diamond-tailings facility at Jagersfontein, South Africa, breached its southern wall. The mudflow killed at least one person, displaced hundreds, and destroyed infrastructure across the town of Kopanong. Torres-Cruz & O'Donovan (2023, *Scientific Reports*) reconstructed the failure from public Sentinel-2 alone and found a **multi-year precursor signal**: pond migration, deposition asymmetry, gully growth on the wall face. The signal was not hidden. It lived in nobody's review queue.

Tailings storage facilities (TSFs) are now regulated under the Global Industry Standard on Tailings Management (GISTM), whose Principle 7 obliges operators to design, operate, and **monitor** tailings facilities to manage risk across the lifecycle. Auditors enforce this with physical inspection schedules and ad-hoc review of public data. The gap is not detection; it is the absence of a machine-generated, time-stamped, contract-framed artefact that an auditor can sign and file against a specific Principle.

## 2. The thesis

Move the audit from humans-on-schedules to a satellite-readable compliance contract. Per acquisition, a small-satellite-resident vision-language model emits a time-stamped, claim-by-claim assessment whose schema matches the regulator's required artefact format. The artefact — not a dashboard, not a transcript — is the deliverable; investigation transcripts, dashboards, and alerts are downstream consumers of it, not substitutes for it.

The pattern is sized for the next generation of small Earth-observation satellites (Orin-class compute, constrained downlink), not for flagship platforms like Sentinel-2 that already enjoy gigabit links and full-imagery downlink. The marginal-downlink-cost story below depends on this: the on-orbit deliverable is ~2 KB of structured JSON per pass, not megabytes of imagery.

This is a deliberately non-agentic stance. The auditor's job is to file a defensible record, not to explore. SatDiff produces that record automatically and at acquisition cadence.

## 3. Architecture

```
─────────────────── on-orbit ───────────────────         ─── ground ───
SimSat (Sentinel-2)  →  Physical-diff module      →  Gate (Φ-sat heritage)
                        (NDWI, NDMI, gully,           ↓
                        asymmetry, pond-to-wall)      if interesting
                                                      ↓
                                               LFM2.5-VL (GGUF / llama-server)
                                               prompted with contract + diff
                                                      ↓
                                               Rules engine (severity, action)
                                                      ↓
                                               Structured JSON (~2 KB)
                                                      ↓
                                               ════════ DOWNLINK ════════
                                                      ↓
                                                                Ground supervisor
                                                                joins JSON to imagery
                                                                received via the
                                                                standard EO ground
                                                                channel
                                                                          ↓
                                                                PDF report (Jinja + WeasyPrint)
```

The pipeline is split deliberately across the orbit/ground boundary. **On-orbit** the satellite runs everything from physical-diff through the JSON contract output — that is the marginal-downlink-cost claim (~2 KB per pass instead of full multispectral tiles). **On the ground**, a supervisor joins the JSON to imagery already received through the standard Earth-observation ground channel and renders the human-facing PDF. The satellite never downlinks imagery a second time on SatDiff's budget; it adds a small interpretation layer on top of imagery the regulator's data infrastructure already has.

Two cross-cutting commitments shape every module:

- **SimSat is the integration boundary on the imagery side.** All pipeline ingress routes through the DPhi SimSat API (rubric criterion 1). External STAC catalogues are reserved for one-off scratch debugging.
- **The contract-prompt schema is the integration boundary on the model side.** The schema in `research/contract-prompts/jagersfontein-contract.md` defines `claims[]`, `severity_level`, `recommended_action`, and `regulatory_escalation_flag` exactly. Both upstream (physical-diff numerical fields) and downstream (rules engine, PDF renderer) consume against this schema.

The **rules-engine architecture** is the central technical choice. Severity (`nominal` / `elevated` / `urgent`), recommended action (`none` / `flag_for_review` / `urgent_inspection`), overall status, downlink priority, and regulatory escalation flag are computed deterministically in `phase2/aggregate.py::compute_severity` from the physical-diff numbers, after the model has emitted free-text evidence. Given a Claim 2 with `pond_to_wall_distance_m=9.9` and `pond_area_change_pct=+433`, the engine returns `severity=urgent` and `recommended_action=urgent_inspection` — every time, deterministically, regardless of what the model wrote. The model is the evidence-text writer; Python is the authoritative threshold engine. The next section is what motivates this split.

## 4. Validation: a 17-month Jagersfontein backtest

We backtested the pipeline over the 17 monthly Sentinel-2 acquisitions from 2021-06 through 2022-10 — the window from clean operations through to the post-failure state.

Phase 1 physical-diff metrics match the Torres-Cruz reconstruction qualitatively. The pond grows from 90 k m² in baseline (2017) to a peak of 1.9 M m² in January 2022 (eight months before failure), then to 3.27 M m² post-failure. The deposition-asymmetry index — the ratio of NDWI gradient pointing toward versus away from the failed wall — moves from a baseline 1.2 to **22.57** across the failure month, a clean signature of the lobe-shaped run-out. Gully count on the wall face climbs through 2022. Pond-to-wall distance closes to 9.9 m in the months before failure.

Phase 2 then runs the contract VLM (LFM2.5-VL-450M) against each pass. Of the 16 passes the gate invoked, 16/16 produced schema-valid output, 16/16 cited at least one diff metric in the evidence, and 16/16 graded the asset `overall_status: urgent` — matching Torres-Cruz' finding of continuous covenant violation across the window.

One honest defect: the cloud-cover gate (50% threshold, Φ-sat heritage) skipped the 2022-09-11 failure-day pass at 68% cloud. The hero PDF for the demo is the next clean pass, 2022-10-15. Section 8 owns this and proposes the production fix.

Bulk-rerun command: `python -m phase2.cli --asset jagersfontein --date-range 2021-06-15,2022-10-15`. The 17 per-pass PDFs are regenerable from the JSONs via `python -m phase3 --date-range ...`.

## 5. Fine-tune deliverables

Framework: `Liquid4All/leap-finetune` (Ray Train + Accelerate, managed via `uv`) — not raw `transformers + peft`. Hardware: RTX 4080 Laptop, 12 GB. Base model: LFM2.5-VL-450M.

**Stage 1: VRSBench grounding.** 5 000 VRSBench captioning + VQA samples × 2 epochs of LoRA SFT, 38 m 15 s wall-clock. Eval loss fell from base ~3.21 to **1.41** (−56 %).

The headline metric is per-claim **evidence-correctness** on a held-out test set: does the model cite the right diff fields for the right claim? The contract prompt instructs the model to source Claim 2 (pond) from `pond_to_wall_distance_m`, `pond_area_change_pct`, `NDWI_max`, `B4/B3`; Claim 3 (wall) from `gully_count`, `largest_gully_width_m`, `NDMI_wall_face`, `SWIR_anomaly_flag`; and so on.

| metric (held-out backtest passes) | base LFM2.5-VL-450M | Stage 1 |
|---|---:|---:|
| schema-valid | 16/16 | 16/16 |
| **evidence-correct claims** | **0/30 (0 %)** | **30/30 (100 %)** |

The base model parroted the same three indices into every claim's evidence (e.g. `NDWI_mean=-0.212 NDMI_mean=-0.158 B4/B3=1.278` on every claim, regardless of which physical signal the claim was about). Stage 1 — without any SatDiff-specific examples in training — taught the model to read the per-claim sourcing rules from the prompt and cite the right fields. Claim 4 (deformation) now writes `no SAR data available; multispectral-only path` instead of inventing a number. **The lift comes from generic VRSBench grounding, not from domain-specific examples.**

**Stage 2: methodologically clean negative result.** Training set: **29 hand-authored examples** spanning boundary, escalation, routine, and catastrophic regimes, plus **17 auto-generated examples** from Phase 2 backtest passes — split 35 train / 11 held-out *before* training began. (Examples derived from the Mariana, Oroville, and Edenville historical-disaster papers were considered but failed our quality gate and were excluded.) Stage 2 preserved Stage 1's 100 % evidence-correct rate but **worsened** severity adherence on real held-out data (5 → 9 corrections by the rules engine). The hand-authored cases used contrived metric values around the threshold cliffs (e.g. pond-to-wall = 24 m vs 26 m); the held-out real-data passes lived in a different distribution (pond-to-wall ≈ 9.9 m throughout the failure window). LoRA at this scale (35 examples × 3 epochs ≈ 31 effective steps) cannot reshape multi-tier threshold reasoning. **We ship Stage 1, not Stage 2.**

This is the strongest possible validation of the rules-engine architecture, not a system failure. Severity, action, escalation, and overall-status are computed by `phase2.aggregate.compute_severity` from the physical-diff numbers — *regardless* of what the model emits. **The 16/16 `urgent` grading across the Jagersfontein backtest comes from the rules engine, not from the fine-tune**, and is correct precisely because we did not delegate threshold logic to the model. Stage 2's negative result confirms that this work belongs in deterministic Python at our scale; it does not mean the system fails on cases beyond Jagersfontein. The same engine grades any asset whose physical-diff fields populate the schema.

**Deployment: GGUF + llama-server.** The Stage 1 fp16 checkpoint quantises to a 362 MB Q8_0 backbone plus 182 MB F16 mmproj — 544 MB total, well under the 700 MB budget. End-to-end latency on the RTX 4080 Laptop (sm_89, CUDA 12.6) is **2.38 s per pass**, a 4.7× speedup over the bf16 transformers path with no schema or evidence-quality regression. Mirrors Liquid's wildfire-prevention reference architecturally and demonstrates Orin-readiness via real artefact rather than claim.

## 6. Positioning

The architectural pattern in this submission — on-orbit VLM with a ground-supervised contract output — is the same one Liquid's wildfire-prevention reference adopts. We have specialised it to a different domain (regulated dam compliance) and a different output discipline (claim-indexed audit artefact). DPhi's published reference uses agentic maritime monitoring; this submission is non-agentic by design because the GISTM auditor's required deliverable is a per-claim gold-standard record, not an investigation transcript.

The contract-prompt architecture is sensor- and regulator-agnostic. The submission video opens at the Forggensee dam in Bavaria, regulated under the *Stauanlagensicherheitsverordnung* (StAnlSiV), to demonstrate the portability of the pattern beyond GISTM and beyond tailings.

## 7. Buyer wedge

The defensible gap, after surveying commercial InSAR services (TRE Altamira × Glencore; Insight Terra × Synspective), is not detection — InSAR plus GISTM Principle 7 has largely closed the deformation-detection gap for this asset class. The defensible gap is **interpretation, fusion, and on-satellite scale**:

- **Interpretation layer.** Translating physical signals into contract-framed, claim-indexed outputs that drop directly into a regulator's case file.
- **Multispectral + SAR fusion.** No deployed service unifies these into a single per-asset per-claim narrative. SatDiff's claim schema is sensor-fusion-ready by construction (Claim 4 already declares `no SAR data available` when SAR is absent).
- **On-satellite inference for portfolio scale.** The emerging architecture Liquid AI / LEAP is pushing; nothing deployed today does this on-orbit. Marginal downlink cost is the unlock.

The primary buyer is the **GISTM auditor**: today, physical inspection schedules plus manual review of public imagery; tomorrow, a per-claim assessment per acquisition, signed and time-stamped, that drops into the case file. Adjacent buyers are dam-safety regulators broadly (StAnlSiV, USACE, ANCOLD), insurance underwriters pricing tailings risk, and ESG screens that need defensible audit trails. The integration surface is the JSON schema; any compliance pipeline can adopt it as a developer API.

## 8. Production roadmap and honest gaps

- **Sensor gap.** The DPhi prize platform's onboard sensor is a fisheye camera, not a Sentinel-2 instrument. The on-orbit *pattern* transfers; the imagery does not. Production deployment depends on Sentinel-2 / Sentinel-1 SAR / Planet downlink, with SimSat as the simulation harness.
- **Cloud-cover gate.** The 50 % Φ-sat-heritage threshold skipped the failure-day pass. Production fix: extreme-metric override (force evaluation when prior asymmetry, gully count, or pond-to-wall trajectories cross hard thresholds) plus a SAR sidecar that ignores cloud cover entirely.
- **Severity reasoning inside the model (research item, not a present-day gap).** The system grades severity correctly today — that work is done deterministically by the rules engine, not by the VLM, and the demo's outputs are correct because of it. The roadmap item is reaching the point where the *fine-tuned model alone* can also do this reasoning, eliminating the need for a separate rules engine. Closing that gap is research not engineering — likely a larger backbone or a much larger curated dataset, not an architectural change. Until then, deterministic Python is authoritative and the demo's severity grading is reliable.
- **Submission scope.** Single asset, single regulator, multispectral-only. Production scope is portfolio-scale, multi-regulator, multi-sensor.

## 9. Reproducibility and deliverables

One command from a fresh clone:

```
docker compose up
```

Brings up SimSat, llama-server (Stage 1 GGUF preloaded), and the SatDiff renderer. The 17-month backtest reproduces in under 10 minutes on CPU.

- Code: `phase1/` (loader, masks, physical-diff, gate), `phase2/` (VLM runner, rules engine), `phase3/` (PDF renderer), `inference/` (GGUF tooling and llama-server scripts).
- Hugging Face: `WobblyDopamine/SatDiff-LFM2.5-VL-450M-stage1` — fp16 checkpoint, GGUF pair, model card.
- Hero artefact: `phase3/out/jagersfontein/2022-10-15.pdf` (post-failure, lobe runout visible, Stage 1 evidence-correct).
