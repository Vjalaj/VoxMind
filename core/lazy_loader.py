"""
VoxMind Lazy Loading Utilities
==============================
Deferred imports and lazy initialization for improved startup time.

Features:
- LazyLoader class for deferred module imports
- LazyModel for ML model lazy loading
- Singleton patterns with lazy initialization
- Background preloading

Usage:
    from core.lazy_loader import LazyLoader, LazyModel, lazy_property
    
    # Lazy module import
    easyocr = LazyLoader('easyocr')
    
    # Lazy model loading
    model = LazyModel(load_function, preload=True)
    
    # Lazy property
    class MyClass:
        @lazy_property
        def heavy_resource(self):
            return load_heavy_resource()
"""

import threading
import functools
import logging
import importlib
import time
from typing import Any, Callable, Optional, TypeVar, Generic

logger = logging.getLogger(__name__)

T = TypeVar('T')


class LazyLoader:
    """
    Lazy module loader that defers import until first use.
    
    Usage:
        # Instead of: import easyocr
        easyocr = LazyLoader('easyocr')
        
        # Module is only imported when accessed:
        reader = easyocr.Reader(['en'])
    """
    
    def __init__(self, module_name: str, package: Optional[str] = None):
        self._module_name = module_name
        self._package = package
        self._module = None
        self._lock = threading.Lock()
        self._import_error: Optional[ImportError] = None
    
    def _load(self):
        if self._module is None and self._import_error is None:
            with self._lock:
                if self._module is None and self._import_error is None:
                    try:
                        start = time.perf_counter()
                        self._module = importlib.import_module(
                            self._module_name, 
                            self._package
                        )
                        elapsed = time.perf_counter() - start
                        logger.info(f"Lazy-loaded {self._module_name} in {elapsed:.3f}s")
                    except ImportError as e:
                        self._import_error = e
                        logger.warning(f"Failed to import {self._module_name}: {e}")
    
    def __getattr__(self, name: str) -> Any:
        self._load()
        if self._import_error:
            raise self._import_error
        return getattr(self._module, name)
    
    @property
    def is_available(self) -> bool:
        """Check if module can be imported without actually importing."""
        try:
            spec = importlib.util.find_spec(self._module_name, self._package)
            return spec is not None
        except (ModuleNotFoundError, ValueError):
            return False
    
    @property
    def is_loaded(self) -> bool:
        """Check if module has been loaded."""
        return self._module is not None


class LazyModel(Generic[T]):
    """
    Lazy model loader with optional background preloading.
    
    Usage:
        def load_model():
            from sentence_transformers import SentenceTransformer
            return SentenceTransformer('all-MiniLM-L6-v2')
        
        model = LazyModel(load_model, preload=True)
        
        # Model loads in background, blocks only if not ready
        embeddings = model.get().encode(['hello'])
    """
    
    def __init__(
        self, 
        loader: Callable[[], T],
        preload: bool = False,
        name: str = "model"
    ):
        self._loader = loader
        self._name = name
        self._instance: Optional[T] = None
        self._lock = threading.Lock()
        self._loading = False
        self._error: Optional[Exception] = None
        self._load_time: Optional[float] = None
        
        if preload:
            self.preload()
    
    def preload(self) -> 'LazyModel[T]':
        """Start loading the model in a background thread."""
        if self._instance is not None or self._loading:
            return self
        
        def background_load():
            self._load()
        
        thread = threading.Thread(target=background_load, daemon=True)
        thread.start()
        return self
    
    def _load(self):
        """Internal load (thread-safe)."""
        if self._instance is not None:
            return
        
        with self._lock:
            if self._instance is not None:
                return
            
            self._loading = True
            try:
                start = time.perf_counter()
                logger.info(f"Loading {self._name}...")
                self._instance = self._loader()
                self._load_time = time.perf_counter() - start
                logger.info(f"Loaded {self._name} in {self._load_time:.3f}s")
            except Exception as e:
                self._error = e
                logger.error(f"Failed to load {self._name}: {e}")
            finally:
                self._loading = False
    
    def get(self, timeout: Optional[float] = None) -> T:
        """
        Get the model, loading if necessary.
        
        Args:
            timeout: Max seconds to wait for loading (None = forever)
        
        Returns:
            The loaded model
            
        Raises:
            TimeoutError: If timeout exceeded
            Exception: If loading failed
        """
        if self._instance is not None:
            return self._instance
        
        if self._error:
            raise self._error
        
        # Wait for background loading to complete
        start = time.time()
        while self._loading:
            if timeout and (time.time() - start) > timeout:
                raise TimeoutError(f"{self._name} loading timed out")
            time.sleep(0.01)
        
        # Load synchronously if not already loaded
        if self._instance is None:
            self._load()
        
        if self._error:
            raise self._error
        
        return self._instance
    
    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._instance is not None
    
    @property
    def is_loading(self) -> bool:
        """Check if model is currently loading."""
        return self._loading
    
    @property
    def load_time(self) -> Optional[float]:
        """Get model load time in seconds."""
        return self._load_time


