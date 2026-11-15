"""Our WISE W1/W2 photometry of the validation targets vs AllWISE (allwise_p3as_psd) and CatWISE2020, plus a
field-star test and the J2317 sky-annulus experiment.

    CACHE_DIR=/data/devcache/spectra PYTHONPATH=<backend dir> python wise_check.py

Ours = inverse-variance weighted mean of the visit fluxes that /summary uses (analysis.photometry_lc), Vega mags
with the app's zero points. AllWISE: nearest within 6" of the target propagated to 2010.5 (IRSA Gator).
CatWISE2020: nearest within 10" of the target propagated to 2015.4 (catwise.json, IRSA Gator).
Writes wise_check.json."""
import io
import json
import math
import os
import re

import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io.votable import parse_single_table
from astropy.wcs import WCS

from app import analysis
from app.frames import aperture_flux, mjd_to_year, propagate
from app.psfphot import _propagate
from app.sequences import WISE_R_AP, WISE_R_IN, WISE_R_OUT, get_manifest, load_npy, wise_flux_factor
from app.sources import irsa_gator

HERE = os.path.dirname(os.path.abspath(__file__))
F0 = {"W1": 309.54, "W2": 171.787}


def conv(v):
    if v is np.ma.masked:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return str(v)


def gator(table, ra, dec, r, cols):
    t = parse_single_table(io.BytesIO(irsa_gator(table, ra, dec, r, cols))).to_table()
    return [{k: conv(x[k]) for k in t.colnames} for x in t]


def mag(f, band):
    return -2.5 * math.log10(f / 1e6 / F0[band]) if f and f > 0 else None


def masked_sky_flux(m, cat, band):
    """Mean target visit flux with every CatWISE source (15" radius) masked out of the 50-70" sky annulus."""
    w = WCS(m["grid"]["wcs"])
    c = np.array([(r["ra"], r["dec"], r["pmra"], r["pmdec"], r["epoch"]) for r in cat], float).T
    ny = m["grid"]["height"]
    out = []
    for f in m["frames"]:
        if f["survey"] != "wise" or f["kind"] != "visit" or f["band"] != band or not f.get("magzp") or f["flux_ujy"] is None:
            continue
        img = load_npy(m["id"], f["id"])
        x, y = f["target_px"][0], ny - 1 - f["target_px"][1]
        cx, cy = w.world_to_pixel_values(*_propagate(*c, mjd_to_year(f["mjd"])))
        yy, xx = np.indices(img.shape)
        bm = np.zeros(img.shape, bool)
        for X, Y in zip(cx, cy):
            if math.hypot(X - x, Y - y) < WISE_R_OUT + 6:
                bm |= np.hypot(xx - X, yy - Y) < 15 / 2.75
        n0, _ = aperture_flux(img, x, y, WISE_R_AP, WISE_R_IN, WISE_R_OUT)
        n1, _ = aperture_flux(img, x, y, WISE_R_AP, WISE_R_IN, WISE_R_OUT, bkg_mask=bm)
        k = wise_flux_factor(band, f["magzp"])
        out.append((n0 * k, n1 * k))
    a = np.array(out)
    return float(a[:, 0].mean()), float(a[:, 1].mean())


cw = json.load(open(os.path.join(HERE, "catwise.json")))["rows"]
targets = [json.loads(x) for f in ("targets.jsonl", "extra_targets.jsonl") for x in open(os.path.join(HERE, f))]
rows = []
for o in targets:
    slug = re.sub(r"[^\w+-]+", "_", o["q"]).strip("_")
    meta = os.path.join(HERE, "before", slug, "meta.json")
    if not os.path.exists(meta):
        continue
    m = get_manifest(json.load(open(meta))["sid"])
    lc, source, _ = analysis.photometry_lc(m, analysis.static_sky_flux(m))
    ra, dec = propagate(o["ra"], o["dec"], o["pm"][0], o["pm"][1], o["ep"], 2010.5)
    aw = gator("allwise_p3as_psd", ra, dec, 6, ["designation", "w1mpro", "w2mpro", "w1sigmpro", "w2sigmpro", "cc_flags"])
    aw = min(aw, key=lambda r: r["dist"]) if aw else None
    c = cw.get(o["q"]) or gator("catwise_2020", o["ra"], o["dec"], 5, ["source_name", "w1mpro", "w2mpro"])
    c = min(c, key=lambda r: r["dist"]) if c else None
    r = {"object": o["q"], "slug": slug, "pm_arcsec_yr": math.hypot(*o["pm"]) / 1000, "source": source,
         "gal_b": round(float(SkyCoord(o["ra"], o["dec"], unit="deg").galactic.b.deg), 1),
         "allwise": aw, "catwise": c and {k: c[k] for k in ("source_name", "w1mpro", "w2mpro", "dist")}}
    for b in ("W1", "W2"):
        if not lc or not lc.get(b):
            continue
        f, e = (np.array([p[i] for p in lc[b]]) for i in (1, 2))
        mu, er = analysis._wmean(f, e)
        r[b] = {"flux_ujy": mu, "err_ujy": er, "mag": mag(mu, b), "snr": mu / er, "n_visits": len(f)}
        for name, ref in (("allwise", aw), ("catwise", c)):
            v = ref and ref.get(b.lower() + "mpro")
            if isinstance(v, float) and r[b]["mag"] is not None:
                r[b][f"minus_{name}"] = r[b]["mag"] - v
    if o["q"].startswith("WISE J231728"):
        cat = analysis._catalogs(m)["catwise"]
        r["masked_annulus_experiment"] = {b: dict(zip(("unmasked_mean_ujy", "masked_mean_ujy"), masked_sky_flux(m, cat, b)))
                                          for b in ("W1", "W2")}
    rows.append(r)
    print(slug, {b: {k: round(v, 2) for k, v in r[b].items() if k.startswith(("mag", "minus"))} for b in ("W1", "W2") if b in r}, flush=True)


