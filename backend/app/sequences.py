"""Aligned WISE + SPHEREx frame sequences: background job, manifest on disk, PNG frames, photometry."""
import csv
import hashlib
import io
import json
import logging
import math
import multiprocessing
import os
import re
import threading
import time
from collections import Counter, deque
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool

import numpy as np
from astropy.time import Time
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from . import sources
from .config import CACHE_DIR, MAX_RUNNING_SEQUENCES, S3_MAX_CONCURRENCY, WORKER_PROCESSES
from .frames import (PIX_ARCSEC, aperture_flux, clipped_mean, deep_stack, default_fov_deg, grid_wcs_json,
                     group_by_gap, load_grid, make_grid, mjd_to_year, propagate, render_diff_png, render_exposure_png,
                     render_png, render_sigma_png, save_grid)
from .sources import NoOverlap, query_frames, read_section

log = logging.getLogger("ultracool.sequences")
router = APIRouter()

JOB_POOL = ThreadPoolExecutor(max_workers=MAX_RUNNING_SEQUENCES)  # one orchestrator thread per running sequence
# worker tasks one sequence keeps queued at a time: with many sequences running (batch precompute), a newly
# opened one queues behind a bounded number of tasks instead of behind every frame of every other sequence
INFLIGHT_PER_SEQUENCE = 2 * WORKER_PROCESSES
JOBS: dict[str, Future] = {}
JOBS_LOCK = threading.Lock()
STARTED: dict[str, tuple[float, int]] = {}  # running fetch: (start time, units done then), for eta_s
DURATIONS: deque = deque(maxlen=20)  # seconds of recent runs that had frames to fetch, for eta_s
# S3 reads are I/O bound, the rest is GIL-bound: WORKER_PROCESSES processes x READ_THREADS reader threads
READ_THREADS = max(1, math.ceil(S3_MAX_CONCURRENCY / WORKER_PROCESSES))
CHUNK_READS = 2 * READ_THREADS  # frames per worker task: keeps its reader threads busy, progress stays live
_proc_pool: ProcessPoolExecutor | None = None
_proc_lock = threading.Lock()
_read_pool: ThreadPoolExecutor | None = None  # per worker process

WISE_WAVELENGTH = {"W1": 3.4, "W2": 4.6}
WISE_F0_JY = {"W1": 309.540, "W2": 171.787}
# WISE standard aperture: 8.25" radius, sky annulus 50-70" (clear of the PSF wings), in 2.75" pixels
WISE_R_AP, WISE_R_IN, WISE_R_OUT = 3.0, 50 / PIX_ARCSEC, 70 / PIX_ARCSEC
# fraction of CatWISE profile-fit flux inside that aperture: median over 63 (W1) / 66 (W2) static, unsaturated
# stars (10.5-13.5 mag) in NEOWISE visit stacks of 3 fields; star-to-star scatter 3% (W1), 6% (W2)
WISE_APCORR = {"W1": 0.861, "W2": 0.846}
MAX_EXPOSURE_WINDOW_D = 30
# bump when photometry or frame processing changes: part of the sequence id, so old caches are not reused
# (4: SPHEREx crowded-field background, frames.aperture_flux; 5: grids stored quantised, frames.save_grid)
PIPELINE_VERSION = 5
ID_RE = re.compile(r"^[0-9a-f]{16}$")
FRAME_RE = re.compile(r"^[\w.-]+$")


