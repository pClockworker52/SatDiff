# Satellite Architecture — What We're Assuming and Emulating

**Purpose:** establish the compute, bandwidth, and sensor assumptions behind SatDiff's "on-satellite VLM inference" claim. Answer the user's question: *are satellites running COBOL on a Pentium III, or something else, and what's realistic to emulate?*

TL;DR: modern Earth-observation satellites run **Linux on AMD Ryzen / Zynq UltraScale+ / ARM-class SoCs with Myriad-X or Hailo-8 AI accelerators**, delivering **1–5 TOPS in 30–50 W**. A VLM like **LFM2.5-VL-450M** (released April 2026) has **sub-250 ms edge inference** and is the first VLM size class credibly targetable at that compute envelope. **No VLM has flown in orbit yet** — SatDiff's architecture is at the frontier, not behind it.

---

## 1. Current state of on-satellite compute

### 1.1 The flight-heritage stack (what's actually flying or flown)

| Platform | Compute | Notable missions | Notes |
|----------|---------|------------------|-------|
| **NVIDIA Jetson Orin NX 16GB** ← **hackathon prize platform** | 100 TOPS sparse / ~50 TOPS dense INT8; 1024-core Ampere GPU + 32 Tensor Cores; 8-core Arm Cortex-A78AE; 16 GB LPDDR5; ~15–25 W | DPhi Space flight platform (hackathon prize offers 5 GPU-hours); also Loft Orbital YAM-9 class | **This is the actual target hardware for the hackathon prize deployment.** More headroom than iX10/Leopard for VLM inference. |
| **Unibap SpaceCloud iX10** | AMD Ryzen V1000 + 8× Radeon GPU + Myriad X (iX10-101) or Hailo-8 (iX10-102); 24 GB DDR4 ECC; 2× 4 TB NVMe; <40 W | D-Orbit, Loft Orbital, Dragonfly | Commercial edge-AI flight computer. Runs Linux. Peer to Orin for EO smallsats. |
| **KP Labs Leopard DPU** | Zynq UltraScale+ ZU9EG (FPGA + ARM); 16 GB DDR4; 2× 240 GB SSD; ~3 TOPS; cold-redundant nodes + TMR radiation-hard supervisor | Intuition-1 (launched Nov 2023, operating) | First commercial AI DPU with flight heritage for hyperspectral; 192-band sensor onboard. Does CNN cloud detection + segmentation on-orbit. |
| **Intel Movidius Myriad 2 VPU** | Eyes-of-Things (EoT) board; ~1 TFLOPS; watts-level | Φ-sat-1 (2020), Φ-sat-2 (2024) | First on-board DNN inference in orbit (cloud detection, saved ~30% bandwidth). Used for Φ-sat-2's four AI apps. |
| **Loft Orbital "Ultimate Edge" / Virtual Missions** | CPU + GPU compute nodes (specific SKUs not public); software-defined payload bus | YAM-6, YAM-9 (in orbit) | Customer-iterable AI models in orbit. Most production-realistic analogue to SatDiff's "supervisory-loop prompt updates". |
| **OPS-SAT (ESA, 2019–2024)** | ARM Cortex-A9 based, Linux; 1 GB RAM | Reentered May 2024; hosted SaaSy ML, anomaly detection, super-resolution | Flying laboratory for ML experimentation — pattern SatDiff follows. |
| **Legacy radiation-hardened** | BAE RAD750 (PowerPC, 200 MHz, ~400 MIPS, ~10 W) | Mars 2020 Perseverance, JWST, Curiosity | **This is the "Pentium III" stereotype**, and it is real for deep-space missions. Not representative of modern Earth-observation smallsats. |

**Takeaway for SatDiff:** the hackathon prize explicitly deploys on **NVIDIA Orin 16GB** (100 TOPS sparse, 16 GB LPDDR5, ~25 W). LFM2-VL-450M runs sub-250ms on edge hardware; LFM2-VL-1.6B comfortably fits; LFM2-VL-3B is plausible. The submission writeup should target Orin as the production hardware spec while keeping Unibap iX10 / Leopard as peer alternatives for non-DPhi flight platforms. Orin is also confirmed by Loft Orbital's YAM-9 as a deployed space-edge platform, so the claim is not DPhi-specific.

The hackathon's prize package also allocates **5 MB upload / 10 MB download** per winner month on the satellite. A 2 KB per-pass JSON report scales to 1000 passes in 2 MB, well inside the 10 MB download budget — this **exactly validates the compact-report framing** §4 below. Use these numbers verbatim in the submission writeup.

### 1.2 What "radiation tolerant" actually means at this class

