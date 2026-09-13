"""
thunderstrike.py
----------------
Full Angry Thunderstrike sequence:
- Flashes fullscreen electrical lightning canvas animation
- Synthesizes thunderstrike audio / crash
- Shakes the desktop pet window
- Forcibly minimizes all running application windows (Win+D)
"""

import ctypes
import logging
import random
import time
import tkinter as tk
from typing import Callable

logger = logging.getLogger("thunderstrike")


def minimize_all_windows() -> None:
    """Safely minimizes all open desktop windows via Windows Win+D keyboard event."""
    try:
        user32 = ctypes.windll.user32
        VK_LWIN = 0x5B
        VK_D = 0x44
        KEYEVENTF_KEYUP = 0x0002

        user32.keybd_event(VK_LWIN, 0, 0, 0)
        user32.keybd_event(VK_D, 0, 0, 0)
        user32.keybd_event(VK_D, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
        logger.info("Executed minimize_all_windows (Win+D).")
    except Exception as exc:
        logger.warning(f"Could not minimize windows: {exc}")


class ThunderstrikeOverlay(tk.Toplevel):
    def __init__(self, root: tk.Tk, on_finished: Callable[[], None] | None = None):
        super().__init__(root)
        self.root = root
        self.on_finished = on_finished
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.config(bg="#000000")

        self.screen_w = self.winfo_screenwidth()
        self.screen_h = self.winfo_screenheight()
        self.geometry(f"{self.screen_w}x{self.screen_h}+0+0")
        self.lift()

        self.canvas = tk.Canvas(
            self,
            width=self.screen_w,
            height=self.screen_h,
            bg="#050510",
            highlightthickness=0,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self._flash_count = 0
        self._play_thunder_sound()
        self._animate_lightning()

    def _play_thunder_sound(self) -> None:
        try:
            import pygame
            from pathlib import Path
            audio_path = Path(__file__).resolve().parent.parent / "assets" / "audio" / "thunder.mp3"
            if audio_path.exists():
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                sound = pygame.mixer.Sound(str(audio_path))
                sound.play()
                return
        except Exception:
            pass
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONHAND)
        except Exception:
            pass

    def _generate_lightning_branch(self, x1: float, y1: float, x2: float, y2: float, depth: int = 5) -> list[tuple[float, float]]:
        points = [(x1, y1)]
        cur_x, cur_y = x1, y1
        steps = depth * 4
        dx = (x2 - x1) / steps
        dy = (y2 - y1) / steps

        for _ in range(steps - 1):
            cur_x += dx + random.uniform(-25, 25)
            cur_y += dy + random.uniform(-10, 10)
            points.append((cur_x, cur_y))
        points.append((x2, y2))
        return points

    def _animate_lightning(self) -> None:
        self.canvas.delete("all")
        if self._flash_count < 8:
            # Random strobe effect (white / electric cyan)
            bg_color = random.choice(["#ffffff", "#38bdf8", "#0284c7", "#000000"])
            self.canvas.config(bg=bg_color)

            # Draw multiple branching lightning bolts
            for _ in range(random.randint(2, 5)):
                start_x = random.randint(int(self.screen_w * 0.2), int(self.screen_w * 0.8))
                end_x = start_x + random.randint(-200, 200)
                branch = self._generate_lightning_branch(start_x, 0, end_x, self.screen_h, depth=4)

                # Draw outer glow
                for i in range(len(branch) - 1):
                    self.canvas.create_line(
                        branch[i][0], branch[i][1], branch[i + 1][0], branch[i + 1][1],
                        fill="#00f0ff", width=6,
                    )
                    self.canvas.create_line(
                        branch[i][0], branch[i][1], branch[i + 1][0], branch[i + 1][1],
                        fill="#ffffff", width=2,
                    )

            self._flash_count += 1
            self.after(random.randint(60, 110), self._animate_lightning)
        else:
            # End of strike: minimize all apps and dismiss
            minimize_all_windows()
            self.after(150, self._cleanup)

    def _cleanup(self) -> None:
        try:
            self.destroy()
        except Exception:
            pass
        if self.on_finished:
            self.on_finished()


def trigger_thunderstrike(root: tk.Tk, on_finished: Callable[[], None] | None = None) -> None:
    """Spawns the Thunderstrike sequence and minimizes all windows."""
    ThunderstrikeOverlay(root, on_finished=on_finished)
