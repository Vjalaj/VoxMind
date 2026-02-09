"""Command history for undo/replay functionality.

Tracks executed commands for history navigation and undo support.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime
import threading
import time
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class HistoryEntry:
    """Single command history entry."""
    command_id: str
    raw_text: str
    parsed: Dict[str, Any]
    response: Optional[str]
    success: bool
    timestamp: float
    can_undo: bool = False
    undo_command: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'command_id': self.command_id,
            'raw_text': self.raw_text,
            'command': self.parsed.get('command', 'unknown'),
            'response': self.response,
            'success': self.success,
            'timestamp': datetime.fromtimestamp(self.timestamp).isoformat(),
            'can_undo': self.can_undo,
        }


# Undo mappings for reversible commands
UNDO_MAPPINGS: Dict[str, Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]] = {}


def register_undo(command: str):
    """Decorator to register undo handler for a command."""
    def decorator(func: Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]):
        UNDO_MAPPINGS[command] = func
        return func
    return decorator


# Built-in undo mappings

@register_undo('control_volume')
def undo_volume(parsed: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Generate undo command for volume changes."""
    params = parsed.get('params', {})
    action = params.get('action')
    
    if action == 'up':
        return {'command': 'control_volume', 'params': {'action': 'down'}}
    elif action == 'down':
        return {'command': 'control_volume', 'params': {'action': 'up'}}
    elif action == 'mute':
        return {'command': 'control_volume', 'params': {'action': 'unmute'}}
    elif action == 'unmute':
        return {'command': 'control_volume', 'params': {'action': 'mute'}}
    return None


@register_undo('control_brightness')
def undo_brightness(parsed: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Generate undo command for brightness changes."""
    params = parsed.get('params', {})
    action = params.get('action')
    
    if action == 'up':
        return {'command': 'control_brightness', 'params': {'action': 'down'}}
    elif action == 'down':
        return {'command': 'control_brightness', 'params': {'action': 'up'}}
    return None


@register_undo('control_window')
def undo_window(parsed: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Generate undo command for window control."""
    params = parsed.get('params', {})
    action = params.get('action')
    
    if action == 'minimize':
        return {'command': 'control_window', 'params': {'action': 'restore'}}
    elif action == 'maximize':
        return {'command': 'control_window', 'params': {'action': 'restore'}}
    return None


class CommandHistory:
    """
    Maintains command history for navigation and undo.
    """
    
    def __init__(self, max_size: int = 100):
        """
        Args:
            max_size: Maximum history entries to keep
        """
        self.max_size = max_size
        self._history: deque = deque(maxlen=max_size)
        self._undo_stack: List[HistoryEntry] = []
        self._redo_stack: List[HistoryEntry] = []
        self._lock = threading.Lock()
    
    def record(self, command_id: str, raw_text: str, parsed: Dict[str, Any],
               response: Optional[str], success: bool):
        """Record a command execution."""
        # Check if command is undoable
        command = parsed.get('command', 'unknown')
        undo_handler = UNDO_MAPPINGS.get(command)
        undo_command = None
        can_undo = False
        
        if undo_handler and success:
            try:
                undo_command = undo_handler(parsed)
                can_undo = undo_command is not None
            except Exception as e:
                logger.error(f"Undo handler failed: {e}")
        
        entry = HistoryEntry(
            command_id=command_id,
            raw_text=raw_text,
            parsed=parsed,
            response=response,
            success=success,
            timestamp=time.time(),
            can_undo=can_undo,
            undo_command=undo_command
        )
        
        with self._lock:
            self._history.append(entry)
            
            # Add to undo stack if undoable
            if can_undo:
                self._undo_stack.append(entry)
                # Clear redo stack on new command
                self._redo_stack.clear()
    
    def get_last(self, n: int = 1) -> List[HistoryEntry]:
        """Get the last N history entries."""
        with self._lock:
            return list(self._history)[-n:]
    
    def get_all(self) -> List[HistoryEntry]:
        """Get full history."""
        with self._lock:
            return list(self._history)
    
    def search(self, query: str) -> List[HistoryEntry]:
        """Search history for matching commands."""
        query_lower = query.lower()
        with self._lock:
            return [
                entry for entry in self._history
                if query_lower in entry.raw_text.lower()
            ]
    
    def get_by_command(self, command: str) -> List[HistoryEntry]:
        """Get history entries for a specific command type."""
        with self._lock:
            return [
                entry for entry in self._history
                if entry.parsed.get('command') == command
            ]
    
    def can_undo(self) -> bool:
        """Check if undo is available."""
        with self._lock:
            return len(self._undo_stack) > 0
    
    def can_redo(self) -> bool:
        """Check if redo is available."""
        with self._lock:
            return len(self._redo_stack) > 0
    
    def get_undo_command(self) -> Optional[Dict[str, Any]]:
        """Get the undo command for the last undoable action."""
        with self._lock:
            if not self._undo_stack:
                return None
            
            entry = self._undo_stack.pop()
            self._redo_stack.append(entry)
            return entry.undo_command
    
    def get_redo_command(self) -> Optional[Dict[str, Any]]:
        """Get the redo command (original command from undo stack)."""
        with self._lock:
            if not self._redo_stack:
                return None
            
            entry = self._redo_stack.pop()
            self._undo_stack.append(entry)
            return entry.parsed
    
    def clear(self):
        """Clear all history."""
        with self._lock:
            self._history.clear()
            self._undo_stack.clear()
            self._redo_stack.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get history statistics."""
        with self._lock:
            commands = {}
            for entry in self._history:
                cmd = entry.parsed.get('command', 'unknown')
                commands[cmd] = commands.get(cmd, 0) + 1
            
            return {
                'total_entries': len(self._history),
                'max_size': self.max_size,
                'undo_available': len(self._undo_stack),
                'redo_available': len(self._redo_stack),
                'commands': commands,
            }
    
    def export_json(self) -> str:
        """Export history as JSON."""
        with self._lock:
            return json.dumps(
                [entry.to_dict() for entry in self._history],
                indent=2
            )
    
    def get_frequent_commands(self, n: int = 5) -> List[tuple]:
        """Get the N most frequent commands."""
        stats = self.get_stats()
        commands = stats.get('commands', {})
        sorted_cmds = sorted(commands.items(), key=lambda x: x[1], reverse=True)
        return sorted_cmds[:n]
