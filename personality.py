"""VoxMind Personality Module - intelligent conversational responses."""
import random
from datetime import datetime

# Import config for user name
try:
    from config import get_user_name
except ImportError:
    get_user_name = lambda: "sir"

def get_name():
    """Get the user's name, with fallback."""
    name = get_user_name()
    return name if name else "sir"

class VoxPersonality:
    """VoxMind personality for VoxMind."""
    
    # Greeting variations based on time of day
    @classmethod
    def _greetings(cls):
        name = get_name()
        return {
            'morning': [
                f"Good morning, {name}. All systems are online and ready.",
                f"Good morning, {name}. How may I assist you today?",
                f"Rise and shine, {name}. VoxMind at your service.",
            ],
            'afternoon': [
                f"Good afternoon, {name}. Ready when you are.",
                f"Good afternoon, {name}. How can I help?",
                f"Afternoon, {name}. All systems operational.",
            ],
            'evening': [
                f"Good evening, {name}. At your service.",
                f"Good evening, {name}. How may I be of assistance?",
                f"Evening, {name}. What can I do for you?",
            ],
            'night': [
                f"Working late, {name}? I'm here to help.",
                f"At your service, {name}. Even at this hour.",
                f"Hello, {name}. Ready to assist.",
            ]
        }
    
    @classmethod
    def _startup_phrases(cls):
        name = get_name()
        return [
            f"VoxMind online. Good to see you, {name}.",
            f"All systems initialized. Ready to assist, {name}.",
            f"VoxMind is now active. At your command, {name}.",
            f"Powering up complete. How can I help you, {name}?",
        ]
    
    @classmethod
    def _shutdown_phrases(cls):
        name = get_name()
        return [
            f"Goodbye, {name}. VoxMind signing off.",
            f"Until next time, {name}. Shutting down.",
            f"It was a pleasure, {name}. Going offline.",
            f"Take care, {name}. VoxMind out.",
        ]
    
    # Error/failure phrases
    ERROR_PHRASES = [
        "I'm afraid I couldn't complete that request.",
        "My apologies, I encountered an issue.",
        "Something went wrong. Shall I try again?",
        "I wasn't able to do that. Perhaps try rephrasing?",
    ]
    
    # Listening/waiting phrases
    LISTENING_PHRASES = [
        "I'm listening.",
        "Go ahead.",
        "Yes?",
        "What do you need?",
        "At your command.",
    ]
    
    # Not understood phrases
    NOT_UNDERSTOOD = [
        "I didn't quite catch that. Could you repeat?",
        "I'm not sure I understood. Try again?",
        "Could you rephrase that for me?",
        "I didn't understand that command.",
    ]
    
    # Contextual response templates
    RESPONSE_TEMPLATES = {
        'open_browser': [
            "Opening your browser now.",
            "Launching the browser for you.",
            "Browser coming right up.",
        ],
        'search': [
            "Searching for {query}. One moment.",
            "Let me look that up for you. Searching {query}.",
            "Pulling up results for {query}.",
        ],
        'time': [
            "The time is {time}. It's {date}.",
            "It's currently {time}, {date}.",
            "Right now it's {time} on {date}.",
        ],
        'volume_up': [
            "Turning it up.",
            "Increasing volume.",
            "Louder, as requested.",
        ],
        'volume_down': [
            "Turning it down.",
            "Lowering the volume.",
            "Making it quieter.",
        ],
        'volume_mute': [
            "Muting audio.",
            "Silencing the system.",
            "Audio muted.",
        ],
        'volume_unmute': [
            "Unmuting audio.",
            "Restoring sound.",
            "Audio restored.",
        ],
        'brightness_up': [
            "Brightening the display.",
            "Increasing brightness.",
            "Making it brighter.",
        ],
        'brightness_down': [
            "Dimming the display.",
            "Reducing brightness.",
            "Making it easier on the eyes.",
        ],
        'app_open': [
            "Launching {app} for you.",
            "Opening {app} now.",
            "Starting {app}.",
            "{app} coming right up.",
        ],
        'app_close': [
            "Closing {app}.",
            "Shutting down {app}.",
            "Terminating {app}.",
        ],
        'window_minimize': [
            "Minimizing {window}.",
            "Putting {window} out of the way.",
            "{window} minimized.",
        ],
        'window_maximize': [
            "Maximizing {window}.",
            "Expanding {window} to full screen.",
            "{window} maximized.",
        ],
        'system_sleep': [
            "Putting the system to sleep. Rest well.",
            "Entering sleep mode. Goodnight.",
            "System going to sleep.",
        ],
        'system_lock': [
            "Locking the screen. Stay secure.",
            "Screen locked.",
            "Locking your workstation.",
        ],
        'help': [
            "Of course. Here's what I can do for you.",
            "Certainly. Let me explain my capabilities.",
            "I'd be happy to help. Here are my functions.",
        ],
    }
    
    # Status updates for longer operations
    STATUS_UPDATES = {
        'loading': [
            "Working on it...",
            "Just a moment...",
            "Processing...",
        ],
        'searching': [
            "Searching the web...",
            "Looking that up...",
            "Finding information...",
        ],
        'executing': [
            "Executing command...",
            "Running the operation...",
            "On it...",
        ],
    }
    
    @staticmethod
    def get_time_of_day():
        """Get current time of day category."""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 17:
            return 'afternoon'
        elif 17 <= hour < 21:
            return 'evening'
        else:
            return 'night'
    
    @classmethod
    def get_greeting(cls):
        """Get a time-appropriate greeting."""
        time_of_day = cls.get_time_of_day()
        return random.choice(cls._greetings()[time_of_day])
    
    @classmethod
    def get_startup_message(cls):
        """Get a startup message."""
        return random.choice(cls._startup_phrases())
    
    @classmethod
    def get_shutdown_message(cls):
        """Get a shutdown message."""
        return random.choice(cls._shutdown_phrases())
    
    # Acknowledgments before executing commands
    ACKNOWLEDGMENTS = [
        "Right away.",
        "On it.",
        "Consider it done.",
        "Executing now.",
        "Of course.",
        "Certainly.",
        "As you wish.",
        "Processing your request.",
        "One moment.",
        "Understood.",
    ]
    
    # Quick acknowledgments for fast commands
    QUICK_ACKS = [
        "Done.",
        "There you go.",
        "All set.",
        "Complete.",
    ]
    
    @classmethod
    def get_acknowledgment(cls, quick=False):
        """Get an acknowledgment phrase."""
        if quick:
            return random.choice(cls.QUICK_ACKS)
        return random.choice(cls.ACKNOWLEDGMENTS)
    
    @classmethod
    def get_error_message(cls, error=None):
        """Get an error message."""
        base = random.choice(cls.ERROR_PHRASES)
        if error:
            return f"{base} Error: {error}"
        return base
    
    @classmethod
    def get_listening_message(cls):
        """Get a listening prompt."""
        return random.choice(cls.LISTENING_PHRASES)
    
    @classmethod
    def get_not_understood(cls):
        """Get a not understood message."""
        return random.choice(cls.NOT_UNDERSTOOD)
    
    @classmethod
    def get_response(cls, action: str, **kwargs) -> str:
        """Get a contextual response for an action."""
        templates = cls.RESPONSE_TEMPLATES.get(action)
        if templates:
            template = random.choice(templates)
            try:
                return template.format(**kwargs)
            except KeyError:
                return template
        return cls.get_acknowledgment(quick=True)
    
    @classmethod
    def get_status(cls, status_type: str) -> str:
        """Get a status update message."""
        updates = cls.STATUS_UPDATES.get(status_type, cls.STATUS_UPDATES['executing'])
        return random.choice(updates)


# Convenience functions
def greet():
    return VoxPersonality.get_greeting()

def startup():
    return VoxPersonality.get_startup_message()

def shutdown():
    return VoxPersonality.get_shutdown_message()

def ack(quick=False):
    return VoxPersonality.get_acknowledgment(quick)

def error(e=None):
    return VoxPersonality.get_error_message(e)

def listening():
    return VoxPersonality.get_listening_message()

def not_understood():
    return VoxPersonality.get_not_understood()

def respond(action, **kwargs):
    return VoxPersonality.get_response(action, **kwargs)

def status(status_type):
    return VoxPersonality.get_status(status_type)
