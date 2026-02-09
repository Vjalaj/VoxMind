"""Simple wake-word detector with microphone and keyboard fallback (moved to `Tejas`)."""
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
    recognizer.energy_threshold = 3000  # Lower threshold for better detection
    recognizer.dynamic_energy_threshold = True

    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
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
        
        # Check for wake word variations (common misrecognitions)
        wake_variations = [
            "hey vox", "vox", "hey box", "a vox", "evox",
            "hey vax", "vax", "hey fox", "fox", "hey rocks",
            "hey walks", "hey docs", "hey talks", "hey bucks",
            "he vox", "the vox", "ok vox", "yo vox",
            "hey voice", "hey boss", "hey box",
            "hey wax", "hey locks", "hey socks",
            "hey vox mind", "voxmind", "vox mind"
        ]
        
        # Check exact matches
        if any(wake in text for wake in wake_variations):
            return True
        
        # Check for partial matches (words that sound like "vox")
        words = text.split()
        vox_sounds = ["vox", "box", "fox", "vax", "wax", "rocks", "docs", "locks", "socks", "bucks", "voice", "boss"]
        for word in words:
            if word in vox_sounds:
                return True
            # Fuzzy check - if word starts with 'v' or 'b' and ends with 'x' or 'ks'
            if len(word) >= 2 and word[0] in 'vbf' and (word.endswith('x') or word.endswith('ks') or word.endswith('s')):
                return True
                
    except sr.UnknownValueError:
        return False
    except sr.RequestError as e:
        print(f"Recognition error: {e}")
        return False

    return False
