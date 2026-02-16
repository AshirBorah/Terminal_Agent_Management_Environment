from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EventType(Enum):
    INPUT_NEEDED = "input_needed"
    ERROR = "error"
    COMPLETED = "completed"
    SESSION_IDLE = "session_idle"


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


EVENT_PRIORITY: dict[EventType, Priority] = {
    EventType.INPUT_NEEDED: Priority.HIGH,
    EventType.ERROR: Priority.CRITICAL,
    EventType.COMPLETED: Priority.MEDIUM,
    EventType.SESSION_IDLE: Priority.LOW,
}

# Numeric verbosity thresholds for Slack filtering.
# A SlackNotifier with verbosity=V forwards events whose level <= V.
EVENT_VERBOSITY: dict[EventType, int] = {
    EventType.ERROR: 10,
    EventType.INPUT_NEEDED: 10,
    EventType.COMPLETED: 50,
    EventType.SESSION_IDLE: 100,
}


@dataclass
class NotificationEvent:
    event_type: EventType
    session_id: str
    session_name: str
    message: str
    priority: Priority
    timestamp: datetime = field(default_factory=datetime.now)
    matched_text: str = ""
