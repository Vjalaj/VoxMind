"""
VoxMind Windows Platform Implementation
=========================================
Windows-specific implementations of platform abstractions.
"""

import os
import sys
import subprocess
import logging
from typing import List, Optional, Tuple
from datetime import datetime

from .base import (
    Platform, WindowInfo, AppInfo,
    WindowController, AudioController, AppController,
    SystemController, ClipboardController, HotkeyController,
    NotificationController, BaseNotificationController
)

logger = logging.getLogger(__name__)

# =============================================================================
# WINDOWS IMPORTS (Guarded)
# =============================================================================

try:
    import win32gui
    import win32con
    import win32api
    import win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    logger.warning("pywin32 not installed - window control limited")

try:
    import ctypes
    from ctypes import wintypes
    HAS_CTYPES = True
except ImportError:
    HAS_CTYPES = False

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    HAS_PYCAW = True
except ImportError:
    HAS_PYCAW = False
    logger.warning("pycaw not installed - volume control unavailable")


# =============================================================================
# WINDOWS WINDOW CONTROLLER
# =============================================================================

class WindowsWindowController(WindowController):
    """Windows implementation of window control using pywin32."""
    
    def get_active_window(self) -> Optional[WindowInfo]:
        if not HAS_WIN32:
            return None
        try:
            hwnd = win32gui.GetForegroundWindow()
            return self._hwnd_to_info(hwnd)
        except Exception as e:
            logger.error(f"Failed to get active window: {e}")
            return None
    
    def get_all_windows(self) -> List[WindowInfo]:
        if not HAS_WIN32:
            return []
        
        windows = []
        
        def enum_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:  # Skip windows without titles
                    info = self._hwnd_to_info(hwnd)
                    if info:
                        windows.append(info)
            return True
        
        try:
            win32gui.EnumWindows(enum_callback, None)
        except Exception as e:
            logger.error(f"Failed to enumerate windows: {e}")
        
        return windows
    
    def _hwnd_to_info(self, hwnd) -> Optional[WindowInfo]:
        """Convert a window handle to WindowInfo."""
        try:
            title = win32gui.GetWindowText(hwnd)
            rect = win32gui.GetWindowRect(hwnd)
            
            # Get process info
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                import psutil
                proc = psutil.Process(pid)
                process_name = proc.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied, ImportError) as e:
                logger.debug(f"Could not get process name: {e}")
                process_name = "unknown"
            
            # Check window state
            placement = win32gui.GetWindowPlacement(hwnd)
            is_minimized = placement[1] == win32con.SW_SHOWMINIMIZED
            is_maximized = placement[1] == win32con.SW_SHOWMAXIMIZED
            
            return WindowInfo(
                handle=hwnd,
                title=title,
                process_name=process_name,
                pid=pid,
                rect=(rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1]),
                is_visible=win32gui.IsWindowVisible(hwnd),
                is_minimized=is_minimized,
                is_maximized=is_maximized,
            )
        except Exception as e:
            logger.error(f"Failed to get window info: {e}")
            return None
    
    def focus(self, window: WindowInfo) -> bool:
        if not HAS_WIN32:
            return False
        try:
            hwnd = window.handle
            # Restore if minimized
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            return True
        except Exception as e:
            logger.error(f"Failed to focus window: {e}")
            return False
    
    def minimize(self, window: WindowInfo) -> bool:
        if not HAS_WIN32:
            return False
        try:
            win32gui.ShowWindow(window.handle, win32con.SW_MINIMIZE)
            return True
        except Exception as e:
            logger.error(f"Failed to minimize window: {e}")
            return False
    
    def maximize(self, window: WindowInfo) -> bool:
        if not HAS_WIN32:
            return False
        try:
            win32gui.ShowWindow(window.handle, win32con.SW_MAXIMIZE)
            return True
        except Exception as e:
            logger.error(f"Failed to maximize window: {e}")
            return False
    
    def restore(self, window: WindowInfo) -> bool:
        if not HAS_WIN32:
            return False
        try:
            win32gui.ShowWindow(window.handle, win32con.SW_RESTORE)
            return True
        except Exception as e:
            logger.error(f"Failed to restore window: {e}")
            return False
    
    def close(self, window: WindowInfo) -> bool:
        if not HAS_WIN32:
            return False
        try:
            win32gui.PostMessage(window.handle, win32con.WM_CLOSE, 0, 0)
            return True
        except Exception as e:
            logger.error(f"Failed to close window: {e}")
            return False
    
    def snap_left(self, window: WindowInfo) -> bool:
        if not HAS_WIN32:
            return False
        try:
            # Get screen size
            screen_w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            screen_h = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
            
            # Snap to left half
            win32gui.SetWindowPos(
                window.handle, None,
                0, 0, screen_w // 2, screen_h,
                win32con.SWP_NOZORDER
            )
            return True
        except Exception as e:
            logger.error(f"Failed to snap left: {e}")
            return False
    
    def snap_right(self, window: WindowInfo) -> bool:
        if not HAS_WIN32:
            return False
        try:
            screen_w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            screen_h = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
            
            win32gui.SetWindowPos(
                window.handle, None,
                screen_w // 2, 0, screen_w // 2, screen_h,
                win32con.SWP_NOZORDER
            )
            return True
        except Exception as e:
            logger.error(f"Failed to snap right: {e}")
            return False


