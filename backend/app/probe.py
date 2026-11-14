"""Probe: photometry, W1-W2 colour, variability and SPHEREx spectrum of any point in a sequence's field.
preview: forced apertures on the cached grid images, synchronous (seconds). full: background job measuring the
native SPHEREx pixels exactly like the target (sources.read_section -> _spherex_phot on a small grid around the
point); WISE is measured on the cached visit co-adds in both modes (quantised to ~0.02 sigma, frames.save_grid).
Moving the point computes nothing: the frontend only calls this on an explicit action."""
import hashlib
import json
import logging
import math
import threading
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Literal

import numpy as np
from fastapi import APIRouter, HTTPException, Query

from . import sequences
from .analysis import (FWHM_PX, PHOT_FLOOR, REF_YR, _clean, _grid_wcs, _offsets_arcsec, _plain_props, _shifted_stack,
                       centroid, classify_variability, measure_color, photometry_lc, static_sky_flux, typed_spectrum,
                       wise_lightcurve)
from .frames import PIX_ARCSEC, aperture_flux, make_grid, mjd_to_year, propagate
from .sequences import (CHUNK_READS, WISE_R_AP, WISE_R_IN, WISE_R_OUT, WORKER_PROCESSES, get_manifest, load_npy,
                        seq_dir, wise_flux_factor)
from .sources import SX_R_AP, SX_R_IN, SX_R_OUT, NoOverlap, query_frames, read_section
from .spectral import BIN_CENTRE

log = logging.getLogger("ultracool.probe")
router = APIRouter()

SNAP_ARCSEC, SNAP_MIN_SNR = 4.0, 3.0
SX_NATIVE_ARCSEC = 6.15
SX_GRID_R = tuple(r * SX_NATIVE_ARCSEC / PIX_ARCSEC for r in (SX_R_AP, SX_R_IN, SX_R_OUT))  # target radii, grid px
EDGE_PX = SX_GRID_R[1]  # the aperture and at least half of each sky annulus stay on the grid
GRID_SR = (PIX_ARCSEC / 206264.806) ** 2
# preview SPHEREx aperture correction: fraction of a star's total flux inside 12.3" on the bilinearly resampled
# grid = median ratio of grid aperture flux to the native (EPSF-corrected) target flux, per band, over frames at
# S/N > 20 of AL Boo and eps Ind B (3 sequences, agreeing to <= 0.01; 16-84% spread <= 0.01 per band)
PREVIEW_APCORR = {"D1": 0.964, "D2": 0.962, "D3": 0.954, "D4": 0.946, "D5": 0.946, "D6": 0.942}
# annulus scatter of resampled (correlated) grid pixels: 0.29-0.43x the native pipeline-variance error (median
# per band, 4 fields), so preview SPHEREx errors are scaled up to stay comparable; still approximate
PREVIEW_ERR_SCALE = 3.0
PREVIEW_CLIP_SIGMA = 5.0
TRACK_YRS = np.linspace(2010.0, 2026.5, 34)  # where a mover may have been clicked: any frame epoch
# full jobs: one orchestrator, <= MAX_FULL_JOBS waiting; each keeps PROBE_INFLIGHT worker tasks queued (a
# sequence keeps 2x WORKER_PROCESSES), so user sequences are never stuck behind a probe
FULL_POOL = ThreadPoolExecutor(max_workers=1)
MAX_FULL_JOBS = 4
PROBE_INFLIGHT = WORKER_PROCESSES
FULL_JOBS: dict[str, dict] = {}
FULL_LOCK = threading.Lock()


def snap(z, x, y, fwhm_px):
    """Brightest real peak (local maximum of the matched-filter S/N >= SNAP_MIN_SNR) within SNAP_ARCSEC of (x, y)
    in a sigma-unit stack -> (x, y, snr), or None."""
    r = SNAP_ARCSEC / PIX_ARCSEC
    c = centroid(z, x, y, r, fwhm_px, SNAP_MIN_SNR)
    if c is None or math.hypot(c[0] - x, c[1] - y) > r:
        return None
    return c[0], c[1], c[3]


