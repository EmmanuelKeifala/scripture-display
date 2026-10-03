import collections
import json
import os
import subprocess
from typing import Callable, Dict, Optional, Union

import numpy as np
import sounddevice as sd
import webrtcvad

FRAME_MS = 30  # webrtcvad only accepts 10/20/30ms frames


def list_sources() -> Dict[str, Union[str, int]]:
    """Attached audio inputs as {label: source}, for AudioCapture.set_source().

    On PipeWire the source is a node name (every mic, USB sound card and line-in
    the desktop knows about); elsewhere it is a sounddevice input index.
    """
    try:
        dump = subprocess.run(["pw-dump"], capture_output=True, text=True, timeout=3, check=True).stdout
        props = [node.get("info", {}).get("props", {}) for node in json.loads(dump)]
        return {p.get("node.description") or p["node.name"]: p["node.name"]
                for p in props if p.get("media.class", "").startswith("Audio/Source")}
    except (OSError, subprocess.SubprocessError, ValueError):
        # ponytail: raw devices are opened at 16kHz as-is; add resampling if one refuses that rate
        return {d["name"]: i for i, d in enumerate(sd.query_devices()) if d["max_input_channels"] > 0}


class AudioCapture:
    """Microphone -> utterances split on silence, via callback(audio, final).

    While someone is still speaking, the last few seconds are also sent every
    partial_ms with final=False, so a verse can go up before they pause.
    """

    def __init__(self, callback: Callable, sample_rate: int = 16000, aggressiveness: int = 2,
                 silence_ms: int = 600, max_seconds: float = 12, min_speech_ms: int = 240,
                 partial_ms: int = 1000, partial_window_seconds: float = 6,
                 status_callback: Optional[Callable] = None,
                 frame_callback: Optional[Callable] = None):
        self.callback = callback
        self.status_callback = status_callback
        self.frame_callback = frame_callback  # every 30ms frame as 16-bit PCM bytes
        self.source = None  # None = system default; see list_sources()
        self.sample_rate = sample_rate
        self.frame_size = sample_rate * FRAME_MS // 1000
        # Tuning knobs: raise aggressiveness (0-3) in a noisy room, raise
        # silence_ms if a slow speaker gets cut mid-reference.
        self.vad = webrtcvad.Vad(aggressiveness)
        self.silence_frames = silence_ms // FRAME_MS
        self.max_frames = int(max_seconds * 1000) // FRAME_MS
        self.min_speech_frames = min_speech_ms // FRAME_MS
        self.partial_frames = partial_ms // FRAME_MS
        self.partial_window = int(partial_window_seconds * sample_rate)
        self.stream = None
        self._reset()

    def _reset(self):
        self._preroll = collections.deque(maxlen=10)  # 300ms kept from before speech starts
        self._frames = []
        self._speech = 0
        self._silence = 0
        self._dc = None
        self._dead_frames = 0

    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(f"Audio status: {status}")
        if len(indata) != self.frame_size:
            return

        # A muted mic delivers exact zeros; say so once instead of sitting there deaf
        self._dead_frames = 0 if indata.any() else self._dead_frames + 1
        if self._dead_frames == 3000 // FRAME_MS and self.status_callback:
            self.status_callback("Microphone is completely silent - is it muted?")

        # Some laptop mics sit on a large constant offset that drowns the speech;
        # track it slowly and subtract it.
        mean = float(indata.mean())
        self._dc = mean if self._dc is None else 0.95 * self._dc + 0.05 * mean
        frame = indata[:, 0] - self._dc
        pcm = (np.clip(frame, -1, 1) * 32767).astype(np.int16).tobytes()
        if self.frame_callback:
            self.frame_callback(pcm)
        is_speech = self.vad.is_speech(pcm, self.sample_rate)

        if not self._frames:
            self._preroll.append(frame)
            if not is_speech:
                return
            self._frames = list(self._preroll)
            self._preroll.clear()
        else:
            self._frames.append(frame)

        if is_speech:
            self._speech += 1
            self._silence = 0
        else:
            self._silence += 1

        if self._silence >= self.silence_frames or len(self._frames) >= self.max_frames:
            if self._speech >= self.min_speech_frames:
                self.callback(np.concatenate(self._frames), True)
            self._frames = []
            self._speech = 0
            self._silence = 0
        elif len(self._frames) % self.partial_frames == 0 and self._speech >= self.min_speech_frames:
            self.callback(np.concatenate(self._frames)[-self.partial_window:], False)

    def start(self):
        if self.stream:
            return
        self._reset()
        device = self.source
        if isinstance(self.source, str):
            # pipewire-alsa reads the target node from the environment when the stream opens
            os.environ["PIPEWIRE_NODE"] = self.source
            device = "pipewire"
        else:
            os.environ.pop("PIPEWIRE_NODE", None)
        self.stream = sd.InputStream(
            device=device,
            samplerate=self.sample_rate,
            channels=1,
            dtype='float32',
            blocksize=self.frame_size,
            callback=self._audio_callback,
        )
        self.stream.start()
        print(f"Audio capture started: {self.sample_rate}Hz, splitting on silence")

    def set_source(self, source):
        """Switch input; takes effect immediately if already listening."""
        self.source = source
        if self.stream:
            self.stop()
            self.start()

    def stop(self):
        if not self.stream:
            return
        self.stream.stop()
        self.stream.close()
        self.stream = None
        print("Audio capture stopped")
