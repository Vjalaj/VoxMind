"""Enhanced telemetry for backend command processing.

Features:
- Request ID generation
- Latency tracking with percentiles
- Success/failure rates
- Error categorization
- Memory usage tracking
- Time-windowed metrics
"""

from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading
import time
import uuid
import statistics

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


@dataclass
class RequestMetrics:
    """Metrics for a single request."""
    request_id: str
    command: str
    start_time: float
    end_time: Optional[float] = None
    success: bool = True
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    
    @property
    def latency_ms(self) -> Optional[float]:
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000


class LatencyTracker:
    """Tracks latency with percentile calculations."""
    
    def __init__(self, window_size: int = 1000):
        self._latencies: deque = deque(maxlen=window_size)
        self._lock = threading.Lock()
    
    def record(self, latency_ms: float):
        with self._lock:
            self._latencies.append(latency_ms)
    
    def get_percentile(self, p: float) -> Optional[float]:
        """Get percentile (p50, p95, p99, etc.)."""
        with self._lock:
            if not self._latencies:
                return None
            sorted_latencies = sorted(self._latencies)
            idx = int(len(sorted_latencies) * p / 100)
            return sorted_latencies[min(idx, len(sorted_latencies) - 1)]
    
    def get_stats(self) -> Dict[str, Optional[float]]:
        with self._lock:
            if not self._latencies:
                return {
                    'min': None, 'max': None, 'mean': None,
                    'p50': None, 'p95': None, 'p99': None
                }
            latencies = list(self._latencies)
        
        sorted_lat = sorted(latencies)
        n = len(sorted_lat)
        
        return {
            'min': min(latencies),
            'max': max(latencies),
            'mean': statistics.mean(latencies),
            'p50': sorted_lat[int(n * 0.50)],
            'p95': sorted_lat[int(n * 0.95)] if n > 1 else sorted_lat[0],
            'p99': sorted_lat[int(n * 0.99)] if n > 1 else sorted_lat[0],
        }


class TimeWindowCounter:
    """Counts events within a rolling time window."""
    
    def __init__(self, window_seconds: int = 60):
        self._window = window_seconds
        self._events: deque = deque()
        self._lock = threading.Lock()
    
    def increment(self):
        with self._lock:
            now = time.time()
            self._events.append(now)
            self._cleanup(now)
    
    def count(self) -> int:
        with self._lock:
            now = time.time()
            self._cleanup(now)
            return len(self._events)
    
    def _cleanup(self, now: float):
        cutoff = now - self._window
        while self._events and self._events[0] < cutoff:
            self._events.popleft()


