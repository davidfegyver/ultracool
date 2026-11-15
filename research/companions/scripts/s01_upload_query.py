"""Step 1: UltracoolSheet v2.1.0 UCDs with |pm| >= 50 mas/yr and a distance -> TAP upload join against
Gaia DR3 within 120" of the UCD position propagated to Gaia epoch 2016.0.
CDS TAPVizieR / XMatch timed out from this host on 2026-11-15 (raw/endpoint_probe.txt), so the GAVO Heidelberg
mirror gaia.dr3lite (full Gaia DR3 source list, astrometry + photometry columns) is used; column aliases match VizieR.
All cuts (PM, parallax, separation) are applied locally in s02_cuts.py.
Writes raw/ucd_upload.csv, raw/gaia_pairs_raw.csv, raw/s01_query.txt.
Run (cwd = research/companions): nice -n 15 ../../.venv/bin/python scripts/s01_upload_query.py"""
import csv
import math
import time
from pathlib import Path

import pyvo
from astropy.table import Table, vstack

UCS = Path("../discovery/ext/ultracoolsheet_v2.1.0_main.csv")
TAP_URL = "https://dc.zah.uni-heidelberg.de/tap"
DT = 2016.0 - 2025.5027  # UCS ra/dec_20250703_formula epoch (2025-07-03 = 2025.5027) -> Gaia DR3 epoch


def f(x):
    try:
        v = float(x)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None


rows = []
for i, r in enumerate(csv.DictReader(open(UCS))):
    pa, pd, ra, de = f(r["pmra_formula"]), f(r["pmdec_formula"]), f(r["ra_20250703_formula"]), f(r["dec_20250703_formula"])
    dist = f(r["dist_formula"])
    if None in (pa, pd, ra, de, dist) or math.hypot(pa, pd) < 50 or dist <= 0:
        continue
    rows.append(dict(uid=i, ra16=ra + pa / 3.6e6 / math.cos(math.radians(de)) * DT, de16=de + pd / 3.6e6 * DT,
                     pmra=pa, pmdec=pd, mu=math.hypot(pa, pd), plxu=1000.0 / dist))
print("UCDs uploaded:", len(rows))
t = Table(rows=[[r[k] for k in rows[0]] for r in rows], names=list(rows[0]))
t.write("raw/ucd_upload.csv", overwrite=True)

q = """SELECT u.uid, g.source_id AS Source, g.ra AS RA_ICRS, g.dec AS DE_ICRS, g.parallax AS Plx, g.parallax_error AS e_Plx,
 g.pmra AS pmRA, g.pmra_error AS e_pmRA, g.pmdec AS pmDE, g.pmdec_error AS e_pmDE,
 g.phot_g_mean_mag AS Gmag, g.phot_bp_mean_mag AS BPmag, g.phot_rp_mean_mag AS RPmag, g.ruwe AS RUWE,
 g.radial_velocity AS RV, g.radial_velocity_error AS e_RV,
 DISTANCE(POINT('ICRS', g.ra, g.dec), POINT('ICRS', u.ra16, u.de16))*3600 AS sep
FROM TAP_UPLOAD.ucd AS u JOIN gaia.dr3lite AS g
 ON DISTANCE(POINT('ICRS', g.ra, g.dec), POINT('ICRS', u.ra16, u.de16)) < 120.0/3600"""
# GAVO times out (sync ~20 s) as soon as PM/parallax filters are added to the join, so the join is spatial only, in
# chunks of 300 UCDs, and every cut is applied locally (s02_cuts.py).
Path("raw/s01_query.txt").write_text(f"TAP {TAP_URL} (sync, chunks of 300 upload rows)\nupload raw/ucd_upload.csv as TAP_UPLOAD.ucd\n{q}\n")
svc = pyvo.dal.TAPService(TAP_URL)
parts = []
for i0 in range(0, len(t), 300):
    for k in range(4):
        try:
            t0 = time.time()
            parts.append(svc.run_sync(q, uploads={"ucd": t[i0:i0 + 300]}, maxrec=2000000).to_table())
            print(i0, len(parts[-1]), round(time.time() - t0, 1), flush=True)
            break
        except Exception as e:  # noqa: BLE001
            print("retry", i0, repr(e)[:300], flush=True); time.sleep(20)
    else:
        raise SystemExit(f"TAP failed at chunk {i0}")
res = vstack(parts)
for c, n in zip(res.colnames, ["uid", "Source", "RA_ICRS", "DE_ICRS", "Plx", "e_Plx", "pmRA", "e_pmRA", "pmDE", "e_pmDE",
                               "Gmag", "BPmag", "RPmag", "RUWE", "RV", "e_RV", "sep"]):
    if c != n:
        res.rename_column(c, n)
res.write("raw/gaia_pairs_raw.csv", overwrite=True)
print("rows:", len(res))