def _snap_stack(m, pm_px_yr):
    """Deep stack at REF_YR, shifted along the given motion: W2 visits, else W1, else every SPHEREx frame."""
    for pick, fwhm in ((lambda f: f["kind"] == "visit" and f["band"] == "W2", FWHM_PX["W2"]),
                       (lambda f: f["kind"] == "visit" and f["band"] == "W1", FWHM_PX["W1"]),
                       (lambda f: f["survey"] == "spherex", FWHM_PX["SPHEREx"])):
        fs = [f for f in m["frames"] if pick(f) and not f["flagged"]]
        if fs:
            return _shifted_stack(m["id"], fs, pm_px_yr, REF_YR), fwhm
    return None, None


def _cached_movers(m):
    """Vetted movers if /movers has computed them for the current WISE frame set; never computed here
    (shortcut: a probe before /movers ran adopts no PM; upgrade = run find_movers in the full job)."""
    p = seq_dir(m["id"]) / "movers.json"
    if not p.exists():
        return []
    c = json.loads(p.read_text())
    return c.get("movers", []) if c.get("_key") == ["wise", sum(f["survey"] == "wise" for f in m["frames"])] else []


def resolve(m, ra, dec, pmra, pmdec, epoch_yr):
    """Requested point -> (position dict, pm dict): snapped to a peak and/or onto a vetted mover's track.
    The position is given at epoch_yr (the caller's). 400 if off the grid."""
    wcs = _grid_wcs(m)
    nx, ny = m["grid"]["width"], m["grid"]["height"]
    x, y = (float(v) for v in wcs.world_to_pixel_values(ra, dec))
    if not (EDGE_PX <= x <= nx - 1 - EDGE_PX and EDGE_PX <= y <= ny - 1 - EDGE_PX):
        raise HTTPException(400, f"Position outside the sequence field (keep {EDGE_PX * PIX_ARCSEC:.0f}\" from the edge)")
    given = bool(pmra or pmdec)
    pm = {"pmra_masyr": pmra, "pmdec_masyr": pmdec, "epoch_yr": epoch_yr, "source": "given" if given else "none"}
    ra_r, dec_r = propagate(ra, dec, pmra, pmdec, epoch_yr, REF_YR)
    z, fwhm = _snap_stack(m, (-pmra / 1000 / PIX_ARCSEC, pmdec / 1000 / PIX_ARCSEC))
    snapped, offset = False, 0.0
    if z is not None:
        xr, yr = (float(v) for v in wcs.world_to_pixel_values(ra_r, dec_r))
        s = snap(z, xr, yr, fwhm)
        if s:
            ra_s, dec_s = (float(v) for v in wcs.pixel_to_world_values(s[0], s[1]))
            offset = math.hypot(*_offsets_arcsec(ra_s, dec_s, ra_r, dec_r))
            ra_r, dec_r, snapped = ra_s, dec_s, True
    if not given:
        best = None
        for mv in _cached_movers(m):
            tr = [propagate(mv["ra"], mv["dec"], mv["pmra_masyr"], mv["pmdec_masyr"], mv["epoch_yr"], t) for t in TRACK_YRS]
            d = float(np.min(np.hypot(*_offsets_arcsec([p[0] for p in tr], [p[1] for p in tr], ra_r, dec_r))))
            if d <= SNAP_ARCSEC and (best is None or d < best[0]):
                best = (d, mv)
        if best:
            d, mv = best
            ra_r, dec_r = propagate(mv["ra"], mv["dec"], mv["pmra_masyr"], mv["pmdec_masyr"], mv["epoch_yr"], REF_YR)
            pm = {"pmra_masyr": mv["pmra_masyr"], "pmdec_masyr": mv["pmdec_masyr"], "epoch_yr": epoch_yr, "source": "mover"}
            snapped, offset = True, d
    ra_p, dec_p = propagate(ra_r, dec_r, pm["pmra_masyr"], pm["pmdec_masyr"], REF_YR, epoch_yr)
    xp, yp = (float(v) for v in wcs.world_to_pixel_values(ra_p, dec_p))
    pos = {"ra": ra_p % 360, "dec": dec_p, "x_px": xp, "y_px": ny - 1 - yp, "snapped": snapped,
           "snap_offset_arcsec": offset}
    return pos, pm


