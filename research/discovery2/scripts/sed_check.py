"""Self-check for light from neighbours (bright hosts at 15-31"): compare the SPHEREx spectrum with the target's own
catalogue photometry. ratio_J = SPHEREx F_lambda(1.15-1.32 um) / 2MASS J (VHS J if no 2MASS), ratio_W2 = SPHEREx
F_lambda(4.4-4.8 um) / CatWISE W2, both in the same units (uJy/um^2, the /spectrum binned convention). Extra blue light
from a star raises ratio_J / ratio_W2 above the value of isolated objects. Writes out/sed_check.json.
Zero points: 2MASS J 1594 Jy at 1.235 um (Cohen+2003), VHS/MKO J 1560 Jy at 1.25 um (Tokunaga & Vacca 2005),
W2 171.787 Jy at 4.6 um (Jarrett+2011, as in backend/app/sequences.py)."""
import json
from pathlib import Path

import numpy as np
from astropy.table import Table

screen = {r["tag"]: r for r in json.loads(Path("out/screen.json").read_text())}
tm = json.loads(Path("raw/twomass_measured.json").read_text())
vhs = json.loads(Path("raw/vhs_dr5_measured.json").read_text())
cw = Table.read("raw/screen_II_365_catwise_15.ecsv")
out = {}
for tag, s in screen.items():
    p = Path("out") / tag / "summary.json"
    if not p.exists():
        continue
    b = json.loads(p.read_text())["spectrum"].get("binned") or []
    lam = np.array([x["wavelength_um"] for x in b]); f = np.array([x["flambda"] for x in b]); e = np.array([x["err"] for x in b])

    def band(lo, hi):
        m = (lam >= lo) & (lam <= hi)
        w = 1 / e[m] ** 2
        return float(np.sum(f[m] * w) / np.sum(w)), float(1 / np.sqrt(np.sum(w)))

    t = next(x for x in cw if str(x["Name"]) == s["cw_name"])
    w2 = float(t["W2mproPM"])
    j2 = (tm.get(tag) or [{}])[0].get("Jmag")
    jv = (vhs.get(tag) or [{}])[0].get("Jpmag")
    jmag, f0, lj, src = (j2, 1594.0, 1.235, "2MASS") if j2 is not None else ((float(jv), 1560.0, 1.25, "VHS") if jv else (None, None, None, None))
    sj, ej = band(1.15, 1.32)
    sw, ew = band(4.4, 4.8)
    rw = sw / (171.787e6 * 10 ** (-0.4 * w2) / 4.6**2)
    rec = {"W2": w2, "ratio_W2": round(rw, 3), "ratio_W2_err": round(ew / sw * rw, 3)}
    if jmag is not None:
        rj = sj / (f0 * 1e6 * 10 ** (-0.4 * jmag) / lj**2)
        rec.update(J=jmag, J_source=src, ratio_J=round(rj, 3), ratio_J_err=round(ej / sj * rj, 3),
                   J_over_W2=round(rj / rw, 3), J_over_W2_err=round(rj / rw * np.hypot(ej / sj, ew / sw), 3))
    out[tag] = rec
    print(tag, rec)
Path("out/sed_check.json").write_text(json.dumps(out, indent=1))
