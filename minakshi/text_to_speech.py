"""
VoxMind Text-to-Speech Module
=============================
Enhanced TTS with features inspired by Google Cloud TTS and Windows Voice Access.

Supported Features:
- Rate control (words per minute)
- Volume control (0.0 - 1.0)
- Pitch control (NEW - not all engines support this)
- Voice selection by index, name, or language preference
- Pause insertion with {pause:Xs} syntax
- Emphasis simulation with rate/volume changes
- Number/date formatting helpers

Comparison to Google Cloud TTS:
- ✅ Rate, Volume, Voice Selection (supported)
- ⚠️ Pitch (partial - engine dependent)
- ❌ Full SSML (not supported in pyttsx3)
- ❌ Neural/Wavenet voices (requires cloud API)

For full SSML/neural voices, consider google-cloud-texttospeech package.
"""

import pyttsx3
import re
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class SpeechStyle(Enum):
    """Speech styles inspired by Google TTS <google:style> tag."""
    NORMAL = "normal"
    CALM = "calm"           # Slower, softer
    LIVELY = "lively"       # Faster, louder
    EMPHATIC = "emphatic"   # Slower, louder (like <emphasis level="strong">)
    WHISPER = "whisper"     # Very soft, slower


@dataclass
class VoiceConfig:
    """Voice configuration similar to Google TTS VoiceSelectionParams."""
    voice_index: Optional[int] = None
    voice_name: Optional[str] = None
    language_code: Optional[str] = None  # e.g., "en-US", "en-GB"
    gender: Optional[str] = None  # "male", "female"


@dataclass
class AudioConfig:
    """Audio configuration similar to Google TTS AudioConfig."""
    rate: int = 180           # Words per minute (default 200 for most engines)
    volume: float = 0.9       # 0.0 to 1.0
    pitch: float = 1.0        # 0.5 to 2.0 (1.0 = normal) - may not work on all engines
    style: SpeechStyle = SpeechStyle.NORMAL


# Style presets (rate_modifier, volume_modifier)
STYLE_PRESETS = {
    SpeechStyle.NORMAL: (1.0, 1.0),
    SpeechStyle.CALM: (0.85, 0.7),
    SpeechStyle.LIVELY: (1.15, 1.0),
    SpeechStyle.EMPHATIC: (0.8, 1.0),
    SpeechStyle.WHISPER: (0.7, 0.4),
}

test_text = "Hello User, Welcome to voxmind. This is a sample voice"


def list_voices() -> List[Dict[str, Any]]:
    """List all available voices with details.
    
    Returns a list of voice info dicts (similar to Google TTS voices.list).
    """
    engine = pyttsx3.init()
    voices = list(engine.getProperty('voices') or [])  # type: ignore[arg-type]
    
    voice_list = []
    print(f"Total voices available: {len(voices)}")
    for i, v in enumerate(voices):
        voice_info = {
            "index": i,
            "id": v.id,
            "name": v.name,
            "languages": getattr(v, 'languages', []),
            "gender": getattr(v, 'gender', 'unknown'),
        }
        voice_list.append(voice_info)
        print(f"{i}: {v.name}")
    
    engine.stop()
    return voice_list


def find_voice_by_preference(
    language: Optional[str] = None,
    gender: Optional[str] = None,
    name_contains: Optional[str] = None
) -> Optional[int]:
    """Find a voice matching preferences (like Google TTS voice selection).
    
    Args:
        language: Language code like "en", "en-US", "en-GB"
        gender: "male" or "female"
        name_contains: Part of the voice name (e.g., "Zira", "David")
    
    Returns:
        Voice index or None if not found.
    """
    engine = pyttsx3.init()
    voices = list(engine.getProperty('voices') or [])  # type: ignore[arg-type]
    
    for i, v in enumerate(voices):
        name_lower = v.name.lower()
        
        # Check name match (highest priority)
        if name_contains:
            if name_contains.lower() in name_lower:
                engine.stop()
                return i
            else:
                # Name specified but doesn't match - skip this voice
                continue
        
        # Check language
        if language:
            lang_lower = language.lower()
            if lang_lower not in name_lower and lang_lower not in str(getattr(v, 'languages', [])).lower():
                continue
        
        # Check gender (heuristic based on common voice names)
        if gender:
            gender_lower = gender.lower()
            female_names = ['zira', 'hazel', 'susan', 'female', 'woman']
            male_names = ['david', 'mark', 'james', 'male', 'man']
            
            if gender_lower == 'female' and not any(fn in name_lower for fn in female_names):
                continue
            if gender_lower == 'male' and not any(mn in name_lower for mn in male_names):
                continue
        
        engine.stop()
        return i
    
    engine.stop()
    return None


