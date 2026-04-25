# Why On-Satellite Inference? — An Honest Defence

**Question being asked:** "Why can't you just downlink all Sentinel-2 imagery and process it on powerful infrastructure on Earth? Isn't that already how it's done?"

**Short answer:** For Sentinel-2 today, you can — and that's exactly what's done. The on-satellite argument applies in three specific scenarios that SatDiff is designed for, but it is *not* the claim that "ground processing is impossible." This memo replaces the original plan's overclaim with a defensible position.

---

## The honest baseline: ground processing is the current norm

Sentinel-2 downlinks ~1.6 TB/day across the constellation via X-band at 560 Mbps. The Copernicus Data Space Ecosystem and Microsoft Planetary Computer ingest this data and serve it to users worldwide via STAC APIs. Commercial InSAR services (TRE Altamira, Insight Terra) all follow the same pattern: satellite → ground station → cloud GPU processing → customer outputs.

**This works.** It scales to global coverage. It is not the problem SatDiff solves.

In fact, our own Phase 1 backtest depends on this baseline: we will pull the Jagersfontein and Brumadinho archives via the DPhi/SimSat API, which itself fetches from Element 84's STAC endpoint, which itself is downstream of Sentinel-2's standard ground-processing pipeline. We are not opposed to ground processing; we use it.

So if a judge asks "why not just do everything on Earth?", the honest answer starts with: *we already do, for many use cases. SatDiff is the architecture for the use cases where ground-processing economics break.*

## The three scenarios where on-board genuinely wins

### Scenario 1 — Bandwidth-constrained platforms

Sentinel-2 is exceptional. It has dedicated Copernicus ground stations and a 560 Mbps X-band link. Most Earth-observation smallsats and CubeSats do not.

Typical bandwidths:
- Sentinel-class large EO sat: 100–500+ Mbps X-band, 10s–100s of GB/day, multiple daily contacts.
- Commercial smallsat: 10–100 Mbps burst, 100s of MB to a few GB/day.
- CubeSat with S-band: 1–10 Mbps, 10s–100s of MB/day total.
- **The hackathon prize satellite: 10 MB/month download budget.**

For platforms in the lower bands, "download everything and process on Earth" is not a choice the operator gets to make. The platform produces more raw imagery in a single pass than its monthly downlink can carry. Either you compress aggressively (lossy, hurts downstream analysis), or you process on-board and downlink only the conclusions.

The hackathon's own prize platform makes this concrete: 10 MB/month. A single Sentinel-2-resolution tile of 13 bands at 10m over a 100×100 km area is ~1–2 GB compressed. That's hundreds of months of downlink budget for *one tile*. On-board reasoning is the only architecture that fits.

### Scenario 2 — Latency-sensitive applications

For some applications, the round-trip ground-processing loop is the constraint, not the bits.

- **Wildfire detection:** acquired image → ground station (next pass, 30–90 min) → processing pipeline (minutes to hours) → alert dispatch. Total: hours. Wildfire spread in dry conditions: meters per minute. The loop is too slow.
- **Vessel tracking, dark-vessel detection:** vessels move 10–30 km/h. By the time ground processing identifies an anomaly, the vessel has moved past where it was detected.
- **Geopolitical event response:** the gap between "image acquired" and "alert reaches operator" can be the difference between actionable and historical.

For these use cases, on-board inference + immediate downlink of the conclusion is the only way to close the loop fast enough.

SatDiff's tailings-monitoring case is *not* in this scenario — tailings dam failures are slow-horizon (months to years of precursor signals). We don't pitch latency as our wedge. But the architectural pattern we're demonstrating *also* serves the latency-sensitive class, which is how our submission positions the broader applicability.

### Scenario 3 — Portfolio-scale continuous monitoring

This is SatDiff's actual wedge.

For one asset monitored once, ground processing is cheaper. For 800 assets monitored every revisit, the aggregate cost shifts:

- **Compute cost on the ground** scales with raw pixels processed. A reinsurer monitoring 800 TSFs at 5 km² each, every 5 days, is ~580 GB/year of multispectral data to process per cycle, times the inference compute on top.
- **Compute cost on-board** scales with selected-pass × per-pass-inference. With a gate that runs full inference on ~20–30% of passes (cloud-free, change-detected), the compute envelope per asset is 2–3 orders of magnitude smaller.
- **Coordination cost** also matters. Ground processing requires running pipelines, managing failures, paying cloud-egress fees for the customer. On-board processing produces the answer where the data is born; only the answer (not the input) crosses the link.

