"""Sends Telegram push notifications with a tap-to-open booking button."""

from __future__ import annotations

import requests


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send(self, text: str, button_text: str | None = None, button_url: str | None = None) -> None:
        payload: dict = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }
        if button_text and button_url:
            payload["reply_markup"] = {"inline_keyboard": [[{"text": button_text, "url": button_url}]]}

        resp = requests.post(
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()

    def get_updates(self, offset: int) -> list[dict]:
        """Short-polls Telegram for new messages sent to the bot since `offset`."""
        resp = requests.get(
            f"https://api.telegram.org/bot{self.bot_token}/getUpdates",
            params={"offset": offset, "timeout": 0},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("description", "Telegram getUpdates failed"))
        return data.get("result", [])
