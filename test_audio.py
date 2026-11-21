import time
from audio.processor import AudioProcessor


def main():
    print("Listening... speak into your microphone (Ctrl+C to stop)")
    print("Try saying: 'John chapter 3 verse 16' or 'Turn to Matthew 5:1-10'\n")

    processor = AudioProcessor(transcription_callback=lambda text, final: print(f"{'Heard' if final else '  ...'}: {text}"))
    processor.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        processor.stop()


if __name__ == "__main__":
    main()
