"""Print every row (all non-empty columns) of the vz_<tag>.tsv files written by vizier_specific.sh.

Run: nice -n 15 /home/paw/Desktop/ultracool/.venv/bin/python vz_summary.py > vizier_specific_rows.txt   (from research/wdt/lit/)
Each vz_<tag>.tsv holds two asu-tsv answers separated by '#### <source> @ <ra dec>' (T dwarf first, then the WD).
"""
import glob
import os
import re
import tempfile

import vztsv

for f in sorted(glob.glob("vz_*.tsv")):
    print(f"######## {f}")
    for sec in re.split(r"^(?=#### )", open(f, encoding="utf8", errors="replace").read(), flags=re.M):
        if not sec.startswith("#### "):
            continue
        head = sec.splitlines()[0]
        err = re.findall(r"#INFO\tError=(.*)", sec)
        with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False) as t:
            t.write(sec)
        d = vztsv.read(t.name)
        os.unlink(t.name)
        titles = dict(re.findall(r"#Name: (\S+)\n#Title: (.*)", sec))
        print(f"## {head[5:]}: {len(titles)} tables listed, {sum(map(len, d.values()))} rows {('ERROR ' + err[0]) if err else ''}")
        for tab, rows in d.items():
            for r in rows:
                print(f"  [{tab}] " + "; ".join(f"{k}={v}" for k, v in r.items() if v))
