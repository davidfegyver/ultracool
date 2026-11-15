# Validation

This page describes how we tested the pipeline on objects whose answers are already known, and where it still fails. The science claims built on it are in [results.md](results.md).

## Spectral typing

### Test set

We ran the full pipeline on 32 objects, one field at a time, on a private copy of the API:

- 27 ultracool dwarfs from M8.5 to Y2, W2 = 8.8–16.6. They include 5 binaries (2M0746 L0+L1.5, Kelu-1, eps Ind B T1+T6, 2M1534−2952 T4.5+T5, Scholz's star M9.5+T5), 5 objects within 20° of the galactic plane, and WISE J2317−6659, which has no literature type and was used only for the WISE check.
- 5 negative controls that are not ultracool dwarfs: RW Aur (young star), OJ 287 (blazar), LP 791-18 (M6V), BPM 90029 (K5V) and IRAS 08057−3434 (embedded young star).

Literature types come from the SPIFF table when present, else from SIMBAD. For binaries we used the combined-light or primary type, and types later than Y1 were compared as Y1, the last template.

### Before and after

"Before" is the production code at the time (pipeline version 5). "After" adds the three changes described below.

| 26 dwarfs with a literature type | typed "match" | within ±1 subtype | within ±2 | mean \|Δ\| | literature type inside our range |
|---|---|---|---|---|---|
| before | 23 | 13 | 18 | 2.85 | – (no range) |
| after | 24 | 16 | 21 | 1.19 | 16 / 24 |

The biggest improvements were on dwarfs with a bright neighbour. ULAS J000734.90+011247.1 (T7) went from M8 to T5, because a W1 = 13.7 star 13.9″ away sits inside the 12.3″ SPHEREx aperture. 2MASS J12171110−0311131 (T7.5) went from M8 to T5. WISE J205628.90+145953.3 and WISE J173835.52+273258.9 (both Y0) went from T5 to Y0, and 2MASS J07271824+1710012 (T7) from T5 to T7.

There was one regression. WISE J154151.65−225024.9 (Y0) went from "doubtful match d_sdT1" to "match d_sdT1", 9 subtypes off, because two sources at 1.8″ and 4.0″ cannot be separated (see failure modes below).

The 5 negative controls behaved the same before and after. RW Aur came out "insufficient data" (saturated), OJ 287 and BPM 90029 "not consistent with ultracool dwarf templates", and LP 791-18 "warmer than M8: probably an ordinary star". IRAS 08057−3434 is a false "match" both times (Y1 before, L7 γ after). So the false-match rate on controls is 1 of 5.

### What changed

We made three changes: neighbour-aware PSF photometry, outlier rejection when combining frames per channel, and type ranges. All three work on images that were already cached, so no data had to be downloaded again.

#### Neighbour-aware PSF photometry

The target and every CatWISE2020 source within 44″ are fitted together on each SPHEREx frame with one Gaussian PSF and a constant sky. CatWISE motions below 5σ are set to zero, because a static neighbour of J1821+1414 had a spurious 0.5″/yr motion that walked it onto the target. Sources within 5″ of the target are reported as blends, not fitted.

The flux scale was matched to the native EPSF-corrected photometry on 5 isolated dwarfs; the median PSF/native ratio is 0.94–0.99 per band. The errors were calibrated on empty sky with 108,597 fits at 480 source-free positions in 20 fields. Raw least-squares errors were 1.3× (clear sky) to 2.6× (next to neighbours) too small. After calibration, the robust scatter of flux/error is 0.95–0.99 in clear sky and 0.6–1.3 next to neighbours.

The PSF fit is only used when neighbours put more than 10% of the target's light into the aperture. Using it always gave the same ±1/±2 counts on the first 12 typed objects but worse χ² on isolated bright dwarfs (DENIS J0255: χ²ᵣ 0.54 → 3.42). It costs 1.7–4.6 s per field.

#### Channel combination and type ranges

Frames more than 5× (their own error plus the channel's robust spread) from the channel median are dropped. With 3 or more frames, the channel error is scaled up by √χ²ᵣ when the frames scatter more than their errors.

The type range is every template within Δχ² = 4 of the best fit, widened by one subtype each way. The statistical part alone held the literature type for 7 of 20 objects; with the extra ±1 subtype it holds it for 16 of 24. That is why the app shows a range and not a probability.

### Known failure modes

Unresolved blends closer than 5″ still fool the typing. W1541−2250 is typed d_sdT1, and 2M1534−2952 stays "doubtful". The app now says a blend is present, but it does not withhold the type, because that would need the blend's brightness.

Bright neighbours inside the aperture still leave residuals in the Gaussian fit. For WISE 0855−0714, 3 channels at 1.2–1.5 µm are significantly negative, so it is vetoed as "insufficient data" although the best template is Y1. T dwarfs with neighbours come out about 2 subtypes early (ULAS J0007 T5 vs T7, 2M1217 T5 vs T7.5), and their range does not include the literature type. The fix would be the real SPHEREx PSF instead of a Gaussian.

L subtypes scatter by ±2 even for isolated, bright objects (Kelu-1 +2.5, J1507 +2, J0825 −2). That is template degeneracy in the L sequence at this resolution, not photometry.

eps Ind B (T1+T6) comes out T3, as in SPIFF. A two-template fit prefers T2+T6 there, but it improves χ² by even more on single dwarfs, so it cannot flag binaries and we did not adopt it.

The embedded young star IRAS 08057−3434 stays a false match. Its W1−W2 could not be measured, so the colour check cannot demote it, and the water-band check does not catch ice absorption. We tested an ice-band veto on the 30 validation spectra. IRAS 08057 has data − template residuals of −3.7σ (H₂O ice, 2.95–3.15 µm) and −5.3σ (CO₂ ice, 4.22–4.32 µm), but real brown dwarfs reach the same or worse: 2M0559 (T4.5) −3.1σ and −23.4σ, 2M1507 (L5) −3.1σ and −7.3σ, DENIS J0817 (T6) +1.3σ and −8.8σ. A veto would mislabel real brown dwarfs, so we rejected it. A proper test needs ice-band templates or the 2.5–3.5 µm continuum shape.

### Caveat: tuned on the same set

The type-range width, the PSF flux scale and the 10% neighbour threshold were tuned on the same 24 typed objects they are scored on. We did not run a leave-one-out check, so the "after" numbers are likely somewhat optimistic for new objects.

## WISE photometry

We compared our W1 and W2 (the weighted mean of the visit fluxes) with AllWISE and CatWISE2020.

For 18 bright objects (W2 < 13), our W2 − AllWISE is 0.00 to +0.08 mag, and W1 − AllWISE is −0.17 to +0.11 mag, apart from the blends 2M1534 (−0.17) and 2M1217 (−0.34).

CatWISE2020 is not a good reference for fast movers. It comes out 0.3–0.5 mag fainter than both AllWISE and us at 0.8–1.1″/yr, 1.3–1.4 mag at 1.3–2.2″/yr, and 1.7 mag for eps Ind B (4.7″/yr). This explains most of the gap for W1534, which was reported as "W2 about 2× CatWISE": ours is 15.74, AllWISE 16.07 ± 0.20 and CatWISE 16.58.

For WISE J2317−6659 our W1 is too faint: 17.60 ± 0.06 against AllWISE 17.22 ± 0.11, so our W1−W2 is too red by about 0.2–0.3 mag. Masking catalogued sources from the sky annulus fixes this field (W1 = 17.21), but makes 68 isolated field stars in the eps Ind B field too bright (ours/AllWISE 0.97 → 1.18). So we did not apply it, and the bias is still there. For faint sources we quote catalogue colours in [results.md](results.md).

## Motion

We checked the motion fits on objects with known proper motions:

| Object | Literature PM (mas/yr) | Ours (mas/yr) |
|---|---|---|
| 2MASS J0415−0935 (T8) | (2193, 527) | (2206 ± 6, 543 ± 6) |
| 2MASS J1122+2550 (T6) | (−1012, −324) | (−1035 ± 13, −362 ± 13) |
| Barnard's Star | (−802, +10362) | (−820, +10417) |

Agreement on the brown dwarfs is 13–38 mas/yr per axis, so we add a 20 mas/yr per-axis systematic floor to our errors. A blind detect-and-link fit that uses no catalogue motion agrees with the literature to within 37 mas/yr per axis on 2M0415, J1122 and a static control, and finds a diffraction spike incoherent (χ²ᵣ 6.2). Parallaxes are not reliable (the J1122 fit gives −100 ± 48 mas), so we do not use them.

For the white-dwarf pair in [results.md](results.md), we measured the white dwarf itself with the same pipeline and images as a control. We got (86.3, 26.7) ± 14.9 mas/yr against Gaia's (96.03, 36.29), a 0.65σ difference, with 0.20″ RMS residuals per epoch. One of 17 epochs was rejected as a 4σ outlier (a SPHEREx epoch 5″ off).

## Lessons

Each Learn-mode lesson was checked against the data before it went in. Barnard's Star's motion from W2 visits agrees with the catalogue to under 1%. WISE 0855−0714 has W1−W2 ≥ 3.5. eps Ind A and B move together, with separations of 402.1″ (2010) and 401.5″ (2024). AL Boo gives a 166.6 d period (VSX 166.7 d); we used it instead of R Dra, which saturates. The eps Ind A ghost appears at the predicted 114-pixel offset in all 22 W2 visits, and the asteroid (888) Parysatis is found within 2.75″ of its ephemeris in every exposure.

## AI review

Before we claim a science result, we ask an AI model (a large language model) to try to break it. It gets the claim and the evidence files, recomputes every number from catalogues and raw data with its own scripts, searches the literature for prior work, and marks each sub-claim as holds, weakened or wrong. It returns a claim-by-claim table and suggested wording, which we used. It is a model, not a human referee, so it can miss things or be wrong too.

It changed something in every claim we gave it. For WISE J2317−6659 it found that a type had already been published and that our distance rested on a mis-quoted calibrator. For J2358−5218 it found two earlier pair listings, a Gaia temperature and a second photometric type, and it ruled out calling the object a brown dwarf. For the SDSS J1343−0220 pair it kept the claim as a candidate but corrected the separation, distance, type and motion agreement, found five radial velocities we had said did not exist, and showed that the host star is probably an unresolved binary. For the WISE J2354−8140 pair it found a neighbouring star that biased our W1 positions, cut our "seven" motion estimates to two independent ones, and raised the chance of a coincidence to about 10%. The details are in [results.md](results.md).
