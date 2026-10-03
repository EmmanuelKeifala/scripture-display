import json
import threading
import time
from typing import Callable, Optional
from urllib.parse import urlencode

import websocket

from scripture.book_mappings import BOOK_NAMES

URL = "wss://api.deepgram.com/v1/listen"
RETRY_SECONDS = 10
MAX_UTTERANCE_CHARS = 300  # flush a pause-free run of speech so it cannot grow forever


class DeepgramTranscriber:
    """Streams microphone audio to Deepgram and calls callback(text, final).

    `connected` is False whenever the service is unreachable (no internet, bad
    key), which is the caller's cue to use the local model instead. It keeps
    retrying in the background and takes over again once it reconnects.
    """

    def __init__(self, api_key: str, callback: Callable, sample_rate: int = 16000,
                 status_callback: Optional[Callable] = None):
        self.api_key = api_key
        self.callback = callback
        self.status_callback = status_callback
        self.connected = False
        self._ws = None
        self._running = False
        self._thread = None
        self._parts = []  # finalized pieces of the utterance still being spoken

        params = [
            ("model", "nova-3"),
            ("language", "en"),
            # ponytail: raw 16-bit PCM is ~115MB/hour of upload; switch to Opus
            # (PyAV is already installed) if mobile data cost matters
            ("encoding", "linear16"),
            ("sample_rate", sample_rate),
            ("channels", 1),
            ("interim_results", "true"),
            ("endpointing", 500),
            ("smart_format", "true"),
            ("numerals", "true"),
        ]
        # Book names as key terms so "Habakkuk" and "Colossians" come out spelled right
        params += [("keyterm", name) for name in sorted({name.split()[-1] for name in BOOK_NAMES})]
        self._url = f"{URL}?{urlencode(params)}"

    def _status(self, message: str):
        print(message)
        if self.status_callback:
            self.status_callback(message)

    def send(self, pcm: bytes):
        """Called from the audio thread with each frame of 16-bit PCM."""
        if not self.connected:
            return
        try:
            self._ws.send_binary(pcm)
        except Exception:
            self.connected = False  # the receive loop notices and reconnects

    def _on_message(self, message: str):
        data = json.loads(message)
        if data.get("type") != "Results":
            return
        text = data["channel"]["alternatives"][0]["transcript"].strip()

        if not data.get("is_final"):
            if text:
                self.callback(" ".join(self._parts + [text]), False)
            return

        if text:
            self._parts.append(text)
        utterance = " ".join(self._parts)
        if not utterance:
            return
        # speech_final is not reliably set once the speaker has gone quiet; an
        # empty finalized chunk after some speech means the same thing
        if data.get("speech_final") or not text or len(utterance) > MAX_UTTERANCE_CHARS:
            self._parts = []
            self.callback(utterance, True)
        else:
            self.callback(utterance, False)

    def _run(self):
        failing = False
        while self._running:
            try:
                self._ws = websocket.create_connection(
                    self._url, header=[f"Authorization: Token {self.api_key}"], timeout=15
                )
                self._parts = []
                self.connected = True
                failing = False
                self._status("Deepgram connected - using cloud transcription")
                while self._running and self.connected:
                    # Results arrive continuously while audio flows, so a 15s
                    # silence from the server means the link is dead
                    self._on_message(self._ws.recv())
            except Exception as e:
                if self._running and not failing:
                    reason = str(e).split(' -+-+- ')[0]  # drop the HTTP headers websocket-client appends
                    self._status(f"Deepgram unavailable ({reason}) - using local model")
                    failing = True
            finally:
                self.connected = False
                if self._ws:
                    try:
                        self._ws.close()
                    except Exception:
                        pass
            deadline = time.time() + RETRY_SECONDS
            while self._running and time.time() < deadline:
                time.sleep(0.2)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self.connected = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
