"""
Hydro Buddy — a cute desktop water-reminder app.

Every hour, your pixel-art buddy pops up in the corner of your screen with a
speech bubble reminding you to drink water. You can:
  - "Yes, I drank!"  -> asks how soon to remind you again (30 min / 1 hour)
  - "Snooze 10 min"  -> reminds you again in 10 minutes

Runs quietly in the system tray (if 'pystray' is installed) so you can keep
working while it waits for the next reminder.
"""

import os
import sys
import platform
import tkinter as tk
from tkinter import font as tkfont
from PIL import Image, ImageTk

# --------------------------------------------------------------------------
# Config — tweak these to taste
# --------------------------------------------------------------------------
ASSET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "character.gif")
CHAR_WIDTH = 170                 # displayed width of the character (px)
CORNER_MARGIN = 24               # distance from screen edges (px)
TASKBAR_ALLOWANCE = 70           # extra bottom margin so we clear the taskbar

# All of these are in MINUTES. Decimals are fine — e.g. 0.5 = 30 seconds,
# handy for testing without waiting a full hour.
DEFAULT_INTERVAL_MIN = 5 /60        # default reminder interval
SNOOZE_MIN = 5 / 60                 # snooze duration
FOLLOWUP_OPTION_1_MIN = 30       # first "remind me again in..." choice
FOLLOWUP_OPTION_2_MIN = 60       # second "remind me again in..." choice

UNIT_MS = 60_000  # 1 minute, in milliseconds


def minutes_to_ms(minutes: float) -> int:
    return int(minutes * UNIT_MS)


