# First SPHEREx spectrum-based types for Rothermich+2024 companion candidates

Slice: Discovery 2. Date: 2026-11-15. Everything is under `research/discovery2/`. No repo code was edited; no docker; no commits; production was not touched.
Every number below comes from a file under `out/` or `raw/` (named in brackets). SPHEREx R ≈ 40–130 spectrophotometry is not a slit spectrum: "type" means a template match to it, with the validated accuracy of `research/spectra/REPORT.md` (literature type inside our range for 16/24; ±1 subtype for 16/24).

## Bottom line

12 candidates passed the screen and were measured. **Three objects get a first spectrum-based type that survives every self-check. None of them is a confirmed companion.**

| object | photometric type (Rothermich+24) | our SPHEREx type | companion verdict |
|---|---|---|---|
| **CWISE J102322.00−204549.9** (J1023−2045) | (L3) | **late-M, ≈M8–M9** (L3 excluded, Δχ² ≈ 490) | **refuted.** Not bound to CWISE J102244.48−204204.5: Gaia DR3 Δμ = 19 mas/yr (8.6 km/s, bound limit 0.14 km/s), parallax 2.9σ apart. This confirms Rothermich's 0 %. |
| **CWISE J124033.48+460544.7** (J1240+4605) | (M9) | **≈L1 ± 1** (M9–L3) | **not confirmed.** It moves with its host (three PMs agree, p = 0.3–0.8). But its distance at L1 (88–92 pc) is 2.3–3.4σ short of the host's 124 ± 5 pc. Only M9–L0, or an unresolved binary, would fit. |
| **CWISE J011003.61−592650.8** (J0110−5926) | (L2) | **late-M, ≈M8** (M7–M9; L2 excluded, Δχ² ≈ 170) | **not confirmed.** It moves with the white dwarf WDJ011001.84−592642.22 (three PMs, p = 0.24–0.49). But its distance at M8 is 1.8σ beyond the WD's 110 ± 10 pc, and its VHS J−Ks = 0.84 points to M7–M8, which makes the gap larger. |

Two more spectra look like good matches but are **inconclusive**: J2358−5218 (≈L0) and J1325+0223 (late-M).
- Their SPHEREx 1.2 µm flux is 1.8× and 2.0× their own catalogue J magnitude.
- Each sits 30″ from a G ≈ 11 host. The pipeline's neighbour model reports ~0 % neighbour light for both.
- J2358−5218 is still a Gaia-confirmed co-moving pair (Δμ = 0.0 ± 2.1 mas/yr), but that confirmation is Gaia's and Rothermich's, not ours.

No result is a new companion confirmation. The new content is three first spectrum-based classifications. Two of them overturn the photometric estimates by 3–4 subtypes: (L3) → late-M and (L2) → late-M.

## Method

### 1. Candidate list and screen (`scripts/screen.py` → `out/screen.csv`, `out/screen.json`)

**Inputs**
- Rothermich et al. 2024 (AJ 167, 253), VizieR J/AJ/167/253 on the Harvard mirror (`raw/rothermich_table{1,2,11}.tsv`).
  - The VizieR entry has only Table 1 (high probability), Table 2 (photometry) and Table 11 (masses).
  - CDS was down (`raw/rothermich_readme.html`: 302 → cdsarc), so the ReadMe was not read.
- Table 3 (low-probability systems) and Table 4 (spectroscopic observation log) were typed from the arXiv HTML text in `research/verification/rothermich_text.txt` (`raw/rothermich_table3_lowprob.txt`, `raw/rothermich_table4_spectra.txt`).

**Candidates:** 109 secondaries, 74 of them with parenthesised (= photometric) types: 54 high-probability and 20 low-probability.

