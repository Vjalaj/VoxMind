"""
VoxMind - Swadhin Module
=========================
Integrated module combining Response System and Process Mapper.

This module provides:
1. Response Generation - Contextual, personalized responses with multiple tones
2. Process Mapping - App/icon mapping using Task Manager-like access
3. Unified API - Easy-to-use interface for other VoxMind modules

Author: Swadhin
"""

import os
import sys
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'response_system'))

# Import response system components
try:
    from response_system.response_templates import render, TEMPLATES
    from response_system.context import ContextManager
    from response_system.cache import ResponseCache
    from response_system.response_generator import ResponseGenerator
    HAS_RESPONSE_SYSTEM = True
except ImportError as e:
    HAS_RESPONSE_SYSTEM = False
    print(f"Warning: Response system not available: {e}")

# Import process mapper
try:
    from process_mapper import (
        ProcessMapper,
        ProcessInfo,
        ProcessCategory,
        list_running_apps,
        find_app,
        get_app_icon_path,
        get_process_mapper
    )
    HAS_PROCESS_MAPPER = True
except ImportError as e:
    HAS_PROCESS_MAPPER = False
    print(f"Warning: Process mapper not available: {e}")

# Import intonation module
try:
    from intonation import (
        IntonationEngine,
        IntonationResult,
        EmotionalTone,
        add_intonation,
        get_ssml,
        speak_with_intonation,
        analyze_prosody,
        get_intonation_engine
    )
    HAS_INTONATION = True
except ImportError as e:
    HAS_INTONATION = False
    print(f"Warning: Intonation module not available: {e}")

# Import voice models
try:
    from voice_models import (
        VoiceEngine,
        VoiceModel,
        VoicePersona,
        VoiceGender,
        get_voice_engine,
        set_voice,
        greet as voice_greet,
        acknowledge as voice_acknowledge,
        get_system_prompt,
        list_voices,
        voice_response,
        VOICE_MODELS
    )
    HAS_VOICE_MODELS = True
except ImportError as e:
    HAS_VOICE_MODELS = False
    print(f"Warning: Voice models not available: {e}")


# === Tone Enum ===

class ResponseTone(Enum):
    """Available response tones"""
    FRIENDLY = "friendly"
    PROFESSIONAL = "professional"
    HUMOROUS = "humorous"
    NEUTRAL = "neutral"


# === Extended Response Templates for App Commands ===