def _at(pos, pm, mjd):
    return propagate(pos["ra"], pos["dec"], pm["pmra_masyr"], pm["pmdec_masyr"], pm["epoch_yr"], mjd_to_year(mjd))


def _frame(f, px, flux, err, flagged=False, flag_names=(), wavelength_um=None):
    """A manifest-shaped frame for the probe position, so the target's analysis functions apply unchanged."""
    return {"id": f["id"], "survey": f["survey"], "band": f["band"], "kind": f["kind"], "mjd": f["mjd"],
            "wavelength_um": wavelength_um or f["wavelength_um"], "flux_ujy": flux, "flux_err_ujy": err,
            "flagged": bool(flagged), "flag_names": list(flag_names), "magzp": f.get("magzp"),
            "target_px": px}


def grid_frames(m, pos, pm, surveys=("wise", "spherex")):
    """Forced aperture photometry on the cached grid images. WISE exactly as for the target (8.25" aperture,
    50-70" annulus, aperture correction). SPHEREx: the target's 12.3" aperture on the resampled grid in MJy/sr,
    grid pixel solid angle, PREVIEW_APCORR; errors from the annulus scatter of resampled (correlated) pixels,
    times PREVIEW_ERR_SCALE. shortcut: no quality flags at the probe (WISE artifacts are only matched at the
    target; SPHEREx flag bits are not on the grid) and SPHEREx wavelengths are those at the target's detector
    pixel; upgrade = full mode for SPHEREx."""
    wcs = _grid_wcs(m)
    ny = m["grid"]["height"]
    out = []
    for f in m["frames"]:
        if f["survey"] not in surveys or f["kind"] == "exposure" or (f["survey"] == "wise" and f.get("magzp") is None):
            continue
        x, y = (float(v) for v in wcs.world_to_pixel_values(*_at(pos, pm, f["mjd"])))
        img = load_npy(m["id"], f["id"])
        if f["survey"] == "wise":
            net, err = aperture_flux(img, x, y, WISE_R_AP, WISE_R_IN, WISE_R_OUT)
            k = wise_flux_factor(f["band"], f["magzp"])
        else:
            net, err = aperture_flux(img, x, y, *SX_GRID_R)
            k = GRID_SR * 1e12 / PREVIEW_APCORR[f["band"]]
            err *= PREVIEW_ERR_SCALE
        ok = math.isfinite(net)
        out.append(_frame(f, [x, ny - 1 - y], net * k if ok else None, err * k if ok else None))
    flag_outliers([f for f in out if f["survey"] == "spherex" and f["flux_ujy"] is not None])
    return out


def flag_outliers(sx):
    """The grid keeps no SPHEREx flag bits, so cosmic rays and bad pixels (up to 1000x the source) are caught
    as frames > PREVIEW_CLIP_SIGMA off the median of the frames in their own and the two neighbouring spectral
    channels (robust spread, which includes the source's own change over ~7% in wavelength)."""
    if not sx:
        return
    ch = np.array([int(np.argmin(np.abs(BIN_CENTRE - f["wavelength_um"]))) for f in sx])
    fl = np.array([f["flux_ujy"] for f in sx])
    for i, f in enumerate(sx):
        near = fl[np.abs(ch - ch[i]) <= 1]
        if len(near) < 4:
            continue
        med = np.median(near)
        if abs(fl[i] - med) > PREVIEW_CLIP_SIGMA * math.hypot(f["flux_err_ujy"], 1.4826 * np.median(np.abs(near - med))):
            f.update(flagged=True, flag_names=["OUTLIER"])


