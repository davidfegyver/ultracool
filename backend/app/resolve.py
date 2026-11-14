import hashlib
import json
import math
import re
import threading
import warnings

import astropy.units as u
from astropy.coordinates import SkyCoord
from astroquery.simbad import SimbadClass, conf as simbad_conf
from fastapi import APIRouter, HTTPException

from .config import CACHE_DIR

router = APIRouter()

DEG_RE = re.compile(r"^\s*[-+]?\d+(\.\d+)?[\s,]+[-+]?\d+(\.\d+)?\s*$")
# only characters that can appear in sexagesimal coordinates, so names like "Alpha Cha" still go to SIMBAD
SEXA_RE = re.compile(r"^[\d\s:hmsd°'\"+\-.,]+$")
# CDS main site is sometimes down; the Harvard mirror serves the same TAP
SIMBAD_SERVERS = ["simbad.cds.unistra.fr", "simbad.harvard.edu"]
_simbad_lock = threading.Lock()


def _coord_result(ra: float, dec: float) -> dict:
    return {"name": None, "ra": ra, "dec": dec, "pmra_masyr": 0.0, "pmdec_masyr": 0.0,
            "epoch_yr": 2000.0, "otype": None, "sptype": None}


def _val(row, col):
    v = row[col]
    if v is None or getattr(v, "mask", False) is True:
        return None
    if isinstance(v, (bytes, str)):
        return str(v).strip() or None
    v = float(v)
    return None if math.isnan(v) else v


def _simbad(q: str) -> dict | None:
    last_err = None
    with _simbad_lock:  # conf.server is global state
        for server in SIMBAD_SERVERS:
            simbad_conf.server = server
            try:
                s = SimbadClass(timeout=30)
                s.add_votable_fields("pmra", "pmdec", "otype", "sp_type")
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    t = s.query_object(q)
            except Exception as e:  # noqa: BLE001 - try the mirror
                last_err = e
                continue
            if t is None or len(t) == 0:
                return None
            r = t[0]
            return {"name": _val(r, "main_id"), "ra": _val(r, "ra"), "dec": _val(r, "dec"),
                    "pmra_masyr": _val(r, "pmra") or 0.0, "pmdec_masyr": _val(r, "pmdec") or 0.0,
                    "epoch_yr": 2000.0, "otype": _val(r, "otype"), "sptype": _val(r, "sp_type")}
    raise HTTPException(502, f"SIMBAD unavailable: {last_err}")


def resolve(q: str) -> dict:
    q = q.strip()
    if not q:
        raise HTTPException(400, "Empty query")
    if DEG_RE.match(q):
        ra, dec = (float(x) for x in re.split(r"[\s,]+", q))
        if not (0 <= ra < 360 and -90 <= dec <= 90):
            raise HTTPException(400, f"Coordinates out of range: {q}")
        return _coord_result(ra, dec)
    if SEXA_RE.match(q):
        try:
            c = SkyCoord(q, unit=(u.hourangle, u.deg))
        except Exception:
            raise HTTPException(400, f"Cannot parse coordinates: {q}")
        return _coord_result(float(c.ra.deg), float(c.dec.deg))

    path = CACHE_DIR / "resolve" / f"{hashlib.sha1(q.lower().encode()).hexdigest()[:16]}.json"
    if path.exists():
        return json.loads(path.read_text())
    res = _simbad(q)
    if res is None:
        raise HTTPException(404, f"Object not found: {q}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(res))
    return res


@router.get("/api/resolve")
def resolve_route(q: str):
    return resolve(q)
