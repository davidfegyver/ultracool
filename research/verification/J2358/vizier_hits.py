"""Summarise the VizieR 20" cone (all catalogues, queried in parts by -source=<prefix>/*) around J2358-5218.

Run: python3 vizier_hits.py > vizier_hits.txt  (from research/verification/J2358/)
Lists every table with rows, nearest-row separation, catalogue title, and any spectral-type / Teff / class column.
Parts were fetched with: curl -G https://vizier.cfa.harvard.edu/viz-bin/asu-tsv -d -source=<prefix>/* -d "-c=359.6165529 -52.303748"
-d -c.rs=20 -d -out.max=50 -d -out.add=_r  (saved gzipped as vizier_part_*.tsv.gz).
"""
import glob
import re

import vztsv

SPT = re.compile(r"sp|type|teff|class|ucd|mass", re.I)
for f in sorted(glob.glob("vizier_part_*.tsv.gz")):
    txt = vztsv._open(f).read()
    titles = dict(re.findall(r"#Name: (\S+)\n#Title: (.*)", txt))
    d = vztsv.read(f)
    print(f"### {f}: {len(titles)} tables/catalogues listed, {len(d)} with rows")
    for t, rows in d.items():
        rows = sorted(rows, key=lambda r: float(r.get("_r") or 99))
        cat = "/".join(t.split("/")[:4] if t.startswith("J/") else t.split("/")[:2])
        r = rows[0]
        extra = {k: v for k, v in r.items() if v and SPT.search(k)}
        print(f"  {t:32s} n={len(rows):2d} min_r={r.get('_r', '?'):>7s}  [{titles.get(cat, '')[:70]}] {extra}")
