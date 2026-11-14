"""Aligned WISE + SPHEREx frame sequences: background job, manifest on disk, PNG frames, photometry."""
import hashlib
import io
import json
import logging
import math
import os
import re
import threading
import warnings
from concurrent.futures import Future, ThreadPoolExecutor

import numpy as np
from astropy.time import Time
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from .config import CACHE_DIR, S3_MAX_CONCURRENCY
from .frames import (PIX_ARCSEC, aperture_flux, deep_stack, default_fov_deg, grid_wcs_json, group_by_gap,
                     make_grid, mjd_to_year, propagate, render_diff_png, render_png, render_sigma_png)
from .sources import NoOverlap, query_frames, read_section

log = logging.getLogger("ultracool.sequences")
router = APIRouter()

UNIT_POOL = ThreadPoolExecutor(max_workers=S3_MAX_CONCURRENCY)
JOB_POOL = ThreadPoolExecutor(max_workers=4)  # orchestrators wait on UNIT_POOL, so they need their own pool
JOBS: dict[str, Future] = {}
JOBS_LOCK = threading.Lock()
WISE_PER_VISIT = 8
WISE_WAVELENGTH = {"W1": 3.4, "W2": 4.6}
WISE_F0_JY = {"W1": 309.540, "W2": 171.787}
# WISE standard aperture: 8.25" radius, sky annulus 50-70" (clear of the PSF wings), in 2.75" pixels
WISE_R_AP, WISE_R_IN, WISE_R_OUT = 3.0, 50 / PIX_ARCSEC, 70 / PIX_ARCSEC
# fraction of CatWISE profile-fit flux inside that aperture: median over 63 (W1) / 66 (W2) static, unsaturated
# stars (10.5-13.5 mag) in NEOWISE visit stacks of 3 fields; star-to-star scatter 3% (W1), 6% (W2)
WISE_APCORR = {"W1": 0.861, "W2": 0.846}
# bump when photometry or frame processing changes: part of the sequence id, so old caches are not reused
PIPELINE_VERSION = 2
ID_RE = re.compile(r"^[0-9a-f]{16}$")
FRAME_RE = re.compile(r"^[\w.-]+$")


class SeqRequest(BaseModel):
    ra: float
    dec: float
    pmra_masyr: float = 0.0
    pmdec_masyr: float = 0.0
    epoch_yr: float = 2000.0
    fov_deg: float | None = None


def seq_dir(sid):
    return CACHE_DIR / "seq" / sid


def load_manifest(sid):
    p = seq_dir(sid) / "manifest.json"
    return json.loads(p.read_text()) if p.exists() else None


class Manifest:
    """In-memory manifest of one running job; every change is written atomically."""

    def __init__(self, data):
        self.data = data
        self.lock = threading.Lock()
        self.path = seq_dir(data["id"]) / "manifest.json"

    def update(self, frame=None, unit_done=False, **fields):
        with self.lock:
            self.data.update(fields)
            if frame is not None:
                self.data["frames"].append(frame)
            if unit_done:
                self.data["done"] += 1
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data))
            os.replace(tmp, self.path)


def _params(req: SeqRequest):
    pm = math.hypot(req.pmra_masyr, req.pmdec_masyr) / 1000
    fov = req.fov_deg if req.fov_deg is not None else default_fov_deg(pm)
    fov = min(0.25, max(0.02, fov))
    return {"ra": round(req.ra, 5), "dec": round(req.dec, 5), "pmra": round(req.pmra_masyr, 1),
            "pmdec": round(req.pmdec_masyr, 1), "epoch_yr": req.epoch_yr, "fov": round(fov, 3),
            "pipeline": PIPELINE_VERSION}


def start(req: SeqRequest) -> str:
    p = _params(req)
    sid = hashlib.sha1(json.dumps(p, sort_keys=True).encode()).hexdigest()[:16]
    with JOBS_LOCK:
        m = load_manifest(sid)
        if (m and m["status"] == "done") or sid in JOBS:
            return sid
        ra_c, dec_c = propagate(p["ra"], p["dec"], p["pmra"], p["pmdec"], p["epoch_yr"], 2018.0)
        wcs, shape = make_grid(ra_c, dec_c, p["fov"])
        if m is None:
            (seq_dir(sid) / "npy").mkdir(parents=True, exist_ok=True)
            (seq_dir(sid) / "png").mkdir(exist_ok=True)
            m = {"id": sid, "status": "querying", "total": 0, "done": 0, "error": None,
                 "grid": {"wcs": grid_wcs_json(wcs, shape), "width": shape[1], "height": shape[0]},
                 "target": {"ra": p["ra"], "dec": p["dec"], "pmra_masyr": p["pmra"], "pmdec_masyr": p["pmdec"],
                            "epoch_yr": p["epoch_yr"]},
                 "pipeline_version": PIPELINE_VERSION, "frames": []}
        man = Manifest(m)
        man.update(status="querying", error=None)
        JOBS[sid] = JOB_POOL.submit(_run, man, p, wcs, shape)
        JOBS[sid].add_done_callback(lambda _f: JOBS.pop(sid, None))
    return sid


def _units(raw):
    units = [("sx-" + f.stem, [f]) for f in raw if f.survey == "spherex"]
    for band in ("W1", "W2"):
        fs = sorted((f for f in raw if f.survey == "wise" and f.band == band), key=lambda f: f.mjd)
        visits: dict[int, list] = {}
        for g, f in zip(group_by_gap([f.mjd for f in fs], 10), fs):
            visits.setdefault(g, []).append(f)
        for g, members in visits.items():
            n = len(members)
            idx = np.linspace(0, n - 1, min(n, WISE_PER_VISIT)).round().astype(int)
            units.append((f"wise-{band}-v{g:02d}", [members[i] for i in sorted(set(idx))]))
    return units


