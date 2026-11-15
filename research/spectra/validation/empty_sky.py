"""Error calibration of the neighbour-aware PSF photometry (app/psfphot.py) on empty sky.

    CACHE_DIR=/data/devcache/spectra PYTHONPATH=<backend dir> python empty_sky.py

For every validation field: 12 random 'clear' positions >= 4 grid px (11") from any CatWISE2020 source and 12
'near' positions 2-4 px (5.5-11") from one, fitted like a target in up to 200 SPHEREx frames (psfphot with
cache=False). A source-free position has true flux 0, so flux / error should scatter with unit spread.
Writes empty_sky.json: rows [slug, kind, band, flux_ujy, flux_err_ujy (calibrated), nb_ap_ujy, raw_err_ujy]."""
import json
import os
import re

import numpy as np
from astropy.wcs import WCS

from app import analysis, psfphot
from app.sequences import get_manifest

HERE = os.path.dirname(os.path.abspath(__file__))


def positions(cx, cy, width, lo, hi, n, rng):
    out = []
    for _ in range(20000):
        if len(out) == n:
            break
        x, y = rng.uniform(13, width - 14, 2)
        d = np.min(np.hypot(cx - x, cy - y))
        if lo <= d < hi:
            out.append((x, y))
    return out


rows = []
for line in [x for f in ("targets.jsonl", "extra_targets.jsonl") for x in open(os.path.join(HERE, f))]:
    o = json.loads(line)
    slug = re.sub(r"[^\w+-]+", "_", o["q"]).strip("_")
    meta = os.path.join(HERE, "before", slug, "meta.json")
    if not os.path.exists(meta):
        continue
    m = get_manifest(json.load(open(meta))["sid"])
    cat = analysis._catalogs(m)["catwise"] or []
    if not cat:
        continue
    w = WCS(m["grid"]["wcs"])
    c = np.array([(r["ra"], r["dec"]) for r in cat])
    cx, cy = w.world_to_pixel_values(c[:, 0], c[:, 1])
    rng = np.random.default_rng(0)
    sx = [f for f in m["frames"] if f["survey"] == "spherex" and not f["flagged"]]
    sx = [sx[i] for i in np.linspace(0, len(sx) - 1, min(len(sx), 200)).astype(int)]
    for kind, lo, hi in (("clear", 4, np.inf), ("near", 2, 4)):
        for x, y in positions(cx, cy, m["grid"]["width"], lo, hi, 12, rng):
            ra, dec = w.pixel_to_world_values(x, y)
            mm = {**m, "frames": sx, "target": {"ra": float(ra), "dec": float(dec), "pmra_masyr": 0.0,
                                                "pmdec_masyr": 0.0, "epoch_yr": 2015.4}}
            ph = psfphot.photometry(mm, cat, cache=False)
            for f in sx:
                p = ph.get(f["id"])
                if p:
                    rows.append([slug, kind, f["band"], p["flux_ujy"], p["flux_err_ujy"], p["nb_ap_ujy"],
                                 p.get("raw_err_ujy")])
    print(slug, len(rows), flush=True)
json.dump(rows, open(os.path.join(HERE, "empty_sky.json"), "w"))
