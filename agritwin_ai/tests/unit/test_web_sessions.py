from agritwin_ai.web.session_manager import SessionManager


def test_web_sessions_receive_independent_agent_engines():
    manager = SessionManager(max_sessions=4)
    first = manager.get("farmer-session-0001")
    second = manager.get("farmer-session-0002")

    assert first is not second
    assert first.coordinator is not second.coordinator
    assert first.harvest is not second.harvest
    assert first.climate is not second.climate
    assert first.market is not second.market
    assert first.logistics is not second.logistics


def test_session_manager_evicts_oldest_session_at_capacity():
    manager = SessionManager(max_sessions=2)
    manager.get("farmer-session-0001")
    manager.get("farmer-session-0002")
    manager.get("farmer-session-0001")  # Make session 2 the least recently used.
    manager.get("farmer-session-0003")
    assert len(manager._sessions) == 2
    assert "farmer-session-0001" in manager._sessions
    assert "farmer-session-0003" in manager._sessions
    assert "farmer-session-0002" not in manager._sessions
