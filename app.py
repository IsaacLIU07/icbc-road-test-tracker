"""Local setup wizard for the ICBC tracker.

Run with `py app.py`, then open http://127.0.0.1:5000 in a browser.
Binds to localhost only - this is a single-user local tool, not a hosted service.
"""

from __future__ import annotations

from flask import Flask, jsonify, render_template, request

import core
from control import ControlStore

app = Flask(__name__, static_folder="static", template_folder="templates")


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/config")
def get_config():
    if not core.config_exists():
        return jsonify({"exists": False, "config": None})
    try:
        cfg = core.load_config()
    except Exception as exc:
        return jsonify({"exists": True, "config": None, "error": str(exc)}), 500
    return jsonify({"exists": True, "config": cfg})


@app.post("/api/save")
def save_config():
    cfg = request.get_json(force=True)
    error = _validate_config(cfg)
    if error:
        return jsonify({"ok": False, "error": error}), 400
    try:
        core.save_config(cfg)
    except Exception as exc:
        return jsonify({"ok": False, "error": f"Failed to write config.yaml: {exc}"}), 500
    return jsonify({"ok": True})


@app.post("/api/test-notify")
def test_notify():
    cfg = request.get_json(force=True)
    try:
        core.send_test_notification(cfg)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True})


@app.post("/api/dry-run")
def dry_run():
    cfg = request.get_json(force=True)
    try:
        rules, slots, raw = core.check_availability(cfg)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify(
        {
            "ok": True,
            "earliest_eligible": rules.earliest_eligible.isoformat(),
            "slots": [{"date": d.isoformat(), "time": t} for d, t in slots],
            "raw_count": len(raw),
        }
    )


@app.get("/api/status")
def get_status():
    control = ControlStore(core.CONTROL_PATH)
    return jsonify({"paused": control.paused, "last_check": control.last_check})


@app.post("/api/pause")
def pause():
    control = ControlStore(core.CONTROL_PATH)
    control.set_paused(True)
    return jsonify({"ok": True, "paused": True})


@app.post("/api/resume")
def resume():
    control = ControlStore(core.CONTROL_PATH)
    control.set_paused(False)
    return jsonify({"ok": True, "paused": False})


@app.post("/api/telegram/detect-chat-id")
def detect_chat_id():
    body = request.get_json(force=True)
    bot_token = (body or {}).get("bot_token", "").strip()
    if not bot_token:
        return jsonify({"ok": False, "error": "Enter your bot token first."}), 400
    try:
        chat_id = core.detect_telegram_chat_id(bot_token)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "chat_id": chat_id})


def _validate_config(cfg: dict) -> str | None:
    if not isinstance(cfg, dict):
        return "Malformed request."
    try:
        icbc = cfg["icbc"]
        for field in ("last_name", "licence_number", "keyword"):
            if not icbc.get(field):
                return f"Missing ICBC field: {field}"
        if icbc.get("exam_class") not in (5, 7):
            return "exam_class must be 5 or 7"

        licensing = cfg["licensing"]
        if not licensing.get("l_issue_date"):
            return "Missing L issue date"

        location = cfg["location"]
        if not location.get("a_pos_id"):
            return "Missing location.a_pos_id - see the location help text for how to find it"

        date_rules = cfg["date_rules"]
        if not date_rules.get("allowed_ranges"):
            return "Add at least one acceptable date range"
        for r in date_rules["allowed_ranges"]:
            if not r.get("end"):
                return "Every date range needs an end date"

        telegram = cfg["notifications"]["telegram"]
        if not telegram.get("bot_token") or not telegram.get("chat_id"):
            return "Missing Telegram bot token or chat id"

        if not cfg.get("booking_url"):
            return "Missing booking_url"
    except KeyError as exc:
        return f"Missing config section: {exc}"
    return None


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
