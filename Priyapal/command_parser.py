"""
jarvis_assistant.py

Single-file assistant combining:
- Command parser (regex + fast-fail + wake word support)
- Simple Windows-focused execution stubs
- TTS/ASR glue
- Small test harness

Requires:
    pip install SpeechRecognition pyttsx3 pyaudio
"""

from __future__ import annotations

import os
import re
import sys
import time
import traceback
import webbrowser
import subprocess
from typing import Dict, Any, Callable, Match, List, Tuple, Optional

import speech_recognition as sr  # type: ignore
try:
    import pyttsx3  # type: ignore
except Exception:
    pyttsx3 = None  # type: ignore

# ============================================================
# Command parser
# ============================================================

ParamsFn = Callable[[Match[str]], Dict[str, Any]]


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


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip("\n\t \"'.,?!")

# Regex patterns
PATTERNS: List[Tuple[re.Pattern[str], str, ParamsFn]] = [
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
    (
        re.compile(
            r"\b(?:search for|search|google|look up|lookup|find|find me|look for)\b\s+(?P<query>[^\n\r]+)",
            re.I,
        ),
        "search",
        _search_params,
    ),
    (
        re.compile(
            r"\b(?:(what(?:'s| is)? the time|what time is it|tell me the time|current time|time now|"
            r"what(?:'s| is)? the date|what date is it|today(?:'s)? date))\b",
            re.I,
        ),
        "get_time",
        _noop_params,
    ),
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
    (
        re.compile(r"\b(?:volume|sound|audio|mute|unmute)\b.*", re.I),
        "control_volume",
        _volume_params,
    ),
    (
        re.compile(
            r"\b(?P<app_action>open|start|launch|run|close|quit|exit|stop)\b\s+"
            r"(?P<app>[a-z0-9 ._+\-]+)",
            re.I,
        ),
        "control_app",
        _app_params,
    ),
    (
        re.compile(
            r"\b(?:open|show|reveal)\b\s+(?:the\s+)?"
            r"(?P<target>(?:file|folder|directory|path)?\s*[a-z0-9_./\\:\- ]+)",
            re.I,
        ),
        "open_path",
        _file_params,
    ),
    (
        re.compile(
            r"\b(?:help|what can you do|what are your capabilities|who are you|what is this|what are you)\b",
            re.I,
        ),
        "assistant_help",
        _help_params,
    ),
]

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
}


def parse_command(text: str) -> Dict[str, Any]:
    text = normalize_text(text or "")
    if not text:
        return {"command": "unknown", "params": {}}

    # Strip assistant wake words at the start
    for wake in ("jarvis ", "hey jarvis ", "ok jarvis "):
        if text.startswith(wake):
            text = text[len(wake):].lstrip()
            break

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

    if any(kw in text for kw in ("open ", "launch ", "start ", "run ")) and "browser" in text:
        return {"command": "open_browser", "params": {"browser": None}}

    if "time" in text or "date" in text:
        return {"command": "get_time", "params": {}}

    if text:
        return {"command": "search", "params": {"query": text}}

    return {"command": "unknown", "params": {}}


# ============================================================
# Assistant: TTS, ASR, execution, continuous listening
# ============================================================

_engine: Optional[Any] = None
_recognizer: Optional[Any] = None


def _ensure_engine():
    global _engine
    if _engine is None:
        if pyttsx3 is None:
            _engine = None
            return
        try:
            _engine = pyttsx3.init()
        except Exception:
            _engine = None


def _ensure_recognizer():
    global _recognizer
    if _recognizer is None:
        try:
            _recognizer = sr.Recognizer()
        except Exception:
            _recognizer = None


def speak(text: str) -> None:
    print(f"ASSISTANT: {text}")
    _ensure_engine()
    if _engine is None:
        return
    try:
        _engine.say(text)
        _engine.runAndWait()
    except Exception:
        traceback.print_exc()


def short_error_feedback(kind: str) -> None:
    if kind == "asr_unknown":
        speak("Sorry, I couldn't understand. Please say that again.")
    elif kind == "asr_network":
        speak("Speech service seems unavailable. Please check your internet.")
    elif kind == "parse_unknown":
        speak("I am not sure what you mean. Could you rephrase the command?")
    elif kind == "exec_error":
        speak("Something went wrong while executing that command.")
    else:
        speak("An unexpected error occurred.")


def listen_once_continuous(
    timeout: float = 5.0,
    phrase_time_limit: float = 10.0,
) -> str:
    _ensure_recognizer()
    if _recognizer is None:
        raise OSError("Recognizer unavailable")
    try:
        with sr.Microphone() as source:
            _recognizer.adjust_for_ambient_noise(source, duration=0.3)
            try:
                audio = _recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            except sr.WaitTimeoutError:
                return ""
        try:
            text = _recognizer.recognize_google(audio)
            print(f"USER: {text}")
            return text
        except sr.UnknownValueError:
            return ""
        except sr.RequestError:
            raise
        except Exception:
            traceback.print_exc()
            return ""
    except OSError as e:
        print(f"DEBUG: OSError in listen_once_continuous: {e}")
        raise


