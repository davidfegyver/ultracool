# Brown-dwarf candidate verification with the Ultracool Browser pipeline

## 2026-11-15 night run: remaining queue + second screen (Candidates slice)

**Bottom line: no new brown dwarf, and no object got a new robust spectral type.** 21 fields were processed. One SPIFF candidate is an artifact. One SIMBAD `BD?` is a static red source (CatWISE PM spurious). One known T3.5 *control* fails because of blending. The rest are known photometric-type T/Y candidates: motion confirmed, SPHEREx type not robust.

**What was done**
- **Queue:** J0217-0347, UHS J1910+3425 and J0949+1214.
- **Second screen** (`scripts/screen2.py` → `screen2_all.csv`, `screen2_pass.csv`; `bright.py` → `shortlist_vetted.csv`):
  - Inputs: 989 SPIFF NC + 1196 SIMBAD `BD?` rows, after dropping 843 rows without a CatWISE match.
  - Cuts: |b| > 20°, W2 < 15.5, CatWISE PM ≥ 0.15″/yr and ≥ 5σ, W1−W2 ≥ 1, ab = 00, not near IRC+10216 (1.5°), RW LMi (1°), M31, M33, LMC or SMC, not already tested.
  - Result: 6 pass, all SIMBAD `BD?`. **No SPIFF NC passes.** The SPIFF NC with PM ≥ 0.15″/yr at ≥ 5σ are either W2 > 15.5 or sit in the IRC+10216/RW LMi clusters.
  - Removed: HD 12894B and HD 33473C (W2 < 8, CatWISE photometry belongs to the host).
  - Added 14 near-misses (one soft cut missed narrowly).
  - Re-checked against CatWISE2020 **offset-corrected** PMs (VizieR II/365, CfA mirror) and AllWISE W2 < 8 within 3′ (none found). This dropped CWISEP J084726.55+233558.1 (4.9σ).
  - **18 objects processed.**
- **Per object** (`run3.sh`, one IRSA field at a time):
  - Spectrum, colour, motion and movers from the **current production code**: dev API on :8003, code snapshot `/data/devcache/candidates_code/backend_20261114T2353Z` = HEAD 81c83b4, PIPELINE_VERSION 5, hashes in `CODE_STATE_dev_api.txt`. Stored in `out/<name>_dev.json` and attached as `dev` in `out/<name>.json`.
  - Astrometry from the frozen snapshot: per-visit, track, 2-yr deep. The deep fit is the one marked "d".
  - **New blind self-check `blind.py`:** all ≥ 4σ peaks in 2-yr W2 stacks, linked into straight tracks. It uses no catalogue PM, only the CatWISE *position* to pick the track.
  - **New `variants.py`:** type under 5 fitting variants (with/without template spread, 1–2.5 µm only, 2.5–5 µm only, errors ×1.5).
  - **New `neighbours.py`:** 2MASS/Gaia within 15″ (`out/nb_<name>.json`).
  - Literature: `lit.py` → `out/lit_<name>.json` (SIMBAD Harvard TAP: ids, refs, mesSpT, 30″ cone; VizieR all-catalogue 10″ on the CfA mirror). Also UltracoolSheet v2.1.0 (Zenodo 15802304, `ext/`). Montages: `montages/<name>_montage.png`. Table: `results.csv` (`prod_*`, `deep_*`, `blind_*` columns).
- **Lessons applied** from `research/verification/J2317_ADVERSARIAL.md`:
  - CatWISE PMs quoted below are VizieR II/365, offset-corrected, except the 3 queue objects, whose CatWISE values are IRSA uncorrected.
  - Types are given as ranges.
  - Photometric and spectroscopic literature types are kept apart.
  - J2317 Conclusion and table row were updated to the verified values.
