"""Environment-backed settings for the standalone Streamlit UI."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class UISettings(BaseSettings):
    """Backend URL and request timeout used by the UI client."""
    API_BASE_URL: str = "http://localhost:8001"
    API_TIMEOUT_SECONDS: float = 120.0

    model_config = SettingsConfigDict(
        env_prefix="UI_",
        env_file=(
            PROJECT_ROOT / ".env",
            PROJECT_ROOT / "ui" / ".env",
            Path(".env"),
        ),
        extra="ignore",
    )

    @property
    def api_base_url(self) -> str:
        return self.API_BASE_URL.rstrip("/")


ui_settings = UISettings()
