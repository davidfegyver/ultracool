#!/bin/bash
cd /data/research/discovery
while read n ra dec pmra pmdec ep des; do
  [ -f out/$n.json ] && continue
  CACHE_DIR=/data/research/discovery/cache IRSA_MAX_CONCURRENCY=1 S3_MAX_CONCURRENCY=8 PYTHONPATH=snap /home/paw/Desktop/ultracool/.venv/bin/python verify.py $n $ra $dec $pmra $pmdec $ep 2>&1 | grep -v "IRSA call failed\|WARNING" 
done < ${1:-run_list.txt}
