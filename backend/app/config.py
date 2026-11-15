import json
import os
import threading
from pathlib import Path

CACHE_DIR = Path(os.getenv("CACHE_DIR", "/data/cache"))
# frame processing (FITS parsing, reprojection, photometry) is GIL-bound: one worker process per core
WORKER_PROCESSES = int(os.getenv("WORKER_PROCESSES", str(os.cpu_count() or 1)))
# S3 byte-range reads are I/O-bound: ~8 in flight per worker keeps each core busy (S3 latency ~ processing time)
S3_MAX_CONCURRENCY = int(os.getenv("S3_MAX_CONCURRENCY", str(8 * WORKER_PROCESSES)))
IRSA_MAX_CONCURRENCY = int(os.getenv("IRSA_MAX_CONCURRENCY", "2"))
# sequences fetched at once; each orchestrator thread only waits on the shared worker pool
MAX_RUNNING_SEQUENCES = int(os.getenv("MAX_RUNNING_SEQUENCES", str(max(4, WORKER_PROCESSES))))


def write_json(path, obj):
    """Atomic JSON write: readers never see a half-written file (temp name per process and thread)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(obj))
    os.replace(tmp, path)
