"""
llm_provider.py
---------------
Single factory for all LLM instances used across Helix.

Design decisions:
- Each role (analysis, autonomous, reflection, planner, task) gets its own
  LLM instance, but all configuration comes from settings — no hardcoding.
  every caller gets it automatically without any extra code.
- The module caches instances so we don't reconstruct the client on every call.
- Switching provider for a role = change one env var (e.g. ANALYSIS_PROVIDER=openai)

Usage:
    from agent.llm_provider import get_llm

    llm = get_llm("analysis")
    response = llm.invoke("your prompt")
"""

import logging
from functools import lru_cache
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from agent.config import settings

logger = logging.getLogger(__name__)

# Roles Helix uses internally
LLM_ROLES = ("analysis", "autonomous", "reflection", "planner", "task")


def _build_anthropic(temperature: float) -> BaseChatModel:
    from langchain_anthropic import ChatAnthropic  # type: ignore[import]

    return ChatAnthropic(  # type: ignore[call-arg]
        model_name=settings.anthropic_model,
        temperature=temperature,
        max_tokens=settings.llm_max_tokens,
        timeout=settings.llm_timeout_seconds,
        api_key=settings.anthropic_api_key or None,  # None = read from env
    )


def _build_openai(temperature: float) -> BaseChatModel:
    from langchain_openai import ChatOpenAI  # type: ignore[import]

    return ChatOpenAI(
        model=settings.openai_model,
        temperature=temperature,
        max_completion_tokens=settings.llm_max_tokens,
        timeout=settings.llm_timeout_seconds,
        api_key=settings.openai_api_key or None,
    )


def _provider_for_role(role: str) -> str:
    mapping = {
        "analysis": settings.analysis_provider,
        "autonomous": settings.autonomous_provider,
        "reflection": settings.reflection_provider,
        "planner": settings.planner_provider,
        "task": settings.task_provider,
    }
    return mapping.get(role, "anthropic")


def _temperature_for_role(role: str) -> float:
    # Slight variance for roles that benefit from a bit more creativity
    overrides = {
        "reflection": 0.1,
        "planner": 0.2,
        "task": 0.1,
    }
    return overrides.get(role, settings.llm_temperature)


@lru_cache(maxsize=len(LLM_ROLES))
def _cached_llm(role: str) -> BaseChatModel:
    """Build and cache one LLM instance per role."""
    provider = _provider_for_role(role)
    temperature = _temperature_for_role(role)

    logger.info("Building LLM for role='%s' provider='%s'", role, provider)

    if provider == "anthropic":
        return _build_anthropic(temperature)
    elif provider == "openai":
        return _build_openai(temperature)
    else:
        raise ValueError(
            f"Unknown provider '{provider}' for role '{role}'. "
            "Valid options: 'anthropic', 'openai'"
        )


def get_llm(role: str) -> BaseChatModel:
    """
    Public entry point. Returns a cached LLM for the given role.

    Args:
        role: one of "analysis" | "autonomous" | "reflection" | "planner" | "task"
    """
    if role not in LLM_ROLES:
        raise ValueError(f"Unknown role '{role}'. Valid roles: {LLM_ROLES}")
    return _cached_llm(role)


# Retry decorator — apply this to any function that calls .invoke()


def with_retry(func: Any) -> Any:
    """
    Decorator that retries an LLM call with exponential backoff.

    Retries up to settings.llm_max_retries times on any Exception,
    waiting 2^attempt seconds between tries (capped at 30s).

    Usage:
        @with_retry
        def call_llm(...):
            return llm.invoke(prompt)
    """
    return retry(
        stop=stop_after_attempt(settings.llm_max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(Exception),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )(func)


def invoke_with_retry(llm: BaseChatModel, prompt: str) -> str:
    """
    Convenience wrapper: invoke an LLM with automatic retry + response
    normalisation (always returns a plain string).

    Args:
        llm:    any LangChain chat model
        prompt: the full prompt string

    Returns:
        str response content
    """

    @retry(
        stop=stop_after_attempt(settings.llm_max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(Exception),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _invoke() -> str:
        response = llm.invoke(prompt)
        content = response.content
        if isinstance(content, list):
            content = "".join(str(x) for x in content)
        return str(content)

    return _invoke()
