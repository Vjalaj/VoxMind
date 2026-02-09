"""
VoxMind Cython Build Configuration
==================================
Compiles performance-critical Python modules to C for ~10-50x speedup.

Usage:
    # Build in-place
    python setup_cython.py build_ext --inplace
    
    # Clean and rebuild
    python setup_cython.py clean --all
    python setup_cython.py build_ext --inplace

Prerequisites:
    pip install cython numpy

After building:
    The .so/.pyd files can be imported directly, replacing the .py versions.
"""

import sys
import os

try:
    from setuptools import setup, Extension
    from Cython.Build import cythonize
    HAS_CYTHON = True
except ImportError:
    HAS_CYTHON = False
    print("⚠️ Cython not installed. Install with: pip install cython")
    print("   Falling back to pure Python (no speedup)")

# Check for numpy (optional, for vector operations)
try:
    import numpy as np
    HAS_NUMPY = True
    numpy_include = np.get_include()
except ImportError:
    HAS_NUMPY = False
    numpy_include = None


# Compiler directives for maximum performance
CYTHON_DIRECTIVES = {
    'language_level': '3',
    'boundscheck': False,      # Disable bounds checking for speed
    'wraparound': False,       # Disable negative indexing
    'initializedcheck': False, # Don't check uninitialized variables
    'nonecheck': False,        # Don't check for None
    'cdivision': True,         # Use C division (faster, no ZeroDivisionError)
    'embedsignature': True,    # Include Python signatures in docstrings
}

# Modules to compile
CYTHON_MODULES = [
    # Core performance-critical modules
    Extension(
        "core.cython_optimized",
        ["core/cython_optimized.py"],  # Cython can compile .py files too
        include_dirs=[numpy_include] if HAS_NUMPY else [],
    ),
]


def build():
    """Build Cython extensions."""
    if not HAS_CYTHON:
        print("Cannot build without Cython. Install with: pip install cython")
        return
    
    print("=" * 60)
    print("VoxMind Cython Build")
    print("=" * 60)
    
    # Convert .py to .pyx if needed (Cython prefers .pyx)
    for ext in CYTHON_MODULES:
        for source in ext.sources:
            if source.endswith('.py'):
                pyx_source = source[:-3] + '.pyx'
                if not os.path.exists(pyx_source):
                    print(f"Note: {source} will be compiled as pure Python mode")
    
    setup(
        name='voxmind_cython',
        version='1.0.0',
        description='Cython-optimized VoxMind modules',
        ext_modules=cythonize(
            CYTHON_MODULES,
            compiler_directives=CYTHON_DIRECTIVES,
            annotate=True,  # Generate HTML annotation files
        ),
        zip_safe=False,
    )
    
    print("\n✅ Build complete!")
    print("   Generated .so/.pyd files can be imported directly.")
    print("   Check the .html files for optimization opportunities.")


def show_status():
    """Show current Cython build status."""
    print("VoxMind Cython Status")
    print("=" * 40)
    print(f"  Cython installed: {HAS_CYTHON}")
    print(f"  NumPy installed: {HAS_NUMPY}")
    
    # Check for compiled modules
    compiled = []
    for ext in CYTHON_MODULES:
        name = ext.name
        # Check for .so (Linux) or .pyd (Windows)
        for suffix in ['.so', '.pyd', '.cpython-*.so', '.cpython-*.pyd']:
            import glob
            pattern = name.replace('.', '/') + suffix.replace('*', '*')
            matches = glob.glob(pattern)
            if matches:
                compiled.append((name, matches[0]))
                break
    
    if compiled:
        print("\n  Compiled modules:")
        for name, path in compiled:
            print(f"    ✓ {name}: {path}")
    else:
        print("\n  No compiled modules found.")
        print("  Run 'python setup_cython.py build_ext --inplace' to build.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'status':
        show_status()
    elif HAS_CYTHON:
        build()
    else:
        print("Install Cython to build: pip install cython")
