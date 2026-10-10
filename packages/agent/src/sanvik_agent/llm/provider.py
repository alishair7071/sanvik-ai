"""Choose one LangChain chat model. API keys stay in Python."""

import os
from pathlib import Path

from dotenv import dotenv_values
from langchain_core.language_models.chat_models import BaseChatModel

# Change this one value to "groq", "openai", or "anthropic", then restart Sanvik.
ACTIVE_PROVIDER = "groq"
LOCAL_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"
PROVIDERS = {
    "groq": ("GROQ_API_KEY", "openai/gpt-oss-20b"),
    "openai": ("OPENAI_API_KEY", "gpt-4o-mini"),
    "anthropic": ("ANTHROPIC_API_KEY", "claude-sonnet-4-6"),
}


class PlanningError(Exception):
    code = "planning_failed"
    public_message = "Planning failed"


class UnsupportedProvider(PlanningError):
    code = "unsupported_provider"
    public_message = "ACTIVE_PROVIDER must be groq, openai, or anthropic"


class MissingApiKey(PlanningError):
    code = "missing_api_key"

    def __init__(self, key_name: str) -> None:
        self.public_message = f"{key_name} is not set in the Python environment or packages/agent/.env"
        super().__init__(self.public_message)


class ProviderTimeout(PlanningError):
    code = "provider_timeout"
    public_message = "The selected model did not respond before the timeout"


class ProviderFailure(PlanningError):
    code = "provider_failure"
    public_message = "The selected model request failed"


class InvalidModelResponse(PlanningError):
    code = "invalid_model_response"
    public_message = "The selected model returned an invalid plan"


def get_chat_model() -> BaseChatModel:
    """Create the selected model without making an API call."""
    if ACTIVE_PROVIDER not in PROVIDERS:
        raise UnsupportedProvider()
    key_name, model_name = PROVIDERS[ACTIVE_PROVIDER]

    # Read only the selected provider's key. An environment value overrides .env.
    api_key = os.environ.get(key_name)
    if api_key is None:
        api_key = dotenv_values(LOCAL_ENV_FILE).get(key_name)
    if not api_key or not api_key.strip():
        raise MissingApiKey(key_name)

    # Import only the chosen LangChain integration.
    try:
        if ACTIVE_PROVIDER == "groq":
            from langchain_groq import ChatGroq

            return ChatGroq(model=model_name, api_key=api_key, timeout=50, max_retries=0)
        if ACTIVE_PROVIDER == "openai":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(model=model_name, api_key=api_key, timeout=50, max_retries=0)

        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model_name, api_key=api_key, timeout=50, max_retries=0)
    except Exception as exc:
        raise ProviderFailure() from exc