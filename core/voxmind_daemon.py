"""
VoxMind Service Daemon
======================
A persistent background service that makes VoxMind truly interactive.

Features:
- Always-on wake word detection
- Global hotkey support (Win+Shift+V to activate)
- System event hooks (clipboard, window focus)
- System tray integration
- Inter-process communication (IPC) via named pipes
- Plugin/extension system

This is the "subsystem" that makes VoxMind feel like a real OS-integrated assistant.

Usage:
    # Run as daemon (background service)
    python -m core.voxmind_daemon --daemon
    
    # Run interactively (for debugging)
    python -m core.voxmind_daemon
    
    # Install as Windows service
    python -m core.voxmind_daemon --install
"""

import sys
import os
import time
import threading
import queue
import json
import signal
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable, List
from enum import Enum, auto
from datetime import datetime
import ctypes
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger('VoxMind.Daemon')


# ============================================================================
# EVENT SYSTEM
# ============================================================================

class EventType(Enum):
    """Types of events VoxMind can react to."""
    # Voice events
    WAKE_WORD_DETECTED = auto()
    VOICE_COMMAND = auto()
    VOICE_TIMEOUT = auto()
    
    # Input events
    HOTKEY_PRESSED = auto()
    MOUSE_GESTURE = auto()
    
    # System events
    CLIPBOARD_CHANGED = auto()
    WINDOW_FOCUS_CHANGED = auto()
    SYSTEM_IDLE = auto()
    SYSTEM_RESUME = auto()
    
    # App events
    APP_LAUNCHED = auto()
    APP_CLOSED = auto()
    
    # Internal events
    COMMAND_PROCESSED = auto()
    RESPONSE_READY = auto()
    ERROR_OCCURRED = auto()
    
    # Lifecycle events
    DAEMON_STARTED = auto()
    DAEMON_STOPPING = auto()


@dataclass
class VoxEvent:
    """An event in the VoxMind system."""
    type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: str = "system"
    priority: int = 5  # 1=highest, 10=lowest


class EventBus:
    """
    Central event bus for VoxMind daemon.
    All components communicate through events.
    """
    
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._queue: queue.PriorityQueue = queue.PriorityQueue()
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
    
    def subscribe(self, event_type: EventType, handler: Callable):
        """Subscribe to an event type."""
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(handler)
            logger.debug(f"Subscribed to {event_type.name}")
    
    def unsubscribe(self, event_type: EventType, handler: Callable):
        """Unsubscribe from an event type."""
        with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type].remove(handler)
    
    def publish(self, event: VoxEvent):
        """Publish an event to all subscribers."""
        # Priority queue uses (priority, timestamp, event) for ordering
        self._queue.put((event.priority, event.timestamp, event))
    
    def start(self):
        """Start the event processing loop."""
        self._running = True
        self._worker_thread = threading.Thread(target=self._process_loop, daemon=True)
        self._worker_thread.start()
        logger.info("Event bus started")
    
    def stop(self):
        """Stop the event processing loop."""
        self._running = False
        # Put a poison pill to unblock the queue
        self._queue.put((0, 0, None))
        if self._worker_thread:
            self._worker_thread.join(timeout=2)
        logger.info("Event bus stopped")
    
    def _process_loop(self):
        """Main event processing loop."""
        while self._running:
            try:
                priority, timestamp, event = self._queue.get(timeout=0.1)
                if event is None:  # Poison pill
                    break
                self._dispatch(event)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Event processing error: {e}")
    
    def _dispatch(self, event: VoxEvent):
        """Dispatch event to all subscribers."""
        with self._lock:
            handlers = self._subscribers.get(event.type, [])
        
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Handler error for {event.type.name}: {e}")


# ============================================================================
# HOTKEY MANAGER (Global keyboard shortcuts)
# ============================================================================

