
"""LLM reasoning loop with validated tool-call parsing."""

from __future__ import annotations

import json
import re
from typing import Any

from agritwin_ai.runtime.llm import ask_llm


class ReasoningLoop:
    """Ask the LLM to use tools or produce a final answer."""

    def __init__(
        self,
        tools: dict[str, Any] | None = None,
    ) -> None:
        self.tools = tools or {}

    def think(
        self,
        messages: list[dict[str, str]],
        tools: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Return either a tool action or a final natural-language answer.

        Passing an empty tools dictionary disables tool calling for this
        turn. Passing None uses the complete registered tool collection.
        """

        available_tools = self.tools if tools is None else tools

        response = ask_llm(
            messages=messages,
            tools=available_tools or None,
        )

        message = response.choices[0].message

        # Prefer native function calls when the provider returns them.
        if message.tool_calls:
            tool_call = message.tool_calls[0]

            if tool_call.type == "function":
                try:
                    arguments = json.loads(
                        tool_call.function.arguments
                    )

                    if not isinstance(arguments, dict):
                        raise ValueError(
                            "Tool arguments must be a JSON object."
                        )

                    action_data = {
                        "action": tool_call.function.name,
                        "arguments": arguments,
                    }

                    assistant_text = json.dumps(action_data)

                    return assistant_text, {
                        "type": "tool",
                        "data": action_data,
                    }

                except (json.JSONDecodeError, ValueError, TypeError):
                    return message.content or "", {
                        "type": "invalid",
                        "data": message.content or "",
                    }

        assistant_text = (message.content or "").strip()

        if not assistant_text:
            return "", {
                "type": "invalid",
                "data": "The model returned an empty response.",
            }

        # Some models return structured JSON in their message content
        # instead of using native function calling.
        cleaned = re.sub(
            r"```(?:json)?|```",
            "",
            assistant_text,
            flags=re.IGNORECASE,
        ).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            data = None

        if isinstance(data, dict):
            if (
                isinstance(data.get("action"), str)
                and isinstance(data.get("arguments"), dict)
            ):
                return assistant_text, {
                    "type": "tool",
                    "data": data,
                }

            if "final_answer" in data:
                final_answer = data["final_answer"]

                if isinstance(final_answer, str) and final_answer.strip():
                    return assistant_text, {
                        "type": "final",
                        "data": final_answer.strip(),
                    }

        # Natural-language final answers are valid. The LLM should not
        # need to wrap every ordinary response in JSON.
        return assistant_text, {
            "type": "final",
            "data": assistant_text,
        }
