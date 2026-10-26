"""Application settings loaded from environment variables / `.env`."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration. Every field can be overridden with an env var of the same name."""

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "procurement"
    mongo_collection: str = "purchases"

    llm_provider: str = "groq"
    llm_model: str = "openai/gpt-oss-120b"
    # Optional cheaper/faster model for the light nodes (understand, answer). Empty = use llm_model.
    llm_fast_model: str = ""
    llm_temperature: float = 0.0
    llm_max_retries: int = 4  # retries on HTTP 429 / transient errors (exponential backoff)
    llm_backoff_base_s: float = 2.0
    llm_reasoning_effort: str = "low"  # only sent to reasoning models (gpt-oss); keeps token usage low
    groq_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    query_max_time_ms: int = 15000
    query_row_limit: int = 200
    agent_max_retries: int = 2  # self-correction attempts per sub-query
    api_result_rows: int = 50  # rows returned to the UI per pipeline
    cors_origins: str = "*"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings singleton."""
    return Settings()
