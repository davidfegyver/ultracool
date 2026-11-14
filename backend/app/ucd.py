"""SPIFF ultracool-dwarf catalog (16.9k objects): search by spectral type and positional lookup."""
import csv
import re
from pathlib import Path

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from fastapi import APIRouter, HTTPException, Query

from .frames import propagate

router = APIRouter()
SPT_RE = re.compile(r"^([MLTY])(\d+(?:\.\d+)?)")
SPT_BASE = {"M": 0, "L": 10, "T": 20, "Y": 30}


def spt_num(s):
    m = SPT_RE.match(s or "")
    return SPT_BASE[m.group(1)] + float(m.group(2)) if m else None


with open(Path(__file__).parent / "data" / "ucd_catalog.csv", newline="") as fh:
    ROWS = list(csv.DictReader(fh))
COORDS = SkyCoord([r["ra_j2000"] for r in ROWS], [r["dec_j2000"] for r in ROWS], unit=(u.hourangle, u.deg))
RA, DEC = COORDS.ra.deg, COORDS.dec.deg
SPT = np.array([np.nan if (v := spt_num(r["spiff_autotype"])) is None else v for r in ROWS])
DATASETS = sorted({r["dataset"] for r in ROWS})


def _out(i):
    r = ROWS[i]
    chi2 = r["spiff_chi2_r"]
    return {"designation": r["designation"], "ra": float(RA[i]), "dec": float(DEC[i]), "dataset": r["dataset"],
            "spiff_autotype": r["spiff_autotype"], "spiff_chi2_r": float(chi2) if chi2 else None,
            "literature_spectral_type": r["literature_spectral_type"] or None}


def _parse_spt(s, name):
    if s is None:
        return None
    v = spt_num(s.strip())
    if v is None:
        raise HTTPException(400, f"Bad {name}: {s!r} (expected e.g. M7, L2.5, T5, Y1)")
    return v


@router.get("/api/ucds")
def search(spt_min: str | None = None, spt_max: str | None = None, dataset: str | None = None,
           limit: int = Query(500, ge=1, le=5000)):
    lo, hi = _parse_spt(spt_min, "spt_min"), _parse_spt(spt_max, "spt_max")
    m = np.isfinite(SPT)
    if lo is not None:
        m &= SPT >= lo
    if hi is not None:
        m &= SPT <= hi
    if dataset:
        m &= np.array([r["dataset"] == dataset for r in ROWS])
    return [_out(i) for i in np.flatnonzero(m)[:limit]]


@router.get("/api/ucds/datasets")
def datasets():
    return DATASETS


@router.get("/api/ucds/near")
def near(ra: float, dec: float, radius_arcsec: float = Query(10, gt=0, le=3600),
         pmra_masyr: float = 0.0, pmdec_masyr: float = 0.0, epoch_yr: float = 2000.0):
    """Matches within radius of the target's 2000-2026 proper-motion track: catalog positions are at
    mixed survey epochs (e.g. eps Ind B sits at its ~2010.6 position)."""
    sep = np.full(len(ROWS), np.inf)
    for t in range(2000, 2027):
        p = SkyCoord(*propagate(ra, dec, pmra_masyr, pmdec_masyr, epoch_yr, t), unit="deg")
        sep = np.minimum(sep, COORDS.separation(p).arcsec)
    idx = np.flatnonzero(sep <= radius_arcsec)
    return [{**_out(i), "sep_arcsec": float(sep[i])} for i in idx[np.argsort(sep[idx])]]
