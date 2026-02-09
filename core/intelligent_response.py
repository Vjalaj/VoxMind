"""
VoxMind Intelligent Response Engine
====================================
Inspired by ChatGPT's voice mode responsiveness:

Key Features:
- Predictive disambiguation ("Did you mean...?")
- Confidence-based suggestions for ambiguous commands
- Streaming word-by-word responses for low latency feel
- Conversation context memory across turns
- Varied response templates (avoids robotic repetition)
- Graceful handling of unclear/partial input

This makes VoxMind more responsive and user-friendly compared to
basic voice assistants.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Generator, Tuple, Callable
from datetime import datetime
import time
import re
import random
import logging
from collections import deque
import threading

logger = logging.getLogger(__name__)


# ============================================================================
# RESPONSE STREAMING (Low-latency feel like ChatGPT)
# ============================================================================

@dataclass
class StreamingResponse:
    """
    Stream text word-by-word for more responsive feel.
    ChatGPT uses this to start speaking before the full response is ready.
    """
    text: str
    delay: float = 0.02  # 20ms between words feels natural
    
    def stream(self) -> Generator[str, None, None]:
        """Yield text chunks with natural timing."""
        words = self.text.split(' ')
        for i, word in enumerate(words):
            if i < len(words) - 1:
                yield word + ' '
            else:
                yield word
            time.sleep(self.delay)
    
    def stream_for_tts(self) -> Generator[str, None, None]:
        """
        Yield sentence chunks optimized for TTS engines.
        TTS engines work better with complete phrases.
        """
        # Split by sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', self.text)
        for sentence in sentences:
            yield sentence.strip()
            time.sleep(0.1)  # Small pause between sentences


# ============================================================================
# CONVERSATION CONTEXT MEMORY
# ============================================================================

@dataclass
class ConversationTurn:
    """Single turn in conversation."""
    role: str  # 'user' or 'assistant'
    content: str
    intent: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)
    confidence: float = 1.0


class ConversationContext:
    """
    Maintains conversation history for context-aware responses.
    ChatGPT uses this to understand follow-up questions.
    
    Example:
        User: "Open Chrome"
        Assistant: "Opening Chrome"
        User: "Now close it"  <- Understands "it" refers to Chrome
    """
    
    def __init__(self, max_turns: int = 10, context_timeout: float = 300):
        self._history: deque[ConversationTurn] = deque(maxlen=max_turns)
        self._lock = threading.Lock()
        self._context_timeout = context_timeout  # 5 minutes
        self._user_preferences: Dict[str, Any] = {}
        self._last_entity_references: Dict[str, str] = {}  # "it", "that" -> actual entity
    
    def add_turn(self, role: str, content: str, intent: str = None,
                 entities: Dict[str, Any] = None, confidence: float = 1.0):
        """Add a conversation turn."""
        with self._lock:
            turn = ConversationTurn(
                role=role,
                content=content,
                intent=intent,
                entities=entities or {},
                confidence=confidence
            )
            self._history.append(turn)
            
            # Track entity references for pronoun resolution
            if entities:
                for key, value in entities.items():
                    if isinstance(value, str) and value:
                        self._last_entity_references[key] = value
                        # Also track for common pronouns
                        if key in ('app', 'window', 'file'):
                            self._last_entity_references['it'] = value
                            self._last_entity_references['that'] = value
    
    def get_last_intent(self) -> Optional[str]:
        """Get the last recognized intent."""
        with self._lock:
            for turn in reversed(self._history):
                if turn.role == 'user' and turn.intent:
                    return turn.intent
        return None
    
    def get_last_entity(self, entity_type: str) -> Optional[str]:
        """Get the last value of an entity type (for pronoun resolution)."""
        with self._lock:
            return self._last_entity_references.get(entity_type)
    
    def resolve_pronouns(self, text: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve pronouns like 'it', 'that' to actual entities.
        
        Example: "close it" -> "close chrome" (if chrome was last opened)
        """
        resolved = entities.copy()
        text_lower = text.lower()
        
        # Check for pronouns that need resolution
        pronouns = ['it', 'that', 'this', 'the same']
        
        for pronoun in pronouns:
            if pronoun in text_lower:
                # Try to find what the pronoun refers to
                for entity_type in ['app', 'window', 'file', 'query']:
                    if entity_type not in resolved or not resolved[entity_type]:
                        ref = self.get_last_entity(entity_type)
                        if ref:
                            resolved[entity_type] = ref
                            logger.debug(f"Resolved '{pronoun}' to '{ref}' ({entity_type})")
                            break
        
        return resolved
    
    def get_context_summary(self, last_n: int = 3) -> str:
        """Get a summary of recent conversation for context."""
        with self._lock:
            recent = list(self._history)[-last_n:]
            if not recent:
                return ""
            
            summary_parts = []
            for turn in recent:
                prefix = "User" if turn.role == 'user' else "Assistant"
                summary_parts.append(f"{prefix}: {turn.content}")
            
            return "\n".join(summary_parts)
    
    def is_followup_question(self, text: str) -> bool:
        """Check if the current input seems like a follow-up."""
        followup_indicators = [
            'and', 'also', 'then', 'next', 'now', 'what about',
            'how about', 'it', 'that', 'this', 'the same', 'again',
            'one more', 'another'
        ]
        text_lower = text.lower()
        return any(text_lower.startswith(ind) or f" {ind} " in text_lower
                   for ind in followup_indicators)
    
    def clear(self):
        """Clear conversation history."""
        with self._lock:
            self._history.clear()
            self._last_entity_references.clear()


