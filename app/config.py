"""Typed application settings.

Only settings required by the current implementation phase are declared
here. As later phases (detection, ML, IPS) are implemented, their
thresholds and toggles will be added to this model rather than being
read from ``os.environ`` ad hoc elsewhere (see ARCHITECTURE.md, Section 3).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- API ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_token: str = ""  # empty = open (local demo only), per ARCHITECTURE.md 1.7
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:8000"

    # --- MongoDB ---
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "cloud_ids"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Cached (rather than a module-level singleton) so tests can override
    environment variables and call ``get_settings.cache_clear()`` between
    cases if needed.
    """
    return Settings()