class SeqRequest(BaseModel):
    ra: float
    dec: float
    pmra_masyr: float = 0.0
    pmdec_masyr: float = 0.0
    epoch_yr: float = 2000.0
    fov_deg: float | None = None
    mjd_min: float | None = None
    mjd_max: float | None = None
    wise_exposures: bool = False  # every WISE exposure its own frame (asteroid hunting); needs a <= 30 d window
    # fetched first so the default flipbook (W2 + D6) plays within seconds; not part of the sequence id. A
    # repeat POST for a running job does not re-order its queue.
    priority_bands: list[str] = ["W2", "D6"]


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
    lo, hi = req.mjd_min, req.mjd_max
    if lo is not None and hi is not None and lo > hi:
        raise HTTPException(400, "mjd_min must not exceed mjd_max")
    if req.wise_exposures and (lo is None or hi is None or hi - lo > MAX_EXPOSURE_WINDOW_D):
        raise HTTPException(400, f"wise_exposures needs mjd_min and mjd_max at most {MAX_EXPOSURE_WINDOW_D} days apart")
    pm = math.hypot(req.pmra_masyr, req.pmdec_masyr) / 1000
    fov = req.fov_deg if req.fov_deg is not None else default_fov_deg(pm)
    fov = min(0.25, max(0.02, fov))
    return {"ra": round(req.ra, 5), "dec": round(req.dec, 5), "pmra": round(req.pmra_masyr, 1),
            "pmdec": round(req.pmdec_masyr, 1), "epoch_yr": req.epoch_yr, "fov": round(fov, 3),
            "mjd_min": lo, "mjd_max": hi, "wise_exposures": req.wise_exposures, "pipeline": PIPELINE_VERSION}


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
            for sub in ("npy", "png", "prov"):
                (seq_dir(sid) / sub).mkdir(parents=True, exist_ok=True)
            m = {"id": sid, "status": "querying", "total": 0, "done": 0, "error": None,
                 "grid": {"wcs": grid_wcs_json(wcs, shape), "width": shape[1], "height": shape[0]},
                 "target": {"ra": p["ra"], "dec": p["dec"], "pmra_masyr": p["pmra"], "pmdec_masyr": p["pmdec"],
                            "epoch_yr": p["epoch_yr"]},
                 "window": {"mjd_min": p["mjd_min"], "mjd_max": p["mjd_max"], "wise_exposures": p["wise_exposures"]},
                 "pipeline_version": PIPELINE_VERSION, "frames": []}
        man = Manifest(m)
        man.update(status="querying", error=None)
        JOBS[sid] = JOB_POOL.submit(_run, man, p, wcs, shape, req.priority_bands)
        JOBS[sid].add_done_callback(lambda _f: JOBS.pop(sid, None))
    return sid


def _units(raw, wise_exposures=False):
    """(frame_id, kind, members): one per SPHEREx frame; WISE one per visit x band (all its exposures),
    or one per exposure in wise_exposures mode."""
    units = [("sx-" + f.stem, "single", [f]) for f in raw if f.survey == "spherex"]
    for band in ("W1", "W2"):
        fs = sorted((f for f in raw if f.survey == "wise" and f.band == band), key=lambda f: f.mjd)
        if wise_exposures:
            units += [(f"wise-{band}-{f.stem}", "exposure", [f]) for f in fs]
            continue
        visits: dict[int, list] = {}
        for g, f in zip(group_by_gap([f.mjd for f in fs], 10), fs):
            visits.setdefault(g, []).append(f)
        units += [(f"wise-{band}-v{g:02d}", "visit", members) for g, members in visits.items()]
    return units


def _chunks(units):
    """Pack units into worker tasks of about CHUNK_READS frame reads (a big visit is a task of its own)."""
    out, cur, n = [], [], 0
    for u in units:
        cur.append(u)
        n += len(u[2])
        if n >= CHUNK_READS:
            out.append(cur)
            cur, n = [], 0
    return out + ([cur] if cur else [])


def _init_worker(irsa_sem):
    global _read_pool
    sources.IRSA_SEM = irsa_sem
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    _read_pool = ThreadPoolExecutor(max_workers=READ_THREADS)


def _submit(*args):
    """Submit to the frame worker processes; a pool broken by a dead worker (e.g. OOM) is replaced."""
    global _proc_pool
    with _proc_lock:
        for _ in range(2):
            if _proc_pool is None:
                # spawn: forking would copy s3fs/botocore threads and locks of the API process
                _proc_pool = ProcessPoolExecutor(WORKER_PROCESSES, mp_context=multiprocessing.get_context("spawn"),
                                                 initializer=_init_worker, initargs=(sources.IRSA_SEM,))
            try:
                return _proc_pool.submit(*args)
            except BrokenProcessPool:
                _proc_pool = None
        raise BrokenProcessPool("frame worker pool cannot be restarted")


def _in_window(f, p):
    return (p["mjd_min"] is None or f.mjd >= p["mjd_min"]) and (p["mjd_max"] is None or f.mjd <= p["mjd_max"])


