"""Science summary of a sequence (proper motion, W1-W2 colour, variability, spectrum) and a search for every
moving source in the field. Works on the cached grid frames (npy) and the manifest photometry."""
import io
import json
import logging
import math
import urllib.parse
import urllib.request
import warnings
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

from . import ucd
from .frames import PIX_ARCSEC, aperture_flux, deep_stack, group_by_gap, mjd_to_year, propagate
from .sequences import (WISE_F0_JY, WISE_R_AP, WISE_R_IN, WISE_R_OUT, get_manifest, load_npy, seq_dir,
                        wise_flux_factor)
from .sources import irsa_gator
from .spectral import classify

log = logging.getLogger("ultracool.analysis")
router = APIRouter()

WINDOW_YR = 2.0  # WISE co-add windows for astrometry (4 visits each; unTimely/CatWISE use 1-yr pairs)
FWHM_PX = {"W1": 6.1 / PIX_ARCSEC, "W2": 6.4 / PIX_ARCSEC, "SPHEREx": 11.0 / PIX_ARCSEC}
# astrometric floor per co-add (WISE L1b is tied to 2MASS/Gaia to ~0.1-0.2"; SPHEREx 6.15" pixels)
POS_FLOOR_ARCSEC = {"W1": 0.2, "W2": 0.2, "SPHEREx": 0.6}
MIN_SNR = 4.0
PM_PRIOR_MASYR = 300.0  # how far an object with unknown/zero catalog PM may have drifted, per year
REF_YR = 2018.0  # grid-centre epoch; mover positions are given at this epoch
# Variability: per-visit repeatability floor (NEOWISE single-exposure photometry repeats to ~1-2% for bright
# stars, Mainzer+2014; visit co-adds with 8.25" apertures are a little worse)
PHOT_FLOOR = 0.03
# profile fits of saturated stars in the NEOWISE single-exposure catalog drift and scatter by 0.1-0.2 mag
# between visits (Barnard's Star, a constant star, scatters 7-28% per visit in W1)
SATURATED_FLOOR = 0.15
ASTEROID_MAX_ECL_LAT = 35.0  # deg; known asteroids beyond this are rare
ASTEROID_MAX_VISITS = 40  # SkyBoT calls per sequence (4 in parallel, ~3 s each)
VAR_CHI2 = 3.0  # irregular = chi2_red > ~3 without a significant periodogram peak
LS_MIN_EPOCHS = 8
LS_FAP = 0.01
CADENCE_D = 365.25  # NEOWISE visits every ~6 months: periods at 1/k yr are cadence aliases
# W1-W2 colour classes (Vega). Kirkpatrick et al. 2011 (ApJS 197, 19) Fig. 13 / Kirkpatrick et al. 2021
# (ApJS 253, 7): stars and early-M dwarfs sit at W1-W2 ~ 0-0.3, L dwarfs 0.2-0.6, T dwarfs climb from ~0.5
# (T0) through ~2 (T7) to >3 for Y dwarfs; W0855-0714 has W1-W2 ~ 3.5 or more.
W12_EXTREME, W12_RED = 2.0, 0.6
MOVER_MAX_PM_ARCSEC = 12.0  # Barnard's Star 10.4"/yr is the fastest known
MOVER_SIG = 5.0
MOVER_MATCH_PX = 1.5
STATIC_PX = 1.0  # shortcut: sources slower than ~1 px per 16 yr (~0.3"/yr) count as static; upgrade = 1-yr windows


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


def centroid(z, x0, y0, r_search, fwhm_px):
    """Brightest point source within r_search px of (x0, y0) in a sigma-unit image ->
    (x, y, err_px, snr) or None if nothing above MIN_SNR. err = sqrt(2) sigma_psf / SNR.
    A saturated star (NaN core) is located by the centre of its core, good to ~0.3 px."""
    sat = [c for c in _saturated_cores(z) if math.hypot(c[0] - x0, c[1] - y0) <= r_search]
    if sat:
        cx, cy, _ = max(sat, key=lambda c: c[2])
        return cx, cy, 0.3, math.inf
    zf = _fill_nan(z)
    snr = _snr_map(zf, fwhm_px)
    yy, xx = np.indices(z.shape)
    inside = np.hypot(xx - x0, yy - y0) <= r_search
    if not inside.any():
        return None
    i = np.argmax(np.where(inside, snr, -np.inf))
    py, px = np.unravel_index(i, z.shape)
    peak = float(snr[py, px])
    if peak < MIN_SNR:
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


