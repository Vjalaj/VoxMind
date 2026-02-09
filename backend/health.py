"""Health check system for backend monitoring.

Provides health endpoints and status checks.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import threading
import time
import logging

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a single health check."""
    name: str
    status: HealthStatus
    message: str = ""
    latency_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'status': self.status.value,
            'message': self.message,
            'latency_ms': round(self.latency_ms, 2),
            'details': self.details,
            'timestamp': datetime.fromtimestamp(self.timestamp).isoformat(),
        }


@dataclass
class HealthReport:
    """Overall health report."""
    status: HealthStatus
    checks: List[HealthCheckResult]
    uptime_seconds: float
    version: str = "2.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'version': self.version,
            'uptime': str(timedelta(seconds=int(self.uptime_seconds))),
            'uptime_seconds': round(self.uptime_seconds, 2),
            'timestamp': datetime.now().isoformat(),
            'checks': [c.to_dict() for c in self.checks],
        }


class HealthCheck:
    """
    Health check system with pluggable checks.
    """
    
    def __init__(self, version: str = "2.0.0"):
        self.version = version
        self._start_time = time.time()
        self._checks: Dict[str, Callable[[], HealthCheckResult]] = {}
        self._last_results: Dict[str, HealthCheckResult] = {}
        self._lock = threading.Lock()
        
        # Register built-in checks
        self._register_builtin_checks()
    
    def _register_builtin_checks(self):
        """Register default health checks."""
        self.register("memory", self._check_memory)
        self.register("cpu", self._check_cpu)
        self.register("disk", self._check_disk)
    
    def register(self, name: str, check: Callable[[], HealthCheckResult]):
        """Register a health check."""
        with self._lock:
            self._checks[name] = check
    
    def unregister(self, name: str):
        """Unregister a health check."""
        with self._lock:
            self._checks.pop(name, None)
    
    def run_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check."""
        with self._lock:
            check = self._checks.get(name)
        
        if not check:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Check '{name}' not found"
            )
        
        start = time.time()
        try:
            result = check()
            result.latency_ms = (time.time() - start) * 1000
        except Exception as e:
            result = HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                latency_ms=(time.time() - start) * 1000
            )
        
        with self._lock:
            self._last_results[name] = result
        
        return result
    
    def run_all(self) -> HealthReport:
        """Run all health checks and return report."""
        results = []
        
        with self._lock:
            check_names = list(self._checks.keys())
        
        for name in check_names:
            result = self.run_check(name)
            results.append(result)
        
        # Determine overall status
        overall = HealthStatus.HEALTHY
        for result in results:
            if result.status == HealthStatus.UNHEALTHY:
                overall = HealthStatus.UNHEALTHY
                break
            elif result.status == HealthStatus.DEGRADED:
                overall = HealthStatus.DEGRADED
        
        return HealthReport(
            status=overall,
            checks=results,
            uptime_seconds=time.time() - self._start_time,
            version=self.version
        )
    
    def get_uptime(self) -> float:
        """Get uptime in seconds."""
        return time.time() - self._start_time
    
    def is_healthy(self) -> bool:
        """Quick health check - returns True if healthy."""
        report = self.run_all()
        return report.status == HealthStatus.HEALTHY
    
    # Built-in checks
    
    def _check_memory(self) -> HealthCheckResult:
        """Check memory usage."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            process = psutil.Process()
            process_memory = process.memory_info()
            
            used_percent = memory.percent
            
            if used_percent > 95:
                status = HealthStatus.UNHEALTHY
                message = f"Critical memory usage: {used_percent:.1f}%"
            elif used_percent > 85:
                status = HealthStatus.DEGRADED
                message = f"High memory usage: {used_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory usage: {used_percent:.1f}%"
            
            return HealthCheckResult(
                name="memory",
                status=status,
                message=message,
                details={
                    'system_used_percent': used_percent,
                    'system_available_mb': memory.available / (1024 * 1024),
                    'process_rss_mb': process_memory.rss / (1024 * 1024),
                    'process_vms_mb': process_memory.vms / (1024 * 1024),
                }
            )
        except ImportError:
            return HealthCheckResult(
                name="memory",
                status=HealthStatus.UNKNOWN,
                message="psutil not available"
            )
        except Exception as e:
            return HealthCheckResult(
                name="memory",
                status=HealthStatus.UNHEALTHY,
                message=str(e)
            )
    
    def _check_cpu(self) -> HealthCheckResult:
        """Check CPU usage."""
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=0.1)
            process = psutil.Process()
            process_cpu = process.cpu_percent()
            
            if cpu_percent > 95:
                status = HealthStatus.UNHEALTHY
                message = f"Critical CPU usage: {cpu_percent:.1f}%"
            elif cpu_percent > 80:
                status = HealthStatus.DEGRADED
                message = f"High CPU usage: {cpu_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"CPU usage: {cpu_percent:.1f}%"
            
            return HealthCheckResult(
                name="cpu",
                status=status,
                message=message,
                details={
                    'system_percent': cpu_percent,
                    'process_percent': process_cpu,
                    'cores': psutil.cpu_count(),
                }
            )
        except ImportError:
            return HealthCheckResult(
                name="cpu",
                status=HealthStatus.UNKNOWN,
                message="psutil not available"
            )
        except Exception as e:
            return HealthCheckResult(
                name="cpu",
                status=HealthStatus.UNHEALTHY,
                message=str(e)
            )
    
    def _check_disk(self) -> HealthCheckResult:
        """Check disk space."""
        try:
            import psutil
            disk = psutil.disk_usage('/')
            used_percent = disk.percent
            
            if used_percent > 95:
                status = HealthStatus.UNHEALTHY
                message = f"Critical disk usage: {used_percent:.1f}%"
            elif used_percent > 85:
                status = HealthStatus.DEGRADED
                message = f"High disk usage: {used_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk usage: {used_percent:.1f}%"
            
            return HealthCheckResult(
                name="disk",
                status=status,
                message=message,
                details={
                    'used_percent': used_percent,
                    'free_gb': disk.free / (1024 ** 3),
                    'total_gb': disk.total / (1024 ** 3),
                }
            )
        except ImportError:
            return HealthCheckResult(
                name="disk",
                status=HealthStatus.UNKNOWN,
                message="psutil not available"
            )
        except Exception as e:
            return HealthCheckResult(
                name="disk",
                status=HealthStatus.UNHEALTHY,
                message=str(e)
            )