Modern EO edge-AI hardware uses **rad-tolerant COTS with mitigation** rather than full rad-hard silicon:
- ECC memory, TMR (triple modular redundancy) in supervisor subsystems.
- Cold-redundant dual processing nodes (Leopard) so a single-event upset can fail over.
- Aluminium enclosures (5 mm on iX10) for shielding.
- Watchdog + reset-on-SEU with on-board persistent checkpointing.

The implication for SatDiff's architecture: inference need not be deterministic across a single SEU. The supervisory-loop pattern — on-board reports get reviewed on the ground periodically — is already the right design for a rad-tolerant stack.

## 2. On-board ML precedents — what's been flown

| Mission | Year | What it did | Precedent for SatDiff |
|---------|------|------------|------------------------|
| **Φ-sat-1** (ESA, Ubotica, Myriad 2) | 2020 | CNN cloud-detection discards cloudy scenes → ~30% bandwidth saving | **First on-board DNN inference in orbit.** Established the "gate model" pattern — SatDiff's Phase 2.3 "gate" is a direct descendant. |
| **OPS-SAT** (ESA) | 2019–2024 | Anomaly detection, super-resolution, ML SaaS (SaaSy ML); hosted >100 experiments | Established that **re-uploadable ML models in orbit** is operationally feasible — SatDiff's supervisory loop relies on this capability. |
| **Intuition-1** (KP Labs, Leopard DPU) | 2023– | 192-band hyperspectral + 3 TOPS Leopard; on-board cloud detection, land-cover segmentation, hyperspectral classification | **Highest-TOPS on-board AI flown to date** for Earth observation. Commercial, still operating. |
| **Φ-sat-2** (ESA, Open Cosmos, Ubotica) | Aug 2024– | Four AI apps: Sat2Map, cloud detection, vessel detection, deep image compression. Open-source NanoSat MO Framework (NMF) manages uploads/updates | First mission designed around an **AI-app framework** rather than a single baked-in model. Operational architectural precedent for SatDiff. |
| **Loft Orbital YAM-6, YAM-9** | 2022–2024 | Software-defined payloads, customer-iterable ML in orbit | Commercial precedent for the **"upload new prompt / new model" supervisory loop** SatDiff requires. |

**Crucially: no vision-language model has been flown in orbit yet.** The closest published work is Wang et al. 2025 *"A Satellite-Ground Synergistic Large Vision-Language Model System for Earth Observation"* (arXiv 2507.05731) — a paper proposing the architecture, not a flown mission. If SatDiff ships as a working prototype with LFM2-VL end-to-end, it sits at the frontier of demonstrated capability. This is a meaningful submission framing: *"we demonstrate the first VLM-driven on-satellite insurance-monitoring pipeline — an architecture that no mission has yet flown."*

## 3. LFM2 / LFM2-VL in the on-satellite context

### 3.1 The model family (as of April 2026)
- **LFM2-VL-450M** (released April 2026): 450M parameters, SigLIP2 NaFlex vision encoder, 512×512 native resolution with patching for larger images. **Sub-250 ms edge inference.** Bounding-box prediction, multilingual.
- **LFM2-VL-1.6B**: larger vision tower + LFM2-1.2B backbone. Still edge-targeted; ~2× slower than 450M.
- **LFM2-VL-3B**: SigLIP2 encoder + LFM2-2.6B backbone. On-edge but closer to the limit.
- All variants 2× faster on GPU vs comparable VLMs; designed for resource-constrained deployment.
- LFM2 Technical Report on arXiv: 2511.23404 (Nov 2025).

### 3.2 What fits on what

| Hardware | Realistic LFM2-VL variant | Latency budget |
|----------|---------------------------|----------------|
| **NVIDIA Orin 16GB (hackathon prize platform)** | **LFM2-VL-1.6B comfortably; 3B plausible** | **<250 ms per pass (matching published LFM2.5-VL-450M benchmarks; 1.6B within sub-second)** |
| Unibap iX10-102 (Hailo-8 + Ryzen) | LFM2-VL-1.6B comfortably; 3B plausible | <1 s per pass |
| KP Labs Leopard (Zynq UltraScale+, 3 TOPS) | LFM2-VL-450M likely; 1.6B needs careful quantization | 1–3 s per pass |
| Myriad X / Myriad 2 (Φ-sat class) | LFM2-VL-450M only, quantized | Several seconds |

SatDiff's assumption: **target LFM2-VL-1.6B on Orin 16GB** (the hackathon's actual in-orbit deployment target) as the primary, with LFM2-VL-450M as the fallback for more constrained platforms (Leopard, Myriad). The model exists today (April 2026), the hardware is flying today (Loft Orbital YAM-9, DPhi Space), they have not been flown together — which is exactly what a hackathon submission argues *should* be flown.

### 3.3 Implications for the prompt design
- 512×512 native resolution is generous for our use case — Sentinel-2 10-m imagery of the Jagersfontein TSF fits in a ~500×500 patch at ~5 km ground swath.
- Context length is modest; prior-report history needs to be bounded to the last N passes (already in Phase 2.1 design).
- Structured JSON output at 1–2 KB per pass is well within model capability and downlink budget.

