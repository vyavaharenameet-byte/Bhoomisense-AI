"""
services/environment.py
=======================
Collects the environmental + geospatial feature vector for a lat/lon using
ONLY free, keyless public APIs.

IMPORTANT — synchronous on purpose
  Uses the SYNCHRONOUS httpx client for maximum compatibility (incl. Python
  3.13 / 3.14, where the async HTTP stack can fail). The five external calls
  still run CONCURRENTLY via a thread pool, so a full fetch is ~1-2 s, not ~8 s.
  FastAPI runs the calling route in a threadpool, so nothing blocks.

Data sources (all free, no key)
  Open-Meteo Forecast / Archive / Flood API · Open-Elevation · OSM Overpass.
Estimated fields (water level, vegetation, drainage, urbanization) are flagged
in `data_quality` because true values need gauges / satellite rasters.
"""

from __future__ import annotations
import math
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import httpx

from app.config import get_settings

settings = get_settings()
FLOOD_API_URL = "https://flood-api.open-meteo.com/v1/flood"


def _get(client: httpx.Client, url: str, **params) -> dict:
    """GET returning {} on failure — one flaky API never breaks a request.
    The real error is printed so it is not silently hidden."""
    try:
        r = client.get(url, params=params or None,
                        timeout=settings.http_timeout_seconds)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[env] GET {url} failed: {type(e).__name__}: {e}")
        return {}


# --------------------------------------------------------------------------
# Collectors (each runs in its own thread)
# --------------------------------------------------------------------------
def fetch_weather(client, lat, lon) -> dict:
    """Current weather + 14-day rainfall history + soil moisture."""
    d = _get(client, settings.open_meteo_forecast_url,
             latitude=lat, longitude=lon,
             current="temperature_2m,relative_humidity_2m,surface_pressure,"
                     "soil_moisture_0_to_1cm,precipitation",
             daily="precipitation_sum", past_days=14, forecast_days=1,
             timezone="auto")
    cur = d.get("current", {})
    daily = d.get("daily", {})
    rain = daily.get("precipitation_sum", []) or [0]
    dates = daily.get("time", []) or []
    timeline = [{"date": dt, "rainfall_mm": float(v or 0)}
                for dt, v in zip(dates, rain)]
    return {
        "temperature_c": cur.get("temperature_2m", 25.0),
        "humidity_pct": cur.get("relative_humidity_2m", 65.0),
        "pressure_hpa": cur.get("surface_pressure", 1009.0),
        "soil_moisture": cur.get("soil_moisture_0_to_1cm", 0.3),
        "rainfall_24h_mm": cur.get("precipitation", rain[-1] or 0.0),
        "rainfall_7d_mm": float(sum(v or 0 for v in rain[-7:])),
        "rainfall_timeline": timeline,
        "_ok": bool(cur),
    }


def fetch_annual_rainfall(client, lat, lon) -> dict:
    last_year = date.today().year - 1
    d = _get(client, settings.open_meteo_archive_url,
             latitude=lat, longitude=lon,
             start_date=f"{last_year}-01-01", end_date=f"{last_year}-12-31",
             daily="precipitation_sum", timezone="auto")
    series = d.get("daily", {}).get("precipitation_sum", [])
    return {"rainfall_annual_mm": float(sum(v or 0 for v in series)) if series
            else 1100.0, "_ok": bool(series)}


def fetch_river_discharge(client, lat, lon) -> dict:
    """River discharge (m^3/s) from the Open-Meteo Flood API."""
    d = _get(client, FLOOD_API_URL, latitude=lat, longitude=lon,
             daily="river_discharge")
    series = d.get("daily", {}).get("river_discharge", [])
    discharge = float(series[-1]) if series and series[-1] is not None else 0.0
    return {"river_discharge": round(discharge, 1),
            "water_level": round(min(9.0, discharge / 200.0), 2),
            "_ok": bool(series)}


def fetch_elevation_and_slope(client, lat, lon) -> dict:
    """Elevation + slope from 4 neighbouring samples (finite differences)."""
    dd = 0.0025
    pts = [(lat, lon), (lat + dd, lon), (lat - dd, lon),
           (lat, lon + dd), (lat, lon - dd)]
    d = _get(client, settings.open_elevation_url,
             locations="|".join(f"{a},{b}" for a, b in pts))
    res = d.get("results", [])
    if len(res) == 5:
        e = [r["elevation"] for r in res]
        c, n, s, ee, w = e
        dy = (n - s) / (2 * dd * 111_000)
        dx = (ee - w) / (2 * dd * 111_000 *
                         max(math.cos(math.radians(lat)), 0.01))
        slope = math.degrees(math.atan(math.hypot(dx, dy)))
        return {"elevation_m": float(c), "slope_deg": float(slope), "_ok": True}
    return {"elevation_m": 200.0, "slope_deg": 4.0, "_ok": False}


