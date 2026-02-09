"""
VoxMind Advanced Wake Word Detection
====================================
High-accuracy wake word detection with multiple backend support.

Backends:
- Porcupine (recommended): On-device, highly accurate, low latency
- Vosk: Keyword spotting with speech model
- Fuzzy Text: Enhanced text-based matching (fallback)

Usage:
    from core.wake_word import WakeWordDetector, WakeWordBackend
    
    # Use Porcupine (best accuracy)
    detector = WakeWordDetector(backend=WakeWordBackend.PORCUPINE)
    
    # Listen for wake word
    if detector.listen():
        print("Wake word detected!")
    
    # Continuous monitoring
    detector.start_listening(on_wake=lambda: print("Activated!"))

Installation:
    pip install pvporcupine    # Porcupine (requires access key)
    pip install vosk           # Alternative
    pip install SpeechRecognition  # Fallback

Features:
- Multiple wake word support ("Hey Vox", "Vox", "OK Vox")
- Adjustable sensitivity (0.0-1.0)
- Noise-robust detection
- Offline operation (Porcupine/Vosk)
- Metrics and logging
"""

import logging
import time
import threading
import queue
from enum import Enum
from typing import Optional, Callable, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import re
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class WakeWordBackend(Enum):
    """Available wake word detection backends."""
    PORCUPINE = "porcupine"      # Best accuracy, requires API key
    VOSK = "vosk"                # Good, offline
    FUZZY_TEXT = "fuzzy-text"    # Text-based matching (needs STT)
    HYBRID = "hybrid"            # Combine multiple for best results


@dataclass
class WakeWordResult:
    """Result from wake word detection."""
    detected: bool
    wake_word: str = ""
    confidence: float = 0.0
    latency_ms: float = 0.0
    backend: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class WakeWordMetrics:
    """Metrics for wake word detection quality."""
    total_listens: int = 0
    detections: int = 0
    false_positives: int = 0  # User-reported
    missed_detections: int = 0  # User-reported
    avg_latency_ms: float = 0.0
    
    def detection_rate(self) -> float:
        if self.total_listens == 0:
            return 0.0
        return self.detections / self.total_listens
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_listens': self.total_listens,
            'detections': self.detections,
            'detection_rate': f"{self.detection_rate():.1%}",
            'avg_latency_ms': f"{self.avg_latency_ms:.1f}",
            'false_positives': self.false_positives,
            'missed_detections': self.missed_detections,
        }


# =============================================================================
# Check Available Backends
# =============================================================================

def _check_backends() -> Dict[str, bool]:
    """Check which backends are available."""
    available = {}
    
    try:
        import pvporcupine
        available['porcupine'] = True
    except ImportError:
        available['porcupine'] = False
    
    try:
        import vosk
        available['vosk'] = True
    except ImportError:
        available['vosk'] = False
    
    try:
        import speech_recognition
        available['speech_recognition'] = True
    except ImportError:
        available['speech_recognition'] = False
    
    return available


AVAILABLE_BACKENDS = _check_backends()


# =============================================================================
# Porcupine Engine - Best Accuracy
# =============================================================================

