"""
stop.py
-------
Simple, foolproof termination script for Ego-Bot 3000.
Usage:
    python stop.py
    .\\.venv\\Scripts\\python.exe stop.py
"""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
PID_FILE = PROJECT_ROOT / ".egobot.pid"


def kill_process(pid: int) -> bool:
    """Attempts to kill process by PID on Windows."""
    try:
        # Use taskkill for forceful termination of tree on Windows
        res = subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
            text=True,
        )
        return res.returncode == 0
    except Exception as exc:
        print(f"[WARN] Failed to taskkill PID {pid}: {exc}")
        try:
            os.kill(pid, 9)
            return True
        except Exception:
            return False


def main():
    killed_any = False

    # 1. Check PID file
    if PID_FILE.exists():
        try:
            pid_str = PID_FILE.read_text(encoding="utf-8").strip()
            if pid_str.isdigit():
                pid = int(pid_str)
                print(f"[STOP] Found Ego-Bot PID: {pid}. Terminating...")
                if kill_process(pid):
                    print(f"[SUCCESS] Ego-Bot (PID {pid}) terminated successfully.")
                    killed_any = True
                else:
                    print(f"[INFO] Process {pid} was not running.")
        except Exception as exc:
            print(f"[WARN] Error reading PID file: {exc}")
        finally:
            try:
                PID_FILE.unlink(missing_ok=True)
            except Exception:
                pass

    # 2. Also search for any stray main.py processes running under python in this workspace
    try:
        cmd = 'wmic process where "commandline like \'%main.py%\' and name like \'%python%\'" get processid'
        output = subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout
        pids = [int(line.strip()) for line in output.splitlines() if line.strip().isdigit() and int(line.strip()) != os.getpid()]
        for p in pids:
            print(f"[STOP] Found running Ego-Bot process PID {p}. Killing...")
            if kill_process(p):
                killed_any = True
    except Exception:
        pass

    if killed_any:
        print("[DONE] Ego-Bot 3000 has been completely silenced. You are free!")
    else:
        print("[INFO] No running instances of Ego-Bot 3000 were found.")


if __name__ == "__main__":
    main()
