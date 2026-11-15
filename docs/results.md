# Results

We used the app on real candidates during and after the hackathon. This page lists what came out, how sure we are, and what would confirm each result. Every claim here was put through an independent adversarial review: a separate check that tried to break each number against raw data, catalogues and the original papers. Where that review changed our wording, we say so.

A note that applies to every spectral type below: SPHEREx gives low-resolution spectrophotometry (R ≈ 40–130), not a slit spectrum, so a "type" means a match to the SPIFF templates (Gagné et al. 2026). "First" always means the first we found in SIMBAD, VizieR, the UltracoolSheet, the SPIFF table, arXiv and a web search as of November 2026. We had no token for NASA ADS, so ADS full text was not searched.

## WISE J2317-6659 gets a spectrum-based type

WISE J231728.42−665959.3 (= CWISE J231728.89−670001.1) is a faint source that Backyard Worlds volunteers flagged as a possible brown dwarf. Rothermich et al. (2024) estimated a type of T6 from its W2 brightness at the distance of a nearby star pair, HD 219509/219495. That was an estimate, not a measurement.

What we found: its SPHEREx 0.75–5 µm spectrum (453 frames, 89 channels) matches mid-T brown-dwarf templates, ≈T6 ± 1. That is the first spectrum-based type we could find, and it confirms Rothermich's estimate. The spectrum shows the J and H peaks, the 1.4 µm water band, a methane trough at 3.0–3.6 µm, a peak at 4.1 µm and a CO dip at 4.3–4.7 µm. It moves ≈0.5″ per year across 16 years of WISE and SPHEREx images. Five independent proper-motion estimates give 0.48–0.52″/yr, including one from AllWISE to VHS that does not use our pipeline at all: (423, −266) ± 44 mas/yr. Its photometric distance is about 31 pc (26–40 pc) from the Kirkpatrick et al. (2021) relations, which is consistent with the star pair's 28.5 pc. But it moves 140–180 mas/yr (about 20 km/s) differently from the pair, while a bound companion at that separation would differ by less than 1 km/s. So it is not their companion, as Rothermich et al. had already judged likely with a 5.1% co-moving probability.

How sure: high that it is a field mid-T dwarf moving ≈0.5″/yr, and high that it is not bound to HD 219509/219495. The subtype is not: T5, T6 and T7 swap order with one fitting choice, and only 35 of the 89 channels have S/N > 3. T4 and earlier are excluded in every variant (Δχ² ≥ 22).

What is not shown: an exact subtype, a parallax, or anything about gravity or metallicity. Our own W1−W2 (2.08–2.19) is about 0.3 mag redder than the catalogue value of 1.8 (CatWISE 1.83 ± 0.05) because our faint-source W1 comes out too faint; we quote the catalogue colour.

What would confirm it: a near-infrared slit spectrum for the subtype, and a trigonometric parallax for the distance.

What the review changed: our first wording said "typed for the first time" and "a type guessed from its colours". Both were wrong. Rothermich had given a type, and they derived it from brightness at an assumed distance, not from colours. The review also replaced our first distance (27–30 pc, from a single calibrator star whose parallax we had quoted wrongly) with ≈31 pc (26–40 pc) from published relations, softened "sits at the same distance" to "is consistent with", narrowed "T5–T6" to "≈T6 ± 1", and credited the "not a companion" result to Rothermich, since we only confirm it.

## First SPHEREx types for three Rothermich candidates

We screened the 109 companion candidates of Rothermich et al. (2024). 74 had only photometric types, and 15 of those already had SPHEREx types in the SPIFF table, so a "first type" claim would be false for them. After cuts on brightness, crowding and galactic latitude, 12 were measured. Three get a first spectrum-based type that survives every self-check: the fitting variants agree, the other photometry method gives the same answer, the colours fit, and there is no sign of extra neighbour light. None of them is a confirmed companion.

| Object | Photometric type (Rothermich+24) | Our SPHEREx type | Companion |
|---|---|---|---|
| CWISE J102322.00−204549.9 | (L3) | late-M, ≈M8–M9 (L3 excluded, Δχ² ≈ 490) | refuted: Gaia DR3 Δμ = 19 mas/yr (8.6 km/s, bound limit 0.14 km/s) |
| CWISE J124033.48+460544.7 | (M9) | ≈L1 ± 1 (M9–L3) | not confirmed: moves with its host, but at L1 it is at 88–92 pc vs the host's 124 ± 5 pc |
| CWISE J011003.61−592650.8 | (L2) | late-M, ≈M8 (M7–M9; L2 excluded, Δχ² ≈ 170) | not confirmed: moves with the white dwarf, but its distance at M8 is 1.8σ beyond the WD's 110 ± 10 pc |

J1023−2045 has 75 channels at S/N > 5. Its own Gaia parallax gives an absolute W2 magnitude that matches M7–L0, which agrees with the spectrum. Gaia's motions show it is not bound to the star once proposed as its partner, which confirms Rothermich's 0%.

