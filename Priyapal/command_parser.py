"""
command_parser.py

Text-only command parser for a VoxMind assistant.

Responsibilities
----------------
- Take raw text from ASR or typed input (already handled elsewhere).
- Normalize it.
- Map it to a high-level command (intent) and structured parameters.
- Stay OS-agnostic and IO-free: NO audio, NO TTS, NO system calls.

Public API
----------
- parse_command(text: str) -> dict
    Returns a dict with keys:
      - 'command': a string identifier
      - 'params': a dict with extracted parameters

Example intents
---------------
- open_browser: "open the browser", "launch chrome"
- search: "search for python", "google nearest cafe"
- get_time: "what time is it", "what's the date today"
- system_power: "shut down", "restart", "sleep", "lock screen"
- control_volume: "mute", "set volume to 50 percent", "volume up"
- control_app: "open vscode", "close spotify"
- open_path: "open downloads folder", "open file report.docx"
- assistant_help: "what can you do", "who are you"
- navigate: "go back", "go home", "show notifications", "show recent apps"
- media_control: "play", "pause", "next song", "previous track"
- scroll: "scroll down", "scroll up", "scroll to top", "scroll to bottom"

Wake word
---------
- If text starts with "voxmind", "hey voxmind", or "ok voxmind", that prefix
  is stripped before parsing.
- The caller (main.py, wake-word detector, etc.) should decide when to call
  parse_command; this file only handles text → {command, params}.
"""

from __future__ import annotations

import re
from typing import Dict, Any, Callable, Match, List, Tuple

ParamsFn = Callable[[Match[str]], Dict[str, Any]]


# -------------------- Param extractors --------------------


def _noop_params(_: Match[str]) -> Dict[str, Any]:
    return {}


def _browser_params(match: Match[str]) -> Dict[str, Any]:
    browser = match.groupdict().get("browser")
    if not browser:
        return {"browser": None}
    browser = browser.strip().lower()
    if browser in ("google", "google chrome", "chrome browser"):
        browser = "chrome"
    elif browser in ("mozilla", "mozilla firefox", "ff"):
        browser = "firefox"
    elif browser in ("msedge", "microsoft edge", "edge browser"):
        browser = "edge"
    elif browser == "brave browser":
        browser = "brave"
    elif browser == "opera browser":
        browser = "opera"
    return {"browser": browser}


def _search_params(match: Match[str]) -> Dict[str, Any]:
    q = match.groupdict().get("query") or ""
    q = q.strip()
    q = re.sub(r"^(for|about|on)\s+", "", q, flags=re.I)
    q = re.sub(r"\bplease\b\.?$", "", q, flags=re.I).strip()
    return {"query": q}


def _system_power_params(match: Match[str]) -> Dict[str, Any]:
    groups = match.groupdict()
    if groups.get("shutdown"):
        return {"mode": "shutdown"}
    if groups.get("restart"):
        return {"mode": "restart"}
    if groups.get("sleep"):
        return {"mode": "sleep"}
    if groups.get("lock"):
        return {"mode": "lock"}
    return {"mode": None}


def _volume_params(match: Match[str]) -> Dict[str, Any]:
    text = match.group(0).lower()
    if "unmute" in text:
        return {"action": "unmute", "level": None}
    if "mute" in text:
        return {"action": "mute", "level": None}
    if any(k in text for k in ("up", "increase", "raise", "louder")):
        return {"action": "up", "level": None}
    if any(k in text for k in ("down", "decrease", "lower", "softer")):
        return {"action": "down", "level": None}
    m = re.search(r"(\d{1,3})", text)
    if m:
        try:
            level = int(m.group(1))
        except Exception:
            level = None
        if level is not None:
            level = max(0, min(100, level))
        return {"action": "set", "level": level}
    if "set" in text:
        return {"action": "set", "level": None}
    return {"action": None, "level": None}


def _app_params(match: Match[str]) -> Dict[str, Any]:
    app = (match.groupdict().get("app") or "").strip().strip(' "\'')
    action = (match.groupdict().get("app_action") or "").strip().lower()
    if action in ("open", "start", "launch", "run"):
        action = "open"
    elif action in ("close", "quit", "exit", "stop"):
        action = "close"
    else:
        action = None
    return {"app": app or None, "action": action}


def _file_params(match: Match[str]) -> Dict[str, Any]:
    target = (match.groupdict().get("target") or "").strip().strip(' "\'')
    return {"target": target or None}


def _help_params(_: Match[str]) -> Dict[str, Any]:
    return {}


