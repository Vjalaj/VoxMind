# Week 1 Tasks: VoxMind Phase 1 - Core Voice Interface

## Overview
This week focuses on implementing the core voice interface components of VoxMind. Each contributor is assigned a specific task related to Phase 1: Core Voice Interface. Follow the detailed instructions below and create Python modules/files for your components.

## General Guidance
- Install required dependencies from `requirements.txt`
- Create Python files in a `src/` or `voxmind/` folder (create if needed)
- Test your components individually first
- Use clear function names and add comments to your code
- Handle basic error cases and exceptions
- Document any issues or limitations in your `contribution.md`

## Task Assignments

### Jalaj - Speech Recognition Setup
**Task**: Research and set up speech recognition using `speech_recognition` library

**Detailed Steps**:
1. Install `speech_recognition` and `pyaudio` (check requirements.txt)
2. Create a Python file (e.g., `speech_recognition.py`)
3. Set up microphone access using `speech_recognition.Recognizer()`
4. Create a function `listen_for_command()` that:
   - Uses microphone as audio source
   - Adjusts for ambient noise
   - Listens for speech and converts to text using Google Speech Recognition
   - Returns the recognized text or None if failed
5. Handle common errors (network issues, unclear speech)
6. Test with different speaking volumes and distances

**Deliverables**: A working speech recognition module that reliably converts voice input to text

### minakshi - Text-to-Speech Setup
**Task**: Set up text-to-speech using `pyttsx3` library

**Detailed Steps**:
1. Install `pyttsx3` (check requirements.txt)
2. Create a Python file (e.g., `text_to_speech.py`)
3. Initialize the TTS engine with `pyttsx3.init()`
4. Create a function `speak_text(text)` that:
   - Takes text input
   - Speaks the text using the TTS engine
   - Waits for speech to complete
5. Configure voice properties:
   - Set speech rate (words per minute)
   - Set volume level
   - Optionally select different voices if available
6. Test with different text lengths and voice settings

**Deliverables**: A working TTS module that converts text to clear, audible speech

### Priyapal - Basic Command Parsing
**Task**: Implement basic command parsing using simple keyword matching

**Detailed Steps**:
1. Create a Python file (e.g., `command_parser.py`)
2. Define a list of supported commands, e.g.:
   - "open browser" or "launch chrome"
   - "what time is it" or "tell me the time"
   - "search for [topic]"
   - "play music"
   - "shutdown" or "quit"
3. Create a function `parse_command(text)` that:
   - Takes recognized text as input
   - Converts to lowercase for matching
   - Checks for keywords in the text
   - Returns a command identifier (string) or "unknown"
4. Handle variations like "open the browser" vs "launch browser"
5. Return structured data (dict) with command type and any parameters

**Deliverables**: A function that accurately identifies basic commands from text input

### Soumyadeb - Audio Processing Pipeline
**Task**: Set up audio input/output handling system

**Detailed Steps**:
1. Install `pyaudio` and any audio-related dependencies
2. Create a Python file (e.g., `audio_handler.py`)
3. Set up audio input stream:
   - Configure sample rate, channels, format
   - Handle microphone input
4. Set up audio output stream for playback
5. Create functions:
   - `start_recording()` - begin audio capture
   - `stop_recording()` - end capture and return audio data
   - `play_audio(audio_data)` - play back audio
6. Handle audio device selection and configuration
7. Test with different audio formats and quality settings

**Deliverables**: Audio I/O system that can record and play back audio reliably

### Sumant - Wake Word Detection
**Task**: Implement wake word detection to activate listening

**Detailed Steps**:
1. Research simple wake word detection methods
2. Create a Python file (e.g., `wake_word_detector.py`)
3. Choose implementation approach:
   - Use speech_recognition for continuous listening
   - Or implement simple keyword spotting
4. Create a function `listen_for_wake_word(wake_word="Hey VoxMind")` that:
   - Continuously listens in background
   - Detects the wake word in speech
   - Returns True when wake word is heard
   - Handles background noise and false positives
5. Implement timeout and sensitivity settings
6. Test in different noise environments

**Deliverables**: A wake word detection system that reliably activates on command

### Swadhin - Simple Response System
**Task**: Create basic response generation based on commands

**Detailed Steps**:
1. Create a Python file (e.g., `response_generator.py`)
2. Define response templates for each command type:
   - Greeting responses
   - Confirmation messages
   - Error messages for unknown commands
   - Time/date responses
3. Create a function `generate_response(command)` that:
   - Takes parsed command as input
   - Returns appropriate response text
   - Includes variety in responses to avoid repetition
4. Handle edge cases (unknown commands, errors)
5. Make responses conversational and helpful

**Deliverables**: A response system that provides appropriate text replies to commands

### yash - Integration and Testing
**Task**: Integrate all voice interface components into a working system

**Detailed Steps**:
1. Create a main Python file (e.g., `main.py` or `voxmind.py`)
2. Import all component modules
3. Create a main loop that:
   - Waits for wake word detection
   - Activates speech recognition when wake word heard
   - Parses the recognized text into commands
   - Generates appropriate response
   - Speaks the response using TTS
4. Handle the flow between components
5. Add error handling for component failures
6. Test the complete voice interaction pipeline
7. Document integration issues and solutions

**Deliverables**: A working voice interface that combines all components in a cohesive system

## Instructions
1. Work on your assigned task using the project plan and requirements.txt as reference
2. Create modular, reusable code that other contributors can easily integrate
3. Document your progress, challenges, and solutions in your `contribution.md` file
4. Include what resources or AI tools you used
5. Submit your work by Monday night
6. Coordinate with other contributors for integration (especially yash for final integration)

## Resources
- Project plan: `plan.md`
- Dependencies: `requirements.txt`
- Python documentation and library docs as needed
- Stack Overflow, GitHub issues for troubleshooting
- AI assistance: Use ChatGPT (chat.openai.com) in incognito mode for coding queries and guidance