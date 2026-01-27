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
