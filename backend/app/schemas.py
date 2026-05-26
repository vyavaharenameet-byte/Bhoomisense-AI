"""API request & response schemas — the typed contract between the React
frontend and the FastAPI backend."""

from __future__ import annotations
from pydantic import BaseModel, Field


# --------------------------------------------------------------------------
# Requests
# --------------------------------------------------------------------------
class PredictByCityRequest(BaseModel):
    city: str = Field(..., min_length=1, max_length=120,
                      examples=["Mumbai", "Wayanad, Kerala"])


class PredictByCoordsRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


# --------------------------------------------------------------------------
# Responses
# --------------------------------------------------------------------------
class GeoLocation(BaseModel):
    name: str
    latitude: float
    longitude: float
    country: str | None = None


class EnvironmentFeatures(BaseModel):
    """Environmental + geospatial inputs collected for a location.
    `data_quality` flags each value as 'measured' (from an API) or 'estimated'
    (heuristic) — surfaced in the UI for honesty."""
    elevation_m: float
    slope_deg: float
    rainfall_24h_mm: float
    rainfall_7d_mm: float
    rainfall_annual_mm: float
    humidity_pct: float
    temperature_c: float
    pressure_hpa: float
    soil_moisture: float
    distance_to_river_km: float
    river_discharge: float            # m^3/s — Open-Meteo Flood API
    water_level: float                # m above normal (estimated from discharge)
    vegetation_index: float           # NDVI proxy
    mining_proximity_km: float        # distance to nearest mine/quarry (OSM)
    drainage_density: float
    urbanization: float
    antecedent_precip_index: float
    data_quality: dict[str, str] = Field(default_factory=dict)


class RainfallPoint(BaseModel):
    date: str
    rainfall_mm: float


class HazardResult(BaseModel):
    probability: float = Field(..., ge=0, le=1)
    risk_level: str                   # Low | Moderate | High | Severe
    confidence: float = Field(..., ge=0, le=1)
    contributing_factors: list[str] = Field(default_factory=list)


class FeatureContribution(BaseModel):
    feature: str
    importance: float


class PredictionResponse(BaseModel):
    location: GeoLocation
    features: EnvironmentFeatures
    flood: HazardResult
    landslide: HazardResult
    severity_score: float = Field(..., ge=0, le=100)
    severity_level: str
    explanation: str
    flood_factors: list[FeatureContribution]
    landslide_factors: list[FeatureContribution]
    rainfall_timeline: list[RainfallPoint]   # last ~14 days, for the trend chart
    disclaimer: str
