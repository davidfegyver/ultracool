#!/usr/bin/env bash
# Saved-query script for the J2358-5218 adversarial review (2026-11-15). Run from research/verification/J2358/.
# CDS Strasbourg returned 404 / "Page unavailable"; the Harvard mirrors were used. After ~08:00 UTC the VizieR mirrors
# (Harvard, IDIA, NAO, China-VO, IUCAA) started returning header-only answers for large tables (vizier_spotcheck*.txt),
# so re-running this later may give fewer rows than the saved files.
set -u
SIM=https://simbad.harvard.edu/simbad/sim-tap/sync
VZ=https://vizier.cfa.harvard.edu/viz-bin/asu-tsv
T="359.6165529 -52.303748"      # UCD, CatWISE ep 2015.4 (screen.csv row 2)
H="359.62973049 -52.30166686"   # host, Gaia DR3 ep 2016.0
sq() { curl -s -m 180 --retry 3 -G "$SIM" --data-urlencode request=doQuery --data-urlencode lang=adql --data-urlencode format=tsv --data-urlencode "query=$1"; }
vz() { curl -s -m 300 --retry 2 -G "$VZ" "$@"; }

# SIMBAD -> simbad.txt (cone, ident, mesSpT, flux) and simbad2.sh -> simbad2.txt (bibcodes via ref.oidbib, otypes)
{
echo "## SIMBAD cone 60\" around UCD"
sq "SELECT main_id, otype, sp_type, ra, dec, plx_value, pmra, pmdec, rvz_radvel, nbref, DISTANCE(POINT('ICRS',ra,dec),POINT('ICRS',359.6165529,-52.303748))*3600 AS sep FROM basic WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',359.6165529,-52.303748,60/3600.))=1 ORDER BY sep"
for n in "2MASS J23582773-5218133" "UCAC4 189-203856"; do
  echo; echo "## SIMBAD ident for $n"; sq "SELECT i2.id FROM ident AS i1 JOIN ident AS i2 ON i1.oidref=i2.oidref WHERE i1.id='$n'"
  echo; echo "## SIMBAD mesSpT for $n"; sq "SELECT m.* FROM ident i JOIN mesSpT m ON m.oidref=i.oidref WHERE i.id='$n'"
  echo; echo "## SIMBAD flux for $n"; sq "SELECT f.filter, f.flux, f.flux_err, f.bibcode FROM ident i JOIN flux f ON f.oidref=i.oidref WHERE i.id='$n'"
done
} > simbad.txt 2>&1
./simbad2.sh > simbad2.txt 2>&1

