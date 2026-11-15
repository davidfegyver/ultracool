"""Step 9: derived numbers quoted in REPORT.md for the open candidates (inputs copied from out/pairs_cut.csv,
raw/selfcheck/*.json, raw/astrom/J1119_fit.txt, raw/gf21_masses.json). Run: ../../.venv/bin/python scripts/s09_numbers.py"""
import json
import math

K = 4.74047


def dv(d_pc, a1, d1, a2, d2, e):
    dmu = math.hypot(a1 - a2, d1 - d2)
    return round(dmu, 2), round(K * dmu / 1000 * d_pc, 2), round(K * e / 1000 * d_pc, 2)


def vesc(m, au):
    return round(29.7847 * math.sqrt(2 * m / au), 2)


gf = json.load(open("raw/gf21_masses.json"))
out = {}
# J1343: host Gaia DR3 3658413770767688192 plx 12.0064 -> 83.29 pc; UCD PM Best18 (-139,121)+-5; 2MASS->Gaia (-129.8,120.4)+-9.5
d = 1000 / 12.0064
out["J1343_dist_pc"] = round(d, 2)
out["J1343_dv_Best18"] = dv(d, -139.0, 121.0, -140.719, 122.140, 5.0)
out["J1343_dv_2MASS_Gaia"] = dv(d, -129.8, 120.4, -140.719, 122.140, 9.5)
out["J1343_dv_multiepoch_s08"] = dv(d, -140.0, 120.8, -140.719, 122.140, 3.5)  # raw/astrom/multiepoch_fit.txt
out["J1343_dv_CatWISE_UCS"] = dv(d, -141.1, 133.2, -140.719, 122.140, 11.5)
out["J1343_vtan_host"] = round(K * math.hypot(-140.719, 122.140) / 1000 * d, 1)
out["J1343_vesc_0.6+0.08"] = vesc(0.68, 3676)
# J1119: host plx 14.5324 -> 68.81 pc; our 4-epoch fit (4.7,-37.3)+-13.3; Best18 (24,-55)+-15; CatWISE via UCS (-28,-43)+-16
d = 1000 / 14.5324
out["J1119_dist_pc"] = round(d, 2)
out["J1119_dv_ourfit"] = dv(d, 4.7, -37.3, 18.330, -59.414, 13.3)
out["J1119_dv_Best18"] = dv(d, 24.0, -55.0, 18.330, -59.414, 15.0)
out["J1119_dv_CatWISE_UCS"] = dv(d, -28.0, -43.0, 18.330, -59.414, 16.0)
out["J1119_vesc"] = vesc(0.3 + 0.08, 963)  # host M_G 10.55 -> Mamajek mass in out/pairs_cut.csv (~0.3)
# J1600: WD Gaia DR3 6236113362117992832 plx 16.4327+-0.3044; UCD 6236089829993254784 plx 17.7749 (CfA re-query)
out["J1600_dist_WD_pc"] = round(1000 / 16.4327, 2)
out["J1600_dist_UCD_pc"] = round(1000 / 17.7749, 2)
out["J1600_vtan_WD"] = round(K * math.hypot(-38.4226, -293.8000) / 1000 * 1000 / 16.4327, 1)
out["J1600_GF21"] = gf.get("6236113362117992832")
# J2002: host 6879016158977270784 plx 17.8627+-0.2144; UCD 6879015888398994944 plx 15.7132 (+-0.7 UCS)
out["J2002_plx_diff_sigma"] = round((17.8627 - 15.7132) / math.hypot(0.2144, 0.7), 2)
print(json.dumps(out, indent=1))
