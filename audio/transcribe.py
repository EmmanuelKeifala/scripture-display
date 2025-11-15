from faster_whisper import WhisperModel
import numpy as np
import threading
import warnings
from typing import Callable, Optional, List
from queue import Queue, Empty
import torch
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor
import time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.scripture_filter import filter_scripture_text

warnings.filterwarnings("ignore", category=UserWarning)

class WhisperTranscriber:
    MODELS = {
        'tiny': 'Fastest, less accurate (39M params)',
        'tiny.en': 'Fastest English-only (39M params)',
        'base': 'Fast, balanced (74M params)',
        'base.en': 'Fast English-only (74M params)',
        'small': 'Good accuracy, moderate speed (244M params)',
        'small.en': 'Good accuracy English-only (244M params)',
        'medium': 'High accuracy, slower (769M params)',
        'medium.en': 'High accuracy English-only (769M params)',
        'large-v2': 'Best accuracy, slowest (1550M params)',
        'large-v3': 'Latest best accuracy (1550M params)',
        'distil-small.en': 'Distilled: 6x faster than small.en',
        'distil-medium.en': 'Distilled: 6x faster than medium.en',
        'distil-large-v2': 'Distilled: 6x faster than large-v2'
    }
    
    def __init__(self, model_size: str = 'base', language: str = 'en', 
                 callback: Optional[Callable] = None, use_gpu: bool = True,
                 batch_size: int = 16, num_workers: int = 12):
        self.model_size = model_size
        self.language = language
        self.callback = callback
        self.use_gpu = use_gpu and torch.cuda.is_available()
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.model = None
        self.is_processing = False
        self.audio_queue = Queue(maxsize=100)
        self.processing_thread = None
        self.executor = ThreadPoolExecutor(max_workers=6)
        self._transcription_cache = {}
        self._cache_lock = threading.Lock()
    # (guard rails removed) simple pipeline: transcribe and forward results
        
    def load_model(self):
        if self.model is None:
            device = "cuda" if self.use_gpu else "cpu"
            
            if self.use_gpu:
                compute_type = "float16"
                print(f"Loading faster-whisper '{self.model_size}' model on GPU...")
            else:
                compute_type = "int8"
                print(f"Loading faster-whisper '{self.model_size}' model on CPU...")
            
            try:
                self.model = WhisperModel(
                    self.model_size,
                    device=device,
                    compute_type=compute_type,
                    num_workers=self.num_workers,
                    cpu_threads=self.num_workers,
                    download_root=None,
                    local_files_only=False
                )
                print(f"Model loaded: {self.model_size} on {device.upper()} with {compute_type}")
                print(f"Optimization: Using {self.num_workers} workers, batch size {self.batch_size}")
            except Exception as e:
                print(f"GPU loading failed, falling back to CPU: {e}")
                self.use_gpu = False
                self.model = WhisperModel(
                    self.model_size,
                    device="cpu",
                    compute_type="int8",
                    num_workers=self.num_workers
                )
                print(f"Model loaded on CPU with int8 quantization")
    
    def _preprocess_audio(self, audio_data: np.ndarray) -> np.ndarray:
        if len(audio_data.shape) > 1:
            audio_data = audio_data.flatten()
        
        audio_data = audio_data.astype(np.float32)
        
        if audio_data.max() > 1.0:
            audio_data = audio_data / 32768.0
        
        if np.abs(audio_data).max() < 0.001:
            return None
        
        return audio_data
    
    def _generate_cache_key(self, audio_data: np.ndarray) -> str:
        return str(hash(audio_data.tobytes()))[:16]
    
    def transcribe(self, audio_data: np.ndarray) -> dict:
        if self.model is None:
            self.load_model()
        
        audio_data = self._preprocess_audio(audio_data)
        if audio_data is None:
            return {'text': '', 'language': self.language, 'segments': []}
        
        cache_key = self._generate_cache_key(audio_data)
        with self._cache_lock:
            if cache_key in self._transcription_cache:
                return self._transcription_cache[cache_key]
        
    # NOTE: removed the long initial prompt and prefix to avoid biasing the model
    # into repeatedly emitting numeric verse tokens when audio is noisy.
        
        segments_list = []
        text_parts = []
        # Use conservative transcription settings to reduce hallucination/noise
        segments, info = self.model.transcribe(
            audio_data,
            language=self.language,
            beam_size=1,
            best_of=1,
            temperature=0.0,
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
            no_speech_threshold=0.6,
            condition_on_previous_text=False,
            word_timestamps=False,
            # we disabled VAD at the capture level; don't apply internal VAD here
            vad_filter=False,
            without_timestamps=True,
            suppress_blank=True,
            suppress_tokens=[-1]
        )
        
        for segment in segments:
            segments_list.append({
                'start': segment.start,
                'end': segment.end,
                'text': segment.text,
                'confidence': getattr(segment, 'avg_logprob', 0.0)
            })
            text_parts.append(segment.text)
        
        full_text = ' '.join(text_parts).strip()
        
        # Enhance and detect scripture references using the scripture filter
        filtered_text = filter_scripture_text(full_text)
        is_scripture = bool(filtered_text)

        result = {
            # raw transcription
            'text': full_text,
            # filtered/enhanced scripture-like text (empty if not scripture)
            'filtered_text': filtered_text,
            'is_scripture': is_scripture,
            'original_text': full_text,
            'language': info.language,
            'segments': segments_list,
            'language_probability': info.language_probability
        }
        
        with self._cache_lock:
            if len(self._transcription_cache) > 100:
                self._transcription_cache.clear()
            self._transcription_cache[cache_key] = result
        
        return result
    
    def _processing_loop(self):
        batch = []
        last_process_time = time.time()
        
        while self.is_processing:
            try:
                audio_chunk = self.audio_queue.get(timeout=0.1)
                
                if audio_chunk is None:
                    continue
                
                batch.append(audio_chunk)
                
                should_process = (
                    len(batch) >= self.batch_size or 
                    (len(batch) > 0 and time.time() - last_process_time > 0.2)
                )
                
                if should_process:
                    self._process_batch(batch)
                    batch = []
                    last_process_time = time.time()
                
            except Empty:
                if len(batch) > 0 and time.time() - last_process_time > 0.1:
                    self._process_batch(batch)
                    batch = []
                    last_process_time = time.time()
                continue
            except Exception as e:
                print(f"Transcription error: {e}")
                batch = []
    
    def _process_batch(self, batch: List[np.ndarray]):
        for audio_chunk in batch:
            try:
                result = self.transcribe(audio_chunk)
                # Forward any non-empty transcription immediately (no dedupe/filter)
                text = result.get('text', '').strip() if result else ''
                if text and self.callback:
                    self.executor.submit(self.callback, text, result)
            except Exception as e:
                print(f"Batch processing error: {e}")
    
    def start_processing(self):
        if self.is_processing:
            return
        
        self.load_model()
        self.is_processing = True
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        print("Whisper processing started")
    
    def stop_processing(self):
        if not self.is_processing:
            return
        
        self.is_processing = False
        
        if self.processing_thread:
            self.processing_thread.join(timeout=2.0)
            self.processing_thread = None
        
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except Empty:
                break
        
        self.executor.shutdown(wait=False)
        self.executor = ThreadPoolExecutor(max_workers=6)
        
        print("Whisper processing stopped")
    
    def add_audio(self, audio_chunk: np.ndarray):
        if self.is_processing:
            self.audio_queue.put(audio_chunk)
    
    def set_callback(self, callback: Callable):
        self.callback = callback
    
    def get_model_info(self) -> dict:
        return {
            'model': self.model_size,
            'device': 'GPU' if self.use_gpu else 'CPU',
            'batch_size': self.batch_size,
            'workers': self.num_workers,
            'language': self.language
        }
    
    @classmethod
    def get_available_models(cls):
        return cls.MODELS
    
    @staticmethod
    def is_gpu_available() -> bool:
        return torch.cuda.is_available()
    
    @staticmethod
    def get_optimal_batch_size() -> int:
        if torch.cuda.is_available():
            try:
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
                if gpu_memory > 8:
                    return 16
                elif gpu_memory > 4:
                    return 8
                else:
                    return 4
            except:
                return 4
        return 1
