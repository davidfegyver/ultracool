"""Per-object verdict for every measured candidate (out/<tag>/metrics.json + spectrum.json + summary.json).

(a) spectrum: dev-API verdict/type_range/S/N/neighbour flags + 5 refit variants (research/verification/spectral_refit.py
    fit: analytic scale, template spread in quadrature; all, no spread, 1.0-2.5 um, 2.5-5.0 um, errors x1.5) + colour
    consistency (CatWISE W1-W2 and 2MASS J - CatWISE W2 vs the UltracoolSheet v2.1.0 field-single locus per subtype).
(b) companion: our PM (+20 mas/yr/axis systematic floor, research/discovery/REPORT.md) and pipeline-independent PMs
    (CatWISE2020 II/365 offset-corrected; 2MASS -> CatWISE 2015.4 two-epoch; Gaia DR3 when detected) vs the host's
    Gaia DR3 PM: delta-mu, chi2, delta-v_tan at the host distance, bound-orbit limit (escape speed at the projected
    separation, M_tot from Rothermich Table 11 or 0.6 Msun); photometric distance from OUR type range (UltracoolSheet
    empirical M_W2 per subtype, median +- 1.4826 MAD; Kirkpatrick+2021 Table 13 SpT->M_ch2 for L0 and later, RMS 0.31)
    vs the host parallax.
Writes out/<tag>/verdict.json and out/results.csv. Usage: python scripts/verdict.py   (cwd = research/discovery2)"""
import csv
import json
import math
import re
import sys
import time
from pathlib import Path

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.table import Table
from astroquery.vizier import Vizier
from scipy.stats import chi2 as chi2dist

sys.path.insert(0, str(Path("../../backend").resolve()))
from app.spectral import TEMPLATES  # noqa: E402  read-only: the vendored SPIFF templates

SYS_PM = 20.0  # mas/yr per axis, our-pipeline systematic floor (research/discovery/REPORT.md validation)
screen = {r["tag"]: r for r in json.loads(Path("out/screen.json").read_text())}
hosts = json.loads(Path("out/hosts.json").read_text())
cw = Table.read("raw/screen_II_365_catwise_15.ecsv")
t11 = {l.split("\t")[5].strip(): l.split("\t") for l in open("raw/rothermich_table11.tsv") if not l.startswith("#") and l.count("\t") > 8}  # Comp -> row; [8] = Mtot
VHS = json.loads(Path("raw/vhs_dr5_measured.json").read_text())
SED = json.loads(Path("out/sed_check.json").read_text())


def spt_num(label):
    m = re.match(r"^(?:sd|d_sd)?([MLTY])(\d+(?:\.\d+)?)", label or "")
    return {"M": 0, "L": 10, "T": 20, "Y": 30}[m[1]] + float(m[2]) if m else None


