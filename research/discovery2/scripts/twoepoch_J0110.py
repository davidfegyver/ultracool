"""Pipeline-independent two-epoch PM for J0110-5926 (no 2MASS or Gaia counterpart): AllWISE (II/328, positions at the
mean AllWISE epoch, MJD ~55400 = 2010.56) -> VHS DR5 (II/367, J-band MJD 56514.308). Same method as the J2317 review
(research/verification/recompute.py, AllWISE->VHS). Row values copied from the CfA VizieR query logged in REPORT.md.
Writes out/J0110-5926/twoepoch_pm.json."""
import json
import math
from pathlib import Path

from scipy.stats import chi2

aw = (17.5145646, -59.4477121, 0.1054, 0.1045, 55400.0)  # RA, Dec, e_RA_pm, e_DE_pm (arcsec), MJD (AllWISE mean epoch, assumed)
vhs = (17.514813, -59.44759, 0.1, 56514.308233)  # VHS per-source astrometric error 0.1" assumed (not in the VizieR row), J MJD
host = (212.992, 0.970, 167.559, 0.943)  # Gaia DR3 4909222871450620416 (out/hosts.json)
dt = (vhs[3] - aw[4]) / 365.25
pa = (vhs[0] - aw[0]) * math.cos(math.radians(aw[1])) * 3.6e6 / dt
pd = (vhs[1] - aw[1]) * 3.6e6 / dt
ea, ed = math.hypot(aw[2], vhs[2]) * 1000 / dt, math.hypot(aw[3], vhs[2]) * 1000 / dt
da, dd = pa - host[0], pd - host[2]
c2 = (da / math.hypot(ea, host[1])) ** 2 + (dd / math.hypot(ed, host[3])) ** 2
out = {"dt_yr": round(dt, 2), "pmra": round(pa, 1), "pmdec": round(pd, 1), "err": [round(ea, 1), round(ed, 1)], "dmu": [round(da, 1), round(dd, 1)],
       "chi2_2dof": round(c2, 2), "p_value": round(float(chi2.sf(c2, 2)), 3)}
Path("out/J0110-5926/twoepoch_pm.json").write_text(json.dumps(out, indent=1))
print(out)