# Map common app names to Windows executables/commands
APP_MAP: Dict[str, str] = {
    "vscode": "code",
    "visual studio code": "code",
    "notepad": "notepad",
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "spotify": "spotify",
}


def execute_command(command: str, params: Dict[str, Any]) -> None:
    print(f"DEBUG: Executing {command!r} with params {params!r}")
    try:
        if command == "open_browser":
            browser = params.get("browser") or "default"
            speak(f"Opening {browser} browser.")
            url = "https://www.google.com"
            if sys.platform.startswith("win"):
                # Use default browser; specific registered browser names require setup
                webbrowser.open(url)
            else:
                webbrowser.open(url)

        elif command == "search":
            query = params.get("query") or ""
            if not query:
                speak("What should I search for?")
                return
            url = "https://www.google.com/search?q=" + query.replace(" ", "+")
            speak(f"Searching the web for {query}.")
            webbrowser.open(url)

        elif command == "get_time":
            # Placeholder – you can format actual time here
            speak("Getting the current time and date.")

        elif command == "system_power":
            mode = params.get("mode")
            if not sys.platform.startswith("win"):
                speak("System power commands are only configured for Windows right now.")
                return

            if mode == "shutdown":
                speak("Preparing to shut down. This is not executed automatically for safety.")
                # os.system("shutdown /s /t 0")
            elif mode == "restart":
                speak("Preparing to restart. This is not executed automatically for safety.")
                # os.system("shutdown /r /t 0")
            elif mode == "sleep":
                speak("Preparing to put the system to sleep. Not executed automatically for safety.")
                # os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            elif mode == "lock":
                speak("Locking your session.")
                os.system("rundll32.exe user32.dll,LockWorkStation")
            else:
                speak("Which power action did you want: shut down, restart, sleep, or lock?")

        elif command == "control_volume":
            action = params.get("action")
            level = params.get("level")
            # Real volume control needs extra libraries (e.g., pycaw) on Windows.
            if action == "mute":
                speak("Muting volume.")
            elif action == "unmute":
                speak("Unmuting volume.")
            elif action == "up":
                speak("Turning the volume up.")
            elif action == "down":
                speak("Turning the volume down.")
            elif action == "set" and level is not None:
                speak(f"Setting volume to {level} percent.")
            else:
                speak("How should I adjust the volume?")

        elif command == "control_app":
            app = (params.get("app") or "").lower()
            action = params.get("action")
            if not sys.platform.startswith("win"):
                speak("App control is only configured for Windows right now.")
                return

            if not app:
                speak("Which application?")
                return

            target_exe = None
            target_name = app
            for key, exe in APP_MAP.items():
                if key in app:
                    target_exe = exe
                    target_name = key
                    break

            if action == "open":
                if target_exe:
                    speak(f"Opening {target_name}.")
                    try:
                        subprocess.Popen(target_exe)
                    except Exception:
                        speak("I could not open that application.")
                else:
                    speak("I don't know how to open that application yet.")
            elif action == "close":
                if target_exe:
                    speak(f"Closing {target_name}.")
                    # taskkill is Windows-specific
                    os.system(f"taskkill /IM {target_exe}.exe /F")
                else:
                    speak("I don't know how to close that application yet.")
            else:
                speak(f"What should I do with {app}? Open or close it?")

        elif command == "open_path":
            target = params.get("target") or ""
            if not sys.platform.startswith("win"):
                speak("Opening paths is only fully implemented for Windows right now.")
                return

            if "downloads" in target.lower():
                speak("Opening Downloads folder.")
                downloads = os.path.join(os.path.expanduser("~"), "Downloads")
                try:
                    os.startfile(downloads)  # type: ignore[attr-defined]
                except Exception:
                    speak("I could not open your Downloads folder.")
            else:
                speak(f"Opening {target}.")
                try:
                    os.startfile(target)  # type: ignore[attr-defined]
                except Exception:
                    speak("I could not open that path.")

        elif command == "assistant_help":
            speak(
                "I can open apps, control your browser, adjust volume, manage power, "
                "and search the web. Say 'Jarvis' followed by your command.",
            )

        elif command == "unknown":
            short_error_feedback("parse_unknown")

        else:
            short_error_feedback("parse_unknown")

    except Exception:
        traceback.print_exc()
        short_error_feedback("exec_error")


