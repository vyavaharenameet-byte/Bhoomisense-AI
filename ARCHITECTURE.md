# BhoomiSense AI — Architecture & Engineering Guide

This document covers the full system: architecture, every tool choice and its
free-tier limits, deployment, Docker, production hardening, scalability,
security, ML engineering notes, and a roadmap for the remaining features.

---

## 1. System architecture

```
                        ┌──────────────────────────┐
                        │   React + TS frontend     │
                        │   (Vercel — static SPA)   │
                        └────────────┬─────────────┘
                                     │  HTTPS / JSON
                                     ▼
                        ┌──────────────────────────┐
                        │   FastAPI backend         │
                        │   (Render / Railway)      │
                        │  ┌────────────────────┐   │
   free public APIs ◄───┼──┤ environment service │  │
   (Open-Meteo,         │  ├────────────────────┤   │
    Open-Elevation,     │  │ geocoding service   │  │
    OpenStreetMap)      │  ├────────────────────┤   │
                        │  │ inference service  ─┼───┼──► models/*.joblib
                        │  └────────────────────┘   │   (loaded once at startup)
                        └──────┬────────────┬───────┘
                               │            │
                     ┌─────────▼──┐   ┌─────▼──────┐
                     │ PostgreSQL │   │   Redis    │
                     │ (Supabase) │   │  (cache)   │
                     │  optional  │   │  optional  │
                     └────────────┘   └────────────┘

   OFFLINE:  ml/  trains the ensemble → produces models/*.joblib
             which are copied into backend/app/models/
```

**Request flow** (`POST /api/predict/city`):
1. Frontend sends `{ city }`.
2. Backend geocodes via Nominatim → lat/lon.
3. `environment.collect_features()` fires 4 concurrent async calls
   (weather, annual rainfall, elevation+slope, river distance).
4. `feature_engineering` derives 6 interaction features.
5. The three calibrated models predict flood / landslide / severity.
6. A typed `PredictionResponse` returns to the frontend.

**Key design decisions**
- **Async backend** — environmental data needs 4 external calls; running them
  concurrently with `asyncio.gather` cuts latency from ~6 s to ~1–2 s.
- **Models loaded once** via FastAPI `lifespan`, not per request.
- **Graceful degradation** — every external call returns `{}` on failure and
  falls back to climatological defaults; one flaky API never breaks a prediction.
  The response's `data_quality` map tells the user which inputs were real.
- **Shared feature engineering** — the *exact same* code runs at training and
  inference time to prevent training/serving skew.

---

## 2. Folder structure

See `README.md` § "Project structure". Three independent sub-projects
(`ml/`, `backend/`, `frontend/`) so each can be developed, tested and deployed
on its own.

---

## 3. Tool choices — why, free-tier limits, alternatives

### Frontend

| Tool | Why | Free? / Limits | Alternative |
|---|---|---|---|
| React + TypeScript | Industry standard; types catch API-contract bugs | Fully open-source | Svelte, Vue |
| Tailwind CSS | Fast, consistent styling; tiny prod bundle | Open-source | CSS Modules |
| Framer Motion | Declarative animations for the "futuristic" feel | Open-source | CSS animations |
| Recharts | Simple, React-native charts (feature importance) | Open-source | Chart.js, visx |
| React-Leaflet + Leaflet | Interactive maps **without** Google Maps billing | Open-source | MapLibre GL |
| OpenStreetMap tiles | Free map tiles | Free; heavy use → run your own tile server | Carto, Stadia free tier |

### Backend

| Tool | Why | Free? / Limits | Alternative |
|---|---|---|---|
| FastAPI | Async, auto OpenAPI docs, Pydantic validation | Open-source | Flask, Litestar |
| Uvicorn | ASGI server | Open-source | Hypercorn |
| httpx | Async HTTP client for concurrent API calls | Open-source | aiohttp |

### Machine learning

