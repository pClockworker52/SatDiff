# Jagersfontein Research Memo (Phase 0.1)

**Case:** Jagersfontein Tailings Storage Facility (historic diamond-mine tailings)
**Failure date:** 11 September 2022
**Location:** Jagersfontein, Free State Province, South Africa
**Operator (at failure):** Jagersfontein Developments (Pty) Ltd
**Owner:** Stargems Group (Dubai-based diamond trader)
**Tailings type:** Diamond-mine kimberlite fines; unusually high clay content with poor settling behaviour
**Casualties:** 1 dead, 1 missing (later presumed dead), 76 injured
**Property damage:** 51 houses destroyed, 103 severely damaged; mine-waste mud flow covered ~6 km downstream
**Civil litigation:** ~ZAR 3 billion lawsuit (26 victims + Kopanong Local Municipality)
**Criminal case:** opened by DWS 4 November 2022 under §151 National Water Act

## 1. Technical cause

Preliminary assessments and the forensic technical-investigation report (Universities of Pretoria + Witwatersrand, delivered Sept 2024, publicly released Nov 2025) conclude:

- **Long-term engineering failures**, ignored warning signs, and **regulatory-oversight lapses**.
- Dam wall built over unstable, saturated tailings; no working decant system.
- Engineers had warned the wall slope was too steep; safety further undermined by design shortcuts.
- Particular to Jagersfontein: high clay content in the tailings kept fines in suspension; on-site engineers were unaware that a specific flocculant would have enabled settling. Result: very liquid deposition that never consolidated.
- Supernatant pond frequently pressed against the retaining wall — direct contributor to percolation + external erosion failure sequence hypothesised by Torres-Cruz & O'Donovan 2023.
- Official verdict: **"foreseeable and preventable."**

## 2. Published pre-failure satellite signals — the key case

### 2.1 Torres-Cruz & O'Donovan 2023 (Wits, *Scientific Reports*)
Paper: *"Public remotely sensed data raise concerns about history of failed Jagersfontein dam."*
Published 5 April 2023, six months after the failure.

**Data sources (all public):**
- **Sentinel-2** (ESA, 10–20 m multispectral, 2015 onwards)
- **Landsat 8** (NASA/USGS, 30 m multispectral, 2013 onwards)
- Google Earth Pro (commercial imagery composites)
- Post-failure assessment used some commercial high-resolution (Maxar / Planet).

**Pre-failure features documented in public multispectral imagery:**

| Feature | Detectability | First detected | Years before failure |
|---------|--------------|----------------|----------------------|
| Erosion gullies 4–5 m wide on N and SE walls | Sentinel-2 visible + Landsat 8 | Feb 2019 | ~3.5 years |
| Supernatant pond against retaining wall | Sentinel-2 NDWI / visible | persistent from ~2017 | ~5 years |
| Absence of tailings beach (safety buffer) | Sentinel-2 visible | persistent | multi-year |
| Asymmetric deposition (one-sided filling) | Sentinel-2 visible | persistent | multi-year |
| External seepage signs | Sentinel-2 visible at 10 m | 2019 onwards | ~3.5 years |

**Authors' conclusion:** the dam's operational history, visible entirely in public satellite imagery, deviated materially from sound tailings-management practice. Their hypothesis for failure mechanism: percolation of water through the dam followed by external erosion — the full sequence surface-visible in the multispectral archive.

### 2.2 CGG Satellite Blog — InSAR preliminary review
- Sentinel-1 InSAR analysis of the Jagersfontein TSF over Jan 2021 – Aug 2022.
- Identified precursor deformation consistent with outward bulging of the dam (east/west displacement vectors).
- Confirms SAR-based deformation signal exists but was *not* the primary pre-failure anomaly — the multispectral anomalies predated and were more prominent than the SAR signal.

### 2.3 Subsequent SAR-focused work
Sentinel-1 analyses over 2019–2024 (three years pre- and post-failure) show subsidence near the foundation combined with localised uplift — consistent with material stress redistribution. But the central academic finding is that the primary precursors were *visible* in Sentinel-2 / Landsat, not confined to InSAR.