def spt_str(x):
    return "MLTY"[int(x // 10)] + (f"{x % 10:g}")


# ---------------------------------------------------------------- refit variants
def fit1(lam, f, s, t, use_tu=True):
    m = (lam >= t[0, 0]) & (lam <= t[-1, 0])
    if m.sum() < 3:
        return None
    tm, tu = np.interp(lam[m], t[:, 0], t[:, 1]), np.interp(lam[m], t[:, 0], t[:, 2]) * use_tu
    ff, ss = f[m], s[m]
    a = np.sum(ff * tm / ss**2) / np.sum(tm**2 / ss**2)
    for _ in range(2):
        st = np.hypot(ss, a * tu)
        a = np.sum(ff * tm / st**2) / np.sum(tm**2 / st**2)
    return float(np.sum(((ff - a * tm) / np.hypot(ss, a * tu)) ** 2)), int(m.sum())


def rank(lam, f, s, use_tu=True):
    rows = sorted((c / (n - 1), lab) for lab, t in TEMPLATES.items() if (r := fit1(lam, f, s, t, use_tu)) for c, n in [r])
    return [(lab, round(c, 2)) for c, lab in rows[:5]]


def variants(binned):
    lam = np.array([x["wavelength_um"] for x in binned]); f = np.array([x["flambda"] for x in binned]); s = np.array([x["err"] for x in binned])
    nir, mir = lam < 2.5, lam >= 2.5
    return {"all": rank(lam, f, s), "all_no_template_spread": rank(lam, f, s, False), "1.0-2.5um": rank(lam[nir], f[nir], s[nir]),
            "2.5-5.0um": rank(lam[mir], f[mir], s[mir]), "errors_x1.5": rank(lam, f, s * 1.5)}


# ---------------------------------------------------------------- UltracoolSheet field-single calibration per subtype
def fl(r, k):
    try:
        v = float(r[k])
        return v if math.isfinite(v) else None
    except (ValueError, KeyError):
        return None


calib = {}
for r in csv.DictReader(open("../discovery/ext/ultracoolsheet_v2.1.0_main.csv", encoding="utf8")):
    s, plx, eplx, w1, w2, j = (fl(r, k) for k in ("sptnum_formula", "plx_formula", "plxerr_formula", "W1", "W2", "J_2MASS"))
    if s is None or w2 is None or "photSpT" in (r["literature_flag"] or ""):
        continue
    if not ((r["multiplesystem_unresolved_in_this_table"] or "N").startswith("N") and r["youth_evidence"] in ("N", "", "null")):
        continue
    k = int(round(s))
    d = calib.setdefault(k, {"mw2": [], "w12": [], "jw2": [], "jmw2": [], "grp": []})
    if fl(r, "J_MKO") is not None:
        d["jmw2"].append(fl(r, "J_MKO") - w2)
    if fl(r, "G_Gaia") is not None and fl(r, "RP_Gaia") is not None:
        d["grp"].append(fl(r, "G_Gaia") - fl(r, "RP_Gaia"))
    if plx and eplx and plx > 0 and eplx / plx < 0.1:
        d["mw2"].append(w2 + 5 * math.log10(plx / 100))
    if w1 is not None:
        d["w12"].append(w1 - w2)
    if j is not None:
        d["jw2"].append(j - w2)


def stat(k, key):
    v = np.array(calib.get(k, {}).get(key, []))
    if len(v) < 5:
        return None
    return {"n": len(v), "median": float(np.median(v)), "mad": float(1.4826 * np.median(np.abs(v - np.median(v)))),
            "p16": float(np.percentile(v, 16)), "p84": float(np.percentile(v, 84)), "p2.5": float(np.percentile(v, 2.5)), "p97.5": float(np.percentile(v, 97.5))}


def colour_types(c, e, key, lo="p16", hi="p84"):
    """subtypes (integer codes 6..29) whose UCS lo-hi percentile colour interval, widened by the measurement error, holds c"""
    return [k for k in range(6, 30) if (st := stat(k, key)) and st[lo] - e <= c <= st[hi] + e]


K21_SPT_MCH2 = [1.0071e+01, 1.8897e-01, -6.2186e-02, 1.9711e-02, -2.3844e-03, 1.3230e-04, -3.3136e-06, 2.9971e-08]  # L0=0 (arXiv:2011.11616 Table 13)


def k21_mch2(code):
    x = code - 10
    return sum(c * x**i for i, c in enumerate(K21_SPT_MCH2)) if x >= 0 else None


# ---------------------------------------------------------------- 2MASS (II/246) per object, for J and the 2MASS->CatWISE PM
viz = Vizier(columns=["**", "_r"], row_limit=-1)
viz.VIZIER_SERVER = "vizier.cfa.harvard.edu"
TM = Path("raw/twomass_measured.json")
tmass = json.loads(TM.read_text()) if TM.exists() else {}


def twomass(tag, ra, dec, pm_tot):
    if tag not in tmass:
        for k in range(3):
            try:
                t = viz.query_region(SkyCoord(ra, dec, unit="deg"), radius=(2 + pm_tot * 18) * u.arcsec, catalog="II/246/out")
                tmass[tag] = [] if not t else [{c: (None if np.ma.is_masked(r[c]) else (r[c].item() if hasattr(r[c], "item") else r[c]))
                                                 for c in ("2MASS", "RAJ2000", "DEJ2000", "errMaj", "errMin", "Jmag", "e_Jmag", "Hmag", "Kmag", "Qflg", "JD", "_r")} for r in t[0]]
                TM.write_text(json.dumps(tmass, indent=1, default=str))
                break
            except Exception as e:  # noqa: BLE001
                print("2MASS retry", e); time.sleep(15)
    return sorted(tmass.get(tag, []), key=lambda r: r["_r"])


def pm_cmp(name, pa, pd, ea, ed, h, plx, sep_au, mtot):
    da, dd = pa - h["pmRA"], pd - h["pmDE"]
    ea, ed = math.hypot(ea, h["e_pmRA"]), math.hypot(ed, h["e_pmDE"])
    c2 = (da / ea) ** 2 + (dd / ed) ** 2
    dmu = math.hypot(da, dd)
    v_esc = 29.78 * math.sqrt(2 * mtot / sep_au)  # km/s, escape speed at the projected separation (an upper bound for a bound orbit)
    return {"source": name, "pmra": round(pa, 1), "pmdec": round(pd, 1), "err": [round(ea, 1), round(ed, 1)], "dmu_ra": round(da, 1), "dmu_dec": round(dd, 1),
            "dmu_total": round(dmu, 1), "chi2_2dof": round(c2, 2), "p_value": float(f"{chi2dist.sf(c2, 2):.3g}"),
            "dv_tan_kms": round(4.74 * dmu / plx, 2), "dv_tan_err_kms": round(4.74 * math.hypot(da * ea, dd * ed) / max(dmu, 1e-9) / plx, 2),
            "bound_limit_kms": round(v_esc, 2), "bound_limit_masyr": round(v_esc / 4.74 * plx, 2)}


rows = []
for tag in screen:
    d = Path("out") / tag
    if not (d / "metrics.json").exists():
        continue
    met = json.loads((d / "metrics.json").read_text())
    summ = json.loads((d / "summary.json").read_text())
    sp = summ["spectrum"]
    s = screen[tag]
    h = (hosts.get(tag) or {}).get("host_gaia_dr3")
    v = {"tag": tag, "name": s["name"], "seq_id": met["seq_id"], "rothermich_type": s["lit_spt_rothermich"], "table": s["table"], "prob": s["prob"]}
    # ---- (a) spectrum
    b = sp.get("binned") or []
    v["variants"] = variants(b) if len(b) >= 10 else None
    if len(b) >= 10:  # how strongly does the spectrum exclude the photometric type? (production fit, chi2 rescaled by chi2_red when > 1)
        lam = np.array([x["wavelength_um"] for x in b]); f = np.array([x["flambda"] for x in b]); e = np.array([x["err"] for x in b])
        fits = {lab: r for lab, t in TEMPLATES.items() if (r := fit1(lam, f, e, t))}
        c0, n0 = min(fits.values())
        sc = max(1.0, c0 / (n0 - 1))
        rl = s["lit_spt_rothermich"].strip("()")
        v["photometric_type_check"] = {"rothermich_label": rl, "chi2_best": round(c0, 1), "scale": round(sc, 2),
                                       "dchi2_rescaled": round((fits[rl][0] - c0) / sc, 1) if rl in fits else None,
                                       "dchi2_rescaled_by_template": {lab: round((c - c0) / sc, 1) for lab, (c, n) in sorted(fits.items(), key=lambda x: x[1][0])}}
    tr = sp.get("type_range")
    best = (sp.get("best") or {}).get("label")
    v["spectrum"] = {"verdict": sp["verdict"], "best": sp.get("best"), "type_range": tr, "ranking": sp.get("ranking"),
                     "detection_snr": sp.get("detection_snr"), "n_bins": met["n_bins"], "n_bins_snr_gt3": met["n_bins_snr_gt3"],
                     "n_bins_snr_gt5": met["n_bins_snr_gt5"], "photometry": sp.get("photometry"), "neighbour_frac": sp.get("neighbour_frac"),
                     "contaminated": sp.get("contaminated"), "negative_bins": sp.get("negative_bins"), "blends_arcsec": sp.get("blends_arcsec"),
                     "reason": sp.get("reason"), "doubt": sp.get("doubt"), "water_depth": sp.get("water_depth")}
    lo = hi = None
    if tr:
        lo, hi = spt_num(tr[0] if isinstance(tr, list) else tr.get("lo")), spt_num(tr[-1] if isinstance(tr, list) else tr.get("hi"))
    v["type_range_num"] = [lo, hi]
    # variants inside the type range?
    if v["variants"] and lo is not None:
        bests = {k: x[0][0] for k, x in v["variants"].items() if x}
        v["variant_bests"] = bests
        v["variants_inside_range"] = all(lo <= (spt_num(l) or -99) <= hi for l in bests.values())
    # colours
    t = next(x for x in cw if str(x["Name"]) == s["cw_name"])
    w1, w2, ew1, ew2 = float(t["W1mproPM"]), float(t["W2mproPM"]), float(t["e_W1mproPM"]), float(t["e_W2mproPM"])
    pm_tot = math.hypot(s["cw_pmra"], s["cw_pmdec"]) / 1000
    tm = twomass(tag, s["ra"], s["dec"], pm_tot)
    j = tm[0] if tm else None
    cols = {"W1-W2": (w1 - w2, math.hypot(ew1, ew2), "w12")}
    col = {"W1-W2_CatWISE": [round(w1 - w2, 3), round(math.hypot(ew1, ew2), 3)]}
    if j and j["Jmag"] is not None:
        ej = j["e_Jmag"] or 0.15
        col.update({"J_2MASS": [j["Jmag"], j["e_Jmag"]], "J-W2": [round(j["Jmag"] - w2, 3), round(math.hypot(ej, ew2), 3)]})
        cols["J-W2"] = (j["Jmag"] - w2, math.hypot(ej, ew2), "jw2")
    vhs = (VHS.get(tag) or [None])[0]  # VHS DR5 (II/367) Jpmag is MKO J: compared with the UCS J_MKO - W2 locus
    if vhs:
        col["J_VHS"] = [float(vhs["Jpmag"]), float(vhs["e_Jpmag"])]
        col["J_VHS-W2"] = [round(float(vhs["Jpmag"]) - w2, 3), round(math.hypot(float(vhs["e_Jpmag"]), ew2), 3)]
        cols["J_VHS-W2"] = (float(vhs["Jpmag"]) - w2, math.hypot(float(vhs["e_Jpmag"]), ew2), "jmw2")
    col["our_W1-W2"] = [summ["color"].get("w1_w2"), summ["color"].get("w1_w2_err")]
    rng = set(range(int(math.floor(lo)), int(math.ceil(hi)) + 1)) if lo is not None else set()
    for name, (cv, ce, key) in cols.items():
        for lab, (pl, ph) in (("68", ("p16", "p84")), ("95", ("p2.5", "p97.5"))):
            ks = colour_types(cv, ce, key, pl, ph)
            col[f"{name}_types_{lab}"] = [spt_str(k) for k in ks]
            if rng:
                col[f"{name}_consistent_{lab}"] = bool(rng & set(ks))
        if rng:  # the decision uses the 95 % field-locus interval (validated scatter ~2 sigma); 68 % is reported alongside
            col[f"{name}_consistent"] = col[f"{name}_consistent_95"]
    v["colour"] = col
    # ---- (b) companion
    plx = h["Plx"] if h else (float(s["host_plx"]) if s.get("host_plx") not in (None, "") else None)
    if tag == "J1542+5939":  # host RX J1542.3+5936A not resolvable by name in SIMBAD; Rothermich Table 3 Gaia DR3 values
        h = {"Source": "RX J1542.3+5936A (Rothermich Table 3, Gaia DR3)", "pmRA": -88.44, "e_pmRA": 0.02, "pmDE": 20.67, "e_pmDE": 0.02, "Plx": 22.50, "e_Plx": 0.01}
        plx = 22.50
    v["host"] = {"name": s["host"], "gaia": h, "dist_pc": round(1000 / plx, 2) if plx else None, "sep_arcsec": s["sep_arcsec"]}
    row11 = t11.get(s["name"])
    mtot = float(row11[8]) if row11 and row11[8].strip() else 0.6
    sep_au = float(s["sep_arcsec"]) * 1000 / plx if plx else None
    v["host"].update(sep_au_projected=round(sep_au) if sep_au else None, mtot_msun=mtot)
    pms = []
    mo = summ["motion"]
    if h and plx:
        if mo.get("pmra_masyr") is not None:
            pms.append(pm_cmp("ours (dev API /summary, +20 mas/yr floor)", mo["pmra_masyr"], mo["pmdec_masyr"], math.hypot(mo["pmra_err_masyr"], SYS_PM),
                              math.hypot(mo["pmdec_err_masyr"], SYS_PM), h, plx, sep_au, mtot))
        pms.append(pm_cmp("CatWISE2020 II/365 offset-corrected", s["cw_pmra"], s["cw_pmdec"], s["cw_e_pmra"], s["cw_e_pmdec"], h, plx, sep_au, mtot))
        if j:
            # 2MASS (JD) -> CatWISE PM-fit position at MJD 57170 (2015.4): two epochs, independent of our pipeline
            t0 = (j["JD"] - 2451544.5) / 365.25 + 2000
            dt = 2015.4 - t0
            dra = (float(t["RAPMdeg"]) - j["RAJ2000"]) * math.cos(math.radians(j["DEJ2000"])) * 3.6e6 / dt
            dde = (float(t["DEPMdeg"]) - j["DEJ2000"]) * 3.6e6 / dt
            e = math.hypot(j["errMaj"] or 0.1, float(t["e_RAPMdeg"])) * 1000 / dt
            pms.append(pm_cmp(f"2MASS ({t0:.2f}) -> CatWISE (2015.4), {dt:.1f} yr", dra, dde, e, e, h, plx, sep_au, mtot))
        tg = (hosts.get(tag) or {}).get("target_gaia_dr3") or []
        if tg and tg[0].get("pmRA") is not None:
            g = tg[0]
            pms.append(pm_cmp(f"Gaia DR3 {g['Source']} (G={g['Gmag']:.2f}, plx {g['Plx']:.2f}+-{g['e_Plx']:.2f})", g["pmRA"], g["pmDE"], g["e_pmRA"], g["e_pmDE"], h, plx, sep_au, mtot))
            v["target_gaia_plx"] = [g["Plx"], g["e_Plx"]]
            # own-parallax check of the type: M_W2 and Gaia G-RP vs the UCS field locus (95 % interval / median +- 2 MAD)
            mw2 = w2 + 5 * math.log10(g["Plx"] / 100)
            emw2 = math.hypot(ew2, 5 / math.log(10) * g["e_Plx"] / g["Plx"])
            v["own_parallax_check"] = {
                "M_W2": [round(mw2, 2), round(emw2, 2)],
                "M_W2_types_2mad": [spt_str(k) for k in range(6, 30) if (st := stat(k, "mw2")) and abs(mw2 - st["median"]) <= math.hypot(2 * st["mad"], 2 * emw2)],
                "G-RP": round(g["Gmag"] - g["RPmag"], 3) if g.get("RPmag") else None,
                "G-RP_types_95": [spt_str(k) for k in colour_types(g["Gmag"] - g["RPmag"], 0.05, "grp", "p2.5", "p97.5")] if g.get("RPmag") else None,
                "M_W2_by_subtype": {spt_str(k): round(st["median"], 2) for k in range(6, 22) if (st := stat(k, "mw2"))},
                "G-RP_by_subtype": {spt_str(k): round(st["median"], 2) for k in range(6, 22) if (st := stat(k, "grp"))}}
    v["motion_ours"] = {k: mo.get(k) for k in ("verdict", "pmra_masyr", "pmdec_masyr", "pmra_err_masyr", "pmdec_err_masyr", "significance_sigma", "n_epochs", "baseline_yr", "recovered", "consistent_with_catalog")}
    v["pm_vs_host"] = pms
    # ---- adopted type: pipeline range widened to every variant best (downgrade rule: anything that disagrees widens it)
    pc = json.loads((d / "photometry_check.json").read_text()) if (d / "photometry_check.json").exists() else None
    v["photometry_check"] = pc
    sp_ok = sp["verdict"] == "match" and (sp.get("detection_snr") or 0) >= 15 and met["n_bins_snr_gt5"] >= 15 \
        and not sp.get("contaminated") and not sp.get("blends_arcsec")
    # point estimates: pipeline best, every variant best, and the best type from the photometry the pipeline did not use.
    # They must agree within 2 subtypes ("~X +- 1", the J2317 rule); the adopted range is the pipeline range widened to all of them.
    alo = ahi = None
    points = []
    if lo is not None:
        points = [spt_num(best)] + [spt_num(l) for l in (v.get("variant_bests") or {}).values()]
        other = (pc or {}).get("aperture" if met["neighbour_psf_used"] else "psf") or {}
        if other.get("best"):
            points.append(spt_num(other["best"]))
        points = [x for x in points if x is not None]
        alo, ahi = min([lo] + points), max([hi] + points)
    spread = max(points) - min(points) if points else None
    v["type_points"] = {"values": [spt_str(x) for x in points], "spread_subtypes": spread}
    colours_ok = all(val for key, val in col.items() if key.endswith("_consistent"))
    reasons = []
    if not sp_ok:
        reasons.append(f"spectrum not adequate: verdict {sp['verdict']!r}, detection S/N {sp.get('detection_snr') and round(sp['detection_snr'], 1)}, "
                       f"{met['n_bins_snr_gt5']} channels at S/N>5 (need 15), contaminated={sp.get('contaminated')}, blends={sp.get('blends_arcsec')}")
    if spread is not None and spread > 2:
        reasons.append(f"best types of the fitting variants / photometry choices span {spt_str(min(points))}-{spt_str(max(points))} (> 2 subtypes)")
    if not colours_ok:
        reasons.append("colour inconsistent with the type (95 % UCS locus)")
    # SPIFF templates start at M8: a range touching M8 cannot test an earlier photometric type (e.g. Rothermich's M6)
    floor = alo is not None and alo <= 8
    rn = spt_num(s["lit_spt_rothermich"].strip("()"))
    if floor and rn is not None and rn < 8:
        reasons.append(f"type range reaches the M8 template floor and the photometric type ({s['lit_spt_rothermich']}) is earlier than any template")
    # light from a neighbour the PSF model misses: SPHEREx 1.15-1.32 um flux vs the target's own catalogue J (scripts/sed_check.py);
    # the isolated, unflagged J1023-2045 and J1542+5939 give 1.06 and 1.09, so > 1.4 means extra light
    sed = SED.get(tag) or {}
    v["sed_check"] = sed
    sed_bad = (sed.get("ratio_J") or 0) > 1.4
    if sed_bad:
        reasons.append(f"SPHEREx 1.15-1.32 um flux is {sed['ratio_J']:.2f}x the catalogue {sed['J_source']} J (isolated objects: 1.06-1.09): extra light, probably the bright host")
    type_positive = sp_ok and spread is not None and spread <= 2 and colours_ok and not (floor and rn is not None and rn < 8) and not sed_bad
    v["adopted_type_range"] = [spt_str(alo), spt_str(ahi)] if alo is not None else None
    v["template_floor_M8"] = floor
    # photometric distance over the adopted range (1 and 2 sigma: UCS 1.4826 MAD, K21 RMS 0.31 mag), and the tension with the
    # host in distance-modulus space: z = (mod_phot - mod_host) / hypot(sigma_calib, sigma_mod_host from the host parallax error)
    if alo is not None and plx:
        e_plx = (h or {}).get("e_Plx") or (float(s["host_e_plx"]) if s.get("host_e_plx") else 0.0)
        mod_h, e_mod_h = 5 * math.log10(100 / plx), 5 / math.log(10) * e_plx / plx
        dist = {}
        for k in range(int(math.floor(alo)), int(math.ceil(ahi)) + 1):
            ent = {}
            if st := stat(k, "mw2"):
                ent["UCS"] = {"M_W2": round(st["median"], 2), "sig": round(st["mad"], 2), "n": st["n"], "mod": w2 - st["median"]}
            if (m21 := k21_mch2(k)) is not None:
                ent["K21"] = {"M_ch2": round(m21, 2), "sig": 0.31, "mod": 0.070888 + 0.99268 * w2 - m21}
            for e in ent.values():
                mod, sg = e.pop("mod"), e["sig"]
                e.update(d_pc=round(10 ** ((mod + 5) / 5), 1), d_1sig=[round(10 ** ((mod - sg + 5) / 5), 1), round(10 ** ((mod + sg + 5) / 5), 1)],
                         d_2sig=[round(10 ** ((mod - 2 * sg + 5) / 5), 1), round(10 ** ((mod + 2 * sg + 5) / 5), 1)],
                         z_vs_host=round((mod - mod_h) / math.hypot(sg, e_mod_h), 2))
            dist[spt_str(k)] = ent
        r1 = [x for e in dist.values() for m in e.values() for x in m["d_1sig"]]
        r2 = [x for e in dist.values() for m in e.values() for x in m["d_2sig"]]
        hd = 1000 / plx
        v["phot_distance"] = {"per_subtype": dist, "range_1sig_pc": [min(r1), max(r1)] if r1 else None, "range_2sig_pc": [min(r2), max(r2)] if r2 else None,
                              "host_dist_pc": round(hd, 1), "host_dist_err_pc": round(hd * e_plx / plx, 1),
                              "consistent": any(abs(m["z_vs_host"]) <= 2 for e in dist.values() for m in e.values())}
    # ---- companion. Gaia DR3 of the target, when present, is decisive (mas/yr precision + own parallax). Otherwise the
    # pipeline-independent PMs (CatWISE, 2MASS->CatWISE) must all agree at p > 0.01, at least one at p > 0.05.
    # confirmed: that, plus our PM at p > 0.05, plus the photometric distance of our type within 2 sigma of the host's.
    # refuted: Gaia (or every independent PM) disagrees at p < 0.001, or the distance disagrees at 2 sigma.
    ours_p = next((p for p in pms if p["source"].startswith("ours")), None)
    indep = [p for p in pms if not p["source"].startswith("ours")]
    gaia_p = next((p for p in indep if p["source"].startswith("Gaia")), None)
    dist_ok = (v.get("phot_distance") or {}).get("consistent")
    if gaia_p:
        pm_ok, pm_bad = gaia_p["p_value"] > 0.05, gaia_p["p_value"] < 1e-3
    else:
        pm_ok = bool(indep) and all(p["p_value"] > 0.01 for p in indep) and any(p["p_value"] > 0.05 for p in indep)
        pm_bad = len(indep) >= 2 and all(p["p_value"] < 1e-3 for p in indep)  # one CatWISE PM alone cannot refute (systematics)
    # distance at the best-fit type alone (2 sigma, UCS or K21): "confirmed" needs it, not just some type in the widened range
    bt = spt_num(best) if best else None
    at_best = (v.get("phot_distance") or {}).get("per_subtype", {}).get(spt_str(math.floor(bt))) if bt is not None else None
    best_ok = bool(at_best) and any(abs(m["z_vs_host"]) <= 2 for m in at_best.values())
    if pm_bad or dist_ok is False:
        comp = "refuted"
    elif pm_ok and ours_p and ours_p["p_value"] > 0.05 and dist_ok and best_ok:
        comp = "confirmed"
    else:
        comp = "not confirmed"
    v["companion"] = {"status": comp, "distance_at_best_type": at_best, "distance_at_best_type_ok_2sig": best_ok,
                      "decisive_pm": gaia_p["source"] if gaia_p else "CatWISE2020 + 2MASS->CatWISE", "independent_pm_ok": pm_ok,
                      "independent_pm_bad": pm_bad, "distance_consistent_2sig": dist_ok}
    v["classification"] = ("first spectrum-based type + companion confirmed" if type_positive and comp == "confirmed" else
                           f"first spectrum-based type, companion {comp}" if type_positive else f"inconclusive ({'; '.join(reasons)})")
    rows.append(v)
    (d / "verdict.json").write_text(json.dumps(v, indent=1, default=float))
    ours = next((p for p in pms if p["source"].startswith("ours")), {})
    print(f"{tag} {s['lit_spt_rothermich']} | {sp['verdict']} {best} tr={tr} det={sp.get('detection_snr')} b5={met['n_bins_snr_gt5']} psf={met['neighbour_psf_used']} "
          f"| var={v.get('variant_bests')} in={v.get('variants_inside_range')} | W1-W2 {col['W1-W2_CatWISE']} {col.get('W1-W2_consistent')} J-W2 {col.get('J-W2')} {col.get('J-W2_consistent')} "
          f"| dmu {ours.get('dmu_total')} chi2 {ours.get('chi2_2dof')} dv {ours.get('dv_tan_kms')} lim {ours.get('bound_limit_kms')} | d {(v.get('phot_distance') or {}).get('range_1sig_pc')} host {v['host']['dist_pc']}")

with open("out/results.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["tag", "name", "rothermich_type", "prob", "verdict", "best", "chi2_red", "type_range", "detection_snr", "n_bins", "bins_snr_gt3", "bins_snr_gt5",
                "photometry", "max_neighbour_frac", "contaminated", "negative_bins", "variant_bests", "variants_inside_range", "W1-W2_CW", "W1-W2_ok", "J-W2", "J-W2_ok",
                "our_pmra", "our_pmdec", "our_pm_err", "dmu_ours", "chi2_ours", "dvtan_ours", "bound_limit_kms", "dmu_catwise", "chi2_catwise", "phot_d_range", "host_d",
                "phot_d_range_2sig", "adopted_type_range", "companion", "classification"])
    for v in rows:
        sp, c = v["spectrum"], v["colour"]
        o = next((p for p in v["pm_vs_host"] if p["source"].startswith("ours")), {})
        cwp = next((p for p in v["pm_vs_host"] if p["source"].startswith("CatWISE")), {})
        mo = v["motion_ours"]
        w.writerow([v["tag"], v["name"], v["rothermich_type"], v["prob"], sp["verdict"], (sp["best"] or {}).get("label"), (sp["best"] or {}).get("chi2_red"),
                    sp["type_range"], sp["detection_snr"], sp["n_bins"], sp["n_bins_snr_gt3"], sp["n_bins_snr_gt5"], sp["photometry"],
                    max((sp["neighbour_frac"] or {0: None}).values(), default=None) if sp["neighbour_frac"] else None, sp["contaminated"], sp["negative_bins"],
                    v.get("variant_bests"), v.get("variants_inside_range"), c["W1-W2_CatWISE"], c.get("W1-W2_consistent"), c.get("J-W2"), c.get("J-W2_consistent"),
                    mo.get("pmra_masyr"), mo.get("pmdec_masyr"), [mo.get("pmra_err_masyr"), mo.get("pmdec_err_masyr")], o.get("dmu_total"), o.get("chi2_2dof"),
                    o.get("dv_tan_kms"), o.get("bound_limit_kms"), cwp.get("dmu_total"), cwp.get("chi2_2dof"),
                    (v.get("phot_distance") or {}).get("range_1sig_pc"), v["host"]["dist_pc"], (v.get("phot_distance") or {}).get("range_2sig_pc"),
                    v["adopted_type_range"], v["companion"]["status"], v["classification"]])
