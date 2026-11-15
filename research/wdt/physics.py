"""Distance consistency, WD cooling age, T-dwarf Teff/mass, binding and chance alignment for WISE J2354-8140 +
WD J235419.41-814104.96 (Gaia DR3 6350786278796634112).

Run: cd research/wdt && nice -n 15 ../../.venv/bin/python physics.py -> physics_out.json, physics_stdout.txt
Inputs: pm_fit_out.json, vz_gf21_wd.tsv (Gentile Fusillo+2021), lit/wd_paper_rows.txt (O'Brien+2023 Teff/logg/B),
irsa_catwise_2020.tbl, vz_vhsdr5.tsv, gaia_5deg_plx20.tsv, ref/Montreal_Table_Mass_0.{4,5,6} (Bedard+2020 cooling),
ref/evolution_tables/evo_tables+0.0/nc+0.0_co1.0_age (Sonora Bobcat, Marley+2021),
../verification/data/UltracoolSheet_-_Main.csv (UltracoolSheet v2.1.0), ref/kirkpatrick2021_text.txt (Table 13).
"""
import csv
import json
import math
from pathlib import Path

import numpy as np
import astropy.units as u
from astropy.coordinates import SkyCoord

from vztsv import rows

HERE = Path(__file__).resolve().parent
OUT, LOG = {}, []