## 3. Regulatory and monitoring history — a documented enforcement failure

| Date | Event |
|------|-------|
| Feb 2019 | Erosion gullies first detectable in Sentinel-2. |
| Dec 2020 | DWS issues directive: cease deposition. Jagersfontein Developments was over its licensed water-retention volume by **70%**. |
| 7 Jan 2021 | Operations suspended under directive. |
| May 2021 | Directive **overturned** despite the operator's closure plan being rejected and licence conditions unmet. |
| Jun 2021 | Deposition resumes. |
| 11 Sep 2022 | Catastrophic collapse. |
| 4 Nov 2022 | DWS opens criminal case under §151 NWA. |
| Sep 2024 | UP + Wits technical investigation report delivered. Kept confidential at the NPA's request. |
| 28 Nov 2025 | Report publicly released. Verdict: "foreseeable and preventable." Recommended overhaul of tailings-dam regulations: clearer legal authority, stricter licensing, mandatory independent audits, GISTM-aligned practices. |

**Key institutional finding:** DWS could not produce the water-use-licence application or geotechnical investigation reports — records that should have been central. The regulatory system lost documentation that would have enabled effective monitoring. The directive was lifted without the closure-plan acceptance requirement being met.

In contrast to Brumadinho (where monitoring-data quality was the issue), at Jagersfontein the *satellite signal was public and obvious years in advance* — the failure was enforcement, not detection.

## 4. Insurance and loss exposure

- No large reinsurance payout has been publicly reported. Jagersfontein Developments is not a major listed operator; Stargems Group is privately held. Insurance coverage appears to have been minimal relative to the damage.
- The ~ZAR 3 billion civil lawsuit is the principal financial exposure. Municipal and government rebuild costs add meaningfully on top.
- Jagersfontein is *financially* a much smaller case than Brumadinho ($7B+ settlement) but is *analytically* a much cleaner case for Sentinel-2-based demonstration:
  - signals were in multispectral imagery,
  - enforcement failure is what killed the community,
  - the authoritative investigation explicitly uses "foreseeable and preventable" as its verdict.

## 5. Signal summary — what would SatDiff see?

| Signal | Modality | Pre-failure detectable? | Lead time | Strength |
|--------|----------|-------------------------|-----------|----------|
| Erosion gullies on dam walls | Sentinel-2 RGB + B8 NIR | **Yes** | ~3.5 years | Strong, spatially obvious |
| Pond pressed against retaining wall | Sentinel-2 NDWI (B3, B8) | **Yes** | ~5 years | Strong, persistent |
| Tailings beach absent | Sentinel-2 RGB | **Yes** | multi-year | Strong |
| Asymmetric deposition | Sentinel-2 RGB over time | **Yes** | multi-year | Moderate, requires time-series framing |
| Pond area expansion | Sentinel-2 NDWI time series | **Yes** | ~2 years (Dec 2020 DWS "70% over" milestone) | Strong |
| Surface deformation | Sentinel-1 InSAR (SBAS/PSI) | Partial | ~1–2 years | Moderate, secondary to multispectral |
| Downstream vegetation stress | Sentinel-2 NDVI/NDMI | Possibly | N/A | Not the leading signal |

**Bottom line for Jagersfontein:** Sentinel-2 multispectral imagery carries the dominant, spatially-obvious, multi-year precursor signal. SAR is complementary but not primary. This is the inverse profile from Brumadinho.

## 6. Why Jagersfontein works for SatDiff

Jagersfontein fits the plan's thesis much better than Brumadinho:

