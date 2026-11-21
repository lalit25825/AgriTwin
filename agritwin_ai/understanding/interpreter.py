from agritwin_ai.runtime.llm import ask_llm

from agritwin_ai.understanding.prompts import build_understanding_prompt

from agritwin_ai.understanding.parser import (
    parse_understanding_response
)


def understand(user_message, tools):
    """
    Understanding Layer

    Input:
        Human language

    Output:
        UnderstandingResult
    """

    messages = [

        {
            "role": "system",
            "content": build_understanding_prompt(tools)
        },

        {
            "role": "user",
            "content": user_message
        }

    ]

    response = ask_llm(
        messages=messages
    )

    assistant_text = (
        response
        .choices[0]
        .message
        .content
    )

    print()

    print("=" * 50)
    print("UNDERSTANDING RESPONSE")
    print("=" * 50)

    print(assistant_text)

    print("=" * 50)

    return parse_understanding_response(
        assistant_text
    )
