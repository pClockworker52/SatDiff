# SatDiff demo — voice-over script

**Total target**: 4:50–4:58. Speak ~10 % slower than feels natural — VO sounds rushed in the cut. Pause 1 s before and after each segment for editing handles.

**Audio buckets**:
- **Sync** = recorded with the camera (lips on screen).
- **VO** = recorded separately into the mic, laid under visuals later.

Word counts assume ~150 words/minute (comfortable read).

---

## 0:00 – 0:25 — Forggensee opener (already filmed, sync) [25 s, ~75 w]

Existing footage. Verbatim transcript for reference, no re-recording needed:

> *This is the Forggensee, a regulated dam on the Lech, monitored under Bavaria's Stauanlagensicherheitsverordnung. Right now, compliance is humans on inspection schedules. What I'm building turns that into a satellite-readable contract — a vision-language model on-orbit produces a time-stamped, claim-by-claim assessment.*

---

## 0:25 – 0:50 — Time-lapse hook (VO) [25 s, ~70 w]

**Visual**: `demo/jagersfontein_timelapse.mp4` (full-screen, the pond grows then bursts in the final frame).
**Overlays**: date stamp baked into video; subtle title card *"Jagersfontein, South Africa — 2021-06 → 2022-10"* fading in/out at 0:26.

> *And yet — the signal was already there. These are seventeen monthly Sentinel-2 acquisitions of the Jagersfontein tailings dam in South Africa, the year before its September 2022 collapse. The pond grows. The wall thins. By the final frame, the failure has happened. Public imagery. Available to anybody who looked.*

---

## 0:50 – 1:20 — Problem statement, on camera (sync) [30 s, ~85 w]

**Visual**: PIP presenter (small webcam circle, lower-right) over a dark slate. Slate fades in two text lines as you say them.
**Slate text appearing as you speak**:
- line 1 at 0:55: **"GISTM Principle 7"**
- line 2 at 1:05: **"Auditors today: physical inspections + ad-hoc public-imagery review"**

> *International tailings facilities are now regulated under GISTM — the Global Industry Standard on Tailings Management. Principle 7 says operators must monitor, and regulators must audit. Today, that audit is humans on inspection schedules and ad-hoc review of public data. The Jagersfontein signal lived in nobody's review queue. SatDiff turns it into a per-pass artefact the regulator can sign and file.*

---

## 1:20 – 2:30 — Architecture walkthrough (VO) [70 s, ~190 w]

**Visual**: `docs/architecture.svg` revealed left-to-right in time with the VO. Reveal order — keep it tight, one element per ~10 s:
1. SimSat (Sentinel-2)
2. Physical-diff module (NDWI, NDMI, gully, asymmetry, pond-to-wall)
3. Gate (Φ-sat heritage)
4. LFM2.5-VL (GGUF + llama-server)
5. Rules engine (severity, action)
6. Structured JSON (~2 KB)
7. ═══ DOWNLINK ═══
8. Ground supervisor → PDF

**Overlays at the right beat**:
- "~2 KB JSON" near the downlink boundary at 2:00
- "544 MB GGUF on-orbit" near LFM2.5-VL at 1:50
- "2.38 s per pass on RTX 4080 sm_89" at 2:10

> *The pipeline is split across the orbit-to-ground boundary. On the satellite: Sentinel-2 imagery comes in. A Phase 1 physical-diff module computes the numbers an auditor cares about — pond area, deposition asymmetry, gully count, distance from the pond to the retaining wall. A Phi-sat-style gate decides whether the pass is worth thinking about. If yes, the on-orbit model — Liquid AI's LFM2.5 vision-language model, quantised to 544 megabytes — runs against the imagery and the diff. A deterministic rules engine in Python turns those numbers into severity, recommended action, and an escalation flag. The output is two kilobytes of JSON. That is the marginal-downlink-cost claim. The satellite never re-downlinks the imagery on SatDiff's budget. On the ground, a supervisor joins that JSON to the imagery the regulator's data infrastructure already has, and renders the per-pass PDF.*

---

## 2:30 – 3:30 — Live demo screen capture (VO) [60 s, ~165 w]

**Visual**: pre-recorded OBS capture (`demo/captures/livedemo.mkv`):
- 0:00–0:08  `docker compose up -d` shows four services healthy
- 0:08–0:25  `python -m phase2.cli --asset jagersfontein --date 2022-10-15 ...`
- 0:25–0:40  JSON appearing field-by-field (tail-following the file)
- 0:40–0:55  `python -m phase3 --asset jagersfontein --date 2022-10-15` writes the PDF
- 0:55–1:00  page-flip through the hero PDF (`phase3/out/jagersfontein/2022-10-15.pdf`)

**Overlays appearing as the JSON fields land**:
- 2:50: ▸ `severity: urgent`
- 2:55: ▸ `pond_to_wall_distance_m: 9.9`
- 3:00: ▸ `Stage A 0.96 s | Stage B 1.43 s | total 2.38 s`
- 3:10: ▸ `regulatory_escalation_flag: true`