J1240+4605 has the same type, L1, with plain aperture photometry and with neighbour-subtracted photometry, so the host 19″ away does not drive the result. It shares the host's motion across 2MASS, WISE and SPHEREx (1998–2026). An unresolved equal-mass binary or a type at the early end of the range would fix the distance gap; neither is tested.

J0110−5926 has VHS J−Ks = 0.84 ± 0.06, which points to M7–M8 and excludes L2. Our automatic verdict scored it "confirmed", but we downgraded it by hand: the one distance check that does not depend on our templates (J−Ks) makes the gap larger.

What is not shown: M8 is the earliest SPIFF template, so "M8" means "M8 or earlier". Gravity classes (β, γ) are not validated for SPHEREx, so we do not claim them. What would confirm them: optical or near-infrared slit spectra, a parallax for J1240+4605 and J0110−5926, and radial velocities for the companion questions.

### J2358−5218: narrowed, and inconclusive in our own screen

CWISE J235827.96−521813.4 gave a clean-looking match (L0, range M9–L1). Our own screen marked it inconclusive, because its SPHEREx 1.2 µm flux is 1.8× its catalogue J brightness, probably light from the G = 11.4 host 30″ away that our neighbour model does not see.

The adversarial review then narrowed what could be said even if the spectrum were clean. L0 is not separated from M9, so the honest label is M9–L0. Gaia DR3 had already estimated its temperature (2295 ± 256 K) from a low-quality optical RP spectrum, so "first" can only mean the first infrared (1–5 µm) spectrum. A second photometric type (L0, dal Ponte et al. 2023) already existed. The pair itself was listed before Rothermich, by Hartman & Lépine (2020) and Kervella et al. (2022), and a spectrum cannot confirm a co-moving probability; Gaia astrometry does that, with Δμ = 0.0 ± 2.1 mas/yr. Finally, its mass is 0.075–0.084 M☉ if the system is 1 Gyr or older, so it sits at the star/brown-dwarf boundary and should not be called a brown dwarf. We do not count it as a result.

## Two candidate wide pairs

### SDSS J134338.74−022044.6 and UPM J1343−0220

We searched 3,293 fast-moving ultracool dwarfs from the UltracoolSheet against Gaia DR3 for wide companions. We recovered about 90 known pairs and found one that we could not find reported anywhere we could reach: the dwarf SDSS J134338.74−022044.6 (≈L0, L0–L1) and the M0 star UPM J1343−0220 (G = 12.3) at 83 pc. They are 45.15″ apart, about 3,760 au.

Over 16 years their motions on the sky agree to within about 2%: 3–4 ± 3.5 mas/yr on a 186 mas/yr motion, or about 1.5 ± 1.4 km/s. The dwarf's brightness puts it at about 85 pc (roughly 70–100 pc), matching the star's parallax distance. No other Gaia DR3 star in 100 square degrees shares that motion and distance, so the expected number of chance alignments within 45″ is below 1.4 × 10⁻⁵. The pair was probably missed because the dwarf has only a 2-parameter Gaia solution (no parallax or proper motion), so every Gaia-based wide-binary catalogue excludes it by construction.

How sure: a candidate wide co-moving pair, not a discovery and not a confirmed binary. The velocity error is larger than the escape speed (0.6–0.75 km/s), so boundness is not tested. The host star appears to be an unresolved binary itself (RUWE 6.65, a changing Gaia proper motion, and 0.73 mag over-luminous for its colour), so its Gaia motion is not a clean systemic motion and the system may be a triple. Five radial velocities have been published or produced for the L dwarf, all from one SDSS spectrum with S/N ≈ 1–4 per pixel; they range from +1.4 to −285 km/s and are unusable, but one of them (+1.4 ± 12.4 km/s, Schmidt et al. 2010) taken at face value would disagree with the host's −49.6 km/s.

What would confirm it: Gaia DR4, released on 2 December 2026, should give the dwarf its own parallax and proper motion and the host an orbit solution, so it can confirm or rule out the association. A radial velocity of the L dwarf to about 3 km/s would confirm it independently.

What the review changed: the independent adversarial review kept the claim as a candidate pair but corrected our numbers. The separation is 45.15″ (3,760 au), not 44.1″; the distance is ≈85 pc (≈70–100), not 84 ± 6 pc; the type is ≈L0 (L0–L1) rather than a firm L0; the motion agreement is 3–4 ± 3.5 mas/yr, not 1.5 ± 3.5; and our statement that no radial velocity exists was wrong. It also dropped our remark that the system's speed hints at a thick-disk origin.

### WISE J235447.80−814044.9 and WD J235419.41−814104.96

WISE J2354−8140 is a known T dwarf (T6.4 from methane imaging, Tinney et al. 2018; T7 adopted by Kirkpatrick et al. 2021). It sits 63.79″ (1,719 au) from a magnetic, metal-polluted (DZH) white dwarf at 26.95 ± 0.04 pc. We found no paper that pairs the two.