# ============================================================================
# DISAMBIGUATION ENGINE ("Did you mean...?")
# ============================================================================

@dataclass
class DisambiguationOption:
    """A possible interpretation of an ambiguous command."""
    intent: str
    description: str
    confidence: float
    example_phrase: str


class DisambiguationEngine:
    """
    Generates "Did you mean...?" suggestions for ambiguous commands.
    This is a key feature that makes ChatGPT voice feel more intelligent.
    """
    
    # Confidence thresholds
    HIGH_CONFIDENCE = 0.7      # Execute directly
    MEDIUM_CONFIDENCE = 0.4   # Suggest with confirmation
    LOW_CONFIDENCE = 0.25     # Offer multiple options
    
    # Similar intent groups (commands that are often confused)
    INTENT_GROUPS = {
        'media': ['play_music', 'pause_music', 'stop_music', 'next_track'],
        'apps': ['open_browser', 'app_control', 'close_app'],
        'system': ['shutdown', 'restart', 'sleep', 'lock_screen'],
        'window': ['minimize', 'maximize', 'restore', 'close_window'],
        'search': ['search', 'google', 'find_file', 'look_up'],
    }
    
    # Human-readable intent descriptions
    INTENT_DESCRIPTIONS = {
        'open_browser': 'Open your web browser',
        'app_control': 'Open or close an application',
        'search': 'Search the web for something',
        'play_music': 'Play music or media',
        'pause_music': 'Pause the current media',
        'stop_music': 'Stop playing media',
        'shutdown': 'Shut down the computer',
        'restart': 'Restart the computer',
        'sleep': 'Put the computer to sleep',
        'minimize': 'Minimize a window',
        'maximize': 'Maximize a window',
        'volume': 'Adjust the volume',
        'brightness': 'Adjust screen brightness',
        'time': 'Tell the current time',
        'window_control': 'Control window size/position',
        'help': 'Show available commands',
    }
    
    def __init__(self):
        self._similarity_cache: Dict[Tuple[str, str], float] = {}
    
    def needs_disambiguation(self, confidence: float, alternatives: List[Tuple[str, float]] = None) -> bool:
        """Check if disambiguation is needed based on confidence."""
        if confidence >= self.HIGH_CONFIDENCE:
            return False
        
        if alternatives and len(alternatives) > 1:
            # Check if top alternatives are close in confidence
            top_scores = sorted([s for _, s in alternatives], reverse=True)[:2]
            if len(top_scores) >= 2 and top_scores[0] - top_scores[1] < 0.15:
                return True
        
        return confidence < self.MEDIUM_CONFIDENCE
    
    def get_similar_intents(self, intent: str) -> List[str]:
        """Get intents that might be confused with the given intent."""
        similar = []
        for group_name, group_intents in self.INTENT_GROUPS.items():
            if intent in group_intents:
                similar.extend([i for i in group_intents if i != intent])
        return similar
    
    def generate_disambiguation_response(self,
                                          text: str,
                                          top_intent: str,
                                          confidence: float,
                                          alternatives: List[Tuple[str, float]] = None
                                          ) -> Dict[str, Any]:
        """
        Generate a 'Did you mean...?' response with options.
        
        Returns:
            {
                'type': 'disambiguation',
                'message': "I'm not sure what you meant. Did you mean...",
                'options': [
                    {'intent': 'play_music', 'description': 'Play music', 'confidence': 0.4},
                    {'intent': 'search', 'description': 'Search for "play music"', 'confidence': 0.35}
                ],
                'original_text': text
            }
        """
        options = []
        
        # Add the top intent
        options.append(DisambiguationOption(
            intent=top_intent,
            description=self.INTENT_DESCRIPTIONS.get(top_intent, top_intent.replace('_', ' ').title()),
            confidence=confidence,
            example_phrase=self._generate_example(top_intent, text)
        ))
        
        # Add alternatives if provided
        if alternatives:
            for intent, score in alternatives[:3]:  # Top 3 alternatives
                if intent != top_intent and score >= self.LOW_CONFIDENCE:
                    options.append(DisambiguationOption(
                        intent=intent,
                        description=self.INTENT_DESCRIPTIONS.get(intent, intent.replace('_', ' ').title()),
                        confidence=score,
                        example_phrase=self._generate_example(intent, text)
                    ))
        
        # Filter out 'unknown' intent from options
        options = [opt for opt in options if opt.intent != 'unknown']
        
        # Generate the disambiguation message
        if not options:
            # No valid options, return clarification request
            return {
                'type': 'clarification',
                'message': random.choice(self.generate_clarification_phrases()),
                'options': [],
                'original_text': text,
                'top_intent': 'unknown',
                'top_confidence': confidence
            }
        elif len(options) == 1:
            message = f"Did you mean to {options[0].description.lower()}?"
        else:
            message = "I'm not quite sure what you meant. Did you mean one of these?"
        
        return {
            'type': 'disambiguation',
            'message': message,
            'options': [
                {
                    'intent': opt.intent,
                    'description': opt.description,
                    'confidence': opt.confidence,
                    'example': opt.example_phrase
                }
                for opt in sorted(options, key=lambda x: x.confidence, reverse=True)
            ],
            'original_text': text,
            'top_intent': top_intent,
            'top_confidence': confidence
        }
    
    def generate_clarification_phrases(self) -> List[str]:
        """
        Get varied clarification phrases (avoids robotic repetition).
        ChatGPT uses many variations to sound natural.
        """
        return [
            "I didn't quite catch that. Could you say it again?",
            "Sorry, I'm not sure I understood. What would you like me to do?",
            "I didn't get that clearly. Could you rephrase?",
            "I'm having trouble understanding. Could you try again?",
            "Could you repeat that? I want to make sure I help you correctly.",
            "I heard you, but I'm not certain what you'd like. Could you clarify?",
        ]
    
    def _generate_example(self, intent: str, original_text: str) -> str:
        """Generate an example phrase for the intent."""
        examples = {
            'play_music': "Play music",
            'search': f'Search for "{original_text}"',
            'open_browser': "Open the browser",
            'app_control': "Open an application",
            'shutdown': "Shut down the computer",
            'volume': "Adjust the volume",
            'time': "What time is it?",
        }
        return examples.get(intent, f"Do {intent.replace('_', ' ')}")


