"""Simple test runner for the speech recognition service."""
from speech_recognition_service import listen_for_command


def main():
    print("Start test: speak a short phrase after the prompt.")
    try:
        text = listen_for_command(timeout=6, phrase_time_limit=7)
    except Exception as e:
        print(f"Error during listening: {e}")
        return

    if text:
        print("Heard:", text)
    else:
        print("No speech recognized or speech unclear.")


if __name__ == '__main__':
    main()
