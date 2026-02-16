from __future__ import annotations

import json
import logging
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from .models import EVENT_VERBOSITY, EventType, NotificationEvent

log = logging.getLogger(__name__)

# Color bar per event type (Slack attachment sidebar).
_COLORS: dict[EventType, str] = {
    EventType.INPUT_NEEDED: "#f5a623",  # orange
    EventType.ERROR: "#e74c3c",  # red
    EventType.COMPLETED: "#2ecc71",  # green
    EventType.SESSION_IDLE: "#95a5a6",  # grey
}

_EMOJI: dict[EventType, str] = {
    EventType.INPUT_NEEDED: ":warning:",
    EventType.ERROR: ":rotating_light:",
    EventType.COMPLETED: ":white_check_mark:",
    EventType.SESSION_IDLE: ":zzz:",
}


class SlackNotifier:
    """Send notifications to Slack via Incoming Webhook.

    Config (in ``notifications.slack``):
        enabled: bool (default False)
        webhook_url: str — Slack Incoming Webhook URL
        verbosity: int — numeric level (0=off, 10=errors/input, 50=+completed, 100=all)
        sessions: list[str] — session name patterns to forward
            (empty = all sessions, glob-like matching)
    """

    def __init__(
        self,
        enabled: bool = False,
        webhook_url: str = "",
        verbosity: int = 10,
        sessions: list[str] | None = None,
    ) -> None:
        self._enabled = enabled and bool(webhook_url)
        self._webhook_url = webhook_url
        self._verbosity = verbosity
        # Which session names to send for (empty = all)
        self._allowed_sessions: set[str] = set(sessions) if sessions else set()
        self._pool = ThreadPoolExecutor(max_workers=2)

    def notify(self, event: NotificationEvent) -> None:
        if not self._enabled:
            return
        # Verbosity filter
        event_level = EVENT_VERBOSITY.get(event.event_type, 100)
        if event_level > self._verbosity:
            return
        # Session name filter
        if self._allowed_sessions and event.session_name not in self._allowed_sessions:
            return

        payload = self._build_payload(event)
        self._pool.submit(self._post, payload)

    def _build_payload(self, event: NotificationEvent) -> dict[str, Any]:
        emoji = _EMOJI.get(event.event_type, ":bell:")
        color = _COLORS.get(event.event_type, "#439FE0")
        title = f"{emoji} TAME [{event.event_type.value}]"
        fields = [
            {"title": "Session", "value": event.session_name, "short": True},
            {"title": "Priority", "value": event.priority.value, "short": True},
        ]
        if event.matched_text:
            fields.append(
                {
                    "title": "Matched",
                    "value": f"```{event.matched_text[:200]}```",
                    "short": False,
                }
            )
        return {
            "attachments": [
                {
                    "fallback": f"TAME: {event.message}",
                    "color": color,
                    "title": title,
                    "text": event.message,
                    "fields": fields,
                    "footer": "TAME Notification",
                    "ts": int(event.timestamp.timestamp()),
                }
            ]
        }

    def _post(self, payload: dict[str, Any]) -> None:
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self._webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status != 200:
                    log.warning("Slack webhook returned %d", resp.status)
        except Exception:
            log.debug("Slack notification failed", exc_info=True)