| Tool | Why | Free? | Alternative |
|---|---|---|---|
| scikit-learn | Pipelines, calibration, CV, metrics | Open-source | — |
| XGBoost / LightGBM | Best-in-class for tabular environmental data | Open-source | CatBoost |
| Random Forest | Decorrelated errors → better ensemble | sklearn | ExtraTrees |
| SHAP | Explainability (the XAI dashboard) | Open-source | permutation importance |

### Data APIs — **all free, most keyless**

| API | Used for | Free-tier limit | If rate-limited |
|---|---|---|---|
| **Open-Meteo** | Weather, rainfall, soil moisture | No key; ~10k calls/day, non-commercial | Cache 30 min; fall back to OpenWeather free tier |
| **Open-Meteo Archive** | Annual rainfall history | Same | Cache per-city for days |
| **Open-Elevation** | Elevation & slope | No key; public instance can be slow/flaky | Self-host (Docker image exists); or Open-Meteo's `elevation` field |
| **Nominatim (OSM)** | Geocoding city → lat/lon | No key; ~1 req/sec; **requires User-Agent** | Cache aggressively; or Photon / Open-Meteo Geocoding |
| **Overpass (OSM)** | Nearest river/waterway | No key; shared, rate-limited | Cache; or pre-load a rivers dataset into Postgres+PostGIS |

**Honest note:** NDVI, drainage density and urbanization are *estimated* by
heuristics in `environment.py` because true values need Sentinel-2 imagery or
land-cover rasters. They are tagged `"estimated"` in `data_quality`. To make
them real, integrate Google Earth Engine (free research tier) or a one-time
Sentinel-2 / land-cover raster lookup — see § 9.

---

## 4. Environment variables

| File | Variable | Purpose |
|---|---|---|
| `backend/.env` | `ENVIRONMENT` | `development` / `production` |
| | `CORS_ORIGINS` | Comma-separated allowed frontend URLs |
| | `USER_AGENT` | Identifying UA for OSM (required by their policy) |
| | `MODELS_DIR` | Path to `*.joblib` files |
| | `DATABASE_URL` | *(optional)* Postgres connection string |
| | `REDIS_URL` | *(optional)* Redis connection string |
| `frontend/.env` | `VITE_API_URL` | Backend URL (blank in dev — Vite proxies `/api`) |

Templates: `backend/.env.example`, `frontend/.env.example`. **Never commit
`.env`** — `.gitignore` already excludes it.

---

## 5. Docker setup

- `backend/Dockerfile` — `python:3.11-slim`, deps cached in a separate layer,
  honours Render/Railway's injected `$PORT`.
- `frontend/Dockerfile` — multi-stage: Node build → nginx serves static `dist/`.
- `docker-compose.yml` — runs frontend + backend + Postgres + Redis locally:
  ```bash
  docker compose up --build
  ```

---

## 6. Deployment (free tiers)

### Backend → Render (or Railway)
1. Push the repo to GitHub.
2. Render → **New Web Service** → point at `backend/`.
3. Render auto-detects the `Dockerfile`. Set env vars from `.env.example`
   (set `CORS_ORIGINS` to your Vercel URL, `ENVIRONMENT=production`).
4. Deploy. Note the URL, e.g. `https://bhoomisense-api.onrender.com`.

> **Render free tier:** the service **sleeps after ~15 min idle**; the first
> request then takes ~30–50 s to cold-start. Mitigations: a cron pinger
> (e.g. cron-job.org) every 10 min, or accept the cold start, or use Railway
> (limited monthly credits, no forced sleep). The frontend already shows a
> loading skeleton, which masks this.

### Frontend → Vercel
1. Vercel → **Import Project** → select `frontend/`.
2. Framework preset: **Vite**. Build: `npm run build`, output: `dist`.
3. Set env var `VITE_API_URL` = your Render backend URL.
4. Deploy.

