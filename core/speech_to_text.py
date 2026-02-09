"""
VoxMind Advanced Speech-to-Text Service
========================================
High-performance speech recognition with multiple backend support.

Backends:
- faster-whisper (recommended): Local, fast, accurate
- whisper.cpp: Local, C++ optimized (via Python bindings)
- Vosk: Local, lightweight, offline
- Google: Cloud, requires internet (fallback)

Usage:
    from core.speech_to_text import SpeechToText, STTBackend
    
    # Use faster-whisper (best quality/speed ratio)
    stt = SpeechToText(backend=STTBackend.FASTER_WHISPER)
    text = stt.transcribe_microphone()
    
    # Use with audio file
    text = stt.transcribe_file("audio.wav")
    
    # Streaming transcription
    async for partial in stt.stream_transcribe():
        print(partial)

Installation:
    pip install faster-whisper   # Recommended
    pip install vosk             # Lightweight alternative
    pip install SpeechRecognition # For Google fallback
"""

import logging
import time
import threading
import queue
from enum import Enum
from typing import Optional, Generator, AsyncGenerator, Callable, Any, Dict, List
from dataclasses import dataclass, field
from pathlib import Path
import io

logger = logging.getLogger(__name__)


class STTBackend(Enum):
    """Available speech-to-text backends."""
    FASTER_WHISPER = "faster-whisper"  # Best quality, GPU/CPU
    WHISPER_CPP = "whisper-cpp"        # C++ optimized
    VOSK = "vosk"                       # Lightweight, offline
    GOOGLE = "google"                   # Cloud-based fallback


@dataclass
class TranscriptionResult:
    """Result from speech-to-text transcription."""
    text: str
    confidence: float = 1.0
    language: str = "en"
    duration: float = 0.0
    backend: str = ""
    is_final: bool = True
    segments: List[Dict[str, Any]] = field(default_factory=list)


# Check available backends
def _check_backends() -> Dict[str, bool]:
    """Check which backends are available."""
    available = {}
    
    try:
        import faster_whisper
        available['faster-whisper'] = True
    except ImportError:
        available['faster-whisper'] = False
    
    try:
        import whispercpp
        available['whisper-cpp'] = True
    except ImportError:
        available['whisper-cpp'] = False
    
    try:
        import vosk
        available['vosk'] = True
    except ImportError:
        available['vosk'] = False
    
    try:
        import speech_recognition
        available['google'] = True
    except ImportError:
        available['google'] = False
    
    return available


AVAILABLE_BACKENDS = _check_backends()


