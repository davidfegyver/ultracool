"""Step 6: independent self-check of top candidates (args: '<ucd name>|<host Gaia DR3 id>' ...).
 - Gaia DR3 re-query on a different service (VizieR I/355/gaiadr3, CfA mirror asu-tsv; CDS TAPVizieR was unreachable):
   host by Source id, and every Gaia source within 3" of the UCD's 2016.0 position.
 - CatWISE2020 (VizieR II/365, offset-corrected PMs) within 5" of the UCD's 2015.4 position.
 - 2MASS (II/246) within 5" of the UCD's 2MASS-epoch position -> two-epoch PM 2MASS -> CatWISE (ep. ~2015.4 mean) and,
   if the UCD is in Gaia, 2MASS -> Gaia (2016.0). Positional errors assumed 0.1" (2MASS) and 0.1" CatWISE / Gaia.
Writes raw/selfcheck/<name>.json and prints a summary.
Run (cwd = research/companions): ../../.venv/bin/python scripts/s06_selfcheck.py 'NAME|ID' ..."""
import csv
import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

VZ = "https://vizier.cfa.harvard.edu/viz-bin/asu-tsv"
UCS = {r["name"]: r for r in csv.DictReader(open("../discovery/ext/ultracoolsheet_v2.1.0_main.csv"))}
OUT = Path("raw/selfcheck")
OUT.mkdir(parents=True, exist_ok=True)


def vizier(params):
    url = VZ + "?" + urllib.parse.urlencode(params)
    for k in range(4):
        try:
            txt = urllib.request.urlopen(url, timeout=120).read().decode("utf-8", "replace")
            break
        except Exception as e:  # noqa: BLE001
            print("retry", repr(e)[:100]); time.sleep(10)
    else:
        return url, "FAILED"
    # header line, units line, dashes line, data; stray non-table lines (CfA MIME fragments) are ignored
    lines = [l for l in txt.splitlines() if l.strip() and not l.startswith("#")]
    dash = lambda l: l.startswith("-") and set(l) <= {"-", "\t", " "}  # noqa: E731
    heads = [i for i in range(len(lines) - 2) if dash(lines[i + 2])]
    if not heads:
        return url, []
    hdr = [h.strip() for h in lines[heads[0]].split("\t")]
    return url, [dict(zip(hdr, [v.strip() for v in l.split("\t")])) for l in lines[heads[0] + 3:] if not dash(l)]


