"""
NLP-enhanced command parser using sentence transformers for better intent classification.

Enhanced with:
- Multi-intent scoring with alternatives for disambiguation
- Confidence calibration for "Did you mean...?" suggestions
- Better entity extraction with contextual understanding
"""
from typing import Dict, Any, List, Tuple, Optional
import re
import logging
import threading

logger = logging.getLogger(__name__)

# Defer heavy imports - only load when needed
NLP_AVAILABLE = False
SentenceTransformer = None
np = None

def _check_nlp_available():
    """Check if sentence-transformers is available without importing."""
    try:
        import importlib.util
        return importlib.util.find_spec('sentence_transformers') is not None
    except (ImportError, AttributeError, ModuleNotFoundError):
        return False

NLP_AVAILABLE = _check_nlp_available()

class NLPCommandParser:
    _instance = None
    _model_initialized = False
    _loading_thread = None
    _loading_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NLPCommandParser, cls).__new__(cls)
            cls._instance.model = None
            cls._instance.intent_embeddings = None
            cls._instance._initialize_intents()
        return cls._instance
    
    @classmethod
    def preload_model(cls):
        """Start loading the model in background thread."""
        if not NLP_AVAILABLE or cls._model_initialized:
            return
        if cls._loading_thread is None or not cls._loading_thread.is_alive():
            cls._loading_thread = threading.Thread(target=cls._background_load, daemon=True)
            cls._loading_thread.start()
    
    @classmethod
    def _background_load(cls):
        """Load model in background."""
        instance = cls()
        instance._initialize_nlp()

    def _initialize_intents(self):
        """Define intent examples."""
        self.intent_examples = {
            "open_browser": [
                "open browser", "launch browser", "start browser", "go online",
                "open web browser", "start browsing", "launch web browser",
                "open the internet", "browse the web", "open a browser",
                "start a browser", "go to the internet"
            ],
            "time": [
                "what time is it", "current time", "what's the date", "tell me the time",
                "what day is it", "show me the clock", "time now", "what is today's date"
            ],
            "search": [
                "search for python", "google machine learning", "what is AI", "find restaurants",
                "look up information", "search the web", "find me details about",
                "google the weather", "search about", "what is the capital of",
                "tell me about", "find information on", "look for", "google something"
            ],
            "play_music": [
                "play music", "start music", "play a song", "next track", "pause music",
                "stop music", "resume music", "skip song"
            ],
            "shutdown": [
                "shutdown", "restart", "sleep", "lock screen", "power off",
                "turn off computer", "reboot system", "hibernate"
            ],
            "volume": [
                "mute", "volume up", "turn volume to 50", "louder", "quieter",
                "increase volume", "decrease sound", "silence audio", "set volume"
            ],
            "app_control": [
                "open notepad", "launch vscode", "close chrome", "start calculator",
                "run application", "quit program", "open software",
                "close application", "exit program", "kill process", "stop app",
                "launch app", "open app", "close spotify", "quit firefox",
                # Browser apps - should launch app, not open webpage
                "open chrome", "launch chrome", "start chrome", "open google chrome",
                "open firefox", "launch firefox", "start firefox", "open mozilla firefox",
                "open edge", "launch edge", "start edge", "open microsoft edge",
                "open brave", "launch brave", "open opera", "launch opera",
                "open safari", "launch safari", "start safari"
            ],
            "window_control": [
                "minimize chrome", "minimise notepad", "maximize window",
                "restore calculator", "minimize all windows", "show desktop",
                "minimize this", "make it smaller", "full screen", "maximize edge"
            ],
            "brightness": [
                "brightness up", "increase brightness", "make it brighter",
                "dim the screen", "brightness down", "decrease brightness",
                "set brightness to 50", "turn brightness to 80", "lower brightness",
                "screen brighter", "screen dimmer", "full brightness", "max brightness"
            ],
            "help": [
                "help", "what can you do", "who are you", "capabilities",
                "show commands", "list functions", "what are your features"
            ]
        }
        
        if NLP_AVAILABLE and not self._model_initialized:
            self._initialize_nlp()
    
    def _initialize_nlp(self):
        """Initialize the sentence transformer model and compute intent embeddings."""
        global SentenceTransformer, np
        
        with self._loading_lock:
            if self._model_initialized:
                return  # Already loaded by another thread
            
            try:
                # Deferred import of heavy libraries
                if SentenceTransformer is None:
                    logger.info("Loading sentence-transformers...")
                    from sentence_transformers import SentenceTransformer as ST
                    import numpy as numpy_module
                    SentenceTransformer = ST
                    np = numpy_module
                
                logger.info("Loading SentenceTransformer model (this happens once)...")
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                
                # Compute embeddings for all intent examples
                self.intent_embeddings = {}
                for intent, examples in self.intent_examples.items():
                    embeddings = self.model.encode(examples)
                    self.intent_embeddings[intent] = np.mean(embeddings, axis=0)
                
                NLPCommandParser._model_initialized = True
                logger.info("NLP model initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize NLP model: {e}")
                self.model = None

    def extract_entities(self, text: str, intent: str) -> Dict[str, Any]:
        """Extract entities based on intent."""
        entities = {}
        t = text.lower()

        if intent == "search":
            # Extract search query
            search_patterns = [
                r"(?:search|google|look up|find)(?:\s+for)?\s+(.+)",
                r"what\s+is\s+(.+)",
                r"tell\s+me\s+about\s+(.+)"
            ]
            for pattern in search_patterns:
                m = re.search(pattern, t)
                if m:
                    entities["query"] = m.group(1).strip()
                    break
            else:
                entities["query"] = t
        
        elif intent == "app_control":
            # Extract app name - support multi-word app names
            app_match = re.search(r"(?:open|launch|start|run|close|quit|exit)\s+(.+?)(?:\s+app|\s+application)?$", t)
            if app_match:
                entities["app"] = app_match.group(1).strip()
            else:
                # Fallback to single word
                app_match = re.search(r"(?:open|launch|start|run|close|quit|exit)\s+(\w+)", t)
                if app_match:
                    entities["app"] = app_match.group(1)

        elif intent == "window_control":
            # Extract window action and target
            if "minimize" in t or "minimise" in t:
                entities["action"] = "minimize"
            elif "maximize" in t or "maximise" in t:
                entities["action"] = "maximize"
            elif "restore" in t:
                entities["action"] = "restore"
            elif "show desktop" in t or "minimize all" in t:
                entities["action"] = "show_desktop"
            elif "full screen" in t or "fullscreen" in t:
                entities["action"] = "maximize"
            
            # Extract window/app name
            win_match = re.search(r"(?:minimize|minimise|maximize|maximise|restore)\s+(.+?)(?:\s+window)?$", t)
            if win_match:
                entities["window"] = win_match.group(1).strip()

        elif intent == "brightness":
            # Extract brightness level
            bright_match = re.search(r"(?:\bto\b|\bbrightness\b)?\s*(\d{1,3})(?:%)?\b", t)
            if bright_match:
                try:
                    level = int(bright_match.group(1))
                    if 0 <= level <= 100:
                        entities["level"] = level
                except ValueError:
                    pass
            
            if "up" in t or "brighter" in t or "increase" in t or "higher" in t:
                entities["action"] = "up"
            elif "down" in t or "dimmer" in t or "dim" in t or "decrease" in t or "lower" in t:
                entities["action"] = "down"
            elif "max" in t or "full" in t:
                entities["level"] = 100
                entities["action"] = "set"
            elif "level" in entities:
                entities["action"] = "set"

        elif intent == "volume":
            # Extract volume number
            vol_match = re.search(r"(?:\bto\b|\bvolume\b)?\s*(\d{1,3})(?:%)?", t)
            if vol_match:
                try:
                    vol = int(vol_match.group(1))
                    if 0 <= vol <= 100:
                        entities["level"] = vol
                except ValueError:
                    pass
            
            if "mute" in t:
                entities["action"] = "mute"
            elif "unmute" in t:
                entities["action"] = "unmute"
            elif "up" in t or "louder" in t or "increase" in t:
                entities["action"] = "up"
            elif "down" in t or "quieter" in t or "decrease" in t:
                entities["action"] = "down"
            elif "level" in entities:
                entities["action"] = "set"

        return entities
    
    def _classify_with_nlp(self, text: str, threshold: float = 0.35,
                           return_alternatives: bool = False) -> Tuple[str, float, Optional[List[Tuple[str, float]]]]:
        """
        Classify intent using sentence transformers.
        
        Args:
            text: Input text to classify
            threshold: Minimum confidence threshold (0.35 by default)
            return_alternatives: If True, return top N alternative intents for disambiguation
        
        Returns:
            (intent, confidence, alternatives) - alternatives is None if not requested
            
        The alternatives list enables "Did you mean...?" functionality when
        the top intent has low confidence or multiple intents are close.
        """
        if not self.model or not self.intent_embeddings:
            return "unknown", 0.0, None
        
        try:
            # Get embedding for input text
            text_embedding = self.model.encode([text])[0]
            
            # Calculate similarities with all intents
            similarities = {}
            for intent, intent_embedding in self.intent_embeddings.items():
                similarity = np.dot(text_embedding, intent_embedding) / (
                    np.linalg.norm(text_embedding) * np.linalg.norm(intent_embedding)
                )
                similarities[intent] = float(similarity)
            
            # Sort by score descending
            sorted_intents = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
            
            best_intent, best_score = sorted_intents[0]
            
            # Get alternatives for disambiguation
            alternatives = None
            if return_alternatives:
                # Return top 4 alternatives (excluding the best)
                alternatives = [(intent, score) for intent, score in sorted_intents[1:5]
                               if score >= threshold * 0.7]  # Include even lower-confidence alternatives
            
            if best_score >= threshold:
                return best_intent, best_score, alternatives
            else:
                return "unknown", best_score, alternatives
                
        except Exception as e:
            logger.error(f"NLP classification failed: {e}")
            return "unknown", 0.0, None


