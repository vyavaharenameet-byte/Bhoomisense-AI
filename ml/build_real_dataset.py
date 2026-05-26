"""
build_real_dataset.py
=====================
Turns the REAL datasets named in the project spec into a training CSV that
train.py can consume directly. Replaces generate_synthetic_data.py once you
have downloaded the source files.

DATASETS (all free — download manually, then point this script at them):
  1. NASA Global Landslide Catalog (COOLR)
     https://catalog.data.gov/dataset/global-landslide-catalog-export
     -> a CSV with columns including latitude, longitude, event_date,
        country_name. We filter to India.
  2. Kaggle "India Flood" dataset (several exist; pick one with lat/lon OR
     state-level rows). Point --flood-csv at it; adjust COLUMN MAPS below to
     match its real column names.
  3. Daily Rainfall India 2009-2024 (optional — used to enrich rainfall
     features if your flood/landslide rows lack them).

WHY THIS DESIGN
  Disaster catalogs are POSITIVES ONLY (they only record events). A classifier
  needs negatives too, so we sample non-event locations across India. We also
  fetch the environmental feature vector per event so the columns match
  feature_engineering.RAW_FEATURES.

USAGE
  python build_real_dataset.py \
      --landslide-csv data/raw/global_landslide_catalog.csv \
      --flood-csv     data/raw/india_flood.csv \
      --max-rows 4000           # feature fetching is I/O-bound; start small

NOTE ON SPEED
  Feature enrichment calls Open-Meteo's archive API once per location. That is
  rate-limited and slow for large datasets. Start with --max-rows small, cache
  is built in, and you can re-run to resume. For a full run, consider Open-Meteo's
  bulk endpoints or running overnight.
"""

from __future__ import annotations
import argparse
import json
import os
import time

import numpy as np
import pandas as pd
import requests

RNG = np.random.default_rng(42)

# India bounding box (rough) — used to filter events and sample negatives.
INDIA_BBOX = {"lat_min": 6.5, "lat_max": 35.5, "lon_min": 68.0, "lon_max": 97.5}

# ---- COLUMN MAPS: edit these to match your downloaded files' headers --------
LANDSLIDE_COLS = {"lat": "latitude", "lon": "longitude",
                  "date": "event_date", "country": "country_name"}
FLOOD_COLS = {"lat": "latitude", "lon": "longitude", "date": "date"}

CACHE_PATH = "data/.feature_cache.json"


# --------------------------------------------------------------------------
# 1. Load positive events
# --------------------------------------------------------------------------
def load_landslides(path: str) -> pd.DataFrame:
    """NASA Global Landslide Catalog -> Indian landslide events."""
    df = pd.read_csv(path)
    c = LANDSLIDE_COLS
    if c["country"] in df.columns:
        df = df[df[c["country"]].astype(str).str.contains("India", na=False)]
    df = df.rename(columns={c["lat"]: "latitude", c["lon"]: "longitude",
                            c["date"]: "event_date"})
    df = df.dropna(subset=["latitude", "longitude"])
    df = df[_in_india(df)]
    out = df[["latitude", "longitude"]].copy()
    out["event_date"] = pd.to_datetime(df.get("event_date"), errors="coerce")
    out["flood_label"] = 0
    out["landslide_label"] = 1
    print(f"  landslide positives (India): {len(out)}")
    return out


def load_floods(path: str) -> pd.DataFrame:
    """Kaggle India flood dataset -> flood events. Adjust FLOOD_COLS to match."""
    df = pd.read_csv(path)
    c = FLOOD_COLS
    df = df.rename(columns={c["lat"]: "latitude", c["lon"]: "longitude"})
    df = df.dropna(subset=["latitude", "longitude"])
    df = df[_in_india(df)]
    out = df[["latitude", "longitude"]].copy()
    out["event_date"] = pd.to_datetime(df.get(c["date"]), errors="coerce")
    out["flood_label"] = 1
    out["landslide_label"] = 0
    print(f"  flood positives (India): {len(out)}")
    return out


def _in_india(df: pd.DataFrame) -> pd.Series:
    b = INDIA_BBOX
    return (df["latitude"].between(b["lat_min"], b["lat_max"])
            & df["longitude"].between(b["lon_min"], b["lon_max"]))


# --------------------------------------------------------------------------
# 2. Sample negative (no-event) locations
# --------------------------------------------------------------------------
def sample_negatives(n: int) -> pd.DataFrame:
    """Random Indian land points assumed event-free. For best results, exclude
    points within a few km of known events (not done here for brevity)."""
    b = INDIA_BBOX
    out = pd.DataFrame({
        "latitude": RNG.uniform(b["lat_min"], b["lat_max"], n),
        "longitude": RNG.uniform(b["lon_min"], b["lon_max"], n),
    })
    out["event_date"] = pd.NaT
    out["flood_label"] = 0
    out["landslide_label"] = 0
    print(f"  negative samples: {len(out)}")
    return out


# --------------------------------------------------------------------------
# 3. Enrich each location with environmental features (Open-Meteo archive)
# --------------------------------------------------------------------------
def _load_cache() -> dict:
    if os.path.exists(CACHE_PATH):
        return json.load(open(CACHE_PATH))
    return {}