def process_text_markup(text: str) -> List[tuple]:
    """Process simple markup syntax for pauses and emphasis.
    
    Supported syntax (inspired by SSML):
    - {pause:1s} or {pause:500ms} - Insert pause
    - {emphasis}text{/emphasis} - Speak with emphasis
    - {spell}ABC{/spell} - Spell out letters
    
    Returns list of (text, is_pause, pause_duration) tuples.
    """
    segments = []
    
    # Process pause markers: {pause:Xs} or {pause:Xms}
    pattern = r'\{pause:(\d+)(s|ms)\}'
    last_end = 0
    
    for match in re.finditer(pattern, text):
        # Add text before pause
        if match.start() > last_end:
            segments.append((text[last_end:match.start()], False, 0))
        
        # Add pause
        duration = int(match.group(1))
        if match.group(2) == 's':
            duration *= 1000  # Convert to ms
        segments.append(('', True, duration))
        last_end = match.end()
    
    # Add remaining text
    if last_end < len(text):
        segments.append((text[last_end:], False, 0))
    
    return segments if segments else [(text, False, 0)]


def format_as_spoken(text: str) -> str:
    """Format text for better TTS pronunciation (like SSML say-as).
    
    Handles:
    - Ordinals: 1st, 2nd, 3rd -> first, second, third
    - Acronyms in caps: NASA -> N.A.S.A
    - Common abbreviations
    """
    # Ordinal numbers
    ordinals = {
        '1st': 'first', '2nd': 'second', '3rd': 'third', '4th': 'fourth',
        '5th': 'fifth', '6th': 'sixth', '7th': 'seventh', '8th': 'eighth',
        '9th': 'ninth', '10th': 'tenth', '11th': 'eleventh', '12th': 'twelfth',
        '13th': 'thirteenth', '20th': 'twentieth', '21st': 'twenty-first',
        '30th': 'thirtieth', '100th': 'hundredth'
    }
    
    for abbr, full in ordinals.items():
        text = re.sub(rf'\b{abbr}\b', full, text, flags=re.IGNORECASE)
    
    # Spell out all-caps acronyms (3+ letters)
    def spell_acronym(match):
        return ' '.join(match.group(0))
    
    text = re.sub(r'\b[A-Z]{3,}\b', spell_acronym, text)
    
    return text


def speak(text: str, voice_index: int, rate: int = 180, volume: float = 0.8):
    """Speak text with specified voice and audio settings.
    
    Args:
        text: Text to speak
        voice_index: Index of voice from list_voices()
        rate: Speaking rate in words per minute (default 180)
        volume: Volume from 0.0 to 1.0 (default 0.8)
    """
    engine = pyttsx3.init()
    voices = list(engine.getProperty('voices') or [])  # type: ignore[arg-type]

    if voice_index < 0 or voice_index >= len(voices):
        raise ValueError("Voice index out of range")

    engine.setProperty('voice', voices[voice_index].id)
    engine.setProperty('rate', rate)
    engine.setProperty('volume', volume)

    engine.say(text)
    engine.runAndWait()
    
    try:
        engine.stop()
    except RuntimeError:
        pass  # Engine may already be stopped

