"""
VoxMind Command Cache & Fingerprinting Module
==============================================
Hashmap-based caching and command fingerprinting for:
- Response caching (avoid reprocessing identical commands)
- Command fingerprinting (detect duplicate/similar commands)
- Fuzzy matching for similar command detection
- Memory-aware caching with adaptive eviction

Performance Optimization:
- Uses functools.lru_cache for hot paths (C implementation, ~10x faster)
- Custom hashmap for feature-rich command caching
- Memory monitoring for adaptive cache sizing
- Tiered caching (hot/warm/cold)
"""

import hashlib
import time
import re
import sys
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from collections import OrderedDict
from functools import lru_cache, cache
import threading
import json


# =============================================================================
# Memory Utilities
# =============================================================================

def get_object_size(obj: Any) -> int:
    """Estimate memory size of an object in bytes."""
    try:
        return sys.getsizeof(obj)
    except TypeError:
        return 0


def get_total_memory_mb() -> float:
    """Get total process memory in MB."""
    try:
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / (1024 * 1024)
    except ImportError:
        return 0.0


# =============================================================================
# LRU-Cached Hot Path Functions (C-optimized)
# =============================================================================

@lru_cache(maxsize=4096)
def normalize_command_cached(text: str) -> str:
    """
    Normalize command text for exact matching.
    LRU cached - O(1) for repeated normalizations.
    """
    text = text.lower().strip()
    text = ' '.join(text.split())
    text = re.sub(r'[^\w\s\-]', '', text)
    return text


@lru_cache(maxsize=4096)
def compute_exact_hash_cached(text: str) -> str:
    """
    Compute exact MD5 hash of normalized command.
    LRU cached - avoids re-hashing same commands.
    """
    normalized = normalize_command_cached(text)
    return hashlib.md5(normalized.encode()).hexdigest()


@lru_cache(maxsize=2048)
def tokenize_cached(text: str) -> Tuple[str, ...]:
    """
    Tokenize and filter stop words.
    Returns tuple (hashable) for caching.
    """
    # Stop words to ignore
    stop_words = {
        'a', 'an', 'the', 'to', 'for', 'of', 'and', 'or', 'is', 'it',
        'my', 'me', 'i', 'you', 'your', 'please', 'can', 'could', 'would',
        'just', 'now', 'hey', 'vox', 'okay', 'ok', 'um', 'uh', 'like'
    }
    
    # Synonym mappings
    synonyms = {
        'launch': 'open', 'start': 'open', 'run': 'open', 'execute': 'open',
        'close': 'close', 'exit': 'close', 'quit': 'close', 'terminate': 'close', 'kill': 'close',
        'louder': 'volume_up', 'quieter': 'volume_down', 'softer': 'volume_down',
        'brighter': 'brightness_up', 'dimmer': 'brightness_down',
        'click': 'click', 'tap': 'click', 'press': 'press', 'hit': 'press',
        'type': 'type', 'write': 'type', 'enter': 'type',
        'search': 'search', 'find': 'search', 'google': 'search', 'look': 'search',
    }
    
    normalized = normalize_command_cached(text)
    tokens = normalized.split()
    
    result = []
    for token in tokens:
        if token not in stop_words:
            token = synonyms.get(token, token)
            result.append(token)
    
    return tuple(result)  # Tuple for hashability


@lru_cache(maxsize=2048)
def compute_fuzzy_hash_cached(text: str) -> str:
    """
    Compute fuzzy hash based on sorted key tokens.
    LRU cached for repeated fuzzy lookups.
    """
    tokens = tokenize_cached(text)
    sorted_tokens = tuple(sorted(set(tokens)))
    token_str = ' '.join(sorted_tokens)
    return hashlib.md5(token_str.encode()).hexdigest()[:16]


@lru_cache(maxsize=1024)
def levenshtein_distance_cached(s1: str, s2: str) -> int:
    """
    Compute Levenshtein edit distance.
    LRU cached for repeated comparisons.
    """
    if len(s1) < len(s2):
        s1, s2 = s2, s1
    
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


