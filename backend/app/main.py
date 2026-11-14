from fastapi import FastAPI

app = FastAPI(title="Ultracool Browser")


@app.get("/api/health")
def health():
    return {"ok": True}
