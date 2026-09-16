from pydantic_settings import BaseSettings, SettingsConfigDict

from .base import ENV_FILE


class RecommendationSettings(BaseSettings):
    NEIGHBOR_COUNT: int = 30
    MINIMUM_OVERLAP: int = 3
    OVERLAP_SHRINKAGE: float = 10.0
    PREDICTION_SHRINKAGE: float = 5.0
    DEFAULT_TOP_K: int = 5
    QUERY_WEIGHT: float = 0.45
    PROFILE_WEIGHT: float = 0.20
    COLLABORATIVE_WEIGHT: float = 0.20
    QUALITY_WEIGHT: float = 0.15
    GENERAL_PROFILE_WEIGHT: float = 0.20
    GENERAL_COLLABORATIVE_WEIGHT: float = 0.50
    GENERAL_QUALITY_WEIGHT: float = 0.30

    model_config = SettingsConfigDict(
        env_prefix="RECOMMENDATION_", env_file=ENV_FILE, extra="ignore"
    )
