from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .base import ENV_FILE, PROJECT_ROOT


class DataSettings(BaseSettings):
    DIR: Path = PROJECT_ROOT / "data" / "ml-latest-small-filtered"

    @field_validator("DIR", mode="after")
    @classmethod
    def resolve_dir(cls, v: Path) -> Path:
        if not v.is_absolute():
            return PROJECT_ROOT / v
        return v

    model_config = SettingsConfigDict(
        env_prefix="DATA_", env_file=ENV_FILE, extra="ignore"
    )

