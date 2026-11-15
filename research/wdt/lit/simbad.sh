#!/usr/bin/env bash
# SIMBAD (Harvard mirror TAP) for the WD + T dwarf pair. Run from research/wdt/lit/: ./simbad.sh > simbad.txt
SIM=https://simbad.harvard.edu/simbad/sim-tap/sync
sq() { curl -s -m 180 --retry 3 -G "$SIM" --data-urlencode request=doQuery --data-urlencode lang=adql --data-urlencode format=tsv --data-urlencode "query=$1"; }
for o in 18628314 15893936; do
  echo "######## oid $o"
  echo "## basic"; sq "SELECT oid, main_id, otype, sp_type, ra, dec, plx_value, plx_err, pmra, pmdec, nbref FROM basic WHERE oid=$o"
  echo; echo "## ident"; sq "SELECT id FROM ident WHERE oidref=$o"
  echo; echo "## bibcodes"; sq "SELECT r.bibcode, r.title FROM has_ref h JOIN ref r ON r.oidbib=h.oidbibref WHERE h.oidref=$o ORDER BY r.bibcode"
  echo; echo "## otypes"; sq "SELECT otype, origin FROM otypes WHERE oidref=$o"
  echo; echo "## mesSpT"; sq "SELECT * FROM mesSpT WHERE oidref=$o"
  echo; echo "## mesPM"; sq "SELECT * FROM mesPM WHERE oidref=$o"
  echo; echo "## mesPlx"; sq "SELECT * FROM mesPlx WHERE oidref=$o"
  echo; echo "## h_link (as child)"; sq "SELECT h.*, b.main_id AS parent_name FROM h_link h JOIN basic b ON b.oid=h.parent WHERE h.child=$o"
  echo; echo "## h_link (as parent)"; sq "SELECT h.*, b.main_id AS child_name FROM h_link h JOIN basic b ON b.oid=h.child WHERE h.parent=$o"
  echo
done
echo "######## basic cone 120\" around midpoint (358.64, -81.682)"
sq "SELECT oid, main_id, otype, sp_type, ra, dec, plx_value, pmra, pmdec, nbref, DISTANCE(POINT('ICRS',ra,dec),POINT('ICRS',358.64,-81.682))*3600 AS sep FROM basic WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',358.64,-81.682,120/3600.))=1 ORDER BY sep"
