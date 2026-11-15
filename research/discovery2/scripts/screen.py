"""Screen the Rothermich+2024 (AJ 167, 253) UCD companion candidates that only have photometric types.

Inputs (saved in raw/): VizieR J/AJ/167/253 table1/table2/table11 (Harvard mirror asu-tsv, -out.all), Table 3 (low
probability systems, typed from the arXiv HTML text research/verification/rothermich_text.txt, hard-coded below) and
Table 4 (spectroscopic observation log, from the same text).
External queries (saved under raw/screen_*): VizieR CfA mirror II/365 CatWISE2020 (5" target + 15" neighbours),
I/355/gaiadr3 15", II/328 AllWISE 120" (W2 < 8), SIMBAD Harvard TAP cone. Local: UltracoolSheet v2.1.0, SPIFF table.
Output: out/screen.csv (every candidate, every cut, reasons) and out/screen.json.
Run: nice -n 15 ../../.venv/bin/python scripts/screen.py   (cwd = research/discovery2)"""
import csv
import json
import re
import time
from pathlib import Path

import astropy.units as u
import numpy as np
import pyvo
from astropy.coordinates import SkyCoord
from astroquery.vizier import Vizier

RAW, OUT = Path("raw"), Path("out")
W2_MAX, W2_RELAXED, B_MIN = 14.5, 15.3, 15.0


def vz(path):
    lines = [l for l in open(path) if not l.startswith("#") and l.strip()]
    hdr = lines[0].rstrip("\n").split("\t")
    return [{h: v.strip() for h, v in zip(hdr, l.rstrip("\n").split("\t"))} for l in lines[3:]]


t1, t2, t11 = (vz(RAW / f"rothermich_{t}.tsv") for t in ("table1", "table2", "table11"))
by_id, phot = {r["ID"]: r for r in t1}, {r["ID"]: r for r in t2}
spec_log = set(re.findall(r"CWISE J\d{6}\.\d\d[+-]\d{6}\.\d", Path(RAW / "rothermich_table4_spectra.txt").read_text()))

cands = []
for r in t11:  # one row per high-probability system: Host1 (+Host2) + Comp
    c = by_id[r["Comp"]]
    h = by_id.get(r["Host1"]) or next(x for x in t1 if x["Syst"] == c["Syst"] and x["ID"] != c["ID"])
    cands.append(dict(name=c["ID"], table="T1 high-prob", lit_spt_rothermich=c["SpType"], r_spt=c["r_SpType"],
                      ra_des=float(c["_RA"]), dec_des=float(c["_DE"]), roth_pmra=c["pmRA"], roth_pmdec=c["pmDE"],
                      sep_arcsec=c["SepA"], sep_au=c["SepL"], host=h["ID"], host_spt=h["SpType"], host_pmra=h["pmRA"],
                      host_e_pmra=h["e_pmRA"], host_pmdec=h["pmDE"], host_e_pmdec=h["e_pmDE"], host_plx=h["plx"],
                      host_e_plx=h["e_plx"], host_rv=h["RVel"], host2=r["Host2"],
                      prob=max((x["Prob"] for x in t1 if x["Syst"] == c["Syst"] and x["Prob"]), default=""),
                      roth_W1=phot[c["ID"]]["W1mag"], roth_W2=phot[c["ID"]]["W2mag"], roth_J=phot[c["ID"]]["Jmag"]))
