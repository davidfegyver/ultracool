import numpy as np
import pytest

from app import analysis, psfphot
from app.analysis import colour_doubt, typed_spectrum
from app.spectral import BIN_CENTRE, DOUBTFUL, NO_DETECTION, TEMPLATES, WARMER, _bin, classify, spt_num


def _points(lams, seed=1):
    rng = np.random.default_rng(seed)
    t = TEMPLATES["T5"]
    out = []
    for lam in lams:
        flux = 3.7 * np.interp(lam, t[:, 0], t[:, 1]) * lam**2
        out.append({"survey": "spherex", "flagged": False, "wavelength_um": float(lam),
                    "flux_ujy": float(flux * (1 + 0.03 * rng.standard_normal())), "flux_err_ujy": float(0.03 * flux)})
    return out


def test_t5_spectrum_is_typed_t5():
    lams = BIN_CENTRE[(BIN_CENTRE >= 1.01) & (BIN_CENTRE <= 5.0)]
    r = classify(_points(lams))
    assert r["verdict"] == "match"
    assert r["best"]["label"] == "T5"


def test_few_bins_is_insufficient():
    lams = BIN_CENTRE[(BIN_CENTRE >= 1.01)][:5]
    assert classify(_points(lams))["verdict"] == "insufficient data"


def test_noise_is_not_typed():
    """Pure noise fits some template at chi2_r ~1 but must not be called a match."""
    rng = np.random.default_rng(3)
    lams = BIN_CENTRE[(BIN_CENTRE >= 1.01) & (BIN_CENTRE <= 5.0)]
    # spike/neighbour light at 1-3 um (>= 3 sigma per channel, enough channels to fit), only noise at 3.5-5 um
    pts = [{"survey": "spherex", "flagged": False, "wavelength_um": float(lam),
            "flux_ujy": float(30 * rng.standard_normal() + (80 if lam < 3 else 0)), "flux_err_ujy": 30.0}
           for lam in lams for _ in range(3)]
    r = classify(pts)
    assert r["verdict"] == "insufficient data"
    assert r["best"] is None and r["detection_snr"] < 5


def test_faint_but_detected_dwarf_still_typed():
    lams = BIN_CENTRE[(BIN_CENTRE >= 1.01) & (BIN_CENTRE <= 5.0)]
    pts = _points(lams)
    for p in pts:
        p["flux_err_ujy"] *= 4  # ~12% per channel: S/N ~8 each, detection S/N >> 5
    r = classify(pts)
    assert r["verdict"] == "match" and r["best"]["label"].startswith("T")


def _template_points(label, fill_water=False, err=0.08, seed=1):
    """A template's spectrum at 8% per channel; fill_water: the 1.4 um water band replaced by a straight
    continuum, as in a star warmer than M8."""
    rng = np.random.default_rng(seed)
    t = TEMPLATES[label]
    out = []
    for lam in BIN_CENTRE[(BIN_CENTRE >= 1.01) & (BIN_CENTRE <= 5.0)]:
        f = np.interp(lam, t[:, 0], t[:, 1])
        if fill_water and 1.33 <= lam <= 1.55:
            f = np.interp(lam, [1.30, 1.58], np.interp([1.30, 1.58], t[:, 0], t[:, 1]))
        flux = 50 * f * lam**2
        out.append({"survey": "spherex", "flagged": False, "wavelength_um": float(lam),
                    "flux_ujy": float(flux * (1 + err * rng.standard_normal())), "flux_err_ujy": float(err * flux)})
    return out


def test_shallow_water_band_demotes_early_and_l_matches():
    for label in ("M8", "M9", "L0"):
        assert classify(_template_points(label))["verdict"] == "match"
    r = classify(_template_points("M8", fill_water=True))
    assert r["verdict"] == WARMER and r["best"]["label"] == "M8" and r["ranking"]
    assert classify(_template_points("L0", fill_water=True))["verdict"] == DOUBTFUL


