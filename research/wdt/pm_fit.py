"""Proper motion of WISE J2354-8140 (T dwarf) from every position we have, vs the WD Gaia DR3 6350786278796634112.

Run: cd research/wdt && nice -n 15 ../../.venv/bin/python pm_fit.py  -> pm_fit_out.json, pm_fit_stdout.txt
Inputs (all saved next to this script):
  irsa_allwise_p3as_psd.tbl (AllWISE ra/dec/sigra/sigdec; positions at MJD 55400.0, AllWISE convention),
  irsa_allwise_mep.tbl (48 single exposures, MJD 55296-55484: confirms the epoch),
  vz_II365_catwise.tsv -> vizier_II365_catwise.tsv (CatWISE2020 RAPMdeg/DEPMdeg at MJD 57170.0, offset-corrected PM),
  irsa_catwise_2020.tbl (uncorrected PM), vz_vhsdr5.tsv (VHS DR5 detections with per-frame MJDs),
  dev_summary.json (our pipeline WISE epoch centroids), spherex_centroids_out.json (our SPHEREx centroids).
"""
import json
import math
from pathlib import Path

import numpy as np
import astropy.units as u
from astropy.coordinates import get_body_barycentric
from astropy.time import Time
from scipy import stats

from vztsv import rows

HERE = Path(__file__).resolve().parent
RA0, DEC0 = 358.70015, -81.67908
WD = dict(ra=358.58382867379, dec=-81.68455055873, pmra=96.033, e_pmra=0.066, pmdec=36.288, e_pmdec=0.069,
          plx=37.1045, e_plx=0.0610)  # vz_gf21_wd.tsv (= Gaia DR3)
D_PC = 1000 / WD["plx"]
K = 4.740470446  # km/s per (arcsec/yr * pc)
OUT, LOG = {}, []


