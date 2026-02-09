"""
VoxMind Natural Language Engine
================================
Advanced arbitrary language processing and word prediction for life-like AI interaction.

Features:
- Fuzzy matching for typos and speech errors
- Word prediction and sentence completion
- Contextual conversation memory
- Dynamic response generation
- Semantic understanding beyond keywords

This is the core intelligence that makes VoxMind feel intelligent.
"""

import re
import random
import logging
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime
import threading

logger = logging.getLogger(__name__)

# ============================================================================
# FUZZY MATCHING - Handle typos, speech errors, partial words
# ============================================================================

class FuzzyMatcher:
    """Handles approximate string matching for natural speech variations."""
    
    # Common speech-to-text errors and variations
    PHONETIC_SUBSTITUTIONS = {
        # VoxMind variations
        'voxmind': ['box mind', 'vox mind', 'fox mind', 'docks mind', 'rocks mind', 'vox', 'boxmind'],
        
        # Common words with speech errors
        'please': ['pleas', 'pls', 'plz', 'pleez', 'please'],
        'computer': ['compter', 'compooter', 'puter', 'pc'],
        'volume': ['volum', 'volumne', 'vollume', 'vol'],
        'brightness': ['brightnes', 'brigtness', 'brighness', 'bright'],
        'search': ['serch', 'sarch', 'searsh', 'srch'],
        'google': ['googel', 'gogle', 'guggle', 'googl'],
        'open': ['opn', 'oepn', 'opne', 'ope'],
        'close': ['clse', 'cloze', 'cloes', 'clos'],
        'what': ['wat', 'wut', 'whut', 'wha'],
        'time': ['tiem', 'tym', 'taim'],
        'weather': ['wether', 'wheather', 'waether', 'wheater'],
        'music': ['musik', 'musci', 'mucic', 'musi'],
        'spotify': ['spotfy', 'spotifi', 'spot if i', 'spot a fly'],
        'youtube': ['utube', 'you tube', 'youtub', 'u tube', 'new tube'],
        'okay': ['ok', 'okey', 'k', 'oke'],
        'thanks': ['thx', 'thanx', 'thnks', 'thank', 'tanks'],
        'yes': ['yep', 'yeah', 'yea', 'ya', 'yup', 'ys', 'yah'],
        'no': ['nope', 'nah', 'na', 'nop', 'know'],
        
        # Application names
        'chrome': ['crome', 'chrom', 'krome'],
        'firefox': ['fire fox', 'foxfire', 'firefix'],
        'notepad': ['note pad', 'notpad', 'not pad'],
        'calculator': ['calc', 'calcualtor', 'calulator'],
        'settings': ['setting', 'setings', 'seting'],
        'terminal': ['termnial', 'treminal', 'termnal'],
        'whatsapp': ['what sap', 'whats app', 'watsapp', 'what app'],
        
        # Commands
        'increase': ['increace', 'increse', 'encreas'],
        'decrease': ['decreace', 'decrese', 'decreas'],
        'minimize': ['minimise', 'minmize', 'miminize'],
        'maximize': ['maximise', 'maxmize', 'maxamize'],
        'shutdown': ['shut down', 'shutdwn', 'shutdoun'],
        'restart': ['re start', 'restat', 'restrt'],
        
        # Filler words (remove these)
        '': ['um', 'uh', 'er', 'ah', 'like', 'you know'],
    }
    
    # Pre-compiled regex patterns for performance
    _compiled_patterns: Dict[str, List[Tuple[re.Pattern, str]]] = {}
    _patterns_compiled = False
    
    @classmethod
    def _compile_patterns(cls):
        """Pre-compile regex patterns for faster matching."""
        if cls._patterns_compiled:
            return
        for correct_word, variations in cls.PHONETIC_SUBSTITUTIONS.items():
            patterns = []
            for variation in variations:
                pattern = re.compile(r'\b' + re.escape(variation) + r'\b', re.IGNORECASE)
                patterns.append((pattern, correct_word))
            cls._compiled_patterns[correct_word] = patterns
        cls._patterns_compiled = True
    
    @classmethod
    def levenshtein_distance(cls, s1: str, s2: str) -> int:
        """Calculate edit distance between two strings."""
        if len(s1) < len(s2):
            return cls.levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    @classmethod
    def similarity_ratio(cls, s1: str, s2: str) -> float:
        """Return similarity ratio between 0.0 and 1.0."""
        if not s1 or not s2:
            return 0.0
        distance = cls.levenshtein_distance(s1.lower(), s2.lower())
        max_len = max(len(s1), len(s2))
        return 1.0 - (distance / max_len)
    
    @classmethod
    def find_best_match(cls, word: str, candidates: List[str], threshold: float = 0.7) -> Optional[str]:
        """Find the best matching word from candidates."""
        word_lower = word.lower()
        best_match = None
        best_score = threshold
        
        for candidate in candidates:
            score = cls.similarity_ratio(word_lower, candidate.lower())
            if score > best_score:
                best_score = score
                best_match = candidate
        
        return best_match
    
    @classmethod
    def correct_text(cls, text: str) -> str:
        """Apply phonetic corrections to text using pre-compiled patterns."""
        cls._compile_patterns()
        corrected = text.lower()
        
        for correct_word, patterns in cls._compiled_patterns.items():
            for pattern, replacement in patterns:
                corrected = pattern.sub(replacement, corrected)
        
        return corrected