def test_blue_w1_w2_demotes_matches():
    def spec(label):
        return {"verdict": "match", "best": {"label": label}}

    def colour(c, err=0.02, limit=False):
        return {"w1_w2": c, "w1_w2_err": err, "w1_w2_is_lower_limit": limit}

    s = spec("M8")
    colour_doubt(s, colour(0.0))
    assert s["verdict"] == WARMER
    s = spec("L0 γ")
    colour_doubt(s, colour(0.0))
    assert s["verdict"] == DOUBTFUL
    for label, c in (("M9 β", colour(0.22)), ("L1", colour(0.24)), ("T5", colour(2.2)), ("L0", colour(0.0, limit=True)),
                     ("L0", colour(0.1, err=0.3))):
        s = spec(label)
        colour_doubt(s, c)
        assert s["verdict"] == "match", label


def test_no_detection_wins_over_negative_channels(monkeypatch):
    """Empty sky with an over-subtracted background: 'no clear detection', not 'crowded field'."""
    monkeypatch.setattr(analysis, "_catalogs", lambda m: {"catwise": None, "simbad": None})  # CatWISE unavailable
    lams = BIN_CENTRE[(BIN_CENTRE >= 1.01) & (BIN_CENTRE <= 5.0)]
    pts = [{"survey": "spherex", "flagged": False, "wavelength_um": float(lam), "mjd": 60800.0,
            "flux_ujy": -3.0 * 10 if i % 10 == 0 else 0.0, "flux_err_ujy": 10.0} for i, lam in enumerate(lams)]
    m = {"frames": pts, "target": {"ra": 0.0, "dec": 0.0, "pmra_masyr": 0.0, "pmdec_masyr": 0.0, "epoch_yr": 2000.0}}
    s = typed_spectrum(m, {}, {"w1_w2": None})
    assert s["negative_bins"] >= 3
    assert s["reason"] == NO_DETECTION and not s["contaminated"]
    assert s["photometry"] == "aperture" and not s["neighbours_checked"]


def test_outlier_frame_is_dropped_and_scatter_inflates_error():
    pts = [{"wavelength_um": 4.0, "flux_ujy": 100.0 + d, "flux_err_ujy": 1.0} for d in (-1, 0, 1, 0.5, -0.5)]
    _, f, e = _bin(pts + [{"wavelength_um": 4.0, "flux_ujy": 5000.0, "flux_err_ujy": 1.0}])  # cosmic ray
    assert abs(f[0] * 16 - 100.0) < 0.5 and e[0] * 16 == pytest.approx(1 / np.sqrt(5))
    scattered = [{"wavelength_um": 4.0, "flux_ujy": 100.0 + 10 * d, "flux_err_ujy": 1.0} for d in (-1, 0, 1, 0.5, -0.5)]
    _, _, e = _bin(scattered)
    assert e[0] * 16 > 3 / np.sqrt(5)  # 10x the stated errors: error scaled up by sqrt(chi2_red)


def test_type_range_brackets_the_true_type_and_widens_with_noise():
    lams = BIN_CENTRE[(BIN_CENTRE >= 1.01) & (BIN_CENTRE <= 5.0)]
    tight = classify(_points(lams))
    lo, hi = (spt_num(x) for x in tight["type_range"])
    assert lo <= spt_num("T5") <= hi
    noisy = _points(lams)
    for p in noisy:
        p["flux_err_ujy"] *= 6
    lo2, hi2 = (spt_num(x) for x in classify(noisy)["type_range"])
    assert lo2 <= spt_num("T5") <= hi2 and hi2 - lo2 >= hi - lo


def test_psf_fit_removes_a_bright_neighbour():
    """Faint target with a 10x brighter star 11" away (inside the 12.3" SPHEREx aperture): the joint fit
    recovers the target; a plain aperture sum would be dominated by the neighbour."""
    rng = np.random.default_rng(2)
    yy, xx = np.indices((41, 41))

    def star(x, y, flux, s=1.6):
        return flux / (2 * np.pi * s * s) * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * s * s))

    img = 5.0 + rng.standard_normal((41, 41)) + star(20.3, 19.6, 300) + star(24.3, 19.6, 3000)
    flux, err, nb_ap, s = psfphot.fit_frame(img, [(20.3, 19.6), (24.3, 19.6)], psfphot.frame_noise(img))
    assert abs(flux - 300) < 3 * err and err < 30
    assert nb_ap > 1000 and s == pytest.approx(1.6, abs=0.15)
    assert psfphot.fit_frame(np.full((41, 41), np.nan), [(20, 20)], 1.0) is None
