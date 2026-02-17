"""Tests for config resilience: malformed TOML, negative values, invalid regexes."""

from __future__ import annotations

import os
import tempfile

import pytest

from tame.config.defaults import DEFAULT_CONFIG
from tame.config.manager import ConfigManager


# ---------------------------------------------------------------------------
# Tests: Invalid TOML falls back to defaults
# ---------------------------------------------------------------------------


class TestInvalidToml:
    def test_malformed_toml_uses_defaults(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("this is not valid toml [[[")
        mgr = ConfigManager(config_path=str(config_file))
        cfg = mgr.load()
        # Should fall back to defaults without crashing
        assert cfg.get("general", {}).get("log_level") == DEFAULT_CONFIG["general"]["log_level"]

    def test_empty_file_uses_defaults(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("")
        mgr = ConfigManager(config_path=str(config_file))
        cfg = mgr.load()
        assert "general" in cfg
        assert "sessions" in cfg

    def test_partial_config_merges_with_defaults(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('[general]\nlog_level = "DEBUG"\n')
        mgr = ConfigManager(config_path=str(config_file))
        cfg = mgr.load()
        assert cfg["general"]["log_level"] == "DEBUG"
        # Other defaults should still be present
        assert "sessions" in cfg
        assert "patterns" in cfg


# ---------------------------------------------------------------------------
# Tests: Negative numeric values are clamped
# ---------------------------------------------------------------------------


class TestNumericClamping:
    def test_negative_idle_threshold_clamped(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('[sessions]\nidle_threshold_seconds = -100\n')
        mgr = ConfigManager(config_path=str(config_file))
        cfg = mgr.load()
        assert cfg["sessions"]["idle_threshold_seconds"] >= 0

    def test_negative_volume_clamped(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('[notifications.audio]\nvolume = -0.5\n')
        mgr = ConfigManager(config_path=str(config_file))
        cfg = mgr.load()
        assert cfg["notifications"]["audio"]["volume"] >= 0

    def test_negative_resource_poll_clamped(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('[sessions]\nresource_poll_seconds = -5\n')
        mgr = ConfigManager(config_path=str(config_file))
        cfg = mgr.load()
        assert cfg["sessions"]["resource_poll_seconds"] >= 1


# ---------------------------------------------------------------------------
# Tests: Invalid regex patterns are skipped
# ---------------------------------------------------------------------------


class TestInvalidRegex:
    def test_invalid_regex_skipped(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[patterns.error]\n'
            'regexes = ["[invalid_regex", "valid_pattern"]\n'
        )
        mgr = ConfigManager(config_path=str(config_file))
        cfg = mgr.load()
        error_regexes = cfg["patterns"]["error"]["regexes"]
        assert "[invalid_regex" not in error_regexes
        assert "valid_pattern" in error_regexes

    def test_all_invalid_regexes_results_in_empty_list(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[patterns.prompt]\n'
            'regexes = ["[bad1", "[bad2"]\n'
        )
        mgr = ConfigManager(config_path=str(config_file))
        cfg = mgr.load()
        assert cfg["patterns"]["prompt"]["regexes"] == []


# ---------------------------------------------------------------------------
# Tests: Missing config sections use defaults
# ---------------------------------------------------------------------------


class TestMissingSections:
    def test_missing_config_file_creates_default(self, tmp_path):
        config_file = tmp_path / "nonexistent" / "config.toml"
        mgr = ConfigManager(config_path=str(config_file))
        cfg = mgr.load()
        assert cfg["general"]["log_level"] == DEFAULT_CONFIG["general"]["log_level"]
        assert config_file.exists()

    def test_missing_notifications_section_uses_defaults(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('[general]\nlog_level = "INFO"\n')
        mgr = ConfigManager(config_path=str(config_file))
        cfg = mgr.load()
        assert "notifications" in cfg
        assert cfg["notifications"]["enabled"] is True