class HotkeyManager:
    """
    Manages global hotkeys for VoxMind.
    Works even when VoxMind window is not focused.
    """
    
    # Virtual key codes
    VK_SHIFT = 0x10
    VK_CONTROL = 0x11
    VK_ALT = 0x12
    VK_WIN = 0x5B
    VK_V = 0x56
    VK_M = 0x4D
    VK_ESCAPE = 0x1B
    
    MOD_ALT = 0x0001
    MOD_CONTROL = 0x0002
    MOD_SHIFT = 0x0004
    MOD_WIN = 0x0008
    MOD_NOREPEAT = 0x4000
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._hotkeys: Dict[int, Dict] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._next_id = 1
    
    def register(self, modifiers: int, key: int, action: str) -> int:
        """
        Register a global hotkey.
        
        Args:
            modifiers: Combination of MOD_* constants
            key: Virtual key code
            action: Action name to trigger
        
        Returns:
            Hotkey ID
        """
        hotkey_id = self._next_id
        self._next_id += 1
        self._hotkeys[hotkey_id] = {
            'modifiers': modifiers,
            'key': key,
            'action': action
        }
        return hotkey_id
    
    def start(self):
        """Start listening for hotkeys."""
        if sys.platform != 'win32':
            logger.warning("Hotkeys only supported on Windows")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info("Hotkey manager started")
    
    def stop(self):
        """Stop listening for hotkeys."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
    
    def _listen_loop(self):
        """Windows hotkey listening loop."""
        try:
            user32 = ctypes.windll.user32
            
            # Register hotkeys
            for hk_id, hk in self._hotkeys.items():
                result = user32.RegisterHotKey(None, hk_id, 
                                               hk['modifiers'] | self.MOD_NOREPEAT, 
                                               hk['key'])
                if result:
                    logger.info(f"Registered hotkey {hk_id}: {hk['action']}")
                else:
                    logger.warning(f"Failed to register hotkey {hk_id}")
            
            # Message loop
            msg = ctypes.wintypes.MSG()
            while self._running:
                if user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                    if msg.message == 0x0312:  # WM_HOTKEY
                        hotkey_id = msg.wParam
                        if hotkey_id in self._hotkeys:
                            action = self._hotkeys[hotkey_id]['action']
                            self.event_bus.publish(VoxEvent(
                                type=EventType.HOTKEY_PRESSED,
                                data={'action': action, 'hotkey_id': hotkey_id},
                                source='hotkey'
                            ))
                else:
                    time.sleep(0.01)  # Prevent busy loop
            
            # Unregister hotkeys
            for hk_id in self._hotkeys:
                user32.UnregisterHotKey(None, hk_id)
                
        except Exception as e:
            logger.error(f"Hotkey error: {e}")


# Add Windows types for hotkeys
if sys.platform == 'win32':
    import ctypes.wintypes


# ============================================================================
# CLIPBOARD MONITOR
# ============================================================================

class ClipboardMonitor:
    """
    Monitors clipboard changes.
    Useful for "read this" or "translate clipboard" commands.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_content = ""
    
    def start(self):
        """Start monitoring clipboard."""
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Clipboard monitor started")
    
    def stop(self):
        """Stop monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
    
    def _monitor_loop(self):
        """Check clipboard periodically."""
        try:
            import win32clipboard
            
            while self._running:
                try:
                    win32clipboard.OpenClipboard()
                    try:
                        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                            content = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                            if content != self._last_content:
                                self._last_content = content
                                self.event_bus.publish(VoxEvent(
                                    type=EventType.CLIPBOARD_CHANGED,
                                    data={'content': content[:500]},  # Limit size
                                    source='clipboard'
                                ))
                    finally:
                        win32clipboard.CloseClipboard()
                except Exception:
                    pass  # Clipboard busy or inaccessible
                
                time.sleep(0.5)  # Check every 500ms
                
        except ImportError:
            logger.warning("Clipboard monitoring requires pywin32")


# ============================================================================
# WINDOW FOCUS TRACKER
# ============================================================================

class WindowFocusTracker:
    """
    Tracks active window changes.
    Enables context-aware responses based on current app.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_window = ""
        self._current_app = ""
    
    def get_current_app(self) -> str:
        """Get the currently focused application."""
        return self._current_app
    
    def start(self):
        """Start tracking focus."""
        self._running = True
        self._thread = threading.Thread(target=self._track_loop, daemon=True)
        self._thread.start()
        logger.info("Window focus tracker started")
    
    def stop(self):
        """Stop tracking."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
    
    def _track_loop(self):
        """Monitor active window."""
        try:
            import win32gui
            import win32process
            import psutil
            
            while self._running:
                try:
                    hwnd = win32gui.GetForegroundWindow()
                    if hwnd:
                        title = win32gui.GetWindowText(hwnd)
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        try:
                            process = psutil.Process(pid)
                            app_name = process.name()
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                            app_name = "Unknown"
                        
                        window_id = f"{app_name}:{title[:50]}"
                        if window_id != self._last_window:
                            self._last_window = window_id
                            self._current_app = app_name
                            self.event_bus.publish(VoxEvent(
                                type=EventType.WINDOW_FOCUS_CHANGED,
                                data={
                                    'app': app_name,
                                    'title': title,
                                    'hwnd': hwnd
                                },
                                source='window'
                            ))
                except Exception:
                    pass
                
                time.sleep(0.3)  # Check every 300ms
                
        except ImportError:
            logger.warning("Window tracking requires pywin32 and psutil")


# ============================================================================
# VOICE SERVICE
# ============================================================================

class VoiceService:
    """
    Manages voice input (wake word + commands).
    Runs continuously in background.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._running = False
        self._listening_for_command = False
        self._thread: Optional[threading.Thread] = None
        self._wake_words = ["vox", "hey vox", "ok vox", "computer"]
    
    def start(self):
        """Start voice service."""
        self._running = True
        self._thread = threading.Thread(target=self._voice_loop, daemon=True)
        self._thread.start()
        logger.info("Voice service started")
    
    def stop(self):
        """Stop voice service."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def activate(self):
        """Manually activate command listening (e.g., from hotkey)."""
        self._listening_for_command = True
    
    def _voice_loop(self):
        """Main voice processing loop."""
        try:
            # Import speech components
            from core.speech_services import get_services
            services = get_services()
            
            while self._running:
                try:
                    if not self._listening_for_command:
                        # Wait for wake word
                        detected = services.listen_for_wake_word(timeout=2)
                        if detected:
                            self.event_bus.publish(VoxEvent(
                                type=EventType.WAKE_WORD_DETECTED,
                                data={'wake_word': detected},
                                source='voice',
                                priority=1  # High priority
                            ))
                            self._listening_for_command = True
                    
                    if self._listening_for_command:
                        # Listen for command
                        command = services.listen_for_command(timeout=5)
                        if command:
                            self.event_bus.publish(VoxEvent(
                                type=EventType.VOICE_COMMAND,
                                data={'text': command},
                                source='voice',
                                priority=1
                            ))
                        else:
                            self.event_bus.publish(VoxEvent(
                                type=EventType.VOICE_TIMEOUT,
                                source='voice'
                            ))
                        self._listening_for_command = False
                        
                except Exception as e:
                    logger.error(f"Voice error: {e}")
                    time.sleep(1)
                    
        except ImportError as e:
            logger.error(f"Voice service unavailable: {e}")


# ============================================================================
# RESPONSE SERVICE
# ============================================================================

class ResponseService:
    """
    Handles response generation and output (TTS, overlay, etc.)
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._tts_engine = None
        self._overlay = None
    
    def initialize(self):
        """Initialize response components."""
        try:
            import pyttsx3
            self._tts_engine = pyttsx3.init()
            self._tts_engine.setProperty('rate', 180)
            logger.info("TTS engine initialized")
        except Exception as e:
            logger.warning(f"TTS init failed: {e}")
    
    def speak(self, text: str):
        """Speak text via TTS."""
        if self._tts_engine:
            try:
                self._tts_engine.say(text)
                self._tts_engine.runAndWait()
            except Exception as e:
                logger.error(f"TTS error: {e}")
                print(f"[VoxMind]: {text}")
        else:
            print(f"[VoxMind]: {text}")
    
    def show_overlay(self, text: str, duration: float = 3.0):
        """Show overlay notification."""
        # TODO: Integrate with overlay_qt.py
        logger.info(f"[Overlay]: {text}")
    
    def play_sound(self, sound_type: str):
        """Play feedback sound."""
        # TODO: Add sound effects for activation, success, error
        pass


