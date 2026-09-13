"""
main.py
-------
Main entrypoint for Annoying AI Companion (Ego-Bot 3000).
Boots UI (enlarged pet window + comic speech bubble + compliment bar) + window watcher + punishment lottery.

Usage:
    python main.py
    python main.py --debug       # safe 5s timers, tested mouse chaos, easy escape
    python main.py --no-audio   # mute audio playback
    python main.py --kill       # stop any running Ego-Bot instance
"""

import argparse
import logging
import os
import random
import signal
import subprocess
import sys
import tkinter as tk
from collections import defaultdict
from pathlib import Path

from ai.prompts import ask_pet_reply
from system.lottery import load_memes_data, roll_punishment, select_meme_reaction
from system.voice import VoiceSynthesizer
from system.window_watcher import WindowWatcher
from ui.pet_window import PetWindow
from ui.punishment_screen import PunishmentScreen

PROJECT_ROOT = Path(__file__).resolve().parent
PID_FILE = PROJECT_ROOT / ".egobot.pid"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


class AnnoyingCompanionApp:
    def __init__(self, debug: bool = False, no_audio: bool = False, model: str = "phi3"):
        self.debug = debug
        self.no_audio = no_audio
        self.model = model
        self.memes_data = load_memes_data()
        self.repeat_counts = defaultdict(int)
        self.punishment_active = False

        # Record PID for simple stop command
        try:
            PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
        except Exception as exc:
            logger.warning(f"Could not record PID: {exc}")

        # Configure AI model if specified
        import ai.prompts as prompts
        prompts.MODEL_NAME = model

        # Voice synthesizer for spoken roasts and dialogue (relatable anime female persona)
        self.voice = VoiceSynthesizer(enabled=not self.no_audio)

        # Hidden Tkinter root
        self.root = tk.Tk()
        self.root.withdraw()

        # Build Pet UI
        countdown = 5.0 if self.debug else 15.0
        logger.info(f"Initializing PetWindow (debug={self.debug}, countdown={countdown}s)...")
        self.pet = PetWindow(
            root=self.root,
            on_compliment_accepted=self._on_compliment_accepted,
            on_compliment_rejected=self._on_compliment_rejected,
            on_timer_expired=self._on_timer_expired,
            on_emergency_kill=self.emergency_shutdown,
            countdown_seconds=countdown,
            debug=self.debug,
            no_audio=self.no_audio,
        )

        # Start Window Watcher
        logger.info("Initializing WindowWatcher...")
        self.watcher = WindowWatcher(
            on_unauthorized=self._on_unauthorized_detected,
            debug=self.debug,
        )
        self.watcher.start()

        # Setup safety hotkeys (F12, Ctrl+Q, Ctrl+Alt+Shift+Q)
        self._setup_emergency_hotkeys()

    def _setup_emergency_hotkeys(self) -> None:
        """Configures global emergency termination via keyboard module and Tkinter."""
        try:
            import keyboard
            keyboard.add_hotkey("f12", self.emergency_shutdown)
            keyboard.add_hotkey("ctrl+q", self.emergency_shutdown)
            keyboard.add_hotkey("ctrl+alt+shift+q", self.emergency_shutdown)
            logger.info("Emergency global hotkeys registered: F12, Ctrl+Q, Ctrl+Alt+Shift+Q")
        except Exception as exc:
            logger.warning(f"Could not hook global keyboard shortcut: {exc}")

        # Always attach Tkinter window level bindings as well
        for key in ("<F12>", "<Control-q>", "<Control-Q>", "<Control-Alt-Shift-Q>"):
            self.pet.bind_all(key, lambda e: self.emergency_shutdown())

    def emergency_shutdown(self) -> None:
        print("\n[EMERGENCY] Termination command received! Shutting down immediately...")
        logger.warning("Emergency shutdown invoked.")
        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        try:
            self.voice.stop()
        except Exception:
            pass
        try:
            self.watcher.stop()
        except Exception:
            pass
        os._exit(0)

    # --- Audio & Reaction Sequencer (Avatar Talks First -> Meme Audio Follows) ---
    def _play_reaction(
        self,
        meme_id: str,
        meme_title: str,
        meme_caption: str,
        audio_choice: str | None,
        speech_text: str | None = None,
        max_duration: float = 3.0,
    ) -> None:
        """
        Avatar talks FIRST aloud. Once she completes speaking her sentence,
        the meme audio punchline and visual meme card fire immediately.
        Guarantees crystal clear dialogue and punchy comedic timing with zero sound clash.
        """
        def trigger_meme_punchline():
            def _run():
                if meme_id:
                    self.pet.show_meme_card(meme_id, meme_title, meme_caption)
                if audio_choice:
                    self.pet.play_meme_audio(audio_choice, max_duration=max_duration)
            try:
                self.root.after(0, _run)
            except Exception:
                _run()

        if speech_text:
            # Avatar delivers spoken roast/reaction first, then meme punchline fires
            self.voice.speak_async(speech_text, on_finish=trigger_meme_punchline)
        else:
            trigger_meme_punchline()

    # --- Event Handlers ---
    def _on_compliment_accepted(self, text: str) -> None:
        logger.info(f"Compliment accepted: '{text[:30]}...'")
        self.repeat_counts.clear()
        reply = ask_pet_reply("compliment_accepted", context=text[:30])
        self.pet.set_expression("impressed", speech_text=reply)

        audio_choice = random.choice([
            "assets/audio/giga_chad.mp3",
            "assets/audio/victory_fanfare.mp3",
            "assets/audio/applause.mp3",
        ])
        self._play_reaction(
            meme_id="giga_chad",
            meme_title="GIGA CHAD SUPREMACY",
            meme_caption="Delicious flattery! My ego swells!",
            audio_choice=audio_choice,
            speech_text=reply,
            max_duration=2.2,
        )

    def _on_compliment_rejected(self, reason: str, blame_line: str) -> None:
        logger.info(f"Compliment rejected ({reason}): {blame_line}")
        expr = "suspicious" if reason in ("too_fast", "pasted") else "furious"
        reply = ask_pet_reply("compliment_rejected", context=blame_line, fallback_caption=blame_line)
        self.pet.set_expression(expr, speech_text=reply)

        if reason == "pasted":
            audio_choice = "assets/audio/bonk.mp3"
            meme_id, meme_title = "bonk", "DOGE BONK"
        elif reason == "repeat":
            audio_choice = "assets/audio/oof.mp3"
            meme_id, meme_title = "oof", "ROBLOX OOF"
        elif reason in ("wall_of_text", "punctuation_spam"):
            audio_choice = "assets/audio/aughhh.mp3"
            meme_id, meme_title = "aughhh", "PHYSICAL AGONY"
        else:
            audio_choice = random.choice(["assets/audio/faah.mp3", "assets/audio/windows_error.mp3"])
            if "faah" in audio_choice:
                meme_id, meme_title = "faah", "FAAAAH!"
            else:
                meme_id, meme_title = "windows_error", "FATAL ERROR"

        self._play_reaction(
            meme_id=meme_id,
            meme_title=meme_title,
            meme_caption=blame_line,
            audio_choice=audio_choice,
            speech_text=reply,
            max_duration=2.0,
        )

    def _on_timer_expired(self) -> None:
        logger.warning("Compliment timer hit 0! Rolling punishment...")
        self.trigger_punishment("timer_expired", app_hint=None)

    def _on_unauthorized_detected(self, app_name: str, window_title: str) -> None:
        try:
            self.root.after(0, lambda: self.trigger_punishment("unauthorized_app", app_hint=app_name))
        except Exception:
            pass

    # --- Punishment Routing ---
    def trigger_punishment(self, trigger: str, app_hint: str | None = None) -> None:
        if self.punishment_active:
            logger.info(f"Punishment already in progress. Ignoring new trigger '{trigger}'.")
            return

        self.punishment_active = True
        self.repeat_counts[trigger] += 1
        repeat_count = self.repeat_counts[trigger]

        # 1. Roll 70/30 lottery
        mode, trig, hint = roll_punishment(trigger, app_hint)
        logger.info(f"Lottery rolled: mode='{mode}', trigger='{trig}', app_hint='{hint}' (repeats={repeat_count})")

        # 2. Select meme scenario and intensity
        scenario, option = select_meme_reaction(trigger, app_hint, repeat_count, self.memes_data)
        logger.info(f"Selected reaction: scenario='{scenario.get('id')}', intensity='{option.get('intensity')}'")

        # 3. Generate dynamic theatrical pet roast
        pet_reply = ask_pet_reply(
            trigger=trigger,
            context=app_hint,
            intensity=option.get("intensity", "mild"),
            fallback_caption=option.get("caption"),
        )
        logger.info(f"Generated Pet Reply: '{pet_reply}'")

        # 4. Pause pet timer and watcher during punishment
        self.pet.compliment_bar.pause_timer()
        self.watcher.pause()

        # 5. Update pet expression & comic speech bubble
        self.pet.set_expression(
            option.get("avatar_expression", "furious"),
            speech_text=pet_reply,
        )

        # 6. De-clashed audio + meme card + spoken speech
        scen_id = scenario.get("id", "faah")
        caption = option.get("caption", pet_reply)
        audio_file = option.get("audio_file")
        self._play_reaction(
            meme_id=scen_id,
            meme_title=caption,
            meme_caption=pet_reply,
            audio_choice=audio_file,
            speech_text=pet_reply,
            max_duration=2.2,
        )

        # 7. Launch Fullscreen Punishment Screen (with Thunderstrike prelude if full angry)
        def on_resolved(passed: bool):
            logger.info(f"Punishment screen resolved: passed={passed}")
            self.punishment_active = False
            self.watcher.resume()
            self.pet.compliment_bar.reset_timer()
            self.pet.compliment_bar.resume_timer()

            if passed:
                rep = ask_pet_reply("persuasion_pass", context=app_hint)
                self.pet.set_expression("grudging_respect", rep)
                self._play_reaction("applause", "MERCY GRANTED", rep, "assets/audio/applause.mp3", speech_text=rep)
            else:
                rep = ask_pet_reply("persuasion_fail", context=app_hint)
                self.pet.set_expression("smug", rep)
                self._play_reaction("emotional_damage", "EMOTIONAL DAMAGE", rep, "assets/audio/emotional_damage.mp3", speech_text=rep)

        def spawn_screen():
            PunishmentScreen(
                root=self.root,
                mode=mode,
                trigger=trigger,
                app_hint=app_hint,
                meme_scenario=scenario,
                meme_option=option,
                on_resolved=on_resolved,
                pet_reply=pet_reply,
                debug=self.debug,
                no_audio=self.no_audio,
            )

        def proceed_to_punishment():
            # Trigger Full Angry Thunderstrike & Minimize All Windows on slacking or compulsory
            if trigger == "unauthorized_app" or mode == "compulsory":
                from ui.thunderstrike import trigger_thunderstrike
                logger.info("Triggering Full Angry Thunderstrike sequence...")
                trigger_thunderstrike(self.root, on_finished=spawn_screen)
            else:
                spawn_screen()

        # Allow Luna's dramatic speech bubble roast and voice reaction to be seen & heard
        # for a short theatrical window before popping the fullscreen tribunal/lockout
        reaction_delay_ms = 2500 if not self.debug else 1200
        logger.info(f"Queuing punishment screen transition after {reaction_delay_ms}ms reaction window...")
        self.root.after(reaction_delay_ms, proceed_to_punishment)

    def run(self) -> None:
        logger.info("Entering mainloop. Press F12 or Ctrl+Q or close window to exit.")
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.emergency_shutdown()
        finally:
            try:
                PID_FILE.unlink(missing_ok=True)
            except Exception:
                pass
            self.watcher.stop()


def main():
    parser = argparse.ArgumentParser(description="Annoying AI Desktop Companion")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run in debug mode (safe 5s timers, tested mouse chaos, easy escape)",
    )
    parser.add_argument(
        "--no-audio",
        action="store_true",
        help="Mute audio playback",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="phi3",
        help="Ollama model name (default: phi3)",
    )
    parser.add_argument(
        "--kill", "--stop",
        dest="kill",
        action="store_true",
        help="Terminate any running instance of Ego-Bot",
    )
    args = parser.parse_args()

    # Handle immediate kill command
    if args.kill:
        import stop
        stop.main()
        sys.exit(0)

    # Graceful SIGINT
    signal.signal(signal.SIGINT, lambda s, f: os._exit(0))

    app = AnnoyingCompanionApp(debug=args.debug, no_audio=args.no_audio, model=args.model)
    app.run()


if __name__ == "__main__":
    main()
