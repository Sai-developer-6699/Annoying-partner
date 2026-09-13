"""
punishment_screen.py
--------------------
Fullscreen lock UI for:
1. Persuasion Game (3.4a): Plead your case before the AI Judge.
2. Compulsory Punishment (3.4b): Savage meme screen + 30s mouse freeze.
"""

import logging
import threading
import time
import tkinter as tk
from pathlib import Path
from typing import Callable

from ai.prompts import ask_judge
from system.mouse_lock import freeze_mouse

logger = logging.getLogger("punishment_screen")

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class PunishmentScreen(tk.Toplevel):
    def __init__(
        self,
        root: tk.Tk,
        mode: str,  # "persuasion" or "compulsory"
        trigger: str,
        app_hint: str | None,
        meme_scenario: dict,
        meme_option: dict,
        on_resolved: Callable[[bool], None],
        pet_reply: str | None = None,
        debug: bool = False,
        no_audio: bool = False,
    ):
        super().__init__(root)
        self.root = root
        self.mode = mode
        self.trigger = trigger
        self.app_hint = app_hint
        self.meme_scenario = meme_scenario
        self.meme_option = meme_option
        self.on_resolved = on_resolved
        self.pet_reply = pet_reply
        self.debug = debug
        self.no_audio = no_audio

        self._abort_event = threading.Event()
        self._mouse_lock_thread = None
        self._resolved = False

        self._init_window()
        self._build_ui()
        self._play_meme_audio()

        if self.mode == "compulsory":
            self._start_compulsory_lock()

    def _init_window(self) -> None:
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.config(bg="#11111b")

        # Fullscreen bounds
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        self.geometry(f"{screen_w}x{screen_h}+0+0")
        self.lift()
        self.focus_force()

        # Keyboard safety bindings (F12, Ctrl+Q, Escape, Ctrl+Alt+Shift+Q)
        for key in ("<F12>", "<Control-q>", "<Control-Q>", "<Control-Alt-Shift-Q>"):
            self.bind_all(key, lambda e: self.emergency_dismiss())
        self.bind("<Escape>", lambda e: self.emergency_dismiss())

        self._reassert_topmost()

    def _reassert_topmost(self) -> None:
        if self._resolved:
            return
        try:
            self.attributes("-topmost", True)
            self.lift()
        except Exception:
            pass
        self.after(1000, self._reassert_topmost)

    def _play_meme_audio(self) -> None:
        audio_file = self.meme_option.get("audio_file")
        if self.no_audio or not audio_file:
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONHAND)
            except Exception:
                pass
            return

        full_path = PROJECT_ROOT / audio_file if not Path(audio_file).is_absolute() else Path(audio_file)
        if full_path.exists():
            try:
                import pygame
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                pygame.mixer.Sound(str(full_path)).play()
            except Exception as exc:
                logger.warning(f"Failed to play punishment audio: {exc}")

    def _build_ui(self) -> None:
        # Main center container
        self.center_frame = tk.Frame(self, bg="#181825", padx=30, pady=25, relief=tk.RIDGE, bd=2)
        self.center_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Emergency escape info at top-right
        self.esc_label = tk.Label(
            self,
            text="Emergency Kill: F12 / Ctrl+Q / Esc",
            font=("Segoe UI", 9, "bold"),
            fg="#f38ba8",
            bg="#11111b",
        )
        self.esc_label.place(relx=0.98, rely=0.02, anchor=tk.NE)

        # Header Icon + Title
        icon_text = "⚖️" if self.mode == "persuasion" else "🚨"
        title_text = "THE TRIBUNAL IS IN SESSION" if self.mode == "persuasion" else "COMPULSORY PUNISHMENT"
        title_color = "#f38ba8" if self.mode == "compulsory" else "#fab387"

        self.title_label = tk.Label(
            self.center_frame,
            text=f"{icon_text}  {title_text}  {icon_text}",
            font=("Impact", 24),
            fg=title_color,
            bg="#181825",
        )
        self.title_label.pack(pady=(0, 10))

        # Offense banner
        app_info = f" (Target App: {self.app_hint})" if self.app_hint else ""
        offense_str = f"Offense: [{self.trigger.upper()}]{app_info}"
        self.offense_label = tk.Label(
            self.center_frame,
            text=offense_str,
            font=("Segoe UI", 11, "bold"),
            fg="#cdd6f4",
            bg="#313244",
            padx=12,
            pady=4,
        )
        self.offense_label.pack(fill=tk.X, pady=(0, 12))

        # Meme caption banner + dynamic pet roast
        intensity = self.meme_option.get("intensity", "mild").upper()
        display_lines = []
        if self.pet_reply:
            display_lines.append(f'"{self.pet_reply}"')
        meme_caption = self.meme_option.get("caption")
        if meme_caption and meme_caption != self.pet_reply:
            display_lines.append(f"Clip: {meme_caption}")
        if not display_lines:
            display_lines.append('"Slacking off detected! Face judgment!"')

        banner_text = "\n".join(display_lines) + f"\n[{intensity} INTENSITY REACTION]"
        self.caption_label = tk.Label(
            self.center_frame,
            text=banner_text,
            font=("Segoe UI", 12, "italic"),
            fg="#f9e2af",
            bg="#181825",
            wraplength=520,
            justify=tk.CENTER,
        )
        self.caption_label.pack(pady=(0, 15))

        if self.mode == "persuasion":
            self._build_persuasion_ui()
        else:
            self._build_compulsory_ui()

        # Debug emergency dismiss button
        if self.debug:
            self.debug_btn = tk.Button(
                self.center_frame,
                text="[DEBUG] Instant Dismiss",
                font=("Segoe UI", 8),
                bg="#45475a",
                fg="#bac2de",
                command=self.emergency_dismiss,
            )
            self.debug_btn.pack(pady=(12, 0))

    def _build_persuasion_ui(self) -> None:
        self.prompt_label = tk.Label(
            self.center_frame,
            text="Convince the Judge why you deserve to keep using your computer.\nOne chance. Be specific. No lazy excuses.",
            font=("Segoe UI", 10),
            fg="#bac2de",
            bg="#181825",
            justify=tk.CENTER,
        )
        self.prompt_label.pack(pady=(0, 10))

        self.excuse_text = tk.Text(
            self.center_frame,
            width=50,
            height=4,
            font=("Segoe UI", 11),
            bg="#313244",
            fg="#cdd6f4",
            insertbackground="#f5e0dc",
            relief=tk.FLAT,
            padx=8,
            pady=8,
            wrap=tk.WORD,
        )
        self.excuse_text.pack(pady=(0, 10))
        self.excuse_text.focus_set()

        self.verdict_label = tk.Label(
            self.center_frame,
            text="",
            font=("Segoe UI", 11, "bold"),
            fg="#f38ba8",
            bg="#181825",
        )
        self.verdict_label.pack(pady=(0, 10))

        # Action Buttons: Mic Voice Speak + Plead Button
        self.btn_row = tk.Frame(self.center_frame, bg="#181825")
        self.btn_row.pack(pady=(0, 4))

        self.mic_btn = tk.Button(
            self.btn_row,
            text="🎙️ Speak Excuse (Mic)",
            font=("Segoe UI", 10, "bold"),
            bg="#89b4fa",
            fg="#11111b",
            activebackground="#b4befe",
            relief=tk.FLAT,
            cursor="hand2",
            padx=12,
            pady=6,
            command=self._start_mic_excuse,
        )
        self.mic_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.submit_btn = tk.Button(
            self.btn_row,
            text="⚖️ PLEAD CASE TO THE JUDGE",
            font=("Segoe UI", 10, "bold"),
            bg="#cba6f7",
            fg="#11111b",
            activebackground="#b4befe",
            relief=tk.FLAT,
            cursor="hand2",
            padx=14,
            pady=6,
            command=self._submit_excuse,
        )
        self.submit_btn.pack(side=tk.LEFT)

    def _start_mic_excuse(self) -> None:
        from system.mic_listener import listener
        if not listener.is_available:
            self.verdict_label.config(text="❌ Microphone libraries not available", fg="#f38ba8")
            return

        self.mic_btn.config(text="🔴 Recording (4s)...", bg="#f38ba8", state=tk.DISABLED)
        self.verdict_label.config(text="🎙️ Speak your excuse clearly to the Judge...", fg="#a6e3a1")

        def on_status(msg: str):
            try:
                self.after(0, lambda: self.verdict_label.config(text=msg))
            except Exception:
                pass

        def on_result(text: str | None):
            def _apply():
                self.mic_btn.config(text="🎙️ Speak Excuse (Mic)", bg="#89b4fa", state=tk.NORMAL)
                if text:
                    self.excuse_text.delete("1.0", tk.END)
                    self.excuse_text.insert("1.0", text)
                    self._submit_excuse()
                else:
                    self.verdict_label.config(text="⚠️ Could not hear excuse. Type or try again!", fg="#fab387")
            try:
                self.after(0, _apply)
            except Exception:
                pass

        listener.record_and_transcribe(duration=4.5, on_status=on_status, on_result=on_result)

    def _build_compulsory_ui(self) -> None:
        self.lock_status_label = tk.Label(
            self.center_frame,
            text="MOUSE CURSOR LOCKED FOR 30 SECONDS",
            font=("Impact", 16),
            fg="#f38ba8",
            bg="#181825",
        )
        self.lock_status_label.pack(pady=(10, 8))

        self.countdown_label = tk.Label(
            self.center_frame,
            text="30.0s",
            font=("Segoe UI", 24, "bold"),
            fg="#f9e2af",
            bg="#181825",
        )
        self.countdown_label.pack(pady=(0, 10))

        self.warning_note = tk.Label(
            self.center_frame,
            text="Contemplate your work habits while the cursor is incapacitated.",
            font=("Segoe UI", 9, "italic"),
            fg="#a6adc8",
            bg="#181825",
        )
        self.warning_note.pack()

    def _submit_excuse(self) -> None:
        excuse = self.excuse_text.get("1.0", tk.END).strip()
        if not excuse:
            self.verdict_label.config(text="Silence is not an argument. Try harder.", fg="#f38ba8")
            return

        self.submit_btn.config(state=tk.DISABLED, text="The Judge is deliberating...")
        self.verdict_label.config(text="Pondering your worthiness...", fg="#f9e2af")
        self.update_idletasks()

        # Judge deliberation thread
        def judge_worker():
            passed = ask_judge(excuse)
            self.after(0, lambda: self._on_judge_verdict(passed))

        threading.Thread(target=judge_worker, daemon=True).start()

    def _on_judge_verdict(self, passed: bool) -> None:
        if not self.no_audio:
            try:
                import pygame
                import random
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                if passed:
                    sound_file = PROJECT_ROOT / "assets" / "audio" / "applause.mp3"
                else:
                    fail_sound = random.choice(["emotional_damage.mp3", "directed_by_robert_b_weide.mp3", "suraj_dhamu.mp3", "wasted.mp3"])
                    sound_file = PROJECT_ROOT / "assets" / "audio" / fail_sound
                if sound_file.exists():
                    pygame.mixer.Sound(str(sound_file)).play()
            except Exception:
                pass

        if passed:
            self.verdict_label.config(
                text="VERDICT: [PASS] — The Judge is merciful. Back to work!",
                fg="#a6e3a1",
            )
            self.after(1600, lambda: self._close_and_resolve(True))
        else:
            self.verdict_label.config(
                text="VERDICT: [FAIL] — Pathetic excuse! Dropping into COMPULSORY LOCKOUT!",
                fg="#f38ba8",
            )
            # Switch to compulsory mode
            self.after(1800, self._escalate_to_compulsory)

    def _escalate_to_compulsory(self) -> None:
        # Rebuild UI as compulsory
        for widget in self.center_frame.winfo_children():
            widget.destroy()

        self.mode = "compulsory"
        self.title_label = tk.Label(
            self.center_frame,
            text="🚨  COMPULSORY LOCKOUT  🚨",
            font=("Impact", 24),
            fg="#f38ba8",
            bg="#181825",
        )
        self.title_label.pack(pady=(0, 10))

        self.caption_label = tk.Label(
            self.center_frame,
            text="Persuasion failed! Suffer the timeout!",
            font=("Segoe UI", 12, "italic"),
            fg="#f9e2af",
            bg="#181825",
        )
        self.caption_label.pack(pady=(0, 15))

        self._build_compulsory_ui()
        self._start_compulsory_lock()

    def _start_compulsory_lock(self) -> None:
        import random
        # Prioritize inverted mouse controls (60% likelihood)
        self.chaos_mode = random.choices(["inverted_mouse", "cursor_gravity", "corner_freeze"], weights=[0.6, 0.2, 0.2])[0]

        # Inverted cursor punishment is set to 15.0s
        if self.chaos_mode == "inverted_mouse":
            duration = 15.0
        else:
            duration = 5.0 if self.debug else 15.0

        start_time = time.monotonic()

        if hasattr(self, "lock_status_label"):
            if self.chaos_mode == "inverted_mouse":
                self.lock_status_label.config(text="⚠️ INVERTED MOUSE CONTROLS ENGAGED (15s Penalty) ⚠️")
            elif self.chaos_mode == "cursor_gravity":
                self.lock_status_label.config(text="⚠️ CURSOR GRAVITY ENGAGED (Mouse Dragged Down) ⚠️")
            else:
                self.lock_status_label.config(text="🚨 MOUSE CURSOR PINNED TO CORNER 🚨")

        # Start mouse freeze / chaos thread
        def freeze_worker():
            freeze_mouse(
                duration=duration,
                debug=self.debug,
                abort_event=self._abort_event,
                mode=self.chaos_mode,
            )

        self._mouse_lock_thread = threading.Thread(target=freeze_worker, daemon=True)
        self._mouse_lock_thread.start()

        # Tick countdown on UI
        def update_countdown():
            if self._resolved or self._abort_event.is_set():
                return
            remaining = max(0.0, duration - (time.monotonic() - start_time))
            self.countdown_label.config(text=f"{remaining:.1f}s")
            if remaining <= 0.0:
                self._close_and_resolve(False)
            else:
                self.after(100, update_countdown)

        update_countdown()

    def emergency_dismiss(self) -> None:
        logger.warning("Punishment screen dismissed via emergency escape.")
        self._abort_event.set()
        self._close_and_resolve(False)

    def _close_and_resolve(self, passed: bool) -> None:
        if self._resolved:
            return
        self._resolved = True
        self._abort_event.set()
        try:
            self.destroy()
        except Exception:
            pass
        self.on_resolved(passed)