# ============================================================================
# RESPONSE VARIATION SYSTEM (Avoids robotic repetition)
# ============================================================================

class ResponseVariation:
    """
    Provides varied responses for the same intent to avoid sounding robotic.
    ChatGPT never says the exact same thing twice.
    """
    
    # Response templates with multiple variations
    RESPONSE_TEMPLATES = {
        'open_browser': [
            "Opening your browser now.",
            "Starting up the browser for you.",
            "Here comes your browser!",
            "Launching the browser.",
            "Opening the web browser now.",
        ],
        'search': [
            "Searching for {query}.",
            "Looking up {query} for you.",
            "Let me find that - searching for {query}.",
            "Searching the web for {query}.",
            "On it! Searching for {query}.",
        ],
        'time': [
            "It's {time} right now.",
            "The current time is {time}.",
            "Right now it's {time}.",
            "{time}.",
            "It's currently {time}.",
        ],
        'play_music': [
            "Playing music now.",
            "Starting the music.",
            "Here's some music for you!",
            "Music coming right up.",
            "Playing your tunes.",
        ],
        'app_control_open': [
            "Opening {app} for you.",
            "Launching {app} now.",
            "Starting up {app}.",
            "Here comes {app}!",
            "{app} is on its way.",
        ],
        'app_control_close': [
            "Closing {app}.",
            "Shutting down {app}.",
            "Bye bye {app}!",
            "{app} is now closed.",
            "Closed {app} for you.",
        ],
        'volume_up': [
            "Turning the volume up.",
            "Making it louder.",
            "Volume increased.",
            "Cranking up the volume!",
        ],
        'volume_down': [
            "Lowering the volume.",
            "Making it quieter.",
            "Volume decreased.",
            "Turning it down.",
        ],
        'volume_mute': [
            "Muted.",
            "Audio muted.",
            "Silence!",
            "Volume is now muted.",
        ],
        'shutdown': [
            "Shutting down now. Goodbye!",
            "Powering off. See you later!",
            "Shutting down the computer.",
            "Bye for now! Shutting down.",
        ],
        'confirm': [
            "Are you sure you want to {action}?",
            "Just to confirm - you want to {action}?",
            "Should I go ahead and {action}?",
            "Do you really want to {action}?",
        ],
        'error_unclear': [
            "I didn't catch that. Could you say it again?",
            "Sorry, I didn't understand. What was that?",
            "Could you repeat that?",
            "I'm not sure what you meant. Try again?",
            "I didn't quite get that. Once more?",
        ],
        'error_unknown': [
            "I'm not sure how to do that.",
            "That's not something I can help with yet.",
            "I don't have that capability right now.",
            "Hmm, I don't know how to do that one.",
        ],
        'greeting': [
            "Hi! What can I do for you?",
            "Hey there! How can I help?",
            "Hello! What would you like?",
            "Hi! I'm listening.",
        ],
        'acknowledgment': [
            "Got it!",
            "Done!",
            "All set!",
            "You got it!",
            "Sure thing!",
        ],
        'thinking': [
            "Let me think about that...",
            "One moment...",
            "Working on it...",
            "Just a second...",
        ],
    }
    
    def __init__(self):
        self._last_used: Dict[str, int] = {}  # Track last used template index
    
    def get_response(self, template_key: str, **kwargs) -> str:
        """
        Get a varied response for a template key.
        Avoids repeating the same response consecutively.
        """
        templates = self.RESPONSE_TEMPLATES.get(template_key)
        if not templates:
            return f"[No template for: {template_key}]"
        
        # Get last used index and pick a different one
        last_idx = self._last_used.get(template_key, -1)
        available_indices = [i for i in range(len(templates)) if i != last_idx]
        
        if not available_indices:
            available_indices = list(range(len(templates)))
        
        chosen_idx = random.choice(available_indices)
        self._last_used[template_key] = chosen_idx
        
        template = templates[chosen_idx]
        
        # Format with provided kwargs
        try:
            return template.format(**kwargs)
        except KeyError:
            return template  # Return as-is if formatting fails