- **Controls first.**
  - Blind method on known objects:
    - 2M0415 (T8): (2206 ± 10, 534 ± 10) vs literature (2193, 527).
    - J1122+2550: (−1027 ± 12, −361 ± 12) vs (−1012, −324).
    - Static J0442−3855: (2 ± 12, 6 ± 12).
    - J2317: (413 ± 26, −247 ± 26).
    - Spike J2011−0624: incoherent (χ²ᵣ 6.2).
    - **Per-axis agreement with the literature is ≤ 37 mas/yr.**
  - Production typing:
    - 2M0415 T8 → T8.
    - J1122 T6 → T5 (T7 at Δχ²ᵣ 0.03).
    - **PSO J136.5380−14.3267 (lit. NIR T3.5, Best+2020, ϖ 37.4 ± 4.1, PM (−241, 96)) → "warmer than M8: probably an ordinary star", and our astrometry is static.** This control fails. 2MASS stars of J = 14.8, 16.3 and 16.6 lie at 10.2″, 7.0″ and 4.8″ (`out/nb_J0906-1419.json`). The montage shows the detections are the neighbour.
  - `variants.py`: even 2M0415 is not "separable" under every variant (2.5–5 µm alone gives T5, 1–2.5 µm alone gives Y1). So the every-variant rule is too strict for this data; it was used only as a warning flag.
- **Step 4 not done.** The Spectra crowded-field fix (neighbour-aware PSF photometry, `research/spectra/REPORT.md`) exists only uncommitted in the working tree. I ran out of request budget before re-running the summaries with it. **All spectral results below are from HEAD 81c83b4 code.** This re-run is the first follow-up, especially for J0630, J0906, J0601, J1241 and J1639, which all have J ≲ 16 neighbours inside 12.3″.
- **All 21 fields completed.** J0019-0943's first dev field failed with an IRSA SIA 502 (`logs/J0019-0943_dev_error_attempt1.json` in the work directory); the retry succeeded.

**Table (tonight).** PM in mas/yr. d = 2-yr deep epochs, b = blind (both +20 mas/yr floor in `results.csv`), prod = production. SpT = production best template (snapshot code 81c83b4).

