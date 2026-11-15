"""Spectral typing of SPHEREx photometry against the SPIFF ultracool-dwarf templates (CC-BY 4.0, see data/ATTRIBUTION.md).
The /spectrum route lives in analysis.py: it also checks the photometry for contamination by other sources."""
import csv
import math
import re
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
OUTLIER_K = 5.0  # per-channel frame rejection, as probe.flag_outliers
# type range: templates within Delta chi2 = 4 (2 sigma, one parameter) of the best, after rescaling, widened by
# TYPE_SYS subtypes each way: on 20 typed validation dwarfs the statistical range alone held the literature
# type for 7 only, while |ours - literature| <= 1 subtype for 13 (research/spectra/REPORT.md)
TYPE_DCHI2 = 4.0
TYPE_SYS = 1.0
SPT_RE = re.compile(r"([MLTY])(\d+(?:\.\d+)?)")
SPT_BASE = {"M": 0, "L": 10, "T": 20, "Y": 30}
SPT_MIN, SPT_MAX = 8.0, 31.0  # M8 and Y1, the ends of the template grid
# A template "match" needs the target itself: inverse-variance weighted mean F_lambda over the 3.5-5.0 um bins
# (where every ultracool dwarf is brightest relative to its 1-3 um flux) at >= 5 sigma. Noise or a static
# diffraction spike otherwise fits *some* template at chi2_r ~1.5 (J2011-0624 typed "sdT4" at S/N 3.5).
DET_BAND_UM = (3.5, 5.0)
DET_MIN_SNR = 5.0
NO_DETECTION = "no clear SPHEREx detection"
# The templates start at M8, so any warmer star (most field stars) lands on the earliest ones, and blends or
# galaxies can land anywhere. The 1.4 um water band tells them apart: it strengthens steadily from mid-M through
# the L and T sequence (Reid et al. 2001, AJ 121, 1710; Cushing et al. 2005, ApJ 623, 1115). Depth = F_lambda in
# 1.38-1.50 um over the continuum interpolated between 1.20-1.30 and 1.58-1.70 um (at R~40 the band is wide; a
# plain 1.4/1.25 ratio cannot tell water from a warm star's Rayleigh-Jeans fall). Templates: M8-M9 0.72-0.77,
# L 0.50-0.73, T0 0.49 down to T8 0.08. Measured here: LP 944-20 (M9.5) 0.68, 2MASS J0746+20 (L0+L1.5) 0.67,
# Kelu-1 (L2+L3.5) 0.63 (each +-0.02, 0-0.05 deeper than their best templates); ordinary stars 0.91-0.99: two
# Gaia M dwarfs (G=18.7 and 19.5, typed M8/sdM9.5 by chi2 alone) 0.93 +- 0.05 and 0.94 +- 0.07, bright field
# stars 0.93-0.99. A "match" whose band is > WATER_SIGMA shallower than its template's (measurement error plus
# DEPTH_SCATTER, the spread of the six M8-M9 templates) is demoted.
EARLY_LABELS = {"M8", "M8 β", "M9", "M9 β", "M9 γ", "sdM9.5"}
H2O_BAND_UM, H2O_CONT_UM = (1.38, 1.50), ((1.20, 1.30), (1.58, 1.70))
DEPTH_SCATTER = 0.03
WATER_SIGMA = 2.5
WARMER = "warmer than M8: probably an ordinary star"
DOUBTFUL = "doubtful match"


def detection_snr(lam, flx, err):
    sel = (lam >= DET_BAND_UM[0]) & (lam <= DET_BAND_UM[1])
    if not sel.any():
        return None
    w = err[sel] ** -2
    return float(np.sum(w * flx[sel]) / math.sqrt(np.sum(w)))


def _bin(points):
    """Per SPHEREx channel: frames more than OUTLIER_K x (own error + the channel's robust spread) from the
    channel median are dropped (cosmic rays, asteroids, a neighbour's spike, a failed fit), the rest averaged
    with inverse-variance weights; with >= 3 frames the error is scaled up by sqrt(chi2_red) when the frames
    scatter more than their errors say -> (centres, flambda, err)."""
    lam = np.array([p["wavelength_um"] for p in points], float)
    d = np.abs(BIN_CENTRE[None, :] - lam[:, None])
    inside = d <= BIN_WIDTH / 2
    ch = np.where(inside.any(axis=1), np.argmin(np.where(inside, d, np.inf), axis=1), -1)
    f = np.array([p["flux_ujy"] for p in points], float) / lam**2
    e = np.array([p["flux_err_ujy"] for p in points], float) / lam**2
    out = []
    for c in np.unique(ch[ch >= 0]):
        fc, ec = f[ch == c], e[ch == c]
        if len(fc) >= 3:
            med = np.median(fc)
            keep = np.abs(fc - med) <= OUTLIER_K * np.hypot(ec, 1.4826 * np.median(np.abs(fc - med)))
            fc, ec = fc[keep], ec[keep]
        w = ec**-2
        mu, err = float(np.sum(w * fc) / np.sum(w)), float(1 / math.sqrt(np.sum(w)))
        if len(fc) >= 3:
            err *= math.sqrt(max(1.0, float(np.sum(((fc - mu) / ec) ** 2)) / (len(fc) - 1)))
        out.append((BIN_CENTRE[c], mu, err))
    a = np.array(out, float).reshape(-1, 3)
    return a[:, 0], a[:, 1], a[:, 2]