def run_assistant_continuous() -> None:
    speak("Continuous listening enabled. Say 'Jarvis' before your command, or 'stop listening' to turn me off.")

    consecutive_soft_errors = 0
    consecutive_hard_errors = 0

    while True:
        try:
            text = listen_once_continuous(timeout=5.0, phrase_time_limit=10.0)
            if not text:
                consecutive_soft_errors += 1
                if consecutive_soft_errors in (3, 6):
                    speak("I’m still here. Say 'Jarvis' and then your command.")
                time.sleep(0.2)
                continue

            consecutive_soft_errors = 0
            consecutive_hard_errors = 0
            lower = text.lower()

            # Global stop phrases (no wake word required)
            if any(kw in lower for kw in ("stop listening", "sleep now", "go offline")):
                speak("Okay, I will stop listening for now.")
                break

            # Require wake word for all other actions
            if "jarvis" not in lower:
                print("DEBUG: No wake word 'jarvis' in input, ignoring.")
                continue

            result = parse_command(text)
            command = result.get("command", "unknown")
            params = result.get("params", {}) or {}
            if not isinstance(params, dict):
                params = {}

            if command == "unknown":
                short_error_feedback("parse_unknown")
                continue

            execute_command(command, params)
            time.sleep(0.1)

        except sr.RequestError:
            consecutive_hard_errors += 1
            print("DEBUG: RequestError from recognizer in continuous mode.")

            if consecutive_hard_errors == 1:
                speak("Speech service seems unavailable. I’ll retry in a few seconds.")
            elif consecutive_hard_errors % 3 == 0:
                speak("Still no connection to the speech service. Please check your internet.")

            backoff = min(5.0, 1.0 + consecutive_hard_errors * 0.5)
            time.sleep(backoff)
            continue

        except OSError:
            traceback.print_exc()
            speak("I lost access to the microphone. Please check your audio device.")
            time.sleep(5.0)
            continue

        except KeyboardInterrupt:
            speak("Stopping continuous listening. Goodbye.")
            break

        except Exception:
            traceback.print_exc()
            short_error_feedback("exec_error")
            time.sleep(0.5)
            continue


# ============================================================
# Parser test harness and text-only mode
# ============================================================

def run_parser_tests() -> None:
    tests = []

    def add(name: str, text: str, command: str, check):
        tests.append((name, text, command, check))

    add("open_browser_default", "Open the browser", "open_browser", lambda p: p["browser"] is None)
    add("open_browser_chrome", "Launch Chrome", "open_browser", lambda p: p["browser"] == "chrome")
    add("open_browser_firefox", "Can you start firefox browser for me?", "open_browser", lambda p: p["browser"] == "firefox")
    add("search_basic", "Search for quantum tunneling", "search", lambda p: p["query"] == "quantum tunneling")
    add("search_polite", "Google nearest cafe please", "search", lambda p: p["query"] == "nearest cafe")
    add("time_query", "What's the time?", "get_time", lambda p: True)
    add("date_query", "What's the date today?", "get_time", lambda p: True)
    add("shutdown", "Please shut down the computer", "system_power", lambda p: p["mode"] == "shutdown")
    add("restart", "Restart my PC", "system_power", lambda p: p["mode"] == "restart")
    add("sleep", "Put the laptop to sleep", "system_power", lambda p: p["mode"] == "sleep")
    add("lock", "Lock my laptop", "system_power", lambda p: p["mode"] == "lock")
    add("volume_mute", "Mute the volume", "control_volume", lambda p: p["action"] == "mute")
    add("volume_set", "Set volume to 35 percent", "control_volume", lambda p: p["action"] == "set" and p["level"] == 35)
    add("control_app_open", "Open vscode", "control_app", lambda p: p["action"] == "open" and "vscode" in (p["app"] or "").lower())
    add("control_app_close", "Close Spotify", "control_app", lambda p: p["action"] == "close" and "spotify" in (p["app"] or "").lower())
    add("open_path", "Open downloads folder", "open_path", lambda p: "downloads" in (p["target"] or "").lower())
    add("help", "What can you do?", "assistant_help", lambda p: True)
    add("wake_word", "Jarvis search for python tutorials", "search", lambda p: p["query"] == "python tutorials")
    add("unknown_fallback_search", "show me something totally random", "search", lambda p: "random" in p["query"])

    passed = 0
    for name, text, expected_cmd, checker in tests:
        result = parse_command(text)
        cmd = result.get("command")
        params = result.get("params", {})
        ok = cmd == expected_cmd and checker(params)
        print(f"[{'OK' if ok else 'FAIL'}] {name}: {text!r} -> {cmd!r}, {params}")
        if ok:
            passed += 1

    print(f"\n{passed}/{len(tests)} tests passed.")


def run_text_once() -> None:
    print("Type commands (q to quit). They will be parsed and executed without mic.\n")
    while True:
        try:
            text = input("YOU> ")
        except EOFError:
            break
        if not text or text.lower() in ("q", "quit", "exit"):
            break
        result = parse_command(text)
        execute_command(result.get("command", "unknown"), result.get("params", {}) or {})


if __name__ == "__main__":
    if "--test" in sys.argv:
        run_parser_tests()
    elif "--once" in sys.argv:
        run_text_once()
    else:
        try:
            run_assistant_continuous()
        except KeyboardInterrupt:
            print("\nDEBUG: KeyboardInterrupt, shutting down.")
            speak("Shutting down. See you later.")
        except Exception:
            traceback.print_exc()
            speak("A critical error occurred. Restart me when you're ready.")
import speech_recognition as sr
import pyttsx3