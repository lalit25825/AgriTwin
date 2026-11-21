from agritwin_ai.memory.conversation_memory import ConversationMemory
from agritwin_ai.memory.manager import MemoryManager
from agritwin_ai.runtime.session_manager import SessionManager


def test_new_session_clears_conversation_but_preserves_working_memory() -> None:
    conversation = ConversationMemory("system")
    manager = MemoryManager()
    manager.update_working({"crop": "onion"})
    manager.remember_fact("language", "Marathi")
    manager.remember_event("decision", {"decision": "HARVEST"})
    conversation.add_user("old request")

    SessionManager(conversation).start_new_session()

    assert conversation.get_messages() == [{"role": "system", "content": "system"}]
    assert manager.get_working()["crop"].value == "onion"
    assert manager.recall_fact("language").value == "Marathi"
    assert manager.get_last_event().data["decision"] == "HARVEST"


def test_conversation_storage_is_bounded() -> None:
    conversation = ConversationMemory("system")
    for index in range(30):
        conversation.add_user(str(index))
    messages = conversation.get_messages()
    assert len(messages) <= 16  # system prompt plus MAX_MEMORY entries
