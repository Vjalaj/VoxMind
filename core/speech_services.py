"""
VoxMind Speech Services Integration
====================================
Unified interface that integrates:
- Wake word detection (Porcupine, Vosk, Fuzzy)
- Speech-to-text (faster-whisper, Vosk, Google)
- Existing VoxMind modules

This provides drop-in replacements for existing functions
with improved backends.

Usage:
    # Drop-in replacement for existing code
    from core.speech_services import (
        listen_for_wake_word,  # Replaces Tejas.wake_word_detector
        listen_for_command,     # Replaces Jalaj.speech_recognition_service
        SpeechServices          # Unified interface
    )
    
    # Or use unified interface
    services = SpeechServices()
    
    if services.wait_for_wake_word():
        command = services.listen_for_command()
        print(f"Command: {command}")
"""

import logging
from typing import Optional, Callable, Dict, Any
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class STTBackend(Enum):
    """Speech-to-text backends."""
    AUTO = "auto"
    FASTER_WHISPER = "faster-whisper"
    VOSK = "vosk"
    GOOGLE = "google"


class WakeWordBackend(Enum):
    """Wake word detection backends."""
    AUTO = "auto"
    PORCUPINE = "porcupine"
    VOSK = "vosk"
    FUZZY = "fuzzy"


@dataclass
class SpeechConfig:
    """Configuration for speech services."""
    # Wake word settings
    wake_words: tuple = ("hey vox", "ok vox", "vox")
    wake_sensitivity: float = 0.5
    wake_backend: WakeWordBackend = WakeWordBackend.AUTO
    
    # STT settings
    stt_backend: STTBackend = STTBackend.AUTO
    stt_model: str = "base.en"  # For whisper
    stt_timeout: float = 5.0
    stt_phrase_limit: float = 10.0
    
    # Porcupine settings (if used)
    porcupine_key: Optional[str] = None