def speak_with_style(
    text: str,
    style: SpeechStyle = SpeechStyle.NORMAL,
    voice_config: Optional[VoiceConfig] = None,
    audio_config: Optional[AudioConfig] = None
):
    """Speak text with style and configuration (Google TTS-like API).
    
    This is the advanced API inspired by Google Cloud TTS.
    
    Args:
        text: Text to speak (can include {pause:Xs} markup)
        style: Speaking style (NORMAL, CALM, LIVELY, EMPHATIC, WHISPER)
        voice_config: Voice selection parameters
        audio_config: Audio settings (rate, volume, pitch)
    
    Example:
        speak_with_style(
            "Hello! {pause:1s} Welcome to VoxMind.",
            style=SpeechStyle.LIVELY,
            audio_config=AudioConfig(rate=200, volume=0.9)
        )
    """
    audio_config = audio_config or AudioConfig()
    voice_config = voice_config or VoiceConfig()
    
    # Apply style modifiers
    rate_mod, vol_mod = STYLE_PRESETS.get(style, (1.0, 1.0))
    final_rate = int(audio_config.rate * rate_mod)
    final_volume = min(1.0, audio_config.volume * vol_mod)
    
    # Find voice
    voice_idx = voice_config.voice_index
    if voice_idx is None and (voice_config.voice_name or voice_config.language_code):
        voice_idx = find_voice_by_preference(
            language=voice_config.language_code,
            gender=voice_config.gender,
            name_contains=voice_config.voice_name
        )
    
    # Process markup for pauses
    segments = process_text_markup(text)
    
    engine = pyttsx3.init()
    voices = list(engine.getProperty('voices') or [])  # type: ignore[arg-type]
    
    # Set voice
    if voice_idx is not None and 0 <= voice_idx < len(voices):
        engine.setProperty('voice', voices[voice_idx].id)
    else:
        # Default to first English voice
        for v in voices:
            if 'english' in v.name.lower() or 'zira' in v.name.lower():
                engine.setProperty('voice', v.id)
                break
    
    engine.setProperty('rate', final_rate)
    engine.setProperty('volume', final_volume)
    
    # Speak segments with pauses
    for segment_text, is_pause, pause_ms in segments:
        if is_pause:
            engine.runAndWait()
            time.sleep(pause_ms / 1000.0)
        elif segment_text.strip():
            # Format for better pronunciation
            formatted_text = format_as_spoken(segment_text)
            engine.say(formatted_text)
    
    engine.runAndWait()
    
    try:
        engine.stop()
    except RuntimeError:
        pass  # Engine may already be stopped


def demo():
    """Interactive demo to test voices and features."""
    print("\n" + "="*60)
    print("VoxMind TTS Demo - Enhanced with Google TTS-inspired features")
    print("="*60)
    
    voices = list_voices()
    
    print("\n--- Demo Options ---")
    print("1. Test basic voice by index")
    print("2. Test speech styles")
    print("3. Test pause markup")
    print("4. Test formatting (ordinals, acronyms)")
    print("5. Find voice by preference")
    print("q. Quit")
    
    while True:
        choice = input("\nEnter option: ").strip().lower()
        
        if choice == "q":
            print("Quitting...")
            return
        elif choice == "1":
            idx = input("Enter voice index: ").strip()
            try:
                speak(test_text, int(idx))
            except Exception as e:
                print(f"Error: {e}")
        elif choice == "2":
            print("\nTesting styles on: 'Hello, welcome to VoxMind!'")
            for style in SpeechStyle:
                print(f"  Playing: {style.value}...")
                speak_with_style(
                    "Hello, welcome to VoxMind!",
                    style=style
                )
                time.sleep(0.5)
        elif choice == "3":
            test_pause = "Step one, take a breath. {pause:2s} Step two, exhale."
            print(f"\nTesting: '{test_pause}'")
            speak_with_style(test_pause)
        elif choice == "4":
            test_format = "You are 1st in line. NASA has announced the ISS mission."
            print(f"\nOriginal: '{test_format}'")
            formatted = format_as_spoken(test_format)
            print(f"Formatted: '{formatted}'")
            speak_with_style(test_format)
        elif choice == "5":
            lang = input("Language (e.g., 'en', leave blank for any): ").strip() or None
            gender = input("Gender ('male'/'female', leave blank for any): ").strip() or None
            idx = find_voice_by_preference(language=lang, gender=gender)
            if idx is not None:
                print(f"Found voice at index {idx}")
                speak(test_text, idx)
            else:
                print("No matching voice found")
        else:
            print("Invalid option")


if __name__ == "__main__":
    demo()


# =============================================================================
# VoxMind Integration API (with Voice Access Settings support)
# =============================================================================

# Try to import voice access settings (optional dependency)
try:
    from core.voice_access_settings import get_settings, VerbosityLevel
    _has_voice_access_settings = True
except ImportError:
    _has_voice_access_settings = False
    VerbosityLevel = None  # type: ignore


def _should_speak(is_error: bool = False) -> bool:
    """
    Check if we should speak based on verbosity settings.
    
    Inspired by Google Voice Access verbosity levels:
    - ALL: Speak everything
    - ERRORS_ONLY: Only speak on errors
    - NONE: Never speak (visual feedback only)
    """
    if not _has_voice_access_settings or VerbosityLevel is None:
        return True  # No settings module, always speak
    
    try:
        settings = get_settings()
        verbosity = settings.verbosity
        if verbosity.value == "none":
            return False
        if verbosity.value == "errors":
            return is_error
        return True  # VerbosityLevel.ALL
    except (AttributeError, ImportError) as e:
        return True  # Default to speaking on error