| name | CatWISE PM (II/365) | our PM d / b / prod | W1−W2 (prod) | SPHEREx (prod) | neighbours ≤ 12.3″ | literature | verdict |
|---|---|---|---|---|---|---|---|
| J0217-0347 SPIFF NC "T5" | IRSA (−198, 283) | none coherent (d −17 ± 182) | 0.71 | no detection | – | SPIFF only | **artifact: diffraction-spike streak** (ab = D0; montage) |
| J1910+3425 SPIFF NC "L2" | IRSA (78, −17) | (77, 18) / (77, 21) / (75, −1) 4.3σ | 0.18 | M8 1.01 (sdM9.5, L0 within 0.25) | – | SPIFF only | late-M/early-L, slow; **consistent with SPIFF; not a T/Y** |
| J0949+1214 SPIFF NC "T5" | IRSA (−460, −380) | (−183 ± 106, −38) / (−106 ± 129, −94) | 2.44 | no detection, 6 negative bins | – | SPIFF only | **artifact (IRC+10216 field), as expected** |
| J0601-5922 | (−137, 289) | (−239 ± 16, 461) / (−230 ± 61, 457) / (−248, 431) 36σ | 1.04 | "warmer than M8" | J = 14.0 at 14.6″, G = 16.0 at 14.5″ | [T6.5] phot. Kirk21 | known phot. candidate; moving, but **our PM differs from CatWISE by ~100/170** (blend?); spectrum = neighbour |
| J0906-1419 (PSO J136.5380−14.3267) | (−225, 81) | static (19, −36) = neighbour | 0.46 | "warmer than M8" | 3 stars J 14.8–16.6 at 4.8–10.2″ | **T3.5 NIR** Best+20 | **control failure: blending** |
| J2017-3421 | (172, 280) | (239 ± 19, 276) / (235 ± 26, 275) / (208, 301) 12σ | > 4.2 (CW 3.30) | T3 2.56 (T5 2.71, T1 3.05; 4 bins S/N > 5) | – | [T7.5] CH₄-imaging Tinn18 / K19 | moving; **SPHEREx type unconstrained** (T1–T5 vs colour ≈ late T) |
| J0223+0318 | (255, 2) | (226 ± 31, −45) / (241 ± 35, −47) / (444, −99) | 0.85 | T3 0.76 on 45 bins (5 at S/N > 5) | – | T3.5 phot. Skrzypek+16 | moving ~0.24″/yr (prod outlier); type unconstrained |
| J2011-4812 | (95, −411) | (68 ± 25, −349) / (65 ± 28, −344) / (63, −322) | 1.86 | "L7" 1.58 on noise (5 bins S/N > 5) | – | [Y0] phot. Meis20a | moving; **typing noise** |
| J1826-4652 | (−25, −354) | detections = host SIPS J1826−4652 (49, −185) | 0.29 | M8 2.73 (blend) | host J = 13.9 at 9.0″ | M8 phot. (Reylé+18); companion (Rothermich+24) | blended with host: not testable |
| J1900-3108 | (−22, −331) | (−79 ± 27, −265) / (−77 ± 44, −254) / (−116, −275) | > 1.79 | no detection | J = 15.9 at 13.0″ | [T9] Meis20b | moving (Δμα ≈ 57 vs CW) |
| J0630-3717 | (41, 254) | (74 ± 24, 238) / (73 ± 29, 238) / (52, 267) 10σ | > 1.41 (CW 2.23) | sdT4 2.71 (sdM9.5 3.05); 1–2.5 µm → sdM9.5, 2.5–5 µm → T3/T5 | **J = 15.7 star at 11.7″** | [T7] phot. Kirk21 | moving; **most promising spectrum, but contaminated at 1–2.5 µm** → T-like at 2.5–5 µm only; no type claimed |
| J1241-8200 | (311, −35) | b (254 ± 136, −20); d incoherent | 1.66 | "warmer than M8" | J = 15.0 at 12.2″ | [T8.5] Meis20a | spectrum = neighbour; motion weak |
| J1639+1840 | (−504, 146) | (−579 ± 93, −91) / (−566 ± 74, 17) / (−658, −4) 16σ | 2.00 | "warmer than M8" | J = 15.9 at 12.4″ | [T9.5] Kirk21; JWST photometry 2025AJ169.163A | moving (Δμδ ≈ 140 vs CW); spectrum = neighbour |
| J0225+1548 | (426, −67) | (408 ± 83, −32) / (304 ± 54, 52) / (374, 56) 5σ | > 3.07 | no S/N | – | Meis20a (Spitzer) | moving, too faint for SPHEREx |
| J2125-7308 | (287, −378) | (396 ± 46, −412) / (419 ± 73, −472) / (516, −396) | 2.51 | insufficient | – | [T8] Meis20b | moving; prod PM high vs CW |
| J0651-8355 | (−201, 253) | (−182 ± 24, 292) / (−163 ± 39, 272) / (−186, 307) 10σ | > 2.44 | "T3" 1.93 on noise (0 bins S/N > 5) | – | [T8] Meis20b | moving; **typing noise** |
| J1721+5950 | (−359, 16) 12σ | **(−2 ± 32, 3) / (−1 ± 31, −3) / prod 0.7σ** | 2.56 | insufficient | – | Meis20a (Spitzer) | **static: CatWISE PM spurious; red static source (likely extragalactic, cf. J0442)** |
| J1100+0946 | (−565, −87) | (−639 ± 52, −82) / (−656 ± 61, −64) / (−619, −48) | > 2.16 | insufficient | – | Meis20a | moving, too faint for SPHEREx |
| J0931+2325 | (−238, −557) | (−160 ± 62, −645) / (−157 ± 66, −655) / (−251, −513) | > 2.14 | no detection | – | Meis20a | moving, too faint |
| J1302+1911 | (86, −344) | (93 ± 37, −185) / (82 ± 48, −177) / (93, −200) 3.7σ | > 2.59 | "T8" 1.56 (d_sdT8, T9 equal; 1 bin S/N > 5) | – | Meis20a (Spitzer) | moving; **Δμδ ≈ 160 vs CatWISE**; typing noise |
| J0019-0943 | (−223, −274) | none coherent (d −54 ± 260, −164) | 0.95 | "warmer than M8" (S/N 47) | LP 704-85, J = 12.1 at 13.3″ | [T7] phot. Meis20b | spectrum and photometry = LP 704-85; not testable |

