"""Grid geometry, photometry and PNG rendering. Pure numpy/astropy; only render_png touches disk."""
import math
import warnings

import numpy as np
from astropy.stats import SigmaClip, sigma_clip
from astropy.wcs import WCS
from photutils.aperture import ApertureStats, CircularAnnulus, CircularAperture, aperture_photometry
from PIL import Image

PIX_ARCSEC = 2.75  # WISE native; every survey is resampled onto this so frames align


def propagate(ra, dec, pmra_masyr, pmdec_masyr, epoch_yr, t_yr):
    """Linear proper-motion propagation (pmra includes cos dec, as SIMBAD/Gaia give it)."""
    dt = t_yr - epoch_yr
    return (ra + pmra_masyr / 3.6e6 / math.cos(math.radians(dec)) * dt,
            dec + pmdec_masyr / 3.6e6 * dt)


def mjd_to_year(mjd):
    return 2000.0 + (mjd - 51544.5) / 365.25


def default_fov_deg(pm_total_arcsec_yr):
    # wide enough that a 16-year track fits
    return min(0.25, max(0.05, pm_total_arcsec_yr * 16 / 3600 + 0.03))


def make_grid(ra_c, dec_c, fov_deg):
    n = math.ceil(fov_deg * 3600 / PIX_ARCSEC)
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [ra_c, dec_c]
    w.wcs.crpix = [(n + 1) / 2, (n + 1) / 2]
    w.wcs.cdelt = [-PIX_ARCSEC / 3600, PIX_ARCSEC / 3600]
    w.wcs.radesys = "ICRS"
    return w, (n, n)


def grid_wcs_json(wcs, shape):
    ny, nx = shape
    return {"NAXIS": 2, "NAXIS1": nx, "NAXIS2": ny, "CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN",
            "CRVAL1": float(wcs.wcs.crval[0]), "CRVAL2": float(wcs.wcs.crval[1]),
            "CRPIX1": float(wcs.wcs.crpix[0]), "CRPIX2": float(wcs.wcs.crpix[1]),
            "CDELT1": float(wcs.wcs.cdelt[0]), "CDELT2": float(wcs.wcs.cdelt[1]), "RADESYS": "ICRS"}


def group_by_gap(mjds, gap_days):
    """Group index per input (input sorted ascending); a new group starts after a gap > gap_days."""
    out, g = [], 0
    for i, m in enumerate(mjds):
        if i and m - mjds[i - 1] > gap_days:
            g += 1
        out.append(g)
    return out


def _radius(shape, x, y):
    yy, xx = np.indices(shape)
    return np.hypot(xx - x, yy - y)


def aperture_flux(img, x, y, r_ap=3, r_in=6, r_out=10, var=None, mask=None, bkg_mask=None):
    """Background-subtracted aperture sum -> (net, err), in image units x pixels.
    photutils with exact pixel overlap; background = 3-sigma-clipped annulus median.
    err = per-pixel variance (if given, else annulus scatter) plus the error of the background level.
    mask: pixels unusable everywhere (NaN always are); bkg_mask: extra pixels kept out of the annulus only
    (e.g. other sources). More than 20% of the aperture unusable -> (nan, nan)."""
    bad = ~np.isfinite(img) if mask is None else (mask | ~np.isfinite(img))
    ap = CircularAperture((x, y), r_ap)
    ann = CircularAnnulus((x, y), r_in, r_out)
    good_area = float(ap.area_overlap(img, mask=bad))
    if not good_area or good_area < 0.8 * ap.area:
        return math.nan, math.nan
    for bm in ((bad | bkg_mask) if bkg_mask is not None else bad, bad):  # drop bkg_mask if it leaves too little sky
        st = ApertureStats(img, ann, mask=bm, sigma_clip=SigmaClip(sigma=3))
        n_bkg = float(st.sum_aper_area.value)
        if n_bkg >= 10 and math.isfinite(st.median):
            break
    else:
        return math.nan, math.nan
    phot = aperture_photometry(np.where(bad, 0.0, img - st.median), ap, mask=bad, method="exact",
                               error=None if var is None else np.sqrt(np.where(bad, 0.0, var)))
    src_var = float(phot["aperture_sum_err"][0]) ** 2 if var is not None else st.std ** 2 * good_area
    scale = ap.area / good_area  # stand in for the few masked aperture pixels
    net = float(phot["aperture_sum"][0]) * scale
    err = math.sqrt(src_var + st.std ** 2 * good_area ** 2 / n_bkg) * scale
    return net, err


def any_within(mask, x, y, r):
    return bool(mask[_radius(mask.shape, x, y) <= r].any())


def render_png(img, path):
    """asinh-stretched 8-bit grayscale, row 0 = max Dec (flipud), so it matches FITS-style WCS in Aladin.
    shortcut: per-frame stretch hides brightness changes (use the light curve); upgrade = per-band global cuts."""
    a = np.array(img, dtype=np.float64)
    finite = np.isfinite(a)
    if not finite.any():
        a = np.zeros_like(a)
    else:
        a[~finite] = np.nanmin(a)
    lo, hi = np.percentile(a, [0.5, 99.5])
    x = np.clip((a - lo) / (hi - lo if hi > lo else 1.0), 0, 1)
    x = np.arcsinh(10 * x) / np.arcsinh(10)
    Image.fromarray(np.flipud((x * 255).round().astype(np.uint8)), "L").save(path, format="PNG")


def _robust_norm(x):
    med = np.nanmedian(x)
    mad = 1.4826 * np.nanmedian(np.abs(x - med))
    return (x - med) / (mad if mad > 0 else 1.0)


def render_diff_png(a, b, path):
    """b - a in robust sigma units, clipped to +-5: red = brighter in b, blue = brighter in a, gray = no change."""
    v = np.nan_to_num(np.clip(_robust_norm(b) - _robust_norm(a), -5, 5) / 5)
    pos, neg = np.clip(v, 0, 1), np.clip(-v, 0, 1)
    dim = 128 * (1 - np.abs(v))
    rgb = np.stack([dim + 255 * pos, dim, dim + 255 * neg], axis=-1)
    Image.fromarray(np.flipud(np.clip(rgb, 0, 255).round().astype(np.uint8)), "RGB").save(path, format="PNG")


def deep_stack(imgs):
    """3-sigma-clipped mean of robust-normalised frames, in sigma units of the result.
    Mean beats median by ~25% in depth; clipping drops cosmic rays and hot pixels."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN pixels at frame edges
        # mad_std: with plain std a lone outlier among few frames (e.g. 4 WISE visits) can never exceed 3 sigma
        clipped = sigma_clip(np.stack([_robust_norm(i) for i in imgs]), sigma=3, stdfunc="mad_std", axis=0)
        return _robust_norm(clipped.mean(axis=0).filled(np.nan))


def render_sigma_png(z, path, lo=-1.5, hi=6.0):
    """Linear display of an image in sigma units: faint 3-5 sigma sources show as mid-grey blobs."""
    x = np.clip((np.nan_to_num(z, nan=lo) - lo) / (hi - lo), 0, 1)
    Image.fromarray(np.flipud((x * 255).round().astype(np.uint8)), "L").save(path, format="PNG")
