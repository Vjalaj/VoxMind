"""Middleware pipeline for backend processing.

Includes:
- Telemetry middleware (request tracking with latency)
- NLE memory middleware (conversation context)
- Rate limiting middleware
- Circuit breaker middleware
- Timeout middleware
- History middleware
"""

from typing import Protocol, Optional
from .request_context import RequestContext
from .rate_limit import RateLimiter, RateLimitError
from .circuit_breaker import CircuitBreakerRegistry, CircuitOpenError
from .timeout import TimeoutWrapper, TimeoutError as CommandTimeoutError
from .history import CommandHistory
import time
import logging

logger = logging.getLogger(__name__)


class Middleware(Protocol):
    def before(self, ctx: RequestContext) -> None:
        ...

    def after(self, ctx: RequestContext) -> None:
        ...


class TelemetryMiddleware:
    """Enhanced telemetry middleware with latency tracking."""
    
    def __init__(self, telemetry):
        self.telemetry = telemetry

    def before(self, ctx: RequestContext) -> None:
        command = ctx.parsed.get("command", "unknown")
        request_id = self.telemetry.start_request(command)
        ctx.metadata['request_id'] = request_id
        ctx.metadata['start_time'] = time.time()

    def after(self, ctx: RequestContext) -> None:
        request_id = ctx.metadata.get('request_id')
        if request_id:
            self.telemetry.end_request(
                request_id,
                success=ctx.error is None,
                error=ctx.error
            )


class NleMemoryMiddleware:
    """NLE conversation memory middleware."""
    
    def __init__(self, nle_engine_provider):
        self._get_engine = nle_engine_provider

    def before(self, ctx: RequestContext) -> None:
        return None

    def after(self, ctx: RequestContext) -> None:
        if ctx.response is None:
            return
        engine = self._get_engine()
        if engine is None:
            return
        try:
            engine.record_exchange(
                user_input=ctx.raw_text,
                response=ctx.response,
                intent=ctx.parsed.get("command"),
                entities=ctx.parsed.get("params", {}),
            )
        except Exception:
            pass


class RateLimitMiddleware:
    """Rate limiting middleware using token bucket."""
    
    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        self.rate_limiter = rate_limiter or RateLimiter()
    
    def before(self, ctx: RequestContext) -> None:
        command = ctx.parsed.get("command", "unknown")
        result = self.rate_limiter.check(command)
        
        ctx.metadata['rate_limit'] = {
            'remaining': result.remaining,
            'reset_in': result.reset_in
        }
        
        if not result.allowed:
            raise RateLimitError(result)
    
    def after(self, ctx: RequestContext) -> None:
        pass


class CircuitBreakerMiddleware:
    """Circuit breaker middleware for fault tolerance."""
    
    def __init__(self, registry: Optional[CircuitBreakerRegistry] = None):
        self.registry = registry or CircuitBreakerRegistry()
    
    def before(self, ctx: RequestContext) -> None:
        command = ctx.parsed.get("command", "unknown")
        circuit = self.registry.get(command)
        
        if not circuit.can_execute():
            raise CircuitOpenError(command, circuit.get_retry_after())
        
        ctx.metadata['circuit'] = command
    
    def after(self, ctx: RequestContext) -> None:
        command = ctx.metadata.get('circuit')
        if not command:
            return
        
        if ctx.error:
            self.registry.record_failure(command, ctx.error)
        else:
            self.registry.record_success(command)


class HistoryMiddleware:
    """Command history tracking middleware."""
    
    def __init__(self, history: Optional[CommandHistory] = None):
        self.history = history or CommandHistory()
    
    def before(self, ctx: RequestContext) -> None:
        pass
    
    def after(self, ctx: RequestContext) -> None:
        request_id = ctx.metadata.get('request_id', 'unknown')
        self.history.record(
            command_id=request_id,
            raw_text=ctx.raw_text,
            parsed=ctx.parsed,
            response=ctx.response,
            success=ctx.error is None
        )


class LoggingMiddleware:
    """Request/response logging middleware."""
    
    def __init__(self, log_level: int = logging.DEBUG):
        self.log_level = log_level
    
    def before(self, ctx: RequestContext) -> None:
        command = ctx.parsed.get("command", "unknown")
        logger.log(
            self.log_level,
            f"[REQ] {ctx.metadata.get('request_id', '???')}: "
            f"command={command}, text='{ctx.raw_text[:50]}...'"
        )
    
    def after(self, ctx: RequestContext) -> None:
        request_id = ctx.metadata.get('request_id', '???')
        latency = ctx.metadata.get('start_time')
        latency_str = ""
        if latency:
            latency_str = f" ({(time.time() - latency)*1000:.1f}ms)"
        
        if ctx.error:
            logger.log(
                self.log_level,
                f"[ERR] {request_id}: {type(ctx.error).__name__}: {ctx.error}{latency_str}"
            )
        else:
            response_preview = (ctx.response or "")[:50]
            logger.log(
                self.log_level,
                f"[RES] {request_id}: '{response_preview}...'{latency_str}"
            )


class ErrorRecoveryMiddleware:
    """Error recovery and graceful degradation."""
    
    def __init__(self, fallback_response: str = "I encountered an error. Please try again."):
        self.fallback_response = fallback_response
        self.recovery_handlers = {}
    
    def register_recovery(self, error_type: type, handler):
        """Register a recovery handler for an error type."""
        self.recovery_handlers[error_type] = handler
    
    def before(self, ctx: RequestContext) -> None:
        pass
    
    def after(self, ctx: RequestContext) -> None:
        if ctx.error is None:
            return
        
        error_type = type(ctx.error)
        
        # Check for specific recovery handler
        handler = self.recovery_handlers.get(error_type)
        if handler:
            try:
                ctx.response = handler(ctx.error, ctx)
                ctx.error = None
                return
            except Exception:
                pass
        
        # Built-in recovery for known errors
        if isinstance(ctx.error, RateLimitError):
            retry_after = ctx.error.result.retry_after
            ctx.response = f"Too many requests. Please wait {retry_after:.1f} seconds."
            ctx.error = None
        
        elif isinstance(ctx.error, CircuitOpenError):
            ctx.response = f"This feature is temporarily unavailable. Try again in {ctx.error.retry_after:.0f} seconds."
            ctx.error = None
        
        elif isinstance(ctx.error, CommandTimeoutError):
            ctx.response = f"The command took too long. Please try again."
            ctx.error = None
        
        else:
            # Generic fallback
            logger.error(f"Unhandled error: {ctx.error}")
            ctx.response = self.fallback_response
