"""NLP-enhanced command parser using sentence transformers for better intent classification."""
from typing import Dict, Any, List, Tuple
import re
import logging

logger = logging.getLogger(__name__)

# Fallback to basic parser if sentence-transformers not available
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False
    logger.warning("sentence-transformers not available, using basic pattern matching only")

class NLPCommandParser:
    def __init__(self):
        self.model = None
        self.intent_embeddings = None
        self.intent_examples = {
            "open_browser": [
                "open browser", "launch chrome", "start firefox", "go online",
                "open web browser", "start browsing", "launch web browser"
            ],
            "time": [
                "what time is it", "current time", "what's the date", "tell me the time",
                "what day is it", "show me the clock", "time now"
            ],
            "search": [
                "search for python", "google machine learning", "what is AI", "find restaurants",
                "look up information", "search the web", "find me details about"
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
                "increase volume", "decrease sound", "silence audio"
            ],
            "app_control": [
                "open notepad", "launch vscode", "close chrome", "start calculator",
                "run application", "quit program", "open software"
            ],
            "help": [
                "help", "what can you do", "who are you", "capabilities",
                "show commands", "list functions", "what are your features"
            ]
        }
        
        if NLP_AVAILABLE:
            self._initialize_nlp()
    
    def _initialize_nlp(self):
        """Initialize the sentence transformer model and compute intent embeddings."""
        try:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Compute embeddings for all intent examples
            self.intent_embeddings = {}
            for intent, examples in self.intent_examples.items():
                embeddings = self.model.encode(examples)
                self.intent_embeddings[intent] = np.mean(embeddings, axis=0)
            
            logger.info("NLP model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize NLP model: {e}")
            self.model = None
    
    def _classify_with_nlp(self, text: str, threshold: float = 0.6) -> Tuple[str, float]:
        """Classify intent using sentence transformers."""
        if not self.model or not self.intent_embeddings:
            return "unknown", 0.0
        
        try:
            # Get embedding for input text
            text_embedding = self.model.encode([text])[0]
            
            # Calculate similarities with all intents
            similarities = {}
            for intent, intent_embedding in self.intent_embeddings.items():
                similarity = np.dot(text_embedding, intent_embedding) / (
                    np.linalg.norm(text_embedding) * np.linalg.norm(intent_embedding)
                )
                similarities[intent] = similarity
            
            # Get best match
            best_intent = max(similarities, key=similarities.get)
            best_score = similarities[best_intent]
            
            if best_score >= threshold:
                return best_intent, best_score
            else:
                return "unknown", best_score
                
        except Exception as e:
            logger.error(f"NLP classification failed: {e}")
            return "unknown", 0.0

def parse_command_nlp(text: str, use_nlp: bool = True, log_matches: bool = False) -> Dict[str, Any]:
    """Parse command using NLP enhancement when available, fallback to pattern matching."""
    from command_parser import parse_command as basic_parse
    
    original_text = text
    t = (text or "").lower().strip()
    
    if not t:
        return {"type": "unknown", "raw": original_text}
    
    # Remove wake words
    wake_words = ["jarvis", "hey jarvis", "ok jarvis", "assistant"]
    for wake in wake_words:
        if t.startswith(wake + " "):
            t = t[len(wake):].strip()
            break
    
    # Try NLP classification first if available and enabled
    if use_nlp and NLP_AVAILABLE:
        parser = NLPCommandParser()
        intent, confidence = parser._classify_with_nlp(t)
        
        if intent != "unknown":
            if log_matches:
                logger.info(f"NLP classified '{original_text}' as '{intent}' with confidence {confidence:.3f}")
            
            # Extract parameters based on intent
            result = {"type": intent, "raw": original_text, "confidence": confidence, "method": "nlp"}
            
            # Add specific parameter extraction
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
                        result["query"] = m.group(1).strip()
                        break
                else:
                    result["query"] = t
            
            elif intent == "app_control":
                # Extract app name
                app_match = re.search(r"(?:open|launch|start|run|close|quit|exit)\s+(\w+)", t)
                if app_match:
                    result["app"] = app_match.group(1)
            
            return result
    
    # Fallback to basic pattern matching
    basic_result = basic_parse(text, log_matches)
    basic_result["method"] = "pattern"
    return basic_result


def get_nlp_status() -> Dict[str, Any]:
    """Get status of NLP capabilities."""
    return {
        "nlp_available": NLP_AVAILABLE,
        "model_loaded": NLP_AVAILABLE and hasattr(NLPCommandParser(), 'model') and NLPCommandParser().model is not None
    }