def order_units(units, priority_bands):
    """Fetch order: WISE visits of the priority bands, SPHEREx frames of the priority bands, other WISE, other
    SPHEREx; chronological within each. WISE first because /movers needs only WISE (wise_done)."""
    prio = set(priority_bands)
    return sorted(units, key=lambda u: ((0 if u[2][0].band in prio else 2) + (u[2][0].survey == "spherex"),
                                        min(f.mjd for f in u[2])))


def _run(man: Manifest, p, wcs, shape, priority_bands=()):
    sid = man.data["id"]
    try:
        raw = query_frames(*wcs.wcs.crval)
    except Exception as e:  # noqa: BLE001
        log.exception("SIA query failed for %s", sid)
        man.update(status="error", error=f"IRSA SIA query failed: {e}")
        return
    have = {f["id"] for f in man.data["frames"]}
    units = _units([f for f in raw if _in_window(f, p)], p["wise_exposures"])
    todo = order_units([u for u in units if u[0] not in have], priority_bands)
    wise_left = {u[0] for u in todo if u[2][0].survey == "wise"}
    man.update(status="fetching", total=len(units), done=len(units) - len(todo), wise_done=not wise_left)
    STARTED[sid] = (time.time(), len(units) - len(todo))
    chunks = iter(_chunks(todo))
    futs: dict[Future, list] = {}

    def submit_next():
        chunk = next(chunks, None)
        if chunk is not None:
            futs[_submit(_make_chunk, sid, p, wcs, shape, chunk)] = chunk

    for _ in range(INFLIGHT_PER_SEQUENCE):
        submit_next()
    while futs:
        fut = next(as_completed(futs))
        chunk = futs.pop(fut)
        submit_next()
        try:
            results = fut.result()
        except Exception:  # noqa: BLE001 - e.g. a worker process died; its frames are lost, not the sequence
            log.exception("worker task failed for %s", sid)
            results = [(fid, None) for fid, *_ in chunk]
        for fid, frame in results:
            wise_left.discard(fid)
            man.update(frame=frame, unit_done=True, wise_done=not wise_left)
    man.update(status="done")
    t0, _ = STARTED.pop(sid)
    if todo:
        DURATIONS.append(time.time() - t0)
    log.info("sequence %s done: %d frames", sid, len(man.data["frames"]))


def _target(p, mjd):
    return propagate(p["ra"], p["dec"], p["pmra"], p["pmdec"], p["epoch_yr"], mjd_to_year(mjd))


def _make_chunk(sid, p, wcs, shape, units):
    """Worker-process task: read every member of every unit concurrently, then build the frames.
    -> [(frame_id, frame dict | None)]. A failed read drops that exposure only."""
    global _read_pool
    if _read_pool is None:  # called in-process (tests, debugging)
        _read_pool = ThreadPoolExecutor(max_workers=READ_THREADS)

    def read(f):
        try:
            return read_section(f, wcs, shape, _target(p, f.mjd))
        except NoOverlap:
            return None
        except Exception:  # noqa: BLE001
            log.exception("read failed: %s", f.stem)
            return None

    reads = list(_read_pool.map(read, [f for *_, members in units for f in members]))
    out, i = [], 0
    for fid, kind, members in units:
        rs = reads[i:i + len(members)]
        i += len(members)
        try:
            frame = _make_frame(sid, p, wcs, shape, fid, kind, [(f, r) for f, r in zip(members, rs) if r is not None])
        except Exception:  # noqa: BLE001 - one bad frame must not kill the sequence
            log.exception("frame %s failed", fid)
            frame = None
        out.append((fid, frame))
    return out


def wise_flux_factor(band, magzp):
    """uJy per DN of aperture sum (aperture-corrected); linear, so faint and negative measurements survive."""
    return WISE_F0_JY[band] * 1e6 * 10 ** (-0.4 * magzp) / WISE_APCORR[band]


