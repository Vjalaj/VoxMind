"""
VoxMind Unified Memory System
==============================
Centralized conversation memory for context-aware interactions.

This replaces the fragmented memory systems with a single source of truth
for conversation history, entity tracking, and pronoun resolution.
"""

import json
import threading
import time
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Deque
from collections import deque
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class MemoryEntry:
    """A single memory entry (command + response)."""
    timestamp: float
    user_input: str
    response: str
    command: str  # Parsed command type
    entities: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        return cls(**data)


@dataclass 
class EntityReference:
    """Tracks an entity for pronoun resolution."""
    value: str
    entity_type: str  # app, window, file, query, url, person, etc.
    timestamp: float
    source_command: str  # The command that introduced this entity


# =============================================================================
# UNIFIED MEMORY
# =============================================================================

class UnifiedMemory:
    """
    Centralized memory system for VoxMind.
    
    Features:
    - Short-term: Last N exchanges for immediate context
    - Entity tracking: Remember apps, files, queries for pronoun resolution
    - Persistence: Save/load memory across sessions
    - Time decay: Older memories become less relevant
    
    Usage:
        memory = UnifiedMemory.get_instance()
        memory.record("open chrome", "Opening Chrome", "app_control", {"app": "chrome"})
        
        # Later...
        resolved = memory.resolve_pronouns("now close it")  
        # -> {"app": "chrome"}
    """
    
    _instance = None
    _lock = threading.Lock()
    
    # Singleton
    @classmethod
    def get_instance(cls) -> 'UnifiedMemory':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def __init__(self, max_short_term: int = 20, persistence_path: str = None):
        self._short_term: Deque[MemoryEntry] = deque(maxlen=max_short_term)
        self._entities: Dict[str, EntityReference] = {}  # Current entity references
        self._entity_history: Dict[str, List[EntityReference]] = {}  # All past entities by type
        self._user_preferences: Dict[str, Any] = {}
        self._session_start = time.time()
        self._lock = threading.Lock()
        
        # Persistence
        self._persistence_path = persistence_path or self._default_persistence_path()
        self._load_from_disk()
    
    def _default_persistence_path(self) -> str:
        """Get default path for memory persistence."""
        cache_dir = Path(__file__).parent.parent / "cache"
        cache_dir.mkdir(exist_ok=True)
        return str(cache_dir / "memory.json")
    
    # =========================================================================
    # RECORDING
    # =========================================================================
    
    def record(self, user_input: str, response: str, command: str,
               entities: Dict[str, Any] = None, success: bool = True,
               confidence: float = 1.0):
        """
        Record a command exchange to memory.
        
        Args:
            user_input: What the user said
            response: What VoxMind responded
            command: The parsed command type (e.g., "app_control")
            entities: Extracted entities (e.g., {"app": "chrome"})
            success: Whether the command succeeded
            confidence: Parse confidence
        """
        entities = entities or {}
        
        with self._lock:
            # Create memory entry
            entry = MemoryEntry(
                timestamp=time.time(),
                user_input=user_input,
                response=response,
                command=command,
                entities=entities,
                success=success,
                confidence=confidence,
            )
            self._short_term.append(entry)
            
            # Update entity references
            self._update_entities(entities, command)
            
            # Persist periodically (every 10 entries)
            if len(self._short_term) % 10 == 0:
                self._save_to_disk()
        
        logger.debug(f"Recorded: {command} with entities {entities}")
    
    def _update_entities(self, entities: Dict[str, Any], command: str):
        """Update entity references for pronoun resolution."""
        entity_type_map = {
            'app': 'app',
            'app_name': 'app',
            'application': 'app',
            'window': 'window',
            'window_title': 'window',
            'file': 'file',
            'filename': 'file',
            'path': 'file',
            'query': 'query',
            'search_query': 'query',
            'topic': 'query',
            'url': 'url',
            'link': 'url',
            'person': 'person',
            'name': 'person',
            'number': 'number',
            'target': 'target',
        }
        
        for key, value in entities.items():
            if not isinstance(value, str) or not value:
                continue
            
            # Determine entity type
            entity_type = entity_type_map.get(key.lower(), key.lower())
            
            # Create reference
            ref = EntityReference(
                value=value,
                entity_type=entity_type,
                timestamp=time.time(),
                source_command=command,
            )
            
            # Update current entity for this type
            self._entities[entity_type] = ref
            
            # Also store as "it", "that" reference for top-priority entities
            if entity_type in ('app', 'window', 'file', 'query'):
                self._entities['it'] = ref
                self._entities['that'] = ref
                self._entities['this'] = ref
            
            # Add to history
            if entity_type not in self._entity_history:
                self._entity_history[entity_type] = []
            self._entity_history[entity_type].append(ref)
            
            # Limit history per type
            if len(self._entity_history[entity_type]) > 10:
                self._entity_history[entity_type] = self._entity_history[entity_type][-10:]
    
    # =========================================================================
    # RETRIEVAL
    # =========================================================================
    
    def get_last_entity(self, entity_type: str) -> Optional[str]:
        """Get the last value of a specific entity type."""
        with self._lock:
            ref = self._entities.get(entity_type)
            if ref:
                # Check if not too old (5 minute timeout)
                if time.time() - ref.timestamp < 300:
                    return ref.value
        return None
    
    def get_last_command(self) -> Optional[MemoryEntry]:
        """Get the last command entry."""
        with self._lock:
            if self._short_term:
                return self._short_term[-1]
        return None
    
    def get_recent_commands(self, n: int = 5) -> List[MemoryEntry]:
        """Get the N most recent commands."""
        with self._lock:
            return list(self._short_term)[-n:]
    
    def get_context_summary(self, n: int = 3) -> str:
        """Get a text summary of recent context."""
        recent = self.get_recent_commands(n)
        if not recent:
            return ""
        
        lines = []
        for entry in recent:
            lines.append(f"User: {entry.user_input}")
            lines.append(f"Vox: {entry.response}")
        return "\n".join(lines)
    
    # =========================================================================
    # PRONOUN RESOLUTION
    # =========================================================================
    
    def resolve_pronouns(self, text: str, entities: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Resolve pronouns in text to actual entities.
        
        Example:
            Previous: "open chrome"  -> entities = {"app": "chrome"}
            Current: "close it"      -> resolved = {"app": "chrome"}
        
        Args:
            text: The user's current input
            entities: Already-parsed entities from the command
            
        Returns:
            Updated entities dict with resolved pronouns
        """
        entities = dict(entities or {})
        text_lower = text.lower()
        
        # Pronouns to check
        pronoun_patterns = [
            ('it', ['it', "it's"]),
            ('that', ['that', 'that one']),
            ('this', ['this', 'this one']),
            ('them', ['them', 'those']),
            ('the same', ['the same', 'same thing', 'again']),
        ]
        
        with self._lock:
            for entity_key, patterns in pronoun_patterns:
                # Check if any pattern is in the text
                if not any(p in text_lower for p in patterns):
                    continue
                
                # Check what entity types are missing
                ref = self._entities.get(entity_key)
                if not ref:
                    continue
                
                # Check timeout (5 minutes)
                if time.time() - ref.timestamp > 300:
                    continue
                
                # Fill in missing entity
                if ref.entity_type not in entities or not entities[ref.entity_type]:
                    entities[ref.entity_type] = ref.value
                    logger.info(f"Resolved '{entity_key}' -> {ref.entity_type}='{ref.value}'")
        
        return entities
    
    def is_follow_up(self, text: str) -> bool:
        """Check if the current input is a follow-up to the previous command."""
        follow_up_indicators = [
            'also', 'and also', 'and', 'then', 'now',
            'what about', 'how about', 'same for',
            'do that', 'again', 'one more', 'another',
            'more', 'else', 'too', 'next',
            'it', 'that', 'this', 'the same',
        ]
        
        text_lower = text.lower().strip()
        
        # Check if starts with follow-up indicator
        for indicator in follow_up_indicators:
            if text_lower.startswith(indicator + ' '):
                return True
            if f" {indicator} " in text_lower:
                return True
        
        return False
    
    # =========================================================================
    # PERSISTENCE
    # =========================================================================
    
    def _save_to_disk(self):
        """Save memory to disk for persistence across sessions."""
        try:
            data = {
                'short_term': [e.to_dict() for e in self._short_term],
                'entities': {
                    k: {
                        'value': v.value,
                        'entity_type': v.entity_type,
                        'timestamp': v.timestamp,
                        'source_command': v.source_command,
                    }
                    for k, v in self._entities.items()
                },
                'user_preferences': self._user_preferences,
                'saved_at': time.time(),
            }
            
            with open(self._persistence_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Memory saved to {self._persistence_path}")
        except Exception as e:
            logger.warning(f"Failed to save memory: {e}")
    
    def _load_from_disk(self):
        """Load memory from disk."""
        try:
            if not os.path.exists(self._persistence_path):
                return
            
            with open(self._persistence_path, 'r') as f:
                data = json.load(f)
            
            # Check if memory is too old (24 hours)
            saved_at = data.get('saved_at', 0)
            if time.time() - saved_at > 86400:
                logger.info("Memory too old, starting fresh")
                return
            
            # Load short-term memory
            for entry_data in data.get('short_term', []):
                try:
                    entry = MemoryEntry.from_dict(entry_data)
                    self._short_term.append(entry)
                except (KeyError, TypeError, ValueError) as e:
                    logger.debug(f"Skipping invalid memory entry: {e}")
                    continue
            
            # Load entities
            for key, ref_data in data.get('entities', {}).items():
                try:
                    self._entities[key] = EntityReference(
                        value=ref_data['value'],
                        entity_type=ref_data['entity_type'],
                        timestamp=ref_data['timestamp'],
                        source_command=ref_data['source_command'],
                    )
                except (KeyError, TypeError) as e:
                    logger.debug(f"Skipping invalid entity {key}: {e}")
                    continue
            
            # Load preferences
            self._user_preferences = data.get('user_preferences', {})
            
            logger.info(f"Loaded {len(self._short_term)} memory entries")
        except Exception as e:
            logger.warning(f"Failed to load memory: {e}")
    
    def clear(self):
        """Clear all memory."""
        with self._lock:
            self._short_term.clear()
            self._entities.clear()
            self._entity_history.clear()
        
        # Remove persisted file
        try:
            if os.path.exists(self._persistence_path):
                os.remove(self._persistence_path)
        except (OSError, PermissionError) as e:
            logger.debug(f"Could not remove memory file: {e}")
    
    # =========================================================================
    # USER PREFERENCES
    # =========================================================================
    
    def set_preference(self, key: str, value: Any):
        """Set a user preference."""
        with self._lock:
            self._user_preferences[key] = value
            self._save_to_disk()
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        with self._lock:
            return self._user_preferences.get(key, default)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_memory() -> UnifiedMemory:
    """Get the singleton memory instance."""
    return UnifiedMemory.get_instance()


def record_command(user_input: str, response: str, command: str,
                   entities: Dict[str, Any] = None, success: bool = True):
    """Record a command to memory."""
    get_memory().record(user_input, response, command, entities, success)


def resolve_pronouns(text: str, entities: Dict[str, Any] = None) -> Dict[str, Any]:
    """Resolve pronouns in the text."""
    return get_memory().resolve_pronouns(text, entities)


def get_last_entity(entity_type: str) -> Optional[str]:
    """Get the last value of an entity type."""
    return get_memory().get_last_entity(entity_type)


def is_follow_up(text: str) -> bool:
    """Check if text is a follow-up command."""
    return get_memory().is_follow_up(text)


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("VoxMind Unified Memory Test")
    print("=" * 60)
    
    memory = get_memory()
    memory.clear()
    
    # Simulate conversation
    print("\n[1] Recording: 'open chrome'")
    memory.record(
        user_input="open chrome",
        response="Opening Chrome",
        command="app_control",
        entities={"app": "chrome", "action": "open"}
    )
    
    print("[2] Recording: 'search for python tutorials'")
    memory.record(
        user_input="search for python tutorials",
        response="Searching for python tutorials",
        command="search",
        entities={"query": "python tutorials"}
    )
    
    # Test pronoun resolution
    print("\n[3] Testing pronoun resolution:")
    
    test_cases = [
        ("close it", {}),
        ("search for more about it", {}),
        ("tell me more about that", {}),
        ("open that again", {}),
    ]
    
    for text, initial_entities in test_cases:
        resolved = memory.resolve_pronouns(text, initial_entities)
        print(f"  '{text}' -> {resolved}")
    
    # Test context summary
    print("\n[4] Context summary:")
    print(memory.get_context_summary())
    
    # Test follow-up detection
    print("\n[5] Follow-up detection:")
    follow_up_tests = [
        "and also open notepad",
        "then close it",
        "open firefox",
        "what about that",
    ]
    for text in follow_up_tests:
        is_fu = memory.is_follow_up(text)
        print(f"  '{text}' -> follow-up: {is_fu}")
    
    print("\n[6] Last entity tests:")
    print(f"  Last 'app': {memory.get_last_entity('app')}")
    print(f"  Last 'query': {memory.get_last_entity('query')}")
    print(f"  Last 'it': {memory.get_last_entity('it')}")
    
    print("\n✅ Memory system working!")
