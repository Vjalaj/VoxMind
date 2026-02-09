# VoxMind — Voice Assistant

## Overview
VoxMind is a modular voice assistant that recognizes the wake word **"Hey Vox"**, listens to your commands, and responds with actions like opening browsers, searching the web, playing music, controlling your mouse and keyboard, managing applications, and understanding your screen context.

## Quick Start

### 1. Setup Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Install Optional Dependencies (for full features)
```powershell
# For screen OCR (Tesseract)
winget install UB-Mannheim.TesseractOCR

# For window management
pip install pywin32 psutil
```

### 3. Run VoxMind

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
> Say: "open chrome"
Response: Launched Google Chrome

Listening...
> Say: "snap left"
Response: Snapped window to left

Listening...
> Say: "shutdown"
Response: Goodbye!
```

---

## 📋 Complete Command Reference

### 🌐 Browser & Web Commands
| Command | Description |
|---------|-------------|
| `open browser` | Opens default browser |
| `launch chrome` / `open chrome` | Opens Google Chrome |
| `launch edge` / `open edge` | Opens Microsoft Edge |
| `go online` | Opens default browser |
| `search for <query>` | Web search for query |
| `google <query>` | Google search |
| `what is <topic>` | Search for information |
| `go to <website>` | Opens URL (e.g., "go to github.com") |

### 🕐 Time & Date Commands
| Command | Description |
|---------|-------------|
| `what time is it` | Current time |
| `current time` | Current time |
| `what's the date` | Current date |
| `what day is it` | Day of week |
| `today's date` | Current date |

### 🎵 Media Control Commands
| Command | Description |
|---------|-------------|
| `play music` | Start media playback |
| `pause music` / `pause` | Pause playback |
| `next track` / `next song` | Skip to next |
| `previous track` / `previous song` | Go to previous |
| `stop music` | Stop playback |

### 🔊 Volume Control Commands
| Command | Description |
|---------|-------------|
| `volume up` / `louder` | Increase volume 10% |
| `volume down` / `quieter` | Decrease volume 10% |
| `mute` / `unmute` | Toggle mute |
| `set volume to <0-100>` | Set specific volume |
| `turn volume to 50` | Set to 50% |
| `max volume` | Set to 100% |

### 💡 Brightness Control Commands
| Command | Description |
|---------|-------------|
| `brightness up` / `brighter` | Increase brightness 10% |
| `brightness down` / `dimmer` | Decrease brightness 10% |
| `set brightness to <0-100>` | Set specific brightness |
| `max brightness` | Set to 100% |
| `min brightness` | Set to minimum |

### 📱 App Control Commands
| Command | Description |
|---------|-------------|
| `open <app>` | Launch application |
| `launch <app>` | Launch application |
| `start <app>` | Launch application |
| `close <app>` | Close application |
| `exit <app>` | Close application |
| `quit <app>` | Close application |
| `switch to <app>` | Focus application window |
| `go to <app>` | Focus application window |

**Supported Apps:** Chrome, Edge, Firefox, Notepad, Calculator, VS Code, Word, Excel, PowerPoint, Outlook, Teams, Slack, WhatsApp, VLC, and 170+ more installed apps.

### 🪟 Window Management Commands
| Command | Description |
|---------|-------------|
| `minimize` | Minimize current window |
| `minimize <app>` | Minimize specific app |
| `maximize` | Maximize current window |
| `maximize <app>` | Maximize specific app |
| `snap left` | Snap window to left half |
| `snap right` | Snap window to right half |
| `snap top` | Maximize window |
| `snap bottom` | Minimize window |
| `snap top left` | Snap to top-left quarter |
| `snap top right` | Snap to top-right quarter |
| `snap bottom left` | Snap to bottom-left quarter |
| `snap bottom right` | Snap to bottom-right quarter |
| `snap center` | Center window |
| `show desktop` | Minimize all windows (Win+D) |
| `list windows` | List open windows |

### 🖱️ Mouse Control Commands (Voice Access)
| Command | Description |
|---------|-------------|
| `click` | Left click at current position |
| `double click` | Double left click |
| `right click` | Right click |
| `triple click` | Triple click (select line) |
| `move mouse left` | Move mouse left 50px |
| `move mouse right` | Move mouse right 50px |
| `move mouse up` | Move mouse up 50px |
| `move mouse down` | Move mouse down 50px |
| `move mouse left 100` | Move left 100 pixels |
| `move to 500, 300` | Move to coordinates |
| `grid` | Show 3x3 grid overlay |
| `click 5` | Click center of grid cell 5 |
| `scroll up` | Scroll up |
| `scroll down` | Scroll down |
| `scroll left` | Scroll left |
| `scroll right` | Scroll right |
| `drag left` / `drag right` | Drag window 100px |
| `drag to 100, 200` | Drag to coordinates |

