"""Independent recomputation for the J2317-6700 adversarial review.

Run: nice -n 15 /home/paw/Desktop/ultracool/.venv/bin/python research/verification/recompute.py
Inputs: data/UltracoolSheet_-_Main.csv (Zenodo 15802304, v2.1.0), backend/app/data/ucd_catalog.csv,
/data/research/discovery/out/J2317-6700.json and prod_J2317_summary.json; catalogue numbers hard-coded
below are copied from the query outputs saved next to this script (catwise.tbl, catwise_vizier_target.tsv,
vizier_hits_rows.txt, vhs_dr5_target.tsv, simbad_object.txt).
"""
import csv
import json
import math
from pathlib import Path

import numpy as np
from astropy.coordinates import SkyCoord
import astropy.units as u

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = {}

# ---- target (CatWISE2020, epoch 2015.4; catwise.tbl) -------------------------------------------
T_RA, T_DEC = 349.3703834, -67.0003097
W1_CW, W1E_CW, W2_CW, W2E_CW = 17.120, 0.046, 15.295, 0.028          # catwise.tbl w?mpro
W1_AW, W1E_AW, W2_AW, W2E_AW = 17.222, 0.107, 15.222, 0.067          # AllWISE II/328
FW1_UW, FW1E_UW, FW2_UW, FW2E_UW = 148.27, 6.08, 774.15, 24.75       # unWISE II/363 (Vega nanomaggies)
J_VHS, JE_VHS, KS_VHS, KSE_VHS = 16.9814, 0.0354, 17.1204, 0.2294    # VHS DR5 II/367 pmag
JKS_PNT, JKSE_PNT = -0.2514, 0.1215                                   # VHS DR5 J-Kspnt

PM = {  # mas/yr (pmra*, pmdec), errors
    "ours_visit": (419.1, -235.9, 30.0, 30.0),       # REPORT (22.4 stat + 20 sys)
    "ours_deep": (415.3, -247.6, 31.0, 31.0),
    "ours_allpoints_incl_SPHEREx": (414.0, -243.9, 18.9, 18.9),  # J2317-6700.json fit_all (stat only)
    "production": (431.0, -251.3, 22.9, 22.9),
    "CatWISE_IRSA_uncorrected": (462.14, -298.81, 31.0, 29.2),
    "CatWISE_VizieR_corrected(=Rothermich)": (436.56, -288.17, 31.0, 29.2),
}
HOSTS = {  # SIMBAD basic (Gaia DR3)
    "HD 219509 (GJ 4321)": (349.3366964, -66.9193151, 363.824, -410.031, 35.1409),
    "HD 219495 (GJ 4322)": (349.3223198, -66.9378991, 354.926, -407.115, 35.1521),
}


def mag_err_from_flux(f, e):
    return 2.5 / math.log(10) * e / f


# ---- 3. colours --------------------------------------------------------------------------------
w1_uw = 22.5 - 2.5 * math.log10(FW1_UW)
w2_uw = 22.5 - 2.5 * math.log10(FW2_UW)
col = {
    "CatWISE": (W1_CW - W2_CW, math.hypot(W1E_CW, W2E_CW)),
    "AllWISE": (W1_AW - W2_AW, math.hypot(W1E_AW, W2E_AW)),
    "unWISE": (w1_uw - w2_uw, math.hypot(mag_err_from_flux(FW1_UW, FW1E_UW), mag_err_from_flux(FW2_UW, FW2E_UW))),
    "ours_research": (2.080, 0.118),
    "ours_production": (2.187, 0.113),
}
OUT["W1-W2"] = {k: [round(v[0], 3), round(v[1], 3)] for k, v in col.items()}
OUT["J-W2 (VHS J, CatWISE W2)"] = [round(J_VHS - W2_CW, 3), round(math.hypot(JE_VHS, W2E_CW), 3)]
OUT["J-Ks VHS pmag"] = [round(J_VHS - KS_VHS, 3), round(math.hypot(JE_VHS, KSE_VHS), 3)]
OUT["J-Ks VHS pnt"] = [JKS_PNT, JKSE_PNT]

