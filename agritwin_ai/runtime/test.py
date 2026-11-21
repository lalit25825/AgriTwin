from agritwin_ai.runtime.context_builder import ContextBuilder
from agritwin_ai.memory.manager import MemoryManager


memory = MemoryManager()

memory.update_working(
    {
        "crop": "onion",
        "city": "Nashik"
    }
)

memory.remember_fact(
    "preferred_language",
    "Marathi"
)

conversation = [

    {
        "role": "system",
        "content": "Harvest Agent"
    },

    {
        "role": "user",
        "content": "Should I harvest tomorrow?"
    }

]

builder = ContextBuilder()

messages = builder.build(

    conversation,

    memory.get_working(),

    memory.semantic.get_all(),

    memory.episodic.get_all()

)

for message in messages:

    print("=" * 40)

    print(message["role"])

    print(message["content"])