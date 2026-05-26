"""Application settings. Values are read from environment variables / .env.
All external services here are FREE and most need no API key."""

from __future__ import annotations
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "BhoomiSense AI"
    environment: str = "development"          # development | production

    # --- CORS: which frontends may call this API ---------------------------
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # --- Free external services (no key required) --------------------------
    open_meteo_forecast_url: str = "https://api.open-meteo.com/v1/forecast"
    open_meteo_archive_url: str = "https://archive-api.open-meteo.com/v1/archive"
    open_elevation_url: str = "https://api.open-elevation.com/api/v1/lookup"
    nominatim_url: str = "https://nominatim.openstreetmap.org/search"
    overpass_url: str = "https://overpass-api.de/api/interpreter"

    # Nominatim's usage policy REQUIRES a real identifying User-Agent.
    user_agent: str = "BhoomiSenseAI/1.0 (contact: you@example.com)"

    # --- Optional: only if you add OpenWeather as a fallback ---------------
    openweather_api_key: str | None = None

    # --- Models -------------------------------------------------------------
    models_dir: str = "app/models"

    # --- Cache / DB (optional — see ARCHITECTURE.md) -----------------------
    redis_url: str | None = None              # e.g. redis://localhost:6379/0
    database_url: str | None = None           # e.g. postgresql+asyncpg://...

    # --- HTTP client tuning -------------------------------------------------
    http_timeout_seconds: float = 12.0
    cache_ttl_seconds: int = 1800             # 30 min — weather changes slowly

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached singleton — import this everywhere instead of constructing Settings."""
    return Settings()