class Telemetry:
    """
    Enhanced telemetry system with:
    - Request ID generation
    - Latency tracking with percentiles
    - Success/failure rates
    - Error categorization
    - Memory usage tracking
    - Time-windowed metrics (requests per minute)
    """
    
    def __init__(self, history_size: int = 1000):
        self._lock = threading.Lock()
        
        # Basic counters
        self.total_requests = 0
        self.total_errors = 0
        self.command_counts: Dict[str, int] = defaultdict(int)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.error_types: Dict[str, int] = defaultdict(int)
        
        # Request history
        self._request_history: deque = deque(maxlen=history_size)
        self._active_requests: Dict[str, RequestMetrics] = {}
        
        # Latency tracking
        self._global_latency = LatencyTracker(window_size=history_size)
        self._command_latencies: Dict[str, LatencyTracker] = defaultdict(
            lambda: LatencyTracker(window_size=100)
        )
        
        # Time-windowed counters
        self._requests_per_minute = TimeWindowCounter(window_seconds=60)
        self._errors_per_minute = TimeWindowCounter(window_seconds=60)
        
        # Start time for uptime
        self._start_time = time.time()
    
    def generate_request_id(self) -> str:
        """Generate a unique request ID."""
        return str(uuid.uuid4())[:8]
    
    def start_request(self, command: str) -> str:
        """Start tracking a request. Returns request ID."""
        request_id = self.generate_request_id()
        
        with self._lock:
            self.total_requests += 1
            self.command_counts[command] += 1
            self._requests_per_minute.increment()
            
            metrics = RequestMetrics(
                request_id=request_id,
                command=command,
                start_time=time.time()
            )
            self._active_requests[request_id] = metrics
        
        return request_id
    
    def end_request(self, request_id: str, success: bool = True,
                    error: Optional[Exception] = None):
        """End tracking a request."""
        with self._lock:
            if request_id not in self._active_requests:
                return
            
            metrics = self._active_requests.pop(request_id)
            metrics.end_time = time.time()
            metrics.success = success
            
            if error:
                metrics.error_type = type(error).__name__
                metrics.error_message = str(error)[:200]
                self.total_errors += 1
                self.error_counts[metrics.command] += 1
                self.error_types[metrics.error_type] += 1
                self._errors_per_minute.increment()
            
            # Record latency
            if metrics.latency_ms is not None:
                self._global_latency.record(metrics.latency_ms)
                self._command_latencies[metrics.command].record(metrics.latency_ms)
            
            self._request_history.append(metrics)
    
    def record_command(self, command: str):
        """Legacy method for simple command recording."""
        with self._lock:
            self.total_requests += 1
            self.command_counts[command] += 1
            self._requests_per_minute.increment()
    
    def record_error(self, command: str, error: Optional[Exception] = None):
        """Record an error."""
        with self._lock:
            self.total_errors += 1
            self.error_counts[command] += 1
            self._errors_per_minute.increment()
            if error:
                self.error_types[type(error).__name__] += 1
    
    def get_success_rate(self) -> float:
        """Get overall success rate (0-1)."""
        with self._lock:
            if self.total_requests == 0:
                return 1.0
            return 1.0 - (self.total_errors / self.total_requests)
    
    def get_command_success_rate(self, command: str) -> float:
        """Get success rate for a specific command."""
        with self._lock:
            total = self.command_counts.get(command, 0)
            errors = self.error_counts.get(command, 0)
            if total == 0:
                return 1.0
            return 1.0 - (errors / total)
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system resource metrics."""
        if not HAS_PSUTIL:
            return {}
        try:
            process = psutil.Process()
            return {
                'cpu_percent': process.cpu_percent(),
                'memory_mb': process.memory_info().rss / (1024 * 1024),
                'memory_percent': process.memory_percent(),
                'threads': process.num_threads(),
            }
        except Exception:
            return {}
    
    def snapshot(self) -> Dict[str, Any]:
        """Get comprehensive telemetry snapshot."""
        with self._lock:
            uptime = time.time() - self._start_time
            
            return {
                'uptime_seconds': uptime,
                'uptime_formatted': str(timedelta(seconds=int(uptime))),
                
                # Request counts
                'total_requests': self.total_requests,
                'total_errors': self.total_errors,
                'success_rate': self.get_success_rate(),
                
                # Time-windowed
                'requests_per_minute': self._requests_per_minute.count(),
                'errors_per_minute': self._errors_per_minute.count(),
                
                # Per-command breakdown
                'command_counts': dict(self.command_counts),
                'error_counts': dict(self.error_counts),
                'error_types': dict(self.error_types),
                
                # Latency stats
                'latency': self._global_latency.get_stats(),
                
                # Active requests
                'active_requests': len(self._active_requests),
                
                # System metrics
                'system': self.get_system_metrics(),
            }
    
    def get_recent_requests(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get the N most recent requests."""
        with self._lock:
            recent = list(self._request_history)[-n:]
            return [
                {
                    'request_id': m.request_id,
                    'command': m.command,
                    'latency_ms': m.latency_ms,
                    'success': m.success,
                    'error_type': m.error_type,
                    'timestamp': datetime.fromtimestamp(m.start_time).isoformat(),
                }
                for m in recent
            ]
    
    def get_command_latency_stats(self, command: str) -> Dict[str, Optional[float]]:
        """Get latency stats for a specific command."""
        return self._command_latencies[command].get_stats()
