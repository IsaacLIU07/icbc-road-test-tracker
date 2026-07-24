"""Tracks whether notifications are currently paused, and the Telegram
long-poll offset (so restarts don't reprocess old commands)."""

from __future__ import annotations

import json
from pathlib import Path


class ControlStore:
    def __init__(self, path: Path):
        self.path = path
        self._data = {"paused": False, "telegram_offset": 0, "last_check": None}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self._data.update(json.loads(self.path.read_text()))
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=2))

    @property
    def paused(self) -> bool:
        return bool(self._data["paused"])

    def set_paused(self, value: bool) -> None:
        self._data["paused"] = value
        self._save()

    @property
    def telegram_offset(self) -> int:
        return int(self._data["telegram_offset"])

    def set_telegram_offset(self, value: int) -> None:
        self._data["telegram_offset"] = value
        self._save()

    @property
    def last_check(self) -> str | None:
        return self._data.get("last_check")

    def set_last_check(self, value: str) -> None:
        self._data["last_check"] = value
        self._save()
