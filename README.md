# Scripture Display System

Live AI-powered scripture display for sermons. Listens to pastors preaching and automatically displays Bible verses when mentioned.

## Features

- Real-time speech-to-text using Whisper AI
- Automatic Bible verse detection
- Fullscreen scripture display
- Manual verse lookup
- Auto-clear timer
- KJV translation (more coming soon)

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Import Bible database (first time only):
```bash
python3 -m scripture.importer
```

## Usage

Run the application:
```bash
python3 app.py
```

### Manual Testing

1. Click "Toggle Display Window" to show the scripture display
2. Enter a verse (e.g., Book: "John", Chapter: "3", Verse: "16")
3. Click "Display Verse"
4. The verse will appear on the display window and auto-clear after 10 seconds

### Verse Range

Enter verse ranges like "1-3" to display multiple verses (e.g., Psalm 23:1-3)

### Controls

- **Start Listening**: Begin audio processing
- **Stop Listening**: Stop audio processing
- **Display Verse**: Manually display a verse
- **Clear Display**: Remove current verse from display
- **Toggle Display Window**: Show/hide the scripture display

### Settings

- **Translation**: Choose Bible version (KJV available)
- **Auto-clear**: Seconds before verse automatically clears (5-60)
- **Detection Confidence**: Sensitivity for scripture detection (0.1-1.0)

## Project Status

### Phase 1: COMPLETE
- Database setup with 31,100 verses
- Scripture lookup system
- Verse range support

### Phase 2: COMPLETE
- Tkinter GUI
- Control panel
- Display window
- Manual verse input

### Phase 3: COMPLETE
- Scripture detection from text
- Pattern recognition for Bible references
- Book name normalization (handles abbreviations)
- Confidence scoring system
- Multiple reference formats supported
- Integrated text testing interface

### Phase 4: COMPLETE
- Whisper AI integration (base model)
- Real-time audio capture with sounddevice
- Speech-to-text pipeline with buffering
- Threaded audio processing
- Automatic scripture detection from speech
- Full end-to-end pipeline working

## Project Structure

```
whisper/
├── app.py                 # Main application
├── gui/
│   ├── control_panel.py  # Control interface
│   └── display_window.py # Scripture display
├── audio/
│   ├── capture.py        # Microphone capture, split into utterances on silence
│   ├── transcribe.py     # Whisper speech-to-text
│   └── processor.py      # Wires capture to transcription
├── scripture/
│   ├── database.py       # DB management
│   ├── lookup.py         # Verse queries
│   ├── detector.py       # Scripture reference detection
│   ├── book_mappings.py  # Book name normalization
│   └── importer.py       # Import Bible data
└── data/
    └── bible.db          # SQLite database (31,100 verses)
```

## How It Works

1. **Audio Capture**: Microphone input is split into whole utterances on silence (webrtcvad), up to 12 seconds each
2. **Speech Recognition**: Whisper (faster-whisper, `small.en` model) transcribes each utterance, plus a live guess every second while someone is still speaking; everything heard is shown in the Status Log
3. **Scripture Detection**: The transcript is matched for Bible references, written ("John 3:16") or spoken ("John chapter three verse sixteen", "John three sixteen")
4. **Verse Lookup**: Detected references are fetched from the local database
5. **Display**: Verses are shown on the display window with auto-clear timer

## Testing

Test the database:
```bash
python3 test_database.py
```

Test scripture detection:
```bash
python3 test_detector.py
```

Test audio processing (requires microphone):
```bash
python3 test_audio.py
```

Then speak into your microphone:
- "John chapter 3 verse 16"
- "Turn to Matthew 5:1-10"
- "First Corinthians 13:4-7"

## Cloud transcription (optional)

With a Deepgram API key the microphone is streamed to Deepgram (faster and more accurate than the local model); without one, or whenever the internet drops, the local Whisper model is used. Provide the key either way:

- environment variable `DEEPGRAM_API_KEY`, or
- a file named `.deepgram_key` in the project folder containing only the key (it is gitignored)

## Tuning

- **Model size**: `model_size` in `app.py` (`small.en` by default, about 2s behind live on a laptop CPU; `base.en` is about 1s behind but less accurate)
- **Noisy room / cut-off references**: `aggressiveness` and `silence_ms` in `audio/capture.py`
- **False detections**: raise the Detection Confidence slider. A bare "Book N" only shows at 0.6 or lower, except Psalms

## License

MIT