Literature notes: "[ ]" means a photometric type (Kirkpatrick+2019/2021 brackets; UltracoolSheet flag `photSpT`). None of the T/Y candidates has a spectroscopic type in SIMBAD, VizieR (all catalogues, 10″) or UltracoolSheet v2.1.0. For J0223 and J0225 the all-catalogue VizieR query failed (IncompleteRead), so only targeted catalogues were checked (`ext/targeted_vizier_J0223_J0225.txt`). Web searches on the designations gave no relevant hits. ADS full text was not searched (no token).

**Noteworthy (evidence paths)**
1. **J1721+5950 (CWISEP J172104.42+595047.7): CatWISE's 12σ motion is not real.**
   - Evidence: `out/J1721+5950.json` (`fit_deep`, `fit_blind`, `dev.summary.motion`), `montages/J1721+5950_montage.png`.
   - Three independent fits are consistent with zero motion.
   - W1−W2 2.56. A static red source is probably not a nearby brown dwarf. This is the same failure mode as J0442.
2. **J0630-3717 (WISE J063018.26−371735.5, phot. [T7])** is the best spectrum tonight: detection S/N 23 at 3.5–5 µm, 54 bins at S/N > 5.
   - Evidence: `out/J0630-3717.json` (`type_variants`), `out/nb_J0630-3717.json`, `ext/J0630_neighbours.txt`.
   - A J = 15.7 / G = 16.9 star sits inside the aperture at 11.7″, which explains the warm 1–2.5 µm part.
   - It should be re-run with the Spectra PSF fix before any type is claimed.
3. **Pipeline finding: the production contamination test is inactive for slow movers.** `spectrum_contamination` needs the target to have moved 31″, so it returns None below ≈ 0.5″/yr. Here, J0906 (a known T3.5), J0601, J1241 and J1639 were all told "probably an ordinary star" because of static neighbours inside 12.3″.
4. **Typing noise persists.** J2011-4812 ("L7") and J0651-8355 ("T3") pass the 3.5–5 µm S/N ≥ 5 gate with ≤ 5 channels at S/N > 5. A minimum number of S/N > 5 channels would stop these.
5. **Our PM disagrees with CatWISE II/365 at > 3σ in one axis** for J0601 (Δ ≈ 100, 170), J1639 (Δμδ ≈ 140) and J2125 (Δμα ≈ 110–230). For J0601 and J1639 the neighbour is the likely cause. These are not claims; our values are in the table.

## 2026-11-14 run (previous; J2317 parts updated 2026-11-15)
Slice: Discovery. Date: 2026-11-14. Everything is under `/data/research/discovery/`. The repo was not edited.

## Conclusion

