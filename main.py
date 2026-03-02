"""VoxMind - Voice Assistant Integration"""
import argparse
import sys
import os
import re
from time import sleep
import webbrowser
from datetime import datetime
import subprocess
import threading
import random

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

# Import config and personality modules
from config import is_first_run, set_user_name, get_user_name
from personality import VoxPersonality as Vox

# Backend architecture
from backend.app import BackendApp

# Import Natural Language Engine for life-like VoxMind interaction
try:
    from core.natural_language_engine import (
        NaturalLanguageEngine, get_engine, preprocess, predict, understand
    )
    NLE_AVAILABLE = True
    print("Natural Language Engine: Loaded")
except ImportError as e:
    NLE_AVAILABLE = False
    print(f"Natural Language Engine: Not available ({e})")

def _get_nle_engine():
    if not NLE_AVAILABLE:
        return None
    try:
        return get_engine()
    except Exception:
        return None

# Lazy loading flags
_tts_engine = None
_tts_initialized = False

# Import volume control (lightweight)
try:
    from Soumyadeb.audio.volume_control import (
        volume_up, volume_down, volume_set, volume_mute, volume_unmute, volume_toggle_mute
    )
    VOLUME_CONTROL_AVAILABLE = True
except ImportError:
    VOLUME_CONTROL_AVAILABLE = False
    print("Warning: Volume control module not available")

# Lazy-load brightness control
_sbc = None
def _get_brightness_control():
    global _sbc
    if _sbc is None:
        import screen_brightness_control as sbc
        _sbc = sbc
    return _sbc

# Lazy-load window control
_gw = None
def _get_window_control():
    global _gw
    if _gw is None:
        import pygetwindow as gw
        _gw = gw
    return _gw

# Lazy-load input control (voice-driven mouse/keyboard automation)
_input_controller = None
def _get_input_controller():
    global _input_controller
    if _input_controller is None:
        from core.input_control import get_controller
        _input_controller = get_controller()
    return _input_controller

def _parse_input_command(text: str):
    from core.input_control import parse_input_command
    return parse_input_command(text)

# Lazy-load screen context engine (screen sharing/visual understanding)
_screen_engine = None
def _get_screen_engine():
    global _screen_engine
    if _screen_engine is None:
        from core.screen_context import get_screen_engine
        _screen_engine = get_screen_engine()
    return _screen_engine

# Lazy-load screen monitor (continuous screen watching)
_screen_monitor = None
def _get_screen_monitor():
    global _screen_monitor
    if _screen_monitor is None:
        from core.screen_monitor import get_screen_monitor
        _screen_monitor = get_screen_monitor()
    return _screen_monitor

# Lazy-load app control (launch/close/switch applications)
_app_controller = None
def _get_app_controller():
    global _app_controller
    if _app_controller is None:
        from core.app_control import get_app_controller
        _app_controller = get_app_controller()
    return _app_controller

def _parse_app_command(text: str):
    from core.app_control import parse_app_command
    return parse_app_command(text)

def _launch_via_start_menu(app_name: str) -> bool:
    """
    Launch an app by searching in Start Menu - most reliable for Office, Adobe, etc.
    Uses Windows key + search + Enter.
    """
    import time
    try:
        import pyautogui
        pyautogui.PAUSE = 0.1
        
        # Press Windows key to open Start Menu
        pyautogui.press('win')
        time.sleep(0.4)
        
        # Type the app name to search
        pyautogui.typewrite(app_name, interval=0.03)
        time.sleep(0.6)  # Wait for search results
        
        # Press Enter to launch the first result
        pyautogui.press('enter')
        return True
    except ImportError:
        # Fallback: try using PowerShell to simulate
        try:
            import subprocess
            # Use PowerShell to send keys
            ps_script = f'''
            Add-Type -AssemblyName System.Windows.Forms
            [System.Windows.Forms.SendKeys]::SendWait("^{{ESC}}")
            Start-Sleep -Milliseconds 400
            [System.Windows.Forms.SendKeys]::SendWait("{app_name}")
            Start-Sleep -Milliseconds 600
            [System.Windows.Forms.SendKeys]::SendWait("{{ENTER}}")
            '''
            subprocess.run(['powershell', '-Command', ps_script], 
                          capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return True
        except Exception:
            return False
    except Exception:
        return False

# Lazy-load performance analytics
_analytics = None
def _get_analytics():
    global _analytics
    if _analytics is None:
        from core.performance_analytics import get_analytics
        _analytics = get_analytics()
    return _analytics

# Lazy-load command cache (hashmap for response caching & fingerprinting)
_command_cache = None
def _get_command_cache():
    global _command_cache
    if _command_cache is None:
        from core.command_cache import get_command_cache
        _command_cache = get_command_cache()
    return _command_cache

# Lazy-load knowledge engine (multi-source knowledge aggregation)
_knowledge_engine = None
def _get_knowledge_engine():
    global _knowledge_engine
    if _knowledge_engine is None:
        try:
            from core.knowledge_engine import get_engine
            _knowledge_engine = get_engine()
        except ImportError:
            _knowledge_engine = None
    return _knowledge_engine


def _normalize_topic(topic: str) -> str:
    """
    Normalize a topic for better knowledge lookup.
    
    - Removes leading articles (the, a, an)
    - Converts "X brand" -> "X Inc" for company lookups
    - Converts "X company" -> "X Inc"
    - Capitalizes properly
    """
    t = topic.strip()
    
    # Remove leading articles
    t = re.sub(r'^(the|a|an)\s+', '', t, flags=re.IGNORECASE)
    
    # For "X brand" queries, try "X Inc" for companies
    brand_match = re.match(r'^(.+?)\s+brand$', t, re.IGNORECASE)
    if brand_match:
        name = brand_match.group(1).strip()
        # Common tech/consumer brands -> add "Inc"
        known_brands = ['apple', 'google', 'microsoft', 'amazon', 'meta', 'facebook', 
                       'tesla', 'nvidia', 'intel', 'amd', 'samsung', 'sony', 'lg',
                       'nike', 'adidas', 'coca-cola', 'pepsi', 'disney', 'netflix']
        if name.lower() in known_brands:
            t = f"{name} Inc"
        else:
            t = name  # Just use the name without "brand"
    
    # For "X company" queries, try "X Inc"
    company_match = re.match(r'^(.+?)\s+company$', t, re.IGNORECASE)
    if company_match:
        t = f"{company_match.group(1).strip()} Inc"
    
    return t


async def _ask_knowledge(query: str, detail_level: str = "brief") -> str:
    """Ask the knowledge engine about a topic."""
    try:
        from core.knowledge_engine import ask_knowledge
        # Normalize the query for better results
        normalized = _normalize_topic(query)
        return await ask_knowledge(normalized, detail_level=detail_level)
    except Exception as e:
        return f"I couldn't find information about that. Error: {e}"


# Lazy-load advanced question answerer (handles why, how, when, which, if, is questions)
_question_answerer = None
def _get_question_answerer():
    global _question_answerer
    if _question_answerer is None:
        try:
            from Swadhin.question_answering import QuestionAnswerer
            _question_answerer = QuestionAnswerer()
        except ImportError:
            _question_answerer = None
    return _question_answerer


async def _ask_advanced_question(question: str, detailed: bool = False) -> str:
    """
    Answer questions elaborately using advanced QA system.
    
    Handles: what, why, which, when, how, if, is it/there questions.
    Provides discussive, intuitive answers with multiple perspectives.
    """
    answerer = None
    try:
        from Swadhin.question_answering import QuestionAnswerer
        answerer = QuestionAnswerer()
        result = await answerer.answer(question)
        
        # Clean up the fetcher session
        if hasattr(answerer, 'fetcher') and answerer.fetcher:
            await answerer.fetcher.close()
        
        if detailed:
            return result.detailed_answer
        else:
            return result.standard_answer
    except ImportError:
        # Fallback to basic knowledge engine
        return await _ask_knowledge(question, detail_level="detailed" if detailed else "brief")
    except Exception as e:
        # Try to clean up even on error
        if answerer and hasattr(answerer, 'fetcher') and answerer.fetcher:
            try:
                await answerer.fetcher.close()
            except Exception:
                pass
        return f"I had trouble researching that question. {e}"


def _is_advanced_question(text: str) -> bool:
    """
    Check if text is an advanced question type that needs elaborate answering.
    
    Detects: why, which, when, how, if, is it/there questions.
    """
    t = text.lower().strip()
    
    # Advanced question patterns (beyond simple "what is")
    advanced_patterns = [
        # WHY questions - reasons, causes
        r'^why\s+',
        r'(?:what|for what)\s+reason',
        r'what\s+causes?\s+',
        r'what\s+(?:is|are)\s+the\s+(?:reason|cause)',
        
        # HOW questions - methods, processes
        r'^how\s+(?:do|does|did|can|could|would|should|will)\s+',
        r'^how\s+to\s+',
        r'^how\s+come\s+',
        r'(?:what|which)\s+(?:is|are)\s+the\s+(?:process|method|way|step)',
        
        # WHICH questions - comparisons, choices
        r'^which\s+',
        r'(?:what|which)\s+(?:is|are)\s+(?:the\s+)?(?:best|better|worst|worse)',
        r'(?:should\s+i|would\s+you)\s+(?:choose|pick|select|use)',
        r'(?:compare|versus|vs\.?)\s+',
        
        # WHEN questions - temporal
        r'^when\s+',
        r'(?:what|at what)\s+time\s+',
        r'what\s+(?:year|date|day|month|period)\s+',
        r'(?:how\s+long)\s+(?:ago|until|before|after)\s+',
        
        # IF questions - hypotheticals
        r'^(?:what\s+)?if\s+',
        r'^suppose\s+',
        r'^hypothetically\s+',
        r'^(?:is|are|would)\s+it\s+possible\s+',
        
        # IS/Boolean questions - verification
        r'^(?:is|are|was|were)\s+(?:it|there|this|that)\s+',
        r'^(?:can|could|will|would|should|does|did|has|have)\s+',
        r'^(?:isn\'?t|aren\'?t|can\'?t|couldn\'?t|won\'?t|wouldn\'?t)\s+',
        
        # Complex "what" questions that need discussion
        r'^what\s+(?:would|could|might)\s+happen',
        r'^what\s+(?:are|is)\s+the\s+(?:advantage|disadvantage|benefit|drawback|pros?|cons?)',
        r'^what\s+(?:are|is)\s+the\s+(?:difference|similarity)',
        r'^what\s+(?:should|would)\s+',
    ]
    
    import re
    return any(re.search(pattern, t) for pattern in advanced_patterns)

# Lazy-load Windows UI controller (taskbar, start menu, icons)
_windows_ui = None
def _get_windows_ui():
    global _windows_ui
    if _windows_ui is None:
        try:
            from core.windows_ui import get_windows_ui
            _windows_ui = get_windows_ui()
        except ImportError:
            _windows_ui = None
    return _windows_ui

def _parse_windows_ui_command(text: str):
    try:
        from core.windows_ui import parse_windows_ui_command
        return parse_windows_ui_command(text)
    except ImportError:
        return None

def _execute_windows_ui_command(parsed: dict):
    try:
        from core.windows_ui import execute_windows_ui_command
        return execute_windows_ui_command(parsed)
    except ImportError:
        return False, "Windows UI control not available"

# Lazy-load overlay manager (visual grid, number labels)
_overlay_manager = None
def _get_overlay_manager():
    global _overlay_manager
    if _overlay_manager is None:
        try:
            from core.overlay_manager import OverlayManager
            _overlay_manager = OverlayManager()
        except ImportError:
            _overlay_manager = None
    return _overlay_manager

# Lazy-load smart overlay (natural language element targeting)
_smart_overlay = None
def _get_smart_overlay():
    global _smart_overlay
    if _smart_overlay is None:
        try:
            from core.smart_overlay import SmartOverlay
            _smart_overlay = SmartOverlay()
        except ImportError:
            _smart_overlay = None
    return _smart_overlay

# Lazy-load intelligent response engine (varied responses, disambiguation, context)
_intelligent_response = None
def _get_intelligent_response():
    global _intelligent_response
    if _intelligent_response is None:
        try:
            from core.intelligent_response import get_intelligent_response_engine
            _intelligent_response = get_intelligent_response_engine()
        except ImportError:
            _intelligent_response = None
    return _intelligent_response

def _get_varied_response(template_key: str, **kwargs) -> str:
    """Get a varied response to avoid repetition."""
    engine = _get_intelligent_response()
    if engine:
        try:
            return engine.variation.get_response(template_key, **kwargs)
        except Exception:
            pass
    return None

# Lazy-load self-awareness system (introspection, capability discovery)
_self_awareness = None
def _get_self_awareness():
    global _self_awareness
    if _self_awareness is None:
        try:
            from core.self_awareness import SelfAwareVoxMind
            _self_awareness = SelfAwareVoxMind()
        except ImportError:
            _self_awareness = None
    return _self_awareness

# Lazy-load unified memory (conversation context, pronoun resolution)
_unified_memory = None
def _get_memory():
    global _unified_memory
    if _unified_memory is None:
        try:
            from core.unified_memory import get_memory
            _unified_memory = get_memory()
        except ImportError:
            _unified_memory = None
    return _unified_memory

def _record_to_memory(user_input: str, response: str, command: str, 
                      entities: dict = None, success: bool = True):
    """Record a command to unified memory for context tracking."""
    memory = _get_memory()
    if memory:
        try:
            memory.record(user_input, response, command, entities, success)
        except Exception:
            pass

def _resolve_pronouns(text: str, entities: dict = None) -> dict:
    """Resolve pronouns like 'it', 'that' using memory context."""
    memory = _get_memory()
    if memory:
        try:
            return memory.resolve_pronouns(text, entities)
        except Exception:
            pass
    return entities or {}


# Lazy-load voice models (AI personas: Jarvis, Vision, Edith, Elisa, Sofia, Friday)
_voice_engine = None
def _get_voice_engine():
    global _voice_engine
    if _voice_engine is None:
        try:
            from Swadhin.voice_models import get_voice_engine
            _voice_engine = get_voice_engine("friday")  # Default to Friday
        except ImportError:
            _voice_engine = None
    return _voice_engine

def _set_voice(voice_name: str) -> bool:
    """Switch to a different voice persona."""
    engine = _get_voice_engine()
    if engine:
        result = engine.set_voice(voice_name)
        # Also update TTS persona
        try:
            from minakshi.text_to_speech import set_voice_persona
            set_voice_persona(voice_name)
        except ImportError:
            pass
        return result
    return False

def _get_current_voice() -> dict:
    """Get info about the current voice persona."""
    engine = _get_voice_engine()
    if engine:
        return engine.get_voice_info()
    return None

def _list_available_voices() -> list:
    """List all available voice personas."""
    engine = _get_voice_engine()
    if engine:
        return engine.list_voices()
    return []

def _voice_greet() -> str:
    """Get greeting from current voice persona."""
    engine = _get_voice_engine()
    if engine:
        return engine.greet()
    return "Hello!"


# Import basic components (lightweight)
from Jalaj.speech_recognition_service import listen_for_command
from Tejas.wake_word_detector import listen_for_wake_word
from Priyapal.command_parser import parse_command as basic_parse

# Try to import NLP parser (deferred loading)
NLP_AVAILABLE = False
parse_command_nlp = None
try:
    from Tejas.nlp_command_parser import NLP_AVAILABLE as _nlp_avail
    NLP_AVAILABLE = _nlp_avail
    if NLP_AVAILABLE:
        from Tejas.nlp_command_parser import parse_command_nlp, NLPCommandParser
        # Start background model loading
        NLPCommandParser.preload_model()
        print("NLP Parser: Loading in background...")
    else:
        print("NLP Parser: Disabled (dependencies not installed)")
except ImportError:
    print("NLP Parser: Disabled (module not found)")

def _get_tts_engine():
    """Lazy-initialize TTS engine."""
    global _tts_engine, _tts_initialized
    if not _tts_initialized:
        try:
            import pyttsx3
            _tts_engine = pyttsx3.init()
            _tts_engine.setProperty('rate', 180)
            _tts_engine.setProperty('volume', 0.9)
        except Exception as e:
            print(f"[TTS Init Warning]: {e}")
            _tts_engine = None
        _tts_initialized = True
    return _tts_engine

def _reinit_tts_engine():
    """Reinitialize TTS engine after failure."""
    global _tts_engine, _tts_initialized
    _tts_initialized = False
    _tts_engine = None
    return _get_tts_engine()

def speak_text(text):
    """Lazy-loaded TTS function with auto-recovery."""
    engine = _get_tts_engine()
    if engine:
        try:
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"[TTS Error]: {e} - Attempting recovery...")
            engine = _reinit_tts_engine()
            if engine:
                try:
                    engine.say(text)
                    engine.runAndWait()
                except Exception as e2:
                    print(f"[TTS Failed]: {e2}")
                    print(f"[TTS Fallback]: {text}")
            else:
                print(f"[TTS Fallback]: {text}")
    else:
        print(f"[TTS]: {text}")