class FasterWhisperEngine:
    """
    Faster-whisper backend - CTranslate2 optimized Whisper.
    
    4x faster than OpenAI Whisper with same accuracy.
    Supports GPU (CUDA) and CPU.
    """
    
    def __init__(
        self,
        model_size: str = "base.en",  # tiny.en, base.en, small.en, medium.en
        device: str = "auto",          # auto, cuda, cpu
        compute_type: str = "auto"     # auto, float16, int8
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None
        self._lock = threading.Lock()
    
    def _ensure_model(self):
        """Lazy load the model."""
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from faster_whisper import WhisperModel
                    
                    logger.info(f"Loading faster-whisper model: {self.model_size}")
                    start = time.perf_counter()
                    
                    self._model = WhisperModel(
                        self.model_size,
                        device=self.device,
                        compute_type=self.compute_type
                    )
                    
                    elapsed = time.perf_counter() - start
                    logger.info(f"Model loaded in {elapsed:.2f}s")
    
    def transcribe(
        self,
        audio_path: str,
        language: str = "en",
        beam_size: int = 5,
        vad_filter: bool = True
    ) -> TranscriptionResult:
        """Transcribe audio file."""
        self._ensure_model()
        
        start = time.perf_counter()
        
        segments, info = self._model.transcribe(
            audio_path,
            language=language,
            beam_size=beam_size,
            vad_filter=vad_filter  # Skip silence
        )
        
        # Collect segments
        text_parts = []
        segment_data = []
        
        for segment in segments:
            text_parts.append(segment.text.strip())
            segment_data.append({
                'start': segment.start,
                'end': segment.end,
                'text': segment.text.strip(),
                'confidence': segment.avg_logprob
            })
        
        elapsed = time.perf_counter() - start
        
        return TranscriptionResult(
            text=" ".join(text_parts),
            confidence=0.95,  # Whisper is generally high confidence
            language=info.language,
            duration=elapsed,
            backend="faster-whisper",
            segments=segment_data
        )
    
    def transcribe_audio(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        **kwargs
    ) -> TranscriptionResult:
        """Transcribe raw audio bytes."""
        import tempfile
        import wave
        
        # Write to temp WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            with wave.open(f, 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)  # 16-bit
                wav.setframerate(sample_rate)
                wav.writeframes(audio_data)
        
        try:
            return self.transcribe(temp_path, **kwargs)
        finally:
            Path(temp_path).unlink(missing_ok=True)


class VoskEngine:
    """
    Vosk backend - lightweight offline speech recognition.
    
    Very fast, low memory, works offline.
    Good for wake word detection and short commands.
    """
    
    # Model URLs - will be downloaded on first use
    MODEL_URLS = {
        'small': 'vosk-model-small-en-us-0.15',
        'medium': 'vosk-model-en-us-0.22',
        'large': 'vosk-model-en-us-0.22-lgraph',
    }
    
    def __init__(
        self,
        model_name: str = "small",
        model_path: Optional[str] = None
    ):
        self.model_name = model_name
        self.model_path = model_path
        self._model = None
        self._recognizer = None
        self._lock = threading.Lock()
    
    def _ensure_model(self):
        """Load or download the model."""
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from vosk import Model, SetLogLevel
                    
                    SetLogLevel(-1)  # Suppress logs
                    
                    if self.model_path and Path(self.model_path).exists():
                        model_dir = self.model_path
                    else:
                        # Use default model location
                        model_dir = self._download_model()
                    
                    logger.info(f"Loading Vosk model from: {model_dir}")
                    self._model = Model(model_dir)
    
    def _download_model(self) -> str:
        """Download model if not present."""
        import urllib.request
        import zipfile
        
        model_name = self.MODEL_URLS.get(self.model_name, self.model_name)
        model_dir = Path.home() / ".cache" / "vosk" / model_name
        
        if model_dir.exists():
            return str(model_dir)
        
        url = f"https://alphacephei.com/vosk/models/{model_name}.zip"
        zip_path = model_dir.parent / f"{model_name}.zip"
        
        logger.info(f"Downloading Vosk model: {model_name}")
        model_dir.parent.mkdir(parents=True, exist_ok=True)
        
        urllib.request.urlretrieve(url, zip_path)
        
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(model_dir.parent)
        
        zip_path.unlink()
        
        return str(model_dir)
    
    def transcribe_audio(
        self,
        audio_data: bytes,
        sample_rate: int = 16000
    ) -> TranscriptionResult:
        """Transcribe raw audio bytes."""
        self._ensure_model()
        
        from vosk import KaldiRecognizer
        import json
        
        start = time.perf_counter()
        
        recognizer = KaldiRecognizer(self._model, sample_rate)
        recognizer.SetWords(True)
        
        recognizer.AcceptWaveform(audio_data)
        result = json.loads(recognizer.FinalResult())
        
        elapsed = time.perf_counter() - start
        
        return TranscriptionResult(
            text=result.get('text', ''),
            confidence=result.get('confidence', 0.8),
            duration=elapsed,
            backend="vosk"
        )


class GoogleEngine:
    """
    Google Web Speech API backend - cloud-based fallback.
    
    Requires internet connection.
    Good accuracy but adds latency.
    """
    
    def __init__(self):
        self._recognizer = None
    
    def _ensure_recognizer(self):
        if self._recognizer is None:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
    
    def transcribe_audio(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        language: str = "en-US"
    ) -> TranscriptionResult:
        """Transcribe using Google API."""
        import speech_recognition as sr
        
        self._ensure_recognizer()
        start = time.perf_counter()
        
        # Convert to AudioData
        audio = sr.AudioData(audio_data, sample_rate, 2)
        
        try:
            text = self._recognizer.recognize_google(audio, language=language)
            elapsed = time.perf_counter() - start
            
            return TranscriptionResult(
                text=text,
                confidence=0.9,
                language=language,
                duration=elapsed,
                backend="google"
            )
        except sr.UnknownValueError:
            return TranscriptionResult(
                text="",
                confidence=0.0,
                duration=time.perf_counter() - start,
                backend="google"
            )


class SpeechToText:
    """
    Unified speech-to-text interface with multiple backend support.
    
    Usage:
        stt = SpeechToText(backend=STTBackend.FASTER_WHISPER)
        
        # From microphone
        result = stt.transcribe_microphone(timeout=5.0)
        print(result.text)
        
        # From file
        result = stt.transcribe_file("audio.wav")
        
        # Streaming
        for partial in stt.stream_microphone():
            print(partial.text, end='\\r')
    """
    
    def __init__(
        self,
        backend: STTBackend = STTBackend.FASTER_WHISPER,
        model_size: str = "base.en",
        device: str = "auto",
        fallback_to_google: bool = True
    ):
        self.backend = backend
        self.model_size = model_size
        self.fallback_to_google = fallback_to_google
        
        # Initialize appropriate engine
        self._engine = self._create_engine(backend, model_size, device)
        self._fallback_engine = None
        
        if fallback_to_google and AVAILABLE_BACKENDS.get('google'):
            self._fallback_engine = GoogleEngine()
    
    def _create_engine(
        self,
        backend: STTBackend,
        model_size: str,
        device: str
    ):
        """Create the appropriate engine."""
        if backend == STTBackend.FASTER_WHISPER:
            if not AVAILABLE_BACKENDS.get('faster-whisper'):
                logger.warning("faster-whisper not installed, falling back")
                return self._get_fallback_engine()
            return FasterWhisperEngine(model_size=model_size, device=device)
        
        elif backend == STTBackend.VOSK:
            if not AVAILABLE_BACKENDS.get('vosk'):
                logger.warning("vosk not installed, falling back")
                return self._get_fallback_engine()
            return VoskEngine(model_name=model_size)
        
        elif backend == STTBackend.GOOGLE:
            if not AVAILABLE_BACKENDS.get('google'):
                raise RuntimeError("speech_recognition not installed")
            return GoogleEngine()
        
        else:
            return self._get_fallback_engine()
    
    def _get_fallback_engine(self):
        """Get best available fallback engine."""
        if AVAILABLE_BACKENDS.get('google'):
            return GoogleEngine()
        raise RuntimeError("No speech recognition backend available")
    
    def transcribe_microphone(
        self,
        timeout: float = 5.0,
        phrase_time_limit: float = 10.0,
        adjust_for_ambient: bool = True
    ) -> TranscriptionResult:
        """
        Transcribe from microphone.
        
        Args:
            timeout: Max seconds to wait for speech to start
            phrase_time_limit: Max seconds for the phrase
            adjust_for_ambient: Whether to calibrate for ambient noise
        
        Returns:
            TranscriptionResult with transcribed text
        """
        import speech_recognition as sr
        
        recognizer = sr.Recognizer()
        
        try:
            with sr.Microphone() as source:
                if adjust_for_ambient:
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                logger.debug("Listening...")
                audio = recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )
                
                # Get raw audio data
                audio_data = audio.get_raw_data(convert_rate=16000, convert_width=2)
                
                return self._engine.transcribe_audio(audio_data, sample_rate=16000)
                
        except sr.WaitTimeoutError:
            return TranscriptionResult(
                text="",
                confidence=0.0,
                backend=self.backend.value
            )
        except Exception as e:
            logger.error(f"Microphone error: {e}")
            raise
    
    def transcribe_file(self, file_path: str) -> TranscriptionResult:
        """Transcribe an audio file."""
        if hasattr(self._engine, 'transcribe'):
            return self._engine.transcribe(file_path)
        
        # Read file and use transcribe_audio
        import wave
        
        with wave.open(file_path, 'rb') as wav:
            audio_data = wav.readframes(wav.getnframes())
            sample_rate = wav.getframerate()
        
        return self._engine.transcribe_audio(audio_data, sample_rate)
    
    def stream_microphone(
        self,
        chunk_duration: float = 0.5
    ) -> Generator[TranscriptionResult, None, None]:
        """
        Stream transcription from microphone.
        
        Yields partial results as speech is recognized.
        """
        import speech_recognition as sr
        
        recognizer = sr.Recognizer()
        audio_queue = queue.Queue()
        
        def audio_callback(recognizer, audio):
            audio_queue.put(audio.get_raw_data(convert_rate=16000, convert_width=2))
        
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            stop_listening = recognizer.listen_in_background(
                source,
                audio_callback,
                phrase_time_limit=chunk_duration
            )
            
            try:
                while True:
                    try:
                        audio_data = audio_queue.get(timeout=1.0)
                        result = self._engine.transcribe_audio(audio_data)
                        if result.text:
                            yield result
                    except queue.Empty:
                        continue
            finally:
                stop_listening(wait_for_stop=False)
    
    @staticmethod
    def get_available_backends() -> Dict[str, bool]:
        """Get available backends."""
        return AVAILABLE_BACKENDS.copy()
    
    @staticmethod
    def get_recommended_backend() -> STTBackend:
        """Get the recommended backend based on availability."""
        if AVAILABLE_BACKENDS.get('faster-whisper'):
            return STTBackend.FASTER_WHISPER
        elif AVAILABLE_BACKENDS.get('vosk'):
            return STTBackend.VOSK
        elif AVAILABLE_BACKENDS.get('google'):
            return STTBackend.GOOGLE
        else:
            raise RuntimeError("No speech recognition backend available")


