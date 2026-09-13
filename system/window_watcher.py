"""
window_watcher.py
-----------------
Monitors active window titles and running processes using pygetwindow and psutil.
When an unauthorized app or slacking window is detected, triggers a callback to
feed 'unauthorized_app' into the lottery system.
"""

import json
import logging
import threading
import time
from pathlib import Path
from typing import Callable

logger = logging.getLogger("window_watcher")

CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "unauthorized_apps.json"


class WindowWatcher:
    def __init__(
        self,
        on_unauthorized: Callable[[str, str], None],
        config_path: Path | str | None = None,
        debug: bool = False,
    ):
        self.on_unauthorized = on_unauthorized
        self.config_path = Path(config_path) if config_path else CONFIG_PATH
        self.debug = debug
        self.running = False
        self._thread: threading.Thread | None = None
        self._last_trigger_ts = 0.0
        self.paused = False

        self.unauthorized_processes = []
        self.unauthorized_window_keywords = []
        self.poll_interval = 2.5
        self.cooldown = 20.0
        self.load_config()

    def load_config(self) -> None:
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                self.unauthorized_processes = [
                    p.lower() for p in data.get("unauthorized_processes", [])
                ]
                self.unauthorized_window_keywords = [
                    w.lower() for w in data.get("unauthorized_window_keywords", [])
                ]
                self.poll_interval = float(data.get("poll_interval_seconds", 2.5))
                self.cooldown = float(data.get("cooldown_seconds", 20.0))
                self.check_background_processes = bool(data.get("check_background_processes", False))
                logger.info(f"Loaded {len(self.unauthorized_processes)} unauthorized processes (background_check={self.check_background_processes}).")
            except Exception as exc:
                logger.error(f"Failed to parse unauthorized apps config: {exc}")
        else:
            self.unauthorized_processes = ["chrome.exe", "steam.exe", "discord.exe", "brave.exe"]
            self.unauthorized_window_keywords = ["youtube", "netflix", "instagram", "game"]
            self.check_background_processes = False

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True, name="WindowWatcherThread")
        self._thread.start()
        logger.info("WindowWatcher started.")

    def stop(self) -> None:
        self.running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        logger.info("WindowWatcher stopped.")

    def pause(self) -> None:
        """Pause detections, e.g. while punishment screen is active."""
        self.paused = True

    def resume(self) -> None:
        """Resume detections after punishment is cleared."""
        self.paused = False
        self._last_trigger_ts = time.monotonic()  # Give grace period after resuming

    def _watch_loop(self) -> None:
        while self.running:
            if not self.paused:
                self._check_active_window()
            time.sleep(self.poll_interval)

    def _check_active_window(self) -> None:
        now = time.monotonic()
        if (now - self._last_trigger_ts) < self.cooldown:
            return

        active_title = ""
        active_proc_name = ""
        hit_keyword = None
        hit_proc = None

        # 1. Check active foreground window title and active process
        try:
            import win32gui
            import win32process
            import psutil
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                active_title = win32gui.GetWindowText(hwnd).strip()
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    active_proc_name = psutil.Process(pid).name().lower()
                except Exception:
                    pass
        except Exception:
            try:
                import pygetwindow as gw
                window = gw.getActiveWindow()
                if window and window.title:
                    active_title = window.title.strip()
            except Exception:
                pass

        # Check if active foreground process is in unauthorized list (e.g. user is inside Brave)
        if active_proc_name and active_proc_name in self.unauthorized_processes:
            hit_proc = active_proc_name

        # Check active window title keywords
        if not hit_proc and active_title:
            title_lower = active_title.lower()
            for keyword in self.unauthorized_window_keywords:
                if keyword in title_lower:
                    hit_keyword = keyword
                    break

        # 2. Check running background processes via psutil ONLY if explicitly configured
        if not hit_keyword and not hit_proc and self.check_background_processes:
            try:
                import psutil
                for proc in psutil.process_iter(["name"]):
                    try:
                        pname = proc.info.get("name")
                        if pname and pname.lower() in self.unauthorized_processes:
                            hit_proc = pname
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            except Exception as exc:
                logger.debug(f"psutil process check error: {exc}")

        if hit_keyword or hit_proc:
            app_identified = hit_keyword or hit_proc or "distraction"
            self._last_trigger_ts = now
            logger.info(f"Unauthorized app detected: {app_identified} (Window: {active_title})")
            if self.debug:
                print(f"[DEBUG Watcher] Unauthorized hit: {app_identified} | Title: '{active_title}'")
            try:
                self.on_unauthorized(app_identified, active_title)
            except Exception as exc:
                logger.error(f"Error in on_unauthorized callback: {exc}")
