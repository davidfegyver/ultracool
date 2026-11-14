"""IRSA SIA frame discovery and on-grid section reads (anonymous S3 byte ranges, IBE cutout fallback)."""
import hashlib
import io
import json
import logging
import math
import threading
import time
import urllib.request
import warnings
from dataclasses import asdict, dataclass

import astropy.units as u
import numpy as np
import s3fs
from astropy import log as astropy_log
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS, FITSFixedWarning
from astroquery.ipac.irsa import Irsa
from reproject import reproject_interp

from .config import CACHE_DIR, IRSA_MAX_CONCURRENCY, S3_MAX_CONCURRENCY
from .frames import PIX_ARCSEC, any_within, aperture_flux

log = logging.getLogger("ultracool.sources")
astropy_log.setLevel("WARNING")  # WCS-WAVE headers trigger a harmless SIP info message per frame
warnings.filterwarnings("ignore", category=FITSFixedWarning)  # deprecated RADECSYS in WISE headers

IRSA_SEM = threading.Semaphore(IRSA_MAX_CONCURRENCY)  # IRSA returns 503 above ~2 parallel requests
COLLECTIONS = ["spherex_dr1", "spherex_qr3", "wise_allsky", "neowiser"]
SIA_TTL_S = 7 * 86400
MARGIN_PX = 8  # native pixels around the grid footprint; must cover the SPHEREx background annulus
SX_R_AP, SX_R_IN, SX_R_OUT = 2.0, 4.0, 7.0  # SPHEREx photometry radii in native 6.15" pixels
BENIGN_FLAGS = {"SOURCE", "FULLSAMPLE"}  # informational bits, not data problems


class NoOverlap(Exception):
    pass


@dataclass
class RawFrame:
    survey: str
    band: str
    mjd: float
    access_url: str
    bucket: str
    key: str
    region: str
    stem: str


def irsa_retry(fn):
    for i, delay in enumerate([5, 15, 45, None]):
        try:
            with IRSA_SEM:
                return fn()
        except Exception as e:  # noqa: BLE001 - IRSA throws assorted HTTP/VO errors
            if delay is None:
                raise
            log.warning("IRSA call failed (%s), retry %d in %ds", e, i + 1, delay)
            time.sleep(delay)


def query_frames(ra, dec):
    path = CACHE_DIR / "sia" / f"{hashlib.sha1(f'{ra:.5f},{dec:.5f}'.encode()).hexdigest()}.json"
    if path.exists() and time.time() - path.stat().st_mtime < SIA_TTL_S:
        return [RawFrame(**d) for d in json.loads(path.read_text())]
    pos = (SkyCoord(ra, dec, unit="deg"), 1 * u.arcsec)
    out = []
    for c in COLLECTIONS:
        t = irsa_retry(lambda: Irsa.query_sia(pos=pos, collection=c))
        survey = "spherex" if c.startswith("spherex") else "wise"
        for r in t:
            if str(r["dataproduct_subtype"]) != "science":
                continue
            url = str(r["access_url"])
            band = str(r["energy_bandpassname"]).replace("SPHEREx-", "")
            if survey == "wise" and (band not in ("W1", "W2") or not url.endswith("-int-1b.fits")):
                continue
            aws = json.loads(str(r["cloud_access"]) or "{}").get("aws", {})
            out.append(RawFrame(survey, band, float(r["t_min"]), url, aws.get("bucket_name", ""),
                                aws.get("key", ""), aws.get("region", ""), url.rsplit("/", 1)[1].removesuffix(".fits")))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(f) for f in out]))
    return out


_s3: dict[str, s3fs.S3FileSystem] = {}
_s3_lock = threading.Lock()


def _fs(region):
    with _s3_lock:
        if region not in _s3:
            # botocore defaults to 10 pooled connections, which would cap S3_MAX_CONCURRENCY (~35% slower at 32)
            _s3[region] = s3fs.S3FileSystem(anon=True, client_kwargs={"region_name": region},
                                            config_kwargs={"max_pool_connections": S3_MAX_CONCURRENCY})
        return _s3[region]


