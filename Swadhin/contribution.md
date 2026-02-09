# Contribution.md - Swadhin

## Week 1: Response Generation

### What I did:
- **Response Generator**: Contributed to response generation system
  - Created response templates for different command types
  - Implemented contextual responses
  - Added variety to avoid repetition

### Resources used:
- Python documentation
- ChatGPT for response ideas
- Stack Overflow
- UX writing guides

### Challenges faced:
1. **Response variety**: Avoiding repetitive responses
   - Solution: Created multiple response templates

2. **Context awareness**: Responses not matching context
   - Solution: Added context tracking

3. **Error messages**: Generic error messages not helpful
   - Solution: Created specific error responses

---

## Week 2: Response System Enhancement & User Experience

### What I did:

**Response Enhancements:**
- Added personality to responses (friendly, professional, humorous)
- Implemented context-aware responses
- Added response variations to avoid repetition (5+ per command type)
- Enabled multi-sentence responses
- Improved error messages for clarity and usability

**User Experience:**
- Created conversational flow for smoother interactions
- Implemented follow-up question handling
- Added confirmation dialogs for critical actions
- Included helpful suggestions within responses
- Built onboarding responses for new users

**Response Templates:**
- Built a response template system
- Created templates for all command types
- Added dynamic content insertion
- Implemented response personalization

**Testing:**
- Created `tests/test_responses.py`
- Tested all command types
- Verified response variety and randomness
- Tested context handling and state persistence
- Validated error responses
- Checked response tone and appropriateness

**Quality Improvements:**
- Optimized response timing
- Implemented response caching for common queries
- Tested end-to-end conversational flow

### Timeline:
- **Day 1-2**: Personality implementation + response templates
- **Day 3**: Context-aware responses
- **Day 4**: Response variations (5+ per type)
- **Day 5**: User experience improvements
- **Day 6**: Testing
- **Day 7**: Documentation

### Success Criteria:
- Personality implemented (friendly, professional, humorous)
- Context awareness working as expected
- Response variety greater than 5 per command type
- Test coverage above 80%
- User experience improvements documented

---

## Week 3: Process Mapper Module (App/Icon Mapping)

### What I did:

**Created `process_mapper.py` - A dedicated module for app/icon mapping:**

This module solves the problematic mapping of apps/icons by getting access from Task Manager-like system APIs.

**Core Features:**
1. **Process Enumeration** - Gets running processes like Task Manager using `psutil`
2. **Friendly Name Resolution** - Maps process names (e.g., `chrome.exe`) to user-friendly names (e.g., "Google Chrome")
3. **Process Classification** - Categorizes processes (Browser, Office, Development, Media, Communication, etc.)
4. **Icon Extraction** - Extracts app icons from executables using Windows Shell APIs
5. **UWP App Handling** - Properly handles Universal Windows Platform apps
6. **Problematic Mapping Resolution** - Resolves edge cases like:
   - Apps with multiple processes
   - Apps with different display names
   - Background apps becoming foreground
   - ApplicationFrameHost (UWP container)

**Key Components:**
- `ProcessInfo` dataclass - Complete process information
- `ProcessMapper` class - Main mapping engine
- `PROCESS_FRIENDLY_NAMES` - 60+ common process name mappings
- `SYSTEM_PROCESSES` - Set of system/background processes to filter
- `CATEGORY_KEYWORDS` - Keywords for process classification

**Convenience Functions:**
- `list_running_apps()` - Get user-facing applications
- `find_app(query)` - Find app by name with fuzzy matching
- `get_app_icon_path(app_name)` - Get cached icon path

**Technologies Used:**
- `psutil` - Process enumeration
- `pywin32` - Windows API access (icons, window info)
- `PIL/Pillow` - Icon image processing
- JSON caching for icon mappings

### Resources Used:
- Windows API documentation
- psutil documentation
- Python win32api references
- Task Manager internals

