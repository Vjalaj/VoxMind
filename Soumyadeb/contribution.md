# Contribution.md - Soumyadeb

## Week 1: Set up audio processing pipeline

### What I did:
- Designed and implemented a complete audio input/output pipeline in Python.
- Installed and configured audio-related dependencies compatible with modern Python versions.
- Created an `audio_handler.py` module to handle microphone input and speaker output.
- Configured audio parameters such as sample rate, channels, and data format optimized for speech processing.
- Implemented audio recording using callback-based input streams.
- Added playback functionality to test recorded audio.
- Implemented utility functions:
  - `start_recording()` to begin microphone capture
  - `stop_recording()` to stop recording and return audio data
  - `play_audio(audio_data)` to play recorded or generated audio
- Tested the pipeline with different recordings to ensure reliability and audio clarity.

### Resources / AI used:
- Python documentation
- `sounddevice` library documentation
- `soundfile` library documentation
- NumPy documentation
- ChatGPT (for guidance on audio pipeline design and best practices)

### Challenges faced:
- Faced compatibility issues with PyAudio on newer Python versions.
- Researched and switched to the `sounddevice` library, which provides better stability and cross-platform support.
- Ensured correct handling of audio buffers and real-time callbacks without data loss.

### Next steps:
- Integrate Speech-to-Text (STT) using Whisper or Vosk.
- Add Text-to-Speech (TTS) for voice responses.
- Implement wake-word detection (e.g., “Hey Jarvis”).
- Connect the audio pipeline with the core AI reasoning module.
