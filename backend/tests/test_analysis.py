import math
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest
from fastapi import HTTPException

from app.analysis import _target_track, centroid, classify_variability, find_tracks, fit_motion, measure_color
from app.frames import clipped_mean, make_grid
from app.sequences import SeqRequest, _params, _units, run_chunks
from app.sources import RawFrame


def _star(shape, x, y, flux, sigma=1.0):
    yy, xx = np.indices(shape)
    return flux * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * sigma**2)) / (2 * np.pi * sigma**2)


def test_motion_fit_recovers_synthetic_proper_motion():
    rng = np.random.default_rng(1)
    pm_px = (0.8, -0.5)  # px/yr in grid x (west) and y (north)
    years = np.arange(2010.0, 2026.0, 2.0)
    pts = []
    for t in years:
        x, y = 30 + pm_px[0] * (t - 2018), 30 + pm_px[1] * (t - 2018)
        z = rng.standard_normal((60, 60)) + _star((60, 60), x, y, 300)
        c = centroid(z, 30, 30, 12, 2.35)
        assert c is not None
        pts.append(c)
    xs, ys, err = (np.array([p[i] for p in pts]) for i in range(3))
    fit = fit_motion(years, -xs * 2.75, ys * 2.75, err * 2.75)
    assert fit["pmra"] == pytest.approx(-pm_px[0] * 2750, abs=4 * fit["pmra_err"])
    assert fit["pmdec"] == pytest.approx(pm_px[1] * 2750, abs=4 * fit["pmdec_err"])
    assert fit["significance"] > 10


def test_static_source_is_not_moving():
    rng = np.random.default_rng(2)
    years = np.arange(2010.0, 2026.0, 2.0)
    pts = [centroid(rng.standard_normal((60, 60)) + _star((60, 60), 30.3, 29.6, 300), 30, 30, 12, 2.35) for _ in years]
    xs, ys, err = (np.array([p[i] for p in pts]) for i in range(3))
    assert fit_motion(years, -xs * 2.75, ys * 2.75, err * 2.75)["significance"] < 3


def test_saturated_core_centroid():
    z = _star((50, 50), 24.6, 20.2, 5e4, sigma=2.0) + np.random.default_rng(3).standard_normal((50, 50))
    z[z > 300] = np.nan  # saturated core
    x, y, err, _ = centroid(z, 25, 20, 8, 2.35)
    assert (x, y) == pytest.approx((24.6, 20.2), abs=0.3)


def test_find_tracks_finds_mover_among_static_stars():
    rng = np.random.default_rng(4)
    years = [2010.5, 2015.0, 2017.0, 2019.0, 2021.0, 2023.0, 2024.5]
    static = rng.uniform(10, 90, (40, 2))
    dets = []
    for t in years:
        mover = np.array([[20 + 1.2 * (t - 2010), 70 - 0.9 * (t - 2010)]])
        xy = np.vstack([static + rng.normal(0, 0.1, static.shape), mover + rng.normal(0, 0.1, (1, 2))])
        dets.append(np.column_stack([xy, np.full(len(xy), 20.0)]))
    tracks = find_tracks(dets, years)
    assert len(tracks) == 1
    fit = tracks[0]["fit"]
    assert fit["pmra"] == pytest.approx(-1.2 * 2750, rel=0.05)
    assert fit["pmdec"] == pytest.approx(-0.9 * 2750, rel=0.05)


def _visits(n_years=10, seed=0):
    rng = np.random.default_rng(seed)
    return np.sort(np.concatenate([55200 + 182.6 * np.arange(2 * n_years) + rng.uniform(-3, 3, 2 * n_years),
                                   61000 + rng.uniform(0, 400, 6)]))


def test_variability_periodic_vs_constant_vs_irregular():
    t = _visits()
    rng = np.random.default_rng(5)
    mira = 1e6 * (1 + 0.5 * np.sin(2 * np.pi * t / 245.0))
    lc = {b: [(ti, f * (1 + 0.02 * rng.standard_normal()), 0.02 * f) for ti, f in zip(t, mira)] for b in ("W1", "W2")}
    r = classify_variability(lc)
    assert r["verdict"] == "periodic variable"
    assert r["fap"] < 0.01

    const = {b: [(ti, 1e5 * (1 + 0.02 * rng.standard_normal()), 2e3) for ti in t] for b in ("W1", "W2")}
    assert classify_variability(const)["verdict"] == "constant"

    wild = {b: [(ti, 1e5 * (1 + 0.4 * rng.standard_normal()), 2e3) for ti in t] for b in ("W1", "W2")}
    assert classify_variability(wild)["verdict"] == "irregular variable"

    assert classify_variability({"W1": lc["W1"][:3]})["verdict"] == "insufficient data"


