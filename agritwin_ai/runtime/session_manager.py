"""Conversation-session lifecycle management."""


class SessionManager:
    """Manage conversation lifecycle without destroying persistent context."""

    def __init__(self, memory) -> None:
        self.memory = memory

    def start_new_session(self) -> None:
        """
        Start a new conversation session by clearing the conversation history
        while preserving the system prompt and working memory.
        """
        self.memory.start_new_session()

    def clear_conversation(self) -> None:
        """Explicitly clear the conversation when a true new session is required."""
        self.memory.start_new_session()