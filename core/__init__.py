"""
VoxMind Core Module
===================
Advanced natural language processing for life-like AI interaction.

This module provides:
- Natural Language Engine: Fuzzy matching, word prediction, conversation memory
- Speech Services: Wake word detection + speech-to-text (Whisper, Vosk, Porcupine)
- Profiler: Performance monitoring and bottleneck identification
- Lazy Loader: Deferred imports and model loading
- Async Utils: Async patterns for I/O-bound operations
- Command Cache: LRU caching with tiered storage
- Seamless integration with the main VoxMind assistant
"""

from .natural_language_engine import (
    NaturalLanguageEngine,
    FuzzyMatcher,
    WordPredictor,
    ConversationMemory,
    NaturalResponseGenerator,
    get_engine,
    preprocess,
    predict,
    understand,
)

# Performance utilities (lazy imported to avoid overhead)
def get_profiler():
    """Get PerformanceMonitor singleton."""
    from .profiler import PerformanceMonitor
    return PerformanceMonitor.instance()

def get_lazy_loader(module_name: str):
    """Create a lazy loader for a module."""
    from .lazy_loader import LazyLoader
    return LazyLoader(module_name)

def get_async_cache():
    """Get a new AsyncCache instance."""
    from .async_utils import AsyncCache
    return AsyncCache()

# Speech services (lazy imported)
def get_speech_services():
    """Get unified speech services (wake word + STT)."""
    from .speech_services import get_services
    return get_services()

def get_stt(backend: str = "auto"):
    """Get speech-to-text engine."""
    from .speech_to_text import SpeechToText, STTBackend
    backend_map = {
        "auto": SpeechToText.get_recommended_backend(),
        "whisper": STTBackend.FASTER_WHISPER,
        "vosk": STTBackend.VOSK,
        "google": STTBackend.GOOGLE,
    }
    return SpeechToText(backend=backend_map.get(backend, backend_map["auto"]))

def get_wake_detector(sensitivity: float = 0.5):
    """Get wake word detector."""
    from .wake_word import WakeWordDetector
    return WakeWordDetector(sensitivity=sensitivity)

__all__ = [
    # NLE
    'NaturalLanguageEngine',
    'FuzzyMatcher',
    'WordPredictor',
    'ConversationMemory',
    'NaturalResponseGenerator',
    'get_engine',
    'preprocess',
    'predict',
    'understand',
    # Performance utilities
    'get_profiler',
    'get_lazy_loader',
    'get_async_cache',
    # Speech services
    'get_speech_services',
    'get_stt',
    'get_wake_detector',
    # Intelligent response (ChatGPT-like)
    'get_intelligent_response',
    'process_intelligently',
    'get_varied_response',
]

# Intelligent response system (ChatGPT-like disambiguation and varied responses)
def get_intelligent_response():
    """Get the intelligent response engine for ChatGPT-like responses."""
    from .intelligent_response import get_intelligent_response_engine
    return get_intelligent_response_engine()

def process_intelligently(text: str, parsed: dict, execute: bool = False):
    """
    Process a command with intelligent response generation.
    
    Features:
    - 'Did you mean...?' disambiguation for low confidence
    - Context awareness for follow-up questions
    - Varied response templates (avoids robotic repetition)
    - Streaming responses for low-latency feel
    
    Args:
        text: Original user text
        parsed: Parsed command dict (from NLP parser)
        execute: Whether to execute the command
    
    Returns:
        Dict with response, disambiguation info, etc.
    """
    from .intelligent_response import process_command_intelligently
    return process_command_intelligently(text, parsed, execute)

def get_varied_response(template_key: str, **kwargs) -> str:
    """Get a varied response to avoid sounding robotic."""
    from .intelligent_response import get_varied_response as _get_varied
    return _get_varied(template_key, **kwargs)

__version__ = '1.3.0'
