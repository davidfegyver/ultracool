"""Robustness of a SPHEREx template type (lesson 3 of research/verification/J2317_ADVERSARIAL.md): refit the binned
spectra (production = r["dev"] summary, snapshot = r["spectrum"]) with the production fit (analytic scale, template
spread in quadrature; same as research/verification/spectral_refit.py) in five variants: all bins with/without template
spread, 1.0-2.5 um only, 2.5-5.0 um only, errors x1.5. A subtype is 'separable' only if every variant picks it.
Writes r["type_variants"] into out/<name>.json. Usage: python variants.py <name> ..."""
import json
import sys
from pathlib import Path

import numpy as np

CODE = sorted(Path("/data/devcache/candidates_code").glob("backend_*"))[-1]
sys.path.insert(0, str(CODE))
from app.spectral import TEMPLATES  # noqa: E402  read-only: the vendored SPIFF templates of the dev-API code snapshot


def fit1(lam, f, s, t, use_tu=True):
    m = (lam >= t[0, 0]) & (lam <= t[-1, 0])
    if m.sum() < 3:
        return None
    tm, tu = np.interp(lam[m], t[:, 0], t[:, 1]), np.interp(lam[m], t[:, 0], t[:, 2]) * use_tu
    ff, ss = f[m], s[m]
    a = np.sum(ff * tm / ss**2) / np.sum(tm**2 / ss**2)
    for _ in range(2):
        st = np.hypot(ss, a * tu)
        a = np.sum(ff * tm / st**2) / np.sum(tm**2 / st**2)
    return float(np.sum(((ff - a * tm) / np.hypot(ss, a * tu)) ** 2)), int(m.sum())


def rank(lam, f, s, use_tu=True):
    rows = sorted((c / (n - 1), lab) for lab, t in TEMPLATES.items() if (r := fit1(lam, f, s, t, use_tu)) for c, n in [r])
    return [(lab, round(c, 2)) for c, lab in rows[:4]]


for name in sys.argv[1:]:
    p = Path(f"out/{name}.json")
    r = json.loads(p.read_text())
    out = {"code_snapshot": str(CODE)}
    for src, b in (("production", (((r.get("dev") or {}).get("summary") or {}).get("spectrum") or {}).get("binned")),
                   ("snapshot", r["spectrum"].get("binned"))):
        if not b:
            continue
        lam = np.array([x["wavelength_um"] for x in b]); f = np.array([x["flambda"] for x in b]); s = np.array([x["err"] for x in b])
        v = {"all": rank(lam, f, s), "all_no_spread": rank(lam, f, s, False), "1.0-2.5um": rank(lam[lam < 2.5], f[lam < 2.5], s[lam < 2.5]),
             "2.5-5.0um": rank(lam[lam >= 2.5], f[lam >= 2.5], s[lam >= 2.5]), "err_x1.5": rank(lam, f, s * 1.5)}
        bests = {k: x[0][0] for k, x in v.items() if x}
        out[src] = {"variants": v, "best_per_variant": bests, "separable": len(set(bests.values())) == 1}
        print(name, src, "separable" if out[src]["separable"] else "NOT separable", bests)
        for k, x in v.items():
            print("   ", k, x)
    r["type_variants"] = out
    p.write_text(json.dumps(r, default=float))
