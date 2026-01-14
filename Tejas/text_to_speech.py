"""Simple TTS wrapper using pyttsx3 (moved to `Tejas`)."""
from typing import Optional
try:
    import pyttsx3
except Exception:
    pyttsx3 = None


def speak_text(text: str, rate: Optional[int] = None, volume: Optional[float] = None) -> None:
    if pyttsx3 is None:
        # TTS not available; fallback to printing
        print("[TTS unavailable]", text)
        return

    engine = pyttsx3.init()
    if rate is not None:
        engine.setProperty('rate', rate)
    if volume is not None:
        engine.setProperty('volume', max(0.0, min(1.0, volume)))
    engine.say(text)
    engine.runAndWait()
