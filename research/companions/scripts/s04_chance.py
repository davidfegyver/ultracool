"""Step 4: chance-alignment estimate per pair in out/pairs_cut.csv.
For every pair, count Gaia DR3 sources within R of the UCD (epoch 2016) that pass the SAME PM tolerance
(|dmu| < max(3 sigma_comb, 0.1 mu), approximated server side with the pair's own tolerance radius) and parallax
tolerance (Gaia Plx inside the pair's accepted parallax window). Expected false matches inside the pair separation:
N_R * (sep/3600/R)^2 (ratio of circle areas, small-angle; N excludes the host itself).
R = 1 deg; R = 0.25 deg when the PM tolerance exceeds 60 mas/yr (those 1-deg counts exceed GAVO's query time limit;
such pairs have very uncertain UCD PMs anyway).
GAVO gaia.dr3lite (CDS TAPVizieR unreachable). Writes raw/s04_query.txt, raw/s04_counts.json, out/chance.csv.
Only pairs with bound_ok == True are counted.
Run (cwd = research/companions): nice -n 15 ../../.venv/bin/python scripts/s04_chance.py"""
import csv
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pyvo


TAP_URL = "https://dc.zah.uni-heidelberg.de/tap"  # CDS TAPVizieR unreachable (raw/endpoint_probe.txt)
up = {int(r["uid"]): r for r in csv.DictReader(open("raw/ucd_upload.csv"))}
pairs = list(csv.DictReader(open("out/pairs_cut.csv")))
rows = []
for k, p in enumerate(pairs):
    u = up[int(p["uid"])]
    mu = float(u["mu"])
    tol = max(3 * float(p["dmu_sig"]), 0.1 * mu)
    gp, sgp = float(p["g_plx"]), float(p["g_eplx"])
    if p["plx_mode"] == "trig":
        c, w = float(p["ucd_plx"]), max(3 * math.hypot(sgp, float(p["ucd_plxerr"])), 0.2 * float(p["ucd_plx"]))
        lo, hi = c - w, c + w
    else:  # distance window around the photometric distance, mapped to parallax
        d, sd = float(p["ucd_dist"]), float(p["ucd_disterr"])
        w = max(3 * math.hypot(sd, (1000 / gp) * sgp / gp), 0.2 * d)
        lo, hi = 1000 / (d + w), (1000 / (d - w) if d - w > 0 else 1e4)
    rows.append([k, float(u["ra16"]), float(u["de16"]), float(u["pmra"]), float(u["pmdec"]), tol, max(lo, 0.0), hi,
                 1.0 if tol <= 60 else 0.25])
# GAVO times out on filtered upload joins (see s01), so one constant-cone COUNT per pair (q3c index, fast).
Q = """SELECT COUNT(*) AS n FROM gaia.dr3lite AS g
WHERE DISTANCE(POINT('ICRS', g.ra, g.dec), POINT('ICRS', {1}, {2})) < {8}
 AND g.parallax > {6} AND g.parallax < {7} AND SQRT(POWER(g.pmra-({3}),2)+POWER(g.pmdec-({4}),2)) < {5}"""
Path("raw/s04_query.txt").write_text(f"TAP {TAP_URL} sync, one query per pair, template (pid, ra16, de16, pmra, pmdec, tol, plo, phi):\n{Q}\n")
svc = pyvo.dal.TAPService(TAP_URL)
cache_p = Path("raw/s04_counts.json")
n = {int(k): v for k, v in json.loads(cache_p.read_text()).items()} if cache_p.exists() else {}


def count(row):
    for k in range(2):
        try:
            return row[0], [int(svc.run_sync(Q.format(*row)).to_table()["n"][0]), row[8]]
        except Exception as e:  # noqa: BLE001
            print("sync retry", row[0], repr(e)[:120], flush=True); time.sleep(5)
    for k in range(2):  # dense fields exceed the sync limit -> async
        try:
            job = svc.submit_job(Q.format(*row)); job.run()
            job.wait(phases=["COMPLETED", "ERROR", "ABORTED"], timeout=1800); job.raise_if_error()
            return row[0], [int(job.fetch_result().to_table()["n"][0]), row[8]]
        except Exception as e:  # noqa: BLE001
            print("async retry", row[0], repr(e)[:200], flush=True); time.sleep(10)
    print("FAILED pair", row[0], flush=True)
    return row[0], None


# only pairs that already pass the bound-orbit test need a chance estimate (the others are rejected anyway)
todo = [r for r in rows if n.get(r[0]) is None and pairs[r[0]]["bound_ok"] == "True"]
with ThreadPoolExecutor(4) as ex:
    for pid, c in ex.map(count, todo):
        n[pid] = c
        cache_p.write_text(json.dumps(n))
with open("out/chance.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["ucd", "gaia", "sep_arcsec", "tol_masyr", "plx_lo", "plx_hi", "cone_deg", "n_cone_incl_host", "n_field", "expected_false"])
    for k, p in enumerate(pairs):
        if n.get(k) is None:  # unbound pair (not counted) or count failed
            w.writerow([p["ucd"], p["gaia"], p["sep_arcsec"], round(rows[k][5], 1), round(rows[k][6], 3), round(rows[k][7], 3), "", "",
                        "count_failed" if p["bound_ok"] == "True" else "not_counted_unbound", "nan"])
            continue
        c, R = n[k] if isinstance(n[k], list) else (n[k], 1.0)  # early cache entries were plain 1-deg counts
        nf = max(c - 1, 0)  # minus the host itself (inside the cone, passes its own window); the UCD, if in Gaia, may still be counted
        w.writerow([p["ucd"], p["gaia"], p["sep_arcsec"], round(rows[k][5], 1), round(rows[k][6], 3), round(rows[k][7], 3), R,
                    c, nf, f"{nf * (float(p['sep_arcsec']) / 3600 / R) ** 2:.2e}"])
print("done", len(pairs))
