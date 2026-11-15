#!/bin/bash
# VizieR all-catalogue 20" cone, split by catalogue group, for fields where the single all-catalogue asu-tsv call is cut
# off by the CfA mirror after ~120 s (curl exit 18 / IncompleteRead). Usage: scripts/vizier_split.sh <tag> <ra> <dec>
tag=$1; ra=$2; dec=$3
for s in 'J/AJ/*' 'J/ApJ/*' 'J/ApJS/*' 'J/A+A/*' 'J/MNRAS/*' 'J/PASP/*' 'J/other/*' 'J/AN/*' 'J/PASJ/*' 'J/A+AS/*' 'B/*' 'IX/*' 'X/*' 'XI/*'; do
  f="out/$tag/vizier_20as_$(printf '%s' "$s" | tr -d '/*+')".tsv
  curl -s -m 300 -G "https://vizier.cfa.harvard.edu/viz-bin/asu-tsv" --data-urlencode "-source=$s" \
    --data-urlencode "-c=$ra $dec" --data-urlencode "-c.rs=20" --data-urlencode "-out.max=10" -o "$f"
  echo "$s exit=$? bytes=$(wc -c < "$f") tables=$(grep -c '^#Table' "$f") error=$(grep -c 'QUERY_STATUS=ERROR' "$f")"
  sleep 5
done
