"""Fill the disk cache for the demo targets: docker compose exec api python -m scripts.prewarm

Goes through the running API (not in-process) so the server's job registry owns every sequence:
two processes writing one manifest would drop frames.
"""
import json
import os
import time
import urllib.parse
import urllib.request

API = os.getenv("API_URL", "http://localhost:8000")
TARGETS = ["Barnard's Star", "eps Ind B", "WISE J085510.83-071442.5", "RW Aur", "R Dra"]


def call(path, body=None):
    req = urllib.request.Request(API + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def main():
    started = {}
    for q in TARGETS:
        r = call("/api/resolve?" + urllib.parse.urlencode({"q": q}))
        body = {k: r[k] for k in ("ra", "dec", "pmra_masyr", "pmdec_masyr", "epoch_yr")}
        started[q] = (call("/api/sequences", body)["id"], time.time())
    print("target, n_frames_spherex, n_frames_wise, seconds, status", flush=True)
    for q, (sid, t0) in started.items():
        while (m := call(f"/api/sequences/{sid}"))["status"] not in ("done", "error"):
            time.sleep(5)
        n = {s: sum(f["survey"] == s for f in m["frames"]) for s in ("spherex", "wise")}
        print(f"{q}, {n['spherex']}, {n['wise']}, {time.time() - t0:.1f}, {m['status']}", flush=True)


if __name__ == "__main__":
    main()
