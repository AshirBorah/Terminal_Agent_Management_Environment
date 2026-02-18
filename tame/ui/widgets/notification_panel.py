from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Label, Static

from tame.notifications.history import NotificationHistory
from tame.notifications.models import NotificationEvent, Priority


_PRIORITY_STYLE: dict[Priority, str] = {
    Priority.CRITICAL: "bold red",
    Priority.HIGH: "yellow",
    Priority.MEDIUM: "green",
    Priority.LOW: "dim",
}

_PRIORITY_ICON: dict[Priority, str] = {
    Priority.CRITICAL: "!!",
    Priority.HIGH: "!",
    Priority.MEDIUM: "*",
    Priority.LOW: "-",
}


class NotificationRow(Static):
    """A single notification event row."""

    DEFAULT_CSS = """
    NotificationRow {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    NotificationRow:hover {
        background: $surface-darken-2;
    }

    NotificationRow.priority-critical {
        color: #ef4444;
    }

    NotificationRow.priority-high {
        color: #f59e0b;
    }

    NotificationRow.priority-medium {
        color: #22c55e;
    }

    NotificationRow.priority-low {
        color: $text-muted;
    }
    """

    def __init__(self, event: NotificationEvent) -> None:
        super().__init__()
        self._event = event

    def on_mount(self) -> None:
        ev = self._event
        ts = ev.timestamp.strftime("%H:%M:%S")
        icon = _PRIORITY_ICON.get(ev.priority, "-")
        msg = ev.message[:120] + "..." if len(ev.message) > 120 else ev.message
        self.update(f"[{ts}] [{icon}] [{ev.session_name}] {msg}")
        self.add_class(f"priority-{ev.priority.value}")

    def on_click(self) -> None:
        screen = self.screen
        if isinstance(screen, NotificationPanel):
            screen.dismiss(self._event.session_id)


class NotificationPanel(ModalScreen[str | None]):
    """Modal panel showing notification history."""

    DEFAULT_CSS = """
    NotificationPanel {
        align: center middle;
    }

    NotificationPanel #notif-box {
        width: 90%;
        height: 80%;
        padding: 1 2;
        background: $surface;
        border: thick $primary;
    }

    NotificationPanel #notif-header {
        height: 2;
    }

    NotificationPanel #notif-scroll {
        height: 1fr;
    }

    NotificationPanel #notif-footer {
        height: 1;
        color: $text-muted;
    }
    """

    def __init__(self, history: NotificationHistory) -> None:
        super().__init__()
        self._history = history

    def compose(self) -> ComposeResult:
        events_list = self._history.get_all()
        with Vertical(id="notif-box"):
            yield Label(
                f"Notification History ({len(events_list)} events)  [Esc to close, C to clear]",
                id="notif-header",
            )
            with VerticalScroll(id="notif-scroll"):
                if not events_list:
                    yield Label("No notifications yet.", id="notif-empty")
                else:
                    for ev in reversed(events_list):
                        yield NotificationRow(ev)
            yield Label(
                "Click session name to switch  |  C = Clear  |  Esc = Close",
                id="notif-footer",
            )

    def key_escape(self) -> None:
        self.dismiss(None)

    def key_q(self) -> None:
        self.dismiss(None)

    def key_c(self) -> None:
        self._history.clear()
        scroll = self.query_one("#notif-scroll", VerticalScroll)
        for child in list(scroll.children):
            child.remove()
        scroll.mount(Label("No notifications yet.", id="notif-empty"))
        self.query_one("#notif-header", Label).update(
            "Notification History (0 events)  [Esc to close, C to clear]"
        )