def fl(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def two_epoch(ra1, de1, t1, ra2, de2, t2, sig=0.1414):
    dt = t2 - t1
    pmra = (ra2 - ra1) * math.cos(math.radians((de1 + de2) / 2)) * 3.6e6 / dt
    pmde = (de2 - de1) * 3.6e6 / dt
    return round(pmra, 1), round(pmde, 1), round(sig * 1000 / dt, 1), round(dt, 2)


for arg in sys.argv[1:]:
    name, gid = arg.split("|")
    u = UCS[name]
    pa, pd = float(u["pmra_formula"]), float(u["pmdec_formula"])
    ra25, de25 = float(u["ra_20250703_formula"]), float(u["dec_20250703_formula"])

    def at(t):
        return ra25 + pa / 3.6e6 / math.cos(math.radians(de25)) * (t - 2025.5027), de25 + pd / 3.6e6 * (t - 2025.5027)

    rec = {"name": name, "host": gid}
    gcols = "Source RA_ICRS DE_ICRS Plx e_Plx pmRA e_pmRA pmDE e_pmDE Gmag BPmag RPmag RUWE RV e_RV"
    rec["host_gaia"] = vizier({"-source": "I/355/gaiadr3", "Source": gid, "-out": gcols})
    r16, d16 = at(2016.0)
    rec["ucd_gaia_3as"] = vizier({"-source": "I/355/gaiadr3", "-c": f"{r16} {d16}", "-c.rs": "3", "-out": gcols + " _r"})
    r15, d15 = at(2015.4)
    rec["ucd_catwise_5as"] = vizier({"-source": "II/365/catwise", "-c": f"{r15} {d15}", "-c.rs": "5",
                                     "-out": "Name RAPMdeg DEPMdeg pmRA e_pmRA pmDE e_pmDE W1mproPM W2mproPM ab _r"})
    for s in rec["ucd_catwise_5as"][1] if isinstance(rec["ucd_catwise_5as"][1], list) else []:
        for c in ("pmRA", "e_pmRA", "pmDE", "e_pmDE"):  # II/365 PMs are arcsec/yr -> mas/yr
            s[c + "_mas"] = round(float(s[c]) * 1000, 1) if fl(s.get(c)) is not None else None
    # CatWISE II/365 returned empty resources from the CfA mirror on 2026-11-15 (even at J2317, a known CatWISE source),
    # so AllWISE (II/328, PM in mas/yr, mean epoch ~2010.5) is queried as a second WISE-based astrometric source.
    rec["ucd_allwise_5as"] = vizier({"-source": "II/328/allwise", "-c": f"{r15} {d15}", "-c.rs": "6",
                                     "-out": "AllWISE RAJ2000 DEJ2000 pmRA e_pmRA pmDE e_pmDE W1mag W2mag ccf _r"})
    m2 = re.match(r"(\d{4})-(\d\d)-(\d\d)", u["epoch_2mass"])
    t2m = int(m2[1]) + (int(m2[2]) - 1) / 12 + int(m2[3]) / 365.25 if m2 else None
    rec["epoch_2mass_ucs"] = u["epoch_2mass"]
    if t2m:
        r0, d0 = at(t2m)
        rec["ucd_2mass_5as"] = vizier({"-source": "II/246/out", "-c": f"{r0} {d0}", "-c.rs": "5", "-out": "2MASS RAJ2000 DEJ2000 Jmag Kmag JD _r"})
        tm = rec["ucd_2mass_5as"][1]
        if tm and tm != "FAILED":
            m = tm[0]
            t1 = 2000.0 + (float(m["JD"]) - 2451545.0) / 365.25
            for key, src, cols, t2 in (("pm_2mass_catwise", rec["ucd_catwise_5as"][1], ("RAPMdeg", "DEPMdeg"), 2015.4),
                                       ("pm_2mass_gaia", rec["ucd_gaia_3as"][1], ("RA_ICRS", "DE_ICRS"), 2016.0)):
                if src and src != "FAILED":
                    s = src[0]
                    rec[key] = two_epoch(float(m["RAJ2000"]), float(m["DEJ2000"]), t1, float(s[cols[0]]), float(s[cols[1]]), t2)
    rec["ucs_pm"] = [pa, pd, u["pmraerr_formula"], u["pmdecerr_formula"], u["ref_pm_formula"]]
    rec["ucs_plx"] = [u["plx_formula"], u["plxerr_formula"], u["ref_plx_formula"], u["dist_formula"], u["disterr_formula"], u["dist_formula_source"]]
    (OUT / (re.sub(r"[^\w+-]", "_", name) + ".json")).write_text(json.dumps(rec, indent=1))
    h = rec["host_gaia"][1][0] if rec["host_gaia"][1] and rec["host_gaia"][1] != "FAILED" else {}
    print(name, "| host", {k: h.get(k) for k in ("Plx", "e_Plx", "pmRA", "pmDE", "Gmag", "RUWE")},
          "| ucd gaia", [(s.get("Source"), s.get("_r"), s.get("Plx"), s.get("pmRA"), s.get("pmDE"), s.get("Gmag")) for s in (rec["ucd_gaia_3as"][1] or []) if isinstance(s, dict)],
          "| catwise", [(s.get("pmRA_mas"), s.get("e_pmRA_mas"), s.get("pmDE_mas"), s.get("e_pmDE_mas"), s.get("_r"), s.get("ab")) for s in (rec["ucd_catwise_5as"][1] or []) if isinstance(s, dict)],
          "| allwise", [(s.get("AllWISE"), s.get("pmRA"), s.get("e_pmRA"), s.get("pmDE"), s.get("e_pmDE"), s.get("_r"), s.get("ccf")) for s in (rec["ucd_allwise_5as"][1] or []) if isinstance(s, dict)],
          "| 2M->CW", rec.get("pm_2mass_catwise"), "| 2M->Gaia", rec.get("pm_2mass_gaia"), "| UCS", rec["ucs_pm"], flush=True)
