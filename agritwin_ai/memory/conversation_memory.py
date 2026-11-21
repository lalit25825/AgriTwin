from typing import Any

from agritwin_ai.config.settings import MAX_MEMORY


class ConversationMemory:

    def __init__(self, system_prompt: str) -> None:
        self._system_message = {
            "role": "system",
            "content": system_prompt,
        }
        self.messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": system_prompt,
            }
        ]

    def start_new_session(self) -> None:
        """Discard transient dialogue while preserving the system prompt."""
        self.messages = [self._system_message.copy()]

    def add_user(self, message: str) -> None:

        self.messages.append(
            {
                "role": "user",
                "content": message
            }
        )

    def add_assistant(self, message: str) -> None:

        self.messages.append(
            {
                "role": "assistant",
                "content": message
            }
        )

    def add_tool(self, message: str) -> None:

        # We are NOT using OpenAI native tool calling.
        # Store observations as assistant messages.

        self.messages.append(
            {
                "role": "assistant",
                "content": f"Observation:\n{message}"
            }
        )

    def get_messages(self) -> list[dict[str, str]]:

        system = self.messages[:1]

        history = [

            msg

            for msg in self.messages[1:]

        ][-MAX_MEMORY:]

        # Bound storage as well as output, preventing unbounded growth within a request.
        self.messages = system + history
        return list(self.messages)
