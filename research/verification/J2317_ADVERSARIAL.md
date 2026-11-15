# Adversarial review: WISE J231728.42−665959.3 ("J2317−6659 / J2317−6700")

Date: 2026-11-15. Scope: try to break the "Featured result" (frontend/src/components/Landing.tsx:67-79, README.md:18, research/README.md:13, research/discovery/REPORT.md §Conclusion and the J2317-6700 table row).
No repo code was edited. Everything below is in `research/verification/`.

## Overall verdict

**The science core holds. The headline wording does not, and must be softened before the presentation.**

What holds:
- It is a real, fast-moving source. Five independent PM estimates give 0.48–0.52″/yr.
- Its SPHEREx spectrum matches mid-T templates.
- It is not bound to HD 219509/219495. Every PM estimate differs from theirs by 140–180 mas/yr, about 20 km/s.

What breaks:
1. **"Typed for the first time" / "first spectral type".** Rothermich et al. 2024 already gave it a type, (T6). That type is photometric, not "nothing". Ours is the first *spectrum-based* classification we could find, and it confirms their T6 rather than overturning it.
2. **"With a type guessed from its colors" is wrong.** Rothermich derived (T6) from its W2 brightness at the host pair's parallax, not from colours (their §V.1.2). I reproduce their number exactly: T6.1.
3. **"About 28 pc (90 light-years)" is biased low.** It rests on one calibrator, 2MASS J1122+2550. That object is about 0.3 mag fainter than the T6 average, and the report quotes it with the wrong parallax. Published relations give **≈31 pc, 26–40 pc for T5–T6** (85–130 ly).
4. **"Sits at the same distance" is too strong.** The right word is "consistent with".
5. **The "not their companion" result is a confirmation, not new.** Rothermich already scored the pair at **5.1 %** co-moving probability and called it a likely chance alignment.
6. **"T5–T6" is narrower than the data allow.** The T5-vs-T6 order flips with one fitting choice (template-spread weighting), and the near-IR alone prefers T7–T6. Honest statement: **≈T6 ± 1 (mid-T)**.

## Claim-by-claim