def _haversine(la1, lo1, la2, lo2) -> float:
    R = 6371.0
    p1, p2 = math.radians(la1), math.radians(la2)
    dphi, dlam = math.radians(la2 - la1), math.radians(lo2 - lo1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def fetch_osm_geospatial(client, lat, lon) -> dict:
    """Nearest river AND nearest mine/quarry via OSM Overpass."""
    q = f"""
    [out:json][timeout:18];
    (
      way(around:9000,{lat},{lon})["waterway"~"river|stream|canal"];
      way(around:15000,{lat},{lon})["landuse"="quarry"];
      way(around:15000,{lat},{lon})["industrial"="mine"];
      node(around:15000,{lat},{lon})["man_made"="mineshaft"];
    );
    out center 60;
    """
    try:
        r = client.post(settings.overpass_url, data={"data": q},
                         timeout=settings.http_timeout_seconds)
        r.raise_for_status()
        elements = r.json().get("elements", [])
    except Exception as e:
        print(f"[env] Overpass failed: {type(e).__name__}: {e}")
        elements = []

    rivers, mines = [], []
    for el in elements:
        c = el.get("center") or ({"lat": el.get("lat"), "lon": el.get("lon")}
                                 if "lat" in el else None)
        if not c or c["lat"] is None:
            continue
        dist = _haversine(lat, lon, c["lat"], c["lon"])
        (rivers if "waterway" in el.get("tags", {}) else mines).append(dist)

    return {"distance_to_river_km": round(min(rivers), 2) if rivers else 9.0,
            "mining_proximity_km": round(min(mines), 2) if mines else 50.0,
            "_river_ok": bool(rivers), "_mine_ok": bool(mines)}


def _estimate_derived(base: dict) -> dict:
    """Features needing satellite/land-cover rasters — estimated here."""
    annual = base["rainfall_annual_mm"]
    soil, rain7 = base["soil_moisture"], base["rainfall_7d_mm"]
    return {
        "vegetation_index": round(max(-0.1, min(0.9, 0.15 + annual / 3000.0)), 3),
        "drainage_density": round(max(0.3, min(3.0, 0.6 + annual / 1500.0)), 3),
        "urbanization": 0.35,
        "antecedent_precip_index": round(
            max(0.0, min(2.0, soil * 0.6 + rain7 / 600.0)), 3),
    }


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------
def collect_features(lat: float, lon: float) -> dict:
    """Fetch every environmental + geospatial feature. The five external calls
    run concurrently in a thread pool. Synchronous — safe in a FastAPI
    threadpool route."""
    headers = {"User-Agent": settings.user_agent}
    with httpx.Client(headers=headers) as client:
        with ThreadPoolExecutor(max_workers=5) as ex:
            j_weather = ex.submit(fetch_weather, client, lat, lon)
            j_annual = ex.submit(fetch_annual_rainfall, client, lat, lon)
            j_flood = ex.submit(fetch_river_discharge, client, lat, lon)
            j_terrain = ex.submit(fetch_elevation_and_slope, client, lat, lon)
            j_osm = ex.submit(fetch_osm_geospatial, client, lat, lon)
            weather = j_weather.result()
            annual = j_annual.result()
            flood = j_flood.result()
            terrain = j_terrain.result()
            osm = j_osm.result()

    base = {**weather, **annual, **flood, **terrain, **osm}
    derived = _estimate_derived(base)

    quality = {
        "weather": "measured" if weather.get("_ok") else "estimated",
        "annual_rainfall": "measured" if annual.get("_ok") else "estimated",
        "river_discharge": "measured" if flood.get("_ok") else "estimated",
        "water_level": "estimated",
        "terrain": "measured" if terrain.get("_ok") else "estimated",
        "distance_to_river": "measured" if osm.get("_river_ok") else "estimated",
        "mining_proximity": "measured" if osm.get("_mine_ok") else "estimated",
        "vegetation_index": "estimated",
        "drainage_density": "estimated",
        "urbanization": "estimated",
    }

    return {
        "elevation_m": base["elevation_m"], "slope_deg": base["slope_deg"],
        "rainfall_24h_mm": base["rainfall_24h_mm"],
        "rainfall_7d_mm": base["rainfall_7d_mm"],
        "rainfall_annual_mm": base["rainfall_annual_mm"],
        "humidity_pct": base["humidity_pct"],
        "temperature_c": base["temperature_c"],
        "pressure_hpa": base["pressure_hpa"],
        "soil_moisture": base["soil_moisture"],
        "distance_to_river_km": base["distance_to_river_km"],
        "river_discharge": base["river_discharge"],
        "water_level": base["water_level"],
        "mining_proximity_km": base["mining_proximity_km"],
        **derived,
        "data_quality": quality,
        "rainfall_timeline": base["rainfall_timeline"],
    }