# ============================================================================
# COMMAND PROCESSOR
# ============================================================================

class CommandProcessor:
    """
    Processes voice commands using intelligent response system.
    """
    
    def __init__(self, event_bus: EventBus, response_service: ResponseService):
        self.event_bus = event_bus
        self.response = response_service
        self._intelligent_engine = None
    
    def initialize(self):
        """Initialize command processing components."""
        try:
            from core.intelligent_response import get_intelligent_response_engine
            self._intelligent_engine = get_intelligent_response_engine()
            logger.info("Intelligent response engine loaded")
        except ImportError:
            logger.warning("Intelligent response not available")
    
    def process(self, text: str) -> Dict[str, Any]:
        """Process a voice command."""
        try:
            # Parse command
            from Tejas.nlp_command_parser import parse_command_nlp
            parsed = parse_command_nlp(text, include_alternatives=True)
            
            # Process intelligently
            if self._intelligent_engine:
                result = self._intelligent_engine.process_command(text, parsed)
            else:
                result = {'response': f"Processing: {text}", 'executed': False}
            
            return result
            
        except Exception as e:
            logger.error(f"Command processing error: {e}")
            return {'response': "Sorry, I encountered an error.", 'error': str(e)}


# ============================================================================
# SYSTEM TRAY (Windows)
# ============================================================================

