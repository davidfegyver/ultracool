"""Step 2: strict cuts on raw/gaia_pairs_raw.csv (from s01).
Cuts (per assignment): UCD |mu| >= 50 (already server side); |dmu| < max(3 sigma_comb, 0.1|mu_UCD|);
parallax: Gaia plx vs UCD trig plx within max(3 sigma, 20 %), or Gaia distance vs UCD photometric distance within
max(3 sigma, 20 %); projected separation < 10,000 au; drop the UCD's own Gaia counterpart (matched DR3 ID or sep < 2").
Adds dv_tan, host mass (Mamajek EEM table, M_G -> Msun by interpolation; white-dwarf hosts, i.e. below the line
M_G > 2.5 (BP-RP) + 8 or with no BP-RP and M_G > 10: Gentile Fusillo+2021 (J/MNRAS/508/3877, CfA VizieR) MassH,
else 0.6 Msun), escape speed at the
projected separation, and the UltracoolSheet companion/multiplicity fields + note.
Writes out/pairs_cut.csv. Run (cwd = research/companions): ../../.venv/bin/python scripts/s02_cuts.py"""
import csv
import json
import math
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

UCS = list(csv.DictReader(open("../discovery/ext/ultracoolsheet_v2.1.0_main.csv")))


def f(x):
    try:
        v = float(x)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None


# Mamajek EEM dwarf table: M_G -> Msun (main sequence)
lines = [l.split() for l in open("raw/mamajek_EEM_dwarf.txt").read().splitlines()[23:141] if l and not l.startswith("#")]
hdr = open("raw/mamajek_EEM_dwarf.txt").read().splitlines()[22].split()
iG, iM = hdr.index("M_G"), hdr.index("Msun")
mg_m = sorted((float(l[iG]), float(l[iM])) for l in lines if f(l[iG]) is not None and f(l[iM]) is not None)
MG, MS = np.array([a for a, _ in mg_m]), np.array([b for _, b in mg_m])
assert MG[0] < 0 < 4.5 < MG[-1] and abs(np.interp(4.67, MG, MS) - 1.0) < 0.1, (MG[[0, -1]], np.interp(4.67, MG, MS))


GF_CACHE = Path("raw/gf21_masses.json")
GF = json.loads(GF_CACHE.read_text()) if GF_CACHE.exists() else {}


def gf21_mass(source):
    """Gentile Fusillo+2021 MassH (H-atmosphere fit) for a Gaia (E)DR3 source id; None if not listed."""
    if source not in GF:
        url = "https://vizier.cfa.harvard.edu/viz-bin/asu-tsv?" + urllib.parse.urlencode(
            {"-source": "J/MNRAS/508/3877/maincat", "GaiaEDR3": source, "-out": "GaiaEDR3 Pwd MassH e_MassH MassHe e_MassHe"})
        lines = [l for l in urllib.request.urlopen(url, timeout=120).read().decode().splitlines() if l.strip() and not l.startswith("#")]
        heads = [i for i in range(len(lines) - 2) if set(lines[i + 2]) <= {"-", "\t", " "}]
        row = dict(zip(lines[heads[0]].split("\t"), [v.strip() for v in lines[heads[0] + 3].split("\t")])) if heads and len(lines) > heads[0] + 3 else {}
        GF[source] = row
        GF_CACHE.write_text(json.dumps(GF, indent=1))
    return f(GF[source].get("MassH"))


def is_wd(Mg, bprp):
    # WD-locus candidates; BP-RP > 1.6 excluded (faint late-M/L hosts have unreliable BP and fall below the line)
    return Mg > 10 if bprp is None else (bprp < 1.6 and Mg > 2.5 * bprp + 8)


assert is_wd(15.07, 1.306) and is_wd(15.5, 1.503) and not is_wd(14.69, 3.931) and not is_wd(5.35, 0.926) and not is_wd(16.02, 2.776)


def host_mass(Mg, bprp, source):
    if Mg is None:
        return None, "no G"
    if is_wd(Mg, bprp):
        m = gf21_mass(source)
        if m:
            return m, "WD: GF21 MassH"
        if bprp is not None:
            return 0.6, "WD locus, not in GF21 (adopted 0.6)"
    return float(np.interp(Mg, MG, MS)), "Mamajek M_G"


def ucd_mass(sptnum):
    # shortcut: 0.08 Msun for any UCD (M7-Y); it is negligible next to the host in v_esc
    return 0.08


