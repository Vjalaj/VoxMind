"""Circuit breaker pattern for fault tolerance.

Prevents cascading failures by temporarily stopping requests
to failing services/commands.
"""

from typing import Callable, TypeVar, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import threading
import time
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation, requests pass through
    OPEN = "open"           # Failure threshold exceeded, requests blocked
    HALF_OPEN = "half_open" # Testing if service recovered


@dataclass
class CircuitStats:
    """Statistics for a circuit."""
    failures: int = 0
    successes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    total_requests: int = 0
    
    def record_success(self):
        self.successes += 1
        self.consecutive_successes += 1
        self.consecutive_failures = 0
        self.last_success_time = time.time()
        self.total_requests += 1
    
    def record_failure(self):
        self.failures += 1
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        self.last_failure_time = time.time()
        self.total_requests += 1
    
    def failure_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.failures / self.total_requests


class CircuitOpenError(Exception):
    """Raised when circuit is open and request is blocked."""
    
    def __init__(self, command: str, retry_after: float):
        self.command = command
        self.retry_after = retry_after
        super().__init__(
            f"Circuit open for '{command}'. Retry after {retry_after:.1f}s"
        )


class CircuitBreaker:
    """
    Circuit breaker for a single command/service.
    
    States:
    - CLOSED: Normal operation. Track failures.
    - OPEN: Too many failures. Block all requests.
    - HALF_OPEN: After timeout, allow one test request.
    
    Transitions:
    - CLOSED -> OPEN: When consecutive_failures >= threshold
    - OPEN -> HALF_OPEN: After recovery_timeout
    - HALF_OPEN -> CLOSED: If test request succeeds
    - HALF_OPEN -> OPEN: If test request fails
    """
    
    def __init__(self,
                 failure_threshold: int = 5,
                 recovery_timeout: float = 30.0,
                 success_threshold: int = 2):
        """
        Args:
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before trying recovery
            success_threshold: Successes in half-open before closing
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        self.state = CircuitState.CLOSED
        self.stats = CircuitStats()
        self.opened_at: Optional[float] = None
        self._lock = threading.Lock()
    
    def can_execute(self) -> bool:
        """Check if request is allowed."""
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            
            if self.state == CircuitState.OPEN:
                # Check if recovery timeout passed
                if self.opened_at and time.time() - self.opened_at >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    logger.info("Circuit entering half-open state")
                    return True
                return False
            
            if self.state == CircuitState.HALF_OPEN:
                # Allow limited requests for testing
                return True
            
            return False
    
    def record_success(self):
        """Record successful execution."""
        with self._lock:
            self.stats.record_success()
            
            if self.state == CircuitState.HALF_OPEN:
                if self.stats.consecutive_successes >= self.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.opened_at = None
                    logger.info("Circuit closed after recovery")
    
    def record_failure(self, error: Optional[Exception] = None):
        """Record failed execution."""
        with self._lock:
            self.stats.record_failure()
            
            if self.state == CircuitState.HALF_OPEN:
                # Any failure in half-open reopens
                self.state = CircuitState.OPEN
                self.opened_at = time.time()
                logger.warning("Circuit reopened after failed recovery test")
            
            elif self.state == CircuitState.CLOSED:
                if self.stats.consecutive_failures >= self.failure_threshold:
                    self.state = CircuitState.OPEN
                    self.opened_at = time.time()
                    logger.warning(
                        f"Circuit opened after {self.failure_threshold} failures"
                    )
    
    def get_retry_after(self) -> float:
        """Get seconds until retry is allowed."""
        if self.state != CircuitState.OPEN or not self.opened_at:
            return 0.0
        elapsed = time.time() - self.opened_at
        return max(0.0, self.recovery_timeout - elapsed)
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit status."""
        with self._lock:
            return {
                'state': self.state.value,
                'failures': self.stats.failures,
                'successes': self.stats.successes,
                'consecutive_failures': self.stats.consecutive_failures,
                'failure_rate': self.stats.failure_rate(),
                'retry_after': self.get_retry_after() if self.state == CircuitState.OPEN else None,
            }
    
    def reset(self):
        """Reset circuit to closed state."""
        with self._lock:
            self.state = CircuitState.CLOSED
            self.stats = CircuitStats()
            self.opened_at = None


class CircuitBreakerRegistry:
    """
    Registry of circuit breakers for different commands.
    """
    
    def __init__(self,
                 failure_threshold: int = 5,
                 recovery_timeout: float = 30.0,
                 success_threshold: int = 2):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        self._circuits: Dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()
    
    def get(self, command: str) -> CircuitBreaker:
        """Get or create circuit breaker for command."""
        with self._lock:
            if command not in self._circuits:
                self._circuits[command] = CircuitBreaker(
                    self.failure_threshold,
                    self.recovery_timeout,
                    self.success_threshold
                )
            return self._circuits[command]
    
    def check(self, command: str) -> bool:
        """Check if command can execute."""
        return self.get(command).can_execute()
    
    def record_success(self, command: str):
        """Record successful execution."""
        self.get(command).record_success()
    
    def record_failure(self, command: str, error: Optional[Exception] = None):
        """Record failed execution."""
        self.get(command).record_failure(error)
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all circuits."""
        with self._lock:
            return {
                cmd: circuit.get_status()
                for cmd, circuit in self._circuits.items()
            }
    
    def get_open_circuits(self) -> list:
        """Get list of open circuits."""
        with self._lock:
            return [
                cmd for cmd, circuit in self._circuits.items()
                if circuit.state == CircuitState.OPEN
            ]


def with_circuit_breaker(registry: CircuitBreakerRegistry, command: str):
    """
    Decorator to wrap function with circuit breaker.
    
    Usage:
        @with_circuit_breaker(registry, "my_command")
        def my_function():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            circuit = registry.get(command)
            
            if not circuit.can_execute():
                raise CircuitOpenError(command, circuit.get_retry_after())
            
            try:
                result = func(*args, **kwargs)
                circuit.record_success()
                return result
            except Exception as e:
                circuit.record_failure(e)
                raise
        
        return wrapper
    return decorator
