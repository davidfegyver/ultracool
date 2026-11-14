# Brown-dwarf candidate verification with the Ultracool Browser pipeline

Slice: Discovery. Date: 2026-11-14. Everything is under `/data/research/discovery/`. The repo was not edited.

## Conclusion

**One previously unverified brown dwarf now has independent characterization: CWISE J231728.89-670001.1 (= WISE J231728.42-665959.3, "J2317-6700").**
- **What was known before:** SIMBAD lists it as `BD?` with no spectral type. Its only reference is Rothermich et al. 2024 (AJ 167, 253; arXiv:2403.04592). That paper gives a *photometric estimate* of "(T6)" and lists it as a candidate wide companion of the K-dwarf pair HD 219509/HD 219495 (GJ 4321/4322) at 227". The pairing scored *below* their 90 % threshold. It is not in the SPIFF table, and Gaia DR3 has nothing within 4".
- **What we add:**
  1. **First spectrum.** The SPHEREx DR1+QR3 0.75-5 µm spectrum uses 453 frames, 89 channels. It is a textbook T-dwarf SED: J peak 18σ, H peak 14σ, strong 1.4 µm H₂O, a CH₄ trough at 3.0-3.6 µm (0.4 ± 1.0, i.e. no flux), a 4.1 µm peak at 15σ, and CO depression at 4.3-4.7 µm.
     - SPIFF-template typing gives **T6** (χ²ᵣ 1.69). T7 is next at 2.17 and T5 at 2.31.
     - The type is stable in every jackknife: per SPHEREx epoch, first/second half, and with 5 % or 10 % calibration error added.
     - The current production pipeline (template + 5 % errors) prefers T5 (χ²ᵣ 1.56) over T6 (1.64).
     - **Adopted type: T5.5 ± 1.**
  2. **Proper motion from our own 2010-2026 images.** Our value is (μα*, μδ) = **(+419 ± 30, −236 ± 30) mas/yr**, about 0.48"/yr at ~15σ.
     - Three association methods agree: per-visit, catalog-free track, and 2-yr deep epochs.
     - SPHEREx 2025/26 positions continue the WISE track.
     - The production `/summary` independently gives (431 ± 23, −251 ± 23) at 22σ.
     - CatWISE2020 gives (437 ± 31, −288 ± 29). This is consistent (Δ ≈ 1.3σ).
  3. **Colour.** Our own W1−W2 is 2.08 ± 0.12 (production 2.19 ± 0.11; CatWISE 1.83). VHS has J−Ks = −0.25 (CH₄-blue). Both fit a mid-T.
  4. **Distance.** We calibrate on the T6 2MASS J1122+2550 (ϖ = 62.9 mas, our own W2 = 14.14, so M_W2 = 13.13). That gives J2317 a spectrophotometric distance of **27-30 pc** (±20 %). This is the same distance as HD 219509/219495 (ϖ = 35.14 mas, 28.5 pc).
  5. **The companion claim does not hold.** Our PM differs from the host's (364, −410) mas/yr by Δμδ ≈ 170 mas/yr (~5-6σ, ≈ 23 km/s at 28.5 pc). A bound companion at ~6,500 au should differ by < 1 km/s. So J2317 is **co-distant but not co-moving**, which supports Rothermich's sub-threshold classification. Our PM systematics, measured on the two validation T dwarfs, are ≲ 40 mas/yr, too small to close a 170 mas/yr gap.
  6. **Not a contaminant.** The AllWISE counterpart is in the Assef et al. 2018 WISE AGN-candidate catalogue (R90/C75). The 0.48"/yr motion and the T-dwarf spectrum rule out an AGN. This is a concrete example of why colour-only selection is not enough.
- **Confidence:** high that it is a field T5-T6 dwarf at ~28 pc (moves at 15-22σ, spectrum independently typed with χ²ᵣ ≈ 1.6). Moderate that it is *not* bound to GJ 4321/4322.
- **Caveats:**
  - This is SPHEREx R ≈ 40-130 spectrophotometry, not a slit spectrum.
  - Our WISE parallaxes are not reliable (validation: 2M0415 gives 165 ± 25 vs 174 mas, but J1122 gives −100 ± 48). The distance is therefore spectrophotometric only.
  - Literature check: SIMBAD (Harvard mirror), VizieR and web search. ADS full-text was not searched (no token). A 2025-26 paper typing it could exist without our seeing it.