### Models
The `*.joblib` files are committed in `backend/app/models/` and ship inside the
Docker image — no separate model hosting needed. If they grow large, use Git
LFS or attach them as a GitHub Release asset and download them at build time.

### Database (only if you add auth/history)
Supabase → create a project → copy the Postgres connection string into
`DATABASE_URL`. Supabase free tier: 500 MB DB, pauses after 1 week of
inactivity.

### CI/CD
A `.github/workflows/ci.yml` doing `npm run build` + `pytest` on push gives you
free CI via GitHub Actions. Render and Vercel both auto-deploy on push to
`main`.

---

## 7. Production best practices

- **Caching.** Geocoding and weather change slowly. Add a Redis cache (key:
  rounded lat/lon, TTL 30 min) — `config.py` already exposes `redis_url` and
  `cache_ttl_seconds`. This is the single biggest lever for staying inside free
  API limits.
- **Rate limiting.** Add `slowapi` to cap requests per IP and stay polite to
  the OSM/Open-Meteo public instances.
- **Timeouts & retries.** `http_timeout_seconds` is set; add one retry with
  backoff for transient 5xx.
- **Structured logging.** Swap `print` for `logging` with JSON output so
  Render/Railway logs are searchable.
- **Health checks.** `/api/health` reports `models_loaded` — wire it to the
  platform's health-check setting.
- **Pin dependencies.** Use exact versions / a lockfile for reproducible builds.
- **Error contract.** The API already returns typed `{detail: ...}` errors;
  the frontend surfaces them.

---

## 8. Scalability

The architecture scales a long way *without* paid infrastructure:

| Bottleneck | Symptom | Fix (cheap → bigger) |
|---|---|---|
| External API limits | 429s from Open-Meteo/OSM | Redis cache → self-host Nominatim/Open-Elevation (Docker) |
| Backend cold start | Slow first request (Render free) | Cron pinger → Railway → paid instance only if needed |
| Repeated predictions | Same city queried often | Cache full `PredictionResponse` in Redis (TTL ~30 min) |
| Heatmap = many calls | Grid of N×N coord predictions | Batch endpoint + precompute popular regions nightly |
| Model inference CPU | High concurrency | Inference is ms-scale; scale horizontally (stateless backend) behind a load balancer |
| DB load | Many history writes | Postgres handles this easily; add an index on `user_id, created_at` |

Because the backend is **stateless** (models in memory, no session state),
horizontal scaling is just "run more containers" — no architecture change.

---

## 9. Security

- **CORS** — locked to an explicit allow-list (`CORS_ORIGINS`); never `*` in
  production.
- **Input validation** — Pydantic schemas constrain types and ranges
  (lat ∈ [-90,90], city length, etc.); rejects malformed input automatically.
- **No secrets in code** — everything via env vars; `.env` git-ignored.
- **Secrets management** — store production secrets in Render/Vercel's
  encrypted env-var UI, not in the repo.
- **HTTPS everywhere** — Vercel and Render terminate TLS automatically.
- **Auth (when added)** — JWT with short-lived access tokens; hash passwords
  with `bcrypt`/`argon2`; or delegate entirely to Supabase Auth. Never store
  plaintext passwords.
- **SQL safety** — use SQLAlchemy / parameterised queries; never string-format
  SQL.
- **Dependency hygiene** — enable GitHub Dependabot for free vulnerability
  alerts.
- **Rate limiting & abuse** — `slowapi` per-IP limits; consider a simple
  per-day quota if you expose it publicly.

---

## 10. ML engineering notes

The pipeline (`ml/train.py`) is deliberately not "beginner-level":

- **Preprocessing** — `SimpleImputer(median)` inside the `Pipeline`, so the
  *same* imputation runs at inference. ~3% missing values are injected into the
  synthetic data specifically to exercise this.
- **Feature engineering** — 6 interaction features (`terrain_wetness`,
  `slope_rain_stress`, `drainage_deficit`, …) encode domain knowledge that
  bare columns don't.
