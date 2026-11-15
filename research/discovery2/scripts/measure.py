"""Measure one screened candidate on the private dev API (current backend working tree, see CODE_STATE_dev_api.txt).
POST /api/sequences (CatWISE2020 II/365 PM-fit position at 2015.4 + offset-corrected PM, default fov), wait for 'done',
then save /summary, /spectrum, /export.csv and the manifest status to out/<tag>/, plus metrics.json.
Usage: python scripts/measure.py <tag> [api=http://127.0.0.1:8004]   (tag from out/screen.json; cwd = research/discovery2)"""
import json
import sys
import time
from pathlib import Path

import httpx
import numpy as np
from astropy.table import Table

tag = sys.argv[1]
API = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8004"
row = next(r for r in json.loads(Path("out/screen.json").read_text()) if r["tag"] == tag)
cw = Table.read("raw/screen_II_365_catwise_15.ecsv")
t = next(x for x in cw if str(x["Name"]) == row["cw_name"])
body = {"ra": float(t["RAPMdeg"]), "dec": float(t["DEPMdeg"]), "pmra_masyr": float(t["pmRA"]) * 1000,
        "pmdec_masyr": float(t["pmDE"]) * 1000, "epoch_yr": 2015.4}  # II/365: PM-fit position at MJD 57170 = 2015.4
d = Path("out") / tag
d.mkdir(parents=True, exist_ok=True)
c = httpx.Client(base_url=API, timeout=900)
t0 = time.time()
sid = c.post("/api/sequences", json=body).json()["id"]
while (m := c.get(f"/api/sequences/{sid}").json())["status"] not in ("done", "error"):
    time.sleep(15)
t_seq = time.time() - t0


def poll(path):
    for _ in range(12):  # _transient: an external catalogue call failed; retry for 3 min, then keep what we have
        r = c.get(path).json()
        if not r.get("_transient"):
            return r
        time.sleep(15)
    return r


summ = poll(f"/api/sequences/{sid}/summary")
spec = c.get(f"/api/sequences/{sid}/spectrum").json()
(d / "summary.json").write_text(json.dumps(summ, indent=1))
(d / "spectrum.json").write_text(json.dumps(spec, indent=1))
(d / "export.csv").write_text(c.get(f"/api/sequences/{sid}/export.csv").text)
b = spec.get("binned") or []
lam = np.array([x["wavelength_um"] for x in b]); f = np.array([x["flambda"] for x in b]); e = np.array([x["err"] for x in b])
snr = f / e if len(b) else np.array([])
red = (lam >= 3.5) & (lam <= 5.0) if len(b) else np.array([], bool)
mo, co, sp = summ["motion"], summ["color"], summ["spectrum"]
metrics = {
    "tag": tag, "name": row["name"], "request": body, "api": API, "seq_id": sid, "status": m["status"],
    "pipeline_version": m.get("pipeline_version"), "n_spherex": sum(x["survey"] == "spherex" for x in m["frames"]),
    "n_wise": sum(x["survey"] == "wise" for x in m["frames"]), "seconds_sequence": round(t_seq),
    "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "summary_transient": summ.get("_transient"),
    "spectrum": {k: sp.get(k) for k in ("verdict", "best", "type_range", "detection_snr", "photometry", "neighbour_frac",
                                         "contamination", "contaminated", "negative_bins", "blends_arcsec", "reason", "doubt", "water_depth")},
    "ranking": sp.get("ranking"),
    "n_bins": len(b), "n_bins_snr_gt3": int(np.sum(snr > 3)), "n_bins_snr_gt5": int(np.sum(snr > 5)),
    "max_bin_snr": float(snr.max()) if len(b) else None, "median_bin_snr": float(np.median(snr)) if len(b) else None,
    # inverse-variance combined 3.5-5 um flux S/N (the same quantity as detection_snr, recomputed from the bins)
    "snr_3p5_5um": float(np.sum(f[red] / e[red] ** 2) / np.sqrt(np.sum(1 / e[red] ** 2))) if red.any() else None,
    "neighbour_psf_used": sp.get("photometry") == "neighbour-subtracted PSF fit",
    "spectrum_endpoint_verdict": spec.get("verdict"), "spectrum_endpoint_best": spec.get("best"),
    "motion": {k: mo.get(k) for k in ("verdict", "pmra_masyr", "pmdec_masyr", "pm_err_masyr", "pmra_err_masyr", "pmdec_err_masyr",
                                      "significance_sigma", "n_epochs", "baseline_yr", "recovered", "undetected_bands", "catalog_offset_sigma")},
    "color": {k: co.get(k) for k in ("verdict", "w1_w2", "w1_w2_err", "w1_w2_is_lower_limit", "w1", "w2", "source", "note")},
    "plain": summ.get("plain"),
}
(d / "metrics.json").write_text(json.dumps(metrics, indent=1, default=float))
s = metrics["spectrum"]
print(tag, sid, m["status"], metrics["n_spherex"], "SX", metrics["n_wise"], "W", f"{t_seq:.0f}s |", s["verdict"], (s["best"] or {}).get("label"),
      (s["best"] or {}).get("chi2_red"), s["type_range"], "| det", s["detection_snr"], "bins>3", metrics["n_bins_snr_gt3"], "| psf",
      metrics["neighbour_psf_used"], s["neighbour_frac"], "| PM", mo.get("pmra_masyr"), mo.get("pmdec_masyr"), mo.get("significance_sigma"),
      "| W1-W2", co.get("w1_w2"), s.get("reason") or s.get("doubt"), flush=True)
