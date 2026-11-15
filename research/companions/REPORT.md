# Wide co-moving stellar companions to known ultracool dwarfs: Gaia DR3 search

Date: 2026-11-15. Slice: Companions. Everything is under `research/companions/`. No repo code was edited.
Scripts run with `/home/paw/Desktop/ultracool/.venv/bin/python` from `research/companions/`. Heavy queries ran under `nice -n 15`.

## Bottom line

**One pair survives every check and is not in any source we could query:**
**SDSS J134338.74−022044.6 (L0) + UPM J1343−0220 (Gaia DR3 3658413770767688192; G = 12.3, BP−RP = 2.00).**
- Separation 44.1″ = 3,680 au at 83.3 pc.
- Our own 7-epoch, 16-year proper motion for the L0 agrees with the host's Gaia DR3 motion to 1.5 ± 3.5 mas/yr. That is Δv_tan = 0.6 ± 1.4 km/s.
- Its photometric distance (84 ± 6 pc) matches the host's parallax distance (83.3 pc).
- Gaia DR3 has 0 other sources within 1° that match the same PM and parallax windows. Expected chance matches inside 44″: < 1.5 × 10⁻⁴.
- It is a **candidate**, not a confirmed binary. The tangential-velocity error (±1.4 km/s) is larger than the escape speed (0.6–0.75 km/s), so boundness is not tested. We have no RV for the L0, and no spectrum of either object.

Everything else that passed the physical cuts is already known, or its astrometry is too poor to call (details below).
- 71 pairs are flagged in UltracoolSheet itself.
- 19 more are in SIMBAD hierarchies, WDS, El-Badry+2021, SUPERWIDE, Smart+2019 or COCONUTS.
- Three pairs are *catalogued but apparently never studied as UCD systems*:
  - 2MASS J1600−2456 + a cool white dwarf (El-Badry+2021)
  - PSO J130.9+030.1 (El-Badry+2021, SUPERWIDE)
  - 2MASS J2002−1316 (SUPERWIDE)

  These are useful benchmark leads, but **not new discoveries**.
- WISE J235447.80−814044.9 + DZH white dwarf is out of my scope: Main's separate agent owns it. My numbers for it are listed below, after the white-dwarf-mass fix.

## Endpoints (what was reachable)

CDS Strasbourg was unreachable from this host on 2026-11-15 (`raw/endpoint_probe.txt`).
- TAPVizieR and both XMatch hostnames timed out after 20 s; three pyvo attempts also timed out.
- SIMBAD-CDS TAP returned 404.
- ESA Gaia archive timed out.

Used instead (IRSA was not used):
- **Gaia DR3:** GAVO Heidelberg TAP `https://dc.zah.uni-heidelberg.de/tap`, table `gaia.dr3lite`. This is the full DR3 source list with astrometry, photometry, RUWE and RV. Columns are aliased to VizieR names.
  - GAVO times out as soon as PM/parallax filters are added to an upload join. So the 120″ join is spatial only, in chunks of 300, and every cut is applied locally.
  - Exact ADQL: `raw/s01_query.txt`, `raw/s04_query.txt`.
- **VizieR:** CfA mirror `https://vizier.cfa.harvard.edu/viz-bin/asu-tsv`. Every URL is stored next to its result in `raw/lit/*.json`, `raw/selfcheck/*.json` and `raw/targeted_lit.json`.
  - CatWISE2020 (II/365) returned empty resources on this mirror today, even at a known CatWISE source. CatWISE PMs below are therefore the ones copied into UltracoolSheet (`pmra_catwise`), plus the CatWISE 2015.4 positions in UltracoolSheet.
- **SIMBAD:** Harvard mirror TAP `https://simbad.harvard.edu/simbad/sim-tap`.

## Method and numbers