class PorcupineEngine:
    """
    Porcupine wake word engine - on-device, highly accurate.
    
    Porcupine is trained specifically for wake word detection with:
    - Very low false positive rate
    - Sub-100ms latency
    - Works offline
    - Low CPU usage
    
    Requires a free access key from: https://picovoice.ai/
    """
    
    # Custom wake words can be created at https://console.picovoice.ai/
    # For built-in words, use keywords like "alexa", "voxmind", "computer"
    
    def __init__(
        self,
        access_key: Optional[str] = None,
        keywords: List[str] = None,
        keyword_paths: List[str] = None,
        sensitivities: List[float] = None
    ):
        """
        Initialize Porcupine engine.
        
        Args:
            access_key: Picovoice access key (get free at picovoice.ai)
            keywords: Built-in keywords like ["voxmind", "computer"]
            keyword_paths: Paths to custom .ppn keyword files
            sensitivities: Detection sensitivity per keyword (0.0-1.0)
        """
        self.access_key = access_key or self._get_access_key()
        self.keywords = keywords or ["voxmind"]  # "voxmind" sounds like "vox"
        self.keyword_paths = keyword_paths
        self.sensitivities = sensitivities or [0.5] * len(self.keywords)
        
        self._porcupine = None
        self._audio_stream = None
        self._lock = threading.Lock()
    
    def _get_access_key(self) -> str:
        """Get access key from environment or config."""
        import os
        
        # Check environment variable
        key = os.environ.get('PORCUPINE_ACCESS_KEY', '')
        if key:
            return key
        
        # Check config file
        config_path = Path.home() / ".voxmind" / "porcupine_key.txt"
        if config_path.exists():
            return config_path.read_text().strip()
        
        raise ValueError(
            "Porcupine access key not found. Get a free key at https://picovoice.ai/\n"
            "Set it via:\n"
            "  1. Environment variable: PORCUPINE_ACCESS_KEY=your_key\n"
            "  2. File: ~/.voxmind/porcupine_key.txt"
        )
    
    def _ensure_initialized(self):
        """Initialize Porcupine engine."""
        if self._porcupine is None:
            with self._lock:
                if self._porcupine is None:
                    import pvporcupine
                    
                    logger.info("Initializing Porcupine wake word engine...")
                    
                    if self.keyword_paths:
                        self._porcupine = pvporcupine.create(
                            access_key=self.access_key,
                            keyword_paths=self.keyword_paths,
                            sensitivities=self.sensitivities
                        )
                    else:
                        self._porcupine = pvporcupine.create(
                            access_key=self.access_key,
                            keywords=self.keywords,
                            sensitivities=self.sensitivities
                        )
                    
                    logger.info(f"Porcupine initialized with keywords: {self.keywords}")
    
    def process_audio_frame(self, audio_frame: bytes) -> int:
        """
        Process a single audio frame.
        
        Args:
            audio_frame: 16-bit PCM audio, 16kHz, mono
        
        Returns:
            Keyword index if detected, -1 otherwise
        """
        self._ensure_initialized()
        
        import struct
        
        # Convert bytes to int16 array
        frame_length = self._porcupine.frame_length
        if len(audio_frame) < frame_length * 2:
            return -1
        
        pcm = struct.unpack(f'{frame_length}h', audio_frame[:frame_length * 2])
        
        return self._porcupine.process(pcm)
    
    def listen_once(self, timeout: float = 5.0) -> WakeWordResult:
        """
        Listen for wake word with timeout.
        
        Returns:
            WakeWordResult with detection status
        """
        self._ensure_initialized()
        
        import pyaudio
        import struct
        
        start_time = time.time()
        
        pa = pyaudio.PyAudio()
        stream = pa.open(
            rate=self._porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self._porcupine.frame_length
        )
        
        try:
            while time.time() - start_time < timeout:
                pcm = stream.read(self._porcupine.frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from(f'{self._porcupine.frame_length}h', pcm)
                
                keyword_index = self._porcupine.process(pcm)
                
                if keyword_index >= 0:
                    latency = (time.time() - start_time) * 1000
                    keyword = self.keywords[keyword_index] if keyword_index < len(self.keywords) else "custom"
                    
                    return WakeWordResult(
                        detected=True,
                        wake_word=keyword,
                        confidence=0.95,
                        latency_ms=latency,
                        backend="porcupine"
                    )
            
            return WakeWordResult(
                detected=False,
                latency_ms=(time.time() - start_time) * 1000,
                backend="porcupine"
            )
            
        finally:
            stream.close()
            pa.terminate()
    
    def cleanup(self):
        """Clean up resources."""
        if self._porcupine:
            self._porcupine.delete()
            self._porcupine = None


# =============================================================================
# Vosk Keyword Spotter
# =============================================================================

class VoskKeywordSpotter:
    """
    Vosk-based keyword spotting.
    
    Uses Vosk's speech recognition with keyword filtering.
    Fully offline, no API key required.
    """
    
    WAKE_WORDS = [
        "hey vox", "ok vox", "vox", "hey box", "hey fox",
        "voxmind", "hey voxmind", "vox mind"
    ]
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        wake_words: List[str] = None,
        sensitivity: float = 0.5
    ):
        self.model_path = model_path
        self.wake_words = [w.lower() for w in (wake_words or self.WAKE_WORDS)]
        self.sensitivity = sensitivity
        
        self._model = None
        self._lock = threading.Lock()
    
    def _ensure_model(self):
        """Load Vosk model."""
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from vosk import Model, SetLogLevel
                    
                    SetLogLevel(-1)
                    
                    if self.model_path and Path(self.model_path).exists():
                        self._model = Model(self.model_path)
                    else:
                        # Try to find or download small model
                        model_dir = Path.home() / ".cache" / "vosk" / "vosk-model-small-en-us-0.15"
                        if model_dir.exists():
                            self._model = Model(str(model_dir))
                        else:
                            raise RuntimeError(
                                "Vosk model not found. Download from:\n"
                                "https://alphacephei.com/vosk/models"
                            )
    
    def _check_wake_word(self, text: str) -> Tuple[bool, str, float]:
        """Check if text contains wake word."""
        text_lower = text.lower().strip()
        
        # Exact match
        for wake_word in self.wake_words:
            if wake_word in text_lower:
                return True, wake_word, 0.95
        
        # Fuzzy match with threshold based on sensitivity
        threshold = 0.6 + (1 - self.sensitivity) * 0.3  # 0.6-0.9 range
        
        words = text_lower.split()
        for wake_word in self.wake_words:
            wake_parts = wake_word.split()
            
            # Check each word window
            for i in range(max(1, len(words) - len(wake_parts) + 1)):
                window = ' '.join(words[i:i + len(wake_parts)])
                ratio = SequenceMatcher(None, window, wake_word).ratio()
                
                if ratio >= threshold:
                    return True, wake_word, ratio
        
        return False, "", 0.0
    
    def listen_once(self, timeout: float = 5.0) -> WakeWordResult:
        """Listen for wake word using Vosk."""
        self._ensure_model()
        
        import pyaudio
        import json
        from vosk import KaldiRecognizer
        
        start_time = time.time()
        
        recognizer = KaldiRecognizer(self._model, 16000)
        
        pa = pyaudio.PyAudio()
        stream = pa.open(
            rate=16000,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=4000
        )
        
        try:
            while time.time() - start_time < timeout:
                data = stream.read(4000, exception_on_overflow=False)
                
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    text = result.get('text', '')
                    
                    if text:
                        detected, wake_word, confidence = self._check_wake_word(text)
                        if detected:
                            return WakeWordResult(
                                detected=True,
                                wake_word=wake_word,
                                confidence=confidence,
                                latency_ms=(time.time() - start_time) * 1000,
                                backend="vosk"
                            )
                else:
                    # Check partial results
                    partial = json.loads(recognizer.PartialResult())
                    text = partial.get('partial', '')
                    
                    if text:
                        detected, wake_word, confidence = self._check_wake_word(text)
                        if detected:
                            return WakeWordResult(
                                detected=True,
                                wake_word=wake_word,
                                confidence=confidence,
                                latency_ms=(time.time() - start_time) * 1000,
                                backend="vosk"
                            )
            
            return WakeWordResult(
                detected=False,
                latency_ms=(time.time() - start_time) * 1000,
                backend="vosk"
            )
            
        finally:
            stream.close()
            pa.terminate()


