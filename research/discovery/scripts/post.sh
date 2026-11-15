#!/bin/bash
# After run3.sh: blind self-check astrometry + montage (matplotlib from ./pylib) for every finished object in a list.
cd /data/research/discovery
PY=/home/paw/Desktop/ultracool/.venv/bin/python
while read n rest; do
  [ -f out/$n.json ] && grep -q '"dev"' out/$n.json || continue
  grep -q '"fit_blind"' out/$n.json || PYTHONPATH=snap nice -n 15 $PY blind.py $n 2>&1 | grep -v Warn
  [ out/${n}_montage.png -nt out/$n.json ] || PYTHONPATH=pylib nice -n 15 $PY plot.py out/$n.json
done < ${1:-run_list3_full.txt}
