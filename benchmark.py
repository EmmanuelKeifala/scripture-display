#!/usr/bin/env python3
"""
Benchmark script to test Whisper performance optimizations
"""

import time
import numpy as np
from audio.processor import AudioProcessor
from config.performance import get_optimal_config, print_system_info

def create_test_audio(duration=5.0, sample_rate=16000):
    """Create test audio signal"""
    t = np.linspace(0, duration, int(sample_rate * duration))
    # Create a mix of frequencies to simulate speech
    audio = (
        0.3 * np.sin(2 * np.pi * 440 * t) +  # A4 note
        0.2 * np.sin(2 * np.pi * 880 * t) +  # A5 note
        0.1 * np.random.normal(0, 0.1, len(t))  # Noise
    )
    return audio.astype(np.float32)

def benchmark_transcription():
    """Benchmark transcription performance"""
    print("=== Whisper Performance Benchmark ===\n")
    
    # Print system info
    print_system_info()
    print()
    
    # Test different models
    models_to_test = ['tiny.en', 'base.en', 'small.en']
    test_audio = create_test_audio(duration=3.0)
    
    results = []
    
    for model in models_to_test:
        print(f"Testing {model} model...")
        
        # Create processor
        processor = AudioProcessor(model_size=model)
        
        # Measure model loading time
        start_time = time.time()
        processor.transcriber.load_model()
        load_time = time.time() - start_time
        
        # Measure transcription time
        start_time = time.time()
        result = processor.transcriber.transcribe(test_audio)
        transcribe_time = time.time() - start_time
        
        # Calculate metrics
        audio_duration = len(test_audio) / 16000
        real_time_factor = transcribe_time / audio_duration
        
        results.append({
            'model': model,
            'load_time': load_time,
            'transcribe_time': transcribe_time,
            'real_time_factor': real_time_factor,
            'text': result.get('text', ''),
            'confidence': result.get('language_probability', 0)
        })
        
        print(f"  Load time: {load_time:.2f}s")
        print(f"  Transcription time: {transcribe_time:.2f}s")
        print(f"  Real-time factor: {real_time_factor:.2f}x")
        print(f"  Text: '{result.get('text', 'No text')[:50]}...'")
        print()
    
    # Print summary
    print("=== Performance Summary ===")
    print(f"{'Model':<15} {'Load (s)':<10} {'Trans (s)':<10} {'RT Factor':<10} {'Quality'}")
    print("-" * 60)
    
    for r in results:
        quality = "★★★★★" if r['confidence'] > 0.9 else "★★★★☆" if r['confidence'] > 0.8 else "★★★☆☆"
        print(f"{r['model']:<15} {r['load_time']:<10.2f} {r['transcribe_time']:<10.2f} {r['real_time_factor']:<10.2f} {quality}")
    
    # Recommendations
    print("\n=== Recommendations ===")
    fastest = min(results, key=lambda x: x['real_time_factor'])
    print(f"Fastest model: {fastest['model']} ({fastest['real_time_factor']:.2f}x real-time)")
    
    if any(r['real_time_factor'] < 1.0 for r in results):
        real_time_models = [r for r in results if r['real_time_factor'] < 1.0]
        best_real_time = min(real_time_models, key=lambda x: x['real_time_factor'])
        print(f"Best real-time model: {best_real_time['model']} ({best_real_time['real_time_factor']:.2f}x)")
    else:
        print("No models achieved real-time performance. Consider using 'tiny.en' or distilled models.")

def benchmark_vad():
    """Benchmark VAD performance"""
    print("\n=== VAD Performance Test ===")
    
    from audio.vad import AdvancedVAD
    
    # Create test audio with speech and silence
    sample_rate = 16000
    duration = 2.0
    
    # Speech segment
    t = np.linspace(0, duration/2, int(sample_rate * duration/2))
    speech = 0.5 * np.sin(2 * np.pi * 440 * t) + 0.1 * np.random.normal(0, 0.1, len(t))
    
    # Silence segment
    silence = np.zeros(int(sample_rate * duration/2))
    
    # Combined audio
    test_audio = np.concatenate([speech, silence]).astype(np.float32)
    
    # Test VAD
    vad = AdvancedVAD(sample_rate=sample_rate, threshold=0.35)
    
    start_time = time.time()
    is_speech = vad.is_speech(test_audio)
    vad_time = time.time() - start_time
    
    segments = vad.get_speech_segments(test_audio)
    
    print(f"VAD processing time: {vad_time*1000:.2f}ms")
    print(f"Speech detected: {is_speech}")
    print(f"Speech segments: {len(segments)}")
    print(f"Using Silero VAD: {vad.use_silero}")

if __name__ == "__main__":
    try:
        benchmark_transcription()
        benchmark_vad()
        
        print("\n=== Optimization Tips ===")
        print("1. Use 'tiny.en' or 'base.en' for real-time applications")
        print("2. Use distilled models (distil-small.en) for 6x speed improvement")
        print("3. Enable GPU if available for significant speedup")
        print("4. Reduce chunk_duration to 1.0s for even faster response")
        print("5. Lower VAD threshold to 0.3 for more sensitive speech detection")
        
    except Exception as e:
        print(f"Benchmark failed: {e}")
        print("Make sure all dependencies are installed and models are available.")
