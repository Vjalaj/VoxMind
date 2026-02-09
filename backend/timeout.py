"""Request timeout handling for backend commands.

Provides timeout wrappers to prevent hung commands from blocking forever.
"""

from typing import Callable, TypeVar, Any, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from functools import wraps
import threading
import time

T = TypeVar('T')


class TimeoutError(Exception):
    """Raised when a command exceeds its timeout."""
    def __init__(self, timeout: float, command: str = "unknown"):
        self.timeout = timeout
        self.command = command
        super().__init__(f"Command '{command}' timed out after {timeout:.1f}s")


class TimeoutWrapper:
    """
    Wraps function calls with a timeout.
    
    Usage:
        wrapper = TimeoutWrapper(timeout=5.0)
        result = wrapper.execute(slow_function, arg1, arg2)
    """
    
    def __init__(self, timeout: float = 10.0, max_workers: int = 4):
        """
        Args:
            timeout: Default timeout in seconds
            max_workers: Max concurrent timeout-wrapped calls
        """
        self.default_timeout = timeout
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def execute(self, func: Callable[..., T], *args,
                timeout: Optional[float] = None,
                command_name: str = "unknown",
                **kwargs) -> T:
        """
        Execute a function with timeout.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            timeout: Override default timeout
            command_name: Name for error messages
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            TimeoutError: If execution exceeds timeout
        """
        timeout = timeout or self.default_timeout
        
        future = self._executor.submit(func, *args, **kwargs)
        
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError:
            future.cancel()
            raise TimeoutError(timeout, command_name)
    
    def shutdown(self):
        """Shutdown the executor."""
        self._executor.shutdown(wait=False)


def with_timeout(timeout: float = 10.0, command_name: str = "unknown"):
    """
    Decorator to add timeout to a function.
    
    Usage:
        @with_timeout(5.0)
        def slow_function():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        executor = ThreadPoolExecutor(max_workers=1)
        
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            future = executor.submit(func, *args, **kwargs)
            try:
                return future.result(timeout=timeout)
            except FuturesTimeoutError:
                future.cancel()
                raise TimeoutError(timeout, command_name or func.__name__)
        
        return wrapper
    return decorator


class AdaptiveTimeout:
    """
    Adaptive timeout that adjusts based on command history.
    
    Slower commands get more time, faster commands get less.
    """
    
    def __init__(self, 
                 default_timeout: float = 10.0,
                 min_timeout: float = 1.0,
                 max_timeout: float = 60.0,
                 multiplier: float = 2.0):
        """
        Args:
            default_timeout: Starting timeout
            min_timeout: Minimum allowed timeout
            max_timeout: Maximum allowed timeout
            multiplier: Multiply p95 latency by this for timeout
        """
        self.default_timeout = default_timeout
        self.min_timeout = min_timeout
        self.max_timeout = max_timeout
        self.multiplier = multiplier
        
        self._command_times: dict = {}
        self._lock = threading.Lock()
    
    def record(self, command: str, duration: float):
        """Record a command's execution time."""
        with self._lock:
            if command not in self._command_times:
                self._command_times[command] = []
            times = self._command_times[command]
            times.append(duration)
            # Keep last 100 samples
            if len(times) > 100:
                self._command_times[command] = times[-100:]
    
    def get_timeout(self, command: str) -> float:
        """Get adaptive timeout for a command."""
        with self._lock:
            times = self._command_times.get(command)
            
            if not times or len(times) < 3:
                return self.default_timeout
            
            # Use p95 * multiplier as timeout
            sorted_times = sorted(times)
            p95_idx = int(len(sorted_times) * 0.95)
            p95 = sorted_times[p95_idx]
            
            timeout = p95 * self.multiplier
            return max(self.min_timeout, min(self.max_timeout, timeout))