| step | script → output | what | result |
|---|---|---|---|
| 1 | `s01_upload_query.py` → `raw/ucd_upload.csv`, `raw/gaia_pairs_raw.csv` | UltracoolSheet v2.1.0 rows with `pmra/pmdec_formula`, \|μ\| ≥ 50 mas/yr and `dist_formula` (trig or photometric). Position: `ra/dec_20250703_formula` propagated to 2016.0. All Gaia DR3 sources within 120″. | **3,293 UCDs searched**; 187,273 Gaia rows |
| 2 | `s02_cuts.py` → `out/pairs_cut.csv` | (a) \|Δμ\| < max(3σ_comb, 0.1\|μ_UCD\|). (b) Parallax: Gaia ϖ vs UCD trig ϖ within max(3σ, 20 %); or Gaia distance vs UCD photometric distance (with its UltracoolSheet scatter) within max(3σ, 20 %). (c) Projected separation < 10,000 au. (d) Drop the UCD's own counterpart (matched DR3 ID or sep < 2″). Then compute Δv_tan, host mass and v_esc. | 586 pairs, 209 UCDs |
| 2b | same | Bound test: Δv_tan − 2σ < v_esc(M_host + 0.08 M☉, projected sep) | 262 pairs, 132 UCDs |
| 3 | `s04_chance.py` → `out/chance.csv`, `raw/s04_counts.json` | Count Gaia DR3 sources within 1° (0.25° when the PM tolerance > 60 mas/yr) that pass the *same* PM and parallax windows. Expected false = N_field × (sep / R)². Keep < 0.01. | **98 pairs, 95 UCDs** (`out/survivors_all.csv`) |
| 4 | — | UltracoolSheet `has_higher_mass_companion` / `multiplesystem_resolved_in_this_table` ≠ N | 71 pairs (69 UCDs) **known**, flagged in UltracoolSheet |
| 5 | `s05_lit.py` → `raw/lit/*.json` | Remaining 27 pairs (26 UCDs). SIMBAD: both objects' ids, otype, SpT, bibcodes, shared bibcodes, h_link parents/children, Fe/H. El-Badry+2021 by Gaia ID. Rothermich+2024, WDS, Zhang+2021 COCONUTS (J/ApJ/916/53) cones. UltracoolSheet notes mentioning the host. | see table below |
| 6 | `s10_targeted_lit.py` → `raw/targeted_lit.json`; also `raw/smart2019_table5.tsv`, `raw/baron2025_text.txt` | Open pairs, positional 150″ cones on UCD and host: Gálvez-Ortiz+2017 (J/MNRAS/466/2983), Deacon+2014 (J/ApJ/792/119), SLoWPoKES I/II (J/AJ/139/2566, J/AJ/150/57), SUPERWIDE (J/ApJS/247/66), Smart+2019 Table 5 (J/MNRAS/485/4423), El-Badry+2021 (positional), Rothermich+2024, WDS, Gentile Fusillo+2021 WDs. Also full text of Baron+2025 (arXiv:2412.04597) and web searches. | 1 pair with no hit |
| 7 | `s06_selfcheck.py` → `raw/selfcheck/`; `s08_fit_multiepoch.py` → `raw/astrom/multiepoch_fit.txt`; `s09_numbers.py` → `out/numbers.json` | Gaia DR3 re-queried for both objects on the CfA VizieR mirror, a different service from GAVO. 2MASS→Gaia two-epoch PMs. Multi-epoch catalogue-position PM fits for UCDs without Gaia astrometry. | below |

Host masses:
- Mamajek EEM dwarf table, M_G → M☉ by interpolation (`raw/mamajek_EEM_dwarf.txt`, downloaded from pas.rochester.edu).
- **White-dwarf hosts** (BP−RP < 1.6 and M_G > 2.5(BP−RP) + 8, or no BP−RP and M_G > 10): Gentile Fusillo+2021 `MassH` if the source is listed (`raw/gf21_masses.json`). Otherwise 0.6 M☉, or Mamajek if BP−RP is missing and the source is not in GF21.
- This WD branch was **fixed during the run** after Main flagged it. The first version treated WDs with BP−RP ≥ 1.0 as M dwarfs (e.g. 0.086 M☉ for the J2354 DZH WD; GF21 gives 0.457). The fix only raises v_esc. The bound set (262) and the 98 survivors are unchanged (checked). The pre-fix file is kept as `raw/pairs_cut_v1_before_wdfix.csv`.

Shortcuts:
- UCD mass is fixed at 0.08 M☉.
- v_esc uses the *projected* separation. That is the most generous value; it only matters for marginal pairs.
- Gaia DR3 parallax errors were not inflated for faint sources.

