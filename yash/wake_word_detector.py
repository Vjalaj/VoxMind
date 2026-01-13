"""Simple wake-word detector with microphone and keyboard fallback (moved to `yash`)."""
from typing import Optional
import speech_recognition as sr


def listen_for_wake_word(wake_word: str = "hey voxmind",
                         timeout: float = 5.0,
                         phrase_time_limit: float = 4.0,
                         use_keyboard_fallback: bool = True) -> bool:
    """Listen briefly and return True if the wake_word is detected.

    Falls back to a keyboard prompt when microphone access fails.
    """
    recognizer = sr.Recognizer()

    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.8)
            try:
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            except sr.WaitTimeoutError:
                return False
    except OSError:
        if use_keyboard_fallback:
            input("Microphone unavailable — press Enter to simulate wake word...")
            return True
        return False

    try:
        text = recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return False
    except sr.RequestError:
        # network/service issue; signal False so caller can retry or fallback
        return False

    return wake_word.lower() in text.lower()