class SystemTray:
    """
    System tray icon for VoxMind.
    Provides quick access and status display.
    """
    
    def __init__(self, event_bus: EventBus, on_quit: Callable):
        self.event_bus = event_bus
        self.on_quit = on_quit
        self._icon = None
        self._thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start system tray."""
        self._thread = threading.Thread(target=self._run_tray, daemon=True)
        self._thread.start()
        logger.info("System tray started")
    
    def stop(self):
        """Stop system tray."""
        if self._icon:
            self._icon.stop()
    
    def _run_tray(self):
        """Run system tray (requires pystray)."""
        try:
            import pystray
            from PIL import Image
            
            # Create a simple icon (blue circle)
            icon_size = 64
            image = Image.new('RGB', (icon_size, icon_size), color='white')
            # Draw a blue circle
            from PIL import ImageDraw
            draw = ImageDraw.Draw(image)
            draw.ellipse([4, 4, icon_size-4, icon_size-4], fill='#4A90D9')
            
            # Create menu
            menu = pystray.Menu(
                pystray.MenuItem("VoxMind", lambda: None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Activate (Win+Shift+V)", self._on_activate),
                pystray.MenuItem("Settings", self._on_settings),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit", self._on_exit)
            )
            
            self._icon = pystray.Icon("VoxMind", image, "VoxMind - Listening", menu)
            self._icon.run()
            
        except ImportError:
            logger.warning("System tray requires pystray and Pillow")
    
    def _on_activate(self):
        """Activate voice listening."""
        self.event_bus.publish(VoxEvent(
            type=EventType.HOTKEY_PRESSED,
            data={'action': 'activate'},
            source='tray'
        ))
    
    def _on_settings(self):
        """Open settings."""
        logger.info("Settings requested")
    
    def _on_exit(self):
        """Exit daemon."""
        self.on_quit()


# ============================================================================
# IPC SERVER (Inter-Process Communication)
# ============================================================================

class IPCServer:
    r"""
    Named pipe server for IPC.
    Allows other apps to send commands to VoxMind.
    
    Example client:
        import win32file
        pipe = win32file.CreateFile(r'\\.\pipe\VoxMind', ...)
        win32file.WriteFile(pipe, b'{"command": "speak", "text": "Hello"}')
    """
    
    PIPE_NAME = r'\\.\pipe\VoxMind'
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start IPC server."""
        if sys.platform != 'win32':
            logger.warning("Named pipes only supported on Windows")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._server_loop, daemon=True)
        self._thread.start()
        logger.info(f"IPC server started on {self.PIPE_NAME}")
    
    def stop(self):
        """Stop IPC server."""
        self._running = False
        # Connect to unblock the server
        try:
            import win32file
            win32file.CreateFile(
                self.PIPE_NAME, 
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0, None, win32file.OPEN_EXISTING, 0, None
            )
        except (ImportError, OSError, Exception):
            pass
        if self._thread:
            self._thread.join(timeout=2)
    
    def _server_loop(self):
        """Named pipe server loop."""
        try:
            import win32pipe
            import win32file
            
            while self._running:
                try:
                    # Create named pipe
                    pipe = win32pipe.CreateNamedPipe(
                        self.PIPE_NAME,
                        win32pipe.PIPE_ACCESS_DUPLEX,
                        win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
                        1, 65536, 65536, 0, None
                    )
                    
                    # Wait for connection
                    win32pipe.ConnectNamedPipe(pipe, None)
                    
                    # Read message
                    result, data = win32file.ReadFile(pipe, 65536)
                    if data:
                        self._handle_message(data.decode('utf-8'))
                    
                    # Close pipe
                    win32file.CloseHandle(pipe)
                    
                except Exception as e:
                    if self._running:
                        logger.error(f"IPC error: {e}")
                        time.sleep(1)
                        
        except ImportError:
            logger.warning("IPC requires pywin32")
    
    def _handle_message(self, message: str):
        """Handle incoming IPC message."""
        try:
            data = json.loads(message)
            command = data.get('command')
            
            if command == 'speak':
                self.event_bus.publish(VoxEvent(
                    type=EventType.RESPONSE_READY,
                    data={'text': data.get('text', '')},
                    source='ipc'
                ))
            elif command == 'process':
                self.event_bus.publish(VoxEvent(
                    type=EventType.VOICE_COMMAND,
                    data={'text': data.get('text', '')},
                    source='ipc'
                ))
            elif command == 'activate':
                self.event_bus.publish(VoxEvent(
                    type=EventType.HOTKEY_PRESSED,
                    data={'action': 'activate'},
                    source='ipc'
                ))
                
        except json.JSONDecodeError:
            logger.error(f"Invalid IPC message: {message}")


