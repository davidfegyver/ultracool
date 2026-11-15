# Ultracool Browser: 3-minute pitch (NASA Space Apps Challenge 2026, "Planet X and SPHEREx")

8 slides, about 410 spoken words (≈140 words/min, ~2:55). Times are cumulative. Every number below is checked: see the source column at the end. The HTML deck with speaker notes is `docs/pitch/index.html`.

---

## Slide 1 · The hook (0:00–0:20)

**On screen:** full-bleed infrared flipbook of Barnard's Star sliding across 16 years of images (loop it as a GIF). Title: **Ultracool Browser**. URL: **ultracool.earth**

**Say:**
> The Sun's nearest neighbours may still be undiscovered: cold brown dwarfs, failed stars too dim for normal telescopes, and maybe a "Planet X". They glow only in infrared, and they give themselves away by moving. This is 16 years of NASA infrared images of one patch of sky, played as a flipbook. The dot that moves is a star 6 light-years away.

---

## Slide 2 · The problem (0:20–0:40)

**On screen:** three logos/labels: WISE 2010 · NEOWISE 2014–2024 · SPHEREx 2025–26. Under them: "different cameras, pixel grids, archives, file formats".

**Say:**
> NASA has photographed the whole sky in infrared again and again for 16 years, and SPHEREx now adds a 102-colour spectrum of every point. But the data sits in different archives and formats. Seeing whether something moves, or what it is, takes an astronomer a day of scripting. We wanted it to take one click.

---

## Slide 3 · What we built (0:40–1:15) · LIVE DEMO or 30 s screen recording

**On screen:** ultracool.earth. Type "WISE J2317". Flipbook plays → "What we found" badges: *Moves: yes, 0.5″/yr · Red, like T dwarfs · Type T5*. Spectrum plot with the template.

**Say:**
> Type any star or coordinates. We stream only the needed pixels from NASA's public cloud archive, align every image onto one grid, and measure the object with well-established astronomy methods: does it move, how red is it, does it change brightness. Then we match its SPHEREx spectrum against 47 published brown-dwarf templates. Drag the cyan crosshair onto any other dot and it measures that too.

---

## Slide 4 · For everyone (1:15–1:40)

**On screen:** four cards: **Learn** (7 lessons on real objects, with quizzes) · **Explore** (plain-English answers) · **Research** (errors, catalogs, CSV export) · **Discover** (scan a field for movers, classify real vs artifact).

**Say:**
> One tool, four audiences. Students learn on real data in seven short lessons. Curious people get plain-English answers. Astronomers get error bars and exports. And citizen scientists can scan a field for anything that moves and vote on what is real.

---

## Slide 5 · A real result (1:40–2:15)

**On screen:** J2317 montage (W2 epochs 2010→2024 + SPHEREx spectrum with T6 template). Bullet facts:
- WISE J2317−6659: first spectrum-based type, **≈T6 brown dwarf**
- ~0.5″/yr motion, **~30 pc** (25–40 pc)
- Not a companion of the nearby star pair HD 219509/219495
- Checked claim by claim by an independent adversarial review

**Say:**
> And it already produced science. WISE J2317 was only a photometric candidate. Our pipeline measured its SPHEREx spectrum for the first time: a mid-T brown dwarf about 100 light-years away. It sits at the same distance as a nearby star pair but moves differently, so it is not their companion. Before claiming it, we tried to break every number with an independent review.

---

## Slide 6 · Honest science (2:15–2:30)

**On screen:** two numbers, big:
- **21 of 26** known brown dwarfs typed within 2 subtypes (validation set)
- **7 of 7** "new brown-dwarf candidates" from an automated catalogue were not new: diffraction spikes, a scattered-light streak, a young star in ice, a galaxy source, one already known

**Say:**
> We validated on 26 known brown dwarfs: 21 typed within two subtypes. And all seven automated "new candidates" we tested were not new, which is why people need to see the images.

---

## Slide 7 · Standing on the shoulders of giants (2:30–2:45)