def _pixel_sr(w, x, y):
    """Solid angle of the detector pixel at (x, y), from the full (SIP-distorted) WCS."""
    c = w.pixel_to_world([x, x + 1, x], [y, y, y + 1])
    ax, ay = c[0].spherical_offsets_to(c[1])
    bx, by = c[0].spherical_offsets_to(c[2])
    return abs(ax.rad * by.rad - ay.rad * bx.rad)


def _psf_enclosed(hdul, fh, x, y, r, wavelength_um, cutout):
    """Fraction of the EPSF flux within r native pixels: the aperture correction.
    EPSF holds 33x33 PSFs (oversampled OVSMPX x) for a uniform grid of detector zones, x-fast then y,
    ~8.7 KB per row, so on S3 only row 0 and the target's row are read (not the 3.9 MB table).
    IBE cutouts lose detector coordinates; there the zone with the nearest wavelength is used."""
    i = hdul.index_of("EPSF")
    hdu = hdul[i]
    if cutout:
        t = hdu.data
        psf = t["EPSF"][int(np.argmin(np.abs(t["CWAVE"] - wavelength_um)))]
    else:
        start, rowlen = hdul.fileinfo(i)["datLoc"], hdu.header["NAXIS1"]
        dtype = hdu.columns.dtype.newbyteorder(">")

        def row(k):
            fh.seek(start + k * rowlen)
            return np.frombuffer(fh.read(rowlen), dtype=dtype)[0]

        r0 = row(0)
        ny_d, nx_d = hdul["IMAGE"].shape
        nbx, nby = round(nx_d / float(r0["XWIDTH"])), round(ny_d / float(r0["YWIDTH"]))
        bx = min(nbx - 1, max(0, int(x / float(r0["XWIDTH"]))))
        by = min(nby - 1, max(0, int(y / float(r0["YWIDTH"]))))
        rk = row(by * nbx + bx)
        if abs(rk["XCENTER"] - x) > rk["XWIDTH"] or abs(rk["YCENTER"] - y) > rk["YWIDTH"]:
            raise ValueError(f"EPSF zone layout not as expected at ({x:.0f}, {y:.0f})")
        psf = rk["EPSF"]
    os_ = hdu.header["OVSMPX"]
    n = int(round(math.sqrt(np.size(psf))))
    psf = np.asarray(psf, dtype=float).reshape(n, n)
    yy, xx = np.indices(psf.shape)
    rr = np.hypot(xx - (n - 1) / 2, yy - (n - 1) / 2) / os_
    return float(psf[rr <= r].sum() / psf.sum())


def _spherex_phot(hdul, fh, fw, sec, x0, y0, target, wavelength_um, cutout):
    """Forced aperture photometry on native pixels -> {flux_ujy, err_ujy, flagged, apcorr} or None (off section)."""
    x, y = (float(v) for v in fw.world_to_pixel(SkyCoord(*target, unit="deg")))
    xs, ys = x - x0, y - y0
    h, w = sec.shape
    if not (0 <= xs < w and 0 <= ys < h):
        return None
    names = {int(k[4:]): str(v).strip() for k, v in hdul["FLAGS"].header.items() if k.startswith("MSKN")}
    badmask = sum(1 << b for b, n in names.items() if n not in BENIGN_FLAGS)
    srcmask = sum(1 << b for b, n in names.items() if n == "SOURCE")
    flags = np.asarray(hdul["FLAGS"].section[y0:y0 + h, x0:x0 + w]).astype(np.int64)
    var = np.asarray(hdul["VARIANCE"].section[y0:y0 + h, x0:x0 + w], dtype=np.float64)
    bad = (flags & badmask) != 0
    net, err = aperture_flux(sec.astype(np.float64), xs, ys, SX_R_AP, SX_R_IN, SX_R_OUT,
                             var=var, mask=bad, bkg_mask=(flags & srcmask) != 0)
    flagged = any_within(bad, xs, ys, SX_R_AP)
    if not math.isfinite(net):
        return {"flux_ujy": None, "err_ujy": None, "flagged": flagged, "apcorr": None}
    apcorr = _psf_enclosed(hdul, fh, x, y, SX_R_AP, wavelength_um, cutout)
    k = _pixel_sr(fw, x, y) * 1e12 / apcorr  # MJy/sr * sr -> MJy -> uJy, then total flux
    return {"flux_ujy": net * k, "err_ujy": err * k, "flagged": flagged, "apcorr": apcorr}


