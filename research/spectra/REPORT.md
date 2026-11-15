# SPHEREx spectral typing: validation and fixes

Slice: Spectra. Date: 2026-11-15. Data and scripts: `research/spectra/validation/`. Every number below comes from a file there (named in brackets). SPHEREx R ≈ 40–130 spectrophotometry is not a slit spectrum; types here are template matches to it.

## Result

| set (26 dwarfs with a literature type) | typed "match" | within ±1 subtype | within ±2 | mean \|Δ\| | literature type inside our range |
|---|---|---|---|---|---|
| before (production code, PIPELINE_VERSION 5) | 23 | 13 | 18 | 2.85 | – (no range) |
| after (this work) | 24 | 16 | 21 | 1.19 | 16 / 24 |

[`table_before.json`, `table_after.json`, `.md` versions alongside]

Objects whose result changed (before → after, Δ = ours − literature in subtypes):
- ULAS J000734.90+011247.1 (T7): M8 (Δ −19) → **T5** (−2). Cause: a W1 = 13.7 star 13.9″ away inside the 12.3″ SPHEREx aperture (CatWISE cone, see "Fix 1").
- 2MASS J12171110−0311131 (T7.5): M8 (−19.5) → **T5** (−2.5).
- WISE J205628.90+145953.3 (Y0): T5 (−5) → **Y0** (0). WISE J173835.52+273258.9 (Y0): T5 (−5) → **Y0** (0).
- 2MASS J07271824+1710012 (T7): T5 (−2) → **T7** (0).
- WISE J085510.83−071442.5 (Y2 SIMBAD; Y4 in the brief): best template sdM9.5 → **Y1** (the last template), but still "insufficient data": 3 channels remain significantly negative (two stars 8.1″ and 10.6″ away; see "Remaining").
- 2MASS J18212815+1414010 (L4.5): L4 → L5 (+0.5; unchanged quality).
- **Regression:** WISE J154151.65−225024.9 (Y0): "doubtful match d_sdT1" → "match d_sdT1" (Δ −9). See "Remaining failure modes".

Negative controls (5) [`table_before.json`, `table_after.json`]:
- RW Aur (YSO, W2 = 5.3, saturated): "insufficient data" before and after.
- OJ 287 (blazar): "not consistent with ultracool dwarf templates" before and after.
- LP 791-18 (M6V): "warmer than M8: probably an ordinary star" before and after.
- BPM 90029 (K5V): "not consistent" before and after.
- **IRAS 08057−3434 (embedded YSO, CWISE J080741.06−344335.9): a false "match" both before (Y1) and after (L7 γ, χ²ᵣ 3.1, detection S/N 33).** Its W1−W2 could not be measured, so the colour check cannot demote it, and the water-band check does not catch ice/dust absorption. False-match rate on controls: 1/5 before and after.

## Validation set

32 objects [`targets.jsonl`, `extra_targets.jsonl`, `lit.json`]:
- 27 ultracool dwarfs M8.5–Y2, W2 8.8–16.6 (CatWISE) [`catwise.json`]: incl. 5 binaries (2M0746 L0+L1.5, Kelu-1, eps Ind B T1+T6, 2M1534−2952 T4.5+T5, Scholz's star M9.5+T5), 5 with |b| < 20° (Scholz's star b = 2.3°, UGPS J0722 4.3°, J1821 13.0°, DENIS J0817 −14.4°, J0727 15.5°), the four problem cases from the brief, and J2317−6659 (no literature type; WISE check only).
- 5 negative controls: RW Aur, OJ 287, LP 791-18 (M6V), BPM 90029 (K5V), IRAS 08057−3434.
- Literature types: SPIFF `literature_spectral_type` (backend/app/data/ucd_catalog.csv, matched along the PM track within 10″ [`spiff_matches.json`]) when present, else SIMBAD `sp_type` from `/api/resolve` [`resolve.jsonl`]. For binaries the combined-light / primary type is used. Types later than Y1 are compared as Y1. Not searched: ADS full text, Best+2024.
- Every field was computed by a private dev API (`CACHE_DIR=/data/devcache/spectra`, port 8002, one field at a time, `run_fields.py`, log `run_fields.log`); 6 v5 fields were copied from the research caches (ids in `before/*/meta.json`). "Before" = that API's `/summary` and `/spectrum` with the unchanged code [`before/<object>/`]; "after" = `evaluate.py` (same `_summary` code path, uncached) with the new code [`after/<object>.json`].

## What changed (all in the analysis layer; no new downloads)

