"""Neighbour-aware SPHEREx photometry on the cached grid frames: the target and every CatWISE2020 source near it
are fitted together with one Gaussian PSF per frame, so light of neighbours inside SPHEREx's 6.15" pixels is
modelled instead of landing in the target's aperture. Analysis layer only: uses the stored grid images, no new
downloads; results are cached per frame next to the manifest."""
import hashlib
import json
import math

import numpy as np
from astropy.wcs import WCS

from .config import write_json
from .frames import PIX_ARCSEC, mjd_to_year, pixel_sigma, propagate
from .sequences import load_npy, seq_dir
from .sources import GRID_SR, SX_GRID_R

FIT_R_PX = 12.0  # fitted cutout radius around the target (33")
SRC_R_PX = 16.0  # sources this close to the target are in the model (their PSF reaches the cutout)
# a catalog entry this close to the target at the catalog epoch is the target itself (positions/motions of
# SIMBAD and CatWISE differ by 3" for 2MASS J1821+1414) or an unresolvable blend: two sources < 1/2 PSF FWHM
# apart cannot be fitted separately, so it is left in the target
OWN_ENTRY_ARCSEC = 5.0
PM_MIN_SIGMA = 5.0
# Gaussian sigma searched per frame, grid px: SPHEREx PSF (~1 native 6.15" px) after bilinear resampling to 2.75"
# fits at 1.5-1.65 px on bright isolated stars (LP 944-20, 2MASS J0746+20, Kelu-1)
SIGMAS_PX = np.arange(1.2, 2.41, 0.15)
SX_AP_PX = SX_GRID_R[0]  # the native target aperture (12.3"), for the neighbour-light fraction
VERSION = 1  # bump when the fit changes: cached per-frame results are recomputed
# Error model, calibrated on empty sky (research/spectra/validation/empty_sky.py -> empty_sky.json, fit in
# empty_sky_fit.json: 12 'clear' positions >= 11" and 12 'near' positions 5.5-11" from CatWISE sources in each of
# 20 validation fields, 108,597 frame fits; flux/error of a source-free position should scatter by 1):
# err = hypot(least-squares error x ERR_SCALE[band] x (1 + min(0.5, 0.5 r)), NB_ERR_FRAC x neighbour light),
# r = |neighbour light in the aperture| / least-squares error. ERR_SCALE = robust std of flux/error at clear
# positions with r < 0.3 (resampled pixels are correlated, so the formal error is low; most in D1, D5-D6).
# Next to neighbours the Gaussian PSF misfits their wings: raw robust std 1.7-2.6 there, 0.6-1.3 after.
ERR_SCALE = {"D1": 1.56, "D2": 1.08, "D3": 1.0, "D4": 1.05, "D5": 1.37, "D6": 1.85}
NB_ERR_FRAC = 0.04
# PSF-fit flux -> the native EPSF-corrected aperture flux scale: median native / PSF flux over frames at S/N > 20
# of five isolated validation dwarfs (neighbour light < 2% in every band: LP 944-20, LSR J1835+3259,
# 2MASS J0036+1821, J0746+2000, J0825+2115); per-object spread 1-3%. Without it D5-D6 read ~4% low against D2.
PSF_CAL = {"D1": 1.031, "D2": 1.012, "D3": 1.033, "D4": 1.025, "D5": 1.054, "D6": 1.059}


def calibrated_err(err, nb_ap, band):
    return math.hypot(err * ERR_SCALE.get(band, 1.0) * (1 + min(0.5, 0.5 * abs(nb_ap) / err)), NB_ERR_FRAC * nb_ap)


def fit_frame(img, srcs, sigma_noise, sigmas=SIGMAS_PX):
    """Fluxes of point sources at fixed grid positions srcs [(x, y), ...] (first = target) + a constant sky,
    one Gaussian PSF whose width is chosen by least chi2 -> (flux, err, nb_ap, sigma_px) in image units x pixels,
    or None (cutout mostly off the frame). err is the least-squares error scaled up by sqrt(chi2_red) when the
    model fits worse than the noise (PSF mismatch around bright sources). nb_ap = fitted neighbour light inside
    the target's aperture."""
    x0, y0 = srcs[0]
    ny, nx = img.shape
    ylo, yhi = max(0, int(y0 - FIT_R_PX)), min(ny, int(y0 + FIT_R_PX) + 2)
    xlo, xhi = max(0, int(x0 - FIT_R_PX)), min(nx, int(x0 + FIT_R_PX) + 2)
    yy, xx = np.mgrid[ylo:yhi, xlo:xhi]
    cut = img[ylo:yhi, xlo:xhi]
    sel = (np.hypot(xx - x0, yy - y0) <= FIT_R_PX) & np.isfinite(cut)
    if sel.sum() < 0.7 * math.pi * FIT_R_PX ** 2 or not sigma_noise > 0:
        return None
    X, Y, z = xx[sel], yy[sel], cut[sel].astype(np.float64)
    in_ap = np.hypot(X - x0, Y - y0) <= SX_AP_PX
    best = None
    for s in sigmas:
        cols = [np.exp(-((X - sx) ** 2 + (Y - sy) ** 2) / (2 * s * s)) / (2 * math.pi * s * s) for sx, sy in srcs]
        A = np.column_stack(cols + [np.ones_like(z)])
        coef, *_ = np.linalg.lstsq(A, z, rcond=None)
        chi2 = float(np.sum((z - A @ coef) ** 2)) / sigma_noise ** 2
        if best is None or chi2 < best[0]:
            best = (chi2, s, coef, A)
    chi2, s, coef, A = best
    dof = max(1, len(z) - A.shape[1])
    cov = np.linalg.pinv(A.T @ A) * sigma_noise ** 2 * max(1.0, chi2 / dof)
    nb_ap = float(sum(coef[k] * A[in_ap, k].sum() for k in range(1, len(srcs))))
    return float(coef[0]), float(math.sqrt(cov[0, 0])), nb_ap, float(s)