def _process(hdul, fh, frame, grid_wcs, shape, target, cutout=False):
    hdu = hdul["IMAGE"] if frame.survey == "spherex" else hdul[0]
    fw = WCS(hdu.header)
    ny_d, nx_d = hdu.shape
    ny, nx = shape
    corners = grid_wcs.pixel_to_world([-0.5, nx - 0.5, nx - 0.5, -0.5], [-0.5, -0.5, ny - 0.5, ny - 0.5])
    xs, ys = fw.world_to_pixel(corners)
    if not (np.all(np.isfinite(xs)) and np.all(np.isfinite(ys))):
        raise NoOverlap
    x0 = max(0, math.floor(xs.min()) - MARGIN_PX)
    x1 = min(nx_d, math.ceil(xs.max()) + MARGIN_PX + 1)
    y0 = max(0, math.floor(ys.min()) - MARGIN_PX)
    y1 = min(ny_d, math.ceil(ys.max()) + MARGIN_PX + 1)
    if x0 >= x1 or y0 >= y1:
        raise NoOverlap
    sec = np.asarray(hdu.section[y0:y1, x0:x1], dtype=np.float32)
    wsec = fw[y0:y1, x0:x1]
    # the resampled grid image is for display and stacking only; photometry uses native pixels
    img, _ = reproject_interp((sec, wsec), grid_wcs, shape_out=shape, order="bilinear")
    out = {"img": img.astype(np.float32), "wavelength_um": None, "magzp": None, "phot": None}

    if frame.survey == "spherex":
        ww = WCS(hdu.header, fobj=hdul, key="W")
        ww.sip = None
        tx, ty = fw.world_to_pixel(SkyCoord(*target, unit="deg"))
        out["wavelength_um"] = float(ww.pixel_to_world(tx, ty)[0].to_value(u.um))
        out["phot"] = _spherex_phot(hdul, fh, fw, sec, x0, y0, target, out["wavelength_um"], cutout)
    else:
        out["magzp"] = float(hdu.header["MAGZP"])
    return out


def read_section(frame, grid_wcs, shape, target):
    """Frame resampled onto the grid plus native-pixel photometry at target (ra, dec) for SPHEREx:
    {img, wavelength_um, magzp, phot}. Raises NoOverlap."""
    try:
        if not frame.bucket:
            raise FileNotFoundError("no S3 copy")
        with _fs(frame.region).open(f"{frame.bucket}/{frame.key}", "rb", block_size=256 * 1024,
                                    cache_type="bytes") as fh, fits.open(fh) as hdul:
            return _process(hdul, fh, frame, grid_wcs, shape, target)
    except NoOverlap:
        raise
    except Exception as e:  # noqa: BLE001 - any S3 failure falls back to IRSA cutouts
        log.warning("S3 read failed for %s (%s); IBE cutout fallback", frame.stem, e)
    ra, dec = grid_wcs.wcs.crval
    size = shape[1] * PIX_ARCSEC / 3600 * 1.2

    def fetch():
        with urllib.request.urlopen(f"{frame.access_url}?center={ra},{dec}&size={size}", timeout=120) as r:
            return r.read()

    data = irsa_retry(fetch)
    with io.BytesIO(data) as fh, fits.open(fh) as hdul:
        return _process(hdul, fh, frame, grid_wcs, shape, target, cutout=True)
