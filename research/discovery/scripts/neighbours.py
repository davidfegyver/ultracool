"""Static-neighbour check for the SPHEREx aperture (production radius 2 native px = 12.3"). The production
contamination test needs the target to have moved >= ~31" (so it is inactive below ~0.5"/yr); this one simply lists
2MASS (II/246) and Gaia DR3 (I/355) sources within 15" of the CatWISE position (VizieR CfA mirror). A 2MASS J
brighter than ~16.5 inside 12.3" dominates a T dwarf's 1-2.5 um SPHEREx flux.
Writes out/nb_<name>.json. Usage: python neighbours.py <run list>"""
import json
import math
import sys
import urllib.request

R = 15


def cone(src, ra, dec, cols):
    url = (f"https://vizier.cfa.harvard.edu/viz-bin/asu-tsv?-source={src}&-c={ra:.6f}{dec:+.6f}&-c.rs={R}"
           f"&-out={','.join(cols)}&-out.add=_r")
    txt = urllib.request.urlopen(url, timeout=120).read().decode()
    if "QUERY_STATUS=ERROR" in txt:
        raise RuntimeError("VizieR error")
    lines = [l for l in txt.splitlines() if l and not l.startswith("#")]
    if len(lines) < 3:
        return url, []
    hdr = lines[0].split("\t")
    return url, [dict(zip(hdr, (v.strip() for v in l.split("\t")))) for l in lines[3:]]


for line in open(sys.argv[1]):
    n, ra, dec, *_ = line.split()
    ra, dec = float(ra), float(dec)
    out = {"name": n, "ra": ra, "dec": dec, "radius_arcsec": R}
    for key, src, cols in (("2mass", "II/246/out", ["2MASS", "Jmag", "Hmag", "Kmag"]),
                           ("gaia_dr3", "I/355/gaiadr3", ["Source", "Gmag", "RPmag", "PM"])):
        try:
            out[key + "_url"], out[key] = cone(src, ra, dec, cols)
        except Exception as e:  # noqa: BLE001
            out[key] = f"error: {e}"
    json.dump(out, open(f"out/nb_{n}.json", "w"), indent=1)
    j = [x for x in out["2mass"] if isinstance(out["2mass"], list) and x.get("Jmag")] if isinstance(out["2mass"], list) else []
    g = out["gaia_dr3"] if isinstance(out["gaia_dr3"], list) else []
    print(f"{n:11s} 2MASS<15\": {[(x['2MASS'], x['Jmag'], round(float(x['_r']), 1)) for x in j]} | Gaia: {[(x['Gmag'], round(float(x['_r']), 1)) for x in g]}")