def enrich_features(df: pd.DataFrame) -> pd.DataFrame:
    """Fetch the RAW feature columns for every row. I/O-bound and rate-limited;
    results are cached to data/.feature_cache.json so re-runs resume."""
    cache = _load_cache()
    rows = []
    for i, r in df.reset_index(drop=True).iterrows():
        key = f"{r.latitude:.3f},{r.longitude:.3f}"
        if key in cache:
            rows.append(cache[key])
            continue
        feats = _fetch_one(r.latitude, r.longitude, r.event_date)
        cache[key] = feats
        rows.append(feats)
        if i % 25 == 0:
            json.dump(cache, open(CACHE_PATH, "w"))
            print(f"    enriched {i}/{len(df)}")
        time.sleep(0.4)            # be polite to the public API
    json.dump(cache, open(CACHE_PATH, "w"))
    feat_df = pd.DataFrame(rows)
    return pd.concat([df.reset_index(drop=True), feat_df], axis=1)


def _fetch_one(lat: float, lon: float, date) -> dict:
    """Historical weather/rainfall at (lat,lon) around the event date.
    Terrain / mining / vegetation are estimated — same heuristics as the live
    backend, so training and serving stay consistent. Failures -> defaults."""
    end = pd.Timestamp(date) if pd.notna(date) else pd.Timestamp("2022-07-15")
    start = end - pd.Timedelta(days=7)
    try:
        resp = requests.get(
            "https://archive-api.open-meteo.com/v1/archive",
            params={"latitude": lat, "longitude": lon,
                    "start_date": start.strftime("%Y-%m-%d"),
                    "end_date": end.strftime("%Y-%m-%d"),
                    "daily": "precipitation_sum,temperature_2m_mean",
                    "hourly": "soil_moisture_0_to_7cm,relative_humidity_2m",
                    "timezone": "auto"},
            timeout=20)
        d = resp.json()
        rain = d.get("daily", {}).get("precipitation_sum", []) or [0]
        soil = d.get("hourly", {}).get("soil_moisture_0_to_7cm", []) or [0.3]
        hum = d.get("hourly", {}).get("relative_humidity_2m", []) or [65]
        temp = d.get("daily", {}).get("temperature_2m_mean", []) or [26]
    except Exception:
        rain, soil, hum, temp = [0], [0.3], [65], [26]

    rain_7d = float(np.nansum(rain))
    rain_24h = float(rain[-1] or 0)
    soil_m = float(np.nanmean(soil))
    # Estimated terrain/land features (replace with real rasters if available).
    elev = float(RNG.gamma(2.0, 250.0))
    return {
        "elevation_m": elev,
        "slope_deg": float(np.clip(RNG.gamma(1.5, 4.0) + elev / 800, 0, 60)),
        "rainfall_24h_mm": rain_24h,
        "rainfall_7d_mm": rain_7d,
        "rainfall_annual_mm": rain_7d * 12.0,        # rough scale-up
        "humidity_pct": float(np.nanmean(hum)),
        "temperature_c": float(np.nanmean(temp)),
        "pressure_hpa": 1009.0,
        "soil_moisture": soil_m,
        "distance_to_river_km": float(np.clip(RNG.gamma(2.0, 4.0), 0, 60)),
        "river_discharge": float(np.clip(rain_7d * 0.4, 0, 1200)),
        "water_level": float(np.clip(rain_7d / 200.0, 0, 9)),
        "vegetation_index": float(np.clip(RNG.normal(0.45, 0.2), -0.1, 0.95)),
        "mining_proximity_km": float(np.clip(RNG.gamma(3.0, 6.0), 0.1, 80)),
        "drainage_density": float(np.clip(RNG.normal(1.2, 0.5), 0.1, 3.5)),
        "urbanization": 0.35,
        "antecedent_precip_index": float(np.clip(soil_m * 0.6 + rain_7d / 600, 0, 2)),
    }


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--landslide-csv", required=True)
    ap.add_argument("--flood-csv", required=True)
    ap.add_argument("--max-rows", type=int, default=4000)
    ap.add_argument("--neg-ratio", type=float, default=1.5,
                    help="negatives per positive")
    args = ap.parse_args()

    os.makedirs("data", exist_ok=True)
    print("Loading positives ...")
    pos = pd.concat([load_landslides(args.landslide_csv),
                     load_floods(args.flood_csv)], ignore_index=True)

    neg = sample_negatives(int(len(pos) * args.neg_ratio))
    full = pd.concat([pos, neg], ignore_index=True)
    full = full.sample(frac=1, random_state=42).reset_index(drop=True)

    if len(full) > args.max_rows:
        print(f"Capping at --max-rows={args.max_rows} (feature fetch is slow)")
        full = full.head(args.max_rows)

    print("Enriching with environmental features (this is the slow part) ...")
    full = enrich_features(full)

    # Severity proxy from the two labels (real data has no severity column).
    full["severity_score"] = (60 * full["flood_label"]
                              + 55 * full["landslide_label"]
                              + RNG.normal(8, 4, len(full))).clip(0, 100)

    full.to_csv("data/training_data.csv", index=False)
    print(f"\nWrote data/training_data.csv  shape={full.shape}")
    print("Now run:  python train.py")


if __name__ == "__main__":
    main()