## Literature status of the 27 non-UltracoolSheet survivors

| UCD (SpT) | host | sep ″ / au | status | where |
|---|---|---|---|---|
| **SDSS J134338.74−022044.6 (L0)** | UPM J1343−0220 | 44.1 / 3,676 | **no prior report found** | — (all sources in the step 5–6 list, SIMBAD, web) |
| 2MASS J16002647−2456424 (M7.5 pec) | WD Gaia DR3 6236113362117992832 (GF21 WDJ160026.69−245618.65, DZ:) | 24.7 / 1,502 | catalogued (Gaia pair only) | El-Badry+2021 (positional hit; the ID query had returned nothing, see caveats) |
| 2MASS J20025265−1316418 (M8.9 FLD-G) | 2MASS J20024658−1315379 (G 18.4, BP−RP 3.9) | 109 / 6,108 | catalogued | SUPERWIDE (Hartman & Lépine 2020) seq 57112 |
| PSO J130.9+030.1 (M9.4 INT-G) | Gaia DR3 706176328081445888 (G 15.8) | 30.5 / 2,872 | catalogued | El-Badry+2021, SUPERWIDE |
| 2MASS J07202582−5617224 (M5.9 INT-G) | HD 57969 (A1V) | 30.1 / 2,188 | catalogued | El-Badry+2021 |
| 2MASS J11240487+3808054 (M8.5) | RX J1124.1+3808 | 8.2 / 152 | known | WDS RED 23; SIMBAD `RX J1124.1+3808B`; El-Badry |
| 2MASS J23225299−6151275 (L2γ) | 2MASS J23225240−6151114 | 16.5 / 702 | known | Smart+2019 T5; WDS SKF2857; El-Badry |
| CE 507 (M6) | CD−33 13497 | 14.9 / 240 | known | WDS JAO 6; SIMBAD `CD-33 13497B` |
| COCONUTS-3B (L6) | COCONUTS-3A | 61.3 / 1,897 | known | Zhang+2022 (COCONUTS III) |
| DENIS J055146.0−443412 (M8.5) | BLR 1B | 2.4 / 362 | known | WDS BLR 1 |
| L 726-8 (M6) | GJ 65 B | 2.4 / 6 | known | GJ 65 AB |
| LSPM J2331+4607N (d/sdM7) | LSPM J2331+4607S | 4.0 / 604 | known | WDS KPP2694; El-Badry |
| PSO J135.0395+32.0845 (L1.5) | HD 76945 | 61.1 / 4,589 | known | SIMBAD `HD 76945B`; WDS DAM1516 |
| PSO J306.0928−06.6429 (L2.2) | UPM J2024−0638 | 13.4 / 956 | known | WDS WIS 338; El-Badry |
| PSO J330.3214+32.3686 (T2.5) | Wolf 1154 A and B | 77.7 / 2,400 | known | SIMBAD `Wolf 1154 C` |
| SDSS J124514.95+120442.0 (L1) | WD SDSS J124520.60+120531.3 (DA) | 96.4 / 7,847 | known | Smart+2019 Table 5 |
| SDSS J163256.13+350507.2 (L1) | HD 149361 | 57.2 / 1,971 | known | SIMBAD `HD 149361B`; Smart+2019; El-Badry |
| VVV J12564163−6202039 (sdL3) | WD VVV J125644.42−620208.1 | 18.2 / 1,374 | known | Zhang+2024 (MNRAS 533, 1654); El-Badry |
| WISEA J063228.30+264347.3 (M7) | G 103-38 (K5) | 25.7 / 2,133 | catalogued | El-Badry |
| WISEA J124014.80+204752.7 (M7) | BD+21 2442 (K2) | 112.6 / 5,965 | known | WDS OSO 47 AC; SIMBAD `** OSO 47C` |
| WISEA J230743.63+052037.3 (M7) | LP 581-76 | 18.5 / 1,587 | known | WDS SKF2856; El-Badry |
| ULAS J111929.43+002133.1 (L4.5) | UCAC4 452-049871 (G 14.7, M_G 10.6) | 14.0 / 963 | no report found, **co-motion not confirmed** | see below |
| ULAS J093744.66+071903.3 (M9) | WD WDJ093744.35+071910.57 (GF21, 0.72 M☉) | 8.6 / 1,348 | no report found; **UCD PM ±25–29 mas/yr, untestable** | Δv_tan = 17 ± 22 km/s |
| ULAS J104224.20+121206.8 (T7.5) | LP 490-57 | 29.5 / 1,338 | **UCD PM ±80–90 mas/yr, untestable** | Δμ = 164 ± 83 mas/yr; WDS has `WIS 170` at the host position with sep field 999.9 (unclear) |
| ULAS J161934.78+235829.3 (T6) | Gaia DR3 1302018992185488256 | 37.6 / — | **rejected** | host ϖ = 1.26 ± 0.41 mas (≈ 0.8 kpc); it passed only through the wide photometric-distance window |
| WISE J235447.80−814044.9 (T6.4 phot) | WD Gaia DR3 6350786278796634112 (DZH) | 63.8 / 1,718 | Main's separate agent | my numbers: Δμ = 43 ± 24 mas/yr (UCD PM = UCS/CatWISE ±26/23); Δv_tan = 5.5 ± 3.1 km/s vs v_esc 0.74 (GF21 M = 0.457); 0 field matches in 0.25°; no hit in El-Badry, SUPERWIDE, Smart+19, WDS, Rothermich, Gálvez-Ortiz, Deacon (`raw/J2354_targeted_lit.txt`) |