out = []
for r in csv.DictReader(open("raw/gaia_pairs_raw.csv")):
    if f(r["Plx"]) is None or f(r["pmRA"]) is None or float(r["Plx"]) <= 0:
        continue  # no 5-parameter solution or non-positive parallax
    u = UCS[int(r["uid"])]
    sep = float(r["sep"])
    gid = u["sourceID_Gaia_DR3"].replace("Gaia DR3 ", "").strip()
    if sep < 2 or r["Source"] == gid:
        continue
    pa, pd = f(u["pmra_formula"]), f(u["pmdec_formula"])
    spa, spd = f(u["pmraerr_formula"]) or 0.0, f(u["pmdecerr_formula"]) or 0.0
    ga, gd, sga, sgd = (f(r[k]) for k in ("pmRA", "pmDE", "e_pmRA", "e_pmDE"))
    mu = math.hypot(pa, pd)
    da, dd = ga - pa, gd - pd
    dmu = math.hypot(da, dd)
    sig = math.sqrt(((da ** 2) * (spa ** 2 + sga ** 2) + (dd ** 2) * (spd ** 2 + sgd ** 2)) / dmu ** 2) if dmu > 0 else 0.0
    pm_ok = dmu < max(3 * sig, 0.1 * mu)
    gp, sgp = float(r["Plx"]), float(r["e_Plx"])
    up, sup = f(u["plx_formula"]), f(u["plxerr_formula"])
    ud, sud = f(u["dist_formula"]), f(u["disterr_formula"]) or 0.0
    if up is not None and sup is not None:
        plx_mode = "trig"
        dpl = gp - up
        plx_sig = math.hypot(sgp, sup)
        plx_ok = abs(dpl) < max(3 * plx_sig, 0.2 * up)
        plx_n = dpl / plx_sig
    else:
        plx_mode = "phot:" + u["dist_formula_source"]
        dg = 1000 / gp
        sdg = dg * sgp / gp
        dpl = dg - ud
        plx_sig = math.hypot(sdg, sud)
        plx_ok = abs(dpl) < max(3 * plx_sig, 0.2 * ud)
        plx_n = dpl / plx_sig if plx_sig else float("nan")
    d_host = 1000 / gp if gp / sgp > 5 else (1000 / up if up else ud)
    sep_au = sep * d_host
    if not (pm_ok and plx_ok and sep_au < 10000):
        continue
    G, BP, RP = (f(r[k]) for k in ("Gmag", "BPmag", "RPmag"))
    bprp = BP - RP if BP is not None and RP is not None else None
    MGh = G + 5 * math.log10(gp / 100) if G is not None else None
    mh, mh_src = host_mass(MGh, bprp, r["Source"])
    dvt = 4.74047 * dmu / 1000 * d_host
    sdvt = 4.74047 * sig / 1000 * d_host
    vesc = 29.7847 * math.sqrt(2 * ((mh or 0) + ucd_mass(None)) / sep_au)
    out.append(dict(
        uid=r["uid"], ucd=u["name"], ucd_spt_opt=u["spt_opt"], ucd_spt_ir=u["spt_ir"], ucd_G=u["G_Gaia"], ucd_gaia=gid,
        ucd_pmra=pa, ucd_pmdec=pd, ucd_pmerr=f"{spa}/{spd}", ucd_ref_pm=u["ref_pm_formula"],
        ucd_plx=up, ucd_plxerr=sup, ucd_ref_plx=u["ref_plx_formula"], ucd_dist=ud, ucd_disterr=sud, ucd_dist_src=u["dist_formula_source"],
        gaia=r["Source"], g_ra=r["RA_ICRS"], g_dec=r["DE_ICRS"], g_pmra=ga, g_pmdec=gd, g_epm=f"{sga}/{sgd}",
        g_plx=gp, g_eplx=sgp, G=G, BP_RP=round(bprp, 3) if bprp is not None else None, M_G=round(MGh, 2) if MGh is not None else None,
        RUWE=r["RUWE"], RV=r["RV"], sep_arcsec=round(sep, 2), sep_au=round(sep_au), dmu=round(dmu, 2), dmu_sig=round(sig, 2),
        dmu_over_sig=round(dmu / sig, 2) if sig else None, plx_mode=plx_mode, plx_dev_sigma=round(plx_n, 2),
        dvtan_kms=round(dvt, 2), dvtan_err=round(sdvt, 2), host_mass=round(mh, 3) if mh else None, host_mass_src=mh_src,
        vesc_kms=round(vesc, 2), bound_ok=dvt - 2 * sdvt < vesc,
        ucs_multi_unres=u["multiplesystem_unresolved_in_this_table"], ucs_multi_res=u["multiplesystem_resolved_in_this_table"],
        ucs_higher_mass_comp=u["has_higher_mass_companion"], ucs_sep_comp=u["sep_companion"], ucs_note=u["note"],
        ucs_simbad=u["name_simbad"], ucs_ids=u["identifiers_simbad"][:300]))
out.sort(key=lambda x: (x["ucd"], x["sep_arcsec"]))
Path("out").mkdir(exist_ok=True)
with open("out/pairs_cut.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0]))
    w.writeheader()
    w.writerows(out)
print("pairs after strict cuts:", len(out), "UCDs:", len({o["uid"] for o in out}))