def test_color_classes_and_lower_limit():
    def lc(f1, f2, e1=10.0, e2=10.0):
        return {"W1": [(i, f1, e1) for i in range(5)], "W2": [(i, f2, e2) for i in range(5)]}

    # equal Vega magnitudes -> W1-W2 = 0
    assert measure_color(lc(309.540e3, 171.787e3))["verdict"] == "normal star colors"
    red = measure_color(lc(309.540e3, 171.787e3 * 10 ** (0.4 * 1.0)))
    assert red["w1_w2"] == pytest.approx(1.0) and red["verdict"] == "red (L/T dwarf-like)"
    cold = measure_color(lc(5.0, 2000.0))  # W1 not detected
    assert cold["w1_w2_is_lower_limit"] and cold["w1_w2"] > 2 and cold["verdict"].startswith("extremely red")


def test_color_bands_follow_kirkpatrick_2021():
    from app.analysis import _color_class

    # J2317 (T5-T6) 2.19, J0415 (T8) 2.87, eps Ind B (T1+T6) 1.16, L dwarfs and stars < 0.6
    assert [_color_class(c) for c in (0.0, 0.3, 0.6, 1.16, 1.6, 2.19, 2.6, 2.87, 3.6)] == [
        "normal star colors", "normal star colors", "red (L/T dwarf-like)", "red (L/T dwarf-like)",
        "very red (T dwarf-like)", "very red (T dwarf-like)", "extremely red (Y/late-T dwarf-like)",
        "extremely red (Y/late-T dwarf-like)", "extremely red (Y/late-T dwarf-like)"]


def test_plain_sentences_use_words_not_weights():
    from app.analysis import _plain_props, _runner_up

    assert _runner_up([{"label": "T5", "chi2_red": 1.5, "n_bins": 89}, {"label": "T6", "chi2_red": 1.52, "n_bins": 89}]) \
        == "; T6 fits about as well."
    assert "clearly worse" in _runner_up([{"label": "T3", "chi2_red": 4.4, "n_bins": 89}, {"label": "T2", "chi2_red": 5.0, "n_bins": 89}])
    color = {"w1_w2": 1.0, "w1_w2_is_lower_limit": False, "verdict": "red (L/T dwarf-like)"}
    match = {"verdict": "match", "best": {"label": "T1", "prob": 0.97}, "ranking": [{"label": "T1", "chi2_red": 1, "n_bins": 50}]}
    s = _plain_props(color, {"verdict": "constant"}, match)
    assert "%" not in s[-1] and "dusty" not in s[0]
    assert "dusty" in _plain_props(color, {"verdict": "constant"}, {"verdict": "insufficient data"})[0]


def test_wise_exposures_needs_short_window():
    base = {"ra": 10.0, "dec": 5.0}
    with pytest.raises(HTTPException) as e:
        _params(SeqRequest(**base, wise_exposures=True))
    assert e.value.status_code == 400
    with pytest.raises(HTTPException):
        _params(SeqRequest(**base, wise_exposures=True, mjd_min=58000, mjd_max=58040))
    with pytest.raises(HTTPException):
        _params(SeqRequest(**base, mjd_min=58010, mjd_max=58000))
    p = _params(SeqRequest(**base, wise_exposures=True, mjd_min=58000, mjd_max=58030))
    assert p["wise_exposures"] and p["mjd_max"] == 58030
    assert _params(SeqRequest(**base))["mjd_min"] is None


def test_units_kinds():
    def f(survey, band, mjd, stem):
        return RawFrame(survey, band, mjd, "", "", "", "", stem)

    raw = [f("spherex", "D1", 60000, "s1"), f("wise", "W1", 58000.0, "a-w1"), f("wise", "W1", 58001.0, "b-w1"),
           f("wise", "W1", 58200.0, "c-w1")]
    assert {(u[0], u[1], len(u[2])) for u in _units(raw)} == {
        ("sx-s1", "single", 1), ("wise-W1-v00", "visit", 2), ("wise-W1-v01", "visit", 1)}
    assert {(u[0], u[1]) for u in _units(raw, wise_exposures=True)} >= {("wise-W1-a-w1", "exposure"),
                                                                       ("wise-W1-b-w1", "exposure")}