### Challenges Solved:
1. **UWP Apps** - ApplicationFrameHost hides real app info → Solution: Enumerate child processes
2. **Missing Icons** - Some apps don't expose icons properly → Solution: Shell API fallback + caching
3. **Performance** - Enumerating all processes is slow → Solution: Caching with TTL
4. **Name Mapping** - Process names don't match user expectations → Solution: Comprehensive friendly name dictionary

### File Location:
`Swadhin/process_mapper.py`

### Usage Example:
```python
from Swadhin.process_mapper import ProcessMapper, find_app, list_running_apps

# Get all running apps
apps = list_running_apps()
for app in apps:
    print(f"{app['name']} - {app['category']}")

# Find specific app
chrome = find_app("chrome")
if chrome:
    print(f"Found: {chrome['name']} (PID: {chrome['pid']})")

# Use ProcessMapper directly
mapper = ProcessMapper()
summary = mapper.get_process_summary()
print(f"Total processes: {summary['total_processes']}")
```

---

## Week 3 (Part 2): Intonation Module - Human-Like Voice

### What I did:

**Created `intonation.py` - Makes voice smooth, lucid, and natural with human-like intonation:**

This module adds prosody (rhythm, stress, intonation) to make TTS output sound like a real human.

**Core Features:**

1. **Sentence Type Detection**
   - Statements (falling intonation at end)
   - Yes/No Questions (rising intonation)
   - WH-Questions (rise-fall pattern)
   - Exclamations (higher pitch, emphatic)
   - Commands (firm, level)
   - Lists (rising for items, falling for last)

2. **Emotional Tone Modulation**
   - 8 emotional tones: friendly, professional, excited, concerned, apologetic, encouraging, calm, urgent
   - Automatic emotion detection from keywords
   - Per-emotion prosody settings (rate, pitch, pitch range)

3. **Word-Level Analysis**
   - Emphasis detection (very, really, always, etc.)
   - Contrast word handling (but, however, although)
   - Function word reduction (a, the, is, etc.)
   - ALL CAPS detection for strong emphasis

4. **Natural Pauses**
   - Punctuation-based pauses (comma: 150ms, period: 400ms)
   - Breath pauses at natural points
   - Emphasis pauses before important words

5. **Pitch Contours**
   - Sentence melody patterns
   - Position-based pitch interpolation
   - Final pitch changes for sentence types

6. **SSML Generation**
   - Full SSML output for advanced TTS engines
   - Prosody markers for custom implementations
   - Compatible with Google Cloud TTS, Azure, Amazon Polly

**Key Classes:**
- `IntonationEngine` - Main analysis engine
- `SentenceAnnotation` - Per-sentence prosody data
- `WordAnnotation` - Per-word emphasis/pitch data
- `ProsodySettings` - Rate, pitch, volume controls

**Convenience Functions:**
```python
from Swadhin.intonation import add_intonation, speak_with_intonation, get_ssml

# Add intonation markers
result = add_intonation("Hello! How are you today?", "friendly")
print(result.ssml)

# Speak with natural intonation
speak_with_intonation("Found Chrome for you!", "excited")

# Get SSML for TTS
ssml = get_ssml("Please click the button.", "professional")
```

**Integration with SwadhinModule:**
```python
from Swadhin.main import SwadhinModule

m = SwadhinModule()

# Add intonation to response
result = m.add_intonation("Hello! Welcome to VoxMind.", "friendly")
print(result['ssml'])

# Speak with intonation
m.speak("Found Google Chrome for you!", "excited")

# Analyze speech patterns
analysis = m.analyze_speech("That's absolutely amazing!")
```

### Technologies Used:
- Python linguistics patterns
- SSML (Speech Synthesis Markup Language)
- pyttsx3 integration
- Prosody modeling (pitch contours, emphasis levels)

### Linguistic Patterns Implemented:
- **Declination** - Natural pitch lowering through sentences
- **Final lowering** - Statements end with falling pitch
- **Question intonation** - Rising pitch for yes/no questions
- **Focus prosody** - Emphasized words get higher pitch
- **Given/New distinction** - New information gets prominence

