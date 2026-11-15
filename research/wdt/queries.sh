# Every catalogue / API query behind research/wdt (run 2026-11-15, cwd research/wdt). CDS Strasbourg was flaky:
# VizieR via the Harvard mirror, IRSA Gator directly. Literature queries: lit/*.sh (WDTLit sub-task).
V="https://vizier.cfa.harvard.edu/viz-bin/asu-tsv"
G="https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query"
# IRSA Gator cones (10" around the CatWISE position; default columns)
curl -s "$G?catalog=catwise_2020&spatial=cone&objstr=358.70017+-81.67906&radius=10&radunits=arcsec&outfmt=1" -o irsa_catwise_2020.tbl
curl -s "$G?catalog=allwise_p3as_psd&spatial=cone&objstr=358.70017+-81.67906&radius=10&radunits=arcsec&outfmt=1" -o irsa_allwise_p3as_psd.tbl
curl -s "$G?catalog=allwise_p3as_mep&spatial=cone&objstr=358.69938+-81.67915&radius=3&radunits=arcsec&outfmt=1&selcols=ra,dec,mjd,w1mpro_ep,w2mpro_ep,w1sigmpro_ep,w2sigmpro_ep,cc_flags" -o irsa_allwise_mep.tbl
# VizieR (Harvard mirror)
curl -s "$V?-source=II/365/catwise&-c=358.7001937%20-81.6790731&-c.rs=10&-out.all&-out.add=_r" -o vizier_II365_catwise.tsv
C="-c=358.70015%20-81.67908"
for s in "II/367 vhsdr5" "II/246/out 2mass" "II/363/unwise unwise" "I/355/gaiadr3 gaia_ucd" "II/359 vhsdr4" "J/AJ/165/36 untimely"; do
  set -- $s; curl -s "$V?-source=$1&$C&-c.rs=10&-out.all&-out.add=_r&-sort=_r" -o "vz_$2.tsv"; done
curl -s "$V?-source=J/MNRAS/508/3877&-c=358.58383%20-81.68455&-c.rs=5&-out.all&-out.add=_r" -o vz_gf21_wd.tsv
# Gaia DR3 nearby stars within 5 deg (chance alignment); first try failed ("database not reachable"), second worked
curl -s "$V?-source=I/355/gaiadr3&$C&-c.rd=5&Plx=%3E20&-out=Source&-out=RA_ICRS&-out=DE_ICRS&-out=Plx&-out=e_Plx&-out=pmRA&-out=e_pmRA&-out=pmDE&-out=e_pmDE&-out=Gmag&-out=BP-RP&-out=RUWE&-out.add=_r&-out.max=100000" -o gaia_5deg_plx20.tsv
# reference data
curl -s https://www.astro.umontreal.ca/~bergeron/CoolingModels/Tables/Table_Mass_0.{4,5,6}   # -> ref/Montreal_Table_Mass_*
curl -sL https://zenodo.org/api/records/5063476/files/evolution_and_photometery.tar.gz/content -o ref/sonora_bobcat_evolution_and_photometery.tar.gz
curl -sL https://arxiv.org/pdf/2011.11616 -o ref/kirkpatrick2021_2011.11616.pdf   # text: ref/kirkpatrick2021_text.txt (pypdf)
curl -s https://arxiv.org/html/2312.02735 -o ref/obrien2024_2312.02735.html          # O'Brien+2024 Sect. 2 low-mass correction
curl -s https://arxiv.org/html/2505.24560 -o zhang2025_bb1.html                       # Zhang+2025 Benchmark brown dwarfs I
# dev API (CACHE_DIR=/data/devcache/wdt, port 8006, working tree; stopped afterwards)
curl -s -X POST localhost:8006/api/sequences -H 'content-type: application/json' \
  -d '{"ra":358.7001937,"dec":-81.6790731,"pmra_masyr":122,"pmdec_masyr":71,"epoch_yr":2015.4}'   # -> d7960472debb5523
S=localhost:8006/api/sequences/d7960472debb5523
curl -s $S > dev_sequence.json; curl -s $S/summary > dev_summary.json; curl -s $S/spectrum > dev_spectrum.json; curl -s $S/export.csv > dev_export.csv
