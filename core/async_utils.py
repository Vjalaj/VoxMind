"""
VoxMind Async Utilities
=======================
Async patterns for I/O-bound operations.

Features:
- Async wrappers for blocking calls
- Connection pooling for API calls
- Concurrent task execution
- Async caching

Usage:
    from core.async_utils import run_async, AsyncCache, async_timeout
    
    # Run blocking code in thread pool
    result = await run_async(blocking_function, arg1, arg2)
    
    # Async cache
    cache = AsyncCache()
    await cache.set("key", "value")
    value = await cache.get("key")
"""

import asyncio
import functools
import time
import logging
import threading
from typing import Any, Callable, Dict, Optional, TypeVar, Awaitable, Tuple
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

T = TypeVar('T')

# Global thread pool for blocking operations
_thread_pool: Optional[ThreadPoolExecutor] = None
_pool_lock = threading.Lock()


def get_thread_pool(max_workers: int = 4) -> ThreadPoolExecutor:
    """Get or create global thread pool."""
    global _thread_pool
    if _thread_pool is None:
        with _pool_lock:
            if _thread_pool is None:
                _thread_pool = ThreadPoolExecutor(
                    max_workers=max_workers,
                    thread_name_prefix="voxmind-async"
                )
    return _thread_pool


# =============================================================================
# Async Wrappers
# =============================================================================

async def run_async(func: Callable[..., T], *args, **kwargs) -> T:
    """
    Run a blocking function in a thread pool.
    
    This is the primary way to call blocking code from async context.
    
    Usage:
        result = await run_async(blocking_io_operation, arg1, arg2)
    """
    loop = asyncio.get_running_loop()
    pool = get_thread_pool()
    
    # Use functools.partial to pass kwargs
    if kwargs:
        func = functools.partial(func, **kwargs)
    
    return await loop.run_in_executor(pool, func, *args)


def make_async(func: Callable[..., T]) -> Callable[..., Awaitable[T]]:
    """
    Decorator to make a blocking function async.
    
    Usage:
        @make_async
        def slow_blocking_call():
            time.sleep(1)
            return "done"
        
        result = await slow_blocking_call()
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await run_async(func, *args, **kwargs)
    return wrapper


async def gather_with_limit(
    *coros,
    limit: int = 10,
    return_exceptions: bool = False
) -> list:
    """
    Like asyncio.gather but with concurrency limit.
    
    Args:
        *coros: Coroutines to run
        limit: Maximum concurrent tasks
        return_exceptions: Whether to return exceptions instead of raising
    
    Returns:
        List of results in order
    """
    semaphore = asyncio.Semaphore(limit)
    
    async def limited(coro):
        async with semaphore:
            return await coro
    
    return await asyncio.gather(
        *[limited(c) for c in coros],
        return_exceptions=return_exceptions
    )


# =============================================================================
# Async Timeout
# =============================================================================

class AsyncTimeoutError(Exception):
    """Raised when async operation times out."""
    pass


async def async_timeout(coro: Awaitable[T], timeout: float) -> T:
    """
    Run a coroutine with timeout.
    
    Args:
        coro: Coroutine to run
        timeout: Timeout in seconds
    
    Returns:
        Result of coroutine
    
    Raises:
        AsyncTimeoutError: If timeout exceeded
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise AsyncTimeoutError(f"Operation timed out after {timeout}s")


# =============================================================================
# Async Cache
# =============================================================================

@dataclass
class AsyncCacheEntry:
    """Cache entry with timestamp."""
    value: Any
    timestamp: float = field(default_factory=time.time)
    ttl: float = 300.0
    
    @property
    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl


