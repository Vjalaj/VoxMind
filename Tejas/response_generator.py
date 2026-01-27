"""Generate textual responses for parsed commands (moved to `Tejas`)."""
from datetime import datetime
from typing import Dict, Any


def generate_response(parsed: Dict[str, Any]) -> str:
    ctype = parsed.get("type")

    if ctype == "open_browser":
        return "Opening the browser for you."
    if ctype == "time":
        now = datetime.now()
        return f"The time is {now.strftime('%I:%M %p')}."
    if ctype == "search":
        q = parsed.get("query", "")
        return f"Searching for {q}." if q else "What should I search for?"
    if ctype == "play_music":
        return "Playing music." 
    if ctype == "shutdown":
        return "Shutting down. Goodbye."

    return "Sorry, I didn't understand that. Can you rephrase?"
