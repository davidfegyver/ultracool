import logging

from fastapi import FastAPI, Query, Response

from . import analysis, resolve, sequences, spectral, ucd
from .sources import irsa_scs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Ultracool Browser")
app.include_router(resolve.router)
app.include_router(sequences.router)
app.include_router(spectral.router)
app.include_router(ucd.router)
app.include_router(analysis.router)


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/catwise")
def catwise(ra: float = Query(ge=0, lt=360), dec: float = Query(ge=-90, le=90), radius_deg: float = Query(gt=0, le=0.5)):
    """CatWISE2020 cone (VOTable) from IRSA, proxied because IRSA sends no CORS header."""
    return Response(irsa_scs(ra, dec, radius_deg), media_type="text/xml")