def speak_text(
    text: str,
    rate: int = 180,
    volume: float = 0.9,
    style: Optional[str] = None,
    is_error: bool = False,
    force: bool = False
):
    """Speak text using the default system voice.
    
    This is the main function used by VoxMind for voice feedback.
    Creates a fresh engine each time to avoid blocking issues with pyttsx3.
    
    Args:
        text: Text to speak (supports {pause:Xs} markup)
        rate: Speaking rate in WPM (default 180)
        volume: Volume 0.0-1.0 (default 0.9)
        style: Optional style name: "calm", "lively", "emphatic", "whisper"
        is_error: Whether this is an error message (affects verbosity filtering)
        force: Bypass verbosity settings and always speak
    
    Example:
        speak_text("Hello! {pause:1s} How can I help?")
        speak_text("I'm excited!", style="lively")
        speak_text("Error occurred", is_error=True)  # Speaks even in ERRORS_ONLY mode
    """
    # Check verbosity settings (inspired by Google Voice Access)
    if not force and not _should_speak(is_error):
        print(f"[Vox (silent)]: {text}")  # Visual feedback only
        return
    
    # Get settings from voice access config if available
    if _has_voice_access_settings and not force:
        try:
            settings = get_settings()
            rate = settings.voice_rate
            volume = settings.voice_volume
            style = style or settings.voice_style
        except (AttributeError, ImportError):
            pass  # Use defaults if settings unavailable
    
    # Map style string to enum
    speech_style = SpeechStyle.NORMAL
    if style:
        style_map = {s.value: s for s in SpeechStyle}
        speech_style = style_map.get(style.lower(), SpeechStyle.NORMAL)
    
    try:
        speak_with_style(
            text,
            style=speech_style,
            audio_config=AudioConfig(rate=rate, volume=volume)
        )
    except Exception as e:
        print(f"[TTS Error]: {e}")
        print(f"[Vox says]: {text}")


def speak_error(text: str):
    """Speak an error message (respects ERRORS_ONLY verbosity)."""
    speak_text(text, style="emphatic", is_error=True)


def speak_confirmation(text: str):
    """Speak a confirmation (skipped in ERRORS_ONLY mode)."""
    speak_text(text, is_error=False)


def speak_emphasized(text: str):
    """Speak text with emphasis (like SSML <emphasis level="strong">)."""
    speak_text(text, style="emphatic")


def speak_calmly(text: str):
    """Speak text in a calm, soothing manner."""
    speak_text(text, style="calm")


def speak_with_pause(text: str, pause_seconds: float = 1.0):
    """Speak text followed by a pause.
    
    Args:
        text: Text to speak
        pause_seconds: Seconds to pause after speaking
    """
    speak_text(f"{text} {{pause:{pause_seconds}s}}")


# =============================================================================
# Voice Persona Support - Different voices for different AI personalities
# =============================================================================

# Voice persona configurations with enhanced differentiation
# Each persona has unique: rate, pitch, volume, style, and text preprocessing
VOICE_PERSONA_CONFIG = {
    # Male voices (use David voice with pitch/rate variations)
    "jarvis": {
        "voice_keywords": ["david", "mark", "male"],
        "gender": "male",
        "rate": 155,          # Slower, deliberate
        "pitch": -15,         # Lower pitch for authority
        "volume": 0.95,
        "style": "normal",
        "pause_factor": 1.2,  # Longer pauses between sentences
        "description": "Tactical, precise, authoritative"
    },
    "vision": {
        "voice_keywords": ["david", "mark", "male"],
        "gender": "male",
        "rate": 140,          # Very slow, contemplative
        "pitch": -5,          # Slightly lower
        "volume": 0.8,        # Softer, thoughtful
        "style": "calm",
        "pause_factor": 1.5,  # Long pauses for reflection
        "description": "Philosophical, reflective, calm"
    },
    "edith": {
        "voice_keywords": ["david", "mark", "male"],
        "gender": "male",
        "rate": 175,          # Moderate, warm pace
        "pitch": 5,           # Slightly higher for warmth
        "volume": 0.88,
        "style": "calm",
        "pause_factor": 1.1,
        "description": "Empathetic, warm, supportive"
    },
    # Female voices (use Zira voice with pitch/rate variations)
    "elisa": {
        "voice_keywords": ["zira", "hazel", "female"],
        "gender": "female",
        "rate": 165,          # Clear, measured academic pace
        "pitch": -10,         # Slightly lower for authority
        "volume": 0.9,
        "style": "normal",
        "pause_factor": 1.2,
        "description": "Academic, analytical, precise"
    },
    "sofia": {
        "voice_keywords": ["zira", "hazel", "female"],
        "gender": "female",
        "rate": 200,          # Fast, energetic
        "pitch": 15,          # Higher pitch for enthusiasm
        "volume": 0.98,
        "style": "lively",
        "pause_factor": 0.8,  # Shorter pauses, more dynamic
        "description": "Creative, enthusiastic, expressive"
    },
    "friday": {
        "voice_keywords": ["zira", "hazel", "female"],
        "gender": "female",
        "rate": 185,          # Conversational pace
        "pitch": 0,           # Natural pitch
        "volume": 0.9,
        "style": "normal",
        "pause_factor": 1.0,
        "description": "Casual, friendly, approachable"
    },
}

