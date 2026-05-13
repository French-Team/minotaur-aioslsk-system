from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration de l'application."""

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # Soulseek credentials par défaut (surchargeables via .env ou variables d'env)
    soulseek_username: str = ""
    soulseek_password: str = ""

    model_config = {"env_prefix": "AISLSK_", "env_file": ".env"}


settings = Settings()
