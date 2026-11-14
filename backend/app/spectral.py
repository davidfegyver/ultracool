"""Spectral typing of SPHEREx photometry against the SPIFF ultracool-dwarf templates (CC-BY 4.0, see data/ATTRIBUTION.md)."""
import csv
import math
from pathlib import Path

import numpy as np
from fastapi import APIRouter

from .sequences import get_manifest

router = APIRouter()
DATA = Path(__file__).parent / "data"
SUFFIX = "_spherex_standard.csv"


def _load_template(p):
    t = np.genfromtxt(p, delimiter=",", skip_header=1)[:, :2]
    return t[np.isfinite(t).all(axis=1)]  # esdL8 and sdT4 contain a NaN flux row


TEMPLATES = {p.name.removesuffix(SUFFIX): _load_template(p) for p in sorted((DATA / "templates").glob(f"*{SUFFIX}"))}
with open(DATA / "spherex_bins.csv") as fh:
    _bins = np.array([(float(r["wavelength_center_um"]), float(r["wavelength_width_um"])) for r in csv.DictReader(fh)])
BIN_CENTRE, BIN_WIDTH = _bins[:, 0], _bins[:, 1]
MIN_BINS = 10
MAX_CHI2_RED = 10


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
    pts = [f for f in frames
           if f["survey"] == "spherex" and not f["flagged"] and f["flux_ujy"] is not None
           and f["flux_err_ujy"] and f["flux_err_ujy"] > 0 and f["flux_ujy"] / f["flux_err_ujy"] >= 3
           and f["wavelength_um"] is not None and 1.0 <= f["wavelength_um"] <= 5.0]
    lam, flx, err = _bin(pts)
    binned = [{"wavelength_um": float(a), "flambda": float(b), "err": float(c)} for a, b, c in zip(lam, flx, err)]
    if len(lam) < MIN_BINS:
        return {"verdict": "insufficient data", "best": None, "ranking": [], "binned": binned, "template_curve": None}

    fits = []
    for label, t in TEMPLATES.items():
        m = (lam >= t[0, 0]) & (lam <= t[-1, 0])
        n = int(m.sum())
        if n < 2:
            continue
        tm = np.interp(lam[m], t[:, 0], t[:, 1])
        f, s = flx[m], err[m]
        a = np.sum(f * tm / s**2) / np.sum(tm**2 / s**2)
        chi2 = float(np.sum(((f - a * tm) / s) ** 2))
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
    return {"verdict": "match" if best["chi2_red"] <= MAX_CHI2_RED else "not consistent with ultracool dwarf templates",
            "best": best, "ranking": ranking, "binned": binned,
            "template_curve": {"label": label, "wavelength_um": t[:, 0].tolist(), "flambda": (a * t[:, 1]).tolist()}}


@router.get("/api/sequences/{sid}/spectrum")
def spectrum(sid: str):
    return classify(get_manifest(sid)["frames"])
