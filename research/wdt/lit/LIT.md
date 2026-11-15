# Literature / novelty check: Gaia DR3 6350786278796634112 (DZH white dwarf) + WISE J235447.80−814044.9 (T dwarf)

Run 2026-11-15 by the WDTLit agent. CDS Strasbourg was not used: SIMBAD came from the Harvard TAP mirror and VizieR from `vizier.cfa.harvard.edu`. Every claim below names the saved file it rests on. Scripts are in this directory: `simbad.sh`, `simbad_bib.sh`, `vizier_parts.sh`, `vizier_parts_retry.sh`, `vizier_hits.py`, `vizier_specific.sh`, `vz_summary.py`, `arxiv_grep.py`, and `vztsv.py` (copied from `../../verification/J2358/`).

## Verdict: does any source pair these two objects?

**No.** None of the sources checked links the WD and the T dwarf, or names either one as a companion of the other or of anything else.

- **SIMBAD:** no `h_link` parent or child for either object. The 120″ cone holds only the two objects and one unrelated UCAC4 star (`simbad.txt`).
- **Catalogues of wide pairs and companions:**
  - The WD is absent from the O'Brien+2024 40-pc wide-binary table. That table has 132 rows, and its 6 WD+BD rows are other systems (`obrien2024_tablea6_full.tsv`).
  - Zero rows within 60″ in El-Badry+2021 (cone and Gaia-ID queries, with positive controls), SUPERWIDE and WDS (`vz_elbadry2021.tsv`, `vz_id_constraints.tsv`, `vz_superwide.tsv`, `vz_wds.tsv`, `vizier_positive_controls.txt`).
  - Kervella+2022 has a row for the WD, but with N = L = B = 0 candidate companions (`vz_kervella2022.tsv`).
- **Full text of the papers that list the objects:** none mentions the other object. This covers Tinney+2018, Kirkpatrick+2021, O'Brien+2023, Hernandez+2024, O'Brien+2024 and Vincent+2024, plus about 125 more WD/BD papers and the Rothermich+2024 tables (`arxiv_grep*.txt`, `tdwarf_paper_rows.txt`, `wd_paper_rows.txt`, `rothermich_grep.txt`).
- **Web search:** catalogue pages only. Stellarcatalog calls the WD "a single star" (`web_search_log.txt`).

The closest anyone came is Zhang+2025, "Benchmark brown dwarfs I". It cross-matched CatWISE T dwarfs against the GCNS, and the WD is in the GCNS. The pair passes their colour, S/N, motion, latitude, distance and separation cuts. It fails the |Δμ_α| < 40 mas/yr cut, but only if the IRSA CatWISE2020 proper motion is used (Δμ_α = 45.8 mas/yr). The VizieR II/365 copy gives a different μ_α, and with it the pair passes. They name only their 8 retained systems, and this pair is not one of them (`zhang2025_criteria_check.txt`, `zhang2025_bb1_grep.txt`). [INFERENCE: we cannot tell whether it was among their 7 unnamed rejected candidates.]

**Correction to the brief.** The T dwarf is **not** in the Kirkpatrick+2021 20-pc census (Table 11): it is absent from the full 526-row VizieR table11 (`vz_kirk2021_byname.tsv`). It appears only in Table 1, "New L, T, and Y Dwarf Candidates" (note "—": dropped from Spitzer follow-up), and in the amassed-data table A1 (`vz_kirk2021.tsv`, `tdwarf_paper_rows.txt`).

## Per-source table

