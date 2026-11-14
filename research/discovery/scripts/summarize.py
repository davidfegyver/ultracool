"""Collect out/<name>.json into results.csv (one row per verified object)."""
import csv
import json
import math
from pathlib import Path

import numpy as np

SYS_MASYR = 20.0  # per-component systematic floor from the two validation objects (13-38 mas/yr offsets vs literature)
meta = {}
for f in ("run_list.txt", "run_list2.txt", "run_queue.txt"):
    for line in open(f):
        n, ra, dec, pmra, pmdec, ep, des = line.split()
        meta[n] = {"designation": des.replace("_", " "), "ra": float(ra), "dec": float(dec), "cw_pmra": float(pmra), "cw_pmdec": float(pmdec)}
meta["VAL_2M0415"] = {"designation": "2MASS J04151954-0935066 (validation, T8)", "ra": 63.831432, "dec": -9.585187, "cw_pmra": 2193.0, "cw_pmdec": 527.0}

rows = []
for p in sorted(Path("out").glob("*.json")):
    r = json.loads(p.read_text())
    m = meta.get(r["name"], {})
    f = r.get("fit_wise")
    nw = sum(e["survey"] == "wise" for e in r["epochs"])
    ndet = sum(1 for e in r["epochs"] if e["survey"] == "wise" and e.get("target"))
    row = {"name": r["name"], **m, "n_wise_epochs": nw, "n_wise_detected": ndet, "n_ref_stars": r.get("n_ref_stars")}
    if f:
        ea, ed = math.hypot(f["pmra_err"], SYS_MASYR), math.hypot(f["pmdec_err"], SYS_MASYR)
        pm = math.hypot(f["pmra_masyr"], f["pmdec_masyr"])
        pe = math.hypot(f["pmra_masyr"] * ea, f["pmdec_masyr"] * ed) / pm
        d = math.hypot((f["pmra_masyr"] - m.get("cw_pmra", 0)) / ea, (f["pmdec_masyr"] - m.get("cw_pmdec", 0)) / ed)
        row.update(pmra=round(f["pmra_masyr"], 1), pmra_err=round(ea, 1), pmdec=round(f["pmdec_masyr"], 1), pmdec_err=round(ed, 1),
                   pm_total=round(pm, 1), pm_sig=round(pm / pe, 1), plx_mas=round(f["plx_mas"], 0), plx_err=round(f["plx_err"], 0),
                   astrom_chi2r=round(f["chi2_red"], 1), baseline_yr=round(f["baseline_yr"], 1), dev_from_catwise_sigma=round(d, 1))
    s = r["spectrum"]
    b = s.get("binned") or []
    snr = np.array([q["flambda"] / q["err"] for q in b]) if b else np.array([0.0])
    row.update(n_spherex=r["n_spherex"], spec_verdict=s["verdict"], spec_best=s["best"]["label"] if s["best"] else None,
               spec_prob=round(s["best"]["prob"], 2) if s["best"] else None, spec_chi2r=round(s["best"]["chi2_red"], 2) if s["best"] else None,
               spec_runnerup=", ".join(f"{q['label']}({q['chi2_red']:.1f})" for q in s["ranking"][1:4]),
               spec_bins_snr3=int((snr >= 3).sum()), spec_median_snr=round(float(np.median(snr)), 1),
               spec_snr_3p5_5um=round(float(np.median([q["flambda"] / q["err"] for q in b if q["wavelength_um"] > 3.5] or [0])), 1))
    t = r.get("fit_track") or {}
    row.update(trk_n=t.get("n"), trk_pmra=round(t["pmra"], 1) if "pmra" in t else None, trk_pmra_err=round(t["pmra_err"], 1) if "pmra" in t else None,
               trk_pmdec=round(t["pmdec"], 1) if "pmra" in t else None, trk_pmdec_err=round(t["pmdec_err"], 1) if "pmra" in t else None)
    rows.append(row)
keys = list(dict.fromkeys(k for r in rows for k in r))
with open("results.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, keys)
    w.writeheader()
    w.writerows(rows)
for r in rows:
    print({k: r.get(k) for k in ("name", "pmra", "pmra_err", "pmdec", "pmdec_err", "pm_sig", "dev_from_catwise_sigma", "n_wise_detected", "n_wise_epochs",
                                 "spec_best", "spec_chi2r", "spec_bins_snr3", "spec_snr_3p5_5um", "spec_runnerup")})
