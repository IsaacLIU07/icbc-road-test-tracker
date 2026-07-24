# ICBC Road Test Tracker

Get notified the instant an earlier ICBC road test slot opens up — with a
tap-to-open link straight to the booking page — instead of manually
refreshing ICBC's site.

Not affiliated with ICBC. This is a personal automation tool that polls
ICBC's public booking system on your behalf; see [Notes and constraints](#notes-and-constraints)
below before using it.

## What it does

- Polls ICBC for open slots at **one test centre** you choose
- Notifies you on **Telegram** (with a button that opens the ICBC booking
  page) the moment a slot matching your rules appears
- Fully **rule-based**, so you only hear about slots you'd actually take:
  - Any number of acceptable date ranges (e.g. "before Aug 1" and
    "Sep 1–Oct 20")
  - Recurring weekday blackouts (e.g. never Mondays/Tuesdays)
  - Specific individual excluded dates
  - Automatically respects BC's minimum L-holding period (12 months, or 9
    with an approved driver training course) so you're never notified about
    a date you're not legally eligible to book
- **Pause/resume anytime** by sending `/stop` or `/start` to your own
  Telegram bot, or from the local setup wizard — no need to stop the tracker
- A local **setup wizard** (a small web page on your own machine) for
  filling in your details instead of hand-editing a config file
- **Config-driven**: nothing in the code is specific to any one person —
  copy `config.example.yaml`, fill in your own details, run it

## Quick start

See **[SETUP.md](SETUP.md)** for full step-by-step instructions (installing
Python, creating a Telegram bot, finding your test centre's ID, running the
wizard, and keeping it running continuously via Windows Task Scheduler).

Short version, once Python is installed:

```
py -m pip install -r requirements.txt
py app.py
```

Then open `http://127.0.0.1:5000` and fill in the form.

## How it works

A small Python script logs into ICBC's booking system (using the same
last-name / licence-number / keyword you'd use on their site) and polls
for available appointments at your chosen location, filtering results
through your rules. New matches trigger a Telegram push via a bot you
create yourself. Everything — your ICBC details, Telegram token, and rules
— lives in a local `config.yaml` that never leaves your machine (it's
gitignored, and the wizard talks directly to ICBC/Telegram, never to any
third-party server).

## Notes and constraints

- **This automates polling of ICBC's public website**, which is a legal/ToS
  grey area — it doesn't bypass any authentication or access anything you
  couldn't see by logging in yourself, but it's not an officially sanctioned
  integration either. Use at your own discretion.
- ICBC's request/response shapes were reverse-engineered by observing real
  traffic, not from official documentation, so ICBC changing their site
  could break this without warning. `py main.py --dry-run --debug` shows
  the raw API response if something needs adjusting.
- It needs to keep running to notify you — either a terminal window, or
  registered as a Task Scheduler job (covered in `SETUP.md`). It does not
  run when your computer is off; for true 24/7 uptime you'd need to deploy
  it on a small always-on server instead of your own machine.
- This only **notifies** you — it does not auto-book anything. You still
  pick and confirm the slot yourself on ICBC's site.

## License

MIT — see [LICENSE](LICENSE).
