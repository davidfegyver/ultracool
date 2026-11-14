import os
from pathlib import Path

CACHE_DIR = Path(os.getenv("CACHE_DIR", "/data/cache"))
S3_MAX_CONCURRENCY = int(os.getenv("S3_MAX_CONCURRENCY", "16"))
IRSA_MAX_CONCURRENCY = int(os.getenv("IRSA_MAX_CONCURRENCY", "2"))
