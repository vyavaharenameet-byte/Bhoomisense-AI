"""
generate_synthetic_data.py
==========================
Physically-motivated synthetic dataset so the whole pipeline runs on day one,
before downloading the real datasets. See ml/README.md and build_real_dataset.py
for the real-data path (NASA Global Landslide Catalog, Kaggle India flood data).

The synthetic labels follow realistic hydrology / geotechnics so the model
behaves sensibly and SHAP plots look right — but the metrics are NOT
real-world accuracy.
"""

from __future__ import annotations
import os
import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def generate(n: int = 20_000) -> pd.DataFrame:
    """Generate `n` synthetic Indian-region location-samples."""

    # --- Geophysical / terrain features (India-ish ranges) ----------------
    lat = RNG.uniform(8.0, 35.0, n)
    lon = RNG.uniform(68.0, 97.0, n)
    elevation_m = np.clip(RNG.gamma(2.0, 250.0, n), 0, 5000)
    slope_deg = np.clip(RNG.gamma(1.5, 4.0, n) + elevation_m / 800.0, 0, 60)

    # --- Rainfall ----------------------------------------------------------
    rainfall_24h_mm = np.clip(RNG.gamma(1.3, 18.0, n), 0, 400)
    rainfall_7d_mm = rainfall_24h_mm * RNG.uniform(1.5, 4.0, n)
    rainfall_annual_mm = np.clip(RNG.normal(1100, 500, n), 150, 4000)

    # --- Atmosphere --------------------------------------------------------
    humidity_pct = np.clip(RNG.normal(68, 16, n), 10, 100)
    temperature_c = np.clip(RNG.normal(26, 7, n), -5, 48)
    pressure_hpa = np.clip(RNG.normal(1009, 8, n), 970, 1040)

    # --- Hydrology ---------------------------------------------------------
    soil_moisture = np.clip(RNG.beta(2, 3, n) + rainfall_7d_mm / 1500.0, 0, 1)
    distance_to_river_km = np.clip(RNG.gamma(2.0, 4.0, n), 0, 60)
    # River discharge (m^3/s) rises with rainfall and falls with distance.
    river_discharge = np.clip(
        RNG.gamma(2.0, 30.0, n) + rainfall_7d_mm * 0.4
        - distance_to_river_km * 2.0, 0, 1200)
    # Water level (m above normal) — correlated with discharge.
    water_level = np.clip(river_discharge / 200.0 + RNG.normal(0, 0.6, n), 0, 9)

    # --- Land / vegetation -------------------------------------------------
    vegetation_index = np.clip(RNG.normal(0.45, 0.2, n), -0.1, 0.95)  # NDVI proxy
    drainage_density = np.clip(RNG.normal(1.2, 0.5, n), 0.1, 3.5)
    urbanization = np.clip(RNG.beta(2, 5, n), 0, 1)
    # Distance to nearest mine/quarry (km) — most places are far from mining.
    mining_proximity_km = np.clip(RNG.gamma(3.0, 6.0, n), 0.1, 80)
    # Antecedent Precipitation Index — how saturated the ground already is.
    antecedent_precip_index = np.clip(
        soil_moisture * 0.6 + rainfall_7d_mm / 600.0, 0, 2)

    # --- Latent FLOOD risk -------------------------------------------------
    flood_logit = (
        -2.7
        - 0.0022 * elevation_m
        + 0.030 * rainfall_24h_mm
        + 0.0040 * rainfall_7d_mm
        + 2.3 * soil_moisture
        + 0.0035 * river_discharge
        + 0.45 * water_level
        - 0.075 * distance_to_river_km
        - 0.55 * drainage_density
        + 1.8 * urbanization
        + 0.010 * humidity_pct
        + RNG.normal(0, 0.6, n)
    )
    flood_prob = _sigmoid(flood_logit)
    flood_label = (RNG.uniform(0, 1, n) < flood_prob).astype(int)

    # --- Latent LANDSLIDE risk --------------------------------------------
    landslide_logit = (
        -3.5
        + 0.115 * slope_deg
        + 0.0040 * rainfall_7d_mm
        + 2.0 * soil_moisture
        - 1.7 * vegetation_index
        + 0.00035 * elevation_m
        + 0.9 * antecedent_precip_index
        + 0.012 * humidity_pct
        + 0.9 / (mining_proximity_km / 5.0 + 1.0)   # closer mining -> higher
        + RNG.normal(0, 0.65, n)
    )
    landslide_prob = _sigmoid(landslide_logit)
    landslide_label = (RNG.uniform(0, 1, n) < landslide_prob).astype(int)

    # --- Composite severity (regression target, 0-100) -------------------
    severity = (
        55 * flood_prob + 50 * landslide_prob
        + 25 * urbanization + RNG.normal(0, 5, n)
    )
    severity_score = np.clip(severity, 0, 100)

    df = pd.DataFrame({
        "latitude": lat, "longitude": lon,
        "elevation_m": elevation_m, "slope_deg": slope_deg,
        "rainfall_24h_mm": rainfall_24h_mm, "rainfall_7d_mm": rainfall_7d_mm,
        "rainfall_annual_mm": rainfall_annual_mm,
        "humidity_pct": humidity_pct, "temperature_c": temperature_c,
        "pressure_hpa": pressure_hpa, "soil_moisture": soil_moisture,
        "distance_to_river_km": distance_to_river_km,
        "river_discharge": river_discharge, "water_level": water_level,
        "vegetation_index": vegetation_index,
        "mining_proximity_km": mining_proximity_km,
        "drainage_density": drainage_density, "urbanization": urbanization,
        "antecedent_precip_index": antecedent_precip_index,
        "flood_label": flood_label, "landslide_label": landslide_label,
        "severity_score": severity_score,
    })

    # Inject ~3% missing values to exercise the imputation pipeline.
    for col in ["soil_moisture", "vegetation_index", "river_discharge",
                "water_level", "mining_proximity_km"]:
        df.loc[RNG.uniform(0, 1, n) < 0.03, col] = np.nan

    return df


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    out = generate(20_000)
    out.to_csv("data/training_data.csv", index=False)
    print(f"Wrote data/training_data.csv  shape={out.shape}")
    print(f"Flood positives    : {out.flood_label.mean():.1%}")
    print(f"Landslide positives: {out.landslide_label.mean():.1%}")