**Reject rules** (each rejection's reasons are in `screen.csv` → `reject`):
- **Rothermich spectroscopic type:** no parentheses in Table 1, or listed in their Table 4 log.
- **UltracoolSheet v2.1.0:** spectroscopic `spt_opt`/`spt_ir` within 10″ + 20 yr × PM, unless flagged `photSpT`.
- **SPIFF table** (`backend/app/data/ucd_catalog.csv`): any match within 10″ + 20 yr × PM. A SPIFF autotype is itself a SPHEREx-spectrum type (Gagné+2026), so ours would not be the first. Its "literature" column holds candidate labels such as "L0-Y2" and is not trusted.
- **SIMBAD (Harvard TAP, `raw/screen_simbad.json`):** any `mesSpT` entry not from 2024AJ....167..253R and not parenthesised.
- **Brightness:** CatWISE2020 W2 > 14.5 (II/365, CfA mirror, `raw/screen_II_365_catwise_15.ecsv`).
  - Only 2 photometric-type candidates pass at W2 ≤ 14.5, so a **relaxed tier W2 14.5–15.3 was added**.
  - 15.3 is roughly the J2317 brightness, which gave a type. These 10 objects are marked `pass-relaxed`.
- **Latitude:** |b| ≤ 15°.
- **Brighter neighbours within 15″:** a CatWISE source brighter in W1 or W2.
- **Brighter Gaia DR3 neighbour within 15″** (`raw/screen_I_355_gaiadr3_15.ecsv`): brighter in G than the target's own Gaia counterpart (≤ 2″), or G < 19 if the target has none.
- **Bright star within 2′:** AllWISE W2 < 8 (`raw/screen_II_328_allwise_120.ecsv`).
- **Already processed:** listed in `research/discovery/REPORT.md` (J2317−6700, J1826−4652).

**Ranking:** pass tier, then W2 (brightest first), then host probability.

### 2. Measurement (`scripts/measure.py` → `out/<tag>/{summary.json,spectrum.json,export.csv,metrics.json}`, log `out/measure_log.txt`)

**Dev API**
- Started from the current working tree: `cd backend && CACHE_DIR=/data/devcache/discovery2 WORKER_PROCESSES=2 nice -n 15 ../.venv/bin/uvicorn app.main:app --port 8004`.
- Code state: HEAD 04b83c4 plus file hashes, PIPELINE_VERSION 5, SUMMARY_VERSION 2 (`CODE_STATE_dev_api.txt`).
- One field at a time. All 12 fields finished `done` with 332–454 SPHEREx and 44–48 WISE frames. The server was stopped afterwards.

**Request per object:** CatWISE II/365 PM-fit position at 2015.4, the offset-corrected PM, and the default fov.

**Recorded per object:**
- S/N at 3.5–5 µm (`detection_snr`).
- Channels at S/N > 3 and > 5.
- Whether neighbour-aware PSF photometry was triggered (`photometry`, `neighbour_frac`).
- χ²ᵣ of the best fit and the top-5 ranking.
- `type_range`, motion and colour.

### 3. Verdict and self-checks (`scripts/verdict.py` → `out/<tag>/verdict.json`, `out/results.csv`)

**(a) Type.** A type is "first spectrum-based" only if all of these hold:
- **Spectrum quality:** verdict `match` (not "doubtful"), detection S/N ≥ 15, ≥ 15 channels at S/N > 5 (the J2317 level), no `contaminated` flag, no unresolved blend.
- **Fitting variants agree** (same fit as `research/verification/spectral_refit.py`): all channels with and without template spread, 1.0–2.5 µm only, 2.5–5.0 µm only, errors ×1.5.
- **Photometry choice does not matter** (`scripts/aperture_check.py` → `out/<tag>/photometry_check.json`): the photometry the pipeline did not use (plain aperture or neighbour-subtracted PSF) must give a best type that agrees.
  - Agreement means the pipeline best type and all these point estimates lie within 2 subtypes, so "≈X ± 1".
  - The adopted range is the pipeline range widened to include all of them.
- **Colours:** CatWISE W1−W2, 2MASS J − W2, and VHS (MKO) J − W2 lie inside the UltracoolSheet field-single 95 % locus of a subtype in the range. The 68 % result is also stored.
- **No unmodelled neighbour light** (`scripts/sed_check.py` → `out/sed_check.json`): the SPHEREx 1.15–1.32 µm flux is ≤ 1.4× the target's own catalogue J. The isolated objects give 1.06 and 1.09.
- **Template floor:** a range that reaches M8 (the earliest SPIFF template) cannot test an earlier photometric type.

**(b) Companion.**
- **PM inputs:**
  - Our PM, with a 20 mas/yr/axis floor (`research/discovery/REPORT.md` validation).
  - Pipeline-independent PMs: CatWISE2020 offset-corrected; 2MASS (JD epoch) → CatWISE 2015.4 PM-fit position; Gaia DR3 of the target when present; AllWISE → VHS for J0110 (`scripts/twoepoch_J0110.py`).
- **Compared against:** the host's Gaia DR3 (`scripts/hosts.py` → `out/hosts.json`). We report Δμ, χ² (2 dof), Δv_tan at the host distance, and the bound-orbit limit: the escape speed at the projected separation with M_tot from Rothermich Table 11 (0.6 M☉ if missing).
- **Photometric distance:** computed for **our** type range from two calibrations:
  - the UltracoolSheet v2.1.0 empirical M_W2 per subtype (field singles with ϖ/σ > 10; median ± 1.4826 MAD);
  - Kirkpatrick+2021 Table 13 SpT→M_ch2 (L0 and later, RMS 0.31 mag; same coefficients as `research/verification/recompute.py`).
  - The tension with the host is z = Δ(distance modulus)/hypot(calibration σ, host-parallax σ).
- **Decision rules:**
  - **Confirmed:** Gaia DR3 (if present) or every independent PM agrees (p > 0.01, at least one > 0.05), our PM agrees (p > 0.05), |z| ≤ 2 somewhere in the range, **and** |z| ≤ 2 at the best-fit type.
  - **Refuted:** the Gaia PM (or ≥ 2 independent PMs) disagrees at p < 0.001, or |z| > 2 over the whole range.

**(c) Literature** (`scripts/lit.py`, `scripts/vizier_split.sh` → `out/<tag>/lit.json`, `out/<tag>/vizier_*.tsv`; `raw/web_search_log.txt`):
- SIMBAD (all identifiers, bibcodes, mesSpT).
- VizieR all-catalogue 20″ cone on the CfA mirror. When the single call was cut off, it was split per catalogue group.
- J/A+A/685 (Ravinet+2024 Gaia-UCD NIR spectra, `raw/ravinet2024_<tag>.tsv`).
- UltracoolSheet, SPIFF, web search.
- **ADS full text was not searched (no token).**

## Screen summary

[`out/screen.csv`]
- **Input:** 109 Rothermich secondaries.
  - 35 high-probability objects already have spectroscopic types (theirs or the literature's).
  - 74 have photometric types.
- **Result:** 2 pass the strict cuts (W2 ≤ 14.5) and 10 pass in the relaxed tier (W2 14.5–15.3). 97 are rejected.
- **Rejection reasons among the 74 photometric-type objects** (one object can have several):

  | reason | objects |
  |---|---|
  | W2 > 15.3 | 30 |
  | brighter CatWISE source within 15″ | 27 |
  | brighter Gaia source within 15″ | 21 |
  | **SPHEREx autotype already in the SPIFF table** | 15 |
  | \|b\| ≤ 15° | 8 |
  | W2 < 8 star within 2′ | 7 |
  | no CatWISE match at the designation position | 3 |
  | already processed | 2 |
  | in Rothermich's spectroscopic log | 1 |

- Notable: 15 of the 74 photometric-type Rothermich companions already have SPIFF SPHEREx autotypes, e.g. J0851−6030 (W2 13.0, the brightest), J0256−3350, J0809+7417 and J1909+5530. A "first spectrum-based type" claim would be false for them.

## Results: all measured objects

Columns:
- `SX/W`: SPHEREx frames / WISE frames.
- `det`: S/N at 3.5–5 µm.
- `b>3`, `b>5`: channels at S/N > 3 and > 5.
- `nb`: maximum neighbour-light fraction in the aperture; "PSF" means the pipeline switched to neighbour-subtracted photometry.
- `points`: best types over the pipeline fit, the 5 variants and the other photometry.
- `J ratio`: SPHEREx 1.2 µm flux / catalogue J.
- `μ` = our PM (mas/yr), error with the floor.
- `p`: Δμ-vs-host p-values for ours / the independent PMs.
- `d` = photometric 2σ distance range for our adopted range vs the host's.

| tag (CWISE) | Roth. | prob % | W2 | SX/W | pipeline type (χ²ᵣ) [range] | det | b>3 / b>5 | phot., nb | points | J ratio | μ ours | p ours / indep. | d (2σ) vs host pc | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **J1023−2045** J102322.00−204549.9 | (L3) | 0 | 14.12 | 403/44 | M8 (0.82) [M8–M9] | 41.2 | 83/75 | aperture, 0.00 | M8×5, L0, M9β | 1.06 | (1, −155) ± 23 | 0.81 / CW 0.45, 2M→CW 6e-4, **Gaia 6e-132** | 48–124 vs 94.5 | **first spectrum-based type; companion refuted** |
| J2358−5218 J235827.96−521813.4 | (M9) | 100 | 14.20 | 332/44 | L0 (1.04) [M9–L1] | 37.9 | 85/70 | aperture, ~0 | L0, M9 | **1.82** | (116, −5) ± 24 | 0.79 / CW 0.013, 2M→CW 0.008, Gaia 1.0 | 46–112 vs 77.9 | inconclusive: extra light at 1.2 µm (G = 11.4 host at 30″) |
| J0024−4030 J002414.30−403053.7 | (L5) | 99.9 | 14.60 | 421/44 | L7 (1.99) [L6–L8] | 41.7 | 55/48 | PSF, 0.26 | L7, L5βγ, L4β | – | (160, 21) ± 25 | 0.51 / CW 8e-4 | 31–91 vs 53.9 | inconclusive: variants span L4–L7 |
| J0049+4236 J004945.38+423619.3 | (L6) | 100 | 14.85 | 421/48 | L7 (0.18) [L6–T1] | 16.9 | 21/0 | PSF, **3.7** | M8…L8 | – | (−283, 0) ± 38 (not recovered) | 1e-6 / CW 0.62 | – | inconclusive: neighbours 2–4× brighter, no channel at S/N > 5 |
| J1325−1907 J132520.42−190701.2 | (L6) | 87.5 | 14.86 | 344/48 | doubtful L4 (2.02) [L3–L5] | 37.2 | 79/65 | PSF, 0.57 | L1…L8 | – | (36, −113) ± 24 | 0.03 / CW 1e-7 | 35–111 vs 45.0 | inconclusive: water band too shallow, variants span L1–L8 |
| J1542+5939 J154205.53+593900.8 | (M6) | 0 | 14.88 | 417/48 | M8 (0.58) [M8–M9] | 28.5 | 73/60 | aperture, 0.08 | M8, M9, L0 | 1.09 | (−83, 0) ± 24 | 0.68 / CW 0.014, 2M→CW 8e-5 | 68–177 vs 44.4 | inconclusive type (M8 template floor; M6 untestable); companion **refuted** by distance (z = +4.9 to +6.3) |
| **J1240+4605** J124033.48+460544.7 | (M9) | 100 | 14.98 | 434/44 | L1 (1.32) [M9–L3] | 36.4 | 72/64 | PSF, 0.32 | L1×6, L2 | 0.85 | (−144, 85) ± 24 | 0.77 / CW 0.39, 2M→CW 0.30 | 60–161 vs 124.0 | **first spectrum-based type; companion not confirmed** (distance at L1: z = −2.3 / −3.4) |
| J0042+2917 J004218.67+291730.6 | (L5) | 99.5 | 15.02 | 339/48 | L7 (2.18) [L4–L8] | 26.9 | 63/43 | PSF, 0.32 | L3γ…T3 | – | (93, −15) ± 26 | 0.92 / CW 0.62 | 27–111 vs 68.5 | inconclusive: variants span L3–T3 |
| J1325+0223 J132539.70+022309.4 | (M9) | 100 | 15.04 | 383/48 | M8 (1.27) [M8–M9] | 22.9 | 73/53 | aperture, ~0 | M8, L0 | **2.05** | (−197, −148) ± 27 | 0.92 / CW 0.086, 2M→CW 0.51 | 73–190 vs 118.6 | inconclusive: extra light at 1.2 µm (G = 11.0 host at 31″) |
| J0137+3428 J013719.04+342837.6 | (L6) | 99.1 | 15.09 | 345/48 | L7 (1.29) [L6–L8] | 18.3 | 25/12 | aperture, 0.09 | L7, L5βγ, sdL8 | – | (130, −13) ± 27 | 0.84 / CW 0.028 | 39–94 vs 61.6 | inconclusive: 12 channels at S/N > 5; variants L5–L8 |
| J0127−3002 J012715.52−300246.9 | (T0) | 99.9 | 15.23 | 443/46 | doubtful L2 (0.65) [L1–L3] | 18.5 | 57/39 | aperture, 0.08 | L2×6, PSF→L7 | – | (91, 3) ± 27 | 0.35 / CW 0.27 | 45–131 vs 49.6 | inconclusive: W1−W2 = −0.01 (ours) is too blue for L; photometry-dependent |
| **J0110−5926** J011003.61−592650.8 | (L2) | 100 | 15.29 | 454/44 | M8β (1.32) [M8–M9] | 28.1 | 61/58 | PSF, 0.46 | M8×7 | 1.11 | (198, 192) ± 25 | 0.49 / CW 0.24, AllWISE→VHS 0.36 | 97–213 vs 109.8 | **first spectrum-based type; companion not confirmed** (manual downgrade, see below) |

Sources: `out/results.csv`, `out/<tag>/verdict.json`, `out/<tag>/metrics.json`, `out/sed_check.json`. The p-value for J0049's PM is from `verdict.json`; our astrometry did not recover the target there (`motion.recovered = false`).

## Positive result 1: CWISE J102322.00−204549.9, a late-M dwarf, not an L3, and not a companion

**Identifiers and prior status**
- = 2MASS J10232199−2045473 = Gaia DR3 5667969698017693056.
- SIMBAD: `BD?`, no spectral type, no mesSpT. Two bibcodes: 2021A&A...649A...6G (Gaia Catalogue of Nearby Stars) and 2024AJ....167..253R (`out/J1023-2045/lit.json`).
- Rothermich Table 3 (low probability):
  - photometric "(L3)", proposed host CWISE J102244.48−204204.5 (M3) at 573″, co-moving probability **0 %** (`raw/rothermich_table3_lowprob.txt`).
  - Their §V.1.2: secondaries with their own Gaia astrometry were typed "using the photometric relations from Kiman et al. 2019". The table row does not say which method they used.
- VizieR 20″ (21 catalogues with rows; status ok) gives photometry, astrometry and Gaia-derived quantities only:
  - GCNS; Kervella+2022 (J/A+A/657/A7, SpType column empty);
  - J/AJ/161/234; J/AJ/165/267 (Teff 2495 K, a Gaia-photometric estimate);
  - HPMS3 (J/other/JDSO/15/21).
  - **No spectroscopic type.** Not in Ravinet+2024 (`raw/ravinet2024_J1023-2045.tsv`, 0 rows), UltracoolSheet or SPIFF. Web search: no hit (`raw/web_search_log.txt`).

**Spectrum** (seq `af06100b68c08423`; 403 SPHEREx + 44 WISE frames)
- Data: 90 channels, 83 at S/N > 3 and 75 at S/N > 5; detection S/N 41.2. Aperture photometry, catalogued neighbour light < 0.2 % in every band. 0 negative channels.
- Fit: best **M8**, χ²ᵣ 0.82, pipeline range M8–M9.
- Δχ² vs M8 (`photometric_type_check`): M9β 18.5, M9 82.6, L0 83.6, L1 131, L2 251, **L3 490**.
- Variants: M8 / M8β (no template spread) / M8 (1–2.5 µm) / **L0 ≈ M8** (2.5–5 µm alone: χ²ᵣ 0.48 for both) / M8 (errors ×1.5).
- Neighbour-subtracted PSF photometry: M9β [M8–L2].
- **Adopted: late-M, ≈M8–M9.** The full range of point estimates is M8–L0. M8 is the earliest SPIFF template, so earlier types are not tested by the spectrum.

**Independent type checks**
- Its own Gaia parallax, ϖ = 13.06 ± 0.84 mas, gives M_W2 = 9.70 ± 0.14. That matches M7–L0 in the UltracoolSheet field locus (M8 9.37, M9 9.65, L0 9.77; L3 is 10.48) [`own_parallax_check`].
- G−RP = 1.58 is consistent.
- CatWISE W1−W2 = 0.295 ± 0.021 is consistent (95 % locus).
- 2MASS J−W2 = 1.53 ± 0.08 matches M7–L0 at 68 %.
- SPHEREx 1.2 µm / 2MASS J = 1.06 ± 0.03: no extra light.

**Companion test**
- Host Gaia DR3 5667977669477544832: ϖ 10.585 ± 0.043 mas (94.5 pc), PM (−3.00, −169.87).
- **Target Gaia DR3 PM: (0.52 ± 0.64, −151.09 ± 0.78).**
  - Δμ = (3.5, 18.8) mas/yr, χ² = 604.
  - Δv_tan = 8.6 ± 0.4 km/s, against an escape-speed limit of 0.14 km/s at the 54,000 au projected separation.
- **Parallaxes:** 13.06 ± 0.84 vs 10.585 ± 0.043 (2.9σ).
- 2MASS (1999.3) → CatWISE (2015.4): (6.5, −153.9) ± 4.8. It agrees with Gaia and disagrees with the host (p = 6e-4).
- Our 16-yr PM, (1 ± 23, −155 ± 23), and CatWISE are too coarse to separate the two motions.
- Distance at M8: 89 pc (64–124, 2σ). It is consistent with both 77 pc (own parallax) and 94 pc, so it does not decide the case.
- **Verdict: not a companion, which confirms Rothermich's 0 %.**

**Not checked**
- ADS full text.
- Majaess+2026 (Ap&SS 371, 85; paywalled) may list a Gaia-photometric type.
- No optical spectrum; gravity not assessed.

**Suggested public wording**
> CWISE J102322.00−204549.9 had only a brightness-based guess of "L3" (Rothermich et al. 2024). Its SPHEREx spectrum (0.75–5 µm, 403 frames) instead matches late-M dwarf templates (≈M8–M9); an L3 is strongly excluded. Its own Gaia parallax agrees with a late-M dwarf at ~77 pc. Gaia's motions show it is not bound to the star once proposed as its partner, as Rothermich et al. had already judged likely.
> *Caveat:* SPHEREx gives low-resolution spectrophotometry, not a slit spectrum; M8 is the earliest template available, so "late-M" is the safe statement. "First" = first spectrum-based type we found in SIMBAD, VizieR, UltracoolSheet v2.1.0, SPIFF and the web as of Nov 2026 (ADS full text not searched).

## Positive result 2: CWISE J124033.48+460544.7, ≈L1 ± 1; moves with its host, distance not yet consistent

**Identifiers and prior status**
- = 2MASS J12403374+4605437. SIMBAD `LM*`, no spectral type, one bibcode: 2024AJ....167..253R.
- Rothermich Table 1: photometric (M9), host CWISE J124032.46+460559.9 at 19″, probability 100 %, M_tot 0.18 M☉ (Table 11).
- The host is 2MASS J12403269+4605587 = Gaia DR3 1541285199269102848: G 19.34, BP−RP 3.52, ϖ 8.067 ± 0.328 mas (124 ± 5 pc), PM (−133.45 ± 0.18, 71.52 ± 0.25).
- Not in UltracoolSheet, SPIFF or Ravinet+2024 (`raw/ravinet2024_J1240+4605.tsv`, 0 rows). No Gaia counterpart within 2″. Web search: no hit.
- VizieR 20″ (`out/J1240+4605/lit.json`; the single call was cut off, so it was split per catalogue group in `vizier_split_log.txt`; the B/ group was itself cut off, 38 tables read): **no spectroscopic type for the target.**
  - Rows hit only photometry/astrometry catalogues and Rothermich Table 1.
  - That table types the host "(M7)", also photometric.
  - The host itself is in J/AJ/151/41 and J/AJ/153/92: photometric T_eff 2796 K, d_phot 137 ± 14 pc.
  - **The host is brighter than the target in W1/W2:** AllWISE W2 14.12 vs CatWISE 14.98 for the target. This explains the 15–32 % neighbour light.

**Spectrum** (seq `3de847a3ceb96356`; 434 SPHEREx + 44 WISE frames)
- Data: 90 channels, 72 at S/N > 3 and 64 at S/N > 5; detection S/N 36.4.
- Neighbour-subtracted PSF photometry: catalogued neighbours, including the host at 19″, add 15–32 % of the target's flux per band.
- Fit: best **L1**, χ²ᵣ 1.32, range M9–L3. Δχ² (rescaled ÷1.32): L0 0.5, L2 1.2, M8 25, **M9 (Rothermich) 29**.
- Variants: L1 / L1 / L1 / L2 (2.5–5 µm) / L1.
- **Plain aperture photometry also gives L1** (χ²ᵣ 0.64, range M9–L2), so the type does not depend on the neighbour subtraction.
- Colours: W1−W2 0.28 ± 0.03 and 2MASS J−W2 1.60 ± 0.15 are consistent (J−W2 68 %: M7–L1).
- SPHEREx 1.2 µm / 2MASS J = 0.85 ± 0.04: no extra light.
- **Adopted: ≈L1 ± 1.** M9 is disfavoured but inside the ±1 systematic.

**Companion test**
- PMs vs host:
  - ours (−144, 85) ± 24, p = 0.77;
  - CatWISE (−142.4 ± 12.9, 88.9 ± 14.6), p = 0.39;
  - 2MASS (1998.4) → CatWISE (−155, 52) ± 19, p = 0.30.
  - So it is co-moving at the ~15–20 mas/yr level against the host's 152 mas/yr. That cannot test boundness: the bound limit is 0.37 km/s, while our Δv_tan error is ~8–14 km/s.
- Distance at L1:
  - UltracoolSheet 92 pc (85–99); z = −3.4 vs 124 ± 5 pc.
  - Kirkpatrick+21 88 pc (66–117, 2σ); z = −2.3.
  - At M9 or L0, z = −0.4 / −0.7.
- **Verdict: not confirmed.** It is co-moving, but at the best-fit type it is too bright for the host distance. An unresolved equal-mass binary (×1.41 → ~130 pc) or a type at the early end of the range would reconcile this. Neither is tested.

**Not checked**
- ADS full text.
- No Gaia parallax for the target.
- Binarity.
- The PSF model's residuals from the 19″ host (aperture and PSF agree, which limits the effect).

**Suggested public wording**
> CWISE J124033.48+460544.7, a candidate companion of a faint red star 19″ away, had only a brightness-based type estimate (M9; Rothermich et al. 2024). Its SPHEREx spectrum matches early-L templates (≈L1 ± 1), the first spectrum-based type we found. It shares its partner's motion across 2MASS, WISE and SPHEREx (1998–2026), but at L1 it would be closer (~90 pc) than its partner (124 pc); it may be an unresolved pair or an M9–L0. So the companionship is supported by motion, not yet by distance.

## Positive result 3: CWISE J011003.61−592650.8, a late-M dwarf next to a white dwarf, not an L2

**Identifiers and prior status**
- = WISE J011003.46−592651.7. SIMBAD `BD?`, no spectral type, one bibcode: 2024AJ....167..253R.
- Rothermich Table 1: photometric (L2), host the white dwarf WDJ011001.84−592642.22 at 15″, probability 100 %, M_tot 0.5 M☉.
- The host is Gaia DR3 4909222871450620416: G 20.56, ϖ 9.11 ± 0.79 mas (110 ± 10 pc), PM (212.99 ± 0.97, 167.56 ± 0.94).
- Not in UltracoolSheet, SPIFF or Ravinet+2024 (0 rows). No 2MASS and no Gaia counterpart. Web search: no hit.
- VizieR 20″ (27 catalogues with rows, status ok; `out/J0110-5926/lit.json`): **no spectroscopic type.**
  - Carnero Rosell+2019 DES Y3 UCD catalogue (J/MNRAS/489/5301) lists it with **photometric** `SpTypePh` = 9.0. That is consistent with our late-M if their code puts L0 at 10; the code scale was not checked.
  - Two neighbouring AllWISE sources, J011001.14−592650.3 and J011003.56−592641.1, are Assef+2018 C75 AGN candidates. Neither is the target's AllWISE J011003.49−592651.7.
  - The host is in Gentile Fusillo+2019/2021 as a white dwarf: P_WD 0.96, T_eff(H) 4116 K, r_geo 111 pc. A cool, hence old, WD (cooling age not computed).

**Spectrum** (seq `ccd53cf653caf406`; 454 SPHEREx + 44 WISE frames)
- Data: 90 channels, 61 at S/N > 3 and 58 at S/N > 5; detection S/N 28.1.
- Neighbour-subtracted PSF photometry: catalogued neighbour light 17–46 % per band.
- Fit: best M8β (χ²ᵣ 1.32), M8 1.35, range M8–M9. Δχ² (rescaled ÷1.32): M8 1.8, M9β 24, L0 65, M9 70, L1 102, **L2 (Rothermich) 169**.
- Variants: all M8/M8β. The 2.5–5 µm half alone barely discriminates (M8 0.80, L7 0.85, L2 0.85).
- **Plain aperture photometry also gives M8** (χ²ᵣ 0.89).
- The β (low-gravity) template is not claimed: gravity classes are not validated for SPHEREx in `research/spectra/REPORT.md`.
- Colours and extra light:
  - W1−W2 0.27 ± 0.04 and VHS J−W2 1.52 ± 0.04 are consistent.
  - **VHS J−Ks = 0.84 ± 0.06** (`raw/vhs_dr5_measured.json`). UltracoolSheet field singles (MKO) give M7 0.97 [0.85–1.09], M8 1.06 [0.95–1.14] and L2 1.41 [1.21–1.62] (`out/ucs_jk_mko_by_subtype.txt`). That supports M7–M8 and excludes L2.
  - SPHEREx 1.2 µm / VHS J = 1.11 ± 0.04: no extra light.
- **Adopted: late-M, ≈M8 (M7–M9).** M8 is the earliest template.

**Companion test**
- PMs vs the white dwarf:
  - ours (198, 192) ± 25, p = 0.49;
  - CatWISE (190.0 ± 16.9, 182.5 ± 14.9), p = 0.24;
  - AllWISE (2010.6) → VHS (2013.6): (149, 144) ± 47, p = 0.36 (`out/J0110-5926/twoepoch_pm.json`).
  - So it is co-moving against the host's 271 mas/yr total motion.
- Distance at M8: 153 pc (110–213, 2σ); z = +1.8 vs 110 ± 10 pc. At M9, z = +1.1. At M7 (M_W2 9.08) it would be ~175 pc, even farther.
- At the WD's distance it would need M_W2 = 10.09 ± 0.19, which is L0–L1. The spectrum disfavours L0/L1 by Δχ² 65/102, and J−Ks points the other way.
- `verdict.py` scores this "confirmed" (|z| ≤ 2). **I downgrade it by hand to "not confirmed"**: the only distance-sensitive check that is independent of our templates (J−Ks) widens the gap.

**Not checked**
- The WD's own parameters (cooling age, photometric distance).
- Binarity.
- ADS full text.

**Suggested public wording**
> CWISE J011003.61−592650.8, a faint companion candidate 15″ from a white dwarf, had only a brightness-based type estimate (L2; Rothermich et al. 2024). Its SPHEREx spectrum, and its near-infrared colours, instead say it is a late-M dwarf (≈M8), right at the star/brown-dwarf boundary — the first spectrum-based type we found. It shares the white dwarf's motion, but its brightness puts it ~1.5× farther away than the white dwarf, so whether the two are a true pair is still open.

## Inconclusive objects: reasons

| object | reason | files |
|---|---|---|
| J2358−5218, J1325+0223 | Light from the G ≈ 11 host 30″ away: the SPHEREx 1.2 µm flux is 1.8× and 2.0× the 2MASS J. The pipeline's Gaussian-PSF neighbour fraction reports ~0 %, and the PSF re-fit returned "insufficient data" for both (`photometry_check.json`). J2358 is a Gaia DR3 co-moving pair (Δμ = 0.0 ± 2.1 mas/yr, ϖ 11.98 ± 1.43 vs 12.84). It is also in Dal Ponte+2023 DES UCD candidates (J/MNRAS/522/1951, photometric SpT code 10, d_phot 75 pc; code scale not checked). Its "≈L0" is plausible but cannot be claimed from this spectrum. J1325+0223 also has bibcode 2026ApJ..1008...67P (Benchmark Brown Dwarf Systems I: PEPSI abundances of the FGK hosts; `raw/simbad_ref_2026ApJ1008_67P.txt`; full text not read). | `out/sed_check.json`, `out/J2358-5218/lit.json` |
| J1542+5939 | Best M8 sits at the template floor, so Rothermich's (M6) cannot be tested. It is **not at the host's distance**: M8–L0 gives 68–177 pc (2σ) vs 44.4 pc (z ≥ 4.9), and 2MASS→CatWISE disagrees with the host PM (p = 8e-5). That fits Rothermich's 0 %. | `out/J1542+5939/verdict.json` |
| J0024−4030, J0042+2917 | The fitting variants disagree (L4–L7 and L3–T3). Neighbour light 26–32 % (PSF path). | `verdict.json` → `variants` |
| J0049+4236 | Neighbours are 2–4× brighter than the target in the aperture; 0 channels at S/N > 5; our astrometry did not recover the target. | `metrics.json` |
| J1325−1907 | "Doubtful match" (1.4 µm water too shallow for L4); variants span L1–L8. CatWISE PM differs from the WD host's (p = 1e-7, only one independent PM, so not counted as refuted). | `verdict.json` |
| J0137+3428 | Only 12 channels at S/N > 5 (the J2317 claim had 17); variants span L5–L8 (consistent with Rothermich's (L6)). | `metrics.json` |
| J0127−3002 | "Doubtful match": our W1−W2 = −0.01 is too blue for an L (CatWISE: 0.09). Aperture gives L2, PSF gives L7. Rothermich's (T0) is not supported but not tested either. | `photometry_check.json` |

## Findings for the pipeline (not changed)

1. **Bright hosts at ~30″ leak into the SPHEREx photometry undetected.**
   - For G ≈ 11 stars at 30–31″, the Gaussian-PSF neighbour model reports < 1 % neighbour light, but the SPHEREx 1.2 µm flux is 1.8–2.0× the target's 2MASS J (`out/sed_check.json`).
   - A synthetic-J vs catalogue-J check like `scripts/sed_check.py` would catch this. So would the SPHEREx EPSF wings instead of a Gaussian (already listed as an upgrade in `research/spectra/REPORT.md`).
2. **SPIFF coverage:** 15 of the 74 Rothermich photometric-type companions already have SPIFF SPHEREx autotypes. Any "first type" claim must check the SPIFF table (with PM allowance), not only SIMBAD.
3. **Template floor:** M8 is the earliest SPIFF template. Every late-M object here lands on "M8" (J1023, J1542, J1325+0223, J0110), so an "M8" result means "M8 or earlier" unless an absolute magnitude or J−K says otherwise.

## Not checked / limits

- **Literature:**
  - NASA ADS full text (no token).
  - Majaess+2026 (Ap&SS 371, 85, Gaia-photometric UCD candidates; paywalled).
  - 2026ApJ..1008...67P full text.
  - CDS ReadMe of J/AJ/167/253 (CDS down; Harvard mirror used for everything).
  - VizieR "B/" catalogue group for J2358−5218 and J1240+4605: the CfA mirror cut the reply off after 38 tables (curl exit 18). That group is mission logs, GCVS and WD lists, not spectral-type papers.
- **Spectral-type limits:**
  - The SPHEREx gravity classification (β/γ) is not validated.
  - The colour loci are UltracoolSheet field singles. Young/red/blue outliers would widen them.
- **Astrometry assumptions:**
  - The VHS per-source astrometric error is assumed to be 0.1″ in the J0110 AllWISE→VHS PM.
  - The AllWISE mean epoch is assumed to be MJD 55400.
- **Companion test:**
  - Bound-orbit limits use the projected separation and Rothermich's (or an assumed 0.6 M☉) total mass.
  - With our ~25 mas/yr PM errors, no pair can be tested for boundness beyond common proper motion.
- **Screen relaxation:** objects with W2 14.5–15.3 were measured only because the strict W2 ≤ 14.5 cut left 2 objects. All three positives except J1023 come from that relaxed tier, but each has ≥ 58 channels at S/N > 5.

## Files and commands

All Python ran under `nice -n 15 /home/paw/Desktop/ultracool/.venv/bin/python`, cwd `research/discovery2`.

| file | what |
|---|---|
| `scripts/screen.py` → `out/screen.csv`, `out/screen.json` | screen with reasons; raw queries `raw/screen_*.ecsv`, `raw/screen_simbad.json` |
| `scripts/measure.py <tag>` → `out/<tag>/` | dev-API /summary, /spectrum, /export.csv, metrics; `out/measure_log.txt` |
| `scripts/hosts.py` → `out/hosts.json` | host and target Gaia DR3 (VizieR I/355/gaiadr3, CfA) |
| `scripts/aperture_check.py` (with `CACHE_DIR=/data/devcache/discovery2`) → `out/<tag>/photometry_check.json` | aperture vs PSF photometry type |
| `scripts/sed_check.py` → `out/sed_check.json` | SPHEREx vs catalogue J / W2 |
| `scripts/verdict.py` → `out/<tag>/verdict.json`, `out/results.csv` | variants, colours, PMs, distances, classification; `raw/twomass_measured.json`, `raw/vhs_dr5_measured.json` |
| `scripts/twoepoch_J0110.py` → `out/J0110-5926/twoepoch_pm.json` | AllWISE→VHS PM |
| `scripts/lit.py`, `scripts/vizier_split.sh` → `out/<tag>/lit.json`, `out/<tag>/vizier_*.tsv` | literature |
| `out/ucs_jk_mko_by_subtype.txt` | UltracoolSheet MKO J−K per subtype (inline script) |
| `CODE_STATE_dev_api.txt` | dev API code state |

Key URLs:
- `https://vizier.cfa.harvard.edu/viz-bin/asu-tsv?-source=J/AJ/167/253/table1&-out.all&-out.max=unlimited` (same for table2 and table11)
- `https://simbad.harvard.edu/simbad/sim-tap`
- arXiv:2403.04592 (Rothermich+2024)

Dev-API sequence ids are in each `metrics.json` (`seq_id`), cache `/data/devcache/discovery2/seq/<id>/`.