def field_stars(slug, max_visits=8):
    """Isolated (no other AllWISE source within 16.5"), unflagged AllWISE stars at S/N >= 10 (sigmpro <= 0.11)
    in a field, measured like the target on up to max_visits visit grids, with and without the masked annulus
    -> [(band, allwise_mag, mean flux unmasked, mean flux masked)]."""
    m = get_manifest(json.load(open(os.path.join(HERE, "before", slug, "meta.json")))["sid"])
    w, W = WCS(m["grid"]["wcs"]), m["grid"]["width"]
    ra0, dec0 = (float(v) for v in w.wcs.crval)
    t = gator("allwise_p3as_psd", ra0, dec0, W * 2.75 / math.sqrt(2), ["ra", "dec", "w1mpro", "w2mpro", "w1sigmpro",
                                                                        "w2sigmpro", "cc_flags", "ext_flg"])
    sc = SkyCoord([r["ra"] for r in t], [r["dec"] for r in t], unit="deg")
    cat = analysis._catalogs(m)["catwise"]
    c = np.array([(r["ra"], r["dec"], r["pmra"], r["pmdec"], r["epoch"]) for r in cat], float).T
    out = []
    for band in ("W1", "W2"):
        vis = [f for f in m["frames"] if f["survey"] == "wise" and f["band"] == band and f["kind"] == "visit" and f.get("magzp")]
        vis = [vis[i] for i in np.linspace(0, len(vis) - 1, min(max_visits, len(vis))).astype(int)]
        x, y = w.world_to_pixel_values([r["ra"] for r in t], [r["dec"] for r in t])
        good = [i for i, r in enumerate(t) if (r[band.lower() + "sigmpro"] or 9) <= 0.11 and 26 < x[i] < W - 27
                and 26 < y[i] < W - 27 and str(r["cc_flags"]) in ("0000", "0.0") and r["ext_flg"] == 0
                and np.sum(sc.separation(sc[i]).arcsec < 16.5) == 1]
        fl = {i: [] for i in good}
        for f in vis:
            img = load_npy(m["id"], f["id"])
            k = wise_flux_factor(band, f["magzp"])
            cx, cy = w.world_to_pixel_values(*_propagate(*c, mjd_to_year(f["mjd"])))
            yy, xx = np.indices(img.shape)
            for i in good:
                bm = np.zeros(img.shape, bool)
                for X, Y in zip(cx, cy):
                    if math.hypot(X - x[i], Y - y[i]) < WISE_R_OUT + 6:
                        bm |= np.hypot(xx - X, yy - Y) < 15 / 2.75
                n0, _ = aperture_flux(img, x[i], y[i], WISE_R_AP, WISE_R_IN, WISE_R_OUT)
                n1, _ = aperture_flux(img, x[i], y[i], WISE_R_AP, WISE_R_IN, WISE_R_OUT, bkg_mask=bm)
                fl[i].append((n0 * k, n1 * k))
        out += [(band, t[i][band.lower() + "mpro"], *np.mean(fl[i], axis=0).tolist()) for i in good if fl[i]]
    return out


json.dump({"targets": rows, "field_stars_eps_Ind_B": field_stars("eps_Ind_B")},
          open(os.path.join(HERE, "wise_check.json"), "w"), indent=1)
