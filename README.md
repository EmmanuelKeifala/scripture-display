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

- **Start Listening**: Begin audio processing (not yet implemented)
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
│   ├── capture.py        # Real-time microphone capture
│   ├── transcribe.py     # Whisper speech-to-text
│   └── processor.py      # Audio processing pipeline
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

1. **Audio Capture**: Microphone input is captured in 3-second chunks at 16kHz
2. **Speech Recognition**: Whisper AI transcribes the audio to text
3. **Scripture Detection**: Text is analyzed for Bible references using regex patterns
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

## Whisper Model Sizes

The system uses Whisper 'small' model by default for better accuracy. Available models:

- **tiny**: Fastest, less accurate (39M params) - ~1GB RAM
- **base**: Fast, balanced (74M params) - ~1GB RAM
- **small**: Good accuracy, moderate speed (244M params) - ~2GB RAM (DEFAULT)
- **medium**: High accuracy, slower (769M params) - ~5GB RAM
- **large**: Best accuracy, slowest (1550M params) - ~10GB RAM

The 'small' model provides the best balance of speed and accuracy for scripture references.

## Optimization Features

- **Initial Prompt**: Guides Whisper with Bible verse examples for better context
- **5-second Chunks**: Allows complete verse references to be captured
- **No Speech Threshold**: Filters out background noise (0.6 threshold)
- **Beam Search**: Uses beam_size=5 for better transcription quality
- **Temperature 0**: Deterministic output for consistent results

## License

MIT
