import logging

from fastapi import FastAPI

from . import resolve, sequences, spectral, ucd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Ultracool Browser")
app.include_router(resolve.router)
app.include_router(sequences.router)
app.include_router(spectral.router)
app.include_router(ucd.router)


@app.get("/api/health")
def health():
    return {"ok": True}