1. **Neighbour-aware PSF photometry** (`backend/app/psfphot.py`, new). Per SPHEREx frame, on the cached 2.75″ grid image: the target plus every CatWISE2020 source within 44″ are fitted together with one Gaussian PSF (width chosen per frame by least χ²) and a constant sky. The fit uses fixed positions propagated to the frame epoch.
   - CatWISE motions below 5σ are set to zero. A static neighbour of J1821+1414 has a spurious 0.5″/yr motion that walked it onto the target.
   - Sources within 5″ of the target are not fitted separately: they are unresolvable. They are reported as `blends_arcsec`, with a plain sentence.
   - Flux scale (`PSF_CAL`): matched to the native EPSF-corrected photometry. Median PSF/native ratio 0.94–0.99 per band on 5 isolated dwarfs.
   - Errors: calibrated on empty sky, using 108,597 fits at 480 source-free positions in 20 fields [`empty_sky.py`, `empty_sky.json`, `empty_sky_fit.json`]. Raw least-squares errors were 1.3× (clear sky) to 2.6× (next to neighbours) too small. After calibration the robust std of flux/error is 0.95–0.99 in clear sky and 0.6–1.3 next to neighbours.
   - When it is used: `analysis.typed_spectrum` switches to it when catalogued neighbours put > 10 % of the target's flux into the aperture in any band (`NB_FRAC`). Otherwise the native aperture photometry stays. Always-PSF was tested in the kernel on the first 12 typed objects (no saved file). It gave the same ±1/±2 counts (4/9), with worse χ² on isolated bright dwarfs (e.g. DENIS J0255 χ²ᵣ 0.54 → 3.42).
   - Cost: 1.7–4.6 s per field, cached per frame in `psfphot_<hash>.json` next to the manifest. The probe does not cache it.