def get_cache_stats() -> Dict[str, Any]:
    """Get statistics from all LRU caches."""
    return {
        'normalize': normalize_command_cached.cache_info()._asdict(),
        'exact_hash': compute_exact_hash_cached.cache_info()._asdict(),
        'tokenize': tokenize_cached.cache_info()._asdict(),
        'fuzzy_hash': compute_fuzzy_hash_cached.cache_info()._asdict(),
        'levenshtein': levenshtein_distance_cached.cache_info()._asdict(),
    }


def clear_all_caches():
    """Clear all LRU caches."""
    normalize_command_cached.cache_clear()
    compute_exact_hash_cached.cache_clear()
    tokenize_cached.cache_clear()
    compute_fuzzy_hash_cached.cache_clear()
    levenshtein_distance_cached.cache_clear()


# =============================================================================
# Tiered Memory-Aware Cache
# =============================================================================

class TieredCache:
    """
    Three-tier cache: Hot (L1) -> Warm (L2) -> Cold (L3)
    
    - Hot: Recently accessed, small, fastest
    - Warm: Less recent, medium size
    - Cold: Oldest, largest, slowest
    
    Automatically promotes/demotes entries based on access patterns.
    Memory-aware: evicts aggressively when memory pressure is high.
    """
    
    def __init__(
        self,
        hot_size: int = 50,
        warm_size: int = 200,
        cold_size: int = 1000,
        memory_limit_mb: float = 100.0
    ):
        self.hot_size = hot_size
        self.warm_size = warm_size
        self.cold_size = cold_size
        self.memory_limit_mb = memory_limit_mb
        
        # LRU caches for each tier
        self._hot: OrderedDict[str, Any] = OrderedDict()
        self._warm: OrderedDict[str, Any] = OrderedDict()
        self._cold: OrderedDict[str, Any] = OrderedDict()
        
        self._lock = threading.RLock()
        self._stats = {
            'hot_hits': 0, 'warm_hits': 0, 'cold_hits': 0,
            'misses': 0, 'promotions': 0, 'demotions': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """Get value, promoting to hotter tier on access."""
        with self._lock:
            # Check hot
            if key in self._hot:
                self._hot.move_to_end(key)
                self._stats['hot_hits'] += 1
                return self._hot[key]
            
            # Check warm -> promote to hot
            if key in self._warm:
                value = self._warm.pop(key)
                self._promote_to_hot(key, value)
                self._stats['warm_hits'] += 1
                self._stats['promotions'] += 1
                return value
            
            # Check cold -> promote to warm
            if key in self._cold:
                value = self._cold.pop(key)
                self._promote_to_warm(key, value)
                self._stats['cold_hits'] += 1
                self._stats['promotions'] += 1
                return value
            
            self._stats['misses'] += 1
            return None
    
    def set(self, key: str, value: Any) -> None:
        """Set value in hot tier."""
        with self._lock:
            # Remove from other tiers
            self._warm.pop(key, None)
            self._cold.pop(key, None)
            
            # Add to hot
            self._promote_to_hot(key, value)
            
            # Check memory pressure
            self._check_memory()
    
    def _promote_to_hot(self, key: str, value: Any) -> None:
        """Add to hot tier, demoting oldest if needed."""
        if len(self._hot) >= self.hot_size:
            # Demote oldest from hot to warm
            old_key, old_value = self._hot.popitem(last=False)
            self._promote_to_warm(old_key, old_value)
            self._stats['demotions'] += 1
        
        self._hot[key] = value
    
    def _promote_to_warm(self, key: str, value: Any) -> None:
        """Add to warm tier, demoting oldest if needed."""
        if len(self._warm) >= self.warm_size:
            # Demote oldest from warm to cold
            old_key, old_value = self._warm.popitem(last=False)
            self._cold[old_key] = old_value
            
            # Evict from cold if full
            while len(self._cold) > self.cold_size:
                self._cold.popitem(last=False)
            
            self._stats['demotions'] += 1
        
        self._warm[key] = value
    
    def _check_memory(self) -> None:
        """Evict if memory pressure is high."""
        current_mb = get_total_memory_mb()
        if current_mb > self.memory_limit_mb:
            # Aggressive eviction from cold tier
            evict_count = len(self._cold) // 4
            for _ in range(evict_count):
                if self._cold:
                    self._cold.popitem(last=False)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_hits = (
            self._stats['hot_hits'] + 
            self._stats['warm_hits'] + 
            self._stats['cold_hits']
        )
        total = total_hits + self._stats['misses']
        
        return {
            **self._stats,
            'total_hits': total_hits,
            'total_requests': total,
            'hit_rate': f"{(total_hits / total * 100):.1f}%" if total > 0 else "0%",
            'hot_size': len(self._hot),
            'warm_size': len(self._warm),
            'cold_size': len(self._cold),
        }
    
    def clear(self) -> None:
        """Clear all tiers."""
        with self._lock:
            self._hot.clear()
            self._warm.clear()
            self._cold.clear()


# Global tiered cache for frequently accessed data
_tiered_cache = TieredCache()


def get_tiered_cache() -> TieredCache:
    """Get global tiered cache instance."""
    return _tiered_cache


@dataclass
class CacheEntry:
    """Single cache entry with metadata."""
    command_hash: str
    command_text: str
    command_normalized: str
    response: str
    parsed_result: Dict[str, Any]
    timestamp: float
    hits: int = 0
    ttl_seconds: float = 300.0  # 5 minutes default TTL
    
    @property
    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl_seconds
    
    def touch(self):
        """Update access time and increment hits."""
        self.hits += 1


@dataclass
class CommandFingerprint:
    """Fingerprint for command similarity detection."""
    hash_exact: str       # Exact hash (normalized text)
    hash_fuzzy: str       # Fuzzy hash (key tokens only)
    tokens: List[str]     # Tokenized words
    intent: str           # Detected intent
    entities: List[str]   # Extracted entities
    timestamp: float = field(default_factory=time.time)


class CommandHashMap:
    """
    Hashmap-based command caching and fingerprinting system.
    
    Features:
    - O(1) exact match lookup (uses lru_cache for hot paths)
    - Fuzzy/similar command detection
    - LRU eviction policy
    - TTL-based expiration
    - Thread-safe operations
    
    Performance:
    - Hot path functions use functools.lru_cache (C implementation)
    - ~10x faster for repeated operations
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: float = 300.0,
        similarity_threshold: float = 0.8
    ):
        """
        Initialize command hashmap.
        
        Args:
            max_size: Maximum cache entries (LRU eviction after)
            default_ttl: Default TTL in seconds
            similarity_threshold: Threshold for fuzzy matching (0-1)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.similarity_threshold = similarity_threshold
        
        # Primary hashmap: exact hash -> CacheEntry
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        
        # Fuzzy hash index: fuzzy_hash -> list of exact hashes
        self._fuzzy_index: Dict[str, List[str]] = {}
        
        # Token index: token -> list of exact hashes (inverted index)
        self._token_index: Dict[str, List[str]] = {}
        
        # Fingerprint storage
        self._fingerprints: Dict[str, CommandFingerprint] = {}
        
        # Statistics
        self._stats = {
            'hits': 0,
            'misses': 0,
            'fuzzy_hits': 0,
            'evictions': 0,
            'expirations': 0
        }
        
        # Thread safety
        self._lock = threading.RLock()
    
    # =========================================================================
    # Hashing & Fingerprinting (using LRU-cached functions)
    # =========================================================================
    
    def _normalize_command(self, text: str) -> str:
        """Normalize command text - uses LRU cache."""
        return normalize_command_cached(text)
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize and filter - uses LRU cache, returns list."""
        return list(tokenize_cached(text))
    
    def _compute_exact_hash(self, text: str) -> str:
        """Compute exact hash - uses LRU cache."""
        return compute_exact_hash_cached(text)
    
    def _compute_fuzzy_hash(self, text: str) -> str:
        """Compute fuzzy hash - uses LRU cache."""
        return compute_fuzzy_hash_cached(text)
    
    def fingerprint(self, text: str, intent: str = "", entities: List[str] = None) -> CommandFingerprint:
        """
        Create fingerprint for a command.
        
        Args:
            text: Command text
            intent: Detected intent (optional)
            entities: Extracted entities (optional)
        
        Returns:
            CommandFingerprint object
        """
        fp = CommandFingerprint(
            hash_exact=self._compute_exact_hash(text),
            hash_fuzzy=self._compute_fuzzy_hash(text),
            tokens=self._tokenize(text),
            intent=intent,
            entities=entities or []
        )
        
        # Store fingerprint
        with self._lock:
            self._fingerprints[fp.hash_exact] = fp
        
        return fp
    
    # =========================================================================
    # Similarity Detection
    # =========================================================================
    
    def _jaccard_similarity(self, tokens1: List[str], tokens2: List[str]) -> float:
        """Compute Jaccard similarity between token sets."""
        set1, set2 = set(tokens1), set(tokens2)
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Compute Levenshtein edit distance - uses LRU cache."""
        return levenshtein_distance_cached(s1, s2)
    
    def _string_similarity(self, s1: str, s2: str) -> float:
        """Compute normalized string similarity - uses cached Levenshtein."""
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 1.0
        distance = levenshtein_distance_cached(s1, s2)
        return 1.0 - (distance / max_len)
    
    def find_similar(
        self,
        text: str,
        threshold: float = None
    ) -> List[Tuple[str, float, CacheEntry]]:
        """
        Find similar commands in cache.
        
        Args:
            text: Command to search for
            threshold: Similarity threshold (0-1)
        
        Returns:
            List of (original_text, similarity_score, cache_entry)
        """
        threshold = threshold or self.similarity_threshold
        query_tokens = self._tokenize(text)
        query_normalized = self._normalize_command(text)
        
        results = []
        
        with self._lock:
            for hash_key, entry in self._cache.items():
                if entry.is_expired:
                    continue
                
                # Compute combined similarity
                token_sim = self._jaccard_similarity(
                    query_tokens,
                    self._tokenize(entry.command_text)
                )
                string_sim = self._string_similarity(
                    query_normalized,
                    entry.command_normalized
                )
                
                # Weighted average (tokens more important for intent)
                combined_sim = (token_sim * 0.6) + (string_sim * 0.4)
                
                if combined_sim >= threshold:
                    results.append((entry.command_text, combined_sim, entry))
        
        # Sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results
    
    def is_duplicate(self, text: str, time_window: float = 5.0) -> Tuple[bool, Optional[str]]:
        """
        Check if command is a duplicate (same command within time window).
        
        Args:
            text: Command text
            time_window: Time window in seconds
        
        Returns:
            (is_duplicate, original_command_text)
        """
        exact_hash = self._compute_exact_hash(text)
        
        with self._lock:
            if exact_hash in self._cache:
                entry = self._cache[exact_hash]
                if time.time() - entry.timestamp < time_window:
                    return True, entry.command_text
        
        return False, None
    
    # =========================================================================
    # Cache Operations
    # =========================================================================
    
    def get(self, text: str) -> Optional[CacheEntry]:
        """
        Get cached response for exact command match.
        
        Args:
            text: Command text
        
        Returns:
            CacheEntry if found and not expired, None otherwise
        """
        exact_hash = self._compute_exact_hash(text)
        
        with self._lock:
            if exact_hash in self._cache:
                entry = self._cache[exact_hash]
                
                if entry.is_expired:
                    self._evict(exact_hash)
                    self._stats['expirations'] += 1
                    self._stats['misses'] += 1
                    return None
                
                # Move to end (LRU)
                self._cache.move_to_end(exact_hash)
                entry.touch()
                self._stats['hits'] += 1
                return entry
            
            self._stats['misses'] += 1
            return None
    
    def get_fuzzy(self, text: str) -> Optional[CacheEntry]:
        """
        Get cached response using fuzzy matching.
        
        Returns highest similarity match above threshold.
        """
        similar = self.find_similar(text)
        if similar:
            best_match = similar[0]
            if best_match[1] >= self.similarity_threshold:
                self._stats['fuzzy_hits'] += 1
                return best_match[2]
        return None
    
    def put(
        self,
        text: str,
        response: str,
        parsed_result: Dict[str, Any] = None,
        ttl: float = None
    ) -> CacheEntry:
        """
        Cache a command and its response.
        
        Args:
            text: Original command text
            response: Generated response
            parsed_result: Parsed command structure
            ttl: Time-to-live in seconds
        
        Returns:
            Created CacheEntry
        """
        exact_hash = self._compute_exact_hash(text)
        fuzzy_hash = self._compute_fuzzy_hash(text)
        tokens = self._tokenize(text)
        
        entry = CacheEntry(
            command_hash=exact_hash,
            command_text=text,
            command_normalized=self._normalize_command(text),
            response=response,
            parsed_result=parsed_result or {},
            timestamp=time.time(),
            ttl_seconds=ttl or self.default_ttl
        )
        
        with self._lock:
            # Check capacity and evict if needed
            while len(self._cache) >= self.max_size:
                self._evict_oldest()
            
            # Add to primary cache
            self._cache[exact_hash] = entry
            self._cache.move_to_end(exact_hash)
            
            # Update fuzzy index
            if fuzzy_hash not in self._fuzzy_index:
                self._fuzzy_index[fuzzy_hash] = []
            if exact_hash not in self._fuzzy_index[fuzzy_hash]:
                self._fuzzy_index[fuzzy_hash].append(exact_hash)
            
            # Update token index
            for token in tokens:
                if token not in self._token_index:
                    self._token_index[token] = []
                if exact_hash not in self._token_index[token]:
                    self._token_index[token].append(exact_hash)
        
        return entry
    
    def _evict(self, hash_key: str):
        """Evict a single entry."""
        if hash_key in self._cache:
            entry = self._cache.pop(hash_key)
            
            # Clean up indexes
            fuzzy_hash = self._compute_fuzzy_hash(entry.command_text)
            if fuzzy_hash in self._fuzzy_index:
                self._fuzzy_index[fuzzy_hash] = [
                    h for h in self._fuzzy_index[fuzzy_hash] if h != hash_key
                ]
            
            for token in self._tokenize(entry.command_text):
                if token in self._token_index:
                    self._token_index[token] = [
                        h for h in self._token_index[token] if h != hash_key
                    ]
    
    def _evict_oldest(self):
        """Evict oldest (LRU) entry."""
        if self._cache:
            oldest_key = next(iter(self._cache))
            self._evict(oldest_key)
            self._stats['evictions'] += 1
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._fuzzy_index.clear()
            self._token_index.clear()
            self._fingerprints.clear()
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count removed."""
        removed = 0
        with self._lock:
            expired_keys = [
                k for k, v in self._cache.items() if v.is_expired
            ]
            for key in expired_keys:
                self._evict(key)
                removed += 1
                self._stats['expirations'] += 1
        return removed
    
    # =========================================================================
    # Statistics & Info
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics including LRU cache performance."""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            # Get LRU cache stats
            lru_stats = get_cache_stats()
            total_lru_hits = sum(s['hits'] for s in lru_stats.values())
            total_lru_misses = sum(s['misses'] for s in lru_stats.values())
            lru_hit_rate = (total_lru_hits / (total_lru_hits + total_lru_misses) * 100) if (total_lru_hits + total_lru_misses) > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'fuzzy_hits': self._stats['fuzzy_hits'],
                'hit_rate': round(hit_rate, 2),
                'evictions': self._stats['evictions'],
                'expirations': self._stats['expirations'],
                'unique_tokens': len(self._token_index),
                'fuzzy_buckets': len(self._fuzzy_index),
                # LRU cache performance
                'lru_hits': total_lru_hits,
                'lru_misses': total_lru_misses,
                'lru_hit_rate': round(lru_hit_rate, 2),
            }
    
    def get_lru_stats(self) -> Dict[str, Any]:
        """Get detailed LRU cache statistics for each function."""
        return get_cache_stats()
    
    def get_frequent_commands(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get most frequently used commands."""
        with self._lock:
            entries = [(e.command_text, e.hits) for e in self._cache.values()]
            entries.sort(key=lambda x: x[1], reverse=True)
            return entries[:limit]
    
    def __len__(self) -> int:
        return len(self._cache)
    
    def __contains__(self, text: str) -> bool:
        exact_hash = self._compute_exact_hash(text)
        return exact_hash in self._cache


# =============================================================================
# Response Cache Decorator
# =============================================================================

def cached_response(cache: 'CommandHashMap', ttl: float = 300.0):
    """
    Decorator to cache command responses.
    
    Usage:
        @cached_response(command_cache, ttl=60)
        def process_command(text: str) -> Tuple[dict, str]:
            # ... processing ...
            return parsed, response
    """
    def decorator(func: Callable):
        def wrapper(text: str, *args, **kwargs):
            # Check cache first
            entry = cache.get(text)
            if entry:
                return entry.parsed_result, entry.response
            
            # Check fuzzy match
            fuzzy_entry = cache.get_fuzzy(text)
            if fuzzy_entry:
                return fuzzy_entry.parsed_result, fuzzy_entry.response
            
            # Execute function
            parsed, response = func(text, *args, **kwargs)
            
            # Cache result
            cache.put(text, response, parsed, ttl)
            
            return parsed, response
        return wrapper
    return decorator


# =============================================================================
# Singleton Instance
# =============================================================================

_command_cache: Optional[CommandHashMap] = None


def get_command_cache() -> CommandHashMap:
    """Get the global command cache instance."""
    global _command_cache
    if _command_cache is None:
        _command_cache = CommandHashMap(
            max_size=1000,
            default_ttl=300.0,
            similarity_threshold=0.75
        )
    return _command_cache


# =============================================================================
# Demo / Test
# =============================================================================

if __name__ == "__main__":
    import timeit
    
    print("VoxMind Command Cache Demo")
    print("=" * 60)
    
    cache = get_command_cache()
    
    # Test commands
    test_commands = [
        ("open chrome", "Opened Google Chrome", {'command': 'open_app', 'app': 'chrome'}),
        ("launch chrome", "Opened Google Chrome", {'command': 'open_app', 'app': 'chrome'}),
        ("open google chrome", "Opened Google Chrome", {'command': 'open_app', 'app': 'chrome'}),
        ("what time is it", "It's 3:45 PM", {'command': 'time'}),
        ("what's the time", "It's 3:45 PM", {'command': 'time'}),
        ("current time", "It's 3:45 PM", {'command': 'time'}),
        ("volume up", "Volume increased", {'command': 'volume_up'}),
        ("make it louder", "Volume increased", {'command': 'volume_up'}),
        ("turn up the volume", "Volume increased", {'command': 'volume_up'}),
    ]
    
    print("\n📝 Caching commands...")
    for cmd, response, parsed in test_commands:
        cache.put(cmd, response, parsed)
        print(f"  Cached: '{cmd}'")
    
    # Test exact match
    print("\n🔍 Testing exact match:")
    entry = cache.get("open chrome")
    if entry:
        print(f"  ✅ Found: '{entry.command_text}' -> '{entry.response}'")
    
    # Test similar command detection
    print("\n🔎 Testing similar command detection:")
    test_queries = [
        "start chrome",
        "run google chrome please",
        "tell me the time",
        "increase volume",
    ]
    
    for query in test_queries:
        similar = cache.find_similar(query, threshold=0.5)
        print(f"\n  Query: '{query}'")
        if similar:
            for orig, score, entry in similar[:3]:
                print(f"    → {score:.0%} similar to '{orig}'")
        else:
            print("    → No similar commands found")
    
    # Test duplicate detection
    print("\n🔄 Testing duplicate detection:")
    is_dup, orig = cache.is_duplicate("open chrome", time_window=60)
    print(f"  'open chrome' is duplicate: {is_dup}")
    
    # Test fingerprinting
    print("\n🔖 Testing fingerprinting:")
    fp = cache.fingerprint("open chrome and search for weather")
    print(f"  Exact hash: {fp.hash_exact}")
    print(f"  Fuzzy hash: {fp.hash_fuzzy}")
    print(f"  Tokens: {list(fp.tokens)}")
    
    # =========================================================================
    # LRU Cache Performance Benchmark
    # =========================================================================
    print("\n" + "=" * 60)
    print("⚡ LRU CACHE PERFORMANCE BENCHMARK")
    print("=" * 60)
    
    # Clear caches for fair test
    clear_all_caches()
    
    test_text = "please open google chrome browser for me"
    iterations = 10000
    
    # First call (cache miss)
    print(f"\n🔬 Testing with {iterations:,} iterations...")
    
    # Benchmark exact hash computation
    def test_exact_hash():
        compute_exact_hash_cached(test_text)
    
    # First run (cold)
    time_cold = timeit.timeit(test_exact_hash, number=1) * 1000
    
    # Subsequent runs (warm - cached)
    time_warm = timeit.timeit(test_exact_hash, number=iterations) * 1000 / iterations
    
    print(f"\n  Exact Hash Computation:")
    print(f"    • Cold (first call):  {time_cold:.4f} ms")
    print(f"    • Warm (cached):      {time_warm:.6f} ms")
    print(f"    • Speedup:            {time_cold/time_warm:.0f}x faster")
    
    # Benchmark tokenization
    clear_all_caches()
    
    def test_tokenize():
        tokenize_cached(test_text)
    
    time_cold = timeit.timeit(test_tokenize, number=1) * 1000
    time_warm = timeit.timeit(test_tokenize, number=iterations) * 1000 / iterations
    
    print(f"\n  Tokenization:")
    print(f"    • Cold (first call):  {time_cold:.4f} ms")
    print(f"    • Warm (cached):      {time_warm:.6f} ms")
    print(f"    • Speedup:            {time_cold/time_warm:.0f}x faster")
    
    # Benchmark Levenshtein
    clear_all_caches()
    s1, s2 = "open google chrome", "launch chrome browser"
    
    def test_levenshtein():
        levenshtein_distance_cached(s1, s2)
    
    time_cold = timeit.timeit(test_levenshtein, number=1) * 1000
    time_warm = timeit.timeit(test_levenshtein, number=iterations) * 1000 / iterations
    
    print(f"\n  Levenshtein Distance:")
    print(f"    • Cold (first call):  {time_cold:.4f} ms")
    print(f"    • Warm (cached):      {time_warm:.6f} ms")
    print(f"    • Speedup:            {time_cold/time_warm:.0f}x faster")
    
    # Final stats
    print(f"\n📊 Cache Statistics:")
    stats = cache.get_stats()
    print(f"\n  Command Cache:")
    for key in ['size', 'hits', 'misses', 'fuzzy_hits', 'hit_rate']:
        print(f"    • {key}: {stats[key]}")
    
    print(f"\n  LRU Function Caches:")
    print(f"    • Total LRU hits:     {stats['lru_hits']:,}")
    print(f"    • Total LRU misses:   {stats['lru_misses']:,}")
    print(f"    • LRU hit rate:       {stats['lru_hit_rate']}%")
    
    print(f"\n  Per-Function LRU Stats:")
    lru_stats = cache.get_lru_stats()
    for func_name, info in lru_stats.items():
        print(f"    • {func_name:15} hits={info['hits']:>5}, misses={info['misses']:>3}, size={info['currsize']}/{info['maxsize']}")
    
    print("\n" + "=" * 60)
    print("✅ Demo complete!")
    print("=" * 60)