**Second tier: motion-verified, but no usable spectrum.**
- **J1925+2901** (CWISE J192537.88+290159.0):
  - Prior status: photometric [T8.5] in the Kirkpatrick+2021 20-pc census.
  - Motion: 2-yr deep W2 epochs give (137 ± 24, −156 ± 24) mas/yr (production 0.21"/yr, 4σ; CatWISE 0.26"/yr). The source is a 3-4σ blip per visit and 8σ per 2-yr epoch, undetected in W1, so W1−W2 > 2.34.
  - Spectrum: unreliable because of crowding at b ≈ +7°. The SPHEREx 3.0-3.6 µm flux is −14 ± 2 (negative at 6σ), and the 4.3-4.7 µm flux is about 4× below the W2 prediction. The "T6" template match is therefore not trusted.
- **J0756-6001** (WISE J075648.07-600127.4):
  - Prior status: photometric T6.5 candidate (Kirkpatrick+2021).
  - Motion: (328 ± 28, −727 ± 28) mas/yr deep (production 0.91"/yr at 27σ). That implies v_tan ≈ 90-100 km/s at ~25 pc, a thick-disk or halo kinematics hint.
  - Spectrum: dominated by neighbours (crowded field).
- **J0854-5020** (CWISE J085401.22-502028.1):
  - Prior status: photometric T6 candidate.
  - Motion: about 0.93"/yr (production 0.95"/yr at 14.5σ). The source is faint (W2 15.4), in the Galactic plane, and undetected in W1.
  - Spectrum: none (background over-subtraction in a crowded field).
- **J1952-7300** (WISE J195228.10-730047.3):
  - Prior status: photometric T2 (Kirkpatrick+2021).
  - Motion: (240 ± 25, −345 ± 25) mas/yr.
  - Spectrum: clearly T-like (deep 1.4 µm H₂O, CH₄ edge, CH₄ trough at 3.3 µm, 4.1 µm peak). The best template is T4/sdT4 with χ²ᵣ = 18 even with a 5 % floor. **Type ≈ T2-T4, low confidence on the subtype.** A W2 ≈ 12 star 10" away probably contaminates the 6" SPHEREx pixels.
- **J1402+1021** (CWISEP J140247.83+102132.6):
  - Prior status: Meisner+2020 Spitzer candidate.
  - Motion: (−151 ± 25, 33 ± 25) mas/yr (CatWISE −178, +40).
  - Spectrum: shows H₂O. Best match sdT4 ≈ sdM9.5 (χ²ᵣ 9). It sits on a bright-star halo. **L/T-transition dwarf, type unconstrained.**

**No new brown dwarf was discovered.** Every SPIFF "New Candidates" object we tested turned out to be spurious (see below), and no field mover without a prior catalogue entry turned up.

**The most useful negative result:** the bright CWISE-designated "T/Y" entries among SPIFF's 4416 `New Candidates` (Gagné et al. 2026) are mostly not brown dwarfs. All 7 we tested are artifacts, a known T dwarf, or contaminants:
- **Diffraction spikes:** J2011-0624 and J0104+1244 (CatWISE `ab_flags` = D). The "source" is a static spike; SPIFF typed one as T7 and our pipeline typed noise as "sdT4, χ²ᵣ 1.5".
- **Halo of a bright star:** J0109-4652 sits on the wing of L 293-63. CatWISE gives a spurious 1.7"/yr; PSF subtraction finds nothing ≥ 5σ.
- **Scattered light near IRC+10216:** J0946+1355 lies on a streak from IRC+10216 (CW Leo, the brightest 5 µm source in the sky). Clusters of 3-5 SPIFF "T dwarfs" within 0.5° of IRC+10216 and of RW LMi (CIT 6) are the same phenomenon.
- **Embedded YSO:** J0807-3443 (IRAS 08057-3434) is static. CatWISE claims 0.81"/yr; we find (−36 ± 20, 36 ± 31). Its SPHEREx spectrum shows 3.05 µm H₂O-ice and 4.27 µm CO₂-ice absorption.
- **M33:** J0133+3048 is a static M33 source that SPIFF typed "Y0".
- **Already known:** J1122+2550 is the known T6 2MASS J11225550+2550250, not a new candidate. SPIFF missed the match because of its 1.1"/yr motion.

