"""
VoxMind Platform Base Classes
==============================
Abstract interfaces that all platforms must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
import subprocess
import webbrowser
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class WindowInfo:
    """Information about a window."""
    handle: Any  # Platform-specific handle
    title: str
    process_name: str
    pid: int
    rect: Tuple[int, int, int, int]  # x, y, width, height
    is_visible: bool = True
    is_minimized: bool = False
    is_maximized: bool = False


@dataclass
class AppInfo:
    """Information about an installed application."""
    name: str
    path: str
    icon_path: Optional[str] = None
    is_uwp: bool = False  # Windows UWP apps


@dataclass
class AudioDevice:
    """Audio device information."""
    id: str
    name: str
    is_default: bool = False
    volume: float = 1.0
    is_muted: bool = False


# =============================================================================
# ABSTRACT INTERFACES
# =============================================================================

class WindowController(ABC):
    """Abstract interface for window management."""
    
    @abstractmethod
    def get_active_window(self) -> Optional[WindowInfo]:
        """Get the currently active/focused window."""
        pass
    
    @abstractmethod
    def get_all_windows(self) -> List[WindowInfo]:
        """Get all visible windows."""
        pass
    
    @abstractmethod
    def focus(self, window: WindowInfo) -> bool:
        """Focus/activate a window."""
        pass
    
    @abstractmethod
    def minimize(self, window: WindowInfo) -> bool:
        """Minimize a window."""
        pass
    
    @abstractmethod
    def maximize(self, window: WindowInfo) -> bool:
        """Maximize a window."""
        pass
    
    @abstractmethod
    def restore(self, window: WindowInfo) -> bool:
        """Restore a window from minimized/maximized state."""
        pass
    
    @abstractmethod
    def close(self, window: WindowInfo) -> bool:
        """Close a window."""
        pass
    
    @abstractmethod
    def snap_left(self, window: WindowInfo) -> bool:
        """Snap window to left half of screen."""
        pass
    
    @abstractmethod
    def snap_right(self, window: WindowInfo) -> bool:
        """Snap window to right half of screen."""
        pass
    
    def find_by_title(self, title: str) -> Optional[WindowInfo]:
        """Find a window by title substring."""
        title_lower = title.lower()
        for window in self.get_all_windows():
            if title_lower in window.title.lower():
                return window
        return None
    
    def find_by_process(self, process_name: str) -> List[WindowInfo]:
        """Find all windows by process name."""
        proc_lower = process_name.lower()
        return [w for w in self.get_all_windows() 
                if proc_lower in w.process_name.lower()]


class AudioController(ABC):
    """Abstract interface for audio control."""
    
    @abstractmethod
    def get_volume(self) -> float:
        """Get current volume (0.0 - 1.0)."""
        pass
    
    @abstractmethod
    def set_volume(self, level: float) -> bool:
        """Set volume (0.0 - 1.0)."""
        pass
    
    @abstractmethod
    def is_muted(self) -> bool:
        """Check if audio is muted."""
        pass
    
    @abstractmethod
    def mute(self) -> bool:
        """Mute audio."""
        pass
    
    @abstractmethod
    def unmute(self) -> bool:
        """Unmute audio."""
        pass
    
    def toggle_mute(self) -> bool:
        """Toggle mute state."""
        if self.is_muted():
            return self.unmute()
        return self.mute()
    
    def volume_up(self, step: float = 0.1) -> bool:
        """Increase volume by step."""
        current = self.get_volume()
        return self.set_volume(min(1.0, current + step))
    
    def volume_down(self, step: float = 0.1) -> bool:
        """Decrease volume by step."""
        current = self.get_volume()
        return self.set_volume(max(0.0, current - step))


class AppController(ABC):
    """Abstract interface for application management."""
    
    @abstractmethod
    def list_installed(self) -> List[AppInfo]:
        """List installed applications."""
        pass
    
    @abstractmethod
    def launch(self, app_name: str) -> Tuple[bool, str]:
        """Launch an application by name."""
        pass
    
    @abstractmethod
    def terminate(self, app_name: str) -> Tuple[bool, str]:
        """Terminate an application by name."""
        pass
    
    @abstractmethod
    def is_running(self, app_name: str) -> bool:
        """Check if an application is running."""
        pass
    
    def open_url(self, url: str) -> bool:
        """Open a URL in the default browser."""
        try:
            webbrowser.open(url)
            return True
        except Exception as e:
            logger.error(f"Failed to open URL {url}: {e}")
            return False


class SystemController(ABC):
    """Abstract interface for system operations."""
    
    @abstractmethod
    def lock(self) -> bool:
        """Lock the workstation."""
        pass
    
    @abstractmethod
    def sleep(self) -> bool:
        """Put system to sleep."""
        pass
    
    @abstractmethod
    def shutdown(self, delay: int = 0) -> bool:
        """Shutdown the system."""
        pass
    
    @abstractmethod
    def restart(self, delay: int = 0) -> bool:
        """Restart the system."""
        pass
    
    @abstractmethod
    def get_screen_size(self) -> Tuple[int, int]:
        """Get primary screen resolution."""
        pass
    
    @abstractmethod
    def take_screenshot(self, filepath: str = None) -> Optional[str]:
        """Take a screenshot, return file path."""
        pass


class ClipboardController(ABC):
    """Abstract interface for clipboard operations."""
    
    @abstractmethod
    def get_text(self) -> Optional[str]:
        """Get text from clipboard."""
        pass
    
    @abstractmethod
    def set_text(self, text: str) -> bool:
        """Set text to clipboard."""
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """Clear clipboard."""
        pass


class HotkeyController(ABC):
    """Abstract interface for global hotkey registration."""
    
    @abstractmethod
    def register(self, keys: str, callback) -> bool:
        """Register a global hotkey. Keys like 'ctrl+shift+v'."""
        pass
    
    @abstractmethod
    def unregister(self, keys: str) -> bool:
        """Unregister a global hotkey."""
        pass
    
    @abstractmethod
    def unregister_all(self) -> bool:
        """Unregister all hotkeys."""
        pass


class NotificationController(ABC):
    """Abstract interface for system notifications."""
    
    @abstractmethod
    def show(self, title: str, message: str, icon: str = None, 
             duration: int = 5) -> bool:
        """Show a system notification."""
        pass


# =============================================================================
# BASE PLATFORM (Fallback with no-ops)
# =============================================================================

class BaseWindowController(WindowController):
    """Fallback window controller with no-ops."""
    
    def get_active_window(self) -> Optional[WindowInfo]:
        logger.warning("Window control not available on this platform")
        return None
    
    def get_all_windows(self) -> List[WindowInfo]:
        return []
    
    def focus(self, window: WindowInfo) -> bool:
        return False
    
    def minimize(self, window: WindowInfo) -> bool:
        return False
    
    def maximize(self, window: WindowInfo) -> bool:
        return False
    
    def restore(self, window: WindowInfo) -> bool:
        return False
    
    def close(self, window: WindowInfo) -> bool:
        return False
    
    def snap_left(self, window: WindowInfo) -> bool:
        return False
    
    def snap_right(self, window: WindowInfo) -> bool:
        return False


class BaseAudioController(AudioController):
    """Fallback audio controller."""
    
    def get_volume(self) -> float:
        logger.warning("Audio control not available on this platform")
        return 0.5
    
    def set_volume(self, level: float) -> bool:
        return False
    
    def is_muted(self) -> bool:
        return False
    
    def mute(self) -> bool:
        return False
    
    def unmute(self) -> bool:
        return False


class BaseAppController(AppController):
    """Fallback app controller using subprocess."""
    
    def list_installed(self) -> List[AppInfo]:
        return []
    
    def launch(self, app_name: str) -> Tuple[bool, str]:
        try:
            subprocess.Popen([app_name], shell=True)
            return True, f"Launched {app_name}"
        except Exception as e:
            return False, str(e)
    
    def terminate(self, app_name: str) -> Tuple[bool, str]:
        return False, "Not implemented"
    
    def is_running(self, app_name: str) -> bool:
        return False


class BaseSystemController(SystemController):
    """Fallback system controller."""
    
    def lock(self) -> bool:
        logger.warning("System lock not available on this platform")
        return False
    
    def sleep(self) -> bool:
        return False
    
    def shutdown(self, delay: int = 0) -> bool:
        return False
    
    def restart(self, delay: int = 0) -> bool:
        return False
    
    def get_screen_size(self) -> Tuple[int, int]:
        try:
            import pyautogui
            return pyautogui.size()
        except (ImportError, Exception) as e:
            logger.debug(f"Could not get screen size: {e}")
            return (1920, 1080)
    
    def take_screenshot(self, filepath: str = None) -> Optional[str]:
        try:
            import pyautogui
            from datetime import datetime
            if not filepath:
                filepath = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            pyautogui.screenshot(filepath)
            return filepath
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return None


class BaseClipboardController(ClipboardController):
    """Fallback clipboard using pyperclip."""
    
    def get_text(self) -> Optional[str]:
        try:
            import pyperclip
            return pyperclip.paste()
        except (ImportError, Exception) as e:
            logger.debug(f"Could not get clipboard: {e}")
            return None
    
    def set_text(self, text: str) -> bool:
        try:
            import pyperclip
            pyperclip.copy(text)
            return True
        except (ImportError, Exception) as e:
            logger.debug(f"Could not set clipboard: {e}")
            return False
    
    def clear(self) -> bool:
        return self.set_text("")


class BaseHotkeyController(HotkeyController):
    """Fallback hotkey controller using pynput."""
    
    def __init__(self):
        self._hotkeys = {}
    
    def register(self, keys: str, callback) -> bool:
        try:
            from pynput import keyboard
            # Parse keys like "ctrl+shift+v"
            self._hotkeys[keys] = callback
            return True
        except ImportError as e:
            logger.debug(f"pynput not available for hotkeys: {e}")
            return False
    
    def unregister(self, keys: str) -> bool:
        if keys in self._hotkeys:
            del self._hotkeys[keys]
            return True
        return False
    
    def unregister_all(self) -> bool:
        self._hotkeys.clear()
        return True


class BaseNotificationController(NotificationController):
    """Fallback notification using plyer."""
    
    def show(self, title: str, message: str, icon: str = None,
             duration: int = 5) -> bool:
        try:
            from plyer import notification
            notification.notify(
                title=title,
                message=message,
                app_icon=icon,
                timeout=duration
            )
            return True
        except (ImportError, Exception) as e:
            logger.info(f"Notification ({e}): {title} - {message}")
            return False


# =============================================================================
# BASE PLATFORM CLASS
# =============================================================================

class Platform:
    """
    Base platform class that provides fallback implementations.
    Platform-specific modules should subclass this and override controllers.
    """
    
    def __init__(self):
        self.window = BaseWindowController()
        self.audio = BaseAudioController()
        self.app = BaseAppController()
        self.system = BaseSystemController()
        self.clipboard = BaseClipboardController()
        self.hotkey = BaseHotkeyController()
        self.notification = BaseNotificationController()
    
    @property
    def name(self) -> str:
        return "Unknown"
    
    def open_file(self, path: str) -> bool:
        """Open a file with the default application."""
        try:
            import subprocess
            import sys
            if sys.platform == 'win32':
                import os
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', path])
            else:
                subprocess.run(['xdg-open', path])
            return True
        except Exception as e:
            logger.error(f"Failed to open {path}: {e}")
            return False