# ---- UltracoolSheet: is J2317 in it? empirical M_W2 / colours per subtype ------------------------
rows = list(csv.DictReader(open(HERE / "data" / "UltracoolSheet_-_Main.csv", encoding="utf8")))


def f(r, k):
    try:
        v = float(r[k])
        return v if math.isfinite(v) else None
    except (ValueError, KeyError):
        return None


ra = np.array([f(r, "ra_j2000_formula") or np.nan for r in rows])
de = np.array([f(r, "dec_j2000_formula") or np.nan for r in rows])
ok = np.isfinite(ra) & np.isfinite(de)
sep = SkyCoord(ra[ok] * u.deg, de[ok] * u.deg).separation(SkyCoord(T_RA * u.deg, T_DEC * u.deg)).arcsec
idx = np.flatnonzero(ok)[np.argsort(sep)[:3]]
OUT["UltracoolSheet_nearest"] = [
    {"name": rows[i]["name"], "sep_arcsec": round(float(sep[np.searchsorted(np.flatnonzero(ok), i)]), 1)} for i in idx
]


def is_single_field(r):
    return (r["multiplesystem_unresolved_in_this_table"] or "N").startswith("N") and r["youth_evidence"] in ("N", "", "null")


calib = {}
for r in rows:
    s = f(r, "sptnum_formula")  # UCS convention: M0=0? check below
    plx, eplx, w2, w1 = f(r, "plx_formula"), f(r, "plxerr_formula"), f(r, "W2"), f(r, "W1")
    if s is None or plx is None or eplx is None or w2 is None or plx <= 0 or eplx / plx > 0.1:
        continue
    if not is_single_field(r):
        continue
    calib.setdefault(s, []).append((w2 + 5 * math.log10(plx / 100.0), (w1 - w2) if w1 is not None else None, r["name"], r["spt_ir"] or r["spt_opt"]))

# discover the numeric code of T0 from a known object (2MASS J0415-0935 = T8)
code_T8 = next(f(r, "sptnum_formula") for r in rows if r["name"].startswith("2MASS J04151954-0935066") or r["name"].startswith("2MASSI J0415195-093506"))
T0 = code_T8 - 8
OUT["UCS_sptnum_T0_code"] = T0
dist = {}
for sub in range(3, 9):
    vals = calib.get(T0 + sub, [])
    m = np.array([v[0] for v in vals])
    c = np.array([v[1] for v in vals if v[1] is not None])
    if len(m) < 3:
        continue
    med, sd = float(np.median(m)), float(1.4826 * np.median(np.abs(m - np.median(m))))
    d = 10 ** ((W2_CW - med + 5) / 5)
    dlo, dhi = 10 ** ((W2_CW - (med + sd) + 5) / 5), 10 ** ((W2_CW - (med - sd) + 5) / 5)
    dist[f"T{sub}"] = {
        "n": len(m), "M_W2_median": round(med, 2), "M_W2_scatter": round(sd, 2),
        "W1-W2_median": round(float(np.median(c)), 2) if len(c) else None,
        "W1-W2_16_84": [round(float(np.percentile(c, 16)), 2), round(float(np.percentile(c, 84)), 2)] if len(c) else None,
        "dist_pc": round(d, 1), "dist_range_pc": [round(dlo, 1), round(dhi, 1)],
    }
OUT["UCS_empirical_MW2_and_distance(W2_CatWISE=15.295)"] = dist
nir = {}
for r in rows:
    s, j, k, w2 = f(r, "sptnum_formula"), f(r, "J_MKO"), f(r, "K_MKO"), f(r, "W2")
    if s is None or j is None or not is_single_field(r) or not (T0 + 3 <= s <= T0 + 8) or s != int(s):
        continue
    e = nir.setdefault(f"T{int(s - T0)}", {"J-W2": [], "J-K": []})
    if w2 is not None:
        e["J-W2"].append(j - w2)
    if k is not None:
        e["J-K"].append(j - k)
OUT["UCS_NIR_colours_median[16,84] (MKO)"] = {
    t: {c: [round(float(np.median(v)), 2), round(float(np.percentile(v, 16)), 2), round(float(np.percentile(v, 84)), 2), len(v)]
        for c, v in e.items() if len(v) >= 3} for t, e in sorted(nir.items())}

