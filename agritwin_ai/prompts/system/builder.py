from agritwin_ai.prompts.system.identity import IDENTITY
from agritwin_ai.prompts.system.memory_rules import MEMORY_RULES
from agritwin_ai.prompts.system.reasoning_rules import REASONING_RULES
from agritwin_ai.prompts.system.tool_rules import TOOL_RULES
from agritwin_ai.prompts.system.response_rules import RESPONSE_RULES


def build_system_prompt(tool_prompt: str):

    return "\n\n".join(
        [
            IDENTITY,
            MEMORY_RULES,
            REASONING_RULES,
            TOOL_RULES,
            tool_prompt,
            RESPONSE_RULES,
        ]
    )