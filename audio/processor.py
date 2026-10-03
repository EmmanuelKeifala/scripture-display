import os
from pathlib import Path
from typing import Callable, Optional

from audio.capture import AudioCapture
from audio.deepgram import DeepgramTranscriber
from audio.transcribe import WhisperTranscriber

KEY_FILE = Path(__file__).parent.parent / ".deepgram_key"


def deepgram_api_key() -> Optional[str]:
    """DEEPGRAM_API_KEY from the environment, else the first line of .deepgram_key."""
    key = os.environ.get("DEEPGRAM_API_KEY")
    if not key and KEY_FILE.exists():
        # Accept both the bare key and a "DEEPGRAM_API_KEY=..." line
        key = KEY_FILE.read_text().strip().split('=')[-1].strip().strip('"\'')
    return key or None


class AudioProcessor:
    """Microphone -> transcription_callback(text, final).

    With a Deepgram key the audio is streamed to the cloud; the local Whisper
    model only transcribes while the cloud is unreachable, or when there is no key.
    """

    def __init__(self, model_size: str = 'small.en', transcription_callback: Optional[Callable] = None,
                 status_callback: Optional[Callable] = None):
        self.transcriber = WhisperTranscriber(model_size=model_size, callback=transcription_callback)
        key = deepgram_api_key()
        self.cloud = DeepgramTranscriber(key, transcription_callback, status_callback=status_callback) if key else None
        self.capture = AudioCapture(
            callback=self._on_utterance,
            status_callback=status_callback,
            frame_callback=self.cloud.send if self.cloud else None,
        )
        self.is_running = False

    def _on_utterance(self, audio, final):
        if not (self.cloud and self.cloud.connected):
            self.transcriber.add_audio(audio, final)

    def start(self):
        if self.is_running:
            return
        self.transcriber.start_processing()
        if self.cloud:
            self.cloud.start()
        self.capture.start()
        self.is_running = True

    def stop(self):
        if not self.is_running:
            return
        self.capture.stop()
        if self.cloud:
            self.cloud.stop()
        self.transcriber.stop_processing()
        self.is_running = False

    def set_source(self, source):
        self.capture.set_source(source)

    def is_active(self) -> bool:
        return self.is_running
