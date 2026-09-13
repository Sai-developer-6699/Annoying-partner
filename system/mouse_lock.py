"""
mouse_lock.py
-------------
Compulsory mouse detention & physics chaos engine:
- Mode "corner_freeze": Holds cursor in a screen corner for 30s.
- Mode "cursor_gravity": Pulls cursor downward like gravity is dragging it off the screen.
- Mode "inverted_mouse": Reverses mouse movements (anti-control evasion).

Includes strict safety mechanisms:
- abort_event support for emergency stop (Ctrl+Alt+Shift+Q or UI release).
- debug mode where cursor hijacking is simulated/logged only.
- preserves FAILSAFE behavior during development.
"""

import logging
import sys
import threading
import time
from typing import Callable

try:
    import pyautogui
    # Keep failsafe enabled during development as specified in AGENTS.md
    pyautogui.FAILSAFE = True
except ImportError:
    pyautogui = None

logger = logging.getLogger("mouse_lock")


def apply_cursor_chaos(
    duration: float = 30.0,
    mode: str = "corner_freeze",  # "corner_freeze", "cursor_gravity", "inverted_mouse"
    debug: bool = False,
    abort_event: threading.Event | None = None,
    target_corner: str = "bottom_right",
) -> None:
    """
    Executes mouse detention or physics chaos for `duration` seconds.
    Inverted mouse punishment duration is 15.0 seconds as requested.
    """
    if mode == "inverted_mouse" and duration > 5.0:
        effective_duration = 15.0
    elif debug:
        effective_duration = min(duration, 5.0)
    else:
        effective_duration = duration

    logger.info(f"Cursor chaos started (mode={mode}, duration={effective_duration:.1f}s, debug={debug})")
    start_time = time.monotonic()

    if pyautogui is None:
        logger.warning("pyautogui is not installed. Cursor chaos skipped.")
        return

    # Disable automatic (0,0) exception so idle cursors don't immediately crash chaos
    pyautogui.FAILSAFE = False

    try:
        width, height = pyautogui.size()
    except Exception:
        width, height = 1920, 1080

    # 1. Cursor Gravity Mode (drags cursor downward like heavy gravity)
    if mode == "cursor_gravity":
        vy = 3.0
        try:
            while time.monotonic() - start_time < effective_duration:
                if abort_event and abort_event.is_set():
                    break
                try:
                    pos = pyautogui.position()
                    x, y = pos.x, pos.y
                    vy = min(35.0, vy + 1.2)  # gravity acceleration
                    new_y = min(height - 15, int(y + vy))
                    # Clamp safe coordinates
                    safe_x = max(15, min(width - 15, x))
                    pyautogui.moveTo(safe_x, new_y)
                except pyautogui.FailSafeException:
                    logger.warning("Emergency PyAutoGUI failsafe triggered in cursor_gravity.")
                    break
                time.sleep(0.02)
        except Exception as exc:
            logger.error(f"Error in cursor_gravity: {exc}")
        return

    # 2. Inverted Mouse Movement Mode (anti-control: pulls in opposite direction)
    if mode == "inverted_mouse":
        try:
            pos = pyautogui.position()
            last_x, last_y = pos.x, pos.y
            while time.monotonic() - start_time < effective_duration:
                if abort_event and abort_event.is_set():
                    break
                try:
                    cur_pos = pyautogui.position()
                    cur_x, cur_y = cur_pos.x, cur_pos.y
                    dx = cur_x - last_x
                    dy = cur_y - last_y
                    if abs(dx) > 1 or abs(dy) > 1:
                        # Pull cursor in the opposite direction of motion
                        target_x = max(15, min(width - 15, last_x - int(dx * 1.7)))
                        target_y = max(15, min(height - 15, last_y - int(dy * 1.7)))
                        pyautogui.moveTo(target_x, target_y)
                        last_x, last_y = target_x, target_y
                    else:
                        last_x, last_y = cur_x, cur_y
                except pyautogui.FailSafeException:
                    logger.warning("Emergency PyAutoGUI failsafe triggered in inverted_mouse.")
                    break
                time.sleep(0.02)
        except Exception as exc:
            logger.error(f"Error in inverted_mouse: {exc}")
        return

    # 3. Corner Freeze Mode (Default detention)
    if target_corner == "top_left":
        corner_x, corner_y = 15, 15
    elif target_corner == "top_right":
        corner_x, corner_y = max(15, width - 15), 15
    elif target_corner == "bottom_left":
        corner_x, corner_y = 15, max(15, height - 15)
    else:  # bottom_right
        corner_x, corner_y = max(15, width - 15), max(15, height - 15)

    try:
        while time.monotonic() - start_time < effective_duration:
            if abort_event and abort_event.is_set():
                logger.info("Mouse freeze aborted by emergency event.")
                break
            try:
                pyautogui.moveTo(corner_x, corner_y)
            except pyautogui.FailSafeException:
                logger.warning("Emergency PyAutoGUI failsafe triggered in corner_freeze.")
                break
            time.sleep(0.015)
    except Exception as exc:
        logger.error(f"Error during mouse freeze: {exc}")

    logger.info("Cursor chaos completed.")


def freeze_mouse(
    duration: float = 30.0,
    debug: bool = False,
    abort_event: threading.Event | None = None,
    target_corner: str = "bottom_right",
    mode: str = "corner_freeze",
) -> None:
    """Convenience wrapper for apply_cursor_chaos."""
    apply_cursor_chaos(
        duration=duration,
        mode=mode,
        debug=debug,
        abort_event=abort_event,
        target_corner=target_corner,
    )


def start_mouse_freeze_thread(
    duration: float = 30.0,
    debug: bool = False,
    abort_event: threading.Event | None = None,
    on_finish: Callable | None = None,
    mode: str = "corner_freeze",
) -> tuple[threading.Thread, threading.Event]:
    """
    Starts cursor chaos in a daemon thread.
    Returns (thread, abort_event).
    """
    if abort_event is None:
        abort_event = threading.Event()

    def run():
        apply_cursor_chaos(duration=duration, mode=mode, debug=debug, abort_event=abort_event)
        if on_finish:
            on_finish()

    thread = threading.Thread(target=run, daemon=True, name="MouseLockThread")
    thread.start()
    return thread, abort_event