### File Location:
`Swadhin/intonation.py`

---

## Week 3 (Part 3): Voice Models - AI Personas

### What I did:

**Created `voice_models.py` - 6 distinct AI voice personas with unique personalities:**

This module provides diverse AI personalities, each with their own character, speech style, and response templates. Perfect for customizable user experiences and multi-agent systems.

**The 6 Voice Personas:**

| Voice | Gender | Role | Personality |
|-------|--------|------|-------------|
| **JARVIS** | Male | Tactical AI Assistant | Calm, precise, authoritative, efficient |
| **VISION** | Male | Philosophical AI Companion | Thoughtful, curious, insightful, reflective |
| **EDITH** | Male | Empathetic Support AI | Warm, patient, understanding, supportive |
| **ELISA** | Female | Academic Research AI | Analytical, knowledgeable, thorough, precise |
| **SOFIA** | Female | Creative Assistant AI | Imaginative, expressive, enthusiastic, innovative |
| **FRIDAY** | Female | Conversational Smart Assistant | Friendly, witty, adaptive, approachable |

**Core Features:**

1. **Voice Model Definition**
   - Name, gender, role, description
   - Personality traits array
   - Communication style
   - Custom prosody settings (rate, pitch, volume)

2. **Response Templates** (5 types per voice)
   - **Greeting** - How the voice introduces itself
   - **Acknowledgment** - How it confirms commands
   - **Error** - How it reports problems
   - **Thinking** - What it says while processing
   - **Success** - How it reports completion

3. **LLM Integration**
   - Unique `prompt_tag` for each persona
   - Full system prompts for LLM APIs
   - Personality instructions for GPT/Claude/etc.

4. **Prosody Settings Per Voice**
   - Custom speech rate (JARVIS: slow, FRIDAY: medium-fast)
   - Pitch baseline (SOFIA: high, VISION: medium-low)
   - Pitch range (emotional expressiveness)
   - Volume normalization

5. **Intonation Integration**
   - Automatic emotional tone selection per persona
   - SSML generation with voice-specific settings
   - Style-aware response processing

**Key Classes:**
- `VoiceModel` - Dataclass defining a complete persona
- `VoiceProsody` - Speech rate/pitch/volume settings
- `VoicePersona` - Enum of available voices
- `VoiceEngine` - Main engine with all voice operations

**Response Style Examples:**

| Voice | Greeting | Acknowledgment | Success |
|-------|----------|----------------|---------|
| JARVIS | "Systems operational. How may I assist?" | "Understood." | "Operation successful." |
| VISION | "Greetings. I am here to ponder alongside you." | "I see. Let me contemplate this." | "The journey has reached its destination." |
| EDITH | "Hi there! I'm here to help. How are you?" | "Of course, I'm on it." | "There we go, all done!" |
| ELISA | "Hello. Ready for research and analysis." | "Noted. Processing your request." | "Analysis complete. Results confirmed." |
| SOFIA | "Hello, creative soul! Let's make something beautiful!" | "Ooh, love it! Let me work my magic." | "Voilà! How gorgeous is that?" |
| FRIDAY | "Hey! What's up?" | "Got it!" | "Done and done!" |

**Usage Examples:**
```python
from Swadhin.voice_models import VoiceEngine, VoicePersona

# Create engine with default voice
engine = VoiceEngine("friday")

# Get voice templates
print(engine.greet())        # "Hey! What's up?"
print(engine.acknowledge())  # "Got it!"
print(engine.report_success())  # "Done and done!"

# Switch voices
engine.set_voice("jarvis")
print(engine.greet())  # "Systems operational. How may I assist?"

# Get LLM system prompt
prompt = engine.get_system_prompt()
# Use as: openai.chat(messages=[{"role": "system", "content": prompt}, ...])

# Style a response with voice personality
styled = engine.style_response("I found 3 results for you.")
# Returns: "Found 3 results for you." (or styled version)

# Get intonation-enhanced output
result = engine.apply_voice_intonation("Hello!")
print(result['ssml'])  # SSML with voice prosody
```

