# Setup

This tracker is config-driven — anyone can use it by filling in their own
details. Nothing in the code is specific to any one person.

## 1. Install Python

Download and install Python 3.11+ from https://www.python.org/downloads/
(check "Add python.exe to PATH" during install). Verify with:

```
py --version
```

**Use `py`, not `python`, for every command in this guide.** On Windows, the
plain `python` command often hits a Microsoft Store "app execution alias"
stub instead of your real install (you'll see a message like "Python was
not found; run without arguments to install from the Microsoft Store" even
though Python is installed). The `py` launcher reliably finds your real
install and avoids it. It also matters for `pip`: if you have more than one
Python installed (e.g. a Store copy alongside a python.org copy), bare `pip`
can install packages into a *different* interpreter than the one `py` runs —
always use `py -m pip` instead of bare `pip` to keep them in sync.

If `py --version` also fails, disable the stub in
**Settings → Apps → Advanced app settings → App execution aliases** by
turning off `python.exe`/`python3.exe`, then reinstall Python from
python.org.

Then install dependencies from this folder:

```
py -m pip install -r requirements.txt
```

## 2. Create a Telegram bot

1. In Telegram, message **@BotFather**.
2. Send `/newbot`, follow the prompts (pick any name/username).
3. BotFather gives you a **bot token** like `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`.
4. Send your new bot any message (e.g. "hi") so it knows about your chat —
   the setup wizard below can auto-detect your chat ID from this, but only
   after Telegram has seen at least one message from you.

## 3. Find your test centre's location ID

ICBC's API takes a numeric `aPosID` per location rather than a name, and
there's no public lookup endpoint for it, so this is a one-time manual step:

1. Go to the real ICBC road test booking site in Chrome/Edge and start booking
   a road test (you can back out before actually booking anything).
2. Open DevTools (F12) → **Network** tab, filter by `Fetch/XHR`.
3. Select your target test centre in the booking flow.
4. Look for a request to `getAvailableAppointments` (or similar) in the Network
   tab, click it, and check the **Request Payload** — it will contain
   `"aPosID": <number>` for the centre you picked.

## 4. Run the setup wizard

From this folder:

```
py app.py
```

Open **http://127.0.0.1:5000** in your browser. It's a local-only page — it
never leaves your machine, and nothing you type is sent anywhere except
directly to ICBC and Telegram when you click the test/check buttons.

Fill in:
- Your ICBC last name, licence number, and keyword
- Your L issue date and whether you completed an approved driver training
  course — the page shows your computed earliest eligible test date live
- Your target location's name and `aPosID` (from step 3)
- As many acceptable date ranges as you want, plus any weekdays or specific
  dates to always exclude
- Your Telegram bot token, then click **Detect** to auto-fill your chat ID

Before saving, use the buttons at the bottom to:
- **Send test notification** — confirms the Telegram bot/button work; you
  should get a push on your iPhone with an "Open ICBC Booking" button
- **Check availability now** — confirms ICBC login + the availability query
  actually work against the real API, and shows any currently-open
  acceptable slots

If "Check availability now" errors out, ICBC's response shape may differ
from what's assumed in `main.py`/`core.py` (`DATE_KEYS`/`TIME_KEYS`) — run
`py main.py --dry-run --debug` from a terminal to see the raw response
and adjust those field names.

Once both checks look good, click **Save configuration** — this writes
`config.yaml` in this folder (gitignored, never shared, holds your personal
info).

### Editing config.yaml by hand instead

If you'd rather skip the wizard, copy `config.example.yaml` to `config.yaml`
and fill in the same fields directly — the schema is documented with
comments in that file.

## 5. Run it continuously

Quick way — just leave a terminal window open:

```
powershell -ExecutionPolicy Bypass -File run_tracker.ps1
```

More robust way — register it as a Windows Task Scheduler job so it survives
reboots/logoffs while the PC is on. Replace `<path-to-this-folder>` below
with wherever you cloned/downloaded this project (e.g.
`C:\Users\yourname\Documents\icbc-road-test-tracker`):

1. Open **Task Scheduler** → **Create Task…** (not "Create Basic Task").
2. **General tab:** name it "ICBC Road Test Tracker". Under "Security
   options," select **"Run only when user is logged on"** — this is the
   simplest option and needs no stored password. ("Run whether user is
   logged on or not" is possible too, but on some setups Windows rejects the
   stored credentials with a confusing "user account is unknown" error — not
   worth the hassle unless you specifically need it to run before login.)
3. **Triggers tab:** New… → "Begin the task": **At log on** → Enabled → OK.
4. **Actions tab:** New… → Action: **Start a program**
   - Program/script: `powershell.exe`
   - Add arguments: `-ExecutionPolicy Bypass -File "<path-to-this-folder>\run_tracker.ps1"`
   - Start in: `<path-to-this-folder>`
5. **Conditions tab:** uncheck "Start the task only if the computer is on AC
   power" if this is a laptop.
6. **Settings tab:**
   - Check "If the task fails, restart every" → **1 minute**, "Attempt to
     restart up to" → **99** (values much higher than this can cause Task
     Scheduler to silently reject the whole task with a vague "one or more
     arguments are not valid" error).
   - Leave "Stop the task if it runs longer than" **unchecked** — the
     tracker is meant to run indefinitely.
   - Set "If the task is already running, then the following rule applies"
     to **"Do not start a new instance"** — prevents duplicate copies (and
     duplicate Telegram notifications) if the trigger fires more than once.
7. Save. Test it immediately without rebooting: right-click the task →
   **Run**, then check Task Manager for a `powershell.exe`/`python.exe`
   process to confirm it's alive.

Note: with "Run only when user is logged on," the tracker runs in a visible
PowerShell window — closing that window stops it. That's expected; just
leave it minimized.

## 6. Pausing / cancelling notifications

You don't need to stop the tracker to stop notifications. While it's running:

- **From Telegram**: send `/stop` (or `/pause`) to your bot to pause, `/start`
  (or `/resume`) to resume, `/status` to check. The bot confirms each change.
- **From the setup wizard**: run `py app.py`, open http://127.0.0.1:5000, and
  use the "Pause notifications" toggle near the top of the page.

Both control the same running tracker (they share `control.json` in this
folder). Pausing stops it from checking ICBC or sending you anything, without
killing the background process — handy once you've actually booked a test
and want to stop getting pinged, without tearing down the Task Scheduler job.
