# WISE J235447.80−814044.9 (T dwarf) + WD J235419.41−814104.96 (DZH white dwarf): a new wide WD + T dwarf pair?

Date: 2026-11-15. Candidate from `research/companions/out/survivors_all.csv` uid 3873.
The evidence standard follows `research/verification/J2317_ADVERSARIAL.md` and `J2358/J2358_ADVERSARIAL.md`.
Every number below points to a file in this directory. No repo code was edited.

## Verdict

**It can be claimed only as a *candidate* co-moving pair that has not been reported before. It cannot be claimed as a confirmed binary, and the SPHEREx spectral type cannot be claimed.**

What holds:
- The T dwarf moves the same way as the white dwarf. Seven proper-motion (PM) estimates from four independent data sets (WISE, VHS, SPHEREx, CatWISE) all agree with the WD's Gaia PM within 0.2–1.9σ (p = 0.06–1.0).
- Its photometric distance agrees with the WD's parallax distance:
  - 25.7 (22–30) pc from W2 and 26.5 (23–31) pc from Spitzer ch2, for T6.4 (Kirkpatrick+2021 relations).
  - The WD is at 26.95 ± 0.04 pc.
- A chance alignment this close in position, distance and motion is unlikely: < 1.3×10⁻⁵ per T dwarf, < 0.04 over our whole 3,293-object search (strict criteria; 0.25 with loose criteria).
- No catalogue or paper we could reach pairs the two objects (see Literature).

What does not hold, or is weaker than it looks:
1. **"Bound binary" is not shown.**
   - Our best PM difference is Δv_tan = 4.9 ± 2.7 km/s, with estimates ranging 0.2–5.5 km/s.
   - The escape speed at 1,719 au is only 0.73 km/s.
   - The PM errors (~21 mas/yr ≈ 2.7 km/s) are 4× too large to test boundness. The data are consistent with a bound pair, nothing more.
2. **The SPHEREx spectral type is not robust. Do not claim "first spectrum-based type".**
   - The pipeline says T8 (range T7–Y0), but with χ²ᵣ = 3.5.
   - The best template jumps between T8, T5, T7 and even L7γ depending on which channels are used.
   - At 1–2.4 µm the object is essentially undetected: 2 of 28 bins have S/N > 3.
   - A CatWISE neighbour 8.2″ away carries more light than the target at 1.6–3.8 µm.
   - T8 would also put the dwarf at 15–20 pc, in 2–3σ tension with the WD distance.
3. **Earlier PM catalogues were weak and are not quite "consistent":** with the uncorrected IRSA CatWISE2020 PM (the value Kirkpatrick+2021 lists), ΔPMRA = 46 mas/yr (p = 0.06). That fails the Zhang+2025 cut |Δμ| < 40 mas/yr, which is probably why their search, which was designed to find exactly this kind of pair, did not list it.
4. **The WD age is a lower limit, not a clean benchmark.**
   - The cooling age is 5.6–5.8 Gyr from the uncorrected Gaia mass (0.46–0.48 M☉), or 7.8 Gyr from O'Brien+2024's corrected mass (0.594 M☉).
   - The uncorrected mass is below any single-star initial–final mass relation (IFMR).
   - Total age ≳ 8 Gyr, plausibly 10–13 Gyr, with an unquantified systematic error.
5. **The T dwarf's type is photometric only:** T6.4 from CH4 imaging (Tinney+2018) and T7 adopted by Kirkpatrick+2021 (`SpAd = 17.0`). It has no spectrum-based type, ours included.

## Claim-by-claim

