"""Groq/OpenAI-compatible LLM gateway.

The SDK client is created lazily so importing AgriTwin (including its tests,
health endpoint and static UI) does not require provider credentials.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from agritwin_ai.config.settings import GROQ_API_KEY

MODEL_NAME = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")


@lru_cache(maxsize=1)
def _get_client():
    api_key = os.getenv("GROQ_API_KEY") or GROQ_API_KEY
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not configured. Copy .env.example to .env and "
            "add a valid Groq API key before sending an AI request."
        )

    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - depends on installation
        raise RuntimeError(
            "The OpenAI-compatible SDK is missing. Install project dependencies "
            "with: python -m pip install -r requirements.txt"
        ) from exc

    return OpenAI(
        api_key=api_key,
        base_url=BASE_URL,
        timeout=float(os.getenv("LLM_TIMEOUT_SECONDS", "60")),
        max_retries=int(os.getenv("LLM_MAX_RETRIES", "2")),
    )


def ask_llm(messages: list[dict[str, Any]], tools: dict[str, Any] | None = None):
    """Call the configured Groq model using the OpenAI chat-completions API."""
    kwargs: dict[str, Any] = {
        "model": MODEL_NAME,
        "messages": messages,
    }

    if tools:
        openai_tools = []
        for tool_name, tool_info in tools.items():
            properties: dict[str, Any] = {}
            for prop_name, prop_type in tool_info.get("arguments", {}).items():
                type_mapping = {
                    str: "string",
                    int: "integer",
                    float: "number",
                    bool: "boolean",
                    list: "array",
                    dict: "object",
                }
                json_type = type_mapping.get(prop_type, "string")
                properties[prop_name] = {"type": json_type}

            required = tool_info.get("required")
            if required is None:
                required = list(tool_info.get("arguments", {}).keys())

            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_info.get("description", tool_name),
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": list(required),
                        "additionalProperties": False,
                    },
                },
            })

        kwargs["tools"] = openai_tools
        kwargs["tool_choice"] = "auto"

    try:
        return _get_client().chat.completions.create(**kwargs)
    except Exception as exc:
        # Keep transport/provider detail in logs, but expose a useful message
        # from the API layer rather than returning an empty agent response.
        raise RuntimeError(f"LLM request failed: {exc}") from exc