## Method

All code is in `/data/research/discovery/`. It runs the Ultracool Browser backend in-process with a private cache (`cache/`), with IRSA calls strictly sequential. The backend copy is frozen in `snap/app`, taken 2026-11-14 ~18:35 UTC, PIPELINE_VERSION 2.

1. **Candidate lists**
   - **SPIFF** (Gagné et al. 2026, arXiv:2604.22012), dataset `New Candidates`: 4416 rows, none with a literature type. The paper calls these low-S/N QR2 spectra that "hint at" UCD features. We kept the 1832 with L/T/Y autotypes → `spiff_new_candidates_LTY.csv`.
   - **CatWISE2020 match:** IRSA Gator multi-object upload, 5" radius; IRSA TAP sync and async both returned 502. 989 matched → `candidates_catwise.csv`.
   - **SIMBAD** (Harvard TAP) `otype='BD?'` with no spectral type: 2017 objects → `simbad_bd_candidates_nosptype.csv`. Of these, 1351 are not in the SPIFF table within 20" → `simbad_bdq_not_in_spiff.csv`, with CatWISE added → `simbad_bdq_not_in_spiff_catwise.csv`.
   - **Contamination screen** (`screen.py` → `candidates_screened.csv`):
     - stars with K < 4 within a K-dependent radius;
     - M31, M33, LMC, SMC;
     - candidate overdensity (≥ 2 other SPIFF candidates within 0.5°).
     - Caveat: K-band misses mid-IR-bright AGB stars such as IRC+10216. The overdensity flag catches them.
   - **Run lists:** `run_list.txt`, `run_list2.txt`, `run_queue.txt`.
2. **Selection**
   - W2 ≲ 15.3; for reference, SPIFF reaches S/N ≈ 10 per channel at W2 = 14 in QR2.
   - Significant CatWISE PM and red W1−W2.
   - Controls: two literature T dwarfs (2M0415−0935 T8, plus J1122+2550 T6 which came in as a candidate), one static red source (J0442−3855), and one galaxy-field source (J0133+3048).