# =============================================================================
# WINDOWS AUDIO CONTROLLER
# =============================================================================

class WindowsAudioController(AudioController):
    """Windows audio control using pycaw."""
    
    def __init__(self):
        self._volume_interface = None
        self._init_audio()
    
    def _init_audio(self):
        if not HAS_PYCAW:
            return
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            self._volume_interface = interface.QueryInterface(IAudioEndpointVolume)
        except Exception as e:
            logger.debug(f"pycaw init failed, will use fallback: {e}")
    
    def get_volume(self) -> float:
        if not self._volume_interface:
            return 0.5
        try:
            return self._volume_interface.GetMasterVolumeLevelScalar()
        except Exception as e:
            logger.debug(f"Failed to get volume: {e}")
            return 0.5
    
    def set_volume(self, level: float) -> bool:
        if not self._volume_interface:
            return False
        try:
            level = max(0.0, min(1.0, level))
            self._volume_interface.SetMasterVolumeLevelScalar(level, None)
            return True
        except Exception as e:
            logger.error(f"Failed to set volume: {e}")
            return False
    
    def is_muted(self) -> bool:
        if not self._volume_interface:
            return False
        try:
            return bool(self._volume_interface.GetMute())
        except Exception as e:
            logger.debug(f"Failed to check mute status: {e}")
            return False
    
    def mute(self) -> bool:
        if not self._volume_interface:
            return False
        try:
            self._volume_interface.SetMute(1, None)
            return True
        except Exception as e:
            logger.error(f"Failed to mute: {e}")
            return False
    
    def unmute(self) -> bool:
        if not self._volume_interface:
            return False
        try:
            self._volume_interface.SetMute(0, None)
            return True
        except Exception as e:
            logger.error(f"Failed to unmute: {e}")
            return False


# =============================================================================
# WINDOWS APP CONTROLLER
# =============================================================================

