#!/bin/bash
# Night-2 pipeline, one object at a time (IRSA: one new field at a time).
# Usage: ./run3.sh <list> [devonly]
#  1. dev_run.py: current production code on the private dev API (spectrum typing, /summary motion+colour, /movers)
#  2. verify.py (frozen snapshot, validated on 2M0415/J1122): per-visit astrometry; track.py: catalogue-free track;
#     forced.py: 2-yr deep epochs from a static guess; wphot.py: W1/W2; attach dev result; plot.py: montage
cd /data/research/discovery
PY=/home/paw/Desktop/ultracool/.venv/bin/python
export CACHE_DIR=/data/research/discovery/cache IRSA_MAX_CONCURRENCY=1 S3_MAX_CONCURRENCY=8
while read n ra dec pmra pmdec ep des; do
  [ -z "$n" ] && continue
  [ -f out/${n}_dev.json ] || nice -n 15 $PY dev_run.py $n $ra $dec $pmra $pmdec $ep 2>&1 | grep -v "WARNING"
  [ "$2" = devonly ] && continue
  if [ ! -f out/$n.json ] || ! grep -q '"fit_deep"' out/$n.json; then
    PYTHONPATH=snap nice -n 15 $PY verify.py $n $ra $dec $pmra $pmdec $ep 2>&1 | grep -v "IRSA call failed\|WARNING\|read fail\|IBE cutout"
    $PY track.py out/$n.json
    PYTHONPATH=snap $PY forced.py $n
    $PY wphot.py $n
  fi
  $PY -c "import json,sys;p=f'out/{sys.argv[1]}.json';r=json.load(open(p));r['dev']=json.load(open(f'out/{sys.argv[1]}_dev.json'));json.dump(r,open(p,'w'),default=float)" $n
  $PY plot.py out/$n.json
done < $1
