# Research notes

Work done on 2026-11-14 alongside the app. Reports mention scratch paths under `/data/research/...` on the build server; the copies here are the durable versions (scripts in `discovery/scripts/`, figures next to each report).

| Folder / file | What it is |
|---|---|
| [`literature-review.md`](literature-review.md) | How CatWISE, unWISE/unTimely, Backyard Worlds, the WISE/SPHEREx documentation, SPIFF, SkyBoT and variability studies do motion detection, artifact rejection, asteroid identification, brown-dwarf selection, common-proper-motion pairs, variability classification and noise filtering, with a ranked action list. Most top items are now in the pipeline (`backend/app/analysis.py`). |
| [`lessons/`](lessons/) | Data behind the seven Learn-mode lessons (`lessons.json`) and the evidence that each effect is really in the data (montages, light curves). |
| [`discovery/REPORT.md`](discovery/REPORT.md) | Brown-dwarf candidate verification: 15 candidates + 2 controls checked with our own WISE+SPHEREx motion, colour and spectrum. |

## Main science result

**WISE J231728.42-665959.3 (CWISE J231728.89-670001.1) is a mid-T brown dwarf (≈T6 ± 1) at about 30 pc (25–40 pc)**: the first spectrum-based type for this object, confirming the photometric (T6) estimate of Rothermich et al. 2024 (derived from its W2 brightness at the host pair's parallax). Its proper motion, ~0.50″/yr (our 2010-2026 images: (+419 ± 30, −236 ± 30) mas/yr; pipeline-independent AllWISE→VHS: (423, −266) ± 44; CatWISE2020 corrected: (437 ± 31, −288 ± 29)), differs from the nearby K-star pair HD 219509/219495 by 140–180 mas/yr (~20 km/s, vs ≲0.5 km/s allowed for a bound orbit), so it is consistent with the pair's distance but not a companion, in agreement with Rothermich's 5.1 % membership probability. Evidence: [`discovery/montages/J2317-6700_montage.png`](discovery/montages/J2317-6700_montage.png).

Caveats: SPHEREx gives low-resolution spectrophotometry, not a slit spectrum; T5 vs T6 vs T7 are not separable (only 35 of 89 channels have S/N > 3; no sub-dwarf or young mid-T templates); the distance is spectrophotometric (Kirkpatrick+2021 relations); our W1−W2 (2.1–2.2) is 0.3 mag redder than CatWISE/unWISE (1.8) because our faint-source W1 is biased low (under investigation). "First" = first found in SIMBAD, VizieR (244 catalogues), UltracoolSheet, SPIFF, Kirkpatrick+2021/2024, 2026 SPHEREx papers and web search as of November 2026; ADS full text was not searched (no token). Adversarial review: [`verification/J2317_ADVERSARIAL.md`](verification/J2317_ADVERSARIAL.md).

## Negative result

All 7 SPIFF "New Candidates" tested were not new brown dwarfs: diffraction spikes, a bright-star wing, a streak near IRC+10216, an embedded young star with ice absorption, a source in M33, and one already-known T6. Faint automatic candidates need image-level vetting.
