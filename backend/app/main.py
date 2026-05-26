"""
main.py
=======
BhoomiSense AI — FastAPI application entry point.

  uvicorn app.main:app --reload          # development
  uvicorn app.main:app --host 0.0.0.0 --port 8000   # production

The ML models are large-ish, so they are loaded ONCE during the `lifespan`
startup event and stored on `app.state` — never reloaded per request.
"""

from __future__ import annotations
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import meta, predict
from app.config import get_settings
from app.services.inference import PredictionService

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup: load models into memory once -----------------------------
    app.state.predictor = PredictionService()
    print(f"[{settings.app_name}] models loaded — ready.")
    yield
    # --- shutdown ----------------------------------------------------------
    print(f"[{settings.app_name}] shutting down.")


app = FastAPI(
    title=settings.app_name,
    description="ML-powered flood / landslide / environmental severity prediction.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — only the configured frontends may call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(meta.router)
app.include_router(predict.router)


@app.get("/")
async def root() -> dict:
    return {"name": settings.app_name, "docs": "/docs",
            "health": "/api/health"}