def _make_frame(sid, p, wcs, shape, fid, kind, ok):
    if not ok:
        return None
    first = ok[0][0]
    mjd = float(np.median([f.mjd for f, _ in ok]))
    x, y = (float(v) for v in wcs.world_to_pixel_values(*_target(p, mjd)))
    flux = flux_err = zp = None
    flagged, flag_names = False, []
    if first.survey == "spherex":
        r = ok[0][1]
        img, wl, phot = r["img"], r["wavelength_um"], r["phot"]
        if phot:  # measured on the native frame pixels with the pipeline variance
            flux, flux_err, flagged, flag_names = phot["flux_ujy"], phot["err_ujy"], phot["flagged"], phot["flag_names"]
    else:
        img = clipped_mean([r["img"] for _, r in ok])
        wl = WISE_WAVELENGTH[first.band]
        zp = float(np.median([r["magzp"] for _, r in ok]))
        net, err = aperture_flux(img, x, y, WISE_R_AP, WISE_R_IN, WISE_R_OUT)
        if math.isfinite(net):
            k = wise_flux_factor(first.band, zp)
            flux, flux_err = net * k, err * k
        hits = Counter(n for _, r in ok for n in (r["flag_names"] or []))
        flag_names = sorted(hits)
        # spikes/halos of a neighbour sit on the same sky spot in every exposure and survive the clipped mean;
        # ghosts and latents move between exposures and are clipped. Saturation is a note, not a reason to hide.
        flagged = any(c >= len(ok) / 2 for n, c in hits.items() if n != "SATURATED")
    d = seq_dir(sid)
    save_grid(d / "npy" / fid, img)
    (render_exposure_png if kind == "exposure" else render_png)(img, d / "png" / f"{fid}.png")
    (d / "prov" / f"{fid}.json").write_text(json.dumps([f.key or f.access_url for f, _ in ok]))
    ny = shape[0]
    return {"id": fid, "survey": first.survey, "band": first.band, "kind": kind, "mjd": mjd,
            "date": Time(mjd, format="mjd").isot, "wavelength_um": wl, "epoch_index": 0,
            "flux_ujy": flux, "flux_err_ujy": flux_err, "flagged": bool(flagged), "flag_names": flag_names,
            "n_exposures": len(ok), "magzp": zp,
            "target_px": [x, ny - 1 - y], "png": f"/api/sequences/{sid}/frames/{fid}.png"}


@router.post("/api/sequences")
def create_sequence(req: SeqRequest):
    return {"id": start(req)}


def get_manifest(sid):
    m = load_manifest(sid) if ID_RE.match(sid) else None
    if m is None:
        raise HTTPException(404, f"Unknown sequence: {sid}")
    m["frames"].sort(key=lambda f: f["mjd"])
    for f in m["frames"]:  # manifests written before these fields existed
        f.setdefault("kind", "single" if f["survey"] == "spherex" else "visit")
        f.setdefault("flag_names", [])
    m.setdefault("wise_done", m["status"] == "done")  # manifests written before the field existed
    for survey in ("spherex", "wise"):
        fs = [f for f in m["frames"] if f["survey"] == survey]
        for f, g in zip(fs, group_by_gap([f["mjd"] for f in fs], 30)):
            f["epoch_index"] = g
    return m


def queue_status(sid, m):
    """-> (queue_position, eta_s). queue_position: 1-based place among sequences waiting for one of the
    MAX_RUNNING_SEQUENCES slots, None when running, finished or not started here. eta_s (rough): running ->
    remaining units at this run's own rate so far; queued -> (slot waves ahead + its own run) x the median
    duration of recent runs; None without a basis."""
    with JOBS_LOCK:
        waiting = [s for s, f in JOBS.items() if not f.running() and not f.done()]
    typical = float(np.median(DURATIONS)) if DURATIONS else None
    if sid in waiting:
        pos = waiting.index(sid) + 1
        return pos, (math.ceil(pos / MAX_RUNNING_SEQUENCES) + 1) * typical if typical else None
    st = STARTED.get(sid)
    if st and m["status"] == "fetching" and m["done"] > st[1]:
        return None, (m["total"] - m["done"]) * (time.time() - st[0]) / (m["done"] - st[1])
    return None, None


@router.get("/api/sequences/{sid}")
def get_sequence(sid: str):
    m = get_manifest(sid)
    pos, eta = queue_status(sid, m)
    return {**m, "queue_position": pos, "eta_s": eta}


@router.get("/api/sequences/{sid}/frames/{frame_id}.png")
def get_frame_png(sid: str, frame_id: str):
    path = seq_dir(sid) / "png" / f"{frame_id}.png"
    if not (ID_RE.match(sid) and FRAME_RE.match(frame_id) and path.exists()):
        raise HTTPException(404, "Frame not found")
    return FileResponse(path, media_type="image/png",
                        headers={"Cache-Control": "public, max-age=31536000, immutable"})