Its motion agrees with the white dwarf's Gaia motion of (96, 36) mas/yr in every estimate we trust. The one that does not use our pipeline at all, AllWISE to VHS after correcting the catalogue zero-points against Gaia, gives (93 ± 30, 23 ± 28) mas/yr. Our own WISE W2 and SPHEREx positions give (124 ± 19, 49 ± 19) mas/yr. Both are 3–7σ away from zero motion, so it is not a background source. Its brightness and colours point to T7.0–T7.3, and at T6–T7.5 its photometric distance matches the white dwarf's (25.7 pc, 22–30 pc, for T6.4). A T8 or an early T would not fit.

How sure: a candidate co-moving pair, not a confirmed one. The T dwarf has no parallax, and our motions are good to about 20–30 mas/yr (≈3 km/s), four times too coarse to test whether the pair is bound (escape speed 0.73 km/s). Stars with similar motion and distance are not rare in this part of the sky, so there is roughly a 10% chance that the match is a coincidence somewhere in our search of 3,293 dwarfs. The SPHEREx spectrum shows a T dwarf from its 3–5 µm shape but is too faint and blended to give a subtype, so we do not claim one. Zhang et al. (2025) ran a search designed for such pairs; with the uncorrected CatWISE motion they used, this pair falls just outside their cut, so "not reported" does not mean "never seen". If the pair is real, the white dwarf's cooling age makes the system older than about 6 Gyr.

Four white dwarf + T dwarf wide pairs are confirmed and about five more are published candidates, so this would not be a first in general. It is not the nearest (Wolf 1130 C is at 16.6 pc) and not the first with a magnetic white dwarf (LSPM J1459+0851). As far as we know it would be the first with a white dwarf that is both magnetic and metal-polluted, which is a narrow distinction.

What would confirm it: a parallax and a better proper motion for the T dwarf, for example from a few more years of infrared imaging.

What the review changed: it found that a static star 8.2″ away pulls our WISE W1 positions by up to 1.7″, so we dropped W1 from the motion fit. It showed that our "seven proper-motion estimates" share data and amount to two independent ones. It also repeated the chance-alignment estimate in a larger Gaia field and found nine look-alike stars where we had found none, raising the chance of a coincidence from below 4% to about 10%. As a check on our astrometry, the same pipeline measured the white dwarf itself to within 0.65σ of its Gaia motion (see [validation.md](validation.md#motion)).

## What did not work

Negative results are part of the story, because they show why the images need to be looked at.

All 7 SPIFF "New Candidates" we tested were not new brown dwarfs. Two were diffraction spikes (J2011−0624, J0104+1244), one sat on the halo of a bright star (J0109−4652), one lay on a scattered-light streak from IRC+10216 (J0946+1355), one was an embedded young star with ice absorption (J0807−3443, IRAS 08057−3434), one was a source in the galaxy M33 (J0133+3048), and one was the known T6 dwarf 2MASS J11225550+2550250. CatWISE gave several of them spurious motions of up to 1.7″/yr.

A second run processed 21 more fields from SPIFF and from SIMBAD objects marked as possible brown dwarfs. No new brown dwarf came out, and no object got a reliable new type. One SPIFF candidate was a spike artifact, and for J1721+5950 three independent fits showed that CatWISE's 12σ motion is not real. A known T3.5 control failed because three neighbouring stars blended with it, which showed us that our contamination test did not work for slow movers.

The embedded young star IRAS 08057−3434 is still a false "match" in our spectral typing (L7 γ). We tried to veto it with its ice bands at 3.05 and 4.27 µm, but real brown dwarfs show residuals of the same size there, so the veto would have mislabelled them. We rejected it; see [validation.md](validation.md#known-failure-modes).

## References

- Best, W. M. J. et al., UltracoolSheet v2.1.0, Zenodo 15802304
- Dal Ponte, M. et al. 2023, MNRAS 522, 1951
- Day-Jones, A. C. et al. 2011, arXiv:1008.2960 (LSPM J1459+0851 + ULAS J1459+0857)
- Gagné, J. et al. 2026, arXiv:2604.22012 (SPIFF)
- Hartman, Z. D. & Lépine, S. 2020, ApJS 247, 66 (SUPERWIDE)
- Kervella, P. et al. 2022, A&A 657, A7
- Kirkpatrick, J. D. et al. 2021, ApJS 253, 7
- Mace, G. N. et al. 2013, arXiv:1309.1500 (Wolf 1130 C)
- Rothermich, A. et al. 2024, AJ 167, 253; arXiv:2403.04592
- Schmidt, S. J. et al. 2010, AJ 139, 1808
- Tinney, C. G. et al. 2018, ApJS 236, 28
- Zhang et al. 2025, arXiv:2505.24560 (Benchmark brown dwarfs I)
