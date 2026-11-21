from agritwin_ai.memory.manager import MemoryManager
from agritwin_ai.runtime.conversation_resolver import ConversationResolver


def _memory(**updates):
    manager = MemoryManager()
    manager.update_working(updates)
    return manager.get_working()


def test_resolves_city_answer_to_prior_rain_request() -> None:
    history = [
        {"role": "user", "content": "Will it rain tomorrow?"},
        {"role": "assistant", "content": "Which city?"},
    ]

    resolved = ConversationResolver().resolve(history, {}, "Nashik")

    assert resolved == "Will it rain tomorrow in Nashik?"


def test_resolves_crop_answer_to_prior_harvest_request() -> None:
    history = [
        {"role": "user", "content": "Should I harvest tomorrow?"},
        {"role": "assistant", "content": "Which crop?"},
    ]

    resolved = ConversationResolver().resolve(history, {}, "Onion")

    assert resolved == "Should I harvest onions tomorrow?"


def test_resolves_weather_request_from_working_city() -> None:
    resolved = ConversationResolver().resolve(
        [{"role": "user", "content": "My city is Nashik."}],
        _memory(city="Nashik"),
        "Will it rain tomorrow?",
    )

    assert resolved == "Will it rain tomorrow in Nashik?"


def test_resolves_harvest_request_from_working_crop() -> None:
    resolved = ConversationResolver().resolve(
        [{"role": "user", "content": "My crop is onion."}],
        _memory(crop="onion"),
        "Should I harvest next week?",
    )

    assert resolved == "Should I harvest onions next week?"
