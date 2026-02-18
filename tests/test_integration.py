"""Integration smoke tests for TAME.

These tests exercise multi-widget interactions using Textual's async pilot.
"""

from __future__ import annotations

import pytest

from tame.app import TAMEApp
from tame.notifications.models import EventType
from tame.ui.widgets import (
    HeaderBar,
    NotificationPanel,
    SessionSidebar,
    SessionViewer,
    StatusBar,
)
from tame.ui.widgets.session_search_bar import SessionSearchBar


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(tmp_path) -> TAMEApp:
    """Create a TAMEApp with a temp config that won't spawn real tmux."""
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[sessions]\nstart_in_tmux = false\nrestore_tmux_sessions_on_startup = false\n'
        '[notifications]\nenabled = true\n'
    )
    return TAMEApp(config_path=str(config_file))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSessionLifecycle:
    @pytest.mark.asyncio
    async def test_app_starts_with_no_sessions(self, tmp_path):
        app = _make_app(tmp_path)
        async with app.run_test():
            _status_bar = app.query_one(StatusBar)  # verify widget exists
            # No sessions yet
            assert app._active_session_id is None

    @pytest.mark.asyncio
    async def test_session_search_bar_hidden_by_default(self, tmp_path):
        app = _make_app(tmp_path)
        async with app.run_test():
            search_bar = app.query_one(SessionSearchBar)
            assert not search_bar.has_class("visible")


class TestConfigResilience:
    @pytest.mark.asyncio
    async def test_app_starts_with_broken_config(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("this is [[[broken toml")
        app = TAMEApp(config_path=str(config_file))
        async with app.run_test():
            # App should start without crashing
            assert app.query_one(SessionViewer) is not None
            assert app.query_one(SessionSidebar) is not None

    @pytest.mark.asyncio
    async def test_app_starts_with_negative_values(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[sessions]\nidle_threshold_seconds = -100\nresource_poll_seconds = -5\n'
        )
        app = TAMEApp(config_path=str(config_file))
        async with app.run_test():
            assert app.query_one(HeaderBar) is not None


class TestNotificationHistory:
    @pytest.mark.asyncio
    async def test_notification_history_opens(self, tmp_path):
        app = _make_app(tmp_path)
        async with app.run_test() as pilot:
            # Dispatch a test notification
            app._notification_engine.dispatch(
                event_type=EventType.ERROR,
                session_id="test-session",
                session_name="test",
                message="Test error",
            )
            # Open notification history
            app.action_notification_history()
            await pilot.pause()
            # Check that NotificationPanel is pushed
            assert isinstance(app.screen, NotificationPanel)
