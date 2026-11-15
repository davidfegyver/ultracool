# Adversarial review: CWISE J235827.96−521813.4 ("J2358−5218") + UCAC4 189-203856

Date: 2026-11-15. The claim under review:

> "CWISE J235827.96−521813.4 (= 2MASS J23582773−5218133, Gaia G ≈ 20.9) gets its first spectrum-based spectral type from SPHEREx: L0 (range M9–L1), i.e. an ultracool dwarf at the stellar/substellar boundary. It is a wide (~30″, ~2,300 au) co-moving companion of UCAC4 189-203856 (Gaia ϖ ≈ 12.8 mas, ~78 pc), confirming Rothermich et al. 2024's photometric (M9) estimate and their 100 % membership probability with an independent spectrum and a consistent spectrophotometric distance."

The evidence is `research/discovery2/out/J2358-5218/` (verdict.json, spectrum.json, summary.json) and dev sequence `10cd5c77eacd8c7d`, re-fetched read-only into `dev_spectrum_now.json` and `dev_summary_now.json` here. Its binned spectrum is identical to `spectrum.json`.
No repo code was edited. Everything is in `research/verification/J2358/`. The method follows `../J2317_ADVERSARIAL.md`.

## Overall verdict

**It can be claimed only in narrowed form: as a first infrared spectral characterisation of a known pair, not as a discovery.** The physics holds. The novelty and some of the wording do not.

What holds:
- The pair is real and co-moving. Gaia DR3 gives Δμ = (−0.03, +0.04) ± 2.1 mas/yr and Δϖ = −0.86 ± 1.43 mas (0.6σ). The expected number of chance Gaia kinematic twins within 30″ is ~3×10⁻⁵.
- The SPHEREx spectrum (86 channels, 1.03–4.97 µm, median S/N 8 per channel, χ²ᵣ = 1.04) is a clean late-M/early-L ultracool dwarf. Every variant excludes L2 and later (Δχ² ≥ 71). Its band-averaged shape matches the VHS + CatWISE photometric SED to ≤ 0.09 mag.
- Its type agrees with Rothermich's (M9).
- The spectrophotometric distance (M9/L0: 78–81 pc) agrees with the host (77.9 pc) and with the UCD's own Gaia parallax (83.5 pc).

What breaks or must be added:
1. **"L0" is not resolved from M9.** Without the template-spread term, M9 beats L0 (Δχ² = 2.0). The 1–2.5 µm data alone prefer M9 in both settings. The bootstrap gives L0 88 % with the spread term and M9 59 % without it. The earliest SPIFF template is M8, so the grid has no M7 to test the early edge. Absolute magnitudes at the host parallax fit M9–L0 best and put L1 at 1.5–2.3σ. **Honest label: M9–L0 ("≈M9.5 ± 1").** The quoted "M9–L1" range is fine as a conservative bound, but the headline "L0" overstates precision.
2. **"First spectrum-based" needs a qualifier.** Gaia DR3 ESP-UCD already gives **T_eff = 2295 ± 256 K from the object's Gaia RP spectrum**: `teff_espucd`, flag 20, i.e. quality class 2, the lowest. That T_eff ≈ M8.5–L2. It is not a spectral type, so "first spectral type from a spectrum" survives only as **"first infrared (1–5 µm) spectrum and spectrum-based spectral type"**.
3. **A published L0 already exists.** Dal Ponte et al. 2023 (DES Y6 UCD candidates, VizieR J/MNRAS/522/1951) list it with photometric type **SPType = 10 = L0** and D_phot = 74.8 pc. Their template grid starts at L0, so their L0 means "L0 or earlier". There are therefore *two* prior photometric types (M9, L0), not one.
4. **The pair was not first proposed by Rothermich+2024.**
   - Hartman & Lépine 2020 (SUPERWIDE, J/ApJS/247/66 tables 7/8, recno 56824) list it as a candidate pair, in the subset with first-pass probability > 10 % but parallax error > 10 %.
   - Kervella et al. 2022 (J/A+A/657/A7 tablea3) list UCAC4 189-203856 as a common-proper-motion candidate of the UCD. They give sep 30.22″, 2,520 au, ΔV_tan = 0.01 ± 1.19 km/s, V_esc = 0.73 km/s, `LowV = 1`, PlxSc 0.979, and a UCD mass of 0.04 M☉.
   - Rothermich+2024 is the first paper to treat it as a high-probability system with an age/metallicity context. Credit all three.
