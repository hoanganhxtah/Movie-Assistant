from pydantic_settings import BaseSettings, SettingsConfigDict

from .env.base import ENV_FILE
from .env.data_config import DataSettings
from .env.llm_config import APIKeySettings, LLMSettings
from .env.recommendation_config import RecommendationSettings
from .env.search_config import SearchSettings
from .env.server_config import ServerSettings


class ApplicationSettings(BaseSettings):
    NAME: str = "Movie Discovery Agent API"
    VERSION: str = "1.0.0"

    model_config = SettingsConfigDict(
        env_prefix="APP_", env_file=ENV_FILE, extra="ignore"
    )


app_settings = ApplicationSettings()
server_settings = ServerSettings()
data_settings = DataSettings()
search_settings = SearchSettings()
recommendation_settings = RecommendationSettings()
llm_settings = LLMSettings()
api_key_settings = APIKeySettings()