def _navigate_params(match: Match[str]) -> Dict[str, Any]:
    """
    Map navigation phrases to actions:
    - back
    - home
    - notifications
    - recents
    """
    text = match.group(0).lower()

    if "back" in text:
        return {"action": "back"}
    if "home" in text:
        return {"action": "home"}
    if "notification" in text:
        return {"action": "notifications"}
    if "recent" in text:
        return {"action": "recents"}

    return {"action": None}


def _media_params(match: Match[str]) -> Dict[str, Any]:
    """
    Map media phrases to actions:
    - play / pause / stop / next / previous
    """
    text = match.group(0).lower()

    if "play" in text and "pause" not in text:
        return {"action": "play"}
    if "pause" in text:
        return {"action": "pause"}
    if "stop" in text:
        return {"action": "stop"}
    if any(k in text for k in ("next", "skip")):
        return {"action": "next"}
    if any(k in text for k in ("previous", "prev", "back")):
        return {"action": "previous"}

    return {"action": None}


def _scroll_params(match: Match[str]) -> Dict[str, Any]:
    """
    Map scroll phrases to direction:
    - up / down / top / bottom
    """
    text = match.group(0).lower()

    if "to top" in text or "top" in text:
        return {"direction": "top"}
    if "to bottom" in text or "bottom" in text:
        return {"direction": "bottom"}
    if "up" in text:
        return {"direction": "up"}
    if "down" in text:
        return {"direction": "down"}

    return {"direction": None}


def _brightness_params(match: Match[str]) -> Dict[str, Any]:
    """
    Map brightness phrases to actions:
    - up / down / set with level
    """
    text = match.group(0).lower()
    
    # Check for explicit level first
    m = re.search(r"(\d{1,3})", text)
    if m:
        try:
            level = int(m.group(1))
            level = max(0, min(100, level))
            return {"action": "set", "level": level}
        except Exception:
            pass
    
    # Check for max/min
    if "max" in text or "full" in text:
        return {"action": "set", "level": 100}
    if "min" in text:
        return {"action": "set", "level": 0}
    
    # Check for directional commands
    if any(k in text for k in ("up", "increase", "raise", "higher", "brighter")):
        return {"action": "up", "level": None}
    if any(k in text for k in ("down", "decrease", "lower", "dimmer", "dim")):
        return {"action": "down", "level": None}
    
    if "set" in text:
        return {"action": "set", "level": None}
    
    return {"action": None, "level": None}


def _input_control_params(match: Match[str]) -> Dict[str, Any]:
    """
    Extract input control (mouse/keyboard) command parameters.
    Inspired by Microsoft Voice Access and Google Voice Access.
    """
    text = match.group(0).lower()
    
    # Click commands
    if "triple click" in text or "click three" in text:
        return {"type": "mouse_click", "button": "left", "clicks": 3}
    if "double click" in text or "click twice" in text:
        return {"type": "mouse_click", "button": "left", "clicks": 2}
    if "right click" in text or "secondary click" in text:
        return {"type": "mouse_click", "button": "right", "clicks": 1}
    if "middle click" in text:
        return {"type": "mouse_click", "button": "middle", "clicks": 1}
    if re.search(r"\bclick\b", text) and not re.search(r"\bclick\s+\d+", text):
        return {"type": "mouse_click", "button": "left", "clicks": 1}
    
    # Grid click
    grid_match = re.search(r"\bclick\s+(\d{1,2})\b", text)
    if grid_match:
        return {"type": "grid_click", "cell": int(grid_match.group(1))}
    
    # Mouse grid
    if "mouse grid" in text or "show grid" in text:
        return {"type": "mouse_grid", "action": "show"}
    if "close grid" in text or "hide grid" in text:
        return {"type": "mouse_grid", "action": "hide"}
    
    # Mouse move directional
    dir_match = re.search(
        r"move\s+(?:mouse\s+)?(?:cursor\s+)?(up|down|left|right)"
        r"(?:\s+(\d+))?", text
    )
    if dir_match:
        return {
            "type": "mouse_move",
            "direction": dir_match.group(1),
            "distance": int(dir_match.group(2)) if dir_match.group(2) else None
        }
    
    # Mouse move to coordinates
    coord_match = re.search(r"move\s+(?:mouse\s+)?(?:to\s+)?(\d+)\s*,?\s*(\d+)", text)
    if coord_match:
        return {
            "type": "mouse_move",
            "x": int(coord_match.group(1)),
            "y": int(coord_match.group(2))
        }
    
    # Type text
    type_match = re.search(r"type\s+(.+)", text)
    if type_match:
        return {"type": "type_text", "text": type_match.group(1)}
    
    # Press key with modifiers
    hotkey_match = re.search(
        r"press\s+(control|ctrl|alt|shift|win)\s+(\w+)", text
    )
    if hotkey_match:
        modifier = hotkey_match.group(1)
        if modifier == "control":
            modifier = "ctrl"
        return {"type": "hotkey", "modifiers": [modifier], "key": hotkey_match.group(2)}
    
    # Press single key
    key_match = re.search(r"press\s+(\w+)", text)
    if key_match:
        return {"type": "press_key", "key": key_match.group(1)}
    
    # Common keyboard actions
    if re.search(r"\bcopy\b", text):
        return {"type": "hotkey", "modifiers": ["ctrl"], "key": "c"}
    if re.search(r"\bpaste\b", text):
        return {"type": "hotkey", "modifiers": ["ctrl"], "key": "v"}
    if re.search(r"\bcut\b", text):
        return {"type": "hotkey", "modifiers": ["ctrl"], "key": "x"}
    if re.search(r"\bundo\b", text):
        return {"type": "hotkey", "modifiers": ["ctrl"], "key": "z"}
    if re.search(r"\bredo\b", text):
        return {"type": "hotkey", "modifiers": ["ctrl"], "key": "y"}
    if re.search(r"\bselect all\b", text):
        return {"type": "hotkey", "modifiers": ["ctrl"], "key": "a"}
    
    # Screenshot
    if "screenshot" in text:
        return {"type": "window", "action": "screenshot"}
    
    # Switch window
    if "switch window" in text:
        return {"type": "window", "action": "switch"}
    
    # Show desktop
    if "show desktop" in text:
        return {"type": "window", "action": "show_desktop"}
    
    return {"type": "input_control"}