# ============================================================================
# MAIN DAEMON
# ============================================================================

class VoxMindDaemon:
    """
    Main VoxMind daemon that orchestrates all services.
    """
    
    def __init__(self):
        self._running = False
        
        # Core event bus
        self.event_bus = EventBus()
        
        # Services
        self.hotkeys = HotkeyManager(self.event_bus)
        self.clipboard = ClipboardMonitor(self.event_bus)
        self.window_tracker = WindowFocusTracker(self.event_bus)
        self.voice = VoiceService(self.event_bus)
        self.response = ResponseService(self.event_bus)
        self.commands = CommandProcessor(self.event_bus, self.response)
        self.tray = SystemTray(self.event_bus, self.stop)
        self.ipc = IPCServer(self.event_bus)
        
        # Setup default hotkeys
        self._setup_hotkeys()
        
        # Setup event handlers
        self._setup_handlers()
    
    def _setup_hotkeys(self):
        """Register default hotkeys."""
        # Win+Shift+V = Activate VoxMind
        self.hotkeys.register(
            HotkeyManager.MOD_WIN | HotkeyManager.MOD_SHIFT,
            HotkeyManager.VK_V,
            'activate'
        )
        # Win+Shift+M = Mute/unmute
        self.hotkeys.register(
            HotkeyManager.MOD_WIN | HotkeyManager.MOD_SHIFT,
            HotkeyManager.VK_M,
            'toggle_mute'
        )
    
    def _setup_handlers(self):
        """Setup event handlers."""
        self.event_bus.subscribe(EventType.WAKE_WORD_DETECTED, self._on_wake_word)
        self.event_bus.subscribe(EventType.VOICE_COMMAND, self._on_voice_command)
        self.event_bus.subscribe(EventType.VOICE_TIMEOUT, self._on_voice_timeout)
        self.event_bus.subscribe(EventType.HOTKEY_PRESSED, self._on_hotkey)
        self.event_bus.subscribe(EventType.RESPONSE_READY, self._on_response)
        self.event_bus.subscribe(EventType.WINDOW_FOCUS_CHANGED, self._on_window_change)
    
    def _on_wake_word(self, event: VoxEvent):
        """Handle wake word detection."""
        logger.info(f"Wake word detected: {event.data.get('wake_word')}")
        self.response.play_sound('activate')
        self.response.speak("Yes?")
    
    def _on_voice_command(self, event: VoxEvent):
        """Handle voice command."""
        text = event.data.get('text', '')
        logger.info(f"Command: {text}")
        
        result = self.commands.process(text)
        
        if result.get('needs_disambiguation'):
            # Present options
            message = result.get('disambiguation_message', "What did you mean?")
            self.response.speak(message)
        else:
            # Speak response
            response = result.get('response', "Done")
            self.response.speak(response)
    
    def _on_voice_timeout(self, event: VoxEvent):
        """Handle voice timeout."""
        self.response.speak("I didn't catch that.")
    
    def _on_hotkey(self, event: VoxEvent):
        """Handle hotkey press."""
        action = event.data.get('action')
        
        if action == 'activate':
            logger.info("Activated via hotkey")
            self.response.play_sound('activate')
            self.response.speak("Listening")
            self.voice.activate()
        elif action == 'toggle_mute':
            logger.info("Toggle mute via hotkey")
            # TODO: Implement mute toggle
    
    def _on_response(self, event: VoxEvent):
        """Handle response event (from IPC etc.)"""
        text = event.data.get('text', '')
        if text:
            self.response.speak(text)
    
    def _on_window_change(self, event: VoxEvent):
        """Handle window focus change (for context awareness)."""
        app = event.data.get('app', '')
        # Could use this for context-aware commands
        logger.debug(f"Window focus: {app}")
    
    def start(self):
        """Start the daemon."""
        logger.info("=" * 50)
        logger.info("VoxMind Daemon Starting")
        logger.info("=" * 50)
        
        self._running = True
        
        # Initialize services
        self.response.initialize()
        self.commands.initialize()
        
        # Start all services
        self.event_bus.start()
        self.hotkeys.start()
        self.clipboard.start()
        self.window_tracker.start()
        self.voice.start()
        self.tray.start()
        self.ipc.start()
        
        # Publish startup event
        self.event_bus.publish(VoxEvent(
            type=EventType.DAEMON_STARTED,
            source='daemon'
        ))
        
        logger.info("VoxMind Daemon Ready")
        logger.info("Press Win+Shift+V to activate, or say 'Hey Vox'")
        
        # Keep main thread alive
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop the daemon."""
        logger.info("VoxMind Daemon Stopping...")
        
        self.event_bus.publish(VoxEvent(
            type=EventType.DAEMON_STOPPING,
            source='daemon'
        ))
        
        self._running = False
        
        # Stop all services
        self.tray.stop()
        self.ipc.stop()
        self.voice.stop()
        self.window_tracker.stop()
        self.clipboard.stop()
        self.hotkeys.stop()
        self.event_bus.stop()
        
        logger.info("VoxMind Daemon Stopped")


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='VoxMind Daemon')
    parser.add_argument('--daemon', action='store_true', 
                        help='Run as background daemon')
    parser.add_argument('--install', action='store_true',
                        help='Install as Windows service')
    parser.add_argument('--uninstall', action='store_true',
                        help='Uninstall Windows service')
    args = parser.parse_args()
    
    if args.install:
        print("Installing VoxMind as Windows service...")
        # TODO: Use pywin32 to install as service
        print("Service installation not yet implemented.")
        print("For now, run: python -m core.voxmind_daemon")
        return
    
    if args.uninstall:
        print("Uninstalling VoxMind service...")
        # TODO: Uninstall service
        print("Service uninstallation not yet implemented.")
        return
    
    # Run daemon
    daemon = VoxMindDaemon()
    daemon.start()


if __name__ == '__main__':
    main()