### ⌨️ Keyboard Control Commands
| Command | Description |
|---------|-------------|
| `type <text>` | Type text |
| `press enter` | Press Enter key |
| `press escape` | Press Escape key |
| `press tab` | Press Tab key |
| `press backspace` | Press Backspace |
| `press delete` | Press Delete |
| `copy` | Ctrl+C |
| `paste` | Ctrl+V |
| `cut` | Ctrl+X |
| `undo` | Ctrl+Z |
| `redo` | Ctrl+Y |
| `save` | Ctrl+S |
| `select all` | Ctrl+A |
| `find` | Ctrl+F |
| `new tab` | Ctrl+T |
| `close tab` | Ctrl+W |
| `switch window` | Alt+Tab |
| `select word` | Double-click selection |
| `select line` | Triple-click selection |
| `go to start` | Ctrl+Home |
| `go to end` | Ctrl+End |

### 👁️ Screen Context Commands (Visual AI)
| Command | Description |
|---------|-------------|
| `what's on my screen` | Describe screen content |
| `what do you see` | Analyze screen |
| `read the screen` | OCR and read text |
| `describe the screen` | Full screen analysis |
| `click on <text>` | Find and click text on screen |
| `find <text> on screen` | Locate text position |
| `what am I looking at` | Context analysis |
| `help me with this` | Suggest actions |

### 📹 Screen Monitoring Commands
| Command | Description |
|---------|-------------|
| `start watching` | Begin continuous screen monitoring |
| `watch my screen` | Begin monitoring |
| `stop watching` | Stop screen monitoring |
| `pause watching` | Pause monitoring |
| `resume watching` | Resume monitoring |
| `what changed` | Get activity summary |
| `screen activity` | Report screen changes |

### 📊 Performance Analytics Commands
| Command | Description |
|---------|-------------|
| `performance` | Show performance index (0-100) |
| `performance index` | Detailed performance stats |
| `stats` / `statistics` | Show session statistics |
| `how am I doing` | Performance summary |
| `performance report` | Full analytics report |

### ⚡ System Commands
| Command | Description |
|---------|-------------|
| `shutdown` / `exit` / `quit` | Exit VoxMind |
| `restart` | Restart computer |
| `sleep` | Put computer to sleep |
| `lock` / `lock screen` | Lock computer |
| `screenshot` | Take screenshot |

### ❓ Help & Information Commands
| Command | Description |
|---------|-------------|
| `help` | Show available commands |
| `what can you do` | List capabilities |
| `who are you` | VoxMind introduction |
| `call me <name>` | Change your name |

---

## 🏗️ Features

### Core Features
- ✅ Wake word detection ("Hey Vox") - activate once
- ✅ Continuous listening after activation
- ✅ Speech recognition (Google Web Speech API)
- ✅ Enhanced command parsing with 60+ patterns
- ✅ Natural Language Engine (NLE) for understanding
- ✅ Text-to-speech responses (pyttsx3)
- ✅ Keyboard fallback mode

### Voice Access (Windows Voice Access Style)
- ✅ Mouse control (click, move, grid, scroll, drag)
- ✅ Keyboard control (type, hotkeys, shortcuts)
- ✅ 3x3 grid overlay for precise clicking
- ✅ Directional mouse movement

### App Control
- ✅ Launch 170+ installed applications
- ✅ Close applications by name
- ✅ Switch between windows
- ✅ Window snapping (left/right/corners)
- ✅ Show desktop (Win+D)

### Screen Context (Visual AI)
- ✅ Screen capture and OCR (Tesseract/EasyOCR)
- ✅ Text extraction and analysis
- ✅ Entity detection (URLs, emails, prices, dates)
- ✅ App detection from screen content
- ✅ Click on visible text
- ✅ Keyword extraction
- ✅ Action suggestions

### Screen Monitoring
- ✅ Continuous screen watching
- ✅ Change detection (% of screen changed)
- ✅ App switching detection
- ✅ Activity summaries

### Performance Analytics
- ✅ Real-time command tracking
- ✅ Performance index scoring (0-100)
- ✅ Response time statistics (mean, median, P95, P99)
- ✅ Category-wise performance breakdown
- ✅ Wake word detection accuracy
- ✅ Historical trend analysis
- ✅ Error analysis and patterns
- ✅ Session-level metrics

### Command Cache (Hashmap)
- ✅ Response caching (O(1) exact match lookup)
- ✅ Fuzzy matching for similar commands
- ✅ Duplicate command detection
- ✅ LRU eviction policy (1000 entries)
- ✅ TTL-based expiration (5 min default)
- ✅ Command fingerprinting
- ✅ Token-based inverted index