## 4. Downlink economics — the actual numbers

| Satellite class | Downlink rate | Daily data | Notes |
|-----------------|---------------|-----------|-------|
| Sentinel-2 (X-band) | 560 Mbps | ~1.6 TB/day/constellation (two-sat, raw compressed) | 290-km swath, 13 bands, continuous acquisition. **~160 Mbps sustained average.** |
| Typical commercial EO smallsat (X-band) | 100–500 Mbps burst | 10s–100s GB/day | Constrained by ground-station contact windows (typically 10–15 min per pass, 3–6 passes/day). |
| CubeSat (S-band, UHF) | 1–100 Mbps burst | 100s MB – few GB/day | The bandwidth-bound regime SatDiff's "compact report" framing targets. |
| Inter-satellite link (EDRS, optical) | 1–2 Gbps | — | Expensive; used sparingly. |

**Reality check on the SatDiff pitch:** "send the raw tile to the ground" for a *single* Sentinel-2 tile of 13 bands at 10-m resolution over a 100×100 km area is ~1–2 GB compressed. For a portfolio of 800 assets, full-coverage once per revisit cycle, raw downlink is minutes-to-hours of a 500 Mbps X-band pass per day per asset. **The "compact report" framing holds**: a 2 KB per-asset JSON report scales to a 1.6 MB daily portfolio stream — a rounding error on any downlink budget.

The bandwidth argument for on-satellite VLM inference is real and defensible — *but the bigger constraint is contact-window time*, not raw bits/second. On-board reporting produces data that can cross a narrow contact window easily; raw imagery cannot.

## 5. What SatDiff's submission should commit to (compute-realism section)

For the submission writeup's "assumptions" section, we commit to the following as defensible-under-scrutiny:

