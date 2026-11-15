"""SPHEREx per-epoch centroids of WISE J2354-8140 from the dev-API sequence d7960472debb5523 (read-only).

Run: cd research/wdt && CACHE_DIR=/data/devcache/wdt nice -n 15 ../../.venv/bin/python spherex_centroids.py
Mirrors backend/app/analysis.py measure_motion (shifted deep stack per SPHEREx survey epoch, matched-filter
centroid near the CatWISE track), but per band set: D5+D6 (3.8-5 um, where the T dwarf dominates the 8.2"
CatWISE neighbour J235451.78-814043.9) and all bands. Output: spherex_centroids_out.json.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "backend"))
from app.analysis import FWHM_PX, POS_FLOOR_ARCSEC, _grid_wcs, _shifted_stack, _target_px, centroid  # noqa: E402
from app.frames import PIX_ARCSEC, group_by_gap, mjd_to_year  # noqa: E402
from app.sequences import get_manifest  # noqa: E402

SID = "d7960472debb5523"
m = get_manifest(SID)
wcs = _grid_wcs(m)
t = m["target"]
pm_px = (-t["pmra_masyr"] / 1000 / PIX_ARCSEC, t["pmdec_masyr"] / 1000 / PIX_ARCSEC)
sx = sorted([f for f in m["frames"] if f["survey"] == "spherex" and not f.get("flagged")], key=lambda f: f["mjd"])
out = {}
for name, bands in {"D5D6": ("D5", "D6"), "D6": ("D6",), "all": ("D1", "D2", "D3", "D4", "D5", "D6")}.items():
    fs = [f for f in sx if f["band"] in bands]
    groups: dict = {}
    for f, g in zip(fs, group_by_gap([f["mjd"] for f in fs], 30)):
        groups.setdefault(g, []).append(f)
    pts = []
    for g, gf in sorted(groups.items()):
        ty = float(np.mean([mjd_to_year(f["mjd"]) for f in gf]))
        x0, y0 = _target_px(wcs, t, ty)
        stack = _shifted_stack(SID, gf, pm_px, ty)
        c = centroid(stack, x0, y0, 3.0, FWHM_PX["SPHEREx"], 3.0)
        if c is None:
            pts.append({"epoch_yr": ty, "n_frames": len(gf), "detected": False})
            continue
        ra, dec = (float(v) for v in wcs.pixel_to_world_values(c[0], c[1]))
        pts.append({"epoch_yr": round(ty, 4), "mjd": float(np.mean([f["mjd"] for f in gf])), "n_frames": len(gf),
                    "ra": ra, "dec": dec, "snr": round(c[3], 1),
                    "err_stat_arcsec": round(c[2] * PIX_ARCSEC, 3),
                    "err_arcsec": round(math.hypot(c[2] * PIX_ARCSEC, POS_FLOOR_ARCSEC["SPHEREx"]), 3),
                    "offset_from_catwise_track_arcsec": [round((x0 - c[0]) * PIX_ARCSEC, 2), round((c[1] - y0) * PIX_ARCSEC, 2)]})
    out[name] = pts
    print(name, json.dumps(pts, indent=0))
json.dump(out, open(HERE / "spherex_centroids_out.json", "w"), indent=1)
