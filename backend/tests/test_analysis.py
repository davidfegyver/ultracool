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
