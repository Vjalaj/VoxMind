"""
Week 2: Advanced NLP Integration & Parser Enhancement
- 60+ Command Patterns
- Context-aware parsing
- Compound command support
- Parameter validation
- NLP Intent Classification with cache
"""
from typing import Dict, Any, List, Optional, Tuple, Union
import re
import logging
import threading

logger = logging.getLogger(__name__)

# NLP Imports
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False
    logger.warning("sentence-transformers or numpy not installed. Running in pattern-only mode.")

class AdvancedCommandParser:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AdvancedCommandParser, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.context = {"last_intent": None, "last_entities": {}}
        self.model = None
        self.intent_embeddings = {}
        self.intent_examples = self._get_intent_examples()
        
        if NLP_AVAILABLE:
            try:
                # Load model once
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                self._compute_embeddings()
                logger.info("NLP Engine Initialized Successfully")
            except Exception as e:
                logger.error(f"Failed to initialize NLP model: {e}")
                
        self._initialized = True

    def _get_intent_examples(self) -> Dict[str, List[str]]:
        """
        Define 60+ patterns across various categories for NLP training
        """
        return {
            "browser": [
                "open browser", "launch chrome", "start firefox", "open google", 
                "close browser", "new tab", "close tab", "refresh page",
                "go back", "go forward", "open incognito"
            ],
            "search": [
                "search for", "google this", "find information about", "what is", 
                "who is", "look up", "search web for", "browse for",
                "find images of", "show me videos of"
            ],
            "system": [
                "shutdown system", "restart computer", "lock screen", "sleep mode",
                "log out", "turn off", "reboot", "hibernate",
                "check battery", "system info", "cpu usage"
            ],
            "volume": [
                "volume up", "increase volume", "louder", "turn it up",
                "volume down", "decrease volume", "quieter", "lower sound",
                "mute", "unmute", "set volume to 50%", "max volume"
            ],
            "media": [
                "play music", "stop music", "pause track", "resume song",
                "next song", "skip track", "previous song", "play spotify",
                "volume up", "shuffle playlist"
            ],
            "app_control": [
                "open notepad", "launch calculator", "start vscode", "open terminal",
                "close application", "quit program", "kill process", "open file explorer",
                "minize window", "maximize window"
            ],
            "utility": [
                "what time is it", "tell me the date", "set a timer", "start stopwatch",
                "what is the weather", "tell me a joke", "read notification",
                "take a screenshot", "turn on flashlight"
            ],
            "communication": [
                "send email", "read messages", "compose mail", "reply to message",
                "call contact", "open whatsapp", "check inbox"
            ]
        }

    def _compute_embeddings(self):
        """Compute and cache embeddings for intents"""
        for intent, examples in self.intent_examples.items():
            embeddings = self.model.encode(examples)
            # Store mean embedding for the intent
            self.intent_embeddings[intent] = np.mean(embeddings, axis=0)

    def parse(self, text: str) -> List[Dict[str, Any]]:
        """
        Main entry point. Handles compound commands and context.
        Returns a LIST of command dictionaries (to support compound commands).
        """
        text = text.lower().strip()
        
        # 1. Handle Compound Commands (split by 'and', 'then')
        sub_commands = re.split(r'\s+(?:and|then)\s+', text)
        results = []
        
        for cmd_text in sub_commands:
            cmd_text = cmd_text.strip()
            if not cmd_text:
                continue
                
            cmd_result = self._parse_single_command(cmd_text)
            
            # Context Injection (if command is incomplete, try to use context)
            if cmd_result['type'] == 'unknown' and self.context['last_intent']:
                # Example logic: if user just said "python" after "search for java"
                # This is a naive implementation of context
                if self.context['last_intent'] == 'search':
                    cmd_result = {
                        'type': 'search',
                        'query': cmd_text,
                        'confidence': 0.8,
                        'source': 'context_inference'
                    }
            
            results.append(cmd_result)
            
            # Update Context
            if cmd_result['type'] != 'unknown':
                self.context['last_intent'] = cmd_result['type']
                self.context.update(cmd_result) # Store other params like 'query', 'app_name'

        return results

    def _parse_single_command(self, text: str) -> Dict[str, Any]:
        """
        Parse a single atomic command using Regex logic + NLP fallback
        """
        # A. Try Regex Patterns (Deterministic & Fast)
        regex_result = self._match_patterns(text)
        if regex_result:
            regex_result['source'] = 'regex'
            return regex_result

        # B. Try NLP (Probabilistic)
        if NLP_AVAILABLE and self.model:
            nlp_result = self._predict_intent(text)
            if nlp_result['confidence'] > 0.65: # Threshold
                nlp_result['source'] = 'nlp'
                # Attempt to extract entities even if intent came from NLP
                entities = self._extract_entities(text, nlp_result['type'])
                nlp_result.update(entities)
                return nlp_result

        return {'type': 'unknown', 'original_text': text}

    def _match_patterns(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Regex based matching for deterministic commands.
        Includes parameter validation.
        """
        # Browser / Search
        if match := re.search(r'(?:open|launch) (?:browser|chrome|firefox)', text):
            return {'type': 'browser', 'action': 'open'}
        
        if match := re.search(r'(?:search for|google|find) (.+)', text):
            query = match.group(1).strip()
            return {'type': 'search', 'query': query}

        # System / Volume
        if 'volume' in text:
            if match := re.search(r'set volume to (\d+)', text):
                vol = int(match.group(1))
                # Parameter Validation
                if 0 <= vol <= 100:
                    return {'type': 'volume', 'action': 'set', 'value': vol}
            if 'up' in text or 'increase' in text:
                return {'type': 'volume', 'action': 'up'}
            if 'down' in text or 'decrease' in text:
                return {'type': 'volume', 'action': 'down'}
            if 'mute' in text:
                return {'type': 'volume', 'action': 'mute'}

        # App Control
        if match := re.search(r'(?:open|launch|start|run) (\w+)', text):
            # Exclude known non-apps
            app_name = match.group(1).strip()
            if app_name not in ['browser', 'music', 'volume']:
                return {'type': 'app_control', 'action': 'open', 'app_name': app_name}
        
        return None

    def _predict_intent(self, text: str) -> Dict[str, Any]:
        """
        Use Sentence-BERT to classify intent
        """
        text_embedding = self.model.encode([text])[0]
        
        names = []
        scores = []
        
        for intent, intent_embedding in self.intent_embeddings.items():
            # Cosine similarity
            similarity = np.dot(text_embedding, intent_embedding) / (
                np.linalg.norm(text_embedding) * np.linalg.norm(intent_embedding)
            )
            names.append(intent)
            scores.append(similarity)
            
        max_idx = np.argmax(scores)
        return {
            'type': names[max_idx],
            'confidence': float(scores[max_idx])
        }

    def _extract_entities(self, text: str, intent: str) -> Dict[str, Any]:
        """
        Post-NLP entity extraction
        """
        entities = {}
        if intent == 'search':
            # Remove command words to find query
            clean = re.sub(r'(search for|google|find|who is|what is)', '', text).strip()
            entities['query'] = clean
        elif intent == 'app_control':
             match = re.search(r'(?:open|launch|start) (\w+)', text)
             if match:
                 entities['app_name'] = match.group(1)
        
        return entities

if __name__ == "__main__":
    # Test Block
    parser = AdvancedCommandParser()
    
    test_commands = [
        "open google",
        "search for python programming",
        "open browser and search for machine learning",
        "set volume to 50",
        "set volume to 150", # Should trigger validation fail logic (regex won't match) or fall to NLP
        "play some music",
        "what is the weather like"
    ]
    
    for cmd in test_commands:
        print(f"Input: {cmd}")
        print(f"Parsed: {parser.parse(cmd)}")
        print("-" * 20)
