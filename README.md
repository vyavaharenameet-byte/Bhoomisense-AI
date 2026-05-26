# 🌍 BhoomiSense AI

**A climate disaster intelligence platform** — predicts flood probability,
landslide probability, and an environmental severity score for any location on
Earth, using a calibrated machine-learning ensemble fed by live geospatial data.

Built entirely on **free, open-source tools and keyless public APIs** — a
zero-budget student can run and deploy the whole thing.

> ⚠️ **Honest disclaimer.** BhoomiSense is a decision-support and educational
> tool. Real flood/landslide prediction is genuinely hard, and the project
> ships with *synthetic* training data by default (see below). Its predictions
> are model estimates, **not official warnings** — always follow IMD, NDMA and
> local disaster authorities. This disclaimer is also shown in the app UI.

---

## What it does

1. You enter a city (or click anywhere on the map).
2. The backend geocodes it and concurrently fetches **elevation, slope,
   rainfall (24h / 7d / annual), humidity, temperature, pressure, soil
   moisture, river proximity, vegetation, drainage and urbanization**.
3. A tuned **XGBoost + LightGBM + Random Forest soft-voting ensemble** with
   probability calibration predicts flood risk, landslide risk and a 0–100
   severity score, each with a confidence value.
4. The UI shows animated risk gauges, an interactive GIS map, the live
   environmental inputs (flagged *measured* vs *estimated*), an **Explainable-AI
   panel** with SHAP feature importances, and a natural-language explanation.

## Tech stack (all free / open-source)

| Layer | Tech |
|---|---|
| Frontend | React + TypeScript, Tailwind CSS, Framer Motion, Recharts, React-Leaflet |
| Backend | FastAPI, Uvicorn, httpx (async), Pydantic |
| ML | scikit-learn, XGBoost, LightGBM, SHAP |
| Data APIs | Open-Meteo + Open-Meteo **Flood API**, Open-Elevation, OpenStreetMap (Nominatim + Overpass) — *no keys* |
| Maps | Leaflet + OpenStreetMap tiles |
| Deploy | Vercel (frontend) · Render/Railway (backend) · Supabase Postgres · Docker |

## Project structure

```
bhoomisense-ai/
├── ml/                      # Machine-learning pipeline (train here)
│   ├── generate_synthetic_data.py  # synthetic data (runs day one)
│   ├── build_real_dataset.py       # ingests NASA/Kaggle real datasets
│   ├── feature_engineering.py      # separate flood/landslide feature sets
│   ├── train.py                   # ensemble training + calibration + SHAP
│   ├── evaluate.py
│   └── README.md
├── backend/                 # FastAPI inference API
│   └── app/
│       ├── main.py                # app + lifespan model loading
│       ├── config.py
│       ├── schemas.py
│       ├── feature_engineering.py  # copy of ml/ version
│       ├── api/        predict.py, meta.py
│       ├── services/   environment.py, geocoding.py, inference.py
│       └── models/     *.joblib   (trained models)
├── frontend/                # React + TS dashboard
│   └── src/
│       ├── App.tsx, api.ts, types.ts
│       ├── components/  SearchBar, HazardCard, RiskMap, ...
│       └── pages/Dashboard.tsx
├── docker-compose.yml
└── ARCHITECTURE.md          # full architecture, deployment, roadmap
```

---

## Quick start (local, ~10 minutes)

### 1 — Train the models

```bash
cd ml
python -m venv .venv && source .venv/bin/activate   # Win: .venv\Scripts\activate
pip install -r requirements.txt
python generate_synthetic_data.py     # -> data/training_data.csv
python train.py                       # -> models/*.joblib
cp models/*.joblib models/metadata.json ../backend/app/models/
```

*(Pre-trained demo models are already included in `backend/app/models/`, so you
can skip straight to step 2 to just try it.)*

### 2 — Run the backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload          # http://localhost:8000/docs
```

### 3 — Run the frontend

```bash
cd frontend
npm install
npm run dev                            # http://localhost:5173
```

Open `http://localhost:5173`, search a city, and explore.

### Or run everything with Docker

```bash
docker compose up --build              # frontend :8080  ·  backend :8000
```

---

## Using real data instead of synthetic

The pipeline ships with a *physically-motivated synthetic* dataset so it runs
on day one. To get real-world results, swap in real labelled inventories — the
**NASA Global Landslide Catalog**, flood inventories, etc. Full instructions
are in [`ml/README.md`](ml/README.md) → *"Using real data"*.

## Deployment, scaling, security, roadmap

See **[`ARCHITECTURE.md`](ARCHITECTURE.md)** — it covers the full system
architecture, every free-tier limit, deployment steps for Vercel/Render, Docker,
ML engineering notes, security hardening, scalability, and a step-by-step
roadmap for the remaining features (auth, admin dashboard, heatmaps, alerts).

## License

MIT — free to use, modify and learn from.