def _native_chunk(items):
    """Worker-process task: native-pixel SPHEREx photometry at [(frame_id, RawFrame, ra, dec)] ->
    [(frame_id, phot | None, wavelength_um | None)]. A grid covering the sky annulus keeps the IBE fallback valid."""
    pool = sequences._read_pool or ThreadPoolExecutor(sequences.READ_THREADS)
    fov = 2 * SX_R_OUT * SX_NATIVE_ARCSEC / 3600

    def one(item):
        fid, raw, ra, dec = item
        try:
            r = read_section(raw, *make_grid(ra, dec, fov), (ra, dec))
            return fid, r["phot"], r["wavelength_um"]
        except NoOverlap:
            return fid, None, None
        except Exception:  # noqa: BLE001 - one unreadable frame drops that frame only
            log.exception("probe read failed: %s", raw.stem)
            return fid, None, None

    return list(pool.map(one, items))


def native_frames(m, pos, pm, state):
    """SPHEREx frames measured on native pixels, the target method; progress in state (done/total)."""
    wcs = _grid_wcs(m)
    ny = m["grid"]["height"]
    raw = {"sx-" + r.stem: r for r in query_frames(*wcs.wcs.crval) if r.survey == "spherex"}
    sx = [f for f in m["frames"] if f["survey"] == "spherex" and f["id"] in raw]
    items = [(f["id"], raw[f["id"]], *_at(pos, pm, f["mjd"])) for f in sx]
    state["total"] = len(items)
    chunks = iter([items[i:i + CHUNK_READS] for i in range(0, len(items), CHUNK_READS)])
    futs: dict[Future, list] = {}
    got = {}

    def submit_next():
        c = next(chunks, None)
        if c is not None:
            futs[sequences._submit(_native_chunk, c)] = c

    for _ in range(PROBE_INFLIGHT):
        submit_next()
    while futs:
        fut = next(as_completed(futs))
        futs.pop(fut)
        submit_next()
        for fid, phot, wl in fut.result():
            got[fid] = (phot, wl)
            state["done"] += 1
    out = []
    for f in sx:
        phot, wl = got.get(f["id"], (None, None))
        x, y = (float(v) for v in wcs.world_to_pixel_values(*_at(pos, pm, f["mjd"])))
        if phot is None:
            out.append(_frame(f, [x, ny - 1 - y], None, None, wavelength_um=wl))
        else:
            out.append(_frame(f, [x, ny - 1 - y], phot["flux_ujy"], phot["err_ujy"], phot["flagged"],
                              phot["flag_names"], wl))
    return out


def analyse(m, pos, pm, frames, mode):
    """Colour, variability and spectrum of the probe frames with the target's functions (neighbour light
    subtraction for movers, spectrum contamination checks); full mode may fall back to catalog photometry."""
    seq = {**m, "target": {"ra": pos["ra"], "dec": pos["dec"], "pmra_masyr": pm["pmra_masyr"],
                           "pmdec_masyr": pm["pmdec_masyr"], "epoch_yr": pm["epoch_yr"]}, "frames": frames}
    sky = static_sky_flux(seq)
    if mode == "full":
        lc, source, note = photometry_lc(seq, sky)
    else:
        lc, source, note = wise_lightcurve(frames, sky), "pipeline", "WISE visit co-adds, 8.25\" aperture photometry"
    # shortcut: no saturation flags at the probe, so the catalog fallback keeps the 5% floor, not the 15% one
    color = {**measure_color(lc), "source": source, "source_note": note}
    var = {**classify_variability(lc, PHOT_FLOOR), "source": source, "source_note": note}
    spec = typed_spectrum(seq, sky, color)
    first = ("Quick preview from resampled images; errors are approximate." if mode == "preview" else
             "Full measurement on the original SPHEREx pixels, the same method as for the target.")
    s = [first]
    if pm["source"] == "mover":
        s.append(f"The point follows the moving source found here ({math.hypot(pm['pmra_masyr'], pm['pmdec_masyr']) / 1000:.2f}"
                 " arcseconds per year), so it is measured where that source is in every image.")
    elif pos["snapped"]:
        s.append(f"The point was moved {pos['snap_offset_arcsec']:.1f} arcseconds onto the nearest source.")
    else:
        s.append("No clear source at this point: the numbers describe whatever faint light is there.")
    frames_out = [{"frame_id": f["id"], **{k: f[k] for k in ("survey", "band", "mjd", "wavelength_um")},
                   "flux_ujy": f["flux_ujy"], "flux_err_ujy": f["flux_err_ujy"], "flagged": f["flagged"]} for f in frames]
    return {"frames": frames_out, "color": color, "variability": var, "spectrum": spec,
            "plain": s + _plain_props(color, var, spec)}