## The new candidate: SDSS J134338.74−022044.6 + UPM J1343−0220

| quantity | UCD: SDSS J134338.74−022044.6 | host: UPM J1343−0220 |
|---|---|---|
| other names | 2MASS J13433872−0220446, ULAS J134338.64−022043.3, EPIC 251551345, Gaia DR3 3658413667689105920 (2-parameter only, G = 20.92) | Gaia DR3 3658413770767688192, 2MASS J13433803−0220006, TIC 270466787 |
| SpT | L0 (optical, West+2008, via UltracoolSheet) | none in SIMBAD; BP−RP = 2.00, M_G = 7.71 |
| G / BP−RP | 20.93 (UCS) / — | 12.32 / 2.00 |
| ϖ or distance | photometric: 84 ± 6 pc (W2, UCS). J: 86 ± 16; Ks: 87 ± 13; J_MKO: 84 ± 15; K_MKO: 90 ± 12 | 12.006 ± 0.082 mas → 83.3 pc |
| PM (mas/yr) | **ours, 7 epochs 2000.1–2016.0** (SDSS ×3, 2MASS, UKIDSS LAS, CatWISE 2015.4, Gaia 2-param): (−140.0 ± 3.5, +120.8 ± 3.5), χ²ᵣ 0.98/0.78. Best+2018: (−139 ± 5, +121 ± 5). CatWISE (UCS): (−141.1 ± 10.9, +133.2 ± 12.1). 2MASS→Gaia two-epoch: (−129.8, +120.4) ± 9.5 | (−140.72 ± 0.10, +122.14 ± 0.06) |
| RUWE / RV | — / — | **6.65** / −49.6 km/s (Gaia DR3) |
| UltracoolSheet | `age_category` Field, 2.5 (+4.3/−2) Gyr; no companion flag | — |

Pair numbers:
- Separation 44.13″ = **3,676 au**.
- Δμ (ours − host) = (0.7, −1.3) mas/yr: **1.5 ± 3.5 mas/yr → Δv_tan = 0.60 ± 1.38 km/s**.
  - With Best+2018: 0.81 ± 1.97 km/s.
  - With CatWISE: 4.4 ± 4.5 km/s.
- v_esc at the projected separation: 0.58 km/s (single 0.62 M☉ host + 0.08 M☉). About 0.75 km/s if the host is an equal-mass pair (see below).
- Parallax: photometric vs Gaia distance, −0.12σ.
- Chance alignment: **0** Gaia DR3 sources within 1° (besides the host) pass |Δμ| < 18.4 mas/yr and 9.80 < ϖ < 15.17 mas. If one had: expected false < (44.13/3600)² = 1.5 × 10⁻⁴.
- Host v_tan = 73.6 km/s; with RV −49.6 km/s the heliocentric space speed is ≳ 89 km/s.

