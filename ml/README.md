# BhoomiSense — Machine Learning Pipeline

This folder is a self-contained ML project. It trains the three models the
backend serves: **flood**, **landslide**, and **severity**.

## Quick start (runs today, no data download needed)

```bash
cd ml
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python generate_synthetic_data.py   # -> data/training_data.csv
python train.py                     # -> models/*.joblib + metadata.json
python evaluate.py                  # -> reports/*.png
```

Then copy the trained models to the backend:

```bash
cp models/*.joblib models/metadata.json ../backend/app/models/
```

## What the pipeline does

| Stage | File | Detail |
|---|---|---|
| Data | `generate_synthetic_data.py` | Physically-motivated synthetic dataset (see below) |
| Feature engineering | `feature_engineering.py` | **Separate flood & landslide feature sets** + engineered features. **Shared with the backend** |
| Training | `train.py` | One tuned XGBoost+LightGBM+RandomForest calibrated ensemble **per hazard**, each on its own feature set |
| Evaluation | `evaluate.py` | ROC-AUC, F1, confusion matrix, calibration curve, SHAP importances |

### Why these models
- **XGBoost / LightGBM** — gradient-boosted trees are state of the art for
  tabular environmental data; they capture non-linear thresholds (e.g. "flood
  risk jumps once soil moisture > 0.7") that linear regression cannot.
- **Random Forest** — lower variance, decorrelated errors; improves the
  ensemble average.
- **Soft-voting ensemble** — averages calibrated probabilities; more robust
  than any single model.
- **Isotonic calibration** — raw tree ensembles are over-confident. Calibration
  makes "70% probability" actually mean ~70% observed frequency, which matters
  because the UI shows probabilities to users.

### Separate feature sets per hazard
Flood and landslide are different physical processes, so each has its own
trained model and its own feature set (see `feature_engineering.py`):
- **Flood** — rainfall, soil saturation, river discharge & water level, low-flat
  terrain, distance to river, drainage capacity.
- **Landslide** — sustained rainfall, slope, saturated soil, vegetation cover,
  proximity to mining/quarrying, pre-saturation.
A shared severity regressor sees the union of both.

## ⚠️ Honest note on accuracy

The synthetic data follows realistic hydrology/geotechnics, so the model
*behaves* sensibly and SHAP plots look right — but **the metrics you see are
not real-world accuracy.** Real flood/landslide prediction is genuinely hard.
Treat BhoomiSense as a decision-support and education tool, never as a
replacement for official warnings (IMD / NDMA / state disaster authorities).
The UI states this explicitly.

## Using real data

`build_real_dataset.py` does this for you. It ingests the real datasets,
filters to India, samples negatives, fetches environmental features per event,
and writes `data/training_data.csv` — which `train.py` consumes unchanged:

```bash
python build_real_dataset.py \
    --landslide-csv data/raw/global_landslide_catalog.csv \
    --flood-csv     data/raw/india_flood.csv \
    --max-rows 4000
python train.py
```

Feature enrichment is I/O-bound (one Open-Meteo archive call per location, with
caching) — start with a small `--max-rows`. Edit the `COLUMN MAPS` at the top of
the script to match your downloaded files' actual column names.

**Free, real, downloadable sources:**

| Need | Source | Notes |
|---|---|---|
| Landslide positives | NASA Global Landslide Catalog (COOLR) | Free CSV, ~11k events with lat/lon/date |
| Flood events | Dartmouth Flood Observatory / Global Flood Database | Free, polygon + date |
| India flood/landslide history | NDMA / Bhukosh (GSI) open data | Free |
| Elevation & slope | Open-Elevation API, or SRTM 30m tiles | Free |
| Rainfall history | Open-Meteo Historical/Archive API | Free, no key |
| Soil moisture | NASA SMAP / Copernicus | Free with EarthData login |
| Vegetation (NDVI) | Sentinel-2 via Sentinel Hub / Google Earth Engine | Free research tier |

**Building a real training set** (one-time data-engineering job):
1. Take landslide/flood events as **positive** samples (label = 1).
2. Sample random land locations with no recorded event as **negatives**
   (label = 0). Keep classes from being wildly imbalanced (~1:3 is fine).
3. For every sample, fetch the feature columns at that lat/lon/date using the
   APIs above (the backend's `services/` code already does this for live
   queries — reuse it for bulk feature collection).
4. Save as `data/training_data.csv`, then `python train.py`.

Negative sampling and temporal leakage are the two things to get right — see
`ARCHITECTURE.md` § "ML engineering notes".
