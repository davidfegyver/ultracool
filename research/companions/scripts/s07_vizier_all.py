"""Step 7: all-catalogue VizieR cone (CfA mirror asu-tsv, no -source) around each candidate UCD (UltracoolSheet J2000
position, 10") and host (Gaia 2016 position propagated to J2000 with Gaia PM, 10"); lists which catalogues contain each object.
Saves raw/vizier_all/<tag>_{ucd,host}.tsv and prints catalogue names (+ titles) per object.
Run (cwd = research/companions): ../../.venv/bin/python scripts/s07_vizier_all.py"""
import csv
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

VZ = "https://vizier.cfa.harvard.edu/viz-bin/asu-tsv"
OUT = Path("raw/vizier_all")
OUT.mkdir(parents=True, exist_ok=True)
# J2354 (done first, 2026-11-15 08:24) is handled by Main's separate agent; one query takes ~5-15 min on the CfA mirror
CANDS = ["SDSS J134338.74-022044.6", "2MASS J16002647-2456424", "ULAS J111929.43+002133.1", "2MASS J20025265-1316418"]
UCS = {r["name"]: r for r in csv.DictReader(open("../discovery/ext/ultracoolsheet_v2.1.0_main.csv"))}
pairs = {r["ucd"]: r for r in csv.DictReader(open("out/survivors_all.csv"))}


def fetch(ra, de, path):
    url = VZ + "?" + urllib.parse.urlencode({"-c": f"{ra} {de}", "-c.rs": "10", "-out.max": "20"})
    for k in range(4):
        try:
            txt = urllib.request.urlopen(url, timeout=300).read().decode("utf-8", "replace")
            path.write_text(f"# {url}\n" + txt)
            return txt
        except Exception as e:  # noqa: BLE001
            print("retry", repr(e)[:100]); time.sleep(15)
    return ""


for name in CANDS:
    p, u = pairs[name], UCS[name]
    tag = re.sub(r"[^\w+-]", "_", name)
    dt = 2000.0 - 2016.0
    import math
    hra = float(p["g_ra"]) + float(p["g_pmra"]) / 3.6e6 / math.cos(math.radians(float(p["g_dec"]))) * dt
    hde = float(p["g_dec"]) + float(p["g_pmdec"]) / 3.6e6 * dt
    for who, ra, de in (("ucd", u["ra_j2000_formula"], u["dec_j2000_formula"]), ("host", hra, hde)):
        txt = fetch(ra, de, OUT / f"{tag}_{who}.tsv")
        hits = []  # (table, n rows) for tables that actually returned rows (the response also lists empty ones)
        for s in re.split(r"\n#RESOURCE=", txt):
            names = re.findall(r"^#Name: (\S+)", s, re.M)
            titles = re.findall(r"^#Title: (.*)$", s, re.M)
            data = [l for l in s.splitlines() if l and not l.startswith("#")]
            if len(data) > 3:
                hits.append(f"{names[-1] if names else '?'} [{titles[0][:70] if titles else ''}] ({len(data) - 3})")
        print(f"== {name} [{who}] tables with rows:", "; ".join(hits), flush=True)