# =============================================================================
# Enhanced Fuzzy Text Matcher
# =============================================================================

class FuzzyTextMatcher:
    """
    Enhanced text-based wake word matching.
    
    Uses advanced fuzzy matching with phonetic awareness.
    Works with any STT backend.
    """
    
    # Phonetically similar words to "vox"
    VOX_SOUNDS = {
        "vox", "box", "fox", "vax", "wax", "rocks", "docs", "locks",
        "socks", "bucks", "voice", "boss", "docks", "talks", "walks",
        "forks", "pox", "lox", "cox", "knox", "botch", "watch"
    }
    
    # Wake word patterns
    WAKE_PATTERNS = [
        r"\b(hey|ok|hi|yo|the|a)\s*(vox|box|fox|voice|boss)\b",
        r"\b(vox|box|fox)\s*(mind)?\b",
        r"\bvoxmind\b",
        r"\bhey\s*rocks\b",
    ]
    
    def __init__(self, sensitivity: float = 0.5):
        self.sensitivity = sensitivity
        self._patterns = [re.compile(p, re.IGNORECASE) for p in self.WAKE_PATTERNS]
    
    def check(self, text: str) -> WakeWordResult:
        """Check if text contains wake word."""
        text_lower = text.lower().strip()
        
        if not text_lower:
            return WakeWordResult(detected=False, backend="fuzzy-text")
        
        # Pattern matching
        for pattern in self._patterns:
            match = pattern.search(text_lower)
            if match:
                return WakeWordResult(
                    detected=True,
                    wake_word=match.group(),
                    confidence=0.9,
                    backend="fuzzy-text"
                )
        
        # Word-level check for vox sounds
        words = text_lower.split()
        for word in words:
            if word in self.VOX_SOUNDS:
                # Check if preceded by "hey", "ok", etc.
                idx = words.index(word)
                if idx > 0 and words[idx-1] in {"hey", "ok", "hi", "yo", "the", "a"}:
                    return WakeWordResult(
                        detected=True,
                        wake_word=f"{words[idx-1]} {word}",
                        confidence=0.85,
                        backend="fuzzy-text"
                    )
                # Allow standalone if sensitivity is high enough
                elif self.sensitivity >= 0.7:
                    return WakeWordResult(
                        detected=True,
                        wake_word=word,
                        confidence=0.7,
                        backend="fuzzy-text"
                    )
        
        # Fuzzy matching as last resort
        if self.sensitivity >= 0.8:
            threshold = 0.7
            for wake_word in ["hey vox", "ok vox", "vox"]:
                for i in range(max(1, len(words) - 1)):
                    window = ' '.join(words[i:i+2])
                    ratio = SequenceMatcher(None, window, wake_word).ratio()
                    if ratio >= threshold:
                        return WakeWordResult(
                            detected=True,
                            wake_word=wake_word,
                            confidence=ratio,
                            backend="fuzzy-text"
                        )
        
        return WakeWordResult(detected=False, backend="fuzzy-text")


