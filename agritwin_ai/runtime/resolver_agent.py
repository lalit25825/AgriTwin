import json

from agritwin_ai.runtime.llm import ask_llm
from agritwin_ai.runtime.resolver_prompt import RESOLVER_PROMPT


class ResolverAgent:

    def resolve(

        self,

        conversation,

        working_memory,

        latest_message

    ):

        messages = [

            {

                "role": "system",

                "content": RESOLVER_PROMPT

            }

        ]

        history = ""

        for message in conversation:

            # Skip system prompts
            if message["role"] == "system":
                continue

            history += (
                f"{message['role']}:\n"
                f"{message['content']}\n\n"
            )

        memory = ""

        for key, value in working_memory.items():

            memory += f"{key}: {value.value}\n"

        prompt = f"""

Conversation

{history}

Working Memory

{memory}

Latest User Message

{latest_message}

Return JSON only.

"""

        messages.append(

            {

                "role": "user",

                "content": prompt

            }

        )

        print("\n===== RESOLVER MESSAGES =====")

        for m in messages:

            print(m["role"])

        print("=============================\n")

        response = ask_llm(
            messages=messages
        )

        text = response.choices[0].message.content

        print("\n========== RESOLVER RAW ==========")
        print(text)
        print("==================================\n")

        data = json.loads(text)

        print(data)

        return data["resolved_request"]