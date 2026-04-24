# Hackathon Judging Criteria and Prizes — Verbatim

**Source:** official criteria from the Liquid AI Discord (`#ai-in-space-hackathon`), received 2026-04-24. Saved here so we can check the submission against it.

---

## Liquid Track — Weights

### Use of Satellite Imagery — 10%
Satellite images from the DPhi API are the core data source, applied to a real-world domain.

### Innovation and Problem-Solution Fit — 35%
The problem is specific and real. Satellite imagery + LFM2-VL together unlock something neither could do alone, with a **believable path to a product developers would pay to build on**.

### Technical Implementation — 35%
The app runs. **If judges cannot run it without debugging, it does not qualify.** Users have the freedom to choose their deployment and inference tooling (llama.cpp, MLX, ONNX...).

**Fine-tuning LFM2-VL on domain-specific satellite data is strongly encouraged and will be rewarded, with:**
- Documented methodology
- Measurable improvement over the base model
- Publicly shared weights and training code

### Demo and Communication — 20%
End-to-end demo of **you (the participant) explaining the whole thing.** Writing code is easy in 2026. Clearly articulating the problem you are solving and the architecture of your solution is not. Make the effort and you will be rewarded.

---

## General AI Track — Weights (for reference only — we are entering Liquid)

### Use of Satellite Imagery — 20%
Core data source from DPhi API; preference for approaches reflecting space-based acquisition constraints (temporal continuity, large volumes, limited downlink). **Multiple spectral bands usage is rewarded.**

### Innovation and Problem-Solution Fit — 25%
Solution must benefit specifically from **running AI models on the satellite rather than on the ground**. Strong submissions justify (a) why the application must run in orbit (latency, continuous streams, bandwidth), (b) how on-board compute enables capabilities impractical otherwise.

### Technical Implementation — 35%
Must run without debugging. Beyond simple model adaptation. Conceptual innovation, system design, optional fine-tuning all rewarded.

### Demo and Communication — 20%
Same as Liquid Track.

---

## Prize Package

Both tracks receive the same space-credits package. Liquid Track also wins **$5,000 cash.**

### Space-credits package (per winner)
- **5 GPU hours on NVIDIA Orin 16GB** (in-orbit)
- 5 MB of data upload to satellite
- 10 MB of data download from satellite
- 1 GB of in-space storage for 1 month
- All historic images of fisheye camera on the satellite
- Access to all public Docker images and LLMs preloaded on the satellite
- 7 days of testing on the satellite ground compute server

---

## Implications for SatDiff

### 1. Innovation (35%) ≫ imagery-routing (10%)
Our architectural pitch (contract-framed VLM interpretation, Torres-Cruz as validation, audit-trail framing, GISTM wedge) is proportionally the most valuable investment. Get the pitch tight.

### 2. "Believable path to a product developers would pay to build on"
This is **product-market-fit language**, not demo language. The submission writeup and demo must name:
- The buyer (GISTM independent auditor as primary; reinsurer adjacent — per `research/open-questions.md` §4)
- The line-item (Principle 7 compliance; retrospective claim defence)
- Why a developer would build on SatDiff (as an API: per-asset monitoring stream, contract-framed outputs, portfolio-scalable). We should frame SatDiff with a developer-API angle, not just a reinsurer-report angle.

### 3. Fine-tuning has concrete deliverables (part of 35% Technical)
Fine-tuning is not optional in practice for scoring. Must produce:
- **Documented methodology** — training data curation, label format, LoRA/QLoRA config, hyperparameters, loss/eval curves.
- **Measurable improvement over base LFM2-VL** — hold out a test set of Sentinel-2 patches and score base vs fine-tuned on a defined metric (JSON-schema compliance rate, claim-assessment accuracy vs human-labelled reference, latency regression test).
- **Publicly shared weights** — HuggingFace repo under a clear licence.
- **Public training code** — in the submission repo, runnable.

This is a nontrivial deliverable. Budget at least 2 days across Spike 3 + a dedicated fine-tune day.

### 4. Technical Implementation (35%) — the zero-debugging bar is hard
Fresh-clone test on Day 13 is non-negotiable. Judges literally `git clone && docker compose up` and if it doesn't work, the submission is disqualified. Pre-cache any expensive network calls; fail gracefully on missing tokens (e.g., Mapbox) rather than crashing.

### 5. Demo (20%) — you on camera explaining the architecture
Not a screen recording with voiceover. A presenter-visible, problem → architecture → demo narrative. This changes the production plan:
- Camera (webcam sufficient) + decent mic + quiet room.
- Presenter shot intercut with architecture diagrams and live pipeline output.
- 3–5 minutes is the previous-plan assumption; confirm in the Discord if there's a hard length cap.
- The language "writing code is easy in 2026" is pointed — they want **thinking and articulation**, not bravura engineering. Favour the Torres-Cruz validation, audit-trail framing, GISTM wedge in the script.

### 6. NVIDIA Orin 16GB is the actual target hardware
Winners deploy on Orin in orbit for 5 GPU hours. This is a specific architectural commitment. See `research/satellite-architecture.md` (updated) for implications:
- Orin 16GB (Jetson Orin NX-class): 100 TOPS sparse / ~50 TOPS dense INT8, 1024 Ampere CUDA cores + 32 tensor cores, 8-core Cortex-A78AE, LPDDR5 16GB, ~15–25 W.
- More compute headroom than Unibap iX10 (Hailo-8 at 26 TOPS). LFM2-VL-1.6B fits comfortably; 3B plausible.
- Deployment stack should assume Docker-based workflow (the prize mentions "public Docker images preloaded").

### 7. The actual prize satellite has a fisheye camera, not Sentinel-2
This is important for the submission writeup's "production roadmap" section. Our demo uses Sentinel-2 via the DPhi API — which is the hackathon's data, not the prize platform's native sensor. The production story must acknowledge this sensor gap and describe how SatDiff's architecture adapts to whatever multispectral/monospectral/SAR sensor a flight platform actually carries. The contract-prompt architecture is sensor-agnostic; that's a feature to highlight.

### 8. Tiny upload/download budget confirms our compact-report thesis
5 MB upload, 10 MB download **for a month of operation**. Our per-pass JSON is ~2 KB. 1000 passes = 2 MB, well inside the 10 MB download. This exactly validates the "compact report" framing in `research/satellite-architecture.md` §4 — use these numbers directly in the submission writeup.

### 9. Track selection confirmed: Liquid
Liquid Track wins +$5K cash with the same core work. LFM2-VL is already our VLM. Entering Liquid.
