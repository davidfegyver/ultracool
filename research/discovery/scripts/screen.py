"""Screen SPIFF 'New Candidates' (L/T/Y, CatWISE-matched, W2 < 15.3) for bright-star / nearby-galaxy contamination.
Writes candidates_screened.csv."""
import astropy.units as u
import numpy as np
import pyvo
from astropy.coordinates import SkyCoord
from astropy.table import Table

j = Table.read("candidates_catwise.csv")
j = j[~j["w2mpro"].mask]
j = j[j["w2mpro"] < 15.3]
up = Table({"idx": j["idx"], "ra": j["ra_cw"], "dec": j["dec_cw"]})
svc = pyvo.dal.TAPService("https://simbad.harvard.edu/simbad/sim-tap")
q = """SELECT u.idx, b.main_id, b.otype, f.flux AS kmag, DISTANCE(POINT('ICRS',b.ra,b.dec),POINT('ICRS',u.ra,u.dec)) AS sep_deg
FROM basic b JOIN flux f ON f.oidref=b.oid JOIN TAP_UPLOAD.c u ON CONTAINS(POINT('ICRS',b.ra,b.dec),CIRCLE('ICRS',u.ra,u.dec,2.0))=1
WHERE f.filter='K' AND f.flux < 4"""
r = svc.run_sync(q, uploads={"c": up}).to_table()
# brightness-dependent danger radius (ghosts/halos/latents): K=-3 -> 2.4 deg, K=0 -> 0.6 deg, K=4 -> 0.1 deg
bad = {}
for x in r:
    if 0.6 * 10 ** (-0.2 * x["kmag"]) > x["sep_deg"]:
        bad.setdefault(int(x["idx"]), []).append(f"{x['main_id']} (K={x['kmag']:.1f}) at {x['sep_deg'] * 60:.0f}'")
c = SkyCoord(j["ra_cw"], j["dec_cw"], unit="deg")
gal = {"M33": (23.4621, 30.66, 0.6), "M31": (10.6847, 41.269, 2), "LMC": (80.894, -69.756, 5), "SMC": (13.187, -72.829, 3)}
allc = SkyCoord(Table.read("spiff_new_candidates_LTY.csv")["ra"], Table.read("spiff_new_candidates_LTY.csv")["dec"], unit="deg")
flags, crowd = [], []
for k in range(len(j)):
    f = [n for n, (ra, dec, rad) in gal.items() if c[k].separation(SkyCoord(ra, dec, unit="deg")).deg < rad]
    f += bad.get(int(j["idx"][k]), [])[:2]
    n = int((c[k].separation(allc) < 0.5 * u.deg).sum()) - 1  # other SPIFF candidates within 0.5 deg: overdensity = artifact field
    crowd.append(n)
    flags.append("; ".join(f))
j["contam"] = flags
j["n_cand_0p5deg"] = crowd
j["gal_b"] = c.galactic.b.deg
j.sort("w2mpro")
j.write("candidates_screened.csv", overwrite=True)
for x in j:
    print(f"{x['designation']:28s} {x['spiff_autotype']:10s} W2={x['w2mpro']:.2f} W1-W2={x['w1_w2']:.2f} "
          f"pm=({x['pmra'] * 1000:.0f},{x['pmdec'] * 1000:.0f}) {x['pm_sig']:.0f}sig nb={x['nb']} ab={x['ab_flags']} b={x['gal_b']:.0f} "
          f"crowd={x['n_cand_0p5deg']} | {x['contam']}")
