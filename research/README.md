# Research notes

Work done on 2026-11-14 alongside the app. Reports mention scratch paths under `/data/research/...` on the build server; the copies here are the durable versions (scripts in `discovery/scripts/`, figures next to each report).

| Folder / file | What it is |
|---|---|
| [`literature-review.md`](literature-review.md) | How CatWISE, unWISE/unTimely, Backyard Worlds, the WISE/SPHEREx documentation, SPIFF, SkyBoT and variability studies do motion detection, artifact rejection, asteroid identification, brown-dwarf selection, common-proper-motion pairs, variability classification and noise filtering, with a ranked action list. Most top items are now in the pipeline (`backend/app/analysis.py`). |
| [`lessons/`](lessons/) | Data behind the seven Learn-mode lessons (`lessons.json`) and the evidence that each effect is really in the data (montages, light curves). |
| [`discovery/REPORT.md`](discovery/REPORT.md) | Brown-dwarf candidate verification: 15 candidates + 2 controls checked with our own WISE+SPHEREx motion, colour and spectrum. |

## Main science result

**WISE J231728.42-665959.3 (CWISE J231728.89-670001.1) is a T5-T6 brown dwarf at about 28 pc**, the first spectral classification of this object (it previously had only a photometric T6 estimate, Rothermich et al. 2024). Its proper motion measured from our own 2010-2026 images, (+419 ± 30, −236 ± 30) mas/yr, differs from the nearby K-star pair HD 219509/219495 by about 170 mas/yr in declination, so it is co-distant with that pair but not a bound companion. Evidence: [`discovery/montages/J2317-6700_montage.png`](discovery/montages/J2317-6700_montage.png).

Caveats: SPHEREx gives low-resolution spectrophotometry, not a slit spectrum; the distance is spectrophotometric; a recent paper typing the object could exist (no ADS full-text search was possible).

## Negative result

All 7 SPIFF "New Candidates" tested were not new brown dwarfs: diffraction spikes, a bright-star wing, a streak near IRC+10216, an embedded young star with ice absorption, a source in M33, and one already-known T6. Faint automatic candidates need image-level vetting.
