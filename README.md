<<<<<<< HEAD
# VoxMind C++ Core

This is a complete rewrite of the VoxMind engine in C++ (C++17), designed for performance, modularity, and accuracy.

## Features
- **Custom NLU Engine:** Uses a TF-IDF Centroid classifier trained on `training_data.txt`. No external ML libraries required.
- **Cross-Platform Architecture:** Clean separation between Logic, NLU, and OS-Specific Execution.
- **High Performance:** minimal latency compared to Python.
- **Extensible:** Ready for `Vosk` or `Whisper.cpp` integration.

## Directory Structure
```
VoxMindCpp/
├── include/
│   ├── CommandExecutor.h   # Abstract Base Class + Windows/Linux Implementations
│   └── TextClassifier.h    # TF-IDF NLU Engine
├── src/
│   └── main.cpp            # Entry point
├── training_data.txt       # Training dataset (Intent: Phrase)
└── Makefile                # Build script for Linux/Mingw
```

## Supported Commands (Intents)
The system currently recognizes the following categories of commands:
- **Browser:** `browser_open`, `search_web`
- **System:** `time_check`, `date_check`, `shutdown_system`
- **Audio:** `volume_mute`, `volume_up`, `volume_down`
- **Apps:** `notepad_open`, `calculator_open`
- **Accessibility (Mouse):** `mouse_click`, `mouse_right_click`, `mouse_double_click`, `mouse_move_up/down/left/right`
- **Accessibility (Windows):** `window_close`, `window_maximize`, `window_minimize`

## Training
Accuracy can be improved by adding more phrases to `training_data.txt`. The system uses a Bag-of-Words TF-IDF model, so adding synonyms helps significantly.
```bash
cd VoxMindCpp
make
./voxmind
```

### Windows (Target Deployment)
1. Install MinGW or use Visual Studio.
2. Compile `src/main.cpp` ensuring `include/` is in the path.
3. The code automatically detects Windows via `_WIN32` macro and switches to the `WindowsExecutor`.

```powershell
g++ -I./include -std=c++17 -o voxmind.exe src/main.cpp
./voxmind.exe
```

## Customizing Accuracy (Training)
To improve accuracy or add commands, simply edit `training_data.txt`.
Format: `Intent_Name: Example Phrase`

Example:
```text
social_media: open facebook
social_media: check instagram
```
Then add the handler logic in `include/CommandExecutor.h` inside the `WindowsExecutor` class.

## Adding Real Voice Recognition (Vosk Integration)

To replace the text input with real voice:
1. Download **Vosk API** (C++ headers and `.dll/.so`).
2. Include `vosk_api.h` in `main.cpp`.
3. Replace the `std::getline` loop with:
   ```cpp
   VoskRecognizer *rec = vosk_recognizer_new(model, 16000.0);
   // ... Audio Loop reading from PortAudio or Microphone ...
   if (vosk_recognizer_accept_waveform(rec, data, len)) {
       const char* result = vosk_recognizer_result(rec);
       // Parse JSON result to get text -> pass to classifier.predict(text)
   }
   ```
4. This architecture supports it fully as the NLU component is decoupled from Input.
=======
# VoxMind — Voice Assistant

## Overview
VoxMind is a modular voice assistant that recognizes the wake word **"Hey Vox"**, listens to your commands, and responds with actions like opening browsers, searching the web, playing music, and more.

## Quick Start

### 1. Setup Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Run VoxMind

**Voice Mode (Recommended)**
```powershell
python main.py
```
Say **"Hey Vox"** once to activate, then give multiple commands. Say **"shutdown"** to exit.

**Keyboard Mode (Testing)**
```powershell
python main.py --simulate --no-tts
```

## How It Works

1. **Say "Hey Vox"** → Activates VoxMind (only once!)
2. **Give commands** → Keep talking, no need to repeat "Hey Vox"
3. **Say "shutdown"** → Closes VoxMind

### Example Session:
```
Waiting for 'Hey Vox'...
> Say: "Hey Vox"
✓ VoxMind activated! Listening for commands...

Listening...
> Say: "what time is it"
Response: It's 3:45 PM on Monday, January 15

Listening...
> Say: "search for python tutorials"
Response: Searching for python tutorials

Listening...
> Say: "shutdown"
Response: Goodbye!
```

## Supported Commands

