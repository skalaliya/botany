from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="nexuscargo-review-service", version="1.0.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "review"}
