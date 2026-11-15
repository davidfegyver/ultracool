"""Step 10: targeted VizieR (CfA asu-tsv) checks of published wide-binary compilations around the open candidates
(UCD J2000 position from UltracoolSheet, host Gaia position propagated to J2000), radius 150".
The all-catalogue cone (s07) failed with IncompleteRead on the CfA mirror, so these catalogues are queried one by one:
Galvez-Ortiz+2017 J/MNRAS/466/2983, Deacon+2014 J/ApJ/792/119, SLoWPoKES J/AJ/139/2566 + J/AJ/150/57,
SUPERWIDE J/ApJS/247/66, Smart+2019 J/MNRAS/485/4423 (table5), El-Badry+2021 J/MNRAS/506/2269 (positional, 150"),
Rothermich+2024 J/AJ/167/253, WDS B/wds/wds, Gentile Fusillo+2021 J/MNRAS/508/3877 (WD status of the hosts).
Writes raw/targeted_lit.json and prints the non-empty hits.
Run (cwd = research/companions): ../../.venv/bin/python scripts/s10_targeted_lit.py"""
import csv
import json
import math
import time
import urllib.parse
import urllib.request

VZ = "https://vizier.cfa.harvard.edu/viz-bin/asu-tsv"
CATS = ["J/MNRAS/466/2983", "J/ApJ/792/119", "J/AJ/139/2566", "J/AJ/150/57", "J/ApJS/247/66", "J/MNRAS/485/4423/table5",
        "J/MNRAS/506/2269", "J/AJ/167/253", "B/wds/wds", "J/MNRAS/508/3877/maincat"]
CANDS = ["SDSS J134338.74-022044.6", "2MASS J16002647-2456424", "2MASS J20025265-1316418", "ULAS J111929.43+002133.1",
         "ULAS J093744.66+071903.3", "ULAS J104224.20+121206.8", "PSO J130.9+030.1"]
UCS = {r["name"]: r for r in csv.DictReader(open("../discovery/ext/ultracoolsheet_v2.1.0_main.csv"))}
pairs = {r["ucd"]: r for r in csv.DictReader(open("out/survivors_all.csv"))}


def q(cat, ra, de):
    url = VZ + "?" + urllib.parse.urlencode({"-source": cat, "-c": f"{ra} {de}", "-c.rs": "150", "-out.max": "50", "-sort": "_r"})
    for k in range(4):
        try:
            txt = urllib.request.urlopen(url, timeout=180).read().decode("utf-8", "replace")
            break
        except Exception as e:  # noqa: BLE001
            print("retry", cat, repr(e)[:80]); time.sleep(10)
    else:
        return url, "FAILED"
    lines = [l for l in txt.splitlines() if l.strip() and not l.startswith("#")]
    dash = lambda l: l.startswith("-") and set(l) <= {"-", "\t", " "}  # noqa: E731
    heads = [i for i in range(len(lines) - 2) if dash(lines[i + 2])]
    rows = []
    for j, h in enumerate(heads):
        hdr = [x.strip() for x in lines[h].split("\t")]
        end = heads[j + 1] if j + 1 < len(heads) else len(lines)
        rows += [dict(zip(hdr, [v.strip() for v in l.split("\t")])) for l in lines[h + 3:end] if not dash(l)]
    return url, rows


res = {}
for name in CANDS:
    p, u = pairs[name], UCS[name]
    hra = float(p["g_ra"]) - float(p["g_pmra"]) / 3.6e6 / math.cos(math.radians(float(p["g_dec"]))) * 16
    hde = float(p["g_dec"]) - float(p["g_pmdec"]) / 3.6e6 * 16
    for who, ra, de in (("ucd", u["ra_j2000_formula"], u["dec_j2000_formula"]), ("host", hra, hde)):
        for cat in CATS:
            url, rows = q(cat, ra, de)
            res[f"{name}|{who}|{cat}"] = {"url": url, "rows": rows}
            if rows:
                print(name, who, cat, "FAILED" if rows == "FAILED" else [{k: v for k, v in r.items() if v}  for r in rows[:3]], flush=True)
json.dump(res, open("raw/targeted_lit.json", "w"), indent=1)
print("done", len(res))