# Custom health check factories

def create_telemetry_check(telemetry) -> Callable[[], HealthCheckResult]:
    """Create health check for telemetry status."""
    def check() -> HealthCheckResult:
        try:
            snapshot = telemetry.snapshot()
            success_rate = snapshot.get('success_rate', 1.0)
            errors_per_min = snapshot.get('errors_per_minute', 0)
            
            if success_rate < 0.5:
                status = HealthStatus.UNHEALTHY
                message = f"Low success rate: {success_rate*100:.1f}%"
            elif success_rate < 0.9 or errors_per_min > 10:
                status = HealthStatus.DEGRADED
                message = f"Elevated errors: {errors_per_min}/min"
            else:
                status = HealthStatus.HEALTHY
                message = f"Success rate: {success_rate*100:.1f}%"
            
            return HealthCheckResult(
                name="telemetry",
                status=status,
                message=message,
                details={
                    'success_rate': success_rate,
                    'errors_per_minute': errors_per_min,
                    'total_requests': snapshot.get('total_requests', 0),
                }
            )
        except Exception as e:
            return HealthCheckResult(
                name="telemetry",
                status=HealthStatus.UNHEALTHY,
                message=str(e)
            )
    return check


def create_queue_check(queue) -> Callable[[], HealthCheckResult]:
    """Create health check for command queue."""
    def check() -> HealthCheckResult:
        try:
            stats = queue.get_stats()
            depth = stats.get('queue_depth', 0)
            max_size = stats.get('max_queue_size', 1000)
            dropped = stats.get('total_dropped', 0)
            
            utilization = depth / max_size if max_size > 0 else 0
            
            if utilization > 0.9 or dropped > 0:
                status = HealthStatus.UNHEALTHY
                message = f"Queue near capacity: {depth}/{max_size}"
            elif utilization > 0.7:
                status = HealthStatus.DEGRADED
                message = f"Queue filling: {depth}/{max_size}"
            else:
                status = HealthStatus.HEALTHY
                message = f"Queue healthy: {depth}/{max_size}"
            
            return HealthCheckResult(
                name="queue",
                status=status,
                message=message,
                details=stats
            )
        except Exception as e:
            return HealthCheckResult(
                name="queue",
                status=HealthStatus.UNHEALTHY,
                message=str(e)
            )
    return check


def create_circuit_check(registry) -> Callable[[], HealthCheckResult]:
    """Create health check for circuit breakers."""
    def check() -> HealthCheckResult:
        try:
            open_circuits = registry.get_open_circuits()
            all_status = registry.get_status()
            
            if len(open_circuits) > 3:
                status = HealthStatus.UNHEALTHY
                message = f"Multiple circuits open: {open_circuits}"
            elif len(open_circuits) > 0:
                status = HealthStatus.DEGRADED
                message = f"Circuit open: {open_circuits}"
            else:
                status = HealthStatus.HEALTHY
                message = "All circuits closed"
            
            return HealthCheckResult(
                name="circuits",
                status=status,
                message=message,
                details={'open_circuits': open_circuits, 'all': all_status}
            )
        except Exception as e:
            return HealthCheckResult(
                name="circuits",
                status=HealthStatus.UNHEALTHY,
                message=str(e)
            )
    return check
