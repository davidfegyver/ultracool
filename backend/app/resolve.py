import hashlib
import io
import json
import logging
import math
import re
import threading
import warnings

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io.votable import parse_single_table
from astroquery.simbad import SimbadClass, conf as simbad_conf
from fastapi import APIRouter, HTTPException

from .config import CACHE_DIR
from .sources import irsa_gator

log = logging.getLogger("ultracool.resolve")

router = APIRouter()

DEG_RE = re.compile(r"^\s*[-+]?\d+(\.\d+)?[\s,]+[-+]?\d+(\.\d+)?\s*$")
# only characters that can appear in sexagesimal coordinates, so names like "Alpha Cha" still go to SIMBAD
SEXA_RE = re.compile(r"^[\d\s:hmsd°'\"+\-.,]+$")
# CDS main site is sometimes down; the Harvard mirror serves the same TAP
SIMBAD_SERVERS = ["simbad.cds.unistra.fr", "simbad.harvard.edu"]
_simbad_lock = threading.Lock()
# survey designations encode the position: CWISE J201121.52-062438.1 -> 20:11:21.52 -06:24:38.1
DESIG_RE = re.compile(r"\bJ(\d{2})(\d{2})(\d{2}(?:\.\d+)?)([+-])(\d{2})(\d{2})(\d{2}(?:\.\d+)?)\b")
CATWISE_EPOCH_YR = 2015.4  # CatWISE2020 positions are at MJD 57170
# epoch of the position a designation encodes, by survey prefix (WISE/AllWISE: ~2010.5; others: J2000)
DESIG_EPOCH_YR = {"CWISE": CATWISE_EPOCH_YR, "CWISEP": CATWISE_EPOCH_YR, "WISEA": 2010.5, "WISE": 2010.5}
CATWISE_MATCH_ARCSEC = 6.0
RESOLVE_CACHE_VERSION = "v2"  # v2: CatWISE proper-motion fallback


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
            if _val(r, "ra") is None:  # SIMBAD returns a fully masked row for some unknown names
                return None
            return {"name": _val(r, "main_id"), "ra": _val(r, "ra"), "dec": _val(r, "dec"),
                    "pmra_masyr": _val(r, "pmra") or 0.0, "pmdec_masyr": _val(r, "pmdec") or 0.0,
                    "epoch_yr": 2000.0, "otype": _val(r, "otype"), "sptype": _val(r, "sp_type")}
    raise HTTPException(502, f"SIMBAD unavailable: {last_err}")


def parse_designation(q: str) -> dict | None:
    """Position encoded in a survey designation ('CWISE J201121.52-062438.1') -> resolve dict, or None."""
    m = DESIG_RE.search(q)
    if not m:
        return None
    hh, mm, ss, sign, dd, dm, ds = m.groups()
    c = SkyCoord(f"{hh}h{mm}m{ss}s {sign}{dd}d{dm}m{ds}s")
    prefix = q[:m.start()].strip().upper()
    return {**_coord_result(float(c.ra.deg), float(c.dec.deg)), "name": q,
            "epoch_yr": DESIG_EPOCH_YR.get(prefix, 2000.0)}


def _catwise_motion(ra: float, dec: float, radius_arcsec: float) -> dict | None:
    """Nearest CatWISE2020 source with a significant (> 3 sigma) proper motion: its position at the CatWISE
    epoch and its motion, or None (static or noisy motions would only move the target off its SIMBAD place)."""
    data = irsa_gator("catwise_2020", ra, dec, radius_arcsec,
                      ["source_name", "ra", "dec", "pmra", "pmdec", "sigpmra", "sigpmdec"])
    t = parse_single_table(io.BytesIO(data)).to_table()
    if len(t) == 0:
        return None
    sep = SkyCoord(np.asarray(t["ra"], float), np.asarray(t["dec"], float), unit="deg").separation(
        SkyCoord(ra, dec, unit="deg"))
    r = t[int(np.argmin(sep))]
    pm, err = math.hypot(float(r["pmra"]), float(r["pmdec"])), math.hypot(float(r["sigpmra"]), float(r["sigpmdec"]))
    if not (math.isfinite(pm) and math.isfinite(err) and pm > 3 * err):
        return None
    return {"ra": float(r["ra"]), "dec": float(r["dec"]), "epoch_yr": CATWISE_EPOCH_YR,
            "pmra_masyr": float(r["pmra"]) * 1000, "pmdec_masyr": float(r["pmdec"]) * 1000,
            "pm_source": f"CatWISE2020 {str(r['source_name']).strip()}"}


def _with_catwise_motion(res: dict) -> dict:
    """Fill a missing proper motion from CatWISE (SIMBAD lacks it for many WISE-discovered brown dwarfs);
    the position is then CatWISE's, at its own epoch, so the propagation stays self-consistent.
    Only for stars, brown-dwarf candidates and bare designations: CatWISE motions of galaxy cores are
    spurious (M31's nucleus has a '3 sigma' 0.29"/yr)."""
    otype = res.get("otype")
    if res["pmra_masyr"] or res["pmdec_masyr"] or not (otype is None or "*" in otype or otype in {"BD?", "LM?"}):
        return res
    try:
        cw = _catwise_motion(res["ra"], res["dec"], CATWISE_MATCH_ARCSEC)
    except Exception as e:  # noqa: BLE001 - IRSA down: keep the static position rather than fail the lookup
        log.warning("CatWISE proper-motion lookup failed for %s: %s", res.get("name"), e)
        return res
    return {**res, **cw} if cw else res


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

    path = CACHE_DIR / "resolve" / f"{hashlib.sha1((RESOLVE_CACHE_VERSION + q.lower()).encode()).hexdigest()[:16]}.json"
    if path.exists():
        return json.loads(path.read_text())
    res = _simbad(q) or parse_designation(q)
    if res is None:
        raise HTTPException(404, f"Object not found: {q}")
    res = _with_catwise_motion(res)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(res))
    return res


@router.get("/api/resolve")
def resolve_route(q: str):
    return resolve(q)