class SpeechServices:
    """
    Unified speech services for VoxMind.
    
    Provides a single interface for wake word detection and
    speech-to-text with automatic backend selection.
    """
    
    def __init__(self, config: Optional[SpeechConfig] = None):
        self.config = config or SpeechConfig()
        
        self._wake_detector = None
        self._stt_engine = None
        
        # Lazy initialization
        self._initialized = False
    
    def _ensure_initialized(self):
        """Initialize engines on first use."""
        if self._initialized:
            return
        
        # Initialize wake word detector
        try:
            from core.wake_word import WakeWordDetector, WakeWordBackend as WWB
            
            backend_map = {
                WakeWordBackend.PORCUPINE: WWB.PORCUPINE,
                WakeWordBackend.VOSK: WWB.VOSK,
                WakeWordBackend.FUZZY: WWB.FUZZY_TEXT,
                WakeWordBackend.AUTO: None,
            }
            
            self._wake_detector = WakeWordDetector(
                backend=backend_map.get(self.config.wake_backend),
                sensitivity=self.config.wake_sensitivity,
                wake_words=list(self.config.wake_words),
                porcupine_key=self.config.porcupine_key
            )
            logger.info(f"Wake word detector initialized: {self._wake_detector.backend}")
            
        except Exception as e:
            logger.warning(f"Advanced wake word init failed: {e}, using fallback")
            self._wake_detector = None
        
        # Initialize STT engine
        try:
            from core.speech_to_text import SpeechToText, STTBackend as SB
            
            backend_map = {
                STTBackend.FASTER_WHISPER: SB.FASTER_WHISPER,
                STTBackend.VOSK: SB.VOSK,
                STTBackend.GOOGLE: SB.GOOGLE,
                STTBackend.AUTO: SpeechToText.get_recommended_backend(),
            }
            
            self._stt_engine = SpeechToText(
                backend=backend_map.get(self.config.stt_backend, SB.GOOGLE),
                model_size=self.config.stt_model
            )
            logger.info(f"STT engine initialized: {self._stt_engine.backend}")
            
        except Exception as e:
            logger.warning(f"Advanced STT init failed: {e}, using fallback")
            self._stt_engine = None
        
        self._initialized = True
    
    def wait_for_wake_word(self, timeout: float = 5.0) -> bool:
        """
        Wait for wake word.
        
        Uses advanced detector if available, falls back to legacy.
        """
        self._ensure_initialized()
        
        if self._wake_detector:
            return self._wake_detector.listen(timeout=timeout)
        else:
            # Fallback to legacy detector
            return _legacy_wake_word_listen(timeout)
    
    def listen_for_command(
        self,
        timeout: float = None,
        phrase_limit: float = None
    ) -> Optional[str]:
        """
        Listen for voice command.
        
        Uses advanced STT if available, falls back to legacy.
        """
        self._ensure_initialized()
        
        timeout = timeout or self.config.stt_timeout
        phrase_limit = phrase_limit or self.config.stt_phrase_limit
        
        if self._stt_engine:
            result = self._stt_engine.transcribe_microphone(
                timeout=timeout,
                phrase_time_limit=phrase_limit
            )
            return result.text if result.text else None
        else:
            # Fallback to legacy
            return _legacy_listen_for_command(timeout, phrase_limit)
    
    def start_continuous_listening(
        self,
        on_command: Callable[[str], None],
        on_wake: Optional[Callable[[], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None
    ):
        """
        Start continuous wake word + command listening.
        
        Args:
            on_command: Called with transcribed command after wake word
            on_wake: Called when wake word detected (before listening)
            on_error: Called when error occurs
        """
        self._ensure_initialized()
        
        def handle_wake():
            if on_wake:
                on_wake()
            
            command = self.listen_for_command()
            if command:
                on_command(command)
        
        if self._wake_detector:
            self._wake_detector.start_listening(
                on_wake=handle_wake,
                on_error=on_error
            )
        else:
            logger.warning("Continuous listening requires advanced wake detector")
    
    def stop_listening(self):
        """Stop continuous listening."""
        if self._wake_detector:
            self._wake_detector.stop_listening()
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of speech services."""
        self._ensure_initialized()
        
        status = {
            'wake_word_backend': None,
            'stt_backend': None,
            'wake_metrics': None,
        }
        
        if self._wake_detector:
            status['wake_word_backend'] = self._wake_detector.backend.value
            status['wake_metrics'] = self._wake_detector.get_metrics()
        
        if self._stt_engine:
            status['stt_backend'] = self._stt_engine.backend.value
        
        return status
    
    def cleanup(self):
        """Clean up resources."""
        if self._wake_detector:
            self._wake_detector.cleanup()


# =============================================================================
# Legacy Fallbacks (for when new modules aren't available)
# =============================================================================

def _legacy_wake_word_listen(timeout: float = 5.0) -> bool:
    """Legacy wake word detection using Tejas module."""
    try:
        from Tejas.wake_word_detector import listen_for_wake_word as legacy_wake
        return legacy_wake(timeout=timeout)
    except ImportError:
        logger.error("No wake word detector available")
        return False


def _legacy_listen_for_command(
    timeout: float = 5.0,
    phrase_limit: float = 10.0
) -> Optional[str]:
    """Legacy command listening using Jalaj module."""
    try:
        from Jalaj.speech_recognition_service import listen_for_command as legacy_listen
        return legacy_listen(timeout=timeout, phrase_time_limit=phrase_limit)
    except ImportError:
        logger.error("No speech recognition service available")
        return None


# =============================================================================
# Drop-in Replacement Functions
# =============================================================================

# Global services instance
_services: Optional[SpeechServices] = None


def get_services() -> SpeechServices:
    """Get or create global speech services."""
    global _services
    if _services is None:
        _services = SpeechServices()
    return _services


def listen_for_wake_word(
    wake_word: str = "hey vox",
    timeout: float = 3.0,
    phrase_time_limit: float = 3.0,
    use_keyboard_fallback: bool = True
) -> bool:
    """
    Drop-in replacement for Tejas.wake_word_detector.listen_for_wake_word
    
    Uses advanced detection when available, falls back to legacy.
    """
    services = get_services()
    
    try:
        return services.wait_for_wake_word(timeout=timeout)
    except Exception as e:
        if use_keyboard_fallback:
            print(f"Wake word detection error: {e}")
            input("Press Enter to simulate wake word 'hey vox'...")
            return True
        return False


def listen_for_command(
    timeout: float = 5.0,
    phrase_time_limit: Optional[float] = 8.0,
    adjust_for_ambient: bool = True,
    ambient_duration: float = 1.0
) -> Optional[str]:
    """
    Drop-in replacement for Jalaj.speech_recognition_service.listen_for_command
    
    Uses advanced STT when available, falls back to legacy.
    """
    services = get_services()
    
    return services.listen_for_command(
        timeout=timeout,
        phrase_limit=phrase_time_limit
    )


# =============================================================================
# Quick Setup Functions
# =============================================================================

def check_speech_backends() -> Dict[str, bool]:
    """Check which speech backends are available."""
    backends = {
        'faster-whisper': False,
        'vosk': False,
        'google': False,
        'porcupine': False,
    }
    
    try:
        import faster_whisper
        backends['faster-whisper'] = True
    except ImportError:
        pass
    
    try:
        import vosk
        backends['vosk'] = True
    except ImportError:
        pass
    
    try:
        import speech_recognition
        backends['google'] = True
    except ImportError:
        pass
    
    try:
        import pvporcupine
        backends['porcupine'] = True
    except ImportError:
        pass
    
    return backends


def print_backend_status():
    """Print status of all speech backends."""
    print("\n📦 Speech Backend Status:")
    print("=" * 40)
    
    backends = check_speech_backends()
    
    for name, available in backends.items():
        status = "✓ installed" if available else "✗ not installed"
        print(f"  {name}: {status}")
    
    print("\n💡 Recommendations:")
    
    if not backends['faster-whisper']:
        print("  • pip install faster-whisper  # Best STT quality")
    
    if not backends['vosk']:
        print("  • pip install vosk            # Lightweight offline")
    
    if not backends['porcupine']:
        print("  • pip install pvporcupine     # Best wake word accuracy")
        print("    (requires free API key from picovoice.ai)")


if __name__ == "__main__":
    print("VoxMind Speech Services Integration")
    print("=" * 40)
    
    print_backend_status()
    
    print("\n🎤 Testing speech services...")
    
    services = SpeechServices()
    status = services.get_status()
    
    print(f"\n📊 Current configuration:")
    print(f"  Wake backend: {status['wake_word_backend']}")
    print(f"  STT backend: {status['stt_backend']}")
    
    print("\n🔊 Say 'Hey Vox' to test wake word...")
    if services.wait_for_wake_word(timeout=10.0):
        print("✅ Wake word detected!")
        print("\n🎙️ Now say a command...")
        
        command = services.listen_for_command(timeout=5.0)
        if command:
            print(f"✅ Command: \"{command}\"")
        else:
            print("⚠️ No command detected")
    else:
        print("⚠️ No wake word detected")