APP_TEMPLATES = {
    "app_found": {
        "friendly": [
            "Found {app_name} for you! 🎯",
            "Got it! {app_name} is running.",
            "Here's {app_name}! Ready when you are.",
            "{app_name} is up and running! 😊",
            "Found {app_name}! What would you like to do?",
        ],
        "professional": [
            "{app_name} has been located.",
            "Application found: {app_name}.",
            "{app_name} is currently active.",
            "Located {app_name} successfully.",
            "{app_name} is available.",
        ],
        "humorous": [
            "Aha! Found {app_name} hiding in plain sight! 🔍",
            "{app_name} reporting for duty! 🫡",
            "There it is! {app_name} was waiting for you!",
            "{app_name} says hello! 👋",
            "Mission accomplished! {app_name} located! 🎉",
        ]
    },
    "app_not_found": {
        "friendly": [
            "Hmm, I couldn't find {query}. Is it running?",
            "Sorry, {query} doesn't seem to be open.",
            "I can't see {query} right now. Want me to look again?",
            "{query} isn't showing up. Maybe try opening it first?",
            "No luck finding {query}. 🤔",
        ],
        "professional": [
            "Application '{query}' was not found.",
            "Unable to locate {query} in running processes.",
            "{query} is not currently active.",
            "No matching application found for '{query}'.",
            "The requested application '{query}' is not available.",
        ],
        "humorous": [
            "{query} is playing hide and seek... and winning! 🙈",
            "Where's Waldo? More like where's {query}! 😅",
            "{query} has gone incognito! 🕵️",
            "Houston, we have a problem... can't find {query}!",
            "{query} ghosted us! 👻",
        ]
    },
    "app_list": {
        "friendly": [
            "Here are your running apps! 📱",
            "Found {count} apps running for you!",
            "You've got {count} apps open right now.",
            "Here's what's running: {count} apps!",
            "Your active apps ({count} total):",
        ],
        "professional": [
            "Currently running applications: {count}",
            "Active processes: {count} applications.",
            "System report: {count} applications running.",
            "Application inventory: {count} active.",
            "Running applications summary: {count} total.",
        ],
        "humorous": [
            "Behold! {count} apps, all working hard (or hardly working)! 😄",
            "Your digital army: {count} apps strong! 💪",
            "{count} apps? Someone's been busy! 🐝",
            "App roll call: {count} present and accounted for! ✋",
            "Wow, {count} apps! Your computer is having a party! 🎉",
        ]
    },
    "process_summary": {
        "friendly": [
            "Here's your system overview! 📊",
            "Let me break down what's happening...",
            "System status coming right up!",
            "Here's the scoop on your system!",
            "Quick system check for you!",
        ],
        "professional": [
            "System performance summary:",
            "Process analysis complete.",
            "System resource report:",
            "Performance metrics:",
            "System status report:",
        ],
        "humorous": [
            "Time for a health checkup! 🏥",
            "Let's see what the CPU is up to! 🔬",
            "System vitals, doctor! 👨‍⚕️",
            "Peeking under the hood... 🔧",
            "The machines are alive! Here's proof: 🤖",
        ]
    },
    "action_success": {
        "friendly": [
            "Done! ✅",
            "All set! 👍",
            "Got it done for you!",
            "There you go!",
            "Mission accomplished! 🎯",
        ],
        "professional": [
            "Action completed successfully.",
            "Operation completed.",
            "Task executed successfully.",
            "Request processed.",
            "Action performed.",
        ],
        "humorous": [
            "Boom! Done! 💥",
            "And it's outta here! ⚾",
            "Like a boss! 😎",
            "Easy peasy lemon squeezy! 🍋",
            "Nailed it! 🔨",
        ]
    },
    "action_failed": {
        "friendly": [
            "Oops, that didn't work. 😕",
            "Something went wrong, sorry!",
            "I couldn't do that, my bad!",
            "Hmm, that failed. Let me know if you want to retry.",
            "Sorry, that didn't go as planned.",
        ],
        "professional": [
            "The operation could not be completed.",
            "Action failed. Please try again.",
            "Unable to perform the requested action.",
            "An error occurred during execution.",
            "The request could not be processed.",
        ],
        "humorous": [
            "Well, that flopped! 🐟",
            "Error 404: Success not found! 😅",
            "Houston, we have a problem! 🚀",
            "That went sideways... literally! ↔️",
            "Oops! My bad! 🙈",
        ]
    }
}


def render_app_response(template_key: str, tone: str = "friendly", **kwargs) -> str:
    """Render an app-related response template"""
    import random
    
    templates = APP_TEMPLATES.get(template_key, {})
    tone_templates = templates.get(tone, templates.get("friendly", ["Response not available."]))
    
    template = random.choice(tone_templates)
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


# === Main Integration Class ===