def load_npy(sid, frame_id):
    """Grid image of a frame: quantised .npz (current) or float .npy (caches written before it)."""
    base = seq_dir(sid) / "npy" / frame_id
    if not (ID_RE.match(sid) and FRAME_RE.match(frame_id)):
        raise HTTPException(404, f"Frame not found: {frame_id}")
    img = load_grid(base)
    if img is None:
        raise HTTPException(404, f"Frame not found: {frame_id}")
    return img


def _png(render, *args):
    buf = io.BytesIO()
    render(*args, buf)
    return Response(buf.getvalue(), media_type="image/png")


@router.get("/api/sequences/{sid}/diff.png")
def get_diff_png(sid: str, a: str, b: str):
    return _png(render_diff_png, load_npy(sid, a), load_npy(sid, b))


@router.get("/api/sequences/{sid}/stack.png")
def get_stack_png(sid: str, band: str, mjd_min: float = -math.inf, mjd_max: float = math.inf):
    """Deep stack of the unflagged frames of one band, optionally limited to an MJD window (deep epochs)."""
    ids = [f["id"] for f in get_manifest(sid)["frames"]
           if f["band"] == band and not f["flagged"] and mjd_min <= f["mjd"] <= mjd_max]
    if not ids:
        raise HTTPException(404, f"No unflagged {band} frames in that window")
    return _png(render_sigma_png, deep_stack([load_npy(sid, i) for i in ids]))


EXPORT_COLUMNS = ["frame_id", "survey", "band", "kind", "mjd", "date", "wavelength_um", "flux_ujy", "flux_err_ujy",
                  "flagged", "flag_names", "n_exposures", "pipeline_version", "source_files"]
CITATIONS = [
    "WISE: Wright et al. 2010, AJ 140, 1868. NEOWISE: Mainzer et al. 2011, ApJ 731, 53; Mainzer et al. 2014, ApJ 792, 30.",
    "WISE/NEOWISE Level-1b single-exposure images: NASA/IPAC Infrared Science Archive (IRSA), doi:10.26131/IRSA139, doi:10.26131/IRSA144.",
    "SPHEREx: Dore et al. 2014, arXiv:1412.4872; SPHEREx Level-2 spectral images from IRSA (spherex_dr1 / spherex_qr3).",
    "Spectral templates: SPIFF, Gagne et al. 2026, arXiv:2604.22012, doi:10.5281/zenodo.19051216 (CC-BY 4.0).",
    "Software: Astropy (Astropy Collaboration 2013, 2018, 2022), photutils (doi:10.5281/zenodo.596036), reproject.",
]


@router.get("/api/sequences/{sid}/export.csv")
def export_csv(sid: str):
    """Per-frame photometry of the target with provenance; WISE fluxes are aperture photometry on visit
    co-adds (8.25" aperture, aperture-corrected), SPHEREx forced aperture photometry on native pixels."""
    m = get_manifest(sid)
    t = m["target"]
    buf = io.StringIO()
    buf.write(f"# Ultracool Browser photometry export, sequence {sid}, pipeline version {m.get('pipeline_version')}\n"
              f"# target ra={t['ra']} dec={t['dec']} (deg, ICRS) pmra={t['pmra_masyr']} pmdec={t['pmdec_masyr']} "
              f"mas/yr at epoch {t['epoch_yr']}; photometry at the proper-motion-propagated position per frame\n"
              "# flux in microjansky (uJy); mjd = median exposure time of the frame; status=" + m["status"] + "\n")
    buf.writelines(f"# cite: {c}\n" for c in CITATIONS)
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(EXPORT_COLUMNS)
    for f in m["frames"]:
        prov = seq_dir(sid) / "prov" / f"{f['id']}.json"
        files = json.loads(prov.read_text()) if prov.exists() else []
        w.writerow([f["id"], f["survey"], f["band"], f["kind"], f"{f['mjd']:.6f}", f["date"], f["wavelength_um"],
                    "" if f["flux_ujy"] is None else f"{f['flux_ujy']:.6g}",
                    "" if f["flux_err_ujy"] is None else f"{f['flux_err_ujy']:.6g}",
                    int(f["flagged"]), ";".join(f["flag_names"]), f.get("n_exposures", ""),
                    m.get("pipeline_version", ""), ";".join(files)])
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="ultracool-{sid}.csv"'})
