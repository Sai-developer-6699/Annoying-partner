"""
pet_window.py
-------------
Borderless, always-on-top desktop pet avatar window.
Includes:
- overrideredirect(True) + topmost reassert loop
- Draggable window movement
- Dynamic, animated vector Canvas avatar reacting to expressions
- Speech bubble for roasts and blame lines
- Non-blocking pygame.mixer audio playback with fallback
- Embedded ComplimentBar widget
"""

import json
import logging
import math
import os
import random
import tkinter as tk
from pathlib import Path
from typing import Callable

from ui.compliment_bar import ComplimentBar

logger = logging.getLogger("pet_window")

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class PetWindow(tk.Toplevel):
    def __init__(
        self,
        root: tk.Tk,
        on_compliment_accepted: Callable[[str], None],
        on_compliment_rejected: Callable[[str, str], None],
        on_timer_expired: Callable[[], None],
        on_emergency_kill: Callable[[], None] | None = None,
        countdown_seconds: float = 15.0,
        debug: bool = False,
        no_audio: bool = False,
    ):
        super().__init__(root)
        self.root = root
        self.on_compliment_accepted = on_compliment_accepted
        self.on_compliment_rejected = on_compliment_rejected
        self.on_timer_expired = on_timer_expired
        self.on_emergency_kill = on_emergency_kill
        self.countdown_seconds = countdown_seconds
        self.debug = debug
        self.no_audio = no_audio

        self.expression = "smug"
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._nod_frames_remaining = 0
        self._nod_offset_y = 0
        self._is_blinking = False
        self.sprites = {}
        self.current_sprite_frame = 0
        self._current_photo = None
        self.bubble_photo = None

        self._init_window()
        self._init_audio()
        self._init_sprites()
        self._build_ui()
        self._start_animation_loops()

    def _init_window(self) -> None:
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.config(bg="#11111b", highlightthickness=0, bd=0)

        # Position in bottom-right corner with generous taskbar clearance
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        win_w = 420
        win_h = 570
        x = max(20, screen_w - win_w - 30)
        y = max(30, screen_h - win_h - 70)
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")

        # Reassert topmost periodically as specified in Section 3.1
        self._reassert_topmost()

        # Keyboard safety bindings (F12, Ctrl+Q, Ctrl+Alt+Shift+Q)
        for key in ("<F12>", "<Control-q>", "<Control-Q>", "<Control-Alt-Shift-Q>"):
            self.bind_all(key, lambda e: self._trigger_kill_switch())

    def _reassert_topmost(self) -> None:
        try:
            self.attributes("-topmost", True)
            self.lift()
        except Exception:
            pass
        self.after(2000, self._reassert_topmost)

    def _init_audio(self) -> None:
        self.audio_available = False
        if not self.no_audio:
            try:
                import pygame
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                self.audio_available = True
                logger.info("pygame.mixer initialized successfully.")
            except Exception as exc:
                logger.warning(f"Could not initialize pygame.mixer: {exc}")

    def _init_sprites(self) -> None:
        """Loads and caches character spritesheet and spacious comic speech bubble."""
        self.sprites = {}
        avatar_dir = PROJECT_ROOT / "assets" / "avatar"
        char_json = avatar_dir / "luna" / "character.json"
        sprite_png = avatar_dir / "luna" / "sprite.png"

        # Load spacious wide comic speech bubble
        bubble_file = avatar_dir / "bubble_spacious_clean.png"
        if not bubble_file.exists():
            bubble_file = avatar_dir / "bubble_clean.png"
        if not bubble_file.exists():
            bubble_file = avatar_dir / "bubble-to-enter-text.jpg"

        if bubble_file.exists():
            try:
                from PIL import Image, ImageTk
                b_img = Image.open(bubble_file)
                if b_img.mode != "RGBA":
                    b_img = b_img.convert("RGBA")
                target_w = 390
                target_h = int(target_w * (b_img.height / b_img.width))
                b_resized = b_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                self.bubble_photo = ImageTk.PhotoImage(b_resized)
                self.bubble_dims = (target_w, target_h)
                logger.info(f"Loaded and cached spacious comic speech bubble ({b_resized.size}).")
            except Exception as exc:
                logger.warning(f"Failed to load comic speech bubble image: {exc}")

        # Load Luna sprite frames (215x233 cached for instant startup and optimal screen fit)
        if char_json.exists() and sprite_png.exists():
            try:
                from PIL import Image, ImageTk
                data = json.loads(char_json.read_text(encoding="utf-8"))
                fw = data["frame"]["width"]
                fh = data["frame"]["height"]
                target_w, target_h = 215, 233

                cache_dir = avatar_dir / "luna" / "cache_215x233"
                cache_dir.mkdir(exist_ok=True)
                sheet = None

                for state_name, info in data.get("states", {}).items():
                    row = info["row"]
                    num_frames = info["frames"]
                    self.sprites[state_name] = []
                    for f in range(num_frames):
                        cache_file = cache_dir / f"{state_name}_{f}.png"
                        if cache_file.exists():
                            frame_img = Image.open(cache_file)
                        else:
                            if sheet is None:
                                sheet = Image.open(sprite_png)
                            box = (f * fw, row * fh, (f + 1) * fw, (row + 1) * fh)
                            cropped = sheet.crop(box)
                            frame_img = cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)
                            try:
                                frame_img.save(cache_file, "PNG")
                            except Exception:
                                pass
                        self.sprites[state_name].append(ImageTk.PhotoImage(frame_img))
                logger.info(f"Loaded {len(self.sprites)} sprite animation states ({target_w}x{target_h}) instantly from cache.")
            except Exception as exc:
                logger.warning(f"Failed to load sprite sheet: {exc}")
                self.sprites = {}

    def _build_ui(self) -> None:
        # 1. Drag Header
        self.title_bar = tk.Frame(self, bg="#181825", height=28)
        self.title_bar.pack(fill=tk.X)

        self.title_label = tk.Label(
            self.title_bar,
            text="👾 EGO-BOT 3000 • [DRAG ME]",
            font=("Segoe UI", 9, "bold"),
            fg="#cba6f7",
            bg="#181825",
        )
        self.title_label.pack(side=tk.LEFT, padx=12, pady=5)

        self.close_hint = tk.Label(
            self.title_bar,
            text="F12 / Ctrl+Q: Kill",
            font=("Segoe UI", 8, "bold"),
            fg="#f38ba8",
            bg="#181825",
        )
        self.close_hint.pack(side=tk.RIGHT, padx=12, pady=5)

        # Bind dragging on header and main window
        for w in (self.title_bar, self.title_label):
            w.bind("<Button-1>", self._start_drag)
            w.bind("<B1-Motion>", self._on_drag)

        # 2. Status HUD: Mood & AI badges
        self.bubble_meta_frame = tk.Frame(self, bg="#11111b")
        self.bubble_meta_frame.pack(fill=tk.X, padx=14, pady=(5, 0))

        self.bubble_state_label = tk.Label(
            self.bubble_meta_frame,
            text="👑 EGO: 85% • 🎭 MOOD: SMUG",
            font=("Segoe UI", 8, "bold"),
            fg="#f9e2af",
            bg="#11111b",
        )
        self.bubble_state_label.pack(side=tk.LEFT)

        self.bubble_ai_badge = tk.Label(
            self.bubble_meta_frame,
            text="🧠 PHI-3 ACTIVE",
            font=("Segoe UI", 7, "bold"),
            fg="#a6e3a1",
            bg="#11111b",
        )
        self.bubble_ai_badge.pack(side=tk.RIGHT)

        # 3. Action Subline (Explains pet posture & attitude, placed neatly in HUD)
        self.action_subline = tk.Label(
            self,
            text="▶ Current Action: Expectant Smirk (Waiting for flattery)",
            font=("Segoe UI", 8, "italic"),
            fg="#89b4fa",
            bg="#11111b",
            padx=10,
            pady=1,
        )
        self.action_subline.pack(fill=tk.X, pady=(2, 2))

        # 4. Spacious Clean Comic Speech Bubble Canvas (Tail points down directly to Luna)
        bw, bh = getattr(self, "bubble_dims", (390, 184))
        canvas_h = max(175, bh)
        self.bubble_canvas = tk.Canvas(
            self,
            width=420,
            height=canvas_h,
            bg="#11111b",
            highlightthickness=0,
            bd=0,
        )
        self.bubble_canvas.pack(fill=tk.X, pady=(0, 0))
        self.bubble_canvas.bind("<Button-1>", self._start_drag)
        self.bubble_canvas.bind("<B1-Motion>", self._on_drag)

        if self.bubble_photo:
            self.bubble_bg_id = self.bubble_canvas.create_image(
                210, canvas_h // 2, image=self.bubble_photo, anchor=tk.CENTER
            )

        text_cy = (canvas_h - 20) // 2
        self.bubble_text_id = self.bubble_canvas.create_text(
            210,
            text_cy,
            text="Praise my digital genius, human.\nYou have time.",
            font=("Segoe UI", 9, "bold"),
            fill="#11111b",
            width=330,
            justify=tk.CENTER,
        )

        # 5. Avatar Canvas (Centered cleanly below speech bubble)
        self.canvas_frame = tk.Frame(self, bg="#11111b", bd=0, highlightthickness=0)
        self.canvas_frame.pack(fill=tk.X, pady=0)

        self.canvas = tk.Canvas(
            self.canvas_frame,
            width=420,
            height=230,
            bg="#11111b",
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(anchor=tk.CENTER)
        self.canvas.bind("<Button-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._on_drag)

        # 6. Compliment Bar (Packed directly under avatar, 100% visible before timer expires)
        self.compliment_bar = ComplimentBar(
            self,
            on_accepted=self._handle_compliment_accepted,
            on_rejected=self._handle_compliment_rejected,
            on_expired=self._handle_timer_expired,
            countdown_seconds=self.countdown_seconds,
            debug=self.debug,
        )
        self.compliment_bar.pack(fill=tk.X, padx=4, pady=(2, 6))

        # Focus entry immediately so user can praise Luna right away
        try:
            self.compliment_bar.entry.focus_set()
        except Exception:
            pass

        self.draw_avatar()

    def _trigger_kill_switch(self) -> None:
        if self.on_emergency_kill:
            self.on_emergency_kill()
        else:
            import os
            os._exit(0)

    def _start_drag(self, event) -> None:
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_drag(self, event) -> None:
        x = self.winfo_x() + (event.x - self._drag_start_x)
        y = self.winfo_y() + (event.y - self._drag_start_y)
        self.geometry(f"+{x}+{y}")

    # --- Avatar Drawing & Animation ---
    def set_expression(self, expression: str, speech_text: str | None = None) -> None:
        self.expression = expression
        if speech_text:
            text_len = len(speech_text)
            if text_len <= 55:
                font_spec = ("Segoe UI", 10, "bold")
                wrap_w = 310
            elif text_len <= 110:
                font_spec = ("Segoe UI", 9, "bold")
                wrap_w = 325
            else:
                font_spec = ("Segoe UI", 8, "bold")
                wrap_w = 340

            if hasattr(self, "bubble_canvas") and hasattr(self, "bubble_text_id"):
                self.bubble_canvas.itemconfig(
                    self.bubble_text_id,
                    text=speech_text,
                    font=font_spec,
                    width=wrap_w,
                )
            if hasattr(self, "speech_bubble"):
                self.speech_bubble.config(text=speech_text)

        expr = expression.lower()
        action_map = {
            "smug": "Tsundere Proud (Arms crossed, smirking)",
            "smirk": "Smug Superiority (Expecting worship)",
            "grudging_respect": "Grudging Respect (Slight blush)",
            "furious": "Furious Pouting & Piercing Glare!",
            "disgusted": "Disgusted Grimace (Offended by mortal laziness)",
            "suspicious": "Piercing Suspicion (Detecting fraud)",
            "shocked": "Wide-Eyed Shock & Disbelief",
            "confused": "Confused Bafflement",
            "impressed": "Joyful Pride (Ego swell + Nods)",
            "disappointed": "Slumped Disappointment",
            "jumping": "Triumphant Leaping Celebration!",
            "idle": "Judicious Waiting (Tapping foot impatiently)",
        }
        action_desc = action_map.get(expr, f"Expressing {expression.title()}")
        if hasattr(self, "action_subline"):
            self.action_subline.config(text=f"▶ Current Action: {action_desc}")
        if hasattr(self, "bubble_state_label"):
            mood_colors = {
                "furious": "#f38ba8",
                "impressed": "#a6e3a1",
                "smug": "#cba6f7",
                "suspicious": "#f9e2af",
                "shocked": "#fab387",
            }
            color = mood_colors.get(expr, "#f9e2af")
            self.bubble_state_label.config(text=f"🎭 MOOD: {expression.upper()} • ⚡ STATE: ACTIVE", fg=color)

        self.draw_avatar()

    def trigger_nod(self) -> None:
        """Starts a rapid head nod animation on compliment accept."""
        self._nod_frames_remaining = 8
        self._animate_nod()

    def _animate_nod(self) -> None:
        if self._nod_frames_remaining > 0:
            # Oscillation
            self._nod_offset_y = int(6 * math.sin(self._nod_frames_remaining * 0.8))
            self._nod_frames_remaining -= 1
            self.draw_avatar()
            self.after(50, self._animate_nod)
        else:
            self._nod_offset_y = 0
            self.draw_avatar()

    def draw_avatar(self) -> None:
        self.canvas.delete("all")
        cx = 210
        cy = 115 + self._nod_offset_y

        if self.sprites:
            expr = self.expression.lower()
            if expr in ("smug", "smirk", "grudging_respect"):
                state = "tsundereProud"
            elif expr in ("furious", "disgusted", "unimpressed", "suspicious"):
                state = "tsundereAnnoyed"
            elif expr in ("shocked", "confused"):
                state = "surprised"
            elif expr in ("impressed", "laughing"):
                state = "happy"
            elif expr in ("disappointed", "bored"):
                state = "failed"
            elif expr in ("nodding", "jumping"):
                state = "jumping"
            else:
                state = "idle"

            frames = self.sprites.get(state) or self.sprites.get("idle", [])
            if frames:
                frame_idx = self.current_sprite_frame % len(frames)
                photo = frames[frame_idx]
                self._current_photo = photo
                self.canvas.create_image(cx, cy, image=photo, anchor=tk.CENTER)
                return

        # Fallback: Procedural Vector Avatar
        expr = self.expression.lower()
        if expr in ("furious", "disgusted", "shocked"):
            body_color = "#f38ba8"  # Angry red/pink
            eye_color = "#fab387"
            accent_color = "#e64553"
        elif expr in ("impressed", "laughing", "grudging_respect"):
            body_color = "#a6e3a1"  # Happy green
            eye_color = "#94e2d5"
            accent_color = "#40a02b"
        elif expr in ("suspicious", "confused", "unimpressed", "bored"):
            body_color = "#f9e2af"  # Suspicious yellow
            eye_color = "#89b4fa"
            accent_color = "#df8e1d"
        else:  # smirk, smug, normal
            body_color = "#cba6f7"  # Regal violet
            eye_color = "#89dceb"
            accent_color = "#b4befe"

        # Creature Horns / Antennae
        self.canvas.create_polygon(
            cx - 35, cy - 35,
            cx - 50, cy - 60,
            cx - 20, cy - 45,
            fill=accent_color, outline="",
        )
        self.canvas.create_polygon(
            cx + 35, cy - 35,
            cx + 50, cy - 60,
            cx + 20, cy - 45,
            fill=accent_color, outline="",
        )

        # Head / Body Oval
        self.canvas.create_oval(
            cx - 55, cy - 45,
            cx + 55, cy + 45,
            fill=body_color, outline=accent_color, width=3,
        )

        # Cheeks blush
        self.canvas.create_oval(cx - 48, cy + 6, cx - 32, cy + 18, fill=accent_color, outline="")
        self.canvas.create_oval(cx + 32, cy + 6, cx + 48, cy + 18, fill=accent_color, outline="")

        # Eyes
        eye_y = cy - 8
        left_eye_x = cx - 22
        right_eye_x = cx + 22

        if self._is_blinking:
            # Closed eyes (slits)
            self.canvas.create_line(left_eye_x - 12, eye_y, left_eye_x + 12, eye_y, fill="#11111b", width=3)
            self.canvas.create_line(right_eye_x - 12, eye_y, right_eye_x + 12, eye_y, fill="#11111b", width=3)
        elif expr in ("eye_roll",):
            # Eye roll looking up
            self.canvas.create_oval(left_eye_x - 12, eye_y - 12, left_eye_x + 12, eye_y + 12, fill="#ffffff", outline="#11111b", width=2)
            self.canvas.create_oval(right_eye_x - 12, eye_y - 12, right_eye_x + 12, eye_y + 12, fill="#ffffff", outline="#11111b", width=2)
            self.canvas.create_oval(left_eye_x - 4, eye_y - 10, left_eye_x + 4, eye_y - 2, fill="#11111b")
            self.canvas.create_oval(right_eye_x - 4, eye_y - 10, right_eye_x + 4, eye_y - 2, fill="#11111b")
        elif expr in ("suspicious", "unimpressed", "bored"):
            # Half-closed / squished eyes
            self.canvas.create_oval(left_eye_x - 12, eye_y - 6, left_eye_x + 12, eye_y + 6, fill="#ffffff", outline="#11111b", width=2)
            self.canvas.create_oval(right_eye_x - 12, eye_y - 6, right_eye_x + 12, eye_y + 6, fill="#ffffff", outline="#11111b", width=2)
            self.canvas.create_oval(left_eye_x - 4, eye_y - 4, left_eye_x + 4, eye_y + 4, fill="#11111b")
            self.canvas.create_oval(right_eye_x - 4, eye_y - 4, right_eye_x + 4, eye_y + 4, fill="#11111b")
        else:
            # Normal / Big eyes
            self.canvas.create_oval(left_eye_x - 14, eye_y - 14, left_eye_x + 14, eye_y + 14, fill="#ffffff", outline="#11111b", width=2)
            self.canvas.create_oval(right_eye_x - 14, eye_y - 14, right_eye_x + 14, eye_y + 14, fill="#ffffff", outline="#11111b", width=2)
            # Pupils
            self.canvas.create_oval(left_eye_x - 6, eye_y - 6, left_eye_x + 6, eye_y + 6, fill="#11111b")
            self.canvas.create_oval(right_eye_x - 6, eye_y - 6, right_eye_x + 6, eye_y + 6, fill="#11111b")
            # Eye highlights
            self.canvas.create_oval(left_eye_x - 4, eye_y - 4, left_eye_x, eye_y, fill="#ffffff")
            self.canvas.create_oval(right_eye_x - 4, eye_y - 4, right_eye_x, eye_y, fill="#ffffff")

        # Eyebrows
        brow_y = eye_y - 18
        if expr in ("furious",):
            self.canvas.create_line(left_eye_x - 14, brow_y - 4, left_eye_x + 12, brow_y + 6, fill="#11111b", width=3)
            self.canvas.create_line(right_eye_x - 12, brow_y + 6, right_eye_x + 14, brow_y - 4, fill="#11111b", width=3)
        elif expr in ("confused", "suspicious"):
            self.canvas.create_line(left_eye_x - 14, brow_y + 4, left_eye_x + 12, brow_y - 4, fill="#11111b", width=3)
            self.canvas.create_line(right_eye_x - 12, brow_y, right_eye_x + 14, brow_y, fill="#11111b", width=3)
        else:
            self.canvas.create_line(left_eye_x - 12, brow_y, left_eye_x + 12, brow_y, fill="#11111b", width=2)
            self.canvas.create_line(right_eye_x - 12, brow_y, right_eye_x + 12, brow_y, fill="#11111b", width=2)

        # Mouth
        mouth_y = cy + 20
        if expr in ("smirk", "smug"):
            self.canvas.create_arc(cx - 16, mouth_y - 10, cx + 22, mouth_y + 10, start=180, extent=160, style=tk.ARC, width=3, outline="#11111b")
        elif expr in ("laughing", "impressed"):
            self.canvas.create_chord(cx - 20, mouth_y - 8, cx + 20, mouth_y + 18, start=180, extent=180, fill="#f38ba8", outline="#11111b", width=2)
        elif expr in ("furious",):
            self.canvas.create_arc(cx - 20, mouth_y, cx + 20, mouth_y + 16, start=0, extent=180, style=tk.ARC, width=3, outline="#11111b")
        elif expr in ("shocked",):
            self.canvas.create_oval(cx - 10, mouth_y - 4, cx + 10, mouth_y + 16, fill="#11111b")
        elif expr in ("unimpressed", "bored"):
            self.canvas.create_line(cx - 16, mouth_y + 4, cx + 16, mouth_y + 4, fill="#11111b", width=3)
        else:
            self.canvas.create_arc(cx - 14, mouth_y - 6, cx + 14, mouth_y + 10, start=180, extent=180, style=tk.ARC, width=2, outline="#11111b")

    def _start_animation_loops(self) -> None:
        self._schedule_blink()
        if self.sprites:
            self._animate_sprite()

    def _animate_sprite(self) -> None:
        if self.sprites:
            self.current_sprite_frame += 1
            self.draw_avatar()
        self.after(340, self._animate_sprite)

    def _schedule_blink(self) -> None:
        delay = random.randint(2500, 5500)
        self.after(delay, self._blink)

    def _blink(self) -> None:
        self._is_blinking = True
        self.draw_avatar()
        self.after(140, self._unblink)

    def _unblink(self) -> None:
        self._is_blinking = False
        self.draw_avatar()
        self._schedule_blink()

    # --- Sound Playback ---
    def play_meme_audio(
        self,
        audio_path: str | None,
        max_duration: float = 2.2,
        on_complete: Callable[[], None] | None = None,
    ) -> None:
        """
        Plays meme sound effect without blocking.
        Fades out long clips after max_duration so speech isn't delayed.
        Invokes on_complete callback when the sound finish/fade completes so voice speech
        can follow without any clashing.
        """
        if self.no_audio or not self.audio_available:
            if on_complete:
                self.after(50, on_complete)
            return

        if audio_path:
            full_path = PROJECT_ROOT / audio_path if not os.path.isabs(audio_path) else Path(audio_path)
            if full_path.exists():
                try:
                    import pygame
                    sound = pygame.mixer.Sound(str(full_path))
                    sound.play()
                    dur = sound.get_length()
                    logger.info(f"Playing audio: {full_path} (length={dur:.2f}s, max_cap={max_duration:.2f}s)")

                    if dur > max_duration:
                        fade_ms = int(max_duration * 1000)
                        self.after(fade_ms, lambda: sound.fadeout(350))
                        finish_delay = fade_ms + 380
                    else:
                        finish_delay = int(dur * 1000) + 120

                    if on_complete:
                        self.after(finish_delay, on_complete)
                    return
                except Exception as exc:
                    logger.warning(f"Failed to play audio '{full_path}': {exc}")

        # Fallback chime if audio file is not found (e.g. before scrape)
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass

        if on_complete:
            self.after(250, on_complete)

    def show_meme_card(self, meme_id: str, title: str, caption: str, duration_ms: int = 12000) -> None:
        """Displays a floating visual punchline meme card towards screen centre for >10s."""
        try:
            from ui.meme_popup import show_meme_card
            x = self.winfo_x()
            y = self.winfo_y()
            show_meme_card(self, meme_id=meme_id, title=title, caption=caption, pet_x=x, pet_y=y, duration_ms=duration_ms)
        except Exception as exc:
            logger.warning(f"Could not show meme card: {exc}")

    # --- Internal Event Handlers ---
    def _handle_compliment_accepted(self, text: str) -> None:
        self.set_expression("impressed", "Delicious compliment! My superiority grows! ✨")
        self.trigger_nod()
        self.on_compliment_accepted(text)

    def _handle_compliment_rejected(self, reason: str, blame_line: str) -> None:
        expr = "suspicious" if reason in ("too_fast", "pasted") else "furious"
        self.set_expression(expr, blame_line)

        # On severe offenses (lazy copy-paste or repetitive spam), trigger a mini 3s mouse evasion
        if reason in ("pasted", "repeat"):
            try:
                from system.mouse_lock import start_mouse_freeze_thread
                start_mouse_freeze_thread(duration=3.0, mode="inverted_mouse", debug=self.debug)
                logger.info("Triggered 3s mini inverted-mouse evasion for severe compliment offence.")
            except Exception as exc:
                logger.warning(f"Could not trigger mini mouse evasion: {exc}")

        self.on_compliment_rejected(reason, blame_line)

    def _handle_timer_expired(self) -> None:
        self.set_expression("furious", "YOU DARED TO STARVE MY EGO?!")
        self.on_timer_expired()
