#imported important libraries
import pyttsx3 # text-to-speech conversion lib (output)
import speech_recognition as sr # speech to text-recognition lib (input)
import time
import webbrowser # for web browsing

# Initialize components
recognizer = sr.Recognizer()
engine = pyttsx3.init()

# converting text to speech
def speak(text):
    engine.say(text)
    engine.runAndWait()

def proceed_command(command):
    if "open google" in command.lower():
        speak("opening google...")
        webbrowser.open("https://www.google.com")


if __name__ == "__main__":
    speak("Initializing Jarvis....")

    while True:
        print("Recongizing...")
        try:
            #Capture initial audio to check for activation keyword
            with sr.Microphone() as source:
                print("Listening...")
                audio = recognizer.listen(source, timeout=4, phrase_time_limit= 4)
            word = recognizer.recognize_google(audio)
            print(f"You said:{word}")
            # if jarvis is detected , activate and listen for command
            if word.lower() == 'jarvis':
                speak("yes sir, what i can do for you?")
                # time.sleep(1)
                with sr.Microphone() as source:
                    print("jarvis activated...")
                    audio = recognizer.listen(source)
                    command = recognizer.recognize_google(audio)
                proceed_command(command)

        except Exception as e:
            print(f"Error: {e}")