def p(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.append(s)


def yr(mjd):
    return 2000.0 + (mjd - 51544.5) / 365.25


def off(ra, dec):  # gnomonic-enough offsets (arcsec) about the reference; field is < 10" wide
    return ((ra - RA0 + 180) % 360 - 180) * math.cos(math.radians(DEC0)) * 3600, (dec - DEC0) * 3600


def plx_factors(t_yr):
    """(f_ra*, f_dec) so that the parallax shift is plx * f (ICRS, barycentric Earth position in au)."""
    e = get_body_barycentric("earth", Time(t_yr, format="decimalyear")).xyz.to(u.au).value
    a, d = math.radians(RA0), math.radians(DEC0)
    return (e[0] * math.sin(a) - e[1] * math.cos(a),
            e[0] * math.cos(a) * math.sin(d) + e[1] * math.sin(a) * math.sin(d) - e[2] * math.cos(d))


def fit(pts, plx_mas=0.0, scale_chi2=True):
    """Weighted line per axis; pts = [(t, xi, eta, sxi, seta)]; parallax removed at fixed plx_mas."""
    t = np.array([q[0] for q in pts])
    res = {}
    chi2, dof = 0.0, 0
    for k, (i, s) in enumerate(((1, 3), (2, 4))):
        y = np.array([q[i] for q in pts]) - plx_mas / 1000 * np.array([plx_factors(q[0])[k] for q in pts])
        w = 1 / np.array([q[s] for q in pts]) ** 2
        t0 = np.sum(w * t) / np.sum(w)
        A = np.vstack([np.ones_like(t), t - t0]).T
        cov = np.linalg.inv(A.T @ (A * w[:, None]))
        b = cov @ (A.T @ (w * y))
        r = y - A @ b
        chi2 += float(np.sum(w * r**2))
        dof += len(t) - 2
        res[k] = (b[1] * 1000, math.sqrt(cov[1, 1]) * 1000)
    s = math.sqrt(max(1.0, chi2 / dof)) if (scale_chi2 and dof > 0) else 1.0
    return {"pmra": round(res[0][0], 1), "e_pmra": round(res[0][1] * s, 1), "pmdec": round(res[1][0], 1),
            "e_pmdec": round(res[1][1] * s, 1), "chi2_red": round(chi2 / dof, 2) if dof else None, "n": len(pts),
            "baseline_yr": round(float(t.max() - t.min()), 2), "plx_fixed_mas": plx_mas}


# ---------------------------------------------------------------- positions
P = {}
aw = [l.split() for l in open(HERE / "irsa_allwise_p3as_psd.tbl") if not l.startswith(("\\", "|"))][0]
x, y = off(float(aw[1]), float(aw[2]))
P["AllWISE"] = [(yr(55400.0), x, y, float(aw[5]), float(aw[6]))]
cw = rows(HERE / "vizier_II365_catwise.tsv")[0]
x, y = off(float(cw["RAPMdeg"]), float(cw["DEPMdeg"]))
P["CatWISE"] = [(yr(57170.0), x, y, float(cw["e_RAPMdeg"]), float(cw["e_DEPMdeg"]))]
VHS_ERR = 0.10  # assumed per-detection astrometric error (not in the VizieR row); J S/N 11-16
P["VHS"] = []
for r in rows(HERE / "vz_vhsdr5.tsv"):
    clean = r["Jperrbits"] == "0" and float(r["pStar"]) > 0.5
    x, y = off(float(r["RAJ2000"]), float(r["DEJ2000"]))
    p(f"VHS {r['Name']} JMJD {r['JMJD']} pStar {r['pStar']} Jperrbits {r['Jperrbits']} -> {'used' if clean else 'dropped'} offs ({x:.3f},{y:.3f})")
    if clean:
        P["VHS"].append((yr(float(r["JMJD"])), x, y, VHS_ERR, VHS_ERR))
sm = json.load(open(HERE / "dev_summary.json"))["motion"]
P["pipeline_WISE"] = [(yr(q["mjd"]), *off(q["ra"], q["dec"]), q["err_arcsec"], q["err_arcsec"]) for q in sm["points"]]
sc = json.load(open(HERE / "spherex_centroids_out.json"))
P["SPHEREx_D5D6"] = [(q["epoch_yr"], *off(q["ra"], q["dec"]), q["err_arcsec"], q["err_arcsec"]) for q in sc["D5D6"]]
OUT["positions_offsets_arcsec"] = {k: [[round(v, 4) for v in q] for q in L] for k, L in P.items()}

# ---------------------------------------------------------------- estimates
E = {}
E["pipeline_summary(WISE 2010-2024, catalog-prior search)"] = {
    "pmra": round(sm["pmra_masyr"], 1), "e_pmra": round(sm["pmra_err_masyr"], 1), "pmdec": round(sm["pmdec_masyr"], 1),
    "e_pmdec": round(sm["pmdec_err_masyr"], 1), "baseline_yr": round(sm["baseline_yr"], 2), "n": len(sm["points"])}
E["CatWISE2020 corrected (VizieR II/365)"] = {"pmra": round(float(cw["pmRA"]) * 1000, 1), "e_pmra": round(float(cw["e_pmRA"]) * 1000, 1),
                                               "pmdec": round(float(cw["pmDE"]) * 1000, 1), "e_pmdec": round(float(cw["e_pmDE"]) * 1000, 1)}
E["CatWISE2020 uncorrected (IRSA catwise_2020)"] = {"pmra": 141.8, "e_pmra": 25.8, "pmdec": 72.8, "e_pmdec": 23.1}  # irsa_catwise_2020.tbl
for name, keys in {
    "ours WISE+SPHEREx (16.4 yr)": ["pipeline_WISE", "SPHEREx_D5D6"],
    "AllWISE->VHS (2 catalogues, no pipeline)": ["AllWISE", "VHS"],
    "AllWISE+VHS+SPHEREx (no CatWISE)": ["AllWISE", "VHS", "SPHEREx_D5D6"],
    "VHS->SPHEREx (no WISE at all)": ["VHS", "SPHEREx_D5D6"],
    "AllWISE+CatWISE+VHS+SPHEREx (catalogue positions)": ["AllWISE", "CatWISE", "VHS", "SPHEREx_D5D6"],
    "COMBINED: ours WISE+VHS+SPHEREx": ["pipeline_WISE", "VHS", "SPHEREx_D5D6"],
}.items():
    pts = [q for k in keys for q in P[k]]
    E[name] = fit(pts, plx_mas=WD["plx"])
    E[name + " [no parallax term]"] = fit(pts)
    E[name]["uses"] = keys

# ---------------------------------------------------------------- vs WD
cmp_ = {}
for name, e in E.items():
    da, dd = e["pmra"] - WD["pmra"], e["pmdec"] - WD["pmdec"]
    ea, ed = math.hypot(e["e_pmra"], WD["e_pmra"]), math.hypot(e["e_pmdec"], WD["e_pmdec"])
    chi2 = (da / ea) ** 2 + (dd / ed) ** 2
    dmu = math.hypot(da, dd)
    edmu = math.sqrt((da * ea) ** 2 + (dd * ed) ** 2) / dmu if dmu else max(ea, ed)
    cmp_[name] = {"dpmra": round(da, 1), "dpmdec": round(dd, 1), "sig_ra": round(da / ea, 2), "sig_dec": round(dd / ed, 2),
                  "chi2_2dof": round(chi2, 2), "p_value": round(float(stats.chi2.sf(chi2, 2)), 3),
                  "dmu": round(dmu, 1), "e_dmu": round(edmu, 1),
                  "dvtan_kms_at_WD_distance": round(K * dmu / 1000 * D_PC, 2), "e_dvtan_kms": round(K * edmu / 1000 * D_PC, 2),
                  "dvtan_2sigma_upper_kms": round(K * (dmu + 2 * edmu) / 1000 * D_PC, 2)}
OUT["estimates"] = E
OUT["vs_WD"] = cmp_
OUT["WD"] = WD
OUT["WD_distance_pc"] = round(D_PC, 3)
p("\nPM estimates (mas/yr) and comparison with the WD (96.03, 36.29):")
for n, e in E.items():
    c = cmp_[n]
    p(f"{n:62s} ({e['pmra']:6.1f}+-{e['e_pmra']:4.1f}, {e['pmdec']:6.1f}+-{e['e_pmdec']:4.1f}) "
      f"chi2r={e.get('chi2_red')} base={e.get('baseline_yr')} | d=({c['dpmra']:+.0f},{c['dpmdec']:+.0f}) "
      f"chi2={c['chi2_2dof']:.2f} p={c['p_value']:.2f} dv={c['dvtan_kms_at_WD_distance']:.1f}+-{c['e_dvtan_kms']:.1f} km/s")

# ---------------------------------------------------------------- separation at a common epoch (Gaia 2016.0)
best = E["COMBINED: ours WISE+VHS+SPHEREx"]
cw_ra, cw_de = float(cw["RAPMdeg"]), float(cw["DEPMdeg"])
dt = 2016.0 - yr(57170.0)
t_ra = cw_ra + float(cw["pmRA"]) / 3600 / math.cos(math.radians(cw_de)) * dt
t_de = cw_de + float(cw["pmDE"]) / 3600 * dt
from astropy.coordinates import SkyCoord  # noqa: E402
sep = SkyCoord(t_ra * u.deg, t_de * u.deg).separation(SkyCoord(WD["ra"] * u.deg, WD["dec"] * u.deg)).arcsec
OUT["separation_2016"] = {"arcsec": round(sep, 2), "au_projected": round(sep * D_PC, 0),
                          "pa_deg": round(SkyCoord(WD["ra"] * u.deg, WD["dec"] * u.deg).position_angle(SkyCoord(t_ra * u.deg, t_de * u.deg)).deg, 1)}
p("\nseparation (2016.0):", OUT["separation_2016"])
json.dump(OUT, open(HERE / "pm_fit_out.json", "w"), indent=1)
open(HERE / "pm_fit_stdout.txt", "w").write("\n".join(LOG) + "\n")
