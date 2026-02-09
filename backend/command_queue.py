"""Priority command queue for backend processing.

Supports background vs interactive command prioritization.
"""

from typing import Callable, Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import IntEnum
from queue import PriorityQueue, Empty
from concurrent.futures import ThreadPoolExecutor, Future
import threading
import time
import uuid
import logging

logger = logging.getLogger(__name__)


class Priority(IntEnum):
    """Command priorities (lower = higher priority)."""
    CRITICAL = 0    # System commands, urgent
    HIGH = 10       # User interactive commands
    NORMAL = 50     # Standard commands
    LOW = 100       # Background tasks
    BACKGROUND = 200  # Deferred/batch operations


@dataclass(order=True)
class QueuedCommand:
    """Command in the queue."""
    priority: int
    timestamp: float = field(compare=False)
    command_id: str = field(compare=False)
    raw_text: str = field(compare=False)
    parsed: Dict[str, Any] = field(compare=False)
    callback: Optional[Callable[[str, Optional[Exception]], None]] = field(
        compare=False, default=None
    )
    
    @classmethod
    def create(cls, raw_text: str, parsed: Dict[str, Any],
               priority: Priority = Priority.NORMAL,
               callback: Optional[Callable] = None) -> 'QueuedCommand':
        return cls(
            priority=priority,
            timestamp=time.time(),
            command_id=str(uuid.uuid4())[:8],
            raw_text=raw_text,
            parsed=parsed,
            callback=callback
        )


@dataclass
class CommandResult:
    """Result of command execution."""
    command_id: str
    success: bool
    response: Optional[str]
    error: Optional[Exception]
    execution_time: float
    queued_time: float


