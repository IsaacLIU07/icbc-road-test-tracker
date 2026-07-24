"""Shared logic used by both the CLI (main.py) and the local setup-wizard webapp (app.py).

Endpoint shapes were reverse-engineered from public reference implementations
(not official ICBC documentation), so response parsing is deliberately
defensive - see icbc_client.py.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import yaml

from eligibility import min_eligible_date
from icbc_client import ICBCClient
from notifier import TelegramNotifier
from rules import DateRange, DateRules

CONFIG_PATH = Path(__file__).parent / "config.yaml"
STATE_PATH = Path(__file__).parent / "state.json"
CONTROL_PATH = Path(__file__).parent / "control.json"

# Field names are unconfirmed against ICBC's real response schema - see icbc_client.py.
DATE_KEYS = ("apptDate", "appointmentDate", "examDate", "date")
TIME_KEYS = ("startTm", "startTime", "time")

# Keeps config.yaml in a stable, readable key order regardless of dict insertion order.
_CONFIG_KEY_ORDER = [
    "icbc",
    "licensing",
    "location",
    "date_rules",
    "polling",
    "notifications",
    "booking_url",
]


def config_exists() -> bool:
    return CONFIG_PATH.exists()


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Missing {CONFIG_PATH}. Copy config.example.yaml to config.yaml and fill in your details, "
            "or use the setup wizard (py app.py)."
        )
    return yaml.safe_load(CONFIG_PATH.read_text())


def save_config(cfg: dict) -> None:
    ordered = {k: cfg[k] for k in _CONFIG_KEY_ORDER if k in cfg}
    ordered.update({k: v for k, v in cfg.items() if k not in ordered})
    CONFIG_PATH.write_text(yaml.safe_dump(ordered, sort_keys=False, default_flow_style=False))


def build_rules(cfg: dict) -> DateRules:
    l_issue = date.fromisoformat(cfg["licensing"]["l_issue_date"])
    eligible = min_eligible_date(l_issue, bool(cfg["licensing"]["completed_driver_training_course"]))

    ranges = []
    for r in cfg["date_rules"]["allowed_ranges"]:
        start = date.fromisoformat(r["start"]) if r.get("start") else None
        end = date.fromisoformat(r["end"])
        ranges.append(DateRange(start=start, end=end))

    blocked_dates = {date.fromisoformat(d) for d in cfg["date_rules"].get("blocked_dates", [])}
    blocked_weekdays = set(cfg["date_rules"].get("blocked_weekdays", []))

    return DateRules(
        allowed_ranges=ranges,
        blocked_weekdays=blocked_weekdays,
        blocked_dates=blocked_dates,
        earliest_eligible=eligible,
    )


def extract_slot(entry: dict) -> tuple[date, str] | None:
    # Confirmed real shape: entry["appointmentDt"] = {"date": "2026-10-02", "dayOfWeek": "Friday"}.
    # DATE_KEYS is kept as a fallback in case ICBC changes this again.
    d_raw = None
    appointment_dt = entry.get("appointmentDt")
    if isinstance(appointment_dt, dict):
        d_raw = appointment_dt.get("date")
    if d_raw is None:
        d_raw = next((entry[k] for k in DATE_KEYS if k in entry), None)

    t_raw = next((entry[k] for k in TIME_KEYS if k in entry), "")
    if d_raw is None:
        return None
    try:
        d = datetime.fromisoformat(str(d_raw)[:10]).date()
    except ValueError:
        return None
    return d, str(t_raw)


def check_availability(cfg: dict) -> tuple[DateRules, list[tuple[date, str]], list[dict]]:
    """Logs into ICBC, queries the configured location, and returns
    (computed date rules, sorted list of currently-open acceptable slots,
    raw unfiltered API response entries - useful for debugging)."""
    rules = build_rules(cfg)

    a_pos_id = cfg["location"]["a_pos_id"]
    if not a_pos_id:
        raise ValueError("location.a_pos_id is not set - see SETUP.md for how to find it.")

    client = ICBCClient(
        cfg["icbc"]["last_name"],
        cfg["icbc"]["licence_number"],
        cfg["icbc"]["keyword"],
    )
    client.login()

    search_from = max(date.today(), rules.earliest_eligible)
    raw = client.get_available_appointments(a_pos_id, cfg["icbc"]["exam_class"], search_from)

    acceptable = []
    for entry in raw:
        slot = extract_slot(entry)
        if slot is None:
            continue
        d, t = slot
        if rules.is_acceptable(d):
            acceptable.append((d, t))

    return rules, sorted(acceptable), raw


def send_test_notification(cfg: dict) -> None:
    notifier = TelegramNotifier(
        cfg["notifications"]["telegram"]["bot_token"],
        cfg["notifications"]["telegram"]["chat_id"],
    )
    notifier.send(
        "*ICBC tracker test* — this is a test notification.",
        button_text="Open ICBC Booking",
        button_url=cfg["booking_url"],
    )


def process_telegram_commands(cfg: dict, control, notifier: TelegramNotifier) -> None:
    """Checks for new /stop, /start, /status messages sent to the bot and
    updates the pause state accordingly. Ignores messages from any chat
    other than the configured chat_id."""
    own_chat_id = str(cfg["notifications"]["telegram"]["chat_id"])

    updates = notifier.get_updates(control.telegram_offset)
    if not updates:
        return

    for update in updates:
        control.set_telegram_offset(update["update_id"] + 1)

        message = update.get("message") or {}
        chat_id = str(message.get("chat", {}).get("id", ""))
        text = (message.get("text") or "").strip().lower()
        if chat_id != own_chat_id or not text:
            continue

        if text.startswith("/stop") or text.startswith("/pause"):
            control.set_paused(True)
            notifier.send("Notifications paused. Send /start to resume.")
        elif text.startswith("/start") or text.startswith("/resume"):
            control.set_paused(False)
            notifier.send("Notifications resumed.")
        elif text.startswith("/status"):
            notifier.send("Currently paused." if control.paused else "Currently active and checking for openings.")


def detect_telegram_chat_id(bot_token: str) -> str:
    """Calls Telegram's getUpdates and returns the most recent chat id.
    Raises ValueError with a user-facing message if none is found."""
    import requests

    resp = requests.get(f"https://api.telegram.org/bot{bot_token}/getUpdates", timeout=15)
    if resp.status_code == 404:
        raise ValueError("That bot token doesn't look valid (Telegram returned 404 Not Found).")
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise ValueError(data.get("description", "Telegram API returned an error."))

    results = data.get("result", [])
    if not results:
        raise ValueError(
            "No messages found yet. Open Telegram, find your bot, and send it any message (e.g. \"hi\"), then try again."
        )

    last = results[-1]
    chat = (last.get("message") or last.get("channel_post") or {}).get("chat", {})
    chat_id = chat.get("id")
    if chat_id is None:
        raise ValueError("Couldn't find a chat id in Telegram's response.")
    return str(chat_id)
