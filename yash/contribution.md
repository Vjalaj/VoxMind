# Contribution.md - yash

## Week 1: Integration and testing of voice interface components

### What I did:
- [Add your work here]
- Added integration pipeline modules to coordinate voice components:
	- `main.py` — integration entrypoint with simulate mode
	- `wake_word_detector.py` — simple wake-word detector with keyboard fallback
	- `command_parser.py` — basic keyword-based command parser
	- `response_generator.py` — simple response templates (time, search, etc.)
	- `text_to_speech.py` — TTS wrapper using `pyttsx3` with graceful fallback

	These work with the existing `Jalaj/speech_recognition_service.py` for command capture.

### Resources/AI used:
- [List any resources, documentation, AI tools, etc. you used]

### Challenges faced:
- [Optional: Describe any difficulties and how you overcame them]

### Next steps:
- [Optional: What you plan to do next or suggestions for improvement]
- Verify `pyttsx3` installation and test full audio flow (microphone + TTS).
- Add device selection, logging, retries for network errors, and unit tests for parsing.