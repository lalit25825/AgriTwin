from typing import Any, List, Mapping, Optional


class ContextBuilder:

    def build(
        self,
        conversation: list[dict[str, str]],
        working_memory: Mapping[str, Any],
        semantic_memory: Mapping[str, Any],
        episodic_memory: list[Any],
        decision: Optional[dict[str, str]] = None,
    ) -> List[dict[str, str]]:
        """Build LLM messages, putting deterministic decision context before dialogue."""
        messages = []

        # -------------------------
        # System Prompt
        # -------------------------

        messages.append(
            conversation[0]
        )

        # -------------------------
        # Working Memory
        # -------------------------

        if working_memory:

            memory_text = "Current Working Memory:\n"

            for key, item in working_memory.items():

                memory_text += f"- {key}: {item.value}\n"

            messages.append(
                {
                    "role": "system",
                    "content": memory_text
                }
            )

        # -------------------------
        # Semantic Memory
        # -------------------------

        if semantic_memory:

            semantic_text = "Known User Facts:\n"

            for key, item in semantic_memory.items():

                semantic_text += f"- {key}: {item.value}\n"

            messages.append(
                {
                    "role": "system",
                    "content": semantic_text
                }
            )

        # Decision context must be visible before any final LLM explanation.
        if decision:
            messages.append(decision)

        messages.extend(
            conversation[1:]
        )

        return messages
