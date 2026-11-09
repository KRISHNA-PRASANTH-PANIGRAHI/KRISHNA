"""Validated environment configuration. No credentials or bypasses are bundled."""

from functools import lru_cache
import re
from urllib.parse import urlsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./classguard.db"
    database_schema: str = ""
    cors_origins: list[str] = ["http://localhost:3000"]
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_jwt_audience: str = "authenticated"

    @field_validator("database_schema")
    @classmethod
    def validate_database_schema(cls, value: str) -> str:
        value = value.strip()
        if value and re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", value) is None:
            raise ValueError("DATABASE_SCHEMA must be a lowercase SQL identifier of at most 63 characters")
        return value

    @field_validator("supabase_url")
    @classmethod
    def validate_supabase_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        if value:
            parsed = urlsplit(value)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
                raise ValueError("SUPABASE_URL must be an HTTPS origin without credentials, path, query or fragment")
        return value

    @field_validator("supabase_publishable_key")
    @classmethod
    def validate_publishable_key(cls, value: str) -> str:
        value = value.strip()
        if value and (not value.startswith("sb_publishable_") or any(character.isspace() for character in value)):
            raise ValueError("Use a Supabase sb_publishable_ key, never a secret or service-role key")
        return value

    @property
    def authentication_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_publishable_key)

    @property
    def jwt_issuer(self) -> str:
        return f"{self.supabase_url}/auth/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