# Table 3 (low probability), photometric secondaries only (parenthesised types). Values copied from the arXiv HTML.
T3 = [  # name, (SpT), host, host pmra, pmdec, plx, sep", prob %
    ("J002820.38+320128.9", "(L5)", "LP 293-22", 227.42, -77.48, 7.17, 580, 0),
    ("CWISE J045917.62-552557.2", "(L8)", "CWISE J050032.44-552307.0 (T0) [pair of two UCDs]", "", "", 19.78, 660, 66.4),
    ("CWISE J050032.44-552307.0", "(T0)", "CWISE J045917.62-552557.2 (L8) [plx 19.78+-3.96]", 90.78, 96.73, 19.78, 660, 66.4),
    ("CWISE J081701.93+360138.0", "(L3)", "G 51-5", -292.74, -222.47, 16.10, 122, 0),
    ("CWISE J102322.00-204549.9", "(L3)", "CWISE J102244.48-204204.5", -3.00, -169.87, 10.59, 573, 0),
    ("CWISE J103944.79+100732.9", "(L7)", "LSPM J1039+1006", -40.81, -319.02, 18.45, 341, 0),
    ("CWISE J110955.96-293144.5", "(L5)", "CWISE J110924.58-293324.1", -167.97, -4.44, 9.35, 422, 63.4),
    ("CWISE J122736.10+413451.9", "(T3)", "LP 217-15", 99.23, -402.79, 5.43, 1024, 0),
    ("CWISE J132520.42-190701.2", "(L6)", "WDJ132457.07-190212.35", -5.68, -162.45, 22.22, 439, 87.5),
    ("CWISE J134720.42+682042.7", "(T2)", "LP 40-237", -173.58, 68.27, 19.06, 29, 72.8),
    ("CWISE J145735.80+133411.1", "(L4)", "G 136-40", 33.85, -271.53, 20.26, 40, 0),
    ("CWISE J154205.53+593900.8", "(M6)", "RX J1542.3+5936A", -88.44, 20.67, 22.50, 169, 0),
    ("CWISE J155351.21-025829.2", "(L4)", "2MASS J15535171-0258201", -66.97, 26.12, 7.50, 12, 0),
    ("CWISE J182641.78-465249.2", "(T4)", "SIPS J1826-4652", 54.10, -191.00, 23.55, 6, 77.4),
    ("CWISE J204331.57+215556.1", "(T7)", "LSPM J2043+2156", 162.11, -65.13, 19.23, 61, 0.3),
    ("CWISE J221147.93-514120.4", "(L5)", "LTT 8899", 186.68, -88.06, 7.11, 76, 0),
    ("CWISE J224231.76-461402.7", "(T0)", "Gaia DR3 6519217372680214144", 131.33, 4.08, 6.13, 39, 0),
    ("CWISE J230809.74-505232.1", "(T2)", "2MASS J23081176-5052080", 17.24, -123.52, 8.38, 30, 87.2),
    ("CWISE J231249.36-523904.6", "(L7)", "HD 218961", 80.47, -35.44, 14.83, 74, 0.3),
    ("CWISE J231728.89-670001.1", "(T6)", "GJ 4321/4322", 363.82, -410.03, 35.14, 227, 5.1),
]
for n, spt, host, hpa, hpd, plx, sep, prob in T3:
    m = re.search(r"J(\d\d)(\d\d)(\d\d\.\d\d)([+-]\d\d)(\d\d)(\d\d\.\d)", n)
    sc = SkyCoord(f"{m[1]}h{m[2]}m{m[3]}s {m[4]}d{m[5]}m{m[6]}s")
    cands.append(dict(name=n, table="T3 low-prob", lit_spt_rothermich=spt, r_spt="1", ra_des=sc.ra.deg, dec_des=sc.dec.deg,
                      sep_arcsec=sep, host=host, host_pmra=hpa, host_pmdec=hpd, host_plx=plx, prob=prob))

# ---- CatWISE2020 (offset-corrected PMs), Gaia DR3, AllWISE, via the CfA VizieR mirror (batched cone lists)
viz = Vizier(columns=["**", "_r"], row_limit=-1)
viz.VIZIER_SERVER = "vizier.cfa.harvard.edu"
pos = SkyCoord([c["ra_des"] for c in cands], [c["dec_des"] for c in cands], unit="deg")