def measure_motion(m):
    sid = m["id"]
    t = m["target"]
    wcs = _grid_wcs(m)
    ra0, dec0 = (float(v) for v in wcs.wcs.crval)
    groups = _motion_groups(m["frames"])
    cat = {"pmra_masyr": t["pmra_masyr"], "pmdec_masyr": t["pmdec_masyr"]}
    out = {"status": "insufficient data", "pmra_masyr": None, "pmdec_masyr": None, "pmra_err_masyr": None,
           "pmdec_err_masyr": None, "pm_total_arcsec_yr": None, "significance_sigma": None, "baseline_yr": None,
           "n_epochs": 0, "catalog": cat, "consistent_with_catalog": None, "verdict": "insufficient data",
           "points": []}
    if len(groups) < 3:
        return out

    def predict_cat(ty):
        return _offsets_arcsec(*propagate(t["ra"], t["dec"], t["pmra_masyr"], t["pmdec_masyr"], t["epoch_yr"], ty),
                               ra0, dec0)

    model = None
    for _pass in range(2):
        pm_mas = (model["pmra"], model["pmdec"]) if model else (t["pmra_masyr"], t["pmdec_masyr"])
        pm_px = (-pm_mas[0] / 1000 / PIX_ARCSEC, pm_mas[1] / 1000 / PIX_ARCSEC)  # grid x runs west
        pts = []
        for band, fs in groups:
            ty = float(np.mean([mjd_to_year(f["mjd"]) for f in fs]))
            if model:
                dt = ty - model["t0"]
                pxi, peta = model["xi0"] + model["pmra"] / 1000 * dt, model["eta0"] + model["pmdec"] / 1000 * dt
                sig = math.hypot(model["pos_err"], model["pmra_err"] / 1000 * abs(dt))
            else:
                pxi, peta = predict_cat(ty)
                sig = (0.05 * math.hypot(*pm_mas) + PM_PRIOR_MASYR) / 1000 * abs(ty - t["epoch_yr"])
            r_search = min(30.0, max(6.0, 3 * sig)) / PIX_ARCSEC
            x0 = (wcs.wcs.crpix[0] - 1) - pxi / PIX_ARCSEC  # tangent-plane offsets -> grid px (small field)
            y0 = (wcs.wcs.crpix[1] - 1) + peta / PIX_ARCSEC
            c = centroid(_shifted_stack(sid, fs, pm_px, ty), x0, y0, r_search, FWHM_PX[band])
            if c is None:
                continue
            ra, dec = (float(v) for v in wcs.pixel_to_world_values(c[0], c[1]))
            xi, eta = _offsets_arcsec(ra, dec, ra0, dec0)
            err = math.hypot(c[2] * PIX_ARCSEC, POS_FLOOR_ARCSEC[band])
            pts.append({"mjd": float(np.mean([f["mjd"] for f in fs])), "band": band, "ra": ra, "dec": dec,
                        "err_arcsec": err, "_t": ty, "_xi": float(xi), "_eta": float(eta),
                        "_epoch": (band == "SPHEREx", round(ty / WINDOW_YR))})
        if len(pts) < 3:
            return out
        fit = fit_motion([p["_t"] for p in pts], [p["_xi"] for p in pts], [p["_eta"] for p in pts],
                         [p["err_arcsec"] for p in pts])
        keep = [p for p, r in zip(pts, fit["resid"]) if r <= max(4 * p["err_arcsec"] * math.sqrt(max(1, fit["chi2_red"])), 1.0)]
        if 3 <= len(keep) < len(pts):  # one confused/blended epoch must not drag the fit
            pts = keep
            fit = fit_motion([p["_t"] for p in pts], [p["_xi"] for p in pts], [p["_eta"] for p in pts],
                             [p["err_arcsec"] for p in pts])
        model = fit
    years = [p["_t"] for p in pts]
    n_epochs = len({p["_epoch"] for p in pts})
    baseline = max(years) - min(years)
    out.update({"status": "ok", "pmra_masyr": fit["pmra"], "pmdec_masyr": fit["pmdec"],
                "pmra_err_masyr": fit["pmra_err"], "pmdec_err_masyr": fit["pmdec_err"],
                "pm_total_arcsec_yr": fit["pm"] / 1000, "significance_sigma": fit["significance"],
                "baseline_yr": baseline, "n_epochs": n_epochs, "chi2_red": fit["chi2_red"],
                "points": [{k: v for k, v in p.items() if not k.startswith("_")} for p in pts]})
    if n_epochs < 3 or baseline < 2:
        out["status"] = "insufficient data"
        return out
    # single-epoch dipoles are pointing-jitter artifacts (Backyard Worlds): >= 3 epochs over >= 2 yr, >= 3 sigma
    out["verdict"] = "moving" if fit["significance"] >= 3 else "not moving"
    if t["pmra_masyr"] or t["pmdec_masyr"]:
        d = math.hypot((fit["pmra"] - t["pmra_masyr"]) / fit["pmra_err"], (fit["pmdec"] - t["pmdec_masyr"]) / fit["pmdec_err"])
        out["consistent_with_catalog"] = bool(d < 3 or math.hypot(fit["pmra"] - t["pmra_masyr"], fit["pmdec"] - t["pmdec_masyr"])
                                              < 0.03 * math.hypot(t["pmra_masyr"], t["pmdec_masyr"]))
    return out


