"""Science summary of a sequence (proper motion, W1-W2 colour, variability, spectrum) and a search for every
moving source in the field. Works on the cached grid frames (npy) and the manifest photometry."""
import hashlib
import io
import json
import logging
import math
import os
import urllib.parse
import urllib.request
import warnings
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io.votable import parse_single_table
from astropy.timeseries import LombScargle
from astropy.wcs import WCS
from fastapi import APIRouter
from photutils.centroids import centroid_2dg, centroid_quadratic
from photutils.detection import find_peaks
from scipy.ndimage import binary_dilation, gaussian_filter, label, maximum_filter
from scipy.ndimage import shift as nd_shift
from scipy.spatial import cKDTree

from . import config, ucd
from .frames import PIX_ARCSEC, aperture_flux, clipped_mean, deep_stack, group_by_gap, mjd_to_year, propagate
from .sequences import (WISE_F0_JY, WISE_R_AP, WISE_R_IN, WISE_R_OUT, get_manifest, load_npy, seq_dir,
                        wise_flux_factor)
from .sources import WISE_ART_R_ARCSEC, bright_star_artifacts, irsa_gator, query_frames
from .spectral import DOUBTFUL, EARLY_LABELS, NO_DETECTION, WARMER, classify, demote

log = logging.getLogger("ultracool.analysis")
router = APIRouter()

WINDOW_YR = 2.0  # WISE co-add windows for astrometry (4 visits each; unTimely/CatWISE use 1-yr pairs)
FWHM_PX = {"W1": 6.1 / PIX_ARCSEC, "W2": 6.4 / PIX_ARCSEC, "SPHEREx": 11.0 / PIX_ARCSEC}
# astrometric floor per co-add (WISE L1b is tied to 2MASS/Gaia to ~0.1-0.2"; SPHEREx 6.15" pixels)
POS_FLOOR_ARCSEC = {"W1": 0.2, "W2": 0.2, "SPHEREx": 0.6}
MIN_SNR = 4.0
PM_PRIOR_MASYR = 300.0  # how far an object with unknown/zero catalog PM may have drifted, per year
# Known-PM search: the catalog track, give or take the catalog's errors. Positions/PMs are anchored on ~2010-2016
# data (WISE, Gaia), so errors grow away from CAT_EPOCH_YR; the PM error is not in the manifest, so assume
# 3% + 20 mas/yr (SIMBAD vs CatWISE differ by 6% for W1534-1043). Detections must be S/N >= 3 within
# max(1.5 px, 3 sigma) of the prediction: a 3-sigma peak that close to a known track is rarely noise.
CAT_EPOCH_YR = 2015.0
CAT_PM_FRAC, CAT_PM_FLOOR, CAT_POS_ERR = 0.03, 20.0, 0.3
TIGHT_R_PX = 1.5
TIGHT_MIN_SNR = 3.0
OUTLIER_SIGMA = 4.0
BLEND_FLUX_RATIO = 0.2  # another source carrying >= 20% of the target's flux at its spot shifts the centroid
STATIC_SEP_ARCSEC = 2 * 8.25  # target this far from its spot: its aperture there holds only static sky
VAR_MIN_SNR = 5.0  # median per-visit S/N a band needs before its scatter can mean variability
SX_AP_ARCSEC = 2.0 * 6.15  # SPHEREx photometry aperture radius (sources.SX_R_AP native pixels)
CONTAM_FRAC = 0.25  # neighbours adding > 25% of the target's light make a template fit describe them
# a crowded-field sky over-subtraction drives many channels negative: for pure noise, P(z < -2.5) = 0.6%, so
# >= 3 such channels among ~90 happens by chance ~2% of the time
NEG_BIN_SIGMA, NEG_BINS_MAX = -2.5, 3
REF_YR = 2018.0  # grid-centre epoch; mover positions are given at this epoch
# Variability: per-visit repeatability floor. NEOWISE single-exposure photometry repeats to ~1-2% for bright
# stars (Mainzer+2014); our visit co-adds with 8.25" apertures, MAGZP drifts and (for movers) subtracted
# neighbour light scatter more: 5% keeps faint brown dwarfs (W0855, W1534) from reading as variable.
PHOT_FLOOR = 0.05
# profile fits of saturated stars in the NEOWISE single-exposure catalog drift and scatter by 0.1-0.2 mag
# between visits (Barnard's Star, a constant star, scatters 7-28% per visit in W1)
SATURATED_FLOOR = 0.15
ASTEROID_MAX_ECL_LAT = 35.0  # deg; known asteroids beyond this are rare
ASTEROID_MAX_VISITS = 40  # SkyBoT calls per sequence (4 in parallel, ~3 s each)
VAR_CHI2 = 3.0  # irregular = chi2_red > ~3 without a significant periodogram peak
LS_MIN_EPOCHS = 8
LS_FAP = 0.01
CADENCE_D = 365.25  # NEOWISE visits every ~6 months: periods at 1/k yr are cadence aliases
# W1-W2 colour classes (Vega), cut at the Kirkpatrick et al. 2021 (ApJS 253, 7; Table 13, Fig. 14h) polynomial
# W1-W2 = 0.22668 + 0.029069 s - 0.0046379 s^2 + 0.00057825 s^3 (s = 0 at L0, 10 at T0, 20 at Y0; rms 0.28 mag):
# L dwarfs 0.23-0.6 like stars (0-0.3), T0 0.63, T5 1.57, T8 2.62, Y0 3.58; W0855-0714 ~3.5 or more.
W12_RED, W12_VERY_RED, W12_EXTREME = 0.6, 1.6, 2.6  # T0, T5, T8
COLOR_CLASSES = ((W12_EXTREME, "extremely red (Y/late-T dwarf-like)"), (W12_VERY_RED, "very red (T dwarf-like)"),
                 (W12_RED, "red (L/T dwarf-like)"))
# W1-W2 (Vega) loci, median and star-to-star sigma: M8 0.22 +- 0.07 (2,260 dwarfs), L0-L2 0.26-0.27 +- 0.05-0.07
# (Schmidt et al. 2015, AJ 149, 158, Table 4); T and Y dwarfs are redder still (above). Ordinary M0-M4 dwarfs sit
# at 0.01-0.15 (dal Ponte et al. 2023, MNRAS 522, 1951), hotter stars near 0. Used by colour_doubt.
W12_LOCUS_M8, W12_LOCUS_L, W12_LOCUS_SIGMA, W12_DOUBT_SIGMA = 0.22, 0.26, 0.07, 2.0
MOVER_MAX_PM_ARCSEC = 12.0  # Barnard's Star 10.4"/yr is the fastest known
MOVER_SIG = 5.0  # PM significance a track needs (errors inflated by sqrt(chi2_red))
MOVER_DET_SNR = 4.5  # detection threshold in the 2-yr W2 stacks; the vetting below removes what this lets in
MOVER_MATCH_PX = 1.5
MOVER_MAX_CHI2 = 3.0  # positions must follow a straight line within their errors
MOVER_MIN_FRAC = 0.6  # detected in >= max(4, 60%) of the windows
# image vetting compares each detection with stacks of windows when a real mover was >= 1.5 FWHM elsewhere:
# what sits at the spot there is static. A mover slower than 1.5 FWHM (9.6") over the baseline (< ~0.7"/yr
# over 14 yr) cannot be told from a static source this way and is not reported.
MOVER_SEP_FWHM = 1.5
DIPOLE_RATIO, ON_STATIC_RATIO = 0.3, 0.5  # per-frame flux of the static source / the detection's
STATIC_PX = 1.0  # detections recurring within 1 px in half the windows are static
# A track on WISE's predicted spike/halo/ghost artifacts of a bright star in >= this fraction of the sampled
# exposures is that star's artifact (moving with it if the star moves). eps Ind field: its 4 artifact tracks sit
# on them in 59-80% of 44 exposures, eps Ind A itself 7%, eps Ind B 0%; a real source crossing a spike or halo
# does so in a few visits only.
ARTIFACT_FRAC = 0.4


def _num(x):
    """JSON-safe float: NaN/inf -> None, numpy scalars -> float."""
    if x is None:
        return None
    x = float(x)
    return x if math.isfinite(x) else None


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, (int, np.integer)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        return _num(o)
    return o


def _rows(votable_bytes):
    """VOTable -> list of plain dicts (masked/NaN -> None, bytes -> str)."""
    tab = parse_single_table(io.BytesIO(votable_bytes)).to_table()
    out = []
    for r in tab:
        d = {}
        for k in tab.colnames:
            v = r[k]
            if np.ma.is_masked(v):
                v = None
            elif isinstance(v, bytes):
                v = v.decode()
            elif isinstance(v, np.generic):
                v = v.item()
            d[k] = _num(v) if isinstance(v, float) else v
        out.append(d)
    return out


def _grid_wcs(m):
    return WCS(m["grid"]["wcs"])


def _offsets_arcsec(ra, dec, ra0, dec0):
    return ((np.asarray(ra) - ra0 + 180) % 360 - 180) * math.cos(math.radians(dec0)) * 3600, (np.asarray(dec) - dec0) * 3600


# ---------------------------------------------------------------- astrometry


def _fill_nan(z, iters=4):
    """Fill saturated (NaN) star cores from their rim so centroids and peak finding see one blob."""
    z = np.array(z, dtype=np.float64)
    for _ in range(iters):
        bad = ~np.isfinite(z)
        if not bad.any():
            break
        z[bad] = maximum_filter(np.where(bad, -np.inf, z), size=3)[bad]
    z[~np.isfinite(z)] = 0.0
    return z


def _snr_map(z, fwhm_px):
    """Matched-filter S/N of point sources in an image in sigma units (white-noise approximation)."""
    s = fwhm_px / 2.355
    return gaussian_filter(z, s) * math.sqrt(4 * math.pi) * s


def _saturated_cores(z):
    """Saturated stars: enclosed NaN blobs (>= 3 px) ringed by bright pixels -> [(x, y, n_pix)]."""
    lab, n = label(~np.isfinite(z))
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    out = []
    for i in range(1, n + 1):
        if i in edge:
            continue
        blob = lab == i
        ys, xs = np.nonzero(blob)
        if len(xs) < 3:
            continue
        rim = binary_dilation(blob) & ~blob & np.isfinite(z)
        if rim.any() and np.median(z[rim]) > 50:
            out.append((float(xs.mean()), float(ys.mean()), len(xs)))
    return out


