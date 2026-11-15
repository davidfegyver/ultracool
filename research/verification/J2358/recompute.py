"""Independent recomputation for the J2358-5218 adversarial review (companionship, colours, absolute magnitudes, distance).

Run: nice -n 15 /home/paw/Desktop/ultracool/.venv/bin/python research/verification/J2358/recompute.py
Inputs (all saved next to this script): gaia_dr3_{ucd,host}.tsv, gaia_paramp_{ucd,host}.tsv, gaia_twins_10deg.tsv
(VizieR I/355 via the Harvard mirror, see queries.sh), vizier_specific.txt (CatWISE II/365, AllWISE II/328, 2MASS II/246,
VHS DR5 II/367, DES DR2 II/371), EEM_dwarf_UBVIJHK_colors_Teff.txt (Pecaut & Mamajek, v2022.04.16),
UltracoolSheet v2.1.0 (research/discovery/ext/ultracoolsheet_v2.1.0_main.csv), SPIFF table (backend/app/data/ucd_catalog.csv).
"""
import csv
import json
import math
from pathlib import Path

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord

import vztsv

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = {}


def one(path):
    rows = [r for t in vztsv.read(HERE / path).values() for r in t]
    return min(rows, key=lambda r: float(r["_r"]))


def fl(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


U, H = one("gaia_dr3_ucd.tsv"), one("gaia_dr3_host.tsv")
UP, HP = one("gaia_paramp_ucd.tsv"), one("gaia_paramp_host.tsv")
spec = vztsv.read_sections(HERE / "vizier_specific.txt")
near = {k: min(v, key=lambda r: float(r["_r"])) for k, v in spec.items() if v}
CW, AW, TM, VHS, DES = (near[k] for k in ("II/365/catwise", "II/328/allwise", "II/246/out", "II/367/vhs_dr5", "II/371/des_dr2"))
assert float(CW["_r"]) < 1 and float(TM["_r"]) < 3 and float(VHS["_r"]) < 1.5 and float(DES["_r"]) < 1

# ---- Gaia DR3 astrometry ----------------------------------------------------------------------------------------
g = {n: {k: fl(r[k]) for k in ("Plx", "e_Plx", "pmRA", "e_pmRA", "pmDE", "e_pmDE", "Gmag", "BPmag", "RPmag", "RUWE", "epsi", "sepsi", "RV", "e_RV")}
     for n, r in (("ucd", U), ("host", H))}
for n, r in (("ucd", U), ("host", H)):
    g[n].update(source=r["Source"], ra=float(r["RA_ICRS"]), dec=float(r["DE_ICRS"]), NSS=r["NSS"], IPDfmp=r["IPDfmp"], VarFlag=r.get("VarFlag"))
OUT["gaia_dr3"] = g
OUT["gaia_espucd_ucd"] = {"teff_espucd": fl(UP.get("Teff-UCD")), "err": fl(UP.get("e_Teff-UCD")), "flags_espucd": UP.get("Flags-UCD")}
OUT["gaia_host_ap"] = {k: HP.get(k) for k in ("Teff", "logg", "[Fe/H]", "Teff-S", "logg-S", "[M/H]-S", "[alpha/Fe]-S", "Flags-S", "SpType-ELS",
                                              "Mass-Flame", "b_Mass-Flame", "B_Mass-Flame", "Age-Flame", "b_Age-Flame", "B_Age-Flame", "EWHa", "Rad", "Lum-Flame")}

u_, h_ = g["ucd"], g["host"]
dpa, dpd = u_["pmRA"] - h_["pmRA"], u_["pmDE"] - h_["pmDE"]
epa, epd = math.hypot(u_["e_pmRA"], h_["e_pmRA"]), math.hypot(u_["e_pmDE"], h_["e_pmDE"])
dplx, eplx = u_["Plx"] - h_["Plx"], math.hypot(u_["e_Plx"], h_["e_Plx"])
d_host = 1000 / h_["Plx"]
cu, ch = SkyCoord(u_["ra"] * u.deg, u_["dec"] * u.deg), SkyCoord(h_["ra"] * u.deg, h_["dec"] * u.deg)  # both Gaia ep 2016.0
sep = cu.separation(ch).arcsec
M_HOST, M_UCD = 0.69, 0.08  # Rothermich+2024 Table 10 (host 0.69, companion 0.08 Msun)
v_esc = 29.78 * math.sqrt(2 * (M_HOST + M_UCD) / (sep * d_host))
k = 4.74047 / h_["Plx"]  # km/s per mas/yr at the host distance
chi2 = (dpa / epa) ** 2 + (dpd / epd) ** 2
OUT["companion_gaia"] = {
    "dmu_ra": round(dpa, 3), "dmu_dec": round(dpd, 3), "err": [round(epa, 2), round(epd, 2)], "chi2_2dof": round(chi2, 4),
    "p_2dof": round(math.exp(-chi2 / 2), 4), "dplx": round(dplx, 2), "dplx_err": round(eplx, 2), "dplx_sigma": round(dplx / eplx, 2),
    "sep_arcsec_ep2016": round(sep, 2), "proj_sep_au": round(sep * d_host), "host_dist_pc": round(d_host, 2),
    "ucd_dist_pc_own_plx": [round(1000 / u_["Plx"], 1), round(1000 / (u_["Plx"] + u_["e_Plx"]), 1), round(1000 / (u_["Plx"] - u_["e_Plx"]), 1)],
    "v_tan_host_kms": round(k * math.hypot(h_["pmRA"], h_["pmDE"]), 2),
    "dv_tan_kms": round(k * math.hypot(dpa, dpd), 3), "dv_tan_err_kms_per_axis": round(k * max(epa, epd), 2),
    "v_esc_kms_at_proj_sep(Mtot=0.77)": round(v_esc, 3), "v_esc_masyr": round(v_esc / k, 2),
    "note": "Gaia PM error (2.1 mas/yr ~ 0.8 km/s) is comparable to v_esc: data are consistent with a bound pair but cannot prove binding.",
}

# ---- PM of the UCD from other sources vs Gaia ---------------------------------------------------------------------
pms = {
    "Gaia DR3": (u_["pmRA"], u_["pmDE"], u_["e_pmRA"], u_["e_pmDE"]),
    "CatWISE2020 II/365 (offset-corrected)": (1000 * float(CW["pmRA"]), 1000 * float(CW["pmDE"]), 1000 * float(CW["e_pmRA"]), 1000 * float(CW["e_pmDE"])),
    "ours (dev /summary, stat only)": (115.69, -5.50, 13.54, 13.54),  # dev_summary_now.json motion
}
OUT["ucd_pm_vs_host"] = {n: {"pm": [round(a, 1), round(b, 1)], "err": [round(ea, 1), round(eb, 1)],
                             "sigma_vs_host": [round((a - h_["pmRA"]) / ea, 2), round((b - h_["pmDE"]) / eb, 2)]}
                         for n, (a, b, ea, eb) in pms.items()}

# ---- chance alignment: Gaia DR3 'kinematic twins' within 10 deg -----------------------------------------------------
tw = [r for t in vztsv.read(HERE / "gaia_twins_10deg.tsv").values() for r in t]
src_excl = {u_["source"], h_["source"]}
cap_deg2 = 2 * math.pi * (1 - math.cos(math.radians(10))) * (180 / math.pi) ** 2
ca = {"query": "I/355/gaiadr3, 10 deg around host, Plx 7..19, pmRA 83.8..123.8, pmDE -13.9..26.1", "n_rows": len(tw), "area_deg2": round(cap_deg2, 1)}
for dmu in (5, 10, 20):
    sel = [r for r in tw if r["Source"] not in src_excl and math.hypot(float(r["pmRA"]) - h_["pmRA"], float(r["pmDE"]) - h_["pmDE"]) < dmu
           and abs(float(r["Plx"]) - u_["Plx"]) < 3 * u_["e_Plx"]]
    rho = len(sel) / cap_deg2
    lam = rho * math.pi * (sep / 3600) ** 2
    ca[f"|dmu|<{dmu}mas/yr & |plx-11.98|<4.3"] = {"n": len(sel), "per_deg2": round(rho, 3), "expected_within_sep": float(f"{lam:.2e}")}
# same question from the host's point of view: any star this bright/faint is irrelevant, the PM+plx match is what matters
OUT["chance_alignment"] = ca

# ---- photometry + absolute magnitudes vs Pecaut & Mamajek (2022.04.16) -----------------------------------------------
phot = {"G": u_["Gmag"], "RP": u_["RPmag"], "BP": u_["BPmag"], "J_2MASS": float(TM["Jmag"]), "H_2MASS": float(TM["Hmag"]), "Ks_2MASS": float(TM["Kmag"]),
        "J_VHS": float(VHS["Jpmag"]), "H_VHS": float(VHS["Hpmag"]), "Ks_VHS": float(VHS["Kspmag"]),
        "W1_CatWISE": float(CW["W1mproPM"]), "W2_CatWISE": float(CW["W2mproPM"]), "W1_AllWISE": float(AW["W1mag"]), "W2_AllWISE": float(AW["W2mag"]),
        "i_DES": float(DES["imagPSF"]), "z_DES": float(DES["zmagPSF"]), "Y_DES": float(DES["YmagPSF"])}
OUT["ucd_photometry"] = phot
col = {"G-RP": phot["G"] - phot["RP"], "G-J(2MASS)": phot["G"] - phot["J_2MASS"], "J-H(2MASS)": phot["J_2MASS"] - phot["H_2MASS"],
       "H-Ks(2MASS)": phot["H_2MASS"] - phot["Ks_2MASS"], "J-Ks(2MASS)": phot["J_2MASS"] - phot["Ks_2MASS"], "J-Ks(VHS)": phot["J_VHS"] - phot["Ks_VHS"],
       "W1-W2(CatWISE)": phot["W1_CatWISE"] - phot["W2_CatWISE"], "W1-W2(AllWISE)": phot["W1_AllWISE"] - phot["W2_AllWISE"],
       "Ks-W1(2MASS,CatWISE)": phot["Ks_2MASS"] - phot["W1_CatWISE"]}
OUT["ucd_colours"] = {k: round(v, 3) for k, v in col.items()}
dm_host = 5 * math.log10(100 / h_["Plx"])
dm_own = 5 * math.log10(100 / u_["Plx"])
dm_own_err = 5 / math.log(10) * u_["e_Plx"] / u_["Plx"]
absm = {"M_G": phot["G"], "M_J(2MASS)": phot["J_2MASS"], "M_Ks(2MASS)": phot["Ks_2MASS"], "M_W2(CatWISE)": phot["W2_CatWISE"]}
OUT["ucd_absmag_host_plx"] = {k: round(v - dm_host, 2) for k, v in absm.items()}
OUT["ucd_absmag_own_plx"] = {k: [round(v - dm_own, 2), round(dm_own_err, 2)] for k, v in absm.items()}

eem = {}
for line in open(HERE / "EEM_dwarf_UBVIJHK_colors_Teff.txt"):
    p = line.split()
    if p and p[0] in ("M6V", "M7V", "M8V", "M8.5V", "M9V", "M9.5V", "L0V", "L1V", "L2V", "L3V", "K4V", "K5V", "K6V", "K7V"):
        if p[0] in eem:
            continue
        d = dict(zip(["SpT", "Teff", "logT", "BCv", "logL", "Mbol", "R", "Mv", "B-V", "Bt-Vt", "G-V", "Bp-Rp", "G-Rp", "M_G", "b-y", "U-B", "V-Rc", "V-Ic",
                      "V-Ks", "J-H", "H-Ks", "M_J", "M_Ks", "Ks-W1", "W1-W2"], p))
        e = {k: fl(v) for k, v in d.items() if k != "SpT"}
        if e["M_Ks"] is not None and e["Ks-W1"] is not None and e["W1-W2"] is not None:
            e["M_W2"] = round(e["M_Ks"] - e["Ks-W1"] - e["W1-W2"], 2)
        if e["M_G"] is not None and e["M_J"] is not None:
            e["G-J"] = round(e["M_G"] - e["M_J"], 2)
        eem[p[0]] = {k: e[k] for k in ("Teff", "M_G", "G-Rp", "Bp-Rp", "M_J", "M_Ks", "M_W2", "G-J", "J-H", "H-Ks", "W1-W2") if k in e}
OUT["EEM_table_rows"] = eem


def nearest_types(val, key, tol):
    return [s for s, e in eem.items() if s[0] in "ML" and e.get(key) is not None and abs(e[key] - val) <= tol]


ah = OUT["ucd_absmag_host_plx"]
OUT["EEM_types_within_tol"] = {
    "M_G (tol 0.3)": nearest_types(ah["M_G"], "M_G", 0.3), "M_J (tol 0.3)": nearest_types(ah["M_J(2MASS)"], "M_J", 0.3),
    "M_Ks (tol 0.3)": nearest_types(ah["M_Ks(2MASS)"], "M_Ks", 0.3), "M_W2 (tol 0.3)": nearest_types(ah["M_W2(CatWISE)"], "M_W2", 0.3),
    "G-J (tol 0.15)": nearest_types(col["G-J(2MASS)"], "G-J", 0.15), "J-H (tol 0.1)": nearest_types(col["J-H(2MASS)"], "J-H", 0.1),
    "Teff_espucd (1 sigma)": [s for s, e in eem.items() if s[0] in "ML" and abs(e["Teff"] - OUT["gaia_espucd_ucd"]["teff_espucd"]) <= OUT["gaia_espucd_ucd"]["err"]],
}
# host
OUT["host_absmag"] = {"M_G": round(h_["Gmag"] - dm_host, 2), "BP-RP": round(h_["BPmag"] - h_["RPmag"], 3),
                      "EEM_type_by_BP-RP": min((s for s in eem if s[0] == "K"), key=lambda s: abs(eem[s]["Bp-Rp"] - (h_["BPmag"] - h_["RPmag"]))),
                      "EEM_type_by_M_G": min((s for s in eem if s[0] == "K"), key=lambda s: abs(eem[s]["M_G"] - (h_["Gmag"] - dm_host)))}

# ---- UltracoolSheet: membership + empirical field-single loci ------------------------------------------------------
rows = list(csv.DictReader(open(REPO / "research/discovery/ext/ultracoolsheet_v2.1.0_main.csv", encoding="utf8")))
ra = np.array([fl(r["ra_j2000_formula"]) or np.nan for r in rows]); de = np.array([fl(r["dec_j2000_formula"]) or np.nan for r in rows])
ok = np.isfinite(ra) & np.isfinite(de)
s_ucs = SkyCoord(ra[ok] * u.deg, de[ok] * u.deg).separation(cu).arcsec
OUT["UltracoolSheet_nearest"] = {"name": rows[int(np.flatnonzero(ok)[np.argmin(s_ucs)])]["name"], "sep_arcsec": round(float(s_ucs.min()), 1), "n_rows": len(rows)}
spiff = list(csv.DictReader(open(REPO / "backend/app/data/ucd_catalog.csv", encoding="utf8")))
sc = SkyCoord([r["ra_j2000"] for r in spiff], [r["dec_j2000"] for r in spiff], unit=(u.hourangle, u.deg))
s_sp = sc.separation(cu).arcsec
OUT["SPIFF_nearest"] = {"designation": spiff[int(np.argmin(s_sp))]["designation"], "sep_arcsec": round(float(s_sp.min()), 1), "n_rows": len(spiff)}


def single_field(r):
    return (r["multiplesystem_unresolved_in_this_table"] or "N").startswith("N") and r["youth_evidence"] in ("N", "", "null")


loci = {}
for r in rows:
    s, plx, eplx = fl(r["sptnum_formula"]), fl(r["plx_formula"]), fl(r["plxerr_formula"])
    if s is None or s != int(s) or not 6 <= s <= 13 or plx is None or eplx is None or plx <= 0 or eplx / plx > 0.1 or not single_field(r):
        continue
    dm = 5 * math.log10(100 / plx)
    G, J, Ks, W1, W2, RP = (fl(r[c]) for c in ("G_Gaia", "J_2MASS", "Ks_2MASS", "W1", "W2", "RP_Gaia"))
    e = loci.setdefault(("M" if s < 10 else "L") + str(int(s % 10)), {k: [] for k in ("M_W2", "M_G", "M_J", "G-J", "J-Ks", "W1-W2", "G-RP")})
    for key, v in (("M_W2", W2 and W2 - dm), ("M_G", G and G - dm), ("M_J", J and J - dm), ("G-J", G and J and G - J), ("J-Ks", J and Ks and J - Ks),
                   ("W1-W2", W1 and W2 and W1 - W2), ("G-RP", G and RP and G - RP)):
        if v is not None:
            e[key].append(v)
ucd_val = {"M_W2": ah["M_W2(CatWISE)"], "M_G": ah["M_G"], "M_J": ah["M_J(2MASS)"], "G-J": col["G-J(2MASS)"], "J-Ks": col["J-Ks(2MASS)"],
           "W1-W2": col["W1-W2(CatWISE)"], "G-RP": col["G-RP"]}
tab = {}
for t, e in sorted(loci.items(), key=lambda kv: (kv[0][0] == "L", kv[0])):
    tab[t] = {}
    for key, v in e.items():
        if len(v) >= 5:
            v = np.array(v); med = float(np.median(v)); mad = float(1.4826 * np.median(np.abs(v - med)))
            tab[t][key] = [round(med, 2), round(mad, 2), len(v), round((ucd_val[key] - med) / mad, 1) if mad else None]
OUT["UCS_field_single_loci [median, robust sd, n, (ucd-median)/sd]"] = tab

# ---- spectrophotometric distance --------------------------------------------------------------------------------------
w2 = phot["W2_CatWISE"]
dist = {}
for t in ("M9", "L0", "L1"):
    m, sd = tab[t]["M_W2"][0], tab[t]["M_W2"][1]
    dist[f"UCS {t}"] = [round(10 ** ((w2 - m + 5) / 5), 1), round(10 ** ((w2 - m - sd + 5) / 5), 1), round(10 ** ((w2 - m + sd + 5) / 5), 1)]
for t in ("M9V", "M9.5V", "L0V", "L1V"):
    dist[f"EEM {t}"] = round(10 ** ((w2 - eem[t]["M_W2"] + 5) / 5), 1)
# Kirkpatrick+2021 Table 13 (copied from research/verification/recompute.py): SpT->M_ch2 (L0=0; valid L0 and later), W2->ch2
K21_SPT_MCH2 = [1.0071e+01, 1.8897e-01, -6.2186e-02, 1.9711e-02, -2.3844e-03, 1.3230e-04, -3.3136e-06, 2.9971e-08]
ch2 = 0.070888 + 0.99268 * w2
for x, t in ((0, "L0"), (1, "L1")):
    m = sum(c * x**i for i, c in enumerate(K21_SPT_MCH2))
    d = 10 ** ((ch2 - m + 5) / 5)
    dist[f"K21 {t} (rms 0.31)"] = [round(d, 1), round(d * 10 ** (-0.31 / 5), 1), round(d * 10 ** (0.31 / 5), 1)]
dist["host_gaia_pc"] = round(d_host, 2)
dist["ucd_own_gaia_pc"] = OUT["companion_gaia"]["ucd_dist_pc_own_plx"]
OUT["spectrophotometric_distance_pc [d, lo, hi]"] = dist
# Rothermich-style estimate: M_W2 at host parallax (K21 relations do not reach M9; we compare with UCS loci above)
OUT["M_W2_at_host_plx"] = round(w2 - dm_host, 2)

print(json.dumps(OUT, indent=1, ensure_ascii=False))
json.dump(OUT, open(HERE / "recompute_out.json", "w"), indent=1, ensure_ascii=False)