def _catalog_at(cat, t, yr):
    """-> (rows (ra, dec, pmra, pmdec, epoch), separation from the target at epoch yr in ", True where the entry
    is within OWN_ENTRY_ARCSEC of the target at the catalog epoch). A catalog motion below PM_MIN_SIGMA is set
    to zero: spurious CatWISE motions of sources next to a mover (J1821+1414: 0.5"/yr for a static neighbour)
    would otherwise walk them onto the target."""
    c = np.array([(r["ra"], r["dec"], r["pmra"], r["pmdec"], r["epoch"]) for r in cat], float).reshape(-1, 5).T
    sig = np.array([r.get("sigpm") or 0.0 for r in cat], float)
    c[2:4, np.hypot(c[2], c[3]) < PM_MIN_SIGMA * sig] = 0.0
    tra, tde = propagate(t["ra"], t["dec"], t["pmra_masyr"], t["pmdec_masyr"], t["epoch_yr"], c[4])
    own = np.hypot((c[0] - tra) * np.cos(np.radians(tde)), c[1] - tde) * 3600 < OWN_ENTRY_ARCSEC
    ra, de = propagate(*c, yr)
    tra, tde = propagate(t["ra"], t["dec"], t["pmra_masyr"], t["pmdec_masyr"], t["epoch_yr"], yr)
    return c, np.hypot((ra - tra) * np.cos(np.radians(tde)), de - tde) * 3600, own


def _neighbours(cat, t, yr):
    """Catalog sources (not the target's own entry, nor blended with it at the catalog epoch or at yr) within
    SRC_R_PX + 1 px of the target at epoch yr -> array rows (ra, dec, pmra, pmdec, epoch)."""
    c, d, own = _catalog_at(cat or [], t, yr)
    return c[:, ~own & (d >= OWN_ENTRY_ARCSEC) & (d <= (SRC_R_PX + 1) * PIX_ARCSEC)]


def blends(cat, t, yr):
    """Separations (") at epoch yr of catalog sources within OWN_ENTRY_ARCSEC of the target other than the
    nearest (the target's own entry): unresolvable in SPHEREx's 6" pixels, their light stays in the target."""
    _, d, _ = _catalog_at(cat or [], t, yr)
    d = np.sort(d)
    return [round(float(x), 1) for x in d[1:][d[1:] < OWN_ENTRY_ARCSEC]]


def _cache_path(m):
    key = json.dumps([VERSION, m["target"]], sort_keys=True)
    return seq_dir(m["id"]) / f"psfphot_{hashlib.sha1(key.encode()).hexdigest()[:12]}.json"


def photometry(m, cat, cache=True):
    """Neighbour-aware photometry of every unflagged SPHEREx frame of m at m["target"] -> {frame_id: {flux_ujy,
    flux_err_ujy, nb_ap_ujy, sigma_px}} (None per frame off the grid). cat: CatWISE2020 rows (ra, dec, pmra,
    pmdec in mas/yr, epoch). Cached per frame in the sequence directory (cache=False for probe positions)."""
    path = _cache_path(m)
    got = json.loads(path.read_text()) if cache and path.exists() else {}
    todo = [f for f in m["frames"] if f["survey"] == "spherex" and f["id"] not in got and not f["flagged"]
            and f.get("wavelength_um") is not None]
    if not todo:
        return got
    t = m["target"]
    wcs = WCS(m["grid"]["wcs"])
    yrs = [mjd_to_year(f["mjd"]) for f in todo]
    nb = _neighbours(cat, t, float(np.median(yrs)))
    for f, yr in zip(todo, yrs):
        img = load_npy(m["id"], f["id"])
        tx, ty = wcs.world_to_pixel_values(*propagate(t["ra"], t["dec"], t["pmra_masyr"], t["pmdec_masyr"],
                                                      t["epoch_yr"], yr))
        nx, ny = wcs.world_to_pixel_values(*propagate(*nb, yr))
        keep = np.hypot(nx - tx, ny - ty) <= SRC_R_PX
        r = fit_frame(img, [(float(tx), float(ty))] + list(zip(nx[keep].tolist(), ny[keep].tolist())), pixel_sigma(img))
        k = GRID_SR * 1e12 * PSF_CAL.get(f["band"], 1.0)  # MJy/sr x grid pixels -> uJy, native flux scale
        got[f["id"]] = None if r is None else {
            "flux_ujy": r[0] * k, "nb_ap_ujy": r[2] * k, "sigma_px": r[3], "raw_err_ujy": r[1] * k,
            "flux_err_ujy": calibrated_err(r[1], r[2], f["band"]) * k}
    if cache:
        write_json(path, got)
    return got
