"""Fetch each validation field through the dev API (one at a time) and save /summary and /spectrum.
python run_fields.py  (API_URL default http://127.0.0.1:8002); resumable: skips objects with summary.json."""
import json, os, re, time, urllib.request, urllib.parse
API = os.getenv("API_URL", "http://127.0.0.1:8002")
HERE = os.path.dirname(os.path.abspath(__file__))

def call(path, body=None, timeout=900):
    req = urllib.request.Request(API + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)

for line in open(os.path.join(HERE, "targets.jsonl")):
    o = json.loads(line)
    slug = re.sub(r"[^\w+-]+", "_", o["q"]).strip("_")
    d = os.path.join(HERE, "before", slug)
    if os.path.exists(os.path.join(d, "summary.json")):
        continue
    os.makedirs(d, exist_ok=True)
    body = {"ra": o["ra"], "dec": o["dec"], "pmra_masyr": o["pm"][0], "pmdec_masyr": o["pm"][1], "epoch_yr": o["ep"]}
    t0 = time.time()
    sid = o.get("copied_sid") or call("/api/sequences", body)["id"]
    while (m := call(f"/api/sequences/{sid}"))["status"] not in ("done", "error"):
        time.sleep(15)
    fetch_s = time.time() - t0
    s = call(f"/api/sequences/{sid}/spectrum")
    json.dump(s, open(os.path.join(d, "spectrum.json"), "w"), indent=1)
    su = call(f"/api/sequences/{sid}/summary")
    json.dump(su, open(os.path.join(d, "summary.json"), "w"), indent=1)
    json.dump({"object": o, "request": body, "sid": sid, "status": m["status"], "n_frames": len(m["frames"]),
               "fetch_s": round(fetch_s)}, open(os.path.join(d, "meta.json"), "w"), indent=1)
    sp = su["spectrum"]
    print(slug, sid, m["status"], len(m["frames"]), round(fetch_s), sp["verdict"], (sp.get("best") or {}).get("label"), flush=True)