# =============================================================================
# Unified Wake Word Detector
# =============================================================================

class WakeWordDetector:
    """
    Unified wake word detector with multiple backend support.
    
    Usage:
        # Auto-select best available backend
        detector = WakeWordDetector()
        
        # Listen once
        if detector.listen():
            command = listen_for_command()
        
        # Continuous listening with callback
        detector.start_listening(on_wake=handle_wake)
        
        # Stop listening
        detector.stop_listening()
    """
    
    def __init__(
        self,
        backend: Optional[WakeWordBackend] = None,
        sensitivity: float = 0.5,
        wake_words: List[str] = None,
        porcupine_key: Optional[str] = None
    ):
        """
        Initialize wake word detector.
        
        Args:
            backend: Backend to use (auto-selected if None)
            sensitivity: Detection sensitivity 0.0-1.0
            wake_words: Custom wake words (for text-based backends)
            porcupine_key: Picovoice API key (for Porcupine)
        """
        self.sensitivity = sensitivity
        self.wake_words = wake_words or ["hey vox", "ok vox", "vox"]
        
        # Select backend
        if backend is None:
            backend = self._auto_select_backend()
        
        self.backend = backend
        self._engine = self._create_engine(backend, porcupine_key)
        
        # Metrics
        self.metrics = WakeWordMetrics()
        
        # Continuous listening
        self._listening = False
        self._listen_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
    
    def _auto_select_backend(self) -> WakeWordBackend:
        """Auto-select best available backend."""
        if AVAILABLE_BACKENDS.get('porcupine'):
            return WakeWordBackend.PORCUPINE
        elif AVAILABLE_BACKENDS.get('vosk'):
            return WakeWordBackend.VOSK
        elif AVAILABLE_BACKENDS.get('speech_recognition'):
            return WakeWordBackend.FUZZY_TEXT
        else:
            raise RuntimeError("No wake word backend available")
    
    def _create_engine(
        self,
        backend: WakeWordBackend,
        porcupine_key: Optional[str]
    ):
        """Create the appropriate engine."""
        if backend == WakeWordBackend.PORCUPINE:
            if not AVAILABLE_BACKENDS.get('porcupine'):
                logger.warning("Porcupine not available, falling back")
                return FuzzyTextMatcher(self.sensitivity)
            try:
                return PorcupineEngine(access_key=porcupine_key)
            except Exception as e:
                logger.warning(f"Porcupine init failed: {e}, falling back")
                return FuzzyTextMatcher(self.sensitivity)
        
        elif backend == WakeWordBackend.VOSK:
            if not AVAILABLE_BACKENDS.get('vosk'):
                logger.warning("Vosk not available, falling back")
                return FuzzyTextMatcher(self.sensitivity)
            return VoskKeywordSpotter(
                wake_words=self.wake_words,
                sensitivity=self.sensitivity
            )
        
        else:  # FUZZY_TEXT or fallback
            return FuzzyTextMatcher(self.sensitivity)
    
    def set_sensitivity(self, level: float) -> None:
        """Set detection sensitivity (0.0-1.0)."""
        self.sensitivity = max(0.0, min(1.0, level))
        
        if hasattr(self._engine, 'sensitivity'):
            self._engine.sensitivity = self.sensitivity
    
    def listen(self, timeout: float = 5.0) -> bool:
        """
        Listen for wake word.
        
        Args:
            timeout: Max seconds to wait
        
        Returns:
            True if wake word detected
        """
        self.metrics.total_listens += 1
        
        start = time.time()
        
        if hasattr(self._engine, 'listen_once'):
            result = self._engine.listen_once(timeout)
        else:
            # Use STT + fuzzy matching
            result = self._listen_with_stt(timeout)
        
        if result.detected:
            self.metrics.detections += 1
            # Update average latency
            self.metrics.avg_latency_ms = (
                (self.metrics.avg_latency_ms * (self.metrics.detections - 1) + result.latency_ms)
                / self.metrics.detections
            )
            logger.info(f"Wake word detected: '{result.wake_word}' ({result.latency_ms:.0f}ms)")
        
        return result.detected
    
    def _listen_with_stt(self, timeout: float) -> WakeWordResult:
        """Listen using STT + fuzzy matching."""
        import speech_recognition as sr
        
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 2000
        recognizer.dynamic_energy_threshold = True
        
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.3)
                
                try:
                    audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=3.0)
                except sr.WaitTimeoutError:
                    return WakeWordResult(detected=False, backend="fuzzy-text")
                
                start = time.time()
                
                try:
                    text = recognizer.recognize_google(audio).lower()
                    logger.debug(f"Heard: '{text}'")
                    
                    result = self._engine.check(text)
                    result.latency_ms = (time.time() - start) * 1000
                    return result
                    
                except sr.UnknownValueError:
                    return WakeWordResult(detected=False, backend="fuzzy-text")
                except sr.RequestError as e:
                    logger.error(f"Recognition error: {e}")
                    return WakeWordResult(detected=False, backend="fuzzy-text")
                    
        except OSError as e:
            logger.error(f"Microphone error: {e}")
            return WakeWordResult(detected=False, backend="fuzzy-text")
    
    def start_listening(
        self,
        on_wake: Callable[[], None],
        on_error: Optional[Callable[[Exception], None]] = None
    ) -> None:
        """
        Start continuous wake word listening.
        
        Args:
            on_wake: Callback when wake word detected
            on_error: Callback when error occurs
        """
        if self._listening:
            return
        
        self._listening = True
        self._stop_event.clear()
        
        def listen_loop():
            while not self._stop_event.is_set():
                try:
                    if self.listen(timeout=2.0):
                        on_wake()
                except Exception as e:
                    if on_error:
                        on_error(e)
                    else:
                        logger.error(f"Wake word error: {e}")
        
        self._listen_thread = threading.Thread(target=listen_loop, daemon=True)
        self._listen_thread.start()
        
        logger.info("Started continuous wake word listening")
    
    def stop_listening(self) -> None:
        """Stop continuous listening."""
        self._stop_event.set()
        self._listening = False
        
        if self._listen_thread:
            self._listen_thread.join(timeout=2.0)
            self._listen_thread = None
        
        logger.info("Stopped wake word listening")
    
    def report_false_positive(self) -> None:
        """Report a false positive detection (for metrics)."""
        self.metrics.false_positives += 1
    
    def report_missed_detection(self) -> None:
        """Report a missed detection (for metrics)."""
        self.metrics.missed_detections += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get detection metrics."""
        return self.metrics.to_dict()
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.stop_listening()
        if hasattr(self._engine, 'cleanup'):
            self._engine.cleanup()
    
    @staticmethod
    def get_available_backends() -> Dict[str, bool]:
        """Get available backends."""
        return AVAILABLE_BACKENDS.copy()


# =============================================================================
# Convenience Functions
# =============================================================================

_default_detector: Optional[WakeWordDetector] = None


def get_wake_word_detector() -> WakeWordDetector:
    """Get or create default detector."""
    global _default_detector
    if _default_detector is None:
        _default_detector = WakeWordDetector()
    return _default_detector


def listen_for_wake_word(timeout: float = 5.0) -> bool:
    """
    Quick wake word check.
    
    Usage:
        if listen_for_wake_word():
            command = listen_for_command()
    """
    return get_wake_word_detector().listen(timeout)


if __name__ == "__main__":
    print("VoxMind Wake Word Detector")
    print("=" * 40)
    
    # Show available backends
    print("\n📦 Available backends:")
    for backend, available in WakeWordDetector.get_available_backends().items():
        status = "✓" if available else "✗"
        print(f"  {status} {backend}")
    
    # Recommend installation
    if not AVAILABLE_BACKENDS.get('porcupine'):
        print("\n💡 For best accuracy, install Porcupine:")
        print("   pip install pvporcupine")
        print("   Get free API key at: https://picovoice.ai/")
    
    if not AVAILABLE_BACKENDS.get('vosk'):
        print("\n💡 For offline detection, install Vosk:")
        print("   pip install vosk")
    
    # Demo
    print("\n🎤 Testing wake word detection...")
    print("   Say 'Hey Vox' in the next 10 seconds...")
    
    try:
        detector = WakeWordDetector(sensitivity=0.6)
        
        if detector.listen(timeout=10.0):
            print("\n✅ Wake word detected!")
            print(f"   Metrics: {detector.get_metrics()}")
        else:
            print("\n⚠️ No wake word detected")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
