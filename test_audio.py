import time
from audio.processor import AudioProcessor

def on_transcription(text, result):
    print(f"\n{'='*60}")
    print(f"Transcribed: {text}")
    print(f"Language: {result['language']}")
    print(f"{'='*60}\n")

def main():
    print("Audio Processing Test")
    print("=" * 60)
    print("\nThis test will:")
    print("1. Load the Whisper 'base' model")
    print("2. Start listening to your microphone")
    print("3. Transcribe speech in 3-second chunks")
    print("4. Display transcriptions")
    print("\nPress Ctrl+C to stop\n")
    
    processor = AudioProcessor(
        model_size='base',
        transcription_callback=on_transcription
    )
    
    try:
        print("Starting audio processor...")
        processor.start()
        print("Listening... speak into your microphone")
        print("Try saying: 'John chapter 3 verse 16' or 'Turn to Matthew 5:1-10'")
        print("\n")
        
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\nStopping...")
        processor.stop()
        print("Test complete!")

if __name__ == "__main__":
    main()
