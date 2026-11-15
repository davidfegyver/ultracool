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
# the frontend's "Examples" list (TargetBar) and the lessons' "Try it on another object" links (lessons.ts); keep in sync
TARGETS = ["Barnard's Star", "eps Ind B", "WISE J085510.83-071442.5", "RW Aur", "R Dra",
           "WISEA J153429.75-104303.3", "WISE J231728.42-665959.3", "AL Boo",
           "Proxima Cen", "Gl 229 B", "T Tau"]
# Discover-mode example fields (0.25 deg, the Discover field size); keep in sync with frontend Discover examples
DISCOVER = ["WISE J231728.42-665959.3", "WISEA J153429.75-104303.3", "eps Ind B"]
DISCOVER_FOV_DEG = 0.25
_EPS_IND_PM = {"pmra_masyr": 3966.661, "pmdec_masyr": -2536.192, "epoch_yr": 2000.0}
# Learn-mode fields whose request differs from a plain resolve; keep in sync with frontend/src/lessons.ts
LESSONS = {
    "lesson: move together (eps Ind A+B)": {"ra": 330.94218, "dec": -56.78441, "fov_deg": 0.2, **_EPS_IND_PM},
    "lesson: brightness (AL Boo)": {"ra": 204.73282996689997, "dec": 18.711619948339997, "pmra_masyr": -1.924,
                                    "pmdec_masyr": -1.836, "epoch_yr": 2000.0, "fov_deg": 0.05},
    "lesson: irregular (RW Aur)": {"ra": 76.95652603458333, "dec": 30.401438173888888, "pmra_masyr": 7.23,
                                   "pmdec_masyr": -20.33, "epoch_yr": 2000.0, "fov_deg": 0.05},
    "lesson: color (WISE 0855)": {"ra": 133.81890825, "dec": -7.247048, "pmra_masyr": -8123.7, "pmdec_masyr": 673.2,
                                  "epoch_yr": 2000.0, "fov_deg": 0.066},
    "lesson: moves (Barnard)": {"ra": 269.4520769586187, "dec": 4.693364966576667, "pmra_masyr": -801.551,
                                "pmdec_masyr": 10362.394, "epoch_yr": 2000.0, "fov_deg": 0.076},
    "lesson: ghost (eps Ind A)": {"ra": 330.8707, "dec": -56.78598, "fov_deg": 0.25, "mjd_min": 56770,
                                  "mjd_max": 57330, **_EPS_IND_PM},
    "lesson: asteroid (888 Parysatis)": {"ra": 5.9233, "dec": -17.2745, "pmra_masyr": 0.0, "pmdec_masyr": 0.0,
                                         "epoch_yr": 2000.0, "fov_deg": 0.25, "mjd_min": 58814.5,
                                         "mjd_max": 58816.0, "wise_exposures": True},
}


def call(path, body=None):
    req = urllib.request.Request(API + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def main():
    started = {}
    for q in TARGETS + [f"discover: {q}" for q in DISCOVER]:
        name = q.removeprefix("discover: ")
        r = call("/api/resolve?" + urllib.parse.urlencode({"q": name}))
        body = {k: r[k] for k in ("ra", "dec", "pmra_masyr", "pmdec_masyr", "epoch_yr")}
        if q.startswith("discover: "):
            body["fov_deg"] = DISCOVER_FOV_DEG
        started[q] = (call("/api/sequences", body)["id"], time.time())
    for name, body in LESSONS.items():
        started[name] = (call("/api/sequences", body)["id"], time.time())
    print("target, n_frames_spherex, n_frames_wise, seconds, status", flush=True)
    for q, (sid, t0) in started.items():
        while (m := call(f"/api/sequences/{sid}"))["status"] not in ("done", "error"):
            time.sleep(5)
        n = {s: sum(f["survey"] == s for f in m["frames"]) for s in ("spherex", "wise")}
        print(f"{q}, {n['spherex']}, {n['wise']}, {time.time() - t0:.1f}, {m['status']}", flush=True)
    # the first /summary of a field queries IRSA and SkyBoT (tens of seconds); warm it too
    for q, (sid, _) in started.items():
        try:
            call(f"/api/sequences/{sid}/summary")
            if q.startswith("discover: "):
                call(f"/api/sequences/{sid}/movers")
        except Exception as e:  # noqa: BLE001 - a failed warm-up only costs the first visitor time
            print(f"summary/movers warm-up failed for {q}: {e}", flush=True)


if __name__ == "__main__":
    main()