def _run(man: Manifest, p, wcs, shape):
    sid = man.data["id"]
    try:
        raw = query_frames(*wcs.wcs.crval)
    except Exception as e:  # noqa: BLE001
        log.exception("SIA query failed for %s", sid)
        man.update(status="error", error=f"IRSA SIA query failed: {e}")
        return
    have = {f["id"] for f in man.data["frames"]}
    units = _units(raw)
    man.update(status="fetching", total=len(units), done=len(have))
    futs = [UNIT_POOL.submit(_unit, man, p, wcs, shape, fid, members)
            for fid, members in units if fid not in have]
    for f in futs:
        f.result()
    man.update(status="done")
    log.info("sequence %s done: %d frames", sid, len(man.data["frames"]))


def _unit(man: Manifest, p, wcs, shape, fid, members):
    try:
        frame = _make_frame(man.data["id"], p, wcs, shape, fid, members)
    except Exception:  # noqa: BLE001 - one bad frame must not kill the sequence
        log.exception("frame %s failed", fid)
        frame = None
    man.update(frame=frame, unit_done=True)


def _make_frame(sid, p, wcs, shape, fid, members):
    target = lambda mjd: propagate(p["ra"], p["dec"], p["pmra"], p["pmdec"], p["epoch_yr"], mjd_to_year(mjd))
    reads, mjds = [], []
    for f in members:
        try:
            reads.append(read_section(f, wcs, shape, target(f.mjd)))
            mjds.append(f.mjd)
        except NoOverlap:
            continue
    if not reads:
        return None
    first = members[0]
    mjd = float(np.median(mjds))
    x, y = (float(v) for v in wcs.world_to_pixel_values(*target(mjd)))
    flux = flux_err = None
    flagged = False
    if first.survey == "spherex":
        img, wl, phot = reads[0]["img"], reads[0]["wavelength_um"], reads[0]["phot"]
        if phot:  # measured on the native frame pixels with the pipeline variance
            flux, flux_err, flagged = phot["flux_ujy"], phot["err_ujy"], phot["flagged"]
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN columns at frame edges
            img = np.nanmedian(np.stack([r["img"] for r in reads]), axis=0).astype(np.float32)
        wl = WISE_WAVELENGTH[first.band]
        net, err = aperture_flux(img, x, y, WISE_R_AP, WISE_R_IN, WISE_R_OUT)
        if math.isfinite(net):
            # linear in DN, so faint and negative measurements are kept instead of lost in a log
            zp = float(np.median([r["magzp"] for r in reads]))
            k = WISE_F0_JY[first.band] * 1e6 * 10 ** (-0.4 * zp) / WISE_APCORR[first.band]
            flux, flux_err = net * k, err * k
    d = seq_dir(sid)
    np.save(d / "npy" / f"{fid}.npy", img)
    render_png(img, d / "png" / f"{fid}.png")
    ny = shape[0]
    return {"id": fid, "survey": first.survey, "band": first.band, "mjd": mjd,
            "date": Time(mjd, format="mjd").isot, "wavelength_um": wl, "epoch_index": 0,
            "flux_ujy": flux, "flux_err_ujy": flux_err, "flagged": bool(flagged),
            "target_px": [x, ny - 1 - y], "png": f"/api/sequences/{sid}/frames/{fid}.png"}


@router.post("/api/sequences")
def create_sequence(req: SeqRequest):
    return {"id": start(req)}


def get_manifest(sid):
    m = load_manifest(sid) if ID_RE.match(sid) else None
    if m is None:
        raise HTTPException(404, f"Unknown sequence: {sid}")
    m["frames"].sort(key=lambda f: f["mjd"])
    for survey in ("spherex", "wise"):
        fs = [f for f in m["frames"] if f["survey"] == survey]
        for f, g in zip(fs, group_by_gap([f["mjd"] for f in fs], 30)):
            f["epoch_index"] = g
    return m


@router.get("/api/sequences/{sid}")
def get_sequence(sid: str):
    return get_manifest(sid)


@router.get("/api/sequences/{sid}/frames/{frame_id}.png")
def get_frame_png(sid: str, frame_id: str):
    path = seq_dir(sid) / "png" / f"{frame_id}.png"
    if not (ID_RE.match(sid) and FRAME_RE.match(frame_id) and path.exists()):
        raise HTTPException(404, "Frame not found")
    return FileResponse(path, media_type="image/png",
                        headers={"Cache-Control": "public, max-age=31536000, immutable"})


def _load_npy(sid, frame_id):
    path = seq_dir(sid) / "npy" / f"{frame_id}.npy"
    if not (ID_RE.match(sid) and FRAME_RE.match(frame_id) and path.exists()):
        raise HTTPException(404, f"Frame not found: {frame_id}")
    return np.load(path)


def _png(render, *args):
    buf = io.BytesIO()
    render(*args, buf)
    return Response(buf.getvalue(), media_type="image/png")


@router.get("/api/sequences/{sid}/diff.png")
def get_diff_png(sid: str, a: str, b: str):
    return _png(render_diff_png, _load_npy(sid, a), _load_npy(sid, b))


@router.get("/api/sequences/{sid}/stack.png")
def get_stack_png(sid: str, band: str, mjd_min: float = -math.inf, mjd_max: float = math.inf):
    """Deep stack of the unflagged frames of one band, optionally limited to an MJD window (deep epochs)."""
    ids = [f["id"] for f in get_manifest(sid)["frames"]
           if f["band"] == band and not f["flagged"] and mjd_min <= f["mjd"] <= mjd_max]
    if not ids:
        raise HTTPException(404, f"No unflagged {band} frames in that window")
    return _png(render_sigma_png, deep_stack([_load_npy(sid, i) for i in ids]))