def _voice_model_params(match: Match[str]) -> Dict[str, Any]:
    """
    Extract voice model/persona selection parameters.
    Supports: voice jarvis, switch to friday, use sophia voice, etc.
    """
    text = match.group(0).lower()
    
    # Available voice personas
    voices = ['jarvis', 'vision', 'edith', 'elisa', 'sophia', 'friday']
    
    # Check for list voices command
    if any(k in text for k in ('list voice', 'show voice', 'available voice', 'what voice')):
        return {"action": "list"}
    
    # Extract voice name
    for voice in voices:
        if voice in text:
            return {"action": "set", "voice": voice}
    
    return {"action": "list"}


# -------------------- Normalization --------------------


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip("\n\t \"'.,?!")


# -------------------- Patterns --------------------


PATTERNS: List[Tuple[re.Pattern[str], str, ParamsFn]] = [
    # Open browser
    (
        re.compile(
            r"\b(?:open|launch|start|run)\s+(?:the\s+)?"
            r"(?:(?P<browser>chrome|google chrome|firefox|mozilla|safari|edge|msedge|brave|opera|google|microsoft edge)\b"
            r"|browser|web browser)",
            re.I,
        ),
        "open_browser",
        _browser_params,
    ),

    # Search - ONLY explicit web search commands
    # This prevents "find X" from opening browser, keeps it for explicit "search google for X"
    (
        re.compile(
            r"\b(?:search\s+(?:google|bing|online|the\s+web|on\s+google|on\s+bing)\s+(?:for\s+)?|"
            r"google\s+(?:for\s+)?|"
            r"web\s+search\s+(?:for\s+)?|"
            r"search\s+for\s+.+\s+(?:on\s+google|online|on\s+the\s+web)|"
            r"look\s+up\s+.+\s+(?:on\s+google|online))\s*(?P<query>[^\n\r]+)",
            re.I,
        ),
        "search",
        _search_params,
    ),

    # Time / date
    (
        re.compile(
            r"\b(?:(what(?:'s| is)? the time|what time is it|tell me the time|current time|time now|"
            r"what(?:'s| is)? the date|what date is it|today(?:'s)? date))\b",
            re.I,
        ),
        "get_time",
        _noop_params,
    ),

    # System power
    (
        re.compile(
            r"(?:(?P<shutdown>\b(?:shutdown|shut down|power off|turn off)\b)|"
            r"(?P<restart>\b(?:restart|reboot)\b)|"
            r"(?P<sleep>\b(?:sleep|suspend)\b)|"
            r"(?P<lock>\b(?:lock|lock screen|lock the computer|lock my laptop)\b))",
            re.I,
        ),
        "system_power",
        _system_power_params,
    ),

    # Volume / audio
    (
        re.compile(r"\b(?:volume|sound|audio|mute|unmute)\b.*", re.I),
        "control_volume",
        _volume_params,
    ),

    # Brightness / screen
    (
        re.compile(
            r"\b(?:brightness|screen brightness|display brightness|"
            r"brighter|dimmer|dim|brighten)\b.*",
            re.I,
        ),
        "control_brightness",
        _brightness_params,
    ),

    # App control
    (
        re.compile(
            r"\b(?P<app_action>open|start|launch|run|close|quit|exit|stop)\b\s+"
            r"(?P<app>[a-z0-9 ._+\-]+)",
            re.I,
        ),
        "control_app",
        _app_params,
    ),

    # File / folder
    (
        re.compile(
            r"\b(?:open|show|reveal)\b\s+(?:the\s+)?"
            r"(?P<target>(?:file|folder|directory|path)?\s*[a-z0-9_./\\:\- ]+)",
            re.I,
        ),
        "open_path",
        _file_params,
    ),

    # Help / about
    (
        re.compile(
            r"\b(?:help|what can you do|what are your capabilities|who are you|what is this|what are you)\b",
            re.I,
        ),
        "assistant_help",
        _help_params,
    ),

    # Navigation (back, home, notifications, recents)
    (
        re.compile(
            r"\b(?:go back|back|go home|home|show notifications|notifications|show recent apps|recent apps)\b",
            re.I,
        ),
        "navigate",
        _navigate_params,
    ),

    # Media control (play, pause, next, previous)
    (
        re.compile(
            r"\b(?:play|pause|resume|stop|next (?:song|track)?|previous (?:song|track)?|prev(?:ious)? track?)\b",
            re.I,
        ),
        "media_control",
        _media_params,
    ),

    # Scroll
    (
        re.compile(
            r"\b(?:scroll (?:up|down|to the top|to top|to the bottom|to bottom)|scroll up|scroll down)\b",
            re.I,
        ),
        "scroll",
        _scroll_params,
    ),

    # Input control (Voice Access style - mouse/keyboard automation)
    (
        re.compile(
            r"(?:"
            # Mouse clicks
            r"\b(?:click|double click|triple click|right click|middle click)\b|"
            # Mouse movement
            r"\b(?:move\s+(?:mouse|cursor)|mouse grid|show grid|close grid|hide grid)\b|"
            # Keyboard type/press
            r"\btype\s+\w+|"
            r"\bpress\s+\w+|"
            # Common actions
            r"\b(?:copy|paste|cut|undo|redo|select all)\b|"
            # Window management
            r"\b(?:switch window|show desktop|take screenshot|screenshot)\b"
            r").*",
            re.I,
        ),
        "input_control",
        _input_control_params,
    ),

    # Voice model/persona selection
    (
        re.compile(
            r"(?:"
            # Direct voice commands
            r"\b(?:voice|persona)\s+(?:jarvis|vision|edith|elisa|sophia|friday)\b|"
            # Switch to voice
            r"\bswitch\s+(?:to\s+)?(?:jarvis|vision|edith|elisa|sophia|friday)(?:\s+voice)?\b|"
            # Use voice
            r"\buse\s+(?:jarvis|vision|edith|elisa|sophia|friday)(?:\s+voice)?\b|"
            # Change voice
            r"\bchange\s+(?:voice\s+)?(?:to\s+)?(?:jarvis|vision|edith|elisa|sophia|friday)\b|"
            # Set voice
            r"\bset\s+voice\s+(?:to\s+)?(?:jarvis|vision|edith|elisa|sophia|friday)\b|"
            # List voices
            r"\b(?:list|show|what)\s+(?:available\s+)?voices?\b|"
            r"\bavailable\s+voices?\b"
            r")",
            re.I,
        ),
        "voice_model",
        _voice_model_params,
    ),
]