class WindowsAppController(AppController):
    """Windows application control."""
    
    def __init__(self):
        self._app_cache = {}
        self._cache_loaded = False
    
    def list_installed(self) -> List[AppInfo]:
        """List installed applications using PowerShell Get-StartApps."""
        if self._cache_loaded:
            return list(self._app_cache.values())
        
        apps = []
        try:
            result = subprocess.run(
                ['powershell', '-Command', 'Get-StartApps | ConvertTo-Json'],
                capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                if isinstance(data, list):
                    for item in data:
                        app = AppInfo(
                            name=item.get('Name', ''),
                            path=item.get('AppID', ''),
                            is_uwp='!' in item.get('AppID', '')
                        )
                        apps.append(app)
                        self._app_cache[app.name.lower()] = app
        except Exception as e:
            logger.error(f"Failed to list apps: {e}")
        
        self._cache_loaded = True
        return apps
    
    def launch(self, app_name: str) -> Tuple[bool, str]:
        """Launch an application."""
        app_lower = app_name.lower()
        
        # Common app mappings
        app_map = {
            'chrome': 'chrome', 'google chrome': 'chrome',
            'firefox': 'firefox', 'mozilla firefox': 'firefox',
            'edge': 'msedge', 'microsoft edge': 'msedge',
            'notepad': 'notepad',
            'word': 'winword', 'microsoft word': 'winword',
            'excel': 'excel', 'microsoft excel': 'excel',
            'powerpoint': 'powerpnt', 'ppt': 'powerpnt',
            'outlook': 'outlook',
            'explorer': 'explorer', 'file explorer': 'explorer',
            'terminal': 'wt', 'windows terminal': 'wt',
            'cmd': 'cmd', 'command prompt': 'cmd',
            'powershell': 'powershell',
            'calculator': 'calc',
            'paint': 'mspaint',
            'settings': 'ms-settings:',
        }
        
        executable = app_map.get(app_lower, app_name)
        
        try:
            if executable.startswith('ms-'):
                # UWP app via URI
                os.startfile(executable)
            else:
                subprocess.Popen(
                    executable, shell=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            return True, f"Launched {app_name}"
        except Exception as e:
            # Try Start Menu search fallback
            return self._launch_via_start_menu(app_name)
    
    def _launch_via_start_menu(self, app_name: str) -> Tuple[bool, str]:
        """Launch by typing in Start Menu search."""
        try:
            import pyautogui
            import time
            
            pyautogui.press('win')
            time.sleep(0.5)
            pyautogui.typewrite(app_name, interval=0.05)
            time.sleep(0.5)
            pyautogui.press('enter')
            
            return True, f"Searching for {app_name} in Start Menu"
        except Exception as e:
            return False, f"Could not launch {app_name}: {e}"
    
    def terminate(self, app_name: str) -> Tuple[bool, str]:
        """Terminate an application."""
        try:
            result = subprocess.run(
                ['taskkill', '/f', '/im', f'{app_name}.exe'],
                capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode == 0:
                return True, f"Terminated {app_name}"
            return False, result.stderr
        except Exception as e:
            return False, str(e)
    
    def is_running(self, app_name: str) -> bool:
        """Check if application is running."""
        try:
            import psutil
            app_lower = app_name.lower()
            for proc in psutil.process_iter(['name']):
                if app_lower in proc.info['name'].lower():
                    return True
        except (ImportError, psutil.Error) as e:
            logger.debug(f"Could not check running apps: {e}")
        return False


# =============================================================================
# WINDOWS SYSTEM CONTROLLER
# =============================================================================

class WindowsSystemController(SystemController):
    """Windows system operations."""
    
    def lock(self) -> bool:
        try:
            ctypes.windll.user32.LockWorkStation()
            return True
        except (OSError, AttributeError) as e:
            logger.debug(f"LockWorkStation failed: {e}")
            try:
                subprocess.run(
                    ['rundll32.exe', 'user32.dll,LockWorkStation'],
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                return True
            except subprocess.SubprocessError as e2:
                logger.error(f"Failed to lock workstation: {e2}")
                return False
    
    def sleep(self) -> bool:
        try:
            subprocess.run(
                ['rundll32.exe', 'powrprof.dll,SetSuspendState', '0', '1', '0'],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return True
        except subprocess.SubprocessError as e:
            logger.error(f"Failed to sleep: {e}")
            return False
    
    def shutdown(self, delay: int = 0) -> bool:
        try:
            subprocess.run(
                ['shutdown', '/s', '/t', str(delay)],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return True
        except subprocess.SubprocessError as e:
            logger.error(f"Failed to shutdown: {e}")
            return False
    
    def restart(self, delay: int = 0) -> bool:
        try:
            subprocess.run(
                ['shutdown', '/r', '/t', str(delay)],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return True
        except subprocess.SubprocessError as e:
            logger.error(f"Failed to restart: {e}")
            return False
    
    def get_screen_size(self) -> Tuple[int, int]:
        try:
            if HAS_WIN32:
                w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
                h = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
                return (w, h)
        except (OSError, AttributeError) as e:
            logger.debug(f"Win32 screen size failed: {e}")
        
        try:
            import pyautogui
            return pyautogui.size()
        except (ImportError, Exception) as e:
            logger.debug(f"pyautogui screen size failed: {e}")
            return (1920, 1080)
    
    def take_screenshot(self, filepath: str = None) -> Optional[str]:
        try:
            import pyautogui
            if not filepath:
                filepath = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            pyautogui.screenshot(filepath)
            return filepath
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return None


# =============================================================================
# WINDOWS CLIPBOARD CONTROLLER
# =============================================================================

class WindowsClipboardController(ClipboardController):
    """Windows clipboard using win32clipboard."""
    
    def get_text(self) -> Optional[str]:
        if not HAS_WIN32:
            try:
                import pyperclip
                return pyperclip.paste()
            except (ImportError, Exception) as e:
                logger.debug(f"pyperclip get failed: {e}")
                return None
        
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            try:
                data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                return data
            finally:
                win32clipboard.CloseClipboard()
        except Exception as e:
            logger.debug(f"win32clipboard get failed: {e}")
            return None
    
    def set_text(self, text: str) -> bool:
        if not HAS_WIN32:
            try:
                import pyperclip
                pyperclip.copy(text)
                return True
            except (ImportError, Exception) as e:
                logger.debug(f"pyperclip set failed: {e}")
                return False
        
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
            finally:
                win32clipboard.CloseClipboard()
            return True
        except Exception as e:
            logger.debug(f"win32clipboard set failed: {e}")
            return False
            return False
    
    def clear(self) -> bool:
        return self.set_text("")


# =============================================================================
# WINDOWS HOTKEY CONTROLLER
# =============================================================================

class WindowsHotkeyController(HotkeyController):
    """Windows global hotkeys using ctypes."""
    
    def __init__(self):
        self._hotkeys = {}
        self._next_id = 1
    
    def register(self, keys: str, callback) -> bool:
        """Register a global hotkey like 'win+shift+v'."""
        if not HAS_CTYPES:
            return False
        
        try:
            # Parse keys
            modifiers = 0
            vk = 0
            
            parts = keys.lower().replace('+', ' ').split()
            for part in parts:
                if part in ('ctrl', 'control'):
                    modifiers |= 0x0002  # MOD_CONTROL
                elif part in ('alt', 'menu'):
                    modifiers |= 0x0001  # MOD_ALT
                elif part in ('shift',):
                    modifiers |= 0x0004  # MOD_SHIFT
                elif part in ('win', 'windows', 'super'):
                    modifiers |= 0x0008  # MOD_WIN
                else:
                    # Virtual key code
                    if len(part) == 1:
                        vk = ord(part.upper())
                    else:
                        # Named keys
                        vk_map = {
                            'space': 0x20, 'enter': 0x0D, 'tab': 0x09,
                            'escape': 0x1B, 'esc': 0x1B,
                            'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,
                            'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77,
                        }
                        vk = vk_map.get(part, 0)
            
            if vk == 0:
                return False
            
            # Register hotkey
            hotkey_id = self._next_id
            self._next_id += 1
            
            if ctypes.windll.user32.RegisterHotKey(None, hotkey_id, modifiers, vk):
                self._hotkeys[keys] = (hotkey_id, callback)
                return True
            
            return False
        except Exception as e:
            logger.error(f"Failed to register hotkey {keys}: {e}")
            return False
    
    def unregister(self, keys: str) -> bool:
        if keys in self._hotkeys:
            hotkey_id, _ = self._hotkeys[keys]
            try:
                ctypes.windll.user32.UnregisterHotKey(None, hotkey_id)
            except (OSError, AttributeError) as e:
                logger.debug(f"Failed to unregister hotkey: {e}")
            del self._hotkeys[keys]
            return True
        return False
    
    def unregister_all(self) -> bool:
        for keys in list(self._hotkeys.keys()):
            self.unregister(keys)
        return True


# =============================================================================
# WINDOWS PLATFORM
# =============================================================================

class Platform(Platform):
    """Windows platform implementation."""
    
    def __init__(self):
        self.window = WindowsWindowController()
        self.audio = WindowsAudioController()
        self.app = WindowsAppController()
        self.system = WindowsSystemController()
        self.clipboard = WindowsClipboardController()
        self.hotkey = WindowsHotkeyController()
        self.notification = BaseNotificationController()  # Use cross-platform
    
    @property
    def name(self) -> str:
        return "Windows"
    
    def open_file(self, path: str) -> bool:
        try:
            os.startfile(path)
            return True
        except Exception as e:
            logger.error(f"Failed to open {path}: {e}")
            return False