def test_clipped_mean_rejects_cosmic_ray():
    rng = np.random.default_rng(6)
    imgs = [rng.normal(10, 1, (20, 20)) for _ in range(12)]
    imgs[3][5, 5] = 500.0
    imgs[7][8, 8] = np.nan
    m = clipped_mean(imgs)
    assert abs(m[5, 5] - 10) < 1.5 and math.isfinite(m[8, 8])


# ---- faint movers next to static stars (measure_motion on a synthetic sequence on disk)


def _synthetic_sequence(tmp_path, monkeypatch, mover_flux, neighbour_flux=40.0, seed=7):
    from app import sequences
    from app.analysis import measure_motion
    from app.frames import make_grid

    monkeypatch.setattr(sequences, "CACHE_DIR", tmp_path)
    rng = np.random.default_rng(seed)
    sid = "00000000000000aa"
    (tmp_path / "seq" / sid / "npy").mkdir(parents=True)
    wcs, shape = make_grid(150.0, 0.0, 70 * 2.75 / 3600)
    cx, cy = wcs.wcs.crpix[0] - 1, wcs.wcs.crpix[1] - 1
    pmra, pmdec = -1300.0, -2300.0  # mas/yr, like WISEA J1534-1043
    years = [2010.2, 2010.7] + [2014.2 + 0.5 * i for i in range(21)]
    frames = []
    for i, t in enumerate(years):
        x, y = cx - pmra / 1000 * (t - 2018) / 2.75, cy + pmdec / 1000 * (t - 2018) / 2.75
        img = rng.standard_normal(shape) + _star(shape, x, y, mover_flux)
        # a 4x brighter static star 5 px (14") to the side of the track: the brightest source near the
        # prediction, which a wide search latches onto (closer than ~3 px it truly blends in 2-yr stacks)
        img += _star(shape, cx + 4.35, cy + 2.45, neighbour_flux)
        fid = f"wise-W2-v{i:02d}"
        np.savez_compressed(tmp_path / "seq" / sid / "npy" / f"{fid}.npz", raw=img.astype(np.float32))
        frames.append({"id": fid, "survey": "wise", "band": "W2", "kind": "visit", "mjd": 51544.5 + (t - 2000) * 365.25,
                       "flux_ujy": None, "flux_err_ujy": None, "flagged": False, "flag_names": [], "magzp": 20.0,
                       "target_px": [x, shape[0] - 1 - y]})
    m = {"id": sid, "status": "done", "frames": frames,
         "grid": {"wcs": {"NAXIS": 2, "NAXIS1": shape[1], "NAXIS2": shape[0], "CTYPE1": "RA---TAN",
                          "CTYPE2": "DEC--TAN", "CRVAL1": 150.0, "CRVAL2": 0.0, "CRPIX1": float(wcs.wcs.crpix[0]),
                          "CRPIX2": float(wcs.wcs.crpix[1]), "CDELT1": -2.75 / 3600, "CDELT2": 2.75 / 3600},
                  "width": shape[1], "height": shape[0]},
         "target": {"ra": 150.0, "dec": 0.0, "pmra_masyr": pmra, "pmdec_masyr": pmdec, "epoch_yr": 2018.0}}
    return measure_motion(m), (pmra, pmdec)


def test_faint_mover_beside_static_star_is_recovered(tmp_path, monkeypatch):
    mo, (pmra, pmdec) = _synthetic_sequence(tmp_path, monkeypatch, mover_flux=10.0)  # S/N ~3 per visit
    assert mo["recovered"] and mo["verdict"] == "moving"
    assert mo["pmra_masyr"] == pytest.approx(pmra, abs=4 * mo["pmra_err_masyr"] + 100)
    assert mo["pmdec_masyr"] == pytest.approx(pmdec, abs=4 * mo["pmdec_err_masyr"] + 100)


def test_undetectable_mover_is_never_called_not_moving(tmp_path, monkeypatch):
    mo, _ = _synthetic_sequence(tmp_path, monkeypatch, mover_flux=0.0)  # only the static neighbour is there
    assert mo["verdict"] != "not moving"
    assert mo["recovered"] is False


# ---- low-S/N photometry must not make variables or colours


def test_faint_band_variability_is_insufficient():
    t = _visits()
    rng = np.random.default_rng(8)
    faint = {b: [(ti, 30 + 40 * rng.standard_normal(), 15.0) for ti in t] for b in ("W1", "W2")}  # S/N ~2, chi2 ~7
    assert classify_variability(faint)["verdict"] == "insufficient data"