# ---- 2. independent two-catalogue PM: AllWISE (mean MJD 55413.39, sig 0.19") -> VHS DR5 J (MJD 57177.38) -----
aw = SkyCoord(349.3687305 * u.deg, -66.9999274 * u.deg)
vhs = SkyCoord(349.370182 * u.deg, -67.000284 * u.deg)
dt = (57177.379115 - 55413.39062770) / 365.25
dra, ddec = aw.spherical_offsets_to(vhs)
e = math.hypot(0.19, 0.10) / dt * 1000  # VHS per-source astrometric error ~0.1" assumed (not in the VizieR row)
OUT["PM_AllWISE_to_VHS"] = {"dt_yr": round(dt, 2), "pmra": round(dra.to(u.mas).value / dt, 0),
                            "pmdec": round(ddec.to(u.mas).value / dt, 0), "err_per_axis": round(e, 0)}
PM["AllWISE_to_VHS"] = (OUT["PM_AllWISE_to_VHS"]["pmra"], OUT["PM_AllWISE_to_VHS"]["pmdec"], e, e)

# ---- Kirkpatrick+2021 (ApJS 253, 7) Table 13 polynomials, copied from arXiv:2011.11616 p.61-63.
# SpT code: L0=0, T0=10, Y0=20. W2 -> ch2 via row "W2 ch2"; RMS of SpT->Mch2 is 0.31 mag.
def poly(c, x):
    return sum(ci * x**i for i, ci in enumerate(c))


K21_SPT_MCH2 = [1.0071e+01, 1.8897e-01, -6.2186e-02, 1.9711e-02, -2.3844e-03, 1.3230e-04, -3.3136e-06, 2.9971e-08]
K21_SPT_W1W2 = [2.2668e-01, 2.9069e-02, -4.6379e-03, 5.7825e-04]
K21_SPT_JCH2 = [1.8153e+00, 1.8527e-01, -1.7678e-01, 7.2989e-02, -1.1351e-02, 8.1335e-04, -2.7663e-05, 3.6779e-07]
K21_W1W2_SPT = [-3.9840e+00, 3.4029e+01, -2.5352e+01, 1.0073e+01, -1.9779e+00, 1.5181e-01]  # RMS 1.16 subtypes
K21_MCH2_SPT = [1.4559e+03, -4.6516e+02, 5.4301e+01, -2.7423e+00, 5.0950e-02]                # RMS 1.26 subtypes
ch2 = 0.070888 + 0.99268 * W2_CW
k21 = {}
for sub in (4, 5, 5.5, 6, 7):
    x = 10 + sub
    m = poly(K21_SPT_MCH2, x)
    d = 10 ** ((ch2 - m + 5) / 5)
    k21[f"T{sub}"] = {"Mch2": round(m, 2), "dist_pc": round(d, 1),
                      "dist_pc_1sig(0.31mag)": [round(d * 10 ** (-0.31 / 5), 1), round(d * 10 ** (0.31 / 5), 1)],
                      "W1-W2_pred": round(poly(K21_SPT_W1W2, x), 2), "J-ch2_pred": round(poly(K21_SPT_JCH2, x), 2)}
OUT["K21_distance_and_colours(W2=15.295 -> ch2=%.3f)" % ch2] = k21
OUT["K21_SpT_from_W1-W2"] = {k: round(poly(K21_W1W2_SPT, v[0]) - 10, 1) for k, v in col.items()}  # T subtype
OUT["J(VHS)-ch2"] = round(J_VHS - ch2, 2)
# Rothermich's "(T6)": host parallax 35.14 mas + K21 Mch2->SpT
mw2_host = W2_CW + 5 * math.log10(35.14 / 100)
OUT["Rothermich_style_phot_type"] = {"M_W2_at_host_distance": round(mw2_host, 2),
                                     "SpT_T": round(poly(K21_MCH2_SPT, -0.09687 + 1.0063 * mw2_host) - 10, 1)}