def _band_mean(lam, f, e, band):
    sel = (lam >= band[0]) & (lam <= band[1])
    if not sel.any():
        return None
    w = e[sel] ** -2
    return float(np.sum(w * f[sel]) / np.sum(w)), float(1 / math.sqrt(np.sum(w))), sel


def water_depth(lam, flx, err):
    """F_lambda in the 1.4 um water band over the continuum interpolated from both sides -> (depth, err), or
    None (a window without channels, or no positive continuum)."""
    r = [_band_mean(lam, flx, err, w) for w in (H2O_BAND_UM, *H2O_CONT_UM)]
    if any(x is None for x in r):
        return None
    lb, l1, l2 = (float(np.mean(lam[x[2]])) for x in r)
    k = (lb - l1) / (l2 - l1)
    cont = (1 - k) * r[1][0] + k * r[2][0]
    if cont <= 0:
        return None
    d = r[0][0] / cont
    return d, math.hypot(r[0][1], d * math.hypot((1 - k) * r[1][1], k * r[2][1])) / cont


_CH = BIN_CENTRE[(BIN_CENTRE >= 1.0) & (BIN_CENTRE <= 2.0)]
TEMPLATE_DEPTH = {label: water_depth(_CH, np.interp(_CH, t[:, 0], t[:, 1]), np.ones_like(_CH))[0]
                  for label, t in TEMPLATES.items()}


def demote(spec, reason):
    """A template 'match' the object itself argues against: on one of the earliest templates it is a warmer,
    ordinary star; otherwise the match is doubtful. Best match and ranking are kept for experts."""
    spec.update(verdict=WARMER if spec["best"]["label"] in EARLY_LABELS else DOUBTFUL, doubt=reason)


def spt_num(label):
    """Template label -> M0 = 0 ... L0 = 10, T0 = 20, Y0 = 30 (gravity/metallicity tags ignored), or None."""
    m = SPT_RE.search(label)
    return SPT_BASE[m.group(1)] + float(m.group(2)) if m else None


def spt_label(v):
    k = "MLTY"[min(3, int(v // 10))]
    return f"{k}{v - SPT_BASE[k]:g}"


def type_range(fits):
    """[earliest, latest] spectral type among the templates within TYPE_DCHI2 of the best fit, widened by TYPE_SYS
    and clipped to M8-Y1; the chi2
    curve rescaled by the best chi2_red when that exceeds 1 (the errors are then too small for the fit)."""
    c0, _, _, n0 = fits[0]
    scale = max(1.0, c0 / max(1, n0 - 1))
    v = [spt_num(label) for c, label, _, _ in fits if (c - c0) / scale <= TYPE_DCHI2]
    v = [x for x in v if x is not None]
    return [spt_label(max(SPT_MIN, min(v) - TYPE_SYS)), spt_label(min(SPT_MAX, max(v) + TYPE_SYS))] if v else None


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
        det = detection_snr(lam, flx, err)
        return {"verdict": "insufficient data", "best": None, "ranking": [], "binned": binned, "template_curve": None,
                "detection_snr": det,  # None: no 3.5-5 um channel at all (e.g. saturated): no data, not undetected
                **({"reason": NO_DETECTION} if det is not None and det < DET_MIN_SNR else {})}

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
                "template_curve": None, "detection_snr": det, "reason": NO_DETECTION}
    verdict = "match" if best["chi2_red"] <= MAX_CHI2_RED else "not consistent with ultracool dwarf templates"
    out = {"verdict": verdict, "best": best, "ranking": ranking, "binned": binned, "template_curve": curve,
           "detection_snr": det, "water_depth": None, "type_range": type_range(fits)}
    wd = water_depth(lam, flx, err)
    if wd:
        out["water_depth"] = {"value": wd[0], "err": wd[1], "template": TEMPLATE_DEPTH[label]}
        if verdict == "match" and (wd[0] - TEMPLATE_DEPTH[label]) / math.hypot(wd[1], DEPTH_SCATTER) > WATER_SIGMA:
            demote(out, f"its 1.4 micrometre water band is shallower than a {label}'s")
    return out