# -------------------- Fast-fail keyword index --------------------


KEYWORD_INDEX = {
    "browser": ("open_browser",),
    "chrome": ("open_browser",),
    "firefox": ("open_browser",),
    "safari": ("open_browser",),
    "edge": ("open_browser",),
    "google": ("open_browser", "search"),
    "search": ("search",),
    "lookup": ("search",),
    "find": ("search",),
    "time": ("get_time",),
    "date": ("get_time",),
    "today": ("get_time",),
    "brightness": ("control_brightness",),
    "brighter": ("control_brightness",),
    "dimmer": ("control_brightness",),
    "dim": ("control_brightness",),
    "shutdown": ("system_power",),
    "shut down": ("system_power",),
    "power off": ("system_power",),
    "turn off": ("system_power",),
    "restart": ("system_power",),
    "reboot": ("system_power",),
    "sleep": ("system_power",),
    "suspend": ("system_power",),
    "lock": ("system_power",),
    "volume": ("control_volume",),
    "sound": ("control_volume",),
    "audio": ("control_volume",),
    "mute": ("control_volume",),
    "unmute": ("control_volume",),
    "open": ("open_browser", "control_app", "open_path"),
    "start": ("open_browser", "control_app"),
    "launch": ("open_browser", "control_app"),
    "run": ("open_browser", "control_app"),
    "close": ("control_app",),
    "quit": ("control_app",),
    "exit": ("control_app",),
    "help": ("assistant_help",),
    "capabilities": ("assistant_help",),
    "who are you": ("assistant_help",),

    # Navigation
    "go back": ("navigate",),
    "back": ("navigate",),
    "go home": ("navigate",),
    "home": ("navigate",),
    "notifications": ("navigate",),
    "recent apps": ("navigate",),
    "recent": ("navigate",),

    # Media
    "play": ("media_control",),
    "pause": ("media_control",),
    "resume": ("media_control",),
    "next": ("media_control",),
    "previous": ("media_control",),
    "prev": ("media_control",),
    "song": ("media_control",),
    "track": ("media_control",),

    # Scroll
    "scroll": ("scroll",),
    "up": ("scroll",),
    "down": ("scroll",),
    "top": ("scroll",),
    "bottom": ("scroll",),

    # Input control (Voice Access style)
    "click": ("input_control",),
    "double click": ("input_control",),
    "triple click": ("input_control",),
    "right click": ("input_control",),
    "middle click": ("input_control",),
    "mouse": ("input_control",),
    "cursor": ("input_control",),
    "move mouse": ("input_control",),
    "mouse grid": ("input_control",),
    "grid": ("input_control",),
    "type": ("input_control",),
    "press": ("input_control",),
    "copy": ("input_control",),
    "paste": ("input_control",),
    "cut": ("input_control",),
    "undo": ("input_control",),
    "redo": ("input_control",),
    "select all": ("input_control",),
    "switch window": ("input_control",),
    "show desktop": ("input_control",),
    "screenshot": ("input_control",),
    "drag": ("input_control",),

    # Voice model/persona selection
    "voice": ("voice_model",),
    "persona": ("voice_model",),
    "jarvis": ("voice_model",),
    "vision": ("voice_model",),
    "edith": ("voice_model",),
    "elisa": ("voice_model",),
    "sophia": ("voice_model",),
    "friday": ("voice_model",),
}


