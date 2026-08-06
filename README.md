# 💧 Hydro Buddy — Desktop Water Reminder

Your pixel-art buddy pops up in the bottom-right corner of your screen every
hour with a speech bubble reminding you to drink water.

- **✅ Yes, I drank!** → asks how soon to remind you again (30 min / 1 hour)
- **⏰ Snooze 10 min** → reminds you again in 10 minutes
- Closing the popup with the ✕ (if your OS shows one) counts as a snooze

It also adds a small icon to your system tray so it keeps running quietly in
the background, with a right-click menu to trigger a reminder immediately or
quit.

## Setup

1. Make sure you have Python 3.8+ installed.
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run it:
   ```
   python main.py
   ```

That's it — leave it running (minimize the terminal window) and it'll remind
you every hour.

## Customizing

Open `main.py` and edit the constants near the top — all time values are in
**minutes**, and decimals work too (handy for quick testing, e.g. `0.5` = 30
seconds, so you don't have to wait an hour to see it work):

| Constant                  | What it controls                                    |
|----------------------------|------------------------------------------------------|
| `DEFAULT_INTERVAL_MIN`     | Default reminder interval (e.g. `60` = every hour)   |
| `SNOOZE_MIN`               | Snooze duration (e.g. `10` = 10 minutes)             |
| `FOLLOWUP_OPTION_1_MIN`    | First "remind me again in..." button (e.g. `30`)     |
| `FOLLOWUP_OPTION_2_MIN`    | Second "remind me again in..." button (e.g. `60`)    |
| `CHAR_WIDTH`               | Character size in the popup (pixels)                 |
| `CORNER_MARGIN`            | Distance from screen edges                           |

Example for quick testing — reminders every 10 seconds, snooze after 5 seconds:
```python
DEFAULT_INTERVAL_MIN = 10 / 60   # 10 seconds
SNOOZE_MIN = 5 / 60              # 5 seconds
```
Button labels update automatically to say "seconds", "minutes", or "hours"
depending on the value, so you don't need to touch anything else.

## Running automatically at startup

- **Windows**: Press `Win+R`, type `shell:startup`, and drop a shortcut to
  `main.py` (or a small `.bat` file that runs `pythonw main.py`) into the
  folder that opens.
- **macOS**: Add it as a Login Item in System Settings → General → Login Items
  (wrap it in a small shell script or use `pythonw`/`py2app` if you want no
  terminal window).
- **Linux**: Add a `.desktop` entry to your autostart folder
  (`~/.config/autostart/`).

## Notes

- The transparent "floating" background for the character works best on
  Windows. On macOS/Linux, tkinter's transparency support is limited, so the
  popup will show a soft light-blue background behind the character instead
  of true transparency — everything else still works the same.
- `pystray` (the system tray icon) is optional — if it's not installed, the
  app still works, it just won't have a tray icon to quit from (close it via
  Task Manager/Activity Monitor, or add a quit hotkey if you'd like — happy
  to add one).
