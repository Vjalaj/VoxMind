import speech_recognition as sr
import pyttsx3

r = sr.Recognizer()
engine = pyttsx3.init()

with sr.Microphone() as source:
    print("Calibrating for ambient noise...")
    r.adjust_for_ambient_noise(source, duration=0.5)
    print("Speak now...")
    try:
        audio = r.listen(source, timeout=5, phrase_time_limit=8)
    except sr.WaitTimeoutError:
        print("No speech detected within timeout.")
        engine.say("I did not hear anything.")
        engine.runAndWait()
        audio = None

if audio is not None:
    try:
        text = r.recognize_google(audio)
        print("You said:", text)
        engine.say(f"You said {text}")
        engine.runAndWait()
    except sr.UnknownValueError:
        print("Sorry, could not understand audio.")
        engine.say("Sorry, I could not understand.")
        engine.runAndWait()
    except sr.RequestError as e:
        print("Request error:", e)
        engine.say("There was a problem contacting the speech service.")
        engine.runAndWait()
    except Exception as e:
        print("Error:", e)
        engine.say("An unexpected error occurred.")
        engine.runAndWait()