def test_single_bad_visit_does_not_make_a_variable():
    t = _visits()
    rng = np.random.default_rng(9)
    lc = {"W2": [(ti, 1e4 * (1 + 0.02 * rng.standard_normal()), 200.0) for ti in t]}
    lc["W2"][5] = (t[5], 2e4, 200.0)  # one failed co-add
    assert classify_variability(lc)["verdict"] == "constant"


def test_w1_not_seen_by_astrometry_gives_lower_limit():
    lc = {"W1": [(i, 30.0, 5.0) for i in range(10)], "W2": [(i, 100.0, 10.0) for i in range(10)]}
    assert not measure_color(lc)["w1_w2_is_lower_limit"]  # W1 "detected" at 6 sigma: neighbour light
    c = measure_color(lc, w1_undetected=True)
    assert c["w1_w2_is_lower_limit"] and c["w1_w2"] < measure_color(lc)["w1_w2"]


# ---- mover vetting: two static sources must not be linked into a track


def _windows(moving, seed=11):
    from app.analysis import FWHM_PX, _snr_map
    rng = np.random.default_rng(seed)
    years = [2010.3, 2015.1, 2017.1, 2019.1, 2021.1, 2023.1, 2024.3]
    ns = [2, 4, 4, 4, 4, 4, 2]
    shape = (60, 60)
    snrs, dets = [], []
    for t in years:
        x = 20 + 14 * (t - years[0]) / (years[-1] - years[0])  # 1 px/yr: from (20, 30) to (34, 30)
        z = rng.standard_normal(shape)
        if moving:
            z += _star(shape, x, 30, 25.0)
        else:  # two faint static stars at the two ends, detected only intermittently by the linker
            z += _star(shape, 20, 30, 25.0) + _star(shape, 34, 30, 25.0)
        snrs.append(_snr_map(z, FWHM_PX["W2"]))
        dets.append(np.array([[x, 30.0, 6.0]]))  # what the linker saw: one detection per window on the line
    return dets, years, ns, snrs


def test_vetting_rejects_two_static_sources_linked_into_a_track():
    from app.analysis import _vet_track
    dets, years, ns, snrs = _windows(moving=False)
    tracks = find_tracks(dets, years)
    assert len(tracks) == 1  # the linker alone is fooled
    assert _vet_track(tracks[0], dets, years, ns, snrs, {}) is not None


def test_vetting_keeps_a_real_mover():
    from app.analysis import _vet_track
    dets, years, ns, snrs = _windows(moving=True)
    tracks = find_tracks(dets, years)
    assert len(tracks) == 1
    assert _vet_track(tracks[0], dets, years, ns, snrs, {}) is None


def test_fetch_order_puts_priority_bands_and_wise_first():
    from app.sequences import order_units

    def f(survey, band, mjd, stem):
        return RawFrame(survey, band, mjd, "", "", "", "", stem)

    raw = [f("spherex", "D1", 61000, "a"), f("spherex", "D6", 61200, "b"), f("spherex", "D6", 61100, "c"),
           f("wise", "W1", 58000, "w1a"), f("wise", "W2", 58300, "w2b"), f("wise", "W2", 55300, "w2a")]
    order = [u[0] for u in order_units(_units(raw), ["W2", "D6"])]
    assert order == ["wise-W2-v00", "wise-W2-v01", "sx-c", "sx-b", "wise-W1-v00", "sx-a"]


def test_track_on_bright_star_artifacts_is_flagged():
    from app.analysis import _artifact_frac
    from app.frames import make_grid

    wcs, _ = make_grid(150.0, 0.0, 0.05)
    track = lambda ty: (30.0 + 0.5 * (ty - 2018), 30.0)  # noqa: E731 - grid px, moving 1.4"/yr east-west
    mjds = [51544.5 + (y - 2000) * 365.25 for y in np.linspace(2010, 2024, 20)]
    on = [np.array([wcs.pixel_to_world_values(*track(2000 + (mjd - 51544.5) / 365.25))]) for mjd in mjds]
    art = [(mjd, p if i % 4 else np.empty((0, 2))) for i, (mjd, p) in enumerate(zip(mjds, on))]  # on it in 15/20
    assert _artifact_frac(art, wcs, track) == 0.75
    far = [(mjd, p + [0.0, 20 / 3600]) for mjd, p in art]  # artifacts 20" away
    assert _artifact_frac(far, wcs, track) == 0.0


