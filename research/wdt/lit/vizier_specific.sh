#!/usr/bin/env bash
# Specific VizieR catalogues (Harvard mirror), 60" around both objects, all columns. Run from research/wdt/lit/:
#   ./vizier_specific.sh   -> vz_<tag>.tsv (raw asu-tsv, one file per catalogue)
VZ=https://vizier.cfa.harvard.edu/viz-bin/asu-tsv
T="358.70015 -81.67908"; W="358.58383 -81.68455"
while read tag src; do
  { for c in "$T" "$W"; do echo "#### $src @ $c"; curl -s -m 600 --retry 2 -G "$VZ" --data-urlencode "-source=$src" --data-urlencode "-c=$c" -d "-c.rs=60" -d "-out.all" -d "-out.max=200" -d "-out.add=_r"; done; } > vz_$tag.tsv &
  sleep 1
done <<'L'
tinney2018 J/ApJS/236/28/*
kirk2021 J/ApJS/253/7/*
gf2021 J/MNRAS/508/3877/*
gf2019 J/MNRAS/482/4570/*
torres2019 J/MNRAS/485/5573/*
obrien2023 J/MNRAS/518/3055/*
obrien2024 J/MNRAS/527/8687/*
hernandez2024 J/MNRAS/528/6056/*
vincent2024 J/A+A/682/A5/*
garcia2023 J/A+A/679/A127/*
elbadry2021 J/MNRAS/506/2269/*
gcns J/A+A/649/A6/*
wds B/wds/wds
kervella2022 J/A+A/657/A7/*
superwide J/ApJS/247/66/*
gaiadr3 I/355/gaiadr3
catwise II/365/catwise
L
wait
