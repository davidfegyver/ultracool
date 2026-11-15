#!/usr/bin/env bash
# SIMBAD bibcodes+titles (has_ref JOIN ref) for both objects; simbad.sh's ORDER BY r.bibcode was rejected by the TAP parser.
SIM=https://simbad.harvard.edu/simbad/sim-tap/sync
sq() { curl -s -m 180 --retry 3 -G "$SIM" --data-urlencode request=doQuery --data-urlencode lang=adql --data-urlencode format=tsv --data-urlencode "query=$1"; }
for o in 18628314 15893936; do echo "## bibcodes oid $o"; sq "SELECT r.bibcode, r.title FROM has_ref AS h JOIN ref AS r ON r.oidbib=h.oidbibref WHERE h.oidref=$o ORDER BY bibcode"; echo; done
