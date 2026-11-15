"""Literature check for one object: VizieR all-catalogue cone (CfA mirror asu-tsv, 20"), raw text kept in
out/<tag>/vizier_all_20as.tsv; every catalogue with rows, and every row with a spectral-type-like column, in out/<tag>/lit.json,
together with the SIMBAD records (ids, all bibcodes, mesSpT) gathered by screen.py (raw/screen_simbad.json).
Same parser as /data/research/discovery/lit.py. Usage: python scripts/lit.py <tag> ...   (cwd = research/discovery2)"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

SPT_COL = re.compile(r"^(SpT|Sp|SpType|SpTy|SpT[A-Za-z]*|Type|OSpT|NSpT|SpTNIR|SpTOpt|SpTn|SpTo|SpT-?\w*)$", re.I)
screen = {r["tag"]: r for r in json.loads(Path("out/screen.json").read_text())}
sim = json.loads(Path("raw/screen_simbad.json").read_text())

for tag in sys.argv[1:]:
    s = screen[tag]
    d = Path("out") / tag
    url = f"https://vizier.cfa.harvard.edu/viz-bin/asu-tsv?-c={s['ra']:.6f}{s['dec']:+.6f}&-c.rs=20&-out.max=10"  # 50 rows/table hit IncompleteRead on the mirror
    txt, status = "", "error: no response"
    split = d / "vizier_split_log.txt"
    if split.exists():  # single call was cut off: use the I-B partial file + scripts/vizier_split.sh per-group files
        txt = "\n".join(p.read_text(errors="replace") for p in sorted(d.glob("vizier_*20as*.tsv")))
        status = "split queries: " + " ; ".join(split.read_text().split("\n")).strip(" ;")
        url = "see scripts/vizier_split.sh + " + url
    else:
        for k in range(3):
            try:
                with urllib.request.urlopen(url, timeout=600) as r:
                    txt = r.read().decode("utf-8", "replace")
                status = "ok" if "QUERY_STATUS=ERROR" not in txt else "error: mirror QUERY_STATUS=ERROR"
                if status == "ok":
                    break
            except Exception as e:  # noqa: BLE001
                status = f"error: {e}"
            print("vizier retry", tag, status); time.sleep(60)
        (d / "vizier_all_20as.tsv").write_text(txt)
    tables, cur, hdr, skip = {}, None, None, 0
    for line in txt.splitlines():
        if line.startswith("#Table"):
            cur, hdr = line.split("\t")[1].rstrip(":"), None
        elif line.startswith("#") or not cur:
            continue
        elif not line.strip():
            cur = None if hdr else cur
        elif hdr is None:
            hdr, skip = line.split("\t"), 2
        elif skip:
            skip -= 1
        else:
            tables.setdefault(cur, []).append(dict(zip(hdr, line.split("\t"))))
    spt = [{"table": k, "values": [{c: r[c].strip() for c in [c for c in rows[0] if SPT_COL.match(c.strip())] + ["_r"] if c in r} for r in rows]}
           for k, rows in tables.items() if any(SPT_COL.match(c.strip()) for c in rows[0])]
    out = {"tag": tag, "name": s["name"], "vizier_url": url, "vizier_status": status, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "vizier_tables_with_rows": {k: len(v) for k, v in tables.items()}, "vizier_spt_rows": spt, "simbad": sim.get(s["name"])}
    (d / "lit.json").write_text(json.dumps(out, indent=1, default=str))
    print(tag, status, len(tables), "tables;", "SpT rows:", json.dumps(spt)[:600])
    for h in out["simbad"] or []:
        print("   SIMBAD", h["main_id"], h["otype"], h["sp_type"], h["mesSpT"], h["bibcodes"])