def centroid(z, x0, y0, r_search, fwhm_px, min_snr=MIN_SNR):
    """Brightest point source (a local maximum of the matched-filter S/N, so not the wing of a neighbour
    outside the circle) within r_search px of (x0, y0) in a sigma-unit image -> (x, y, err_px, snr) or None
    if nothing above min_snr. err = sqrt(2) sigma_psf / SNR.
    A saturated star (NaN core) is located by the centre of its core, good to ~0.3 px."""
    sat = [c for c in _saturated_cores(z) if math.hypot(c[0] - x0, c[1] - y0) <= r_search]
    if sat:
        cx, cy, _ = max(sat, key=lambda c: c[2])
        return cx, cy, 0.3, math.inf
    zf = _fill_nan(z)
    snr = _snr_map(zf, fwhm_px)
    yy, xx = np.indices(z.shape)
    inside = (np.hypot(xx - x0, yy - y0) <= r_search) & (snr >= maximum_filter(snr, size=3))
    if not inside.any():
        return None
    i = np.argmax(np.where(inside, snr, -np.inf))
    py, px = np.unravel_index(i, z.shape)
    peak = float(snr[py, px])
    if peak < min_snr:
        return None
    h = max(2, int(math.ceil(fwhm_px)))
    ya, yb, xa, xb = max(0, py - h), min(z.shape[0], py + h + 1), max(0, px - h), min(z.shape[1], px + h + 1)
    box = zf[ya:yb, xa:xb]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            cx, cy = centroid_2dg(box - np.median(box))
        except Exception:  # noqa: BLE001 - degenerate box
            cx = cy = math.nan
    if not (math.isfinite(cx) and math.isfinite(cy)) or math.hypot(cx + xa - px, cy + ya - py) > h:
        cx, cy = px - xa, py - ya
    return cx + xa, cy + ya, math.sqrt(2) * fwhm_px / 2.355 / peak, peak


def fit_motion(t_yr, xi, eta, err):
    """Weighted straight-line fit of offsets (arcsec) vs time -> dict with pm (mas/yr), errors, reference
    position at the weighted mean epoch t0. Errors are scaled up by sqrt(chi2_red) when the scatter says so."""
    t, xi, eta, w = (np.asarray(a, float) for a in (t_yr, xi, eta, np.asarray(err, float) ** -2))
    t0 = float(np.sum(w * t) / np.sum(w))
    dt = t - t0
    sw, swtt = np.sum(w), np.sum(w * dt * dt)
    res = {}
    chi2 = 0.0
    for name, y in (("ra", xi), ("dec", eta)):
        a = np.sum(w * y) / sw
        b = np.sum(w * dt * y) / swtt
        chi2 += float(np.sum(w * (y - a - b * dt) ** 2))
        res[name] = (a, b)
    dof = max(1, 2 * len(t) - 4)
    scale = math.sqrt(max(1.0, chi2 / dof))
    sb = scale / math.sqrt(swtt)
    pmra, pmdec = res["ra"][1] * 1000, res["dec"][1] * 1000
    pm = math.hypot(pmra, pmdec)
    pm_err = sb * 1000
    return {"t0": t0, "xi0": res["ra"][0], "eta0": res["dec"][0], "pmra": pmra, "pmdec": pmdec,
            "pmra_err": pm_err, "pmdec_err": pm_err, "pos_err": scale / math.sqrt(sw), "chi2_red": chi2 / dof,
            "pm": pm, "significance": pm / pm_err if pm_err > 0 else 0.0,
            "resid": np.hypot(xi - res["ra"][0] - res["ra"][1] * dt, eta - res["dec"][0] - res["dec"][1] * dt)}


