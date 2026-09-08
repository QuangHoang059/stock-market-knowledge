"""LiteLLM factory — chuyển provider name thành ADK-compatible LiteLlm model.

Provider được chọn qua biến môi trường AGENT_ADK_PROVIDER hoặc qua tham số.
Mapping:
    claude   → anthropic/claude-sonnet-4-5
    gemini   → gemini/gemini-2.5-pro
    deepseek → deepseek/deepseek-chat
"""

from __future__ import annotations

from google.adk.models.lite_llm import LiteLlm

from .config import DEFAULT_PROVIDER, SUPPORTED_PROVIDERS

_PROVIDER_MAP: dict[str, str] = {
    "claude": "anthropic/claude-sonnet-4-5",
    "gemini": "gemini/gemini-2.5-pro",
    "deepseek": "deepseek/deepseek-chat",
}


def resolve_model_name(provider: str) -> str:
    if provider not in _PROVIDER_MAP:
        raise ValueError(
            f"Unknown provider '{provider}'. Supported: {SUPPORTED_PROVIDERS}"
        )
    return _PROVIDER_MAP[provider]


def get_llm(provider: str | None = None) -> LiteLlm:
    """Trả về LiteLlm instance cho ADK agent.

    Tham số:
        provider: tên ngắn ('claude' | 'gemini' | 'deepseek').
                  Mặc định từ AGENT_ADK_PROVIDER env hoặc DEFAULT_PROVIDER.
    """
    import os
    p = provider or os.environ.get("AGENT_ADK_PROVIDER") or DEFAULT_PROVIDER
    return LiteLlm(model=resolve_model_name(p))
