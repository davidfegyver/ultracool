"""Faint-source astrometry: average the per-visit W2 stacks into ~2-year deep epochs, Gaussian-centroid each starting
from ONE fixed (static) guess (the 2018 catalog position) so the fit is not steered toward the catalog motion,
correct the per-visit zero point already derived from field stars, and fit PM (no parallax).
Usage: CACHE_DIR=... PYTHONPATH=snap python forced.py <name> [years_per_bin=2]"""
import json
import math
import sys

import numpy as np

from verify import PIX_ARCSEC, centroid, fit_motion
from app.frames import mjd_to_year

name = sys.argv[1]
span = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
r = json.load(open(f"out/{name}.json"))
st = np.load(f"out/{name}_stamps.npz")
ny, nx = st[st.files[0]].shape
x0, y0 = (nx - 1) / 2, (ny - 1) / 2  # grid centre = catalog position propagated to 2018.0
eps = [e for e in r["epochs"] if e["band"] == "W2"]
bins = {}
for e in eps:
    y = mjd_to_year(e["mjd"])
    bins.setdefault(int((y - 2010.0) // span), []).append(e)
pts, rows = [], []
for b, es in sorted(bins.items()):
    zs = []
    for e in es:
        z = st[f"W2_{e['mjd']:.1f}"]
        dx, dy = e.get("zp_offset_px", [0, 0])
        # shift by the field-star zero point (sub-pixel) before averaging: np.roll is integer, so use interpolation
        from scipy.ndimage import shift
        zs.append(shift(np.nan_to_num(z), (-dy, -dx), order=1))
    z = np.mean(zs, axis=0) * math.sqrt(len(zs))  # sigma units of the mean
    c = centroid(z, x0, y0, half=3)
    mjd = float(np.mean([e["mjd"] for e in es]))
    if not c or c[4] < 3:  # require a >= 3-sigma Gaussian peak
        rows.append({"year": mjd_to_year(mjd), "n_visits": len(es), "detected": False})
        continue
    err = max(0.1, math.hypot(c[2], c[3]) / math.sqrt(2) * PIX_ARCSEC)
    pts.append({"mjd": mjd, "xi": -(c[0] - x0) * PIX_ARCSEC, "eta": (c[1] - y0) * PIX_ARCSEC, "err": err})
    rows.append({"year": mjd_to_year(mjd), "n_visits": len(es), "detected": True, "peak_sigma": c[4], "dx_arcsec": pts[-1]["xi"],
                 "dy_arcsec": pts[-1]["eta"], "err_arcsec": err})
    np.save(f"out/{name}_deep_{b}.npy", z)
fit = fit_motion(pts, r["input"]["ra"], r["input"]["dec"], with_plx=False) if len(pts) >= 3 else None
r["fit_deep"] = {"epochs": rows, "fit": fit}
json.dump(r, open(f"out/{name}.json", "w"), default=float)
for q in rows:
    print({k: round(v, 2) if isinstance(v, float) else v for k, v in q.items()})
print(name, "deep-epoch PM:", fit and {k: round(fit[k], 1) for k in ("pmra_masyr", "pmra_err", "pmdec_masyr", "pmdec_err", "chi2_red")},
      "catalog:", r["input"]["pmra"], r["input"]["pmdec"])
