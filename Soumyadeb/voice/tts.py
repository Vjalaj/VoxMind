# voice/tts.py

import pyttsx3

def speak(text):
    engine = pyttsx3.init()

    engine.setProperty("rate", 170)
    engine.setProperty("volume", 1)

    voices = engine.getProperty('voices')
    engine.setProperty('voice', voices[0].id)

    print(f"Assistant: {text}")
    engine.say(text)
    engine.runAndWait()
    engine.stop()