2. **Robust channel combination** (`spectral._bin`):
   - Frames > 5× (own error + the channel's robust spread) from the channel median are dropped.
   - With ≥ 3 frames, the channel error is scaled up by √χ²ᵣ when the frames scatter more than their errors.
3. **Type range** (`spectral.type_range`, `type_range` in `/spectrum` and `/summary`):
   - Templates within Δχ² = 4 of the best fit, on the χ² curve rescaled when χ²ᵣ > 1, widened by ±1 subtype (`TYPE_SYS`).
   - The statistical part alone held the literature type for 7/20; with ±1 it holds it for 16/24.
   - Plain text: "…fits a T5 brown-dwarf template best; allowing for this method's typical error, its type lies between T4 and T6."
4. **Plain-English honesty fixes** (from the UX review):
   - (a) Probe with no clear source: colour and variability are now "insufficient data" with a reason, and no period is given. The same applies to a target found by the astrometry in neither W1 nor W2 (unless the track stack shows it at S/N ≥ 5).
   - (b) Saturated star on catalog photometry: "constant"/"irregular" become "insufficient data". A period at FAP < 1 % is still reported (R Dra).
   - (c) The p of /summary vs probe full mode for J2317: both use the same code. The probe re-measures native fluxes at the snapped position (one channel fewer, slightly different fluxes), and p = exp(−Δχ²/2) is hypersensitive to that. With the new code both give T5 with range T4–T7 (summary) and T5–T6 statistical (probe frames, kernel check). **The frontend should show `type_range`, not `prob`** (PlotsPanel.tsx:142/214, ResearchPanel.tsx:112 still print p; I did not edit frontend).
5. `SUMMARY_VERSION` (analysis.py) added to the `summary.json` cache key. Without it, production would keep serving old cached summaries forever (key was status + frame count).

## WISE photometry check [`wise_check.py` → `wise_check.json`]

Our W1/W2 (weighted mean of the visit fluxes `/summary` uses) vs AllWISE (2010.5 position) and CatWISE2020:
- **Bright (W2 < 13, 18 objects):** W2 − AllWISE = 0.00 to +0.08 mag, and W1 − AllWISE = −0.17 to +0.11 except blends (2M1534 −0.17, 2M1217 −0.34). **CatWISE2020 is not a valid reference for fast movers.** It is 0.3–0.5 mag fainter than both AllWISE and us at 0.8–1.1″/yr (J1835, J0036, J1507, J0825, DENIS J0255, J0559), 1.3–1.4 mag at 1.3–2.2″/yr (J0727, J0415), and 1.7 mag for eps Ind B (4.7″/yr).
- **W1534 ("W2 ~2× CatWISE"):** ours W2 15.74 vs AllWISE 16.07 ± 0.20 vs CatWISE 16.58. Most of the 0.83 mag gap is the CatWISE fast-mover bias (2.7″/yr). The remaining 0.33 mag vs AllWISE is 1.6σ, at our S/N 7.
- **J2317 (Main's finding):** ours W1 17.60 ± 0.06 vs AllWISE 17.22 ± 0.11 / CatWISE 17.12, and W2 15.43 vs 15.22 / 15.30. So our W1−W2 is too red by ~0.2–0.3 mag.
  - Experiment: masking all CatWISE sources from the 50–70″ sky annulus raises J2317 to W1 = 17.21, W2 = 15.27 [`masked_annulus_experiment`]. That matches AllWISE.
  - But the same masking makes isolated field stars in the eps Ind B field too bright by +12 µJy in W1 (68 stars at W1 16–17: ours/AllWISE 0.97 unmasked → 1.18 masked [`field_stars_eps_Ind_B`]), because the target aperture also holds the unresolved faint-source floor that masking removes from the sky.
  - Hence **no fix was applied**; the bias before = after.
  - The J2317 deficit is local to that field (cause not pinned down: annulus sky level vs AllWISE deblending). The upgrade would be a magnitude-aware annulus mask (CatWISE rows would need w1mpro/w2mpro).
- **Faint W1 and blends:** 2M1122 +0.18, W1738 +1.22 (W1 ≈ 19, below our limit), W2056 −1.12, and W1541 −2.0 vs CatWISE (no AllWISE match). The last two are neighbour/blend light in our 8.25″ aperture.

## Remaining failure modes (measured)

1. **Unresolved blends (< 5″).**
   - W1541−2250 (Y0) is typed d_sdT1 because CatWISE lists sources at 1.8″ and 4.0″ that SPHEREx cannot separate. Before, the 1.4 µm water check demoted it to "doubtful"; after, it is a "match". This is the one regression.
   - 2M1534−2952 stays "doubtful" (blend at 4.4″ fills the water band).
   - The `blends_arcsec` sentence now says so, but the type is not withheld. Withholding needs blend brightness (CatWISE magnitudes are not in the cached field query).
2. **Bright neighbours inside the aperture** still leave systematic residuals in the Gaussian-PSF fit. W0855: 3 channels at 1.2–1.5 µm are significantly negative, so it is vetoed although the best template is Y1. The upgrade is the SPHEREx EPSF instead of a Gaussian (needs native files, i.e. a re-download or probe mode=full).
3. **T dwarfs with neighbours come out ~2 subtypes early** (ULAS J0007 T5 vs T7, 2M1217 T5 vs T7.5): residual neighbour light at 1–1.3 µm. The type range does not include the literature type for these.
4. **L subtypes scatter ±2** (Kelu-1 +2.5, J1507 +2, J0825 −2) on isolated, bright objects. This is template degeneracy in the L sequence at this resolution, not photometry.
5. **eps Ind B (T1+T6)** stays T3 (SPIFF also gives T3). A composite-template test (two templates, non-negative amplitudes) prefers T2+T6 there, but improves χ² by even more on single dwarfs (LP 944-20 30.5 vs eps Ind B 15.8 in rescaled Δχ²). So it cannot flag binaries and was not adopted.

## Not done

- No ice-band veto. Tested 2026-11-15 on the 30 validation spectra: the inverse-variance-weighted data − template residual in 2.95–3.15 µm (H₂O ice) and 4.22–4.32 µm (CO₂ ice) is −3.7σ and −5.3σ for IRAS 08057−3434, but real brown dwarfs reach the same or worse (2M0559 T4.5: −3.1σ, −23.4σ; 2M1507 L5: −3.1σ, −7.3σ; DENIS J0817 T6: +1.3σ, −8.8σ) because bright objects show template mismatch there. A residual-based ice veto would mislabel real brown dwarfs, so the YSO false match stays; a proper test needs ice-band templates or the 2.5–3.5 µm continuum shape.
- No point-source detection test in the SPHEREx stack beyond the existing 3.5–5 µm S/N ≥ 5 rule.
- No leave-one-out check of `TYPE_SYS`, `PSF_CAL` or `NB_FRAC`: these were tuned on the same 24 typed objects they are scored on.
- No ADS full-text search for literature types.

## Deployment

- No PIPELINE_VERSION change and no re-download.
- `SUMMARY_VERSION = 2` makes every cached `summary.json` recompute on its next request: seconds per field, plus one cached CatWISE field query per field (shared `ext/` cache; the movers search already uses the same one).
- `/spectrum` now also needs that CatWISE query. If IRSA is down, it falls back to aperture photometry, and the summary is not cached (`_transient`).
