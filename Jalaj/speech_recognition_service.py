"""Simple speech recognition helper for VoxMind (Jalaj).

Provides `listen_for_command()` which listens from the default microphone,
adjusts for ambient noise and uses Google Web Speech API via SpeechRecognition.

Note: Do not name this file `speech_recognition.py` (it would shadow the library).
"""
from typing import Optional
import speech_recognition as sr


def listen_for_command(timeout: float = 5.0,
                       phrase_time_limit: Optional[float] = 8.0,
                       adjust_for_ambient: bool = True,
                       ambient_duration: float = 1.0) -> Optional[str]:
    """Listen on the default microphone and return recognized text or None.

    Args:
        timeout: maximum number of seconds to wait for a phrase to start.
        phrase_time_limit: maximum number of seconds for the phrase (None to disable).
        adjust_for_ambient: whether to perform ambient noise adjustment first.
        ambient_duration: duration in seconds for ambient adjustment.

    Returns:
        Recognized text (str) if successful, otherwise None.
    """
    recognizer = sr.Recognizer()

    try:
        with sr.Microphone() as source:
            if adjust_for_ambient:
                recognizer.adjust_for_ambient_noise(source, duration=ambient_duration)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
    except sr.WaitTimeoutError:
        return None
    except OSError as e:
        # Microphone not available or other OS-level error
        raise RuntimeError(f"Microphone error: {e}") from e

    try:
        # Uses Google Web Speech API (requires network)
        text = recognizer.recognize_google(audio)
        return text
    except sr.UnknownValueError:
        # speech was unintelligible
        return None
    except sr.RequestError as e:
        # API was unreachable or unresponsive
        raise RuntimeError(f"Speech recognition service error: {e}") from e


if __name__ == "__main__":
    print("Listening for a single short command. Speak after the prompt...")
    try:
        result = listen_for_command()
    except RuntimeError as e:
        print(f"Error: {e}")
    else:
        if result:
            print("Recognized:", result)
        else:
            print("No speech recognized.")