Self-check:
- The host was re-queried on CfA VizieR I/355/gaiadr3 (`raw/selfcheck/SDSS_J134338_74-022044_6.json`): ϖ 12.0064, PM (−140.719, 122.140), RUWE 6.653, identical to GAVO.
- The UCD's Gaia DR3 entry is 2-parameter (no ϖ/PM) at 1.43″ from the PM-propagated position. Its 2016.0 position is the last point of our fit.
- The fit uses only catalogue positions (`raw/astrom/J1343_*.tsv`, UCS CatWISE 2015.4). Per-epoch σ is assumed to be 0.1″. Residuals are ≤ 0.16″ (`raw/astrom/multiepoch_fit.txt`).

Why it is probably physical:
- The motion matches to 1.5 mas/yr over 16 years for a 186 mas/yr mover.
- Four independent photometric distances agree with the host parallax.
- No other Gaia star in 3.1 deg² shares the PM and parallax window.

What it is not yet:
- Boundness is untested: Δv_tan errors exceed v_esc.
- There is no RV for the L0, and no spectrum of the host.

**[INFERENCE]** on the host:
- BP−RP 2.00 corresponds to ~M0.5 on the Mamajek sequence (M_G ≈ 8.44). The host is ~0.7 mag over-luminous for that colour, and it has RUWE 6.65.
- Both point to an unresolved, near-equal-mass binary host. That would make this a hierarchical triple.

What it adds:
- A bright (G = 12.3) M0-ish host at 83 pc whose metallicity can be measured. That gives a metallicity and age anchor for an L0 at the stellar/substellar boundary.
- The L0 is also a K2 target (EPIC 251551345) used in UCD flare and planet-occurrence papers. A metallicity and age for it would feed those statistics.
- The high space velocity (≳ 89 km/s) hints at an old, possibly thick-disk system [INFERENCE].
- Follow-up: RV of the L0, host spectrum ([Fe/H], activity), high-resolution imaging of the host (RUWE).

## Catalogued but uncharacterised (not new, but worth a look)

- **2MASS J16002647−2456424 (M7.5 pec) + WDJ160026.69−245618.65.**
  - The WD is SIMBAD `WD* DZ:` (Vincent+2024 Teff 4237 K, log g 7.91). GF21 gives Teff_H 4359 K, M = 0.571 ± 0.103 M☉.
  - Pair numbers: 24.7″ / 1,502 au. Δμ = 2.55 ± 0.64 mas/yr → Δv_tan = 0.74 ± 0.18 km/s, vs v_esc 0.88. Chance 4.7 × 10⁻⁵. v_tan of the WD: 85.5 km/s.
  - Parallax tension: 17.77 ± 0.4 vs 16.43 ± 0.30 mas (−2.7σ).
  - It is in El-Badry+2021. I found no paper that treats it as a WD+UCD age benchmark (not in Baron+2025, SIMBAD, or the web).
  - SIMBAD also lists AB Dor/Upper Sco "parents" for the UCD, which is inconsistent with an 85 km/s v_tan [INFERENCE: likely spurious kinematic memberships].
- **2MASS J20025265−1316418 (M8.9) + 2MASS J20024658−1315379** (itself a late-M, M_G 14.7).
  - In SUPERWIDE.
  - Marginal: Δv_tan = 0.43 ± 0.15 km/s vs v_esc 0.22; parallax difference 2.9σ.
- **PSO J130.9+030.1 (M9.4 INT-G) + Gaia DR3 706176328081445888**, in El-Badry and SUPERWIDE.
  - Δv_tan = 0.29 ± 0.28 km/s vs v_esc 0.46; ϖ agrees (0.3σ). Chance 7 × 10⁻⁵.

## Unconfirmed: ULAS J111929.43+002133.1 (L4.5) + UCAC4 452-049871

The PM sources disagree:
- Best+2018 (24 ± 12, −55 ± 18) matches the host (18.3, −59.4) mas/yr.
- CatWISE via UltracoolSheet (−28.0 ± 15.5, −43.0 ± 16.6) is 49 mas/yr off (Δv_tan 16 ± 5 km/s).
- Our 4-epoch fit (SDSS 1999.2, UKIDSS 2008.3, PS1 2012.4, CatWISE 2015.4) gives (4.7 ± 13.1, −37.3 ± 13.5), 1.0σ/1.6σ off. That is Δv_tan 8.5 ± 4.3 km/s; χ²ᵣ ≈ 2.6, so the positions scatter by 0.1–0.2″.