> *Here is the same pipeline running on the post-failure pass. Docker compose brings up SimSat, the llama-server with the Stage 1 weights pre-loaded, and the SatDiff renderer. Phase 2 issues a two-stage decode: first a free-text describe of what the model sees, then a contract JSON shaped to the auditor's schema. The rules engine grades severity from the physical-diff numbers — pond-to-wall distance is nine point nine metres, the engine returns urgent. Total time per pass: two point three eight seconds on a laptop GPU. The PDF is the human-readable artefact. One page per acquisition. Imagery, diff metrics, per-claim assessments, signed and time-stamped.*

---

## 3:30 – 4:00 — Fine-tune story (VO) [30 s, ~85 w]

**Visual**: full-screen card with two side-by-side evidence strings:

```
BASE LFM2.5-VL-450M       STAGE 1 FINE-TUNE
NDWI_mean=-0.212          pond_to_wall_distance_m=9.9
NDMI_mean=-0.158          pond_area_change_pct=433
B4/B3=1.278               NDWI_max=0.909
                          B4/B3=1.278
```

Then the table fades in:

```
                  base    Stage 1
schema-valid      6/6     6/6
evidence-correct  0/30    30/30
```

**Overlay at 3:48**: ▸ *"Stage 2 (negative result, not shipped)"* in smaller grey text.

> *Stage 1 was a five-thousand-sample LoRA fine-tune on VRSBench, the public remote-sensing benchmark. No SatDiff-specific examples. Evidence-correctness on held-out passes lifted from zero out of thirty to thirty out of thirty. Stage 2 tried to push severity reasoning into the model itself — it failed, and we did not ship it. That negative result is exactly why severity lives in deterministic Python, not in the weights.*

---

## 4:00 – 4:30 — Forggensee comeback (VO) [30 s, ~80 w]

**Visual**: split layout — `demo/forggensee_rgb.png` (left, 50 %), the Stage A text scrolling in on the right (paragraphs 1 and 2 only — drop the duplicates 3 + 4 in editing).
**Overlay at 4:02**: small map pin animation showing 47.57° N, 10.74° E.

> *Same model, same Stage A prompt, pointed at a Sentinel-2 tile of the Forggensee in Bavaria. The model identifies the impoundment, the wall, the surrounding land. The vocabulary still leans tailings-dam — because the prompt does. Plug a different contract schema in for Bavaria's Stauanlagensicherheitsverordnung, and the same architecture carries. The model is the writer; the contract is the schema; the architecture is portable.*

---

## 4:30 – 5:00 — Close, on camera (sync) [30 s, ~90 w]

**Visual**: PIP presenter (lower-right) over a dark slate. At 4:50 the slate transitions to a clean URL card:

```
Weights:  huggingface.co/WobblyDopamine/SatDiff-LFM2.5-VL-450M-stage1
Code:     github.com/<your-handle>/SatDiff
Run:      docker compose up
```

> *SatDiff puts a per-claim, contract-framed audit artefact in front of the regulator at acquisition cadence. The primary buyer is the GISTM auditor; adjacent buyers are dam-safety regulators, insurance underwriters, and ESG screens. Weights are public. Code is reproducible from a fresh clone. One command — docker compose up. Thank you.*

---

## Recording order recommendation

Record in this order to minimise context-switching:

1. **All voice-over takes back-to-back** (segments 0:25, 1:20, 2:30, 3:30, 4:00). Mic + room. Do 2–3 takes per segment, pick the best in DaVinci. ~45 min including resets.
2. **Two on-camera takes**: intro (0:50–1:20) and close (4:30–5:00). Same lighting + outfit. ~30 min including 3–5 takes each.
3. **Live-demo screen capture** in OBS — open a clean terminal + browser, walk through the cue points above, ~5 takes total. ~30 min.

Total active recording: ~1 h 45 min.

## Vocal notes for the recording booth

- **Numbers** trip non-native readers — slow down on "two point three eight seconds", "thirty out of thirty", "zero out of thirty". Practice once aloud.
- **GISTM** is "G-I-S-T-M" (initialism, not "gist-em").
- **Sentinel** = "SEN-tin-ul", first syllable stressed.
- **NDWI / NDMI / B4-B3** — only spoken once (in the architecture VO list) — read the letters; do not try to expand.
- **LFM2.5** — say it as "L-F-M two point five".
- **Stauanlagensicherheitsverordnung** — own it, say it the way you said it at the dam. The German term is part of the message.
- **Φ-sat** — pronounced "fee-sat".

## Total word count by bucket

| segment | type | words | seconds @ 150 wpm |
|---|---|---:|---:|
| 0:00–0:25 | sync (existing) | ~75 | 25 |
| 0:25–0:50 | VO | ~70 | 25 |
| 0:50–1:20 | sync (intro) | ~85 | 30 |
| 1:20–2:30 | VO | ~190 | 70 |
| 2:30–3:30 | VO | ~165 | 60 |
| 3:30–4:00 | VO | ~85 | 30 |
| 4:00–4:30 | VO | ~80 | 30 |
| 4:30–5:00 | sync (close) | ~90 | 30 |
| **total** | — | **~840** | **~300 = 5:00** |
