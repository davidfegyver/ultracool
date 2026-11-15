"""Summarise the VizieR 60" all-catalogue cones (queried by -source=<prefix>/*, vizier_parts.sh) around the T dwarf / WD.

Run: python3 vizier_hits.py tdw > vizier_hits_tdw.txt; python3 vizier_hits.py wd > vizier_hits_wd.txt   (from research/wdt/lit/)
Lists every table with rows, nearest-row separation, catalogue title, and the nearest row's non-empty columns whose
name matches companion/binary/pair/SpT/mass/Teff (FLAG). Rows within 5" of the target are marked '*'.
"""
import glob
import re
import sys

import vztsv

FLAG = re.compile(r"comp|bin|pair|prim|sec|sp|type|teff|mass|class|wd|ucd|logg|age|mult|note|rem|flag", re.I)
obj = sys.argv[1]
for f in sorted(glob.glob(f"parts_{obj}/vizier_part_*.tsv.gz")):
    txt = vztsv._open(f).read()
    titles = dict(re.findall(r"#Name: (\S+)\n#Title: (.*)", txt))
    err = re.findall(r"#INFO\tError=(.*)", txt)
    d = vztsv.read(f)
    print(f"### {f}: {len(titles)} tables/catalogues listed, {len(d)} with rows; {len(txt)} chars {err or ''}")
    for t, rows in d.items():
        rows = sorted(rows, key=lambda r: float(r.get("_r") or 99))
        cat = "/".join(t.split("/")[:4] if t.startswith("J/") else t.split("/")[:2])
        r = rows[0]
        extra = {k: v for k, v in r.items() if v and FLAG.search(k)}
        near = "*" if float(r.get("_r") or 99) <= 5 else " "
        print(f" {near}{t:34s} n={len(rows):2d} min_r={r.get('_r', '?'):>7s}  [{titles.get(cat, '')[:70]}] {extra}")