# ---------------------------------------------------------------- photometry: colour and variability


def wise_lightcurve(frames):
    """{band: [(mjd, flux_ujy, err_ujy)]} from unflagged WISE visit frames with a measurement."""
    lc: dict[str, list] = {}
    for f in frames:
        if f["survey"] == "wise" and f["kind"] == "visit" and not f["flagged"] and f["flux_ujy"] is not None \
                and f["flux_err_ujy"] and f["flux_err_ujy"] > 0:
            lc.setdefault(f["band"], []).append((f["mjd"], f["flux_ujy"], f["flux_err_ujy"]))
    return lc


def _wmean(fl, er):
    w = er ** -2
    mu = float(np.sum(w * fl) / np.sum(w))
    err = float(1 / math.sqrt(np.sum(w)))
    if len(fl) > 2:  # a variable or badly-calibrated source: the scatter, not the formal error, sets the error
        err = max(err, float(np.std(fl, ddof=1) / math.sqrt(len(fl))))
    return mu, err


def measure_color(lc):
    """W1-W2 (Vega). With >= 3 visits detected in both bands: median of the per-visit colours (robust for
    variables, whose W1 and W2 rise and fall together); else from the weighted-mean fluxes."""
    out = {"w1_w2": None, "w1_w2_err": None, "w1_w2_is_lower_limit": False, "verdict": "insufficient data"}
    if not lc.get("W1") or not lc.get("W2"):
        return out
    w2 = {round(p[0]): p for p in lc["W2"]}
    per_visit = [(-2.5 * math.log10(p1[1] / WISE_F0_JY["W1"]) + 2.5 * math.log10(p2[1] / WISE_F0_JY["W2"]),
                  1.0857 * math.hypot(p1[2] / p1[1], p2[2] / p2[1]))
                 for p1 in lc["W1"] if (p2 := w2.get(round(p1[0]))) and p1[1] >= 3 * p1[2] and p2[1] >= 3 * p2[2]]
    if len(per_visit) >= 3:
        cs, es = np.array(per_visit).T
        c = float(np.median(cs))
        out.update(w1_w2=c, w1_w2_err=max(1.253 * float(np.std(cs)), float(np.median(es))) / math.sqrt(len(cs)))
        return {**out, "verdict": _color_class(c)}
    (f1, e1), (f2, e2) = (_wmean(np.array([p[1] for p in lc[b]]), np.array([p[2] for p in lc[b]])) for b in ("W1", "W2"))
    if f2 / e2 < 5:
        return out
    if f1 / e1 >= 3:
        c = -2.5 * math.log10(f1 / WISE_F0_JY["W1"]) + 2.5 * math.log10(f2 / WISE_F0_JY["W2"])
        out.update(w1_w2=c, w1_w2_err=1.0857 * math.hypot(e1 / f1, e2 / f2))
    else:  # W1 not detected: 2-sigma upper limit on W1 -> lower limit on the colour
        c = -2.5 * math.log10((max(f1, 0) + 2 * e1) / WISE_F0_JY["W1"]) + 2.5 * math.log10(f2 / WISE_F0_JY["W2"])
        out.update(w1_w2=c, w1_w2_is_lower_limit=True)
    out["verdict"] = "insufficient data" if out["w1_w2_is_lower_limit"] and c < W12_EXTREME else _color_class(c)
    return out


