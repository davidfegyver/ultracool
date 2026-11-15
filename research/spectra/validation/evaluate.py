"""Recompute colour + typed spectrum for every validation field with the `app` package on PYTHONPATH.

    CACHE_DIR=/data/devcache/spectra PYTHONPATH=<backend dir> python evaluate.py <out_dir>

Reads targets.jsonl and before/<slug>/meta.json (sequence id), calls analysis._summary uncached (same code path
as /summary) and writes <out_dir>/<slug>.json = {sid, spectrum, color, plain}."""
import json
import os
import re
import sys

from app import analysis
from app.sequences import get_manifest

HERE = os.path.dirname(os.path.abspath(__file__))
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
only = set(sys.argv[2:])
for line in [x for f in ("targets.jsonl", "extra_targets.jsonl") for x in open(os.path.join(HERE, f))]:
    o = json.loads(line)
    slug = re.sub(r"[^\w+-]+", "_", o["q"]).strip("_")
    meta = os.path.join(HERE, "before", slug, "meta.json")
    if not os.path.exists(meta) or (only and slug not in only):
        continue
    sid = json.load(open(meta))["sid"]
    s = analysis._clean(analysis._summary(get_manifest(sid)))
    json.dump({"sid": sid, "spectrum": s["spectrum"], "color": s["color"], "plain": s["plain"]},
              open(os.path.join(out, slug + ".json"), "w"), indent=1)
    sp = s["spectrum"]
    print(slug, sp["verdict"], (sp.get("best") or {}).get("label"), sp.get("type_range"), flush=True)
