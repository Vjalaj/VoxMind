# 🎙️ Vox AI Assistant  
## 📅 Week 1 & Week 2 Contribution Report  

---

# 🌟 Project Overview

**Vox** is a modular AI voice assistant built using Python.  
Over two weeks, the project evolved from basic audio handling to a fully functional voice-based assistant with API integration and persistent memory.

---

# 🗓️ Week 1: Audio Handler Development

## 🎯 Objective
Build a stable audio input/output system as the foundation of the voice assistant.

---

## 🛠️ Implementations

### 📂 `audio_handler.py`
- Microphone input handling
- Audio stream initialization
- Device enumeration & selection
- Buffer management
- Basic noise filtering
- Audio lifecycle control

---

## ⚠️ Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| Multiple audio devices | Implemented device enumeration & manual selection |
| Background noise | Added ambient noise adjustment |
| Buffer overflow | Optimized buffer configuration |

---

## 📚 Resources Used
- PyAudio Documentation  
- Audio Processing Tutorials  
- Stack Overflow  
- ChatGPT (Debugging & Guidance)

---

# 🗓️ Week 2: AI Assistant Core Integration

## 🎯 Objective
Transform the audio system into a fully functional modular AI assistant named **Vox**.

---

# 🏗️ Updated Project Structure

Soumyadeb/
│
├── main.py
├── config/settings.py
├── voice/
│ ├── recorder.py
│ ├── noise_reduction.py
│ └── tts.py
├── services/weather_api.py
├── utils/assistant_utils.py
├── database/db.py
└── requirements.txt


---

# 🧠 Module Contributions

---

## 🧩 main.py — Core Controller
- Continuous assistant loop
- Stop command detection
- Voice response confirmation
- Database memory integration
- Error handling

**Application:** Controls workflow → Listen → Process → Speak → Store

---

## ⚙️ config/settings.py — Configuration Layer
- API key storage
- Assistant settings
- Stop commands
- Default city

**Application:** Clean separation between configuration & logic.

---

## 🎤 voice/recorder.py — Speech Recognition
- Microphone listening
- Google speech recognition integration
- Ambient noise calibration

**Application:** Converts speech into text commands.

---

## 🔊 voice/tts.py — Text-to-Speech
- Integrated `pyttsx3`
- Configured voice rate & volume
- Stable audio playback

**Application:** Provides spoken responses for interaction.

---

## 🌦️ services/weather_api.py — Weather Integration
- OpenWeatherMap API integration
- Dynamic city extraction
- API error handling

**Application:** Enables queries like:
> “Tell me the weather of Delhi”

---

## 🧠 utils/assistant_utils.py — Command Processor
- Intent detection logic
- Regex-based city parsing
- Command routing

**Application:** Acts as assistant decision engine.

---

## 🗃️ database/db.py — SQLite Memory System
- Designed conversation table
- Save & retrieve functions
- Timestamp tracking

**Application:** Enables memory feature:
> “Tell me the old conversation”

Assistant replies with stored interaction history.

---

## 📦 requirements.txt — Dependency Management
- requests
- pyttsx3
- speechrecognition
- pyaudio

Ensures reproducible environment setup.

---

# 🚀 Features Achieved

✅ Voice-controlled weather queries  
✅ Dynamic city detection  
✅ Persistent SQLite conversation memory  
✅ Stop command handling  
✅ Modular architecture  
✅ Spoken confirmation ("Task Complete")  
✅ Error handling and stability improvements  

---

# 🗓️ Timeline

- **Day 1–2:** Audio enhancements & microphone stabilization  
- **Day 3:** Weather API integration & city parsing logic  
- **Day 4:** SQLite database setup & memory integration  
- **Day 5:** Optimization & error handling improvements  
- **Day 6:** Full system testing (voice + API + database)  
- **Day 7:** Documentation & contribution formatting  

---

# 📈 Project Evolution

**Week 1 →** Audio Infrastructure  
**Week 2 →** Intelligent Modular Voice Assistant  

Vox now supports:
- 🎤 Voice input  
- 🌦️ Live weather data  
- 🔊 Spoken responses  
- 🧠 Persistent memory  
- 🛑 Command control  

---

# 🎓 Learning Outcomes

- Real-time audio stream handling  
- Speech recognition systems  
- API integration in modular architecture  
- SQLite database management  
- Voice AI workflow design  
- Multi-module debugging  

---

# 🔮 Future Scope

- GPT-based conversational AI  
- Wake word detection  
- Advanced noise reduction  
- Multi-command memory  
- GUI integration  
- Background assistant mode  

---

# 👨‍💻 Developed By
Soumyadeb Dutta  
AI & Data Science Enthusiast  

---

⭐ *Vox is evolving from a basic audio handler to a scalable AI assistant platform.*

---

## Contact
- Tech Lead: Jalaj
- Questions: Team Whatsapp
- Code Reviews: PR and tag Jalaj