"""
Performance configuration for optimized Whisper transcription
Tuned for maximum speed and accuracy balance
"""

import multiprocessing
import torch

# System detection
CPU_CORES = multiprocessing.cpu_count()
try:
    HAS_GPU = torch.cuda.is_available()
except:
    HAS_GPU = False

# Audio capture settings
AUDIO_CONFIG = {
    'sample_rate': 16000,
    'channels': 1,
    'chunk_duration': 1.5,  # Reduced for faster processing
    'blocksize': 512,       # Smaller blocks for lower latency
    'queue_maxsize': 100,   # Larger queue for better buffering
}

# VAD settings - optimized for speed and sensitivity
VAD_CONFIG = {
    'threshold': 0.35,                    # More sensitive
    'min_speech_duration_ms': 150,        # Faster detection
    'min_silence_duration_ms': 50,        # Less silence required
    'speech_pad_ms': 20,                  # Minimal padding
    'max_silence_chunks': 2,              # Quick silence cutoff
    'energy_threshold': 0.0005,           # More sensitive energy
    'zcr_threshold': 0.05,                # Lower ZCR threshold
}

# Whisper model settings - optimized for accuracy and speed
WHISPER_CONFIG = {
    'batch_size': 16 if HAS_GPU else 4,
    'num_workers': min(12, CPU_CORES),
    'use_gpu': HAS_GPU,
    'compute_type': 'float16' if HAS_GPU else 'int8',
    'executor_workers': 6,
    'queue_maxsize': 100,
    'cache_size': 100,
}

# Transcription parameters - balanced for speed and accuracy
TRANSCRIPTION_PARAMS = {
    'beam_size': 3,                       # Reduced for speed
    'best_of': 3,                         # Reduced for speed
    'temperature': [0.0, 0.1, 0.2],       # Fewer temperature steps
    'compression_ratio_threshold': 2.2,
    'log_prob_threshold': -0.8,           # More lenient
    'no_speech_threshold': 0.4,           # More sensitive
    'condition_on_previous_text': True,
    'word_timestamps': False,             # Disabled for speed
    'without_timestamps': True,           # Faster processing
    'suppress_blank': True,
    'suppress_tokens': [-1],
}

# VAD parameters for Whisper
WHISPER_VAD_PARAMS = {
    'threshold': 0.35,
    'min_speech_duration_ms': 150,
    'max_speech_duration_s': 30.0,
    'min_silence_duration_ms': 500,
    'speech_pad_ms': 200,
}

# Processing timing - optimized for real-time
PROCESSING_CONFIG = {
    'batch_timeout': 0.2,                 # Process batches quickly
    'empty_timeout': 0.1,                 # Handle empty queues fast
    'processing_timeout': 0.1,            # Quick processing loop
    'shutdown_timeout': 2.0,
}

# Model recommendations based on use case
MODEL_RECOMMENDATIONS = {
    'fastest': 'tiny.en',          # Ultra-fast, basic accuracy
    'balanced': 'base.en',         # Good balance (recommended)
    'accurate': 'small.en',        # Better accuracy, slower
    'best': 'medium.en',           # High accuracy, much slower
    'distilled_fast': 'distil-small.en',    # 6x faster than small
    'distilled_accurate': 'distil-medium.en', # 6x faster than medium
}

def get_optimal_config():
    """Get optimal configuration based on system capabilities"""
    config = {
        'audio': AUDIO_CONFIG,
        'vad': VAD_CONFIG,
        'whisper': WHISPER_CONFIG,
        'transcription': TRANSCRIPTION_PARAMS,
        'whisper_vad': WHISPER_VAD_PARAMS,
        'processing': PROCESSING_CONFIG,
    }
    
    # Adjust based on system
    if not HAS_GPU:
        config['whisper']['batch_size'] = 4
        config['whisper']['num_workers'] = min(4, CPU_CORES)
        config['processing']['batch_timeout'] = 0.5
    
    return config

def print_system_info():
    """Print system information for optimization"""
    print(f"System Configuration:")
    print(f"  CPU Cores: {CPU_CORES}")
    print(f"  GPU Available: {HAS_GPU}")
    if HAS_GPU:
        try:
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
            print(f"  GPU: {gpu_name}")
            print(f"  GPU Memory: {gpu_memory:.1f}GB")
        except:
            print("  GPU: Available but details unavailable")
    
    config = get_optimal_config()
    print(f"\nOptimal Settings:")
    print(f"  Batch Size: {config['whisper']['batch_size']}")
    print(f"  Workers: {config['whisper']['num_workers']}")
    print(f"  Chunk Duration: {config['audio']['chunk_duration']}s")
    print(f"  VAD Threshold: {config['vad']['threshold']}")

if __name__ == "__main__":
    print_system_info()
