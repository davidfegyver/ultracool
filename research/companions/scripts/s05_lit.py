"""Step 5: literature / known-pair checks for the pairs that survive the physical cuts.
Survivor = bound_ok (dv_tan - 2 sigma < v_esc) AND expected_false < 0.01 AND no UltracoolSheet companion entry
(has_higher_mass_companion / multiplesystem_resolved_in_this_table == 'N').
Per survivor (all saved to raw/lit/<ucd>__<gaia>.json):
 - SIMBAD (Harvard mirror TAP; CDS SIMBAD TAP returned 404): host by ident 'Gaia DR3 <id>', UCD by UltracoolSheet
   name_simbad (fallback: 5" cone at the UCD's 2016 position); main_id, otype, sp_type, all identifiers,
   bibcodes+titles, h_link parents/children, Fe/H rows (mesFe_h); bibcodes common to both objects.
 - VizieR (CfA mirror asu-tsv): El-Badry+2021 J/MNRAS/506/2269 by Source1/Source2 (host and UCD Gaia IDs);
   Rothermich+2024 J/AJ/167/253 (all tables) within 150" of the UCD; WDS B/wds/wds within 90" of the host;
   Zhang+2021 COCONUTS (J/ApJ/916/53) within 150" of the UCD.
 - UltracoolSheet: any row whose note or companion field mentions the host's SIMBAD main_id / identifiers.
Run (cwd = research/companions): nice -n 15 ../../.venv/bin/python scripts/s05_lit.py"""
import csv
import io
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pyvo

SIM = pyvo.dal.TAPService("https://simbad.harvard.edu/simbad/sim-tap")
VZ = "https://vizier.cfa.harvard.edu/viz-bin/asu-tsv"
UCS = list(csv.DictReader(open("../discovery/ext/ultracoolsheet_v2.1.0_main.csv")))
OUT = Path("raw/lit")
OUT.mkdir(parents=True, exist_ok=True)


def tap(q):
    for k in range(4):
        try:
            t = SIM.run_sync(q).to_table()
            return [{c: (v.item() if hasattr(v, "item") else (None if v is None else str(v))) for c, v in zip(t.colnames, r)} for r in t]
        except Exception as e:  # noqa: BLE001
            print("simbad retry", repr(e)[:150]); time.sleep(10)
    return "FAILED"


def vizier(params):
    url = VZ + "?" + urllib.parse.urlencode(params)
    for k in range(4):
        try:
            txt = urllib.request.urlopen(url, timeout=120).read().decode("utf-8", "replace")
            # asu-tsv: per table a header line, a units line and a dashes line, then data rows. Anything else
            # (blank lines, stray MIME lines the CfA mirror sometimes emits) is ignored.
            lines = [l for l in txt.splitlines() if l.strip() and not l.startswith("#")]
            dash = lambda l: l.startswith("-") and set(l) <= {"-", "\t", " "}  # noqa: E731
            heads = {i for i in range(len(lines) - 2) if dash(lines[i + 2])}
            rows, hdr = [], None
            for i, l in enumerate(lines):
                if i in heads:
                    hdr = [v.strip() for v in l.split("\t")]
                elif hdr and i - 1 not in heads and i - 2 not in heads and not dash(l):
                    rows.append(dict(zip(hdr, [v.strip() for v in l.split("\t")])))
            return {"url": url, "rows": rows}
        except Exception as e:  # noqa: BLE001
            print("vizier retry", repr(e)[:150]); time.sleep(10)
    return {"url": url, "rows": "FAILED"}


def simbad_obj(where):
    b = tap(f"SELECT TOP 3 b.oid, b.main_id, b.otype, b.sp_type, b.plx_value, b.pmra, b.pmdec, b.ra, b.dec FROM basic b {where}")
    if b == "FAILED" or not b:
        return {"basic": b}
    oid = b[0]["oid"]
    return {"basic": b,
            "ids": [r["id"] for r in tap(f"SELECT id FROM ident WHERE oidref={oid}") or []],
            "refs": tap(f"SELECT r.bibcode, r.title FROM has_ref h JOIN ref r ON r.oidbib=h.oidbibref WHERE h.oidref={oid}"),
            "parents": tap(f"SELECT b.main_id, b.otype, h.link_bibcode FROM h_link h JOIN basic b ON b.oid=h.parent WHERE h.child={oid}"),
            "children": tap(f"SELECT b.main_id, b.otype, h.link_bibcode FROM h_link h JOIN basic b ON b.oid=h.child WHERE h.parent={oid}"),
            "feh": tap(f"SELECT fe_h, teff, log_g, bibcode FROM mesFe_h WHERE oidref={oid}")}