**One previously unverified brown dwarf now has a spectrum-based characterization: CWISE J231728.89-670001.1 (= WISE J231728.42-665959.3, "J2317-6700").** Values below are the ones that survived the adversarial review in [`research/verification/J2317_ADVERSARIAL.md`](../verification/J2317_ADVERSARIAL.md) (2026-11-15).
- **What was known before:** SIMBAD lists it as `BD?` with no spectral type. Its only reference is Rothermich et al. 2024 (AJ 167, 253; arXiv:2403.04592). That paper gives a *photometric estimate* of "(T6)", derived from its W2 brightness at the host pair's parallax (their §V.1.2, Kirkpatrick+2021 M_W2–SpT relation; not from colours), and lists it as a low-probability (5.1 %) co-moving candidate of the K-dwarf pair HD 219509/HD 219495 (GJ 4321/4322) at 227". It is not in the SPIFF table or UltracoolSheet v2.1.0, and Gaia DR3 has nothing within 4" (nearest source ≈ 19").
- **What we add:**
  1. **First spectrum-based type we could find, confirming Rothermich's photometric (T6).** The SPHEREx DR1+QR3 0.75-5 µm spectrum uses 453 frames, 89 channels (35 at S/N > 3). It shows mid-T features: J and H peaks, 1.4 µm H₂O, a CH₄ trough at 3.0-3.6 µm, a 4.1 µm peak and CO depression at 4.3-4.7 µm.
     - Research snapshot: T6 (χ²ᵣ 1.69), T7 2.17, T5 2.31. Production v5 (template spread included): T5 (χ²ᵣ 1.56), T6 1.64. Near-IR only (1-2.5 µm) prefers T7-T6.
     - The T5/T6/T7 order flips with one fitting choice (template-spread weighting), so subtypes are not separable. T4 and earlier are excluded in every variant (Δχ² ≥ 22).
     - **Adopted type: ≈T6 ± 1 (mid-T).**
  2. **Proper motion from our own 2010-2026 images: ≈0.5"/yr.** Our value is (μα*, μδ) = (+419 ± 30, −236 ± 30) mas/yr.
     - Four of our methods agree: per-visit, catalog-free track, 2-yr deep epochs, and tonight's blind detect-and-link fit (413 ± 32, −247 ± 32) (`out/J2317-6700.json` → `fit_blind`).
     - The production `/summary` gives (431 ± 23, −251 ± 23), 21.8σ statistical only (≈16σ with the 20 mas/yr floor).
     - CatWISE2020 offset-corrected (VizieR II/365): (437 ± 31, −288 ± 29). AllWISE→VHS two-epoch (independent of our pipeline): (423, −266) ± 44. All agree within ≤ 1.3σ per axis.
  3. **Colour.** Catalogue W1−W2 ≈ 1.8 (CatWISE 1.83 ± 0.05, unWISE 1.79 ± 0.06), which fits a mid-T. Our own aperture photometry gives 2.08-2.19. It is biased red by a W1 that comes out 0.45 mag fainter than CatWISE; the cause is not known. VHS J−Ks = −0.25 ± 0.12 (CH₄-blue).
  4. **Distance ~31 pc (26-40 pc, photometric).** This uses the Kirkpatrick+2021 Table 13 M–SpT relation (RMS 0.31 mag) for T5-T6, not a single calibrator. The earlier "27-30 pc" relied on one calibrator, 2MASS J1122+2550, and is withdrawn. That object's parallax is 66.3 ± 2.3 mas (Kirkpatrick+2019), not 62.9, and it is 0.33 mag fainter than the T6 median. The distance is *consistent with* that of HD 219509/219495 (28.5 pc). For an unresolved equal-mass binary, multiply by 1.41.
  5. **Not a companion: we confirm Rothermich's 5.1 % co-moving probability.** Every PM estimate differs from the host's (364, −410) mas/yr by 140-180 mas/yr (≈ 20 km/s at 28.5 pc). A bound companion at ≥ 6,700 au would differ by < 1 km/s.
  6. **Not a contaminant.** The AllWISE counterpart is listed as an AGN *candidate* in Assef et al. 2018 (R90/C75). The motion and the T-dwarf spectrum rule out an AGN.
- **Confidence:** high that it is a field mid-T dwarf (≈T6 ± 1) at ~31 pc (26-40) that moves ≈0.5"/yr. High that it is not bound to GJ 4321/4322; that agrees with Rothermich+2024.
- **Caveats:**
  - This is SPHEREx R ≈ 40-130 spectrophotometry, not a slit spectrum.
  - The distance is photometric.
  - "First" means the first spectrum-based type we found in SIMBAD, VizieR, the UltracoolSheet v2.1.0, SPIFF and arXiv as of Nov 2026. ADS full text was not searched (no token).

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
| **J2317-6700** CWISE J231728.89-670001.1 | 349.37038, −67.00031 | (437 ± 31, −288 ± 29) VizieR II/365 corrected | (419 ± 30, −236 ± 30); d (415 ± 31, −248 ± 31); blind (413 ± 32, −247 ± 32); prod (431 ± 23, −251 ± 23) | ours 2.08 ± 0.12 (biased red, W1 too faint); catalogue CW 1.83 ± 0.05 | ≈T6 ± 1 (snap T6 1.69; prod T5 1.56, T6 1.64) | BD?, phot. (T6) from M_W2 at host ϖ, 5.1 % co-mover of GJ 4321/4322 (Rothermich+24) | **mid-T dwarf, first spectrum-based type, confirms Rothermich's (T6); ~31 pc (26-40); not a companion (confirms Rothermich)**; see `research/verification/J2317_ADVERSARIAL.md` |
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
