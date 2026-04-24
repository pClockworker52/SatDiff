# Brumadinho Research Memo (Phase 0.1)

**Case:** Córrego do Feijão Dam I (Dam B1), Brumadinho, Minas Gerais, Brazil
**Failure date:** 25 January 2019
**Operator:** Vale S.A.
**Dam type:** Upstream-raised iron-ore tailings dam
**Casualties:** 270 deaths (official)
**Settlement:** BRL 37.7 bn (~USD 7.0–9.1 bn) between Vale and the State of Minas Gerais / federal authorities (Feb 2021)
**SEC settlement:** USD 56 M (2023, disclosure-related)

## 1. Technical cause (Robertson Expert Panel, 2019)

The independent panel commissioned by Vale (Robertson, Morgenstern, da Silva, Fourie) concluded:

- **Primary mechanism:** flow liquefaction within the tailings mass, triggered by loose, saturated, heavy, brittle iron-rich tailings under high shear stress.
- **Contributing factors:** steep upstream-constructed slope; water management that allowed water close to dam crest (weak tailings deposited near crest); high-iron tailings with inter-particle bonding (brittle once triggered to undrained); lack of internal drainage → high water level in toe region.
- **Critical finding for SatDiff:** *"The failure is unique in that it occurred with no apparent signs of distress prior to failure. High-quality drone video flown over Dam I only seven days prior showed no signs of distress."*

Translation: visible-spectrum precursors (cracking, crest deformation, obvious seepage) were **absent or below visual detection threshold**. The failure was an internal-liquefaction event with no surface-visual tell.

## 2. Published pre-failure satellite signals

### 2.1 InSAR (Sentinel-1 SAR) — Grebby et al. 2021, *Communications Earth & Environment*
- Technique: ISBAS (Intermittent Small Baseline Subset) InSAR developed by University of Nottingham / Terra Motion.
- Data: Sentinel-1 C-band SAR archive.
- Finding: anomalous deformation on dam wall and tailings beach, accelerating from **late October 2018** following increased rainfall.
- Lead time: failure date could have been predicted within ~1 week, from ~40 days prior to collapse.
- Key qualifier: ISBAS is an *advanced* InSAR variant designed to cope with vegetated terrain; conventional PSI/SBAS had weaker results.

### 2.2 Corroborating InSAR work
- **Du et al. 2020** (*Remote Sensing*, MDPI, open access): SBAS + PSI on Sentinel-1 confirmed pre-failure displacement signals, though with less lead time than ISBAS.
- **Ferreira et al. / ACG 2025** (conference): multi-sensor comparison — TerraSAR-X, COSMO-SkyMed, Sentinel-1 — all confirm deformation precursors, with higher-resolution X-band sensors giving cleaner signals.

### 2.3 Sentinel-2 multispectral — the uncomfortable finding
Published Sentinel-2 NDVI time series at Brumadinho (Alves et al., IntechOpen 2022; Silva et al., *Environ. Monit. Assess.* 2021):

| Year | Mean NDVI |
|------|-----------|
| 2017 | 0.314 |
| 2018 | 0.340 (↑ vs 2017) |
| 2019 | 0.146 (post-collapse) |
| 2020 | 0.150 |
| 2021 | 0.156 |

**Sentinel-2 NDVI did NOT show pre-failure vegetation stress at Brumadinho.** The 2019 collapse in NDVI is post-collapse impact, not precursor.

One longer-horizon multispectral signal is reported (Silva et al. 2021): "a decreasing trend in moisture content at the surface and the full evanescence of pond water through time (2011–2019) suggest water was gradually penetrating the fill downwards, causing seepage erosion." This is a multi-year surface-moisture / pond-area evanescence signal that *may* be Sentinel-2-detectable but operates on a much slower horizon than the 40-day ISBAS signal.

## 3. What Vale was actually doing at the time

- 94 piezometers, 41 water-level indicators, inclinometers, total station/reflective prisms, LiDAR, seismograph, ground-based SAR.
- Expert-panel finding: piezometric and flowmeter data had "inconsistencies"; **inclinometer data were "completely worthless"** due to instrumentation deficiencies.
- Internal Vale email traffic showed sensor-data problems flagged two days before collapse.
- A 2016 internal risk assessment (leaked later) had rated the loss potential as "high."

**Institutional finding:** the primary failure was not monitoring absence but (a) instrumentation quality and (b) failure to act on warnings already present. This is important context for the counterfactual in Phase 4 — *better monitoring alone* is not a clean save.

## 4. Insurance / reinsurance exposure

- Vale-State-of-MG global settlement: BRL 37.7 bn (~USD 7.0–9.1 bn, Feb 2021). This is civil/environmental, not pure property/BI insurance recovery.
- Vale's direct liability insurance coverage was small relative to the total loss — reporting suggests most of the $7 B+ was uninsured / self-retained by Vale. This matters: Brumadinho changed the reinsurance market's appetite for tailings exposure more than it generated a single massive reinsurance payout.
- Post-Brumadinho industry response: Munich Re (NatCatSERVICE, Corporate Insurance Partner unit) and Swiss Re re-priced tailings exposure and tightened underwriting requirements around monitoring attestations. WTW 2020 analysis: "Almost overnight insurers woke up to the full financial impact that a significant tailings failure could have on their books."
- GISTM (Global Industry Standard on Tailings Management, published Aug 2020) emerged as the post-Brumadinho compliance response. Principle 7 mandates a comprehensive monitoring system; for "Extreme"/"Very High" Consequence Classification TSFs, InSAR monitoring is now the de-facto norm.
- Samarco/Fundão (2015, same operator group) is the comparable prior event; combined, Samarco + Brumadinho are why "tailings exposure" is now a named line on reinsurer risk dashboards.

