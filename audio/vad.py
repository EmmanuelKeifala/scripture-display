import numpy as np
import torch
from typing import Optional, List, Tuple
import warnings
from functools import lru_cache
import threading
from concurrent.futures import ThreadPoolExecutor

warnings.filterwarnings("ignore", category=UserWarning)

class AdvancedVAD:
    def __init__(self, sample_rate: int = 16000, threshold: float = 0.4):
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.model = None
        self.use_silero = False
        self._cache = {}
        self._cache_lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        try:
            self.model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False
            )
            self.get_speech_timestamps = utils[0]
            self.use_silero = True
            print("Silero-VAD loaded successfully")
        except Exception as e:
            print(f"Silero-VAD not available, using energy-based VAD: {e}")
            self.model = None
    
    def is_speech(self, audio_data: np.ndarray) -> bool:
        if audio_data is None or len(audio_data) == 0:
            return False
        
        if self.use_silero and self.model is not None:
            return self._silero_vad(audio_data)
        else:
            return self._energy_vad(audio_data)
    
    def _silero_vad(self, audio_data: np.ndarray) -> bool:
        try:
            if len(audio_data.shape) > 1:
                audio_data = audio_data.flatten()
            
            audio_tensor = torch.from_numpy(audio_data).float()
            
            if audio_tensor.shape[0] < 512:
                return False
            
            speech_timestamps = self.get_speech_timestamps(
                audio_tensor,
                self.model,
                sampling_rate=self.sample_rate,
                threshold=self.threshold,
                min_speech_duration_ms=300,
                min_silence_duration_ms=100,
                speech_pad_ms=50,
                return_seconds=False
            )
            
            if len(speech_timestamps) > 0:
                total_speech = sum(ts['end'] - ts['start'] for ts in speech_timestamps)
                speech_ratio = total_speech / len(audio_data)
                return speech_ratio > 0.3
            
            return False
        
        except Exception as e:
            print(f"Silero VAD error: {e}")
            return self._energy_vad(audio_data)
    
    def _energy_vad(self, audio_data: np.ndarray) -> bool:
        if len(audio_data.shape) > 1:
            audio_data = audio_data.flatten()
        
        energy = np.sum(audio_data ** 2) / len(audio_data)
        
        if energy < 1e-6:
            return False
        
        zcr = np.sum(np.abs(np.diff(np.sign(audio_data)))) / (2 * len(audio_data))
        
        energy_threshold = 0.001
        zcr_threshold = 0.08
        
        return energy > energy_threshold and zcr > zcr_threshold
    
    def get_speech_segments(self, audio_data: np.ndarray) -> List[Tuple[int, int]]:
        if not self.use_silero or self.model is None:
            return [(0, len(audio_data))] if self.is_speech(audio_data) else []
        
        try:
            if len(audio_data.shape) > 1:
                audio_data = audio_data.flatten()
            
            audio_tensor = torch.from_numpy(audio_data).float()
            
            speech_timestamps = self.get_speech_timestamps(
                audio_tensor,
                self.model,
                sampling_rate=self.sample_rate,
                threshold=self.threshold,
                min_speech_duration_ms=250,
                min_silence_duration_ms=100
            )
            
            return [(ts['start'], ts['end']) for ts in speech_timestamps]
        
        except Exception as e:
            print(f"Speech segmentation error: {e}")
            return [(0, len(audio_data))] if self._energy_vad(audio_data) else []
    
    def filter_silence(self, audio_data: np.ndarray) -> Optional[np.ndarray]:
        if not self.is_speech(audio_data):
            return None
        
        segments = self.get_speech_segments(audio_data)
        if not segments:
            return None
        
        speech_audio = []
        for start, end in segments:
            speech_audio.extend(audio_data[start:end])
        
        return np.array(speech_audio, dtype=np.float32) if speech_audio else None
