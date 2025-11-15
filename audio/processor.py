from audio.capture import AudioCapture
from audio.transcribe import WhisperTranscriber
from typing import Callable, Optional
from utils.scripture_classifier import classify_text

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

        # Use LLM to classify whether this is scripture
        # keep recent raw chunks to allow cross-chunk detection
        try:
            if raw:
                self._raw_buffer.append(raw.strip())
                # trim buffer
                if len(self._raw_buffer) > self._raw_buffer_max:
                    self._raw_buffer = self._raw_buffer[-self._raw_buffer_max:]

            # Try direct classification first (single chunk)
            classification = classify_text(raw) if raw else None
            
            if classification and classification['is_scripture']:
                filtered = classification['cleaned'] or classification['text']
                print(f"  [LLM: SCRIPTURE] confidence={classification['confidence']:.2f} -> '{filtered}'")
                print(f"  [DEBUG] Callback set: {self.transcription_callback is not None}")
                
                if filtered and filtered != self._last_displayed_filtered:
                    self._last_displayed_filtered = filtered
                    # Augment result with classification info
                    result_with_class = dict(result) if result else {}
                    result_with_class['is_scripture'] = True
                    result_with_class['filtered_text'] = filtered
                    result_with_class['llm_confidence'] = classification['confidence']
                    
                    if self.transcription_callback:
                        print(f"  [INVOKING CALLBACK] with: '{filtered}'")
                        self.transcription_callback(filtered, result_with_class)
                    else:
                        print(f"  [WARNING] No callback set!")
                    # clear buffer after a successful detection (IMPORTANT: don't let sermon content accumulate)
                    self._raw_buffer = []
                    return
                else:
                    print(f"  [SKIPPED] Filtered same as last: '{filtered}' == '{self._last_displayed_filtered}'")

            # If not scripture alone, try combined buffer
            combined = ' '.join([p for p in self._raw_buffer if p])
            if combined and combined != raw:
                combined_classification = classify_text(combined)
                print(f"  [LLM: COMBINED] '{combined}' -> is_scripture={combined_classification['is_scripture']}, confidence={combined_classification['confidence']:.2f}")
                
                if combined_classification['is_scripture']:
                    filtered = combined_classification['cleaned'] or combined
                    if filtered and filtered != self._last_displayed_filtered:
                        self._last_displayed_filtered = filtered
                        synthetic_result = {
                            'text': combined,
                            'filtered_text': filtered,
                            'is_scripture': True,
                            'original_text': combined,
                            'language': result.get('language') if result else 'en',
                            'segments': [],
                            'language_probability': 1.0,
                            'llm_confidence': combined_classification['confidence']
                        }
                        if self.transcription_callback:
                            self.transcription_callback(filtered, synthetic_result)
                        # clear buffer after detection to avoid repeats
                        self._raw_buffer = []
                        return
        except Exception as e:
            print(f"  [LLM classification error: {e}]")
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