*No single clean "reinsurance paid €X" figure was found in public sources. The honest framing is "~$7 B in total civil/environmental liability with outsized influence on reinsurance appetite."*

## 5. Signal summary — what would SatDiff see?

| Signal | Modality | Pre-failure detectable? | Lead time | Notes |
|--------|----------|-------------------------|-----------|-------|
| Crest deformation | Sentinel-1 InSAR (ISBAS) | **Yes** | ~40 days | Published lead finding |
| Crest deformation | Sentinel-1 InSAR (conventional PSI/SBAS) | Yes, weaker | <40 days | Noisier over vegetated terrain |
| Visible crest cracking | Sentinel-2 RGB | **No** | N/A | Drone footage 7 days out showed nothing |
| Vegetation stress | Sentinel-2 NDVI | **No** | N/A | 2018 NDVI slightly higher than 2017 |
| Pond area/evanescence | Sentinel-2 NDWI / B4/B3 | Possibly, multi-year | 12–60 months | Very slow, weak signal |
| Surface moisture | Sentinel-2 SWIR / radar | Possibly, multi-year | 12–60 months | Slow trend, not an acute precursor |
| Drainage / seepage downstream | Sentinel-2 NDWI | Unclear from literature | — | Not highlighted as a precursor in peer-reviewed work |

**Bottom line for Brumadinho:** the only robust pre-failure satellite precursor in the peer-reviewed record is Sentinel-1 SAR-based deformation. Sentinel-2 multispectral alone is **not** a sufficient signal source for this case.

## 6. Implication for SatDiff's "pure Sentinel-2" story

The plan's Phase 1.5 and Phase 2.7 kill criteria explicitly anticipate this. The three honest options:

1. **Add Sentinel-1 SAR to the pipeline.** Ingest published ISBAS/SBAS-like deformation summaries as one of the physical-diff inputs to the VLM. The VLM's role becomes "translate deformation + multispectral context + contract into claim-framed output." This is the most rigorous path and the one most aligned with what production would actually look like.
2. **Narrow the Brumadinho claim.** Don't claim pre-failure detection from Sentinel-2. Instead, demonstrate the *interpretation architecture* using known-published deformation signals as input, and show the VLM producing the contract-framed output that human analysts produce today. This is honest but less visually dramatic.
3. **Pivot Brumadinho entirely.** Reserve Brumadinho as context/narrative and pick a primary case where Sentinel-2 is the natural sensor (illegal mining expansion, flaring, EUDR deforestation, Jagersfontein post-failure-signal analysis).

Recommendation: proceed to Jagersfontein research before deciding. Jagersfontein may have stronger visible-spectrum precursors (its failure mechanism and setting differ), in which case the two cases together justify Option 1 (SAR + multispectral fusion) as the honest pipeline. If Jagersfontein is also SAR-dominant, Option 3 gets stronger.

## Sources

- [Grebby et al. 2021, *Communications Earth & Environment*](https://www.nature.com/articles/s43247-020-00079-2)
- [AGU Landslide Blog commentary on Grebby 2021](https://blogs.agu.org/landslideblog/2021/01/08/brumadinho-prediction/)
- [Preventionweb / U. Nottingham press release](https://www.preventionweb.net/news/view/75655)
- [Du et al. 2020, Sentinel-1 SBAS/PSI, *Remote Sensing*](https://www.mdpi.com/2072-4292/12/21/3664)
- [Alves et al. 2022, Sentinel-2 NDVI analysis, IntechOpen](https://www.intechopen.com/chapters/85113)
- [Silva et al. 2021, *Environmental Monitoring and Assessment*](https://link.springer.com/article/10.1007/s10661-021-09417-z)
- [ScienceDirect: 2019 Brumadinho tailings dam collapse — possible cause and impacts](https://www.sciencedirect.com/science/article/pii/S0303243420300192)
- [Robertson et al. 2019, Expert Panel Final Report (PDF)](https://bdrb1investigationstacc.z15.web.core.windows.net/assets/Feijao-Dam-I-Expert-Panel-Report-ENG.pdf)
- [AGU Landslide Blog summary of Expert Panel report](https://blogs.agu.org/landslideblog/2020/01/20/brumadinho-tailings-disaster/)
- [Nature 2023: slip surface mechanism of delayed failure](https://www.nature.com/articles/s43247-023-01086-9)
- [WTW 2020: Tailings facilities and dam failure — risk and insurance perspective](https://www.wtwco.com/en-US/Insights/2020/03/tailings-facilities-and-dam-failure-from-a-risk-management-and-insurance-perspective)
- [Munich Re: Risk-prone dams](https://www.munichre.com/en/insights/infrastructure/risk-prone-dams.html)
- [NHESS 2021: Modelling Brumadinho, loss-of-life, and reduction](https://nhess.copernicus.org/articles/21/21/2021/)
- [Insurance Journal: Vale $7 B settlement](https://www.insurancejournal.com/news/international/2021/02/04/600073.htm)
- [Insurance Journal: Vale $56 M SEC settlement](https://www.insurancejournal.com/news/international/2023/03/29/714204.htm)
- [Australasian Mine Safety Journal: 2016 Vale internal risk assessment](https://www.amsj.com.au/2016-vale-tailing-dam-risk-assessment-said-loss-potential-high/)
- [World Mine Tailings Failures: Brumadinho engineering history](https://worldminetailingsfailures.org/corrego-do-feijao-tailings-failure-1-25-2019/)
