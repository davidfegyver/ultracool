#!/usr/bin/env bash
# SIMBAD (Harvard mirror TAP) bibcodes + otypes for both objects; fixes the ref join of queries.sh (ref key = oidbib).
SIM=https://simbad.harvard.edu/simbad/sim-tap/sync
sq() { curl -s -m 180 --retry 3 -G "$SIM" --data-urlencode request=doQuery --data-urlencode lang=adql --data-urlencode format=tsv --data-urlencode "query=$1"; }
for n in "2MASS J23582773-5218133" "UCAC4 189-203856"; do
  echo "## SIMBAD bibcodes for $n"
  sq "SELECT r.bibcode, r.title FROM ident i JOIN has_ref h ON h.oidref=i.oidref JOIN ref r ON r.oidbib=h.oidbibref WHERE i.id='$n'"
  echo; echo "## SIMBAD otypes for $n"
  sq "SELECT o.otype, o.origin FROM ident i JOIN otypes o ON o.oidref=i.oidref WHERE i.id='$n'"
  echo
done
echo "## SIMBAD ident for UCAC4 189-203856"
sq "SELECT i2.id FROM ident AS i1 JOIN ident AS i2 ON i1.oidref=i2.oidref WHERE i1.id='UCAC4 189-203856'"
