"""Does the SPHEREx binned spectrum reproduce the catalogue SED shape (2MASS/VHS J,H,Ks; CatWISE W1,W2)?

Run: /home/paw/Desktop/ultracool/.venv/bin/python research/verification/J2358/sed_check.py
Synthetic band flux = mean of the binned F_lambda inside a top-hat band (crude: no filter curves). Compared as ratios to J,
because our aperture photometry has no aperture correction (absolute scale is low by a PSF-dependent factor).
Zero points (Vega, F_lambda, W cm^-2 um^-1): 2MASS J/H/Ks Cohen+2003 (3.129e-13, 1.133e-13, 4.283e-14);
WISE W1/W2 Jarrett+2011 (8.1787e-15, 2.4150e-15).
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
b = json.load(open(HERE / "dev_spectrum_now.json"))["binned"]
lam = np.array([x["wavelength_um"] for x in b]); f = np.array([x["flambda"] for x in b]); s = np.array([x["err"] for x in b])
BANDS = {"J": (1.11, 1.36, 3.129e-13), "H": (1.50, 1.80, 1.133e-13), "Ks": (2.00, 2.31, 4.283e-14), "W1": (3.0, 3.9, 8.1787e-15), "W2": (4.1, 5.0, 2.4150e-15)}
CAT = {"2MASS+CatWISE": {"J": 16.279, "H": 15.526, "Ks": 14.826, "W1": 14.537, "W2": 14.200},
       "VHS+CatWISE (VISTA J,H,Ks ~ 2MASS within ~0.05-0.1 mag)": {"J": 16.104, "H": 15.539, "Ks": 15.001, "W1": 14.537, "W2": 14.200}}
out = {}
syn = {}
for k, (lo, hi, _) in BANDS.items():
    m = (lam >= lo) & (lam <= hi)
    w = 1 / s[m] ** 2
    syn[k] = (float(np.sum(w * f[m]) / np.sum(w)), float(1 / np.sqrt(np.sum(w))), int(m.sum()))
out["spherex_band_means"] = {k: [round(v[0], 2), round(v[1], 2), v[2]] for k, v in syn.items()}
for name, mags in CAT.items():
    cat = {k: BANDS[k][2] * 10 ** (-0.4 * mags[k]) for k in BANDS}
    rows = {}
    for k in BANDS:
        r_sx = syn[k][0] / syn["J"][0]
        r_cat = cat[k] / cat["J"]
        rows[k] = {"ratio_to_J_spherex": round(r_sx, 3), "ratio_to_J_catalog": round(r_cat, 3), "spherex_minus_catalog_mag": round(-2.5 * np.log10(r_sx / r_cat), 2)}
    out[name] = rows
print(json.dumps(out, indent=1))
json.dump(out, open(HERE / "sed_check_out.json", "w"), indent=1)
