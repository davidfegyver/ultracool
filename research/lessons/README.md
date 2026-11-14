# Lesson data (LessonFinder)

`lessons.json`: 7 specs. Coordinates are epoch 2000 with PM, so the existing `POST /api/sequences` body is
`{ra, dec, pmra_masyr, pmdec_masyr, epoch_yr, fov_deg, mjd_min, mjd_max, wise_exposures}`.
Extra optional keys: `markers` (lessons 3, 6: objects to circle, since the target circle sits on empty sky or on the star),
`stack_windows` (lesson 2: MJD windows for `stack.png`), `track` (lesson 7: per-exposure ephemeris), `alternative` (lesson 4).

| # | Lesson | Object / setting | Verified? | How | Montage |
|---|---|---|---|---|---|
| 1 | Something moves | Barnard's Star, fov 0.076, W2 + D6 | yes | W2 visit-median centroids 2010-2024: PM (-820, +10417) mas/yr vs catalog (-802, +10362); 10.45"/yr | `lesson1_barnard.png` |
| 2 | Right color | WISE 0855-0714, fov 0.066, W1 vs W2, 2-yr deep stacks | yes | production manifest: W2 = 461±6 µJy (13.93 mag), W1 = 8±3 µJy (~18.9), W1-W2 ≥ 3.5; dot in W2 stacks, nothing in W1 | `lesson2_w0855_stacks.png` |
| 3 | Move together | eps Ind A+B, centre = midpoint, fov 0.2 (fits; 0.25 also fits) | yes | A (3932, -2554) ±(39, 28), B (4006, -2493) ±(130, 122) mas/yr; separation 402.1" (2010) and 401.5" (2024) | `lesson3_epsInd_A_B_W2.png` |
| 4 | Brightness changes | **AL Boo** (Mira, P 166.7 d) replaces R Dra | yes (AL Boo) | this repo's backend pipeline on WISE visits gives W1 range 0.99 mag, LS period 166.6 d (VSX 166.7). R Dra is saturated, so the in-app flux is null for all frames. Catalog photometry still gives R Dra P = 246.4 d (VSX 246.1) | `lesson4_5_lightcurves.png` |
| 5 | Dusty disk, no pattern | RW Aur, fov 0.05, W1/W2 | yes (catalog only) | NEOWISE single-exposure catalog: W2 range 2.3 mag, W1 range 1.3 mag, no significant period (FAP 0.06). **In-app flux is null** (saturated) | `lesson4_5_lightcurves.png` |
| 6 | Real or ghost? | W2 optical ghost of eps Ind A, centre 60" E of A, fov 0.25, 2014-04 to 2015-11 | yes | ring at the predicted +114 detector-px offset in all 22 W2 visits (mean 7σ/px) that swaps sides every 6 months (PA 242° vs 62°, 316"). The opposite-season spot reads 0.05σ. IRSA ARTID `-art-w2-O.tbl` flags it in 11/13 frames. Second example: cosmic-ray exposure 11779r110 (in the SAA) has 150 one-frame blobs vs 1-4 | `lesson6_ghost_epsInd_W2.png`, panel 2 of lesson 7 |
| 7 | Asteroid | (888) Parysatis, 2019-11-27/28, wise_exposures, fov 0.25 | yes | IRSA MOST ephemeris; 13 W2 + 13 W1 L1b exposures from S3; 246-505σ peaks within ≤2.75" of the ephemeris in every exposure. The same spots in other exposures read 1.9σ (median), and 6 other visits 2010-21 read 0.9σ. Motion 24.5"/h, 77" per exposure gap | `lesson7_asteroid_888_parysatis_W2.png` |

## Findings that affect the app
- WISE photometry is null for saturated stars: Barnard, R Dra and RW Aur have `flux_ujy=null` in every WISE frame of the production manifests, and in nearly all SPHEREx frames. Lessons 4 (R Dra) and 5 would show empty light curves. Either use AL Boo (done for lesson 4), add a fallback to `neowiser_p1bs_psd` catalog photometry, or both. Do not mix AllWISE and NEOWISE saturated mags: they differ by about 2 mag in W2 for R Dra.
- The 6-month cadence aliases Mira periods: AL Boo's 166.7 d cycle looks like a 5.2-year wave. A periodogram plus a phase fold recovers the true period.
- The default visit median erases asteroids (montage panel "median of the visit"). Lesson 7 needs `wise_exposures=true` with an MJD window of 1.5 d or less.
- Ghost geometry from WISE Exp. Supp. IV.4.g Table 17: the W2 ghost sits at (+114, 0) detector px and appears for parents with W2 ≤ 4.5. Barnard's Star (W2 ~3.8) has only a faint ghost, while eps Ind A gives an obvious ring. The per-frame artifact tables `<frame>-art-w{1,2}-{D,H,O,P}.tbl` (spikes, halos, ghosts, latents) are in the S3 bucket next to each L1b frame.

## Files
- `man/*.json`: production manifests (read-only GET).
- `phot_*.xml`: IRSA SCS photometry.
- `ast/`, `ghost/`: S3 section reads (npz + json) and the scripts that made them, `read_ast.py` and `read_ghost.py`.
- `run_wise_units.py`: runs the backend's WISE visit units for one target. It expects the current `_make_frame(sid, p, wcs, shape, fid, kind, ok)` signature.
- `alboo_wise_pipeline.json`: its output for AL Boo.
- `most_*.pkl`: IRSA MOST results.
- `mira_cands.csv`: SIMBAD candidate Miras.