def _motion_groups(frames):
    """Epoch groups for astrometry: WISE per band in 2-yr windows (per visit when the target is bright or
    saturated: more epochs, no smearing), SPHEREx per survey epoch (all bands where the target is seen, all
    bands if its photometry is unusable everywhere, e.g. saturated)."""
    groups: dict[tuple, list] = {}
    wise = [f for f in frames if f["survey"] == "wise" and f["kind"] == "visit"]
    snr_w = [f["flux_ujy"] / f["flux_err_ujy"] for f in wise if f["flux_ujy"] is not None and f["flux_err_ujy"]]
    bright = (sum("SATURATED" in f["flag_names"] for f in wise) >= 0.5 * max(1, len(wise))
              or (snr_w and np.median(snr_w) >= 30))
    for f in wise:
        key = f["id"] if bright else int((mjd_to_year(f["mjd"]) - 2010) // WINDOW_YR)
        groups.setdefault((f["band"], key), []).append(f)
    sx = [f for f in frames if f["survey"] == "spherex"]
    snr: dict[str, list] = {}
    for f in sx:
        if f["flux_ujy"] is not None and f["flux_err_ujy"]:
            snr.setdefault(f["band"], []).append(f["flux_ujy"] / f["flux_err_ujy"])
    bands = {b for b, v in snr.items() if np.median(v) >= 3} if snr else {f["band"] for f in sx}
    sx = [f for f in sx if f["band"] in bands]
    for f, g in zip(sx, group_by_gap([f["mjd"] for f in sx], 30)):
        groups.setdefault(("SPHEREx", g), []).append(f)
    return [(k[0], v) for k, v in sorted(groups.items(), key=lambda kv: np.mean([f["mjd"] for f in kv[1]]))]


def _shifted_stack(sid, fs, pm_px_yr, t_mid):
    """Deep stack of frames shifted along the assumed motion to the group's mean epoch (no smearing)."""
    imgs = []
    for f in fs:
        img = load_npy(sid, f["id"])
        dt = mjd_to_year(f["mjd"]) - t_mid
        dx, dy = pm_px_yr[0] * dt, pm_px_yr[1] * dt
        imgs.append(nd_shift(img, (-dy, -dx), order=1, cval=np.nan) if abs(dx) + abs(dy) > 0.05 else img)
    return deep_stack(imgs)


def _robust_fit(pts, rejected):
    """Fit; while the worst point is > OUTLIER_SIGMA off the line (its own error, not chi2-scaled), drop it."""
    while True:
        fit = fit_motion([p["_t"] for p in pts], [p["_xi"] for p in pts], [p["_eta"] for p in pts],
                         [p["err_arcsec"] for p in pts])
        norm = fit["resid"] / np.array([p["err_arcsec"] for p in pts])
        k = int(np.argmax(norm))
        if norm[k] <= OUTLIER_SIGMA or len(pts) <= 3:
            return pts, fit
        rejected.append({**_public(pts[k]), "reason": f"off the track by {norm[k]:.0f} sigma"})
        pts = pts[:k] + pts[k + 1:]


def _public(p):
    return {k: v for k, v in p.items() if not k.startswith("_")}


def measure_motion(m):
    """Proper motion from per-epoch centroids. With a catalog PM the target is looked for only near the
    catalog track (a faint mover must not latch onto a static neighbour), epochs where it sits on another
    source are dropped, bands where it is mostly undetected are dropped, then a straight line is fitted with
    outlier rejection and a second pass searches around the fitted track (adding SPHEREx)."""
    sid = m["id"]
    t = m["target"]
    wcs = _grid_wcs(m)
    ra0, dec0 = (float(v) for v in wcs.wcs.crval)
    groups = _motion_groups(m["frames"])
    cat = {"pmra_masyr": t["pmra_masyr"], "pmdec_masyr": t["pmdec_masyr"]}
    pm_cat = math.hypot(t["pmra_masyr"], t["pmdec_masyr"])
    out = {"status": "insufficient data", "pmra_masyr": None, "pmdec_masyr": None, "pmra_err_masyr": None,
           "pmdec_err_masyr": None, "pm_total_arcsec_yr": None, "significance_sigma": None, "baseline_yr": None,
           "n_epochs": 0, "catalog": cat, "consistent_with_catalog": None, "verdict": "insufficient data",
           "recovered": False, "track_snr": None, "undetected_bands": [], "points": [], "rejected_points": []}
    if pm_cat:
        out["track_snr"] = _track_snr(m, wcs, ra0, dec0)
    if len(groups) < 3:
        return out
    cx0, cy0 = wcs.wcs.crpix[0] - 1, wcs.wcs.crpix[1] - 1
    blend_cache: dict = {}

    def predict_cat(ty):
        return _offsets_arcsec(*propagate(t["ra"], t["dec"], t["pmra_masyr"], t["pmdec_masyr"], t["epoch_yr"], ty),
                               ra0, dec0)

    def measure(model, use_groups, rejected):
        pm_mas = (model["pmra"], model["pmdec"]) if model else (t["pmra_masyr"], t["pmdec_masyr"])
        pm_px = (-pm_mas[0] / 1000 / PIX_ARCSEC, pm_mas[1] / 1000 / PIX_ARCSEC)  # grid x runs west
        pts, tried = [], {}
        for band, fs in use_groups:
            ty = float(np.mean([mjd_to_year(f["mjd"]) for f in fs]))
            if model:
                dt = ty - model["t0"]
                pxi, peta = model["xi0"] + model["pmra"] / 1000 * dt, model["eta0"] + model["pmdec"] / 1000 * dt
                sig = math.hypot(model["pos_err"], model["pmra_err"] / 1000 * abs(dt))
                r_search, min_snr = max(TIGHT_R_PX, 3 * sig / PIX_ARCSEC), TIGHT_MIN_SNR
            elif pm_cat:
                pxi, peta = predict_cat(ty)
                sig = (CAT_PM_FRAC * pm_cat + CAT_PM_FLOOR) / 1000 * abs(ty - CAT_EPOCH_YR) + CAT_POS_ERR
                r_search, min_snr = max(TIGHT_R_PX, 3 * sig / PIX_ARCSEC), TIGHT_MIN_SNR
            else:  # unknown motion: the brightest source near the given position
                pxi, peta = predict_cat(ty)
                sig = PM_PRIOR_MASYR / 1000 * abs(ty - CAT_EPOCH_YR)
                r_search, min_snr = max(6.0, 3 * sig) / PIX_ARCSEC, MIN_SNR
            r_search = min(r_search, 30.0 / PIX_ARCSEC)
            tried[band] = tried.get(band, 0) + 1
            stack = _shifted_stack(sid, fs, pm_px, ty)
            c = centroid(stack, cx0 - pxi / PIX_ARCSEC, cy0 + peta / PIX_ARCSEC, r_search, FWHM_PX[band], min_snr)
            if c is None:
                continue
            ra, dec = (float(v) for v in wcs.pixel_to_world_values(c[0], c[1]))
            xi, eta = _offsets_arcsec(ra, dec, ra0, dec0)
            p = {"mjd": float(np.mean([f["mjd"] for f in fs])), "band": band, "ra": ra, "dec": dec,
                 "err_arcsec": math.hypot(c[2] * PIX_ARCSEC, POS_FLOOR_ARCSEC[band]), "snr": min(c[3], 1e4),
                 "_t": ty, "_xi": float(xi), "_eta": float(eta), "_epoch": (band == "SPHEREx", round(ty / WINDOW_YR))}
            ratio = None
            if math.isfinite(c[3]) and band != "SPHEREx":
                ratio = _blend_ratio(m, blend_cache, band, fs, ty, c, math.hypot(*pm_mas) / 1000)
            if ratio is not None and ratio > BLEND_FLUX_RATIO:
                rejected.append({**_public(p), "reason": f"blended: other sources at this spot carry {ratio:.0%} of its flux"})
                continue
            pts.append(p)
        for band, n in tried.items():  # mostly undetected band: its few "detections" are noise or neighbours
            got = [p for p in pts if p["band"] == band]
            if got and len(got) < 0.5 * n:
                rejected += [{**_public(p), "reason": f"{band}: target detected in only {len(got)} of {n} epochs"} for p in got]
                pts = [p for p in pts if p["band"] != band]
        return pts

    rejected: list = []
    pts = measure(None, [g for g in groups if g[0] != "SPHEREx"] if pm_cat else groups, rejected)
    if len(pts) >= 3:
        pts, fit = _robust_fit(pts, rejected)
        rejected = []  # second pass re-measures every epoch around the fitted track
        pts2 = measure(fit, groups, rejected)
        if len(pts2) >= 3:
            pts, fit = _robust_fit(pts2, rejected)
    out["rejected_points"] = rejected
    out["points"] = [_public(p) for p in pts]
    out["n_epochs"] = n_epochs = len({p["_epoch"] for p in pts})
    if len(pts) < 3:
        return out
    # WISE bands in which the track was followed in no epoch: aperture flux there belongs to neighbours
    out["undetected_bands"] = sorted({g[0] for g in groups if g[0] in ("W1", "W2")} - {p["band"] for p in pts})
    years = [p["_t"] for p in pts]
    baseline = max(years) - min(years)
    out.update({"status": "ok", "pmra_masyr": fit["pmra"], "pmdec_masyr": fit["pmdec"],
                "pmra_err_masyr": fit["pmra_err"], "pmdec_err_masyr": fit["pmdec_err"],
                "pm_total_arcsec_yr": fit["pm"] / 1000, "significance_sigma": fit["significance"],
                "baseline_yr": baseline, "chi2_red": fit["chi2_red"]})
    if n_epochs < 3 or baseline < 2:
        out["status"] = "insufficient data"
        return out
    # single-epoch dipoles are pointing-jitter artifacts (Backyard Worlds): >= 3 epochs over >= 2 yr, >= 3 sigma
    moving = fit["significance"] >= 3
    if not pm_cat:
        out.update(recovered=True, verdict="moving" if moving else "not moving")
        return out
    # the catalog PM uncertainty is not in the manifest: assume CAT_PM_FRAC of it + CAT_PM_FLOOR
    s_cat = CAT_PM_FRAC * pm_cat + CAT_PM_FLOOR
    d = math.hypot(fit["pmra"] - t["pmra_masyr"], fit["pmdec"] - t["pmdec_masyr"]) / math.hypot(fit["pmra_err"], s_cat)
    out.update(consistent_with_catalog=d < 3, recovered=d < 3, catalog_offset_sigma=d)
    if moving:
        out["verdict"] = "moving"
    elif d < 3:
        out["verdict"] = "not moving"
    # else no motion measured although the catalog says there should be: we followed something else
    return out


def _blend_ratio(m, cache, band, fs, ty, c, pm_arcsec_yr):
    """Flux of whatever else sits at the target's spot, as a fraction of the target's flux: the same band's
    visits from years when the target was >= 1.5 FWHM away, stacked, measured at its position. None when the
    target moves too slowly for such years to exist."""
    if pm_arcsec_yr <= 0:
        return None
    dt_min = 1.5 * FWHM_PX[band] * PIX_ARCSEC / pm_arcsec_yr
    if dt_min > 6:
        return None
    others = [f for f in m["frames"] if f["survey"] == "wise" and f["kind"] == "visit" and f["band"] == band
              and abs(mjd_to_year(f["mjd"]) - ty) >= dt_min]
    if len(others) < 2:
        return None
    key = tuple(sorted(f["id"] for f in others))
    if key not in cache:
        cache[key] = _snr_map(_fill_nan(deep_stack([load_npy(m["id"], f["id"]) for f in others])), FWHM_PX[band])
    snr = cache[key]
    s = snr[min(snr.shape[0] - 1, max(0, round(c[1]))), min(snr.shape[1] - 1, max(0, round(c[0])))]
    # stacked S/N scales as flux x sqrt(frames): compare per-frame flux
    return max(0.0, float(s)) / math.sqrt(len(others)) / (c[3] / math.sqrt(len(fs)))


def _track_snr(m, wcs, ra0, dec0):
    """Shift-and-stack all W2 visits along the catalog proper motion to REF_YR: S/N of the target there.
    Confirms a faint mover that single epochs cannot follow."""
    t = m["target"]
    fs = [f for f in m["frames"] if f["survey"] == "wise" and f["kind"] == "visit" and f["band"] == "W2"]
    if len(fs) < 2:
        return None
    pm_px = (-t["pmra_masyr"] / 1000 / PIX_ARCSEC, t["pmdec_masyr"] / 1000 / PIX_ARCSEC)
    snr = _snr_map(_fill_nan(_shifted_stack(m["id"], fs, pm_px, REF_YR)), FWHM_PX["W2"])
    xi, eta = _offsets_arcsec(*propagate(t["ra"], t["dec"], t["pmra_masyr"], t["pmdec_masyr"], t["epoch_yr"], REF_YR),
                              ra0, dec0)
    x, y = wcs.wcs.crpix[0] - 1 - xi / PIX_ARCSEC, wcs.wcs.crpix[1] - 1 + eta / PIX_ARCSEC
    yy, xx = np.indices(snr.shape)
    near = np.hypot(xx - x, yy - y) <= TIGHT_R_PX
    return float(snr[near].max()) if near.any() else None


# ---------------------------------------------------------------- photometry: colour and variability


def wise_lightcurve(frames, sky=None):
    """{band: [(mjd, flux_ujy, err_ujy)]} from unflagged WISE visit frames with a measurement. sky: optional
    {frame_id: (flux, err)} of other sources inside the aperture, subtracted where it is significant (> 3
    sigma; elsewhere subtracting would only add noise); visits without an entry are then left out. Visits
    whose error is > 5x the band's median are failed co-adds (few good exposures, halos) and are dropped."""
    lc: dict[str, list] = {}
    for f in frames:
        if f["survey"] == "wise" and f["kind"] == "visit" and not f["flagged"] and f["flux_ujy"] is not None \
                and f["flux_err_ujy"] and f["flux_err_ujy"] > 0:
            flux, err = f["flux_ujy"], f["flux_err_ujy"]
            if sky:
                if f["id"] not in sky:
                    continue
                s, se = sky[f["id"]]
                if abs(s) > 3 * se:
                    flux, err = flux - s, math.hypot(err, se)
            lc.setdefault(f["band"], []).append((f["mjd"], flux, err))
    for b, pts in lc.items():
        e_med = float(np.median([p[2] for p in pts]))
        lc[b] = [p for p in pts if p[2] <= 5 * e_med]
    return lc


def static_sky_flux(m):
    """For a fast mover: the flux that static sources (background stars, galaxies) put into its aperture at
    each visit, measured on a co-add of the same band's visits from years when the target was >= STATIC_SEP
    away -> {frame_id: (flux_ujy, err_ujy)}; {} when it moves too slowly for such years to exist. Without
    this, a faint mover's light curve and colour track whatever it happens to pass over."""
    t = m["target"]
    pm = math.hypot(t["pmra_masyr"], t["pmdec_masyr"]) / 1000
    if pm <= 0 or STATIC_SEP_ARCSEC / pm > 6:
        return {}
    dt_min = STATIC_SEP_ARCSEC / pm
    visits = [f for f in m["frames"] if f["survey"] == "wise" and f["kind"] == "visit"]
    ny = m["grid"]["height"]
    imgs, skies, out = {}, {}, {}
    for f in visits:
        if f["flux_ujy"] is None or f.get("magzp") is None:
            continue
        ty = mjd_to_year(f["mjd"])
        key = tuple(sorted(g["id"] for g in visits if g["band"] == f["band"] and abs(mjd_to_year(g["mjd"]) - ty) >= dt_min))
        if len(key) < 2:
            continue
        if key not in skies:
            skies[key] = clipped_mean([imgs.setdefault(i, load_npy(m["id"], i)) for i in key])
        x, y = f["target_px"][0], ny - 1 - f["target_px"][1]
        net, err = aperture_flux(skies[key], x, y, WISE_R_AP, WISE_R_IN, WISE_R_OUT)
        if math.isfinite(net):
            k = wise_flux_factor(f["band"], f["magzp"])
            out[f["id"]] = (net * k, err * k)
    return out


def _wmean(fl, er):
    w = er ** -2
    mu = float(np.sum(w * fl) / np.sum(w))
    err = float(1 / math.sqrt(np.sum(w)))
    if len(fl) > 2:  # a variable or badly-calibrated source: the scatter, not the formal error, sets the error
        err = max(err, float(np.std(fl, ddof=1) / math.sqrt(len(fl))))
    return mu, err


def measure_color(lc, w1_undetected=False):
    """W1-W2 (Vega). With >= 3 visits detected in both bands: median of the per-visit colours (robust for
    variables, whose W1 and W2 rise and fall together); else from the weighted-mean fluxes. A W1 flux below
    3 sigma, or w1_undetected (the astrometry found no source at the target's track in W1, so any W1
    aperture flux belongs to neighbours), gives a lower limit from the 2-sigma W1 upper limit."""
    out = {"w1_w2": None, "w1_w2_err": None, "w1_w2_is_lower_limit": False, "verdict": "insufficient data"}
    if not lc.get("W1") or not lc.get("W2"):
        return out
    w2 = {round(p[0]): p for p in lc["W2"]}
    per_visit = [(-2.5 * math.log10(p1[1] / WISE_F0_JY["W1"]) + 2.5 * math.log10(p2[1] / WISE_F0_JY["W2"]),
                  1.0857 * math.hypot(p1[2] / p1[1], p2[2] / p2[1]))
                 for p1 in lc["W1"] if (p2 := w2.get(round(p1[0]))) and p1[1] >= 3 * p1[2] and p2[1] >= 3 * p2[2]]
    if len(per_visit) >= 3 and not w1_undetected:
        cs, es = np.array(per_visit).T
        c = float(np.median(cs))
        out.update(w1_w2=c, w1_w2_err=max(1.253 * float(np.std(cs)), float(np.median(es))) / math.sqrt(len(cs)))
        return {**out, "verdict": _color_class(c)}
    (f1, e1), (f2, e2) = (_wmean(np.array([p[1] for p in lc[b]]), np.array([p[2] for p in lc[b]])) for b in ("W1", "W2"))
    if f2 / e2 < 5:
        return out
    if f1 / e1 >= 3 and not w1_undetected:
        c = -2.5 * math.log10(f1 / WISE_F0_JY["W1"]) + 2.5 * math.log10(f2 / WISE_F0_JY["W2"])
        out.update(w1_w2=c, w1_w2_err=1.0857 * math.hypot(e1 / f1, e2 / f2))
    else:  # W1 not detected: 2-sigma upper limit on W1 -> lower limit on the colour
        c = -2.5 * math.log10((max(f1, 0) + 2 * e1) / WISE_F0_JY["W1"]) + 2.5 * math.log10(f2 / WISE_F0_JY["W2"])
        out.update(w1_w2=c, w1_w2_is_lower_limit=True)
    # a lower limit only classifies when it already clears a class boundary
    out["verdict"] = "insufficient data" if out["w1_w2_is_lower_limit"] and c < W12_RED else _color_class(c)
    return out


def _color_class(c):
    return next((name for lo, name in COLOR_CLASSES if c >= lo), "normal star colors")


def _periodogram(t, mag, dmag):
    """Lomb-Scargle best period outside the cadence aliases -> (period_d, fap, alias_warning, alternatives)
    or None. alternatives: periods whose power is within 30% of the best and that the half-year visit cadence
    cannot tell apart from it (f +- 1/yr, f +- 2/yr): e.g. R Dra's 245 d and ~710 d look alike in NEOWISE."""
    span = float(t.max() - t.min())
    if len({round(x) for x in t}) < LS_MIN_EPOCHS or span <= 60:
        return None
    ls = LombScargle(t, mag, dmag)
    # >= 3 cycles in the span: a 2-cycle "period" is a trend, and long periods are where the half-year
    # cadence folds real periods to (AL Boo's 166.7 d shows up at ~1900 d = 1/(1/166.7 - 2/yr))
    fmin, fmax = 3 / span, 1 / 30
    freq, power = ls.autopower(minimum_frequency=fmin, maximum_frequency=fmax, samples_per_peak=10)
    # NEOWISE visits every ~half year: power at harmonics of 1/yr is window function and scan-direction
    # systematics, not the star. Search outside them (one resolution element, 1/span, each side: wider
    # zones swallowed AL Boo's true 166.7 d next to the 182.6 d harmonic); warn when the highest peak sat there.
    harmonics = np.arange(1, 13) / CADENCE_D
    alias = np.min(np.abs(freq[:, None] - harmonics), axis=1) < 1 / span
    if alias.all():
        return None
    k = int(np.argmax(np.where(alias, -np.inf, power)))
    fap = float(ls.false_alarm_probability(power[k], minimum_frequency=fmin, maximum_frequency=fmax))
    alts = []
    for fa in {abs(freq[k] + s * j / CADENCE_D) for s in (-1, 1) for j in (1, 2)}:
        if fmin <= fa <= fmax and np.min(np.abs(fa - harmonics)) >= 1 / span:
            # the partner peak, refined on a fine local grid
            fg = np.linspace(fa - 1 / span, fa + 1 / span, 41)
            pg = ls.power(fg)
            p = float(1 / fg[int(np.argmax(pg))])
            if pg.max() >= 0.7 * power[k] and all(abs(p / q - 1) > 0.03 for q in [1 / freq[k], *alts]):
                alts.append(p)
    return float(1 / freq[k]), fap, bool(alias[int(np.argmax(power))]), sorted(alts)


def classify_variability(lc, floor=PHOT_FLOOR):
    """lc: {band: [(mjd, flux, err)]} -> chi2_red about the weighted mean per band (errors with a repeatability
    floor), robust amplitude, Lomb-Scargle per band on magnitudes (lowest false-alarm probability wins, times
    the number of bands searched: one bad band, e.g. deeply saturated W2, must not hide the other)."""
    bands, pgrams = {}, []
    for b, pts in sorted(lc.items()):
        if len(pts) < 3:
            continue
        t, f, e = (np.array(v, float) for v in zip(*pts))
        snr = float(np.median(f / e))
        mu = float(np.sum(f / e**2) / np.sum(1 / e**2))
        e = np.hypot(e, floor * abs(mu))
        mu = float(np.sum(f / e**2) / np.sum(1 / e**2))
        z2 = ((f - mu) / e) ** 2
        chi2 = float(np.sum(z2) / (len(f) - 1))
        # one deviant visit (a bad co-add, an artifact, a passing neighbour) does not make a variable star:
        # the verdict uses chi2 without the worst point (real variables deviate in many visits)
        chi2_robust = float((np.sum(z2) - z2.max()) / (len(f) - 2)) if len(f) >= 6 else chi2
        p5, p95 = np.percentile(f, [5, 95])
        bands[b] = {"n": len(f), "chi2_red": chi2, "chi2_red_without_worst": chi2_robust,
                    "amplitude_mag": 2.5 * math.log10(p95 / p5) if p5 > 0 else None, "median_snr": snr}
        pos = f > 0
        if snr >= VAR_MIN_SNR and pos.sum() >= LS_MIN_EPOCHS and (
                pg := _periodogram(t[pos], -2.5 * np.log10(f[pos]), 1.0857 * e[pos] / f[pos])):
            pgrams.append(pg)
    out = {"bands": bands, "verdict": "insufficient data", "period_days": None, "fap": None,
           "period_alias_warning": False, "period_alternatives_days": []}
    # faint bands: noise, residual neighbour light and background errors dominate; judge only well-measured bands
    usable = [v for v in bands.values() if v["n"] >= 5 and v["median_snr"] >= VAR_MIN_SNR]
    if not usable:
        return out
    variable = any(v["chi2_red_without_worst"] > VAR_CHI2 for v in usable)
    if pgrams:
        period, fap, alias, alts = min(pgrams, key=lambda p: p[1])
        out["fap"] = min(1.0, fap * len(pgrams))
        if out["fap"] < LS_FAP:  # the alias warning only qualifies a period we actually report
            out.update(period_days=period, period_alternatives_days=alts, period_alias_warning=alias or bool(alts))
    # a period at FAP < 1% is itself a detection of variability (R Dra's catalog points scatter little
    # about the mean once the 15% saturated-star floor is applied, yet fold cleanly)
    out["verdict"] = ("periodic variable" if out["period_days"] is not None else
                      "irregular variable" if variable else "constant")
    return out


def _ext_cached(key, fetch):
    """Result of an external query, shared by every sequence that asks the same physical question (lesson
    field and plain search of one star): CACHE_DIR/ext/<sha1 of key>.json. fetch() raising (service down)
    caches nothing, so the next call retries."""
    path = config.CACHE_DIR / "ext" / f"{hashlib.sha1(json.dumps(key, sort_keys=True).encode()).hexdigest()}.json"
    if path.exists():
        return json.loads(path.read_text())
    res = fetch()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(_clean(res)))
    tmp.replace(path)
    return res