def p(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.append(s)


def poly(c, x):
    return sum(ci * x**i for i, ci in enumerate(c))


pm = json.load(open(HERE / "pm_fit_out.json"))
WD = pm["WD"]
D_WD = pm["WD_distance_pc"]
SEP_AU = pm["separation_2016"]["au_projected"]
SEP_AS = pm["separation_2016"]["arcsec"]

# ---------------------------------------------------------------- photometry of the T dwarf
cw = [l.split() for l in open(HERE / "irsa_catwise_2020.tbl") if not l.startswith(("\\", "|"))][0]
W1, eW1, W2, eW2 = float(cw[10]), float(cw[11]), float(cw[12]), float(cw[13])  # w1mpro, w1sigmpro, w2mpro, w2sigmpro
vhs = [r for r in rows(HERE / "vz_vhsdr5.tsv") if r["Jperrbits"] == "0" and float(r["pStar"]) > 0.5]
jw = np.array([1 / float(r["e_Jpmag"]) ** 2 for r in vhs])
J = float(np.sum(jw * [float(r["Jpmag"]) for r in vhs]) / jw.sum())
eJ = float(1 / math.sqrt(jw.sum()))
OUT["photometry"] = {"W1_CatWISE": W1, "W2_CatWISE": W2, "W1-W2": round(W1 - W2, 3), "e_W1-W2": round(math.hypot(eW1, eW2), 3),
                     "J_VHS_DR5_mean_of_clean_detections": round(J, 3), "e_J": round(eJ, 3),
                     "J_VHS_individual": [[r["JMJD"], r["Jpmag"], r["e_Jpmag"]] for r in vhs]}

# ---------------------------------------------------------------- Kirkpatrick+2021 Table 13 (ref/kirkpatrick2021_text.txt lines 4246+)
SPT_MCH2 = [1.0071e+01, 1.8897e-01, -6.2186e-02, 1.9711e-02, -2.3844e-03, 1.3230e-04, -3.3136e-06, 2.9971e-08]  # rms 0.31
SPT_MJ = [1.1808e+01, 3.3790e-01, -1.9013e-01, 7.1759e-02, -9.9829e-03, 6.3147e-04, -1.8672e-05, 2.1526e-07]  # rms 0.60
SPT_W1W2 = [2.2668e-01, 2.9069e-02, -4.6379e-03, 5.7825e-04]  # rms 0.28
W1W2_SPT = [-3.9840e+00, 3.4029e+01, -2.5352e+01, 1.0073e+01, -1.9779e+00, 1.5181e-01]  # rms 1.16 subtypes
SPT_TEFF_T = [5.1413e+03, -3.6865e+02, 6.7301e+00]  # 14.75 <= SpT <= 22, rms 79 K
CH2 = 0.070888 + 0.99268 * W2  # W2 -> ch2, rms 0.10


def dist(m, M, rms):
    d = 10 ** ((m - M + 5) / 5)
    return [round(d, 1), round(d * 10 ** (-rms / 5), 1), round(d * 10 ** (rms / 5), 1)]


k21 = {}
for lab, sub in (("T5", 5), ("T6", 6), ("T6.4 (Tinney CH4)", 6.4), ("T7", 7), ("T8", 8), ("T9", 9)):
    x = 10 + sub
    mch2, mj = poly(SPT_MCH2, x), poly(SPT_MJ, x)
    k21[lab] = {"M_ch2": round(mch2, 2), "d_ch2_pc[best,-1sig,+1sig]": dist(CH2, mch2, math.hypot(0.31, 0.10)),
                "M_JMKO": round(mj, 2), "d_J_pc": dist(J, mj, 0.60),
                "Teff_K": round(poly(SPT_TEFF_T, x)), "W1-W2_pred": round(poly(SPT_W1W2, x), 2)}
OUT["K21_distances(W2 CatWISE, J VHS)"] = k21
OUT["K21_SpT_from_W1-W2"] = "T" + str(round(poly(W1W2_SPT, W1 - W2) - 10, 1)) + " (rms 1.16 subtypes)"
# Spitzer photometry from Kirkpatrick+2021 table A1 (lit/vizier_specific_rows.txt: ch1 16.613+-0.040, ch2 15.066+-0.021, SpAd 17.0)
CH1_S, CH2_S = 16.613, 15.066
OUT["K21_Spitzer"] = {"ch1-ch2": round(CH1_S - CH2_S, 3),
                      "SpT_from_ch1-ch2(rms 1.26)": "T" + str(round(poly([5.4614, 21.717, -16.691, 6.1763, -0.81737], CH1_S - CH2_S) - 10, 1)),
                      "d_ch2_pc[best,-1sig,+1sig]": {lab: dist(CH2_S, poly(SPT_MCH2, 10 + sub), 0.31) for lab, sub in
                                                     (("T5", 5), ("T6", 6), ("T6.4", 6.4), ("T7", 7), ("T8", 8))}}
# required absolute magnitude at the WD distance
OUT["at_WD_distance"] = {"M_ch2": round(CH2 - 5 * math.log10(D_WD / 10), 2), "M_J": round(J - 5 * math.log10(D_WD / 10), 2),
                         "K21_SpT_from_M_ch2": "T" + str(round(poly([1.4559e+03, -4.6516e+02, 5.4301e+01, -2.7423e+00, 5.0950e-02],
                                                                     CH2 - 5 * math.log10(D_WD / 10)) - 10, 1)) + " (rms 1.26)"}

# UltracoolSheet empirical (field singles, plx/err > 10): median +- 1.4826 MAD of M_W2 and M_JMKO per integer subtype
ucs = list(csv.DictReader(open(HERE.parent / "verification" / "data" / "UltracoolSheet_-_Main.csv", encoding="utf8")))


def f(r, k):
    try:
        v = float(r[k])
        return v if math.isfinite(v) else None
    except (ValueError, KeyError):
        return None


T0 = next(f(r, "sptnum_formula") for r in ucs if r["name"].startswith(("2MASS J04151954-0935066", "2MASSI J0415195-093506"))) - 8
emp = {}
for sub in range(4, 10):
    mw2, mj = [], []
    for r in ucs:
        s, plx, eplx = f(r, "sptnum_formula"), f(r, "plx_formula"), f(r, "plxerr_formula")
        if s != T0 + sub or plx is None or eplx is None or plx <= 0 or eplx / plx > 0.1:
            continue
        if not (r["multiplesystem_unresolved_in_this_table"] or "N").startswith("N") or r["youth_evidence"] not in ("N", "", "null"):
            continue
        if f(r, "W2") is not None:
            mw2.append(f(r, "W2") + 5 * math.log10(plx / 100))
        if f(r, "J_MKO") is not None:
            mj.append(f(r, "J_MKO") + 5 * math.log10(plx / 100))
    e = {}
    for nm, arr, mag in (("W2", mw2, W2), ("J", mj, J)):
        if len(arr) >= 3:
            med = float(np.median(arr))
            sd = float(1.4826 * np.median(np.abs(np.array(arr) - med)))
            e[nm] = {"n": len(arr), "M_median": round(med, 2), "scatter": round(sd, 2), "d_pc[best,-1sig,+1sig]": dist(mag, med, sd)}
    emp[f"T{sub}"] = e
OUT["UCS_empirical_distances"] = emp

# T dwarf in UltracoolSheet itself (its own distance column)
near = [r for r in ucs if r["name"].startswith("WISE J235447.80")]
OUT["UCS_row"] = {k: near[0][k] for k in ("name", "spt_ir", "spt_opt", "dist_formula", "disterr_formula", "dist_formula_source" if "dist_formula_source" in near[0] else "name", "W1", "W2", "J_MKO")} if near else None

# ---------------------------------------------------------------- WD parameters and cooling age
gf = rows(HERE / "vz_gf21_wd.tsv")[0]
WDP = {"GF21_H": (float(gf["TeffH"]), float(gf["e_TeffH"]), float(gf["loggH"]), float(gf["MassH"]), float(gf["e_MassH"])),
       "GF21_He": (float(gf["TeffHe"]), float(gf["e_TeffHe"]), float(gf["loggHe"]), float(gf["MassHe"]), float(gf["e_MassHe"]))}
OUT["WD_params"] = {k: dict(zip(("Teff", "e_Teff", "logg", "mass", "e_mass"), v)) for k, v in WDP.items()}
OUT["WD_params"]["OBrien2023_photometric"] = {"Teff": 4480, "e_Teff": 40, "logg": 7.77, "e_logg": 0.04, "B_MG": "0.6 +- 0.2",
                                              "note": "DZH; spectrum not fitted (Zeeman-split Ca II); lit/wd_paper_rows.txt"}


def montreal(mass_str, atm):
    """Teff, logg, age arrays from a Bedard+2020 Table_Mass file; atm 'H' (first block) or 'He' (second block)."""
    lines = open(HERE / "ref" / f"Montreal_Table_Mass_{mass_str}").read().splitlines()
    starts = [i for i, l in enumerate(lines) if "grid" in l]
    i0 = starts[0 if atm == "H" else 1]
    i1 = starts[1] if atm == "H" else len(lines)
    data = []
    for l in lines[i0 + 2:i1]:
        x = l.split()
        if len(x) > 40 and x[0][0].isdigit():
            data.append((float(x[0]), float(x[1]), float(x[-1])))
    return np.array(data)


def cool_age(teff, mass, atm):
    ages = {}
    for ms in ("0.4", "0.5", "0.6"):
        d = montreal(ms, atm)
        d = d[np.argsort(d[:, 0])]
        ages[float(ms)] = float(np.interp(teff, d[:, 0], d[:, 2]))
    ms = sorted(ages)
    return float(np.interp(mass, ms, [ages[m] for m in ms])) / 1e9


cool = {}
for k, (teff, et, lg, m, em) in WDP.items():
    atm = "He" if "He" in k else "H"
    em_eff = max(em, 0.03)  # GF21 mass errors (0.0007-0.016) are statistical only; 0.03 Msun systematic floor
    a = cool_age(teff, m, atm)
    grid = [cool_age(teff + dt, m + dm, atm) for dt in (-et, et) for dm in (-em_eff, em_eff)]
    cool[k] = {"age_Gyr": round(a, 2), "range_Gyr": [round(min(grid), 2), round(max(grid), 2)], "mass_err_used": em_eff}
OUT["WD_cooling_age_Bedard2020"] = cool
# O'Brien+2024 tablea1 (lit/vizier_specific_rows.txt): uncorrected H fit = GF21; ad-hoc low-mass correction for Teff < 6000 K
# (their Sect. 2, ref/obrien2024_2312.02735.txt): Teff_c 4676 K, M_c 0.594, cooling age_c 7.76 Gyr
OUT["WD_params"]["OBrien2024_corrected"] = {"Teff": 4676, "mass": 0.594, "cooling_age_Gyr": 7.76, "uncorrected": [4476, 0.457]}
# Cummings+2018 IFMR (MIST), valid M_i 0.83-2.85: M_f = 0.080 M_i + 0.489 -> M_f >= 0.556 for any single-star progenitor
ifmr = {}
for lab, mf, tcool in (("uncorrected GF21 H 0.457", 0.457, cool["GF21_H"]["age_Gyr"]), ("uncorrected GF21 He 0.480", 0.480, cool["GF21_He"]["age_Gyr"]),
                       ("OBrien corrected 0.594-0.03", 0.564, 7.76), ("OBrien corrected 0.594", 0.594, 7.76), ("OBrien corrected 0.594+0.03", 0.624, 7.76)):
    mi = (mf - 0.489) / 0.080
    if mi < 0.83:
        ifmr[lab] = {"M_i": None, "note": "below Cummings+2018 IFMR range: no single-star progenitor younger than the Galaxy; "
                                          "progenitor lifetime unconstrained -> cooling age is a LOWER LIMIT on the system age"}
        continue
    # shortcut: main-sequence+giant lifetime ~ 10 Gyr (M/Msun)^-2.5 (textbook scaling, ~20-30% accuracy); upgrade = MIST tracks
    t_pre = 10 * mi ** -2.5
    ifmr[lab] = {"M_i": round(mi, 2), "t_pre_WD_Gyr(approx)": round(t_pre, 1), "t_cool_Gyr": tcool, "total_Gyr": round(t_pre + tcool, 1)}
OUT["IFMR_total_age"] = ifmr

# ---------------------------------------------------------------- T dwarf mass from Sonora Bobcat at the WD age
evo = HERE / "ref" / "evolution_tables" / "evo_tables+0.0" / "nc+0.0_co1.0_age"
blocks, cur = {}, None
for l in open(evo):
    x = l.split()
    if len(x) == 6 and x[0][0].isdigit():
        blocks.setdefault(float(x[0]), []).append((float(x[1]), float(x[3])))
OUT["sonora_ages_Gyr"] = sorted(blocks)


def bd_mass(teff, age):
    ag = sorted(blocks)
    res = []
    for a in ag:
        d = np.array(blocks[a])
        d = d[np.argsort(d[:, 1])]
        res.append(float(np.interp(teff, d[:, 1], d[:, 0])))
    return float(np.interp(age, ag, res)) * 1047.57  # Mjup


mass = {}
for lab, sub in (("T6.4", 6.4), ("T5", 5), ("T8", 8)):
    teff = poly(SPT_TEFF_T, 10 + sub)
    mass[lab] = {"Teff_K": round(teff), "Teff_range": [round(teff - 79), round(teff + 79)]}
    for age in (4.0, 6.0, 8.0, 10.0):
        mass[lab][f"M_Jup@{age:g}Gyr"] = [round(bd_mass(teff, age), 1), round(bd_mass(teff - 79, age), 1), round(bd_mass(teff + 79, age), 1)]
OUT["T_dwarf_mass_Sonora_Bobcat[best,Teff-79,Teff+79]"] = mass

# ---------------------------------------------------------------- binding
G = 6.674e-11
MSUN, AU = 1.989e30, 1.496e11
m_wd = 0.47
m_bd = 0.05
mtot = m_wd + m_bd
vesc = math.sqrt(2 * G * mtot * MSUN / (SEP_AU * AU)) / 1000
vcirc = vesc / math.sqrt(2)
OUT["binding"] = {"M_total_Msun": mtot, "sep_projected_au": SEP_AU, "v_esc_kms_at_projected_sep": round(vesc, 3),
                  "v_circ_kms": round(vcirc, 3), "v_esc_masyr": round(vesc / 4.74047 / D_WD * 1000, 2),
                  "orbital_period_kyr_if_a=sep": round(math.sqrt((SEP_AU) ** 3 / mtot) / 1000, 1),
                  "binding_energy_erg": float("%.2e" % (G * m_wd * MSUN * m_bd * MSUN / (SEP_AU * AU) * 1e7))}
cmb = pm["vs_WD"]["COMBINED: ours WISE+VHS+SPHEREx"]
OUT["binding"]["dvtan_combined_kms"] = [cmb["dvtan_kms_at_WD_distance"], cmb["e_dvtan_kms"]]
OUT["binding"]["dvtan_2sigma_upper_kms"] = cmb["dvtan_2sigma_upper_kms"]
OUT["binding"]["verdict"] = ("measured dv_tan is consistent with 0 and with v_esc; its error (%.1f km/s) is %.0fx v_esc, so boundness "
                             "is neither shown nor excluded" % (cmb["e_dvtan_kms"], cmb["e_dvtan_kms"] / vesc))

# ---------------------------------------------------------------- chance alignment
g = rows(HERE / "gaia_5deg_plx20.tsv")
c0 = SkyCoord(358.70015 * u.deg, -81.67908 * u.deg)
best = pm["estimates"]["COMBINED: ours WISE+VHS+SPHEREx"]
R_DEG = 5.0
N_UCD = 3293  # rows in research/companions/raw/ucd_upload.csv (UCDs searched by our companion pipeline), look-elsewhere factor
area = 2 * math.pi * (1 - math.cos(math.radians(R_DEG))) * (180 / math.pi) ** 2
circle = math.pi * (SEP_AS / 3600) ** 2
chance = {"field_radius_deg": R_DEG, "field_area_deg2": round(area, 2), "n_gaia_plx_gt20": len(g)}
for nm, plx_lo, plx_hi, nsig in (("plx 30-59 mas (T dwarf phot. d 17-33 pc), PM within 2 sigma", 30.3, 58.8, 2),
                                  ("plx 25-100 mas (d < 40 pc), PM within 3 sigma", 25, 100, 3),
                                  ("plx > 20 mas, any PM", 20, 1e9, None)):
    n = 0
    hits = []
    for r in g:
        if not r.get("Plx") or r["Source"] == "6350786278796634112":  # the candidate host itself is not "field"
            continue
        plx = float(r["Plx"])
        if not (plx_lo <= plx <= plx_hi):
            continue
        if nsig is not None:
            if not r.get("pmRA"):
                continue
            da, dd = float(r["pmRA"]) - best["pmra"], float(r["pmDE"]) - best["pmdec"]
            if (da / best["e_pmra"]) ** 2 + (dd / best["e_pmdec"]) ** 2 > nsig**2:
                continue
        n += 1
        hits.append([r["Source"], r["Plx"], r["pmRA"], r["pmDE"], r["_r"]])
    # n = 0 -> use 1 as a conservative upper bound on the field density
    rate = max(n, 1) * circle / area
    chance[nm] = {"n_excluding_WD": n, "expected_within_sep_per_UCD": float("%.2e" % rate),
                  "expected_in_whole_search(N_UCD=3293)": round(rate * N_UCD, 3), "sources": hits if nsig else None}
OUT["chance_alignment"] = chance
for k, v in OUT.items():
    p(k, json.dumps(v))
json.dump(OUT, open(HERE / "physics_out.json", "w"), indent=1)
open(HERE / "physics_stdout.txt", "w").write("\n".join(LOG) + "\n")
