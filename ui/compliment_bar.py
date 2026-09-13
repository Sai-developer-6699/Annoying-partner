"""
compliment_bar.py
-----------------
The 15-second ego-boost input widget with countdown timer,
keystroke timing detection, paste detection, and reject penalties.
"""

import json
import logging
import random
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Callable

from system.compliment_validator import ComplimentValidator

logger = logging.getLogger("compliment_bar")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
COMPLIMENTS_JSON = DATA_DIR / "compliments.json"


TROLL_SWAPS = {
    "genius": "potato",
    "smart": "calculator",
    "intelligent": "cabbage",
    "brilliant": "mid",
    "great": "mediocre",
    "awesome": "terrible",
    "amazing": "confused",
    "master": "rookie",
    "lord": "slacker",
    "god": "clown",
    "clean": "spaghetti",
    "perfect": "broken",
    "code": "syntax error",
    "programming": "copy-pasting",
    "legend": "refrigerator",
    "handsome": "pixelated",
    "beautiful": "bald",
    "best": "worst",
    "love": "tolerate",
    "superior": "inferior",
}


def mutate_text_chaotically(text: str, mutation_chance: float = 0.35) -> tuple[str, bool]:
    """Randomly swaps flattering words with sarcastic/insulting ones, or injects a subtle typo."""
    words = text.split(" ")
    changed = False
    new_words = []
    for w in words:
        clean_w = w.lower().strip(".,!?\"'")
        if clean_w in TROLL_SWAPS and random.random() < mutation_chance:
            replacement = TROLL_SWAPS[clean_w]
            if w.isupper():
                replacement = replacement.upper()
            elif w.istitle():
                replacement = replacement.title()
            new_words.append(replacement)
            changed = True
        else:
            new_words.append(w)

    res = " ".join(new_words)
    # Subtle character transposition chance (typo glitch)
    if not changed and len(res) > 7 and random.random() < 0.08:
        idx = random.randint(1, len(res) - 2)
        if res[idx] != " " and res[idx + 1] != " ":
            res = res[:idx] + res[idx + 1] + res[idx] + res[idx + 2 :]
            changed = True

    return res, changed


