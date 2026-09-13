"""Provider-agnostic LangChain chat-model factory.

The factory follows the same pattern as Super_RAGentic_20-08: provider selection
comes entirely from environment settings and imports happen only in the selected
branch. The returned model is passed directly to LangChain `create_agent()`.
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from agent_service.app.config import api_key_settings, llm_settings


DISABLED_PROVIDERS = {"", "none", "off", "disabled"}


def _api_key(value: str | None, provider: str) -> str:
    if value:
        return value
    raise ValueError(
        f"API key is required for LLM_PROVIDER={provider}. "
        "Set LLM_API_KEY or the provider-specific environment variable."
    )


def get_chat_model() -> BaseChatModel:
    """Create a LangChain model from env for OpenAI, Gemini, Claude, Groq or Bedrock."""
    provider = llm_settings.PROVIDER.lower()
    model = llm_settings.MODEL
    temperature = llm_settings.TEMPERATURE
    max_tokens = llm_settings.MAX_TOKENS

    if provider in {"gemini", "google"}:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=_api_key(
                llm_settings.API_KEY or api_key_settings.GEMINI_API_KEY, provider
            ),
            temperature=temperature,
            max_tokens=max_tokens,
        )

    if provider in {"openai", "oai", "openai-compatible", "openai_compatible"}:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            api_key=_api_key(
                llm_settings.API_KEY or api_key_settings.OPENAI_API_KEY, provider
            ),
            base_url=llm_settings.BASE_URL,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    if provider in {"anthropic", "claude"}:
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=model,
            api_key=_api_key(
                llm_settings.API_KEY or api_key_settings.ANTHROPIC_API_KEY, provider
            ),
            temperature=temperature,
            max_tokens=max_tokens,
        )

    if provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=model,
            api_key=_api_key(
                llm_settings.API_KEY or api_key_settings.GROQ_API_KEY, provider
            ),
            temperature=temperature,
            max_tokens=max_tokens,
        )

    if provider in {"bedrock", "aws", "aws-bedrock"}:
        from langchain_aws import ChatBedrockConverse

        return ChatBedrockConverse(
            model=model,
            region_name=api_key_settings.AWS_REGION,
            temperature=temperature,
            max_tokens=max_tokens,
            aws_access_key_id=api_key_settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=api_key_settings.AWS_SECRET_ACCESS_KEY,
            aws_session_token=api_key_settings.AWS_SESSION_TOKEN,
        )

    if provider in DISABLED_PROVIDERS:
        raise ValueError("LLM_PROVIDER is disabled; set it to a supported provider.")

    raise ValueError(
        f"Unsupported LLM_PROVIDER: {llm_settings.PROVIDER!r}. "
        "Use gemini | openai | openai-compatible | anthropic | groq | bedrock."
    )
