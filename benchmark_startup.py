"""
VoxMind Startup Benchmark & Performance Analysis
=================================================
Comprehensive profiling for startup time and runtime performance.

Usage:
    python benchmark_startup.py              # Basic benchmark
    python benchmark_startup.py --detailed   # Detailed cProfile analysis
    python benchmark_startup.py --memory     # Include memory profiling
    python benchmark_startup.py --cython     # Show Cython candidates
"""
import time
import sys
import os
import argparse

# Setup path
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def benchmark_basic():
    """Basic startup timing benchmark."""
    print("=" * 60)
    print("VOXMIND STARTUP BENCHMARK")
    print("=" * 60)
    
    timings = {}
    start = time.perf_counter()
    
    # Core imports
    t1 = time.perf_counter()
    try:
        from Jalaj.speech_recognition_service import listen_for_command
        from Tejas.wake_word_detector import listen_for_wake_word
        from Priyapal.command_parser import parse_command as basic_parse
        timings['core_imports'] = time.perf_counter() - t1
        print(f"✓ Core imports: {timings['core_imports']:.3f}s")
    except ImportError as e:
        timings['core_imports'] = time.perf_counter() - t1
        print(f"⚠ Core imports (partial): {timings['core_imports']:.3f}s - {e}")
    
    # Volume control
    t1 = time.perf_counter()
    try:
        from Soumyadeb.audio.volume_control import volume_up
        timings['volume_control'] = time.perf_counter() - t1
        print(f"✓ Volume control: {timings['volume_control']:.3f}s")
    except ImportError as e:
        timings['volume_control'] = time.perf_counter() - t1
        print(f"⚠ Volume control: {timings['volume_control']:.3f}s - {e}")
    
    # NLP module (deferred load)
    t1 = time.perf_counter()
    try:
        from Tejas.nlp_command_parser import NLP_AVAILABLE, NLPCommandParser
        timings['nlp_check'] = time.perf_counter() - t1
        print(f"✓ NLP module check: {timings['nlp_check']:.3f}s (available: {NLP_AVAILABLE})")
    except ImportError as e:
        timings['nlp_check'] = time.perf_counter() - t1
        print(f"⚠ NLP module: {timings['nlp_check']:.3f}s - {e}")
        NLP_AVAILABLE = False
    
    # OCR Engine
    t1 = time.perf_counter()
    try:
        from core.ocr_engine import OCREngine, HAS_EASYOCR, HAS_TESSERACT
        timings['ocr_engine'] = time.perf_counter() - t1
        backends = []
        if HAS_EASYOCR: backends.append("EasyOCR")
        if HAS_TESSERACT: backends.append("Tesseract")
        print(f"✓ OCR Engine: {timings['ocr_engine']:.3f}s (backends: {', '.join(backends) or 'none'})")
    except ImportError as e:
        timings['ocr_engine'] = time.perf_counter() - t1
        print(f"⚠ OCR Engine: {timings['ocr_engine']:.3f}s - {e}")
    
    # Command Cache
    t1 = time.perf_counter()
    try:
        from core.command_cache import CommandHashMap, get_cache_stats
        timings['command_cache'] = time.perf_counter() - t1
        print(f"✓ Command Cache: {timings['command_cache']:.3f}s")
    except ImportError as e:
        timings['command_cache'] = time.perf_counter() - t1
        print(f"⚠ Command Cache: {timings['command_cache']:.3f}s - {e}")
    
    # Natural Language Engine
    t1 = time.perf_counter()
    try:
        from core.natural_language_engine import NaturalLanguageEngine
        timings['nle'] = time.perf_counter() - t1
        print(f"✓ NL Engine: {timings['nle']:.3f}s")
    except ImportError as e:
        timings['nle'] = time.perf_counter() - t1
        print(f"⚠ NL Engine: {timings['nle']:.3f}s - {e}")
    
    # Screen Context
    t1 = time.perf_counter()
    try:
        from core.screen_context import ScreenContext
        timings['screen_context'] = time.perf_counter() - t1
        print(f"✓ Screen Context: {timings['screen_context']:.3f}s")
    except ImportError as e:
        timings['screen_context'] = time.perf_counter() - t1
        print(f"⚠ Screen Context: {timings['screen_context']:.3f}s - {e}")
    
    # Background model loading (non-blocking)
    t1 = time.perf_counter()
    if NLP_AVAILABLE:
        NLPCommandParser.preload_model()
        timings['nlp_preload_start'] = time.perf_counter() - t1
        print(f"✓ NLP preload initiated: {timings['nlp_preload_start']:.3f}s (background)")
    
    total = time.perf_counter() - start
    
    print("-" * 60)
    print(f"TOTAL STARTUP TIME: {total:.3f}s")
    print("-" * 60)
    
    # Recommendations
    print("\n📊 PERFORMANCE RECOMMENDATIONS:")
    slow_threshold = 0.1  # 100ms
    for name, duration in sorted(timings.items(), key=lambda x: -x[1]):
        if duration > slow_threshold:
            print(f"  ⚠ {name}: {duration:.3f}s - Consider lazy loading")
    
    if total < 1.0:
        print(f"\n✅ Startup is fast ({total:.2f}s < 1s target)")
    elif total < 2.0:
        print(f"\n⚠ Startup is acceptable ({total:.2f}s)")
    else:
        print(f"\n❌ Startup is slow ({total:.2f}s > 2s) - optimize imports")
    
    return timings


