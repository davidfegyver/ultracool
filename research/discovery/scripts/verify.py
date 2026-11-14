"""Independent verification of one brown-dwarf candidate with the Ultracool Browser pipeline (snapshot in ./snap).
Usage: CACHE_DIR=... PYTHONPATH=snap python verify.py <name> <ra> <dec> <pmra> <pmdec> <epoch_yr>
Writes out/<name>.json (+ out/<name>_stamps.npz). Astrometry: per-visit W1/W2 stacks of ALL WISE exposures
(not the 8 the app uses), Gaussian centroids, per-visit zero-point tied to field stars, PM+parallax LSQ fit."""
import json
import math
import sys
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from astropy.coordinates import SkyCoord, get_body_barycentric
from astropy.time import Time
import astropy.units as u
from scipy import ndimage
from scipy.optimize import curve_fit

from app import sequences as S
from app.frames import PIX_ARCSEC, deep_stack, group_by_gap, make_grid, mjd_to_year, propagate
from app.sources import NoOverlap, query_frames, read_section
from app.spectral import classify

warnings.filterwarnings("ignore")
OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
POOL = ThreadPoolExecutor(6)
MAX_PER_VISIT = 40


def gauss(xy, a, x0, y0, s, c):
    x, y = xy
    return a * np.exp(-((x - x0) ** 2 + (y - y0) ** 2) / (2 * s * s)) + c


def centroid(z, x, y, half=4):
    """2-D Gaussian fit on a (2*half+1)^2 cutout around integer (x, y) -> (x, y, ex, ey, peak) or None."""
    xi, yi = int(round(x)), int(round(y))
    ny, nx = z.shape
    if not (half <= xi < nx - half and half <= yi < ny - half):
        return None
    cut = z[yi - half:yi + half + 1, xi - half:xi + half + 1]
    if not np.isfinite(cut).all():
        return None
    yy, xx = np.mgrid[yi - half:yi + half + 1, xi - half:xi + half + 1]
    try:
        p, cov = curve_fit(gauss, (xx.ravel(), yy.ravel()), cut.ravel(),
                           p0=[cut.max(), x, y, 1.0, 0.0], bounds=([0, x - 3, y - 3, 0.4, -5], [np.inf, x + 3, y + 3, 4, 5]))
    except Exception:
        return None
    res = cut.ravel() - gauss((xx.ravel(), yy.ravel()), *p)
    rms = float(np.std(res))
    e = np.sqrt(np.diag(cov))
    return float(p[1]), float(p[2]), float(e[1]), float(e[2]), float(p[0]), rms


def detect(z, thresh=6.0):
    """Local maxima above thresh sigma, then Gaussian centroids."""
    zz = np.nan_to_num(z, nan=0)
    peaks = (zz == ndimage.maximum_filter(zz, size=5)) & (zz > thresh)
    out = []
    for y, x in zip(*np.nonzero(peaks)):
        c = centroid(z, x, y)
        if c and abs(c[0] - x) < 1.5 and abs(c[1] - y) < 1.5:
            out.append(c)
    return out


def stack(frames, wcs, shape, target):
    def rd(f):
        try:
            return read_section(f, wcs, shape, target)["img"]
        except NoOverlap:
            return None
        except Exception as e:  # noqa: BLE001
            print("read fail", f.stem, e, flush=True)
            return None
    imgs = [i for i in POOL.map(rd, frames) if i is not None]
    return (deep_stack(imgs), len(imgs)) if imgs else (None, 0)


def parallax_factors(mjd, ra, dec):
    e = get_body_barycentric("earth", Time(mjd, format="mjd")).xyz.to_value(u.au)
    a, d = math.radians(ra), math.radians(dec)
    X, Y, Z = e
    return X * math.sin(a) - Y * math.cos(a), X * math.cos(a) * math.sin(d) + Y * math.sin(a) * math.sin(d) - Z * math.cos(d)