def test_queue_position_and_eta(monkeypatch):
    from concurrent.futures import Future

    from app import sequences

    running, waiting1, waiting2 = Future(), Future(), Future()
    running.set_running_or_notify_cancel()
    monkeypatch.setattr(sequences, "JOBS", {"a": running, "b": waiting1, "c": waiting2})
    monkeypatch.setattr(sequences, "MAX_RUNNING_SEQUENCES", 1)
    monkeypatch.setattr(sequences, "DURATIONS", sequences.deque([100.0]))
    monkeypatch.setattr(sequences, "STARTED", {"a": (sequences.time.time() - 50, 10)})
    assert sequences.queue_status("c", {"status": "querying", "done": 0, "total": 0}) == (2, 300.0)
    pos, eta = sequences.queue_status("a", {"status": "fetching", "done": 60, "total": 110})
    assert pos is None and eta == pytest.approx(50, rel=0.05)  # 50 units at 1 unit/s
    assert sequences.queue_status("z", {"status": "done", "done": 5, "total": 5}) == (None, None)


def test_saturated_or_undetected_target_is_not_sure(monkeypatch):
    """Saturated star on catalog photometry: no 'constant'/'irregular' verdict (a period still counts); target
    found in neither W1 nor W2 by the astrometry: no colour and no variability verdict."""
    from app import analysis

    lc = {b: [(55000.0 + 180 * i, 1000.0 * (2 if i == 3 else 1), 10.0) for i in range(12)] for b in ("W1", "W2")}
    motion = {"recovered": True, "undetected_bands": [], "track_snr": None, "verdict": "not moving"}
    monkeypatch.setattr(analysis, "measure_motion", lambda m: dict(motion))
    monkeypatch.setattr(analysis, "static_sky_flux", lambda m: {})
    monkeypatch.setattr(analysis, "find_asteroids", lambda m: [])
    monkeypatch.setattr(analysis, "typed_spectrum", lambda m, sky, color: {"verdict": "insufficient data",
                                                                           "neighbours_checked": True})
    monkeypatch.setattr(analysis, "_plain", lambda *a: [])
    monkeypatch.setattr(analysis, "photometry_lc", lambda m, sky: (lc, "catalog", "catalog"))
    monkeypatch.setattr(analysis, "_saturated", lambda m: True)
    s = analysis._summary({})
    assert s["variability"]["verdict"] == "insufficient data" and "saturated" in s["variability"]["note"]
    monkeypatch.setattr(analysis, "_saturated", lambda m: False)
    monkeypatch.setattr(analysis, "photometry_lc", lambda m, sky: (lc, "pipeline", "pipeline"))
    motion["undetected_bands"] = ["W1", "W2"]
    s = analysis._summary({})
    assert s["color"]["w1_w2"] is None and s["variability"]["verdict"] == "insufficient data"


def test_target_track_exact_at_high_dec_grid_corner():
    # the flat-sky offsets this replaced were 1.3 px off at a 0.25-deg grid corner at Dec +75
    wcs, _ = make_grid(30.0, 75.0, 0.25)
    years = np.arange(2010.0, 2026.0, 2.0)
    px = [(3 + 0.4 * (t - 2010), 4 + 0.3 * (t - 2010)) for t in years]
    pts = [{"ra": float(r), "dec": float(d), "mjd": 51544.5 + (t - 2000) * 365.25, "err_arcsec": 0.1}
           for t, (x, y) in zip(years, px) for r, d in [wcs.pixel_to_world_values(x, y)]]
    fit = _target_track(None, {"recovered": True, "verdict": "moving", "points": pts}, wcs)
    for t, (x, y) in zip(years, px):
        dt = t - fit["t0"]
        assert abs(-(fit["xi0"] + fit["pmra"] / 1000 * dt) / 2.75 - x) < 0.05
        assert abs((fit["eta0"] + fit["pmdec"] / 1000 * dt) / 2.75 - y) < 0.05


def _task(k, chunk):
    if chunk == [3]:
        raise RuntimeError("worker died")
    return [k * c for c in chunk]


def test_run_chunks_reports_a_failed_task_and_finishes_the_rest(monkeypatch):
    with ThreadPoolExecutor(2) as pool:
        monkeypatch.setattr("app.sequences._submit", pool.submit)
        got = {c[0]: r for c, r in run_chunks(_task, [[i] for i in range(6)], 2, 10)}
    assert isinstance(got.pop(3), RuntimeError)
    assert got == {i: [10 * i] for i in (0, 1, 2, 4, 5)}
