"""
compliment_validator.py
------------------------
Handles the "type a unique compliment every 15s" rule, including the
"you typed/pasted that too fast, that's cheating" blame feature.

Wire this into the Tkinter Entry widget like:

    entry.bind("<KeyRelease>", validator.on_keystroke)
    entry.bind("<<Paste>>", validator.on_paste_event)

and call validator.submit(text) when the user hits Enter / the submit button.
"""

import difflib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

COMPLIMENTS_JSON = Path(__file__).resolve().parent.parent / "data" / "compliments.json"

# Below this many ms between the first and last keystroke of a message of
# this length, we assume it was pasted/auto-typed rather than actually typed.
MIN_MS_PER_CHAR = 25


@dataclass
class ComplimentValidator:
    max_history: int = 15
    similarity_threshold: float = 0.82
    history: list[str] = field(default_factory=list)
    _first_keystroke_ts: float | None = None
    _last_paste_flag: bool = False

    @classmethod
    def load(cls) -> "ComplimentValidator":
        data = json.loads(COMPLIMENTS_JSON.read_text(encoding="utf-8"))
        return cls(
            max_history=data.get("max_history", 15),
            similarity_threshold=data.get("similarity_threshold", 0.82),
            history=list(data.get("history", [])),
        )

    def save(self) -> None:
        data = json.loads(COMPLIMENTS_JSON.read_text(encoding="utf-8"))
        data["history"] = self.history[-self.max_history :]
        COMPLIMENTS_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # --- typing-rate / paste tracking -------------------------------------
    def on_keystroke(self, _event=None) -> None:
        if self._first_keystroke_ts is None:
            self._first_keystroke_ts = time.monotonic()

    def on_paste_event(self, _event=None) -> None:
        self._last_paste_flag = True

    def reset_typing_tracker(self) -> None:
        self._first_keystroke_ts = None
        self._last_paste_flag = False

    # --- core validation ----------------------------------------------------
    def submit(self, text: str) -> dict:
        """Returns {"accepted": bool, "reason": str, "blame_line": str | None}"""
        text = text.strip()
        elapsed = (time.monotonic() - self._first_keystroke_ts) if self._first_keystroke_ts else None
        was_pasted = self._last_paste_flag
        self.reset_typing_tracker()

        if not text:
            return self._reject("empty", "That's not even a compliment, that's silence.")

        if was_pasted:
            return self._reject("pasted", "Pasting doesn't count. Type it like you mean it.")

        if len(text) > 220:
            return self._reject(
                "wall_of_text",
                "That's a whole essay, not a compliment! Keep it under 220 chars, mortal.",
            )

        # Check repeated punctuation spam (from annoying-ai-companion-1)
        for spam_pat in ("!!!", "???", "...!!!", "!?!?"):
            if spam_pat in text:
                return self._reject(
                    "punctuation_spam",
                    "Excessive punctuation detected! Flattery requires words, not frantic symbols.",
                )

        if elapsed is not None and len(text) > 0:
            ms_per_char = (elapsed * 1000) / len(text)
            if ms_per_char < MIN_MS_PER_CHAR:
                return self._reject(
                    "too_fast",
                    "Nobody types that fast and means it. Slow down and try again.",
                )

        if self._is_repeat(text):
            return self._reject("repeat", "Heard that one already. Say something new.")

        self._add_to_history(text)
        self.save()
        return {"accepted": True, "reason": "ok", "blame_line": None}

    def _is_repeat(self, text: str) -> bool:
        for prior in self.history:
            ratio = difflib.SequenceMatcher(None, text.lower(), prior.lower()).ratio()
            if ratio >= self.similarity_threshold:
                return True
        return False

    def _add_to_history(self, text: str) -> None:
        self.history.append(text)
        self.history = self.history[-self.max_history :]

    @staticmethod
    def _reject(reason: str, blame_line: str) -> dict:
        return {"accepted": False, "reason": reason, "blame_line": blame_line}
