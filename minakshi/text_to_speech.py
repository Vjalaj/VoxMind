import pyttsx3

test_text = "Hello User, Welcome to voxmind. This is a sample voice"

def list_voices():
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')

    print(f"Total voices available: {len(voices)}")
    for i, v in enumerate(voices):
        print(f"{i}: {v.name}")

def speak(text, voice_index, rate = 180, volume = 0.8):
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')

    if voice_index < 0 or voice_index >= len(voices):
        raise ValueError("Voice index out of range")

    engine.setProperty('voice', voices[voice_index].id)
    engine.setProperty('rate', rate)
    engine.setProperty('volume', volume)

    engine.say(text)
    engine.runAndWait()

def demo():
    list_voices()
    while True:
        choice = input("\nEnter voice index to test \n(Type 'q' to quit)").strip()
        if choice.lower() == "q":
            print("Quitting...")
            return
        try :
            idx = int(choice)
            speak(test_text, idx)
        except Exception as e:
            print(f"Error: {e}")
            continue
        again = input("\nWant to try next voice? (y/n)").lower()
        if again != "y":
            print("Exiting Demo...")
            return

if __name__ == "__main__":
    demo()



