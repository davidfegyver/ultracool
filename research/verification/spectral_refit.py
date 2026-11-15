"""Refit the J2317-6700 SPHEREx binned spectrum against all 47 SPIFF templates and two-template blends.

Run: nice -n 15 /home/paw/Desktop/ultracool/.venv/bin/python research/verification/spectral_refit.py
Inputs: prod_spectrum_now.json (GET /api/sequences/685314abd15e38d9/spectrum, pipeline v5) and
/data/research/discovery/out/J2317-6700.json (research snapshot). Templates: backend/app/data/templates.
Fit = the production one (backend/app/spectral.py classify): analytic scale, template spread added in quadrature.
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "backend"))
from app.spectral import TEMPLATES  # noqa: E402  (read-only import of the vendored templates)


def fit1(lam, f, s, t, use_tu=True):
    m = (lam >= t[0, 0]) & (lam <= t[-1, 0])
    tm, tu = np.interp(lam[m], t[:, 0], t[:, 1]), np.interp(lam[m], t[:, 0], t[:, 2]) * use_tu
    ff, ss = f[m], s[m]
    a = np.sum(ff * tm / ss**2) / np.sum(tm**2 / ss**2)
    for _ in range(2):
        st = np.hypot(ss, a * tu)
        a = np.sum(ff * tm / st**2) / np.sum(tm**2 / st**2)
    return float(np.sum(((ff - a * tm) / np.hypot(ss, a * tu)) ** 2)), int(m.sum())


def fit2(lam, f, s, t1, t2):
    """Non-negative two-component blend (unresolved binary), no template spread; returns chi2, n."""
    lo, hi = max(t1[0, 0], t2[0, 0]), min(t1[-1, 0], t2[-1, 0])
    m = (lam >= lo) & (lam <= hi)
    A = np.vstack([np.interp(lam[m], t[:, 0], t[:, 1]) for t in (t1, t2)]).T / s[m, None]
    b = f[m] / s[m]
    x, *_ = np.linalg.lstsq(A, b, rcond=None)
    if (x < 0).any():  # fall back to the better single component
        return min(float(np.sum((b - A[:, [i]] @ np.linalg.lstsq(A[:, [i]], b, rcond=None)[0]) ** 2)) for i in (0, 1)), int(m.sum())
    return float(np.sum((b - A @ x) ** 2)), int(m.sum())


def table(lam, f, s, title, sel=None):
    if sel is not None:
        lam, f, s = lam[sel], f[sel], s[sel]
    rows = []
    for lab, t in TEMPLATES.items():
        c, n = fit1(lam, f, s, t)
        c0, _ = fit1(lam, f, s, t, use_tu=False)
        rows.append((c, lab, n, c0))
    rows.sort()
    best = rows[0][0]
    print(f"\n== {title}: {len(lam)} bins")
    print("label   chi2   chi2_red  dchi2  | chi2_red without template spread")
    for c, lab, n, c0 in rows[:10]:
        print(f"{lab:7s} {c:6.1f} {c/(n-1):7.2f} {c-best:6.1f}  | {c0/(n-1):6.2f}")
    return {lab: round(c - best, 1) for c, lab, *_ in rows[:10]}


out = {}
spectra = {
    "production_v5": json.load(open(HERE / "prod_spectrum_now.json"))["binned"],
    "research_snapshot": json.load(open("/data/research/discovery/out/J2317-6700.json"))["spectrum"]["binned"],
}
for name, b in spectra.items():
    lam = np.array([x["wavelength_um"] for x in b]); f = np.array([x["flambda"] for x in b]); s = np.array([x["err"] for x in b])
    out[name] = {
        "all": table(lam, f, s, f"{name} all"),
        "1.0-2.5um": table(lam, f, s, f"{name} 1.0-2.5 um only", lam < 2.5),
        "2.5-5.0um": table(lam, f, s, f"{name} 2.5-5.0 um only", lam >= 2.5),
        "s_x1.5": table(lam, f, s * 1.5, f"{name} errors x1.5"),
    }
    # unresolved binaries among T0-T9
    Ts = [f"T{i}" for i in range(10)]
    single = {lab: fit2(lam, f, s, TEMPLATES[lab], TEMPLATES[lab]) for lab in Ts}
    pairs = sorted((fit2(lam, f, s, TEMPLATES[a], TEMPLATES[b])[0], a, b) for a, b in itertools.combinations(Ts, 2))
    smin = min(v[0] for v in single.values())
    print(f"\n== {name}: best two-template blends (no template spread); best single chi2 = {smin:.1f}")
    for c, a, b2 in pairs[:6]:
        print(f"  {a}+{b2}: chi2 {c:.1f} (dchi2 vs best single {c - smin:+.1f})")
    out[name]["blends_top"] = [[a, b2, round(c - smin, 1)] for c, a, b2 in pairs[:6]]

json.dump(out, open(HERE / "spectral_refit_out.json", "w"), indent=1)
