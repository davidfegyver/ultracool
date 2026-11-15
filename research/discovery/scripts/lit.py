"""Literature status for a list of objects (checked, not remembered). Per object writes out/lit_<tag>.json with
 - SIMBAD (Harvard TAP mirror): main_id, otype, sp_type, nbref, all identifiers, every reference (bibcode, title),
   SIMBAD spectral-type measurements (mesSpT), and every SIMBAD object within 30";
 - VizieR (CfA mirror, asu-tsv, all catalogues): every catalogue row within 10" of the position (raw text kept in
   out/lit_<tag>_vizier.tsv), and the subset of rows with a spectral-type-like column (SpT/Sp/SpType...).
Usage: python lit.py <tag> <ra> <dec> <simbad name> [...more quadruples]"""
import json
import re
import os
import sys
import time
import urllib.request

import pyvo

TAP = pyvo.dal.TAPService("https://simbad.harvard.edu/simbad/sim-tap")
SPT_COL = re.compile(r"^(SpT|Sp|SpType|SpTy|SpT[A-Za-z]*|Type|OSpT|NSpT|SpTNIR|SpTOpt|SpTn|SpTo)$", re.I)


def q(adql):
    for k in range(3):
        try:
            return [dict(zip(r.keys(), [x.item() if hasattr(x, "item") else x for x in r.values()])) for r in
                    (dict(row) for row in TAP.run_sync(adql).to_table())]
        except Exception as e:  # noqa: BLE001
            print("simbad retry", e); time.sleep(5)
    return None


def esc(s):
    return s.replace("'", "''")


def one(tag, ra, dec, name):
    p = f"out/lit_{tag}.json"
    old = json.load(open(p)) if os.path.exists(p) else {}
    if old.get("vizier_status") == "ok" and old.get("simbad_cone30") is not None:
        return
    out = {"tag": tag, "query_name": name, "ra": ra, "dec": dec, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": {"simbad": "https://simbad.harvard.edu/simbad/sim-tap", "vizier": "vizier.cfa.harvard.edu (all catalogues, 10 arcsec)"}}
    if old.get("simbad_cone30") is not None:  # SIMBAD part already done: only VizieR failed last time
        out.update({k: v for k, v in old.items() if k.startswith("simbad")})
        b = out["simbad_basic"]
    else:
        b = q(f"SELECT b.oid, b.main_id, b.otype, b.sp_type, b.sp_bibcode, b.nbref, b.plx_value, b.pmra, b.pmdec FROM basic b JOIN ident i ON i.oidref=b.oid WHERE i.id='{esc(name)}'")
        out["simbad_basic"] = b
        if b:
            oid = b[0]["oid"]
            out["simbad_ids"] = [r["id"] for r in q(f"SELECT id FROM ident WHERE oidref={oid}") or []]
            out["simbad_refs"] = q(f"SELECT r.bibcode, r.title FROM has_ref h JOIN ref r ON r.oidbib=h.oidbibref WHERE h.oidref={oid} ORDER BY 1")
            out["simbad_mesSpT"] = q(f"SELECT sptype, bibcode FROM mesSpT WHERE oidref={oid}")
        out["simbad_cone30"] = q(f"SELECT main_id, otype, sp_type, nbref, DISTANCE(POINT('ICRS',ra,dec),POINT('ICRS',{ra},{dec}))*3600 AS sep FROM basic "
                                 f"WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{ra},{dec},{30 / 3600}))=1 ORDER BY sep")
    # all VizieR catalogues within 10": asu-tsv on the CfA mirror (~90 s; the votable endpoint times out at its gateway)
    url = f"https://vizier.cfa.harvard.edu/viz-bin/asu-tsv?-c={ra:.6f}{dec:+.6f}&-c.rs=10&-out.max=20"
    txt, status = "", "error: no response"
    for k in range(3):
        try:
            with urllib.request.urlopen(url, timeout=400) as r:
                txt = r.read().decode("utf-8", "replace")
            # the mirror answers HTTP 200 with QUERY_STATUS=ERROR when its database is down: that is a failure, not "no rows"
            status = "ok" if "QUERY_STATUS=ERROR" not in txt else "error: " + "; ".join(
                l.split("=", 1)[1].strip() for l in txt.splitlines() if l.startswith("#INFO\tError=") and l.split("=", 1)[1].strip())[:200]
            if status == "ok":
                break
        except Exception as e:  # noqa: BLE001
            status = f"error: {e}"
        print("vizier retry", tag, status); time.sleep(60)
    open(f"out/lit_{tag}_vizier.tsv", "w").write(txt)
    out["vizier_url"], out["vizier_status"] = url, status
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
    out["vizier_tables_with_rows"] = {k: len(v) for k, v in tables.items()}
    spt = []
    for k, rows in tables.items():
        cols = [c for c in rows[0] if SPT_COL.match(c.strip())]
        if cols:
            spt.append({"table": k, "values": [{c: r[c].strip() for c in cols + [c for c in ("_r",) if c in r]} for r in rows]})
    out["vizier_spt_rows"] = spt
    res = tables
    open(f"out/lit_{tag}.json", "w").write(json.dumps(out, default=str, indent=1))
    bb = (b or [{}])[0]
    print(f"== {tag} {bb.get('main_id')} otype={bb.get('otype')} sp={bb.get('sp_type')!r} nbref={bb.get('nbref')} mesSpT={out.get('simbad_mesSpT')}")
    for r in out.get("simbad_refs") or []:
        print("   ref", r["bibcode"], (r["title"] or "")[:90])
    for s in spt:
        print("   vizier", s["table"], s["values"][:3])
    print("   vizier", out["vizier_status"], "tables with rows", len(res), "| cone30:", [(c["main_id"], c["otype"], c["sp_type"], round(c["sep"], 1)) for c in out["simbad_cone30"] or []][:6])


a = sys.argv[1:]
for i in range(0, len(a), 4):
    one(a[i], float(a[i + 1]), float(a[i + 2]), a[i + 3])
    time.sleep(10)  # be gentle with the mirror
