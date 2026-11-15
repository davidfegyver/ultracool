#!/usr/bin/env bash
# VizieR (Harvard mirror) 60" all-catalogue cones split by prefix (no -source truncates). Run from research/wdt/lit/.
VZ=https://vizier.cfa.harvard.edu/viz-bin/asu-tsv
declare -A POS=([tdw]="358.70015 -81.67908" [wd]="358.58383 -81.68455")
for obj in tdw wd; do mkdir -p parts_$obj
 for part in "J/A+A/*" "J/ApJ/*" "J/AJ/*" "J/ApJS/*" "J/MNRAS/*" "J/PASP/*" "J/other/*" "J/AN/*" "J/PASJ/*" "J/RNAAS/*" "B/*" "V/*" "IV/*" "III/*" "VI/*" "VII/*" "IX/*" "I/*" "II/*"; do
  f="parts_$obj/vizier_part_$(echo "$part" | tr '/*+' '__p').tsv"
  ( curl -s -m 1200 -G "$VZ" --data-urlencode "-source=$part" --data-urlencode "-c=${POS[$obj]}" -d "-c.rs=60" -d "-out.max=50" -d "-out.add=_r" -o "$f" && gzip -9f "$f"; echo "$(date -u +%T) $obj $part done" ) &
  sleep 2
 done
done
wait
