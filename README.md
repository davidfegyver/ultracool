# Ultracool Browser

Ultracool Browser plays 16 years of NASA infrared images of any patch of sky as one aligned flipbook: WISE (2010), NEOWISE (2014–2024) and SPHEREx (2025–2026). It measures whether the object in the middle moves, how red it is, whether its brightness changes, and what its SPHEREx 0.75–5 µm spectrum looks like next to published brown-dwarf templates. We built it for the NASA Space Apps Challenge 2026 ("Planet X and SPHEREx").

Try it at **https://ultracool.earth**.

## What you can do

- **Learn**: seven short lessons on real data, each with a quiz (a moving star, a very cold brown dwarf, a pair moving together, a pulsating star, an irregular young star, a camera ghost, an asteroid).
- **Explore**: type a name or coordinates and get short answers to "does it move, is it cold, does it change, what type is it?".
- **Research**: the same answers as numbers with error bars, plus catalogue overlays, blink and difference images, deep stacks, a probe that measures any other source in the field, and CSV export.
- **Discover**: scan a field for everything that moves, check each candidate against image artifacts and CatWISE, and mark it as real, artifact or unsure.

## Main results

The tool gave WISE J231728.42−665959.3 its first spectrum-based type: a mid-T brown dwarf (≈T6 ± 1) at about 30 pc (25–40 pc), confirming the brightness-based T6 estimate of Rothermich et al. (2024). It also gave first spectrum-based types to three more of their candidates, and found two candidate wide pairs that we could not find in the literature. We also tested 7 new brown-dwarf candidates from an automated catalogue; none of them turned out to be new. Before publishing each claim we asked an AI model to try to break it, and every time it corrected something. Details, caveats and what would confirm each result are in [docs/results.md](docs/results.md).

## Quick start

You need Docker with Compose and outbound HTTPS to IRSA (`irsa.ipac.caltech.edu`), AWS S3 and SIMBAD.

```bash
cp .env.example .env            # set PUBLIC_HOSTNAME / PUBLIC_PORT
docker compose up --build -d
open http://localhost:8080      # first view of a new field takes 1-3 min, then it is cached
```

Optional: pre-compute the demo targets and lesson fields (about 20 min):

```bash
docker compose exec api python -m scripts.prewarm
```

Configuration, the API, deployment and local development are described in [docs/api.md](docs/api.md).

## Documentation

| File | For |
|---|---|
| [docs/user-guide.md](docs/user-guide.md) | anyone: how to read the flipbook and the answers, no astronomy needed |
| [docs/how-it-works.md](docs/how-it-works.md) | the pipeline step by step, and which published method each step uses |
| [docs/results.md](docs/results.md) | the science results, how sure we are, and what would confirm them |
| [docs/validation.md](docs/validation.md) | how we tested the spectral typing, photometry and motion fits |
| [docs/api.md](docs/api.md) | endpoints, configuration, deployment, development |

## Credits

We are a small team of IT students. The science in this tool is not ours: the images come from NASA missions, the brown-dwarf templates and catalogue from the SPIFF team, the colour and distance relations from published papers, and the algorithms from open-source libraries. Our part is putting them together on one 16-year grid, turning the measurements into short answers that include their uncertainty, and checking the results. The full list of data, papers and software we rely on is in [docs/how-it-works.md](docs/how-it-works.md#what-we-built-vs-what-we-use).

## Licence and attribution

Images and catalogues: WISE, NEOWISE, SPHEREx and CatWISE2020 via the NASA/IPAC Infrared Science Archive; SIMBAD and VizieR (CDS); asteroid positions from IMCCE SkyBoT; sky viewer Aladin Lite (CDS). The brown-dwarf templates, SPHEREx channel table and ultracool-dwarf catalogue in `backend/app/data/` are from SPIFF (Gagné et al. 2026, doi:10.5281/zenodo.19051216) under CC-BY 4.0; see [backend/app/data/ATTRIBUTION.md](backend/app/data/ATTRIBUTION.md).
