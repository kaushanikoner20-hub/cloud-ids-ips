"""
Application configuration and environment variable management.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # API Configuration
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)
    APP_TITLE: str = Field(default="Cloud IDS/IPS API")
    APP_VERSION: str = Field(default="0.1.0")
    LOG_LEVEL: str = Field(default="INFO")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
