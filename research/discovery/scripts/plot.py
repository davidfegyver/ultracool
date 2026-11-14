"""Montage per candidate: W2/SPHEREx epoch stacks, astrometric track, SPHEREx spectrum. Usage: python plot.py out/<name>.json"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PIX = 2.75


def main(path):
    r = json.loads(Path(path).read_text())
    st = np.load(Path(path).with_name(r["name"] + "_stamps.npz"))
    keys = sorted([k for k in st.files if k.startswith("W2")], key=lambda k: float(k.split("_")[1]))
    sxk = sorted([k for k in st.files if k.startswith("SX")], key=lambda k: float(k.split("_")[1]))
    pick = [keys[i] for i in sorted(set(np.linspace(0, len(keys) - 1, min(5, len(keys))).round().astype(int)))] + sxk[:2] if keys else sxk[:2]
    ep = {f"{e['band'].split('>')[0] if e['survey']=='wise' else 'SX'}_{e['mjd']:.1f}": e for e in r["epochs"]}
    fig = plt.figure(figsize=(3 * max(len(pick), 4), 7))
    gs = fig.add_gridspec(2, max(len(pick), 4))
    for i, k in enumerate(pick):
        ax = fig.add_subplot(gs[0, i])
        z = st[k]
        e = ep.get(k)
        cx, cy = (e["pred"] if e else (z.shape[1] / 2, z.shape[0] / 2))
        h = 15
        # asinh in sigma units: 5-sigma sources visible, bright neighbours not saturated into blobs
        ax.imshow(np.arcsinh(z / 2), origin="lower", cmap="gray", vmin=-0.7, vmax=np.arcsinh(100), extent=(-0.5, z.shape[1] - 0.5, -0.5, z.shape[0] - 0.5))
        ax.set_xlim(cx - h, cx + h); ax.set_ylim(cy - h, cy + h)
        ax.add_patch(plt.Circle((cx, cy), 2.5, fill=False, color="cyan", lw=1))
        if e and e.get("target"):
            ax.plot(e["target"]["x"] + e["zp_offset_px"][0], e["target"]["y"] + e["zp_offset_px"][1], "r+", ms=10)
        yr = 2000 + (float(k.split("_")[1]) - 51544.5) / 365.25
        ax.set_title(f"{'W2' if k.startswith('W2') else 'SPHEREx >3.8um'} {yr:.1f}", fontsize=9)
        ax.set_xticks([]); ax.set_yticks([])
    pts = r["points"]
    deep = r.get("fit_deep") or {}
    use_deep = len(pts) < 10 and deep.get("fit")
    if use_deep:  # faint source: 2-yr deep-epoch centroids instead of per-visit detections
        pts = [{"mjd": 51544.5 + (q["year"] - 2000) * 365.25, "xi": q["dx_arcsec"], "eta": q["dy_arcsec"], "err": q["err_arcsec"], "survey": "wise"}
               for q in deep["epochs"] if q["detected"]]
    ax = fig.add_subplot(gs[1, :2])
    if pts:
        t = np.array([2000 + (p["mjd"] - 51544.5) / 365.25 for p in pts])
        for key, lab, c in (("xi", "east offset", "C0"), ("eta", "north offset", "C3")):
            v = np.array([p[key] for p in pts]); er = np.array([p["err"] for p in pts])
            sx = np.array([p["survey"] == "spherex" for p in pts])
            ax.errorbar(t[~sx], v[~sx], er[~sx], fmt="o", ms=3, color=c, label=lab + " (WISE)")
            if sx.any():
                ax.errorbar(t[sx], v[sx], er[sx], fmt="s", ms=5, mfc="none", color=c, label=lab + " (SPHEREx)")
        f = deep["fit"] if use_deep else r.get("fit_wise")
        if f:
            ax.set_title(f"WISE PM: ({f['pmra_masyr']:.0f}±{f['pmra_err']:.0f}, {f['pmdec_masyr']:.0f}±{f['pmdec_err']:.0f}) mas/yr", fontsize=9)
        ax.set_xlabel("year"); ax.set_ylabel("arcsec from grid centre"); ax.legend(fontsize=7)
    ax = fig.add_subplot(gs[1, 2:])
    s = r["spectrum"]
    b = s.get("binned") or []
    if b:
        lam = np.array([q["wavelength_um"] for q in b]); f = np.array([q["flambda"] for q in b]); e = np.array([q["err"] for q in b])
        ax.errorbar(lam, f, e, fmt="o", ms=3, color="k", label="SPHEREx (this work)")
        tc = s.get("template_curve")
        if tc:
            ax.plot(tc["wavelength_um"], tc["flambda"], "r-", label=f"SPIFF template {tc['label']}")
        ax.axhline(0, color="gray", lw=0.5)
        ax.set_xlabel("wavelength (um)"); ax.set_ylabel("F_lambda (uJy/um^2, arb.)"); ax.legend(fontsize=7)
        best = s.get("best")
        ax.set_title(f"{s['verdict']}" + (f": {best['label']} p={best['prob']:.2f} chi2r={best['chi2_red']:.1f}" if best else ""), fontsize=9)
    fig.suptitle(r["name"])
    fig.tight_layout()
    out = Path(path).with_name(r["name"] + "_montage.png")
    fig.savefig(out, dpi=90)
    print(out)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        main(p)