| # | Claim (ours) | Independent value(s) | Verdict | Why |
|---|---|---|---|---|
| 1a | "typed for the first time", "first spectral type" | Rothermich+2024 Table 3: `CWISE J231728.89-670001.1 (T6)`, a parenthesised estimate (`rothermich_J2317_row.txt`). No spectroscopic type found in SIMBAD, VizieR, UltracoolSheet v2.1.0, the SPIFF table, the four 2026 SPHEREx UCD papers, or the web. | **weakened** | A type existed. Ours is the first *spectrum-based* one we could find. ADS full text and Semantic Scholar full text were unreachable. |
| 1b | "only listed as a possible brown dwarf" | SIMBAD otype `BD?` (from 2024AJ....167..253R); only 1 bibcode; no mesSpT row (`simbad_object.txt`) | **holds** | |
| 1c | "with a type guessed from its colors" | Rothermich §V.1.2: secondaries without spectra are typed "by adopting the host star's parallax and using the spectral type versus M_W2 relation" of Kirkpatrick+2021. Reproduced: M_W2 = 13.02 at ϖ = 35.14 mas → **T6.1** (`recompute_out.json` → `Rothermich_style_phot_type`) | **wrong** | The type came from brightness at an assumed distance, not colour. Colour alone would also give T6.0 (K21 W1−W2 relation), but that is not what the paper did. |
| 2a | PM (+419 ± 30, −236 ± 30) mas/yr, "0.48″/yr" | CatWISE2020 corrected (VizieR II/365): (436.6 ± 31.0, −288.2 ± 29.2) = 0.52″/yr. CatWISE2020 uncorrected (IRSA): (462.1 ± 31.0, −298.8 ± 29.2) = 0.55″/yr. **AllWISE→VHS two-epoch, fully independent of our pipeline: (423, −266) ± 44 = 0.50″/yr.** Our all-points fit including SPHEREx: 480.5 ± 19. Production: (430.8, −251.6) ± 23 = 0.50″/yr. | **holds** (say "≈0.5″/yr") | Every estimate agrees within ≤ 1.3σ per axis (`pm_differences`). |
| 2b | production "22σ" | 0.499 / 0.0229 = 21.8σ, statistical only (6 epochs). With the report's 20 mas/yr systematic floor: ≈ 16σ. CatWISE alone: 17σ. AllWISE→VHS alone: 11σ. | **holds** | Quote it as "statistical". |
| 2c | CatWISE quoted as (462, −299) and as (437, −288) | Both are CatWISE2020. IRSA `catwise_2020` PMRA is documented as "(note uncorrected systematic in CatWISE2020)". VizieR II/365 note (1): PMRA/PMDE "include the correction of … offsetpmra and offsetpmdec … table CatWISE2020Table120201012.tbl". Rothermich quotes the corrected one. | **explained; inconsistent use** | REPORT's table row uses the uncorrected value. Its text uses the corrected value but the "Δ ≈ 1.3σ" was computed against the uncorrected one (production `catalog_offset_sigma`). Use (437 ± 31, −288 ± 29) with its source. The app's `/api/resolve` also returns the uncorrected IRSA PM (`prod_resolve.json`); effect ≤ 0.3″ over 10 yr, harmless. |
| 3a | W1−W2 2.08 ± 0.12 (research), 2.19 ± 0.11 (production) | CatWISE 1.825 ± 0.054; unWISE (II/363) 1.794 ± 0.056; AllWISE 2.00 ± 0.13 | **weakened** | Ours is 0.25–0.36 mag redder than CatWISE/unWISE (2–3σ). Our W1 = 17.57 vs CatWISE 17.12 (0.45 mag fainter); our W2 is 0.19 mag fainter. Probably a systematic in our faint-source aperture photometry. **Not explained.** Quote the catalogue colour of 1.8. The production text "extremely red (Y/late-T dwarf-like)" overstates a 1.8 colour, which is mid-T. |
| 3b | VHS J−Ks = −0.25 | VHS DR5 (II/367) VHS J231728.84-670001.0 at 0.29″: J−Ks(pnt) = −0.251 ± 0.122; Jpmag 16.981 ± 0.035, Kspmag 17.120 ± 0.229 (Ks only ≈ 4.7σ) | **holds** | UltracoolSheet field singles (MKO J−K median [16–84 %]): T5 −0.26 [−0.47, −0.02], T6 −0.39, T7 −0.28 |
| 3c | colours "fit a mid-T" | K21 SpT(W1−W2): T6.0 (CatWISE), T6.6–6.9 (ours). UCS W1−W2: T5 1.68 [1.48, 1.85], T6 2.01 [1.69, 2.30]. J−W2 = 1.69 ± 0.05 (VHS J − CatWISE W2): UCS T4 1.81, T5 1.91 [1.66, 2.27], T6 2.10 [1.92, 2.42]; K21 J−ch2 1.73 vs predicted 1.89 (T5) / 2.07 (T6), RMS 0.44 | **holds**, T5–T6 | J−W2 leans earlier (T4–T5). W1−W2 leans later (T6–T7). |
| 4 | SPHEREx type T6 (χ²ᵣ 1.69) research vs T5 (1.56) production, adopted "T5–T6" / "T5.5 ± 1" | 89 channels; only 35 at S/N > 3 and 17 at S/N > 5; max 10.4, median 2.1; 23 channels negative. The two binned spectra are nearly identical. The ordering is set by the template-spread term: T5's template spread is large. Without it, T6 1.64 vs T5 2.24; with it, T5 1.56 vs T6 1.64. Near-IR alone (1–2.5 µm): T7 0 < T6 +4.4 < T8 +8.5 < T5 +12.9 Δχ². 2.5–5 µm alone: T5 (with spread) or T6 (without). Errors × 1.5 (χ²ᵣ ≈ 1.6 shows they are underestimated): T6 0, T5 +6.8, T7 +17. Production 1.4 µm water depth −0.10 ± 0.06 vs 0.13 for the T5 template: deeper, i.e. later type. T4 and T3 are excluded in every variant (Δχ² ≥ 22). | **weakened** → "≈T6 ± 1" | T5/T6/T7 are not cleanly separable: the method choice moves the answer by one subtype. Binary: two-template blends never improve on the single T6 (Δχ² = 0), so there is no evidence of a spectral binary, but a similar-type pair is undetectable. Metallicity/gravity: the library has only sdT4, d_sdT1, d_sdT8 (d_sdT8 gives χ² identical to T8) and no young or sub-dwarf mid-T templates, so this is **untestable**. |
| 5 | distance 27–30 pc, "about 28 pc (90 ly)" | **K21 Table 13** (SpT→Mch2; W2→ch2; RMS 0.31 mag): T5 34.4 (29.8–39.7), T5.5 32.6 (28.3–37.6), T6 30.6 (26.5–35.3), T7 26.1, T4 37.6 pc. **UltracoolSheet empirical** (field singles with ϖ/σ > 10; median M_W2 ± MAD): T5 12.70 ± 0.33 → 33.1 (28.4–38.6) pc; T6 12.88 ± 0.37 → 30.4 (25.7–36.0) pc. The calibrator J1122+2550 has ϖ = 66.3 ± 2.3 mas in UCS (Kirk19), not 62.9, so M_W2 = 13.21: 0.33 mag fainter than the T6 median. | **weakened** | Our single calibrator biases the distance low by about 10–15 %. Honest value: **≈31 pc, 26–40 pc (85–130 ly)** for T5–T6. If it is an unresolved equal-mass binary, multiply by 1.41. |
| 5b | host ϖ 35.14, PM (364, −410) | SIMBAD (Gaia DR3): HD 219509 ϖ 35.141 ± 0.022, PM (363.82, −410.03), RV +66.0; HD 219495 ϖ 35.152 ± 0.012, PM (354.93, −407.12), RV +67.1 (`simbad_object.txt`) | **holds** | |
| 5c | "sits at the same distance" | 28.46 pc lies inside 26–40 pc. Rothermich's (T6) was *derived* by assuming that distance. | **weakened** → "consistent with" | |
| 6 | "moves differently, so most likely not their companion" (Δμδ ≈ 170 mas/yr, 5–6σ) | Δμ vs HD 219509 for each PM estimate: ours (55, 174) → χ² = 37 (2 dof); production (67, 159) → χ² = 57; CatWISE corrected (73, 122) → χ² = 23 (p = 1e-5); AllWISE→VHS (59, 144) → χ² = 12.3 (p = 0.002). Δv_tan = 19–25 km/s at 28.5 pc. Circular orbital speed at the ≥ 6,700 au projected separation for 1.5 M☉ is 0.45 km/s, about 3 mas/yr. | **holds, but not new** | Our PM systematics (≲ 40 mas/yr) cannot close a 140–180 mas/yr gap. Rothermich Table 3 ("Low Probability Co-moving Systems") already gives a 5.1 % CoMover probability and calls such pairs "a high likelihood of being chance alignments". "Once suggested as its host" is fair only if it adds that the suggestion was already rated unlikely. |
| 6b | separation 227″ / 6,500 au (Rothermich) | 234.7″ from HD 219495 and 295.4″ from HD 219509 (CatWISE ep. 2015.4 vs SIMBAD J2000 positions, so a few-arcsec epoch mismatch) | holds | |
| 7a | AllWISE counterpart in the Assef+2018 R90 and C75 AGN-candidate catalogues | VizieR J/ApJS/234/23 r90cat and c75cat both contain WISEA J231728.49-665959.7 (W1 17.222, W2 15.222) (`vizier_hits_rows.txt`) | **holds** | Say "listed as an AGN *candidate*". |
| 7b | "16 years of WISE and SPHEREx images" | Data used: WISE 2010.33–2024.33 (44 visit frames), SPHEREx 2025.31–2026.75 (453 frames), so 16.4 yr (`prod_export.csv`). The 0.48″/yr figure is the 16.4-yr fit including SPHEREx positions (`fit_all`). The production PM uses WISE only (14.0 yr). | **holds** | |
| 7c | "90 light-years" | 28 pc = 91 ly, but see #5: ≈ 100 ly (85–130) | **weakened** | |
| 7d | "Gaia DR3 has nothing within 4″" | Nearest Gaia DR3 source is 6388326556409907584 at ≈ 19″ (G = 20.2, a neighbour star) | holds | That neighbour (VHS J ≈ 17.75, ≈ 0.5× the target's J flux) is 19–24″ away during the SPHEREx epochs (≈ 3–4 SPHEREx pixels). Minor possible PSF-wing contamination at 1–2 µm; not checked. |

## Prior-work search (item 1): every source checked

| Source | Query | Result |
|---|---|---|
| SIMBAD (CDS Strasbourg was down, returning an HTML "Page unavailable"; used the Harvard mirror TAP `https://simbad.harvard.edu/simbad/sim-tap/sync`) | `basic` cone 288″; `ident`, `has_ref⋈ref`, `otypes`, `mesSpT`, `mesPM`, `flux` for oid 27207645 | 3 identifiers: WISE J231728.42-665959.3, WISEA J231728.49-665959.7, CWISE J231728.89-670001.1. **One bibcode: 2024AJ....167..253R.** No measured SpT, PM or photometry. |
| VizieR all-catalogue, 20″ (Harvard mirror `asu-tsv?-c=349.37038 -67.00031&-c.rs=20`; 244 catalogues examined) | `vizier_all_20as_harvard.tsv`, `vizier_hits_rows.txt` | Target hits: AllWISE, Assef+2018 R90/C75. Other hits are the 19″ neighbour star (USNO-B, NOMAD, GSC2.3, PPMXL, Gaia DR2/DR3/distances, TIC, KS4). **No SpT column for the target.** |
| VizieR specific catalogues, 30″ | II/365 CatWISE, II/367 & II/359 VHS, II/363 unWISE, II/379 SkyMapper, II/371 DES, II/246 2MASS, II/335, II/358, V/154, II/376, J/AJ/167/253, J/ApJS/253/7, J/ApJS/271/55 | Photometry and astrometry only (CatWISE, VHS, unWISE). **Not in Kirkpatrick+2021 or Kirkpatrick+2024.** Rothermich's VizieR table holds only Table 1 (high probability). DES and 2MASS: no counterpart. |
| UltracoolSheet v2.1.0 (Zenodo 15802304, 2025-07-03) | positional match | **Absent** (nearest UCS object 9220″ away) |
| SPIFF autotype table (`backend/app/data/ucd_catalog.csv`, 16,917 rows) | positional match | **Absent** (nearest 6822″) |
| Rothermich+2024 (arXiv:2403.04592 HTML, `rothermich_text.txt`) | full-text grep | Table 3 row only: (T6) estimated, PM (436.56 ± 31.00, −288.17 ± 29.20) "ref 3 = Marocco+2021", 227″, 6,500 au, probability 5.1 %. **No spectrum** (Table 4 does not list it). |
| SPHEREx UCD papers 2025–2026 (arxiv.org/search for "SPHEREx brown dwarf", "SPHEREx T dwarf", "SPHEREx ultracool dwarf", "SPHEREx spectral type"; `arxiv_search.txt`) | HTML full-text grep for 2317 / 231728 / 349.37 / GJ 4321 / HD 219509 | 2604.22012 SPIFF: no mention. 2604.26771 SUDA: sample drawn from UltracoolSheet, so excluded. 2607.00543 (spectral sequence of standards): no mention. 2608.08908 (low-gravity sample from UltracoolSheet): no mention. 2512.12098 and 2508.09370: not opened (ML spectral-binary / typing papers on existing spectra; low risk). |
| Web search | `"CWISE J231728.89-670001.1"`, `"J231728.89-670001.1" OR "J231728.42-665959.3" OR "J231728.49-665959.7"`, `"J2317-6700" brown dwarf` | No relevant hits |
| NASA ADS | API without token | **HTTP 401: not checked** (no token in env) |
| Semantic Scholar full-text snippet API | 3 designations | **HTTP 429 (rate limit) on every try: not checked** |
| JWST/Gemini/Magellan programmes, ATels, RNAAS | — | **Not checked** individually (beyond web search) |

## Recommended slide wording

**Headline:**
> WISE J2317−6659: the first spectrum-based type for a citizen-science brown-dwarf candidate, from SPHEREx

**Body (one paragraph):**
> Backyard Worlds volunteers flagged this faint infrared source as a possible T6 brown dwarf. That type was estimated from its brightness, not measured (Rothermich et al. 2024). With this app we extracted its SPHEREx 0.75–5 µm spectrum: it matches mid-T brown-dwarf templates (≈T6 ± 1), confirming the estimate. It moves ≈0.5″ per year across 16 years of WISE and SPHEREx images. Its estimated distance (~30 pc, 25–40 pc; ~100 light-years) is consistent with the nearby star pair HD 219509/219495. But it moves ~150 mas/yr (≈20 km/s) differently, so it is not their companion, as Rothermich et al. had already judged likely.

**Caveat line:**
> SPHEREx gives low-resolution spectrophotometry (R≈40–130), not a slit spectrum; the distance is photometric. "First" means the first we found in SIMBAD, VizieR, the UltracoolSheet, SPIFF and arXiv as of Nov 2026 (ADS full text not searched).

**Remove or soften:**
- "typed for the first time" / "first spectral type" → "first spectrum-based type".
- "with a type guessed from its colors" → "a type estimated from its brightness". The colours claim is factually wrong.
- "about 28 parsecs (90 light-years)" → "~30 pc (25–40 pc)".
- "sits at the same distance" → "is consistent with the distance of".
- "once suggested as its host … most likely not their companion" → credit Rothermich's 5 % score; our PM confirms it.
- "T5–T6" → "≈T6 ± 1 (mid-T)", or keep "T5–T6" only with "±1 subtype".
- W1−W2 2.08/2.19 → quote CatWISE 1.83 ± 0.05. Drop "extremely red / Y-like" anywhere it is shown for this object.
- CatWISE PM: one value, (437 ± 31, −288 ± 29) mas/yr, labelled "CatWISE2020, offset-corrected (VizieR II/365)".
- J1122+2550 parallax: 66.3 ± 2.3 mas (Kirkpatrick+2019, via UltracoolSheet), not 62.9. Better, drop the single-calibrator distance entirely.

## Files and commands

All scripts run under `nice -n 15` with `/home/paw/Desktop/ultracool/.venv/bin/python`.

| File | What |
|---|---|
| `recompute.py` → `recompute_out.json`, `recompute_stdout.txt` | Colours (CatWISE/AllWISE/unWISE/ours/VHS), UltracoolSheet presence + empirical M_W2 and colours per subtype, K21 Table 13 distances/colours/SpT(W1−W2), Rothermich-style photometric type, AllWISE→VHS PM, all PM comparisons, companion Δμ/χ²/Δv, separations, S/N of the binned spectrum, Δχ² tables |
| `spectral_refit.py` → `spectral_refit_out.json`, `spectral_refit_stdout.txt` | All 47 SPIFF templates, with and without template spread; near-IR-only and 2.5–5 µm-only fits; errors ×1.5; two-template T-dwarf blends; for both the production v5 and research-snapshot binned spectra (imports `backend/app/spectral.py` read-only for the templates) |
| `simbad_object.txt`, `simbad_cone288.txt` | SIMBAD TAP results (Harvard mirror) |
| `vizier_all_20as_harvard.tsv`, `vizier_hits_rows.txt`, `vizier_specific.txt`, `vhs_dr5_target.tsv`, `catwise_vizier_target.tsv`, `rothermich_vizier.txt` | VizieR results |
| `catwise.tbl`, `allwise.tbl`, `catwise2020_readme.txt` | IRSA Gator `catwise_2020` and `allwise_p3as_psd` cones |
| `rothermich_text.txt`, `rothermich_J2317_row.txt` | arXiv:2403.04592 HTML as text, and the J2317 + GJ 4321/4322 rows of Table 3 |
| `prod_resolve.json`, `prod_summary_now.json`, `prod_spectrum_now.json`, `prod_export.csv` | Production API (cached sequence 685314abd15e38d9, pipeline v5); read-only GETs plus the cached POST |
| `arxiv_search.txt`, `s2_snippet_search.txt` | Literature-search logs |
| `data/UltracoolSheet_-_Main.csv` | UltracoolSheet v2.1.0 (Zenodo 15802304) |

Key URLs:
- https://arxiv.org/html/2403.04592 (Rothermich+2024, Table 3 and §V.1.2)
- https://arxiv.org/pdf/2011.11616 (Kirkpatrick+2021, Table 13, pp. 61–63)
- https://irsa.ipac.caltech.edu/data/WISE/CatWISE/gator_docs/catwise_colDescriptions.html (PMRA "uncorrected systematic")
- VizieR II/365 note (1) (offset-corrected PMs)
- https://zenodo.org/records/15802304 (UltracoolSheet)
- arXiv 2604.22012, 2604.26771, 2607.00543, 2608.08908

## Not checked

- NASA ADS full text (no token; HTTP 401), Semantic Scholar full text (HTTP 429), Google Scholar.
- Individual JWST/Gemini/Magellan/ESO programme lists, ATels, RNAAS. CDS Strasbourg was down, so only Harvard mirrors were used.
- Dupuy & Liu 2012 relations (K21 and the UltracoolSheet empirical calibration were used instead).
- The VHS per-source astrometric error: 0.1″ was assumed for the AllWISE→VHS PM.
- The root cause of our 0.45 mag fainter W1.
- SPHEREx PSF-wing contamination from the 19″ neighbour.
- Whether J2317 lies in any SPHEREx-team internal catalogue that is not public.