5. **"Confirming … their 100 % membership probability with an independent spectrum" is a category error.** A spectrum does not test co-motion; the Gaia DR3 astrometry does, and Rothermich already used it. What the spectrum adds is a type consistent with the system distance. Our own WISE + SPHEREx proper motion (115.7, −5.5) ± 13.5 mas/yr agrees with the host within 0.9σ. It is independent of Gaia but 6× weaker, so it is a consistency check, not a confirmation.
6. **"Brown dwarf" is not justified; "at the stellar/substellar boundary" is.** BHAC15 isochrones at the measured M_Ks = 10.37 and T_eff ≈ 2300 K give:
   - 0.075–0.084 M☉ for ages ≥ 1 Gyr: a star at the hydrogen-burning limit.
   - 0.068–0.080 M☉ at 0.5–0.8 Gyr.
   - 0.05–0.06 M☉ only if the system is ≤ 0.3 Gyr.
   The only age indicator is the host's chromospheric activity: Žerjal+2017 Ca II IRT EW 0.29 ± 0.11 Å, log age 8.86, i.e. ~0.7 Gyr, behind Rothermich's "0.1–1 Gyr". So the object is on the boundary. The app's plain-language line "fits a L0 brown-dwarf template" (`dev_summary_now.json` → `plain[3]`) should say "ultracool-dwarf template".

## Claim-by-claim

