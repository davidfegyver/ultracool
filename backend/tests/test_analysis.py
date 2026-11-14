import math

import numpy as np
import pytest
from fastapi import HTTPException

from app.analysis import centroid, classify_variability, find_tracks, fit_motion, measure_color
from app.frames import clipped_mean
from app.sequences import SeqRequest, _params, _units
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
        np.save(tmp_path / "seq" / sid / "npy" / f"{fid}.npy", img.astype(np.float32))
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