# -------------------- Main parse function --------------------


def parse_command(text: str) -> Dict[str, Any]:
    """
    Parse text into {'command': <id>, 'params': {...}}.

    This function is pure and side-effect free.
    """
    text = normalize_text(text or "")
    if not text:
        return {"command": "unknown", "params": {}}

    # Strip assistant wake words at the start
    for wake in ("voxmind ", "hey voxmind ", "ok voxmind "):
        if text.startswith(wake):
            text = text[len(wake):].lstrip()
            break

    # Fast-fail keyword filtering
    candidate_cmds = set()
    for kw, cmds in KEYWORD_INDEX.items():
        if kw in text:
            candidate_cmds.update(cmds)

    if candidate_cmds:
        for pattern, cmd_id, params_fn in PATTERNS:
            if cmd_id not in candidate_cmds:
                continue
            m = pattern.search(text)
            if m:
                try:
                    params = params_fn(m)
                except Exception:
                    params = {}
                return {"command": cmd_id, "params": params}
    else:
        for pattern, cmd_id, params_fn in PATTERNS:
            m = pattern.search(text)
            if m:
                try:
                    params = params_fn(m)
                except Exception:
                    params = {}
                return {"command": cmd_id, "params": params}

    # Simple fallbacks
    if any(kw in text for kw in ("open ", "launch ", "start ", "run ")) and "browser" in text:
        return {"command": "open_browser", "params": {"browser": None}}

    if "time" in text or "date" in text:
        return {"command": "get_time", "params": {}}

    # Only search when explicitly requested with "search" keyword
    # Don't auto-search for unrecognized commands
    if text.startswith("search ") or text.startswith("search for ") or text.startswith("google ") or text.startswith("look up "):
        query = text
        for prefix in ("search for ", "search ", "google ", "look up "):
            if text.startswith(prefix):
                query = text[len(prefix):].strip()
                break
        if query:
            return {"command": "search", "params": {"query": query}}

    return {"command": "unknown", "params": {}}
