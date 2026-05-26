"""
services/inference.py
=====================
Loads the three serialized models once at startup and serves predictions.

For a location's environmental feature vector it returns, per hazard:
  - calibrated probability + risk level + confidence
  - human-readable contributing factors (grounded in the actual values)
  - SHAP-derived feature importances (from training metadata)
plus a composite severity score and a natural-language explanation. No paid
LLM is used — the explanation is deterministic and template-based.
"""

from __future__ import annotations
import json
import os

import joblib
import pandas as pd

from app.config import get_settings
from app.feature_engineering import (get_flood_matrix, get_landslide_matrix,
                                     get_severity_matrix)

settings = get_settings()

# Human-readable labels for SHAP feature names shown in the XAI dashboard.
_LABELS = {
    "rainfall_24h_mm": "24-hour rainfall", "rainfall_7d_mm": "7-day rainfall",
    "humidity_pct": "humidity", "soil_moisture": "soil saturation",
    "river_discharge": "river discharge", "water_level": "river water level",
    "elevation_m": "elevation", "distance_to_river_km": "distance to river",
    "drainage_density": "drainage capacity", "urbanization": "urban land cover",
    "rainfall_accumulation": "accumulated rainfall",
    "rain_soil_interaction": "rain-on-saturated-soil",
    "terrain_wetness": "low wet terrain", "drainage_deficit": "drainage deficit",
    "elevation_river_ratio": "height above water",
    "flood_pressure_index": "river hydraulic pressure",
    "slope_deg": "slope steepness", "mining_proximity_km": "mining proximity",
    "vegetation_index": "vegetation cover",
    "antecedent_precip_index": "pre-saturated ground",
    "slope_rain_stress": "rain-loaded slopes",
    "terrain_instability": "terrain instability",
    "vegetation_stability": "slope-stabilising vegetation",
    "mining_disturbance": "slope disturbance from mining",
    "saturated_slope_load": "saturated soil load on slope",
}


def _risk_level(p: float) -> str:
    return ("Low" if p < 0.20 else "Moderate" if p < 0.45
            else "High" if p < 0.70 else "Severe")


def _severity_level(s: float) -> str:
    return ("Low" if s < 30 else "Moderate" if s < 55
            else "High" if s < 75 else "Severe")


class PredictionService:
    """Holds the loaded models. Instantiate once (see main.py lifespan)."""

    def __init__(self) -> None:
        d = settings.models_dir
        self.flood = joblib.load(os.path.join(d, "flood_model.joblib"))
        self.landslide = joblib.load(os.path.join(d, "landslide_model.joblib"))
        self.severity = joblib.load(os.path.join(d, "severity_model.joblib"))
        with open(os.path.join(d, "metadata.json")) as fh:
            self.metadata = json.load(fh)

    # ---------------------------------------------------------------- predict
    def predict(self, features: dict) -> dict:
        quality = features.get("data_quality", {})
        raw = {k: v for k, v in features.items()
               if k not in ("data_quality", "rainfall_timeline")}
        row = pd.DataFrame([raw])

        flood_p = float(self.flood.predict_proba(get_flood_matrix(row))[0, 1])
        land_p = float(self.landslide.predict_proba(
            get_landslide_matrix(row))[0, 1])
        severity = max(0.0, min(100.0,
                       float(self.severity.predict(get_severity_matrix(row))[0])))

        # Confidence: decisive predictions + few estimated inputs -> higher.
        penalty = min(0.30, 0.04 * sum(1 for v in quality.values()
                                       if v == "estimated"))

        def conf(p):
            return round(max(0.35, 0.55 + 0.45 * abs(p - 0.5) * 2 - penalty), 3)

        return {
            "flood": {
                "probability": round(flood_p, 4),
                "risk_level": _risk_level(flood_p), "confidence": conf(flood_p),
                "contributing_factors": self._flood_factors(features),
            },
            "landslide": {
                "probability": round(land_p, 4),
                "risk_level": _risk_level(land_p), "confidence": conf(land_p),
                "contributing_factors": self._landslide_factors(features),
            },
            "severity_score": round(severity, 1),
            "severity_level": _severity_level(severity),
            "flood_factors": self._importances("flood"),
            "landslide_factors": self._importances("landslide"),
            "explanation": self._explain(features, flood_p, land_p, severity),
        }

    # ---------------------------------------------------------- factor logic
    @staticmethod
    def _flood_factors(f: dict) -> list[str]:
        out = []
        if f["rainfall_24h_mm"] > 50:
            out.append(f"Heavy 24h rainfall ({f['rainfall_24h_mm']:.0f} mm)")
        if f["rainfall_7d_mm"] > 120:
            out.append(f"Sustained rainfall ({f['rainfall_7d_mm']:.0f} mm/7d)")
        if f["river_discharge"] > 150:
            out.append(f"Elevated river discharge ({f['river_discharge']:.0f} m³/s)")
        if f["water_level"] > 2.5:
            out.append("High river water level")
        if f["soil_moisture"] > 0.6:
            out.append("Near-saturated soil")
        if f["distance_to_river_km"] < 2:
            out.append("Very close to a river")
        if f["elevation_m"] < 50:
            out.append("Very low-lying terrain")
        return out or ["No strongly elevated flood factors"]

    @staticmethod
    def _landslide_factors(f: dict) -> list[str]:
        out = []
        if f["slope_deg"] > 20:
            out.append(f"Steep terrain ({f['slope_deg']:.0f}° slope)")
        if f["rainfall_7d_mm"] > 120:
            out.append(f"Sustained rainfall ({f['rainfall_7d_mm']:.0f} mm/7d)")
        if f["soil_moisture"] > 0.6:
            out.append("Saturated, heavy soil")
        if f["vegetation_index"] < 0.3:
            out.append("Sparse stabilising vegetation")
        if f["mining_proximity_km"] < 5:
            out.append(f"Mining/quarrying nearby ({f['mining_proximity_km']:.1f} km)")
        if f["antecedent_precip_index"] > 1.2:
            out.append("Ground already pre-saturated")
        return out or ["No strongly elevated landslide factors"]

    def _importances(self, hazard: str, k: int = 6) -> list[dict]:
        imp = self.metadata["models"][hazard]["feature_importance"]
        return [{"feature": _LABELS.get(name, name), "importance": v}
                for name, v in list(imp.items())[:k]]

    def _explain(self, f, flood_p, land_p, severity) -> str:
        fl, ll = self._flood_factors(f), self._landslide_factors(f)
        return (
            f"This location shows {_risk_level(flood_p).lower()} flood risk "
            f"({flood_p:.0%}) and {_risk_level(land_p).lower()} landslide risk "
            f"({land_p:.0%}), with a composite severity score of "
            f"{severity:.0f}/100. Flood drivers here: {', '.join(fl).lower()}. "
            f"Landslide drivers: {', '.join(ll).lower()}. Flood risk reflects "
            "water arriving faster than it drains; landslide risk reflects "
            "slopes loaded by rain and saturated soil. Treat this as decision "
            "support alongside official advisories, not a standalone warning."
        )
