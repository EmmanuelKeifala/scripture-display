from audio.capture import AudioCapture
from audio.transcribe import WhisperTranscriber
from typing import Callable, Optional
from utils.scripture_filter import filter_scripture_text

class AudioProcessor:
    def __init__(self, model_size: str = 'base', transcription_callback: Optional[Callable] = None):
        self.model_size = model_size
        self.transcription_callback = transcription_callback
        
        self.capture = AudioCapture(
            sample_rate=16000,
            channels=1,
            chunk_duration=1.5,
            # VAD disabled to stream raw chunks directly to the transcriber
            use_vad=False,
            vad_threshold=0.4
        )
        
        self.transcriber = WhisperTranscriber(
            model_size=model_size,
            language='en',
            use_gpu=True,
            batch_size=16,
            num_workers=12
        )
        
        self.capture.set_callback(self._on_audio_chunk)
        self.transcriber.set_callback(self._on_transcription)
        
        self.is_running = False
        # buffer recent raw transcriptions to combine fragmented phrases
        self._raw_buffer = []
        self._raw_buffer_max = 5  # increased from 3 to handle more fragmentation
        self._last_displayed_filtered = None
    
    def _on_audio_chunk(self, audio_chunk):
        self.transcriber.add_audio(audio_chunk)
    
    def _on_transcription(self, text, result):
        # Always log raw transcription for diagnostics
        try:
            raw = result.get('text', '') if result else text
            print(f"RAW TRANSCRIBED: {raw}")
        except Exception:
            pass

        # Only forward/display when detected as scripture
        # keep recent raw chunks to allow cross-chunk detection (e.g. "John." + "Chapter 1")
        try:
            if raw:
                self._raw_buffer.append(raw.strip())
                # trim buffer
                if len(self._raw_buffer) > self._raw_buffer_max:
                    self._raw_buffer = self._raw_buffer[-self._raw_buffer_max:]

            # If the model already flagged this chunk as scripture, forward it
            if self.transcription_callback and result and result.get('is_scripture'):
                filtered = result.get('filtered_text', result.get('text', ''))
                print(f"  [Model flagged as scripture] -> filtered: '{filtered}'")
                if filtered and filtered != self._last_displayed_filtered:
                    self._last_displayed_filtered = filtered
                    self.transcription_callback(filtered, result)
                    # clear buffer after a successful detection
                    self._raw_buffer = []
                return

            # Attempt combined detection from recent raw chunks
            combined = ' '.join([p for p in self._raw_buffer if p])
            if combined:
                combined_filtered = filter_scripture_text(combined)
                # DEBUG: show what the filter decided
                print(f"  [Combined attempt] buffer={self._raw_buffer} -> combined='{combined}'")
                print(f"  [Combined attempt] filtered='{combined_filtered}'")
                
                if combined_filtered and combined_filtered != self._last_displayed_filtered:
                    self._last_displayed_filtered = combined_filtered
                    synthetic_result = {
                        'text': combined,
                        'filtered_text': combined_filtered,
                        'is_scripture': True,
                        'original_text': combined,
                        'language': result.get('language') if result else 'en',
                        'segments': [],
                        'language_probability': 1.0
                    }
                    if self.transcription_callback:
                        self.transcription_callback(combined_filtered, synthetic_result)
                    # clear buffer after detection to avoid repeats
                    self._raw_buffer = []
                    return
        except Exception:
            # Don't let detection errors break the pipeline
            pass
    
    def start(self):
        if self.is_running:
            return
        
        print(f"Starting audio processor with '{self.model_size}' model...")
        
        self.transcriber.start_processing()
        self.capture.start()
        
        self.is_running = True
        print("Audio processor started")
    
    def stop(self):
        if not self.is_running:
            return
        
        print("Stopping audio processor...")
        
        self.capture.stop()
        self.transcriber.stop_processing()
        
        self.is_running = False
        print("Audio processor stopped")
    
    def set_transcription_callback(self, callback: Callable):
        self.transcription_callback = callback
        self.transcriber.set_callback(self._on_transcription)
    
    def change_model(self, model_size: str):
        was_running = self.is_running
        
        if was_running:
            self.stop()
        
        self.model_size = model_size
        self.transcriber = WhisperTranscriber(
            model_size=model_size,
            language='en',
            use_gpu=True,
            batch_size=16,
            num_workers=12
        )
        self.transcriber.set_callback(self._on_transcription)
        
        if was_running:
            self.start()
    
    def is_active(self) -> bool:
        return self.is_running
