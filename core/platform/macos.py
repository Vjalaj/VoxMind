"""
VoxMind macOS Platform Implementation
=======================================
macOS-specific implementations of platform abstractions.
"""

import os
import subprocess
import logging
from typing import List, Optional, Tuple
from datetime import datetime

from .base import (
    Platform as BasePlatform, WindowInfo, AppInfo,
    WindowController, AudioController, AppController,
    SystemController, ClipboardController, HotkeyController,
    NotificationController, BaseClipboardController,
    BaseHotkeyController
)

logger = logging.getLogger(__name__)


# =============================================================================
# HELPER: Run AppleScript
# =============================================================================

def run_applescript(script: str) -> Optional[str]:
    """Run an AppleScript and return the output."""
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception as e:
        logger.error(f"AppleScript failed: {e}")
        return None


def run_applescript_lines(lines: List[str]) -> Optional[str]:
    """Run multi-line AppleScript."""
    script = '\n'.join(lines)
    return run_applescript(script)


# =============================================================================
# MACOS WINDOW CONTROLLER
# =============================================================================

class MacOSWindowController(WindowController):
    """macOS window control using AppleScript."""
    
    def get_active_window(self) -> Optional[WindowInfo]:
        script = '''
        tell application "System Events"
            set frontApp to first application process whose frontmost is true
            set appName to name of frontApp
            try
                set winName to name of front window of frontApp
            on error
                set winName to ""
            end try
            return appName & "|" & winName
        end tell
        '''
        result = run_applescript(script)
        if result:
            parts = result.split('|', 1)
            return WindowInfo(
                handle=parts[0],  # Use app name as handle
                title=parts[1] if len(parts) > 1 else "",
                process_name=parts[0],
                pid=0,
                rect=(0, 0, 0, 0),
            )
        return None
    
    def get_all_windows(self) -> List[WindowInfo]:
        script = '''
        tell application "System Events"
            set windowList to {}
            repeat with proc in (every process whose visible is true)
                set procName to name of proc
                try
                    repeat with win in (every window of proc)
                        set winName to name of win
                        set end of windowList to procName & "|" & winName
                    end repeat
                end try
            end repeat
            return windowList
        end tell
        '''
        result = run_applescript(script)
        if not result:
            return []
        
        windows = []
        for item in result.split(', '):
            parts = item.split('|', 1)
            if len(parts) >= 2:
                windows.append(WindowInfo(
                    handle=parts[0],
                    title=parts[1],
                    process_name=parts[0],
                    pid=0,
                    rect=(0, 0, 0, 0),
                ))
        return windows
    
    def focus(self, window: WindowInfo) -> bool:
        script = f'''
        tell application "{window.process_name}"
            activate
        end tell
        '''
        return run_applescript(script) is not None
    
    def minimize(self, window: WindowInfo) -> bool:
        script = f'''
        tell application "System Events"
            tell process "{window.process_name}"
                try
                    click button 3 of front window
                end try
            end tell
        end tell
        '''
        return run_applescript(script) is not None
    
    def maximize(self, window: WindowInfo) -> bool:
        # macOS uses "zoom" instead of maximize
        script = f'''
        tell application "System Events"
            tell process "{window.process_name}"
                try
                    click button 2 of front window
                end try
            end tell
        end tell
        '''
        return run_applescript(script) is not None
    
    def restore(self, window: WindowInfo) -> bool:
        # Activate the app to unminimize
        return self.focus(window)
    
    def close(self, window: WindowInfo) -> bool:
        script = f'''
        tell application "System Events"
            tell process "{window.process_name}"
                try
                    click button 1 of front window
                end try
            end tell
        end tell
        '''
        return run_applescript(script) is not None
    
    def snap_left(self, window: WindowInfo) -> bool:
        # macOS doesn't have native snap, use window positioning
        try:
            import pyautogui
            w, h = pyautogui.size()
            script = f'''
            tell application "System Events"
                tell process "{window.process_name}"
                    try
                        set position of front window to {{0, 0}}
                        set size of front window to {{{w // 2}, {h}}}
                    end try
                end tell
            end tell
            '''
            return run_applescript(script) is not None
        except (ImportError, Exception) as e:
            logger.debug(f"snap_left failed: {e}")
            return False
    
    def snap_right(self, window: WindowInfo) -> bool:
        try:
            import pyautogui
            w, h = pyautogui.size()
            script = f'''
            tell application "System Events"
                tell process "{window.process_name}"
                    try
                        set position of front window to {{{w // 2}, 0}}
                        set size of front window to {{{w // 2}, {h}}}
                    end try
                end tell
            end tell
            '''
            return run_applescript(script) is not None
        except (ImportError, Exception) as e:
            logger.debug(f"snap_right failed: {e}")
            return False


