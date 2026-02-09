"""
VoxMind Cython-Optimized Functions
==================================
Type-annotated functions ready for Cython compilation.

To compile with Cython:
1. Rename this file to cython_optimized.pyx
2. Create setup.py (see below)
3. Run: python setup.py build_ext --inplace

These functions are the CPU-bound hot paths identified by profiling.
They can be used as-is in pure Python or compiled with Cython for ~10-50x speedup.

Setup.py template:
```python
from setuptools import setup
from Cython.Build import cythonize

setup(
    ext_modules=cythonize(
        "core/cython_optimized.pyx",
        compiler_directives={'language_level': "3"}
    )
)
```
"""

from typing import List, Tuple, Dict, Optional
import re

# =============================================================================
# Type Hints for Cython (These become C types when compiled)
# =============================================================================

# In .pyx file, these would be:
# cdef int, cdef double, cdef str, etc.


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Compute Levenshtein edit distance between two strings.
    
    This is a CPU-bound O(n*m) algorithm that benefits greatly from Cython.
    In Cython, this becomes ~20x faster due to:
    - Native C integer operations
    - No Python object overhead
    - Bound checking disabled
    
    Cython version would use:
    ```cython
    @cython.boundscheck(False)
    @cython.wraparound(False)
    cpdef int levenshtein_distance(str s1, str s2):
        cdef int len1 = len(s1)
        cdef int len2 = len(s2)
        cdef int i, j, cost
        cdef list previous_row, current_row
        ...
    ```
    """
    # Type annotations for Cython
    len1: int = len(s1)
    len2: int = len(s2)
    
    if len1 < len2:
        return levenshtein_distance(s2, s1)
    
    if len2 == 0:
        return len1
    
    # In Cython: cdef int* previous_row = <int*>malloc(...)
    previous_row: List[int] = list(range(len2 + 1))
    current_row: List[int] = [0] * (len2 + 1)
    
    i: int
    j: int
    c1: str
    c2: str
    insertions: int
    deletions: int
    substitutions: int
    
    for i in range(len1):
        c1 = s1[i]
        current_row[0] = i + 1
        
        for j in range(len2):
            c2 = s2[j]
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (0 if c1 == c2 else 1)
            current_row[j + 1] = min(insertions, deletions, substitutions)
        
        # Swap rows
        previous_row, current_row = current_row, previous_row
    
    return previous_row[len2]


def levenshtein_similarity(s1: str, s2: str) -> float:
    """
    Compute similarity ratio (0.0 to 1.0) between two strings.
    """
    if not s1 or not s2:
        return 0.0
    
    max_len: int = max(len(s1), len(s2))
    distance: int = levenshtein_distance(s1.lower(), s2.lower())
    
    return 1.0 - (distance / max_len)


def jaccard_similarity(tokens1: List[str], tokens2: List[str]) -> float:
    """
    Compute Jaccard similarity between two token lists.
    
    In Cython with set operations optimized.
    """
    if not tokens1 or not tokens2:
        return 0.0
    
    set1: set = set(tokens1)
    set2: set = set(tokens2)
    
    intersection: int = len(set1 & set2)
    union: int = len(set1 | set2)
    
    return intersection / union if union > 0 else 0.0


def normalize_text(text: str) -> str:
    """
    Normalize text for matching.
    
    In Cython, regex operations still use Python's re module,
    but string operations are faster.
    """
    result: str = text.lower().strip()
    result = ' '.join(result.split())  # Normalize whitespace
    result = re.sub(r'[^\w\s\-]', '', result)  # Remove punctuation
    return result


# Stop words as a frozenset for O(1) lookup
STOP_WORDS: frozenset = frozenset({
    'a', 'an', 'the', 'to', 'for', 'of', 'and', 'or', 'is', 'it',
    'my', 'me', 'i', 'you', 'your', 'please', 'can', 'could', 'would',
    'just', 'now', 'hey', 'vox', 'okay', 'ok', 'um', 'uh', 'like'
})

# Synonyms as a dict for O(1) lookup
SYNONYMS: Dict[str, str] = {
    'launch': 'open', 'start': 'open', 'run': 'open', 'execute': 'open',
    'close': 'close', 'exit': 'close', 'quit': 'close', 'terminate': 'close', 'kill': 'close',
    'louder': 'volume_up', 'quieter': 'volume_down', 'softer': 'volume_down',
    'brighter': 'brightness_up', 'dimmer': 'brightness_down',
    'click': 'click', 'tap': 'click', 'press': 'press', 'hit': 'press',
    'type': 'type', 'write': 'type', 'enter': 'type',
    'search': 'search', 'find': 'search', 'google': 'search', 'look': 'search',
}


def tokenize_and_filter(text: str) -> Tuple[str, ...]:
    """
    Tokenize text, filter stop words, apply synonyms.
    
    Returns tuple for hashability (can be used as dict key).
    
    In Cython, list comprehensions become native loops.
    """
    normalized: str = normalize_text(text)
    tokens: List[str] = normalized.split()
    
    result: List[str] = []
    token: str
    
    for token in tokens:
        if token not in STOP_WORDS:
            token = SYNONYMS.get(token, token)
            result.append(token)
    
    return tuple(result)


def cosine_similarity_fast(vec1: List[float], vec2: List[float]) -> float:
    """
    Fast cosine similarity for embedding vectors.
    
    In Cython with numpy integration:
    ```cython
    import numpy as np
    cimport numpy as np
    
    @cython.boundscheck(False)
    cpdef double cosine_similarity_fast(np.ndarray[np.float64_t, ndim=1] vec1,
                                         np.ndarray[np.float64_t, ndim=1] vec2):
        cdef double dot = 0.0
        cdef double norm1 = 0.0
        cdef double norm2 = 0.0
        cdef int i
        cdef int n = vec1.shape[0]
        
        for i in range(n):
            dot += vec1[i] * vec2[i]
            norm1 += vec1[i] * vec1[i]
            norm2 += vec2[i] * vec2[i]
        
        return dot / (sqrt(norm1) * sqrt(norm2))
    ```
    """
    if len(vec1) != len(vec2):
        raise ValueError("Vectors must have same length")
    
    dot: float = 0.0
    norm1: float = 0.0
    norm2: float = 0.0
    
    i: int
    for i in range(len(vec1)):
        dot += vec1[i] * vec2[i]
        norm1 += vec1[i] * vec1[i]
        norm2 += vec2[i] * vec2[i]
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot / ((norm1 ** 0.5) * (norm2 ** 0.5))


def find_best_match(
    query: str,
    candidates: List[str],
    threshold: float = 0.7
) -> Optional[Tuple[str, float]]:
    """
    Find best matching string from candidates using Levenshtein.
    
    Returns (best_match, similarity_score) or None if below threshold.
    """
    best_match: Optional[str] = None
    best_score: float = threshold
    
    query_lower: str = query.lower()
    
    candidate: str
    score: float
    
    for candidate in candidates:
        score = levenshtein_similarity(query_lower, candidate.lower())
        if score > best_score:
            best_score = score
            best_match = candidate
    
    if best_match is not None:
        return (best_match, best_score)
    return None


def batch_similarity(
    query: str,
    candidates: List[str]
) -> List[Tuple[str, float]]:
    """
    Compute similarity scores for all candidates.
    
    In Cython, this can be parallelized with prange:
    ```cython
    from cython.parallel import prange
    
    for i in prange(n, nogil=True):
        scores[i] = levenshtein_similarity(query, candidates[i])
    ```
    """
    result: List[Tuple[str, float]] = []
    
    candidate: str
    for candidate in candidates:
        score = levenshtein_similarity(query, candidate)
        result.append((candidate, score))
    
    # Sort by score descending
    result.sort(key=lambda x: x[1], reverse=True)
    
    return result


# =============================================================================
# Benchmark / Demo
# =============================================================================

def benchmark_functions() -> Dict[str, float]:
    """Benchmark all functions and return timings."""
    import time
    
    results: Dict[str, float] = {}
    iterations = 10000
    
    # Test data
    s1 = "open google chrome browser"
    s2 = "launch chrome web browser"
    text = "please open the google chrome browser for me now"
    candidates = ["chrome", "firefox", "edge", "safari", "opera", "brave"]
    
    # Levenshtein
    start = time.perf_counter()
    for _ in range(iterations):
        levenshtein_distance(s1, s2)
    results['levenshtein'] = (time.perf_counter() - start) / iterations * 1000
    
    # Tokenize
    start = time.perf_counter()
    for _ in range(iterations):
        tokenize_and_filter(text)
    results['tokenize'] = (time.perf_counter() - start) / iterations * 1000
    
    # Jaccard
    tokens1 = list(tokenize_and_filter(s1))
    tokens2 = list(tokenize_and_filter(s2))
    start = time.perf_counter()
    for _ in range(iterations):
        jaccard_similarity(tokens1, tokens2)
    results['jaccard'] = (time.perf_counter() - start) / iterations * 1000
    
    # Find best match
    start = time.perf_counter()
    for _ in range(iterations // 10):
        find_best_match("chrom", candidates)
    results['find_match'] = (time.perf_counter() - start) / (iterations // 10) * 1000
    
    return results


if __name__ == "__main__":
    print("VoxMind Cython-Ready Functions")
    print("=" * 50)
    
    # Demo
    print("\n📊 Demo:")
    s1 = "open chrome browser"
    s2 = "launch chrome"
    
    print(f"  Levenshtein('{s1}', '{s2}'): {levenshtein_distance(s1, s2)}")
    print(f"  Similarity: {levenshtein_similarity(s1, s2):.2%}")
    
    text = "please open google chrome for me"
    tokens = tokenize_and_filter(text)
    print(f"\n  Tokenize('{text}'):")
    print(f"    {tokens}")
    
    # Benchmark
    print("\n⏱️ Benchmark (10,000 iterations each):")
    results = benchmark_functions()
    for name, ms in results.items():
        print(f"  {name}: {ms:.4f} ms/call")
    
    print("\n💡 To compile with Cython:")
    print("  1. pip install cython")
    print("  2. Rename to cython_optimized.pyx")
    print("  3. Create setup.py (see docstring)")
    print("  4. python setup.py build_ext --inplace")
    print("  5. Expected speedup: 10-50x for CPU-bound functions")