# Try to use optimized TTS from minakshi module with voice persona support
try:
    from minakshi.text_to_speech import speak_text_with_persona as speak_text
    from minakshi.text_to_speech import speak_as_persona, set_voice_persona, get_voice_persona
    print("TTS: Using minakshi.text_to_speech module with voice personas")
except Exception as e:
    print(f"TTS: Using built-in fallback (minakshi module not loaded: {e})")
    # Fallback functions
    def set_voice_persona(name): pass
    def get_voice_persona(): return "default"
    def speak_as_persona(text, persona=None, **kw): speak_text(text)

def parse_command(text: str) -> dict:
    """Parse command using NLP if available, otherwise fall back to basic parser.
    
    Returns a unified format: {'command': ..., 'params': {...}}
    
    Now enhanced with Natural Language Engine for:
    - Fuzzy matching (handles typos/speech errors)
    - Word prediction
    - Context-aware reference resolution
    - Pronoun resolution ("close it" -> "close chrome")
    """
    import re
    
    # Step 1: Preprocess with Natural Language Engine
    if NLE_AVAILABLE:
        engine = get_engine()
        # Update engine with current user name
        user_name = get_user_name() or "sir"
        engine.set_user_name(user_name)
        
        # Full understanding pipeline
        understanding = engine.understand(text)
        text = understanding['preprocessed_text']
        is_follow_up = understanding['is_follow_up']
        last_intent = understanding['last_intent']
    else:
        is_follow_up = False
        last_intent = None
    
    # Step 2: Check for pronouns and resolve from memory context
    memory = _get_memory()
    original_text = text
    pronoun_resolved_entities = {}
    
    if memory:
        # Check if this looks like a follow-up with pronouns
        text_lower = text.lower()
        has_pronoun = any(p in text_lower for p in [' it', ' that', ' this', ' them', 'close it', 'open it'])
        
        if has_pronoun or is_follow_up:
            # Get resolved entities from memory
            pronoun_resolved_entities = memory.resolve_pronouns(text, {})
            
            # If we resolved an app, inject it into the text for better parsing
            if 'app' in pronoun_resolved_entities:
                resolved_app = pronoun_resolved_entities['app']
                # Replace "it", "that" with actual app name for parsing
                text = re.sub(r'\bit\b', resolved_app, text, flags=re.IGNORECASE)
                text = re.sub(r'\bthat\b', resolved_app, text, flags=re.IGNORECASE)
    
    t = text.lower().strip()
    
    # =========================================================================
    # CONVERSATIONAL RESPONSES (greetings, thanks, etc.)
    # Note: "how are you" is handled in introspection for self-status
    # =========================================================================
    greetings = ['how do you do', 'how\'s it going', 'what\'s up', 'howdy', 'hey there', 'hello there']
    if any(g in t for g in greetings):
        return {
            'command': 'conversation',
            'params': {'type': 'greeting'},
            'confidence': 0.95,
            'method': 'conversation'
        }
    
    thanks_phrases = ['thank you', 'thanks', 'thank', 'appreciate it', 'good job', 'well done', 'nice work']
    if any(p in t for p in thanks_phrases):
        return {
            'command': 'conversation',
            'params': {'type': 'thanks'},
            'confidence': 0.95,
            'method': 'conversation'
        }
    
    goodbye_phrases = ['goodbye', 'bye', 'see you', 'later', 'take care']
    if any(p in t for p in goodbye_phrases) and 'search' not in t:
        return {
            'command': 'conversation',
            'params': {'type': 'goodbye'},
            'confidence': 0.95,
            'method': 'conversation'
        }
    
    # =========================================================================
    # DAEMON / BACKGROUND SERVICE MODE
    # =========================================================================
    daemon_patterns = ['run daemon', 'start daemon', 'background mode', 
                       'always listening', 'run as service', 'stay running',
                       'run in background']
    if any(p in t for p in daemon_patterns):
        return {
            'command': 'daemon',
            'params': {'action': 'start'},
            'confidence': 0.95,
            'method': 'daemon'
        }
    
    # =========================================================================
    # SELF-IDENTITY QUESTIONS (before knowledge to avoid "Your Name" movie issue)
    # =========================================================================
    identity_patterns = [
        'what is your name', 'what\'s your name', 'who are you', 
        'what are you', 'what should i call you', 'your name',
        'tell me your name', 'what do i call you', 'introduce yourself',
        'what are you called', 'who am i talking to', 'who am i speaking to'
    ]
    if any(p in t for p in identity_patterns):
        return {
            'command': 'conversation',
            'params': {'type': 'identity'},
            'confidence': 0.98,
            'method': 'conversation'
        }
    
    # Capabilities questions
    capability_patterns = [
        'what can you do', 'what are your capabilities', 'what do you do',
        'how can you help', 'what are you capable of', 'show me what you can do',
        'list your features', 'what features do you have'
    ]
    if any(p in t for p in capability_patterns):
        return {
            'command': 'assistant_help',
            'params': {},
            'confidence': 0.95,
            'method': 'conversation'
        }
    
    # Introspection commands ("can you do X?", "how are you?", self-awareness)
    can_you_match = re.match(r'^can\s+you\s+(.+)\??$', t, re.IGNORECASE)
    if can_you_match:
        task = can_you_match.group(1).strip()
        return {
            'command': 'introspection',
            'params': {'type': 'can_do', 'task': task},
            'confidence': 0.9,
            'method': 'self_awareness'
        }
    
    how_are_you_patterns = [
        'how are you', 'how are you doing', 'how do you feel',
        'are you okay', 'are you alright', 'what is your status',
        'system status', 'status report', 'give me a status'
    ]
    if any(p in t for p in how_are_you_patterns):
        return {
            'command': 'introspection',
            'params': {'type': 'status'},
            'confidence': 0.9,
            'method': 'self_awareness'
        }
    
    # Backend diagnostics commands
    backend_health_patterns = ['health check', 'check health', 'backend status', 'system health']
    if any(p in t for p in backend_health_patterns):
        return {
            'command': 'backend_health',
            'params': {},
            'confidence': 0.95,
            'method': 'backend'
        }
    
    telemetry_patterns = ['telemetry', 'show telemetry', 'command stats', 'statistics', 'usage stats']
    if any(p in t for p in telemetry_patterns):
        return {
            'command': 'backend_telemetry',
            'params': {},
            'confidence': 0.95,
            'method': 'backend'
        }
    
    undo_patterns = ['undo', 'undo that', 'take that back', 'what did i say', 'last command', 'previous command']
    if any(p in t for p in undo_patterns):
        return {
            'command': 'command_history',
            'params': {'action': 'last'},
            'confidence': 0.9,
            'method': 'backend'
        }
    
    # =========================================================================
    # VOICE PERSONA COMMANDS (voice jarvis, voice sofia, list voices, etc.)
    # =========================================================================
    voice_names = ['jarvis', 'vision', 'edith', 'elisa', 'sofia', 'friday', 'default']
    
    # "voice sofia", "switch to jarvis", "use friday voice"
    voice_patterns = [
        r'^voice\s+(\w+)$',
        r'^(?:switch|change)\s+(?:to\s+)?(\w+)(?:\s+voice)?$',
        r'^(?:use|set)\s+(\w+)\s+voice$',
        r'^(?:speak|talk)\s+(?:like|as)\s+(\w+)$',
    ]
    
    for pattern in voice_patterns:
        match = re.match(pattern, t, re.IGNORECASE)
        if match:
            voice_name = match.group(1).lower()
            if voice_name in voice_names:
                return {
                    'command': 'voice_model',
                    'params': {'voice': voice_name, 'action': 'set'},
                    'confidence': 0.95,
                    'method': 'voice_persona'
                }
    
    # "list voices", "what voices do you have", "available voices"
    list_voice_patterns = [
        'list voices', 'show voices', 'available voices', 
        'what voices', 'which voices', 'voices available',
        'what voices do you have', 'your voices'
    ]
    if any(p in t for p in list_voice_patterns):
        return {
            'command': 'voice_model',
            'params': {'action': 'list'},
            'confidence': 0.95,
            'method': 'voice_persona'
        }
    
    # =========================================================================
    # MATHEMATICS (calculus, algebra, statistics, etc.)
    # =========================================================================
    math_patterns = [
        # Integrals
        (r'^(?:what\s+is\s+)?(?:the\s+)?integr(?:al|ate)\s+(?:of\s+)?(.+?)(?:\s+d([a-z]))?$', 'integral'),
        (r'^(?:∫|int)\s*(.+?)\s*d([a-z])', 'integral'),
        (r'^(?:solve\s+)?(?:the\s+)?integral\s+(?:of\s+)?(.+)', 'integral'),
        # Derivatives
        (r'^(?:what\s+is\s+)?(?:the\s+)?(?:derivative|differentiate|diff)\s+(?:of\s+)?(.+)', 'derivative'),
        (r'^d/d([a-z])\s*\[?\s*(.+?)\s*\]?$', 'derivative'),
        # Limits
        (r'^(?:what\s+is\s+)?(?:the\s+)?limit\s+(?:of\s+)?(.+)', 'limit'),
        # Solve equations
        (r'^solve\s+(?:the\s+)?(?:equation\s+)?(.+)', 'solve'),
        (r'^(?:find|what\s+(?:is|are))\s+(?:the\s+)?(?:root|roots|solution|solutions)\s+(?:of\s+)?(.+)', 'solve'),
        # Simplify/expand
        (r'^simplify\s+(.+)', 'simplify'),
        (r'^expand\s+(.+)', 'expand'),
        (r'^factor(?:ize)?\s+(.+)', 'factor'),
        # Statistics
        (r'^(\d+)\s+choose\s+(\d+)', 'combination'),
        (r'^(\d+)\s*!$', 'factorial'),
        (r'^(?:what\s+is\s+)?(\d+)\s+factorial', 'factorial'),
        # Matrix operations
        (r'^(?:find\s+)?(?:the\s+)?determinant\s+(?:of\s+)?(.+)', 'matrix'),
        (r'^(?:find\s+)?(?:the\s+)?inverse\s+(?:of\s+)?(?:matrix\s+)?(.+)', 'matrix'),
        (r'^(?:find\s+)?(?:the\s+)?eigenvalues?\s+(?:of\s+)?(.+)', 'matrix'),
        # Series
        (r'^taylor\s+(?:series\s+)?(?:of\s+)?(.+)', 'series'),
        (r'^maclaurin\s+(?:series\s+)?(?:of\s+)?(.+)', 'series'),
        # General math
        (r'^(?:calculate|compute|evaluate)\s+(.+)', 'calculate'),
    ]
    
    for pattern, math_type in math_patterns:
        match = re.match(pattern, t, re.IGNORECASE)
        if match:
            return {
                'command': 'math',
                'params': {
                    'query': text.strip(),
                    'math_type': math_type
                },
                'confidence': 0.95,
                'method': 'math'
            }
    
    # Open math blackboard
    if any(p in t for p in ['open math', 'math blackboard', 'open blackboard', 'math solver', 'open calculator']):
        return {
            'command': 'open_blackboard',
            'params': {},
            'confidence': 0.95,
            'method': 'math'
        }
    
    # =========================================================================
    # EXPLICIT WEB SEARCH (only when user says "search google", "google for", etc.)
    # =========================================================================
    explicit_search_patterns = [
        r'^(?:search\s+(?:google|bing|online|the\s+web|on\s+google|on\s+bing)\s+(?:for\s+)?(.+))$',
        r'^(?:google\s+(?:for\s+)?(.+))$',
        r'^(?:search\s+for\s+(.+)\s+(?:on\s+google|online|on\s+the\s+web))$',
        r'^(?:look\s+up\s+(.+)\s+(?:on\s+google|online))$',
        r'^(?:find\s+(.+)\s+(?:on\s+google|online|on\s+the\s+web))$',
        r'^(?:web\s+search\s+(?:for\s+)?(.+))$',
    ]
    
    for pattern in explicit_search_patterns:
        match = re.match(pattern, t, re.IGNORECASE)
        if match:
            query = match.group(1).strip().rstrip('?')
            return {
                'command': 'search',
                'params': {'query': query},
                'confidence': 0.98,
                'method': 'explicit_search'
            }
    
    # =========================================================================
    # KNOWLEDGE QUERIES ("tell me about X", "who is X", "what is X", "define X")
    # =========================================================================
    knowledge_patterns = [
        (r'^(?:tell\s+(?:me\s+)?(?:something\s+)?about|about)\s+(.+)$', 'brief'),
        (r'^(?:who\s+(?:is|was|are|were))\s+(.+)$', 'brief'),
        (r'^(?:what\s+(?:is|are|was|were))\s+(.+)$', 'brief'),
        (r'^(?:define)\s+(.+)$', 'brief'),
        (r'^(?:what\s+(?:does|do))\s+(.+?)\s+mean$', 'brief'),
        (r'^(?:give\s+me\s+)?(?:information|info)\s+(?:about|on)\s+(.+)$', 'brief'),
        # "do you know X", "have you heard of X"
        (r'^(?:do\s+you\s+know\s+(?:about\s+)?(?:the\s+)?|have\s+you\s+heard\s+of\s+)(.+)$', 'brief'),
    ]
    
    # =========================================================================
    # ELABORATE TOPIC PATTERNS (describe, discuss, explain, analyze, explore)
    # These trigger detailed, discussive answers
    # =========================================================================
    elaborate_topic_patterns = [
        # Describe - detailed explanation
        (r'^describe\s+(.+)$', 'complex'),
        (r'^(?:give\s+(?:me\s+)?)?(?:a\s+)?description\s+(?:of|about)\s+(.+)$', 'complex'),
        
        # Discuss - discussive, multiple perspectives
        (r'^discuss\s+(.+)$', 'complex'),
        (r'^(?:let\'?s\s+)?(?:have\s+a\s+)?discussion\s+(?:about|on)\s+(.+)$', 'complex'),
        
        # Explain - thorough explanation
        (r'^explain\s+(.+)$', 'complex'),
        (r'^(?:give\s+(?:me\s+)?)?(?:an?\s+)?explanation\s+(?:of|about|for)\s+(.+)$', 'complex'),
        
        # Analyze - analytical breakdown
        (r'^analyze\s+(.+)$', 'complex'),
        (r'^analyse\s+(.+)$', 'complex'),  # British spelling
        (r'^(?:give\s+(?:me\s+)?)?(?:an?\s+)?analysis\s+(?:of|about|on)\s+(.+)$', 'complex'),
        
        # Explore - thorough exploration
        (r'^explore\s+(.+)$', 'complex'),
        (r'^(?:let\'?s\s+)?exploration\s+(?:of|about)\s+(.+)$', 'complex'),
        
        # Elaborate - more detail
        (r'^elaborate\s+(?:on\s+)?(.+)$', 'complex'),
        (r'^(?:give\s+(?:me\s+)?)?(?:more\s+)?(?:detail|details)\s+(?:about|on)\s+(.+)$', 'complex'),
        
        # In-depth / comprehensive
        (r'^(?:in[- ]?depth|detailed|comprehensive)\s+(?:info(?:rmation)?|explanation|overview)\s+(?:about|on|of)\s+(.+)$', 'complex'),
        (r'^(?:research|look\s+into|investigate)\s+(.+)$', 'complex'),
        
        # Talk about / tell me more
        (r'^(?:talk|speak)\s+(?:to\s+me\s+)?about\s+(.+)$', 'complex'),
        (r'^tell\s+me\s+(?:more|everything|all)\s+about\s+(.+)$', 'complex'),
        
        # Teach / educate
        (r'^teach\s+me\s+(?:about\s+)?(.+)$', 'complex'),
        (r'^educate\s+me\s+(?:about|on)\s+(.+)$', 'complex'),
        
        # Break down / walk through
        (r'^break\s+(?:it\s+)?down[:]?\s+(.+)$', 'complex'),
        (r'^walk\s+(?:me\s+)?through\s+(.+)$', 'complex'),
    ]
    
    for pattern, question_type in elaborate_topic_patterns:
        match = re.match(pattern, t, re.IGNORECASE)
        if match:
            topic = match.group(1).strip().rstrip('?')
            # Skip self-referential questions
            self_words = ['your name', 'you', 'yourself', 'voxmind', 'vox']
            if not any(sw in topic.lower() for sw in self_words):
                return {
                    'command': 'advanced_question',
                    'params': {
                        'question': text.strip(),
                        'topic': topic,
                        'question_type': question_type,
                        'detailed': True,  # Always detailed for elaborate patterns
                    },
                    'confidence': 0.93,
                    'method': 'elaborate_topic'
                }
    
    # =========================================================================
    # ADVANCED QUESTIONS (why, how, which, when, if, is it/there)
    # These require elaborate, discussive answers
    # =========================================================================
    advanced_question_patterns = [
        # WHY questions - reasons, causes, motivations
        (r'^why\s+(?:is|are|was|were|does|do|did|can|could|would|should|will|don\'?t|doesn\'?t|didn\'?t)?\s*(.+)$', 'why'),
        (r'^(?:what|for what)\s+reason\s+(.+)$', 'why'),
        (r'^what\s+causes?\s+(.+)$', 'why'),
        (r'^what\s+(?:is|are)\s+the\s+(?:reason|cause)\s+(?:for|of|behind)\s+(.+)$', 'why'),
        
        # HOW questions - methods, processes, instructions
        (r'^how\s+(?:do|does|did|can|could|would|should|will)\s+(.+)$', 'how'),
        (r'^how\s+to\s+(.+)$', 'how'),
        (r'^how\s+come\s+(.+)$', 'how'),
        (r'^(?:what|which)\s+(?:is|are)\s+the\s+(?:process|method|way|step)s?\s+(?:to|for)\s+(.+)$', 'how'),
        (r'^(?:tell|show|teach|explain)\s+(?:me\s+)?how\s+(?:to\s+)?(.+)$', 'how'),
        
        # WHICH questions - comparisons, choices
        (r'^which\s+(?:is|are|was|were|one|ones|should|would|could)\s*(.+)$', 'which'),
        (r'^which\s+(.+)\s+(?:should|would|could|do)\s+', 'which'),
        (r'^which\s+(.+)$', 'which'),  # Catch-all for which questions
        (r'^(?:what|which)\s+(?:is|are)\s+(?:the\s+)?(?:best|better|worst|worse)\s+(.+)$', 'which'),
        (r'^(?:should\s+i|would\s+you)\s+(?:choose|pick|select|use|learn)\s+(.+)$', 'which'),
        # "X versus Y" but NOT "X vs code" (VS Code is an app name)
        (r'^(.+)\s+(?:versus)\s+(.+)\??$', 'which'),
        (r'^(.+)\s+vs\.?\s+(?!code\b)(.+)\??$', 'which'),
        
        # WHEN questions - temporal, dates, timing
        (r'^when\s+(?:is|are|was|were|does|do|did|can|could|would|should|will)?\s*(.+)$', 'when'),
        (r'^(?:what|at what)\s+time\s+(.+)$', 'when'),
        (r'^what\s+(?:year|date|day|month|period)\s+(.+)$', 'when'),
        (r'^(?:how\s+long)\s+(?:ago|until|before|after)\s+(.+)$', 'when'),
        
        # IF questions - hypotheticals, conditionals
        (r'^(?:what\s+)?if\s+(.+)$', 'if'),
        (r'^(?:what\s+)?(?:would|could|might)\s+happen\s+if\s+(.+)$', 'if'),
        (r'^suppose\s+(.+)$', 'if'),
        (r'^assuming\s+(.+)$', 'if'),
        (r'^hypothetically[,]?\s+(.+)$', 'if'),
        
        # IS/Boolean questions - verification, existence
        (r'^(?:is|are|was|were)\s+(?:it|there|this|that)\s+(.+)$', 'boolean'),
        (r'^(?:is|are|was|were)\s+(.+)\s+(?:true|real|possible|correct|right|dangerous|safe|good|bad|better|worse|legal|illegal|healthy|harmful)[\?\s]*$', 'boolean'),
        (r'^(?:is|are)\s+(.+)$', 'boolean'),  # Catch-all for "is X?" questions
        (r'^(?:can|could|will|would|should|does|did|has|have)\s+(.+)$', 'boolean'),
        (r'^(?:isn\'?t|aren\'?t|wasn\'?t|weren\'?t|can\'?t|couldn\'?t)\s+(.+)$', 'boolean'),
        
        # Complex questions needing discussion
        (r'^what\s+(?:would|could|might)\s+happen\s+(.+)$', 'complex'),
        (r'^what\s+(?:are|is)\s+the\s+(?:advantage|disadvantage|benefit|drawback|pros?|cons?)s?\s+(?:of|to)\s+(.+)$', 'complex'),
        (r'^what\s+(?:are|is)\s+the\s+(?:difference|similarity)s?\s+between\s+(.+)$', 'complex'),
    ]
    
    for pattern, question_type in advanced_question_patterns:
        match = re.match(pattern, t, re.IGNORECASE)
        if match:
            topic = match.group(1).strip().rstrip('?')
            # Skip self-referential questions  
            self_words = ['your name', 'you', 'yourself', 'voxmind', 'vox']
            if not any(sw in topic.lower() for sw in self_words):
                return {
                    'command': 'advanced_question',
                    'params': {
                        'question': text.strip(),  # Keep original question
                        'topic': topic,
                        'question_type': question_type,
                        'detailed': question_type in ('why', 'how', 'complex'),
                    },
                    'confidence': 0.92,
                    'method': 'advanced_qa'
                }
    
    # Standard knowledge patterns (simple "what is" questions)
    for pattern, detail_level in knowledge_patterns:
        match = re.match(pattern, t, re.IGNORECASE)
        if match:
            topic = match.group(1).strip()
            # Filter out screen-related queries, self-references, and system queries
            screen_words = ['screen', 'display', 'monitor', 'window']
            self_words = ['your name', 'you', 'yourself', 'voxmind', 'vox']
            system_words = ['active apps', 'active windows', 'my apps', 'my windows', 'running apps', 
                           'running windows', 'open apps', 'open windows', 'my active']
            if (not any(sw in topic for sw in screen_words) and 
                not any(sw in topic for sw in self_words) and
                not any(sw in topic.lower() for sw in system_words)):
                return {
                    'command': 'knowledge',
                    'params': {'topic': topic, 'detail_level': detail_level},
                    'confidence': 0.9,
                    'method': 'knowledge'
                }
    
    # Check for screen monitoring commands
    monitor_triggers = [
        ('start watching', 'start'),
        ('start monitoring', 'start'),
        ('watch my screen', 'start'),
        ('keep watching', 'start'),
        ('stop watching', 'stop'),
        ('stop monitoring', 'stop'),
        ('pause watching', 'pause'),
        ('resume watching', 'resume'),
        ('what changed', 'summary'),
        ('screen activity', 'summary'),
        ('what have you seen', 'summary'),
    ]
    for trigger, action in monitor_triggers:
        if trigger in t:
            return {
                'command': 'screen_monitor',
                'params': {'action': action},
                'confidence': 0.95,
                'method': 'screen_monitor'
            }
    
    # Check for screen context commands FIRST (before NLP)
    screen_triggers = [
        'what do you see', 'what\'s on screen', 'what is on screen',
        'read the screen', 'read my screen', 'look at my screen',
        'what am i looking at', 'describe the screen', 'screen context',
        'what\'s on my screen', 'analyze screen', 'share screen',
        'look at this', 'what is this', 'help me with this',
    ]
    if any(trigger in t for trigger in screen_triggers):
        action = 'describe'
        target = None
        if 'click on' in t:
            action = 'click'
            import re
            match = re.search(r'click on ["\']?(.+?)["\']?$', t)
            if match:
                target = match.group(1).strip()
        elif 'find' in t and 'on screen' in t:
            action = 'find'
            import re
            match = re.search(r'find (?:on screen |the )?["\']?(.+?)["\']?$', t)
            if match:
                target = match.group(1).strip()
        
        return {
            'command': 'screen_context',
            'params': {'action': action, 'target': target},
            'confidence': 0.95,
            'method': 'screen_context'
        }
    
    # Check for click on <text> pattern
    if 'click on' in t:
        import re
        match = re.search(r'click on ["\']?(.+?)["\']?$', t)
        if match:
            return {
                'command': 'screen_context',
                'params': {'action': 'click', 'target': match.group(1).strip()},
                'confidence': 0.9,
                'method': 'screen_context'
            }
    
    # Check for find on screen pattern
    if 'find' in t and ('on screen' in t or 'on my screen' in t):
        import re
        match = re.search(r'find ["\']?(.+?)["\']?\s*on (?:my )?screen', t)
        if match:
            return {
                'command': 'screen_context',
                'params': {'action': 'find', 'target': match.group(1).strip()},
                'confidence': 0.9,
                'method': 'screen_context'
            }
    
    # Check for name change command
    if any(phrase in t for phrase in ['call me', 'my name is', 'change my name', 'rename me']):
        import re
        # Extract the new name
        patterns = [
            r"call me (\w+)",
            r"my name is (\w+)",
            r"change my name to (\w+)",
            r"rename me to (\w+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, t)
            if match:
                new_name = match.group(1).title()
                return {
                    'command': 'change_name',
                    'params': {'name': new_name},
                    'confidence': 1.0,
                    'method': 'pattern'
                }
    
    # =========================================================================
    # WINDOWS UI COMMANDS (taskbar, start menu, desktop icons)
    # =========================================================================
    windows_ui_triggers = [
        'start menu', 'open start', 'click start', 'show start', 'close start',
        'taskbar', 'system tray', 'notification', 'quick settings',
        'desktop icon', 'show desktop', 'task view',
        'snap left', 'snap right', 'snap top', 'snap bottom',
        'close window', 'minimize window', 'maximize window',
        'run dialog', 'clipboard history', 'take screenshot', 'snipping',
        'emoji', 'file explorer', 'open settings',
        # Active windows and switching
        'active apps', 'active windows', 'open apps', 'open windows', 'running apps',
        'previous window', 'last window', 'back to', 'alt tab',
        'focus window', 'activate window', 'enable window', 'switch to',
        'split screen', 'side by side', '50 50', 'split half',
        # Questions about windows/screen
        'what windows', 'which windows', 'windows are open', 'apps are open',
        'what is open', 'what\'s open', 'what is running', 'what\'s running',
    ]
    
    # Handle bare 'start' command specially
    if t == 'start':
        return {
            'command': 'windows_ui',
            'params': {'type': 'windows_ui', 'action': 'open_start'},
            'confidence': 0.95,
            'method': 'windows_ui'
        }
    
    # Handle bare system commands (shutdown, sleep, restart, lock)
    if t in ['shutdown', 'shut down']:
        return {
            'command': 'system_power',
            'params': {'mode': 'shutdown'},
            'confidence': 0.98,
            'method': 'direct_command'
        }
    
    if t in ['sleep', 'go to sleep']:
        return {
            'command': 'system_power',
            'params': {'mode': 'sleep'},
            'confidence': 0.98,
            'method': 'direct_command'
        }
    
    if t in ['restart', 'reboot']:
        return {
            'command': 'system_power',
            'params': {'mode': 'restart'},
            'confidence': 0.98,
            'method': 'direct_command'
        }
    
    if t in ['lock', 'lock screen', 'lock computer']:
        return {
            'command': 'system_power',
            'params': {'mode': 'lock'},
            'confidence': 0.98,
            'method': 'direct_command'
        }
    
    # Handle bare window commands (maximize, minimize)
    if t in ['maximize', 'maximise', 'max']:
        return {
            'command': 'windows_ui',
            'params': {'type': 'windows_ui', 'action': 'maximize_window'},
            'confidence': 0.95,
            'method': 'windows_ui'
        }
    
    if t in ['minimize', 'minimise', 'min']:
        return {
            'command': 'windows_ui',
            'params': {'type': 'windows_ui', 'action': 'minimize_window'},
            'confidence': 0.95,
            'method': 'windows_ui'
        }
    
    if t in ['restore', 'restore window']:
        return {
            'command': 'windows_ui',
            'params': {'type': 'windows_ui', 'action': 'restore_window'},
            'confidence': 0.95,
            'method': 'windows_ui'
        }
    
    # Handle "what windows are open" type questions and active apps queries
    if any(q in t for q in ['what windows', 'which windows', 'windows are open', 
                             'apps are open', 'what is open', 'what\'s open',
                             'what is running', 'what\'s running',
                             'active apps', 'active windows', 'my active apps',
                             'my active windows', 'running apps', 'open apps']):
        return {
            'command': 'windows_ui',
            'params': {'type': 'windows_ui', 'action': 'list_active'},
            'confidence': 0.95,
            'method': 'windows_ui'
        }
    
    if any(trigger in t for trigger in windows_ui_triggers):
        windows_ui_parsed = _parse_windows_ui_command(text)
        if windows_ui_parsed:
            return {
                'command': 'windows_ui',
                'params': windows_ui_parsed,
                'confidence': 0.95,
                'method': 'windows_ui'
            }
    
    # =========================================================================
    # WINDOW SNAP COMMANDS (must be before advanced_question patterns)
    # "snap window", "snap Chrome", "snap Chrome with VS Code"
    # =========================================================================
    snap_patterns = [
        # "snap [app] with [app2]" - side by side two specific apps
        (r'^snap\s+(.+?)\s+(?:with|and|beside|alongside)\s+(.+)$', 'snap_with'),
        # "snap window left/right/up/down" - snap current window to direction
        (r'^snap\s+(?:this\s+)?(?:the\s+)?window\s+(?:to\s+)?(left|right|up|down|top|bottom)$', 'snap_window_dir'),
        # "snap window" or "snap this window" (no direction - default to left)
        (r'^snap\s+(?:this\s+)?(?:the\s+)?window$', 'snap_window'),
        # "snap [app] left/right" - but NOT "snap window left"
        (r'^snap\s+(?!window\b)(.+?)\s+(?:to\s+)?(left|right|top|bottom|up|down)$', 'snap_app_dir'),
        # "snap [app]" (no direction - default to left) - but NOT "snap window"
        (r'^snap\s+(?!window\b)(?!left\b)(?!right\b)(?!top\b)(?!bottom\b)(?!up\b)(?!down\b)(?!to\s)(.+)$', 'snap_app'),
    ]
    
    for pattern, snap_type in snap_patterns:
        match = re.match(pattern, t, re.IGNORECASE)
        if match:
            if snap_type == 'snap_with':
                app1 = match.group(1).strip()
                app2 = match.group(2).strip()
                return {
                    'command': 'windows_ui',
                    'params': {
                        'type': 'windows_ui',
                        'action': 'snap_with',
                        'app1': app1,
                        'app2': app2
                    },
                    'confidence': 0.95,
                    'method': 'snap_apps'
                }
            elif snap_type == 'snap_window_dir':
                direction = match.group(1).strip()
                # Map up/down to top/bottom for consistency
                dir_map = {'up': 'top', 'down': 'bottom'}
                direction = dir_map.get(direction.lower(), direction.lower())
                return {
                    'command': 'windows_ui',
                    'params': {
                        'type': 'windows_ui',
                        'action': 'snap',
                        'direction': direction
                    },
                    'confidence': 0.95,
                    'method': 'snap_window'
                }
            elif snap_type == 'snap_window':
                return {
                    'command': 'windows_ui',
                    'params': {
                        'type': 'windows_ui',
                        'action': 'snap',
                        'direction': 'left'  # Default direction
                    },
                    'confidence': 0.95,
                    'method': 'snap_window'
                }
            elif snap_type == 'snap_app_dir':
                app_name = match.group(1).strip()
                direction = match.group(2).strip()
                return {
                    'command': 'windows_ui',
                    'params': {
                        'type': 'windows_ui',
                        'action': 'snap_app',
                        'app_name': app_name,
                        'direction': direction
                    },
                    'confidence': 0.95,
                    'method': 'snap_app'
                }
            elif snap_type == 'snap_app':
                app_name = match.group(1).strip()
                return {
                    'command': 'windows_ui',
                    'params': {
                        'type': 'windows_ui',
                        'action': 'snap_app',
                        'app_name': app_name,
                        'direction': 'left'  # Default direction
                    },
                    'confidence': 0.95,
                    'method': 'snap_app'
                }
    
    # =========================================================================
    # WINDOW CONTROL FOR SPECIFIC APPS (minimize/maximize/close [app])
    # Must be before advanced_question patterns to avoid "minimize vs code" → Gray code
    # =========================================================================
    window_control_patterns = [
        # Minimize app - British and American spellings
        (r'^(?:minimise|minimize)\s+(.+?)(?:\s+window)?$', 'minimize'),
        (r'^(?:min)\s+(.+)$', 'minimize'),
        # Maximize app
        (r'^(?:maximise|maximize)\s+(.+?)(?:\s+window)?$', 'maximize'),
        (r'^(?:max)\s+(.+)$', 'maximize'),
        # Close app
        (r'^close\s+(.+?)(?:\s+window)?$', 'close'),
        # Restore app
        (r'^restore\s+(.+?)(?:\s+window)?$', 'restore'),
    ]
    
    for pattern, action in window_control_patterns:
        match = re.match(pattern, t, re.IGNORECASE)
        if match:
            app_name = match.group(1).strip()
            # Skip if it's a generic "window" reference (handled by windows_ui_triggers)
            if app_name.lower() in ['window', 'this window', 'the window', 'this', 'that']:
                continue
            # Skip if it looks like a question word
            if app_name.lower() in ['what', 'why', 'how', 'when', 'where', 'which']:
                continue
            return {
                'command': 'windows_ui',
                'params': {
                    'type': 'windows_ui',
                    'action': f'{action}_app',
                    'app_name': app_name
                },
                'confidence': 0.95,
                'method': 'window_control'
            }
    
    # =========================================================================
    # CHECK INPUT CONTROL COMMANDS EARLY (scroll, mouse mode, click, etc.)
    # These are high-priority commands that should not be misinterpreted
    # =========================================================================
    
    # Handle "show numbers" for visual overlay (Voice Access style)
    if t in ['show numbers', 'show labels', 'numbers', 'labels']:
        return {
            'command': 'overlay',
            'params': {'action': 'show_numbers'},
            'confidence': 0.95,
            'method': 'overlay'
        }
    
    if t in ['hide numbers', 'hide labels', 'cancel numbers', 'cancel labels', 'cancel']:
        return {
            'command': 'overlay',
            'params': {'action': 'hide'},
            'confidence': 0.95,
            'method': 'overlay'
        }
    
    # =========================================================================
    # NATURAL LANGUAGE ELEMENT TARGETING (smart overlay)
    # "click the settings button", "click the red icon", "click on submit"
    # =========================================================================
    nl_click_patterns = [
        r'^(?:click|tap|press|select)\s+(?:the\s+|on\s+(?:the\s+)?)?(.+?)\s*(?:button|icon|link|option|menu|tab)?$',
        r'^(?:click|tap|press|select)\s+on\s+(.+)$',
        r'^(?:find\s+and\s+)?click\s+(.+)$',
    ]
    
    # Check for natural language click (not just a number)
    for pattern in nl_click_patterns:
        match = re.match(pattern, t, re.IGNORECASE)
        if match:
            target = match.group(1).strip()
            # If it's just a number, let regular input_control handle it
            if target.isdigit():
                break
            # If it's natural language like "settings", "save button", etc.
            if len(target) > 1 and not target.isdigit():
                return {
                    'command': 'smart_click',
                    'params': {'target': target, 'original_text': text},
                    'confidence': 0.85,
                    'method': 'smart_overlay'
                }
    
    input_control_triggers = [
        'scroll', 'click', 'double click', 'triple click', 'right click',
        'mouse grid', 'show grid', 'mouse mode', 'activate mouse', 'enable mouse',
        'deactivate mouse', 'disable mouse', 'move mouse', 'move cursor',
        'drag', 'press ', 'type ', 'copy', 'paste', 'cut', 'undo', 'redo',
        'select all', 'select word', 'select line', 'go to start', 'go to end',
    ]
    
    # Also check for directional commands (short form like "left 50 pixels")
    directional_pattern = re.match(r'^(up|down|left|right)(?:\s+\d+)?(?:\s*(?:pixels?|px))?$', t)
    
    if directional_pattern or any(trigger in t for trigger in input_control_triggers):
        input_parsed = _parse_input_command(text)
        if input_parsed.get('type') != 'unknown':
            return {
                'command': 'input_control',
                'params': input_parsed,
                'confidence': 0.95,
                'method': 'input_control'
            }
    
    # =========================================================================
    # EXPLICIT APP CONTROL CHECK - Check for specific app names BEFORE NLP
    # This ensures "open Chrome" launches Chrome app, not opens Google.com
    # =========================================================================
    browser_apps = ['chrome', 'google chrome', 'firefox', 'mozilla firefox', 
                    'edge', 'microsoft edge', 'brave', 'opera', 'safari', 'vivaldi']
    common_apps = browser_apps + ['notepad', 'calculator', 'calc', 'paint', 'word', 'excel',
                   'powerpoint', 'explorer', 'file explorer', 'files', 'settings',
                   'vscode', 'vs code', 'visual studio code', 'code', 'terminal',
                   'cmd', 'powershell', 'spotify', 'discord', 'slack', 'teams',
                   'skype', 'zoom', 'whatsapp', 'telegram', 'outlook', 'mail',
                   'task manager', 'control panel', 'store', 'microsoft store',
                   'vlc', 'media player', 'steam', 'epic games', 'blender', 'photoshop']
    
    open_app_match = re.match(r'^(?:open|launch|start|run)\s+(.+?)(?:\s+app(?:lication)?)?$', t, re.IGNORECASE)
    if open_app_match:
        app_name = open_app_match.group(1).strip().lower()
        # Check if app_name matches any known app
        for known_app in common_apps:
            if app_name == known_app or known_app in app_name or app_name in known_app:
                return {
                    'command': 'control_app',
                    'params': {'app': app_name, 'action': 'open'},
                    'confidence': 0.95,
                    'method': 'explicit_app_control'
                }
    
    close_app_match = re.match(r'^(?:close|quit|exit|stop|kill)\s+(.+?)(?:\s+app(?:lication)?)?$', t, re.IGNORECASE)
    if close_app_match:
        app_name = close_app_match.group(1).strip().lower()
        for known_app in common_apps:
            if app_name == known_app or known_app in app_name or app_name in known_app:
                return {
                    'command': 'control_app',
                    'params': {'app': app_name, 'action': 'close'},
                    'confidence': 0.95,
                    'method': 'explicit_app_control'
                }
    
    if NLP_AVAILABLE and parse_command_nlp is not None:
        nlp_result = parse_command_nlp(text, use_nlp=True)
        intent = nlp_result.get('type', 'unknown')
        confidence = nlp_result.get('confidence', 0.0)
        
        # Map NLP intents to command format
        intent_map = {
            'open_browser': 'open_browser',
            'time': 'get_time',
            'search': 'search',
            'play_music': 'media_control',
            'shutdown': 'system_power',
            'volume': 'control_volume',
            'brightness': 'control_brightness',
            'app_control': 'control_app',
            'window_control': 'control_window',
            'help': 'assistant_help',
            'input_control': 'input_control',
            'mouse': 'input_control',
            'keyboard': 'input_control',
            'screen_context': 'screen_context',
            'what_on_screen': 'screen_context',
            'read_screen': 'screen_context',
            'knowledge': 'knowledge',
            'define': 'knowledge',
            'explain': 'knowledge',
        }
        
        cmd = intent_map.get(intent, 'unknown')
        
        # Check if this is a knowledge query before falling through
        t_lower = text.lower().strip()
        knowledge_triggers = [
            'tell me about', 'tell about', 'who is', 'who was', 
            'what is', 'what are', 'define', 'explain', 'describe',
            'information about', 'info about', 'research'
        ]
        if any(t_lower.startswith(trigger) for trigger in knowledge_triggers):
            # Extract topic from the query
            topic = t_lower
            for trigger in knowledge_triggers:
                if topic.startswith(trigger):
                    topic = topic[len(trigger):].strip()
                    break
            return {
                'command': 'knowledge',
                'params': {'topic': topic, 'detail_level': 'brief'},
                'confidence': 0.85,
                'method': 'nlp_knowledge'
            }
        
        # Only allow search if user explicitly said "search"
        # This prevents random things from being searched
        if cmd == 'search':
            explicit_search = any(t_lower.startswith(p) for p in ['search ', 'search for ', 'google ', 'look up ', 'find me '])
            if not explicit_search:
                cmd = 'unknown'
        
        # If NLP didn't recognize intent well, try app control first, then basic parser
        if cmd == 'unknown' or confidence < 0.3:
            # Try app control parsing (minimize, maximize, switch, etc.)
            app_parsed = _parse_app_command(text)
            if app_parsed:
                return {
                    'command': 'app_control',
                    'params': app_parsed,
                    'confidence': 0.9,
                    'method': 'app_control'
                }
            # Fall back to basic parser
            result = basic_parse(text)
            result['method'] = 'basic'
            return result
        
        # Build params from NLP entities
        params = {}
        if 'query' in nlp_result:
            params['query'] = nlp_result['query']
        if 'app' in nlp_result:
            params['app'] = nlp_result['app']
            params['action'] = 'close' if 'close' in text.lower() else 'open'
        if 'level' in nlp_result:
            params['level'] = nlp_result['level']
        if 'action' in nlp_result:
            params['action'] = nlp_result['action']
        if 'window' in nlp_result:
            params['window'] = nlp_result['window']
        
        # Handle shutdown intent specially
        if intent == 'shutdown':
            if 'restart' in text.lower():
                params['mode'] = 'restart'
            elif 'sleep' in text.lower():
                params['mode'] = 'sleep'
            elif 'lock' in text.lower():
                params['mode'] = 'lock'
            else:
                params['mode'] = 'shutdown'
        
        return {
            'command': cmd,
            'params': params,
            'confidence': confidence,
            'method': 'nlp'
        }
    else:
        # Fall back to basic parser
        result = basic_parse(text)
        result['method'] = 'basic'
        
        # Check for app control commands FIRST (open, close, switch, go to apps)
        # This catches "go to vs code", "switch to chrome", etc.
        app_parsed = _parse_app_command(text)
        if app_parsed:
            return {
                'command': 'app_control',
                'params': app_parsed,
                'confidence': 0.9,
                'method': 'app_control'
            }
        
        # Check for input control commands (Voice Access style)
        if result.get('command') == 'unknown' or result.get('command') == 'search':
            input_parsed = _parse_input_command(text)
            if input_parsed.get('type') != 'unknown':
                return {
                    'command': 'input_control',
                    'params': input_parsed,
                    'confidence': 0.9,
                    'method': 'input_control'
                }
        
        return result


def execute_input_command(parsed: dict) -> str:
    """
    Execute voice-driven input control commands.
    Inspired by Microsoft Voice Access and Google Voice Access.
    """
    params = parsed.get('params', {})
    cmd_type = params.get('type', 'unknown')
    
    try:
        controller = _get_input_controller()
        
        if not controller.available:
            return "Input control is not available. Please install pyautogui."
        
        # =====================================================================
        # MOUSE COMMANDS
        # =====================================================================
        
        if cmd_type == 'mouse_click':
            button = params.get('button', 'left')
            clicks = params.get('clicks', 1)
            
            from core.input_control import MouseButton
            btn_map = {'left': MouseButton.LEFT, 'right': MouseButton.RIGHT, 'middle': MouseButton.MIDDLE}
            btn = btn_map.get(button, MouseButton.LEFT)
            
            if controller.mouse.click(btn, clicks):
                if clicks == 2:
                    return "Double clicked."
                elif clicks == 3:
                    return "Triple clicked to select."
                elif button == 'right':
                    return "Right clicked."
                return "Clicked."
            return "Failed to click."
        
        elif cmd_type == 'grid_click':
            cell = params.get('cell', 1)
            # Try visual overlay first
            overlay = _get_overlay_manager()
            if overlay and overlay.is_available:
                result = overlay.click(cell)
                if result.success:
                    return f"Clicked {cell}."
            # Fallback to non-visual grid
            if not controller.mouse.grid_active:
                controller.mouse.create_grid(3, 3)
            if controller.mouse.click_grid(cell):
                return f"Clicked cell {cell}."
            return f"Invalid grid cell: {cell}"
        
        elif cmd_type == 'mouse_grid':
            action = params.get('action', 'show')
            if action == 'show':
                # Try visual overlay first
                overlay = _get_overlay_manager()
                if overlay and overlay.is_available:
                    if overlay.show_grid(size=3):
                        return "Grid overlay active. Say a number 1-9 to click that area."
                # Fallback to non-visual grid
                cells = controller.mouse.create_grid(3, 3)
                return f"Mouse grid active. Say a number 1-9 to click that area."
            else:
                # Hide overlay and internal grid
                overlay = _get_overlay_manager()
                if overlay:
                    overlay.hide()
                controller.mouse.close_grid()
                return "Grid closed."
        
        elif cmd_type == 'mouse_mode':
            action = params.get('action', 'activate')
            if action == 'activate':
                # Enable mouse mode - show grid and prepare for mouse commands
                controller.mouse.create_grid(3, 3)
                return "Mouse mode activated. Say 'click', 'move mouse', or a number 1-9 to control. Say 'deactivate mouse mode' to exit."
            else:
                controller.mouse.close_grid()
                return "Mouse mode deactivated."
        
        elif cmd_type == 'mouse_move':
            if 'x' in params and 'y' in params:
                # Absolute movement
                x, y = params['x'], params['y']
                if controller.mouse.move_to(x, y):
                    return f"Mouse moved to {x}, {y}."
                return "Failed to move mouse."
            elif 'direction' in params:
                # Directional movement
                from core.input_control import Direction
                dir_map = {
                    'up': Direction.UP, 'down': Direction.DOWN,
                    'left': Direction.LEFT, 'right': Direction.RIGHT,
                    'up_left': Direction.UP_LEFT, 'up_right': Direction.UP_RIGHT,
                    'down_left': Direction.DOWN_LEFT, 'down_right': Direction.DOWN_RIGHT,
                }
                direction = dir_map.get(params['direction'], Direction.UP)
                distance = params.get('distance')
                if controller.mouse.move_direction(direction, distance):
                    return f"Mouse moved {params['direction']}."
                return "Failed to move mouse."
        
        elif cmd_type == 'scroll':
            direction = params.get('direction', 'down')
            amount = params.get('amount', 3)
            
            if direction == 'top':
                controller.mouse.scroll_to_top()
                return "Scrolled to top."
            elif direction == 'bottom':
                controller.mouse.scroll_to_bottom()
                return "Scrolled to bottom."
            elif direction == 'up':
                controller.mouse.scroll_up(amount)
                return "Scrolled up."
            else:
                controller.mouse.scroll_down(amount)
                return "Scrolled down."
        
        elif cmd_type == 'drag':
            x, y = params.get('x', 0), params.get('y', 0)
            if controller.mouse.drag_to(x, y):
                return f"Dragged to {x}, {y}."
            return "Failed to drag."
        
        # =====================================================================
        # KEYBOARD COMMANDS
        # =====================================================================
        
        elif cmd_type == 'type_text':
            text_to_type = params.get('text', '')
            if text_to_type:
                if controller.keyboard.type_unicode(text_to_type):
                    return f"Typed: {text_to_type[:30]}{'...' if len(text_to_type) > 30 else ''}"
            return "Nothing to type."
        
        elif cmd_type == 'press_key':
            key = params.get('key', '')
            if key and controller.keyboard.press_key(key):
                return f"Pressed {key}."
            return f"Failed to press {key}."
        
        elif cmd_type == 'hotkey':
            modifiers = params.get('modifiers', [])
            key = params.get('key', '')
            if modifiers and key:
                if controller.keyboard.hotkey(*modifiers, key):
                    combo = '+'.join(modifiers) + '+' + key
                    return f"Pressed {combo}."
            return "Failed to press hotkey."
        
        elif cmd_type == 'select':
            target = params.get('target', '')
            if target == 'word':
                controller.keyboard.select_word()
                return "Word selected."
            elif target == 'line':
                controller.keyboard.select_line()
                return "Line selected."
            elif target == 'to_start':
                controller.keyboard.select_to_start()
                return "Selected to start."
            elif target == 'to_end':
                controller.keyboard.select_to_end()
                return "Selected to end."
        
        elif cmd_type == 'navigate':
            target = params.get('target', '')
            if target == 'start':
                controller.keyboard.go_to_start()
                return "Moved to start."
            elif target == 'end':
                controller.keyboard.go_to_end()
                return "Moved to end."
            elif target == 'next_word':
                controller.keyboard.next_word()
                return "Next word."
            elif target == 'prev_word':
                controller.keyboard.prev_word()
                return "Previous word."
        
        elif cmd_type == 'window':
            action = params.get('action', '')
            if action == 'switch':
                controller.keyboard.switch_window()
                return "Switching windows."
            elif action == 'close':
                controller.keyboard.close_window()
                return "Closing window."
            elif action == 'minimize':
                controller.keyboard.minimize_window()
                return "Window minimized."
            elif action == 'maximize':
                controller.keyboard.maximize_window()
                return "Window maximized."
            elif action == 'snap_left':
                controller.keyboard.snap_left()
                return "Snapped left."
            elif action == 'snap_right':
                controller.keyboard.snap_right()
                return "Snapped right."
            elif action == 'show_desktop':
                controller.keyboard.show_desktop()
                return "Showing desktop."
            elif action == 'task_view':
                controller.keyboard.task_view()
                return "Opening task view."
            elif action == 'screenshot':
                controller.keyboard.screenshot()
                return "Screenshot tool opened."
        
        elif cmd_type == 'help':
            topic = params.get('topic', 'all')
            if topic == 'mouse':
                return """Mouse Commands:
• "click" / "double click" / "right click"
• "move mouse up/down/left/right [pixels]"
• "move mouse to X, Y"
• "scroll up/down"
• "show grid" / "mouse grid" - show clickable grid overlay
• "show numbers" - show numbered labels on screen elements
• "click [number]" - click grid cell or labeled element
• "hide numbers" / "cancel" - hide overlay
• "drag to X, Y"
"""
            elif topic == 'keyboard':
                return """Keyboard Commands:
• "type [text]" - type text
• "press [key]" - press a key (enter, tab, escape, etc.)
• "press control [key]" - keyboard shortcut
• "copy" / "paste" / "cut" / "undo" / "redo"
• "select all" / "select word" / "select line"
• "go to start" / "go to end"
"""
            else:
                return """Voice Input Commands:

Mouse:
• click, double click, right click
• move mouse [direction] [pixels]
• scroll up/down, show grid, show numbers

Keyboard:
• type [text], press [key]
• copy, paste, cut, undo, redo
• select all/word/line

Windows:
• switch/close/minimize/maximize window
• snap left/right, show desktop, screenshot
• show active apps, previous window, split screen

Visual Overlay:
• show numbers - label clickable elements
• show grid - 3x3 grid overlay
• click [number] - click labeled element
• cancel - hide overlay
"""
        
        return Vox.get_not_understood()
        
    except Exception as e:
        return Vox.get_error_message(str(e))


def execute_screen_command(parsed: dict) -> str:
    """
    Execute screen context commands - let Vox see and understand the screen.
    """
    params = parsed.get('params', {})
    action = params.get('action', 'describe')
    target = params.get('target')
    
    try:
        engine = _get_screen_engine()
        
        if not engine.ocr_available:
            return ("I can capture your screen, but I need Tesseract OCR to read it. "
                    "Please install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki")
        
        if action == 'describe':
            # Full screen analysis and description
            print("[Analyzing screen...]")
            description = engine.describe_screen()
            
            # Also show quick context summary
            context = engine.get_last_context()
            if context and context.keywords:
                print(f"  [Keywords: {', '.join(context.keywords[:5])}]")
            if context and context.suggested_actions:
                print(f"  [Suggestions: {', '.join(context.suggested_actions[:3])}]")
            
            return description
        
        elif action == 'click':
            if not target:
                return "What would you like me to click on?"
            
            print(f"[Looking for '{target}' on screen...]")
            if engine.click_on_text(target):
                return f"I found and clicked on '{target}'."
            else:
                return f"I couldn't find '{target}' on the screen. Try being more specific."
        
        elif action == 'find':
            if not target:
                return "What would you like me to find?"
            
            print(f"[Searching for '{target}' on screen...]")
            matches = engine.find_text_on_screen(target)
            
            if matches:
                if len(matches) == 1:
                    match = matches[0]
                    return f"Found '{target}' at position ({match.region.center[0]}, {match.region.center[1]})"
                else:
                    return f"Found '{target}' in {len(matches)} places on screen."
            else:
                return f"I couldn't find '{target}' on the screen."
        
        elif action == 'context':
            # Get quick context
            quick = engine.get_quick_context()
            parts = []
            
            if quick.get('app'):
                parts.append(f"App: {quick['app']}")
            if quick.get('title'):
                parts.append(f"Title: {quick['title']}")
            if quick.get('keywords'):
                parts.append(f"Topics: {', '.join(quick['keywords'])}")
            if quick.get('suggested_actions'):
                parts.append(f"You might want to: {', '.join(quick['suggested_actions'])}")
            
            return " | ".join(parts) if parts else "I couldn't analyze the screen."
        
        return engine.describe_screen()
        
    except Exception as e:
        return Vox.get_error_message(f"Screen analysis failed: {str(e)}")


def execute_screen_monitor_command(parsed: dict) -> str:
    """
    Execute screen monitor commands - start/stop continuous screen watching.
    """
    params = parsed.get('params', {})
    action = params.get('action', 'status')
    
    try:
        monitor = _get_screen_monitor()
        
        if action == 'start':
            if monitor.is_running:
                return "I'm already watching your screen."
            monitor.start()
            return "I'm now watching your screen. I'll notice when things change."
        
        elif action == 'stop':
            if not monitor._running:
                return "I'm not currently watching the screen."
            monitor.stop()
            return "I've stopped watching the screen."
        
        elif action == 'pause':
            monitor.pause()
            return "Screen watching paused."
        
        elif action == 'resume':
            monitor.resume()
            return "Screen watching resumed."
        
        elif action == 'summary':
            if not monitor.frames:
                return "I haven't captured any screen activity yet. Say 'start watching' first."
            
            summary = monitor.get_activity_summary(60)
            events = monitor.get_recent_events(3)
            
            result = summary
            if events:
                event_strs = [f"{e.event_type}: {e.description}" for e in events]
                result += f" | Recent: {', '.join(event_strs)}"
            
            return result
        
        elif action == 'status':
            if monitor.is_running:
                context = monitor.get_current_context()
                return f"Screen watching is active. {context}"
            return "Screen watching is not active."
        
        return "I'm not sure what to do with screen monitoring."
        
    except Exception as e:
        return Vox.get_error_message(f"Screen monitor error: {str(e)}")


def execute_app_command(parsed: dict) -> str:
    """
    Execute app control commands - launch, close, switch, snap applications.
    """
    action = parsed.get('action', '')
    app = parsed.get('app')
    
    try:
        controller = _get_app_controller()
        
        if action == 'open':
            success, msg = controller.open(app)
            if success:
                return Vox.get_confirmation_message() + f" {msg}"
            return msg
        
        elif action == 'open_url':
            url = parsed.get('url', '')
            success, msg = controller.open_url(url)
            if success:
                return f"Opening {url}."
            return msg
        
        elif action == 'close':
            success, msg = controller.close(app)
            if success:
                return msg
            return Vox.get_error_message(msg)
        
        elif action == 'switch':
            success, msg = controller.switch_to(app)
            if success:
                return msg
            # If window not found, try launching the app
            success2, msg2 = controller.open(app)
            if success2:
                return f"Launching {app}."
            return msg
        
        elif action == 'minimize':
            success, msg = controller.minimize(app)
            return msg
        
        elif action == 'maximize':
            success, msg = controller.maximize(app)
            return msg
        
        elif action == 'snap':
            position = parsed.get('position', 'left')
            success, msg = controller.snap(position, app)
            return msg
        
        elif action == 'show_desktop':
            success, msg = controller.show_desktop()
            return msg
        
        elif action == 'list_windows':
            windows = controller.list_windows()
            if windows:
                window_list = ', '.join(windows[:5])
                more = f' and {len(windows) - 5} more' if len(windows) > 5 else ''
                return f"Open windows: {window_list}{more}."
            return "No windows are open."
        
        elif action == 'search':
            query = parsed.get('query', '')
            apps = controller.search_apps(query) if query else []
            if apps:
                return f"Found apps: {', '.join(apps[:5])}"
            return "No matching apps found."
        
        elif action == 'drag':
            x = parsed.get('x', 0)
            y = parsed.get('y', 0)
            success, msg = controller.drag_window(x, y, app)
            return msg
        
        elif action == 'drag_by':
            dx = parsed.get('dx', 0)
            dy = parsed.get('dy', 0)
            success, msg = controller.drag_window_by(dx, dy, app)
            return msg
        
        return "I'm not sure how to do that with apps."
        
    except Exception as e:
        return Vox.get_error_message(f"App control failed: {str(e)}")


def execute_file_ops_command(params: dict) -> str:
    """
    Execute file/directory operations using shutil and os.
    Supports: copy, move, rename, delete, create_folder, list_folder, current_dir, folder_size.
    """
    import shutil
    import os
    from pathlib import Path
    
    action = params.get('action', 'unknown')
    source = params.get('source')
    dest = params.get('dest')
    
    # Expand user paths (~) and environment variables
    def expand_path(p):
        if not p:
            return None
        p = os.path.expanduser(p)
        p = os.path.expandvars(p)
        return os.path.abspath(p)
    
    source_path = expand_path(source) if source else None
    dest_path = expand_path(dest) if dest else None
    
    try:
        if action == 'copy':
            if not source_path:
                return "Please specify what to copy. Say 'copy <file/folder> to <destination>'."
            if not dest_path:
                return "Please specify where to copy. Say 'copy <file/folder> to <destination>'."
            if not os.path.exists(source_path):
                return f"Cannot find '{source}'. Please check the path."
            
            if os.path.isdir(source_path):
                shutil.copytree(source_path, dest_path)
                return f"Copied folder '{source}' to '{dest}'."
            else:
                shutil.copy2(source_path, dest_path)
                return f"Copied file '{source}' to '{dest}'."
        
        elif action == 'move':
            if not source_path:
                return "Please specify what to move. Say 'move <file/folder> to <destination>'."
            if not dest_path:
                return "Please specify where to move. Say 'move <file/folder> to <destination>'."
            if not os.path.exists(source_path):
                return f"Cannot find '{source}'. Please check the path."
            
            shutil.move(source_path, dest_path)
            return f"Moved '{source}' to '{dest}'."
        
        elif action == 'rename':
            if not source_path:
                return "Please specify what to rename. Say 'rename <file/folder> to <newname>'."
            if not dest_path:
                return "Please specify the new name. Say 'rename <file/folder> to <newname>'."
            if not os.path.exists(source_path):
                return f"Cannot find '{source}'. Please check the path."
            
            # If dest is just a name (not a path), keep in same directory
            if not os.path.dirname(dest):
                dest_path = os.path.join(os.path.dirname(source_path), dest)
            
            os.rename(source_path, dest_path)
            return f"Renamed '{source}' to '{dest}'."
        
        elif action == 'delete':
            if not source_path:
                return "Please specify what to delete. Say 'delete <file/folder>'."
            if not os.path.exists(source_path):
                return f"Cannot find '{source}'. Nothing to delete."
            
            if os.path.isdir(source_path):
                shutil.rmtree(source_path)
                return f"Deleted folder '{source}' and all its contents."
            else:
                os.remove(source_path)
                return f"Deleted file '{source}'."
        
        elif action == 'create_folder':
            if not source_path:
                return "Please specify the folder name. Say 'create folder <name>'."
            
            os.makedirs(source_path, exist_ok=True)
            return f"Created folder '{source}'."
        
        elif action == 'list_folder':
            target = source_path or os.getcwd()
            if not os.path.exists(target):
                return f"Cannot find folder '{source}'."
            if not os.path.isdir(target):
                return f"'{source}' is not a folder."
            
            items = os.listdir(target)
            if not items:
                return f"The folder '{source or 'current directory'}' is empty."
            
            # Separate files and folders
            folders = [f + '/' for f in items if os.path.isdir(os.path.join(target, f))]
            files = [f for f in items if os.path.isfile(os.path.join(target, f))]
            
            result_parts = []
            if folders:
                result_parts.append(f"Folders: {', '.join(folders[:10])}")
                if len(folders) > 10:
                    result_parts.append(f"... and {len(folders) - 10} more folders")
            if files:
                result_parts.append(f"Files: {', '.join(files[:10])}")
                if len(files) > 10:
                    result_parts.append(f"... and {len(files) - 10} more files")
            
            return '. '.join(result_parts)
        
        elif action == 'current_dir':
            cwd = os.getcwd()
            return f"Current directory: {cwd}"
        
        elif action == 'folder_size':
            target = source_path or os.getcwd()
            if not os.path.exists(target):
                return f"Cannot find '{source}'."
            
            if os.path.isfile(target):
                size = os.path.getsize(target)
            else:
                size = sum(
                    os.path.getsize(os.path.join(dirpath, f))
                    for dirpath, _, filenames in os.walk(target)
                    for f in filenames
                )
            
            # Format size
            if size < 1024:
                size_str = f"{size} bytes"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            elif size < 1024 * 1024 * 1024:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            else:
                size_str = f"{size / (1024 * 1024 * 1024):.2f} GB"
            
            return f"Size of '{source or 'current directory'}': {size_str}"
        
        else:
            return f"I don't know how to perform that file operation. Try 'copy', 'move', 'rename', 'delete', 'create folder', 'list folder', or 'current directory'."
    
    except PermissionError:
        return f"Permission denied. I can't access '{source}'."
    except FileNotFoundError:
        return f"File or folder not found: '{source}'."
    except FileExistsError:
        return f"'{dest}' already exists. Please choose a different name."
    except Exception as e:
        return f"File operation failed: {str(e)}"


def execute_command(parsed):
    """Execute the parsed command and return response."""
    cmd = parsed.get('command', 'unknown')
    params = parsed.get('params', {})
    
    # Handle conversational responses
    if cmd == 'conversation':
        conv_type = params.get('type', '')
        user_name = get_user_name() or "friend"
        if conv_type == 'greeting':
            import random
            responses = [
                f"I'm doing great, {user_name}! Ready to help you.",
                f"All systems running smoothly, {user_name}. What can I do for you?",
                f"I'm excellent, thank you for asking! How can I assist you?",
                f"Feeling energized and ready to help, {user_name}!",
            ]
            return random.choice(responses)
        elif conv_type == 'thanks':
            import random
            responses = [
                f"You're welcome, {user_name}!",
                "Happy to help!",
                "Anytime!",
                f"My pleasure, {user_name}.",
                "Glad I could assist!",
            ]
            return random.choice(responses)
        elif conv_type == 'goodbye':
            import random
            responses = [
                f"Goodbye, {user_name}! I'll be here when you need me.",
                f"See you later, {user_name}!",
                "Take care! Just say 'Hey Vox' when you're back.",
            ]
            return random.choice(responses)
        elif conv_type == 'identity':
            import random
            responses = [
                f"I'm VoxMind, your personal voice assistant. Nice to meet you, {user_name}!",
                f"My name is VoxMind, but you can call me Vox. I'm here to help you, {user_name}.",
                f"I'm VoxMind - your intelligent voice-controlled assistant. How can I help you today?",
                f"VoxMind at your service, {user_name}! I'm your AI assistant for voice control and information.",
            ]
            return random.choice(responses)
        return Vox.get_acknowledgment()
    
    # Handle advanced questions (why, how, which, when, if, is it/there)
    if cmd == 'advanced_question':
        question = params.get('question', '')
        topic = params.get('topic', '')
        question_type = params.get('question_type', 'what')
        detailed = params.get('detailed', False)
        
        if question:
            import asyncio
            try:
                # Create new event loop for this request
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(_ask_advanced_question(question, detailed=detailed))
                finally:
                    # Clean up: run pending callbacks, then close
                    try:
                        # Give pending tasks a chance to clean up
                        loop.run_until_complete(asyncio.sleep(0.1))
                    except Exception:
                        pass
                    loop.close()
                
                if result and len(result) > 10:
                    # For speech, potentially truncate but keep more for elaborate answers
                    max_speech_length = 800 if detailed else 500
                    if len(result) > max_speech_length:
                        spoken = result[:max_speech_length] + "... Would you like me to continue with more details?"
                    else:
                        spoken = result
                    return spoken
                else:
                    # Fallback to basic knowledge query
                    return f"I couldn't find a comprehensive answer. Let me try a simpler search for '{topic}'."
            except Exception as e:
                return f"I had trouble researching that question. {e}"
        return "What would you like to know?"
    
    # Handle math problems
    if cmd == 'math':
        query = params.get('query', '')
        if query:
            try:
                from core.math_solver import solve_math
                result = solve_math(query)
                if result.success:
                    # Format response for speech
                    response = f"The answer is: {result.result_text}."
                    if result.explanation:
                        response += f" {result.explanation}"
                    return response
                else:
                    return f"I couldn't solve that math problem. {result.error}"
            except ImportError:
                return "Math solver is not available. Try 'open math blackboard' for the visual calculator."
            except Exception as e:
                return f"Error solving math: {e}"
        return "What math problem would you like me to solve?"
    
    # Open math blackboard (native app)
    if cmd == 'open_blackboard':
        try:
            import subprocess
            import threading
            
            def start_math_app():
                subprocess.Popen(
                    [sys.executable, 'run_math_app.py'],
                    cwd=ROOT,
                    creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
                )
            
            threading.Thread(target=start_math_app, daemon=True).start()
            return "Opening the Mathematics Blackboard app. You can solve complex equations with step-by-step solutions there!"
        except Exception as e:
            return f"Couldn't open the blackboard: {e}"
    
    # Handle knowledge queries
    if cmd == 'knowledge':
        topic = params.get('topic', '')
        detail_level = params.get('detail_level', 'brief')
        if topic:
            import asyncio
            try:
                # Run async knowledge query
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(_ask_knowledge(topic, detail_level))
                finally:
                    loop.close()
                
                if result and len(result) > 10:
                    # Truncate for speech if too long
                    if len(result) > 500:
                        spoken = result[:500] + "... I have more details if you'd like."
                    else:
                        spoken = result
                    return spoken
                else:
                    return f"I couldn't find detailed information about {topic}. Try searching online?"
            except Exception as e:
                return f"I had trouble researching {topic}. Would you like me to search online instead?"
        return "What would you like to know about?"
    
    if cmd == 'change_name':
        new_name = params.get('name', '')
        if new_name:
            old_name = get_user_name() or "friend"
            set_user_name(new_name)
            return f"Of course! I'll call you {new_name} from now on. It's a pleasure, {new_name}."
        return "What would you like me to call you?"
    
    elif cmd == 'open_browser':
        browser = params.get('browser')
        webbrowser.open('https://www.google.com')
        return Vox.get_response('open_browser')
    
    elif cmd == 'search':
        query = params.get('query', '')
        if query:
            webbrowser.open(f'https://www.google.com/search?q={query}')
            return Vox.get_response('search', query=query)
        return "What would you like me to search for?"
    
    elif cmd == 'get_time':
        now = datetime.now()
        time_str = now.strftime('%I:%M %p')
        date_str = now.strftime('%A, %B %d')
        return Vox.get_response('time', time=time_str, date=date_str)
    
    elif cmd == 'control_volume':
        action = params.get('action')
        level = params.get('level')
        
        if not VOLUME_CONTROL_AVAILABLE:
            return Vox.get_error_message("Volume control is not available")
        
        if action == 'mute':
            volume_mute()
            return Vox.get_response('volume_mute')
        elif action == 'unmute':
            volume_unmute()
            return Vox.get_response('volume_unmute')
        elif action == 'up':
            volume_up(10)
            return Vox.get_response('volume_up')
        elif action == 'down':
            volume_down(10)
            return Vox.get_response('volume_down')
        elif action == 'set' and level is not None:
            volume_set(level)
            return f"Volume set to {level}%."
        return Vox.get_acknowledgment(quick=True)
    
    elif cmd == 'control_brightness':
        sbc = _get_brightness_control()
        action = params.get('action')
        level = params.get('level')
        
        try:
            current = sbc.get_brightness()[0]  # Get first monitor
            
            if action == 'up':
                new_level = min(100, current + 10)
                sbc.set_brightness(new_level)
                return f"{Vox.get_response('brightness_up')} Now at {new_level}%."
            elif action == 'down':
                new_level = max(0, current - 10)
                sbc.set_brightness(new_level)
                return f"{Vox.get_response('brightness_down')} Now at {new_level}%."
            elif action == 'set' and level is not None:
                sbc.set_brightness(level)
                return f"Brightness set to {level}%."
            else:
                return f"Current brightness is at {current}%."
        except Exception as e:
            return Vox.get_error_message(str(e))
    
    elif cmd == 'control_app':
        app = params.get('app', '').lower()
        action = params.get('action', 'open')
        
        # Map common app names to executable commands
        # Office apps use Start Menu search for reliability
        app_map = {
            'notepad': 'notepad',
            'calculator': 'calc',
            'calc': 'calc',
            'paint': 'mspaint',
            # Microsoft Office - use start command with app name for Start Menu search
            'word': 'START_MENU:Word',
            'microsoft word': 'START_MENU:Word',
            'excel': 'START_MENU:Excel',
            'microsoft excel': 'START_MENU:Excel',
            'powerpoint': 'START_MENU:PowerPoint',
            'microsoft powerpoint': 'START_MENU:PowerPoint',
            'onenote': 'START_MENU:OneNote',
            'microsoft onenote': 'START_MENU:OneNote',
            'access': 'START_MENU:Access',
            'microsoft access': 'START_MENU:Access',
            'publisher': 'START_MENU:Publisher',
            'microsoft publisher': 'START_MENU:Publisher',
            # Browsers
            'chrome': 'start chrome',
            'google chrome': 'start chrome',
            'firefox': 'start firefox',
            'mozilla firefox': 'start firefox',
            'edge': 'start msedge',
            'microsoft edge': 'start msedge',
            'brave': 'start brave',
            'opera': 'start opera',
            'vivaldi': 'start vivaldi',
            # System utilities
            'explorer': 'explorer',
            'files': 'explorer',
            'file explorer': 'explorer',
            'settings': 'start ms-settings:',
            'store': 'start ms-windows-store:',
            'microsoft store': 'start ms-windows-store:',
            'whatsapp': 'start "" "shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App"',
            'spotify': 'start spotify:',
            'vscode': 'code',
            'vs code': 'code',
            'visual studio code': 'code',
            'code': 'code',
            'terminal': 'wt',
            'windows terminal': 'wt',
            'cmd': 'cmd',
            'command prompt': 'cmd',
            'powershell': 'powershell',
            'task manager': 'taskmgr',
            'control panel': 'control',
            'discord': 'start discord:',
            'slack': 'start slack:',
            'zoom': 'start zoommtg:',
            'teams': 'start msteams:',
            'microsoft teams': 'start msteams:',
            'outlook': 'START_MENU:Outlook',
            'microsoft outlook': 'START_MENU:Outlook',
            'mail': 'start outlookmail:',
            'vlc': 'start vlc:',
            'steam': 'start steam:',
            'obs': 'obs64',
            'obs studio': 'obs64',
            # Adobe apps
            'photoshop': 'START_MENU:Photoshop',
            'adobe photoshop': 'START_MENU:Photoshop',
            'illustrator': 'START_MENU:Illustrator',
            'adobe illustrator': 'START_MENU:Illustrator',
            'premiere': 'START_MENU:Premiere',
            'adobe premiere': 'START_MENU:Premiere',
        }
        
        # Try to find app in map
        executable = app_map.get(app)
        if not executable:
            # Try partial match
            for key, val in app_map.items():
                if key in app or app in key:
                    executable = val
                    break
        
        # If not in static map, try app discovery
        if not executable:
            try:
                from core.app_discovery import find_app, discover_all_apps
                discovered = find_app(app)
                if discovered:
                    if discovered.is_uwp and discovered.app_id:
                        executable = f'start "" "shell:AppsFolder\\{discovered.app_id}!App"'
                    elif discovered.executable:
                        executable = f'start "" "{discovered.executable}"'
                    elif discovered.app_id:
                        executable = f'start "" "{discovered.app_id}"'
            except ImportError:
                pass
        
        if not executable:
            # Fallback: Use Start Menu search for unknown apps
            executable = f'START_MENU:{app}'
        
        if action == 'open':
            try:
                # Handle START_MENU: prefix - uses Start Menu search (most reliable for Office, Adobe, etc.)
                if executable.startswith('START_MENU:'):
                    search_term = executable[11:]  # Remove 'START_MENU:' prefix
                    _launch_via_start_menu(search_term)
                elif executable.startswith('start '):
                    os.system(executable)
                else:
                    subprocess.Popen(executable, shell=True)
                return Vox.get_response('app_open', app=app.title())
            except Exception as e:
                return Vox.get_error_message(f"Could not open {app}")
        elif action == 'close':
            # Handle special cases
            close_map = {'edge': 'msedge', 'chrome': 'chrome', 'firefox': 'firefox'}
            exe_name = close_map.get(app, app)
            os.system(f'taskkill /f /im {exe_name}.exe 2>nul')
            return Vox.get_response('app_close', app=app.title())
    
    elif cmd == 'control_window':
        gw = _get_window_control()
        action = params.get('action', 'minimize')
        window_name = params.get('window', '')
        
        if action == 'show_desktop':
            # Minimize all windows
            try:
                for win in gw.getAllWindows():
                    if win.title and win.visible:
                        try:
                            win.minimize()
                        except Exception:
                            pass  # Skip windows that can't be minimized
                return "Clearing the desktop for you."
            except Exception as e:
                return Vox.get_error_message(str(e))
        
        if not window_name:
            return "Which window would you like me to manage?"
        
        # Find matching windows
        try:
            windows = gw.getWindowsWithTitle(window_name)
            if not windows:
                # Try case-insensitive partial match
                all_windows = gw.getAllWindows()
                windows = [w for w in all_windows if window_name.lower() in w.title.lower()]
            
            if not windows:
                return f"I couldn't find a window matching '{window_name}'."
            
            win = windows[0]  # Get first matching window
            win_title = win.title[:30] + '...' if len(win.title) > 30 else win.title
            
            if action == 'minimize':
                win.minimize()
                return Vox.get_response('window_minimize', window=win_title)
            elif action == 'maximize':
                win.maximize()
                return Vox.get_response('window_maximize', window=win_title)
            elif action == 'restore':
                win.restore()
                return f"{win_title} restored."
            else:
                return Vox.get_not_understood()
        except Exception as e:
            return Vox.get_error_message(str(e))
    
    elif cmd == 'system_power':
        mode = params.get('mode')
        if mode == 'shutdown':
            return Vox.get_shutdown_message()
        elif mode == 'restart':
            return "Restarting the system. See you shortly."
        elif mode == 'sleep':
            os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')
            return Vox.get_response('system_sleep')
        elif mode == 'lock':
            os.system('rundll32.exe user32.dll,LockWorkStation')
            return Vox.get_response('system_lock')
    
    elif cmd == 'media_control':
        action = params.get('action')
        return f"Media {action}. {Vox.get_acknowledgment(quick=True)}"
    
    elif cmd == 'assistant_help':
        intro = Vox.get_response('help')
        print(f"\n{intro}")
        print("\n+--------------------------------------+")
        print("|       VOXMIND CAPABILITIES           |")
        print("+--------------------------------------+")
        print("|  Browser: 'open browser'             |")
        print("|  Search: 'search for [topic]'        |")
        print("|  Time: 'what time is it'             |")
        print("|  Volume: 'volume up/down/mute'       |")
        print("|  Brightness: 'brighter/dimmer'       |")
        print("|  Apps: 'open/close [app]'            |")
        print("|  Windows: 'minimize/maximize'        |")
        print("|  System: 'sleep/lock/restart'        |")
        print("+--------------------------------------+")
        print("|     VOICE ACCESS (Mouse/Keyboard)    |")
        print("+--------------------------------------+")
        print("|  Mouse: 'click', 'double click'      |")
        print("|  Move: 'move mouse up/down/left'     |")
        print("|  Grid: 'mouse grid', 'click 5'       |")
        print("|  Scroll: 'scroll up/down'            |")
        print("|  Type: 'type hello world'            |")
        print("|  Keys: 'press enter', 'press ctrl c' |")
        print("|  Edit: 'copy', 'paste', 'undo'       |")
        print("|  Windows: 'switch window', 'snap'    |")
        print("+--------------------------------------+")
        print("|     SMART OVERLAY (Visual Control)   |")
        print("+--------------------------------------+")
        print("|  'show numbers' - label elements     |")
        print("|  'click 5' - click numbered item     |")
        print("|  'click the settings button'         |")
        print("|  'click the save icon'               |")
        print("|  'cancel' - hide overlay             |")
        print("+--------------------------------------+")
        print("|     SCREEN SHARING (Visual AI)       |")
        print("+--------------------------------------+")
        print("|  'what's on my screen'               |")
        print("|  'describe the screen'               |")
        print("|  'what am I looking at'              |")
        print("|  'find [text] on screen'             |")
        print("+--------------------------------------+")
        print("|     INTROSPECTION (Self-Awareness)   |")
        print("+--------------------------------------+")
        print("|  'can you open apps?'                |")
        print("|  'how are you doing?'                |")
        print("|  'status report'                     |")
        print("+--------------------------------------+")
        print("|     VOICE PERSONAS                   |")
        print("+--------------------------------------+")
        print("|  'voice jarvis' - tactical AI        |")
        print("|  'voice friday' - casual assistant   |")
        print("|  'voice sofia' - creative AI         |")
        print("|  'list voices' - see all options     |")
        print("+--------------------------------------+")
        print("|     BACKEND (Diagnostics)            |")
        print("+--------------------------------------+")
        print("|  'health check' - system health      |")
        print("|  'telemetry' - usage statistics      |")
        print("|  'last command' - history            |")
        print("+--------------------------------------+")
        print("  Say 'Hey Vox' to wake me up!\n")
        return intro
    
    elif cmd == 'navigate':
        action = params.get('action')
        return f"Navigation {action} received"
    
    elif cmd == 'scroll':
        direction = params.get('direction')
        return f"Scrolling {direction}"
    
    elif cmd == 'voice_model':
        # Handle voice model/persona selection
        action = params.get('action', 'list')
        voice_name = params.get('voice', '')
        
        if action == 'list':
            voices = _list_available_voices()
            if voices:
                current = _get_current_voice()
                current_name = current['name'] if current else 'Unknown'
                voice_list = ", ".join([v['name'] for v in voices])
                return f"Available voices: {voice_list}. Currently using {current_name}."
            return "Voice models are not available."
        
        elif action == 'set' and voice_name:
            if _set_voice(voice_name):
                voice_info = _get_current_voice()
                greeting = _voice_greet()
                return f"Switched to {voice_info['name']}. {greeting}"
            else:
                return f"I don't know a voice called {voice_name}. Try Jarvis, Vision, Edith, Elisa, Sofia, or Friday."
        
        return "Say 'voice Jarvis' or 'switch to Friday' to change my voice."
    
    elif cmd == 'input_control':
        # Handle voice-driven mouse/keyboard automation
        return execute_input_command(parsed)
    
    elif cmd == 'overlay':
        # Handle visual overlays (numbers, grid)
        action = params.get('action', '')
        overlay = _get_overlay_manager()
        
        if not overlay or not overlay.is_available:
            return "Visual overlay is not available. Try 'mouse grid' instead."
        
        if action == 'show_numbers':
            if overlay.show_numbers():
                return "Showing numbered labels. Say a number to click, or 'cancel' to hide."
            return "Could not show number labels."
        elif action == 'show_grid':
            size = params.get('size', 3)
            if overlay.show_grid(size=size):
                return f"Grid overlay active. Say 1-{size*size} to click."
            return "Could not show grid."
        elif action == 'hide':
            overlay.hide()
            return "Overlay hidden."
        elif action == 'click':
            number = params.get('number', 1)
            result = overlay.click(number)
            if result.success:
                return f"Clicked {number}."
            return f"Could not click {number}."
        return "Unknown overlay action."
    
    elif cmd == 'screen_context':
        # Handle screen sharing / visual understanding
        return execute_screen_command(parsed)
    
    elif cmd == 'screen_monitor':
        # Handle continuous screen watching
        return execute_screen_monitor_command(parsed)
    
    elif cmd == 'app_control':
        # Handle app launching, closing, switching
        return execute_app_command(parsed.get('params', {}))
    
    elif cmd == 'windows_ui':
        # Handle Windows UI commands (taskbar, start menu, etc.)
        params = parsed.get('params', {})
        success, message = _execute_windows_ui_command(params)
        if success:
            return message
        return f"Couldn't complete that action: {message}"
    
    elif cmd == 'file_ops':
        # Handle file/directory operations (shutil-style)
        return execute_file_ops_command(parsed.get('params', {}))
    
    elif cmd == 'daemon':
        # Start VoxMind as a background daemon
        import subprocess
        import sys
        try:
            # Launch the daemon in a new process
            subprocess.Popen(
                [sys.executable, 'run_daemon.py'],
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
            )
            return "Starting VoxMind daemon. It will run in the background with Win+Shift+V hotkey support."
        except Exception as e:
            return f"Could not start daemon: {e}"
    
    elif cmd == 'smart_click':
        # Natural language element targeting using smart overlay
        target = params.get('target', '')
        smart_overlay = _get_smart_overlay()
        
        if smart_overlay:
            try:
                # Show overlay and try to click the target by description
                if smart_overlay._overlay and not smart_overlay._overlay.is_visible:
                    smart_overlay.show()
                
                result = smart_overlay.click(target)
                
                if result.success:
                    smart_overlay.hide()
                    return f"Clicked {result.element_name or target}."
                elif result.alternatives:
                    # Multiple matches found
                    return f"Found multiple matches. Try being more specific, or say a number: {result.alternatives[:5]}"
                else:
                    return f"I couldn't find '{target}' on the screen. Try 'show numbers' to see what I can click."
            except Exception as e:
                return f"Smart click failed: {e}. Try 'show numbers' for manual selection."
        else:
            # Fallback: use screen context to find and click text
            try:
                screen_engine = _get_screen_engine()
                if screen_engine:
                    # Use OCR to find text on screen
                    screen_text = screen_engine.read_screen()
                    if target.lower() in screen_text.lower():
                        # Found text, but can't click without coordinates
                        return f"I found '{target}' on the screen but couldn't click it. Try 'show numbers' to select elements."
                return f"I couldn't find '{target}' on the screen."
            except Exception as e:
                return f"Click failed: {e}"
    
    elif cmd == 'introspection':
        # Self-awareness and introspection commands
        intro_type = params.get('type', '')
        self_aware = _get_self_awareness()
        
        if intro_type == 'can_do':
            task = params.get('task', '')
            if self_aware:
                try:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(
                            self_aware.process_with_awareness(f"Can you {task}?")
                        )
                        return result.get('response', f"I'm not sure if I can {task}.")
                    finally:
                        loop.close()
                except Exception as e:
                    # Fallback response
                    pass
            
            # Simple fallback for common tasks
            known_tasks = {
                'open apps': True, 'open applications': True, 'launch apps': True,
                'close apps': True, 'search': True, 'search the web': True,
                'control volume': True, 'change volume': True, 'mute': True,
                'take screenshots': True, 'screenshot': True,
                'type text': True, 'type': True, 'enter text': True,
                'click': True, 'click buttons': True, 'press keys': True,
                'scroll': True, 'scroll pages': True,
                'read the screen': True, 'see the screen': True,
                'answer questions': True, 'help me': True,
                'fly': False, 'make coffee': False, 'cook': False,
                'feel emotions': False, 'feel': False, 'love': False,
                'be conscious': False, 'think for yourself': False,
            }
            task_lower = task.lower()
            for known, can_do in known_tasks.items():
                if known in task_lower:
                    if can_do:
                        return f"Yes, I can {task}! Just ask me to do it."
                    else:
                        return f"No, I can't {task}. I'm a digital assistant without physical capabilities or consciousness."
            
            return f"I'm not sure if I can {task}, but I'm happy to try! Just ask."
        
        elif intro_type == 'status':
            if self_aware:
                try:
                    report = self_aware.get_self_report()
                    # Return a summarized spoken version
                    print(report)  # Show full report in terminal
                    return "I'm running well! All systems are operational. I've printed a detailed status report to the console."
                except Exception:
                    pass
            
            user_name = get_user_name() or "friend"
            import random
            responses = [
                f"I'm doing great, {user_name}! Ready to help whenever you need me.",
                f"All systems running smoothly, {user_name}. How can I help?",
                f"I'm feeling energized and ready to assist, {user_name}!",
                f"Operating at peak performance, {user_name}. What can I do for you?",
            ]
            return random.choice(responses)
        
        return "I'm here and ready to help!"
    
    elif cmd == 'backend_health':
        # Show backend health status
        try:
            health = get_backend_health()
            status = health.get('status', 'unknown')
            checks = health.get('checks', {})
            
            print("\n" + "=" * 40)
            print("     BACKEND HEALTH CHECK")
            print("=" * 40)
            for name, check_status in checks.items():
                icon = "✅" if check_status.get('healthy', False) else "❌"
                print(f"  {icon} {name}: {check_status.get('message', 'unknown')}")
            print("=" * 40 + "\n")
            
            if status == 'healthy':
                return "All backend systems are healthy and operational."
            elif status == 'degraded':
                return "Backend is operational but some systems are degraded. Check the console for details."
            else:
                return f"Backend status: {status}. Some issues detected."
        except Exception as e:
            return f"Could not check backend health: {e}"
    
    elif cmd == 'backend_telemetry':
        # Show telemetry stats
        try:
            telemetry = get_backend_telemetry()
            
            print("\n" + "=" * 40)
            print("     BACKEND TELEMETRY")
            print("=" * 40)
            print(f"  Total Requests: {telemetry.get('total_requests', 0)}")
            print(f"  Success Rate: {telemetry.get('success_rate', 0):.1%}")
            print(f"  Avg Latency: {telemetry.get('avg_latency_ms', 0):.0f}ms")
            print(f"  Active Requests: {telemetry.get('active_requests', 0)}")
            
            cmd_counts = telemetry.get('command_counts', {})
            if cmd_counts:
                print("\n  Top Commands:")
                sorted_cmds = sorted(cmd_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                for cmd_name, count in sorted_cmds:
                    print(f"    • {cmd_name}: {count}")
            
            print("=" * 40 + "\n")
            
            return f"Processed {telemetry.get('total_requests', 0)} requests with {telemetry.get('success_rate', 0):.0%} success rate."
        except Exception as e:
            return f"Could not get telemetry: {e}"
    
    elif cmd == 'command_history':
        # Show last command or undo
        action = params.get('action', 'last')
        try:
            result = undo_last_command()
            return result
        except Exception as e:
            return f"Could not access command history: {e}"
    
    # Last resort: if command is unknown, try treating it as a knowledge query
    # This handles cases like "equation of motion" without explicit "what is"
    elif cmd == 'unknown':
        raw_text = parsed.get('raw', '') or parsed.get('params', {}).get('query', '')
        if raw_text and len(raw_text) > 3:
            # Check if it looks like a topic (not a command word)
            command_words = ['open', 'close', 'click', 'press', 'type', 'scroll', 
                           'move', 'volume', 'brightness', 'minimize', 'maximize']
            if not any(raw_text.lower().startswith(cw) for cw in command_words):
                import asyncio
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(_ask_knowledge(raw_text, 'brief'))
                    finally:
                        loop.close()
                    
                    if result and len(result) > 20 and 'couldn\'t find' not in result.lower():
                        return result
                except Exception:
                    pass
        return Vox.get_not_understood()
    
    return Vox.get_not_understood()

# Initialize backend app after core command handlers are defined
backend_app = BackendApp(
    parser=parse_command,
    executor=execute_command,
    nle_engine_provider=_get_nle_engine,
    # Enable all production features
    enable_rate_limiting=True,
    enable_circuit_breaker=True,
    enable_timeout=True,
    enable_queue=False,  # Keep sync for voice interaction
    enable_history=True,
    default_timeout=30.0,
    rate_limit_capacity=120,  # 120 commands per minute max
    rate_limit_rate=2.0,      # Refill 2 tokens per second
)

def get_backend_health():
    """Get backend health status."""
    return backend_app.get_health()

def get_backend_telemetry():
    """Get backend telemetry snapshot."""
    return backend_app.telemetry_snapshot()

def undo_last_command():
    """Undo the last command if possible."""
    if backend_app.history:
        last_cmd = backend_app.history.get_last()
        if last_cmd:
            return f"Last command was: {last_cmd.raw_text} -> {last_cmd.response}"
    return "No command history available."

def first_run_setup(simulate=False, no_tts=False):
    """First run setup - ask for user's name."""
    print("\n" + "=" * 50)
    print("     Welcome to V O X M I N D")
    print("     Your Personal AI Assistant")
    print("=" * 50)
    
    intro = "Hello! I'm VoxMind, your personal assistant. Before we begin, what should I call you?"
    print(f"\n{intro}\n")
    
    if not no_tts:
        try:
            speak_text(intro)
        except Exception as e:
            print(f"[TTS warning]: {e}")
    
    # Get user's name
    try:
        if simulate:
            name = input("Your name: ").strip()
        else:
            # Try to listen for the name
            print("[Listening for your name...]")
            try:
                name = listen_for_command(timeout=10.0, phrase_time_limit=5.0)
                if name:
                    name = name.strip().title()
            except RuntimeError as e:
                print(f"[Speech recognition error]: {e}")
                name = None
            
            if not name:
                print("I didn't catch that. Please type your name:")
                name = input("Your name: ").strip()
    except EOFError:
        name = "Boss"
    
    if not name:
        name = "Boss"
    
    # Save the name
    set_user_name(name)
    
    # Confirm
    confirm_msg = f"Wonderful! I'll call you {name}. It's a pleasure to meet you, {name}. Let's get started!"
    print(f"\n{confirm_msg}\n")
    
    if not no_tts:
        try:
            speak_text(confirm_msg)
        except Exception as e:
            print(f"[TTS warning]: {e}")
    
    sleep(1)

def run_loop(simulate=False, no_tts=False, skip_wake=False):
    # Check for first run
    if is_first_run():
        first_run_setup(simulate, no_tts)
    
    # Initialize performance analytics
    analytics = _get_analytics()
    analytics.start_session()
    
    user_name = get_user_name() or "friend"
    startup_msg = Vox.get_startup_message()
    
    print("\n" + "=" * 50)
    print("           V O X M I N D")
    print("       Your Personal Assistant")
    print("=" * 50)
    print(f"\n{startup_msg}\n")
    print(">> Say 'Hey Vox' to wake me up")
    print(">> Say 'help' to see what I can do")
    print(">> Say 'performance' to see stats")
    print(">> Say 'open interface' for web UI 🌐")
    print(">> Say 'show numbers' for clickable labels")
    print(">> Say 'show grid' for mouse grid overlay")
    print(">> Say 'shutdown' to exit")
    print("=" * 50 + "\n")
    
    if not no_tts:
        try:
            speak_text(startup_msg)
        except Exception as e:
            print(f"[TTS warning]: {e}")
    
    active = False
    
    while True:
        try:
            if simulate:
                if not active:
                    try:
                        input("Press Enter to simulate 'Hey Vox'...")
                    except EOFError:
                        break
                    active = True
                    analytics.record_wake_word(True)
                    listening_msg = Vox.get_listening_message()
                    print(f"\n* {listening_msg}\n")
                try:
                    cmd_text = input("You: ").strip()
                except EOFError:
                    break
            else:
                if not active:
                    print("[Waiting for 'Hey Vox'...]")
                    wake_detected = listen_for_wake_word()
                    analytics.record_wake_word(wake_detected)
                    if wake_detected:
                        active = True
                        listening_msg = Vox.get_listening_message()
                        print(f"\n* {listening_msg}\n")
                        if not no_tts:
                            try:
                                speak_text(listening_msg)
                            except Exception as e:
                                print(f"[TTS warning]: {e}")
                    continue
                
                print("[Listening...]")
                try:
                    cmd_text = listen_for_command(
                        timeout=5.0,
                        phrase_time_limit=8.0,
                        adjust_for_ambient=True,
                        ambient_duration=0.5
                    )
                except RuntimeError as e:
                    print(f"Error: {e}")
                    continue
            
            if not cmd_text:
                print("[No command heard. Try again.]\n")
                continue
            
            print(f"You said: '{cmd_text}'")
            
            # Start timing for analytics
            analytics.start_command()
            
            # Get command cache
            command_cache = _get_command_cache()
            
            # Check for duplicate command (within 2 seconds)
            is_dup, orig_cmd = command_cache.is_duplicate(cmd_text, time_window=2.0)
            if is_dup:
                print(f"[Duplicate command detected, skipping]")
                continue
            
            # Check for performance command
            cmd_lower = cmd_text.lower().strip()
            if cmd_lower in ['performance', 'performance index', 'show performance', 
                            'stats', 'statistics', 'how am i doing', 'performance report']:
                analytics.print_summary(24)
                perf = analytics.calculate_performance_index(24)
                response = f"Your VoxMind performance index is {perf.overall_score} out of 100, grade {perf.grade}. " \
                          f"Accuracy is {perf.accuracy_score}%, speed score is {perf.speed_score}%."
                analytics.record_command(cmd_text, 'performance', 'system', True)
                print(f"Vox: {response}\n")
                if not no_tts:
                    try:
                        speak_text(response)
                    except Exception as e:
                        print(f"[TTS warning]: {e}")
                continue
            
            # Check for cache stats command
            if cmd_lower in ['cache stats', 'cache status', 'show cache']:
                stats = command_cache.get_stats()
                response = f"Cache has {stats['size']} entries with {stats['hit_rate']}% hit rate. " \
                          f"{stats['hits']} hits, {stats['misses']} misses, {stats['fuzzy_hits']} fuzzy matches."
                print(f"\n📦 Cache Statistics:")
                for k, v in stats.items():
                    print(f"   • {k}: {v}")
                print(f"\nVox: {response}\n")
                if not no_tts:
                    try:
                        speak_text(response)
                    except Exception as e:
                        print(f"[TTS warning]: {e}")
                continue
            
            # Check for interface command - launch web UI
            if cmd_lower in ['open interface', 'show interface', 'launch interface', 
                            'open web interface', 'start interface', 'interface',
                            'open dashboard', 'show dashboard', 'web mode']:
                print("\n🌐 Launching VoxMind Web Interface...")
                try:
                    import subprocess
                    import webbrowser
                    # Start interface server in background
                    interface_proc = subprocess.Popen(
                        [sys.executable, 'run_interface.py', '--no-browser'],
                        cwd=ROOT,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    sleep(1.5)  # Wait for server to start
                    webbrowser.open('http://127.0.0.1:5000')
                    response = "I've opened the web interface for you. You can interact with me using the browser for math, physics, and coding assistance."
                except Exception as e:
                    response = f"Sorry, I couldn't launch the interface. Error: {e}"
                print(f"\nVox: {response}\n")
                if not no_tts:
                    try:
                        speak_text(response)
                    except Exception as e:
                        print(f"[TTS warning]: {e}")
                continue
            
            # Check cache for exact match first
            cached_entry = command_cache.get(cmd_text)
            if cached_entry:
                print(f"[Cache HIT - exact match]")
                parsed = cached_entry.parsed_result
                response = cached_entry.response
                error = None
            else:
                # Check for fuzzy match (similar command)
                fuzzy_entry = command_cache.get_fuzzy(cmd_text)
                if fuzzy_entry:
                    print(f"[Cache HIT - fuzzy match: '{fuzzy_entry.command_text}']")
                    parsed = fuzzy_entry.parsed_result
                    response = fuzzy_entry.response
                    error = None
                else:
                    # No cache hit, process normally
                    parsed, response, error = backend_app.handle(cmd_text)
                    
                    # Cache the result if successful
                    if response and not error:
                        command_cache.put(cmd_text, response, parsed, ttl=300.0)
            
            method = parsed.get('method', 'unknown')
            confidence = parsed.get('confidence', 0)
            command_type = parsed.get('command', 'unknown')
            
            # Determine category for analytics
            category = _get_command_category(command_type)
            
            if method == 'nlp' and confidence > 0:
                print(f"[Understood: {parsed['command']} - {confidence:.0%} confidence]")
            else:
                print(f"[Command: {parsed['command']}]")
            
            # Record command to analytics
            success = error is None and response is not None
            analytics.record_command(
                command_text=cmd_text,
                command_type=command_type,
                category=category,
                success=success,
                confidence=confidence if confidence else 1.0,
                error_message=str(error) if error else ""
            )
            
            # Record to unified memory for context/pronoun resolution
            _record_to_memory(
                user_input=cmd_text,
                response=response or "",
                command=command_type,
                entities=parsed.get('params', {}),
                success=success
            )
            
            # Check for shutdown
            if parsed.get('command') == 'system_power':
                mode = parsed.get('params', {}).get('mode')
                if mode in ['shutdown', 'restart']:
                    # End session and show final stats
                    analytics.end_session()
                    print("\n📊 Session Performance Summary:")
                    analytics.print_summary(1)  # Last hour stats
                    
                    response = Vox.get_shutdown_message()
                    print(f"\nVox: {response}\n")
                    if not no_tts:
                        try:
                            speak_text(response)
                        except Exception as e:
                            print(f"[TTS warning]: {e}")
                    break
            
            if response is None:
                response = Vox.get_error_message(str(error)) if error else Vox.get_not_understood()
            print(f"Vox: {response}\n")
            
            if not no_tts:
                try:
                    speak_text(response)
                except Exception as e:
                    print(f"TTS error: {e}")
            
            sleep(0.3)
            
        except KeyboardInterrupt:
            # End session on interrupt
            analytics.end_session()
            print("\n📊 Session Performance Summary:")
            analytics.print_summary(1)
            
            goodbye = Vox.get_shutdown_message()
            print(f"\n{goodbye}")
            break
        except Exception as e:
            print(f"Error: {e}\n")


def _get_command_category(command_type: str) -> str:
    """Map command type to analytics category."""
    category_map = {
        # Browser
        'open_browser': 'browser',
        'search': 'search',
        'search_web': 'search',
        'google': 'search',
        # Time
        'time': 'time',
        'date': 'time',
        'day': 'time',
        # Media
        'play_music': 'media',
        'pause_music': 'media',
        'next_track': 'media',
        'media': 'media',
        # Volume
        'volume_up': 'volume',
        'volume_down': 'volume',
        'volume_set': 'volume',
        'mute': 'volume',
        'volume': 'volume',
        # Brightness
        'brightness': 'brightness',
        'brightness_up': 'brightness',
        'brightness_down': 'brightness',
        # Apps
        'open_app': 'app_control',
        'close_app': 'app_control',
        'switch_app': 'app_control',
        'app_control': 'app_control',
        # Windows
        'snap': 'window',
        'minimize': 'window',
        'maximize': 'window',
        'show_desktop': 'window',
        'window': 'window',
        # Mouse
        'click': 'mouse',
        'move': 'mouse',
        'scroll': 'mouse',
        'drag': 'mouse',
        'grid': 'mouse',
        'input_control': 'mouse',
        # Keyboard
        'type': 'keyboard',
        'press': 'keyboard',
        'hotkey': 'keyboard',
        'keyboard': 'keyboard',
        # Screen
        'describe_screen': 'screen',
        'find_text': 'screen',
        'click_text': 'screen',
        'screen_context': 'screen',
        # Monitor
        'screen_monitor': 'monitor',
        'start_watching': 'monitor',
        'stop_watching': 'monitor',
        # System
        'system_power': 'system',
        'shutdown': 'system',
        'restart': 'system',
        'lock': 'system',
        # Help
        'help': 'help',
        'greeting': 'help',
    }
    return category_map.get(command_type, 'unknown')

def main():
    parser = argparse.ArgumentParser(description='VoxMind Voice Assistant')
    parser.add_argument('--simulate', action='store_true', help='Keyboard mode')
    parser.add_argument('--no-tts', action='store_true', help='Disable TTS')
    args = parser.parse_args()
    
    run_loop(simulate=args.simulate, no_tts=args.no_tts)

if __name__ == '__main__':
    main()