# =============================================================================
# MACOS AUDIO CONTROLLER
# =============================================================================

class MacOSAudioController(AudioController):
    """macOS audio control using osascript."""
    
    def get_volume(self) -> float:
        result = run_applescript('output volume of (get volume settings)')
        if result:
            try:
                return int(result) / 100.0
            except (ValueError, TypeError):
                pass
        return 0.5
    
    def set_volume(self, level: float) -> bool:
        level = max(0.0, min(1.0, level))
        volume_int = int(level * 100)
        return run_applescript(f'set volume output volume {volume_int}') is not None
    
    def is_muted(self) -> bool:
        result = run_applescript('output muted of (get volume settings)')
        return result == 'true'
    
    def mute(self) -> bool:
        return run_applescript('set volume output muted true') is not None
    
    def unmute(self) -> bool:
        return run_applescript('set volume output muted false') is not None


# =============================================================================
# MACOS APP CONTROLLER
# =============================================================================

class MacOSAppController(AppController):
    """macOS application control."""
    
    def list_installed(self) -> List[AppInfo]:
        """List installed applications from /Applications."""
        apps = []
        app_dirs = ['/Applications', os.path.expanduser('~/Applications')]
        
        for app_dir in app_dirs:
            if not os.path.isdir(app_dir):
                continue
            
            for item in os.listdir(app_dir):
                if item.endswith('.app'):
                    name = item[:-4]  # Remove .app
                    path = os.path.join(app_dir, item)
                    apps.append(AppInfo(name=name, path=path))
        
        return apps
    
    def launch(self, app_name: str) -> Tuple[bool, str]:
        """Launch an application."""
        # Common app mappings
        app_map = {
            'chrome': 'Google Chrome',
            'google chrome': 'Google Chrome',
            'firefox': 'Firefox',
            'safari': 'Safari',
            'terminal': 'Terminal',
            'finder': 'Finder',
            'files': 'Finder',
            'settings': 'System Preferences',
            'preferences': 'System Preferences',
            'calculator': 'Calculator',
            'notes': 'Notes',
            'mail': 'Mail',
            'calendar': 'Calendar',
            'music': 'Music',
            'photos': 'Photos',
            'messages': 'Messages',
            'code': 'Visual Studio Code',
            'vscode': 'Visual Studio Code',
        }
        
        app_display_name = app_map.get(app_name.lower(), app_name)
        
        # Try direct launch
        script = f'tell application "{app_display_name}" to activate'
        if run_applescript(script) is not None:
            return True, f"Launched {app_name}"
        
        # Try opening from /Applications
        try:
            subprocess.Popen(['open', '-a', app_display_name])
            return True, f"Launched {app_name}"
        except subprocess.SubprocessError as e:
            logger.debug(f"open -a failed: {e}")
        
        return False, f"Could not launch {app_name}"
    
    def terminate(self, app_name: str) -> Tuple[bool, str]:
        """Terminate an application."""
        script = f'tell application "{app_name}" to quit'
        if run_applescript(script) is not None:
            return True, f"Terminated {app_name}"
        
        # Force quit
        try:
            subprocess.run(['pkill', '-f', app_name], check=True)
            return True, f"Force quit {app_name}"
        except subprocess.SubprocessError as e:
            return False, f"Could not terminate {app_name}: {e}"
    
    def is_running(self, app_name: str) -> bool:
        script = f'''
        tell application "System Events"
            (name of processes) contains "{app_name}"
        end tell
        '''
        result = run_applescript(script)
        return result == 'true'