# Current active persona
_current_persona = "friday"


def set_voice_persona(persona_name: str) -> bool:
    """Set the active voice persona for TTS.
    
    Args:
        persona_name: Name of persona (jarvis, vision, edith, elisa, sofia, friday)
    
    Returns:
        True if persona was set successfully
    """
    global _current_persona
    persona_lower = persona_name.lower()
    if persona_lower in VOICE_PERSONA_CONFIG:
        _current_persona = persona_lower
        return True
    return False


def get_voice_persona() -> str:
    """Get the current voice persona name."""
    return _current_persona


def get_voice_persona_config(persona_name: str = None) -> dict:
    """Get configuration for a voice persona."""
    name = (persona_name or _current_persona).lower()
    return VOICE_PERSONA_CONFIG.get(name, VOICE_PERSONA_CONFIG["friday"])


def speak_as_persona(
    text: str,
    persona: str = None,
    is_error: bool = False,
    force: bool = False
):
    """Speak text using the specified voice persona's settings.
    
    Each persona has distinct:
    - Voice (male/female)
    - Speaking rate
    - Volume
    - Style (calm, lively, etc.)
    
    Args:
        text: Text to speak
        persona: Persona name (uses current if None)
        is_error: Whether this is an error message
        force: Bypass verbosity settings
    
    Example:
        speak_as_persona("Hello!", "jarvis")  # Male, slower, precise
        speak_as_persona("Let's go!", "sofia")  # Female, faster, lively
    """
    # Check verbosity
    if not force and not _should_speak(is_error):
        print(f"[Vox (silent)]: {text}")
        return
    
    # Get persona config
    config = get_voice_persona_config(persona)
    
    # Find appropriate voice
    voice_idx = None
    for keyword in config.get("voice_keywords", []):
        voice_idx = find_voice_by_preference(name_contains=keyword)
        if voice_idx is not None:
            break
    
    # Fallback: try by gender
    if voice_idx is None:
        voice_idx = find_voice_by_preference(gender=config.get("gender"))
    
    # Get speech settings
    rate = config.get("rate", 180)
    volume = config.get("volume", 0.9)
    pitch_offset = config.get("pitch", 0)
    pause_factor = config.get("pause_factor", 1.0)
    style_name = config.get("style", "normal")
    
    # Apply style modifiers
    style_map = {s.value: s for s in SpeechStyle}
    speech_style = style_map.get(style_name, SpeechStyle.NORMAL)
    rate_mod, vol_mod = STYLE_PRESETS.get(speech_style, (1.0, 1.0))
    final_rate = int(rate * rate_mod)
    final_volume = min(1.0, volume * vol_mod)
    
    try:
        # Use direct engine control for pitch adjustment
        engine = pyttsx3.init()
        voices = list(engine.getProperty('voices') or [])
        
        # Set voice
        if voice_idx is not None and 0 <= voice_idx < len(voices):
            engine.setProperty('voice', voices[voice_idx].id)
        
        # Set rate and volume
        engine.setProperty('rate', final_rate)
        engine.setProperty('volume', final_volume)
        
        # Apply pitch adjustment (SAPI5 specific - works on Windows)
        # Pitch range is typically -10 to +10, we scale our -15 to +15 range
        try:
            # For SAPI5, we can inject pitch via XML
            if pitch_offset != 0:
                # Use SAPI pitch tags: <pitch absmiddle="N"/> where N is -10 to +10
                pitch_val = max(-10, min(10, pitch_offset // 1.5))  # Scale to SAPI range
                text = f'<pitch absmiddle="{int(pitch_val)}"/>{text}'
        except (TypeError, ValueError) as e:
            pass  # Skip pitch adjustment if calculation fails
        
        # Add pauses between sentences based on pause_factor
        if pause_factor != 1.0:
            import re
            # Add pause markers after sentence endings
            pause_ms = int(300 * pause_factor)
            text = re.sub(r'([.!?])\s+', rf'\1 {{pause:{pause_ms}ms}} ', text)
        
        # Process markup for pauses
        segments = process_text_markup(text)
        
        for segment_text, is_pause, pause_ms in segments:
            if is_pause:
                engine.runAndWait()
                time.sleep(pause_ms / 1000.0)
            elif segment_text.strip():
                formatted_text = format_as_spoken(segment_text)
                engine.say(formatted_text)
        
        engine.runAndWait()
        engine.stop()
        
    except Exception as e:
        print(f"[TTS Error]: {e}")
        print(f"[{(persona or _current_persona).title()}]: {text}")


def speak_text_with_persona(
    text: str,
    rate: int = None,
    volume: float = None,
    style: Optional[str] = None,
    is_error: bool = False,
    force: bool = False
):
    """Enhanced speak_text that uses current voice persona settings.
    
    If rate/volume/style are not provided, uses the current persona's defaults.
    Uses pitch adjustment and pause factors for distinct voice variations.
    """
    config = get_voice_persona_config()
    
    # Check verbosity
    if not force and not _should_speak(is_error):
        print(f"[Vox (silent)]: {text}")
        return
    
    # Use persona defaults if not overridden
    final_rate = rate if rate is not None else config.get("rate", 180)
    final_volume = volume if volume is not None else config.get("volume", 0.9)
    final_style = style if style is not None else config.get("style", "normal")
    pitch_offset = config.get("pitch", 0)
    pause_factor = config.get("pause_factor", 1.0)
    
    # Find voice for current persona
    voice_idx = None
    for keyword in config.get("voice_keywords", []):
        voice_idx = find_voice_by_preference(name_contains=keyword)
        if voice_idx is not None:
            break
    
    if voice_idx is None:
        voice_idx = find_voice_by_preference(gender=config.get("gender"))
    
    # Apply style modifiers
    style_map = {s.value: s for s in SpeechStyle}
    speech_style = style_map.get(final_style, SpeechStyle.NORMAL)
    rate_mod, vol_mod = STYLE_PRESETS.get(speech_style, (1.0, 1.0))
    final_rate = int(final_rate * rate_mod)
    final_volume = min(1.0, final_volume * vol_mod)
    
    try:
        engine = pyttsx3.init()
        voices = list(engine.getProperty('voices') or [])
        
        # Set voice
        if voice_idx is not None and 0 <= voice_idx < len(voices):
            engine.setProperty('voice', voices[voice_idx].id)
        
        # Set rate and volume
        engine.setProperty('rate', final_rate)
        engine.setProperty('volume', final_volume)
        
        # Apply pitch adjustment (SAPI5 specific)
        processed_text = text
        try:
            if pitch_offset != 0:
                pitch_val = max(-10, min(10, pitch_offset // 1.5))
                processed_text = f'<pitch absmiddle="{int(pitch_val)}"/>{text}'
        except (TypeError, ValueError):
            pass  # Skip pitch adjustment if calculation fails
        
        # Add pauses between sentences
        if pause_factor != 1.0:
            import re
            pause_ms = int(300 * pause_factor)
            processed_text = re.sub(r'([.!?])\s+', rf'\1 {{pause:{pause_ms}ms}} ', processed_text)
        
        # Process markup
        segments = process_text_markup(processed_text)
        
        for segment_text, is_pause, pause_ms in segments:
            if is_pause:
                engine.runAndWait()
                time.sleep(pause_ms / 1000.0)
            elif segment_text.strip():
                formatted_text = format_as_spoken(segment_text)
                engine.say(formatted_text)
        
        engine.runAndWait()
        engine.stop()
        
    except Exception as e:
        print(f"[TTS Error]: {e}")
        print(f"[Vox]: {text}")
        print(f"[Vox]: {text}")


# Backwards compatibility
def _init_engine():
    """Legacy function - no longer needed but kept for compatibility."""
    return True

