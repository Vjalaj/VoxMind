"""Basic command parser using keyword matching (moved to `yash`)."""
from typing import Dict, Any
import re


def parse_command(text: str) -> Dict[str, Any]:
    t = (text or "").lower().strip()
    if not t:
        return {"type": "unknown", "raw": text}
    # open browser / specific browsers
    if ("open" in t and ("browser" in t or "chrome" in t or "edge" in t or "firefox" in t)) \
       or ("launch" in t and ("browser" in t or "chrome" in t)):
        return {"type": "open_browser", "raw": text}

    # time queries
    if "time" in t or "what time" in t or "what's the time" in t:
        return {"type": "time", "raw": text}

    # search queries: allow "search for X" or "search X"
    m = re.search(r"search(?: for)? (.+)", t)
    if m:
        query = m.group(1).strip()
        return {"type": "search", "query": query, "raw": text}

    # If user just says "search" without query
    if t == "search":
        return {"type": "search", "query": "", "raw": text}

    if "play music" in t or "play some music" in t:
        return {"type": "play_music", "raw": text}

    if "shutdown" in t or "quit" in t or "exit" in t:
        return {"type": "shutdown", "raw": text}

    return {"type": "unknown", "raw": text}