1. **Primary target platform:** **NVIDIA Jetson Orin NX 16GB** (= the DPhi Space hackathon prize platform; also flight-proven on Loft Orbital YAM-9). 100 TOPS sparse INT8, 1024 Ampere CUDA cores + 32 Tensor Cores, 8-core Cortex-A78AE, 16 GB LPDDR5, ~15–25 W. Runs Docker-based workloads. Peer platforms: Unibap iX10, KP Labs Leopard.
2. **Model:** LFM2-VL-1.6B primary, LFM2-VL-450M fallback. Runtime is deployment-flexible (llama.cpp, MLX, ONNX, LEAP native) per rubric allowance. Sub-250ms per-pass latency target (matching published LFM2.5-VL-450M benchmarks).
3. **Sensor note:** the hackathon's actual prize satellite carries a fisheye camera, not a Sentinel-2 multispectral imager. SatDiff's demo uses Sentinel-2 via the DPhi API (the hackathon's dataset). The contract-prompt architecture is sensor-agnostic, which means a production deployment targets whatever sensor the flight platform carries. The submission writeup names this explicitly in the production-roadmap section.
4. **Sensor fusion for tailings cases:** Sentinel-2 multispectral + Sentinel-1 SAR deformation sidecar. The deformation sidecar is (a) pre-computed on ground and uplinked as part of the baseline package for v0, or (b) for production, run on-satellite as a separate lightweight process.
5. **Downlink envelope:** <10 KB per pass per asset for structured reports. Validated against the hackathon's 10 MB/month download budget — a 2 KB report × 1000 passes = 2 MB, well within budget. Raw imagery downlink remains optional and on-demand (e.g., when supervisory loop requests full frame for a specific flagged asset).
6. **Update cadence:** baseline + contract prompt updated only via supervisory-loop upload (ground-initiated). On-board state is read-write for inference outputs and prior-report history; read-only for baseline and contract. This is the security model.
7. **Radiation tolerance:** assumed at COTS-with-mitigation level. Single-event-upset recovery via watchdog + checkpoint; we do not claim full rad-hard silicon.

**What we do not claim:**
- We are not flying anything. The submission is a ground-based emulation of the pattern.
- We do not claim LFM2-VL has been flown (nothing has). Our claim is that it *can* fly given the hardware profile above.
- We do not claim on-board InSAR processing. That remains a ground task in v0.

## 6. Follow-ups for laptop spikes

These check whether our architectural assumptions actually hold in practice:

1. **LEAP/LFM2-VL spike**: pull LFM2-VL-450M (and 1.6B if time) via LEAP. Run 2-image + structured-text → JSON on a sample Jagersfontein pair. Measure wall-clock latency on laptop CPU/GPU. Extrapolate to Hailo-8 via published multipliers.
2. **Contract-prompt compile spike**: given the Jagersfontein contract (`research/contract-prompts/jagersfontein-contract.md`) and a single pass, does LFM2-VL produce valid JSON matching the schema? How often does it drift? This calibrates how much retry/validation logic we need.
3. **Bandwidth budget sanity**: compute actual byte size of (a) per-pass JSON report, (b) weekly portfolio roll-up, (c) a Sentinel-1 SAR sidecar summary. Verify all fit in well under 100 KB/day/asset — if so, the "compact downlink" claim is empirically supported by our own pipeline.

## Sources

### On-satellite compute hardware
- [Unibap SpaceCloud iX10 homepage](https://unibap.com/solutions/hardware/ix10/)
- [Unibap iX10-102 datasheet (PDF)](https://unibap.com/wp-content/uploads/2024/07/spacecloud-ix10-102.pdf)
- [Unibap iX10-101 datasheet (PDF)](https://unibap.com/wp-content/uploads/2024/04/ix10-101-product-overview.pdf)
- [Satsearch — Unibap iX10-100](https://satsearch.co/products/unibap-space-cloud-i-x10-100-computer)
- [KP Labs Leopard DPU](https://www.kplabs.space/solutions/hardware/leopard)
- [Dragonfly Aerospace × Unibap partnership](https://dragonflyaerospace.com/dragonfly-aerospace-and-unibap-power-edge-ai-satellite-missions/)

### On-board ML missions
- [Φ-sat-1 mission (ESA Φ-lab)](https://philab.esa.int/flagship-programmes/phi-sats-programme/)
- [Wikipedia — Phi-Sat-1](https://en.wikipedia.org/wiki/Phi-Sat-1)
- [Ubotica — first on-board AI in space](https://ubotica.com/satellite-successfully-applies-ai-to-process-earth-observation-imagery-in-flight-in-historic-first-for-space/)
- [Hackster — Intel Movidius Myriad 2 on Phi-Sat-1](https://www.hackster.io/news/intel-s-movidius-myriad-2-vpu-takes-artificial-intelligence-into-space-aboard-the-phisat-1-af8b6e0b5c5b)
- [Phi-Sat-2 Wikipedia](https://en.wikipedia.org/wiki/Phi-Sat-2)
- [ESA — Introducing Phisat-2](https://www.esa.int/Applications/Observing_the_Earth/Phsat-2/Introducing_Phsat-2)
- [Open Cosmos — Phisat-2 launch](https://www.open-cosmos.com/news/phisat-2-launch)
- [KP Labs — Intuition-1](https://www.kplabs.space/projects-and-missions/intuition-1)
- [KP Labs — first hyperspectral AI in orbit](https://www.kplabs.space/press-releases/press-release-first-hyperspectral-images-processed-by-ai-on-board-intuition-1-satellite)
- [ESA — OPS-SAT](https://www.esa.int/Enabling_Support/Operations/OPS-SAT)
- [Wikipedia — OPS-SAT](https://en.wikipedia.org/wiki/OPS-SAT)
- [OPS-SAT data-centric competition (Springer)](https://link.springer.com/article/10.1007/s42064-023-0196-y)
- [Loft Orbital YAM-9 — edge compute milestone](https://loftorbital.com/yam-9-benchmarking-the-future-of-ai-enabled-space-infrastructure/)
- [Loft Orbital — On-Orbit AI](https://loftorbital.com/on-orbit-ai/)
- [Loft Orbital × SkyServe partnership](https://spacenews.com/loft-orbital-and-skyserve-partner-on-ai-powered-earth-observation-application/)

### LFM2 / LFM2-VL
- [LFM2-VL announcement — Liquid AI](https://www.liquid.ai/blog/lfm2-vl-efficient-vision-language-models)
- [LFM2 Technical Report (arXiv)](https://arxiv.org/abs/2511.23404)
- [LFM2.5-VL-450M release coverage — MarkTechPost (April 2026)](https://www.marktechpost.com/2026/04/11/liquid-ai-releases-lfm2-5-vl-450m-a-450m-parameter-vision-language-model-with-bounding-box-prediction-multilingual-support-and-sub-250ms-edge-inference/)
- [Liquid Foundation Models](https://www.liquid.ai/models)
- [LFM2-1.2B on Hugging Face](https://huggingface.co/LiquidAI/LFM2-1.2B)

### Downlink economics
- [ESA — Sentinel-2 operations](https://www.esa.int/Enabling_Support/Operations/Sentinel-2_operations)
- [Sentinel-2 User Handbook (PDF)](https://sentinel.esa.int/documents/247904/685211/sentinel-2_user_handbook)
- [SentiWiki — S2 Mission](https://sentiwiki.copernicus.eu/web/s2-mission)

### VLM-on-satellite state of the art
- [Wang et al. 2025 — Satellite-Ground Synergistic LVLM System (arXiv)](https://arxiv.org/abs/2507.05731)