- **Models** — XGBoost + LightGBM + Random Forest, each tuned, combined in a
  weighted **soft-voting ensemble**.
- **Hyperparameter tuning** — `RandomizedSearchCV` (4-fold CV) over depth,
  learning rate, subsample, etc.
- **Probability calibration** — `CalibratedClassifierCV(isotonic)`. Critical:
  the UI shows probabilities to users, so "70%" must mean ~70% observed
  frequency, not just a ranking.
- **Evaluation** — ROC-AUC, F1, accuracy, confusion matrix on a held-out test
  set; `evaluate.py` adds ROC and calibration curves.
- **Explainability** — SHAP `TreeExplainer` → normalized feature importances
  saved to `metadata.json` and surfaced in the XAI dashboard.
- **Serialization** — `joblib` dumps the full calibrated pipeline.

**When you move to real data**, two things matter most:
1. **Negative sampling.** Flood/landslide catalogs are *positives only*.
   Sample non-event locations as negatives; keep classes ~1:3, and sample
   negatives from realistic land areas (not oceans).
2. **Temporal leakage.** Features must reflect conditions *at the event date*,
   not today. Use Open-Meteo's archive API with the event date. For evaluation,
   split by time (train on older events, test on newer) — a random split
   over-estimates accuracy.

---

## 11. Implementation roadmap

The core (search → fetch → predict → explainable dashboard) is **done and
working**. Layer the rest on in this order:

**Phase 1 — Real data (highest impact)**
- [ ] Download NASA Global Landslide Catalog + a flood inventory.
- [ ] Write a `ml/build_real_dataset.py` that does negative sampling and
      fetches features per event date (reuse `environment.py`).
- [ ] Retrain; evaluate with a *time-based* split. Update the UI's accuracy copy.

**Phase 2 — Persistence & caching**
- [ ] Add SQLAlchemy + `asyncpg`; create `users`, `search_history` tables.
- [ ] Add Redis caching for geocoding + weather + full predictions.
- [ ] Move search history from `localStorage` to a DB-backed endpoint.

**Phase 3 — Authentication**
- [ ] Supabase Auth (simplest) **or** custom JWT (`/auth/register`, `/auth/login`).
- [ ] Protect history/admin routes with an auth dependency.

**Phase 4 — Heatmaps & GIS layers**
- [ ] Add `POST /api/predict/grid` that scores an N×N lat/lon grid.
- [ ] Render it with `leaflet.heat` as a true risk heatmap.
- [ ] Add weather/terrain overlay layers (Open-Meteo, OSM terrain tiles).

**Phase 5 — Admin & analytics**
- [ ] Admin dashboard: region-wise aggregates, query volume, model metrics
      (read from `metadata.json` + DB).
- [ ] Disaster alerts: threshold severity → store alerts; optional email via a
      free tier (e.g. Resend free tier) or browser notifications.

**Phase 6 — Forecasting**
- [ ] Rainfall forecast: Open-Meteo already provides 7-day forecasts — display
      them directly. Only train a custom LSTM if you have a specific gap; a
      from-scratch LSTM on limited data will *not* beat Open-Meteo's model, so
      treat this as optional/research.

---

## 12. Honest limitations

- **Synthetic data by default.** Shipped metrics are not real-world accuracy.
- **Estimated features.** NDVI / drainage / urbanization are heuristics until
  you integrate satellite/land-cover data.
- **Point predictions, not hydrological models.** BhoomiSense is statistical
  decision-support; it is not a physics-based flood model and is not a
  substitute for IMD/NDMA warnings. This is stated in the app UI.
- **Free-tier ops.** Render cold starts and public-API rate limits are real;
  caching is the main mitigation.

These limitations are normal for a zero-budget project and are honestly
surfaced to users rather than hidden — which is itself good engineering.