def vq(cat, rad):
    p = RAW / f"screen_{cat.replace('/', '_')}_{rad}.ecsv"
    if p.exists():
        from astropy.table import Table
        return Table.read(p)
    for k in range(3):
        try:
            t = viz.query_region(pos, radius=rad * u.arcsec, catalog=cat)[0]
            t.write(p, overwrite=True)
            return t
        except Exception as e:  # noqa: BLE001
            print("vizier retry", cat, e); time.sleep(20)
    raise SystemExit(f"VizieR {cat} failed")


cw = vq("II/365/catwise", 15)
gaia = vq("I/355/gaiadr3", 15)
aw = vq("II/328/allwise", 120)

# ---- UltracoolSheet v2.1.0 and SPIFF
ucs = list(csv.DictReader(open("../discovery/ext/ultracoolsheet_v2.1.0_main.csv")))
ucs_c = SkyCoord([float(r["ra_j2000_formula"] or "nan") for r in ucs], [float(r["dec_j2000_formula"] or "nan") for r in ucs], unit="deg")
spiff = list(csv.DictReader(open("../../backend/app/data/ucd_catalog.csv")))
spiff_c = SkyCoord([r["ra_j2000"] for r in spiff], [r["dec_j2000"] for r in spiff], unit=(u.hourangle, u.deg))

# ---- prior work (research/discovery/REPORT.md): any object already processed there
prior = Path("../discovery/REPORT.md").read_text()
prior_tags = set(re.findall(r"\bJ\d{4}[+-]\d{4}\b", prior))

TAP = pyvo.dal.TAPService("https://simbad.harvard.edu/simbad/sim-tap")
simbad_cache = RAW / "screen_simbad.json"
sim = json.loads(simbad_cache.read_text()) if simbad_cache.exists() else {}