# ============================================================================
# INTELLIGENT RESPONSE ENGINE (Main class)
# ============================================================================

class IntelligentResponseEngine:
    """
    Main intelligent response engine combining all features:
    - Disambiguation
    - Context awareness
    - Response variation
    - Streaming responses
    
    Usage:
        engine = IntelligentResponseEngine()
        
        # Process a command
        result = engine.process_command(text, parsed_result)
        
        # Check if disambiguation needed
        if result['needs_disambiguation']:
            # Present options to user
            print(result['disambiguation_message'])
        else:
            # Execute and respond
            response = result['response']
    """
    
    def __init__(self):
        self.context = ConversationContext()
        self.disambiguation = DisambiguationEngine()
        self.variation = ResponseVariation()
        self._command_handlers: Dict[str, Callable] = {}
    
    def register_handler(self, intent: str, handler: Callable):
        """Register a command handler for an intent."""
        self._command_handlers[intent] = handler
    
    def process_command(self, text: str, parsed: Dict[str, Any],
                        execute: bool = False) -> Dict[str, Any]:
        """
        Process a parsed command intelligently.
        
        Args:
            text: Original user text
            parsed: Parsed command result (from NLPCommandParser)
            execute: Whether to execute the command or just generate response
        
        Returns:
            {
                'intent': str,
                'confidence': float,
                'needs_disambiguation': bool,
                'disambiguation_message': Optional[str],
                'disambiguation_options': Optional[List],
                'response': str,
                'response_stream': Optional[Generator],
                'entities': Dict,
                'context_used': bool,
                'executed': bool
            }
        """
        intent = parsed.get('type', 'unknown')
        confidence = parsed.get('confidence', 1.0)
        entities = {k: v for k, v in parsed.items()
                    if k not in ('type', 'raw', 'confidence', 'method')}
        
        # Check for follow-up and resolve pronouns
        context_used = False
        if self.context.is_followup_question(text):
            entities = self.context.resolve_pronouns(text, entities)
            context_used = True
        
        # Get alternatives for disambiguation (if available from NLP)
        alternatives = parsed.get('alternatives', [])
        
        # Check if disambiguation is needed
        needs_disambiguation = self.disambiguation.needs_disambiguation(confidence, alternatives)
        
        result = {
            'intent': intent,
            'confidence': confidence,
            'entities': entities,
            'context_used': context_used,
            'original_text': text,
            'needs_disambiguation': needs_disambiguation,
            'disambiguation_message': None,
            'disambiguation_options': None,
            'response': None,
            'response_stream': None,
            'executed': False,
        }
        
        if needs_disambiguation:
            # Generate disambiguation response
            disambig = self.disambiguation.generate_disambiguation_response(
                text, intent, confidence, alternatives
            )
            result['disambiguation_message'] = disambig['message']
            result['disambiguation_options'] = disambig['options']
            result['response'] = disambig['message']
            
        else:
            # Generate response
            response = self._generate_response(intent, entities)
            result['response'] = response
            result['response_stream'] = StreamingResponse(response).stream
            
            # Execute if requested
            if execute and intent in self._command_handlers:
                try:
                    self._command_handlers[intent](entities)
                    result['executed'] = True
                except Exception as e:
                    logger.error(f"Execution failed for {intent}: {e}")
                    result['response'] = self.variation.get_response('error_unknown')
        
        # Add to conversation context
        self.context.add_turn(
            role='user',
            content=text,
            intent=intent,
            entities=entities,
            confidence=confidence
        )
        
        if result['response']:
            self.context.add_turn(
                role='assistant',
                content=result['response']
            )
        
        return result
    
    def _generate_response(self, intent: str, entities: Dict[str, Any]) -> str:
        """Generate a varied response for the intent."""
        
        if intent == 'unknown':
            return self.variation.get_response('error_unclear')
        
        if intent == 'time':
            from datetime import datetime
            now = datetime.now()
            time_str = now.strftime('%I:%M %p')
            return self.variation.get_response('time', time=time_str)
        
        if intent == 'search':
            query = entities.get('query', 'that')
            return self.variation.get_response('search', query=query)
        
        if intent == 'app_control':
            app = entities.get('app', 'the application')
            action = entities.get('action', 'open')
            if action in ('close', 'quit', 'exit', 'kill'):
                return self.variation.get_response('app_control_close', app=app)
            return self.variation.get_response('app_control_open', app=app)
        
        if intent == 'volume':
            action = entities.get('action', 'adjust')
            if action == 'mute':
                return self.variation.get_response('volume_mute')
            elif action == 'up':
                return self.variation.get_response('volume_up')
            elif action == 'down':
                return self.variation.get_response('volume_down')
            level = entities.get('level')
            if level is not None:
                return f"Setting volume to {level}%."
            return "Adjusting the volume."
        
        if intent == 'shutdown':
            return self.variation.get_response('shutdown')
        
        if intent == 'play_music':
            return self.variation.get_response('play_music')
        
        if intent == 'open_browser':
            return self.variation.get_response('open_browser')
        
        if intent == 'help':
            return "I can open apps, search the web, control volume, play music, and more. What would you like?"
        
        # Generic fallback
        template_key = intent.replace('_', ' ')
        return f"Okay, {template_key}."
    
    def handle_disambiguation_choice(self, choice_index: int,
                                      last_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle user's choice from disambiguation options.
        
        Args:
            choice_index: Index of chosen option (0-based)
            last_result: The previous disambiguation result
        
        Returns:
            New processed result with chosen intent
        """
        options = last_result.get('disambiguation_options', [])
        if not options or choice_index >= len(options):
            return {
                'error': True,
                'response': "Sorry, that wasn't a valid choice."
            }
        
        chosen = options[choice_index]
        chosen_intent = chosen['intent']
        
        # Create a new parsed result with the chosen intent
        new_parsed = {
            'type': chosen_intent,
            'confidence': 1.0,  # User confirmed, so confidence is high
            'raw': last_result.get('original_text', ''),
            **last_result.get('entities', {})
        }
        
        return self.process_command(
            last_result.get('original_text', ''),
            new_parsed,
            execute=True
        )
    
    def get_clarification_response(self) -> str:
        """Get a varied 'I didn't understand' response."""
        return random.choice(self.disambiguation.generate_clarification_phrases())
    
    def clear_context(self):
        """Clear conversation context (e.g., after timeout or user request)."""
        self.context.clear()


# ============================================================================
# QUICK RESPONSE HELPERS (For drop-in use)
# ============================================================================

# Global instance
_engine: Optional[IntelligentResponseEngine] = None


def get_intelligent_response_engine() -> IntelligentResponseEngine:
    """Get the global intelligent response engine instance."""
    global _engine
    if _engine is None:
        _engine = IntelligentResponseEngine()
    return _engine


def process_command_intelligently(text: str, parsed: Dict[str, Any],
                                   execute: bool = False) -> Dict[str, Any]:
    """
    Convenience function to process a command intelligently.
    
    Usage:
        from core.intelligent_response import process_command_intelligently
        
        parsed = parse_command_nlp("play some music")
        result = process_command_intelligently("play some music", parsed)
        
        if result['needs_disambiguation']:
            speak(result['disambiguation_message'])
        else:
            speak(result['response'])
    """
    return get_intelligent_response_engine().process_command(text, parsed, execute)


def get_varied_response(template_key: str, **kwargs) -> str:
    """
    Get a varied response without using the full engine.
    
    Usage:
        response = get_varied_response('search', query='cats')
    """
    return ResponseVariation().get_response(template_key, **kwargs)


def get_clarification() -> str:
    """Get a clarification response for unclear input."""
    return get_intelligent_response_engine().get_clarification_response()


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Demo the intelligent response system
    engine = IntelligentResponseEngine()
    
    print("=== VoxMind Intelligent Response Demo ===\n")
    
    # Test 1: High confidence command
    print("Test 1: Clear command")
    result = engine.process_command(
        "open chrome",
        {'type': 'app_control', 'app': 'chrome', 'confidence': 0.85}
    )
    print(f"  Input: 'open chrome'")
    print(f"  Response: {result['response']}")
    print(f"  Needs disambiguation: {result['needs_disambiguation']}")
    print()
    
    # Test 2: Ambiguous command
    print("Test 2: Ambiguous command")
    result = engine.process_command(
        "play",
        {
            'type': 'play_music', 
            'confidence': 0.35,
            'alternatives': [('search', 0.32), ('app_control', 0.28)]
        }
    )
    print(f"  Input: 'play'")
    print(f"  Needs disambiguation: {result['needs_disambiguation']}")
    print(f"  Message: {result['disambiguation_message']}")
    print(f"  Options: {[o['description'] for o in result['disambiguation_options']]}")
    print()
    
    # Test 3: Follow-up with pronoun resolution
    print("Test 3: Follow-up command")
    engine.process_command(
        "open notepad",
        {'type': 'app_control', 'app': 'notepad', 'confidence': 0.9}
    )
    result = engine.process_command(
        "now close it",
        {'type': 'app_control', 'action': 'close', 'confidence': 0.8}
    )
    print(f"  First: 'open notepad'")
    print(f"  Second: 'now close it'")
    print(f"  Resolved entity: {result['entities'].get('app', 'NOT RESOLVED')}")
    print(f"  Context used: {result['context_used']}")
    print(f"  Response: {result['response']}")
    print()
    
    # Test 4: Response variation
    print("Test 4: Response variation (same intent, different responses)")
    for i in range(3):
        result = engine.process_command(
            "what time is it",
            {'type': 'time', 'confidence': 0.95}
        )
        print(f"  Response {i+1}: {result['response']}")
    print()
    
    # Test 5: Streaming response
    print("Test 5: Streaming response")
    result = engine.process_command(
        "search for python tutorials",
        {'type': 'search', 'query': 'python tutorials', 'confidence': 0.9}
    )
    print("  Streaming: ", end='')
    for chunk in result['response_stream']():
        print(chunk, end='', flush=True)
    print("\n")
    
    print("=== Demo Complete ===")