def lazy_property(func: Callable[[Any], T]) -> property:
    """
    Decorator for lazy-evaluated properties.
    
    The property is computed once on first access, then cached.
    
    Usage:
        class MyClass:
            @lazy_property
            def heavy_computation(self):
                return expensive_operation()
    """
    attr_name = f'_lazy_{func.__name__}'
    
    @functools.wraps(func)
    def wrapper(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, func(self))
        return getattr(self, attr_name)
    
    return property(wrapper)


class SingletonMeta(type):
    """
    Thread-safe singleton metaclass with lazy initialization.
    
    Usage:
        class MySingleton(metaclass=SingletonMeta):
            def __init__(self):
                # This only runs once
                self.data = load_data()
    """
    _instances = {}
    _lock = threading.Lock()
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
        return cls._instances[cls]


class DeferredInitMixin:
    """
    Mixin for classes with expensive initialization.
    
    Usage:
        class MyClass(DeferredInitMixin):
            def _deferred_init(self):
                self.model = load_heavy_model()
            
            def use_model(self):
                self._ensure_initialized()
                return self.model.predict(...)
    """
    _initialized = False
    _init_lock = None
    
    def __init__(self):
        self._init_lock = threading.Lock()
    
    def _ensure_initialized(self):
        """Ensure deferred initialization has run."""
        if not self._initialized:
            with self._init_lock:
                if not self._initialized:
                    self._deferred_init()
                    self._initialized = True
    
    def _deferred_init(self):
        """Override this with expensive initialization."""
        pass
    
    def preload(self):
        """Trigger deferred initialization in background."""
        thread = threading.Thread(target=self._ensure_initialized, daemon=True)
        thread.start()


# =============================================================================
# Pre-configured Lazy Loaders for Common Heavy Modules
# =============================================================================

# ML/AI Libraries
sentence_transformers = LazyLoader('sentence_transformers')
torch = LazyLoader('torch')
tensorflow = LazyLoader('tensorflow')
numpy = LazyLoader('numpy')

# OCR Libraries
easyocr = LazyLoader('easyocr')
pytesseract = LazyLoader('pytesseract')

# Image Processing
cv2 = LazyLoader('cv2')
PIL = LazyLoader('PIL')

# Audio Processing
speech_recognition = LazyLoader('speech_recognition')
pyaudio = LazyLoader('pyaudio')


# =============================================================================
# Utility Functions
# =============================================================================

def check_module_available(module_name: str) -> bool:
    """Check if a module is available without importing it."""
    try:
        spec = importlib.util.find_spec(module_name)
        return spec is not None
    except (ModuleNotFoundError, ValueError):
        return False


def lazy_import(module_name: str, attribute: Optional[str] = None) -> Any:
    """
    Import a module or attribute lazily.
    
    Args:
        module_name: Name of module to import
        attribute: Optional attribute to get from module
    
    Returns:
        Module or attribute
    """
    loader = LazyLoader(module_name)
    if attribute:
        return getattr(loader, attribute)
    return loader


def preload_modules(*module_names: str) -> None:
    """
    Preload modules in background threads.
    
    Args:
        *module_names: Names of modules to preload
    """
    def load(name):
        try:
            importlib.import_module(name)
            logger.info(f"Preloaded {name}")
        except ImportError as e:
            logger.debug(f"Could not preload {name}: {e}")
    
    for name in module_names:
        thread = threading.Thread(target=load, args=(name,), daemon=True)
        thread.start()


if __name__ == "__main__":
    # Demo
    print("Lazy Loading Demo")
    print("=" * 40)
    
    # Check availability without importing
    print(f"numpy available: {numpy.is_available}")
    print(f"easyocr available: {easyocr.is_available}")
    print(f"torch available: {torch.is_available}")
    
    # Lazy property demo
    class Demo:
        @lazy_property
        def expensive(self):
            print("Computing expensive property...")
            time.sleep(0.1)
            return 42
    
    demo = Demo()
    print(f"\nFirst access: {demo.expensive}")  # Computes
    print(f"Second access: {demo.expensive}")   # Cached
