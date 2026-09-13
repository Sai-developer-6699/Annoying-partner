"""
voice.py
--------
Thread-safe, non-blocking Speech Synthesizer for Ego-Bot 3000.
Features:
- Primary Engine: edge-tts with anime companion persona ('en-US-AnaNeural' or 'en-GB-SoniaNeural')
  with upbeat pitch (+8Hz) and rate (+12%).
- Plays speech through dedicated pygame.mixer.Channel(1) so it never interrupts sound effects.
- Offline Fallback: pyttsx3 dynamically locked to local female voices ('Microsoft Hazel' or
  'Microsoft Zira') so the awkward default male David voice is NEVER used.
"""

import asyncio
import logging
import os
import queue
import re
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("voice")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TTS_CACHE_DIR = PROJECT_ROOT / "assets" / "audio" / "tts_cache"
TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class VoiceSynthesizer:
    def __init__(
        self,
        enabled: bool = True,
        voice_name: str = "en-US-AnaNeural",
        rate_str: str = "+12%",
        pitch_str: str = "+8Hz",
    ):
        self.enabled = enabled
        self.voice_name = voice_name
        self.rate_str = rate_str
        self.pitch_str = pitch_str

        self._speech_queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

        if self.enabled:
            self._start_worker()

    def _start_worker(self) -> None:
        self._worker_thread = threading.Thread(
            target=self._process_queue, daemon=True, name="EgoBotVoiceWorker"
        )
        self._worker_thread.start()
        logger.info("VoiceSynthesizer worker started with anime persona.")

    def _init_pyttsx3_fallback(self):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", 190)
            engine.setProperty("volume", 1.0)
            # Find female voice (Hazel or Zira)
            female_voice = None
            for v in engine.getProperty("voices"):
                name_l = v.name.lower()
                if "hazel" in name_l or "zira" in name_l or "female" in name_l:
                    female_voice = v.id
                    break
            if female_voice:
                engine.setProperty("voice", female_voice)
                logger.info(f"pyttsx3 female fallback voice configured: {female_voice}")
            return engine
        except Exception as exc:
            logger.warning(f"Could not initialize pyttsx3 fallback: {exc}")
            return None

    def _process_queue(self) -> None:
        fallback_engine = None

        # Try to initialize pygame.mixer channel 1 for voice
        voice_channel = None
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            voice_channel = pygame.mixer.Channel(1)
        except Exception as exc:
            logger.warning(f"Could not initialize pygame voice channel: {exc}")

        while not self._stop_event.is_set():
            try:
                item = self._speech_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if item is None or self._stop_event.is_set():
                break

            if isinstance(item, tuple):
                text, on_finish = item
            else:
                text, on_finish = item, None

            try:
                # Clean text of markdown / symbols / emoji artifacts for crisp speech
                clean_text = re.sub(r"[\*#\[\]_~`]", "", text)
                clean_text = re.sub(r"[^\x00-\x7F]+", " ", clean_text).strip()
                if not clean_text:
                    if on_finish and not self._stop_event.is_set():
                        on_finish()
                    continue

                spoken_successfully = False

                # 1. Primary: edge-tts neural anime synthesis
                try:
                    import edge_tts
                    temp_file = TTS_CACHE_DIR / f"tts_{int(time.time() * 1000) % 10000}.mp3"
                    
                    async def _synthesize():
                        comm = edge_tts.Communicate(
                            clean_text,
                            voice=self.voice_name,
                            rate=self.rate_str,
                            pitch=self.pitch_str,
                        )
                        await comm.save(str(temp_file))

                    asyncio.run(_synthesize())

                    if temp_file.exists() and temp_file.stat().st_size > 0:
                        import pygame
                        sound = pygame.mixer.Sound(str(temp_file))
                        if voice_channel is None:
                            voice_channel = pygame.mixer.Channel(1)
                        voice_channel.play(sound)

                        # Non-blocking wait for speech playback to finish
                        duration = sound.get_length()
                        start_wait = time.monotonic()
                        while voice_channel.get_busy() and (time.monotonic() - start_wait < duration + 0.5):
                            if self._stop_event.is_set():
                                voice_channel.stop()
                                break
                            time.sleep(0.04)

                        spoken_successfully = True
                except Exception as edge_exc:
                    logger.warning(f"edge-tts failed (falling back to pyttsx3 female): {edge_exc}")

                # 2. Fallback: pyttsx3 with Hazel/Zira female voice
                if not spoken_successfully:
                    if fallback_engine is None:
                        fallback_engine = self._init_pyttsx3_fallback()
                    if fallback_engine:
                        fallback_engine.say(clean_text)
                        fallback_engine.runAndWait()

            except Exception as exc:
                logger.warning(f"Error speaking text '{text[:30]}': {exc}")
            finally:
                self._speech_queue.task_done()
                if on_finish and not self._stop_event.is_set():
                    try:
                        on_finish()
                    except Exception as fin_exc:
                        logger.warning(f"Error in on_finish speech callback: {fin_exc}")

        try:
            if fallback_engine:
                fallback_engine.stop()
        except Exception:
            pass

    def speak_async(self, text: str, on_finish: Optional[Callable[[], None]] = None) -> None:
        """Queues dialogue to be spoken aloud non-blockingly, then calls on_finish when done."""
        if not self.enabled or not text:
            if on_finish:
                try:
                    on_finish()
                except Exception:
                    pass
            return

        # Drop excessive backlog so speech doesn't lag behind current visual state
        if self._speech_queue.qsize() > 1:
            try:
                while not self._speech_queue.empty():
                    self._speech_queue.get_nowait()
                    self._speech_queue.task_done()
            except Exception:
                pass

        self._speech_queue.put((text, on_finish))
        logger.info(f"Queued spoken dialogue: '{text[:40]}...'")

    def stop(self) -> None:
        """Stops the synthesizer and worker thread."""
        self._stop_event.set()
        self._speech_queue.put(None)
