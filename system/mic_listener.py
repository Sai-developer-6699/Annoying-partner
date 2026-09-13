"""
mic_listener.py
---------------
Lightweight microphone recording and speech-to-text listener for Ego-Bot 3000.
Supports background listening, single-shot recording, and transcription via
Google Speech Recognition with graceful offline fallback.
"""

import io
import logging
import threading
import time
from typing import Callable

logger = logging.getLogger("mic_listener")

try:
    import numpy as np
    import sounddevice as sd
    import speech_recognition as sr
    AUDIO_SUPPORTED = True
except ImportError:
    AUDIO_SUPPORTED = False


class MicListener:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.recognizer = sr.Recognizer() if AUDIO_SUPPORTED else None
        self._is_recording = False
        self._stop_event = threading.Event()

    @property
    def is_available(self) -> bool:
        return AUDIO_SUPPORTED

    def record_and_transcribe(
        self,
        duration: float = 4.0,
        on_status: Callable[[str], None] | None = None,
        on_result: Callable[[str | None], None] | None = None,
    ) -> threading.Thread:
        """Starts a background thread that records audio for `duration` seconds
        and transcribes it into text, invoking on_result(text).
        """
        thread = threading.Thread(
            target=self._worker,
            args=(duration, on_status, on_result),
            daemon=True,
            name="MicListenerThread",
        )
        thread.start()
        return thread

    def _worker(
        self,
        duration: float,
        on_status: Callable[[str], None] | None,
        on_result: Callable[[str | None], None] | None,
    ) -> None:
        if not AUDIO_SUPPORTED or not self.recognizer:
            if on_status:
                on_status("❌ Mic libraries missing")
            if on_result:
                on_result(None)
            return

        try:
            if on_status:
                on_status("🎙️ Listening...")
            logger.info(f"Starting mic recording for {duration}s at {self.sample_rate}Hz...")

            # Record using sounddevice
            recording = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
            )
            sd.wait()

            if on_status:
                on_status("🧠 Transcribing voice...")
            logger.info("Recording finished. Transcribing via SpeechRecognition...")

            # Convert numpy array to AudioData
            raw_data = recording.tobytes()
            audio_data = sr.AudioData(raw_data, self.sample_rate, 2)

            # Transcribe with Google Speech API (built into speech_recognition)
            try:
                text = self.recognizer.recognize_google(audio_data)
                logger.info(f"Transcribed voice speech: '{text}'")
                if on_status:
                    on_status("✅ Understood!")
                if on_result:
                    on_result(text)
            except sr.UnknownValueError:
                logger.warning("Speech recognizer could not understand audio.")
                if on_status:
                    on_status("⚠️ Could not hear clearly")
                if on_result:
                    on_result(None)
            except sr.RequestError as req_err:
                logger.warning(f"Google speech recognition network error: {req_err}")
                if on_status:
                    on_status("🌐 Speech network offline")
                if on_result:
                    on_result(None)

        except Exception as exc:
            logger.error(f"Error in mic listener worker: {exc}")
            if on_status:
                on_status(f"❌ Mic Error: {exc}")
            if on_result:
                on_result(None)


# Global singleton instance
listener = MicListener()
