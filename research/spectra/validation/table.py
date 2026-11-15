"""Confusion table: literature vs SPHEREx template type for one result set.

    python table.py before   # before/<slug>/summary.json (dev API, baseline code)
    python table.py after    # after/<slug>.json (evaluate.py with the new code)

Writes table_<set>.json and table_<set>.md next to this file."""
import json
import os
import re
import sys

from astropy.coordinates import SkyCoord

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = {"M": 0, "L": 10, "T": 20, "Y": 30}
Y_MAX = 31.0  # Y1, the last template


def spt(s):
    m = re.search(r"([MLTY])(\d+(?:\.\d+)?)", s or "")
    return BASE[m.group(1)] + float(m.group(2)) if m else None


def fmt(v):
    if v is None:
        return "-"
    k = "MLTY"[min(3, int(v // 10))]
    x = v - BASE[k]
    return f"{k}{x:g}"


def load(which, slug):
    p = os.path.join(HERE, "before", slug, "summary.json") if which == "before" else os.path.join(HERE, which, slug + ".json")
    return json.load(open(p)) if os.path.exists(p) else None


which = sys.argv[1]
lit = json.load(open(os.path.join(HERE, "lit.json")))
rows = []
for line in [x for f in ("targets.jsonl", "extra_targets.jsonl") for x in open(os.path.join(HERE, f))]:
    o = json.loads(line)
    slug = re.sub(r"[^\w+-]+", "_", o["q"]).strip("_")
    r = load(which, slug)
    if r is None:
        continue
    sp = r["spectrum"]
    L = lit[o["q"]]
    lv = spt(L["lit"])
    b = SkyCoord(o["ra"], o["dec"], unit="deg").galactic.b.deg
    best = (sp.get("best") or {}).get("label") or ((sp.get("ranking") or [{}])[0].get("label"))
    ov = spt(best)
    d = None if lv is None or ov is None else ov - min(lv, Y_MAX)
    rows.append({"object": o["q"], "slug": slug, "role": L["role"], "lit": L["lit"], "lit_src": L["src"],
                 "binary": bool(L.get("binary")), "gal_b": round(b, 1), "crowded": bool(abs(b) < 15),
                 "verdict": sp["verdict"], "typed": sp["verdict"] == "match", "label": best,
                 "type_range": sp.get("type_range"),
                 "chi2_red": (sp.get("best") or (sp.get("ranking") or [{}])[0]).get("chi2_red"),
                 "detection_snr": sp.get("detection_snr"), "negative_bins": sp.get("negative_bins"),
                 "contamination": sp.get("contamination"), "reason": sp.get("reason") or sp.get("doubt"),
                 "delta": d})


def stats(rs):
    ucd = [r for r in rs if r["role"] == "ucd" and r["lit"]]
    typed = [r for r in ucd if r["typed"] and r["delta"] is not None]
    n = len(typed)
    in_range = [r for r in typed if r["type_range"] and spt(r["type_range"][0]) - 0.01 <= min(spt(r["lit"]), Y_MAX) <= spt(r["type_range"][1]) + 0.01]
    return {"n_ucd_with_lit": len(ucd), "n_typed": n,
            "within_1": sum(abs(r["delta"]) <= 1 for r in typed), "within_2": sum(abs(r["delta"]) <= 2 for r in typed),
            "mean_abs_delta": round(sum(abs(r["delta"]) for r in typed) / n, 2) if n else None,
            "lit_in_type_range": len(in_range) if any(r["type_range"] for r in typed) else None,
            "controls": sum(r["role"] == "control" for r in rs),
            "false_match_controls": [r["object"] for r in rs if r["role"] == "control" and r["typed"]]}


st = stats(rows)
json.dump({"set": which, "stats": st, "rows": rows}, open(os.path.join(HERE, f"table_{which}.json"), "w"), indent=1)
md = ["| object | lit. | role | b | our verdict | best | range | Δ | χ²ᵣ | det S/N | note |", "|" + "---|" * 11]
for r in rows:
    tr = "–".join(r["type_range"]) if r["type_range"] else ""
    md.append(f"| {r['object']} | {r['lit'] or '-'}{' (bin.)' if r['binary'] else ''} | {r['role']} | {r['gal_b']} | "
              f"{r['verdict']} | {r['label'] or '-'} | {tr} | {'' if r['delta'] is None else f'{r['delta']:+g}'} | "
              f"{'' if r['chi2_red'] is None else f'{r['chi2_red']:.1f}'} | "
              f"{'' if r['detection_snr'] is None else f'{r['detection_snr']:.0f}'} | {r['reason'] or ''} |")
md.append("")
md.append("stats: " + json.dumps(st))
open(os.path.join(HERE, f"table_{which}.md"), "w").write("\n".join(md) + "\n")
print("\n".join(md))
