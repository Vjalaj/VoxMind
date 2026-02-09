"""Backend application orchestration.

Enhanced backend with:
- Request timeout protection
- Rate limiting
- Circuit breaker fault tolerance
- Command queue with priorities
- Health monitoring
- Command history with undo
- Comprehensive telemetry
"""

from typing import Callable, Dict, Any, Optional
from .router import CommandRouter
from .telemetry import Telemetry
from .middleware import (
    TelemetryMiddleware, NleMemoryMiddleware,
    RateLimitMiddleware, CircuitBreakerMiddleware,
    HistoryMiddleware, LoggingMiddleware, ErrorRecoveryMiddleware
)
from .rate_limit import RateLimiter
from .circuit_breaker import CircuitBreakerRegistry
from .health import HealthCheck, create_telemetry_check, create_circuit_check
from .history import CommandHistory
from .timeout import TimeoutWrapper, AdaptiveTimeout
from .command_queue import CommandQueue, Priority, infer_priority
import logging

logger = logging.getLogger(__name__)


class BackendApp:
    """
    Enhanced backend application with full production features.
    
    Features:
    - Timeout protection for hung commands
    - Rate limiting to prevent abuse
    - Circuit breaker for fault tolerance
    - Priority command queue
    - Health monitoring
    - Command history with undo support
    - Comprehensive telemetry with latency tracking
    """
    
    def __init__(
        self,
        parser: Callable[[str], Dict[str, Any]],
        executor: Callable[[Dict[str, Any]], str],
        nle_engine_provider: Optional[Callable[[], Any]] = None,
        # Configuration
        enable_rate_limiting: bool = True,
        enable_circuit_breaker: bool = True,
        enable_timeout: bool = True,
        enable_queue: bool = False,  # Disabled by default for sync operation
        enable_history: bool = True,
        default_timeout: float = 30.0,
        rate_limit_capacity: int = 120,
        rate_limit_rate: float = 2.0,
    ):
        self.parser = parser
        self._raw_executor = executor
        
        # Core components
        self.telemetry = Telemetry()
        self.rate_limiter = RateLimiter(
            global_capacity=rate_limit_capacity,
            global_rate=rate_limit_rate
        ) if enable_rate_limiting else None
        self.circuit_breaker = CircuitBreakerRegistry() if enable_circuit_breaker else None
        self.timeout_wrapper = TimeoutWrapper(timeout=default_timeout) if enable_timeout else None
        self.adaptive_timeout = AdaptiveTimeout(default_timeout=default_timeout)
        self.history = CommandHistory() if enable_history else None
        self.health = HealthCheck()
        
        # Wrap executor with timeout if enabled
        if enable_timeout:
            self.executor = self._timeout_executor
        else:
            self.executor = executor
        
        # Command queue (optional)
        self.queue = CommandQueue(
            executor=self.executor,
            max_workers=4
        ) if enable_queue else None
        
        # Router with middleware
        self.router = CommandRouter()
        self.router.set_fallback(self.executor)
        
        # Add middleware in order
        self.router.use(TelemetryMiddleware(self.telemetry))
        
        if enable_rate_limiting and self.rate_limiter:
            self.router.use(RateLimitMiddleware(self.rate_limiter))
        
        if enable_circuit_breaker and self.circuit_breaker:
            self.router.use(CircuitBreakerMiddleware(self.circuit_breaker))
        
        if nle_engine_provider is not None:
            self.router.use(NleMemoryMiddleware(nle_engine_provider))
        
        if enable_history and self.history:
            self.router.use(HistoryMiddleware(self.history))
        
        # Error recovery should be last
        self.router.use(ErrorRecoveryMiddleware())
        
        # Register health checks
        self.health.register("telemetry", create_telemetry_check(self.telemetry))
        if self.circuit_breaker:
            self.health.register("circuits", create_circuit_check(self.circuit_breaker))
    
    def _timeout_executor(self, parsed: Dict[str, Any]) -> str:
        """Execute with timeout protection."""
        command = parsed.get('command', 'unknown')
        timeout = self.adaptive_timeout.get_timeout(command)
        
        import time
        start = time.time()
        
        result = self.timeout_wrapper.execute(
            self._raw_executor,
            parsed,
            timeout=timeout,
            command_name=command
        )
        
        # Record timing for adaptive timeout
        duration = time.time() - start
        self.adaptive_timeout.record(command, duration)
        
        return result
    
    def handle(self, raw_text: str):
        """
        Handle a command synchronously.
        
        Returns:
            tuple: (parsed, response, error)
        """
        parsed = self.parser(raw_text)
        ctx = self.router.dispatch(raw_text, parsed)
        return parsed, ctx.response, ctx.error
    
    def handle_async(self, raw_text: str,
                     callback: Optional[Callable] = None) -> Optional[str]:
        """
        Handle a command asynchronously via queue.
        
        Args:
            raw_text: Raw command text
            callback: Optional callback(response, error)
            
        Returns:
            Command ID or None if queue not enabled
        """
        if not self.queue:
            logger.warning("Queue not enabled, falling back to sync")
            parsed, response, error = self.handle(raw_text)
            if callback:
                callback(response, error)
            return None
        
        parsed = self.parser(raw_text)
        priority = infer_priority(parsed)
        return self.queue.enqueue(raw_text, parsed, priority, callback)
    
    def undo(self) -> Optional[str]:
        """Execute undo for last undoable command."""
        if not self.history or not self.history.can_undo():
            return "Nothing to undo."
        
        undo_command = self.history.get_undo_command()
        if undo_command:
            try:
                return self.executor(undo_command)
            except Exception as e:
                return f"Undo failed: {e}"
        return "Cannot undo that command."
    
    def redo(self) -> Optional[str]:
        """Execute redo for last undone command."""
        if not self.history or not self.history.can_redo():
            return "Nothing to redo."
        
        redo_command = self.history.get_redo_command()
        if redo_command:
            try:
                return self.executor(redo_command)
            except Exception as e:
                return f"Redo failed: {e}"
        return "Cannot redo that command."
    
    def get_health(self) -> Dict[str, Any]:
        """Get health status."""
        return self.health.run_all().to_dict()
    
    def is_healthy(self) -> bool:
        """Quick health check."""
        return self.health.is_healthy()
    
    def telemetry_snapshot(self) -> Dict[str, Any]:
        """Get comprehensive telemetry snapshot."""
        snapshot = self.telemetry.snapshot()
        
        # Add component status
        if self.rate_limiter:
            snapshot['rate_limiter'] = self.rate_limiter.get_status()
        if self.circuit_breaker:
            snapshot['circuits'] = self.circuit_breaker.get_status()
        if self.queue:
            snapshot['queue'] = self.queue.get_stats()
        if self.history:
            snapshot['history'] = self.history.get_stats()
        
        return snapshot
    
    def get_recent_history(self, n: int = 10):
        """Get recent command history."""
        if not self.history:
            return []
        return [e.to_dict() for e in self.history.get_last(n)]
    
    def shutdown(self):
        """Graceful shutdown."""
        if self.queue:
            self.queue.shutdown(wait=True)
        if self.timeout_wrapper:
            self.timeout_wrapper.shutdown()
