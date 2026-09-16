from pydantic_settings import BaseSettings, SettingsConfigDict

from .base import ENV_FILE


class LLMSettings(BaseSettings):
    PROVIDER: str = "groq"
    MODEL: str = "openai/gpt-oss-20b"
    API_KEY: str | None = None
    BASE_URL: str | None = None
    TEMPERATURE: float = 0.0
    MAX_TOKENS: int = 800

    model_config = SettingsConfigDict(
        env_prefix="LLM_", env_file=ENV_FILE, extra="ignore"
    )


class APIKeySettings(BaseSettings):
    """Provider-specific credentials, with LLM_API_KEY taking precedence."""

    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_SESSION_TOKEN: str | None = None
    AWS_REGION: str = "us-east-1"

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")