**Integration with SwadhinModule:**
```python
from Swadhin.main import SwadhinModule

# Initialize with a voice
m = SwadhinModule(voice="jarvis")

# Voice operations
print(m.voice_greet())       # Voice-specific greeting
print(m.voice_acknowledge()) # Voice-specific acknowledgment
print(m.voice_success())     # Voice-specific success

# Switch voice
m.set_voice("sofia")
print(m.voice_greet())  # Sofia's creative greeting

# Get LLM prompt for current voice
system_prompt = m.get_llm_system_prompt()

# Get all voice info
voices = m.list_voices()
current = m.get_voice()

# Styled response with intonation
result = m.voice_styled_response("Found Chrome for you!")
print(result['ssml'])
print(result['voice_name'])
```

### Voice Selection Guide:

| Use Case | Recommended Voice |
|----------|------------------|
| Technical/Professional tasks | JARVIS, ELISA |
| Casual conversation | FRIDAY, EDITH |
| Creative projects | SOFIA |
| Deep discussions | VISION |
| Emotional support | EDITH |
| Quick commands | FRIDAY, JARVIS |

### File Location:
`Swadhin/voice_models.py`

---

## Updated Main Integrator

The `main.py` now includes all four modules:

| Component | Status | Description |
|-----------|--------|-------------|
| Response System | ✅ | Contextual responses with personality |
| Process Mapper | ✅ | App/icon mapping from Task Manager |
| Intonation Engine | ✅ | Human-like voice with prosody |
| Voice Models | ✅ | 6 AI personas (3 male, 3 female) |

**New Voice Methods Added:**
- `set_voice(name)` - Switch active voice persona
- `get_voice()` - Get current voice info
- `list_voices()` - List all available voices
- `voice_greet()` - Get persona-specific greeting
- `voice_acknowledge()` - Get acknowledgment response
- `voice_success()` - Get success message
- `voice_error(msg)` - Get error message
- `voice_thinking()` - Get thinking/processing message
- `get_llm_system_prompt()` - Get LLM system prompt for current voice
- `voice_styled_response(text)` - Get styled response with SSML

---

## Week 4: Advanced Question Answering System

### What I did:

**Created `question_answering/` - A comprehensive system for elaborate, discussive answers:**

This module enables VoxMind to answer questions intuitively and discussively, going beyond simple "what" questions to handle **why, which, when, how, if, and is it/there** questions.

**Core Architecture:**

| Module | Purpose |
|--------|---------|
| `question_classifier.py` | Classifies question types and extracts topics/intent |
| `knowledge_fetcher.py` | Fetches large chunks from multiple online sources |
| `elaborate_answerer.py` | Generates discussive, multi-perspective answers |
| `question_handler.py` | Main orchestrator with async interface |

---

### Question Types Supported:

| Type | Example | Answer Style |
|------|---------|--------------|
| **WHAT** | "What is machine learning?" | Definitions, explanations |
| **WHY** | "Why is the sky blue?" | Reasons, causes, motivations |
| **HOW** | "How does photosynthesis work?" | Processes, methods, step-by-step |
| **WHICH** | "Which language should I learn?" | Comparisons, recommendations |
| **WHEN** | "When was the internet invented?" | Timeline, historical context |
| **IF** | "What if bees went extinct?" | Hypotheticals, consequences |
| **IS/BOOLEAN** | "Is AI dangerous?" | Verification, nuanced yes/no |

---

### Key Features:

**1. Question Classification (`question_classifier.py`)**
- Detects question type from 9 categories
- Extracts topic, subtopics, and keywords
- Identifies question complexity (simple/moderate/complex)
- Detects requirements: opinions, comparisons, examples, discussion
- Generates optimized search queries per question type

