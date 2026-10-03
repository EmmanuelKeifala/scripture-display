import os
import queue
import threading
from typing import Callable, Optional

import numpy as np
from faster_whisper import WhisperModel


class WhisperTranscriber:
    """Transcribes utterances on a worker thread and calls callback(text, final)."""

    def __init__(self, model_size: str = 'base', language: str = 'en',
                 callback: Optional[Callable] = None):
        self.model_size = model_size
        self.language = language
        self.callback = callback
        self.model = None
        self.is_processing = False
        self.audio_queue = queue.Queue(maxsize=20)
        self._partial = None  # newest in-progress audio; older ones are simply overwritten
        self.processing_thread = None

    def load_model(self):
        if self.model is None:
            print(f"Loading faster-whisper '{self.model_size}' model...")
            self.model = WhisperModel(
                self.model_size,
                device="auto",
                compute_type="int8",
                cpu_threads=max(1, (os.cpu_count() or 2) // 2),
            )
            print("Model loaded")

    def transcribe(self, audio: np.ndarray, final: bool = True) -> str:
        self.load_model()
        audio = audio - audio.mean()
        peak = np.abs(audio).max()
        if peak > 0:
            audio = audio * (0.9 / peak)
        # No initial_prompt or hotwords on purpose: on unclear audio Whisper echoes
        # them ("Thessalonians chapter 5 verse...", measured), which would put false
        # verses on screen. temperature=0 disables the retry-on-doubt decoding that
        # otherwise stalls a single utterance for many seconds.
        segments, _ = self.model.transcribe(
            audio,
            language=self.language,
            beam_size=5 if final else 1,
            vad_filter=True,
            condition_on_previous_text=False,
            temperature=0.0,
        )
        return ' '.join(s.text.strip() for s in segments if s.no_speech_prob < 0.6).strip()

    def add_audio(self, audio: np.ndarray, final: bool = True):
        if not final:
            self._partial = audio
            return
        self._partial = None
        try:
            self.audio_queue.put_nowait(audio)
        except queue.Full:
            # Falling behind real time: drop the oldest utterance, keep the newest
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                pass
            self.audio_queue.put_nowait(audio)

    def _processing_loop(self):
        while self.is_processing:
            try:
                audio, final = self.audio_queue.get(timeout=0.05), True
            except queue.Empty:
                audio, self._partial, final = self._partial, None, False
                if audio is None:
                    continue
            try:
                text = self.transcribe(audio, final)
                if text and self.callback:
                    self.callback(text, final)
            except Exception as e:
                print(f"Transcription error: {e}")

    def start_processing(self):
        if self.is_processing:
            return
        self.load_model()
        self.is_processing = True
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()

    def stop_processing(self):
        if not self.is_processing:
            return
        self.is_processing = False
        self.processing_thread.join(timeout=2.0)
        self.processing_thread = None
        while not self.audio_queue.empty():
            self.audio_queue.get_nowait()
