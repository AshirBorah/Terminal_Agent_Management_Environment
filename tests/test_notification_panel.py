"""Tests for the notification history panel and filter methods."""

from __future__ import annotations

from datetime import datetime

from tame.notifications.history import NotificationHistory
from tame.notifications.models import EventType, NotificationEvent, Priority


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(
    event_type: EventType = EventType.ERROR,
    session_id: str = "s1",
    session_name: str = "session-1",
    message: str = "test",
    priority: Priority = Priority.CRITICAL,
) -> NotificationEvent:
    return NotificationEvent(
        event_type=event_type,
        session_id=session_id,
        session_name=session_name,
        message=message,
        priority=priority,
        timestamp=datetime.now(),
    )


# ---------------------------------------------------------------------------
# Tests: NotificationHistory filters
# ---------------------------------------------------------------------------


class TestNotificationHistoryFilters:
    def test_get_by_session(self):
        history = NotificationHistory()
        history.add(_make_event(session_id="s1"))
        history.add(_make_event(session_id="s2"))
        history.add(_make_event(session_id="s1"))
        assert len(history.get_by_session("s1")) == 2
        assert len(history.get_by_session("s2")) == 1
        assert len(history.get_by_session("s3")) == 0

    def test_get_by_type(self):
        history = NotificationHistory()
        history.add(_make_event(event_type=EventType.ERROR))
        history.add(_make_event(event_type=EventType.COMPLETED))
        history.add(_make_event(event_type=EventType.ERROR))
        assert len(history.get_by_type(EventType.ERROR)) == 2
        assert len(history.get_by_type(EventType.COMPLETED)) == 1
        assert len(history.get_by_type(EventType.INPUT_NEEDED)) == 0


# ---------------------------------------------------------------------------
# Tests: NotificationHistory basics
# ---------------------------------------------------------------------------


class TestNotificationHistory:
    def test_correct_event_count(self):
        history = NotificationHistory()
        for i in range(5):
            history.add(_make_event(message=f"msg-{i}"))
        assert len(history) == 5
        assert len(history.get_all()) == 5

    def test_clear_empties_history(self):
        history = NotificationHistory()
        for i in range(3):
            history.add(_make_event())
        assert len(history) == 3
        history.clear()
        assert len(history) == 0
        assert history.get_all() == []

    def test_empty_state(self):
        history = NotificationHistory()
        assert len(history) == 0
        assert history.get_all() == []
        assert history.get_recent() == []

    def test_ring_buffer_eviction(self):
        history = NotificationHistory(max_size=3)
        for i in range(5):
            history.add(_make_event(message=f"msg-{i}"))
        assert len(history) == 3
        messages = [e.message for e in history.get_all()]
        assert messages == ["msg-2", "msg-3", "msg-4"]


# ---------------------------------------------------------------------------
# Tests: Priority mapping
# ---------------------------------------------------------------------------


class TestPriorityMapping:
    def test_critical_events(self):
        ev = _make_event(event_type=EventType.ERROR, priority=Priority.CRITICAL)
        assert ev.priority == Priority.CRITICAL

    def test_high_events(self):
        ev = _make_event(event_type=EventType.INPUT_NEEDED, priority=Priority.HIGH)
        assert ev.priority == Priority.HIGH

    def test_medium_events(self):
        ev = _make_event(event_type=EventType.COMPLETED, priority=Priority.MEDIUM)
        assert ev.priority == Priority.MEDIUM

    def test_low_events(self):
        ev = _make_event(event_type=EventType.SESSION_IDLE, priority=Priority.LOW)
        assert ev.priority == Priority.LOW
