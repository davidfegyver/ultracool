"""Catalog-free re-association: follow the source from its first-epoch detection, predicting each next epoch from the
track so far (no CatWISE PM used after the start), then fit PM. Guards against confirming a wrong catalog PM.
Usage: python track.py out/<name>.json ..."""
import json
import math
import sys

import numpy as np

PIX = 2.75


def track(r, max_jump_px=2.0):
    eps = sorted((e for e in r["epochs"] if e["survey"] == "wise"), key=lambda e: e["mjd"])
    pts = []
    for e in eps:
        dx, dy = e.get("zp_offset_px", [0, 0])
        dets = [(d[0] - dx, d[1] - dy, d) for d in e["dets"]]
        t = 2000 + (e["mjd"] - 51544.5) / 365.25
        if not pts:
            px, py = e["pred"]
            cand = [c for c in dets if math.hypot(c[0] - px, c[1] - py) < 2.5]
        else:
            if len(pts) >= 3:
                T = np.array([p[0] for p in pts])
                px = np.polyval(np.polyfit(T, [p[1] for p in pts], 1), t)
                py = np.polyval(np.polyfit(T, [p[2] for p in pts], 1), t)
            else:
                px, py = pts[-1][1], pts[-1][2]
            # before the track has 3 points its motion is unknown: allow up to ~2.75"/yr over the gap
            rad = max_jump_px if len(pts) >= 3 else max_jump_px + (t - pts[-1][0])
            cand = [c for c in dets if math.hypot(c[0] - px, c[1] - py) < rad]
        if cand:
            c = min(cand, key=lambda c: math.hypot(c[0] - px, c[1] - py))
            err = max(0.1, math.hypot(c[2][2], c[2][3]) / math.sqrt(2) * PIX)
            pts.append((t, c[0], c[1], err))
    if len(pts) < 6:
        return {"n": len(pts), "n_epochs": len(eps)}
    T = np.array([p[0] for p in pts]) - 2018
    w = 1 / np.array([p[3] for p in pts]) ** 2
    out = {"n": len(pts), "n_epochs": len(eps), "baseline_yr": float(T.max() - T.min())}
    for key, col, sign in (("pmra", 1, -1), ("pmdec", 2, 1)):
        y = sign * np.array([p[col] for p in pts]) * PIX
        A = np.vstack([np.ones_like(T), T]).T
        cov = np.linalg.inv(A.T @ (A * w[:, None]))
        sol = cov @ (A.T @ (w * y))
        chi2r = float(np.sum(w * (y - A @ sol) ** 2) / (len(y) - 2))
        out[key] = float(sol[1] * 1000)
        out[key + "_err"] = float(math.sqrt(cov[1, 1] * max(1, chi2r)) * 1000)
    return out


if __name__ == "__main__":
    for p in sys.argv[1:]:
        r = json.load(open(p))
        t = track(r)
        r["fit_track"] = t
        json.dump(r, open(p, "w"), default=float)
        print(r["name"], {k: round(v, 1) if isinstance(v, float) else v for k, v in t.items()})
