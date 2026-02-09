"""
VoxMind Response Generator
==========================
Generate textual responses for parsed commands.

Enhanced to use the intelligent response system for:
- Varied response templates (avoids robotic repetition)
- Context-aware responses
- 'Did you mean...?' disambiguation

Usage:
    from Tejas.response_generator import generate_response, generate_intelligent_response
    
    # Basic (legacy)
    response = generate_response(parsed)
    
    # Intelligent (recommended)
    result = generate_intelligent_response("open chrome", parsed)
    if result.get('needs_disambiguation'):
        print(result['disambiguation_message'])
    else:
        print(result['response'])
"""
from datetime import datetime
from typing import Dict, Any, Optional


def generate_response(parsed: Dict[str, Any]) -> str:
    """
    Generate a basic textual response for a parsed command.
    
    For more varied and context-aware responses, use generate_intelligent_response().
    """
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
    if ctype == "app_control":
        app = parsed.get("app", "the application")
        action = parsed.get("action", "open")
        if action in ("close", "quit", "exit"):
            return f"Closing {app}."
        return f"Opening {app}."
    if ctype == "volume":
        action = parsed.get("action", "adjust")
        level = parsed.get("level")
        if action == "mute":
            return "Muted."
        elif level is not None:
            return f"Setting volume to {level}%."
        elif action == "up":
            return "Volume up."
        elif action == "down":
            return "Volume down."
        return "Adjusting volume."

    return "Sorry, I didn't understand that. Can you rephrase?"


def generate_intelligent_response(text: str, parsed: Dict[str, Any],
                                    execute: bool = False) -> Dict[str, Any]:
    """
    Generate an intelligent response using the new response engine.
    
    Features:
    - 'Did you mean...?' disambiguation for ambiguous commands
    - Varied response templates (never says the same thing twice)
    - Context awareness for follow-up questions
    - Streaming response capability
    
    Args:
        text: Original user text
        parsed: Parsed command dict from NLP parser
        execute: Whether to execute the command
    
    Returns:
        {
            'response': str,              # The response text
            'needs_disambiguation': bool, # Whether user needs to clarify
            'disambiguation_message': str,# "Did you mean...?" message
            'options': list,              # Disambiguation options
            'confidence': float,          # Command confidence
            'executed': bool,             # Whether command was executed
        }
    """
    try:
        from core.intelligent_response import process_command_intelligently
        return process_command_intelligently(text, parsed, execute)
    except ImportError:
        # Fallback to basic response
        return {
            'response': generate_response(parsed),
            'needs_disambiguation': False,
            'confidence': parsed.get('confidence', 1.0),
            'executed': False
        }


def get_clarification() -> str:
    """Get a varied 'I didn't understand' response."""
    try:
        from core.intelligent_response import get_clarification
        return get_clarification()
    except ImportError:
        return "I didn't understand that. Can you try again?"


def get_varied_response(template_key: str, **kwargs) -> str:
    """
    Get a varied response for a template key.
    
    Template keys: 'search', 'time', 'play_music', 'app_control_open', 
                   'app_control_close', 'volume_up', 'volume_down', etc.
    """
    try:
        from core.intelligent_response import get_varied_response
        return get_varied_response(template_key, **kwargs)
    except ImportError:
        return f"[{template_key}]"
