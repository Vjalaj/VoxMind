"""Rate limiting for backend request handling.

Implements token bucket algorithm for request rate limiting.
"""

from typing import Dict, Optional
from dataclasses import dataclass
import threading
import time


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    reset_in: float  # Seconds until next token
    retry_after: Optional[float] = None  # Seconds to wait if denied


class TokenBucket:
    """
    Token bucket rate limiter.
    
    Tokens refill at a constant rate. Each request consumes one token.
    If no tokens available, request is denied.
    """
    
    def __init__(self, capacity: int = 60, refill_rate: float = 1.0):
        """
        Args:
            capacity: Maximum tokens (burst size)
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()
        self._lock = threading.Lock()
    
    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
    
    def acquire(self, tokens: int = 1) -> RateLimitResult:
        """
        Try to acquire tokens.
        
        Returns:
            RateLimitResult with allowed status and metadata
        """
        with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                time_to_next = 1.0 / self.refill_rate if self.refill_rate > 0 else 0
                return RateLimitResult(
                    allowed=True,
                    remaining=int(self.tokens),
                    reset_in=time_to_next
                )
            else:
                # Calculate wait time
                needed = tokens - self.tokens
                wait_time = needed / self.refill_rate if self.refill_rate > 0 else float('inf')
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_in=wait_time,
                    retry_after=wait_time
                )
    
    def peek(self) -> int:
        """Get current token count without consuming."""
        with self._lock:
            self._refill()
            return int(self.tokens)


class RateLimiter:
    """
    Rate limiter with per-command and global limits.
    """
    
    def __init__(self,
                 global_capacity: int = 120,
                 global_rate: float = 2.0,
                 command_capacity: int = 30,
                 command_rate: float = 0.5):
        """
        Args:
            global_capacity: Global burst limit
            global_rate: Global requests per second
            command_capacity: Per-command burst limit
            command_rate: Per-command requests per second
        """
        self._global_bucket = TokenBucket(global_capacity, global_rate)
        self._command_buckets: Dict[str, TokenBucket] = {}
        self._command_capacity = command_capacity
        self._command_rate = command_rate
        self._lock = threading.Lock()
    
    def _get_command_bucket(self, command: str) -> TokenBucket:
        """Get or create bucket for a command."""
        with self._lock:
            if command not in self._command_buckets:
                self._command_buckets[command] = TokenBucket(
                    self._command_capacity,
                    self._command_rate
                )
            return self._command_buckets[command]
    
    def check(self, command: str) -> RateLimitResult:
        """
        Check if request is allowed.
        
        Args:
            command: Command type being executed
            
        Returns:
            RateLimitResult
        """
        # Check global limit first
        global_result = self._global_bucket.acquire()
        if not global_result.allowed:
            return global_result
        
        # Check per-command limit
        command_bucket = self._get_command_bucket(command)
        command_result = command_bucket.acquire()
        
        if not command_result.allowed:
            # Refund the global token since command limit was hit
            self._global_bucket.tokens = min(
                self._global_bucket.capacity,
                self._global_bucket.tokens + 1
            )
            return command_result
        
        # Both passed
        return RateLimitResult(
            allowed=True,
            remaining=min(global_result.remaining, command_result.remaining),
            reset_in=max(global_result.reset_in, command_result.reset_in)
        )
    
    def get_status(self) -> Dict:
        """Get current rate limiter status."""
        with self._lock:
            return {
                'global_remaining': self._global_bucket.peek(),
                'global_capacity': self._global_bucket.capacity,
                'commands': {
                    cmd: bucket.peek()
                    for cmd, bucket in self._command_buckets.items()
                }
            }


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, result: RateLimitResult):
        self.result = result
        super().__init__(
            f"Rate limit exceeded. Retry after {result.retry_after:.1f}s"
        )
