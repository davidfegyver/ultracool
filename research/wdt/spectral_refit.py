"""Refit the WISE J2354-8140 SPHEREx binned spectrum (dev API /spectrum, sequence d7960472debb5523) against the
47 SPIFF templates, in the variants used for J2317/J2358 (research/verification/spectral_refit.py).

Run: cd research/wdt && nice -n 15 ../../.venv/bin/python spectral_refit.py -> spectral_refit_out.json, spectral_refit_stdout.txt
Fit = production (backend/app/spectral.py classify): analytic scale, template spread added in quadrature.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "backend"))
from app.spectral import TEMPLATES  # noqa: E402  (read-only import of the vendored templates)

LOG = []


def p(s=""):
    print(s)
    LOG.append(s)


def fit1(lam, f, s, t, use_tu=True):
    m = (lam >= t[0, 0]) & (lam <= t[-1, 0])
    tm, tu = np.interp(lam[m], t[:, 0], t[:, 1]), np.interp(lam[m], t[:, 0], t[:, 2]) * use_tu
    ff, ss = f[m], s[m]
    a = np.sum(ff * tm / ss**2) / np.sum(tm**2 / ss**2)
    for _ in range(2):
        st = np.hypot(ss, a * tu)
        a = np.sum(ff * tm / st**2) / np.sum(tm**2 / st**2)
    return float(np.sum(((ff - a * tm) / np.hypot(ss, a * tu)) ** 2)), int(m.sum())


def table(lam, f, s, title, sel=None, use_tu=True, top=8):
    if sel is not None:
        lam, f, s = lam[sel], f[sel], s[sel]
    rows = sorted((*fit1(lam, f, s, t, use_tu), lab) for lab, t in TEMPLATES.items())
    best = rows[0][0]
    p(f"\n== {title}: {len(lam)} bins ({'with' if use_tu else 'without'} template spread)")
    p("label     chi2  chi2_red  dchi2")
    for c, n, lab in rows[:top]:
        p(f"{lab:8s} {c:6.1f} {c / (n - 1):7.2f} {c - best:6.1f}")
    ts = {lab: round(c - best, 1) for c, n, lab in rows if lab in [f"T{i}" for i in range(10)] + ["Y0", "Y1"]}
    p("  T/Y dchi2: " + ", ".join(f"{k} {v}" for k, v in sorted(ts.items(), key=lambda kv: (kv[0][0] == 'Y', int(kv[0][1:])))))
    return {"top": [[lab, round(c / (n - 1), 2), round(c - best, 1)] for c, n, lab in rows[:top]], "T_Y_dchi2": ts}


sp = json.load(open(HERE / "dev_spectrum.json"))
b = sp["binned"]
lam = np.array([x["wavelength_um"] for x in b])
f = np.array([x["flambda"] for x in b])
s = np.array([x["err"] for x in b])
snr = f / s
out = {"n_bins": len(b), "snr_median": round(float(np.median(snr)), 2), "snr_max": round(float(snr.max()), 2),
       "n_snr_gt3": int((snr > 3).sum()), "n_snr_gt5": int((snr > 5).sum()), "n_negative": int((f < 0).sum()),
       "snr_by_range": {k: [int(((snr > 3) & sel).sum()), int(sel.sum())] for k, sel in
                        {"1.0-1.6": lam < 1.6, "1.6-2.4": (lam >= 1.6) & (lam < 2.4), "2.4-3.8": (lam >= 2.4) & (lam < 3.8),
                         "3.8-5.0": lam >= 3.8}.items()},
       "pipeline": {k: sp[k] for k in ("verdict", "best", "type_range", "detection_snr", "neighbour_frac", "photometry")}}
p(json.dumps({k: v for k, v in out.items() if k != "pipeline"}))
v = {}
v["all"] = table(lam, f, s, "all")
v["all_no_spread"] = table(lam, f, s, "all", use_tu=False)
v["1.0-2.5um"] = table(lam, f, s, "1.0-2.5 um only", lam < 2.5)
v["1.0-2.5um_no_spread"] = table(lam, f, s, "1.0-2.5 um only", lam < 2.5, use_tu=False)
v["2.5-5.0um"] = table(lam, f, s, "2.5-5.0 um only", lam >= 2.5)
v["2.5-5.0um_no_spread"] = table(lam, f, s, "2.5-5.0 um only", lam >= 2.5, use_tu=False)
v["errors_x_sqrt_chi2r(1.86)"] = table(lam, f, s * np.sqrt(3.475), "errors x sqrt(best chi2_red)")
# neighbour light exceeds the target's in D3-D4 (neighbour_frac 1.26, 1.38): drop 1.6-3.8 um
v["no_1.6-3.8um"] = table(lam, f, s, "without 1.6-3.8 um (D3-D4, neighbour-dominated)", (lam < 1.6) | (lam >= 3.8))
v["snr_gt3_only"] = table(lam, f, s, "S/N > 3 bins only", snr > 3)
out["variants"] = v
json.dump(out, open(HERE / "spectral_refit_out.json", "w"), indent=1)
open(HERE / "spectral_refit_stdout.txt", "w").write("\n".join(LOG) + "\n")