def _color_class(c):
    return ("extremely red (Y/late-T dwarf-like)" if c >= W12_EXTREME else
            "red (L/T dwarf-like)" if c >= W12_RED else "normal star colors")


def _periodogram(t, mag, dmag):
    """Lomb-Scargle best period outside the cadence aliases -> (period_d, fap, alias_warning, alternatives)
    or None. alternatives: periods whose power is within 30% of the best and that the half-year visit cadence
    cannot tell apart from it (f +- 1/yr, f +- 2/yr): e.g. R Dra's 245 d and ~710 d look alike in NEOWISE."""
    span = float(t.max() - t.min())
    if len({round(x) for x in t}) < LS_MIN_EPOCHS or span <= 60:
        return None
    ls = LombScargle(t, mag, dmag)
    fmin, fmax = 2 / span, 1 / 30
    freq, power = ls.autopower(minimum_frequency=fmin, maximum_frequency=fmax, samples_per_peak=10)
    # NEOWISE visits every ~half year: power at harmonics of 1/yr is window function and scan-direction
    # systematics, not the star. Search outside them; warn when the overall highest peak sat there.
    harmonics = np.arange(1, 13) / CADENCE_D
    alias = np.min(np.abs(freq[:, None] - harmonics), axis=1) < 3 / span
    if alias.all():
        return None
    k = int(np.argmax(np.where(alias, -np.inf, power)))
    fap = float(ls.false_alarm_probability(power[k], minimum_frequency=fmin, maximum_frequency=fmax))
    alts = []
    for fa in {abs(freq[k] + s * j / CADENCE_D) for s in (-1, 1) for j in (1, 2)}:
        if fmin <= fa <= fmax and np.min(np.abs(fa - harmonics)) >= 3 / span:
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
        mu = float(np.sum(f / e**2) / np.sum(1 / e**2))
        e = np.hypot(e, floor * abs(mu))
        mu = float(np.sum(f / e**2) / np.sum(1 / e**2))
        chi2 = float(np.sum(((f - mu) / e) ** 2) / (len(f) - 1))
        p5, p95 = np.percentile(f, [5, 95])
        bands[b] = {"n": len(f), "chi2_red": chi2, "amplitude_mag": 2.5 * math.log10(p95 / p5) if p5 > 0 else None}
        pos = f > 0
        if pos.sum() >= LS_MIN_EPOCHS and (pg := _periodogram(t[pos], -2.5 * np.log10(f[pos]), 1.0857 * e[pos] / f[pos])):
            pgrams.append(pg)
    out = {"bands": bands, "verdict": "insufficient data", "period_days": None, "fap": None,
           "period_alias_warning": False, "period_alternatives_days": []}
    if not any(v["n"] >= 5 for v in bands.values()):
        return out
    variable = any(v["n"] >= 5 and v["chi2_red"] > VAR_CHI2 for v in bands.values())
    if pgrams:
        period, fap, alias, alts = min(pgrams, key=lambda p: p[1])
        out.update(fap=min(1.0, fap * len(pgrams)), period_alias_warning=alias or bool(alts))
        if out["fap"] < LS_FAP:
            out.update(period_days=period, period_alternatives_days=alts)
    out["verdict"] = ("periodic variable" if variable and out["period_days"] is not None else
                      "irregular variable" if variable else "constant")
    return out