This isn't an argument that ground processing is *impossible* at portfolio scale. It's an argument that **on-board is the architecture that makes the marginal cost per asset low enough to pencil out for continuous monitoring of large, distributed asset portfolios that are currently monitored only episodically.**

## Φ-sat-1: the canonical precedent

The European Space Agency's Φ-sat-1 (2020) ran on-board CNN inference for cloud detection on the HyperScout-2 sensor. It saved ~30% bandwidth by discarding cloudy scenes before downlink.

Φ-sat-1 was not bandwidth-starved. It had perfectly adequate downlink. The mission ran on-board ML anyway, because *even on a well-resourced satellite, on-board pre-filtering produces meaningful efficiency at scale*. The ESA paper's framing: "on-board AI is sensible whenever the cost of generating a useful conclusion locally is less than the cost of moving the raw input to where the conclusion would otherwise be made."

That's the Φ-sat-1 framing, and it's the right framing for SatDiff. The argument is **economics at scale**, not capacity scarcity.

## SatDiff's specific positioning

To be precise about what we claim and what we don't:

**We do NOT claim:**
- "Sentinel-2 cannot be downlinked and processed on Earth." (False; it is, every day.)
- "Ground processing is impossible at portfolio scale." (False; it's expensive but possible.)
- "On-board inference is mandatory for tailings-dam monitoring as it exists today." (Not true — TRE Altamira and Insight Terra do tailings InSAR with ground processing and it works.)

**We DO claim:**
- For monitoring portfolios of distributed assets at low marginal cost per asset, the on-board architecture is the one that scales.
- For deployment on bandwidth-constrained platforms (the hackathon prize satellite, future smallsat fleets), on-board reasoning is the only architecture that fits.
- The architectural pattern — physical-diff + VLM + structured output — is sensor-agnostic and transfers to platforms where ground processing is genuinely impossible.
- Φ-sat-1 (2020) demonstrated that on-board ML pays off even on bandwidth-adequate platforms; SatDiff extends that pattern from "cloud detection" to "claim-framed contract assessment."

## Implications for the demo and submission writeup

**Pitch language to use:**

> "Today, satellite imagery is downlinked and processed on Earth. That works. SatDiff is the architecture for the next layer of monitoring — continuous, contract-framed, portfolio-scale — where on-board reasoning produces the conclusion at the moment of acquisition, on a 25-watt envelope, under a 10 MB/month downlink budget. The same architecture deploys today on platforms with adequate bandwidth to gate which scenes are worth shipping (after Φ-sat-1's pattern), and tomorrow on bandwidth-constrained smallsat fleets where it is the only architecture that fits."

**Pitch language to avoid:**

> ~~"Satellites cannot invoke cloud APIs."~~ — too absolute; many can during ground contact.
> ~~"You cannot download Sentinel-2 imagery to Earth."~~ — false.
> ~~"On-satellite inference is mandatory for monitoring tailings dams."~~ — overclaim.

**For the Q&A:**

If a judge asks "why not just process on Earth?", answer:

> "For Sentinel-2 today, you can. We do — our backtest pulls the archive from the standard ground-processed STAC API. The on-board argument applies in three specific scenarios: (1) bandwidth-constrained platforms like this hackathon's prize satellite at 10 MB/month, where you literally can't ship raw imagery; (2) latency-sensitive applications like wildfire or vessel detection where the ground round-trip is too slow; and (3) portfolio-scale monitoring where the aggregate per-asset cost of ground processing dominates. SatDiff demonstrates the pattern for case (3), and the same architecture transfers to (1) and (2). Φ-sat-1 in 2020 showed on-board ML pays off even on platforms with adequate bandwidth, by gating which scenes are worth downlinking. We extend that pattern from cloud detection to claim-framed monitoring."

That answer is honest, specific, and grounded in a flying precedent. It doesn't overclaim and it leaves no obvious counter-attack.

## One thing to flag for the Liquid Track

The "must run in orbit" argument is a **General Track** scoring criterion, not a Liquid Track one. Liquid Track scores Innovation on "satellite imagery + LFM2-VL together unlock something neither could do alone, with a believable path to a product developers would pay to build on."

So while this defence matters for Q&A and credibility, **don't front-load it in the demo video.** The Liquid Track demo should lead with the VLM-as-interpretation-layer story (contract-framed reasoning, audit trail, GISTM wedge) and treat on-board as the architectural commitment that makes the pattern viable at portfolio scale — not as the headline claim.

If asked, defend the on-board choice with the framework above. If not asked, don't dwell on it.
