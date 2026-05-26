"""
services/geocoding.py
=====================
Turns a place name into coordinates. Uses TWO free, keyless geocoders so a
flaky server never breaks a lookup:
  1. Open-Meteo Geocoding API  (primary)
  2. OpenStreetMap Nominatim   (fallback)

IMPORTANT — synchronous on purpose
  This module uses the SYNCHRONOUS httpx client (`httpx.Client`), not the
  async one. The synchronous networking path is the most compatible across
  Python versions, including very new ones (3.13 / 3.14) where the async
  stack can fail. FastAPI runs the route handlers that call this in a
  threadpool, so the event loop is never blocked.

NOTE: BhoomiSense predicts for a *specific city or town*, not a whole country.
"""

from __future__ import annotations
import httpx

from app.config import get_settings

settings = get_settings()
OPEN_METEO_GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"


def _open_meteo(client: httpx.Client, city: str) -> dict | None:
    """Primary geocoder — Open-Meteo."""
    try:
        r = client.get(
            OPEN_METEO_GEOCODE,
            params={"name": city, "count": 1, "language": "en", "format": "json"},
            timeout=settings.http_timeout_seconds,
        )
        r.raise_for_status()
        results = r.json().get("results") or []
    except Exception as e:                          # surfaced, not hidden
        print(f"[geocode] Open-Meteo failed for '{city}': {type(e).__name__}: {e}")
        return None
    if not results:
        return None
    t = results[0]
    return {"name": t.get("name", city),
            "latitude": float(t["latitude"]),
            "longitude": float(t["longitude"]),
            "country": t.get("country")}


def _nominatim(client: httpx.Client, city: str) -> dict | None:
    """Fallback geocoder — OpenStreetMap Nominatim."""
    try:
        r = client.get(
            settings.nominatim_url,
            params={"q": city, "format": "json", "limit": 1, "addressdetails": 1},
            headers={"User-Agent": settings.user_agent},
            timeout=settings.http_timeout_seconds,
        )
        r.raise_for_status()
        results = r.json()
    except Exception as e:
        print(f"[geocode] Nominatim failed for '{city}': {type(e).__name__}: {e}")
        return None
    if not results:
        return None
    t = results[0]
    return {"name": t.get("display_name", city).split(",")[0].strip(),
            "latitude": float(t["lat"]),
            "longitude": float(t["lon"]),
            "country": t.get("address", {}).get("country")}


def geocode_city(city: str) -> dict | None:
    """Return {name, latitude, longitude, country}, or None if not found.
    Synchronous — safe to call from a FastAPI threadpool route."""
    with httpx.Client() as client:
        return _open_meteo(client, city) or _nominatim(client, city)
