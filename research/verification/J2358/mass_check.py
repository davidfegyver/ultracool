"""Star or brown dwarf? Interpolate BHAC15 (Baraffe+2015) isochrones at the UCD's M_Ks / M_J (host parallax) and Teff.

Run: /home/paw/Desktop/ultracool/.venv/bin/python research/verification/J2358/mass_check.py
Input: BHAC15_iso.2mass (http://perso.ens-lyon.fr/isabelle.baraffe/BHAC15dir/BHAC15_iso.2mass, saved here).
UCD: 2MASS Ks 14.826 +- 0.124, J 16.279 +- 0.119; host parallax 12.8445 mas; Teff 2295 +- 256 K (Gaia ESP-UCD) and
~2270 K (Pecaut & Mamajek L0V). Hydrogen-burning limit in BHAC15 ~0.07-0.075 Msun.
shortcut: dust-free BHAC15 atmospheres are rough near L0; DUSTY/Saumon-Marley tracks would refine masses.
"""
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
iso, age = {}, None
for line in open(HERE / "BHAC15_iso.2mass"):
    if "t (Gyr)" in line:
        age = float(line.split("=")[1])
        iso[age] = []
    elif age is not None and line.strip() and not line.startswith("!"):
        iso[age].append([float(x) for x in line.split()])
DM = 5 * math.log10(100 / 12.8445)
MK, MJ = 14.826 - DM, 16.279 - DM
out = {"M_Ks": round(MK, 2), "M_J": round(MJ, 2)}
for a in (0.1, 0.2, 0.3, 0.5, 0.8, 1.0, 2.0, 5.0, 10.0):
    t = np.array(iso[min(iso, key=lambda x: abs(x - a))])
    m, teff, mj, mk = t[:, 0], t[:, 1], t[:, 6], t[:, 8]
    o = {}
    for lab, x, col in (("from_M_Ks", MK, mk), ("from_M_J", MJ, mj), ("from_Teff2295", 2295, teff), ("from_Teff2039", 2039, teff), ("from_Teff2551", 2551, teff)):
        order = np.argsort(col)
        o[lab] = round(float(np.interp(x, col[order], m[order])), 3) if col.min() <= x <= col.max() else "outside grid"
    out[f"{a} Gyr (iso {min(iso, key=lambda x: abs(x - a))})"] = o
print(json.dumps(out, indent=1))
json.dump(out, open(HERE / "mass_check_out.json", "w"), indent=1)
