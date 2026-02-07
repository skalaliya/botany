from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="nexuscargo-validation-service", version="1.0.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "validation"}