rows = []
for i, c in enumerate(cands):
    q = cw[cw["_q"] == i + 1]
    tgt = q[np.argmin(q["_r"])] if len(q) and q["_r"].min() < 5 else None
    rej, soft = [], []
    c.update(cw_name=None)
    if tgt is None:
        rej.append("no CatWISE2020 source within 5\" of the designation position")
    else:
        c.update(cw_name=str(tgt["Name"]), ra=float(tgt["RA_ICRS"]), dec=float(tgt["DE_ICRS"]), W1=float(tgt["W1mproPM"]),
                 W2=float(tgt["W2mproPM"]), e_W2=float(tgt["e_W2mproPM"]),  # II/365 pmRA/pmDE are arcsec/yr, offset-corrected
                 cw_pmra=float(tgt["pmRA"]) * 1000, cw_pmdec=float(tgt["pmDE"]) * 1000,
                 cw_e_pmra=float(tgt["e_pmRA"]) * 1000, cw_e_pmdec=float(tgt["e_pmDE"]) * 1000, cw_ab=str(tgt["abf"]), cw_cc=str(tgt["ccf"]))
    ra, dec = c.get("ra", c["ra_des"]), c.get("dec", c["dec_des"])
    sc = SkyCoord(ra, dec, unit="deg")
    c["glat"] = round(float(sc.galactic.b.deg), 2)
    pm_tot = np.hypot(c.get("cw_pmra", 0) or 0, c.get("cw_pmdec", 0) or 0) / 1000  # arcsec/yr
    # spectroscopic type already published?
    if c["table"].startswith("T1") and not c["lit_spt_rothermich"].startswith("("):
        rej.append(f"Rothermich+24 spectroscopic type {c['lit_spt_rothermich']}")
    if any(abs(SkyCoord(f"{s[7:9]}h{s[9:11]}m{s[11:16]}s {s[16:19]}d{s[19:21]}m{s[21:25]}s").separation(sc).arcsec) < 3 for s in spec_log):
        rej.append("in Rothermich+24 Table 4 spectroscopic log")
    rad_pm = 10 + pm_tot * 20  # 10" plus 20 yr of motion (catalogue epochs 2000-2020)
    d = ucs_c.separation(sc).arcsec
    j = int(np.nanargmin(d))
    c["ucs_sep"] = round(float(d[j]), 1)
    if d[j] < rad_pm:
        u_ = ucs[j]
        c["ucs"] = f"{u_['name']} opt={u_['spt_opt']} ({u_['ref_spt_opt']}) ir={u_['spt_ir']} ({u_['ref_spt_ir']}) flag={u_['literature_flag']}"
        if (u_["spt_opt"] or u_["spt_ir"]) and "photSpT" not in u_["literature_flag"]:
            rej.append(f"UltracoolSheet spectroscopic type: {c['ucs']}")
    d = spiff_c.separation(sc).arcsec
    j = int(np.argmin(d))
    c["spiff_sep"] = round(float(d[j]), 1)
    if d[j] < rad_pm:
        s = spiff[j]
        c["spiff"] = f"{s['designation']} {s['dataset']} auto={s['spiff_autotype']} lit={s['literature_spectral_type']}"
        # SPIFF autotypes are SPHEREx-spectrum types (Gagne+2026): a match means our type would not be the first one.
        # Their 'literature' column holds e.g. "L0-Y2" (candidate class) or numeric photometric estimates, so it is quoted, not trusted.
        rej.append(f"SPIFF SPHEREx autotype already published: {c['spiff']}")
    # SIMBAD (Harvard TAP): sp_type + bibcode + mesSpT, cone 3" + motion since 2000
    key = c["name"]
    if key not in sim:
        rr = 3 + pm_tot * 16
        for k in range(3):
            try:
                t = TAP.run_sync(f"SELECT b.oid, b.main_id, b.otype, b.sp_type, b.sp_bibcode, b.nbref, DISTANCE(POINT('ICRS',b.ra,b.dec),POINT('ICRS',{ra},{dec}))*3600 AS sep "
                                 f"FROM basic b WHERE CONTAINS(POINT('ICRS',b.ra,b.dec),CIRCLE('ICRS',{ra},{dec},{rr / 3600}))=1 ORDER BY sep").to_table()
                hits = [{k2: (v.item() if hasattr(v, "item") else v) for k2, v in zip(t.colnames, row)} for row in t]
                for h in hits:
                    m2 = TAP.run_sync(f"SELECT sptype, bibcode FROM mesSpT WHERE oidref={h['oid']}").to_table()
                    h["mesSpT"] = [[str(a), str(b)] for a, b in m2]
                    h["bibcodes"] = [str(x[0]) for x in TAP.run_sync(f"SELECT r.bibcode FROM has_ref h JOIN ref r ON r.oidbib=h.oidbibref WHERE h.oidref={h['oid']}").to_table()]
                sim[key] = hits
                simbad_cache.write_text(json.dumps(sim, default=str, indent=1))
                break
            except Exception as e:  # noqa: BLE001
                print("simbad retry", key, e); time.sleep(10)
    hits = sim.get(key)
    if hits is None:
        soft.append("SIMBAD query failed")
    else:
        c["simbad"] = "; ".join(f"{h['main_id']} [{h['otype']}] sp={h['sp_type']!s} ({h['sp_bibcode']}) mesSpT={h['mesSpT']} nbref={h['nbref']} sep={h['sep']:.1f}" for h in hits)
        for h in hits:
            mes = [m for m in h["mesSpT"] if m[0] and not m[0].startswith("(") and "2024AJ....167..253R" not in m[1]]
            if mes:
                rej.append(f"SIMBAD spectral type {mes} for {h['main_id']}")
    # brightness and latitude
    W2 = c.get("W2") or (float(c["roth_W2"]) if c.get("roth_W2") else None)  # no CatWISE match: Rothermich Table 2 W2
    if W2 is not None and W2 > W2_MAX:
        (soft if W2 <= W2_RELAXED else rej).append(f"W2 {W2:.2f} > {W2_MAX}" + (" (inside relaxed tier <= 15.3)" if W2 <= W2_RELAXED else ""))
    if abs(c["glat"]) <= B_MIN:
        rej.append(f"|b| = {abs(c['glat']):.1f} <= 15")
    # neighbours: CatWISE within 15" brighter (W1 or W2) than the target
    if tgt is not None:
        nb = q[(q["Name"] != tgt["Name"]) & ((q["W2mproPM"] < tgt["W2mproPM"]) | (q["W1mproPM"] < tgt["W1mproPM"]))]
        c["cw_brighter_15"] = "; ".join(f"{n['Name']} W1={n['W1mproPM']:.2f} W2={n['W2mproPM']:.2f} r={n['_r']:.1f}" for n in nb)
        if len(nb):
            rej.append(f"brighter CatWISE source within 15\": {c['cw_brighter_15']}")
    # Gaia DR3 within 15": counterpart = within 2" (CatWISE 2015.4 vs Gaia 2016.0); a neighbour counts if brighter in G
    # than the counterpart, or G < 19 when the target has no Gaia counterpart (G = 19 star ~ J 17.5, the J of an L dwarf at W2 14.5)
    g = gaia[gaia["_q"] == i + 1]
    cp = g[g["_r"] < 2]
    gcp = float(np.min(cp["Gmag"])) if len(cp) else None
    c["gaia_G_counterpart"] = gcp
    if len(cp):
        c["gaia_cp"] = f"{cp[np.argmin(cp['_r'])]['Source']} G={gcp:.2f} plx={cp[np.argmin(cp['_r'])]['Plx']}"
    lim = gcp if gcp is not None else 19.0
    gn = g[(g["_r"] >= 2) & (g["Gmag"] < lim)]
    c["gaia_brighter_15"] = "; ".join(f"{n['Source']} G={n['Gmag']:.2f} r={n['_r']:.1f}" for n in gn)
    if len(gn):
        rej.append(f"brighter Gaia DR3 source within 15\": {c['gaia_brighter_15']}")
    a = aw[(aw["_q"] == i + 1) & (aw["W2mag"] < 8)]
    if len(a):
        c["allwise_w2lt8_2arcmin"] = "; ".join(f"{n['AllWISE']} W2={n['W2mag']:.2f} r={n['_r']:.0f}" for n in a)
        rej.append(f"W2 < 8 star within 2': {c['allwise_w2lt8_2arcmin']}")
    tag = re.search(r"J(\d{4})\d*\.\d+([+-]\d{4})", c["name"])
    c["tag"] = f"J{tag[1]}{tag[2]}"
    if c["tag"] in prior_tags:
        rej.append("already processed in research/discovery/REPORT.md")
    c["reject"] = " | ".join(rej)
    c["notes"] = " | ".join(soft)
    c["status"] = "reject" if rej else ("pass" if W2 is not None and W2 <= W2_MAX else "pass-relaxed (W2 14.5-15.3)")
    rows.append(c)

