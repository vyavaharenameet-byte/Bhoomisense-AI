"""
api/meta.py
===========
Utility endpoints: health check, raw geocoding, and model metadata
(feature importances + training metrics, used by the Explainable-AI dashboard).
"""

from __future__ import annotations
from fastapi import APIRouter, HTTPException, Request

from app.schemas import GeoLocation
from app.services.geocoding import geocode_city

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health")
async def health(request: Request) -> dict:
    """Liveness/readiness probe — also confirms models are loaded."""
    loaded = hasattr(request.app.state, "predictor")
    return {"status": "ok" if loaded else "degraded", "models_loaded": loaded}


@router.get("/geocode", response_model=GeoLocation)
def geocode(city: str, request: Request):
    """Resolve a city name to coordinates (frontend autocomplete / map centring)."""
    location = geocode_city(city)
    if location is None:
        raise HTTPException(404, f"Could not locate '{city}'.")
    return GeoLocation(**location)


@router.get("/model/metadata")
async def model_metadata(request: Request) -> dict:
    """Training metrics + SHAP feature importances for the XAI dashboard."""
    return request.app.state.predictor.metadata
