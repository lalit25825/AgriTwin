from agritwin_ai.understanding.interpreter import understand
from agritwin_ai.runtime.conversation_resolver import ConversationResolver

class ConversationPipeline:
    """Prepare a user request for the agent runtime."""

    def __init__(
        self,
        conversation_memory,
        memory_manager,
        context_builder,
        tools=None,
    ):
        self.conversation = conversation_memory
        self.memory = memory_manager
        self.context_builder = context_builder
        self.tools = tools or {}
        self.resolver = ConversationResolver()

    def prepare(
        self,
        user_message,
        decision=None,
    ):

        # Capture previous conversation BEFORE adding the current message.
        conversation_history = self.conversation.get_messages()

        resolved_request = self.resolver.resolve(
            conversation_history=conversation_history,
            working_memory=self.memory.get_working(),
            latest_user_message=user_message,
        )

        print()
        print("=" * 50)
        print("RESOLVED REQUEST")
        print("=" * 50)
        print(resolved_request)
        print("=" * 50)

        # Store the original user message in conversation memory.
        self.conversation.add_user(user_message)

        understanding = understand(
            resolved_request,
            self.tools,
        )

        # Merge extracted entities and updates into working memory.
        memory_updates = {}
        if understanding.entities:
            for key, value in understanding.entities.items():
                if value is not None:
                    memory_updates[key] = value
        if understanding.updates:
            memory_updates.update(understanding.updates)

        self.memory.update_working(memory_updates)

        messages = self.context_builder.build(
            conversation=self.conversation.get_messages(),
            working_memory=self.memory.get_working(),
            semantic_memory=self.memory.semantic.get_all(),
            episodic_memory=self.memory.episodic.get_all(),
            decision=decision,
        )

        return understanding, messages