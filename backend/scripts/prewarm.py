"""Fill the disk cache for the demo targets: docker compose exec api python -m scripts.prewarm"""
import time

from app import sequences
from app.resolve import resolve
from app.sequences import SeqRequest

TARGETS = ["Barnard's Star", "eps Ind B", "WISE J085510.83-071442.5", "RW Aur", "R Dra"]


def main():
    started = {}
    for q in TARGETS:
        r = resolve(q)
        sid = sequences.start(SeqRequest(ra=r["ra"], dec=r["dec"], pmra_masyr=r["pmra_masyr"],
                                         pmdec_masyr=r["pmdec_masyr"], epoch_yr=r["epoch_yr"]))
        started[q] = (sid, time.time())
    print("target, n_frames_spherex, n_frames_wise, seconds, status", flush=True)
    for q, (sid, t0) in started.items():
        job = sequences.JOBS.get(sid)
        if job is not None:
            job.result()
        m = sequences.get_manifest(sid)
        n = {s: sum(f["survey"] == s for f in m["frames"]) for s in ("spherex", "wise")}
        print(f"{q}, {n['spherex']}, {n['wise']}, {time.time() - t0:.1f}, {m['status']}", flush=True)


if __name__ == "__main__":
    main()
