import logging
import urllib.parse
import urllib.request

from fastapi import FastAPI, Query, Response

from . import resolve, sequences, spectral, ucd
from .sources import irsa_retry

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Ultracool Browser")
app.include_router(resolve.router)
app.include_router(sequences.router)
app.include_router(spectral.router)
app.include_router(ucd.router)


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/catwise")
def catwise(ra: float = Query(ge=0, lt=360), dec: float = Query(ge=-90, le=90), radius_deg: float = Query(gt=0, le=0.5)):
    """CatWISE2020 cone (VOTable) from IRSA, proxied because IRSA sends no CORS header."""
    url = "https://irsa.ipac.caltech.edu/SCS?" + urllib.parse.urlencode(
        {"table": "catwise_2020", "RA": ra, "DEC": dec, "SR": radius_deg})

    def fetch():
        with urllib.request.urlopen(url, timeout=120) as r:
            return r.read()

    return Response(irsa_retry(fetch), media_type="text/xml")
