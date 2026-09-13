"""
meme_popup.py
-------------
A floating, borderless meme visual card popup that appears beside the pet
avatar whenever a hilarious meme reaction or roast fires.
Displays meme title badges, quotes, and reactions synchronized with audio.
"""

import logging
import tkinter as tk
from typing import Optional

logger = logging.getLogger("meme_popup")

MEME_BADGES = {
    "faah": ("💥 FAAAAH! (FAHADH FAASIL / AAVESHAM)", "#f38ba8"),
    "emotional_damage": ("💔 EMOTIONAL DAMAGE!", "#f38ba8"),
    "bruh": ("😐 BRUH MOMENT", "#f9e2af"),
    "salim_kumar": ("🌴 SALIM KUMAR COMEDY", "#89b4fa"),
    "suraj_dhamu": ("🎬 DASHAMOOLAM DAMU", "#fab387"),
    "jagathy_comedy": ("😂 JAGATHY SREEKUMAR", "#a6e3a1"),
    "fbi_open_up": ("🚨 FBI OPEN UP!", "#f38ba8"),
    "giga_chad": ("👑 GIGA CHAD SUPREMACY", "#cba6f7"),
    "directed_by_robert_b_weide": ("🎺 DIRECTED BY ROBERT B. WEIDE", "#f9e2af"),
    "windows_error": ("⚠️ FATAL ERROR 404", "#f38ba8"),
    "bonk": ("🐕 BONK! SLACKER DETENTION", "#fab387"),
    "wasted": ("☠️ GTA V: WASTED", "#f38ba8"),
    "thunder": ("⚡ FULL ANGRY THUNDERSTRIKE", "#89dceb"),
    "run_vine": ("🏃 RUN! DEADLINE PANIC", "#fab387"),
    "metal_pipe": ("🔊 CHAOTIC METAL PIPE CLANG", "#cdd6f4"),
    "victory_fanfare": ("🎺 FINAL FANTASY LEVEL UP", "#a6e3a1"),
    "applause": ("👏 STANDING OVATION", "#a6e3a1"),
    "nope_tf2": ("🚫 ENGINEER: NOPE", "#f38ba8"),
    "aughhh": ("😫 PHYSICAL AGONY", "#fab387"),
    "oof": ("🧱 ROBLOX OOF", "#f9e2af"),
    "rick_roll": ("🕺 NEVER GONNA GIVE YOU UP", "#cba6f7"),
}


class MemeCardPopup(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Widget,
        meme_id: str,
        title: str,
        caption: str,
        pet_x: int = 0,
        pet_y: int = 0,
        duration_ms: int = 12000,
    ):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.config(bg="#11111b")

        self._drag_start_x = 0
        self._drag_start_y = 0

        badge_text, badge_color = MEME_BADGES.get(meme_id, (f"✨ {title.upper()}", "#cba6f7"))

        # Card container frame (Bold punchy glowing border)
        self.card = tk.Frame(
            self,
            bg="#181825",
            highlightbackground=badge_color,
            highlightcolor=badge_color,
            highlightthickness=3,
            padx=18,
            pady=14,
        )
        self.card.pack(fill=tk.BOTH, expand=True)

        # Header: Badge + Close Hint
        self.top_row = tk.Frame(self.card, bg="#181825")
        self.top_row.pack(fill=tk.X, pady=(0, 8))

        self.badge_label = tk.Label(
            self.top_row,
            text=badge_text,
            font=("Segoe UI", 10, "bold"),
            fg="#11111b",
            bg=badge_color,
            padx=8,
            pady=3,
        )
        self.badge_label.pack(side=tk.LEFT)

        self.close_btn = tk.Label(
            self.top_row,
            text="✕ [12s]",
            font=("Segoe UI", 9, "bold"),
            fg="#a6adc8",
            bg="#181825",
            cursor="hand2",
        )
        self.close_btn.pack(side=tk.RIGHT)
        self.close_btn.bind("<Button-1>", lambda e: self._dismiss())

        # Big Meme Title
        display_title = title if len(title) < 36 else meme_id.replace("_", " ").upper()
        self.title_label = tk.Label(
            self.card,
            text=display_title,
            font=("Impact", 17),
            fg="#cdd6f4",
            bg="#181825",
            justify=tk.LEFT,
        )
        self.title_label.pack(anchor=tk.W)

        # Caption / Quote text
        self.caption_label = tk.Label(
            self.card,
            text=f'"{caption}"',
            font=("Segoe UI", 11, "italic"),
            fg="#f9e2af",
            bg="#181825",
            wraplength=420,
            justify=tk.LEFT,
        )
        self.caption_label.pack(anchor=tk.W, pady=(6, 8))

        # Bottom hint
        self.hint_label = tk.Label(
            self.card,
            text="💡 Click card or press ESC to dismiss early",
            font=("Segoe UI", 8),
            fg="#6c7086",
            bg="#181825",
        )
        self.hint_label.pack(anchor=tk.E)

        # Bind dragging & dismiss
        for w in (self.card, self.title_label, self.caption_label):
            w.bind("<Button-1>", self._start_drag)
            w.bind("<B1-Motion>", self._on_drag)

        self.bind("<Escape>", lambda e: self._dismiss())

        # Position prominently towards the CENTRE of the screen
        self.update_idletasks()
        w = max(420, self.winfo_reqwidth())
        h = self.winfo_reqheight()

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        pos_x = max(20, (screen_w - w) // 2)
        pos_y = max(40, (screen_h - h) // 2 - 80)
        self.geometry(f"{w}x{h}+{pos_x}+{pos_y}")

        # Auto-dismiss timer (> 10 seconds: default 12,000ms)
        self.after(duration_ms, self._dismiss)

    def _start_drag(self, event) -> None:
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_drag(self, event) -> None:
        x = self.winfo_x() + (event.x - self._drag_start_x)
        y = self.winfo_y() + (event.y - self._drag_start_y)
        self.geometry(f"+{x}+{y}")

    def _dismiss(self) -> None:
        try:
            self.destroy()
        except Exception:
            pass


def show_meme_card(
    parent: tk.Widget,
    meme_id: str,
    title: str,
    caption: str,
    pet_x: int = 0,
    pet_y: int = 0,
    duration_ms: int = 12000,
) -> Optional[MemeCardPopup]:
    """Helper to display the punchline meme card centered on screen for >10s."""
    try:
        return MemeCardPopup(
            parent=parent,
            meme_id=meme_id,
            title=title,
            caption=caption,
            pet_x=pet_x,
            pet_y=pet_y,
            duration_ms=duration_ms,
        )
    except Exception as exc:
        logger.warning(f"Could not show meme card: {exc}")
        return None