| Source | Query | Result | File |
|---|---|---|---|
| SIMBAD TAP, T dwarf (oid 18628314) | basic, ident, has_ref⋈ref, otypes, mesSpT/PM/Plx, h_link | 3 idents (WISE J235447.80−814044.9, WISEA, CWISE); otype BD? (from Tinney+2018) plus MIR. **2 refs: 2018ApJS..236...28T, 2021ApJS..253....7K.** No SpT, PM, Plx measurements; no h_link. | `simbad.txt`, `simbad_bib.txt` |
| SIMBAD TAP, WD (oid 15893936) | same | Gaia DR2/DR3 idents only; otypes *, PM*, WD*, WD?. **9 refs** (as in the brief). mesSpT: DZH (O'Brien+2023), DC: (Vincent+2024). No h_link. | `simbad.txt`, `simbad_bib.txt` |
| SIMBAD cone 120″ around (358.64, −81.682) | basic | 3 objects: the WD (32.3″), the T dwarf (32.5″), and UCAC4 042-017920 (105″; ϖ 0.58 mas, unrelated) | `simbad.txt` |
| VizieR all-catalogue 60″, T dwarf | 19 prefix cones (`J/A+A/*` … `II/*`); `B/*` is truncated at B/vsx, so 12 B catalogues were queried one by one | Within 5″: AllWISE, Griffith+2012 (J/AJ/144/148, Spitzer [3.6] 16.51, [4.5] 15.08), Assef+2018 WISE-AGN, Kirkpatrick+2021 table1 and tablea1. No Gaia, 2MASS or DENIS counterpart. No column flags a companion or binary. B catalogues (VSX, WDS, MK, GCVS, SB9, PASTEL, ESO/HST/Gemini/Chandra/XMM/Swift logs): 0 rows. | `vizier_hits_tdw.txt`, `parts_tdw/` |
| VizieR all-catalogue 60″, WD | same | Within 5″: Gaia DR2/DR3 and their distances, 2MASS 23541939−8141049, AllWISE, DENIS, TIC 410255721, NOMAD/USNO-B/PPMXL/GSC, Medan+2021, GCNS, GF2019, GF2021, Torres+2019, Torres+2019 (50 pc), O'Brien+2023, O'Brien+2024, Vincent+2024, García-Zamora+2023 (SPPred DC), García-Zamora+2025 (SPPred **DZ**), Jiménez-Esteban+2023, Kao+2024, Madurga Favieres+2024 (WISE IR excess: **"No Excess"**), Gaia synthetic photometry, Gavras+2023, Kervella+2022 (Mass 0.06), SHBoost, Wang+2025 TESS flares (0 flares, "single"). Flagged columns are Teff, logg, mass, SpT, `Bin`=single, `FinalExcess`. **None names a companion.** B catalogues: ESO archive observations of the WD (programmes 114.2713.002 and 1103.D-0763(B), 549–718 s exposures) and Gemini GS-2021A-Q-320; VSX, WDS and the rest: 0 rows. | `vizier_hits_wd.txt`, `parts_wd/`, `parts_wd/vizier_B_individual.tsv` |
| Tinney+2018 (2018ApJS..236...28T) | VizieR J/ApJS/236/28: "Table or Catalog not found"; arXiv:1804.00362 HTML | Table 2 row J235447.80−814044.9: W1 18.23±0.33, W2 15.03±0.07, W1−W2 >3.20, J_MKO 17.64±0.05, CH4s 17.68±0.06, CH4s−CH4l −1.04±0.12, **T6.4±0.5** (methane type), plus 2.61±0.09 and 2.65±0.10 (J−W2 colours [INFERENCE from header]). Table 5: μ′ = (+30, −15) ± 230 mas/yr. Text lists W2354−8140 among "3 early T dwarfs … for which typing spectroscopy is required". **No companion column and no mention of the WD.** | `vz_tinney2018.tsv`, `tdwarf_paper_rows.txt`, `arxiv_grep.txt` |
| Kirkpatrick+2021 (J/ApJS/253/7) | 60″ cones on all tables; full table11/table4/plx | **table1** (new candidates): CWISE J235448.04−814044.6, Spitzer note "—", discoverers G, J, K, N (Goodman, Kirkpatrick, Khalil, Ammar). **tablea1**: SpAd 17.0 (= T7: the same code gives 2MASS 0415−0935 T8 = 18.0, `vz_kirk2021_spad_scale.tsv`), no optical or IR spectral-type reference ("−"), μ = (141.83±25.8, 72.83±23.1) mas/yr (CatWISE2020), ϖ_CatWISE 101±69 mas, J_MKO 17.61±0.04, Ks 18.13±0.26 (VHS), ch1 16.613±0.040, ch2 15.066±0.021, W1 17.365, W2 15.021. **No companion column exists in tablea1.** Not in table11 (the 20-pc census), table4 or plx. | `vz_kirk2021.tsv`, `vz_kirk2021_byname.tsv`, `vizier_specific_rows.txt` |
| Gentile Fusillo+2021 (J/MNRAS/508/3877) | 60″ cone, all columns | WDJ235419.41−814104.96, P_WD 0.9945. H: Teff 4476±44, logg 7.768±0.035, M 0.457±0.016. He: 4546±34, 7.814±0.017, 0.480±0.001. No companion column. | `vz_gf2021.tsv`, `vizier_specific_rows.txt` |
| Gentile Fusillo+2019 (J/MNRAS/482/4570) | same | P_WD 0.9986. H: 4565±33, 7.802±0.021, 0.464±0.006. He: 4610±26, 7.824±0.012, 0.467±0.002 | `vz_gf2019.tsv` |
| O'Brien+2023 (J/MNRAS/518/3055; arXiv:2210.01608) | table3 cone; HTML grep | DZH, Teff_Gaia 4480±40, logg_Gaia 7.77±0.04. Flag B=* points to Table 4: **⟨B⟩ = 0.6±0.2 MG**. Text: Ca II H and K split into 2+2 and 6 components (Zeeman); "DZH … not fitted due to the complexity of the splitting". No companion mention. | `vz_obrien2023.tsv`, `wd_paper_rows.txt` |
| O'Brien+2024 (J/MNRAS/527/8687; arXiv:2312.02735) | tablea1 cone; full tablea6 (wide binaries); HTML grep | tablea1: DZH, atmosphere H, Teff 4476±44, logg 7.769±0.035, M 0.457±0.016. Low-mass-corrected values: Teff 4676, M 0.594, **cooling age 7.76** (unit not in the column description; Gyr [INFERENCE]). **tablea6: WD absent.** It has 132 rows (WDMS 95, WDWD 15, WDBD 5, WDMSBD 1, …); its BD companions are GD 165B, PSO J058.9869+45.4296, WISEU 0055+5947, CWISE J000229.93+635217.0, L 97-3 B and Wolf 1130C, all "BD not in Gaia". HTML: 0 matches. | `vz_obrien2024.tsv`, `obrien2024_tablea6_full.tsv`, `arxiv_grep.txt` |
| Hernandez+2024 (2024MNRAS.528.6056H; arXiv:2401.15158) | VizieR: not found; HTML grep | Table 5 (magnetic WDs with TESS): WD J235419.41−814104.96, TIC 410255721, **× (no clear periodic variation)**, 26.95 pc, FluxCT 1 (22.9 %). No companion mention. | `vz_hernandez2024.tsv`, `wd_paper_rows.txt` |
| Vincent+2024 (J/A+A/682/A5; arXiv:2308.05572) | cone | XP class **DC:** (P_DC 0.64, P_DZ 0.30, P_DA 0.03). Pure-H fit: Teff 4629±28, logg 7.871±0.016, M 0.502±0.012, log L/L☉ −4.115. HTML: 0 matches. | `vz_vincent2024.tsv` |
| García-Zamora+2023 (J/A+A/679/A127), Torres+2019 (J/MNRAS/485/5573) | cones | GZ23 SPPred DC. Torres+2019: Pop = 0, UVW = (−3.05, 8.10, 1.94) km/s | `vz_garcia2023.tsv`, `vz_torres2019.tsv` |
| El-Badry+2021 (J/MNRAS/506/2269) | 60″ cones on both objects; Source1/Source2 = WD Gaia ID | 0 rows. Expected: the T dwarf has no Gaia source. Positive controls (first row by cone and by Source1) work. | `vz_elbadry2021.tsv`, `vz_id_constraints.tsv`, `vizier_positive_controls.txt` |
| GCNS (J/A+A/649/A6) | cones | WD in table1c: GCNSprob 1.000, WDprob 0.965, RUWE 1.01, IPDfmp 0, Dist50 26.95 pc, SkyMapper/2MASS/WISE cross-ids. T dwarf: 0 rows (not in Gaia). The VizieR GCNS has no binary or companion table (only table1c, table1r, missing); the GCNS paper HTML (arXiv:2012.02061) has 0 matches. | `vz_gcns.tsv`, `arxiv_grep.txt` |
| WDS (B/wds/wds), Kervella+2022 (J/A+A/657/A7), SUPERWIDE (J/ApJS/247/66) | 60″ cones on both | WDS: 0 rows. SUPERWIDE: 0 rows. Kervella tablea3 (Gaia stars within 100 pc) has the WD with T=1 (parent), DMS=0, W=0 (not in WDS), N=L=B=0 companions, and **Mass 0.06** [INFERENCE: a main-sequence M_K–mass value, meaningless for a WD]. | `vz_wds.tsv`, `vz_kervella2022.tsv`, `vz_superwide.tsv` |
| Rothermich+2024 (Backyard Worlds, 89 co-moving UCDs) | grep of local tables 1, 2, 11, lowprob, spectra and the full text for 2354, 235447, 235448, 235419, the WD Gaia ID, 358.7, 358.58, J2354 | 0 matches in every file. Positive control "2358": 3/2/1/5 matches. | `rothermich_grep.txt` |
| Zhang+2025 Benchmark BDs I (arXiv:2505.24560; /tmp/bb1.pdf) | HTML grep and PDF text (pdfminer) | 0 matches for 2354, 235447, 235448, 235419, the Gaia ID, 8140, "white dwarf" or "WD". Selection: CatWISE late-T × GCNS, Δμ < 40 mas/yr, d < 40 pc, sep < 10′, giving 15 candidates, 8 kept (all named; none is this pair) and 7 rejected (not named). | `zhang2025_bb1_grep.txt`, `zhang2025_criteria_check.txt` |
| "Benchmark brown dwarfs II" and 2025–26 follow-ups | arXiv API `ti:"benchmark brown dwarfs"`; web search | No paper II found. Related 2026 papers 2607.09851 (Benchmark BD Systems I, FGK hosts), 2608.26029, 2609.13433 and 2604.09845 were grepped: 0 matches. | `arxiv_grep.txt`, `arxiv_grep_extra.txt`, `web_search_log.txt` |
| arXiv title/abstract API, 11 queries 2019–2026 (WD+BD wide/companion, WD+T dwarf, WD+UCD companion/binary, COCONUTS, Backyard Worlds+WD, benchmark BD+WD, magnetic DZ companion, WD wide binaries 40 pc), plus 10 explicit papers | Full-text grep (HTML, else PDF via pdfminer, else abstract) for 2354−81 (−, −, –, $-$), 235447, 235448, 235419, 235420, J2354, the Gaia ID, 358.58, 358.70, 358.69 | 106 papers. Hits only in the papers that list the objects (Tinney, Kirkpatrick, O'Brien+2023, Hernandez). Every other "J2354"/"358.58" hit is a different object: WISE 2354+0240, WD J235432.47+…, J2354−3316, WISEA J235456.63−…, and a LAMOST table value at RA 159.4. **No paper mentions both objects.** | `arxiv_grep.txt` |
| Extra arXiv papers | 2604.09845, 2607.09851, 2609.13433, 2609.03017 ("scarcity of WD–BD binaries", 2026), 2412.04597 (new UCD companions to nearby WDs), 2312.10158, 2007.15389, 2301.02101/2204.09739/1911.00125 (PDF text), plus 13 Backyard Worlds / COCONUTS / CatWISE / 20-pc-IMF papers | 0 matches for either object | `arxiv_grep_extra.txt`, `arxiv_grep_extra2.txt` |
| Web search (10 queries) | All 3 T-dwarf designations, the WD Gaia ID, the WDJ name, "J2354-8140 white dwarf", "WISE 2354-8140 companion", Benchmark BDs II | Only catalogue pages (stellarcatalog "single star", starcarta "DZ … 4629 K"). No pairing anywhere. | `web_search_log.txt` |

## WD physical parameters found (Gaia DR3 6350786278796634112 = WDJ235419.41−814104.96)

| Catalogue | SpT / atmosphere | Teff (K) | log g | Mass (M☉) | Other | File |
|---|---|---|---|---|---|---|
| O'Brien+2023 (spectroscopy) | **DZH** | 4480±40 (Gaia phot.) | 7.77±0.04 | – | **⟨B⟩ = 0.6±0.2 MG**; Zeeman-split Ca II H&K; no spectroscopic fit | `vz_obrien2023.tsv`, `wd_paper_rows.txt` |
| O'Brien+2024 (40-pc sample) | DZH, H | 4476±44 | 7.769±0.035 | 0.457±0.016 | Low-mass-corrected: Teff 4676, M 0.594, **cooling age 7.76** (Gyr [INFERENCE]) | `vz_obrien2024.tsv` |
| Gentile Fusillo+2021 | H | 4476±44 | 7.768±0.035 | 0.457±0.016 | P_WD 0.9945 | `vz_gf2021.tsv` |
| Gentile Fusillo+2021 | He | 4546±34 | 7.814±0.017 | 0.480±0.001 | | `vz_gf2021.tsv` |
| Gentile Fusillo+2019 (DR2) | H / He | 4565±33 / 4610±26 | 7.802±0.021 / 7.824±0.012 | 0.464±0.006 / 0.467±0.002 | | `vz_gf2019.tsv` |
| Vincent+2024 (XP) | DC: (P_DZ 0.30), pure H | 4629±28 | 7.871±0.016 | 0.502±0.012 | log L −4.115 | `vz_vincent2024.tsv` |
| García-Zamora+2023 / +2025 (XP) | DC / DZ | – | – | – | | `vz_garcia2023.tsv`, `vizier_hits_wd.txt` |
| Madurga Favieres+2024 | – | 4476 | 7.77 | 0.46 | **WISE W1/W2: "No Excess"** (W1 15.36 vs model 15.18; W2 15.37 vs 15.05) | `vizier_hits_wd.txt` |
| Hernandez+2024 (TESS) | magnetic | – | – | – | No clear rotation period (×), TIC 410255721 | `wd_paper_rows.txt` |
| Astrometry (GF2021 / GCNS) | | | | | ϖ 37.1045±0.061 mas (26.95 pc), μ (96.033, 36.288) mas/yr, RUWE 1.01, G 17.22 | `vz_gf2021.tsv`, `vz_gcns.tsv` |

No catalogue gives a total age (cooling plus progenitor) or a metal abundance. O'Brien+2023 did not fit the spectrum.

## T dwarf rows (WISE J235447.80−814044.9 = CWISE J235448.04−814044.6)

| Source | SpT | Photometry | Astrometry | Companion / notes column | File |
|---|---|---|---|---|---|
| Tinney+2018 Table 2 / Table 5 | T6.4±0.5 (CH4 imaging); text: "early T … typing spectroscopy required" | W1 18.23±0.33, W2 15.03±0.07, J_MKO 17.64±0.05, CH4s 17.68±0.06 | μ′ (+30, −15) ± 230 mas/yr | none | `tdwarf_paper_rows.txt` |
| Kirkpatrick+2021 table1 / tablea1 | SpAd 17.0 (T7, no spectrum) | J_MKO 17.61±0.04, Ks 18.13±0.26, ch1 16.613±0.040, ch2 15.066±0.021, W1/W2 (CatWISE) 17.239/15.027 | μ (141.83±25.8, 72.83±23.1) mas/yr, ϖ 101±69 mas | none (tablea1 has no such column); table1 note "—" | `vz_kirk2021.tsv` |
| Griffith+2012 (J/AJ/144/148 table1) | – | [3.6] 16.509, [4.5] 15.079, W1 18.231, W2 15.027 | – | none; this ref is not in SIMBAD's bibliography | `vizier_hits_tdw.txt` |
| CatWISE2020 II/365 (VizieR) vs IRSA | – | – | VizieR pmRA/pmDE 121.85/70.60; IRSA 141.83/72.83 (±25.8/23.1) mas/yr; nb = 1, ab_flags 00 | – | `vizier_specific_rows.txt`, `../irsa_catwise_2020.tbl` |

## Not checked

- **NASA ADS** (no token) and Google Scholar. Journal-only full texts not on arXiv. AAS meeting abstracts. Backyard Worlds forum and Zooniverse Talk.
- **VizieR completeness.** `B/*` truncates at B/vsx, so only 12 B catalogues were queried individually. The first pass of several prefix cones returned "database not currently reachable" and was re-run (`vizier_parts.log`, `vizier_parts_retry.log`). The `II/*` prefix answer lacks CatWISE (II/365) even though a direct query returns it (`vz_catwise.tsv`), so large tables can drop out of prefix cones silently. J/RNAAS is not a valid prefix.
- **arXiv coverage.**
  - The title/abstract API is fuzzy, and two queries ("WD+BD companion" and COCONUTS) hit the 60-result cap, so older papers may be missed.
  - Pre-2019 papers were searched only if named explicitly.
  - The sweep patterns (`2354-81` in 4 dash forms, `J2354`, 235447/8, 235419/20, the Gaia ID, RA strings) would miss Tinney-style "W2354" written with a LaTeX minus in some other paper.
  - Tables published only as machine-readable files are invisible to the HTML/PDF grep. This matters for 2604.01323 (3,000 Backyard Worlds L/T candidates) and 2312.03639 (20-pc census of ~3,600 objects; PDF text only): 0 matches in both, but their full tables were not downloaded.
- **Zhang+2025 rejected candidates.** Their 7 rejected pairs are not named, and the CatWISE μ_α discrepancy (VizieR 121.85 vs IRSA 141.83 mas/yr) was not resolved. So we cannot say whether this pair was considered and rejected.
- **GCNS binaries.** The GCNS wide-binary list is not in VizieR and was not queried in the Gaia archive.
- **ESO and Gemini programmes on the WD.** Programme 114.2713.002 (ESO P114, telescope ID 91) and Gemini GS-2021A-Q-320: PI and purpose not looked up. These could be unpublished follow-up (e.g. polarimetry). No archive observations exist within 60″ of the T dwarf (`parts_tdw/vizier_B_individual.tsv`).
- **Kirkpatrick SpAd scale.** Calibrated with one object (2MASS 0415−0935 T8 = 18.0); the VizieR ReadMe was unreachable. The meaning of tablea1 `T` = "C" was not decoded.
- **O'Brien+2024 age unit.** The column description gives no unit for `Agec`. The paper's definition of the low-mass correction was not read.
- **SIMBAD** lists only 2 refs for the T dwarf and misses Griffith+2012 (found via VizieR), so papers that use another name for it could be missed.
- **Gaia DR4 / future releases**: not checked.