**2. Knowledge Fetching (`knowledge_fetcher.py`)**
- Fetches from multiple sources in parallel:
  - Wikipedia (full articles, sections)
  - DuckDuckGo (instant answers)
  - Reddit (community perspectives)
  - StackExchange (technical answers)
  - Wikidata (structured facts)
  - ArXiv (academic papers)
- Aggregates and scores by reliability
- Extracts main facts, consensus points, different perspectives
- Builds timeline for temporal questions

**3. Elaborate Answering (`elaborate_answerer.py`)**
- Question-type specific answer structures:
  - WHY: Reasoning chains with causes
  - HOW: Step-by-step processes
  - WHICH: Comparative analysis
  - WHEN: Timeline with events
  - IF: Hypothetical consequences
- Multiple answer formats:
  - `brief_answer`: 1-2 sentences
  - `standard_answer`: 3-5 sentences
  - `detailed_answer`: Full elaboration (up to 2000 chars)
  - `speech_optimized`: Cleaned for TTS
- Discussive elements:
  - Different perspectives section
  - Examples with introductions
  - Follow-up question suggestions
  - Proper transitions and elaborations

**4. Answer Orchestration (`question_handler.py`)**
- Async-first architecture with sync wrapper
- Configurable timeouts and source limits
- Statistics tracking
- Graceful error handling

---

### Usage Examples:

```python
from Swadhin.question_answering import answer_question, QuestionAnswerer

# Simple async interface
result = await answer_question("Why do leaves change color in fall?")
print(result.detailed_answer)

# Full control
answerer = QuestionAnswerer()
result = await answerer.answer("How does machine learning work?")

# Access different formats
print(result.brief_answer)      # Quick summary
print(result.standard_answer)   # Moderate detail  
print(result.detailed_answer)   # Full elaboration
print(result.speech_optimized)  # For TTS

# Question-specific data
print(result.reasoning)      # For WHY questions
print(result.steps)          # For HOW questions
print(result.comparisons)    # For WHICH questions
print(result.timeline)       # For WHEN questions
print(result.perspectives)   # Different viewpoints

# Follow-up suggestions
print(result.follow_up_questions)
```

**Classification Only:**
```python
from Swadhin.question_answering import QuestionClassifier

classifier = QuestionClassifier()
analysis = classifier.classify("Why is the sky blue?")

print(analysis.primary_type)    # QuestionType.WHY
print(analysis.topic)           # "sky blue" / "sky is blue"
print(analysis.intent)          # "reason"
print(analysis.complexity)      # "simple"
print(analysis.keywords)        # ["sky", "blue"]

# Get search queries
queries = classifier.get_search_queries(analysis)
# ['sky blue', 'reasons sky blue', 'causes of sky blue', ...]
```

---

### Integration with VoxMind Main:

**New command type in `main.py`:**
```python
# Detected for questions like:
# - "Why is the sky blue?"
# - "How does machine learning work?"
# - "Which programming language is best?"
# - "When was Python invented?"
# - "What if the sun disappeared?"
# - "Is artificial intelligence dangerous?"

{
    'command': 'advanced_question',
    'params': {
        'question': 'Why is the sky blue?',
        'topic': 'sky is blue',
        'question_type': 'why',
        'detailed': True,
    },
    'confidence': 0.92,
    'method': 'advanced_qa'
}
```

**Handler in `execute_command()`:**
- Uses async `_ask_advanced_question()` function
- Falls back to basic knowledge engine if advanced QA unavailable
- Truncates for speech with "continue?" option for long answers

---

### Answer Quality Features:

| Feature | Implementation |
|---------|----------------|
| **Discussive** | Multiple perspectives, "Some argue...", "On the other hand..." |
| **Intuitive** | Natural language flow, conversational transitions |
| **Elaborate** | Main points + examples + perspectives + conclusion |
| **Multi-source** | Wikipedia + Reddit + StackExchange + more |
| **Type-specific** | WHY→reasoning, HOW→steps, WHICH→comparisons |
| **Follow-up** | Suggested next questions based on topic |