def _response(mode, ra, dec, pos, pm, status="ok", res=None, progress=None, error=None, queue_position=None):
    res = res or {"frames": [], "color": None, "variability": None, "spectrum": None,
                  "plain": ["Full measurement on the original SPHEREx pixels is running."] if status == "running" else []}
    return _clean({"status": status, "mode": mode, "requested": {"ra": ra, "dec": dec}, "position": pos, "pm": pm,
                   **res, "progress": progress, "error": error, "queue_position": queue_position})


def _cache_key(sid, pos, pm):
    k = [sid, round(pos["ra"] * 7200), round(pos["dec"] * 7200), round(pm["pmra_masyr"]), round(pm["pmdec_masyr"]),
         round(pm["epoch_yr"], 1)]  # 0.5" cells, 1 mas/yr
    return hashlib.sha1(json.dumps(k).encode()).hexdigest()[:16]


def _run_full(key, m, pos, pm, state, path):
    try:
        frames = grid_frames(m, pos, pm, ("wise",)) + native_frames(m, pos, pm, state)
        res = analyse(m, pos, pm, frames, "full")
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(_clean({**res, "_key": [m["status"], len(m["frames"])]})))
        tmp.replace(path)
        with FULL_LOCK:
            FULL_JOBS.pop(key, None)
    except Exception as e:  # noqa: BLE001 - reported to the caller, who may retry
        log.exception("probe %s failed", key)
        state["error"] = f"{type(e).__name__}: {e}"


@router.get("/api/sequences/{sid}/probe")
def probe(sid: str, ra: float = Query(ge=0, lt=360), dec: float = Query(ge=-90, le=90),
          pmra_masyr: float = Query(0.0, ge=-20000, le=20000), pmdec_masyr: float = Query(0.0, ge=-20000, le=20000),
          epoch_yr: float = Query(2000.0, ge=1900, le=2100), mode: Literal["preview", "full"] = "preview"):
    m = get_manifest(sid)
    if mode == "preview" and not m["frames"]:
        raise HTTPException(409, "Sequence has no frames yet")
    if mode == "full" and not (m["wise_done"] or m["status"] == "done"):
        raise HTTPException(409, "Sequence still fetching its WISE frames; full measurement needs them")
    pos, pm = resolve(m, ra, dec, pmra_masyr, pmdec_masyr, epoch_yr)
    if mode == "preview":
        return _response(mode, ra, dec, pos, pm, res=analyse(m, pos, pm, grid_frames(m, pos, pm), "preview"))
    key = _cache_key(sid, pos, pm)
    path = seq_dir(sid) / "probe" / f"{key}.json"
    if path.exists():
        c = json.loads(path.read_text())
        if c.pop("_key") == [m["status"], len(m["frames"])]:
            return _response(mode, ra, dec, pos, pm, res=c)
    with FULL_LOCK:
        st = FULL_JOBS.get(key)
        if st and st["error"]:  # report the failure once; the next call retries
            FULL_JOBS.pop(key)
            return _response(mode, ra, dec, pos, pm, status="error", error=st["error"])
        if st is None:
            if len(FULL_JOBS) >= MAX_FULL_JOBS:
                raise HTTPException(503, "Too many full measurements queued; try again in a minute")
            st = FULL_JOBS[key] = {"done": 0, "total": 0, "error": None}
            st["future"] = FULL_POOL.submit(_run_full, key, m, pos, pm, st, path)
        # 1-based place among full jobs waiting for the single orchestrator; None once running
        waiting = [k for k, s in FULL_JOBS.items() if not (s["future"].running() or s["future"].done())]
    return _response(mode, ra, dec, pos, pm, status="running", progress={"done": st["done"], "total": st["total"]},
                     queue_position=waiting.index(key) + 1 if key in waiting else None)