def _catalog_rows(m):
    """Single-exposure profile-fit detections of the target: AllWISE multi-epoch photometry (2010-11) and
    NEOWISE (2014-24), one IRSA cone per 2-yr window around the PM-propagated position, then only detections
    within 3" of the position predicted at their own mjd."""
    t = m["target"]
    pm = math.hypot(t["pmra_masyr"], t["pmdec_masyr"]) / 1000
    windows = sorted({int((mjd_to_year(f["mjd"]) - 2010) // WINDOW_YR) for f in m["frames"] if f["survey"] == "wise"})
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
    path = seq_dir(m["id"]) / "catalog_lc.json"
    if path.exists():
        return json.loads(path.read_text())
    res = _clean(catalog_lightcurve(m))
    if m["status"] == "done":  # the epoch windows come from the frames
        path.write_text(json.dumps(res))
    return res


@router.get("/api/sequences/{sid}/catalog_lightcurve")
def catalog_lightcurve_route(sid: str):
    return _catalog_lc_cached(get_manifest(sid))


def photometry_lc(m):
    """-> (lc, source, note). Our WISE visit photometry ("pipeline") when >= 5 visits per band have a flux;
    else catalog profile-fit photometry ("catalog": saturated stars, which our apertures cannot measure).
    source None: catalog needed but IRSA unavailable."""
    lc = wise_lightcurve(m["frames"])
    if all(len(lc.get(b, [])) >= 5 for b in ("W1", "W2")):
        return lc, "pipeline", "WISE visit co-adds, 8.25\" aperture photometry"
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
        s.append(f"It moves across the sky: about {motion['pm_total_arcsec_yr']:.2f} arcseconds per year, measured over "
                 f"{motion['baseline_yr']:.0f} years ({motion['significance_sigma']:.0f} sigma){cat}.")
    elif motion["verdict"] == "not moving":
        s.append(f"No motion detected over {motion['baseline_yr']:.0f} years (less than about "
                 f"{3 * motion['pmra_err_masyr'] / 1000:.2f} arcseconds per year): a distant star, a galaxy, or too slow to see.")
    else:
        s.append("Not enough clear detections in separate years to measure whether it moves.")
    if color["w1_w2"] is not None:
        val = f"at least {color['w1_w2']:.1f}" if color["w1_w2_is_lower_limit"] else f"{color['w1_w2']:.2f}"
        s.append({"extremely red (Y/late-T dwarf-like)": f"Its infrared colour W1-W2 = {val} mag is extremely red, like the coldest brown dwarfs (late-T and Y).",
                  "red (L/T dwarf-like)": f"Its infrared colour W1-W2 = {val} mag is red, as for L/T brown dwarfs (dusty or very cool stars can look like this too).",
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
    if spec["verdict"] == "match":
        s.append(f"Its SPHEREx spectrum looks most like a {spec['best']['label']} brown-dwarf template "
                 f"(probability {spec['best']['prob']:.0%}).")
    elif spec["verdict"] == "insufficient data":
        s.append("Not enough clean SPHEREx measurements to read its spectrum.")
    else:
        s.append("Its SPHEREx spectrum does not look like an ultracool dwarf (no template fits well).")
    return s


def _cached(m, name, compute):
    """Result cached in the sequence directory, recomputed when the frame set changes; results that hit an
    unavailable external service (`_transient`) are not cached, so the next call retries."""
    key = [m["status"], len(m["frames"])]
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
    url = "https://ssp.imcce.fr/webservices/skybot/api/conesearch.php?" + urllib.parse.urlencode(
        {"-ep": f"{jd:.5f}", "-ra": ra, "-dec": dec, "-rs": round(radius_arcsec), "-mime": "json",
         "-output": "basic", "-loc": "500", "-from": "UltracoolBrowser"})
    with urllib.request.urlopen(url, timeout=60) as r:
        body = r.read()
    return json.loads(body) if body.strip() else []  # HTTP 204: nothing in the cone


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


def _summary(m):
    motion = measure_motion(m)
    lc, source, note = photometry_lc(m)
    floor = SATURATED_FLOOR if source == "catalog" and _saturated(m) else PHOT_FLOOR
    color = {**measure_color(lc), "source": source, "source_note": note}
    var = {**classify_variability(lc, floor), "source": source, "source_note": note}
    spec = classify(m["frames"])
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
    """dets: per window an array of (x, y, snr); years: window epochs. Linear tracks through >= 3 windows (and
    at least half of them), anchored on a detection in one of the first two and one of the last two windows,
    that are not explained by static sources -> list of dicts with the fit and the detections used."""
    W = len(dets)
    trees = [cKDTree(d[:, :2]) if len(d) else None for d in dets]

    def near(w, xy, r):
        return trees[w] is not None and bool(trees[w].query_ball_point(xy, r))

    static = []
    for w, d in enumerate(dets):
        others = [v for v in range(W) if v != w]
        static.append(np.array([sum(near(v, p[:2], STATIC_PX) for v in others) >= 0.5 * len(others) for p in d], bool))
    max_px_yr = MOVER_MAX_PM_ARCSEC / PIX_ARCSEC
    min_n = max(3, math.ceil(W / 2))
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
                    if fit["significance"] < MOVER_SIG or fit["chi2_red"] > 10:
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
    """CatWISE2020 (IRSA) and SIMBAD (Harvard mirror) sources in the field, cached; None per catalog on failure."""
    path = seq_dir(m["id"]) / "field_catalogs.json"
    cached = json.loads(path.read_text()) if path.exists() else {}
    wcs = _grid_wcs(m)
    ra0, dec0 = (float(v) for v in wcs.wcs.crval)
    r_deg = m["grid"]["width"] * PIX_ARCSEC / 3600 / math.sqrt(2) + 0.005
    if cached.get("catwise") is None:
        try:
            cached["catwise"] = [{"name": r["source_name"], "ra": r["ra_pm"], "dec": r["dec_pm"],
                                  "pmra": (r["pmra"] or 0) * 1000, "pmdec": (r["pmdec"] or 0) * 1000, "epoch": 2015.4}
                                 for r in _rows(irsa_gator("catwise_2020", ra0, dec0, r_deg * 3600,
                                                           ["source_name", "ra_pm", "dec_pm", "pmra", "pmdec"]))
                                 if r["ra_pm"] is not None]
        except Exception as e:  # noqa: BLE001
            log.warning("CatWISE field query failed: %s", e)
    if cached.get("simbad") is None:
        try:
            q = ("SELECT main_id, ra, dec, pmra, pmdec FROM basic WHERE CONTAINS(POINT('ICRS', ra, dec), "
                 f"CIRCLE('ICRS', {ra0}, {dec0}, {r_deg}))=1")
            url = "https://simbad.harvard.edu/simbad/sim-tap/sync?" + urllib.parse.urlencode(
                {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "votable", "QUERY": q})
            with urllib.request.urlopen(url, timeout=60) as resp:
                rows = _rows(resp.read())
            cached["simbad"] = [{"name": r["main_id"], "ra": r["ra"], "dec": r["dec"], "pmra": r["pmra"] or 0.0,
                                 "pmdec": r["pmdec"] or 0.0, "epoch": 2000.0} for r in rows if r["ra"] is not None]
        except Exception as e:  # noqa: BLE001
            log.warning("SIMBAD field query failed: %s", e)
    path.write_text(json.dumps(cached))
    return cached


def _match(cat, ra, dec, pmra, pmdec, r_arcsec=5.0):
    """Nearest catalog entry to the mover (each propagated to the catalog's epoch with the mover's PM); among
    entries within 1" of the nearest, the shortest name, so a star wins over its planets ("... b")."""
    hits = []
    for c in cat or []:
        pra, pdec = propagate(ra, dec, pmra, pmdec, REF_YR, c["epoch"])
        d = math.hypot(*_offsets_arcsec(c["ra"], c["dec"], pra, pdec))
        if d <= r_arcsec:
            hits.append((d, c["name"]))
    if not hits:
        return None
    d0 = min(h[0] for h in hits)
    return min((h for h in hits if h[0] <= d0 + 1.0), key=lambda h: len(h[1]))[1]


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


def find_movers(m):
    sid = m["id"]
    wcs = _grid_wcs(m)
    t = m["target"]
    fs = [f for f in m["frames"] if f["survey"] == "wise" and f["band"] == "W2"]
    wins: dict[int, list] = {}
    for f in fs:
        wins.setdefault(int((mjd_to_year(f["mjd"]) - 2010) // WINDOW_YR), []).append(f)
    keys = sorted(wins)
    if len(keys) < 3:
        return {"movers": [], "status": "insufficient data"}
    years = [float(np.mean([mjd_to_year(f["mjd"]) for f in wins[k]])) for k in keys]
    dets = [_detect(deep_stack([load_npy(sid, f["id"]) for f in wins[k]]), FWHM_PX["W2"]) for k in keys]
    tracks = find_tracks(dets, years)
    cats = _catalogs(m) if tracks else {}
    tx, ty = (float(v) for v in wcs.world_to_pixel_values(
        *propagate(t["ra"], t["dec"], t["pmra_masyr"], t["pmdec_masyr"], t["epoch_yr"], REF_YR)))
    ny = m["grid"]["height"]
    movers = []
    for tr in tracks:
        fit = tr["fit"]
        # fit was done on (-x, y) * PIX_ARCSEC: east/north offsets from the grid origin in arcsec
        x0, y0 = -fit["xi0"] / PIX_ARCSEC, fit["eta0"] / PIX_ARCSEC

        def track(ty_, x0=x0, y0=y0, fit=fit):
            dt = ty_ - fit["t0"]
            return x0 - fit["pmra"] / 1000 / PIX_ARCSEC * dt, y0 + fit["pmdec"] / 1000 / PIX_ARCSEC * dt

        x, y = track(REF_YR)
        ra, dec = (float(v) for v in wcs.pixel_to_world_values(x, y))
        col = _forced_color(m, wcs, track)
        known = {"simbad": _match(cats.get("simbad"), ra, dec, fit["pmra"], fit["pmdec"]),
                 "catwise": _match(cats.get("catwise"), ra, dec, fit["pmra"], fit["pmdec"]),
                 "spiff": None}
        sp = ucd.near(ra=ra, dec=dec, radius_arcsec=5.0, pmra_masyr=fit["pmra"], pmdec_masyr=fit["pmdec"], epoch_yr=REF_YR)
        if sp:
            known["spiff"] = f"{sp[0]['designation']} ({sp[0]['spiff_autotype']})"
        movers.append({"ra": ra, "dec": dec, "epoch_yr": REF_YR, "x_px": x, "y_px": ny - 1 - y,
                       "pmra_masyr": fit["pmra"], "pmdec_masyr": fit["pmdec"], "pm_err_masyr": fit["pmra_err"],
                       "significance_sigma": fit["significance"], "n_epochs": tr["n"],
                       "w1_w2": None if col["w1_w2_is_lower_limit"] else col["w1_w2"],
                       "w1_w2_lower_limit": col["w1_w2"] if col["w1_w2_is_lower_limit"] else None,
                       "known": known, "is_target": math.hypot(x - tx, y - ty) <= 3.0, "cpm_with": []})
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
    return {"movers": movers, "status": "ok",
            "_transient": bool(tracks) and (cats.get("catwise") is None or cats.get("simbad") is None)}


@router.get("/api/sequences/{sid}/movers")
def movers(sid: str):
    return _cached(get_manifest(sid), "movers.json", find_movers)
