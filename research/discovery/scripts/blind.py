"""Blind self-check astrometry (no catalogue proper motion used anywhere).
verify.py associates per-visit detections with the CatWISE-PM prediction, track.py starts from the CatWISE-PM-predicted
first-epoch position, forced.py centroids at one fixed guess. Here instead every 2-yr W2 deep stack (field-star
zero point applied) is searched for ALL peaks >= 4 sigma; straight-line tracks are built from every pair of detections in
the first two and last two windows (|motion| <= 3"/yr); a track's support is the number of windows with a detection
within 1.5 px of the line. Kept: the best-supported track whose position at the CatWISE epoch lies within 3" of the
CatWISE position (position only). Static vs moving is judged by the significance of the fitted PM.
Usage: PYTHONPATH=snap python blind.py <name> [years_per_bin=2]  -> r["fit_blind"] in out/<name>.json"""
import json
import math
import sys

import numpy as np
from scipy.ndimage import shift

from app.frames import make_grid, mjd_to_year, propagate
from verify import PIX_ARCSEC, detect, fit_motion

name = sys.argv[1]
span = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
r = json.load(open(f"out/{name}.json"))
st = np.load(f"out/{name}_stamps.npz")
i = r["input"]
wcs, shape = make_grid(*propagate(i["ra"], i["dec"], i["pmra"], i["pmdec"], i["epoch_yr"], 2018.0), 0.06)
x0, y0 = (shape[1] - 1) / 2, (shape[0] - 1) / 2
cx, cy = (float(v) for v in wcs.world_to_pixel_values(i["ra"], i["dec"]))  # CatWISE position at its own epoch: no PM
bins = {}
for e in (e for e in r["epochs"] if e["band"] == "W2"):
    bins.setdefault(int((mjd_to_year(e["mjd"]) - 2010.0) // span), []).append(e)
wins = []
for b, es in sorted(bins.items()):
    zs = [shift(np.nan_to_num(st[f"W2_{e['mjd']:.1f}"]), tuple(-v for v in e.get("zp_offset_px", [0, 0])[::-1]), order=1) for e in es]
    z = np.mean(zs, axis=0) * math.sqrt(len(zs))
    mjd = float(np.mean([e["mjd"] for e in es]))
    wins.append({"mjd": mjd, "year": mjd_to_year(mjd), "dets": detect(z, 4.0)})
n = len(wins)
MAXPX = 3.0 / PIX_ARCSEC  # 3"/yr


def support(x_at, y_at):
    used = []
    for w in wins:
        px, py = x_at(w["year"]), y_at(w["year"])
        d = [q for q in w["dets"] if math.hypot(q[0] - px, q[1] - py) < 1.5]
        if d:
            used.append((w, min(d, key=lambda q: math.hypot(q[0] - px, q[1] - py))))
    return used


best = None
for ia in (0, 1):
    for ib in (n - 2, n - 1):
        if ib <= ia:
            continue
        A, B = wins[ia], wins[ib]
        dt = B["year"] - A["year"]
        for a in A["dets"]:
            for b in B["dets"]:
                vx, vy = (b[0] - a[0]) / dt, (b[1] - a[1]) / dt
                if math.hypot(vx, vy) > MAXPX:
                    continue
                ty = i["epoch_yr"]
                if math.hypot(a[0] + vx * (ty - A["year"]) - cx, a[1] + vy * (ty - A["year"]) - cy) * PIX_ARCSEC > 3.0:
                    continue
                used = support(lambda t: a[0] + vx * (t - A["year"]), lambda t: a[1] + vy * (t - A["year"]))
                res = sum(math.hypot(q[0] - (a[0] + vx * (w["year"] - A["year"])), q[1] - (a[1] + vy * (w["year"] - A["year"]))) for w, q in used)
                key = (len(used), -res)
                if best is None or key > best[0]:
                    best = (key, used)
out = {"n_windows": n, "years": [w["year"] for w in wins], "n_dets": [len(w["dets"]) for w in wins]}
if best:
    used = best[1]
    pts = [{"mjd": w["mjd"], "xi": -(q[0] - x0) * PIX_ARCSEC, "eta": (q[1] - y0) * PIX_ARCSEC,
            "err": max(0.1, math.hypot(q[2], q[3]) / math.sqrt(2) * PIX_ARCSEC)} for w, q in used]
    out.update(support=len(used), points=pts, fit=fit_motion(pts, i["ra"], i["dec"], with_plx=False) if len(pts) >= 4 else None)
r["fit_blind"] = out
json.dump(r, open(f"out/{name}.json", "w"), default=float)
f = out.get("fit")
print(name, "blind: windows", n, "support", out.get("support"),
      "PM", f and (round(f["pmra_masyr"]), round(f["pmra_err"]), round(f["pmdec_masyr"]), round(f["pmdec_err"]), round(f["chi2_red"] or 0, 1)),
      "| CatWISE", i["pmra"], i["pmdec"])
