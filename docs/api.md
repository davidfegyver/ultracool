# API, configuration and deployment

This page is for people who want to run the app themselves or call its API. The app is two containers: a FastAPI backend (`api`) and an nginx container (`web`) that serves the built React frontend and proxies `/api` to the backend. nginx is the only entry point.

## Running it

You need Docker with Compose and outbound HTTPS to IRSA (`irsa.ipac.caltech.edu`), AWS S3 and SIMBAD.

```bash
cp .env.example .env            # set PUBLIC_HOSTNAME / PUBLIC_PORT
docker compose up --build -d
curl -s localhost:8080/api/health   # {"ok":true}
```

The first view of a new field takes 1–3 minutes while the images are read and aligned. After that it is cached in the `cache` Docker volume and opens instantly.

### Pre-warming the cache

The demo targets and the lesson fields can be computed ahead of time (about 20 minutes):

```bash
docker compose exec api python -m scripts.prewarm
```

For larger runs there is a resumable batch script. This one pre-computes every T and Y dwarf in the SPIFF catalogue, including the movers search, and scales with CPU cores:

```bash
docker compose exec api python -m scripts.batch --spt-min T0 --spt-max Y1 --movers --state /data/cache/batch_TY.jsonl
```

## Configuration

All settings are environment variables, read from `.env` by Compose.

| Variable | Default | Meaning |
|---|---|---|
| `PUBLIC_HOSTNAME`, `PUBLIC_PORT` | `localhost`, `8080` | nginx server name and published port |
| `CACHE_DIR` | `/data/cache` | frame and result cache (a Docker volume) |
| `WORKER_PROCESSES` | CPU count | frame-processing processes |
| `S3_MAX_CONCURRENCY` | 8 × workers | parallel S3 reads |
| `IRSA_MAX_CONCURRENCY` | `2` | parallel IRSA requests (IRSA throttles above about 2) |
| `MAX_RUNNING_SEQUENCES` | max(4, workers) | fields fetched at once; others wait in a queue (`queue_position`, `eta_s`) |

## Endpoints

All routes are under `/api` and return JSON unless noted.

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | liveness check |
| `GET /api/resolve?q=` | name, designation or coordinates → position and proper motion |
| `POST /api/sequences` | start or reuse an aligned frame sequence. Body: `ra, dec, pmra_masyr, pmdec_masyr, epoch_yr, fov_deg, mjd_min, mjd_max, wise_exposures` |
| `GET /api/sequences/{id}` | manifest: status, `queue_position`, `eta_s`, grid WCS, frames with photometry |
| `GET /api/sequences/{id}/summary` | motion, colour, variability, spectrum, asteroids and the plain-English sentences |
| `GET /api/sequences/{id}/movers` | moving sources in the field, vetted against static sources, bright-star artifacts and CatWISE |
| `GET /api/sequences/{id}/probe?ra&dec[&mode=full]` | measure any point in the field: quick preview from cached images, or a full re-measurement on the original pixels |
| `GET /api/sequences/{id}/spectrum` | SPHEREx spectral typing |
| `GET /api/sequences/{id}/catalog_lightcurve` | catalogue light curve (used for saturated stars) |
| `GET /api/sequences/{id}/export.csv` | photometry export with provenance and citations |
| `GET /api/sequences/{id}/frames/{frame}.png` | one aligned frame |
| `GET /api/sequences/{id}/stack.png`, `/diff.png` | deep stacks and difference images |
| `GET /api/ucds`, `GET /api/ucds/near` | search the SPIFF ultracool-dwarf catalogue by type, or by position |

A typical client resolves a name, posts the result to `/api/sequences`, polls the manifest until `status` is `done`, and then asks for `/summary`:

```bash
curl -s "localhost:8080/api/resolve?q=Barnard%27s%20Star"
curl -s -X POST localhost:8080/api/sequences -H 'content-type: application/json' \
  -d '{"ra": 269.452, "dec": 4.693, "pmra_masyr": -802, "pmdec_masyr": 10362, "epoch_yr": 2000.0}'
curl -s localhost:8080/api/sequences/<id>/summary
```

Frame PNGs are served with a one-year immutable cache header, since a frame never changes once written. Summaries are cached per field and recomputed when the pipeline or summary version changes.

## Deployment

The public site at https://ultracool.earth runs on one small server behind Cloudflare. Cloudflare's SSL mode is Flexible: visitors get HTTPS, and Cloudflare talks plain HTTP to nginx on `PUBLIC_PORT`. There is no TLS setup in this repo for that reason.

nginx limits each visitor to about 12 new fields per minute (burst 20). Full probe measurements are capped server-wide by the API: one running and four waiting. Everything else is unlimited, and requests from the host itself are exempt. The visitor address comes from the `CF-Connecting-IP` header, which nginx trusts only from Cloudflare's published IP ranges. All of this is in `frontend/nginx.conf.template`.

Before a demo, run the pre-warm script once. The cache volume survives restarts and rebuilds.

## Development

Backend, with a local cache directory:

```bash
cd backend && pip install -r requirements.txt && pytest -q tests
CACHE_DIR=/tmp/cache uvicorn app.main:app --port 8000
```

Frontend, with a dev server that proxies `/api` to `localhost:8000` (set `VITE_API_TARGET` to change it):

```bash
cd frontend && npm ci && npm run dev
```

Type-check the frontend with `npx tsc -b`.

## Data licence

The SPIFF templates, channel table and ultracool-dwarf catalogue in `backend/app/data/` are CC-BY 4.0; see [ATTRIBUTION.md](../backend/app/data/ATTRIBUTION.md). Everything else is fetched live from public archives and is not redistributed in this repo.