# Gaia DR3 (I/355): main, astrophysical parameters (incl. ESP-UCD), supp, XP spectra view, epoch photometry
for who in "ucd:$T" "host:$H"; do n=${who%%:*}; c=${who#*:}
  vz -d "-source=I/355/gaiadr3" --data-urlencode "-c=$c" -d "-c.rs=3" -d "-out.all" -d "-out.add=_r" > gaia_dr3_$n.tsv
  vz -d "-source=I/355/paramp" --data-urlencode "-c=$c" -d "-c.rs=3" -d "-out.all" -d "-out.add=_r" > gaia_paramp_$n.tsv
  for s in paramsup spectra epphot; do vz -d "-source=I/355/$s" --data-urlencode "-c=$c" -d "-c.rs=3" -d "-out.all" -d "-out.add=_r" > gaia_I_355_${s}_$n.tsv; done
done
vz -d "-source=I/358/*" --data-urlencode "-c=$H" -d "-c.rs=2" -d "-out.all" -d "-out.add=_r" > gaia_I_358_vari_host.tsv
# chance alignment: Gaia DR3 kinematic twins in 10 deg; neighbourhood of the host; 1-deg plx>5 field
GOUT="Source,RA_ICRS,DE_ICRS,Plx,e_Plx,pmRA,e_pmRA,pmDE,e_pmDE,Gmag,BP-RP,RUWE"
vz -d "-source=I/355/gaiadr3" --data-urlencode "-c=$H" -d "-c.rd=10" --data-urlencode "-out=$GOUT,RV" -d "Plx=7..19" -d "pmRA=83.8..123.8" --data-urlencode "pmDE=-13.9..26.1" -d "-out.max=unlimited" -d "-out.add=_r" > gaia_twins_10deg.tsv
vz -d "-source=I/355/gaiadr3" --data-urlencode "-c=$H" -d "-c.rs=120" --data-urlencode "-out=$GOUT" -d "-out.max=unlimited" -d "-out.add=_r" > gaia_host_120as.tsv
vz -d "-source=I/355/gaiadr3" --data-urlencode "-c=$H" -d "-c.rd=1" --data-urlencode "-out=$GOUT" -d "Plx=>5" -d "-out.max=unlimited" -d "-out.add=_r" > gaia_field_1deg_plx5.tsv

# host spectroscopy / activity (RAVE DR6, Zerjal+2017) and earlier pair catalogues (Kervella+2022, SUPERWIDE)
{ for s in "III/283/*" "J/ApJ/835/61/*"; do echo "## $s"; vz --data-urlencode "-source=$s" --data-urlencode "-c=$H" -d "-c.rs=5" -d "-out.all" -d "-out.add=_r"; done; } > host_rave_zerjal.tsv
{ for s in "J/A+A/657/A7/*" "J/ApJS/247/66/*"; do for c in "$H" "359.6164183 -52.3037170"; do echo "## $s @ $c"; vz --data-urlencode "-source=$s" --data-urlencode "-c=$c" -d "-c.rs=3" -d "-out.all" -d "-out.add=_r"; done; done; } > prior_pair_catalogues.tsv

# Specific catalogues around the UCD (20") -> vizier_specific.txt
for s in II/365/catwise II/328/allwise II/246/out II/367/vhs_dr5 II/359/vhs_dr4 II/371/des_dr2 II/379/smssdr4 J/A+A/619/L8/table J/A+A/649/A6/table1c J/A+A/669/A139 J/A+A/674/A39 J/AJ/167/253/table1; do
  echo "## $s"; vz -d "-source=$s" --data-urlencode "-c=$T" -d "-c.rs=20" -d "-out.all" -d "-out.add=_r" | grep -v '^#' | grep -v '^$'
done > vizier_specific.txt

# All-catalogue 20" cone. Without -source the mirror truncates the answer at ~385 kB (B/denis), twice:
vz --data-urlencode "-c=$T" -d "-c.rs=20" -d "-out.max=50" -d "-out.add=_r" > vizier_all_20as_ucd.tsv
vz --data-urlencode "-c=$H" -d "-c.rs=5" -d "-out.max=50" -d "-out.add=_r" > vizier_all_5as_host.tsv
# ... so it was split by catalogue prefix (summary: vizier_hits.py -> vizier_hits.txt)
for part in "J/A+A/*" "J/ApJ/*" "J/AJ/*" "J/ApJS/*" "J/MNRAS/*" "J/PASP/*" "J/other/*" "J/AN/*" "J/PASJ/*" "J/RNAAS/*" "B/*" "V/*" "IV/*" "III/*" "VI/*" "VII/*" "IX/*" "I/*" "II/*"; do
  f="vizier_part_$(echo "$part" | tr '/*+' '__p').tsv"
  curl -s -m 1200 -G "$VZ" --data-urlencode "-source=$part" --data-urlencode "-c=$T" -d "-c.rs=20" -d "-out.max=50" -d "-out.add=_r" -o "$f" && gzip -9f "$f"
done
{ for s in B/vsx/vsx B/wds/wds B/mk/mktypes B/gcvs/gcvs_cat; do for c in "$T" "$H"; do echo "## $s @ $c"; vz -d "-source=$s" --data-urlencode "-c=$c" -d "-c.rs=20" -d "-out.add=_r" | grep -v "^#" | grep -v "^$" | sed -n '4,20p'; done; done; } > vizier_B_and_check.txt

# Reference tables
curl -s -m 60 https://www.pas.rochester.edu/~emamajek/EEM_dwarf_UBVIJHK_colors_Teff.txt -o EEM_dwarf_UBVIJHK_colors_Teff.txt
curl -s -m 60 -L http://perso.ens-lyon.fr/isabelle.baraffe/BHAC15dir/BHAC15_iso.2mass -o BHAC15_iso.2mass
# Dev API (read-only, existing sequence)
curl -s -m 60 localhost:8004/api/sequences/10cd5c77eacd8c7d/spectrum > dev_spectrum_now.json
curl -s -m 60 localhost:8004/api/sequences/10cd5c77eacd8c7d/summary > dev_summary_now.json
