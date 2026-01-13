"""Enhanced command parser with improved patterns, synonyms, and logging."""
from typing import Dict, Any, Optional
import re
import logging

# Set up logging
logger = logging.getLogger(__name__)

def parse_command(text: str, log_matches: bool = False) -> Dict[str, Any]:
    """Parse command with enhanced pattern matching and optional logging."""
    original_text = text
    t = (text or "").lower().strip()
    
    if not t:
        return {"type": "unknown", "raw": original_text}
    
    # Remove wake words
    wake_words = ["hey vox", "vox", "jarvis", "hey jarvis", "ok jarvis", "assistant"]
    for wake in wake_words:
        if t.startswith(wake + " "):
            t = t[len(wake):].strip()
            break
    
    matched_pattern = None
    
    # Browser commands - expanded patterns
    browser_patterns = [
        r"\b(?:open|launch|start|run)\s+(?:the\s+)?(?:browser|chrome|firefox|edge|safari|opera|brave)",
        r"\b(?:open|launch)\s+(?:google\s+)?chrome",
        r"\bstart\s+browsing",
        r"\bgo\s+online"
    ]
    
    for pattern in browser_patterns:
        if re.search(pattern, t):
            matched_pattern = f"browser: {pattern}"
            if log_matches:
                logger.info(f"Matched browser pattern: {pattern} for input: '{original_text}'")
            return {"type": "open_browser", "raw": original_text, "matched_pattern": matched_pattern}
    
    # Time queries - expanded patterns
    time_patterns = [
        r"\b(?:what(?:'s| is)?\s+(?:the\s+)?time|time\s+now|current\s+time)",
        r"\bwhat\s+time\s+is\s+it",
        r"\btell\s+me\s+the\s+time",
        r"\b(?:what(?:'s| is)?\s+(?:the\s+)?date|today(?:'s)?\s+date)",
        r"\bwhat\s+day\s+is\s+it"
    ]
    
    for pattern in time_patterns:
        if re.search(pattern, t):
            matched_pattern = f"time: {pattern}"
            if log_matches:
                logger.info(f"Matched time pattern: {pattern} for input: '{original_text}'")
            return {"type": "time", "raw": original_text, "matched_pattern": matched_pattern}
    
    # Search queries - enhanced patterns
    search_patterns = [
        r"\b(?:search|google|look\s+up|find)\s+(?:for\s+)?(.+)",
        r"\b(?:lookup|find\s+me)\s+(.+)",
        r"\bwhat\s+is\s+(.+)",
        r"\btell\s+me\s+about\s+(.+)"
    ]
    
    for pattern in search_patterns:
        m = re.search(pattern, t)
        if m:
            query = m.group(1).strip()
            matched_pattern = f"search: {pattern}"
            if log_matches:
                logger.info(f"Matched search pattern: {pattern} for input: '{original_text}', query: '{query}'")
            return {"type": "search", "query": query, "raw": original_text, "matched_pattern": matched_pattern}
    
    # Music/media commands - expanded patterns
    music_patterns = [
        r"\bplay\s+(?:some\s+)?music",
        r"\bstart\s+music",
        r"\bput\s+on\s+(?:some\s+)?music",
        r"\bplay\s+(?:a\s+)?song",
        r"\bplay\s+audio",
        r"\bpause\s+music",
        r"\bstop\s+music",
        r"\bnext\s+(?:song|track)",
        r"\bprevious\s+(?:song|track)",
        r"\bskip\s+(?:song|track)"
    ]
    
    for pattern in music_patterns:
        if re.search(pattern, t):
            matched_pattern = f"music: {pattern}"
            if log_matches:
                logger.info(f"Matched music pattern: {pattern} for input: '{original_text}'")
            return {"type": "play_music", "raw": original_text, "matched_pattern": matched_pattern}
    
    # System commands - expanded patterns
    shutdown_patterns = [
        r"\b(?:shutdown|shut\s+down|power\s+off|turn\s+off)",
        r"\b(?:restart|reboot)",
        r"\b(?:sleep|suspend|hibernate)",
        r"\b(?:lock|lock\s+screen)",
        r"\b(?:quit|exit|close)\s+(?:application|program|system)"
    ]
    
    for pattern in shutdown_patterns:
        if re.search(pattern, t):
            matched_pattern = f"system: {pattern}"
            if log_matches:
                logger.info(f"Matched system pattern: {pattern} for input: '{original_text}'")
            return {"type": "shutdown", "raw": original_text, "matched_pattern": matched_pattern}
    
    # Volume control - new patterns
    volume_patterns = [
        r"\b(?:mute|unmute|silence)",
        r"\bvolume\s+(?:up|down|increase|decrease)",
        r"\b(?:turn\s+)?volume\s+(?:to\s+)?(\d+)",
        r"\b(?:louder|quieter|softer)"
    ]
    
    for pattern in volume_patterns:
        if re.search(pattern, t):
            matched_pattern = f"volume: {pattern}"
            if log_matches:
                logger.info(f"Matched volume pattern: {pattern} for input: '{original_text}'")
            return {"type": "volume", "raw": original_text, "matched_pattern": matched_pattern}
    
    # Application control - new patterns
    app_patterns = [
        r"\b(?:open|launch|start|run)\s+(\w+)",
        r"\b(?:close|quit|exit)\s+(\w+)"
    ]
    
    for pattern in app_patterns:
        m = re.search(pattern, t)
        if m:
            app_name = m.group(1)
            matched_pattern = f"app: {pattern}"
            if log_matches:
                logger.info(f"Matched app pattern: {pattern} for input: '{original_text}', app: '{app_name}'")
            return {"type": "app_control", "app": app_name, "raw": original_text, "matched_pattern": matched_pattern}
    
    # Help/assistant queries - new patterns
    help_patterns = [
        r"\b(?:help|what\s+can\s+you\s+do|capabilities)",
        r"\bwho\s+are\s+you",
        r"\bwhat\s+are\s+you"
    ]
    
    for pattern in help_patterns:
        if re.search(pattern, t):
            matched_pattern = f"help: {pattern}"
            if log_matches:
                logger.info(f"Matched help pattern: {pattern} for input: '{original_text}'")
            return {"type": "help", "raw": original_text, "matched_pattern": matched_pattern}
    
    # Fallback: treat as search if it contains meaningful words
    if len(t.split()) > 0 and not t in ["search", "help", "time"]:
        matched_pattern = "fallback: search"
        if log_matches:
            logger.info(f"Fallback to search for input: '{original_text}'")
        return {"type": "search", "query": t, "raw": original_text, "matched_pattern": matched_pattern}
    
    if log_matches:
        logger.info(f"No pattern matched for input: '{original_text}'")
    return {"type": "unknown", "raw": original_text, "matched_pattern": None}


def get_supported_commands() -> Dict[str, list]:
    """Return a dictionary of supported command types and example phrases."""
    return {
        "open_browser": ["open browser", "launch chrome", "start firefox", "go online"],
        "time": ["what time is it", "current time", "what's the date", "tell me the time"],
        "search": ["search for python", "google machine learning", "what is AI", "find restaurants"],
        "play_music": ["play music", "start music", "play a song", "next track", "pause music"],
        "shutdown": ["shutdown", "restart", "sleep", "lock screen", "power off"],
        "volume": ["mute", "volume up", "turn volume to 50", "louder", "quieter"],
        "app_control": ["open notepad", "launch vscode", "close chrome", "start calculator"],
        "help": ["help", "what can you do", "who are you", "capabilities"]
    }