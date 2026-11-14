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
from .frames import PIX_ARCSEC

log = logging.getLogger("ultracool.sources")
astropy_log.setLevel("WARNING")  # WCS-WAVE headers trigger a harmless SIP info message per frame
warnings.filterwarnings("ignore", category=FITSFixedWarning)  # deprecated RADECSYS in WISE headers

IRSA_SEM = threading.Semaphore(IRSA_MAX_CONCURRENCY)  # IRSA returns 503 above ~2 parallel requests
COLLECTIONS = ["spherex_dr1", "spherex_qr3", "wise_allsky", "neowiser"]
SIA_TTL_S = 7 * 86400
MARGIN_PX = 5


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


def _process(hdul, frame, grid_wcs, shape):
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
    img, _ = reproject_interp((sec, wsec), grid_wcs, shape_out=shape, order="bilinear")
    out = {"img": img.astype(np.float32), "flags_bad": None, "wavelength_um": None, "magzp": None}

    if frame.survey == "spherex":
        fh = hdul["FLAGS"].header
        badmask = 0
        for k in fh:
            if k.startswith("MSKN") and str(fh[k]).strip() != "SOURCE":
                badmask |= 1 << int(k[4:])
        flags = np.asarray(hdul["FLAGS"].section[y0:y1, x0:x1]).astype(np.int64)
        bad = ((flags & badmask) != 0).astype(np.float32)
        bad_g, _ = reproject_interp((bad, wsec), grid_wcs, shape_out=shape, order="nearest-neighbor")
        out["flags_bad"] = np.nan_to_num(bad_g) > 0.5
        ww = WCS(hdu.header, fobj=hdul, key="W")
        ww.sip = None
        cx, cy = fw.world_to_pixel(grid_wcs.pixel_to_world((nx - 1) / 2, (ny - 1) / 2))
        out["wavelength_um"] = float(ww.pixel_to_world(cx, cy)[0].to_value(u.um))
    else:
        out["magzp"] = float(hdu.header["MAGZP"])
    return out


def read_section(frame, grid_wcs, shape):
    """Frame resampled onto the grid: {img, flags_bad, wavelength_um, magzp}. Raises NoOverlap."""
    try:
        if not frame.bucket:
            raise FileNotFoundError("no S3 copy")
        with _fs(frame.region).open(f"{frame.bucket}/{frame.key}", "rb", block_size=256 * 1024,
                                    cache_type="bytes") as fh, fits.open(fh) as hdul:
            return _process(hdul, frame, grid_wcs, shape)
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
    with fits.open(io.BytesIO(data)) as hdul:
        return _process(hdul, frame, grid_wcs, shape)
