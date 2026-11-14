import os
from pathlib import Path

CACHE_DIR = Path(os.getenv("CACHE_DIR", "/data/cache"))
S3_MAX_CONCURRENCY = int(os.getenv("S3_MAX_CONCURRENCY", "16"))
IRSA_MAX_CONCURRENCY = int(os.getenv("IRSA_MAX_CONCURRENCY", "2"))
# frame processing (FITS parsing, reprojection, photometry) is GIL-bound: one worker process per core
WORKER_PROCESSES = int(os.getenv("WORKER_PROCESSES", str(min(4, os.cpu_count() or 1))))
