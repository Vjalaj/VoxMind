"""Simple wake-word detector with microphone and keyboard fallback (moved to `yash`)."""
from typing import Optional
import speech_recognition as sr


def listen_for_wake_word(wake_word: str = "hey vox",
                         timeout: float = 3.0,
                         phrase_time_limit: float = 3.0,
                         use_keyboard_fallback: bool = True) -> bool:
    """Listen briefly and return True if the wake_word is detected.

    Falls back to a keyboard prompt when microphone access fails.
    """
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 4000
    recognizer.dynamic_energy_threshold = True

    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            except sr.WaitTimeoutError:
                return False
    except OSError as e:
        if use_keyboard_fallback:
            print(f"Microphone error: {e}")
            input("Press Enter to simulate wake word 'hey vox'...")
            return True
        return False

    try:
        text = recognizer.recognize_google(audio).lower()
        print(f"Heard: '{text}'")
        # Check for wake word variations
        wake_variations = ["hey vox", "vox", "hey box", "a vox"]
        if any(wake in text for wake in wake_variations):
            return True
    except sr.UnknownValueError:
        return False
    except sr.RequestError as e:
        print(f"Recognition error: {e}")
        return False

    return False
