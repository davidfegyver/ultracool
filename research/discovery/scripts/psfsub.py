"""Azimuthal-median subtraction of a bright neighbour in the per-visit W2 stacks, then forced S/N at the candidate's
predicted position. Usage: python psfsub.py <name> <bright_x> <bright_y> (grid px, approx)"""
import json, sys, numpy as np
name, bx, by = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
r = json.load(open(f"out/{name}.json")); st = np.load(f"out/{name}_stamps.npz")
ep = {f"{e['band']}_{e['mjd']:.1f}": e for e in r["epochs"] if e["survey"] == "wise"}
yy, xx = np.indices(st[st.files[0]].shape)
rows = []
for k, e in ep.items():
    z = st[k]
    d = min(e["dets"], key=lambda d: np.hypot(d[0]-bx, d[1]-by))  # bright star centroid this visit
    rr = np.hypot(xx-d[0], yy-d[1])
    prof = np.array([np.nanmedian(z[(rr >= i) & (rr < i+1)]) for i in range(40)])
    model = np.interp(rr, np.arange(40)+0.5, prof)
    res = z - model
    px, py = e["pred"]
    ap = np.hypot(xx-px, yy-py) <= 1.5
    ctrl = [np.nansum(res[np.hypot(xx-(d[0]+(px-d[0])*np.cos(t)-(py-d[1])*np.sin(t)), yy-(d[1]+(px-d[0])*np.sin(t)+(py-d[1])*np.cos(t))) <= 1.5]) for t in np.linspace(0.5, 2*np.pi-0.5, 12)]
    rows.append((k, float(np.nansum(res[ap])), float(np.median(ctrl)), float(np.std(ctrl))))
    np.save(f"out/{name}_res_{k}.npy", res)
for k, s, m, sd in rows: print(k, f"aperture={s:.1f} ring-median={m:.1f} ring-std={sd:.1f} -> excess {(s-m)/sd:.1f} sigma")
