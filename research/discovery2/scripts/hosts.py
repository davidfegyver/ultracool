"""Host-star astrometry for the measured candidates: SIMBAD (Harvard TAP) position of the host named in Rothermich+24,
then the Gaia DR3 source (VizieR I/355/gaiadr3, CfA mirror) nearest to it (within 3"), with PM, parallax, errors, G, RUWE.
Also the target's own Gaia DR3 counterpart (if any) within 2" of the CatWISE position.
Writes out/hosts.json. Usage: python scripts/hosts.py <tag> ...   (cwd = research/discovery2)"""
import json
import sys
import time
from pathlib import Path

import astropy.units as u
import pyvo
import numpy as np
from astropy.coordinates import SkyCoord
from astroquery.vizier import Vizier

TAP = pyvo.dal.TAPService("https://simbad.harvard.edu/simbad/sim-tap")
viz = Vizier(columns=["Source", "RA_ICRS", "DE_ICRS", "Plx", "e_Plx", "pmRA", "e_pmRA", "pmDE", "e_pmDE", "Gmag", "BPmag", "RPmag", "RUWE", "RV", "e_RV", "_r"], row_limit=-1)
viz.VIZIER_SERVER = "vizier.cfa.harvard.edu"
screen = {r["tag"]: r for r in json.loads(Path("out/screen.json").read_text())}
p = Path("out/hosts.json")
out = json.loads(p.read_text()) if p.exists() else {}


def gaia(ra, dec, rad):
    for k in range(3):
        try:
            t = viz.query_region(SkyCoord(ra, dec, unit="deg"), radius=rad * u.arcsec, catalog="I/355/gaiadr3")
            return [] if not t else [{c: (None if np.ma.is_masked(r[c]) else (r[c].item() if hasattr(r[c], "item") else r[c])) for c in t[0].colnames} for r in t[0]]
        except Exception as e:  # noqa: BLE001
            print("retry", e); time.sleep(15)
    raise SystemExit("VizieR failed")


for tag in sys.argv[1:]:
    s = screen[tag]
    host = s["host"].split(" [")[0].split(" (")[0]
    q = TAP.run_sync(f"SELECT b.main_id, b.ra, b.dec, b.plx_value, b.pmra, b.pmdec, b.sp_type, b.rvz_radvel FROM basic b JOIN ident i ON i.oidref=b.oid WHERE i.id='{host}'").to_table()
    sim = {k: (v.item() if hasattr(v, "item") else v) for k, v in zip(q.colnames, q[0])} if len(q) else None
    rec = {"host_query": host, "simbad": sim}
    # host position: SIMBAD, else the J2000 coordinates in a WDJ/RX-style name (Gentile Fusillo+21 WDJ names are J2000, ep. 2000)
    if sim:
        hra, hdec = sim["ra"], sim["dec"]
    else:
        import re
        m = re.search(r"J(\d\d)(\d\d)(\d\d\.\d+)([+-]\d\d)(\d\d)(\d\d\.\d+)", host)
        hc = SkyCoord(f"{m[1]}h{m[2]}m{m[3]}s {m[4]}d{m[5]}m{m[6]}s") if m else None
        hra, hdec = (hc.ra.deg, hc.dec.deg) if hc is not None else (None, None)
    # 20" cone (16 yr of motion for the fastest hosts); the host is the source whose parallax matches Rothermich's (Gaia DR3)
    if hra is not None and s.get("host_plx") not in (None, ""):
        g = [r for r in gaia(hra, hdec, 20) if r["Plx"] is not None]
        rec["host_gaia_dr3"] = min(g, key=lambda r: abs(r["Plx"] - float(s["host_plx"]))) if g else None
    rec["host_position_used"] = [hra, hdec]
    rec["target_gaia_dr3"] = sorted(gaia(s["ra"], s["dec"], 2), key=lambda r: r["_r"])
    out[tag] = rec
    p.write_text(json.dumps(out, indent=1, default=str))
    h = rec.get("host_gaia_dr3") or {}
    print(tag, host, "| SIMBAD", sim and (sim["main_id"], sim["plx_value"], sim["pmra"], sim["pmdec"]), "| Gaia", h.get("Source"), h.get("Plx"), h.get("pmRA"), h.get("pmDE"), h.get("RUWE"),
          "| target Gaia", [(r["Source"], r["Gmag"], r["Plx"], r["pmRA"], r["pmDE"]) for r in rec["target_gaia_dr3"]])
