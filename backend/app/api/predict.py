"""
api/predict.py
==============
Core prediction endpoints. Pipeline per request:
  geocode (if city) -> collect environmental + geospatial features
  -> per-hazard model inference -> assemble PredictionResponse.
"""

from __future__ import annotations
from fastapi import APIRouter, HTTPException, Request

from app.schemas import (EnvironmentFeatures, GeoLocation, PredictByCityRequest,
                         PredictByCoordsRequest, PredictionResponse,
                         RainfallPoint)
from app.services.environment import collect_features
from app.services.geocoding import geocode_city

router = APIRouter(prefix="/api", tags=["prediction"])

_DISCLAIMER = (
    "BhoomiSense AI is a decision-support and educational tool. Predictions are "
    "model estimates and may be wrong. They are NOT official warnings — always "
    "follow IMD, NDMA and local disaster-management authorities."
)


def _run(location: dict, request: Request) -> PredictionResponse:
    service = request.app.state.predictor
    features = collect_features(location["latitude"], location["longitude"])
    result = service.predict(features)

    timeline = features.pop("rainfall_timeline", [])

    return PredictionResponse(
        location=GeoLocation(**location),
        features=EnvironmentFeatures(**features),
        flood=result["flood"],
        landslide=result["landslide"],
        severity_score=result["severity_score"],
        severity_level=result["severity_level"],
        explanation=result["explanation"],
        flood_factors=result["flood_factors"],
        landslide_factors=result["landslide_factors"],
        rainfall_timeline=[RainfallPoint(**p) for p in timeline],
        disclaimer=_DISCLAIMER,
    )


@router.post("/predict/city", response_model=PredictionResponse)
def predict_by_city(payload: PredictByCityRequest, request: Request):
    """Predict flood / landslide / severity risk for a named city."""
    location = geocode_city(payload.city)
    if location is None:
        raise HTTPException(404, f"Could not locate '{payload.city}'. "
                                 "Enter a specific city or town — e.g. Mumbai, "
                                 "Pune, Wayanad — not a whole country or state.")
    return _run(location, request)


@router.post("/predict/coords", response_model=PredictionResponse)
def predict_by_coords(payload: PredictByCoordsRequest, request: Request):
    """Predict for explicit coordinates (used by map clicks)."""
    location = {"name": f"{payload.latitude:.3f}, {payload.longitude:.3f}",
                "latitude": payload.latitude, "longitude": payload.longitude,
                "country": None}
    return _run(location, request)
