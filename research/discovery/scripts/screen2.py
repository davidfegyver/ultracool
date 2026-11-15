"""Second-pass screen (2026-11-14 night) of the untested SPIFF 'New Candidates' (L/T/Y) and SIMBAD 'BD?' objects without
spectral type, using the CatWISE2020 matches already on disk (candidates_catwise.csv, simbad_bdq_not_in_spiff_catwise.csv).
Cuts: |b| > 20 deg, W2 < 15.5, CatWISE PM >= 0.15"/yr and >= 5 sigma, W1-W2 >= 1.0, ab_flags == '00',
not within 1.5 deg of IRC+10216 / 1 deg of RW LMi, not in M31/M33/LMC/SMC, not already verified (out/*.json).
Bright-star (W2 < 8 within 3') check is done separately (bright.py) on the survivors. Writes screen2_pass.csv."""
import csv
import math
from pathlib import Path

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord

AVOID = {"IRC+10216": (146.98917, 13.27877, 1.5), "RW LMi": (154.00949, 30.57196, 1.0), "M33": (23.4621, 30.66, 0.8),
         "M31": (10.6847, 41.269, 2.0), "LMC": (80.894, -69.756, 6.0), "SMC": (13.187, -72.829, 3.0)}
import json
pos = [json.loads(p.read_text())["input"] for p in Path("out").glob("*.json")]
done = SkyCoord([i["ra"] for i in pos], [i["dec"] for i in pos], unit="deg")


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return math.nan


rows = []
for r in csv.DictReader(open("candidates_catwise.csv")):
    sig = math.hypot(f(r["sigpmra"]), f(r["sigpmdec"])) / math.sqrt(2)
    rows.append({"src": "SPIFF NC", "name": r["designation"], "ra": f(r["ra_cw"]), "dec": f(r["dec_cw"]), "spiff": r["spiff_autotype"],
                 "w1": f(r["w1mpro"]), "w2": f(r["w2mpro"]), "pmra": f(r["pmra"]) * 1000, "pmdec": f(r["pmdec"]) * 1000,
                 "pm_err": sig * 1000, "ab": r["ab_flags"], "cc": r["cc_flags"], "nb": r["nb"], "cw": r["source_name"]})
for r in csv.DictReader(open("simbad_bdq_not_in_spiff_catwise.csv")):
    if not r["source_name"]:
        continue
    rows.append({"src": "SIMBAD BD?", "name": r["main_id"], "ra": f(r["ra"]), "dec": f(r["dec"]), "spiff": "",
                 "w1": f(r["w1mpro"]), "w2": f(r["w2mpro"]), "pmra": f(r["pmra_2"]) * 1000, "pmdec": f(r["pmdec_2"]) * 1000,
                 "pm_err": f(r["sigpmra"]) * 1000,  # this file lacks sigpmdec; re-queried for the short list
                 "ab": r["ab_flags"], "cc": "", "nb": r["nb"], "cw": r["source_name"]})
n_unmatched = sum(math.isnan(r["ra"]) or math.isnan(r["w2"]) for r in rows)
rows = [r for r in rows if not (math.isnan(r["ra"]) or math.isnan(r["w2"]))]
print("dropped (no CatWISE match / no W2):", n_unmatched)
c = SkyCoord([r["ra"] for r in rows], [r["dec"] for r in rows], unit="deg")
b = c.galactic.b.deg
near_done = c.match_to_catalog_sky(done)[1].arcsec < 20
avoid = {k: c.separation(SkyCoord(ra, dec, unit="deg")).deg < rad for k, (ra, dec, rad) in AVOID.items()}
counts = {}
out = []
for k, r in enumerate(rows):
    r["gal_b"] = round(float(b[k]), 1)
    r["pm"] = math.hypot(r["pmra"], r["pmdec"])
    r["pm_sig"] = r["pm"] / r["pm_err"] if r["pm_err"] > 0 else 0
    r["w1_w2"] = r["w1"] - r["w2"]
    tests = [("|b|>20", abs(b[k]) > 20), ("W2<15.5", r["w2"] < 15.5), ("PM>=0.15", r["pm"] >= 150), ("PM>=5sig", r["pm_sig"] >= 5),
             ("W1-W2>=1", r["w1_w2"] >= 1.0 or (math.isnan(r["w1"]) and r["w2"] < 15.5)), ("ab=00", r["ab"] == "00"),
             ("not tested", not near_done[k]), ("not avoid", not any(v[k] for v in avoid.values()))]
    r["fails"] = "; ".join(t for t, ok in tests if not ok)
    first = next((t for t, ok in tests if not ok), None)
    if first:
        counts[first] = counts.get(first, 0) + 1
    else:
        out.append(r)
# near misses: exactly one failed cut, and that cut is a soft magnitude/kinematic one missed by a small margin
SOFT = {"|b|>20": lambda r: abs(r["gal_b"]) > 15, "W2<15.5": lambda r: r["w2"] < 15.8, "PM>=0.15": lambda r: r["pm"] >= 100,
        "W1-W2>=1": lambda r: r["w1_w2"] >= 0.8}
near = [r for r in rows if r.get("fails") in SOFT and SOFT[r["fails"]](r)]
with open("screen2_all.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, ["src", "name", "cw", "ra", "dec", "gal_b", "spiff", "w1", "w2", "w1_w2", "pmra", "pmdec", "pm", "pm_err",
                            "pm_sig", "ab", "cc", "nb", "fails"], extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
print("near misses (one soft cut, small margin):")
for r in sorted(near, key=lambda r: r["w2"]):
    print(f"  NEAR {r['src']:10s} {r['name'][:30]:30s} {r['spiff']:8s} W2={r['w2']:.2f} W1-W2={r['w1_w2']:.2f} pm={r['pm']:.0f} ({r['pm_sig']:.0f}s) b={r['gal_b']} ab={r['ab']} fails={r['fails']}")
# de-duplicate (same CatWISE source from both lists)
seen, uniq = set(), []
for r in out:
    if r["cw"] not in seen:
        seen.add(r["cw"]); uniq.append(r)
print("input", len(rows), "first failing cut:", counts, "pass", len(uniq))
keys = ["src", "name", "cw", "ra", "dec", "gal_b", "spiff", "w1", "w2", "w1_w2", "pmra", "pmdec", "pm", "pm_err", "pm_sig", "ab", "cc", "nb"]
uniq.sort(key=lambda r: r["w2"])
with open("screen2_pass.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, keys, extrasaction="ignore")
    w.writeheader()
    w.writerows(uniq)
for r in uniq:
    print(f"{r['src']:10s} {r['name'][:30]:30s} {r['spiff']:8s} W2={r['w2']:.2f} W1-W2={r['w1_w2']:.2f} pm={r['pm']:.0f} ({r['pm_sig']:.0f}s) b={r['gal_b']} cc={r['cc']} nb={r['nb']}")
# short list for vetting: strict passes + near misses; W2 < 8 rows dropped (a companion whose CatWISE match is its
# bright host star: HD 12894B, HD 33473C), the SPHEREx/WISE photometry there measures the host
short = [dict(r, tier="pass") for r in uniq if r["w2"] >= 8] + [dict(r, tier="near") for r in sorted(near, key=lambda r: r["w2"]) if r["w2"] >= 8]
with open("screen2_shortlist_in.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, keys + ["tier", "fails"], extrasaction="ignore")
    w.writeheader()
    w.writerows(short)
print("short list", len(short))
