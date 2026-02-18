from __future__ import annotations

import copy
import logging
import os
import re
import tomllib
from pathlib import Path

from tame.config.defaults import DEFAULT_CONFIG

log = logging.getLogger(__name__)

# Numeric config keys that must be non-negative, with their floor values.
_CLAMP_NON_NEGATIVE: dict[str, float] = {
    "idle_threshold_seconds": 0,
    "idle_prompt_timeout": 0,
    "state_debounce_ms": 0,
    "resource_poll_seconds": 1,
    "timeout_ms": 0,
    "volume": 0,
    "max_size": 1,
    "timeout": 0,
    "verbosity": 0,
}


class ConfigManager:
    def __init__(self, config_path: str | None = None) -> None:
        if config_path is not None:
            self._config_path = Path(config_path).expanduser()
        else:
            xdg = os.environ.get("XDG_CONFIG_HOME", "~/.config")
            self._config_path = Path(xdg).expanduser() / "tame" / "config.toml"
        self._config: dict = {}

    @property
    def config(self) -> dict:
        if not self._config:
            self._config = self.load()
        return self._config

    def load(self) -> dict:
        defaults = copy.deepcopy(DEFAULT_CONFIG)
        if not self._config_path.exists():
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            self.save(defaults)
            self._config = defaults
            return defaults

        try:
            with open(self._config_path, "rb") as f:
                user_config = tomllib.load(f)
        except Exception as exc:
            log.warning(
                "Failed to parse config %s: %s — using defaults", self._config_path, exc
            )
            self._config = defaults
            return defaults

        merged = self._deep_merge(defaults, user_config)
        self._clamp_numeric_values(merged)
        self._validate_regex_patterns(merged)
        self._config = merged
        return merged

    def _clamp_numeric_values(self, config: dict) -> None:
        """Walk config and clamp known numeric fields to sane ranges."""
        for key, value in config.items():
            if isinstance(value, dict):
                self._clamp_numeric_values(value)
            elif key in _CLAMP_NON_NEGATIVE and isinstance(value, (int, float)):
                floor = _CLAMP_NON_NEGATIVE[key]
                if value < floor:
                    log.warning(
                        "Config key %r has invalid value %s, clamping to %s",
                        key,
                        value,
                        floor,
                    )
                    config[key] = floor

    def _validate_regex_patterns(self, config: dict) -> None:
        """Test-compile all regex patterns; replace invalid ones."""
        patterns_cfg = config.get("patterns", {})
        for category in ("error", "prompt", "completion", "progress"):
            cat_cfg = patterns_cfg.get(category, {})
            if not isinstance(cat_cfg, dict):
                continue
            for list_key in ("regexes", "shell_regexes", "weak_regexes"):
                regexes = cat_cfg.get(list_key, [])
                if not isinstance(regexes, list):
                    continue
                valid: list[str] = []
                for pattern in regexes:
                    try:
                        re.compile(pattern)
                        valid.append(pattern)
                    except re.error as exc:
                        log.warning(
                            "Invalid regex in patterns.%s.%s: %r (%s) — skipping",
                            category,
                            list_key,
                            pattern,
                            exc,
                        )
                cat_cfg[list_key] = valid

    def _deep_merge(self, base: dict, override: dict) -> dict:
        result = base.copy()
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def save(self, config: dict) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        toml_str = self._dict_to_toml(config)
        with open(self._config_path, "w") as f:
            f.write(toml_str)

    def get(self, key_path: str, default: object = None) -> object:
        keys = key_path.split(".")
        current: object = self.config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    # ------------------------------------------------------------------
    # Minimal TOML serializer (no tomli_w dependency)
    # ------------------------------------------------------------------

    def _dict_to_toml(self, d: dict, prefix: str = "") -> str:
        lines: list[str] = []
        tables: list[tuple[str, str, dict]] = []

        for key, value in d.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                tables.append((key, full_key, value))
            else:
                lines.append(f"{key} = {self._toml_value(value)}")

        result = "\n".join(lines)
        for _key, full_key, table in tables:
            section = self._dict_to_toml(table, prefix=full_key)
            header = f"\n[{full_key}]\n"
            result += header + section

        return result

    @staticmethod
    def _toml_value(value: object) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            return str(value)
        if isinstance(value, str):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        if isinstance(value, list):
            items = ", ".join(ConfigManager._toml_value(item) for item in value)
            return f"[{items}]"
        return str(value)