**On screen:** two columns.
- *Built on the research community:* data from NASA WISE, NEOWISE, SPHEREx (IRSA), CatWISE2020, Gaia, SIMBAD/VizieR (CDS); brown-dwarf templates and typing from SPIFF (Gagné et al. 2026); colour/distance relations from Kirkpatrick et al. 2021 and Schmidt et al. 2015; photometry and statistics from Astropy, photutils, reproject (Lomb–Scargle); artifact flags from WISE, asteroids from IMCCE SkyBoT; candidate lists from Rothermich et al. 2024, Kirkpatrick et al. 2021, UltracoolSheet (Best et al.).
- *What we added:* three missions aligned into one 16-year flipbook in one click; plain-language answers that show their uncertainty; probe, lessons, citizen-science vetting; our own validation and an adversarial check of every claim; applying it to new SPHEREx data (J2317's first spectrum-based type).

**Say:**
> We are IT students, so to be clear: the science is not ours. The data is NASA's and Gaia's, the brown-dwarf templates are the SPIFF team's, the relations come from published papers, the algorithms from open-source libraries. What we built is the bridge: one aligned 16-year view, honest plain-language answers, and a check of every claim.

---

## Slide 8 · What's next (2:45–3:00)

**On screen:** ultracool.earth · QR code · team names.
- Open science: every result reproducible, CSV export with provenance
- Next: classroom pack, Backyard Worlds-style volunteer vetting, follow-up spectra for our candidates

**Say:**
> It runs today on one small server, using only open data. Next: a classroom pack and a volunteer vetting network, so the next nearby neighbour can be found by a student. Try it at ultracool.earth.

---

## Jury notes (for Q&A, not slides)

| Juror | Likely interest | Answer ready |
|---|---|---|
| Hanga Katreiner (space software, outreach) | Is it usable by the public, on phones? | Learn + Explore modes, 7 lessons with quizzes, plain-English results; phone layout for Learn/Explore *(only claim once deployed)*. |
| Dr. Tibor Pacher (physicist, Puli Space) | Is the science real? | Validation 21/26 within ±2 subtypes, mean error 1.2 subtypes; type ranges instead of single labels; known limits: low-resolution spectrophotometry (R≈40–130), crowded fields, faint W1 bias. |
| Miki Bata (business development) | Who uses it, what does it cost? | One 4-vCPU server, only open NASA data streamed from public S3 (no data copies), cache for popular objects; users: schools, planetariums, citizen-science projects, astronomers vetting candidates. |
| István Molnár (AI, enterprise software) | Architecture, automation, AI | FastAPI + numpy/astropy pipeline, parallel S3 byte-range reads, versioned caches, per-visitor rate limits; AI-assisted development with adversarial agents re-checking every claim against raw data and catalogues. |

**Expected hard questions**
- *"Is J2317 really new?"* → First spectrum-based type found in SIMBAD, VizieR (244 catalogues), UltracoolSheet, SPIFF, 2026 SPHEREx papers and web search; ADS full text not searched; the earlier type (Rothermich 2024) was an estimate from brightness, and ours confirms it.
- *"Why not just use catalogues?"* → Catalogues mis-measure fast movers and include artifacts: our test of 7 automated candidates found 0 real new brown dwarfs.
- *"How accurate is the type?"* → ±1–2 subtypes; we show a range (e.g. T4–T7), not a single label.

## Sources for every number

| Claim | Source |
|---|---|
| 16 years, WISE 2010 / NEOWISE 2014–2024 / SPHEREx 2025–26 | README.md; data span 2010.33–2026.75 (research/verification/J2317_ADVERSARIAL.md) |
| Barnard's Star 6 light-years | 1.83 pc (SIMBAD parallax 546.98 mas) |
| 102 SPHEREx colours, 47 templates | SPIFF bins/templates (backend/app/data) |
| 7 lessons with quizzes | frontend/src/lessons.ts |
| J2317 ≈T6 ± 1, ~30 pc (25–40), ~0.5″/yr, not a companion | research/verification/J2317_ADVERSARIAL.md, research/README.md |
| 21 of 26 within ±2 subtypes, mean error 1.19 | research/spectra/REPORT.md |
| 7 of 7 SPIFF "New Candidates" not new | research/discovery/REPORT.md |
| One 4-vCPU server | deployment (Linode 8 GB, 4 vCPU) |