3. **Per-object verification** (`verify.py`, `track.py`, `forced.py`, `wphot.py`, `psfsub.py`, `plot.py`, `summarize.py`)
   - **Spectrum:**
     - The app's own sequence uses a 0.06° grid at 2.75"/px and every SPHEREx DR1+QR3 frame (235-577 per object).
     - Photometry is native-pixel forced aperture photometry with VARIANCE, FLAGS and EPSF aperture correction.
     - `spectral.classify` fits the 47 SPIFF templates.
     - Jackknife over epochs and halves; we also added 5 %/10 % calibration floors.
   - **Astrometry:**
     - For each WISE visit (2010 cryo plus NEOWISE 2014-2024), we stack all W1/W2 L1b exposures (≤ 40, not the app's 8) on the grid with sigma clipping.
     - We fit 2-D Gaussian centroids to every source above 6σ.
     - Each visit's zero point is tied to field stars seen in ≥ 60 % of visits.
     - The fit is a weighted least-squares solution for PM (+ parallax), with errors scaled by √χ²ᵣ.
     - Three independent associations:
       - (a) nearest detection within 6.9" of the CatWISE-PM prediction;
       - (b) catalog-free tracking from the first-epoch detection;
       - (c) for faint sources, 2-yr deep W2 epochs centroided from one *static* starting guess, so the fit is not steered toward the catalog motion.
     - A 20 mas/yr per-axis systematic is added in quadrature.
   - **Colour:** our own W1/W2 come from the app's 8.25" visit photometry (CatWISE-calibrated aperture correction). The W1 3σ limit gives a W1−W2 lower bound.
   - **Cross-check:** the production `/summary` and `/movers` for J1925, J0756, J0854 and J2317 (files `prod_*_summary.json`).
   - **Literature:**
     - SIMBAD identifiers and bibliography within 60";
     - Gaia DR3 within 4-6" (Harvard VizieR);
     - the Kirkpatrick et al. 2021 20-pc census (J/ApJS/253/7);
     - all VizieR tables within 30" of J2317;
     - the Rothermich+2024 arXiv HTML;
     - web search.
4. **Validation**

   | object | lit. PM (mas/yr) | ours (visit fit) | lit. SpT | our SPHEREx type | W1−W2 lit / ours |
   |---|---|---|---|---|---|
   | 2MASS J0415−0935 | (2193, 527) | (2206 ± 6, 543 ± 6) | T8 | T8 (χ²ᵣ 9.6, high S/N) | 2.9 / 2.88 ± 0.03 |
   | 2MASS J1122+2550 | (−1012, −324) Best+20; CatWISE (−1040, −360) | (−1035 ± 13, −362 ± 13) | T6 | T7 (χ²ᵣ 1.85; T6 next) | — / 2.13 ± 0.04 |

   - Agreement is 13-38 mas/yr per axis. That is the source of the 20 mas/yr systematic floor; it may be optimistic for objects with few reference stars.
   - 2M0415 parallax: 165 ± 25 mas vs 174.3. The J1122 parallax fails (−100 ± 48), so parallaxes are not used.

## Candidate table

PM in mas/yr. "Ours" is the per-visit fit, or the 2-yr deep-epoch fit (marked d) for faint sources. Errors include the 20 mas/yr systematic. W1−W2 is ours unless marked CW (CatWISE). Types in brackets are photometric estimates from the literature.

| name (designation) | RA, Dec (deg, CatWISE ep. 2015.4) | CatWISE PM | our PM | W1−W2 | SPHEREx type (χ²ᵣ) | literature status | verdict |
|---|---|---|---|---|---|---|---|
| **J2317-6700** CWISE J231728.89-670001.1 | 349.37038, −67.00031 | (462 ± 31, −299 ± 29) | (419 ± 30, −236 ± 30); d (415 ± 31, −248 ± 31); prod (431 ± 23, −251 ± 23) | 2.08 ± 0.12 | **T6** (1.69; T7 2.17, T5 2.31); prod T5 (1.56) | BD?, phot. (T6), low-prob. companion of GJ 4321/4322 (Rothermich+24) | **verified T5-T6 dwarf, ~28 pc; co-distant, not co-moving with GJ 4321/4322** |
| J1925+2901 CWISE J192537.88+290159.0 | 291.40785, 29.03308 | (173 ± 20, −192 ± 22) | d (137 ± 24, −156 ± 24); prod (167 ± 58, −133 ± 58) | > 2.34 (CW 2.71) | unreliable (crowded; "T6" 4.6) | [T8.5] Kirkpatrick+21 | motion + colour confirmed; spectrum inconclusive |
| J0756-6001 WISE J075648.07-600127.4 | 119.20143, −60.02525 | (383 ± 21, −782 ± 22) | d (328 ± 28, −727 ± 28); prod (393 ± 39, −823 ± 39) | 1.59 ± 0.11 (CW 2.35; W1 blended) | contaminated (sdM9.5, 25.6) | [T6.5] Kirkpatrick+21 | motion confirmed (0.80-0.91"/yr) |
| J0854-5020 CWISE J085401.22-502028.1 | 133.50512, −50.34114 | (−599 ± 20, 598 ± 20) | d (−773 ± 62, 517 ± 62); prod (−746 ± 69, 595 ± 69) | > 1.84 (CW 1.49) | insufficient (crowded) | [T6] Kirkpatrick+21 | motion confirmed |
| J1952-7300 WISE J195228.10-730047.3 | 298.11856, −73.01373 | (299 ± 21, −378 ± 22) | (245 ± 26, −348 ± 26); d (237 ± 23, −342 ± 23) | 0.95 ± 0.03 | T-like, sdT4/T4 (21.6; 17.9 with 5 %) | [T2] Kirkpatrick+21 | motion confirmed; T2-T4, subtype low confidence |
| J1402+1021 CWISEP J140247.83+102132.6 | 210.69925, 10.35911 | (−178 ± 15, 40 ± 15) | (−150 ± 24, 32 ± 24) | 0.86 ± 0.09 | sdT4 ≈ sdM9.5 (9.1) | Meisner+20 candidate; SIMBAD PM (−140, 57) | moving L/T dwarf; type unconstrained (bright-star halo) |
| J0748-0140 PSO J117.0600−01.6779 | 117.05987, −1.67822 | (−367 ± 23, −401 ± 23) | blended: d (−246 ± 29, −324 ± 29) | 0.93 (W1 blended; CW 1.77) | contaminated (sdM9.5, 13) | ϖ 42.6 ± 3.7, PM (−361, −360) Best+20 | known; 6" neighbour spoils our data. M_W2 = 12.4 (T-like) from lit. ϖ |
| J1531-3306 CWISE J153143.38−330657.3 | 232.93077, −33.11594 | (−28 ± 38, −308 ± 38) | not separable | — (CW 3.74) | = neighbour star | [Y0] Kirkpatrick+21 | not testable: 8" from bright star |
| J0442-3855 WISE J044214.18−385515.8 | 70.55920, −38.92104 | (42 ± 25, −5 ± 25) | (−8 ± 24, 12 ± 24): **static** | > 3.36 (CW 3.11) | featureless, rising to 5 µm ("d_sdT1" 2.7) | BD? Kirkpatrick+21 (ϖ −12.4 ± 4.9) | **red but static → extragalactic contaminant** |
| J0109-4652 CWISE J010931.47−465245.8 (SPIFF NC, "L0γ pec") | 17.38113, −46.87939 | (1502 ± 47, −834 ± 47) | no source (0/44 visits; PSF-subtracted ≤ 2σ in one season only) | — | = L 293-63 (M0) | SPIFF New Candidate | **artifact: bright-star PSF wing** |
| J0946+1355 CWISE J094640.40+135550.6 (SPIFF NC, "T1") | 146.66835, 13.93074 | (522 ± 19, 472 ± 19) | no point source (streak) | — | continuum (sdM9.5) | SPIFF NC | **artifact: IRC+10216 scattered-light streak** |
| J2011-0624 CWISE J201121.52−062438.1 (SPIFF NC, "T7") | 302.83969, −6.41061 | (−93 ± 21, −277 ± 21) | static spike | — | noise ("sdT4" 1.5) | SPIFF NC | **artifact: diffraction spike** (CatWISE ab=D) |
| J0104+1244 CWISE J010458.32+124444.5 (SPIFF NC, "T3") | 16.24300, 12.74570 | (190 ± 20, 187 ± 20) | static spike | — | insufficient | SPIFF NC | **artifact: diffraction spike** (ab=D) |
| J0807-3443 CWISE J080741.06−344335.9 (SPIFF NC, "L3 pec") | 121.92110, −34.72664 | (790 ± 25, −201 ± 25) | (−36 ± 28, 36 ± 37): **static** | 2.04 ± 0.26 | ice absorption 3.05/4.27 µm (not UCD) | IRAS 08057-3434 (FIR) | **embedded YSO, spurious PM** |
| J0133+3048 CWISE J013306.71+304815.2 (SPIFF NC, "Y0") | 23.27796, 30.80422 | (−23 ± 28, −87 ± 28) | d (7 ± 34, 27 ± 34): static | > 2.66 | insufficient | in M33 disc | **M33 source, not a UCD** |
| J1122+2550 CWISE J112254.10+255019.2 (SPIFF NC, "T3") | 170.72638, 25.83896 | (−1040 ± 15, −360 ± 15) | (−1035 ± 24, −362 ± 24) | 2.13 ± 0.04 | T7 (1.85) | **known T6** 2MASS J11225550+2550250 | known (validation) |
| VAL 2MASS J0415−0935 | 63.83143, −9.58519 (J2000) | lit. (2193, 527) | (2206 ± 21, 543 ± 21) | 2.88 ± 0.03 | T8 (9.6) | T8 | validation passes |

The side candidate for Main is below.

**Side candidate for Main: CatWISE J153433.97−104218.7** (233.64156, −10.70521; W1 18.14 ± 0.15, W2 16.50 ± 0.11)
- **CatWISE PM** is (−154 ± 112, −90 ± 131) mas/yr: 1.4σ, **not significant**.
- **Catalogs:** no SIMBAD object within 30" and no Gaia DR3 within 4". NED was not reachable or tried.
- **Our data:**
  - App photometry gives W2 = 38 ± 17 µJy (≈ 2σ, 16.6 mag) and W1 = −12 ± 7 µJy, so W1−W2 > 1.3 (3σ).
  - 3-yr and 7-yr deep W2 stacks reach only ≤ 3-4.5σ, with no consistent centroid track, so no PM can be measured (`out/J1534-1042_montage.png`).
  - SPHEREx: insufficient data.
- **Verdict:** too faint for our data, with no evidence of motion. A red, slow, isolated W2 = 16.5 source is more likely an AGN or galaxy than a distant L/T dwarf, but this is unproven either way.

## Files

- **Candidate lists (CSV):**
  - `spiff_new_candidates_LTY.csv` (1832)
  - `candidates_catwise.csv`
  - `candidates_screened.csv` (51 bright, with contamination flags)
  - `simbad_bd_candidates_nosptype.csv` (2017)
  - `simbad_bdq_not_in_spiff.csv` / `simbad_bdq_not_in_spiff_catwise.csv` (1196 with CatWISE)
  - `simbad_xmatch_raw.csv`
  - `catwise_gator*.tbl`
- **Results:** `results.csv` (one row per verified object, from `summarize.py`) and `out/<name>.json` (all epochs, detections, fits, spectrum).
- **Montages:** `out/<name>_montage.png`. Each has W2 epoch stacks 2010→2024, SPHEREx > 3.8 µm stacks 2025-26, the astrometric track and the SPHEREx spectrum with its best template. The key ones are:
  - `out/J2317-6700_montage.png`
  - `out/J1925+2901_montage.png`
  - `out/J0756-6001_montage.png`
  - `out/J1952-7300_montage.png`
  - artifacts: `out/J0109-4652_montage.png`, `out/J0946+1355_montage.png`, `out/J2011-0624_montage.png`, `out/J0807-3443_montage.png`
  - validation: `out/VAL_2M0415_montage.png`
- **Production cross-checks:** `prod_J2317_summary.json`, `prod_J2317_movers.json`, `prod_J1925_summary.json`, `prod_J0756_summary.json`, `prod_J0854_summary.json`.

## Findings for the pipeline (not changed; backend slice owns the code)

1. **SPHEREx forced photometry in crowded fields** (|b| ≲ 20°): fluxes go strongly negative, e.g. J1925 3.0-3.6 µm at −6σ and J0854 −100 to −250 at 1-2 µm. The `SOURCE`-masked annulus probably over-subtracts the background. Template "matches" on such spectra are meaningless, so the contamination flag should also trip on significantly negative bins.
2. **Template typing of noise or spike light can still come out as "match" with χ²ᵣ ≈ 1.5** (J2011-0624 "sdT4", J0442 "d_sdT1"). This needs a minimum-S/N-at-4 µm requirement, and/or a positional check that a point source is actually detected in the SPHEREx stack.
3. **App lesson on artifacts ("Real or ghost?"):** the IRC+10216 / RW LMi fields and CatWISE `ab_flags` = D sources are good teaching cases.

## Not done / not verified

- No ADS full-text search, so a 2025-26 spectroscopic paper on J2317 cannot be excluded. SIMBAD shows none.
- No PSF-fitting photometry for crowded fields.
- No parallaxes beyond validation.
- 3 queued lower-priority candidates were skipped for time: J0949+1214 (a duplicate of the IRC+10216 artifact case), J0217-0347, and UHS J1910+3425.
- Most of the 4416 SPIFF New Candidates are fainter (W2 > 15.3) and untested.
