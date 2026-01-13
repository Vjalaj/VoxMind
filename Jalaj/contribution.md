# Contribution.md - Jalaj

## Week 1: Speech Recognition & System Integration

### What I did:
- **Speech Recognition Service**: Implemented `speech_recognition_service.py` with robust `listen_for_command()` function
  - Proper timeout handling (5s timeout, 8s phrase limit)
  - Ambient noise adjustment (0.5s duration)
  - Comprehensive error handling with RuntimeError for better debugging
  - Test script `test_listen.py` for standalone testing

- **System Integration & Coordination**: Led the integration of all team components into `main.py`
  - Integrated Priyapal's advanced command parser (40+ patterns)
  - Integrated yash's wake word detector with "Hey Vox" support
  - Integrated minakshi/yash's TTS system
  - Implemented continuous listening mode (activate once with "Hey Vox")
  - Built actual command execution system:
    - Browser opening (webbrowser)
    - Web search (Google)
    - Time/date display
    - Volume control (mute/unmute/up/down/set)
    - App control (open/close applications)
    - System commands (shutdown/restart/sleep/lock)
  - Clean user interface with status messages
  - Proper error handling and graceful degradation

- **Dependencies**: Updated `requirements.txt` with all required packages

### Resources/AI used:
- Stack Overflow for PyAudio troubleshooting
- YouTube tutorials on speech recognition
- ChatGPT for integration patterns and error handling
- Google for Windows system command syntax
- Amazon Q for code review and optimization

### Challenges faced:
1. **PyAudio Installation on Windows**: Required prebuilt wheel from unofficial binaries
   - Solution: Documented in README with download link
   
2. **Wake Word Repetition**: Initial design required "Hey Vox" for every command
   - Solution: Implemented continuous listening mode with activation state
   
3. **Speech Recognition Accuracy**: Google API sometimes misheard commands
   - Solution: Used Priyapal's advanced parser with synonym support and wake word variations
   
4. **Component Integration**: Different team members used different return formats
   - Solution: Standardized on Priyapal's `{'command': 'type', 'params': {...}}` format
   
5. **Error Handling**: Components failed silently making debugging difficult
   - Solution: Added comprehensive error messages and logging throughout

### Key Integration Decisions:
- **Parser Choice**: Used Priyapal's advanced parser over basic yash parser (40+ patterns vs 8 patterns)
- **Speech Recognition**: Used my implementation with proper timeout/ambient noise handling
- **Wake Word**: Used yash's detector with "Hey Vox" and variations ("vox", "hey box", "a vox")
- **TTS**: Fallback chain: minakshi → yash → pyttsx3 direct
- **Continuous Mode**: Activate once, listen continuously until "shutdown"

### Testing:
- Tested speech recognition in various noise environments
- Tested wake word detection with different pronunciations
- Tested all command types (browser, search, time, volume, apps, system)
- Tested keyboard simulation mode for development
- Tested error handling (no mic, no internet, invalid commands)

### Next steps:
- Add more command types (weather, calendar, reminders)
- Implement local wake word detection (faster, no internet needed)
- Add conversation history/context
- Improve volume control with better Windows integration
- Add configuration file for customization
- Implement unit tests for all components
- Add logging system for debugging

### Week 2 Tasks:
See `tasks.md` for detailed Week 2 assignments including testing requirements.