class CommandQueue:
    """
    Priority queue for command execution.
    
    Features:
    - Priority-based ordering
    - Background worker threads
    - Callback support
    - Queue depth monitoring
    """
    
    def __init__(self,
                 executor: Callable[[Dict[str, Any]], str],
                 max_workers: int = 4,
                 max_queue_size: int = 1000):
        """
        Args:
            executor: Function to execute commands
            max_workers: Number of worker threads
            max_queue_size: Maximum pending commands
        """
        self.executor = executor
        self.max_queue_size = max_queue_size
        
        self._queue: PriorityQueue = PriorityQueue(maxsize=max_queue_size)
        self._thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self._results: Dict[str, CommandResult] = {}
        self._pending: Dict[str, Future] = {}
        self._lock = threading.Lock()
        self._running = True
        
        # Stats
        self._total_queued = 0
        self._total_processed = 0
        self._total_dropped = 0
    
    def enqueue(self, raw_text: str, parsed: Dict[str, Any],
                priority: Priority = Priority.NORMAL,
                callback: Optional[Callable] = None) -> Optional[str]:
        """
        Add command to queue.
        
        Args:
            raw_text: Original command text
            parsed: Parsed command dict
            priority: Command priority
            callback: Optional callback(response, error)
            
        Returns:
            Command ID or None if queue full
        """
        if self._queue.full():
            self._total_dropped += 1
            logger.warning("Command queue full, dropping command")
            return None
        
        cmd = QueuedCommand.create(raw_text, parsed, priority, callback)
        self._queue.put(cmd)
        self._total_queued += 1
        
        # Submit for processing
        future = self._thread_pool.submit(self._process_next)
        with self._lock:
            self._pending[cmd.command_id] = future
        
        return cmd.command_id
    
    def enqueue_sync(self, raw_text: str, parsed: Dict[str, Any],
                     priority: Priority = Priority.NORMAL,
                     timeout: Optional[float] = None) -> CommandResult:
        """
        Add command and wait for result.
        
        Args:
            raw_text: Original command text
            parsed: Parsed command dict
            priority: Command priority
            timeout: Max wait time
            
        Returns:
            CommandResult
        """
        event = threading.Event()
        result_holder = [None]
        
        def on_complete(response, error):
            result_holder[0] = (response, error)
            event.set()
        
        command_id = self.enqueue(raw_text, parsed, priority, on_complete)
        
        if command_id is None:
            return CommandResult(
                command_id="",
                success=False,
                response=None,
                error=Exception("Queue full"),
                execution_time=0,
                queued_time=0
            )
        
        event.wait(timeout=timeout)
        
        if result_holder[0] is None:
            return CommandResult(
                command_id=command_id,
                success=False,
                response=None,
                error=Exception("Timeout waiting for result"),
                execution_time=0,
                queued_time=0
            )
        
        response, error = result_holder[0]
        return self._results.get(command_id, CommandResult(
            command_id=command_id,
            success=error is None,
            response=response,
            error=error,
            execution_time=0,
            queued_time=0
        ))
    
    def _process_next(self):
        """Process next command from queue."""
        try:
            cmd = self._queue.get(timeout=1.0)
        except Empty:
            return
        
        queued_time = time.time() - cmd.timestamp
        start_time = time.time()
        
        response = None
        error = None
        
        try:
            response = self.executor(cmd.parsed)
        except Exception as e:
            error = e
            logger.error(f"Command execution failed: {e}")
        
        execution_time = time.time() - start_time
        
        result = CommandResult(
            command_id=cmd.command_id,
            success=error is None,
            response=response,
            error=error,
            execution_time=execution_time,
            queued_time=queued_time
        )
        
        with self._lock:
            self._results[cmd.command_id] = result
            self._pending.pop(cmd.command_id, None)
        
        self._total_processed += 1
        
        # Call callback if provided
        if cmd.callback:
            try:
                cmd.callback(response, error)
            except Exception as e:
                logger.error(f"Callback failed: {e}")
        
        self._queue.task_done()
    
    def get_result(self, command_id: str) -> Optional[CommandResult]:
        """Get result for a command ID."""
        with self._lock:
            return self._results.get(command_id)
    
    def wait_for_result(self, command_id: str,
                        timeout: Optional[float] = None) -> Optional[CommandResult]:
        """Wait for a command to complete and get result."""
        with self._lock:
            future = self._pending.get(command_id)
        
        if future:
            try:
                future.result(timeout=timeout)
            except Exception:
                pass
        
        return self.get_result(command_id)
    
    def get_queue_depth(self) -> int:
        """Get number of pending commands."""
        return self._queue.qsize()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        with self._lock:
            return {
                'queue_depth': self._queue.qsize(),
                'max_queue_size': self.max_queue_size,
                'total_queued': self._total_queued,
                'total_processed': self._total_processed,
                'total_dropped': self._total_dropped,
                'pending_results': len(self._pending),
                'cached_results': len(self._results),
            }
    
    def shutdown(self, wait: bool = True):
        """Shutdown the queue."""
        self._running = False
        self._thread_pool.shutdown(wait=wait)


# Priority inference based on command type
COMMAND_PRIORITIES: Dict[str, Priority] = {
    # Critical
    'shutdown': Priority.CRITICAL,
    'restart': Priority.CRITICAL,
    'system_power': Priority.CRITICAL,
    
    # High priority (interactive)
    'input_control': Priority.HIGH,
    'click': Priority.HIGH,
    'smart_click': Priority.HIGH,
    'overlay': Priority.HIGH,
    'windows_ui': Priority.HIGH,
    
    # Normal
    'open_browser': Priority.NORMAL,
    'search': Priority.NORMAL,
    'control_app': Priority.NORMAL,
    'get_time': Priority.NORMAL,
    'control_volume': Priority.NORMAL,
    'conversation': Priority.NORMAL,
    
    # Low priority
    'knowledge': Priority.LOW,
    'screen_context': Priority.LOW,
    
    # Background
    'daemon': Priority.BACKGROUND,
    'introspection': Priority.BACKGROUND,
}


def infer_priority(parsed: Dict[str, Any]) -> Priority:
    """Infer priority from parsed command."""
    command = parsed.get('command', 'unknown')
    return COMMAND_PRIORITIES.get(command, Priority.NORMAL)