# =============================================================================
# MACOS SYSTEM CONTROLLER
# =============================================================================

class MacOSSystemController(SystemController):
    """macOS system operations."""
    
    def lock(self) -> bool:
        # Activate screensaver which effectively locks
        script = 'tell application "System Events" to keystroke "q" using {control down, command down}'
        if run_applescript(script) is not None:
            return True
        
        try:
            subprocess.run(['pmset', 'displaysleepnow'], check=True)
            return True
        except subprocess.SubprocessError as e:
            logger.debug(f"pmset lock failed: {e}")
            return False
    
    def sleep(self) -> bool:
        try:
            subprocess.run(['pmset', 'sleepnow'], check=True)
            return True
        except subprocess.SubprocessError as e:
            logger.debug(f"pmset sleep failed: {e}")
            script = 'tell application "System Events" to sleep'
            return run_applescript(script) is not None
    
    def shutdown(self, delay: int = 0) -> bool:
        script = 'tell application "System Events" to shut down'
        return run_applescript(script) is not None
    
    def restart(self, delay: int = 0) -> bool:
        script = 'tell application "System Events" to restart'
        return run_applescript(script) is not None
    
    def get_screen_size(self) -> Tuple[int, int]:
        script = '''
        tell application "Finder"
            set screenBounds to bounds of window of desktop
            return (item 3 of screenBounds) & "x" & (item 4 of screenBounds)
        end tell
        '''
        result = run_applescript(script)
        if result:
            try:
                parts = result.split('x')
                return (int(parts[0]), int(parts[1]))
            except (ValueError, IndexError):
                pass
        
        try:
            import pyautogui
            return pyautogui.size()
        except (ImportError, Exception) as e:
            logger.debug(f"pyautogui screen size failed: {e}")
            return (1920, 1080)
    
    def take_screenshot(self, filepath: str = None) -> Optional[str]:
        if not filepath:
            filepath = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        try:
            subprocess.run(['screencapture', filepath], check=True)
            return filepath
        except subprocess.SubprocessError as e:
            logger.debug(f"screencapture failed: {e}")
            try:
                import pyautogui
                pyautogui.screenshot(filepath)
                return filepath
            except (ImportError, Exception) as e2:
                logger.debug(f"pyautogui screenshot failed: {e2}")
                return None


# =============================================================================
# MACOS CLIPBOARD CONTROLLER
# =============================================================================

class MacOSClipboardController(ClipboardController):
    """macOS clipboard using pbcopy/pbpaste."""
    
    def get_text(self) -> Optional[str]:
        try:
            result = subprocess.run(['pbpaste'], capture_output=True, text=True)
            return result.stdout
        except subprocess.SubprocessError as e:
            logger.debug(f"pbpaste failed: {e}")
            return None
    
    def set_text(self, text: str) -> bool:
        try:
            process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
            process.communicate(text.encode('utf-8'))
            return process.returncode == 0
        except subprocess.SubprocessError as e:
            logger.debug(f"pbcopy failed: {e}")
            return False
    
    def clear(self) -> bool:
        return self.set_text("")


# =============================================================================
# MACOS NOTIFICATION CONTROLLER
# =============================================================================

class MacOSNotificationController(NotificationController):
    """macOS notifications using osascript."""
    
    def show(self, title: str, message: str, icon: str = None,
             duration: int = 5) -> bool:
        script = f'display notification "{message}" with title "{title}"'
        return run_applescript(script) is not None


# =============================================================================
# MACOS PLATFORM
# =============================================================================

class Platform(BasePlatform):
    """macOS platform implementation."""
    
    def __init__(self):
        self.window = MacOSWindowController()
        self.audio = MacOSAudioController()
        self.app = MacOSAppController()
        self.system = MacOSSystemController()
        self.clipboard = MacOSClipboardController()
        self.hotkey = BaseHotkeyController()  # pynput works on macOS
        self.notification = MacOSNotificationController()
    
    @property
    def name(self) -> str:
        return "macOS"
    
    def open_file(self, path: str) -> bool:
        try:
            subprocess.Popen(['open', path])
            return True
        except Exception as e:
            logger.error(f"Failed to open {path}: {e}")
            return False
