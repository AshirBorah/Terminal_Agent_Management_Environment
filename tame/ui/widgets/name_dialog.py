from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Select


# Result type: (name, profile) or None on cancel
NameDialogResult = tuple[str, str] | None

PROFILE_OPTIONS: list[tuple[str, str]] = [
    ("None", ""),
    ("Claude", "claude"),
    ("Codex", "codex"),
    ("Training", "training"),
]


class NameDialog(ModalScreen[NameDialogResult]):
    """Modal dialog that asks for a session name and optional profile."""

    DEFAULT_CSS = """
    NameDialog {
        align: center middle;
    }

    NameDialog #dialog-box {
        width: 55;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: thick $primary;
    }

    NameDialog #name-input {
        margin-top: 1;
    }

    NameDialog #profile-row {
        margin-top: 1;
        height: auto;
    }

    NameDialog #profile-label {
        width: auto;
        padding-right: 1;
    }

    NameDialog #profile-select {
        width: 1fr;
    }

    NameDialog #hint-label {
        margin-top: 1;
        color: $text-muted;
    }
    """

    def __init__(self, default_name: str, show_profile: bool = True) -> None:
        super().__init__()
        self._default_name = default_name
        self._show_profile = show_profile

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog-box"):
            yield Label("Session name:")
            yield Input(value=self._default_name, id="name-input")
            if self._show_profile:
                with Horizontal(id="profile-row"):
                    yield Label("Profile:", id="profile-label")
                    yield Select(
                        PROFILE_OPTIONS,
                        value="",
                        id="profile-select",
                        allow_blank=False,
                    )
            yield Label("Enter to confirm, Escape to cancel", id="hint-label")

    def on_mount(self) -> None:
        self.query_one("#name-input", Input).focus()

    def _get_result(self) -> NameDialogResult:
        name_input = self.query_one("#name-input", Input)
        name = name_input.value.strip() or self._default_name
        profile = ""
        if self._show_profile:
            try:
                select = self.query_one("#profile-select", Select)
                profile = str(select.value) if select.value is not Select.BLANK else ""
            except Exception:
                pass
        return (name, profile)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self.dismiss(self._get_result())

    def key_escape(self) -> None:
        self.dismiss(None)