def fit_motion(pts, ra, dec, with_plx=True):
    """pts: [{mjd, xi, eta, err}] arcsec -> PM (mas/yr), parallax (mas), errors rescaled by sqrt(chi2_red) if > 1."""
    if len(pts) < 4:
        return None
    t = np.array([mjd_to_year(p["mjd"]) - 2018.0 for p in pts])
    pf = np.array([parallax_factors(p["mjd"], ra, dec) for p in pts])
    rows, b, w = [], [], []
    for i, p in enumerate(pts):
        rows.append([1, 0, t[i], 0] + ([pf[i, 0]] if with_plx else []))
        rows.append([0, 1, 0, t[i]] + ([pf[i, 1]] if with_plx else []))
        b += [p["xi"], p["eta"]]
        w += [1 / p["err"] ** 2] * 2
    A, b, w = np.array(rows), np.array(b), np.array(w)
    cov = np.linalg.inv(A.T @ (A * w[:, None]))
    sol = cov @ (A.T @ (w * b))
    chi2 = float(np.sum(w * (b - A @ sol) ** 2))
    dof = len(b) - len(sol)
    scale = max(1.0, chi2 / dof) if dof > 0 else 1.0
    err = np.sqrt(np.diag(cov) * scale)
    out = {"pmra_masyr": sol[2] * 1000, "pmdec_masyr": sol[3] * 1000, "pmra_err": err[2] * 1000, "pmdec_err": err[3] * 1000,
           "chi2_red": chi2 / dof if dof > 0 else None, "n": len(pts),
           "baseline_yr": float(t.max() - t.min()), "resid": (b - A @ sol).reshape(-1, 2).tolist()}
    if with_plx:
        out["plx_mas"], out["plx_err"] = sol[4] * 1000, err[4] * 1000
    pm = math.hypot(out["pmra_masyr"], out["pmdec_masyr"])
    pe = math.hypot(out["pmra_masyr"] * out["pmra_err"], out["pmdec_masyr"] * out["pmdec_err"]) / pm if pm else None
    out["pm_total_masyr"], out["pm_total_err"] = pm, pe
    return {k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in out.items()}


