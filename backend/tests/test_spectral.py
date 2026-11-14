import numpy as np

from app.spectral import BIN_CENTRE, TEMPLATES, classify


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
