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
