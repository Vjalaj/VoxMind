import random

TEMPLATES = {
    "greet": {
        "friendly": [
            "Hey {name}! How can I help you today?",
            "Hi {name}! Nice to see you 😊",
            "Hello {name}! What can I do for you?",
            "Hey there {name}! Ready to begin?",
            "Hi {name}! Let’s get started."
        ],
        "professional": [
            "Hello {name}. How may I assist you?",
            "Good day {name}. Please share your request.",
            "Greetings {name}. How can I help?",
            "Welcome {name}. Let me know your requirement.",
            "Hello {name}. I am ready to assist."
        ],
        "humorous": [
            "Hey {name}! I’m awake and ready 😄",
            "Hi {name}! Let’s make things happen!",
            "Hello {name}! What’s today’s mission?",
            "Hey {name}! Coffee loaded ☕",
            "Hi {name}! Hit me with your question."
        ]
    },

    "error": {
        "neutral": [
            "Something went wrong. Please try again.",
            "Oops! That didn’t work.",
            "I couldn’t understand that request.",
            "An unexpected error occurred.",
            "Please check your input and retry."
        ]
    },

    "confirm": {
        "neutral": [
            "Are you sure you want to {action}?",
            "Please confirm before I proceed.",
            "This action is irreversible. Continue?",
            "Do you want me to go ahead?",
            "Kindly confirm to continue."
        ]
    },

    "onboarding": {
        "friendly": [
            "Welcome {name}! I’ll help you step by step.",
            "Hey {name}! Let’s get you started 🚀",
            "Glad you’re here {name}! Ask me anything.",
            "Welcome aboard {name}! I’m here to help.",
            "Hi {name}! Let’s begin your journey."
        ]
    }
}

def render(command, tone="friendly", **data):
    tones = TEMPLATES.get(command, {})
    responses = tones.get(tone) or tones.get("neutral", [])
    return random.choice(responses).format(**data)
