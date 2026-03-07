"""
config.py

Single source of truth for all configuration.

Reads from environment variables / .env file automatically via pydantic-settings.
Every agent module imports `settings` from here instead of calling load_dotenv()
directly.

Usage:
    from agent.config import settings
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # silently ignore unrecognised env vars
        case_sensitive=False,
    )

    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")

    # Change these two lines to switch providers/models globally
    anthropic_model: str = Field(
        default="claude-haiku-4-5-20251001",
        alias="ANTHROPIC_MODEL",
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        alias="OPENAI_MODEL",
    )

    # Which provider to use for each role
    analysis_provider: str = Field(default="anthropic", alias="ANALYSIS_PROVIDER")
    autonomous_provider: str = Field(default="anthropic", alias="AUTONOMOUS_PROVIDER")
    reflection_provider: str = Field(default="anthropic", alias="REFLECTION_PROVIDER")
    planner_provider: str = Field(default="openai", alias="PLANNER_PROVIDER")
    task_provider: str = Field(default="anthropic", alias="TASK_PROVIDER")

    #  LLM Behaviour
    llm_temperature: float = Field(default=0.0, alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=8192, alias="LLM_MAX_TOKENS")
    llm_max_retries: int = Field(default=3, alias="LLM_MAX_RETRIES")
    llm_timeout_seconds: int = Field(default=90, alias="LLM_TIMEOUT_SECONDS")

    #  Database
    db_path: Path = Field(
        default=Path(__file__).resolve().parent.parent / "db" / "database.db",
        alias="DB_PATH",
    )

    # Agent behaviour
    agent_max_steps: int = Field(default=10, alias="AGENT_MAX_STEPS")

    #  Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns a cached Settings singleton.
    Call get_settings.cache_clear() in tests to reload from a fresh .env.
    """
    return Settings()


# Module-level singleton — import this directly in agent modules
settings = get_settings()