def main(name, ra, dec, pmra, pmdec, epoch):
    t0 = time.time()
    res = {"name": name, "input": {"ra": ra, "dec": dec, "pmra": pmra, "pmdec": pmdec, "epoch_yr": epoch}}
    # 1. the app's own sequence: SPHEREx forced photometry -> spectrum, plus SPHEREx grid images
    req = S.SeqRequest(ra=ra, dec=dec, pmra_masyr=pmra, pmdec_masyr=pmdec, epoch_yr=epoch, fov_deg=0.06)
    sid = S.start(req)
    while S.JOBS.get(sid):
        S.JOBS[sid].result() if sid in S.JOBS else None
        time.sleep(1)
    man = S.get_manifest(sid)
    res["seq_id"], res["seq_status"] = sid, man["status"]
    sx = [f for f in man["frames"] if f["survey"] == "spherex"]
    res["n_spherex"] = len(sx)
    spec = classify(man["frames"])
    res["spectrum"] = spec
    print(name, "sequence", sid, man["status"], len(sx), "spherex frames", spec["verdict"], spec["best"], f"{time.time()-t0:.0f}s", flush=True)

    # 2. astrometry on all WISE exposures per visit
    p = S._params(req)
    ra_c, dec_c = propagate(p["ra"], p["dec"], p["pmra"], p["pmdec"], p["epoch_yr"], 2018.0)
    wcs, shape = make_grid(ra_c, dec_c, p["fov"])
    raw = query_frames(*wcs.wcs.crval)
    pred = lambda mjd: wcs.world_to_pixel_values(*propagate(ra, dec, pmra, pmdec, epoch, mjd_to_year(mjd)))
    epochs = []  # {mjd, band, survey, dets:[...], target_pred:(x,y)}
    stamps = {}
    for band in ("W2", "W1"):
        fs = sorted((f for f in raw if f.survey == "wise" and f.band == band), key=lambda f: f.mjd)
        groups = {}
        for g, f in zip(group_by_gap([f.mjd for f in fs], 10), fs):
            groups.setdefault(g, []).append(f)
        for g, mem in groups.items():
            idx = sorted(set(np.linspace(0, len(mem) - 1, min(len(mem), MAX_PER_VISIT)).round().astype(int)))
            mem = [mem[i] for i in idx]
            mjd = float(np.median([f.mjd for f in mem]))
            z, n = stack(mem, wcs, shape, propagate(ra, dec, pmra, pmdec, epoch, mjd_to_year(mjd)))
            if z is None:
                continue
            epochs.append({"mjd": mjd, "band": band, "survey": "wise", "n_exp": n, "dets": detect(z), "pred": [float(v) for v in pred(mjd)]})
            stamps[f"{band}_{mjd:.1f}"] = z.astype(np.float32)
    # SPHEREx epoch stacks, long-wavelength frames where brown dwarfs are brightest
    sxl = [f for f in sx if f["wavelength_um"] and f["wavelength_um"] >= 3.8]
    for g in sorted(set(f["epoch_index"] for f in sxl)):
        mem = [f for f in sxl if f["epoch_index"] == g]
        imgs = [np.load(S.seq_dir(sid) / "npy" / f"{f['id']}.npy") for f in mem]
        z = deep_stack(imgs)
        mjd = float(np.median([f["mjd"] for f in mem]))
        epochs.append({"mjd": mjd, "band": "SX>3.8um", "survey": "spherex", "n_exp": len(mem), "dets": detect(z), "pred": [float(v) for v in pred(mjd)]})
        stamps[f"SX_{mjd:.1f}"] = z.astype(np.float32)
    np.savez_compressed(OUT / f"{name}_stamps.npz", **stamps)

    # master list of field sources from WISE W2 epochs: cluster detections within 1.5 px
    master = []
    for e in epochs:
        if e["survey"] != "wise":
            continue
        for d in e["dets"]:
            for m in master:
                if math.hypot(m[0] - d[0], m[1] - d[1]) < 1.5:
                    m[2].append(d); break
            else:
                master.append([d[0], d[1], [d]])
    nw = sum(e["survey"] == "wise" for e in epochs)
    ref = [(np.median([d[0] for d in m[2]]), np.median([d[1] for d in m[2]])) for m in master if len(m[2]) >= 0.6 * nw]
    # the target itself (and any mover) is not a reference: drop refs within 6 px of any predicted target position
    track = np.array([e["pred"] for e in epochs])
    ref = [r for r in ref if np.min(np.hypot(track[:, 0] - r[0], track[:, 1] - r[1])) > 6]
    res["n_ref_stars"] = len(ref)

    pts = []
    for e in epochs:
        dets = e["dets"]
        offs = []
        for rx, ry in ref:
            dd = [(d[0] - rx, d[1] - ry) for d in dets if math.hypot(d[0] - rx, d[1] - ry) < 1.5]
            if dd:
                offs.append(dd[0])
        dx, dy = (np.median(offs, axis=0) if len(offs) >= 3 else (0.0, 0.0))
        e["zp_offset_px"], e["n_ref"] = [float(dx), float(dy)], len(offs)
        px, py = e["pred"]
        cand = [d for d in dets if math.hypot(d[0] - px, d[1] - py) < 2.5]  # 6.9" from the CatWISE-PM prediction
        if not cand:
            e["target"] = None
            continue
        d = min(cand, key=lambda d: math.hypot(d[0] - px, d[1] - py))
        x, y = d[0] - dx, d[1] - dy
        w = wcs.pixel_to_world(x, y)
        c0 = SkyCoord(ra_c, dec_c, unit="deg")
        xi, eta = c0.spherical_offsets_to(w)
        # floors: WISE visit-stack centroids ~0.1" (validation chi2), SPHEREx 6.15" pixels: 0.4" until calibrated
        err = max(0.1 if e["survey"] == "wise" else 0.4, math.hypot(d[2], d[3]) / math.sqrt(2) * PIX_ARCSEC)
        e["target"] = {"x": x, "y": y, "ra": float(w.ra.deg), "dec": float(w.dec.deg), "peak_sigma": d[4], "err_arcsec": err}
        pts.append({"mjd": e["mjd"], "band": e["band"], "survey": e["survey"], "xi": float(xi.arcsec), "eta": float(eta.arcsec), "err": err})
    res["epochs"] = epochs
    res["points"] = pts
    wise = [q for q in pts if q["survey"] == "wise"]
    res["fit_wise"] = fit_motion(wise, ra, dec)
    res["fit_wise_noplx"] = fit_motion(wise, ra, dec, with_plx=False)
    res["fit_all"] = fit_motion(pts, ra, dec)
    # control: same fit for every reference star seen in >= 60% of W2 epochs (should be ~0 mas/yr)
    ctrl = []
    w2 = [e for e in epochs if e["band"] == "W2"]
    for rx, ry in ref:
        sp = []
        for e in w2:
            dd = [d for d in e["dets"] if math.hypot(d[0] - rx, d[1] - ry) < 1.5]
            if dd:
                d = dd[0]
                sp.append({"mjd": e["mjd"], "xi": -(d[0] - e["zp_offset_px"][0]) * PIX_ARCSEC, "eta": (d[1] - e["zp_offset_px"][1]) * PIX_ARCSEC,
                           "err": max(0.03, math.hypot(d[2], d[3]) / math.sqrt(2) * PIX_ARCSEC), "peak": d[4]})
        f = fit_motion(sp, ra, dec, with_plx=False) if len(sp) >= 0.6 * len(w2) else None
        if f:
            ctrl.append({"x": rx, "y": ry, "peak": float(np.median([s["peak"] for s in sp])), "pmra": f["pmra_masyr"], "pmdec": f["pmdec_masyr"],
                         "pm_err": math.hypot(f["pmra_err"], f["pmdec_err"]) / math.sqrt(2)})
    res["control_stars"] = ctrl
    res["seconds"] = time.time() - t0
    (OUT / f"{name}.json").write_text(json.dumps(res, default=float))
    fw = res["fit_wise"]
    print(name, "WISE PM", fw and {k: round(fw[k], 1) for k in ("pmra_masyr", "pmra_err", "pmdec_masyr", "pmdec_err", "plx_mas", "plx_err", "chi2_red")},
          "n", fw and fw["n"], "refs", len(ref), f"{res['seconds']:.0f}s", flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], *map(float, a[1:6]))
