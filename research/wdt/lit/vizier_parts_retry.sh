#!/usr/bin/env bash
# Serial retry of the prefix parts from vizier_parts.sh that came back "database not currently reachable" (files < 2 kB) or
# whose saved request line has no -source (a first version of this script lost the prefix and saved no-source answers),
# plus B/* sub-catalogues queried one by one (B/* truncates at B/vsx, as in research/verification/J2358). Run from research/wdt/lit/.
VZ=https://vizier.cfa.harvard.edu/viz-bin/asu-tsv
declare -A POS=([tdw]="358.70015 -81.67908" [wd]="358.58383 -81.68455")
PARTS=("J/A+A/*" "J/ApJ/*" "J/AJ/*" "J/ApJS/*" "J/MNRAS/*" "J/PASP/*" "J/other/*" "J/AN/*" "J/PASJ/*" "J/RNAAS/*" "B/*" "V/*" "IV/*" "III/*" "VI/*" "VII/*" "IX/*" "I/*" "II/*")
for obj in tdw wd; do
 for part in "${PARTS[@]}"; do
  f="parts_$obj/vizier_part_$(echo "$part" | tr '/*+' '__p').tsv"
  [ -f "$f.gz" ] && [ "$(stat -c %s "$f.gz")" -gt 2000 ] && zgrep -q 'request=.*-source=[^&]' "$f.gz" && continue
  zgrep -qs "Table or Catalog not found" "$f.gz" && continue
  [ "$part" = "B/*" ] && continue  # truncated at B/vsx; replaced by vizier_B_individual.tsv below
  for a in 1 2 3; do
   curl -s -m 1200 -G "$VZ" --data-urlencode "-source=$part" --data-urlencode "-c=${POS[$obj]}" -d "-c.rs=60" -d "-out.max=50" -d "-out.add=_r" -o "$f"
   if [ "$(stat -c %s "$f")" -gt 2000 ]; then gzip -9f "$f"; echo "$(date -u +%T) $obj $part ok (attempt $a)"; break; fi
   echo "$(date -u +%T) $obj $part failed attempt $a: $(grep -m1 Error "$f")"; rm -f "$f"; sleep 30
  done
 done
 [ -s parts_$obj/vizier_B_individual.tsv ] && continue
 { for s in B/vsx/vsx B/wds/wds B/mk/mktypes B/gcvs/gcvs_cat B/sb9/main B/pastel/pastel B/eso/eso_arc B/hst/hstlog B/gemini/obscore B/chandra/chandra B/xmm/xmmlog B/swift/swiftlog; do
   echo "#### $s"; curl -s -m 600 -G "$VZ" -d "-source=$s" --data-urlencode "-c=${POS[$obj]}" -d "-c.rs=60" -d "-out.max=50" -d "-out.add=_r"; done; } > parts_$obj/vizier_B_individual.tsv
done