1. **Sentinel-2 is load-bearing.** A pure-Sentinel-2 backtest here has real signal to find. The Torres-Cruz & O'Donovan paper is the ground-truth reference: each feature they identified becomes a testable VLM assessment.
2. **The contract-framing story works cleanly.** The monitoring contract's claim conditions (containment geometry, pond management, surface integrity, downstream slope) map directly onto visible anomalies present for years pre-failure.
3. **The counterfactual is credible.** The official report's "foreseeable and preventable" verdict is not our editorialising — it is the conclusion of UP + Wits technical experts. SatDiff's pitch becomes: "had this pipeline been running from 2017, the claim conditions that correspond to the Torres-Cruz findings would have been elevated continuously from Feb 2019. The regulatory enforcement failure that occurred would have had a persistent, dated, machine-generated record of public-satellite precursors to contend with."
4. **Honest framing about the limits.** We can simultaneously say: "monitoring alone would not have prevented Jagersfontein — enforcement failed. But machine-generated, contract-framed, time-stamped escalations might have made enforcement failure costlier or harder to paper over."

## Sources

- [Torres-Cruz & O'Donovan 2023, *Scientific Reports*](https://www.nature.com/articles/s41598-023-31633-5)
- [Wits University press release (2023-04)](https://www.wits.ac.za/news/latest-news/research-news/2023/2023-04/civil-engineers-use-public-satellite-images-to-study-why-the-jagersfontein-dam-failed-.html)
- [EurekAlert! coverage of Wits study](https://www.eurekalert.org/news-releases/985155)
- [ScienceDaily coverage of Wits study](https://sciencedaily.com/releases/2023/04/230405111914.htm)
- [Mining Weekly — Jagersfontein deviated from best practice](https://www.miningweekly.com/article/new-study-shows-jagersfontein-dam-deviated-from-best-practice-2023-04-12)
- [Nature — Keeping an eye on tailings dams](https://www.nature.com/articles/d44148-023-00101-7)
- [CGG Satellite Blog — Jagersfontein TSF InSAR preliminary](https://satelliteblog.cgg.com/jagersfontein-tsf-failure-preliminary-satellite-imagery/)
- [AGU Landslide Blog — Jagersfontein failure](https://blogs.agu.org/landslideblog/2022/09/12/jagersfontein/)
- [AGU Landslide Blog — Analysing aerial and satellite imagery](https://blogs.agu.org/landslideblog/2022/09/13/jagersfontein-tailings-dam-2/)
- [AGU Landslide Blog — Planet high-resolution imagery](https://blogs.agu.org/landslideblog/2022/09/26/jagersfontein-tailings-dam-failure-planet/)
- [NASA Earth Observatory — Jagersfontein Covered in Mining Waste](https://earthobservatory.nasa.gov/images/150497/jagersfontein-covered-in-mining-waste)
- [Wikipedia — 2022 Jagersfontein dam collapse](https://en.wikipedia.org/wiki/2022_Jagersfontein_dam_collapse)
- [Bench Marks Foundation report](https://www.bench-marks.org.za/wp-content/uploads/2023/09/Jagersfontein-report-BMF-Sep23.pdf)
- [ScienceDirect — An industrial disaster 150 years in the making](https://www.sciencedirect.com/science/article/pii/S2212420924003479)
- [South African Government — Technical Investigation Report release](https://www.gov.za/news/media-statements/deputy-ministers-david-mahlobo-and-sello-seitlholo-release-technical)
- [Sowetan — "foreseeable and preventable"](https://www.sowetan.co.za/news/2025-11-30-jagersfontein-dam-collapse-deemed-foreseeable-and-preventable/)
- [Moneyweb — Jagersfontein ordered to cease ops 2020](https://www.moneyweb.co.za/mineweb/jagersfontein-was-ordered-to-cease-tailings-operations-in-2020-but-continued-anyway/)
- [Bowmans — complicated regulatory regime](https://bowmanslaw.com/insights/south-africa-jagersfontein-tragedy-highlights-complicated-regulatory-regime-for-tailings-dams/)
- [SABC News — R3B lawsuit](https://www.sabcnews.com/sabcnews/jagersfontein-disaster-victims-municipality-file-r3-bln-lawsuit/)
- [Earthworks — two years later](https://earthworks.org/blog/a-dereliction-of-duty-jagersfontein-mine-waste-disaster-two-years-later/)
- [NRi Digital Mine — Cleaning up tailings dams](https://mine.nridigital.com/mine_dec23/jagersfontein-tailings-dam-south-africa)