# ---- 6. companion test ---------------------------------------------------------------------------
host_d_pc = 1000 / 35.14
comp = {}
for name, (pa, pd, ea, ed) in PM.items():
    for hname, (hra, hdec, hpa, hpd, hplx) in HOSTS.items():
        da, dd = pa - hpa, pd - hpd
        chi2 = (da / ea) ** 2 + (dd / ed) ** 2
        dv = 4.74047 * math.hypot(da, dd) / 1000 * host_d_pc
        comp[f"{name} vs {hname}"] = {
            "dmu_ra": round(da, 1), "dmu_dec": round(dd, 1), "sig_ra": round(da / ea, 2), "sig_dec": round(dd / ed, 2),
            "dmu_total": round(math.hypot(da, dd), 1), "chi2_2dof": round(chi2, 1),
            "p_2dof": float(f"{math.exp(-chi2 / 2):.2e}"), "dv_tan_kms_at_28.46pc": round(dv, 1),
        }
OUT["companion"] = comp
c_t = SkyCoord(T_RA * u.deg, T_DEC * u.deg)
seps = {}
for hname, (hra, hdec, *_ ) in HOSTS.items():
    s = c_t.separation(SkyCoord(hra * u.deg, hdec * u.deg)).arcsec  # host coords are J2000/ep2016 (SIMBAD); ~ few arcsec effect
    seps[hname] = {"sep_arcsec": round(s, 1), "proj_au": round(s * host_d_pc)}
OUT["separation"] = seps
# orbital speed for a circular orbit at the projected separation, M_tot ~ 0.75+0.72+0.04 Msun (two K dwarfs + BD)
a_au = 6500
OUT["v_orb_kms_at_6500au_1.5Msun"] = round(29.78 * math.sqrt(1.5 / a_au), 2)

# ---- 2. PM consistency: ours vs CatWISE (corrected) -----------------------------------------------
pmc = {}
for name in ("ours_visit", "ours_deep", "production"):
    for ref in ("CatWISE_VizieR_corrected(=Rothermich)", "CatWISE_IRSA_uncorrected"):
        a, b = PM[name], PM[ref]
        pmc[f"{name} - {ref}"] = [round(a[0] - b[0], 1), round(a[1] - b[1], 1),
                                  round((a[0] - b[0]) / math.hypot(a[2], b[2]), 2), round((a[1] - b[1]) / math.hypot(a[3], b[3]), 2)]
OUT["pm_differences [dRA, dDec, sigRA, sigDec]"] = pmc
for k, (a, b, ea, eb) in PM.items():
    tot = math.hypot(a, b)
    OUT.setdefault("pm_total", {})[k] = [round(tot, 1), round(math.hypot(a * ea, b * eb) / tot, 1)]

# ---- 4. spectral typing separability --------------------------------------------------------------
disc = json.load(open("/data/research/discovery/out/J2317-6700.json"))
prod = json.load(open("/data/research/discovery/prod_J2317_summary.json"))
bins = disc["spectrum"]["binned"]
wl = np.array([b["wavelength_um"] for b in bins]); fl = np.array([b["flambda"] for b in bins]); er = np.array([b["err"] for b in bins])
snr = fl / er
OUT["spectrum_bins"] = {
    "n_bins": len(bins), "n_snr_gt3": int((snr > 3).sum()), "n_snr_gt5": int((snr > 5).sum()), "max_snr": round(float(snr.max()), 1),
    "median_snr": round(float(np.median(snr)), 2),
    "n_negative_flux": int((fl < 0).sum()),
}
for lab, src in (("research", disc["spectrum"]), ("production", prod["spectrum"])):
    rk = src["ranking"]
    n = rk[0]["n_bins"]
    best = rk[0]["chi2_red"] * (n - 1)
    OUT[f"typing_{lab}"] = [{"label": x["label"], "chi2_red": round(x["chi2_red"], 3),
                             "dchi2": round(x["chi2_red"] * (n - 1) - best, 1),
                             "dchi2_if_errors_rescaled_by_sqrt_chi2r": round((x["chi2_red"] * (n - 1) - best) / rk[0]["chi2_red"], 1)} for x in rk]

print(json.dumps(OUT, indent=1))
json.dump(OUT, open(HERE / "recompute_out.json", "w"), indent=1)
