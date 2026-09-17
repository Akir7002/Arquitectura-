"""
Capa de configuración (Core).

Sigue la recomendación oficial de FastAPI para el manejo de configuración:
https://fastapi.tiangolo.com/advanced/settings/

- Usa `pydantic-settings` para tipar y validar la configuración.
- Lee variables de entorno y, opcionalmente, un archivo `.env`.
- Se expone una única instancia cacheada con `lru_cache` para no releer
  el `.env` en cada request (patrón "Settings and Environment Variables"
  documentado por FastAPI).
- Aplica el principio de "Config" de la metodología 12-Factor App
  (https://12factor.net/config): la configuración vive en el entorno,
  nunca hardcodeada en el código fuente.
"""

from functools import lru_cache
from typing import List

from pydantic import AnyUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Metadatos de la aplicación ---
    APP_NAME: str = "Users API"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # --- Base de datos ---
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"

    # --- Seguridad / JWT ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # --- CORS ---
    BACKEND_CORS_ORIGINS: List[str] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def split_cors_origins(cls, value):
        """Permite declarar los orígenes CORS como CSV en el .env."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Devuelve una instancia única (singleton) de Settings.

    `lru_cache` evita reconstruir/releer la configuración en cada
    inyección de dependencia y facilita sobreescribirla en los tests
    mediante `app.dependency_overrides`.
    """
    return Settings()