| Command Type | Examples |
|-------------|----------|
| **Browser** | "open browser", "launch chrome", "go online" |
| **Search** | "search for python", "what is AI", "find restaurants" |
| **Time** | "what time is it", "current time", "what's the date" |
| **Music** | "play music", "next track", "pause music" |
| **Volume** | "mute", "volume up", "louder", "turn volume to 50" |
| **Apps** | "open notepad", "launch vscode", "close chrome" |
| **System** | "shutdown", "restart", "sleep", "lock screen" |
| **Help** | "help", "what can you do", "who are you" |

## Features
- ✅ Wake word detection ("Hey Vox") - activate once
- ✅ Continuous listening after activation
- ✅ Speech recognition (Google Web Speech API)
- ✅ Enhanced command parsing with 40+ patterns
- ✅ Natural language understanding
- ✅ Text-to-speech responses
- ✅ Keyboard fallback mode
- ✅ Actual command execution (browser, search, time, volume, apps, system)

## Troubleshooting

### Wake Word Not Detected
1. **Check microphone**: Ensure it's connected and permissions are granted
2. **Speak clearly**: Say "Hey Vox" clearly and wait for response
3. **Check volume**: Microphone should pick up your voice
4. **Use keyboard mode**: Run with `--simulate` flag for testing

### PyAudio Installation Issues (Windows)
Download prebuilt wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
```powershell
pip install PyAudio-0.2.11-cp3xx-cp3xx-win_amd64.whl
```

### Microphone Not Working
- Verify system permissions for microphone access
- Check default input device in Windows Sound settings
- Test with: `python Jalaj\test_listen.py`

### TTS Not Speaking
- Confirm `pyttsx3` is installed: `pip install pyttsx3`
- Use `--no-tts` flag to disable TTS and print responses

## Testing Components

**Test Speech Recognition**
```powershell
python Jalaj\test_listen.py
```

**Test Wake Word Detection**
```powershell
python Tejas\test_wake_word.py
```

**Test Enhanced Command Parser**
```powershell
python Tejas\test_enhanced_parser.py
```

## Project Structure
```
VoxMind/
├── main.py                    # Main integration (Jalaj's coordination)
├── requirements.txt           # Dependencies
├── Jalaj/                     # Speech recognition + Integration
│   ├── speech_recognition_service.py
│   └── test_listen.py
├── Tejas/                      # Wake word, TTS, response
│   ├── wake_word_detector.py
│   ├── text_to_speech.py
│   └── response_generator.py
├── Priyapal/                  # Advanced command parser
│   └── command_parser.py
├── minakshi/                  # Text-to-speech
│   └── text_to_speech.py
├── Swadhin/                   # Response generation
├── Sumant/                    # Wake word detection
└── Soumyadeb/                 # Audio handling
```

## Contributors

### Week 1 - Core Voice Interface
- **Jalaj**: Speech recognition + System integration & coordination
- **Tejas**: Wake word detection, TTS, response generation
- **Priyapal**: Advanced command parser (40+ patterns)
- **Minakshi**: Text-to-speech implementation
- **Swadhin**: Response generation & user experience
- **Sumant**: Wake word detection
- **Soumyadeb**: Audio handling

See individual `contribution.md` files in each folder.

### Week 2 Tasks
For latest task assignments and updates, visit: **https://github.com/your-repo/VoxMind/blob/main/tasks.md**

Or view locally: `tasks.md` in project root

## Command Line Options

```
python main.py [OPTIONS]

Options:
  --simulate    Use keyboard input instead of microphone
  --no-tts      Disable text-to-speech (print only)
```

## Examples

```powershell
# Full voice mode (recommended)
python main.py
> Say: "Hey Vox"
> Say: "what time is it"
> Say: "open browser"
> Say: "shutdown"

# Keyboard testing
python main.py --simulate --no-tts
> Press Enter to activate
> Type: "search for python tutorials"
> Type: "shutdown"
```

## Recent Improvements

### Enhanced Command Parser (Priyapal)
- **40+ patterns** for better command recognition
- **Synonym support**: Multiple ways to say the same thing
- **Wake word handling**: Automatically strips "hey vox", "jarvis", etc.
- **Smart fallbacks**: Unknown commands become search queries

### Improved Speech Recognition (Jalaj)
- Better timeout and phrase limits
- Ambient noise adjustment
- Robust error handling

### Continuous Listening Mode
- Say "Hey Vox" once to activate
- Give multiple commands without repeating wake word
- Say "shutdown" to exit

See `PARSER_IMPROVEMENTS.md` for details.
>>>>>>> 8a47837fadb5e56b3de25b88fb6c45f2b6008970