def benchmark_detailed():
    """Detailed cProfile analysis."""
    print("\n" + "=" * 60)
    print("DETAILED PROFILING (cProfile)")
    print("=" * 60)
    
    try:
        from core.profiler import run_with_cprofile, profile_startup
        
        result, stats = run_with_cprofile(profile_startup)
        
        print("\nStartup Component Timings:")
        for key, value in result.items():
            print(f"  {key}: {value}")
        
        print("\nTop Functions by Cumulative Time:")
        print(stats[:2000])  # First 2000 chars of stats
        
    except ImportError as e:
        print(f"Could not import profiler: {e}")
        print("Run basic benchmark instead")
        benchmark_basic()


def benchmark_memory():
    """Memory profiling during startup."""
    print("\n" + "=" * 60)
    print("MEMORY PROFILING")
    print("=" * 60)
    
    try:
        from core.profiler import get_memory_snapshot, profile_memory
        
        # Before imports
        mem_before = get_memory_snapshot()
        print(f"\nBefore imports: {mem_before}")
        
        # Import heavy modules
        def heavy_imports():
            from core.natural_language_engine import NaturalLanguageEngine
            from core.screen_context import ScreenContext
            from core.ocr_engine import OCREngine
        
        result, mem_stats = profile_memory(heavy_imports)
        
        # After imports
        mem_after = get_memory_snapshot()
        
        print(f"After imports: {mem_after}")
        print(f"\nMemory Delta:")
        print(f"  Peak during imports: {mem_stats['peak_mb']:.2f} MB")
        
        if mem_stats['peak_mb'] > 100:
            print("\n⚠ High memory usage - consider lazy loading heavy modules")
        else:
            print("\n✅ Memory usage is reasonable")
            
    except ImportError as e:
        print(f"Could not run memory profiling: {e}")
        print("Install psutil for better memory stats: pip install psutil")


def show_cython_candidates():
    """Show functions that would benefit from Cython compilation."""
    print("\n" + "=" * 60)
    print("CYTHON OPTIMIZATION CANDIDATES")
    print("=" * 60)
    
    try:
        from core.profiler import print_cython_guide
        print_cython_guide()
    except ImportError:
        print("""
CPU-bound functions that would benefit from Cython:

1. core/command_cache.py:
   - levenshtein_distance_cached() - Pure CPU string comparison
   - tokenize_cached() - String tokenization
   
2. core/natural_language_engine.py:
   - FuzzyMatcher.levenshtein_distance() - Edit distance calculation
   
3. core/screen_context.py:
   - Any pixel-level image processing

To compile with Cython:
1. pip install cython
2. Create .pyx file with type hints
3. python setup.py build_ext --inplace
""")


def main():
    parser = argparse.ArgumentParser(description='VoxMind Startup Benchmark')
    parser.add_argument('--detailed', action='store_true', help='Run detailed cProfile analysis')
    parser.add_argument('--memory', action='store_true', help='Include memory profiling')
    parser.add_argument('--cython', action='store_true', help='Show Cython optimization candidates')
    parser.add_argument('--all', action='store_true', help='Run all benchmarks')
    
    args = parser.parse_args()
    
    # Always run basic benchmark
    timings = benchmark_basic()
    
    if args.detailed or args.all:
        benchmark_detailed()
    
    if args.memory or args.all:
        benchmark_memory()
    
    if args.cython or args.all:
        show_cython_candidates()
    
    # Print profiler report if available
    try:
        from core.profiler import PerformanceMonitor
        PerformanceMonitor.print_report()
    except ImportError:
        pass
    
    print("\n💡 Tips:")
    print("  - Use 'python benchmark_startup.py --all' for complete analysis")
    print("  - NLP models load in background while waiting for wake word")
    print("  - Use lazy loading for rarely-used modules")


if __name__ == "__main__":
    main()
