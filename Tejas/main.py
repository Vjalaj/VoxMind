"""Integration entry point for VoxMind voice pipeline (placed in `Tejas/`).

Run with `--simulate` to use keyboard/text I/O instead of microphone for quick tests.
"""
import argparse
import sys
import os
from time import sleep

# Ensure project root is on sys.path so sibling packages (e.g. Jalaj) import correctly
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from Jalaj.speech_recognition_service import listen_for_command
from Tejas.wake_word_detector import listen_for_wake_word
from Tejas.command_parser import parse_command
from Tejas.response_generator import generate_response
from Tejas.text_to_speech import speak_text


def run_loop(simulate: bool = False, no_tts: bool = False):
    print("VoxMind integration starting. Press Ctrl-C to exit.")

    try:
        while True:
            if simulate:
                input("Press Enter to simulate wake word...")
                cmd_text = input("Type the spoken command (simulate): ").strip()
            else:
                print("Listening for wake word...")
                heard = listen_for_wake_word()
                if not heard:
                    # not detected; continue listening
                    continue
                print("Wake word detected — listening for command...")
                cmd_text = listen_for_command()

            if not cmd_text:
                print("No command recognized.")
                continue

            print("Heard:", cmd_text)
            parsed = parse_command(cmd_text)
            response = generate_response(parsed)
            print("Response:", response)

            if not no_tts:
                speak_text(response)

            if parsed.get('type') == 'shutdown':
                print('Shutdown command received — exiting.')
                break

            # small pause before next cycle
            sleep(0.5)

    except KeyboardInterrupt:
        print('\nInterrupted — exiting.')


def main(argv=None):
    parser = argparse.ArgumentParser(description='VoxMind integration runner')
    parser.add_argument('--simulate', action='store_true', help='Use keyboard I/O instead of microphone')
    parser.add_argument('--no-tts', action='store_true', help='Do not run TTS (print responses)')
    args = parser.parse_args(argv)
    run_loop(simulate=args.simulate, no_tts=args.no_tts)


if __name__ == '__main__':
    main()
