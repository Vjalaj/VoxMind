# main.py

from voice.recorder import listen
from voice.tts import speak
from utils.assistant_utils import process_command
from config.settings import STOP_COMMANDS
from database.db import init_db, save_conversation, get_last_conversation


def main():
    init_db()  # ✅ create table if not exists

    speak("Vox assistant started. How can I help you?")

    while True:
        command = listen()

        if not command:
            continue

        print(f"Command Received: {command}")

        # ✅ STOP
        if any(stop in command.lower() for stop in STOP_COMMANDS):
            speak("Stopping assistant. Goodbye.")
            break

        # ✅ FETCH OLD CONVERSATION
        if "old conversation" in command:
            last = get_last_conversation()

            if last:
                user_cmd, assistant_reply = last

                response = (
                    "Hello. "
                    f"You told me: {user_cmd}. "
                    f"And I replied: {assistant_reply}."
                )

                speak(response)
                speak("Task Complete")
            else:
                speak("No previous conversation found.")
                speak("Task Complete")

            continue

        # ✅ NORMAL COMMAND PROCESSING
        response = process_command(command)

        speak(response)
        speak("Task Complete")

        # ✅ SAVE TO DATABASE
        save_conversation(command, response)


if __name__ == "__main__":
    main()
