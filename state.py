"""Tracks which acceptable slots we've already notified about, across restarts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


class StateStore:
    def __init__(self, path: Path):
        self.path = path
        self._known: set[str] = set()
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self._known = set(json.loads(self.path.read_text()))
            except (json.JSONDecodeError, OSError):
                self._known = set()

    def _save(self) -> None:
        self.path.write_text(json.dumps(sorted(self._known), indent=2))

    def diff_and_update(self, current_keys: Iterable[str]) -> list[str]:
        """Returns keys that are new since the last call, then updates stored state
        to exactly match current_keys (so slots that later disappear and reopen
        will notify again)."""
        current = set(current_keys)
        new_keys = sorted(current - self._known)
        self._known = current
        self._save()
        return new_keys