Other numbers:
- The photometric distance (59 ± 9 pc) is consistent with the host (68.8 pc, 1.1σ).
- 0 field matches within 1°.
- Not in any checked catalogue.

**Not claimable** until a precise PM exists (the UCD is not in Gaia).

## Caveats

- **ID-based El-Badry lookups on the CfA mirror gave a false negative.** For J1600−2456, `s05_lit.py` (query by Source1/Source2 = host ID) returned nothing, but the positional cone in `s10` found the pair. The CfA mirror also sometimes returned stray MIME text instead of a table; the parser was hardened afterwards. All *open* pairs were therefore re-checked positionally (`s10`).
  - J1343 and J1119 cannot be in El-Badry or SUPERWIDE at all: their UCDs lack Gaia 5-parameter astrometry.
  - For the pairs labelled "known", one positive source is enough, so this does not affect them.
- **Chance estimate.** The count includes the UCD itself if it is in Gaia (conservative). The field PM window is a circle of the pair's own tolerance radius.
- The bound test with *projected* separation is generous. Pairs whose UCD has PM errors ≥ 25 mas/yr (J0937, J1042, J1119, J2354) pass only because the error bars are large.
- The 71 UltracoolSheet-flagged survivors were not individually re-verified. In two of them our Gaia match is a different star of the same known system: HD 33632 Ab (our host is HD 33632 B at 34″) and HD 72946 B (our host is HD 72947 at 10″).

## Not checked

- **NASA ADS full text:** no token, so not available. COCONUTS IV and later papers (Zhang+2024), Marocco+2020 (DES wide UCD binaries; no VizieR code found) and Zhang+2026 "Halo stars harbour few wide ultracool companions" were not opened. They are covered only through SIMBAD bibcodes and web search.
- **CatWISE2020 (II/365) live query:** the CfA mirror was broken today; the UltracoolSheet copies were used instead. Also not checked: CDS XMatch / TAPVizieR (down), the ESA Gaia archive (down), and Gaia DR3 NSS (out of scope).
- **The all-catalogue VizieR cone:** `s07` failed with IncompleteRead on the CfA mirror. Only J2354's UCD and host completed (`raw/vizier_all/`).
- **Physical characterisation:** no RVs for the UCDs, and no spectra or metallicities for the J1343 host (SIMBAD `mesFe_h` is empty).
- UCDs with |μ| < 50 mas/yr or without a distance in UltracoolSheet (597 of 3,890) were not searched.

## Suggested public wording

> Searching the 3,293 fast-moving ultracool dwarfs in the UltracoolSheet against Gaia DR3, we recovered ~90 known wide companions and found one pair we could not find in the literature: the L0 dwarf SDSS J134338.74−022044.6 and the star UPM J1343−0220, 44″ (≈3,700 au) apart at 83 pc. They share the same motion on the sky to within 1.5 ± 3.5 mas/yr over 16 years, and the dwarf's estimated distance matches the star's measured one. It is a strong *candidate* wide binary. Confirmation needs a radial velocity for the L dwarf; the host's metallicity would then make it a benchmark.

Avoid "discovered a new binary" / "confirmed". Say "candidate", "not found in SIMBAD, WDS, El-Badry+2021 or other wide-binary catalogues we queried (ADS full text not searched)".

## Files

- `scripts/s01_upload_query.py` … `s10_targeted_lit.py` (each docstring lists inputs, outputs and URLs)
- `out/pairs_cut.csv`: 586 pairs with all cut quantities
- `out/chance.csv`
- `out/survivors_all.csv`: 98 pairs
- `out/numbers.json`
- `raw/`: every query result (`gaia_pairs_raw.csv`, `lit/`, `selfcheck/`, `astrom/`, `targeted_lit.json`, `smart2019_table5.tsv`, `baron2025_text.txt`, `gf21_masses.json`, `endpoint_probe.txt`)
