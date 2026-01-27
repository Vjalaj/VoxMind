def simple_response_system(user_input):
    user_input = user_input.lower().strip()

    if user_input in ["hi", "hello", "hey"]:
        return "Hello! How can I help you today?"

    elif user_input in ["how are you", "how are you doing"]:
        return "I'm doing great! Thanks for asking."

    elif user_input in ["what is your name", "who are you"]:
        return "I am a simple response system created by Swadhin."

    elif user_input in ["bye", "exit", "quit"]:
        return "Goodbye! Have a great day."

    else:
        return "Sorry, I didn't understand that. Please try again."


# Example usage
while True:
    user_text = input("You: ")
    response = simple_response_system(user_text)
    print("Bot:", response)

    if user_text.lower() in ["bye", "exit", "quit"]:
        break
