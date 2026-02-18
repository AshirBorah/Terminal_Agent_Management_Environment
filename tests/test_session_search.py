"""Tests for in-session search (SessionSearchBar + SessionViewer search)."""

from __future__ import annotations

import pytest

# Skip entire module when pyte is not available
pyte = pytest.importorskip("pyte")

from tame.ui.widgets.session_viewer import SessionViewer, _TerminalState  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_viewer_with_content(lines: list[str], rows: int = 24, cols: int = 80) -> SessionViewer:
    """Create a SessionViewer with pyte terminal loaded with given lines."""
    viewer = SessionViewer()
    viewer._rows = rows
    viewer._cols = cols
    viewer._has_session = True
    terminal = _TerminalState("test-session", rows, cols)
    text = "\r\n".join(lines) + "\r\n"
    terminal.feed(text)
    viewer._terminals["test-session"] = terminal
    viewer._active_terminal = terminal
    return viewer


# ---------------------------------------------------------------------------
# Tests: match-finding logic
# ---------------------------------------------------------------------------


class TestFindMatches:
    def test_plain_text_match(self):
        viewer = _make_viewer_with_content(["hello world", "foo bar", "hello again"])
        matches = viewer._find_matches_in_screen("hello", False)
        assert len(matches) == 2
        # Both should be on different rows
        rows = {m[0] for m in matches}
        assert len(rows) == 2

    def test_plain_text_case_insensitive(self):
        viewer = _make_viewer_with_content(["Hello World", "HELLO"])
        matches = viewer._find_matches_in_screen("hello", False)
        assert len(matches) == 2

    def test_regex_match(self):
        viewer = _make_viewer_with_content(["error: something", "warning: other", "error: again"])
        matches = viewer._find_matches_in_screen(r"error:\s+\w+", True)
        assert len(matches) == 2

    def test_invalid_regex_returns_empty(self):
        viewer = _make_viewer_with_content(["test"])
        matches = viewer._find_matches_in_screen("[invalid", True)
        assert matches == []

    def test_no_match(self):
        viewer = _make_viewer_with_content(["hello world"])
        matches = viewer._find_matches_in_screen("xyz", False)
        assert matches == []

    def test_multiple_matches_per_line(self):
        viewer = _make_viewer_with_content(["aaa bbb aaa"])
        matches = viewer._find_matches_in_screen("aaa", False)
        assert len(matches) == 2
        assert matches[0][0] == matches[1][0]  # same row
        assert matches[0][1] != matches[1][1]  # different columns


# ---------------------------------------------------------------------------
# Tests: set/clear search highlights
# ---------------------------------------------------------------------------


class TestSearchHighlights:
    def test_set_search_highlights_returns_count(self):
        viewer = _make_viewer_with_content(["hello world", "hello again"])
        count = viewer.set_search_highlights("hello")
        assert count == 2
        assert viewer.match_count == 2
        assert viewer.current_match_index == 0

    def test_set_search_highlights_empty_query(self):
        viewer = _make_viewer_with_content(["hello world"])
        count = viewer.set_search_highlights("")
        assert count == 0
        assert viewer.match_count == 0
        assert viewer.current_match_index == -1

    def test_clear_search_highlights(self):
        viewer = _make_viewer_with_content(["hello"])
        viewer.set_search_highlights("hello")
        assert viewer.match_count > 0
        viewer.clear_search_highlights()
        assert viewer.match_count == 0
        assert viewer.current_match_index == -1


# ---------------------------------------------------------------------------
# Tests: navigation
# ---------------------------------------------------------------------------


class TestSearchNavigation:
    def test_navigate_forward_wraps(self):
        viewer = _make_viewer_with_content(["a", "b", "a"])
        viewer.set_search_highlights("a")
        assert viewer.match_count == 2
        assert viewer.current_match_index == 0
        viewer.navigate_search(forward=True)
        assert viewer.current_match_index == 1
        viewer.navigate_search(forward=True)
        assert viewer.current_match_index == 0  # wrapped

    def test_navigate_backward_wraps(self):
        viewer = _make_viewer_with_content(["a", "b", "a"])
        viewer.set_search_highlights("a")
        assert viewer.current_match_index == 0
        viewer.navigate_search(forward=False)
        assert viewer.current_match_index == 1  # wrapped to last

    def test_navigate_no_matches_returns_negative(self):
        viewer = _make_viewer_with_content(["hello"])
        viewer.set_search_highlights("xyz")
        idx = viewer.navigate_search(forward=True)
        assert idx == -1