---

### Technologies Used:
- `aiohttp` - Async HTTP requests
- `asyncio` - Concurrent source fetching
- Python `re` - Pattern matching for classification
- Python `dataclasses` - Clean data structures

---

### File Locations:
```
Swadhin/
├── question_answering/
│   ├── __init__.py               # Package exports
│   ├── question_classifier.py    # Question type detection
│   ├── knowledge_fetcher.py      # Multi-source fetching
│   ├── elaborate_answerer.py     # Answer generation
│   ├── question_handler.py       # Main orchestrator
│   └── test_question_answering.py # Test suite
```

---

### Test Coverage:

Run tests with:
```bash
cd Swadhin/question_answering
python -m pytest test_question_answering.py -v
```

Tests include:
- ✅ WHAT question classification
- ✅ WHY question classification  
- ✅ HOW question classification
- ✅ WHICH question classification
- ✅ WHEN question classification
- ✅ IF question classification
- ✅ IS/Boolean question classification
- ✅ Topic extraction accuracy
- ✅ Search query generation
- ✅ Complexity detection
- ✅ Requirement detection (opinion, comparison, examples)
- ✅ Full answer pipeline (network required)

---

## Week 4 Enhancement: Elaborate Topics & Explicit Search

### What I added:

**1. Elaborate Topic Triggers in `main.py`:**

Added new command patterns for detailed, discussive answers on topics:

| Trigger | Example | Behavior |
|---------|---------|----------|
| `describe` | "Describe quantum computing" | Detailed explanation |
| `discuss` | "Discuss climate change" | Multiple perspectives |
| `explain` | "Explain machine learning" | Thorough explanation |
| `analyze`/`analyse` | "Analyze the French Revolution" | Analytical breakdown |
| `explore` | "Explore blockchain technology" | Thorough exploration |
| `elaborate` | "Elaborate on AI ethics" | More detail on topic |
| `talk about` | "Talk about space exploration" | Discussive answer |
| `tell me more` | "Tell me everything about Python" | Comprehensive info |
| `teach me` | "Teach me about neural networks" | Educational style |
| `walk through` | "Walk me through photosynthesis" | Step-by-step |
| `break down` | "Break down the water cycle" | Structured breakdown |
| `research` | "Research renewable energy" | In-depth investigation |

All these now route to the `advanced_question` handler for elaborate, multi-source answers.

**2. Explicit Web Search Only:**

Changed search behavior so web search (opening browser) ONLY happens when explicitly requested:

| Will Open Browser | Won't Open Browser |
|-------------------|---------------------|
| "search google for cats" | "describe cats" |
| "google machine learning" | "explain machine learning" |
| "web search for Python" | "tell me about Python" |
| "look up cats on google" | "research renewable energy" |
| "search for X online" | "what is quantum physics" |

**Files Modified:**
- `main.py`: Added `explicit_search_patterns` section before `knowledge_patterns`
- `main.py`: Added `elaborate_topic_patterns` section for detailed answers
- `Priyapal/command_parser.py`: Made search pattern explicit-only

---

## Updated Main Integrator

The `main.py` now includes all five modules:

| Component | Status | Description |
|-----------|--------|-------------|
| Response System | ✅ | Contextual responses with personality |
| Process Mapper | ✅ | App/icon mapping from Task Manager |
| Intonation Engine | ✅ | Human-like voice with prosody |
| Voice Models | ✅ | 6 AI personas (3 male, 3 female) |
| **Question Answering** | ✅ | Elaborate answers for all question types |
| **Elaborate Topics** | ✅ | describe, discuss, explain, analyze triggers |
| **Explicit Search** | ✅ | Only opens browser when explicitly asked |

## Contact
- Tech Lead: Jalaj
- Questions: Team Discord/Slack
- Code Reviews: PR and tag Jalaj
