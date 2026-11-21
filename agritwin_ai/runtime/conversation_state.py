class ConversationState:
    """Agent-neutral container for transient request context."""

    def __init__(self):

        self.entities = {}
        self.observations = {}
        self.decision = None
