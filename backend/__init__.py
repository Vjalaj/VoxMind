"""VoxMind backend architecture package.

Enhanced backend with:
- Telemetry (latency, request IDs, percentiles)
- Timeout protection
- Rate limiting
- Circuit breaker
- Command queue with priorities
- Health checks
- Command history with undo
"""

from .app import BackendApp
from .router import CommandRouter
from .telemetry import Telemetry, RequestMetrics, LatencyTracker
from .request_context import RequestContext
from .timeout import TimeoutWrapper, TimeoutError, AdaptiveTimeout
from .rate_limit import RateLimiter, RateLimitError, TokenBucket
from .circuit_breaker import (
    CircuitBreaker, CircuitBreakerRegistry, CircuitOpenError, CircuitState
)
from .command_queue import CommandQueue, Priority, QueuedCommand, infer_priority
from .health import HealthCheck, HealthStatus, HealthCheckResult, HealthReport
from .history import CommandHistory, HistoryEntry
from .middleware import (
    Middleware, TelemetryMiddleware, NleMemoryMiddleware,
    RateLimitMiddleware, CircuitBreakerMiddleware,
    HistoryMiddleware, LoggingMiddleware, ErrorRecoveryMiddleware
)

__all__ = [
    # Core
    "BackendApp",
    "CommandRouter", 
    "RequestContext",
    
    # Telemetry
    "Telemetry",
    "RequestMetrics",
    "LatencyTracker",
    
    # Timeout
    "TimeoutWrapper",
    "TimeoutError",
    "AdaptiveTimeout",
    
    # Rate limiting
    "RateLimiter",
    "RateLimitError",
    "TokenBucket",
    
    # Circuit breaker
    "CircuitBreaker",
    "CircuitBreakerRegistry",
    "CircuitOpenError",
    "CircuitState",
    
    # Command queue
    "CommandQueue",
    "Priority",
    "QueuedCommand",
    "infer_priority",
    
    # Health
    "HealthCheck",
    "HealthStatus",
    "HealthCheckResult",
    "HealthReport",
    
    # History
    "CommandHistory",
    "HistoryEntry",
    
    # Middleware
    "Middleware",
    "TelemetryMiddleware",
    "NleMemoryMiddleware",
    "RateLimitMiddleware",
    "CircuitBreakerMiddleware",
    "HistoryMiddleware",
    "LoggingMiddleware",
    "ErrorRecoveryMiddleware",
]