# ============================================================================
# WORD PREDICTION - Anticipate and complete user input
# ============================================================================

class WordPredictor:
    """N-gram based word prediction for natural conversation flow."""
    
    def __init__(self):
        # Lock for thread-safe updates (must be created first!)
        self._lock = threading.Lock()
        
        # Bigram and trigram models for word prediction
        self.bigrams: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.trigrams: Dict[Tuple[str, str], Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.word_frequencies: Dict[str, int] = defaultdict(int)
        
        # Common command patterns
        self._train_on_patterns()
    
    def _train_on_patterns(self):
        """Train on common voice command patterns."""
        training_phrases = [
            # Browser/Search
            "open browser", "open google chrome", "open firefox",
            "search for", "search google for", "look up", "find information about",
            "what is", "who is", "where is", "when is", "how to",
            "tell me about", "show me", "find me",
            
            # System control
            "turn on", "turn off", "set volume to", "increase volume", "decrease volume",
            "set brightness to", "increase brightness", "decrease brightness",
            "mute audio", "unmute audio", "lock screen", "shutdown computer",
            "restart computer", "open settings",
            
            # App control
            "open application", "close application", "launch", "start",
            "open notepad", "open calculator", "open spotify", "open youtube",
            "play music", "pause music", "next song", "previous song",
            "stop music", "resume music",
            
            # Time/Date
            "what time is it", "what is the time", "what is the date",
            "what day is it", "set alarm for", "set timer for", "remind me to",
            
            # Conversational
            "how are you", "what can you do", "help me", "thank you",
            "yes please", "no thanks", "cancel that", "never mind",
            "that's all", "goodbye", "good morning", "good night",
            
            # Weather
            "what is the weather", "how is the weather", "weather forecast",
            "will it rain", "temperature today", "weather in",
        ]
        
        for phrase in training_phrases:
            self.learn_from_text(phrase)
    
    def learn_from_text(self, text: str):
        """Learn word patterns from user input."""
        words = text.lower().split()
        if not words:
            return
        
        with self._lock:
            # Update frequencies
            for word in words:
                self.word_frequencies[word] += 1
            
            # Update bigrams
            for i in range(len(words) - 1):
                self.bigrams[words[i]][words[i + 1]] += 1
            
            # Update trigrams
            for i in range(len(words) - 2):
                key = (words[i], words[i + 1])
                self.trigrams[key][words[i + 2]] += 1
    
    def predict_next_word(self, context: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Predict the next word based on context."""
        words = context.lower().split()
        predictions = []
        
        if len(words) >= 2:
            # Try trigram prediction first
            key = (words[-2], words[-1])
            if key in self.trigrams:
                total = sum(self.trigrams[key].values())
                predictions = [
                    (word, count / total)
                    for word, count in sorted(
                        self.trigrams[key].items(),
                        key=lambda x: -x[1]
                    )[:top_k]
                ]
        
        if not predictions and words:
            # Fall back to bigram prediction
            last_word = words[-1]
            if last_word in self.bigrams:
                total = sum(self.bigrams[last_word].values())
                predictions = [
                    (word, count / total)
                    for word, count in sorted(
                        self.bigrams[last_word].items(),
                        key=lambda x: -x[1]
                    )[:top_k]
                ]
        
        return predictions
    
    def complete_partial_word(self, partial: str, top_k: int = 5) -> List[str]:
        """Complete a partially typed word."""
        partial_lower = partial.lower()
        
        candidates = [
            (word, freq)
            for word, freq in self.word_frequencies.items()
            if word.startswith(partial_lower)
        ]
        
        # Sort by frequency
        candidates.sort(key=lambda x: -x[1])
        
        return [word for word, _ in candidates[:top_k]]


# ============================================================================
# CONVERSATION MEMORY - Remember context across interactions
# ============================================================================

class ConversationMemory:
    """Maintains conversation context for natural dialogue."""
    
    def __init__(self, max_history: int = 20):
        self.max_history = max_history
        self.history: List[Dict[str, Any]] = []
        self.entities: Dict[str, Any] = {}  # Extracted entities from conversation
        self.user_preferences: Dict[str, Any] = {}
        self.last_command: Optional[str] = None
        self.last_response: Optional[str] = None
        self.session_start = datetime.now()
        self._lock = threading.Lock()
    
    def add_exchange(self, user_input: str, response: str, intent: Optional[str] = None,
                     entities: Optional[Dict] = None):
        """Record a conversation exchange."""
        with self._lock:
            exchange = {
                'timestamp': datetime.now(),
                'user': user_input,
                'assistant': response,
                'intent': intent,
                'entities': entities or {}
            }
            
            self.history.append(exchange)
            self.last_command = user_input
            self.last_response = response
            
            # Update entity memory
            if entities:
                self.entities.update(entities)
            
            # Trim history if needed
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]
    
    def get_context_summary(self) -> str:
        """Get a summary of recent context for response generation."""
        if not self.history:
            return ""
        
        recent = self.history[-3:]  # Last 3 exchanges
        summary_parts = []
        
        for exchange in recent:
            if exchange.get('intent'):
                summary_parts.append(f"User asked about: {exchange['intent']}")
        
        return "; ".join(summary_parts)
    
    def resolve_reference(self, text: str) -> str:
        """Resolve pronouns and references based on context."""
        # Handle 'it', 'that', 'this' references
        pronouns = ['it', 'that', 'this', 'those', 'them']
        
        text_lower = text.lower()
        
        for pronoun in pronouns:
            pattern = r'\b' + pronoun + r'\b'
            if re.search(pattern, text_lower):
                # Try to find what 'it' refers to
                if self.entities.get('query'):
                    text = re.sub(pattern, self.entities['query'], text, flags=re.IGNORECASE)
                elif self.entities.get('app_name'):
                    text = re.sub(pattern, self.entities['app_name'], text, flags=re.IGNORECASE)
        
        return text
    
    def is_follow_up(self, text: str) -> bool:
        """Detect if this is a follow-up to the previous command."""
        follow_up_indicators = [
            'also', 'and also', 'what about', 'how about',
            'same for', 'do that', 'again', 'one more',
            'another', 'more', 'else', 'too'
        ]
        
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in follow_up_indicators)
    
    def get_last_intent(self) -> Optional[str]:
        """Get the last recognized intent."""
        if self.history:
            return self.history[-1].get('intent')
        return None


# ============================================================================
# NATURAL RESPONSE GENERATOR - Dynamic, non-templated responses
# ============================================================================

class NaturalResponseGenerator:
    """Generates dynamic, intelligent responses."""
    
    def __init__(self, user_name: str = "sir"):
        self.user_name = user_name
        self.conversation_memory = ConversationMemory()
        
        # Response variation pools
        self.affirmations = [
            "Certainly", "Of course", "Right away", "Understood",
            "At once", "As you wish", "Absolutely", "Consider it done",
            "On it", "Will do"
        ]
        
        self.acknowledgments = [
            "I see", "Got it", "Understood", "Noted", "Alright"
        ]
        
        self.transitions = [
            "Now", "Alright", "Very well", "Moving on", "Next"
        ]
        
        self.personality_traits = {
            'helpful': 0.9,
            'formal': 0.6,
            'witty': 0.3,
            'concise': 0.7
        }
    
    def set_user_name(self, name: str):
        """Update the user's name."""
        self.user_name = name
    
    def _get_time_greeting(self) -> str:
        """Get appropriate greeting based on time of day."""
        hour = datetime.now().hour
        
        if 5 <= hour < 12:
            return f"Good morning, {self.user_name}"
        elif 12 <= hour < 17:
            return f"Good afternoon, {self.user_name}"
        elif 17 <= hour < 21:
            return f"Good evening, {self.user_name}"
        else:
            return f"Hello, {self.user_name}"
    
    def generate_confirmation(self, action: str, **kwargs) -> str:
        """Generate a natural confirmation response."""
        affirmation = random.choice(self.affirmations)
        
        templates = [
            f"{affirmation}, {self.user_name}. {action}",
            f"{action}. {affirmation}.",
            f"{affirmation}. {action}",
        ]
        
        response = random.choice(templates)
        
        # Apply any kwargs
        for key, value in kwargs.items():
            response = response.replace('{' + key + '}', str(value))
        
        return response
    
    def generate_status_update(self, status: str, detail: Optional[str] = None) -> str:
        """Generate a status update response."""
        if detail:
            return f"{status}. {detail}"
        return status
    
    def generate_error_response(self, error_type: str = "general") -> str:
        """Generate a natural error response."""
        error_responses = {
            'general': [
                f"I'm afraid I couldn't complete that request, {self.user_name}.",
                f"My apologies, {self.user_name}. Something went wrong.",
                f"I encountered an issue, {self.user_name}. Shall I try again?",
            ],
            'not_understood': [
                f"I didn't quite catch that, {self.user_name}. Could you rephrase?",
                f"I'm not sure I understood, {self.user_name}. Try again?",
                f"Pardon me, {self.user_name}. Could you repeat that?",
            ],
            'not_found': [
                f"I couldn't find what you're looking for, {self.user_name}.",
                f"No results found, {self.user_name}. Perhaps try different terms?",
            ],
            'permission': [
                f"I don't have permission to do that, {self.user_name}.",
                f"That action requires additional permissions, {self.user_name}.",
            ]
        }
        
        responses = error_responses.get(error_type, error_responses['general'])
        return random.choice(responses)
    
    def generate_follow_up(self, context: str) -> str:
        """Generate a follow-up response based on context."""
        follow_ups = [
            f"Is there anything else, {self.user_name}?",
            f"What else can I help with?",
            f"Shall I do anything else?",
            f"At your service, {self.user_name}.",
        ]
        return random.choice(follow_ups)
    
    def generate_contextual_response(self, intent: str, entities: Dict[str, Any],
                                      success: bool = True) -> str:
        """Generate a response based on intent and entities."""
        if not success:
            return self.generate_error_response()
        
        affirmation = random.choice(self.affirmations)
        
        response_templates = {
            'search': [
                f"{affirmation}. Searching for {{query}} now.",
                f"Let me look up {{query}} for you, {self.user_name}.",
                f"Pulling up results for {{query}}.",
            ],
            'open_browser': [
                f"Opening your browser now, {self.user_name}.",
                f"{affirmation}. Launching the browser.",
                f"Browser coming right up.",
            ],
            'time': [
                f"It's currently {{time}}, {self.user_name}.",
                f"The time is {{time}}.",
                f"Right now it's {{time}}.",
            ],
            'volume': [
                f"Adjusting volume now.",
                f"{affirmation}. Volume updated.",
                f"Sound levels adjusted.",
            ],
            'app_control': [
                f"{affirmation}. Opening {{app_name}} for you.",
                f"Launching {{app_name}} now.",
                f"{{app_name}} coming right up, {self.user_name}.",
            ],
            'greeting': [
                self._get_time_greeting() + ". How may I assist you?",
                f"Hello, {self.user_name}. What can I do for you?",
                f"At your service, {self.user_name}.",
            ]
        }
        
        templates = response_templates.get(intent, [f"{affirmation}, {self.user_name}."])
        response = random.choice(templates)
        
        # Fill in entities - use format() for cleaner substitution
        try:
            response = response.format(**entities)
        except KeyError:
            # If some keys are missing, do manual replacement
            for key, value in entities.items():
                response = response.replace('{' + key + '}', str(value))
        
        return response


# ============================================================================
# MAIN NATURAL LANGUAGE ENGINE
# ============================================================================

class NaturalLanguageEngine:
    """
    Main engine combining all NLP capabilities for life-like interaction.
    
    This is what makes VoxMind feel intelligent - understanding arbitrary
    language, predicting intent, and responding naturally.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(NaturalLanguageEngine, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.fuzzy_matcher = FuzzyMatcher()
        self.word_predictor = WordPredictor()
        self.conversation_memory = ConversationMemory()
        self.response_generator = NaturalResponseGenerator()
        
        self._initialized = True
        logger.info("Natural Language Engine initialized")
    
    def set_user_name(self, name: str):
        """Set the user's name for personalized responses."""
        self.response_generator.set_user_name(name)
    
    def preprocess(self, text: str) -> str:
        """
        Preprocess user input for better understanding.
        
        - Correct common speech-to-text errors
        - Resolve pronouns and references
        - Normalize text
        """
        # Step 1: Basic normalization
        text = text.strip()
        
        # Step 2: Apply phonetic corrections
        text = self.fuzzy_matcher.correct_text(text)
        
        # Step 3: Resolve references from conversation context
        text = self.conversation_memory.resolve_reference(text)
        
        return text
    
    def predict_completion(self, partial_input: str) -> List[str]:
        """
        Predict possible completions for partial input.
        Useful for real-time suggestions while user is speaking.
        """
        predictions = self.word_predictor.predict_next_word(partial_input)
        
        if predictions:
            return [word for word, _ in predictions]
        
        # If we have a partial last word, try to complete it
        words = partial_input.split()
        if words:
            last_word = words[-1]
            if len(last_word) >= 2:  # Only predict for words with 2+ chars
                completions = self.word_predictor.complete_partial_word(last_word)
                return completions
        
        return []
    
    def understand(self, text: str) -> Dict[str, Any]:
        """
        Full language understanding pipeline.
        
        Returns a dictionary with:
        - preprocessed_text: Cleaned input
        - is_follow_up: Whether this continues previous conversation
        - predictions: Possible completions
        - context: Relevant conversation context
        """
        preprocessed = self.preprocess(text)
        
        return {
            'original_text': text,
            'preprocessed_text': preprocessed,
            'is_follow_up': self.conversation_memory.is_follow_up(text),
            'predictions': self.predict_completion(preprocessed),
            'context_summary': self.conversation_memory.get_context_summary(),
            'last_intent': self.conversation_memory.get_last_intent(),
        }
    
    def generate_response(self, intent: str, entities: Dict[str, Any],
                          success: bool = True) -> str:
        """Generate a natural response for the given intent."""
        return self.response_generator.generate_contextual_response(
            intent, entities, success
        )
    
    def record_exchange(self, user_input: str, response: str,
                        intent: Optional[str] = None,
                        entities: Optional[Dict] = None):
        """Record a conversation exchange for context learning."""
        self.conversation_memory.add_exchange(user_input, response, intent, entities)
        
        # Learn from user input for better predictions
        self.word_predictor.learn_from_text(user_input)
    
    def get_follow_up_prompt(self) -> str:
        """Get a contextual follow-up prompt."""
        return self.response_generator.generate_follow_up(
            self.conversation_memory.get_context_summary()
        )


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

# Singleton instance
_engine: Optional[NaturalLanguageEngine] = None

def get_engine() -> NaturalLanguageEngine:
    """Get the singleton NaturalLanguageEngine instance."""
    global _engine
    if _engine is None:
        _engine = NaturalLanguageEngine()
    return _engine

def preprocess(text: str) -> str:
    """Preprocess text using the engine."""
    return get_engine().preprocess(text)

def predict(partial_input: str) -> List[str]:
    """Get word predictions."""
    return get_engine().predict_completion(partial_input)

def understand(text: str) -> Dict[str, Any]:
    """Full language understanding."""
    return get_engine().understand(text)


# ============================================================================
# TEST / DEMO
# ============================================================================

if __name__ == "__main__":
    # Demo the Natural Language Engine
    print("=" * 60)
    print("VoxMind Natural Language Engine Demo")
    print("=" * 60)
    
    engine = NaturalLanguageEngine()
    engine.set_user_name("Tony")
    
    # Test fuzzy matching
    print("\n[1] Fuzzy Matching (handling speech errors):")
    test_phrases = [
        "serch for python tutorials",  # 'serch' -> 'search'
        "opn the browser",  # 'opn' -> 'open'
        "wat time is it",  # 'wat' -> 'what'
        "increase volumne",  # 'volumne' -> 'volume'
    ]
    for phrase in test_phrases:
        corrected = engine.preprocess(phrase)
        print(f"  '{phrase}' -> '{corrected}'")
    
    # Test word prediction
    print("\n[2] Word Prediction:")
    test_contexts = [
        "open",
        "search for",
        "what is the",
        "set volume",
    ]
    for context in test_contexts:
        predictions = engine.predict_completion(context)
        print(f"  '{context}' -> {predictions[:3]}")
    
    # Test response generation
    print("\n[3] Natural Response Generation:")
    responses = [
        engine.generate_response("search", {"query": "weather forecast"}),
        engine.generate_response("app_control", {"app_name": "Spotify"}),
        engine.generate_response("time", {"time": "3:45 PM"}),
        engine.generate_response("greeting", {}),
    ]
    for resp in responses:
        print(f"  -> {resp}")
    
    # Test conversation memory
    print("\n[4] Conversation Context:")
    engine.record_exchange("search for python", "Searching for python", "search", {"query": "python"})
    engine.record_exchange("tell me more about it", "Here's more info on python", "search", {"query": "python"})
    
    # Now test reference resolution
    test_ref = "download it"
    resolved = engine.preprocess(test_ref)
    print(f"  '{test_ref}' (with context) -> '{resolved}'")
    
    print("\n" + "=" * 60)
    print("Engine ready for intelligent interaction!")
    print("=" * 60)