def parse_command_nlp(text: str, use_nlp: bool = True, log_matches: bool = False,
                      include_alternatives: bool = True) -> Dict[str, Any]:
    """
    Parse command using NLP enhancement when available, fallback to pattern matching.
    
    Args:
        text: User input text
        use_nlp: Whether to use NLP (sentence transformers)
        log_matches: Whether to log successful matches
        include_alternatives: Whether to include alternative intents for disambiguation
    
    Returns:
        {
            'type': intent,
            'raw': original text,
            'confidence': float,
            'method': 'nlp' or 'pattern',
            'alternatives': [(intent, score), ...],  # For disambiguation
            ... (entities)
        }
    """
    # Import with proper path handling
    import sys
    import os
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
    from Priyapal.command_parser import parse_command as basic_parse
    
    original_text = text
    t = (text or "").lower().strip()
    
    if not t:
        return {"type": "unknown", "raw": original_text, "alternatives": []}
    
    # Remove wake words
    wake_words = ["vox", "hey vox", "ok vox", "computer"]
    for wake in wake_words:
        if t.startswith(wake + " "):
            t = t[len(wake):].strip()
            break
    
    # Try NLP classification first if available and enabled
    if use_nlp and NLP_AVAILABLE:
        parser = NLPCommandParser()
        intent, confidence, alternatives = parser._classify_with_nlp(
            t, return_alternatives=include_alternatives
        )
        
        if intent != "unknown":
            if log_matches:
                logger.info(f"NLP classified '{original_text}' as '{intent}' with confidence {confidence:.3f}")
            
            # Extract parameters based on intent
            result = {
                "type": intent,
                "raw": original_text,
                "confidence": confidence,
                "method": "nlp",
                "alternatives": alternatives or []
            }
            
            # Add specific parameter extraction
            entities = parser.extract_entities(t, intent)
            result.update(entities)
            
            return result
        else:
            # Even for unknown, include alternatives so disambiguation can help
            if alternatives:
                return {
                    "type": "unknown",
                    "raw": original_text,
                    "confidence": confidence,
                    "method": "nlp",
                    "alternatives": alternatives,
                    "needs_clarification": True
                }
    
    # Fallback to basic pattern matching
    basic_result = basic_parse(text)  # Priyapal's parser only takes 1 arg
    basic_result["method"] = "pattern"
    basic_result["alternatives"] = []
    basic_result.setdefault("confidence", 1.0 if basic_result.get("type") != "unknown" else 0.0)
    return basic_result


def parse_command_intelligent(text: str) -> Dict[str, Any]:
    """
    Parse and process a command with intelligent response generation.
    
    This is the recommended function for new code - it combines NLP parsing
    with disambiguation and response generation.
    
    Usage:
        result = parse_command_intelligent("play some music")
        
        if result['needs_disambiguation']:
            print(result['disambiguation_message'])
            for i, opt in enumerate(result['options']):
                print(f"  {i+1}. {opt['description']}")
        else:
            print(result['response'])
    """
    try:
        # Import here to avoid circular imports
        from core.intelligent_response import process_command_intelligently
        
        parsed = parse_command_nlp(text, include_alternatives=True)
        return process_command_intelligently(text, parsed)
    except ImportError:
        # Fallback if intelligent_response not available
        return parse_command_nlp(text)


def get_nlp_status() -> Dict[str, Any]:
    """Get status of NLP capabilities."""
    return {
        "nlp_available": NLP_AVAILABLE,
        "model_loaded": NLP_AVAILABLE and hasattr(NLPCommandParser(), 'model') and NLPCommandParser().model is not None
    }