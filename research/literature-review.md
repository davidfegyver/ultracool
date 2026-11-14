# Literature & Tool Review — Ultracool Browser Pipeline Improvements

*(No repo files modified; this is the complete deliverable.)*

## 1. Motion detection

**References:** CatWISE2020 (Marocco et al. 2021, [IOPscience](https://iopscience.iop.org/article/10.3847/1538-4365/abd805), [IRSA README](https://irsa.ipac.caltech.edu/data/WISE/CatWISE/gator_docs/CatWISE2020README_IRSA.txt)); CatWISE Preliminary (Eisenhardt et al. 2020, [IOPscience](https://iopscience.iop.org/article/10.3847/1538-4365/ab7f2a)); unWISE time-resolved coadds (Meisner et al. 2018, [arXiv:1710.02526](https://arxiv.org/abs/1710.02526); Meisner et al. 2019 unWISE 5-yr, [IOPscience](https://iopscience.iop.org/article/10.1088/1538-3873/ab3df4)); unTimely (Meisner et al. 2022/23, [IOPscience](https://iopscience.iop.org/article/10.3847/1538-3881/aca2ab), [arXiv:2209.14327](https://arxiv.org/abs/2209.14327)); Backyard Worlds (Kuchner et al. 2017, [IOPscience](https://iopscience.iop.org/article/10.3847/2041-8213/aa7200); 3000 candidates paper, [IOPscience](https://iopscience.iop.org/article/10.3847/1538-3881/ae5b60); WiseView, [blog](https://blog.backyardworlds.org/2017/09/13/wiseview)).

CatWISE fits a 2-parameter linear motion model (RA, Dec vs. time) to detections grouped into **~12 epochs over an 8-year baseline** (coadds of same-visit exposures), using the AllWISE WPHOT-derived PSF-fit astrometry per epoch, then reports `pmra`/`pmdec` with formal errors and a motion-significance statistic. unWISE/unTimely instead build **one coadd per ~6-month sky pass** ("epoch"), each from ≳12 single exposures stacked with per-pixel outlier rejection, then run **crowdsource** PSF photometry independently per epoch at low per-epoch S/N thresholds (**S/N=4.0 in W1, 2.5 in W2**) and link detections across epochs, enabling faint movers CatWISE misses. WiseView/Backyard Worlds presents these same per-epoch coadds as a human-viewable flipbook; volunteers flag an object as a real mover if it displaces consistently frame-to-frame (not a single-frame "dipole", which they explicitly call out as a pointing jitter artifact, not real motion — [FAQ](https://www.zooniverse.org/projects/marckuchner/backyard-worlds-planet-9/about/faq)).

**Recommendation for us:**
1. (M) Implement an automatic PM fit, not just a catalog-predicted track: per-epoch (visit) centroid via the existing aperture photometry's weighted centroid, then weighted linear least-squares fit vs. mjd for RA(t)/Dec(t), giving `pmra_masyr`, `pmdec_masyr`, formal errors, and significance = `pm_total/pm_err`. This is exactly contract item 3's `summary.motion` and item 4's `movers` endpoint. Threshold **significance ≥ 3σ and baseline ≥ 2 yr** to call "moving" (mirrors CatWISE's conservative motion flag and avoids single-epoch centroiding noise). **Effort M, high benefit** — this is the single biggest capability gap vs. "target_px is only predicted."
2. (S) Treat two adjacent SPHEREx/WISE frames differing only by spacecraft pointing jitter as a known false positive ("dipole"): require consistency across ≥3 epochs, not just endpoints.
3. (L, optional) Adopt unTimely-style per-visit low-threshold coadds + independent detection to catch movers *not* already centered on the queried target (feeds the `movers` endpoint search for companions/unknown movers in field).

## 2. Artifact taxonomy

**References:** WISE Explanatory Supplement, ArtID module ([sec4_4g](https://irsa.ipac.caltech.edu/data/WISE/docs/release/All-Sky/expsup/sec4_4g.html), [sec2_4ci cc_flags](https://irsa.ipac.caltech.edu/data/WISE/docs/release/All-Sky/expsup/sec2_4ci.html)); SPHEREx Explanatory Supplement ([PDF](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp_QR.pdf)); SPHEREx electrical-artifact bestiary (2025, [arXiv:2608.09862](https://arxiv.org/html/2608.09862v2), [Pebblous blog](https://blog.pebblous.ai/blog/spherex-detector-artifact-bestiary/en/)).

WISE `cc_flags` per band uses a single-letter code with **upper-case = spurious source (fake), lower-case = real source with contaminated photometry**: `D/d`=diffraction spike (45°/135°/225°/315° from a bright parent, length/width scale with parent mag per empirical tables), `H/h`=scattered-light halo (radial, `log10(r_h)=a·m_p+b`), `O/o`=optical ghost, `P/p`=persistence/latent (image of a previous bright source lingering in later frames — this is the one that most looks like a stationary "fake mover" across epochs because it fades but doesn't move), `G`=glint (off-frame bright source). SPHEREx flags are bit-named in header keywords `MSKNnnnn` and include `GHOST`, `GHOST_FPA`, `PERSIST`, `STREAK`, `SNOWBALL` (cosmic-ray "snowball" halos), `CROSSTALK` (detector electrical crosstalk between H2RG readout channels), `HALO` (applied around SNOWBALL/transient clusters), `BLOOM` (source blooming vs. true transient), `TRANSIENT`/`OVERFLOW`/`SUR_ERROR` (per-exposure on-board flags combined on ground into named composites).

**Recommendation:**
1. (S) We already drop all MSKN bits except SOURCE/FULLSAMPLE as "bad" for SPHEREx photometry — correct, keep it, but **also surface the flag name(s)** in the API/UI (e.g. `flagged_reason: "GHOST"`) rather than a boolean, so users can self-diagnose "real or ghost?" (skill 6). **Effort S, directly implements a taught lesson.**
2. (M) For WISE we currently use *no* masking (`flagged` always false). Add cc_flags/msk parsing from the WISE `-msk-1b` bitmask (contract didn't require it but it's the biggest gap for skill 6 on WISE frames): treat PERSIST (latent) specifically, since it is the WISE analogue of a "ghost that doesn't move" and is the most confusable with a real faint companion.
3. (S) UI: since `D`/`H`/`O`/`P` are radial/linear from a *bright neighbor*, a quick heuristic ("any saturated/bright source within spike-length of target") is cheap and catches most WISE false movers without full bitmask parsing if time is short.

## 3. Asteroid identification

**References:** NEOWISE moving-object pipeline WMOPS ([NEOWISE Expl. Supp. sec4_3](https://wise2.ipac.caltech.edu/docs/release/neowise/expsup/sec4_3.html); Mainzer et al. 2011 [IOPscience](https://iopscience.iop.org/article/10.1088/0004-637X/731/1/53); Mainzer et al. 2014 reactivation [IOPscience](https://iopscience.iop.org/article/10.1088/0004-637X/792/1/30)); IMCCE SkyBoT ([API docs](https://ssp.imcce.fr/webservices/skybot/api/conesearch), [astroquery.imcce](https://docs.astropy.org/projects/astroquery/en/latest/imcce/imcce.html)); JPL SBDB/Horizons/SB-Ident ([ssd-api.jpl.nasa.gov/doc](https://ssd-api.jpl.nasa.gov/doc/sbdb.html), [sbident pkg](https://github.com/bengebre/sbident)).

NEOWISE detects asteroids on **single exposures** (not coadds, because asteroids move between exposures within a visit) via WMOPS, which links tracklets across the ~1-day visit. Typical **main-belt asteroid rates are a few arcsec/hour to a few arcsec/exposure**, enough to displace within one ~1-day WISE visit but show as a point absent in other epochs — exactly skill 7. SkyBoT's REST cone search is trivial to call: `GET https://ssp.imcce.fr/webservices/skybot/api/conesearch.php?-ep=<JD or ISO>&-ra=<deg>&-dec=<deg>&-rs=<radius_arcsec>&-mime=json&-output=basic&-from=UltracoolBrowser` (or use `astroquery.imcce.Skybot.cone_search(SkyCoord, radius, epoch)`); returns name, position, error, apparent rate (arcsec/h). JPL's `sbident` package or `ssd-api.jpl.nasa.gov/doc/sbident.html` offers an equivalent for objects not yet in SkyBoT's catalog (close to real-time discoveries).

**Recommendation:**
1. (S) At WISE-visit granularity, query SkyBoT once per visit midpoint-MJD/field center (geocentric observer code `500` is adequate at WISE's ~arcmin-scale fields) and flag any frame whose field contains a known minor planet within the visit window; mark that work-unit's photometry excluded from stacks (asteroids already get killed by the visit median, this just explains why to the user — the "Asteroid" lesson). **Effort S, cheap win, directly implements skill 7 with a primary-source API.**
2. (M) To actually *show* an asteroid moving within a single WISE visit (current pipeline medians away all 8 exposures per visit), add an opt-in "asteroid mode" using the new `wise_exposures=true` contract flag: render per-exposure frames (already planned) and overlay SkyBoT ephemeris track.
3. JPL Horizons/SBIdent are untested from this host — mark `[INFERENCE]` for reachability; SkyBoT was confirmed reachable via doc fetch only, not a live query from this box in this session.

## 4. Brown dwarf color & spectrum

**References:** Kirkpatrict-descended W1−W2 vs SpT polynomials ([RNAAS 2022](https://iopscience.iop.org/article/10.3847/2515-5172/acaafb)); CatWISE/AllWISE color selection (Meisner 2020 Y-dwarf, [ApJ](https://iopscience.iop.org/article/10.3847/1538-4357/ab6215); Schneider+ extreme T subdwarf, [arXiv:2111.08182](https://arxiv.org/abs/2111.08182)); SPIFF (Gagné et al. 2026, [arXiv:2604.22012](https://arxiv.org/abs/2604.22012)); SPExPI (Kiwy 2026, [RNAAS](https://iopscience.iop.org/article/10.3847/2515-5172/ae707b), [github](https://github.com/fkiwy/spexpi)); SUDA atlas ([arXiv:2604.26771](https://arxiv.org/abs/2604.26771)); xcavation ([PyPI](https://pypi.org/project/xcavation/), [github](https://github.com/huntbrooks85/Xcavation)); IRSA Spectrophotometry Tool ([docs](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html)).

W1−W2 reddens monotonically from ~0 (early M) through L/T transition (~1.5–2.5) to Y dwarfs (>2.5–3+), the basis of our `summary.color` verdicts — thresholds in the plan's spec roughly match the published polynomials. SPIFF's actual method (now confirmed from the published paper, not just the abstract): builds **47 hybrid templates per subtype M9–Y1**, combining empirical SPHEREx spectra with synthetic photometry from spectroscopic standards blueward of 2.4 µm, and does analytic-amplitude χ² typing — matches what our `spectral.py` already does; this is a direct validation of our chosen approach. SPExPI adds **PSF-fit photometry** (vs. our aperture) specifically tuned for fast-moving sources — relevant to our note that SPHEREx photometry has no aperture correction PSF fit. xcavation is a general SPHEREx retrieval+photometry toolkit (less specialized, lower priority).

**Recommendation:**
1. (S) No change needed to spectral typing approach — it already follows SPIFF's published method closely; just verify bin table/template provenance citation in export.csv header (contract item 5 already requires citations).
2. (M) Consider SPExPI-style PSF-fit flux as an upgrade path for SPHEREx photometry (currently aperture + EPSF correction, no full PSF fit) — would reduce flux scatter for faint UCDs like WISE 0855. **Effort M, defer unless spectra for faint targets are visibly noisy.**
3. (S) Add molecule-band highlighting already planned (CH4 3.3 µm, CO 4.6 µm, CO2 4.3 µm, H2O) — confirmed scientifically standard in SPIFF/SUDA discussions.

## 5. Common proper motion pairs

**References:** Gaia-DR2 wide-binary catalogs ([IOPscience 2019](https://iopscience.iop.org/article/10.3847/1538-3881/aafacc); SUPERWIDE [IOPscience](https://iopscience.iop.org/article/10.3847/1538-4365/ab79a6)); Gaia EDR3 resolved CPM companions ([A&A 2022](https://www.aanda.org/articles/aa/full_html/2022/01/aa42146-21/aa42146-21.html)).

Standard criteria combine (a) **proper-motion agreement within relative error** (commonly a 10–20% relative-PM-difference cut, or a χ²-style PM-vector-difference significance test), (b) **parallax/distance agreement** when available, and (c) a **plausible projected separation** (physical binaries cut at some max separation in AU given distance, or for wide-field visual pairs simply "both fall inside the field and share PM direction within N°").

**Recommendation:** (S) For `movers` endpoint common-proper-motion flagging between target and any other detected mover in field (Epsilon Indi A/Ba/Bb lesson): flag a pair if `|ΔPM_vector| / sqrt(σ1²+σ2²) < 3` (3σ agreement) **and** angular separation < 20′ (SPHEREx FOV-scale). No parallax available from our pipeline, so skip that criterion — note as a known limitation. **Effort S, directly implements skill 3.**

## 6. Variability classification

**References:** WISE periodic variables ([arXiv:2012.04690](https://arxiv.org/abs/2012.04690)); Astropy Lomb-Scargle docs ([docs.astropy.org](https://docs.astropy.org/en/stable/timeseries/lombscargle.html)); ASAS-SN Mira classification criteria ([arXiv:1809.07329](https://arxiv.org/abs/1809.07329)); YSO mid-IR variability study ([arXiv:2312.05753](https://arxiv.org/abs/2312.05753)).

ASAS-SN defines Mira as **amplitude ≳2.5 mag (V), period >100 d**, decreasing toward longer wavelength (R Dra's ~245 d period at WISE wavelengths will show smaller but still large amplitude). WISE's ~6-month revisit cadence (≈2 visits/year, few exposures each) is classically under-sampled for periods near 1 yr (strong 1-yr aliasing in Lomb-Scargle); published WISE periodic-variable work explicitly flags and tries to break the 1-year alias. With only 20–40 epochs over several years, robust period recovery needs a **false-alarm-probability threshold** (Astropy LS gives `false_alarm_probability`), and periodic vs. stochastic distinguished by: periodic → LS power peak with FAP < 0.01 **and** phase-folded scatter ≪ raw scatter; stochastic/irregular (T Tauri/RW Aur) → no significant LS peak but reduced χ² ≫ 1 against a constant model.

**Recommendation:**
1. (M) Implement Lomb-Scargle via `astropy.timeseries.LombScargle` on per-band flux vs mjd (needs ≥8 epochs), report `period_days` only if FAP < 0.01, else null; classify "periodic variable" (LS significant), "irregular variable" (`chi2_red` vs constant > ~3 but no LS peak), "constant" (`chi2_red` ~1), "insufficient data" (<5 epochs) — matches contract's `summary.variability` shape exactly. **Effort M, required by contract, high benefit for both R Dra and RW Aur lessons.**
2. (S) Explicitly flag/suppress the 1-year and 0.5-year aliases in the reported period (check if best period is within ~5% of 365.25 or 182.6 d and demote confidence) since WISE sampling guarantees these are spurious for many objects.

## 7. Noise filtering

**References:** Gnuastro coadd outlier rejection ([IOPscience](https://iopscience.iop.org/article/10.3847/2515-5172/aea78e)); Zackay & Ofek "How to COAAD Images I/II" (ZOGY, [ApJ 2017](https://iopscience.iop.org/article/10.3847/1538-4357/836/2/187)); LSST DMTN-015 coadd flavors ([dmtn-015.lsst.io](https://dmtn-015.lsst.io/)); AWAIC WISE coadder ([arXiv:0812.4310](https://arxiv.org/abs/0812.4310)).

Standard practice: **sigma-clipped mean/median** rejects per-pixel outliers (cosmic rays, single-frame artifacts) before coaddition — we already do this for `stack.png`. ZOGY-style "proper coaddition" and PSF-matched detection correlate each image by its own PSF before stacking for optimal S/N, and account for **correlated noise introduced by resampling/reprojection** (reprojection smooths noise and breaks the simple √N scaling — our `reproject_interp` bilinear step introduces exactly this correlation, currently uncorrected in our VARIANCE-based error propagation).

**Recommendation:**
1. (M) For WISE visit medians, switch simple `nanmedian` to **sigma-clipped median** (reject >3σ pixels before combining) — catches cosmic rays/short transients within a visit that a plain median of only 8 exposures may still pass. **Effort S–M, improves robustness of all WISE flux measurements.**
2. (L, defer) Correlated-noise correction after `reproject_interp` resampling (ZOGY/ Gnuastro-style) — real but complex; our current flux errors (from VARIANCE propagation) are likely mildly underestimated post-resampling. Document as a known limitation rather than fix under hackathon time pressure.

---

## Top-10 Ranked Action List

| # | Action | Topic | Effort | Benefit |
|---|---|---|---|---|
| 1 | Automatic PM fit (weighted linear LSQ on measured centroids) → `summary.motion` + `movers` | 1 | M | Core "does it move?" capability, fixes known weakness |
| 2 | Lomb-Scargle variability classification with FAP threshold + alias flagging → `summary.variability` | 6 | M | Required by contract, powers R Dra/RW Aur lessons |
| 3 | Common-proper-motion pair flagging (3σ PM agreement, <20′ sep) in `movers` | 5 | S | Powers Epsilon Indi lesson directly |
| 4 | Surface SPHEREx flag *names* (GHOST/PERSIST/STREAK/...) not just boolean | 2 | S | Core to "real or ghost?" lesson |
| 5 | SkyBoT cone-search per visit to flag/explain asteroid-affected frames | 3 | S | Cheap, real external API, powers asteroid lesson |
| 6 | Sigma-clipped (not plain) median for WISE visit stacking | 7 | S–M | Robustness across all photometry |
| 7 | WISE cc_flags/msk bitmask parsing → `flagged` for WISE frames (currently always false) | 2 | M | Closes a named weakness |
| 8 | Document/tag 1-yr & 0.5-yr period aliases as low-confidence | 6 | S | Avoids false "periodic" claims from WISE cadence |
| 9 | PSF-fit (SPExPI-style) photometry for faint SPHEREx sources | 4 | M | Better spectra for faint UCDs like WISE 0855 |
| 10 | Correlated-noise correction after reprojection | 7 | L | Real but defer; document as limitation |

**Could not verify in this session:** JPL Horizons/SBIdent reachability from this host (web docs only, no live test); whether our WISE `-msk-1b` files are actually fetched anywhere in `sources.py` today (grep showed WISE flagging is currently hardcoded false, consistent with the plan's stated weakness, but I did not re-read the full `sources.py` to confirm no partial implementation exists).