def _target_key(t):
    """The target's track, rounded to well below what changes a query (0.36", 0.1 mas/yr)."""
    return [round(t["ra"], 4), round(t["dec"], 4), round(t["pmra_masyr"], 1), round(t["pmdec_masyr"], 1), t["epoch_yr"]]


def _catalog_rows(m):
    """Single-exposure profile-fit detections of the target: AllWISE multi-epoch photometry (2010-11) and
    NEOWISE (2014-24), one IRSA cone per 2-yr window around the PM-propagated position, then only detections
    within 3" of the position predicted at their own mjd."""
    t = m["target"]
    windows = sorted({int((mjd_to_year(f["mjd"]) - 2010) // WINDOW_YR) for f in m["frames"] if f["survey"] == "wise"})
    return _ext_cached({"q": "wise_catalog_rows", "target": _target_key(t), "windows": windows},
                       lambda: _fetch_catalog_rows(t, windows))


def _fetch_catalog_rows(t, windows):
    pm = math.hypot(t["pmra_masyr"], t["pmdec_masyr"]) / 1000
    rows = []
    for w in windows:
        ty = 2010 + (w + 0.5) * WINDOW_YR
        ra, dec = propagate(t["ra"], t["dec"], t["pmra_masyr"], t["pmdec_masyr"], t["epoch_yr"], ty)
        table, sfx = ("allwise_p3as_mep", "_ep") if ty < 2013 else ("neowiser_p1bs_psd", "")
        cols = ["mjd", "ra", "dec", f"w1mpro{sfx}", f"w1sigmpro{sfx}", f"w2mpro{sfx}", f"w2sigmpro{sfx}", "cc_flags",
                "qi_fact" if sfx else "qual_frame"]
        for r in _rows(irsa_gator(table, ra, dec, pm * WINDOW_YR / 2 + 3, cols)):
            if r["mjd"] is None or (r.get("qual_frame") == 0 if not sfx else r.get("qi_fact") == 0):
                continue
            pra, pdec = propagate(t["ra"], t["dec"], t["pmra_masyr"], t["pmdec_masyr"], t["epoch_yr"], mjd_to_year(r["mjd"]))
            if math.hypot(*_offsets_arcsec(r["ra"], r["dec"], pra, pdec)) <= 3.0:
                rows.append({"table": table, "mjd": r["mjd"], "cc_flags": str(r["cc_flags"] or "0000"),
                             **{k: r[f"{k}{sfx}"] for k in ("w1mpro", "w1sigmpro", "w2mpro", "w2sigmpro")}})
    return sorted(rows, key=lambda r: r["mjd"])


def _saturated(m):
    wise = [f for f in m["frames"] if f["survey"] == "wise"]
    return bool(wise) and sum("SATURATED" in f["flag_names"] for f in wise) >= 0.5 * len(wise)


def catalog_lightcurve(m):
    """Per-visit medians of catalog profile-fit photometry; artifact-flagged detections (cc_flags) dropped.
    AllWISE values of saturated stars are left out: they differ from NEOWISE's by up to ~2 mag (R Dra, W2)."""
    rows = _catalog_rows(m)
    saturated = _saturated(m)
    points = []
    for i, band in enumerate(("W1", "W2")):
        b = band.lower()
        for table in ("allwise_p3as_mep", "neowiser_p1bs_psd"):
            if saturated and table == "allwise_p3as_mep":
                continue
            # null sigmpro = upper limit for faint sources, but common for saturated profile fits: keep those
            pts = [r for r in rows if r["table"] == table and r[f"{b}mpro"] is not None
                   and (saturated or r[f"{b}sigmpro"] is not None) and r["cc_flags"][i] == "0"]
            for g in sorted(set(gs := group_by_gap([r["mjd"] for r in pts], 10))):
                vs = [r for r, gi in zip(pts, gs) if gi == g]
                mags = np.array([r[f"{b}mpro"] for r in vs])
                mag = float(np.median(mags))
                sig = [r[f"{b}sigmpro"] for r in vs if r[f"{b}sigmpro"] is not None]
                mag_err = max(1.253 * float(np.std(mags)) / math.sqrt(len(vs)) if len(vs) > 1 else 0.0,
                              (float(np.median(sig)) if sig else 0.05) / math.sqrt(len(vs)), 0.01)
                flux = WISE_F0_JY[band] * 1e6 * 10 ** (-0.4 * mag)
                points.append({"mjd": float(np.median([r["mjd"] for r in vs])), "band": band, "flux_ujy": flux,
                               "flux_err_ujy": flux * mag_err / 1.0857, "mag": mag, "mag_err": mag_err,
                               "n": len(vs), "table": table})
    points.sort(key=lambda p: (p["band"], p["mjd"]))
    return {"source": "neowiser_p1bs_psd+allwise_p3as_mep", "status": "ok" if points else "no data",
            "saturated": saturated, "points": points}


def _catalog_lc_cached(m):
    """Cheap once the IRSA rows are cached (_catalog_rows); recomputed per call so it follows the frames."""
    return _clean(catalog_lightcurve(m))


@router.get("/api/sequences/{sid}/catalog_lightcurve")
def catalog_lightcurve_route(sid: str):
    return _catalog_lc_cached(get_manifest(sid))


def photometry_lc(m, sky):
    """-> (lc, source, note). Our WISE visit photometry ("pipeline") when >= 5 visits per band have a flux;
    else catalog profile-fit photometry ("catalog": saturated stars, which our apertures cannot measure).
    source None: catalog needed but IRSA unavailable."""
    lc = wise_lightcurve(m["frames"], sky)
    if all(len(lc.get(b, [])) >= 5 for b in ("W1", "W2")):
        return lc, "pipeline", "WISE visit co-adds, 8.25\" aperture photometry" + (
            "; light of static sources the target passes over subtracted" if sky else "")
    try:
        cat = _catalog_lc_cached(m)
    except Exception as e:  # noqa: BLE001 - IRSA down: say so instead of failing the summary
        log.warning("catalog light curve failed for %s: %s", m["id"], e)
        return lc, None, "WISE pipeline photometry insufficient and IRSA catalogs unavailable"
    clc: dict[str, list] = {}
    for p in cat["points"]:
        clc.setdefault(p["band"], []).append((p["mjd"], p["flux_ujy"], p["flux_err_ujy"]))
    note = "NEOWISE/AllWISE single-exposure catalog profile fits, per-visit medians"
    return clc, "catalog", note + ("; target saturated in the images" if cat["saturated"] else "")


# ---------------------------------------------------------------- plain English


def _plain(motion, color, var, spec):
    s = []
    if motion["verdict"] == "moving":
        cat = ""
        if motion["consistent_with_catalog"] is True:
            cat = ", matching the catalog proper motion"
        elif motion["consistent_with_catalog"] is False:
            cat = ", which differs from the catalog value"
        sig = motion["significance_sigma"]
        conf = ("a very confident measurement" if sig > 10 else "a confident measurement" if sig >= 5 else
                "a tentative measurement")
        s.append(f"It moves across the sky: about {motion['pm_total_arcsec_yr']:.2f} arcseconds per year, measured over "
                 f"{motion['baseline_yr']:.0f} years ({conf}){cat}.")
    elif motion["verdict"] == "not moving":
        s.append(f"No motion detected over {motion['baseline_yr']:.0f} years (less than about "
                 f"{3 * motion['pmra_err_masyr'] / 1000:.2f} arcseconds per year): a distant star, a galaxy, or too slow to see.")
    elif motion["catalog"]["pmra_masyr"] or motion["catalog"]["pmdec_masyr"]:
        cat_pm = math.hypot(motion["catalog"]["pmra_masyr"], motion["catalog"]["pmdec_masyr"]) / 1000
        ts = motion.get("track_snr")
        seen = (f" Stacking all WISE images along its catalog motion ({cat_pm:.2f} arcseconds per year) does show it "
                f"(signal-to-noise {ts:.0f}), so it is there, just too faint to follow year by year."
                if ts is not None and ts >= 5 else
                " Even stacking all WISE images along its catalog motion does not show it clearly.")
        s.append("We could not follow it from year to year: in single WISE epochs it is too faint or sits on other "
                 "stars, so its motion is not measured here." + seen)
    else:
        s.append("Not enough clear detections in separate years to measure whether it moves.")
    return s + _plain_props(color, var, spec)


def _runner_up(ranking):
    """How the next-best template compares: the relative weights are not probabilities of the type, so say it in
    words. Delta chi2 < 4 (2 sigma for one parameter) counts as 'about as well'."""
    if len(ranking) < 2:
        return "."
    chi2 = [r["chi2_red"] * (r["n_bins"] - 1) for r in ranking[:2]]
    return f"; the next best ({ranking[1]['label']}) fits {'about as well' if chi2[1] - chi2[0] < 4 else 'clearly worse'}."


def _plain_props(color, var, spec):
    """Colour, variability and spectrum sentences (also used by the probe)."""
    s = []
    if color["w1_w2"] is not None:
        val = f"at least {color['w1_w2']:.1f}" if color["w1_w2_is_lower_limit"] else f"{color['w1_w2']:.2f}"
        hedge = "" if spec["verdict"] == "match" else " (dusty or very cool stars can look like this too)"
        s.append({"extremely red (Y/late-T dwarf-like)": f"Its infrared colour W1-W2 = {val} mag is extremely red, like the coldest brown dwarfs (late-T and Y).",
                  "very red (T dwarf-like)": f"Its infrared colour W1-W2 = {val} mag is very red, like T-type brown dwarfs.",
                  "red (L/T dwarf-like)": f"Its infrared colour W1-W2 = {val} mag is red, as for early-T and the reddest L brown dwarfs{hedge}.",
                  "normal star colors": f"Its infrared colour W1-W2 = {val} mag is normal for a star, not a cold brown dwarf.",
                  }.get(color["verdict"], "Its infrared colour could not be pinned down."))
    else:
        s.append("Its WISE W1-W2 colour could not be measured (too faint or not covered).")
    if var["verdict"] == "periodic variable":
        alts = " or ".join(f"~{p:.0f}" for p in var["period_alternatives_days"])
        s.append(f"Its brightness rises and falls regularly, every ~{var['period_days']:.0f} days"
                 + (f" ({alts} days fit the twice-yearly WISE visits equally well)." if alts else "."))
    else:
        s.append({"irregular variable": "Its brightness changes, but without a regular pattern (irregular variable).",
                  "constant": "Its infrared brightness stays constant within the measurement errors.",
                  }.get(var["verdict"], "Too few WISE measurements to tell whether its brightness changes."))
    label = spec["best"]["label"] if spec.get("best") else None
    if spec["verdict"] == "match":
        s.append(f"Its SPHEREx spectrum fits a {label} brown-dwarf template best" + _runner_up(spec["ranking"]))
    elif spec["verdict"] == WARMER:
        s.append(f"Its SPHEREx spectrum is closest to one of the warmest templates ({label}), but {spec['doubt']}: "
                 "probably an ordinary star, warmer than the ultracool dwarfs.")
    elif spec["verdict"] == DOUBTFUL:
        s.append(f"Its SPHEREx spectrum looks most like a {label} template, but {spec['doubt']}, so that type is doubtful.")
    elif spec.get("contaminated"):
        s.append("It sits in a crowded part of the sky where SPHEREx's large pixels are full of other stars, so its "
                 "spectrum cannot be measured reliably." if "crowded" in spec["reason"] else
                 "Other stars or galaxies share SPHEREx's large pixels at its position and add much of the light, "
                 "so its spectrum cannot be read cleanly.")
    elif spec.get("reason") == NO_DETECTION:
        s.append("SPHEREx does not clearly detect it at 3.5-5 micrometres, so its spectrum cannot be typed.")
    elif spec["verdict"] == "insufficient data":
        s.append("Not enough clean SPHEREx measurements to read its spectrum.")
    else:
        s.append("Its SPHEREx spectrum does not look like an ultracool dwarf (no template fits well).")
    return s


def _cached(m, name, compute, key=None):
    """Result cached in the sequence directory, recomputed when the frame set changes (key; default status +
    frame count); results that hit an unavailable external service (`_transient`) are not cached, so the next
    call retries."""
    key = key or [m["status"], len(m["frames"])]
    path = seq_dir(m["id"]) / name
    if path.exists():
        c = json.loads(path.read_text())
        if c.get("_key") == key:
            return {k: v for k, v in c.items() if k != "_key"}
    res = _clean(compute(m))
    if not res.pop("_transient", False):
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({**res, "_key": key}))
        tmp.replace(path)
    return res


def _skybot(jd, ra, dec, radius_arcsec):
    key = {"q": "skybot", "jd": round(jd, 2), "ra": round(ra, 4), "dec": round(dec, 4), "r": round(radius_arcsec)}
    return _ext_cached(key, lambda: _fetch_skybot(jd, ra, dec, radius_arcsec))


def _fetch_skybot(jd, ra, dec, radius_arcsec):
    url = "https://ssp.imcce.fr/webservices/skybot/api/conesearch.php?" + urllib.parse.urlencode(
        {"-ep": f"{jd:.5f}", "-ra": ra, "-dec": dec, "-rs": round(radius_arcsec), "-mime": "json",
         "-output": "basic", "-loc": "500", "-from": "UltracoolBrowser"})
    with urllib.request.urlopen(url, timeout=60) as r:
        body = r.read()
    res = json.loads(body) if body.strip() else []  # HTTP 204: nothing in the cone
    if isinstance(res, dict):  # per-request error, e.g. "Epoch ... not available" for some early-2010 dates
        log.info("SkyBoT at JD %.2f: %s", jd, res.get("message"))
        return []
    return res


def find_asteroids(m):
    """Known solar-system objects in the field at each WISE visit (IMCCE SkyBoT, geocentric ephemerides:
    WISE's low orbit shifts main-belt positions by < ~10"). Only near the ecliptic, where they live.
    -> list, or None if SkyBoT failed."""
    ra0, dec0 = (float(v) for v in _grid_wcs(m).wcs.crval)
    if abs(SkyCoord(ra0, dec0, unit="deg").barycentrictrueecliptic.lat.deg) > ASTEROID_MAX_ECL_LAT:
        return []
    mjds = sorted({round(f["mjd"], 2) for f in m["frames"] if f["survey"] == "wise" and f["band"] == "W2"})
    r = m["grid"]["width"] * PIX_ARCSEC / math.sqrt(2)
    try:
        with ThreadPoolExecutor(4) as pool:
            res = list(pool.map(lambda mjd: _skybot(mjd + 2400000.5, ra0, dec0, r), mjds[:ASTEROID_MAX_VISITS]))
    except Exception as e:  # noqa: BLE001
        log.warning("SkyBoT failed: %s", e)
        return None
    out = []
    for mjd, rows in zip(mjds, res):
        for a in rows:
            c = SkyCoord(a["RA (hms)"], a["DEC (dms)"], unit=("hourangle", "deg"))
            out.append({"name": a.get("Name"), "ra": c.ra.deg, "dec": c.dec.deg, "mjd": mjd,
                        "rate_arcsec_h": math.hypot(a.get("dRA (arcsec/h)") or 0, a.get("dDEC (arcsec/h)") or 0),
                        "vmag": a.get("VMag (mag)")})
    return out


def spectrum_contamination(m, sky):
    """Light of other sources inside the SPHEREx aperture (2 native px = 12.3" radius) at the target's SPHEREx
    position, as a fraction of the target's own WISE flux (or its 2-sigma upper limit when undetected), per
    WISE band: measured on visits from years when the target was >= 31" away. None when the target moves too
    slowly for that (then neighbours are in every image and nothing here can separate them)."""
    t = m["target"]
    pm = math.hypot(t["pmra_masyr"], t["pmdec_masyr"]) / 1000
    sx = [mjd_to_year(f["mjd"]) for f in m["frames"] if f["survey"] == "spherex"]
    if not sx or pm <= 0:
        return None
    t_sx = float(np.median(sx))
    dt_min = (2 * SX_AP_ARCSEC + 6.4) / pm
    x, y = (float(v) for v in _grid_wcs(m).world_to_pixel_values(
        *propagate(t["ra"], t["dec"], t["pmra_masyr"], t["pmdec_masyr"], t["epoch_yr"], t_sx)))
    lc = wise_lightcurve(m["frames"], sky)
    out = {}
    for band in ("W1", "W2"):
        fs = [f for f in m["frames"] if f["survey"] == "wise" and f["kind"] == "visit" and f["band"] == band
              and f.get("magzp") is not None and abs(mjd_to_year(f["mjd"]) - t_sx) >= dt_min]
        if len(fs) < 2 or not lc.get(band):
            return None
        net, err = aperture_flux(clipped_mean([load_npy(m["id"], f["id"]) for f in fs]), x, y,
                                 SX_AP_ARCSEC / PIX_ARCSEC, 4 * 6.15 / PIX_ARCSEC, 7 * 6.15 / PIX_ARCSEC)
        if not math.isfinite(net):
            return None
        f_t, e_t = _wmean(np.array([p[1] for p in lc[band]]), np.array([p[2] for p in lc[band]]))
        k = wise_flux_factor(band, float(np.median([f["magzp"] for f in fs])))  # DN -> uJy (8.25" apcorr: conservative)
        out[band] = net * k / max(f_t, 2 * e_t) if net > 3 * err else 0.0
    return out


def colour_doubt(spec, color):
    """Demote a template match whose W1-W2 is > W12_DOUBT_SIGMA (measurement and locus scatter) bluer than the
    locus of its type. A lower limit cannot argue against a type."""
    if not color or color.get("w1_w2") is None or color.get("w1_w2_is_lower_limit") or color.get("w1_w2_err") is None:
        return
    early = spec["best"]["label"] in EARLY_LABELS
    locus = W12_LOCUS_M8 if early else W12_LOCUS_L
    c = color["w1_w2"]
    if c < locus - W12_DOUBT_SIGMA * math.hypot(color["w1_w2_err"], W12_LOCUS_SIGMA):
        demote(spec, f"its W1-W2 colour ({c:.2f} mag) is bluer than {'M8-M9' if early else 'L, T and Y'} dwarfs "
                     f"(typically {locus:.2f} mag or redder)")


def typed_spectrum(m, sky, color):
    """spectral.classify, then: no clear SPHEREx detection stays that (there is no spectrum to be contaminated);
    a detection is 'insufficient data' (ranking kept for experts) when the photometry is contaminated: other
    sources supply a large part of the light in the SPHEREx aperture (then any template 'match' describes the
    neighbour: W0855-0714 typed as an M dwarf), or >= NEG_BINS_MAX channels are significantly negative (crowded
    field, sky over-subtracted: J1925+2901 at b = +7 deg). A remaining match must agree with the WISE colour."""
    spec = classify(m["frames"])
    c = spectrum_contamination(m, sky)
    neg = sum(b["flambda"] / b["err"] < NEG_BIN_SIGMA for b in spec["binned"] if b["err"] > 0)
    spec.update(contamination=c, negative_bins=neg)
    reason = None
    if spec.get("reason") == NO_DETECTION:
        pass
    elif c and max(c.values()) > CONTAM_FRAC:
        reason = "other stars or galaxies add much of the light in SPHEREx's large pixels"
    elif neg >= NEG_BINS_MAX:
        reason = f"{neg} channels significantly negative: crowded-field background, photometry unreliable"
    spec["contaminated"] = reason is not None
    if reason:
        spec.update(verdict="insufficient data", best=None, template_curve=None, reason=reason)
    elif spec["verdict"] == "match":
        colour_doubt(spec, color)
    return spec


@router.get("/api/sequences/{sid}/spectrum")
def spectrum(sid: str):
    """Colour from our WISE photometry only (no catalog fallback: this is polled while frames arrive), so for
    saturated stars the colour check of /summary may differ."""
    m = get_manifest(sid)
    sky = static_sky_flux(m)
    return _clean(typed_spectrum(m, sky, measure_color(wise_lightcurve(m["frames"], sky))))


def _summary(m):
    motion = measure_motion(m)
    sky = static_sky_flux(m)
    lc, source, note = photometry_lc(m, sky)
    floor = SATURATED_FLOOR if source == "catalog" and _saturated(m) else PHOT_FLOOR
    w1_undetected = motion["recovered"] and "W1" in motion["undetected_bands"] and source == "pipeline"
    color = {**measure_color(lc, w1_undetected), "source": source, "source_note": note}
    var = {**classify_variability(lc, floor), "source": source, "source_note": note}
    spec = typed_spectrum(m, sky, color)
    asteroids = find_asteroids(m)
    return {"motion": motion, "color": color, "variability": var, "spectrum": spec,
            "plain": _plain(motion, color, var, spec), "asteroids": asteroids or [],
            "_transient": source is None or asteroids is None}


@router.get("/api/sequences/{sid}/summary")
def summary(sid: str):
    return _cached(get_manifest(sid), "summary.json", _summary)


# ---------------------------------------------------------------- moving-source search


def _detect(z, fwhm_px, thresh=MOVER_SIG):
    """Point sources in a sigma-unit stack -> array of (x, y, snr). Saturated stars are placed at the centre
    of their NaN core; peaks on their filled plateau and wings are dropped."""
    snr = _snr_map(_fill_nan(z), fwhm_px)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # quadratic centroid off a flat peak: handled below
        t = find_peaks(snr, threshold=thresh, box_size=5, centroid_func=centroid_quadratic, border_width=5)
    cores = _saturated_cores(z)
    out = [(cx, cy, 1e4) for cx, cy, _ in cores]
    if t is not None:
        x, y = np.array(t["x_centroid"], float), np.array(t["y_centroid"], float)
        ok = np.isfinite(x) & np.isfinite(y) & (np.hypot(x - t["x_peak"], y - t["y_peak"]) < 1.5)
        x, y = np.where(ok, x, t["x_peak"]), np.where(ok, y, t["y_peak"])
        for xi, yi, s in zip(x, y, np.array(t["peak_value"], float)):
            if all(math.hypot(xi - cx, yi - cy) > math.sqrt(n / math.pi) + 2 * fwhm_px for cx, cy, n in cores):
                out.append((xi, yi, s))
    return np.array(out, float).reshape(-1, 3)


def find_tracks(dets, years, fwhm_px=FWHM_PX["W2"]):
    """dets: per window an array of (x, y, snr); years: window epochs. Linear tracks through >= max(4, 60%) of
    the windows, anchored on a detection in one of the first two and one of the last two windows, not made of
    detections that recur in place, that follow a straight line (chi2_red <= MOVER_MAX_CHI2) and move at
    >= MOVER_SIG -> list of dicts with the fit and the detections used. Image-level vetting is _vet_track."""
    W = len(dets)
    trees = [cKDTree(d[:, :2]) if len(d) else None for d in dets]

    def near(w, xy, r):
        return trees[w] is not None and bool(trees[w].query_ball_point(xy, r))

    static = []
    for w, d in enumerate(dets):
        others = [v for v in range(W) if v != w]
        static.append(np.array([sum(near(v, p[:2], STATIC_PX) for v in others) >= 0.5 * len(others) for p in d], bool))
    max_px_yr = MOVER_MAX_PM_ARCSEC / PIX_ARCSEC
    min_n = max(4, math.ceil(MOVER_MIN_FRAC * W))
    cands = []
    for wa in range(min(2, W)):
        for wb in range(max(wa + 1, W - 2), W):
            dt = years[wb] - years[wa]
            if dt < 4 or trees[wb] is None:
                continue
            for ia in np.flatnonzero(~static[wa]):
                a = dets[wa][ia]
                for ib in trees[wb].query_ball_point(a[:2], max_px_yr * dt):
                    b = dets[wb][ib]
                    if static[wb][ib] or math.hypot(*(b[:2] - a[:2])) < 1.5:
                        continue
                    # a static pair: something still sits at a's spot later, or at b's spot earlier
                    if near(wb, a[:2], STATIC_PX) or near(wa, b[:2], STATIC_PX):
                        continue
                    v = (b[:2] - a[:2]) / dt
                    used = {wa: ia, wb: ib}
                    for w in range(W):
                        if w in used or trees[w] is None:
                            continue
                        p = a[:2] + v * (years[w] - years[wa])
                        dist, j = trees[w].query(p)
                        if dist <= MOVER_MATCH_PX:
                            used[w] = int(j)
                    if len(used) < min_n:
                        continue
                    ws = sorted(used)
                    pts = np.array([dets[w][used[w]] for w in ws])
                    # saturated cores (snr 1e4) are good to ~0.3 px; others sqrt(2) sigma_psf / SNR + 0.2"
                    err = np.where(pts[:, 2] >= 1e4, 0.3, np.sqrt(2) * fwhm_px / 2.355 / np.maximum(pts[:, 2], 1) + 0.07)
                    fit = fit_motion([years[w] for w in ws], -pts[:, 0] * PIX_ARCSEC, pts[:, 1] * PIX_ARCSEC, err * PIX_ARCSEC)
                    if fit["significance"] < MOVER_SIG or fit["chi2_red"] > MOVER_MAX_CHI2:
                        continue
                    cands.append({"fit": fit, "used": used, "n": len(used)})
    cands.sort(key=lambda c: (-c["n"], c["fit"]["chi2_red"]))
    taken, tracks = set(), []
    for c in cands:
        keys = {(w, i) for w, i in c["used"].items()}
        if keys & taken:
            continue
        taken |= keys
        tracks.append(c)
    return tracks


def _catalogs(m):
    """CatWISE2020 (IRSA) and SIMBAD (Harvard mirror) sources in the field, cached per cone (shared between
    sequences); None per catalog on failure (not cached, retried next call)."""
    ra0, dec0 = (float(v) for v in _grid_wcs(m).wcs.crval)
    r_deg = m["grid"]["width"] * PIX_ARCSEC / 3600 / math.sqrt(2) + 0.005
    cone = [round(ra0, 4), round(dec0, 4), round(r_deg, 4)]
    out = {}
    try:
        out["catwise"] = _ext_cached({"q": "catwise_2020_field", "cone": cone}, lambda: _fetch_catwise(ra0, dec0, r_deg))
    except Exception as e:  # noqa: BLE001
        log.warning("CatWISE field query failed: %s", e)
        out["catwise"] = None
    try:
        out["simbad"] = _ext_cached({"q": "simbad_field", "cone": cone}, lambda: _fetch_simbad(ra0, dec0, r_deg))
    except Exception as e:  # noqa: BLE001
        log.warning("SIMBAD field query failed: %s", e)
        out["simbad"] = None
    return out


def _fetch_catwise(ra0, dec0, r_deg):
    return [{"name": r["source_name"], "ra": r["ra_pm"], "dec": r["dec_pm"],
             "pmra": (r["pmra"] or 0) * 1000, "pmdec": (r["pmdec"] or 0) * 1000,
             "sigpm": math.hypot(r["sigpmra"] or 0.1, r["sigpmdec"] or 0.1) / math.sqrt(2) * 1000, "epoch": 2015.4}
            for r in _rows(irsa_gator("catwise_2020", ra0, dec0, r_deg * 3600,
                                      ["source_name", "ra_pm", "dec_pm", "pmra", "pmdec", "sigpmra", "sigpmdec"]))
            if r["ra_pm"] is not None]


def _fetch_simbad(ra0, dec0, r_deg):
    q = ("SELECT main_id, ra, dec, pmra, pmdec FROM basic WHERE CONTAINS(POINT('ICRS', ra, dec), "
         f"CIRCLE('ICRS', {ra0}, {dec0}, {r_deg}))=1")
    url = "https://simbad.harvard.edu/simbad/sim-tap/sync?" + urllib.parse.urlencode(
        {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "votable", "QUERY": q})
    with urllib.request.urlopen(url, timeout=60) as resp:
        rows = _rows(resp.read())
    return [{"name": r["main_id"], "ra": r["ra"], "dec": r["dec"], "pmra": r["pmra"] or 0.0,
             "pmdec": r["pmdec"] or 0.0, "epoch": 2000.0} for r in rows if r["ra"] is not None]


def _match(cat, ra, dec, pmra, pmdec, pm_err, r_arcsec=3.0):
    """Catalog entry at the mover's position at the catalog's epoch (propagated with the mover's PM) ->
    (entry, pm_offset_sigma) for the nearest within r_arcsec; among entries within 1" of the nearest, the
    shortest name, so a star wins over its planets ("... b"). pm_offset_sigma compares the two motions
    (catalog error from 'sigpm', else 10% + 20 mas/yr: SIMBAD gives none)."""
    hits = []
    for c in cat or []:
        pra, pdec = propagate(ra, dec, pmra, pmdec, REF_YR, c["epoch"])
        d = math.hypot(*_offsets_arcsec(c["ra"], c["dec"], pra, pdec))
        if d <= r_arcsec:
            hits.append((d, c))
    if not hits:
        return None, None
    d0 = min(h[0] for h in hits)
    c = min((h for h in hits if h[0] <= d0 + 1.0), key=lambda h: len(h[1]["name"]))[1]
    s_cat = c.get("sigpm") or 0.1 * math.hypot(c["pmra"], c["pmdec"]) + 20
    return c, math.hypot(c["pmra"] - pmra, c["pmdec"] - pmdec) / math.hypot(pm_err, s_cat)


def _forced_color(m, wcs, track):
    """W1-W2 of a mover from forced aperture photometry on every WISE visit frame along its track."""
    lc: dict[str, list] = {}
    for f in m["frames"]:
        if f["survey"] != "wise" or f["kind"] != "visit" or f.get("magzp") is None:
            continue
        x, y = track(mjd_to_year(f["mjd"]))
        net, err = aperture_flux(load_npy(m["id"], f["id"]), x, y, WISE_R_AP, WISE_R_IN, WISE_R_OUT)
        if math.isfinite(net) and err > 0:
            k = wise_flux_factor(f["band"], f["magzp"])
            lc.setdefault(f["band"], []).append((f["mjd"], net * k, err * k))
    return measure_color(lc)


def _vet_track(tr, dets, years, ns, snrs, cache):
    """Image-level checks of a linked track -> rejection reason or None. snrs: per-window matched-filter S/N
    maps, ns: frames per window. The static sky at a spot = windows when the track was >= MOVER_SEP_FWHM away.
    (c) dipole: a real mover has left its first position by the late windows and was not yet at its last
    position in the early ones; (d) it must not sit on a static source in most windows."""
    fit = tr["fit"]
    pm = fit["pm"] / 1000
    if pm <= 0:
        return "not moving"
    dt_sep = MOVER_SEP_FWHM * FWHM_PX["W2"] * PIX_ARCSEC / pm
    W = len(years)
    ws = sorted(tr["used"])

    def static_ratio(w, others):
        """(S/N, per-frame flux ratio) of what the other windows show at detection w's position. A saturated
        detection has no usable S/N: there, static means a saturated core at the same spot in another window."""
        x, y, snr = dets[w][tr["used"][w]]
        if snr >= 1e4:
            sep = MOVER_SEP_FWHM * FWHM_PX["W2"]
            hit = any(len(dets[v]) and np.any((dets[v][:, 2] >= 1e4)
                                              & (np.hypot(dets[v][:, 0] - x, dets[v][:, 1] - y) < sep)) for v in others)
            return (math.inf, math.inf) if hit else (0.0, 0.0)
        key = tuple(others)
        if key not in cache:
            n = sum(ns[v] for v in others)
            cache[key] = (sum(math.sqrt(ns[v]) * snrs[v] for v in others) / math.sqrt(n), n)
        s, n = cache[key]
        val = float(s[min(s.shape[0] - 1, max(0, round(y))), min(s.shape[1] - 1, max(0, round(x)))])
        return val, (val / math.sqrt(n)) / (snr / math.sqrt(ns[w]))

    first, last = ws[0], ws[-1]
    late = [v for v in range(W) if years[v] - years[first] >= dt_sep]
    early = [v for v in range(W) if years[last] - years[v] >= dt_sep]
    if not late or not early:
        return "moves too little to tell from a static source"
    for w, others in ((first, late), (last, early)):
        val, ratio = static_ratio(w, others)
        if val >= 3 and ratio > DIPOLE_RATIO:
            return "no dipole: a static source stays where the track starts or ends"
    on_static = 0
    for w in ws:
        others = [v for v in range(W) if abs(years[v] - years[w]) >= dt_sep]
        if others:
            val, ratio = static_ratio(w, others)
            on_static += val >= 3 and ratio > ON_STATIC_RATIO
    if on_static >= 0.5 * len(ws):
        return "sits on static sources along most of its track"
    return None


def _target_track(m, motion, wcs):
    """The target's measured track (summary motion) as a fit in grid-pixel convention, or None."""
    if not motion["recovered"] or motion["verdict"] != "moving":
        return None
    ra0, dec0 = (float(v) for v in wcs.wcs.crval)
    pts = motion["points"]
    xi, eta = _offsets_arcsec([p["ra"] for p in pts], [p["dec"] for p in pts], ra0, dec0)
    cx, cy = wcs.wcs.crpix[0] - 1, wcs.wcs.crpix[1] - 1
    # same convention as find_tracks: offsets (-x, y) * PIX_ARCSEC from the grid origin
    return fit_motion([mjd_to_year(p["mjd"]) for p in pts], np.asarray(xi) - cx * PIX_ARCSEC,
                      np.asarray(eta) + cy * PIX_ARCSEC, [p["err_arcsec"] for p in pts])


def _artifact_samples(m, visits):
    """WISE spike/halo/ghost artifact positions in two W2 exposures (first, middle) of every visit ->
    [(mjd, array of (ra, dec))], or [] if IRSA's frame list is unavailable (then nothing is vetoed)."""
    lo, hi = min(f["mjd"] for f in visits) - 10, max(f["mjd"] for f in visits) + 10
    try:
        raw = sorted((r for r in query_frames(*_grid_wcs(m).wcs.crval)
                      if r.survey == "wise" and r.band == "W2" and lo <= r.mjd <= hi), key=lambda r: r.mjd)
    except Exception as e:  # noqa: BLE001
        log.warning("artifact check skipped: %s", e)
        return []
    groups: dict[int, list] = {}
    for r, g in zip(raw, group_by_gap([r.mjd for r in raw], 10)):
        groups.setdefault(g, []).append(r)
    sample = [v[i] for v in groups.values() for i in sorted({0, len(v) // 2})]
    pts = bright_star_artifacts(sample)
    return [(r.mjd, np.array(pts[r.stem], float).reshape(-1, 2)) for r in sample if r.stem in pts]


def _artifact_frac(art, wcs, track):
    """Fraction of the sampled exposures in which the track sits within WISE_ART_R_ARCSEC of a flagged artifact."""
    hits = 0
    for mjd, p in art:
        if len(p):
            ra, dec = (float(v) for v in wcs.pixel_to_world_values(*track(mjd_to_year(mjd))))
            hits += float(np.min(np.hypot(*_offsets_arcsec(p[:, 0], p[:, 1], ra, dec)))) <= WISE_ART_R_ARCSEC
    return hits / len(art)


def find_movers(m):
    """Every significantly moving source in the field: tracks linked through 2-yr W2 stacks (find_tracks),
    vetted in the images (_vet_track) and against CatWISE motions; the target's own track (summary motion)
    is always included when it was recovered as moving."""
    sid = m["id"]
    wcs = _grid_wcs(m)
    t = m["target"]
    fs = [f for f in m["frames"] if f["survey"] == "wise" and f["kind"] == "visit" and f["band"] == "W2"]
    wins: dict[int, list] = {}
    for f in fs:
        wins.setdefault(int((mjd_to_year(f["mjd"]) - 2010) // WINDOW_YR), []).append(f)
    keys = sorted(wins)
    if len(keys) < 3:
        return {"movers": [], "rejected": [], "vetting": {}, "status": "insufficient data"}
    years = [float(np.mean([mjd_to_year(f["mjd"]) for f in wins[k]])) for k in keys]
    ns = [len(wins[k]) for k in keys]
    stacks = [deep_stack([load_npy(sid, f["id"]) for f in wins[k]]) for k in keys]
    snrs = [_snr_map(_fill_nan(z), FWHM_PX["W2"]) for z in stacks]
    dets = [_detect(z, FWHM_PX["W2"], MOVER_DET_SNR) for z in stacks]
    vetting: Counter = Counter()
    cache: dict = {}
    tracks = []
    for tr in find_tracks(dets, years):
        reason = _vet_track(tr, dets, years, ns, snrs, cache)
        if reason:
            vetting[reason] += 1
        else:
            tracks.append({**tr, "target": False})
    motion = measure_motion(m)
    tfit = _target_track(m, motion, wcs)
    if tfit is not None:
        def same(tr):
            f = tr["fit"]
            dx = (f["xi0"] + f["pmra"] / 1000 * (REF_YR - f["t0"])) - (tfit["xi0"] + tfit["pmra"] / 1000 * (REF_YR - tfit["t0"]))
            dy = (f["eta0"] + f["pmdec"] / 1000 * (REF_YR - f["t0"])) - (tfit["eta0"] + tfit["pmdec"] / 1000 * (REF_YR - tfit["t0"]))
            return math.hypot(dx, dy) <= 3 * PIX_ARCSEC
        tracks = [tr for tr in tracks if not same(tr)]  # the target's own measurement replaces a linked copy
        tracks.append({"fit": tfit, "n": motion["n_epochs"], "target": True})
    cats = _catalogs(m) if tracks else {}
    ny = m["grid"]["height"]
    movers, rejected = [], []
    art = None  # fetched for the first candidate that needs it
    for tr in tracks:
        fit = tr["fit"]
        # fit is on (-x, y) * PIX_ARCSEC: east/north offsets from the grid origin in arcsec
        x0, y0 = -fit["xi0"] / PIX_ARCSEC, fit["eta0"] / PIX_ARCSEC

        def track(ty_, x0=x0, y0=y0, fit=fit):
            dt = ty_ - fit["t0"]
            return x0 - fit["pmra"] / 1000 / PIX_ARCSEC * dt, y0 + fit["pmdec"] / 1000 / PIX_ARCSEC * dt

        x, y = track(REF_YR)
        ra, dec = (float(v) for v in wcs.pixel_to_world_values(x, y))
        entry = {"ra": ra, "dec": dec, "epoch_yr": REF_YR, "x_px": x, "y_px": ny - 1 - y,
                 "pmra_masyr": fit["pmra"], "pmdec_masyr": fit["pmdec"], "pm_err_masyr": fit["pmra_err"],
                 "significance_sigma": fit["significance"], "chi2_red": fit["chi2_red"], "n_epochs": tr["n"]}
        if not tr["target"]:
            if art is None:
                art = _artifact_samples(m, fs)
            if art and _artifact_frac(art, wcs, track) >= ARTIFACT_FRAC:
                rejected.append({**entry, "reason": "artifact of a bright star"})
                vetting["artifact of a bright star"] += 1
                continue
        cw, cw_d = _match(cats.get("catwise"), ra, dec, fit["pmra"], fit["pmdec"], fit["pmra_err"])
        if cw and not tr["target"] and math.hypot(cw["pmra"], cw["pmdec"]) < max(3 * cw["sigpm"], 100) and cw_d >= 3:
            rejected.append({**entry, "reason": f"catalog says static: CatWISE {cw['name']} moves "
                                                f"{math.hypot(cw['pmra'], cw['pmdec']) / 1000:.2f}\"/yr"})
            vetting["catalog says static"] += 1
            continue
        sb, sb_d = _match(cats.get("simbad"), ra, dec, fit["pmra"], fit["pmdec"], fit["pmra_err"])
        known = {"simbad": sb["name"] if sb and (sb_d < 3 or not (sb["pmra"] or sb["pmdec"])) else None,
                 "catwise": cw["name"] if cw and cw_d < 3 else None, "spiff": None}
        sp = ucd.near(ra=ra, dec=dec, radius_arcsec=5.0, pmra_masyr=fit["pmra"], pmdec_masyr=fit["pmdec"], epoch_yr=REF_YR)
        if sp:
            known["spiff"] = f"{sp[0]['designation']} ({sp[0]['spiff_autotype']})"
        if tr["target"]:  # same colour as /summary: neighbour light subtracted, W1 limit if astrometry missed it
            col = measure_color(wise_lightcurve(m["frames"], static_sky_flux(m)), "W1" in motion["undetected_bands"])
        else:
            col = _forced_color(m, wcs, track)
        movers.append({**entry, "w1_w2": None if col["w1_w2_is_lower_limit"] else col["w1_w2"],
                       "w1_w2_lower_limit": col["w1_w2"] if col["w1_w2_is_lower_limit"] else None,
                       "known": known, "is_target": tr["target"], "cpm_with": []})
    # common proper motion: PM vectors equal within 3 sigma (e.g. eps Ind A and Ba/Bb)
    tgt = next((mv for mv in movers if mv["is_target"]), None)
    ref = ((tgt["pmra_masyr"], tgt["pmdec_masyr"], tgt["pm_err_masyr"]) if tgt else
           (t["pmra_masyr"], t["pmdec_masyr"], max(20.0, 0.05 * math.hypot(t["pmra_masyr"], t["pmdec_masyr"])))
           if (t["pmra_masyr"] or t["pmdec_masyr"]) else None)

    def cpm(a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1]) / math.hypot(a[2], b[2]) < 3

    for i, a in enumerate(movers):
        va = (a["pmra_masyr"], a["pmdec_masyr"], a["pm_err_masyr"])
        a["cpm_with"] = [j for j, b in enumerate(movers)
                         if j != i and cpm(va, (b["pmra_masyr"], b["pmdec_masyr"], b["pm_err_masyr"]))]
        if not a["is_target"] and ref and cpm(va, ref):
            a["cpm_with"].append("target")
    return {"movers": movers, "rejected": rejected, "vetting": dict(vetting), "status": "ok",
            "_transient": bool(tracks) and (cats.get("catwise") is None or cats.get("simbad") is None)}


@router.get("/api/sequences/{sid}/movers")
def movers(sid: str):
    """Needs only the WISE W2 visits: computed once every WISE unit is in (manifest wise_done), even while
    SPHEREx frames are still arriving; cached on the WISE frame set."""
    m = get_manifest(sid)
    if not m["wise_done"]:
        return {"movers": [], "rejected": [], "vetting": {}, "status": "insufficient data", "pending": True}
    wise = [f for f in m["frames"] if f["survey"] == "wise"]
    return _cached({**m, "frames": wise}, "movers.json", find_movers, key=["wise", len(wise)])
