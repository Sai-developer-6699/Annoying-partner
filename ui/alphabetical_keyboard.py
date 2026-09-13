"""
alphabetical_keyboard.py
------------------------
An anti-QWERTY on-screen keyboard where keys are strictly arranged in
Alphabetical Order (A B C D E F G...) to make typing compliments
hilariously frustrating and slow.
"""

import tkinter as tk
from typing import Callable


class AlphabeticalKeyboard(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Widget,
        entry_widget: tk.Entry,
        on_submit: Callable[[], None],
        on_keystroke: Callable[[any], None] | None = None,
    ):
        super().__init__(parent)
        self.entry_widget = entry_widget
        self.on_submit = on_submit
        self.on_keystroke = on_keystroke

        self.title("🔤 Anti-QWERTY Alphabetical Keyboard")
        self.attributes("-topmost", True)
        self.config(bg="#181825", padx=8, pady=8)
        self.resizable(False, False)

        self._build_keyboard()

    def _build_keyboard(self) -> None:
        title_label = tk.Label(
            self,
            text="ALPHABETICAL INPUT PROTOCOL\n(Good luck finding your letters)",
            font=("Segoe UI", 9, "bold"),
            fg="#f9e2af",
            bg="#181825",
            justify=tk.CENTER,
        )
        title_label.pack(pady=(0, 6))

        key_rows = [
            ["A", "B", "C", "D", "E", "F", "G"],
            ["H", "I", "J", "K", "L", "M", "N"],
            ["O", "P", "Q", "R", "S", "T", "U"],
            ["V", "W", "X", "Y", "Z", "SPACE", "BACKSPACE"],
        ]

        keys_frame = tk.Frame(self, bg="#181825")
        keys_frame.pack()

        for r_idx, row in enumerate(key_rows):
            row_frame = tk.Frame(keys_frame, bg="#181825")
            row_frame.pack(pady=2)
            for key in row:
                btn_w = 4 if key in ("SPACE", "BACKSPACE") else 3
                btn = tk.Button(
                    row_frame,
                    text="␣" if key == "SPACE" else ("⌫" if key == "BACKSPACE" else key),
                    font=("Segoe UI", 9, "bold"),
                    width=btn_w,
                    bg="#313244",
                    fg="#cdd6f4",
                    activebackground="#cba6f7",
                    activeforeground="#11111b",
                    relief=tk.FLAT,
                    cursor="hand2",
                    command=lambda k=key: self._on_key_click(k),
                )
                btn.pack(side=tk.LEFT, padx=2)

        # Enter button
        submit_btn = tk.Button(
            self,
            text="✨ SUBMIT COMPLIMENT ✨",
            font=("Segoe UI", 9, "bold"),
            bg="#a6e3a1",
            fg="#11111b",
            activebackground="#94e2d5",
            relief=tk.FLAT,
            cursor="hand2",
            pady=4,
            command=self._on_enter_click,
        )
        submit_btn.pack(fill=tk.X, pady=(6, 0))

    def _on_key_click(self, key: str) -> None:
        if key == "SPACE":
            self.entry_widget.insert(tk.INSERT, " ")
        elif key == "BACKSPACE":
            pos = self.entry_widget.index(tk.INSERT)
            if pos > 0:
                self.entry_widget.delete(pos - 1, pos)
        else:
            self.entry_widget.insert(tk.INSERT, key.lower())

        # Troll Autocorrect check
        import random
        if key == "SPACE" or random.random() < 0.15:
            try:
                from ui.compliment_bar import mutate_text_chaotically
                txt = self.entry_widget.get()
                new_txt, changed = mutate_text_chaotically(txt)
                if changed:
                    self.entry_widget.delete(0, tk.END)
                    self.entry_widget.insert(0, new_txt)
            except Exception:
                pass

        if self.on_keystroke:
            self.on_keystroke(None)

    def _on_enter_click(self) -> None:
        self.on_submit()
