"""Our own W1/W2 from the app's forced visit photometry (sequence manifest): weighted mean flux -> Vega mag, W1-W2."""
import json, math, sys, numpy as np
F0 = {"W1": 309.540, "W2": 171.787}
for name in sys.argv[1:]:
    r = json.load(open(f"out/{name}.json"))
    m = json.load(open(f"cache/seq/{r['seq_id']}/manifest.json"))
    out = {}
    for b in ("W1", "W2"):
        fr = [f for f in m["frames"] if f["band"] == b and f["flux_ujy"] is not None and f["flux_err_ujy"]]
        f = np.array([x["flux_ujy"] for x in fr]); e = np.array([x["flux_err_ujy"] for x in fr]); w = 1 / e**2
        mu, se = (f * w).sum() / w.sum(), 1 / math.sqrt(w.sum())
        se *= max(1, math.sqrt(np.sum(w * (f - mu) ** 2) / (len(f) - 1)))  # scatter-inflated
        out[b] = (mu, se, -2.5 * math.log10(mu / (F0[b] * 1e6)) if mu > 0 else None, len(f))
    c = out["W1"][2] - out["W2"][2] if out["W1"][2] and out["W2"][2] else None
    ce = 1.0857 * math.hypot(out["W1"][1] / out["W1"][0], out["W2"][1] / out["W2"][0]) if c is not None else None
    lim = -2.5 * math.log10(3 * out["W1"][1] / (F0["W1"] * 1e6)) - out["W2"][2] if out["W2"][2] else None
    r["wise_phot"] = {"W1_ujy": out["W1"][:2], "W2_ujy": out["W2"][:2], "W1": out["W1"][2], "W2": out["W2"][2], "w1_w2": c, "w1_w2_err": ce, "w1_w2_3sig_lower": lim}
    json.dump(r, open(f"out/{name}.json", "w"), default=float)
    print(name, {k: (round(v, 2) if isinstance(v, float) else v) for k, v in r["wise_phot"].items() if not k.endswith("ujy")},
          "W1 uJy %.1f+-%.1f W2 uJy %.1f+-%.1f" % (*out["W1"][:2], *out["W2"][:2]))
