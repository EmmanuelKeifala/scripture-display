import torch
import sounddevice as sd
import numpy as np
from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq

# Load model directly
processor = AutoProcessor.from_pretrained("openai/whisper-tiny")
model = AutoModelForSpeechSeq2Seq.from_pretrained("openai/whisper-tiny")

# Set parameters
RATE = 16000  # 16kHz sampling rate (Whisper works well with this)
CHANNELS = 1  # Mono audio
CHUNK = 1024  # Size of each audio chunk

# Function to process the audio in chunks
def listen_and_transcribe():
    print("Listening...")
    
    # Continuously listen for audio chunks and transcribe
    def callback(indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        
        # Convert to numpy array and process through Whisper model
        audio_array = np.array(indata[:, 0], dtype=np.int16)  # Use one channel
        
        # Process audio through Whisper model
        inputs = processor(audio_array, return_tensors="pt", sampling_rate=RATE)
        with torch.no_grad():
            logits = model.generate(**inputs)
        
        # Decode the transcription
        transcription = processor.decode(logits[0], skip_special_tokens=True)
        print("Transcription:", transcription)

    # Open audio stream
    with sd.InputStream(callback=callback, channels=CHANNELS, samplerate=RATE, blocksize=CHUNK):
        sd.sleep(1000000)  # Keep listening indefinitely

# Start listening and transcribing
listen_and_transcribe()