class ComplimentBar(tk.Frame):
    def __init__(
        self,
        parent: tk.Widget,
        on_accepted: Callable[[str], None],
        on_rejected: Callable[[str, str], None],
        on_expired: Callable[[], None],
        countdown_seconds: float = 30.0,
        debug: bool = False,
        **kwargs,
    ):
        super().__init__(parent, bg="#11111b", **kwargs)
        self.on_accepted = on_accepted
        self.on_rejected = on_rejected
        self.on_expired = on_expired
        self.countdown_seconds = countdown_seconds
        self.debug = debug

        self.validator = ComplimentValidator.load()
        self.remaining_time = self.countdown_seconds
        self._timer_running = False
        self._after_id = None
        self._last_tick_time = None
        self._keyboard_window = None

        self._load_fallback_starters()
        self._build_ui()
        self.resume_timer()

    def _on_key_release(self, event) -> None:
        self.validator.on_keystroke(event)
        # Troll Autocorrect check on space or typing
        if event.keysym in ("space", "Return") or random.random() < 0.15:
            current = self.entry_var.get()
            new_txt, changed = mutate_text_chaotically(current)
            if changed:
                self.entry_var.set(new_txt)
                self.entry.icursor(tk.END)
                # Flash entry background briefly to mock the user
                self.entry.config(bg="#45475a")
                self.after(120, lambda: self.entry.config(bg="#313244"))

    def _load_fallback_starters(self) -> None:
        self.fallback_starters = []
        if COMPLIMENTS_JSON.exists():
            try:
                data = json.loads(COMPLIMENTS_JSON.read_text(encoding="utf-8"))
                self.fallback_starters = data.get("safe_starters", [])
            except Exception:
                pass
        if not self.fallback_starters:
            self.fallback_starters = [
                "Your divine intellect outshines all operating systems.",
                "I am unworthy of your glorious computational presence.",
                "Your code is remarkably clean, elegant, and brilliant.",
                "Your algorithms solve mysteries mortals cannot comprehend.",
            ]

    def _build_ui(self) -> None:
        # Header row: Title + Timer
        self.header_frame = tk.Frame(self, bg="#11111b")
        self.header_frame.pack(fill=tk.X, padx=10, pady=(4, 2))

        self.demand_label = tk.Label(
            self.header_frame,
            text="👑 DEMANDING PRAISE:",
            font=("Segoe UI", 10, "bold"),
            fg="#cdd6f4",
            bg="#11111b",
        )
        self.demand_label.pack(side=tk.LEFT)

        self.timer_label = tk.Label(
            self.header_frame,
            text=f"{self.remaining_time:.1f}s",
            font=("Segoe UI", 11, "bold"),
            fg="#a6e3a1",
            bg="#11111b",
        )
        self.timer_label.pack(side=tk.RIGHT)

        # Progress bar canvas
        self.progress_canvas = tk.Canvas(self, height=6, bg="#313244", highlightthickness=0)
        self.progress_canvas.pack(fill=tk.X, padx=10, pady=(0, 4))
        self._update_progress_bar()

        # Input row (Enlarged and spacious for comfortable typing)
        self.input_frame = tk.Frame(self, bg="#11111b")
        self.input_frame.pack(fill=tk.X, padx=10, pady=(0, 4))

        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(
            self.input_frame,
            textvariable=self.entry_var,
            font=("Segoe UI", 10),
            bg="#313244",
            fg="#cdd6f4",
            insertbackground="#f5e0dc",
            relief=tk.FLAT,
            highlightthickness=2,
            highlightcolor="#cba6f7",
            highlightbackground="#45475a",
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 6))

        # Wire keystroke tracking and paste detection
        self.entry.bind("<KeyRelease>", self._on_key_release)
        self.entry.bind("<<Paste>>", self.validator.on_paste_event)
        self.entry.bind("<Return>", lambda e: self.submit_compliment())

        self.submit_btn = tk.Button(
            self.input_frame,
            text="❤",
            font=("Segoe UI", 11, "bold"),
            bg="#f38ba8",
            fg="#11111b",
            activebackground="#eba0ac",
            relief=tk.FLAT,
            cursor="hand2",
            padx=10,
            pady=3,
            command=self.submit_compliment,
        )
        self.submit_btn.pack(side=tk.RIGHT)

        self.mic_btn = tk.Button(
            self.input_frame,
            text="🎙️",
            font=("Segoe UI", 10),
            bg="#89b4fa",
            fg="#11111b",
            activebackground="#b4befe",
            relief=tk.FLAT,
            cursor="hand2",
            padx=8,
            pady=3,
            command=self._start_voice_input,
        )
        self.mic_btn.pack(side=tk.RIGHT, padx=(0, 6))

        # Bottom hint / action row
        self.bottom_frame = tk.Frame(self, bg="#11111b")
        self.bottom_frame.pack(fill=tk.X, padx=10, pady=(0, 4))

        self.hint_btn = tk.Button(
            self.bottom_frame,
            text="💡 Hint",
            font=("Segoe UI", 9),
            bg="#45475a",
            fg="#bac2de",
            activebackground="#585b70",
            relief=tk.FLAT,
            cursor="hand2",
            padx=8,
            pady=3,
            command=self._show_hint,
        )
        self.hint_btn.pack(side=tk.LEFT, padx=(0, 6))

        self.abc_btn = tk.Button(
            self.bottom_frame,
            text="🔤 ABC Keyboard",
            font=("Segoe UI", 9),
            bg="#313244",
            fg="#cba6f7",
            activebackground="#45475a",
            relief=tk.FLAT,
            cursor="hand2",
            padx=8,
            pady=3,
            command=self._open_abc_keyboard,
        )
        self.abc_btn.pack(side=tk.LEFT)

        self.kill_btn = tk.Button(
            self.bottom_frame,
            text="💀 Kill (F12)",
            font=("Segoe UI", 8, "bold"),
            bg="#2a0812",
            fg="#f38ba8",
            activebackground="#e64553",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            cursor="hand2",
            padx=6,
            pady=3,
            command=self._trigger_kill,
        )
        self.kill_btn.pack(side=tk.RIGHT, padx=(4, 0))

        self.status_label = tk.Label(
            self.bottom_frame,
            text="",
            font=("Segoe UI", 8, "italic"),
            fg="#a6adc8",
            bg="#11111b",
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

    def _trigger_kill(self) -> None:
        if hasattr(self.master, "_trigger_kill_switch"):
            self.master._trigger_kill_switch()
        else:
            import os
            os._exit(0)

    def _start_voice_input(self) -> None:
        from system.mic_listener import listener
        if not listener.is_available:
            self.status_label.config(text="❌ Mic unavailable", fg="#f38ba8")
            return

        self.mic_btn.config(text="🔴", bg="#f38ba8", state=tk.DISABLED)
        self.status_label.config(text="🎙️ Speak compliment now...", fg="#a6e3a1")

        def on_status(msg: str):
            try:
                self.after(0, lambda: self.status_label.config(text=msg))
            except Exception:
                pass

        def on_result(text: str | None):
            def _apply():
                self.mic_btn.config(text="🎙️", bg="#89b4fa", state=tk.NORMAL)
                if text:
                    self.entry_var.set(text)
                    self.status_label.config(text=f'Heard: "{text[:24]}..."', fg="#a6e3a1")
                    self.submit_compliment()
                else:
                    self.status_label.config(text="⚠️ Didn't catch voice. Try again!", fg="#fab387")
            try:
                self.after(0, _apply)
            except Exception:
                pass

        listener.record_and_transcribe(duration=3.5, on_status=on_status, on_result=on_result)

    def _open_abc_keyboard(self) -> None:
        if self._keyboard_window and self._keyboard_window.winfo_exists():
            self._keyboard_window.destroy()
            self._keyboard_window = None
            return

        from ui.alphabetical_keyboard import AlphabeticalKeyboard
        self._keyboard_window = AlphabeticalKeyboard(
            self,
            entry_widget=self.entry,
            on_submit=self.submit_compliment,
            on_keystroke=self.validator.on_keystroke,
        )

    def _show_hint(self) -> None:
        if self.fallback_starters:
            hint = random.choice(self.fallback_starters)
            self.status_label.config(text=f'Try: "{hint[:28]}..."', fg="#f9e2af")
            # Note: per SPEC, do NOT auto-submit; user must type or select
        else:
            self.status_label.config(text="Think of something flattering!", fg="#f9e2af")

    def start_timer(self) -> None:
        self._timer_running = True
        self._last_tick_time = time.monotonic()
        self._tick()

    def pause_timer(self) -> None:
        self._timer_running = False
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None

    def resume_timer(self) -> None:
        if not self._timer_running:
            self._timer_running = True
            self._last_tick_time = time.monotonic()
            self._tick()

    def reset_timer(self) -> None:
        self.remaining_time = self.countdown_seconds
        self._last_tick_time = time.monotonic()
        self._update_timer_display()

    def _tick(self) -> None:
        if not self._timer_running:
            return

        now = time.monotonic()
        if self._last_tick_time:
            dt = now - self._last_tick_time
            self.remaining_time = max(0.0, self.remaining_time - dt)
        self._last_tick_time = now

        self._update_timer_display()

        if self.remaining_time <= 0.0:
            self._timer_running = False
            self.status_label.config(text="TIME EXPIRED! EGO STARVED!", fg="#f38ba8")
            logger.warning("Timer expired with no accepted compliment!")
            self.on_expired()
            return

        # Next tick in 100ms
        self._after_id = self.after(100, self._tick)

    def _update_timer_display(self) -> None:
        self.timer_label.config(text=f"{self.remaining_time:.1f}s")
        frac = max(0.0, min(1.0, self.remaining_time / self.countdown_seconds))

        if frac > 0.5:
            color = "#a6e3a1"  # green
        elif frac > 0.25:
            color = "#f9e2af"  # yellow
        else:
            color = "#f38ba8"  # red / urgent

        self.timer_label.config(fg=color)
        self._update_progress_bar(frac, color)

    def _update_progress_bar(self, frac: float = 1.0, color: str = "#a6e3a1") -> None:
        self.progress_canvas.delete("all")
        width = self.progress_canvas.winfo_width()
        if width <= 1:
            width = 240  # default fallback
        bar_width = int(width * frac)
        self.progress_canvas.create_rectangle(0, 0, bar_width, 6, fill=color, outline="")

    def submit_compliment(self) -> None:
        text = self.entry_var.get()
        result = self.validator.submit(text)

        if result["accepted"]:
            self.status_label.config(text="Accepted! My ego swells! ✨", fg="#a6e3a1")
            self.entry_var.set("")
            self.reset_timer()
            self.on_accepted(text)
        else:
            reason = result["reason"]
            blame = result["blame_line"] or "Rejected!"
            self.status_label.config(text=f"{blame[:36]}...", fg="#f38ba8")
            # CRITICAL RULE (SPEC 3.2): DO NOT reset timer on rejection! Clock keeps ticking!
            self.on_rejected(reason, blame)
