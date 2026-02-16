from __future__ import annotations

import re
from dataclasses import dataclass


# Priority order for scanning — earlier categories win on ties.
# "weak_prompt" is checked after "prompt" so strong prompts take precedence.
SCAN_ORDER: list[str] = ["error", "prompt", "weak_prompt", "completion", "progress"]


@dataclass(frozen=True, slots=True)
class PatternMatch:
    category: str
    pattern_index: int
    matched_text: str
    line: str


class PatternMatcher:
    def __init__(self, patterns: dict[str, list[str]]) -> None:
        # Compile once.  Stored as category -> list[(index, compiled_re)].
        import logging

        _log = logging.getLogger("tame.pattern_matcher")
        self._compiled: dict[str, list[tuple[int, re.Pattern[str]]]] = {}
        for category, raw_patterns in patterns.items():
            compiled: list[tuple[int, re.Pattern[str]]] = []
            for i, p in enumerate(raw_patterns):
                try:
                    compiled.append((i, re.compile(p, re.IGNORECASE)))
                except re.error as exc:
                    _log.warning(
                        "Skipping invalid regex in [%s] pattern #%d %r: %s",
                        category,
                        i,
                        p,
                        exc,
                    )
            self._compiled[category] = compiled

    def scan(self, line: str) -> PatternMatch | None:
        for category in SCAN_ORDER:
            compiled = self._compiled.get(category, [])
            for idx, rx in compiled:
                m = rx.search(line)
                if m:
                    return PatternMatch(
                        category=category,
                        pattern_index=idx,
                        matched_text=m.group(),
                        line=line,
                    )
        # Check any categories not in SCAN_ORDER (user-defined extras).
        for category, compiled in self._compiled.items():
            if category in SCAN_ORDER:
                continue
            for idx, rx in compiled:
                m = rx.search(line)
                if m:
                    return PatternMatch(
                        category=category,
                        pattern_index=idx,
                        matched_text=m.group(),
                        line=line,
                    )
        return None
