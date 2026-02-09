"""
VoxMind Performance Profiler
============================
Comprehensive profiling utilities for identifying performance bottlenecks.

Features:
- Function-level profiling with decorators
- Memory profiling
- Hot path identification
- Cython compilation candidates
- Performance metrics collection

Usage:
    from core.profiler import profile, profile_memory, PerformanceMonitor
    
    @profile
    def my_function():
        ...
    
    with PerformanceMonitor("my_operation"):
        ...
"""

import cProfile
import pstats
import time
import functools
import logging
import threading
import tracemalloc
import io
import sys
from typing import Dict, Any, Callable, Optional, List, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# Performance Metrics Data Classes
# =============================================================================

@dataclass
class FunctionMetrics:
    """Metrics for a single function."""
    name: str
    module: str
    total_calls: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0
    last_call_time: float = 0.0
    memory_peak: int = 0  # bytes
    is_hot_path: bool = False
    cython_candidate: bool = False
    
    def update(self, execution_time: float, memory_delta: int = 0):
        """Update metrics after a function call."""
        self.total_calls += 1
        self.total_time += execution_time
        self.last_call_time = execution_time
        self.min_time = min(self.min_time, execution_time)
        self.max_time = max(self.max_time, execution_time)
        self.avg_time = self.total_time / self.total_calls
        self.memory_peak = max(self.memory_peak, memory_delta)
        
        # Mark as hot path if called frequently or takes significant time
        if self.total_calls > 100 or self.avg_time > 0.1:
            self.is_hot_path = True
        
        # Mark as Cython candidate if CPU-bound and called frequently
        if self.is_hot_path and self.avg_time > 0.01 and self.total_calls > 10:
            self.cython_candidate = True


@dataclass
class ProfileReport:
    """Complete profiling report."""
    timestamp: float = field(default_factory=time.time)
    functions: Dict[str, FunctionMetrics] = field(default_factory=dict)
    hot_paths: List[str] = field(default_factory=list)
    cython_candidates: List[str] = field(default_factory=list)
    total_memory_peak: int = 0
    startup_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'hot_paths': self.hot_paths,
            'cython_candidates': self.cython_candidates,
            'total_memory_peak_mb': self.total_memory_peak / (1024 * 1024),
            'startup_time': self.startup_time,
            'function_count': len(self.functions),
        }


# =============================================================================
# Global Performance Monitor
# =============================================================================