| # | Claim | Value | Independent check | Verdict |
|---|---|---|---|---|
| 1 | T dwarf PM ≈ WD PM | WD Gaia DR3 (96.03 ± 0.07, 36.29 ± 0.07) mas/yr (`vz_gf21_wd.tsv`) | 7 T-dwarf estimates; see the PM table below (`pm_fit_out.json`) | **holds** (all p ≥ 0.06; 6 of 7 p ≥ 0.18) |
| 1b | our pipeline astrometry is trustworthy at this level | Control: the same pipeline and images measure the **WD** at (86.3, 26.7) ± 14.9 mas/yr, i.e. Δ = (−9.7, −9.6) from Gaia (0.65σ). Per-epoch residuals vs Gaia: 0.20″ RMS per axis. 1 of 17 epochs rejected as a 4σ outlier (a SPHEREx epoch 5″ off). | `wd_control.py` → `wd_control_out.json` | **holds** (no systematic > ~15 mas/yr) |
| 1c | CatWISE agrees | II/365 (offset-corrected): (121.8 ± 25.8, 70.6 ± 23.1), p = 0.20. IRSA (uncorrected): (141.8, 72.8), p = 0.06. The WD's own CatWISE II/365 PM is (91.5 ± 14.2, 52.0 ± 12.5), so the relative T−WD CatWISE PM is (30 ± 29, 19 ± 26). | `vizier_II365_catwise.tsv`, `irsa_catwise_2020.tbl`, `lit/vizier_specific_rows.txt` | **holds** (≤ 1σ relative) |
| 2 | Separation | 63.79″ at 2016.0, PA 72°, **1,719 au projected** | `pm_fit_out.json` → `separation_2016` | holds |
| 3 | Photometric distance = WD distance | T6.4: W2 → 25.7 (22.1–29.9) pc; Spitzer ch2 → 26.5 (23.0–30.5); VHS J → 31.9 (24.2–42.1). T7: 23.3–24.0 pc. UltracoolSheet empirical T6: 27.1 (22.9–32.0), T7: 23.4 (20.7–26.6). WD: 26.95 ± 0.04 pc. | K21 Table 13 polynomials copied from `ref/kirkpatrick2021_text.txt` l.4246ff; UltracoolSheet v2.1.0 (`physics.py`) | **holds** (≤ 0.5σ for T6–T7) |
| 3b | Type implied by the WD distance | M_ch2 = 12.85 → T5.4 ± 1.3. W1−W2 = 2.21 → T6.9 ± 1.2. ch1−ch2 = 1.55 → T7.3 ± 1.3. | `physics_out.json` → `at_WD_distance`, `K21_SpT_from_W1-W2`, `K21_Spitzer` | consistent with T6–T7 |
| 4 | SPHEREx type (pipeline T8, T7–Y0) | 76 bins: median S/N 1.9, 24 bins > 3σ, 10 bins > 5σ. Detected only above 2.4 µm (S/N > 3 in 22 of 48 bins; 2 of 28 below). Best fit by variant: all bins T8 (χ²ᵣ 3.48); no spread T8; 1–2.5 µm Y1/sdT4 (flat, everything within Δχ² 6); **2.5–5 µm T5 (with spread) / T7 (without)**; S/N > 3 bins only **T5** (χ²ᵣ 0.74, T6 +44); **dropping the neighbour-dominated 1.6–3.8 µm: L7γ**. | `spectral_refit.py` → `spectral_refit_out.json`, `spectral_refit_stdout.txt`; `dev_spectrum.json` (`neighbour_frac` D3 1.26, D4 1.38) | **not robust → do not claim a type** |
| 5 | WD parameters | GF21 H: T_eff 4476 ± 44 K, log g 7.77, M 0.457 ± 0.016. GF21 He: 4546 K, 7.81, 0.480. O'Brien+2024 corrected: T_eff 4676 K, **M 0.594 M☉, cooling age 7.76 Gyr**. Vincent+2024 (XP): 4629 K, 0.502 M☉, type "DC:" (wrong; it is DZH). O'Brien+2023: DZH, ⟨B⟩ = 0.6 ± 0.2 MG; spectrum not model-fitted because of Zeeman splitting. | `vz_gf21_wd.tsv`, `lit/vizier_specific_rows.txt`, `lit/wd_paper_rows.txt`, `ref/obrien2024_2312.02735.txt` | holds (but see #6) |
| 6 | System age (benchmark) | Bédard+2020 cooling age 5.8 (5.0–6.6) Gyr (H) / 5.6 (5.0–6.1) Gyr (He) at the uncorrected mass, or 7.76 Gyr (O'Brien corrected). Uncorrected mass < 0.556 M☉ → no single-star progenitor in the Cummings+2018 IFMR. Corrected 0.594 ± 0.03 → M_i 0.94–1.69 M☉ → pre-WD lifetime ≈ 2.7–12 Gyr (crude 10 Gyr·M^−2.5 scaling) → total ≈ 10.5–20 Gyr (unphysical upper end shows the IFMR/correction systematics). | `physics_out.json` → `WD_cooling_age_Bedard2020`, `IFMR_total_age`; `ref/Montreal_Table_Mass_*` | **weak**: say "older than ~6–8 Gyr" |
| 7 | T-dwarf mass | T_eff(T6.4) = 906 ± 79 K (K21 SpT–T_eff). Sonora Bobcat: 55 (50–60) M_Jup at 6 Gyr, 60 (55–64) at 8 Gyr, 64 (59–67) at 10 Gyr. If T7 (819 K), a few M_Jup lower. | `physics_out.json` → `T_dwarf_mass_Sonora_Bobcat`; `ref/evolution_tables/` | holds as "≈0.05–0.065 M☉, a brown dwarf" if the age ≥ 6 Gyr |
| 8 | Bound? | M_tot ≈ 0.52 M☉ (0.47 + 0.05): v_esc = 0.73 km/s (5.7 mas/yr), v_circ = 0.52 km/s, P ≈ 99 kyr for a = 1,719 au, E_bind ≈ 2.4×10⁴¹ erg. Measured Δv_tan = 4.9 ± 2.7 km/s (combined fit); the 2σ upper bound is 10.3 km/s. | `physics_out.json` → `binding` | **untested**: consistent with bound; errors 4× v_esc |
| 9 | Chance alignment | Gaia DR3 within 5° (78.5 deg²): 77 stars with ϖ > 20 mas. Excluding the WD, **0** have ϖ 30–59 mas AND PM within 2σ of the T dwarf's → < 1.3×10⁻⁵ expected within 63.8″ (counting 1 as the bound); × 3,293 UCDs searched → < 0.04. Looser cut (ϖ > 25, PM within 3σ): 6 stars → 7.5×10⁻⁵ per UCD, **0.25** over the whole search. | `gaia_5deg_plx20.tsv`, `physics_out.json` → `chance_alignment` | **holds** for the strict case; the loose-case look-elsewhere (0.25) is why it stays a *candidate* |

## Proper-motion analysis

Positions used (offsets in `pm_fit_out.json` → `positions_offsets_arcsec`):

| Data set | Epoch | Source file | Note |
|---|---|---|---|
| AllWISE | 2010.56 (MJD 55400, the AllWISE reference epoch; 48 single exposures span MJD 55296–55484) | `irsa_allwise_p3as_psd.tbl`, `irsa_allwise_mep.tbl` | σ 0.17/0.15″ |
| CatWISE2020 | 2015.40 (RAPMdeg/DEPMdeg) | `vizier_II365_catwise.tsv` | shares WISE images with AllWISE and our pipeline |
| VHS DR5 J (2 clean detections) | 2015.88, 2016.46 | `vz_vhsdr5.tsv` | σ 0.10″ assumed (not in VizieR). A third detection (MJD 57340.10, `Jperrbits` 8388736, pGal 0.99) was dropped. |
| Our pipeline WISE (7 windows × W1, W2) | 2010.3–2024.3 | `dev_summary.json` → `motion.points` | sequence d7960472debb5523 |
| Our SPHEREx D5+D6 (3 survey epochs; 43/59/37 frames; S/N 21–29) | 2025.72, 2026.29, 2026.70 | `spherex_centroids.py` → `spherex_centroids_out.json` | 0.6″ floor. All three lie within 0.55″ of the CatWISE track. |
| 2MASS, Gaia DR3, unTimely | — | `vz_2mass.tsv`, `vz_gaia_ucd.tsv`, `vz_untimely.tsv` | **no rows** (J 17.6 is below the 2MASS limit; no Gaia source; the unTimely VizieR ID J/AJ/165/36 returned nothing, so unTimely was **not checked**) |

PM fits (mas/yr; parallax term fixed at the WD's 37.1 mas; dropping it changes values by ≤ 3 mas/yr). Comparison with the WD (96.03, 36.29):

| Estimate | μα* | μδ | baseline | Δμ vs WD | χ² (2 dof), p | Δv_tan (km/s) |
|---|---|---|---|---|---|---|
| Pipeline `/summary` (WISE only) | 101.9 ± 27.2 | 54.8 ± 27.2 | 14.0 yr | (+6, +18) | 0.51, 0.78 | 2.5 ± 3.5 |
| **Ours WISE + SPHEREx** | 101.4 ± 22.6 | 55.3 ± 22.6 | 16.4 yr | (+5, +19) | 0.76, 0.68 | 2.5 ± 2.9 |
| AllWISE → VHS (no pipeline) | 78.0 ± 32.0 | 17.4 ± 30.0 | 5.9 yr | (−18, −19) | 0.71, 0.70 | 3.3 ± 4.0 |
| VHS → SPHEREx (no WISE) | 121.4 ± 37.9 | 63.3 ± 37.9 | 10.8 yr | (+25, +27) | 0.96, 0.62 | 4.7 ± 4.8 |
| AllWISE + VHS + SPHEREx | 96.9 ± 23.7 | 35.4 ± 22.8 | 16.1 yr | (+1, −1) | 0.00, 1.00 | 0.2 ± 3.0 |
| AllWISE + CatWISE + VHS + SPHEREx | 96.8 ± 23.7 | 34.5 ± 22.8 | 16.1 yr | (+1, −2) | 0.01, 1.00 | 0.2 ± 2.9 |
| CatWISE2020 corrected (II/365) | 121.8 ± 25.8 | 70.6 ± 23.1 | — | (+26, +34) | 3.20, 0.20 | 5.5 ± 3.1 |
| CatWISE2020 uncorrected (IRSA; = K21 table A1) | 141.8 ± 25.8 | 72.8 ± 23.1 | — | (+46, +36) | 5.65, 0.06 | 7.5 ± 3.2 |
| **Combined: ours WISE + VHS + SPHEREx** | **123.3 ± 20.9** | **63.7 ± 20.9** | 16.4 yr | (+27, +27) | 3.42, 0.18 | **4.9 ± 2.7** |

Reading:
- Every estimate puts the T dwarf's motion within ~2σ of the WD's, in the same direction: position angle 63° (combined) vs 69° (WD). The total PM is 139 ± 21 mas/yr, so the motion itself is detected at 6.6σ.
- The estimates scatter by about ±20 mas/yr, as their errors predict.
  - The "combined" fit is pulled up by the VHS points, which sit about 0.1″ off our WISE track. This is a frame zero-point issue: VHS is tied to 2MASS, while WISE and SPHEREx come from our reprojection.
  - So the combined error is optimistic by roughly the 10 mas/yr control offset.
- The WD control (#1b) measures the WD itself with the same images: our pipeline is good to about 10 ± 15 mas/yr here.
- Bottom line: the PM agreement is real at the ~25 mas/yr level (≈ 3 km/s). It excludes a typical unrelated field star (tens of km/s), but it cannot measure orbital motion.

## SPHEREx spectrum

`dev_spectrum.json` comes from pipeline v5 with neighbour-subtracted PSF photometry. Pipeline verdict: "match", best T8 (p = 0.50, tied with the subdwarf template d_sdT8), `type_range` T7–Y0, χ²ᵣ = 3.48 over 76 bins, `detection_snr` 19.5, 0 negative bins.

The pipeline's plain-language summary says "fits a T8 brown-dwarf template best … between T7 and Y0". **That sentence should not be repeated publicly for this object.** Reasons:
- **Detection is mid-IR only.** S/N > 3 in 1/13 bins at 1.0–1.6 µm, 1/15 at 1.6–2.4, 5/14 at 2.4–3.8 and 17/34 at 3.8–5.0 µm.
- **There is neighbour light.** CatWISE J235451.78−814043.9 is 8.2″ E, with W1 17.95 and W2 17.73 (`vizier_II365_catwise.tsv`). In W1 it is about as bright as the target, inside one SPHEREx pixel (6.2″). The pipeline's `neighbour_frac` is 1.26 (D3) and 1.38 (D4): the subtracted neighbour flux exceeds the target's own at 1.6–3.8 µm.
- **The type flips with the fitting choice** (`spectral_refit_stdout.txt`):
  - all bins → T8;
  - only S/N > 3 → T5 (χ²ᵣ 0.74);
  - 2.5–5 µm → T5 or T7, depending on the template-spread term;
  - without 1.6–3.8 µm → L7γ.
  - The 1–2.5 µm part cannot separate anything from Y1 to sdT4.
- **T8 conflicts with the distance:** M_W2 for T8 puts the dwarf at 15–20 pc, against the WD's 26.95 pc.

What can be said: the 3–5 µm SPHEREx shape (a methane trough near 3.3 µm, flux peaking at 4–5 µm) is that of a T dwarf. This confirms the photometric T classification but does not refine it.

## Age and the DZH white dwarf

- **What DZH means.** Metal lines (Ca II H&K) split by a 0.6 ± 0.2 MG magnetic field (O'Brien+2023, `lit/wd_paper_rows.txt`).
  - The metals mean the WD is accreting rocky planetary debris now. So the system probably kept a planetary system through the giant phase, despite having a ~1,700 au brown-dwarf companion. This is an interesting combination, but our data do not test it.
  - The magnetic field matters for the age: O'Brien+2023 did not fit the spectrum, so T_eff/log g come only from Gaia photometry.
  - The low uncorrected mass (0.46 M☉) is a known bias for cool WDs, and O'Brien+2024 apply an ad-hoc correction to 0.594 M☉. Magnetism in old, cool WDs is common; it can also come from binary mergers. If this WD were a merger product, its cooling age would not date the system.
  - TESS shows no periodic variation (Hernandez+2024 Table 5: "×", 1 sector), so there is no rotation period.
  - Hernandez+2024 list it among "single" magnetic WDs: no known close companion. A 1,700 au T dwarf would not have been considered.
  - Madurga Favieres+2024 find no WISE infrared excess (`lit/vizier_hits_wd.txt`). So there is no sign of an unresolved close brown dwarf or a dusty debris disc. The T dwarf at 64″ is far outside WISE's 6″ beam.
  - O'Brien+2024 define their `Agec` column as the "cooling age after low-mass correction", in Gyr (`ref/obrien2024_2312.02735.txt`).
- **Age.**
  - The cooling age is 5.0–7.8 Gyr across fits and models. That is a firm lower limit on the system age (assuming no merger).
  - With the corrected mass and the Cummings+2018 IFMR, the total age is ≈ 10–13 Gyr (`IFMR_total_age`; crude progenitor lifetimes).
  - Honest statement: **"an old system, ≳ 6 Gyr (likely ≳ 8 Gyr)"**.
  - The T dwarf would then be a 0.05–0.065 M☉ brown dwarf (Sonora Bobcat). As a benchmark, the age is the useful part. The mass precision is limited by the photometric type (±1 subtype ≈ ±80 K).

## Literature status (novelty)

**No source we could reach pairs the two objects.** Full details are in `lit/LIT.md` (WDTLit sub-task).

| Source | Result | File |
|---|---|---|
| SIMBAD (Harvard TAP) | T dwarf: otype BD?, 2 refs (Tinney+2018, Kirkpatrick+2021). WD: 9 refs, all WD catalogues. No `h_link` parent/child for either object. The 120″ cone holds only the two objects + 1 unrelated star. | `lit/simbad.txt`, `lit/simbad_bib.txt` |
| VizieR all-catalogue 60″ cones, both objects (prefix-split) | No companion/binary column for either. Within 5″ of the WD: Madurga Favieres+2024 WISE excess = **"No Excess"**; Wang+2025 TESS flares Bin = "single"; Kervella+2022: 0 companions. | `lit/vizier_hits_*.txt` |
| Tinney+2018 | T6.4 ± 0.5 (CH4); μ′ (+30, −15) ± 230 mas/yr; "typing spectroscopy required". No mention of the WD. | `lit/tdwarf_paper_rows.txt` |
| Kirkpatrick+2021 | Table 1 (new candidates; discoverers G, J, K, N; dropped from Spitzer follow-up) and Table A1 (SpAd T7, no spectrum, CatWISE uncorrected PM). **Not in the 20-pc census table** (the brief was wrong on this). No companion column. | `lit/vz_kirk2021*.tsv` |
| O'Brien+2023 / +2024 | DZH, 0.6 MG; WD **absent from the O'Brien+2024 wide-binary table A6** (132 rows, 6 WD+BD, all other systems). Text: 0 matches. | `lit/obrien2024_tablea6_full.tsv`, `lit/wd_paper_rows.txt` |
| Hernandez+2024 | Table 5: no TESS period. Calls its sample "single" magnetic WDs. No companion. | `lit/wd_paper_rows.txt` |
| El-Badry+2021, SUPERWIDE, WDS, GCNS | 0 rows / no binary entry (expected for El-Badry: the T dwarf is not in Gaia). Positive controls OK. | `lit/vz_*.tsv`, `lit/vizier_positive_controls.txt` |
| Rothermich+2024 (Backyard Worlds co-movers) | 0 matches in all local tables + text | `lit/rothermich_grep.txt` |
| **Zhang+2025, Benchmark brown dwarfs I (arXiv:2505.24560)** | Searched CatWISE T dwarfs × GCNS for exactly such pairs. The pair passes cuts 1–7, 9 and 10 (W1−W2 2.21, S/N 23/48, PM > 100, PM errors < 50, b = −35°, nb = 1, ab_flags 00, d 27 pc, 64″). For the |Δμ| < 40 cut (eq. 8): **fails with the IRSA CatWISE2020 PM** (Δμα 45.8), passes with the VizieR II/365 PM (Δμα 25.8). They name only the 8 pairs they kept; this is not one of them. Their 7 rejections are unnamed: if it got that far, the likely reason is no DECam coverage at δ = −81.7° [INFERENCE]. No paper II found. | `lit/zhang2025_criteria_check.txt`, `zhang2025_bb1.txt` |
| arXiv full-text grep (≈129 papers: WD+BD/UCD wide binaries, COCONUTS, Backyard Worlds, benchmark BDs, 40-pc WDs, magnetic DZ) | Hits only in the papers that list each object separately. **No paper mentions both.** | `lit/arxiv_grep*.txt` |
| Web search (10 queries) | Catalogue pages only (stellarcatalog calls the WD "a single star") | `lit/web_search_log.txt` |

Not searched: NASA ADS full text (no token), Google Scholar, AAS abstracts, the Backyard Worlds forum, and machine-readable tables of 2604.01323 / 2312.03639. Also unknown: whether ESO programme 114.2713.002 or Gemini GS-2021A-Q-320 (both observed the WD) are unpublished follow-up.

**Status: not previously reported as a pair (as far as we could check).** Caveat: Zhang+2025 ran a search designed for exactly such pairs. With the CatWISE PM they used, this pair falls 6 mas/yr outside their cut, and their rejected candidates are unnamed. So "first" means first *reported*, not first *seen*.

Our added value over the literature:
1. An independent 16-year proper motion (WISE + VISTA + SPHEREx), validated on the WD itself, that agrees with the WD's Gaia motion.
2. A photometric-distance match (25.7–26.5 pc vs 26.95 pc).
3. A chance-alignment estimate.
4. A SPHEREx 1–5 µm spectrum that confirms a T dwarf.
5. An age context from the WD (≳ 6 Gyr cooling) that would make the brown dwarf a ~55–65 M_Jup benchmark.

## Suggested public wording

**Headline:**
> A brown dwarf that may orbit an old white dwarf: a new candidate pair found with this app

**Body:**
> WISE J2354−8140 is a cold methane brown dwarf (type ≈T6–T7, estimated from imaging and colours). It was catalogued by Tinney et al. (2018) and, through Backyard Worlds volunteers, by Kirkpatrick et al. (2021). Our catalogue search noticed that it sits 64″ (≈1,700 au) from a nearby white dwarf, WD J2354−8141, which is 27 pc away and has a magnetic, metal-polluted atmosphere. With this app we tracked the brown dwarf across 16 years of WISE, VISTA and SPHEREx images. It moves across the sky like the white dwarf, to within our ~25 mas/yr precision (about 3 km/s), and its brightness puts it at the same distance (≈26 pc). We found no earlier paper that pairs the two. If they are bound, the white dwarf's cooling age makes the system older than ~6 billion years, which would make the brown dwarf a ~55–65 Jupiter-mass benchmark of known age.

**Caveat line:**
> Candidate, not confirmed: our proper motions are ~10× too coarse to show the pair is bound, and the brown dwarf has no measured parallax. Its SPHEREx spectrum confirms a T dwarf but is too faint and blended to give a precise type. "Not reported before" means not found in SIMBAD, VizieR, the arXiv papers listed, or a web search (Nov 2026; ADS full text not searched). Zhang et al. (2025) ran a search designed for such pairs, but with the CatWISE motion they used, this one falls just outside their cut.

**Do not say:**
- "discovered a binary" / "bound companion" / "confirmed" → say "candidate co-moving pair".
- "first spectral type" / "SPHEREx shows it is T8" → say "SPHEREx confirms a T dwarf".
- "brown dwarf discovered" → the T dwarf itself is known (Tinney+2018; K21). The new thing is the possible pairing.
- A precise age ("12 Gyr") → say "older than ~6 billion years".

## What we add vs prior work

| Item | Before us | Ours |
|---|---|---|
| T dwarf | Tinney+2018 (CH4 imaging T6.4); K21 (BYW discovery credit G, J, K, N; adopted T7; Spitzer ch1/ch2; CatWISE uncorrected PM) | Independent 16.4-yr PM (WISE + VHS + SPHEREx), pipeline validated on the WD itself. SPHEREx 1–5 µm spectrum (T-like, type not refined). |
| WD | GF21, O'Brien+2023 (DZH, 0.6 MG), O'Brien+2024 (corrected mass/age), Hernandez+2024 (single magnetic, no TESS period), Vincent+2024 | — |
| Pairing | none found (LIT) | First proposal of the pair, with distance + PM consistency, a chance-alignment estimate and an age context |

## Files

| File | What |
|---|---|
| `queries.sh` | Every catalogue / API / reference download |
| `dev_post.json`, `dev_sequence.json`, `dev_summary.json`, `dev_spectrum.json`, `dev_export.csv` | Dev API (working tree, :8006, CACHE_DIR /data/devcache/wdt), sequence d7960472debb5523, 541 frames (42 WISE visits, 499 SPHEREx) |
| `spherex_centroids.py` → `spherex_centroids_out.json` | SPHEREx per-epoch centroids (D5+D6, D6, all bands) |
| `pm_fit.py` → `pm_fit_out.json`, `pm_fit_stdout.txt` | All PM fits, comparison with the WD, separation |
| `wd_control.py` → `wd_control_out.json` | Pipeline astrometry control on the WD itself |
| `spectral_refit.py` → `spectral_refit_out.json`, `spectral_refit_stdout.txt` | SPHEREx template refits (variants) |
| `physics.py` → `physics_out.json`, `physics_stdout.txt` | Distances (K21, UltracoolSheet), T_eff, WD cooling ages, IFMR, Sonora masses, binding, chance alignment |
| `irsa_*.tbl`, `vizier_II365_catwise.tsv`, `vz_*.tsv`, `gaia_5deg_plx20.tsv` | Catalogue query outputs |
| `zhang2025_bb1.html/.txt` | Zhang+2025 (arXiv:2505.24560) |
| `ref/` | Montreal cooling tables (Bédard+2020), Sonora Bobcat evolution tables (Zenodo 5063476), K21 PDF + text, O'Brien+2024 HTML + text |
| `lit/` | Literature search (SIMBAD, VizieR all-catalogue cones, arXiv greps, web search); see `lit/LIT.md` |
| `vztsv.py` | TSV reader |

Re-run: `cd research/wdt && CACHE_DIR=/data/devcache/wdt nice -n 15 ../../.venv/bin/python spherex_centroids.py && nice -n 15 ../../.venv/bin/python pm_fit.py && nice -n 15 ../../.venv/bin/python spectral_refit.py && nice -n 15 ../../.venv/bin/python physics.py && CACHE_DIR=/data/devcache/wdt nice -n 15 ../../.venv/bin/python wd_control.py`.

## Not checked

- **A parallax for the T dwarf.** None is published. The CatWISE plx1/plx2 (101 ± 69, 70 ± 69 mas) are uninformative. This is the decisive missing measurement, together with a better PM.
- **unTimely** (VizieR ID returned nothing) and **VHS DR6** (not on VizieR). Tinney+2018's CH4 imaging positions and epochs: their table is not on VizieR (`lit/vizier_specific_rows.txt`) and the paper's table was not read for positions.
- **The VHS astrometric error** (0.10″ assumed) and the frame tie between VHS (2MASS) and our WISE/SPHEREx reprojection: there is a ~0.1″ zero-point, see the "combined" fit.
- **The 0.6″ SPHEREx floor.** It is set by the pipeline, not measured. The WD control is consistent with it.
- **PSF-fit neighbour removal quality** at 1.6–3.8 µm (neighbour J235451.78−814043.9).
- **A proper IFMR + MIST lifetime calculation.** The pre-WD lifetime uses a 10 Gyr·M^−2.5 scaling. There is no DZ-specific (He + metals) atmosphere fit of the WD; the photometric masses assume pure H or pure He.
- ATMO 2020 (only Sonora Bobcat used) and metallicity effects on the T-dwarf mass.
- **Chance alignment:** a 5° Gaia field only (sources with ϖ > 20 mas). It ignores Gaia incompleteness for faint, cool WDs/brown dwarfs and treats the look-elsewhere factor as uniform over 3,293 UCDs.
- **NASA ADS full text** (no token) and anything listed under "Not checked" in `lit/LIT.md`.
