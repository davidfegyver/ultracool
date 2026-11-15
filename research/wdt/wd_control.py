"""Control: measure the WHITE DWARF's proper motion with the same images and centroiding as the T dwarf
(sequence d7960472debb5523; the WD lies 64" from the grid centre, inside the 181" field) and compare with Gaia DR3.
This calibrates our WISE+SPHEREx astrometric systematics at the same brightness (WD W2 ~ 15) and field.

Run: cd research/wdt && CACHE_DIR=/data/devcache/wdt nice -n 15 ../../.venv/bin/python wd_control.py -> wd_control_out.json
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "backend"))
from app.analysis import FWHM_PX, POS_FLOOR_ARCSEC, _grid_wcs, _motion_groups, _shifted_stack, centroid, fit_motion  # noqa: E402
from app.frames import PIX_ARCSEC, group_by_gap, mjd_to_year, propagate  # noqa: E402
from app.sequences import get_manifest  # noqa: E402

SID = "d7960472debb5523"
WD = dict(ra=358.58382867379, dec=-81.68455055873, pmra=96.033, pmdec=36.288, epoch=2016.0)  # Gaia DR3 (vz_gf21_wd.tsv)
m = get_manifest(SID)
wcs = _grid_wcs(m)
pm_px = (-WD["pmra"] / 1000 / PIX_ARCSEC, WD["pmdec"] / 1000 / PIX_ARCSEC)
groups = [g for g in _motion_groups(m["frames"]) if g[0] != "SPHEREx"]
# SPHEREx: all bands (the WD, Teff 4500 K, is brightest at 1-2 um), one group per survey epoch
sx = sorted([f for f in m["frames"] if f["survey"] == "spherex" and not f.get("flagged")], key=lambda f: f["mjd"])
sxg: dict = {}
for f, g in zip(sx, group_by_gap([f["mjd"] for f in sx], 30)):
    sxg.setdefault(g, []).append(f)
groups += [("SPHEREx", v) for _, v in sorted(sxg.items())]
pts = []
for band, fs in groups:
    ty = float(np.mean([mjd_to_year(f["mjd"]) for f in fs]))
    x0, y0 = wcs.world_to_pixel_values(*propagate(WD["ra"], WD["dec"], WD["pmra"], WD["pmdec"], WD["epoch"], ty))
    c = centroid(_shifted_stack(SID, fs, pm_px, ty), float(x0), float(y0), 3.0, FWHM_PX[band], 3.0)
    if c is None:
        continue
    ra, dec = (float(v) for v in wcs.pixel_to_world_values(c[0], c[1]))
    xi = ((ra - WD["ra"] + 180) % 360 - 180) * math.cos(math.radians(WD["dec"])) * 3600
    eta = (dec - WD["dec"]) * 3600
    # offset from the Gaia-predicted position (arcsec, east/north): the absolute astrometric error per epoch
    rx0, rd0 = propagate(WD["ra"], WD["dec"], WD["pmra"], WD["pmdec"], WD["epoch"], ty)
    pts.append({"band": band, "t": round(ty, 3), "xi": xi, "eta": eta, "snr": round(c[3], 1),
                "err": math.hypot(c[2] * PIX_ARCSEC, POS_FLOOR_ARCSEC[band]),
                "resid_vs_gaia_arcsec": [round(((ra - rx0 + 180) % 360 - 180) * math.cos(math.radians(WD["dec"])) * 3600, 3),
                                         round((dec - rd0) * 3600, 3)]})
out = {"points": pts}
for name, sel in (("WISE only", lambda q: q["band"] != "SPHEREx"), ("WISE+SPHEREx (all bands)", lambda q: True)):
    q = [x for x in pts if sel(x)]
    while True:  # pipeline rule (analysis._robust_fit): drop the worst point while it is > 4 sigma off the line
        fm = fit_motion([x["t"] for x in q], [x["xi"] for x in q], [x["eta"] for x in q], [x["err"] for x in q])
        k = int(np.argmax(fm["resid"] / np.array([x["err"] for x in q])))
        if fm["resid"][k] / q[k]["err"] <= 4 or len(q) <= 3:
            break
        out.setdefault(name + " rejected", []).append([q[k]["band"], q[k]["t"]])
        q = q[:k] + q[k + 1:]
    out[name] = {"pmra": round(fm["pmra"], 1), "pmdec": round(fm["pmdec"], 1), "err": round(fm["pmra_err"], 1),
                 "chi2_red": round(fm["chi2_red"], 2), "n": len(q),
                 "dpmra_vs_gaia": round(fm["pmra"] - WD["pmra"], 1), "dpmdec_vs_gaia": round(fm["pmdec"] - WD["pmdec"], 1)}
r = np.array([x["resid_vs_gaia_arcsec"] for x in pts if abs(x["resid_vs_gaia_arcsec"][0]) < 2])
out["resid_rms_arcsec_per_axis(excluding >2\" outliers)"] = [round(float(np.sqrt(np.mean(r[:, 0] ** 2))), 3),
                                                            round(float(np.sqrt(np.mean(r[:, 1] ** 2))), 3)]
print(json.dumps(out, indent=1))
json.dump(out, open(HERE / "wd_control_out.json", "w"), indent=1)