| # | Claim (ours) | Independent value(s) | Verdict | Sources |
|---|---|---|---|---|
| 1a | "first spectrum-based spectral type" | No published spectral type from a spectrum was found: SIMBAD has no `mesSpT` and only 2 bibcodes; Rothermich Table 4 (spectroscopic observations) does not list it; it is absent from UltracoolSheet, SPIFF, 16 arXiv papers (full-text grep) and the web. **But Gaia DR3 ESP-UCD T_eff = 2295 ± 256 K from the RP spectrum (flag 20 = quality 2, lowest).** No Gaia XP spectrum is published (G = 20.9 > 17.65; I/355/spectra returns 0 rows). | **weakened** | `simbad.txt`, `simbad2.txt`, `gaia_paramp_ucd.tsv` (`Teff-UCD`, `Flags-UCD`), `gaia_I_355_spectra_ucd.tsv`, `apsis_espucd_flag_excerpts.txt` (flag definition, arXiv:2206.05992), `arxiv_grep.txt`, `web_search_log.txt` |
| 1b | Prior type = Rothermich "(M9)", photometric | Rothermich Table 1: `(M9)`, ref 1 = their own estimate. §V.1.2: secondaries without spectra are typed from M_W2 at the host parallax (Kirkpatrick+2021). Reproduced: M_W2 = 14.200 − 4.457 = **9.74**, matching UltracoolSheet field singles M9 9.66 ± 0.34 and L0 9.75 ± 0.39. **Also Dal Ponte+2023 SPType = 10 (L0), photometric, grid floor L0.** | **incomplete** (two photometric types exist) | `../rothermich_text.txt` §V.1.2, `vizier_hits.txt`, `vizier_part_J_MNRAS__.tsv.gz` (column note: "Photometric spectral type ranging L0 to T9 with L0=10"), `recompute_out.json` |
| 2a | SPHEREx type L0 (χ²ᵣ 1.04, p = 0.9997) | 86 bins; S/N median 8.2, max 17.1; 85 bins > 3σ, 70 bins > 5σ; 0 negative. Δχ² vs L0 (with spread): M8 +16.6, M9 +23.1, L1 +31.8, L2 +71, L3 +164. **Without spread: M9 0, L0 +2.0, L1 +41, M8 +44.** 1.0–2.5 µm: M9 0, L0 +1.8 (+2.0 without spread). 2.5–5 µm: L0 0, L0γ +1.1 (with spread); L0γ 0, L0β +7.6, M9 +12.5, L0 +21 (without). Errors × 1.5: L0 0, M9 +9.0. S/N > 5 only: L0 0, M8 +12.6. Bootstrap of field standards: L0 442/500, M8 57, M9 1 (with spread); M9 296, L0 203 (without). | **weakened → "M9–L0"** | `spectral_refit.py`, `spectral_refit_out.json`, `spectral_refit_stdout.txt` |
| 2b | range "M9–L1" | The spectrum alone allows M8–L0. M8 is the grid edge (no M7 template). Absolute magnitudes at the host parallax vs UltracoolSheet field singles, in σ (M_G / M_J / M_W2 / G−J): **M8** 2.4 / 2.2 / 1.3 / 1.8; **M9** 1.2 / 1.2 / 0.2 / 0.6; **L0** 0.6 / 0.8 / 0.0 / −0.1; **L1** −1.5 / −0.8 / −2.3 / −1.8. Pecaut & Mamajek (2022.04.16): M_G → M9–L0, M_J → M9–L1, M_W2 → M8.5–L0, G−J → M9–L1. Gaia ESP-UCD T_eff 2295 ± 256 K → M8.5–L2. | **holds** as a conservative range; best estimate M9–L0 | `recompute_out.json` (`UCS_field_single_loci`, `EEM_types_within_tol`), `EEM_dwarf_UBVIJHK_colors_Teff.txt` |
| 2c | spectrum is clean / uncontaminated | SPHEREx band means / J vs VHS + CatWISE: H −0.01, Ks −0.07, W1 −0.01, W2 −0.09 mag (vs 2MASS: +0.18/+0.28, but 2MASS J±0.12, Ks±0.12 are noisy). VHS galaxy J = 19.24 at 3.6″ (pGal 0.9) and a DES galaxy at 7.8″ lie inside the 8.25″ aperture: ≈ 5–10 % of the 1–1.3 µm flux. No CatWISE source within 11.6″ (W2 17.5, 3.3 mag fainter). | **holds** (minor contamination at λ < 1.3 µm, not modelled) | `sed_check.py`, `sed_check_out.json`, `vizier_specific.txt` (II/367, II/371, II/365) |
| 2d | colours fit M9/L0 | W1−W2: CatWISE 0.337 ± 0.020, AllWISE 0.382, ours 0.259 ± 0.013. UltracoolSheet M9/L0 0.25 ± 0.04 → CatWISE is +2.1/+2.2σ red. J−Ks: 2MASS 1.45 ± 0.17 (L0 1.22 ± 0.13, +1.8σ); VHS 1.10 ± 0.03. G−RP 1.523 ± 0.066 (M9/L0 1.57). | **holds** (slightly red W1−W2, possibly youth or noise; not significant) | `recompute_out.json` |
| 3a | co-moving companion | Gaia DR3 UCD 6521791947874851968: ϖ 11.98 ± 1.43, μ (103.807 ± 2.112, 6.127 ± 2.148). Host 6521792325832957440: ϖ 12.8445 ± 0.0179, μ (103.838, 6.091). Δμ = (−0.031, +0.036) ± 2.1 mas/yr, χ² = 0.0005 (2 dof). This is luck: P(χ² that small) ≈ 2.5×10⁻⁴, so it is not extra evidence. Δϖ = −0.86 ± 1.43 (0.6σ). CatWISE PM (117.2, 27.5) ± (9.4, 8.3) is 1.4σ/2.6σ off: a known CatWISE systematic, irrelevant given Gaia. Our WISE + SPHEREx PM (115.7, −5.5) ± 13.5: 0.9σ/0.9σ. | **holds** (strongly) | `gaia_dr3_ucd.tsv`, `gaia_dr3_host.tsv`, `recompute_out.json` → `companion_gaia`, `ucd_pm_vs_host` |
| 3b | ~30″, ~2,300 au, ~78 pc | 30.22″ (Gaia epoch 2016); host d = 77.85 pc → **2,353 au** projected. Kervella: 2,520 au (EDR3 parallax 12.862). Rothermich: 30.0″, 2,300 au. | **holds** | `recompute_out.json` |
| 3c | bound? | v_tan(host) = 38.4 km/s. ΔV_tan = 0.02 ± 0.8 km/s. V_esc at 2,353 au for 0.77 M☉ = **0.76 km/s (2.06 mas/yr)**. The Gaia error equals V_esc, so the data are consistent with a bound orbit but cannot prove it. Kervella: `LowV = 1`, `BndSc = 0.000`. | **holds as "co-moving"**; "bound" unproven | `prior_pair_catalogues.tsv` |
| 3d | chance alignment negligible | Gaia DR3 within 10° (313 deg²), ϖ within 3σ of the UCD (7.7–16.3 mas): 8 / 44 / 110 sources with \|Δμ\| < 5 / 10 / 20 mas/yr. Expected number within 30.2″ = **5.7×10⁻⁶ / 3.1×10⁻⁵ / 7.8×10⁻⁵**. No other Gaia source within 120″ of the host shares the motion. | **holds** | `gaia_twins_10deg.tsv`, `gaia_host_120as.tsv`, `recompute_out.json` → `chance_alignment` |
| 3e | "consistent spectrophotometric distance" | W2 = 14.200. UltracoolSheet M_W2: M9 → 80.9 (69–95) pc, L0 → 77.6 (65–93), L1 → 64.3 (59–70). Pecaut & Mamajek: M9 75.9, L0 71.8, L1 65.5. Kirkpatrick+2021 L0 (rms 0.31): 65.9 (57–76). Dal Ponte D_phot 74.8. Host **77.85**; UCD's own Gaia **83.5 (74.6–94.7)**. | **holds** for M9/L0 (L1 is 1–2σ short). It adds little: the UCD's own Gaia parallax already measures its distance. | `recompute_out.json` → `spectrophotometric_distance_pc` |
| 4a | "ultracool dwarf at the stellar/substellar boundary" | BHAC15 (M_Ks 10.37, M_J 11.82, T_eff 2295 K): ≥ 1 Gyr → 0.075–0.084 M☉; 0.5–0.8 Gyr → 0.063–0.080; 0.3 Gyr → 0.05–0.06; 0.1 Gyr → 0.035. Rothermich mass 0.08 M☉; Kervella 0.04 M☉. | **holds**; "brown dwarf" would be **unjustified** | `mass_check.py`, `mass_check_out.json`, `BHAC15_iso.2mass` |
| 4b | host UCAC4 189-203856 | = RAVE J235830.9-521806 = TIC 201234567 = 2MASS J23583095-5218061. G 11.388, BP−RP 1.445, M_G 6.93 → **K5V–K6V** (Pecaut & Mamajek). GSP-Phot T_eff 4542 K, log g 4.64; GSP-Spec T_eff 4472 K, log g 5.10. FLAME 0.72 (0.68–0.76) M☉. Rothermich "(K)", 0.69 M☉. SIMBAD otype PM*, no SpT. | **holds** | `gaia_paramp_host.tsv`, `simbad2.txt` |
| 4c | host single? | RUWE 1.27 (< 1.4), `IPDfmp` 0, NSS 0, rv_chisq p = 0.28 over 26 RVS transits. RVs: −6.66 ± 0.25 (DR3), −7.14 ± 0.33 (DR2), −8.04 ± 1.0 (RAVE, 2004). Not in WDS, VSX lists `ROT`, Gaia `SOLAR_LIKE` variable (ΔG 0.06 mag). No other co-mover within 120″. | **no evidence of binarity** (a mildly high RUWE leaves room for a faint close companion) | `gaia_dr3_host.tsv`, `gaia_I_358_vari_host.tsv`, `vizier_B_and_check.txt`, `host_rave_zerjal.tsv` |
| 4d | benchmark value (age / metallicity) | Age: Žerjal+2017 EW_IRT 0.29 ± 0.11 Å (only 2.6σ), log age 8.86 (~0.7 Gyr) → Rothermich Table 8 "Age_Lit 0.1–1 Gyr" (ref [210] = Žerjal+2017; no rotation age). Gaia vbroad 8.3 ± 3.9 km/s. FLAME age 7.3 (4.5–11.5) Gyr is uninformative for a K dwarf [INFERENCE]. **Metallicity disagrees**: RAVE/Boeche+2011 [Fe/H] −0.17 ± 0.20 (Rothermich Table 9), GSP-Spec [M/H] +0.34 (flag string `0000000200000…`), GSP-Phot +0.55 (known to be biased). | **weak benchmark**: age only loosely constrained, metallicity unsettled | `host_rave_zerjal.tsv`, `gaia_paramp_host.tsv`, `../rothermich_text.txt` Tables 8–9 |
| 5 | "confirming Rothermich's 100 % membership with an independent spectrum" | The membership probability is kinematic (Gaia), so a spectrum cannot confirm it. Kervella+2022 and SUPERWIDE (2020) had already listed the pair. | **wrong as worded** → "consistent with" | `prior_pair_catalogues.tsv`, `vizier_hits.txt` |

