"""
feature_engineering.py
======================
Single source of truth for feature engineering — used IDENTICALLY at training
time (ml/train.py) and inference time (backend), preventing training/serving
skew.

This version uses SEPARATE feature sets per hazard, because flood and landslide
are driven by different physics:

  FLOOD      <- water arriving + water not draining away
               (rainfall, soil saturation, river discharge/level, low-flat
                terrain, proximity to rivers, poor drainage)

  LANDSLIDE  <- slopes failing under load
               (sustained rainfall, steep slope, saturated soil, sparse
                vegetation, slope disturbance from mining)

A location is described by one shared RAW feature dict; each hazard then
selects and derives only the features relevant to it.
"""

from __future__ import annotations
import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# RAW features — everything the backend collects for a location.
# --------------------------------------------------------------------------
RAW_FEATURES = [
    "elevation_m", "slope_deg", "rainfall_24h_mm", "rainfall_7d_mm",
    "rainfall_annual_mm", "humidity_pct", "temperature_c", "pressure_hpa",
    "soil_moisture", "distance_to_river_km", "river_discharge", "water_level",
    "vegetation_index", "mining_proximity_km", "drainage_density",
    "urbanization", "antecedent_precip_index",
]

# --------------------------------------------------------------------------
# Per-hazard MODEL INPUT columns (raw + engineered). Order is fixed — the
# models are trained on exactly these columns in this order.
# --------------------------------------------------------------------------
FLOOD_FEATURES = [
    # raw
    "rainfall_24h_mm", "rainfall_7d_mm", "humidity_pct", "soil_moisture",
    "river_discharge", "water_level", "elevation_m", "distance_to_river_km",
    "drainage_density", "urbanization",
    # engineered
    "rainfall_accumulation", "rain_soil_interaction", "terrain_wetness",
    "drainage_deficit", "elevation_river_ratio", "flood_pressure_index",
]

LANDSLIDE_FEATURES = [
    # raw
    "rainfall_7d_mm", "slope_deg", "elevation_m", "soil_moisture",
    "mining_proximity_km", "vegetation_index", "humidity_pct",
    "antecedent_precip_index",
    # engineered
    "slope_rain_stress", "terrain_instability", "vegetation_stability",
    "mining_disturbance", "saturated_slope_load",
]

# Severity regressor sees the union of both hazards' signals.
SEVERITY_FEATURES = sorted(set(FLOOD_FEATURES) | set(LANDSLIDE_FEATURES))


# --------------------------------------------------------------------------
# Derived-feature engineering. Pure functions — never mutate the input.
# --------------------------------------------------------------------------
def _add_flood_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # Total recent water load (a 24h burst counts double — it arrives faster).
    out["rainfall_accumulation"] = (2.0 * out["rainfall_24h_mm"]
                                    + out["rainfall_7d_mm"])
    # Classic flood interaction: rain on already-saturated ground runs off.
    out["rain_soil_interaction"] = out["rainfall_24h_mm"] * out["soil_moisture"]
    # Saturated, low-lying ground holds water.
    out["terrain_wetness"] = (
        out["soil_moisture"] * (1.0 / (1.0 + out["elevation_m"] / 300.0))
    )
    # Urban runoff the drainage network cannot absorb.
    out["drainage_deficit"] = out["urbanization"] / (out["drainage_density"] + 0.3)
    # Height above nearby water vs how close that water is.
    out["elevation_river_ratio"] = (out["elevation_m"]
                                    / (out["distance_to_river_km"] + 1.0))
    # Combined hydraulic pressure: discharge + level, weighted by proximity.
    out["flood_pressure_index"] = (
        (out["river_discharge"] / 100.0 + out["water_level"])
        / (out["distance_to_river_km"] + 1.0)
    )
    return out


def _add_landslide_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # Slope amplified by sustained rainfall — the primary landslide trigger.
    out["slope_rain_stress"] = out["slope_deg"] * np.log1p(out["rainfall_7d_mm"])
    # Terrain instability score: steep + bare + saturated.
    out["terrain_instability"] = (
        (out["slope_deg"] / 45.0)
        * (1.0 - out["vegetation_index"].clip(0, 1))
        * out["soil_moisture"]
    )
    # Healthy vegetation roots stabilise slopes.
    out["vegetation_stability"] = (out["vegetation_index"]
                                   * (1.0 - out["slope_deg"] / 90.0))
    # Mining/quarrying near steep ground removes support — closer = worse.
    out["mining_disturbance"] = ((1.0 / (out["mining_proximity_km"] + 0.5))
                                 * out["slope_deg"])
    # Saturated soil mass loading a slope.
    out["saturated_slope_load"] = out["soil_moisture"] * out["slope_deg"]
    return out


def _ensure(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for c in cols:
        if c not in df.columns:
            df[c] = np.nan
    return df[cols]


def get_flood_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer + select the flood model's input columns, in order."""
    return _ensure(_add_flood_features(df), FLOOD_FEATURES)


def get_landslide_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer + select the landslide model's input columns, in order."""
    return _ensure(_add_landslide_features(df), LANDSLIDE_FEATURES)


def get_severity_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer everything, then select the severity regressor's columns."""
    enriched = _add_landslide_features(_add_flood_features(df))
    return _ensure(enriched, SEVERITY_FEATURES)