class SwadhinModule:
    """
    Integrated module for VoxMind - Response System + Process Mapper.
    
    Usage:
        from Swadhin.main import SwadhinModule
        
        swadhin = SwadhinModule()
        
        # Find an app with contextual response
        result = swadhin.find_app("chrome", tone="friendly")
        
        # List running apps
        apps = swadhin.list_apps(tone="humorous")
        
        # Generate a response
        response = swadhin.respond("greet", name="User", tone="professional")
        
        # Get system summary
        summary = swadhin.get_system_summary(tone="friendly")
    """
    
    def __init__(self, user_id: str = "default", voice: str = "friday"):
        """
        Initialize the Swadhin module.
        
        Args:
            user_id: User identifier for context tracking
            voice: Default voice persona (jarvis, vision, edith, elisa, sofia, friday)
        """
        self.user_id = user_id
        self.tone = ResponseTone.FRIENDLY
        
        # Initialize components
        if HAS_RESPONSE_SYSTEM:
            self.response_generator = ResponseGenerator()
            self.context = ContextManager()
            self.cache = ResponseCache()
        else:
            self.response_generator = None
            self.context = None
            self.cache = None
        
        if HAS_PROCESS_MAPPER:
            self.process_mapper = get_process_mapper()
        else:
            self.process_mapper = None
        
        # Initialize voice engine
        if HAS_VOICE_MODELS:
            self.voice_engine = get_voice_engine(voice)
        else:
            self.voice_engine = None
    
    def set_tone(self, tone: str) -> None:
        """Set the default response tone"""
        try:
            self.tone = ResponseTone(tone.lower())
        except ValueError:
            self.tone = ResponseTone.FRIENDLY
    
    def get_tone(self) -> str:
        """Get the current response tone"""
        return self.tone.value
    
    # === Voice Model Methods ===
    
    def set_voice(self, name: str) -> bool:
        """
        Set the active voice persona.
        
        Args:
            name: Voice name (jarvis, vision, edith, elisa, sofia, friday)
            
        Returns:
            True if voice was set successfully
        """
        if not HAS_VOICE_MODELS:
            return False
        return self.voice_engine.set_voice(name)
    
    def get_voice(self) -> Optional[Dict[str, Any]]:
        """Get information about the current voice"""
        if not HAS_VOICE_MODELS:
            return None
        return self.voice_engine.get_voice_info()
    
    def list_voices(self) -> List[Dict[str, Any]]:
        """List all available voice personas"""
        if not HAS_VOICE_MODELS:
            return []
        return self.voice_engine.list_voices()
    
    def voice_greet(self) -> str:
        """Get a greeting from the current voice persona"""
        if not HAS_VOICE_MODELS:
            return "Hello!"
        return self.voice_engine.greet()
    
    def voice_acknowledge(self) -> str:
        """Get an acknowledgment from the current voice persona"""
        if not HAS_VOICE_MODELS:
            return "Understood."
        return self.voice_engine.acknowledge()
    
    def voice_success(self) -> str:
        """Get a success message from the current voice persona"""
        if not HAS_VOICE_MODELS:
            return "Done!"
        return self.voice_engine.report_success()
    
    def voice_error(self, error_msg: Optional[str] = None) -> str:
        """Get an error message from the current voice persona"""
        if not HAS_VOICE_MODELS:
            return f"Error: {error_msg}" if error_msg else "An error occurred."
        return self.voice_engine.report_error(error_msg)
    
    def voice_thinking(self) -> str:
        """Get a thinking/processing message from the current voice"""
        if not HAS_VOICE_MODELS:
            return "Processing..."
        return self.voice_engine.report_thinking()
    
    def get_llm_system_prompt(self) -> str:
        """
        Get the system prompt for LLM integration.
        Use this as the system message when calling an LLM.
        """
        if not HAS_VOICE_MODELS:
            return "You are a helpful AI assistant."
        return self.voice_engine.get_system_prompt()
    
    def voice_styled_response(self, text: str) -> Dict[str, Any]:
        """
        Get a response styled by the current voice with intonation.
        
        Args:
            text: The response text
            
        Returns:
            Dict with styled text, SSML, and voice info
        """
        if not HAS_VOICE_MODELS:
            return {"text": text, "voice": "default"}
        
        styled = self.voice_engine.style_response(text)
        result = self.voice_engine.apply_voice_intonation(styled)
        result["styled_text"] = styled
        return result
    
    # === Response Generation ===
    
    def respond(self, command: str, tone: Optional[str] = None, **kwargs) -> str:
        """
        Generate a contextual response.
        
        Args:
            command: Command type (greet, error, confirm, onboarding)
            tone: Response tone (friendly, professional, humorous, neutral)
            **kwargs: Template variables
            
        Returns:
            Generated response string
        """
        tone = tone or self.tone.value
        
        if HAS_RESPONSE_SYSTEM:
            return self.response_generator.generate(
                self.user_id, command, tone, **kwargs
            )
        else:
            # Fallback simple response
            return f"[{command}] Response system not available."
    
    def respond_app(self, template_key: str, tone: Optional[str] = None, **kwargs) -> str:
        """
        Generate an app-related response.
        
        Args:
            template_key: Template key (app_found, app_not_found, app_list, etc.)
            tone: Response tone
            **kwargs: Template variables
            
        Returns:
            Generated response string
        """
        tone = tone or self.tone.value
        return render_app_response(template_key, tone, **kwargs)
    
    # === Process/App Management ===
    
    def find_app(self, query: str, tone: Optional[str] = None) -> Dict[str, Any]:
        """
        Find a running app by name with contextual response.
        
        Args:
            query: App name to search for
            tone: Response tone
            
        Returns:
            Dict with app info and response
        """
        tone = tone or self.tone.value
        
        if not HAS_PROCESS_MAPPER:
            return {
                "found": False,
                "response": "Process mapper not available.",
                "app": None
            }
        
        app_info = find_app(query)
        
        if app_info:
            response = self.respond_app(
                "app_found", 
                tone, 
                app_name=app_info['name']
            )
            return {
                "found": True,
                "response": response,
                "app": app_info
            }
        else:
            response = self.respond_app("app_not_found", tone, query=query)
            return {
                "found": False,
                "response": response,
                "app": None
            }
    
    def list_apps(self, tone: Optional[str] = None) -> Dict[str, Any]:
        """
        List all running apps with contextual response.
        
        Args:
            tone: Response tone
            
        Returns:
            Dict with apps list and response
        """
        tone = tone or self.tone.value
        
        if not HAS_PROCESS_MAPPER:
            return {
                "response": "Process mapper not available.",
                "apps": [],
                "count": 0
            }
        
        apps = list_running_apps()
        count = len(apps)
        
        response = self.respond_app("app_list", tone, count=count)
        
        return {
            "response": response,
            "apps": apps,
            "count": count
        }
    
    def get_app_icon(self, app_name: str) -> Optional[str]:
        """
        Get the icon path for an app.
        
        Args:
            app_name: App name
            
        Returns:
            Path to icon file or None
        """
        if not HAS_PROCESS_MAPPER:
            return None
        
        return get_app_icon_path(app_name)
    
    def get_apps_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Get apps filtered by category.
        
        Args:
            category: Category name (browser, office, development, etc.)
            
        Returns:
            List of apps in that category
        """
        if not HAS_PROCESS_MAPPER:
            return []
        
        apps = list_running_apps()
        return [app for app in apps if app.get('category') == category.lower()]
    
    # === System Information ===
    
    def get_system_summary(self, tone: Optional[str] = None) -> Dict[str, Any]:
        """
        Get system summary with contextual response.
        
        Args:
            tone: Response tone
            
        Returns:
            Dict with system summary and response
        """
        tone = tone or self.tone.value
        
        if not HAS_PROCESS_MAPPER:
            return {
                "response": "Process mapper not available.",
                "summary": None
            }
        
        summary = self.process_mapper.get_process_summary()
        response = self.respond_app("process_summary", tone)
        
        return {
            "response": response,
            "summary": summary
        }
    
    # === Contextual Actions ===
    
    def execute_with_response(
        self, 
        action: callable, 
        success_tone: Optional[str] = None,
        *args, 
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute an action and return with contextual response.
        
        Args:
            action: Callable to execute
            success_tone: Tone for response
            *args, **kwargs: Arguments for the action
            
        Returns:
            Dict with success status, result, and response
        """
        tone = success_tone or self.tone.value
        
        try:
            result = action(*args, **kwargs)
            response = self.respond_app("action_success", tone)
            return {
                "success": True,
                "result": result,
                "response": response
            }
        except Exception as e:
            response = self.respond_app("action_failed", tone)
            return {
                "success": False,
                "error": str(e),
                "response": response
            }
    
    # === User Context ===
    
    def set_user_context(self, key: str, value: Any) -> None:
        """Set a context value for the current user"""
        if self.context:
            self.context.set(self.user_id, key, value)
    
    def get_user_context(self, key: str, default: Any = None) -> Any:
        """Get a context value for the current user"""
        if self.context:
            return self.context.get(self.user_id, key, default)
        return default
    
    def reset_user_context(self) -> None:
        """Reset all context for the current user"""
        if self.context:
            self.context.reset(self.user_id)
    
    # === Intonation / Speech ===
    
    def add_intonation(self, text: str, tone: Optional[str] = None) -> Dict[str, Any]:
        """
        Add human-like intonation to text for natural speech.
        
        Args:
            text: Text to add intonation to
            tone: Emotional tone (friendly, professional, excited, etc.)
            
        Returns:
            Dict with SSML, prosody markers, and analysis
        """
        if not HAS_INTONATION:
            return {
                "success": False,
                "error": "Intonation module not available",
                "text": text,
                "ssml": f"<speak>{text}</speak>"
            }
        
        tone = tone or self.tone.value
        
        try:
            emotional_tone = EmotionalTone(tone.lower())
        except ValueError:
            emotional_tone = EmotionalTone.FRIENDLY
        
        result = add_intonation(text, emotional_tone.value)
        
        return {
            "success": True,
            "text": result.original_text,
            "ssml": result.ssml,
            "estimated_duration_ms": result.estimated_duration_ms,
            "prosody_markers": result.prosody_markers,
            "sentences": [
                {
                    "text": s.text,
                    "type": s.sentence_type.value,
                    "tone": s.emotional_tone.value,
                    "final_pitch": s.final_pitch_change
                }
                for s in result.annotated_sentences
            ]
        }
    
    def speak(self, text: str, tone: Optional[str] = None, 
              rate: int = 150, volume: float = 0.9) -> Dict[str, Any]:
        """
        Speak text with human-like intonation.
        
        Args:
            text: Text to speak
            tone: Emotional tone
            rate: Speaking rate (words per minute)
            volume: Volume (0.0 to 1.0)
            
        Returns:
            Dict with success status
        """
        if not HAS_INTONATION:
            return {
                "success": False,
                "error": "Intonation module not available"
            }
        
        tone = tone or self.tone.value
        
        try:
            speak_with_intonation(text, tone, rate, volume)
            return {
                "success": True,
                "text": text,
                "tone": tone
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_ssml(self, text: str, tone: Optional[str] = None) -> str:
        """
        Get SSML-formatted text with intonation markers.
        
        Args:
            text: Text to convert
            tone: Emotional tone
            
        Returns:
            SSML string for TTS engines
        """
        if not HAS_INTONATION:
            return f"<speak>{text}</speak>"
        
        tone = tone or self.tone.value
        return get_ssml(text, tone)
    
    def analyze_speech(self, text: str) -> Dict[str, Any]:
        """
        Analyze text for prosody and speech patterns.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict with prosody analysis
        """
        if not HAS_INTONATION:
            return {"error": "Intonation module not available"}
        
        return analyze_prosody(text)
    
    # === Status ===
    
    def get_status(self) -> Dict[str, Any]:
        """Get module status"""
        voice_info = None
        if self.voice_engine:
            voice_info = self.voice_engine.get_voice_info()
        
        return {
            "user_id": self.user_id,
            "tone": self.tone.value,
            "response_system": HAS_RESPONSE_SYSTEM,
            "process_mapper": HAS_PROCESS_MAPPER,
            "intonation": HAS_INTONATION,
            "voice_models": HAS_VOICE_MODELS,
            "current_voice": voice_info,
            "components": {
                "response_generator": self.response_generator is not None,
                "context_manager": self.context is not None,
                "cache": self.cache is not None,
                "process_mapper": self.process_mapper is not None,
                "intonation_engine": HAS_INTONATION,
                "voice_engine": self.voice_engine is not None
            }
        }


# === Convenience Functions ===

_default_module: Optional[SwadhinModule] = None

def get_module(user_id: str = "default") -> SwadhinModule:
    """Get or create the default SwadhinModule instance"""
    global _default_module
    if _default_module is None or _default_module.user_id != user_id:
        _default_module = SwadhinModule(user_id)
    return _default_module


def quick_find_app(query: str, tone: str = "friendly") -> str:
    """Quickly find an app and get a response"""
    module = get_module()
    result = module.find_app(query, tone)
    return result["response"]


def quick_list_apps(tone: str = "friendly") -> str:
    """Quickly list apps and get a response"""
    module = get_module()
    result = module.list_apps(tone)
    
    response = result["response"]
    if result["apps"]:
        app_names = [app["name"] for app in result["apps"][:10]]
        response += "\n• " + "\n• ".join(app_names)
        if result["count"] > 10:
            response += f"\n  ...and {result['count'] - 10} more"
    
    return response


def quick_respond(command: str, tone: str = "friendly", **kwargs) -> str:
    """Quickly generate a response"""
    module = get_module()
    return module.respond(command, tone, **kwargs)


# === CLI Interface ===

def main():
    """Interactive CLI for testing the Swadhin module"""
    print("=" * 60)
    print("VoxMind - Swadhin Module")
    print("Response System + Process Mapper Integration")
    print("=" * 60)
    
    module = SwadhinModule(user_id="cli_user", voice="friday")
    
    # Show status
    status = module.get_status()
    print(f"\n📊 Module Status:")
    print(f"   Response System: {'✅' if status['response_system'] else '❌'}")
    print(f"   Process Mapper:  {'✅' if status['process_mapper'] else '❌'}")
    print(f"   Voice Models:    {'✅' if status['voice_models'] else '❌'}")
    print(f"   Current Tone:    {status['tone']}")
    if status.get('current_voice'):
        print(f"   Current Voice:   {status['current_voice']['name']}")
    
    # Interactive loop
    print("\n" + "-" * 60)
    print("Commands:")
    print("  find <app>     - Find a running application")
    print("  list           - List all running apps")
    print("  summary        - System process summary")
    print("  tone <name>    - Set tone (friendly|professional|humorous)")
    print("  voice <name>   - Set voice (jarvis|vision|edith|elisa|sofia|friday)")
    print("  voices         - List all available voices")
    print("  greet          - Hear current voice greeting")
    print("  quit           - Exit")
    print("-" * 60)
    
    while True:
        try:
            user_input = input("\n> ").strip().lower()
            
            if not user_input:
                continue
            
            if user_input in ["quit", "exit", "bye"]:
                farewell = module.voice_greet().replace("Hi", "Goodbye").replace("Hey", "Bye").replace("Hello", "Goodbye")
                print(farewell)
                break
            
            elif user_input.startswith("find "):
                query = user_input[5:].strip()
                result = module.find_app(query)
                print(f"\n{result['response']}")
                if result['found']:
                    app = result['app']
                    print(f"   Process: {app['process']}")
                    print(f"   PID: {app['pid']}")
                    print(f"   Category: {app['category']}")
            
            elif user_input == "list":
                result = module.list_apps()
                print(f"\n{result['response']}")
                for app in result['apps'][:10]:
                    print(f"   • {app['name']} ({app['category']})")
                if result['count'] > 10:
                    print(f"   ...and {result['count'] - 10} more")
            
            elif user_input == "summary":
                result = module.get_system_summary()
                print(f"\n{result['response']}")
                if result['summary']:
                    s = result['summary']
                    print(f"   Total Processes: {s['total_processes']}")
                    print(f"   Memory Usage: {s['total_memory_mb']:.1f} MB")
                    print(f"   Top Memory Users:")
                    for app in s['top_memory'][:3]:
                        print(f"      • {app['name']}: {app['memory_mb']:.1f} MB")
            
            elif user_input.startswith("tone "):
                new_tone = user_input[5:].strip()
                module.set_tone(new_tone)
                print(f"Tone set to: {module.get_tone()}")
            
            # Voice commands
            elif user_input.startswith("voice "):
                voice_name = user_input[6:].strip()
                if module.set_voice(voice_name):
                    voice_info = module.get_voice()
                    print(f"\n🎤 Voice changed to: {voice_info['name']}")
                    print(f"   Role: {voice_info['role']}")
                    print(f"   Style: {voice_info['style']}")
                    print(f"\n   {module.voice_greet()}")
                else:
                    print(f"❌ Unknown voice: {voice_name}")
                    print("   Available: jarvis, vision, edith, elisa, sofia, friday")
            
            elif user_input == "voices":
                print("\n🎤 Available Voice Personas:")
                for v in module.list_voices():
                    current = " (current)" if module.get_voice() and v['name'] == module.get_voice()['name'] else ""
                    print(f"   • {v['name'].lower():<8} - {v['role']}{current}")
            
            elif user_input == "greet":
                print(f"\n{module.voice_greet()}")
            
            elif user_input in ["hi", "hello", "hey"]:
                print(module.voice_greet())
            
            else:
                print("Unknown command. Try: find <app>, voice <name>, voices, quit")
                
        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