pairs = list(csv.DictReader(open("out/pairs_cut.csv")))
chance = list(csv.DictReader(open("out/chance.csv")))
surv = []
for p, c in zip(pairs, chance):
    assert p["gaia"] == c["gaia"]
    p.update(n_field=c["n_field"], expected_false=c["expected_false"])
    if p["bound_ok"] == "True" and float(c["expected_false"]) < 0.01:
        surv.append(p)
print("bound & chance survivors:", len(surv))
with open("out/survivors_all.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(surv[0]))
    w.writeheader(); w.writerows(surv)

for p in surv:
    if p["ucs_higher_mass_comp"] != "N" or p["ucs_multi_res"] != "N":
        continue
    fn = OUT / (re.sub(r"[^\w+-]", "_", p["ucd"]) + "__" + p["gaia"] + ".json")
    if fn.exists():
        continue
    rec = {"pair": p}
    rec["host_simbad"] = simbad_obj(f"JOIN ident i ON i.oidref=b.oid WHERE i.id='Gaia DR3 {p['gaia']}'")
    nm = p["ucs_simbad"].replace("'", "''")
    rec["ucd_simbad"] = simbad_obj(f"JOIN ident i ON i.oidref=b.oid WHERE i.id='{nm}'") if nm and nm != "null" else {"basic": []}
    if not rec["ucd_simbad"].get("basic"):
        up = next(r for r in csv.DictReader(open("raw/ucd_upload.csv")) if r["uid"] == p["uid"])
        rec["ucd_simbad"] = simbad_obj(f"WHERE CONTAINS(POINT('ICRS', b.ra, b.dec), CIRCLE('ICRS', {up['ra16']}, {up['de16']}, 10.0/3600))=1")
    hr = rec["host_simbad"].get("refs") or []
    ur = rec["ucd_simbad"].get("refs") or []
    if isinstance(hr, list) and isinstance(ur, list):
        hb = {r["bibcode"]: r["title"] for r in hr}
        rec["common_bibcodes"] = [(r["bibcode"], r["title"]) for r in ur if r["bibcode"] in hb]
    ug = p["ucd_gaia"] if p["ucd_gaia"] not in ("", "null") else None
    rec["elbadry"] = [vizier({"-source": "J/MNRAS/506/2269", col: gid, "-out": "Source1 Source2 sepAU R", "-out.max": "50"})
                      for gid in filter(None, [p["gaia"], ug]) for col in ("Source1", "Source2")]
    rec["rothermich"] = vizier({"-source": "J/AJ/167/253", "-c": f"{p['g_ra']} {p['g_dec']}", "-c.rs": "150", "-out.max": "50"})
    rec["wds"] = vizier({"-source": "B/wds/wds", "-c": f"{p['g_ra']} {p['g_dec']}", "-c.rs": "90", "-out.max": "50"})
    rec["coconuts_zhang21"] = vizier({"-source": "J/ApJ/916/53", "-c": f"{p['g_ra']} {p['g_dec']}", "-c.rs": "150", "-out.max": "50"})
    names = set(rec["host_simbad"].get("ids") or [])
    if rec["host_simbad"].get("basic") and rec["host_simbad"]["basic"] != "FAILED":
        names.add(rec["host_simbad"]["basic"][0]["main_id"])
    names = {re.sub(r"\s+", " ", n).strip() for n in names if not n.startswith(("Gaia", "TIC", "2MASS J", "WISEA", "TYC"))} | {n for n in names if n.startswith("TYC")}
    rec["ucs_mentions_host"] = [(r["name"], r["has_higher_mass_companion"], r["note"][:200]) for r in UCS
                                for n in names if len(n) > 4 and (n in r["note"] or n in r["has_higher_mass_companion"])]
    fn.write_text(json.dumps(rec, indent=1, default=str))
    print("done", p["ucd"], p["gaia"], flush=True)
