import sounddevice as sd
import numpy as np
import queue
import threading
from typing import Callable, Optional
from audio.vad import AdvancedVAD

class AudioCapture:
    def __init__(self, sample_rate: int = 16000, channels: int = 1, 
                 chunk_duration: float = 1.5, callback: Optional[Callable] = None,
                 use_vad: bool = True, vad_threshold: float = 0.4):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_duration = chunk_duration
        self.chunk_size = int(sample_rate * chunk_duration)
        self.callback = callback
        self.use_vad = use_vad
        
        self.audio_queue = queue.Queue(maxsize=100)
        self.is_recording = False
        self.stream = None
        self.buffer = []
        
        self.vad = AdvancedVAD(sample_rate=sample_rate, threshold=vad_threshold) if use_vad else None
        self.speech_buffer = []
        self.silence_duration = 0
        self.max_silence_chunks = 2
        
    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(f"Audio status: {status}")
        
        if self.is_recording:
            audio_data = indata.copy().flatten()
            self.buffer.extend(audio_data)
            
            if len(self.buffer) >= self.chunk_size:
                chunk = np.array(self.buffer[:self.chunk_size], dtype=np.float32)
                self.buffer = self.buffer[self.chunk_size:]
                
                if self.use_vad and self.vad:
                    if self.vad.is_speech(chunk):
                        self.speech_buffer.extend(chunk)
                        self.silence_duration = 0
                    else:
                        self.silence_duration += 1
                        
                        if len(self.speech_buffer) > 0:
                            self.speech_buffer.extend(chunk)
                    
                    if len(self.speech_buffer) >= self.chunk_size or \
                       (len(self.speech_buffer) > 0 and self.silence_duration >= self.max_silence_chunks):
                        
                        speech_chunk = np.array(self.speech_buffer[:self.chunk_size], dtype=np.float32)
                        self.speech_buffer = self.speech_buffer[self.chunk_size:] if len(self.speech_buffer) > self.chunk_size else []
                        
                        if self.callback:
                            self.callback(speech_chunk)
                        else:
                            try:
                                self.audio_queue.put_nowait(speech_chunk)
                            except queue.Full:
                                pass
                        
                        if self.silence_duration >= self.max_silence_chunks:
                            self.speech_buffer = []
                            self.silence_duration = 0
                else:
                    if self.callback:
                        self.callback(chunk)
                    else:
                        try:
                            self.audio_queue.put_nowait(chunk)
                        except queue.Full:
                            pass
    
    def start(self):
        if self.is_recording:
            return
        
        self.is_recording = True
        self.buffer = []
        self.speech_buffer = []
        self.silence_duration = 0
        
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=self._audio_callback,
            blocksize=512,
            dtype='float32',
            latency='low'
        )
        self.stream.start()
        vad_status = "with VAD" if self.use_vad else "without VAD"
        print(f"Audio capture started: {self.sample_rate}Hz, {self.chunk_duration}s chunks {vad_status}")
    
    def stop(self):
        if not self.is_recording:
            return
        
        self.is_recording = False
        
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        self.buffer = []
        self.speech_buffer = []
        self.silence_duration = 0
        print("Audio capture stopped")
    
    def get_chunk(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def clear_queue(self):
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
    
    def set_callback(self, callback: Callable):
        self.callback = callback
    
    def is_active(self) -> bool:
        return self.is_recording