class AsyncCache:
    """
    Thread-safe async cache with TTL support.
    
    Usage:
        cache = AsyncCache(default_ttl=60.0)
        
        await cache.set("key", "value")
        value = await cache.get("key")
        
        # With custom TTL
        await cache.set("key", "value", ttl=10.0)
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: float = 300.0
    ):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, AsyncCacheEntry] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if entry.is_expired:
                del self._cache[key]
                return None
            return entry.value
    
    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in cache."""
        async with self._lock:
            # Evict if at capacity
            if len(self._cache) >= self.max_size:
                await self._evict_oldest()
            
            self._cache[key] = AsyncCacheEntry(
                value=value,
                ttl=ttl or self.default_ttl
            )
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def clear(self) -> None:
        """Clear all entries."""
        async with self._lock:
            self._cache.clear()
    
    async def _evict_oldest(self) -> None:
        """Evict oldest entry (must hold lock)."""
        if not self._cache:
            return
        
        # Find oldest
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].timestamp
        )
        del self._cache[oldest_key]
    
    def get_sync(self, key: str) -> Optional[Any]:
        """Synchronous get (for use in sync context)."""
        entry = self._cache.get(key)
        if entry is None or entry.is_expired:
            return None
        return entry.value
    
    def set_sync(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Synchronous set (for use in sync context)."""
        self._cache[key] = AsyncCacheEntry(
            value=value,
            ttl=ttl or self.default_ttl
        )


# =============================================================================
# Async Retry
# =============================================================================

async def async_retry(
    coro_factory: Callable[[], Awaitable[T]],
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple = (Exception,)
) -> T:
    """
    Retry a coroutine with exponential backoff.
    
    Args:
        coro_factory: Factory that creates new coroutine each attempt
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts
        backoff: Backoff multiplier
        exceptions: Tuple of exceptions to catch
    
    Returns:
        Result of successful coroutine
    
    Raises:
        Last exception if all attempts fail
    """
    last_exception = None
    current_delay = delay
    
    for attempt in range(max_attempts):
        try:
            return await coro_factory()
        except exceptions as e:
            last_exception = e
            logger.warning(f"Attempt {attempt + 1}/{max_attempts} failed: {e}")
            
            if attempt < max_attempts - 1:
                await asyncio.sleep(current_delay)
                current_delay *= backoff
    
    raise last_exception


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple = (Exception,)
):
    """
    Decorator for async retry.
    
    Usage:
        @retry(max_attempts=3, delay=1.0)
        async def flaky_api_call():
            ...
    """
    def decorator(func: Callable[..., Awaitable[T]]):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await async_retry(
                lambda: func(*args, **kwargs),
                max_attempts=max_attempts,
                delay=delay,
                backoff=backoff,
                exceptions=exceptions
            )
        return wrapper
    return decorator


# =============================================================================
# Async Event Bus
# =============================================================================

class AsyncEventBus:
    """
    Simple async event bus for decoupled communication.
    
    Usage:
        bus = AsyncEventBus()
        
        async def handler(data):
            print(f"Received: {data}")
        
        bus.subscribe("my_event", handler)
        await bus.emit("my_event", {"message": "hello"})
    """
    
    def __init__(self):
        self._handlers: Dict[str, list] = {}
        self._lock = asyncio.Lock()
    
    def subscribe(
        self,
        event: str,
        handler: Callable[[Any], Awaitable[None]]
    ) -> Callable[[], None]:
        """
        Subscribe to an event.
        
        Returns:
            Unsubscribe function
        """
        if event not in self._handlers:
            self._handlers[event] = []
        
        self._handlers[event].append(handler)
        
        def unsubscribe():
            self._handlers[event].remove(handler)
        
        return unsubscribe
    
    async def emit(self, event: str, data: Any = None) -> None:
        """Emit an event to all handlers."""
        handlers = self._handlers.get(event, [])
        
        if handlers:
            await asyncio.gather(
                *[h(data) for h in handlers],
                return_exceptions=True
            )
    
    def emit_sync(self, event: str, data: Any = None) -> None:
        """
        Emit event from sync context.
        Creates new event loop if needed.
        """
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(self.emit(event, data))
        except RuntimeError:
            # No running loop, run synchronously in new loop
            asyncio.run(self.emit(event, data))


# =============================================================================
# Async Queue for Background Tasks
# =============================================================================

class BackgroundTaskQueue:
    """
    Queue for processing background tasks.
    
    Usage:
        queue = BackgroundTaskQueue()
        await queue.start()
        
        await queue.enqueue(some_async_task, arg1, arg2)
        
        await queue.stop()
    """
    
    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers
        self._queue: asyncio.Queue = asyncio.Queue()
        self._workers: list = []
        self._running = False
    
    async def start(self) -> None:
        """Start worker tasks."""
        if self._running:
            return
        
        self._running = True
        self._workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self.max_workers)
        ]
    
    async def stop(self, wait: bool = True) -> None:
        """Stop worker tasks."""
        self._running = False
        
        # Add sentinel values to wake workers
        for _ in self._workers:
            await self._queue.put(None)
        
        if wait:
            await asyncio.gather(*self._workers, return_exceptions=True)
    
    async def enqueue(
        self,
        coro_factory: Callable[..., Awaitable],
        *args,
        **kwargs
    ) -> None:
        """Add task to queue."""
        await self._queue.put((coro_factory, args, kwargs))
    
    async def _worker(self, worker_id: int) -> None:
        """Worker that processes queue items."""
        while self._running:
            try:
                item = await self._queue.get()
                
                if item is None:  # Sentinel for shutdown
                    break
                
                coro_factory, args, kwargs = item
                
                try:
                    await coro_factory(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Worker {worker_id} task failed: {e}")
                finally:
                    self._queue.task_done()
                    
            except asyncio.CancelledError:
                break


# =============================================================================
# Global Event Bus Instance
# =============================================================================

event_bus = AsyncEventBus()


if __name__ == "__main__":
    import time
    
    async def demo():
        print("Async Utils Demo")
        print("=" * 40)
        
        # Demo run_async
        def blocking_sleep(seconds):
            time.sleep(seconds)
            return f"Slept for {seconds}s"
        
        print("\n1. run_async (blocking -> async):")
        result = await run_async(blocking_sleep, 0.1)
        print(f"   Result: {result}")
        
        # Demo async cache
        print("\n2. AsyncCache:")
        cache = AsyncCache()
        await cache.set("test", "hello", ttl=5.0)
        value = await cache.get("test")
        print(f"   Cached value: {value}")
        
        # Demo gather_with_limit
        print("\n3. gather_with_limit:")
        async def task(i):
            await asyncio.sleep(0.1)
            return i * 2
        
        results = await gather_with_limit(
            *[task(i) for i in range(5)],
            limit=2
        )
        print(f"   Results: {results}")
        
        # Demo event bus
        print("\n4. AsyncEventBus:")
        received = []
        
        async def handler(data):
            received.append(data)
        
        event_bus.subscribe("test", handler)
        await event_bus.emit("test", {"message": "hello"})
        print(f"   Received: {received}")
        
        print("\nAll demos complete!")
    
    asyncio.run(demo())
