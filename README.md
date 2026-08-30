# 💧 Hydro Buddy — Desktop Water Reminder

Your pixel-art buddy pops up in the bottom-right corner of your screen on a
timer with a speech bubble reminding you to drink water.

## ✨ Features

- **Animated reminder popup** — a pixel-art character with a speech bubble
  appears in the corner of your screen at a configurable interval (30
  minutes by default).
- **✅ Yes, I drank!** → asks how soon to remind you again (30 min / 1 hour).
- **⏰ Snooze 10 min** → reminds you again in 10 minutes.
- Closing the popup with the ✕ counts as a snooze.
- **System tray icon** (optional, via `pystray`) — right-click to trigger a
  reminder immediately ("Remind me now") or quit the app.
- **Startup toast** — a brief "Hydro Buddy is running!" notification on launch.
- Transparent-background character rendering (true transparency on Windows;
  a soft background fallback on macOS/Linux).

## 🛠️ Tech Stack

| Category | Technology |
|---|---|
| Language | Python 3.8+ |
| GUI | tkinter (standard library) |
| Image processing | Pillow, NumPy (custom alpha-compositing for GIF transparency) |
| System tray | pystray *(optional)* |

## 🧠 How It Works

The app loads and processes the character GIF once at startup (removing its
white background via an alpha ramp + color decontamination step), then uses
tkinter's `.after()` scheduler to show a popup at the configured interval.
Depending on your response, it reschedules the next reminder — either after
a snooze, or after the interval you pick in the follow-up popup.

## 🏗️ Architecture

```text
Launch → Load & process GIF frames → Schedule first reminder
                                            ↓
                                    Reminder popup shown
                                            ↓
                  Yes, I drank! ──┐          │          ┌── Snooze / Close
                                  ↓          ↓          ↓
                    Follow-up: pick interval    Reschedule after snooze time
                                  ↓
                          Reschedule accordingly
```

## 🚀 Getting Started

1. Make sure you have Python 3.8+ installed.
2. Install dependencies:
```bash
   pip install -r requirements.txt
```
3. Run it:
```bash
   python main.py
```

That's it — leave it running (minimize the terminal window) and it'll remind
you on schedule.

## 💻 Customizing

Open `main.py` and edit the constants near the top — all time values are in
**minutes**, and decimals work too (e.g. `0.5` = 30 seconds, handy for
quick testing without waiting a full interval):

| Constant | What it controls |
|---|---|
| `DEFAULT_INTERVAL_MIN` | Default reminder interval (currently `30`) |
| `SNOOZE_MIN` | Snooze duration (currently `10`) |
| `FOLLOWUP_OPTION_1_MIN` | First "remind me again in..." button (`30`) |
| `FOLLOWUP_OPTION_2_MIN` | Second "remind me again in..." button (`60`) |
| `CHAR_WIDTH` | Character size in the popup (pixels) |
| `CORNER_MARGIN` | Distance from screen edges |

Button labels update automatically to say "seconds", "minutes", or "hours"
depending on the value.

## 📂 Project Structure

```text
Hydro-Buddy-Water-Reminder/
├── main.py             # App logic: GUI, scheduling, tray icon
├── requirements.txt    # Pillow, pystray, numpy
└── assets/
    └── character.gif   # Animated pixel-art character
```

## 🌐 Running Automatically at Startup

- **Windows**: Press `Win+R`, type `shell:startup`, and drop a shortcut to
  `main.py` (or a small `.bat` file running `pythonw main.py`) into the
  folder that opens.
- **macOS**: Add it as a Login Item in System Settings → General → Login
  Items (wrap it in a shell script or use `pythonw`/`py2app` for no
  terminal window).
- **Linux**: Add a `.desktop` entry to `~/.config/autostart/`.

## 🔮 Future Improvements

- Native OS notifications instead of custom tkinter popups.
- A settings UI instead of editing constants directly in `main.py`.
- Optional intake history/logging.

## 🎯 Skills Demonstrated

- Python GUI development with tkinter (event-driven programming, custom
  widgets, canvas drawing).
- Image processing: GIF frame extraction and alpha-channel compositing
  with Pillow + NumPy.
- Cross-platform handling of OS-specific quirks (window transparency).
- Graceful optional-dependency handling (system tray via `pystray`).

## 👨‍💻 Author

Jay Patel

AI/ML Engineer | Data Science | Automation | Python | Data Analysis | Data Engineer