### System Control
- ✅ Volume control (up/down/mute/set)
- ✅ Brightness control
- ✅ Power management (shutdown/restart/sleep/lock)

---

## 🔧 Troubleshooting

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

### Screen OCR Not Working
1. Install Tesseract: `winget install UB-Mannheim.TesseractOCR`
2. Or use EasyOCR fallback (automatic, no install needed)

### Window Management Not Working
```powershell
pip install pywin32 psutil
```

### TTS Not Speaking
- Confirm `pyttsx3` is installed: `pip install pyttsx3`
- Use `--no-tts` flag to disable TTS and print responses

---

## 🧪 Testing Components

**Test Speech Recognition**
```powershell
python Jalaj\test_listen.py
```

**Test Wake Word Detection**
```powershell
python Tejas\test_wake_word.py
```

**Test Command Parser**
```powershell
python Tejas\test_enhanced_parser.py
```

**Test Input Control (Mouse/Keyboard)**
```powershell
python test_input_control.py
```

**Test Screen Context**
```powershell
python test_screen_context.py
```

**Test App Control**
```powershell
python demo_app_control.py
```

**Test Visual Demo (Watch Vox control windows)**
```powershell
python demo_visual_control.py
```

---

## 📁 Project Structure

```
VoxMind/
├── main.py                     # Main voice assistant integration
├── requirements.txt            # Python dependencies
├── config.py                   # Configuration settings
├── personality.py              # AI personality definitions
│
├── core/                       # Core modules
│   ├── voice_access.py         # Mouse & keyboard control (Voice Access)
│   ├── screen_context.py       # Screen capture, OCR, visual AI
│   ├── app_control.py          # Application management (170+ apps)
│   └── screen_monitor.py       # Continuous screen watching
│
├── Jalaj/                      # Speech recognition & Integration
│   ├── speech_recognition_service.py
│   └── test_listen.py
│
├── Tejas/                      # Wake word, TTS, NLP parser
│   ├── wake_word_detector.py   # "Hey Vox" detection
│   ├── nlp_command_parser.py   # Natural language command parsing
│   ├── text_to_speech.py       # Speech output
│   └── response_generator.py   # Response templates
│
├── Priyapal/                   # Command parsing & wake word
│   ├── command_parser.py       # Advanced pattern matching
│   └── wake_word_enhancement.py
│
├── minakshi/                   # Text-to-speech
│   └── text_to_speech.py
│
├── Swadhin/                    # Response system
│   └── response_system/
│       ├── response_generator.py
│       ├── response_templates.py
│       └── context.py
│
├── Sumant/                     # Advanced NLU
│   └── advanced_command_parser.py
│
├── Soumyadeb/                  # Audio & database
│   ├── audio/
│   │   ├── audio_handler.py
│   │   └── volume_control.py
│   └── database/
│       ├── conversation_db.py
│       └── user_profiles.py
│
├── demos/                      # Demo scripts
│   ├── demo_app_control.py     # App control demo
│   ├── demo_visual_control.py  # Visual window control demo
│   └── demo_mouse_control.py   # Mouse control demo
│
└── tests/                      # Test files
    ├── test_input_control.py
    ├── test_screen_context.py
    ├── test_snap_drag.py
    └── test_personality.py
```

---

## 👥 Contributors

| Developer | Contributions |
|-----------|---------------|
| **Jalaj** | Speech recognition, system integration, coordination |
| **Tejas** | Wake word detection, NLP command parser, TTS, response generation |
| **Priyapal** | Advanced command parser (60+ patterns), wake word enhancement |
| **Minakshi** | Text-to-speech implementation |
| **Swadhin** | Response generation, context management, caching |
| **Sumant** | Advanced NLU, multi-intent parsing |
| **Soumyadeb** | Audio handling, volume control, database, user profiles |

---

## 📈 Roadmap Progress

See [90_DAY_ROADMAP.md](90_DAY_ROADMAP.md) for detailed development plan.

| Phase | Status | Features |
|-------|--------|----------|
| Week 1-2 | ✅ Complete | Core voice pipeline, wake word, speech recognition |
| Week 3-4 | ✅ Complete | Enhanced command parsing, response generation |
| Week 5-6 | ✅ Complete | Voice Access (mouse/keyboard control) |
| Week 7-8 | ✅ Complete | Screen Context (OCR, visual AI) |
| Week 9-10 | ✅ Complete | App Control, Window Management |
| Week 11-12 | 🔄 In Progress | Advanced features, polish |

---

## 📜 License

MIT License - See LICENSE file for details.

---

**VoxMind** — Voice-First Computing for Everyone 🎤✨

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
- **Wake word handling**: Automatically strips "hey vox", "voxmind", etc.
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