class PerformanceMonitor:
    """
    Global performance monitoring singleton.
    
    Usage:
        # As context manager
        with PerformanceMonitor.measure("operation_name"):
            do_something()
        
        # Get metrics
        report = PerformanceMonitor.get_report()
    """
    
    _instance: Optional['PerformanceMonitor'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance
    
    def _init(self):
        """Initialize the monitor."""
        self.metrics: Dict[str, FunctionMetrics] = {}
        self.enabled = True
        self.memory_tracking = False
        self._start_time = time.time()
    
    @classmethod
    def instance(cls) -> 'PerformanceMonitor':
        """Get or create singleton instance."""
        return cls()
    
    @classmethod
    @contextmanager
    def measure(cls, name: str, track_memory: bool = False):
        """
        Context manager for measuring execution time.
        
        Args:
            name: Operation name for tracking
            track_memory: Whether to track memory allocation
        """
        monitor = cls.instance()
        if not monitor.enabled:
            yield
            return
        
        memory_start = 0
        if track_memory:
            tracemalloc.start()
            memory_start = tracemalloc.get_traced_memory()[0]
        
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            memory_delta = 0
            
            if track_memory:
                memory_delta = tracemalloc.get_traced_memory()[0] - memory_start
                tracemalloc.stop()
            
            monitor._record(name, elapsed, memory_delta)
    
    def _record(self, name: str, elapsed: float, memory_delta: int):
        """Record a measurement."""
        if name not in self.metrics:
            parts = name.rsplit('.', 1)
            module = parts[0] if len(parts) > 1 else '__main__'
            func_name = parts[-1]
            self.metrics[name] = FunctionMetrics(name=func_name, module=module)
        
        self.metrics[name].update(elapsed, memory_delta)
    
    @classmethod
    def get_report(cls) -> ProfileReport:
        """Generate a profiling report."""
        monitor = cls.instance()
        report = ProfileReport()
        report.functions = monitor.metrics.copy()
        report.startup_time = time.time() - monitor._start_time
        
        # Identify hot paths and Cython candidates
        for name, metrics in monitor.metrics.items():
            if metrics.is_hot_path:
                report.hot_paths.append(name)
            if metrics.cython_candidate:
                report.cython_candidates.append(name)
        
        # Sort by total time
        report.hot_paths.sort(
            key=lambda n: monitor.metrics[n].total_time,
            reverse=True
        )
        
        return report
    
    @classmethod
    def print_report(cls):
        """Print a formatted profiling report."""
        report = cls.get_report()
        
        print("\n" + "=" * 70)
        print("VOXMIND PERFORMANCE REPORT")
        print("=" * 70)
        print(f"Uptime: {report.startup_time:.2f}s")
        print(f"Functions tracked: {len(report.functions)}")
        
        if report.hot_paths:
            print("\n🔥 HOT PATHS (optimize these first):")
            print("-" * 50)
            for name in report.hot_paths[:10]:
                m = report.functions[name]
                print(f"  {name}")
                print(f"    Calls: {m.total_calls}, Total: {m.total_time:.3f}s, Avg: {m.avg_time*1000:.2f}ms")
        
        if report.cython_candidates:
            print("\n⚡ CYTHON CANDIDATES (CPU-bound hot paths):")
            print("-" * 50)
            for name in report.cython_candidates[:5]:
                m = report.functions[name]
                print(f"  {name} - {m.total_calls} calls, avg {m.avg_time*1000:.2f}ms")
        
        print("=" * 70 + "\n")
    
    @classmethod
    def reset(cls):
        """Reset all metrics."""
        monitor = cls.instance()
        monitor.metrics.clear()
        monitor._start_time = time.time()


# =============================================================================
# Profiling Decorators
# =============================================================================

def profile(func: Callable = None, *, track_memory: bool = False) -> Callable:
    """
    Decorator to profile a function's execution time.
    
    Usage:
        @profile
        def my_function():
            ...
        
        @profile(track_memory=True)
        def memory_heavy_function():
            ...
    """
    def decorator(fn: Callable) -> Callable:
        name = f"{fn.__module__}.{fn.__qualname__}"
        
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            with PerformanceMonitor.measure(name, track_memory=track_memory):
                return fn(*args, **kwargs)
        
        return wrapper
    
    if func is not None:
        return decorator(func)
    return decorator


def profile_async(func: Callable = None, *, track_memory: bool = False) -> Callable:
    """
    Decorator to profile async functions.
    
    Usage:
        @profile_async
        async def my_async_function():
            ...
    """
    def decorator(fn: Callable) -> Callable:
        name = f"{fn.__module__}.{fn.__qualname__}"
        
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return await fn(*args, **kwargs)
            finally:
                elapsed = time.perf_counter() - start
                PerformanceMonitor.instance()._record(name, elapsed, 0)
        
        return wrapper
    
    if func is not None:
        return decorator(func)
    return decorator


# =============================================================================
# cProfile Integration
# =============================================================================

def run_with_cprofile(func: Callable, *args, **kwargs) -> Tuple[Any, str]:
    """
    Run a function with cProfile and return result + stats.
    
    Returns:
        Tuple of (function_result, formatted_stats_string)
    """
    profiler = cProfile.Profile()
    result = profiler.runcall(func, *args, **kwargs)
    
    # Format stats
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats('cumulative')
    stats.print_stats(30)
    
    return result, stream.getvalue()


def profile_startup() -> Dict[str, Any]:
    """
    Profile VoxMind startup and return detailed timing.
    
    Returns:
        Dictionary with timing for each component
    """
    timings = {}
    
    # Core imports
    start = time.perf_counter()
    with PerformanceMonitor.measure("startup.core_imports"):
        pass  # Already imported
    timings['core_imports'] = time.perf_counter() - start
    
    # NLP module
    start = time.perf_counter()
    try:
        from Tejas.nlp_command_parser import NLP_AVAILABLE, NLPCommandParser
        timings['nlp_check'] = time.perf_counter() - start
        timings['nlp_available'] = NLP_AVAILABLE
    except ImportError:
        timings['nlp_check'] = time.perf_counter() - start
        timings['nlp_available'] = False
    
    # OCR Engine
    start = time.perf_counter()
    try:
        from core.ocr_engine import OCREngine, HAS_EASYOCR, HAS_TESSERACT
        timings['ocr_import'] = time.perf_counter() - start
        timings['ocr_easyocr'] = HAS_EASYOCR
        timings['ocr_tesseract'] = HAS_TESSERACT
    except ImportError:
        timings['ocr_import'] = time.perf_counter() - start
    
    # Cache module
    start = time.perf_counter()
    try:
        from core.command_cache import CommandHashMap, get_cache_stats
        timings['cache_import'] = time.perf_counter() - start
    except ImportError:
        timings['cache_import'] = time.perf_counter() - start
    
    return timings


# =============================================================================
# Memory Profiling
# =============================================================================

def profile_memory(func: Callable, *args, **kwargs) -> Tuple[Any, Dict[str, Any]]:
    """
    Profile memory usage of a function.
    
    Returns:
        Tuple of (result, memory_stats)
    """
    tracemalloc.start()
    
    result = func(*args, **kwargs)
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    stats = {
        'current_mb': current / (1024 * 1024),
        'peak_mb': peak / (1024 * 1024),
    }
    
    return result, stats


def get_memory_snapshot() -> Dict[str, Any]:
    """Get current memory usage snapshot."""
    import gc
    gc.collect()
    
    try:
        import psutil
        process = psutil.Process()
        mem = process.memory_info()
        return {
            'rss_mb': mem.rss / (1024 * 1024),
            'vms_mb': mem.vms / (1024 * 1024),
        }
    except ImportError:
        return {'note': 'Install psutil for memory stats'}


# =============================================================================
# Cython Compilation Helpers
# =============================================================================

CYTHON_CANDIDATES = """
# VoxMind Cython Compilation Candidates
# =====================================
# These functions are CPU-bound hot paths that would benefit from Cython.
# 
# To compile with Cython:
# 1. Rename file to .pyx
# 2. Add type annotations
# 3. Create setup.py with cythonize
#
# Priority candidates based on profiling:

## core/command_cache.py
- levenshtein_distance_cached() - Edit distance is pure CPU
- tokenize_cached() - String processing
- normalize_command_cached() - Regex operations

## core/natural_language_engine.py  
- FuzzyMatcher.levenshtein_distance() - Duplicate of cached version
- FuzzyMatcher.fuzzy_match() - Heavy string processing

## core/screen_context.py
- Image processing loops (if not using OpenCV)
- Pixel analysis functions

## Example Cython optimization for Levenshtein:

```cython
# levenshtein.pyx
cimport cython
from libc.stdlib cimport malloc, free

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int levenshtein_distance(str s1, str s2):
    cdef int len1 = len(s1)
    cdef int len2 = len(s2)
    cdef int* prev = <int*>malloc((len2 + 1) * sizeof(int))
    cdef int* curr = <int*>malloc((len2 + 1) * sizeof(int))
    cdef int i, j, cost
    
    for j in range(len2 + 1):
        prev[j] = j
    
    for i in range(1, len1 + 1):
        curr[0] = i
        for j in range(1, len2 + 1):
            cost = 0 if s1[i-1] == s2[j-1] else 1
            curr[j] = min(prev[j] + 1, curr[j-1] + 1, prev[j-1] + cost)
        prev, curr = curr, prev
    
    result = prev[len2]
    free(prev)
    free(curr)
    return result
```
"""


def identify_cython_candidates() -> List[str]:
    """Identify functions that would benefit from Cython compilation."""
    report = PerformanceMonitor.get_report()
    return report.cython_candidates


def print_cython_guide():
    """Print guide for Cython optimization."""
    print(CYTHON_CANDIDATES)


# =============================================================================
# Benchmarking Utilities
# =============================================================================

def benchmark(func: Callable, iterations: int = 100, warmup: int = 5) -> Dict[str, float]:
    """
    Benchmark a function with multiple iterations.
    
    Args:
        func: Function to benchmark (no arguments)
        iterations: Number of iterations
        warmup: Warmup iterations (not counted)
    
    Returns:
        Dictionary with timing statistics
    """
    # Warmup
    for _ in range(warmup):
        func()
    
    # Benchmark
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        times.append(time.perf_counter() - start)
    
    return {
        'iterations': iterations,
        'total': sum(times),
        'mean': sum(times) / len(times),
        'min': min(times),
        'max': max(times),
        'median': sorted(times)[len(times) // 2],
    }


def compare_implementations(funcs: Dict[str, Callable], iterations: int = 100) -> Dict[str, Dict[str, float]]:
    """
    Compare multiple implementations of the same function.
    
    Args:
        funcs: Dictionary of {name: function}
        iterations: Iterations per function
    
    Returns:
        Dictionary of benchmark results
    """
    results = {}
    for name, func in funcs.items():
        print(f"Benchmarking {name}...")
        results[name] = benchmark(func, iterations)
    
    # Print comparison
    print("\n" + "=" * 50)
    print("BENCHMARK COMPARISON")
    print("=" * 50)
    
    sorted_results = sorted(results.items(), key=lambda x: x[1]['mean'])
    fastest = sorted_results[0][1]['mean']
    
    for name, stats in sorted_results:
        speedup = stats['mean'] / fastest if fastest > 0 else 1
        print(f"{name}: {stats['mean']*1000:.3f}ms avg ({speedup:.1f}x)")
    
    return results


if __name__ == "__main__":
    # Demo profiling
    print("VoxMind Profiler Demo")
    print("=" * 40)
    
    # Profile startup
    timings = profile_startup()
    print("\nStartup Timings:")
    for key, value in timings.items():
        print(f"  {key}: {value}")
    
    # Show memory
    mem = get_memory_snapshot()
    print("\nMemory Usage:")
    for key, value in mem.items():
        print(f"  {key}: {value}")
    
    print("\n" + CYTHON_CANDIDATES[:500] + "...")
