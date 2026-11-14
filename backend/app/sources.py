"""IRSA SIA frame discovery and on-grid section reads (anonymous S3 byte ranges, IBE cutout fallback)."""
import gzip
import hashlib
import io
import json
import logging
import math
import multiprocessing
import threading
import time
import urllib.parse
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
from .frames import PIX_ARCSEC, _radius, aperture_flux

log = logging.getLogger("ultracool.sources")
astropy_log.setLevel("WARNING")  # WCS-WAVE headers trigger a harmless SIP info message per frame
warnings.filterwarnings("ignore", category=FITSFixedWarning)  # deprecated RADECSYS in WISE headers

# IRSA returns 503 above ~2 parallel requests; a process-shared semaphore so frame worker processes
# (sequences.PROC_POOL, given this object at start) and the API process share one budget
IRSA_SEM = multiprocessing.get_context("spawn").Semaphore(IRSA_MAX_CONCURRENCY)
COLLECTIONS = ["spherex_dr1", "spherex_qr3", "wise_allsky", "neowiser"]
SIA_TTL_S = 7 * 86400
MARGIN_PX = 8  # native pixels around the grid footprint; must cover the SPHEREx background annulus
SX_R_AP, SX_R_IN, SX_R_OUT = 2.0, 4.0, 7.0  # SPHEREx photometry radii in native 6.15" pixels
BENIGN_FLAGS = {"SOURCE", "FULLSAMPLE"}  # informational bits, not data problems
# IRSA's conservative L1b mask (NEOWISE Explanatory Supplement III.3.d: bits 1,3,4,6,9,10-19,21,30) minus the
# saturation bits 11-18: those pixels keep a valid ramp fit from the unsaturated first reads, and the clipped
# visit mean handles the rest. Fatal pixels (incl. saturated already in read 1) are NaN in the image anyway.
WISE_BAD_BITS = sum(1 << b for b in (1, 3, 4, 6, 9, 10, 19, 21, 30))
WISE_SAT_BITS = sum(1 << b for b in range(10, 19))
# artifact tables next to each L1b image: positions of spurious detections of diffraction spikes, halos,
# optical ghosts and latents (short-term P, anneal-resistant R); a hit within one PSF FWHM names the target
WISE_ART = {"D": "SPIKE", "H": "HALO", "O": "GHOST", "P": "LATENT", "R": "LATENT"}
WISE_ART_R_ARCSEC = 6.0
WISE_R_AP_NATIVE = 3.0  # 8.25" standard aperture in native 2.75" pixels


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


def irsa_scs(ra, dec, radius_deg, table="catwise_2020"):
    """IRSA simple cone search -> VOTable bytes (retried, under IRSA_SEM)."""
    url = "https://irsa.ipac.caltech.edu/SCS?" + urllib.parse.urlencode(
        {"table": table, "RA": ra, "DEC": dec, "SR": radius_deg})

    def fetch():
        with urllib.request.urlopen(url, timeout=120) as r:
            return r.read()

    return irsa_retry(fetch)


def irsa_gator(catalog, ra, dec, radius_arcsec, cols):
    """IRSA Gator cone query with column selection -> VOTable bytes (retried, under IRSA_SEM). Used for
    catalog look-ups by the analysis: answers when the SCS front end returns 502, and selcols keeps the
    huge NEOWISE single-exposure table small."""
    url = "https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query?" + urllib.parse.urlencode(
        {"catalog": catalog, "spatial": "cone", "radius": radius_arcsec, "radunits": "arcsec",
         "objstr": f"{ra:.6f} {dec:+.6f}", "outfmt": 3, "selcols": ",".join(cols)})

    def fetch():
        with urllib.request.urlopen(url, timeout=180) as r:
            data = r.read()
        if b"<VOTABLE" not in data[:2000]:
            raise RuntimeError(f"Gator: not a VOTable: {data[:200]!r}")
        return data

    return irsa_retry(fetch)


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
    """Forced aperture photometry on native pixels -> {flux_ujy, err_ujy, flagged, flag_names, apcorr}
    or None (off section)."""
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
    hit = int(np.bitwise_or.reduce(flags[_radius(flags.shape, xs, ys) <= SX_R_AP], initial=0)) & badmask
    flag_names = sorted({n for b, n in names.items() if hit >> b & 1})
    out = {"flux_ujy": None, "err_ujy": None, "flagged": bool(hit), "flag_names": flag_names, "apcorr": None}
    if not math.isfinite(net):
        return out
    apcorr = _psf_enclosed(hdul, fh, x, y, SX_R_AP, wavelength_um, cutout)
    k = _pixel_sr(fw, x, y) * 1e12 / apcorr  # MJy/sr * sr -> MJy -> uJy, then total flux
    return {**out, "flux_ujy": net * k, "err_ujy": err * k, "apcorr": apcorr}


def _wise_extras(frame):
    """L1b bit mask (gzip, read whole: ~150 KB) and artifact tables stored next to the -int-1b.fits key.
    -> (mask array | None, {artifact name: [(ra, dec), ...]}). Missing files are skipped."""
    bl = frame.band.lower()
    base = frame.key.removesuffix(f"-{bl}-int-1b.fits")
    paths = [f"{frame.bucket}/{base}-{bl}-msk-1b.fits.gz"] + [f"{frame.bucket}/{base}-art-{bl}-{c}.tbl" for c in WISE_ART]
    got = _fs(frame.region).cat(paths, on_error="omit")
    msk = None
    if isinstance(got.get(paths[0]), bytes):
        with fits.open(io.BytesIO(gzip.decompress(got[paths[0]]))) as h:
            msk = np.asarray(h[0].data)
    art: dict[str, list] = {}
    for c, p in zip(WISE_ART, paths[1:]):
        if isinstance(got.get(p), bytes):
            for line in got[p].decode().splitlines():
                parts = line.split()
                if len(parts) >= 2 and not line.lstrip().startswith(("|", "\\")):
                    art.setdefault(WISE_ART[c], []).append((float(parts[0]), float(parts[1])))
    return msk, art


def _wise_quality(frame, fw, sec, x0, y0, target):
    """Mask bad L1b pixels in sec (in place) and name what touches the target: SATURATED + artifact types."""
    msk, art = _wise_extras(frame)
    tc = SkyCoord(*target, unit="deg")
    names = set()
    if msk is not None:
        m = msk[y0:y0 + sec.shape[0], x0:x0 + sec.shape[1]].astype(np.int64)
        sec[(m & WISE_BAD_BITS) != 0] = np.nan
        tx, ty = (float(v) for v in fw.world_to_pixel(tc))
        if (m[_radius(m.shape, tx - x0, ty - y0) <= WISE_R_AP_NATIVE] & WISE_SAT_BITS).any():
            names.add("SATURATED")
    for name, pos in art.items():
        p = np.array(pos)
        if (SkyCoord(p[:, 0], p[:, 1], unit="deg").separation(tc).arcsec <= WISE_ART_R_ARCSEC).any():
            names.add(name)
    return sorted(names)


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
    flag_names = None
    if frame.survey == "wise" and not cutout:  # shortcut: IBE cutouts come without mask/artifact files
        flag_names = _wise_quality(frame, fw, sec, x0, y0, target)
    # the resampled grid image is for display and stacking only; photometry uses native pixels
    img, _ = reproject_interp((sec, wsec), grid_wcs, shape_out=shape, order="bilinear")
    out = {"img": img.astype(np.float32), "wavelength_um": None, "magzp": None, "phot": None,
           "flag_names": flag_names}

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
    {img, wavelength_um, magzp, phot, flag_names}. Raises NoOverlap."""
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
