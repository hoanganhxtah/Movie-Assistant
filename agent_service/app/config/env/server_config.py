from pydantic_settings import BaseSettings, SettingsConfigDict

from .base import ENV_FILE


class ServerSettings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    RELOAD: bool = False
    CONTEXT_PATH: str = "/api/v1"

    model_config = SettingsConfigDict(
        env_prefix="SERVER_", env_file=ENV_FILE, extra="ignore"
    )
