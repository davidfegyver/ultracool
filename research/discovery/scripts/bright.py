"""Short-list vetting from VizieR (CfA mirror; not IRSA, which the field runs use): for each row of screen2_shortlist_in.csv:
CatWISE2020 (II/365/catwise) within 5" (full PM errors, ab/cc flags) and AllWISE (II/328/allwise)
stars with W2 < 8 within 3'. Writes shortlist_vetted.csv."""
import csv
import math
import time

import astropy.units as u
from astropy.coordinates import SkyCoord
from astroquery.vizier import Vizier

SRV = "vizier.cfa.harvard.edu"  # CDS viz-bin/votable answers 404 tonight
V = Vizier(columns=["**", "_r"], row_limit=-1, timeout=120, vizier_server=SRV)
rows = list(csv.DictReader(open("screen2_shortlist_in.csv")))
out = []
for r in rows:
    c = SkyCoord(float(r["ra"]), float(r["dec"]), unit="deg")
    for k in range(3):
        try:
            cw = V.query_region(c, radius=12 * u.arcsec, catalog="II/365/catwise")  # SIMBAD J2000 vs CatWISE 2015.4: up to ~9" at 0.6"/yr
            bw = Vizier(columns=["AllWISE", "RAJ2000", "DEJ2000", "W2mag"], column_filters={"W2mag": "<8"}, row_limit=-1, timeout=120, vizier_server=SRV,
                        ).query_region(c, radius=3 * u.arcmin, catalog="II/328/allwise")
            break
        except Exception as e:  # noqa: BLE001
            print("retry", r["name"], e); time.sleep(5)
    t = cw[0] if len(cw) else None
    if t is not None:
        t.sort("_r")
        x = t[0]
        # VizieR CatWISE PMs are in arcsec/yr
        pmra, pmde, e1, e2 = (1000 * float(x[k]) for k in ("pmRA", "pmDE", "e_pmRA", "e_pmDE"))
        pm = math.hypot(pmra, pmde)
        pm_err = math.hypot(pmra * e1, pmde * e2) / pm
        r.update(cw_name=str(x["Name"]), cw_sep=round(c.separation(SkyCoord(x["RA_ICRS"], x["DE_ICRS"], unit="deg")).arcsec, 2), cw_pmra=pmra, cw_pmdec=pmde,
                 cw_e_pmra=e1, cw_e_pmdec=e2, cw_pm=round(pm, 1), cw_pm_sig=round(pm / pm_err, 1), cw_ab=str(x["abf"]), cw_cc=str(x["ccf"]),
                 cw_w1=float(x["W1mproPM"]), cw_w2=float(x["W2mproPM"]), cw_ra=float(x["RA_ICRS"]), cw_dec=float(x["DE_ICRS"]),
                 cw_mjd=float(x["MJD"]), cw_n_within_12=len(t))
    b = bw[0] if len(bw) else []
    r["bright_w2lt8_3arcmin"] = "; ".join(f"{s['AllWISE']} W2={float(s['W2mag']):.1f} at {c.separation(SkyCoord(s['RAJ2000'], s['DEJ2000'], unit='deg')).arcsec:.0f}\"" for s in b)
    out.append(r)
    print(r["name"], r.get("cw_name"), r.get("cw_pm"), r.get("cw_pm_sig"), r.get("cw_ab"), r.get("cw_cc"), "| bright:", r["bright_w2lt8_3arcmin"] or "none")
keys = list(dict.fromkeys(k for r in out for k in r))
with open("shortlist_vetted.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, keys)
    w.writeheader()
    w.writerows(out)
