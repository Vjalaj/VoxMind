# VoxMind Performance Optimization Guide

## Overview

This guide documents the performance optimization infrastructure added to VoxMind, including profiling tools, lazy loading, caching improvements, async patterns, and Cython compilation support.

## New Modules Created

### 1. `core/profiler.py` - Performance Profiling

**Purpose:** Comprehensive profiling utilities for identifying bottlenecks.

```python
from core.profiler import profile, PerformanceMonitor, run_with_cprofile

# Decorator for function profiling
@profile
def my_function():
    ...

# Context manager for code blocks
with PerformanceMonitor.measure("operation_name"):
    do_something()

# Get performance report
PerformanceMonitor.print_report()
```

**Features:**
- Function-level timing with `@profile` decorator
- Memory profiling with `@profile(track_memory=True)`
- Automatic hot path identification
- Cython candidate detection
- cProfile integration

---

### 2. `core/lazy_loader.py` - Lazy Loading Utilities

**Purpose:** Defer heavy imports and model loading until needed.

```python
from core.lazy_loader import LazyLoader, LazyModel, lazy_property

# Lazy module import (doesn't load until accessed)
easyocr = LazyLoader('easyocr')

# Lazy model with background preloading
model = LazyModel(load_function, preload=True)
result = model.get()  # Blocks only if not ready

# Lazy property
class MyClass:
    @lazy_property
    def heavy_resource(self):
        return load_heavy_resource()
```

**Pre-configured lazy loaders:**
- `sentence_transformers`, `torch`, `tensorflow`
- `easyocr`, `pytesseract`
- `cv2`, `PIL`
- `speech_recognition`, `pyaudio`

---

### 3. `core/async_utils.py` - Async Patterns

**Purpose:** Async wrappers for I/O-bound operations.

```python
from core.async_utils import run_async, AsyncCache, async_retry

# Run blocking code in thread pool
result = await run_async(blocking_function, arg1, arg2)

# Async cache with TTL
cache = AsyncCache()
await cache.set("key", "value", ttl=60)
value = await cache.get("key")

# Retry with exponential backoff
@retry(max_attempts=3, delay=1.0)
async def flaky_api_call():
    ...
```

**Features:**
- Thread pool for blocking operations
- Async cache with TTL
- Retry with exponential backoff
- Event bus for decoupled communication
- Background task queue

---

### 4. `core/cython_optimized.py` - Cython-Ready Functions

**Purpose:** Type-annotated hot path functions ready for Cython compilation.

**CPU-bound functions included:**
- `levenshtein_distance()` - String edit distance
- `levenshtein_similarity()` - Similarity ratio
- `jaccard_similarity()` - Token set similarity
- `tokenize_and_filter()` - Text tokenization
- `cosine_similarity_fast()` - Vector similarity
- `batch_similarity()` - Batch comparisons

**To compile with Cython:**
```bash
pip install cython
python setup_cython.py build_ext --inplace
```

Expected speedup: **10-50x** for CPU-bound functions.

---

### 5. `core/command_cache.py` - Enhanced Caching

**New features added:**

**TieredCache (Hot/Warm/Cold):**
```python
from core.command_cache import get_tiered_cache

cache = get_tiered_cache()
cache.set("key", "value")
value = cache.get("key")  # Auto-promotes on access
```

**Memory-aware eviction:**
- Monitors process memory
- Aggressive eviction under memory pressure
- Configurable limits

---

## Enhanced `benchmark_startup.py`

Run comprehensive startup analysis:

```bash
# Basic benchmark
python benchmark_startup.py

# Detailed cProfile analysis
python benchmark_startup.py --detailed

# Include memory profiling
python benchmark_startup.py --memory

# Show Cython candidates
python benchmark_startup.py --cython

# Run all benchmarks
python benchmark_startup.py --all
```

---

## Performance Recommendations

### 1. Startup Optimization

| Module | Recommendation |
|--------|---------------|
| NLP Model | ✅ Already lazy-loads in background |
| OCR Engine | ✅ EasyOCR reader lazy-loads on first use |
| Wake Word | Consider Porcupine (C++ under the hood) |
| Screen Context | Lazy imports for PIL/Tesseract |

### 2. Runtime Optimization

| Operation | Solution |
|-----------|----------|
| Repeated commands | LRU cache (already implemented) |
| Similar commands | Fuzzy hash index + tiered cache |
| API calls | Async with retry + caching |
| Heavy models | Keep in memory, don't reload |

### 3. Memory Optimization

| Issue | Solution |
|-------|----------|
| Large models | Lazy loading, unload when idle |
| Cache bloat | TieredCache with eviction |
| Leaks | Use weak references for callbacks |

---

## Profiling Workflow

### Step 1: Profile Startup
```bash
python benchmark_startup.py --all
```

### Step 2: Identify Hot Paths
```python
from core.profiler import PerformanceMonitor

# Run your code...

# Check results
PerformanceMonitor.print_report()
```

### Step 3: Optimize Hot Paths

For **CPU-bound** (computation):
1. Check `core/cython_optimized.py`
2. Compile with Cython: `python setup_cython.py build_ext --inplace`

For **I/O-bound** (network, disk):
1. Use `await run_async()` for blocking calls
2. Use `AsyncCache` for repeated requests

For **Memory-bound**:
1. Use `LazyModel` for large models
2. Use `TieredCache` for data caching

---

## Quick Reference

### Add Profiling to a Function
```python
from core.profiler import profile

@profile
def my_slow_function():
    ...
```

### Make Blocking Code Async
```python
from core.async_utils import run_async

result = await run_async(blocking_io_operation, arg1, arg2)
```

### Lazy Load a Heavy Module
```python
from core.lazy_loader import LazyLoader

heavy_lib = LazyLoader('heavy_library')
# Not loaded until:
heavy_lib.some_function()
```

### Cache with TTL
```python
from core.async_utils import AsyncCache

cache = AsyncCache(default_ttl=60.0)
await cache.set("key", "value")
```

---

## Files Modified/Created

| File | Status | Description |
|------|--------|-------------|
| `core/profiler.py` | ✨ New | Profiling utilities |
| `core/lazy_loader.py` | ✨ New | Lazy loading patterns |
| `core/async_utils.py` | ✨ New | Async utilities |
| `core/cython_optimized.py` | ✨ New | Cython-ready functions |
| `setup_cython.py` | ✨ New | Cython build script |
| `benchmark_startup.py` | 📝 Enhanced | Added detailed profiling |
| `core/command_cache.py` | 📝 Enhanced | Added TieredCache |

---

## When to Use C/C++

Based on analysis of VoxMind:

### ✅ Use C/C++ Libraries (via Python bindings)
- **OpenCV** for image processing (already C++)
- **Whisper.cpp** for speech recognition
- **Porcupine** for wake word detection
- **PyTorch/TensorFlow** (already optimized)

### ⚠️ Consider Cython for
- Levenshtein distance (done in `cython_optimized.py`)
- Custom tokenization loops
- Batch similarity calculations

### ❌ Don't Need C/C++ for
- API calls (I/O bound)
- Command parsing (fast enough)
- UI rendering (Qt handles it)

---

## Next Steps

1. **Run benchmarks** to establish baseline
2. **Profile** your specific use cases
3. **Optimize** identified bottlenecks
4. **Compile Cython** if CPU-bound issues remain
5. **Monitor** with ongoing profiling
