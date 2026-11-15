"""Run one candidate through the CURRENT production code on the private dev API (port 8003, code snapshot recorded in
CODE_STATE.txt), and store manifest summary, /summary and /movers in out/<name>_dev.json.
Then copy the SIA cache entry so verify.py (frozen snapshot, same grid centre) makes no second IRSA SIA query.
Usage: python dev_run.py <name> <ra> <dec> <pmra> <pmdec> <epoch_yr> [api=http://127.0.0.1:8003]"""
import json
import shutil
import sys
import time
from pathlib import Path

import httpx

name, ra, dec, pmra, pmdec, ep = sys.argv[1], *map(float, sys.argv[2:7])
API = sys.argv[7] if len(sys.argv) > 7 else "http://127.0.0.1:8003"
DEV_CACHE = Path("/data/devcache/candidates")
CODE = sorted(Path("/data/devcache/candidates_code").glob("backend_*"))[-1]  # the snapshot the dev API was started from
c = httpx.Client(base_url=API, timeout=600)
t0 = time.time()
body = {"ra": ra, "dec": dec, "pmra_masyr": pmra, "pmdec_masyr": pmdec, "epoch_yr": ep, "fov_deg": 0.06}
sid = c.post("/api/sequences", json=body).json()["id"]
while True:
    m = c.get(f"/api/sequences/{sid}").json()
    if m["status"] in ("done", "error"):
        break
    time.sleep(10)
t_seq = time.time() - t0


def poll(path):
    for _ in range(12):  # transient = an external catalogue/SkyBoT call failed; give it 2 min, then keep what we have
        r = c.get(path).json()
        if not r.get("pending") and not r.get("_transient"):
            return r
        time.sleep(10)
    return r


summ = poll(f"/api/sequences/{sid}/summary")
mov = poll(f"/api/sequences/{sid}/movers")
out = {"name": name, "request": body, "api": API, "code_snapshot": str(CODE), "seq_id": sid, "status": m["status"],
       "pipeline_version": m.get("pipeline_version"), "n_frames": len(m["frames"]),
       "n_spherex": sum(f["survey"] == "spherex" for f in m["frames"]), "n_wise": sum(f["survey"] == "wise" for f in m["frames"]),
       "seconds_sequence": t_seq, "seconds_total": time.time() - t0, "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "summary": summ, "movers": mov}
Path(f"out/{name}_dev.json").write_text(json.dumps(out, default=float))
for p in (DEV_CACHE / "sia").glob("*.json"):
    q = Path("cache/sia") / p.name
    if not q.exists():
        shutil.copy2(p, q)
mo, sp, co = summ.get("motion", {}), summ.get("spectrum", {}), summ.get("color", {})
print(name, sid, m["status"], out["n_spherex"], "SX", out["n_wise"], "WISE", f"{out['seconds_total']:.0f}s |",
      "PM", mo.get("verdict"), mo.get("pmra_masyr") and round(mo["pmra_masyr"]), mo.get("pmdec_masyr") and round(mo["pmdec_masyr"]),
      mo.get("significance_sigma") and round(mo["significance_sigma"], 1), "| W1-W2", co.get("w1_w2") and round(co["w1_w2"], 2),
      "| spec", sp.get("verdict"), (sp.get("best") or {}).get("label"), (sp.get("best") or {}).get("chi2_red"), sp.get("reason") or sp.get("doubt"),
      "| movers", len(mov.get("movers", [])), flush=True)
