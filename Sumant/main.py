#imported important libraries
import pyttsx3 # text-to-speech conversion lib (output)
import speech_recognition as sr # speech to text-recognition lib (input)
import time
import webbrowser # for web browsing
import os
import sys

# Add current directory to path so we can import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from advanced_command_parser import AdvancedCommandParser

# Initialize components
recognizer = sr.Recognizer()
engine = pyttsx3.init()
parser = AdvancedCommandParser()  # Week 2: Integrated Advanced Parser

# converting text to speech
def speak(text):
    print(f"Jarvis: {text}")
    engine.say(text)
    engine.runAndWait()

def execute_action(result):
    """Execute a single parsed command action"""
    cmd_type = result.get('type')
    confidence = result.get('confidence', 1.0)
    
    # Check confidence threshold for NLP commands
    if result.get('source') == 'nlp' and confidence < 0.6:
        speak("I'm not sure what you mean.")
        return

    if cmd_type == 'browser':
        speak("Opening browser...")
        webbrowser.open("https://www.google.com")
        
    elif cmd_type == 'search':
        query = result.get('query', '')
        if query:
            speak(f"Searching for {query}")
            webbrowser.open(f"https://www.google.com/search?q={query}")
        else:
            speak("What should I search for?")
            
    elif cmd_type == 'volume':
        action = result.get('action')
        value = result.get('value')
        if action == 'set':
            speak(f"Setting volume to {value} percent")
            # Logic to set system volume would go here
        elif action == 'up':
            speak("Increasing volume")
        elif action == 'down':
            speak("Decreasing volume")
        elif action == 'mute':
            speak("Muting audio")
            
    elif cmd_type == 'app_control':
        app_name = result.get('app_name', 'application')
        speak(f"Opening {app_name}")
        # Logic to open app would go here (os.system or subprocess)
        
    elif cmd_type == 'system':
        speak(f"Executing system command: {result.get('raw', 'unknown')}")
        
    elif cmd_type == 'media':
        speak(f"Media control: {result.get('raw', 'unknown')}")
        
    elif cmd_type == 'utility':
        speak("Running utility function")
        
    else:
        speak("I didn't understand that command yet.")

def proceed_command(command):
    if not command:
        return
        
    print(f"Processing: {command}")
    
    # Week 2: Use Advanced Parser
    results = parser.parse(command)
    
    if not results:
        speak("Sorry, I couldn't parse that command.")
        return

    # Handle Compound Commands
    for result in results:
        execute_action(result)


if __name__ == "__main__":
    speak("Initializing Jarvis (Week 2 Enhanced Mode)....")

    while True:
        print("Waiting for wake word...")
        try:
            #Capture initial audio to check for activation keyword
            with sr.Microphone() as source:
                # Adjust for ambient noise for better accuracy
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                print("Listening for 'Jarvis'...")
                try:
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                    word = recognizer.recognize_google(audio)
                    print(f"You said: {word}")
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    continue
            
            # if jarvis is detected , activate and listen for command
            if 'jarvis' in word.lower():
                speak("Yes, I'm listening.")
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    print("Listening for command...")
                    try:
                        audio = recognizer.listen(source, timeout=8, phrase_time_limit=8)
                        command = recognizer.recognize_google(audio)
                        proceed_command(command)
                    except sr.UnknownValueError:
                        speak("Sorry, I didn't catch that.")
                    except sr.WaitTimeoutError:
                        speak("Listening timed out.")

        except Exception as e:
            print(f"Error: {e}")
            # time.sleep(1) # Prevent rapid looping on error