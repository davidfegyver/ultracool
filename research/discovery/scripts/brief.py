"""Compact per-object facts for the report, all read from out/<name>.json (+ out/lit_<name>.json, UltracoolSheet v2.1.0).
Also K21 Table 13 spectrophotometric distance ranges (polynomials copied in research/verification/recompute.py).
Usage: python brief.py <name> ..."""
import csv
import json
import math
import sys

import numpy as np

UCS = list(csv.DictReader(open("ext/ultracoolsheet_v2.1.0_main.csv")))
K21_SPT_MCH2 = [1.0071e+01, 1.8897e-01, -6.2186e-02, 1.9711e-02, -2.3844e-03, 1.3230e-04, -3.3136e-06, 2.9971e-08]  # L0=0, T0=10; RMS 0.31 mag


def k21_dist(w2, t_lo, t_hi):
    """distance range (pc) for T subtypes t_lo..t_hi, widened by the 0.31 mag relation scatter"""
    ch2 = 0.070888 + 0.99268 * w2
    ds = [10 ** ((ch2 - sum(c * (10 + t) ** i for i, c in enumerate(K21_SPT_MCH2)) + 5) / 5) for t in np.arange(t_lo, t_hi + 0.01, 0.5)]
    return round(min(ds) * 10 ** (-0.31 / 5), 1), round(max(ds) * 10 ** (0.31 / 5), 1)


def ucs(ra, dec):
    best = None
    for r in UCS:
        try:
            d = math.hypot((float(r["ra_j2000_formula"]) - ra) * math.cos(math.radians(dec)), float(r["dec_j2000_formula"]) - dec) * 3600
        except ValueError:
            continue
        if best is None or d < best[0]:
            best = (d, r)
    return best


for n in sys.argv[1:]:
    r = json.load(open(f"out/{n}.json"))
    i = r["input"]
    print(f"===== {n}  input CatWISE pos/PM {i}")
    for k in ("fit_wise", "fit_wise_noplx"):
        f = r.get(k)
        if f:
            print(f"  {k}: ({f['pmra_masyr']:.0f}±{f['pmra_err']:.0f}, {f['pmdec_masyr']:.0f}±{f['pmdec_err']:.0f}) chi2r {f['chi2_red']:.1f} n {f['n']}")
    t = r.get("fit_track") or {}
    if "pmra" in t:
        print(f"  track: ({t['pmra']:.0f}±{t['pmra_err']:.0f}, {t['pmdec']:.0f}±{t['pmdec_err']:.0f}) n {t['n']}/{t['n_epochs']}")
    for k in ("fit_deep", "fit_blind"):
        f = (r.get(k) or {}).get("fit")
        if f:
            print(f"  {k}: ({f['pmra_masyr']:.0f}±{f['pmra_err']:.0f}, {f['pmdec_masyr']:.0f}±{f['pmdec_err']:.0f}) chi2r {f['chi2_red']:.1f} n {f['n']}")
        elif k in r:
            print(f"  {k}: no fit", {kk: v for kk, v in r[k].items() if kk in ("support", "n_windows")})
    wp = r.get("wise_phot") or {}
    print("  ours W1/W2:", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in wp.items() if not k.endswith("ujy")})
    dv = (r.get("dev") or {}).get("summary") or {}
    if dv:
        m, c, s = dv["motion"], dv["color"], dv["spectrum"]
        print(f"  prod motion: {m['verdict']} ({m.get('pmra_masyr') or 0:.0f}, {m.get('pmdec_masyr') or 0:.0f}) ±{m.get('pmra_err_masyr') or 0:.0f} sig {m.get('significance_sigma') or 0:.1f} consistent_with_cat {m.get('consistent_with_catalog')} undetected {m.get('undetected_bands')}")
        print(f"  prod colour: {c.get('w1_w2')} ± {c.get('w1_w2_err')} lower={c.get('w1_w2_is_lower_limit')} {c.get('verdict')}")
        b = s.get("binned") or []
        snr = np.array([q["flambda"] / q["err"] for q in b]) if b else np.zeros(1)
        print(f"  prod spectrum: {s['verdict']} best={s.get('best')} det_snr={s.get('detection_snr')} water={s.get('water_depth')} contam={s.get('contamination')} neg={s.get('negative_bins')} note={s.get('reason') or s.get('doubt')}")
        print(f"     bins {len(b)} S/N>3 {(snr > 3).sum()} S/N>5 {(snr > 5).sum()} ranking {[(q['label'], round(q['chi2_red'], 2)) for q in s.get('ranking') or []]}")
        mv = (r["dev"].get("movers") or {}).get("movers") or []
        print("  prod movers:", [(round(x['pmra_masyr']), round(x['pmdec_masyr']), round(x['significance_sigma'], 1), x['is_target'], x['known']) for x in mv])
    s = r["spectrum"]
    print(f"  snap spectrum: {s['verdict']} {s.get('best')} ranking {[(q['label'], round(q['chi2_red'], 2)) for q in s.get('ranking') or []][:4]}")
    try:
        L = json.load(open(f"out/lit_{n}.json"))
        b = (L.get("simbad_basic") or [{}])[0]
        print(f"  SIMBAD: {b.get('main_id')} otype {b.get('otype')} sp {b.get('sp_type')!r} refs {[x['bibcode'] for x in L.get('simbad_refs') or []]}")
        print(f"  VizieR ({L.get('vizier_status')}): SpT rows {[(x['table'], x['values'][:2]) for x in L.get('vizier_spt_rows') or []]}")
        print(f"  SIMBAD 30\": {[(x['main_id'], x['otype'], round(x['sep'], 1)) for x in L.get('simbad_cone30') or []]}")
    except FileNotFoundError:
        print("  no lit file")
    u = ucs(i["ra"], i["dec"])
    if u and u[0] < 15:
        print(f"  UltracoolSheet v2.1.0: {u[1]['name']} sep {u[0]:.1f}\" spt_opt {u[1]['spt_opt']} spt_ir {u[1]['spt_ir']} ({u[1]['ref_spt_ir']}) flag {u[1]['literature_flag']}")
    else:
        print("  UltracoolSheet v2.1.0: none within 15\"")