# =============================================================================
# Convenience Functions
# =============================================================================

_default_stt: Optional[SpeechToText] = None


def get_speech_to_text() -> SpeechToText:
    """Get or create default STT instance."""
    global _default_stt
    if _default_stt is None:
        backend = SpeechToText.get_recommended_backend()
        _default_stt = SpeechToText(backend=backend)
    return _default_stt


def transcribe(
    timeout: float = 5.0,
    backend: Optional[STTBackend] = None
) -> str:
    """
    Quick transcription from microphone.
    
    Usage:
        text = transcribe()
        print(f"You said: {text}")
    """
    if backend:
        stt = SpeechToText(backend=backend)
    else:
        stt = get_speech_to_text()
    
    result = stt.transcribe_microphone(timeout=timeout)
    return result.text


if __name__ == "__main__":
    print("VoxMind Speech-to-Text Service")
    print("=" * 40)
    
    # Show available backends
    print("\n📦 Available backends:")
    for backend, available in SpeechToText.get_available_backends().items():
        status = "✓" if available else "✗"
        print(f"  {status} {backend}")
    
    # Recommend installation
    if not AVAILABLE_BACKENDS.get('faster-whisper'):
        print("\n💡 For best performance, install faster-whisper:")
        print("   pip install faster-whisper")
    
    if not AVAILABLE_BACKENDS.get('vosk'):
        print("\n💡 For lightweight offline STT, install vosk:")
        print("   pip install vosk")
    
    # Demo if any backend available
    recommended = None
    try:
        recommended = SpeechToText.get_recommended_backend()
        print(f"\n🎯 Recommended backend: {recommended.value}")
    except RuntimeError:
        print("\n❌ No STT backend available. Install one of the above.")
    
    if recommended:
        print("\n🎤 Testing microphone transcription...")
        print("   Speak something in the next 5 seconds...")
        
        try:
            stt = SpeechToText(backend=recommended)
            result = stt.transcribe_microphone(timeout=5.0)
            
            if result.text:
                print(f"\n✅ Transcribed: \"{result.text}\"")
                print(f"   Backend: {result.backend}")
                print(f"   Duration: {result.duration:.2f}s")
            else:
                print("\n⚠️ No speech detected")
        except Exception as e:
            print(f"\n❌ Error: {e}")
