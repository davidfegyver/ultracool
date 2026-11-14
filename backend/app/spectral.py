"""Spectral typing of SPHEREx photometry against the SPIFF ultracool-dwarf templates (CC-BY 4.0, see data/ATTRIBUTION.md).
The /spectrum route lives in analysis.py: it also checks the photometry for contamination by other sources."""
import csv
import math
from pathlib import Path

import numpy as np

DATA = Path(__file__).parent / "data"
SUFFIX = "_spherex_standard.csv"


def _load_template(p):
    """(wavelength, F_lambda, uncertainty): the uncertainty is the spread of the standards behind each
    hybrid template (median ~20% for early T), which SPIFF also carries into its chi2."""
    t = np.genfromtxt(p, delimiter=",", skip_header=1)[:, :3]
    t = t[np.isfinite(t[:, :2]).all(axis=1)]  # esdL8 and sdT4 contain a NaN flux row
    t[:, 2] = np.nan_to_num(t[:, 2])
    return t


TEMPLATES = {p.name.removesuffix(SUFFIX): _load_template(p) for p in sorted((DATA / "templates").glob(f"*{SUFFIX}"))}
with open(DATA / "spherex_bins.csv") as fh:
    _bins = np.array([(float(r["wavelength_center_um"]), float(r["wavelength_width_um"])) for r in csv.DictReader(fh)])
BIN_CENTRE, BIN_WIDTH = _bins[:, 0], _bins[:, 1]
MIN_BINS = 10
MAX_CHI2_RED = 10
# per-channel systematic floor, added in quadrature after binning (it does not average down over repeat
# visits): SPHEREx L2 calibration is quoted at the few-% level (IRSA SPHEREx DR1 explanatory notes), and our
# forced photometry adds EPSF-zone aperture corrections and pixel-phase effects of a few % more. 3% left
# eps Ind B (SPIFF T3 at chi2_r 1.6) at chi2_r 10.5 with every residual a smooth few-% wiggle; 5% gives 4.5.
SYS_FRAC = 0.05
# A template "match" needs the target itself: inverse-variance weighted mean F_lambda over the 3.5-5.0 um bins
# (where every ultracool dwarf is brightest relative to its 1-3 um flux) at >= 5 sigma. Noise or a static
# diffraction spike otherwise fits *some* template at chi2_r ~1.5 (J2011-0624 typed "sdT4" at S/N 3.5).
DET_BAND_UM = (3.5, 5.0)
DET_MIN_SNR = 5.0


def detection_snr(lam, flx, err):
    sel = (lam >= DET_BAND_UM[0]) & (lam <= DET_BAND_UM[1])
    if not sel.any():
        return None
    w = err[sel] ** -2
    return float(np.sum(w * flx[sel]) / math.sqrt(np.sum(w)))


def _bin(points):
    """Inverse-variance weighted F_lambda per SPHEREx channel -> (centres, flambda, err)."""
    sw = np.zeros(len(BIN_CENTRE))
    swf = np.zeros(len(BIN_CENTRE))
    for p in points:
        lam = p["wavelength_um"]
        inside = np.abs(BIN_CENTRE - lam) <= BIN_WIDTH / 2
        if not inside.any():
            continue
        i = int(np.argmin(np.where(inside, np.abs(BIN_CENTRE - lam), np.inf)))
        f, e = p["flux_ujy"] / lam**2, p["flux_err_ujy"] / lam**2
        sw[i] += 1 / e**2
        swf[i] += f / e**2
    ok = sw > 0
    return BIN_CENTRE[ok], swf[ok] / sw[ok], 1 / np.sqrt(sw[ok])


def classify(frames):
    # No per-frame S/N cut: for faint targets it keeps only upward noise, and the non-detections
    # (e.g. no 1-3 um flux from a cold dwarf) are what separates the templates. S/N is judged per bin.
    pts = [f for f in frames
           if f["survey"] == "spherex" and not f["flagged"] and f["flux_ujy"] is not None
           and f["flux_err_ujy"] and f["flux_err_ujy"] > 0
           and f["wavelength_um"] is not None and 1.0 <= f["wavelength_um"] <= 5.0]
    lam, flx, err = _bin(pts)
    err = np.hypot(err, SYS_FRAC * np.abs(flx))
    binned = [{"wavelength_um": float(a), "flambda": float(b), "err": float(c)} for a, b, c in zip(lam, flx, err)]
    if int(np.sum(flx / err >= 3)) < MIN_BINS:
        return {"verdict": "insufficient data", "best": None, "ranking": [], "binned": binned, "template_curve": None,
                "detection_snr": detection_snr(lam, flx, err)}

    fits = []
    for label, t in TEMPLATES.items():
        m = (lam >= t[0, 0]) & (lam <= t[-1, 0])
        n = int(m.sum())
        if n < 2:
            continue
        tm = np.interp(lam[m], t[:, 0], t[:, 1])
        tu = np.interp(lam[m], t[:, 0], t[:, 2])
        f, s = flx[m], err[m]
        a = np.sum(f * tm / s**2) / np.sum(tm**2 / s**2)
        for _ in range(2):  # template spread scales with the fitted amplitude: refit with the total error
            st = np.hypot(s, a * tu)
            a = np.sum(f * tm / st**2) / np.sum(tm**2 / st**2)
        chi2 = float(np.sum(((f - a * tm) / np.hypot(s, a * tu)) ** 2))
        fits.append((chi2, label, float(a), n))
    fits.sort()
    chi2_min = fits[0][0]
    w = np.array([math.exp(-(c - chi2_min) / 2) for c, *_ in fits])
    probs = w / w.sum()
    ranking = [{"label": label, "prob": float(p), "chi2_red": c / (n - 1), "n_bins": n}
               for (c, label, _, n), p in zip(fits, probs)][:5]
    best = ranking[0]
    _, label, a, _ = fits[0]
    t = TEMPLATES[label]
    det = detection_snr(lam, flx, err)
    curve = {"label": label, "wavelength_um": t[:, 0].tolist(), "flambda": (a * t[:, 1]).tolist()}
    if det is None or det < DET_MIN_SNR:  # ranking kept for experts, no type claimed
        return {"verdict": "insufficient data", "best": None, "ranking": ranking, "binned": binned,
                "template_curve": None, "detection_snr": det, "reason": "no clear SPHEREx detection"}
    return {"verdict": "match" if best["chi2_red"] <= MAX_CHI2_RED else "not consistent with ultracool dwarf templates",
            "best": best, "ranking": ranking, "binned": binned, "template_curve": curve, "detection_snr": det}