prob = lambda c: float(c.get("prob") or 0)  # noqa: E731
rows.sort(key=lambda c: ({"pass": 0, "pass-relaxed (W2 14.5-15.3)": 1, "reject": 2}[c["status"]], c.get("W2") or 99, -prob(c)))
for k, c in enumerate(rows):
    c["rank"] = k + 1 if c["status"] != "reject" else ""
cols = ["rank", "status", "tag", "name", "table", "lit_spt_rothermich", "W2", "e_W2", "W1", "glat", "prob", "host", "host_plx", "sep_arcsec",
        "cw_pmra", "cw_e_pmra", "cw_pmdec", "cw_e_pmdec", "host_pmra", "host_pmdec", "cw_ab", "cw_cc", "gaia_G_counterpart", "reject", "notes",
        "simbad", "ucs", "spiff", "cw_brighter_15", "gaia_brighter_15", "ra", "dec", "cw_name"]
with open(OUT / "screen.csv", "w", newline="") as f:
    w = csv.DictWriter(f, cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
(OUT / "screen.json").write_text(json.dumps(rows, default=str, indent=1))
for c in rows:
    print(c["rank"], c["status"][:12], c["tag"], c["lit_spt_rothermich"], c.get("W2"), c["glat"], c.get("prob"), "|", c["reject"][:150], "|", c["notes"][:80])
