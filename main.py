"""ICBC road-test availability tracker (CLI).

For a friendlier setup experience, use the local setup wizard instead:
    py app.py

Usage:
    py main.py --test-notify   # send one test Telegram message and exit
    py main.py --dry-run       # run one check, print results, notify nobody
    py main.py --dry-run --debug  # also print the raw ICBC API response
    py main.py                 # run continuously, notifying on new acceptable slots
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from datetime import datetime

import core
from control import ControlStore
from notifier import TelegramNotifier
from rules import WEEKDAY_NAMES
from state import StateStore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Run one check, print results, send no notification")
    parser.add_argument("--test-notify", action="store_true", help="Send a single test Telegram message and exit")
    parser.add_argument("--debug", action="store_true", help="Print the raw ICBC API response")
    args = parser.parse_args()

    try:
        cfg = core.load_config()
    except FileNotFoundError as exc:
        sys.exit(str(exc))

    if args.test_notify:
        core.send_test_notification(cfg)
        print("Test notification sent.")
        return

    if args.dry_run:
        try:
            rules, slots, raw = core.check_availability(cfg)
        except Exception as exc:
            sys.exit(f"Check failed: {exc}")
        print(f"Earliest eligible test date: {rules.earliest_eligible.isoformat()}")
        if args.debug:
            print(f"(debug) raw ICBC response ({len(raw)} entries):")
            print(raw)
            print(f"(debug) {len(slots)} acceptable slot(s) after filtering")
        if not slots:
            print("No acceptable slots found right now.")
        for d, t in slots:
            print(f"  {d.isoformat()} {t} ({WEEKDAY_NAMES[d.weekday()]})")
        return

    rules = core.build_rules(cfg)
    print(f"Earliest eligible test date: {rules.earliest_eligible.isoformat()}")

    state = StateStore(core.STATE_PATH)
    control = ControlStore(core.CONTROL_PATH)
    notifier = TelegramNotifier(
        cfg["notifications"]["telegram"]["bot_token"],
        cfg["notifications"]["telegram"]["chat_id"],
    )
    interval_min = cfg["polling"]["interval_seconds_min"]
    interval_max = cfg["polling"]["interval_seconds_max"]

    print("Starting continuous polling. Send /stop or /start to the bot to pause/resume. Ctrl+C to quit entirely.")
    try:
        notifier.send(f"ICBC tracker started. Watching {cfg['location']['name']} for openings.")
    except Exception as exc:
        print(f"Error sending startup notification: {exc}", file=sys.stderr)

    while True:
        try:
            core.process_telegram_commands(cfg, control, notifier)
        except Exception as exc:
            print(f"Error checking Telegram commands: {exc}", file=sys.stderr)

        if control.paused:
            print("Paused - waiting for /start...")
        else:
            try:
                _, slots, _ = core.check_availability(cfg)
                control.set_last_check(datetime.now().strftime("%Y-%m-%d %H:%M"))
                keys = [f"{d.isoformat()}|{t}" for d, t in slots]
                new_keys = state.diff_and_update(keys)
                for key in new_keys:
                    d_str, t_str = key.split("|", 1)
                    notifier.send(
                        f"*New ICBC test slot open!*\n{d_str} at {t_str}\n{cfg['location']['name']}",
                        button_text="Open ICBC Booking",
                        button_url=cfg["booking_url"],
                    )
                    print(f"Notified: {key}")
            except Exception as exc:  # keep the loop alive across transient failures
                print(f"Error during poll: {exc}", file=sys.stderr)

        time.sleep(random.uniform(interval_min, interval_max))


if __name__ == "__main__":
    main()
