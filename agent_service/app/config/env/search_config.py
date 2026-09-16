from pydantic_settings import BaseSettings, SettingsConfigDict

from .base import ENV_FILE


class SearchSettings(BaseSettings):
    MAX_FEATURES: int = 30_000
    CANDIDATE_POOL: int = 100

    model_config = SettingsConfigDict(
        env_prefix="SEARCH_", env_file=ENV_FILE, extra="ignore"
    )

