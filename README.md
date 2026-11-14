# Ultracool Browser

**Watch 16 years of the infrared sky move.** Pick any star, brown dwarf or patch of sky and play NASA infrared images from WISE (2010), NEOWISE (2014–2024) and SPHEREx (2025–2026) as one aligned flipbook. The app measures motion, colour, brightness changes and a 0.75–5 µm SPHEREx spectrum typed against brown-dwarf templates.

Built for NASA Space Apps 2026 ("Planet X and SPHEREx").

## Four modes

| Mode | For | What you get |
|---|---|---|
| **Learn** | newcomers | Seven short lessons on real data, each with a quiz: something moves (Barnard's Star), right colour (WISE 0855−0714), move together (ε Indi A + B), brightness changes (AL Bootis), no pattern (RW Aurigae), real or ghost (an optical ghost of ε Indi A), asteroid ((888) Parysatis). |
| **Explore** | curious minds | Search any name or coordinates; a "What we found" panel answers in plain English: does it move, is it cold, does it change, what type is it. |
| **Research** | astronomers, students | Proper motion fitted from our own images with errors, W1−W2 colour, variability (χ², Lomb–Scargle with cadence-alias warnings), SPHEREx spectral typing, catalog overlays, difference images, deep stacks, single exposures, CSV export with provenance. |
| **Discover** | citizen scientists | Scan a 0.25° field for every moving source, vetted against image artifacts and CatWISE; classify candidates as real mover, artifact or unsure and export your classifications. |

## Science result

Using this pipeline, **WISE J231728.42−665959.3 was typed for the first time: a T5–T6 brown dwarf at ~28 pc**, co-distant with the star pair HD 219509/219495 but not moving with it. Details, the candidate table and the methods are in [`research/`](research/README.md).

## Quick start

Requires Docker with Compose and outbound HTTPS to IRSA (`irsa.ipac.caltech.edu`), AWS S3 and SIMBAD.

```bash
cp .env.example .env            # set PUBLIC_HOSTNAME / PUBLIC_PORT
docker compose up --build -d
open http://localhost:8080      # first view of a new field takes 1-3 min, then it is cached
```

Pre-compute the demo targets and lesson fields (optional, ~20 min):

```bash
docker compose exec api python -m scripts.prewarm
```

## How it works

```mermaid
flowchart LR
  B[Browser: React + Aladin Lite] -->|/api| N[nginx]
  N --> A[FastAPI]
  A -->|SIA search| I[IRSA]
  A -->|byte-range reads| S[(AWS S3: WISE + SPHEREx images)]
  A -->|catalogs| C[CatWISE / NEOWISE via IRSA, SIMBAD, SkyBoT]
  A --> D[(disk cache)]
```

- **Frames:** WISE/NEOWISE L1b exposures and SPHEREx L2 images are read directly from the public NASA S3 buckets (only the needed pixels), masked with the missions' artifact flags, and resampled onto one 2.75″ grid. WISE exposures of each visit are combined with a sigma-clipped mean.
- **Photometry:** SPHEREx on native pixels with the pipeline variance, PSF aperture correction and crowded-field sky estimate; WISE with an aperture correction calibrated on CatWISE stars. Saturated stars fall back to NEOWISE/AllWISE catalog photometry.
- **Motion:** centroids along the predicted track in 2-year WISE stacks and SPHEREx epochs, weighted linear fit; "moving" needs ≥3σ over ≥2 years and ≥3 epochs.
- **Spectra:** SPHEREx fluxes binned into the 102 SPIFF channels and fitted with 47 SPIFF templates; a type is only given when the source is detected at S/N ≥ 5.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `PUBLIC_HOSTNAME`, `PUBLIC_PORT` | `localhost`, `8080` | nginx server name and published port |
| `CACHE_DIR` | `/data/cache` | frame/result cache (a Docker volume) |
| `WORKER_PROCESSES` | CPU count | frame-processing processes |
| `S3_MAX_CONCURRENCY` | 8 × workers | parallel S3 reads |
| `IRSA_MAX_CONCURRENCY` | `2` | parallel IRSA requests (IRSA throttles above ~2) |

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/resolve?q=` | name, designation or coordinates → position and proper motion |
| `POST /api/sequences` | start/reuse an aligned frame sequence (`ra, dec, pmra_masyr, pmdec_masyr, epoch_yr, fov_deg, mjd_min, mjd_max, wise_exposures`) |
| `GET /api/sequences/{id}` | manifest: status, grid WCS, frames with photometry |
| `GET /api/sequences/{id}/summary` | motion, colour, variability, spectrum, asteroids, plain-English sentences |
| `GET /api/sequences/{id}/movers` | vetted moving sources in the field |
| `GET /api/sequences/{id}/spectrum`, `/catalog_lightcurve`, `/export.csv` | spectral typing, catalog light curve, photometry export |
| `GET /api/sequences/{id}/stack.png`, `/diff.png`, `/frames/{frame}.png` | deep stacks, difference images, frames |
| `GET /api/ucds`, `/api/ucds/near` | SPIFF ultracool-dwarf catalog search |

## Development

```bash
cd backend && pip install -r requirements.txt && pytest -q tests
CACHE_DIR=/tmp/cache uvicorn app.main:app --port 8000
cd frontend && npm ci && npm run dev      # proxies /api to localhost:8000 (VITE_API_TARGET to change)
```

## Data and credits

WISE (Wright et al. 2010) and NEOWISE (Mainzer et al. 2011, 2014) images and catalogs, SPHEREx (Doré et al. 2014) Level-2 images, CatWISE2020 (Marocco et al. 2021): NASA/IPAC Infrared Science Archive. SIMBAD (CDS, Harvard mirror). Asteroids: IMCCE SkyBoT. Brown-dwarf templates and catalog: SPIFF (Gagné et al. 2026, doi:10.5281/zenodo.19051216, CC-BY 4.0; see `backend/app/data/ATTRIBUTION.md`). Sky viewer: Aladin Lite (CDS). Software: Astropy, photutils, reproject, FastAPI, React, Plotly.