def format_minutes_label(minutes: float) -> str:
    """Turns 30 -> '30 minutes', 60 -> '1 hour', 90 -> '1.5 hours', 0.5 -> '30 seconds'."""
    if minutes < 1:
        seconds = round(minutes * 60)
        return f"{seconds} second{'s' if seconds != 1 else ''}"
    if minutes % 60 == 0:
        hours = int(minutes // 60)
        return f"{hours} hour{'s' if hours != 1 else ''}"
    if minutes > 60:
        hours = minutes / 60
        return f"{hours:g} hours"
    m = int(minutes) if minutes == int(minutes) else minutes
    return f"{m} minute{'s' if m != 1 else ''}"


# --------------------------------------------------------------------------
# GIF loading — resize + make near-white background transparent
# --------------------------------------------------------------------------
def load_gif_frames(path, target_width):
    """Returns (frames: list[ImageTk.PhotoImage], durations: list[int], size: (w,h)).

    Removes the gif's white background and turns it transparent. A hard
    cutoff leaves a faint white "halo" around the character on dark
    backgrounds (leftover white bleeding into the anti-aliased edge
    pixels), so this uses a soft alpha ramp plus color decontamination:
    edge pixels are un-blended from white so they look clean on any
    background, light or dark.

    Some source gifs include a fade-out/fade-in transition at the loop
    point (character mostly faded to white) so the loop reads smoothly on
    a white page. That's invisible on a white background but looks like a
    broken, fragmented character on a dark one — so frames that are mostly
    empty after removing the white background are dropped from the loop.
    """
    import numpy as np

    im = Image.open(path)
    frames = []
    durations = []
    opaque_ratios = []
    ratio = target_width / im.width
    target_size = (target_width, max(1, int(im.height * ratio)))

    # Pixels whiter than UPPER are fully transparent, darker than LOWER are
    # fully opaque, and everything between ramps smoothly (removes hard edges).
    LOWER, UPPER = 200.0, 247.0

    for i in range(im.n_frames):
        im.seek(i)
        frame = im.convert("RGBA").resize(target_size, Image.LANCZOS)

        arr = np.asarray(frame).astype(np.float32)
        rgb = arr[..., :3]
        whiteness = rgb.min(axis=2)  # low = colorful/dark, high = near-white

        alpha = np.clip((UPPER - whiteness) / (UPPER - LOWER), 0.0, 1.0)
        alpha_safe = np.where(alpha > 0.001, alpha, 1.0)[..., None]

        # Un-blend the white background out of translucent edge pixels so
        # they don't carry a leftover white tint once alpha-composited.
        decontaminated = (rgb - 255.0 * (1.0 - alpha_safe)) / alpha_safe
        arr[..., :3] = np.clip(decontaminated, 0, 255)
        arr[..., 3] = alpha * 255.0

        frame = Image.fromarray(arr.astype(np.uint8), mode="RGBA")
        opaque_ratios.append(float((alpha > 0.5).mean()))
        durations.append(im.info.get("duration", 80))
        frames.append(frame)

    # Drop near-blank fade frames: the source gif fades to white at its loop
    # point, so anything meaningfully thinner than the "full body" frames is
    # a fade transition, not a real pose.
    peak = max(opaque_ratios) if opaque_ratios else 0
    keep_threshold = peak * 0.90
    kept = [
        (f, d) for f, d, r in zip(frames, durations, opaque_ratios)
        if r >= keep_threshold
    ]
    if kept:
        frames, durations = zip(*kept)
        frames, durations = list(frames), list(durations)

    photo_frames = [ImageTk.PhotoImage(f) for f in frames]
    return photo_frames, durations, target_size


# --------------------------------------------------------------------------
# Rounded speech-bubble drawing helper
# --------------------------------------------------------------------------
def draw_speech_bubble(canvas, x, y, w, h, radius=16, tail=True):
    """Draws a rounded rectangle with a small downward tail on the canvas."""
    points = [
        x + radius, y,
        x + w - radius, y,
        x + w, y,
        x + w, y + radius,
        x + w, y + h - radius,
        x + w, y + h,
        x + w - radius, y + h,
        x + radius, y + h,
        x, y + h,
        x, y + h - radius,
        x, y + radius,
        x, y,
    ]
    canvas.create_polygon(points, smooth=True, fill="#eaf6ff", outline="#57b6ee", width=2)
    if tail:
        tail_x = x + w * 0.28
        canvas.create_polygon(
            tail_x, y + h - 2,
            tail_x + 14, y + h - 2,
            tail_x + 2, y + h + 14,
            fill="#eaf6ff", outline="#57b6ee",
        )


# --------------------------------------------------------------------------
# Popup base window (borderless, always-on-top, bottom-right corner)
# --------------------------------------------------------------------------
class PopupBase(tk.Toplevel):
    def __init__(self, app, width, height):
        super().__init__(app.root)
        self.app = app
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        try:
            self.attributes("-alpha", 0.98)
        except tk.TclError:
            pass

        self.bg_color = "#f4fbff"
        self.configure(bg=self.bg_color)

        # Best-effort transparency (Windows supports colorkey transparency well)
        self.transparent_ok = False
        if platform.system() == "Windows":
            try:
                self.attributes("-transparentcolor", self.bg_color)
                self.transparent_ok = True
            except tk.TclError:
                pass

        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x = sw - width - CORNER_MARGIN
        y = sh - height - TASKBAR_ALLOWANCE
        self.geometry(f"{width}x{height}+{x}+{y}")

        self.canvas = tk.Canvas(self, width=width, height=height,
                                 bg=self.bg_color, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)


# --------------------------------------------------------------------------
# Main reminder popup: character + "drink water" bubble + Yes/Snooze
# --------------------------------------------------------------------------
class ReminderPopup(PopupBase):
    WIDTH = 240
    HEIGHT = 460

    def __init__(self, app):
        super().__init__(app, self.WIDTH, self.HEIGHT)
        self.frame_idx = 0
        self._anim_job = None

        bubble_font = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        draw_speech_bubble(self.canvas, 10, 10, self.WIDTH - 20, 66)
        self.canvas.create_text(
            self.WIDTH / 2, 43,
            text="💧 Time to drink some water!",
            font=bubble_font, fill="#1c6ea4", width=self.WIDTH - 40,
        )

        self.char_item = self.canvas.create_image(
            self.WIDTH / 2, 100, anchor="n", image=app.frames[0]
        )

        btn_font = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        yes_btn = tk.Button(
            self, text="✅  Yes, I drank!", font=btn_font,
            bg="#3fb27f", fg="white", activebackground="#33996b",
            relief="flat", cursor="hand2", command=self.on_yes,
        )
        snooze_btn = tk.Button(
            self, text="⏰  Snooze 10 min", font=btn_font,
            bg="#f0a84e", fg="white", activebackground="#d9933c",
            relief="flat", cursor="hand2", command=self.on_snooze,
        )
        self.canvas.create_window(self.WIDTH / 2, self.HEIGHT - 60, window=yes_btn,
                                   width=self.WIDTH - 30, height=36)
        self.canvas.create_window(self.WIDTH / 2, self.HEIGHT - 18, window=snooze_btn,
                                   width=self.WIDTH - 30, height=36)

        self.protocol("WM_DELETE_WINDOW", self.on_snooze)  # closing = snooze
        self._animate()

    def _animate(self):
        self.frame_idx = (self.frame_idx + 1) % len(self.app.frames)
        self.canvas.itemconfig(self.char_item, image=self.app.frames[self.frame_idx])
        duration = self.app.durations[self.frame_idx]
        self._anim_job = self.after(duration, self._animate)

    def _close(self):
        if self._anim_job:
            self.after_cancel(self._anim_job)
        self.destroy()

    def on_yes(self):
        self._close()
        FollowUpPopup(self.app)

    def on_snooze(self):
        self._close()
        self.app.schedule_next(SNOOZE_MIN)


# --------------------------------------------------------------------------
# Follow-up popup: "remind me again in 30 min / 1 hour"
# --------------------------------------------------------------------------
class FollowUpPopup(PopupBase):
    WIDTH = 240
    HEIGHT = 260

    def __init__(self, app):
        super().__init__(app, self.WIDTH, self.HEIGHT)

        bubble_font = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        draw_speech_bubble(self.canvas, 10, 10, self.WIDTH - 20, 66)
        self.canvas.create_text(
            self.WIDTH / 2, 43,
            text="Nice! 🎉 Remind me again in:",
            font=bubble_font, fill="#1c6ea4", width=self.WIDTH - 40,
        )
        self.canvas.create_image(self.WIDTH / 2, 90, anchor="n", image=app.frames[0])

        btn_font = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        option1_btn = tk.Button(
            self, text=format_minutes_label(FOLLOWUP_OPTION_1_MIN), font=btn_font,
            bg="#57b6ee", fg="white", activebackground="#3f9dd6",
            relief="flat", cursor="hand2",
            command=lambda: self.choose(FOLLOWUP_OPTION_1_MIN),
        )
        option2_btn = tk.Button(
            self, text=format_minutes_label(FOLLOWUP_OPTION_2_MIN), font=btn_font,
            bg="#57b6ee", fg="white", activebackground="#3f9dd6",
            relief="flat", cursor="hand2",
            command=lambda: self.choose(FOLLOWUP_OPTION_2_MIN),
        )
        self.canvas.create_window(self.WIDTH / 2, self.HEIGHT - 60, window=option1_btn,
                                   width=self.WIDTH - 30, height=36)
        self.canvas.create_window(self.WIDTH / 2, self.HEIGHT - 18, window=option2_btn,
                                   width=self.WIDTH - 30, height=36)

        self.protocol("WM_DELETE_WINDOW", lambda: self.choose(DEFAULT_INTERVAL_MIN))

    def choose(self, minutes):
        self.destroy()
        self.app.schedule_next(minutes)


# --------------------------------------------------------------------------
# App controller
# --------------------------------------------------------------------------
class HydroBuddyApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()  # no main window, just background scheduling

        if not os.path.exists(ASSET_PATH):
            raise FileNotFoundError(f"Character gif not found at: {ASSET_PATH}")

        self.frames, self.durations, _ = load_gif_frames(ASSET_PATH, CHAR_WIDTH)
        self.current_popup = None
        self.job_id = None

        self.tray_icon = None
        self._setup_tray()

        # First reminder after the default interval
        self.schedule_next(DEFAULT_INTERVAL_MIN)

    # ---- scheduling ----
    def schedule_next(self, minutes):
        if self.job_id:
            self.root.after_cancel(self.job_id)
        self.job_id = self.root.after(minutes_to_ms(minutes), self.show_reminder)

    def show_reminder(self):
        self.current_popup = ReminderPopup(self)

    def remind_now(self):
        """Used by the tray menu's 'Remind Now' item, for testing."""
        self.root.after(0, self.show_reminder)

    # ---- system tray (optional, needs `pystray`) ----
    def _setup_tray(self):
        try:
            import pystray
            from PIL import Image as PILImage
        except ImportError:
            print("[HydroBuddy] Tip: `pip install pystray` for a system tray icon.")
            return

        icon_img = PILImage.open(ASSET_PATH).convert("RGBA").resize((64, 64))

        def on_quit(icon, item):
            icon.stop()
            self.root.after(0, self.root.destroy)

        def on_remind_now(icon, item):
            self.remind_now()

        menu = pystray.Menu(
            pystray.MenuItem("Remind me now", on_remind_now),
            pystray.MenuItem("Quit", on_quit),
        )
        self.tray_icon = pystray.Icon("HydroBuddy", icon_img, "Hydro Buddy", menu)

        import threading
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def run(self):
        self.root.mainloop()
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass


if __name__ == "__main__":
    app = HydroBuddyApp()
    app.run()
