"""Resumable batch precompute through the running API: sequences + /summary (+ /movers) for many objects.

    API_URL=http://localhost:8000 python -m scripts.batch --spt-min T0 --spt-max Y1 --movers
    API_URL=... python -m scripts.batch --csv targets.csv          # columns ra,dec[,pmra,pmdec,epoch_yr,name]

Objects come from the SPIFF ultracool-dwarf catalog (app/data/ucd_catalog.csv, filter by --spt-min/--spt-max/
--dataset) or a CSV. By default every name goes through /api/resolve (SIMBAD, then the CatWISE proper-motion
fallback): without a proper motion fast movers are lost (ULAS J0007+0112 came out "not moving", typed M8).
--resolve designations only resolves CWISE/WISEA/... names; --resolve none never resolves. Progress and ETA go
to stdout, one JSON line per finished object to --state; a restart skips objects already done there (errors are
retried).
Goes through the API (not in-process) so the server's job registry owns every sequence manifest.
"""
import argparse
import csv
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

from scripts.prewarm import API, call

NEW_QUERIES = threading.Semaphore(2)  # politeness: <= 2 objects in resolve + IRSA SIA query at a time
DESIG_PREFIX_RE = re.compile(r"^C?WISE\w*\s*J\d")  # CWISE, CWISEP, WISE, WISEA, WISEPA, WISEPC, ... J<coords>
POLL_S = 10


def spiff_objects(spt_min, spt_max, dataset):
    from fastapi import HTTPException

    from app import ucd  # the server's own catalog and spectral-type filter
    try:
        rows = ucd.search(spt_min, spt_max, dataset, limit=len(ucd.ROWS))
    except HTTPException as e:
        sys.exit(e.detail)
    return [{"name": r["designation"], "ra": r["ra"], "dec": r["dec"]} for r in rows]


def csv_objects(path):
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            o = {"ra": float(r["ra"]), "dec": float(r["dec"]), "name": r.get("name") or None}
            for k in ("pmra", "pmdec"):
                if r.get(k):
                    o[f"{k}_masyr"] = float(r[k])
            if r.get("epoch_yr"):
                o["epoch_yr"] = float(r["epoch_yr"])
            yield o


def key_of(o):
    return o["name"] or f"{o['ra']:.5f},{o['dec']:.5f}"


def target_body(o, mode):
    """Sequence request for an object: /api/resolve for designations (CatWISE motion), else its position."""
    body = {"ra": o["ra"], "dec": o["dec"], "pmra_masyr": o.get("pmra_masyr", 0.0),
            "pmdec_masyr": o.get("pmdec_masyr", 0.0), "epoch_yr": o.get("epoch_yr", 2000.0)}
    if o["name"] and (mode == "all" or (mode == "designations" and DESIG_PREFIX_RE.match(o["name"]))):
        try:
            r = call("/api/resolve?" + urllib.parse.urlencode({"q": o["name"]}), timeout=300)
            # a resolver hit far from the catalog position is another object: keep the catalog's
            if abs(r["dec"] - o["dec"]) < 0.01 and abs((r["ra"] - o["ra"] + 180) % 360 - 180) < 0.02:
                body = {k: r[k] for k in ("ra", "dec", "pmra_masyr", "pmdec_masyr", "epoch_yr")}
        except (urllib.error.URLError, TimeoutError, KeyError) as e:
            print(f"  resolve failed for {o['name']}: {e}; using catalog position", flush=True)
    return body


def process(o, args):
    t0 = time.time()
    out = {"key": key_of(o), "name": o["name"]}
    with NEW_QUERIES:  # resolve + POST + IRSA frame discovery ("querying")
        body = target_body(o, args.resolve)
        sid = call("/api/sequences", body)["id"]
        out.update(sid=sid, request=body)
        while (m := call(f"/api/sequences/{sid}"))["status"] == "querying":
            time.sleep(2)
    while m["status"] not in ("done", "error"):
        time.sleep(POLL_S)
        m = call(f"/api/sequences/{sid}")
    out.update(status=m["status"], error=m.get("error"), frames=len(m["frames"]))
    if m["status"] == "done":
        s = call(f"/api/sequences/{sid}/summary")
        out["summary"] = {"motion": s["motion"]["verdict"], "pm_arcsec_yr": s["motion"]["pm_total_arcsec_yr"],
                          "color": s["color"]["verdict"], "w1_w2": s["color"]["w1_w2"],
                          "variability": s["variability"]["verdict"], "spectrum": s["spectrum"]["verdict"],
                          "best": (s["spectrum"].get("best") or {}).get("label")}
        if args.movers:
            mv = call(f"/api/sequences/{sid}/movers")
            out["movers"] = len(mv["movers"])
    out["seconds"] = round(time.time() - t0, 1)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", help="CSV with ra,dec[,pmra,pmdec,epoch_yr,name] instead of the SPIFF catalog")
    ap.add_argument("--spt-min", help="SPIFF autotype lower bound, e.g. T0")
    ap.add_argument("--spt-max", help="SPIFF autotype upper bound, e.g. Y1")
    ap.add_argument("--dataset", help="SPIFF dataset, exact (see /api/ucds/datasets)")
    ap.add_argument("--limit", type=int, help="at most this many objects (after filtering and skipping done ones)")
    ap.add_argument("--concurrency", type=int, default=max(1, (os.cpu_count() or 2) // 2),
                    help="sequences in flight (default: cores / 2)")
    ap.add_argument("--movers", action="store_true", help="also warm /movers")
    ap.add_argument("--resolve", choices=["designations", "all", "none"], default="all")
    ap.add_argument("--state", default="batch_state.jsonl", help="JSON lines, one per finished object")
    args = ap.parse_args()

    done = set()
    if os.path.exists(args.state):
        with open(args.state) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue  # a line cut by a crash
                if r.get("status") == "done":
                    done.add(r["key"])
    objs = csv_objects(args.csv) if args.csv else spiff_objects(args.spt_min, args.spt_max, args.dataset)
    todo = [o for o in objs if key_of(o) not in done][:args.limit]
    print(f"{len(todo)} objects to do, {len(done)} already done; concurrency {args.concurrency}; API {API}", flush=True)
    lock = threading.Lock()
    t_start, n_ok, n_err = time.time(), 0, 0

    def run(o):
        nonlocal n_ok, n_err
        try:
            r = process(o, args)
        except Exception as e:  # noqa: BLE001 - one bad object must not stop a multi-day run
            r = {"key": key_of(o), "name": o["name"], "status": "error", "error": f"{type(e).__name__}: {e}"}
        with lock:
            with open(args.state, "a") as fh:
                fh.write(json.dumps(r) + "\n")
            n_ok += r["status"] == "done"
            n_err += r["status"] != "done"
            n = n_ok + n_err
            eta = (time.time() - t_start) / n * (len(todo) - n)
            print(f"[{n}/{len(todo)}] {r['key']}: {r['status']} {r.get('seconds', '')}s "
                  f"{json.dumps(r.get('summary')) if r.get('summary') else r.get('error') or ''} "
                  f"| errors {n_err} | ETA {eta / 3600:.1f} h", flush=True)

    with ThreadPoolExecutor(args.concurrency) as pool:
        list(pool.map(run, todo))
    print(f"finished: {n_ok} done, {n_err} errors in {(time.time() - t_start) / 3600:.2f} h", flush=True)


if __name__ == "__main__":
    main()
