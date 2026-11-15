"""Independent refit of the J2358-5218 SPHEREx binned spectrum against all 47 SPIFF templates.

Run: nice -n 15 /home/paw/Desktop/ultracool/.venv/bin/python research/verification/J2358/spectral_refit.py
Input: research/discovery2/out/J2358-5218/spectrum.json (dev API /api/sequences/10cd5c77eacd8c7d/spectrum, pipeline v5),
plus a fresh GET of the same endpoint saved as dev_spectrum_now.json. Templates: backend/app/data/templates
(imported read-only). Fit = production one (analytic scale, template spread in quadrature), adapted from
research/verification/spectral_refit.py.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "backend"))
from app.spectral import TEMPLATES  # noqa: E402

LETTER = {"M": 0, "L": 10, "T": 20, "Y": 30}
FIELD = [k for k in TEMPLATES if " " not in k and k[0] in "MLTY"]  # field-gravity standards only


def num(lab):
    return LETTER[lab[0]] + float(lab[1:])


def fit1(lam, f, s, t, use_tu=True):
    m = (lam >= t[0, 0]) & (lam <= t[-1, 0])
    tm, tu = np.interp(lam[m], t[:, 0], t[:, 1]), np.interp(lam[m], t[:, 0], t[:, 2]) * use_tu
    ff, ss = f[m], s[m]
    a = np.sum(ff * tm / ss**2) / np.sum(tm**2 / ss**2)
    for _ in range(2):
        st = np.hypot(ss, a * tu)
        a = np.sum(ff * tm / st**2) / np.sum(tm**2 / st**2)
    return float(np.sum(((ff - a * tm) / np.hypot(ss, a * tu)) ** 2)), int(m.sum())


def table(lam, f, s, title, use_tu=True, labels=None, show=8):
    rows = sorted((*fit1(lam, f, s, TEMPLATES[k], use_tu), k) for k in (labels or TEMPLATES))
    best = rows[0][0]
    print(f"\n== {title}: {len(lam)} bins, template spread {'on' if use_tu else 'off'}")
    for c, n, k in rows[:show]:
        print(f"  {k:7s} chi2 {c:6.1f}  chi2_red {c/(n-1):5.2f}  dchi2 {c-best:6.1f}")
    return [[k, round(c / (n - 1), 3), round(c - best, 1)] for c, n, k in rows[:show]]


def curve(lam, f, s, use_tu):
    """chi2 versus field-standard subtype (M8..T2) for the chi2-curve figure in the report."""
    out = {}
    for k in sorted(FIELD, key=num):
        if num(k) <= 22:
            c, n = fit1(lam, f, s, TEMPLATES[k], use_tu)
            out[k] = round(c, 1)
    return out


def bootstrap(lam, f, s, use_tu, n=500, seed=1):
    """Resample bins with replacement; distribution of the best field-gravity standard."""
    rng = np.random.default_rng(seed)
    from collections import Counter
    cnt = Counter()
    for _ in range(n):
        i = rng.integers(0, len(lam), len(lam))
        i = np.sort(i)
        cnt[min(FIELD, key=lambda k: fit1(lam[i], f[i], s[i], TEMPLATES[k], use_tu)[0])] += 1
    return dict(cnt.most_common())


out = {}
for name, path in {"evidence_spectrum_json": REPO / "research/discovery2/out/J2358-5218/spectrum.json",
                   "dev_api_now": HERE / "dev_spectrum_now.json"}.items():
    if not path.exists():
        continue
    b = json.load(open(path))["binned"]
    lam = np.array([x["wavelength_um"] for x in b]); f = np.array([x["flambda"] for x in b]); s = np.array([x["err"] for x in b])
    snr = f / s
    o = out[name] = {"n_bins": len(lam), "lam_range": [float(lam.min()), float(lam.max())],
                     "snr_median": round(float(np.median(snr)), 1), "snr_max": round(float(snr.max()), 1),
                     "n_snr_gt3": int((snr > 3).sum()), "n_snr_gt5": int((snr > 5).sum()), "n_negative": int((f < 0).sum())}
    print(f"\n######## {name}: {o}")
    nir, mir = lam < 2.5, lam >= 2.5
    o["all"] = table(lam, f, s, "all")
    o["all_no_spread"] = table(lam, f, s, "all", use_tu=False)
    o["1.0-2.5_spread"] = table(lam[nir], f[nir], s[nir], "1.0-2.5 um")
    o["1.0-2.5_no_spread"] = table(lam[nir], f[nir], s[nir], "1.0-2.5 um", use_tu=False)
    o["2.5-5.0_spread"] = table(lam[mir], f[mir], s[mir], "2.5-5.0 um")
    o["2.5-5.0_no_spread"] = table(lam[mir], f[mir], s[mir], "2.5-5.0 um", use_tu=False)
    o["err_x1.5"] = table(lam, f, s * 1.5, "errors x1.5")
    o["field_only"] = table(lam, f, s, "field-gravity standards only", labels=FIELD)
    hi = snr > 5
    o["snr_gt5_only"] = table(lam[hi], f[hi], s[hi], "S/N>5 bins only")
    o["chi2_curve_spread"] = curve(lam, f, s, True)
    o["chi2_curve_no_spread"] = curve(lam, f, s, False)
    print("\nchi2 curve (spread on): ", o["chi2_curve_spread"])
    print("chi2 curve (spread off):", o["chi2_curve_no_spread"])
    o["bootstrap_field_spread"] = bootstrap(lam, f, s, True)
    o["bootstrap_field_no_spread"] = bootstrap(lam, f, s, False)
    print("bootstrap best field standard (spread on): ", o["bootstrap_field_spread"])
    print("bootstrap best field standard (spread off):", o["bootstrap_field_no_spread"])

json.dump(out, open(HERE / "spectral_refit_out.json", "w"), indent=1, ensure_ascii=False)