## Prior-work search (item 1): every source checked

| Source | Query | Result |
|---|---|---|
| SIMBAD (CDS down → Harvard TAP `https://simbad.harvard.edu/simbad/sim-tap/sync`) | cone 60″; `ident`, `has_ref⋈ref` (bibcodes), `mesSpT`, `flux`, `otypes` for both objects | UCD: `2MASS J23582773-5218133`, otype **LM\***. Identifiers: Gaia DR3 6521791947874851968, WISE J235827.88-521813.4, WISEA J235827.90-521813.5, CWISE J235827.96-521813.4. **2 bibcodes: 2021A&A...649A...6G (GCNS), 2024AJ....167..253R.** No `mesSpT`. Host: 11 bibcodes (RAVE DR2–DR6, RAVE distances, Boeche+2011 abundances, GCNS, Rothermich). The `otypes` query for the UCD timed out (504) every time. |
| VizieR all-catalogue 20″ cone (Harvard mirror) | No `-source`: truncated at ~385 kB twice. Split into 19 prefix queries (`vizier_part_*.tsv.gz`, summary `vizier_hits.txt`). | UCD hits: Gaia DR2/EDR3/DR3 + Bailer-Jones distances, 2MASS, AllWISE, DENIS, NOMAD, TIC 8.2, GCNS, Medan+2021 (K/M cross-match), Gagné+2015 BASS input list, Ashby+2013 SSDF IRAC, Legacy Survey DR8 photo-z, **Kervella+2022 (mass 0.04)**, **SUPERWIDE (Hartman & Lépine 2020)**, **Dal Ponte+2023 (SPType L0)**, **Rothermich+2024 (M9)**. No spectroscopic SpT column anywhere. |
| VizieR specific (`vizier_specific.txt`, 07:3x UTC while the mirror worked) | CatWISE, AllWISE, 2MASS, VHS DR4/DR5, DES DR2, SkyMapper DR4, Reylé+2018 Gaia UCDs (J/A+A/619/L8), GCNS, Sarro+2023 Gaia DR3 UCDs (J/A+A/669/A139), Creevey+2023 golden sample (J/A+A/674/A39), Rothermich | Photometry and astrometry only. **Not in Reylé+2018, Sarro+2023 or Creevey+2023 tables** (0 rows). |
| Gaia DR3 | I/355/gaiadr3, paramp, paramsup, spectra, epphot | ESP-UCD T_eff 2295 ± 256 K, flag 20. No XP spectrum or epoch photometry published. Astrometric excess noise 4.2 mas (significance 2.97), RUWE 1.21: typical of a faint red source, but unresolved binarity is not excluded. |
| UltracoolSheet v2.1.0 | positional match | **Absent** (nearest UltracoolSheet object 14,634″ away) |
| SPIFF autotype table (`backend/app/data/ucd_catalog.csv`, 16,917 rows) | positional match | **Absent** (nearest 4,205″). Therefore also not in the SUDA atlas (arXiv 2604.26771, drawn from UltracoolSheet) [INFERENCE from its sample definition]. |
| Rothermich+2024 (arXiv:2403.04592 HTML, `../rothermich_text.txt`) | full-text grep for 2358 / UCAC4 189-203856 | Found in Table 1 (`(M9)`, 30″, 2,300 au, 100 %), Table 2 (photometry: G 20.922, J 16.08, H 15.48, K 14.99 from VHS, W1 14.54, W2 14.20), Table 8 (host age 0.1–1 Gyr, Žerjal+2017), Table 9 (host [Fe/H] −0.17 ± 0.20, Boeche+2011) and Table 10 (masses 0.69 + 0.08 M☉, binding energy 3.0×10⁴¹ erg). **Not in Table 4 (spectroscopic observations), and no text discussion.** |
| arXiv export API (title/abstract: SPHEREx × brown dwarf / ultracool / L dwarf / M dwarf; Backyard Worlds companion; wide companion ultracool Gaia) | 16 papers, full-text HTML grep for 2358-5218, 235827, 23582773, J2358, 189-203856, both Gaia IDs, 359.616, 359.62 (`arxiv_grep.py`, `arxiv_grep.txt`) | Only 2403.04592 (Rothermich) hits. SPHEREx papers 2604.22012 (SPIFF), 2604.26771 (SUDA), 2607.00543, 2608.08908, 2608.25993: no mention. |
| Web search (3 queries) | `web_search_log.txt` | Catalogue pages only |
| LAMOST / RAVE / 6dF | VizieR V/* and III/* parts: 0 UCD rows | The UCD (G 20.9, J 16.1) is far below the RAVE/6dF limits. LAMOST does not reach δ = −52° [INFERENCE]. The host *is* a RAVE star (DR2–DR6). |
| NASA ADS | API | **HTTP 401 (no token): ADS full text not searched** (`ads_probe.txt`) |

## What is actually new versus prior work

| Item | Before us | What we add |
|---|---|---|
| Pair identification | Hartman & Lépine 2020 (candidate), Kervella+2022 (CPM candidate, low ΔV_tan), Rothermich+2024 (100 %, BYW) | Nothing new. An independent WISE + SPHEREx proper motion agrees, but at 13.5 mas/yr precision vs Gaia's 2.1. |
| Spectral class | Rothermich (M9) from M_W2; Dal Ponte+2023 L0 (photometric, grid floor); Gaia ESP-UCD T_eff 2295 ± 256 K (RP spectrum, quality 2) | **First 1–5 µm spectrum (SPHEREx, 86 channels) and first spectrum-based spectral type: M9–L0.** It agrees with all three. |
| Distance | Gaia ϖ of both objects (host 0.14 %, UCD 12 %) | A consistent spectrophotometric distance: a sanity check, not new information. |
| Mass / nature | Rothermich 0.08 M☉, Kervella 0.04 M☉ | Our BHAC15 bracket: 0.075–0.084 M☉ if ≥ 1 Gyr, below 0.07 only if ≤ 0.5 Gyr. Not new data, but it settles the wording: "boundary", not "brown dwarf". |
| Peculiarity | — | No peculiarity at SPHEREx resolution (χ²ᵣ ≈ 1). The 2.5–5 µm part mildly prefers L0γ without the spread term: a hint only, not a gravity measurement. |

## Recommended public wording

**Headline:**
> SPHEREx gives the first infrared spectrum of a faint ultracool companion to a nearby K star: a late-M / early-L dwarf (≈M9–L0) at the edge between stars and brown dwarfs.

**Body:**
> CWISE J2358−5218 is a faint (Gaia G = 20.9) ultracool dwarf that moves across the sky together with the K dwarf UCAC4 189-203856, 30″ (≈2,350 au) away at 78 pc. The pair was flagged in Gaia-based companion searches (Hartman & Lépine 2020; Kervella et al. 2022) and by Backyard Worlds volunteers (Rothermich et al. 2024), who estimated an M9 type from its brightness. With this app we extracted its SPHEREx 1–5 µm spectrum. It matches ultracool-dwarf templates of type M9–L0, consistent with that estimate and with Gaia's temperature (~2,300 K). Its mass is ~0.07–0.08 solar masses, right at the hydrogen-burning limit, so whether it is a very-low-mass star or a brown dwarf depends on the system's age, which is still poorly known.

**Caveat line:**
> SPHEREx gives low-resolution spectrophotometry (R ≈ 40–130), not a slit spectrum. "First" means the first infrared spectrum we found in SIMBAD, VizieR, the UltracoolSheet, SPIFF and arXiv as of Nov 2026 (ADS full text not searched). Gaia DR3 had already estimated its temperature from a low-S/N optical (RP) spectrum.

**Remove or soften:**
- "first spectrum-based spectral type" → "first infrared spectrum / first spectrum-based type", plus the Gaia ESP-UCD caveat.
- "L0" → "M9–L0" (or "≈L0, ±1 subtype"). Do not imply L0 is distinguished from M9.
- "confirming … 100 % membership probability with an independent spectrum" → "consistent with the co-moving system identified from Gaia astrometry". Cite SUPERWIDE and Kervella as well as Rothermich.
- "brown-dwarf template" (app `plain` text) → "ultracool-dwarf template". Do not call it a brown dwarf.
- "consistent spectrophotometric distance": fine, but quote the UCD's own Gaia parallax (83.5 +11/−9 pc) as the primary evidence.

## Files

All Python runs used `nice -n 15 /home/paw/Desktop/ultracool/.venv/bin/python`. CDS Strasbourg was down, so the Harvard mirrors were used.

| File | What |
|---|---|
| `queries.sh` | Every catalogue / API query (SIMBAD, VizieR, Gaia, reference tables, dev API) |
| `simbad.txt`, `simbad2.sh`, `simbad2.txt` | SIMBAD TAP results |
| `gaia_dr3_{ucd,host}.tsv`, `gaia_paramp_{ucd,host}.tsv`, `gaia_I_355_{paramsup,spectra,epphot}_*.tsv`, `gaia_I_358_vari_host.tsv` | Gaia DR3 main, AP (ESP-UCD, GSP-Phot/Spec, FLAME), supp, XP (none), epoch photometry (none), variability |
| `gaia_twins_10deg.tsv`, `gaia_host_120as.tsv`, `gaia_field_1deg_plx5.tsv` | Chance-alignment and neighbourhood queries |
| `vizier_specific.txt`, `vizier_all_20as_ucd.tsv` (truncated), `vizier_all_5as_host.tsv` (truncated), `vizier_part_*.tsv.gz`, `vizier_hits.py` → `vizier_hits.txt`, `vizier_B_and_check.txt`, `vizier_spotcheck*.txt` | VizieR cone results and the mirror-degradation evidence |
| `prior_pair_catalogues.tsv`, `host_rave_zerjal.tsv` | Kervella+2022 and SUPERWIDE rows; RAVE DR6 and Žerjal+2017 host rows |
| `recompute.py` → `recompute_out.json`, `recompute_stdout.txt` | Gaia companionship, chance alignment, colours, absolute magnitudes vs Pecaut & Mamajek and UltracoolSheet loci, distances, presence in UltracoolSheet/SPIFF (`vztsv.py` = TSV reader) |
| `spectral_refit.py` → `spectral_refit_out.json`, `spectral_refit_stdout.txt` | 47-template refits: with/without spread, NIR/MIR halves, errors × 1.5, field-only, S/N > 5, χ² curve, bootstrap |
| `sed_check.py` → `sed_check_out.json` | SPHEREx band ratios vs 2MASS/VHS/CatWISE |
| `mass_check.py` → `mass_check_out.json` | BHAC15 masses vs age |
| `EEM_dwarf_UBVIJHK_colors_Teff.txt`, `BHAC15_iso.2mass` | Reference tables (Pecaut & Mamajek v2022.04.16; Baraffe+2015) |
| `apsis_espucd_flag_excerpts.txt`, `sarro2023_flag_excerpts.txt`, `gaia_dr3_espucd_doc_aip.txt` | ESP-UCD definitions (arXiv 2206.05992, 2206.05864, 2211.03641; gaia.aip.de) |
| `arxiv_grep.py` → `arxiv_grep.txt`, `web_search_log.txt`, `ads_probe.txt` | Literature-search logs |
| `dev_spectrum_now.json`, `dev_summary_now.json` | Dev API sequence 10cd5c77eacd8c7d (read-only GET) |

Key URLs:
- https://arxiv.org/html/2403.04592 (Rothermich+2024, §V.1.2 and Tables 1, 2, 4, 8–10)
- https://arxiv.org/html/2206.05992v1 (ESP-UCD quality flags)
- VizieR J/MNRAS/522/1951 (Dal Ponte+2023), J/A+A/657/A7 (Kervella+2022), J/ApJS/247/66 (Hartman & Lépine 2020), J/ApJ/835/61 (Žerjal+2017), I/355, I/358
- https://www.pas.rochester.edu/~emamajek/EEM_dwarf_UBVIJHK_colors_Teff.txt
- http://perso.ens-lyon.fr/isabelle.baraffe/BHAC15dir/BHAC15_iso.2mass

## Not checked

- **NASA ADS full text** (HTTP 401, no token) and Google Scholar.
- **VizieR completeness.** The no-`-source` cone truncates server-side. The `I/*` and `II/*` prefix scans (run ≈ 08:00 UTC) missed tables that had returned rows earlier (CatWISE, VHS, DES, Gaia `paramp`). After ~08:00 UTC the Harvard, IDIA, NAO, China-VO and IUCAA mirrors returned header-only answers for large tables, including positive controls (`vizier_spotcheck*.txt`). The `J/*` scans (07:44–07:55) did return the known positives (Kervella, Dal Ponte, SUPERWIDE, Rothermich). The `B/*` scan truncates at B/vsx, which was queried directly. A catalogue with a spectral type could still hide in a table that failed silently.
- SIMBAD `otypes` for the UCD (504 every time).
- Gaia DR3 ESP-UCD flag second digit ("20" vs "2"): only the 0/1/2 quality classes are documented in the text I could reach (gea.esac.esa.int unreachable).
- GSP-Spec flag decoding for the host's [M/H] = +0.34 (stated as an inference only); RAVE DR6 per-pipeline [M/H] tables (not returned by the cone).
- Dupuy & Liu 2012 relations: the PDF was fetched but the table was not extracted; Kirkpatrick+2021, UltracoolSheet and Pecaut & Mamajek were used instead.
- Gyrochronology (no TESS period in Rothermich Table 7); host UVW / BANYAN Σ membership.
- PSF-fit SPHEREx photometry: ours is aperture photometry. Galaxy contamination (VHS J = 19.2 at 3.6″, DES galaxy at 7.8″) inside the 8.25″ aperture was estimated at 5–10 % below 1.3 µm, not modelled.
- Any SPHEREx-team internal catalogue that is not public.
