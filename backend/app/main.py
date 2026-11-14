from fastapi import FastAPI

from . import resolve

app = FastAPI(title="Ultracool Browser")
app.include_router(resolve.router)


@app.get("/api/health")
def health():
    return {"ok": True}
