"""
VoxMind App Control Module
Provides voice-controlled application management: launch, close, switch, minimize, maximize, snap windows.
Inspired by Windows Voice Access and Google Voice Access.
"""

import subprocess
import re
import os
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple, Any
from enum import Enum
import ctypes
from ctypes import wintypes
import time

# Windows API imports
try:
    import win32gui
    import win32con
    import win32process
    import win32api
    import psutil
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    print("Warning: pywin32 not installed. Some features will be limited.")


class WindowAction(Enum):
    """Window management actions"""
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"
    RESTORE = "restore"
    CLOSE = "close"
    FOCUS = "focus"
    SNAP_LEFT = "snap_left"
    SNAP_RIGHT = "snap_right"
    SNAP_TOP = "snap_top"
    SNAP_BOTTOM = "snap_bottom"
    SNAP_TOP_LEFT = "snap_top_left"
    SNAP_TOP_RIGHT = "snap_top_right"
    SNAP_BOTTOM_LEFT = "snap_bottom_left"
    SNAP_BOTTOM_RIGHT = "snap_bottom_right"


@dataclass
class AppInfo:
    """Information about an installed application"""
    name: str
    app_id: str
    aliases: List[str] = field(default_factory=list)
    executable: Optional[str] = None
    is_uwp: bool = False
    
    def matches(self, query: str) -> bool:
        """Check if query matches this app"""
        query_lower = query.lower().strip()
        if query_lower in self.name.lower():
            return True
        for alias in self.aliases:
            if query_lower == alias.lower():
                return True
        return False


@dataclass 
class WindowInfo:
    """Information about an open window"""
    hwnd: int
    title: str
    process_name: str
    pid: int
    is_visible: bool
    is_minimized: bool
    is_maximized: bool
    rect: Tuple[int, int, int, int]  # left, top, right, bottom


class AppRegistry:
    """Registry of installed applications with common aliases"""
    
    # Common app aliases for voice commands
    COMMON_ALIASES = {
        "chrome": ["google chrome", "browser", "web browser"],
        "edge": ["microsoft edge", "browser"],
        "firefox": ["mozilla firefox", "browser"],
        "notepad": ["text editor", "notes"],
        "calculator": ["calc"],
        "terminal": ["console", "command prompt", "cmd", "powershell"],
        "file explorer": ["explorer", "files", "my computer", "this pc"],
        "settings": ["control panel", "preferences", "system settings"],
        "vs code": ["visual studio code", "code", "vscode"],
        "word": ["microsoft word", "document", "doc"],
        "excel": ["microsoft excel", "spreadsheet"],
        "powerpoint": ["microsoft powerpoint", "slides", "presentation"],
        "outlook": ["email", "mail"],
        "teams": ["microsoft teams"],
        "slack": ["slack messenger"],
        "discord": ["discord chat"],
        "spotify": ["music player", "music"],
        "vlc": ["vlc media player", "video player", "media player"],
        "photos": ["photo viewer", "pictures"],
        "paint": ["paint app", "drawing"],
        "snipping tool": ["screenshot", "screen capture"],
        "task manager": ["processes", "performance"],
        "chatgpt": ["chat gpt", "ai chat"],
        "copilot": ["microsoft copilot", "ai assistant"],
        "whatsapp": ["whats app"],
        "github desktop": ["github"],
        "zoom": ["zoom workplace", "video call", "meeting"],
        "recall": ["windows recall", "memory", "ai recall"],
        "phone link": ["phone", "your phone", "mobile"],
        "clock": ["timer", "alarm", "stopwatch"],
        "weather": ["forecast"],
        "maps": ["windows maps", "directions"],
        "sticky notes": ["notes", "quick notes"],
        "voice recorder": ["recorder", "sound recorder"],
    }
    
    def __init__(self):
        self.apps: Dict[str, AppInfo] = {}
        self._load_apps()
    
    def _load_apps(self):
        """Load installed applications from Windows"""
        try:
            # Get apps from Start Menu
            result = subprocess.run(
                ["powershell", "-Command", "Get-StartApps | Select-Object Name, AppID | ConvertTo-Json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                import json
                apps_data = json.loads(result.stdout)
                if isinstance(apps_data, dict):
                    apps_data = [apps_data]
                
                for app in apps_data:
                    name = app.get("Name", "")
                    app_id = app.get("AppID", "")
                    if name and app_id:
                        # Determine if UWP app
                        is_uwp = "_" in app_id and "!" in app_id
                        
                        # Get aliases
                        name_lower = name.lower()
                        aliases = []
                        for key, alias_list in self.COMMON_ALIASES.items():
                            if key in name_lower:
                                aliases.extend(alias_list)
                        
                        self.apps[name_lower] = AppInfo(
                            name=name,
                            app_id=app_id,
                            aliases=aliases,
                            is_uwp=is_uwp
                        )
        except Exception as e:
            print(f"Warning: Could not load apps: {e}")
    
    def find_app(self, query: str) -> Optional[AppInfo]:
        """Find an app by name or alias"""
        query_lower = query.lower().strip()
        
        # Direct name match
        if query_lower in self.apps:
            return self.apps[query_lower]
        
        # Partial match in name
        for name, app in self.apps.items():
            if query_lower in name:
                return app
        
        # Alias match
        for name, app in self.apps.items():
            if app.matches(query):
                return app
        
        # Fuzzy match - check if query words are in app name
        query_words = query_lower.split()
        for name, app in self.apps.items():
            if all(word in name for word in query_words):
                return app
        
        return None
    
    def search_apps(self, query: str, limit: int = 10) -> List[AppInfo]:
        """Search for apps matching a query"""
        query_lower = query.lower().strip()
        matches = []
        
        for name, app in self.apps.items():
            if query_lower in name or app.matches(query):
                matches.append(app)
                if len(matches) >= limit:
                    break
        
        return matches
    
    def list_categories(self) -> Dict[str, List[str]]:
        """List apps by category"""
        categories = {
            "browsers": [],
            "office": [],
            "development": [],
            "media": [],
            "communication": [],
            "utilities": [],
            "system": [],
            "other": []
        }
        
        for name, app in self.apps.items():
            if any(x in name for x in ["chrome", "edge", "firefox", "browser"]):
                categories["browsers"].append(app.name)
            elif any(x in name for x in ["word", "excel", "powerpoint", "office", "outlook"]):
                categories["office"].append(app.name)
            elif any(x in name for x in ["code", "visual studio", "python", "git", "terminal"]):
                categories["development"].append(app.name)
            elif any(x in name for x in ["player", "music", "video", "photo", "vlc", "spotify"]):
                categories["media"].append(app.name)
            elif any(x in name for x in ["teams", "slack", "whatsapp", "discord", "zoom", "mail"]):
                categories["communication"].append(app.name)
            elif any(x in name for x in ["calculator", "notepad", "paint", "snipping", "clock"]):
                categories["utilities"].append(app.name)
            elif any(x in name for x in ["settings", "control", "task manager", "services"]):
                categories["system"].append(app.name)
            else:
                categories["other"].append(app.name)
        
        return categories


class AppLauncher:
    """Launch and manage applications"""
    
    def __init__(self, registry: Optional[AppRegistry] = None):
        self.registry = registry or AppRegistry()
    
    def launch(self, app_name: str) -> Tuple[bool, str]:
        """Launch an application by name"""
        app = self.registry.find_app(app_name)
        
        if not app:
            # Try direct launch as executable
            return self._try_direct_launch(app_name)
        
        try:
            if app.is_uwp:
                # Launch UWP app using start shell
                subprocess.Popen(
                    ["powershell", "-Command", f"Start-Process 'shell:AppsFolder\\{app.app_id}'"],
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                # Launch Win32 app
                subprocess.Popen(
                    ["powershell", "-Command", f"Start-Process '{app.app_id}'"],
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            
            return True, f"Launched {app.name}"
        except Exception as e:
            return False, f"Failed to launch {app.name}: {e}"
    
    def _try_direct_launch(self, name: str) -> Tuple[bool, str]:
        """Try to launch by direct name/command"""
        # Common direct commands
        direct_commands = {
            "notepad": "notepad.exe",
            "calc": "calc.exe",
            "calculator": "calc.exe",
            "paint": "mspaint.exe",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
            "explorer": "explorer.exe",
            "control": "control.exe",
            "regedit": "regedit.exe",
            "taskmgr": "taskmgr.exe",
            "task manager": "taskmgr.exe",
            "recall": "ms-recall:",  # Windows 11 Recall
            "windows recall": "ms-recall:",
            "phone link": "ms-phone:",
            "your phone": "ms-phone:",
            "settings": "ms-settings:",
            "clock": "ms-clock:",
            "alarms": "ms-clock:",
            "weather": "bingweather:",
            "maps": "bingmaps:",
            "sticky notes": "ms-stickynotes:",
            "feedback": "feedback-hub:",
        }
        
        name_lower = name.lower().strip()
        
        # Special handling for Start Menu
        if name_lower in ["start", "start menu"]:
            try:
                import pyautogui
                pyautogui.press('win')
                return True, "Start menu opened"
            except (ImportError, Exception) as e:
                try:
                    # Fallback: use keyboard simulation
                    import ctypes
                    ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)  # Win key down
                    ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0)  # Win key up
                    return True, "Start menu opened"
                except (OSError, AttributeError) as e2:
                    return False, f"Could not open Start menu: {e2}"
        
        if name_lower in direct_commands:
            try:
                subprocess.Popen(direct_commands[name_lower], creationflags=subprocess.CREATE_NO_WINDOW)
                return True, f"Launched {name}"
            except Exception as e:
                return False, f"Failed to launch {name}: {e}"
        
        # Try as shell command
        try:
            os.startfile(name)
            return True, f"Launched {name}"
        except Exception:
            pass
        
        # Fallback: Use Start Menu search to launch the app
        # This is the most reliable way to launch apps like Word, PowerPoint, etc.
        return self._launch_via_start_menu(name)
    
    def _launch_via_start_menu(self, app_name: str) -> Tuple[bool, str]:
        """Launch an app by searching in Start Menu (most reliable method).
        
        This works for apps like Microsoft Word, PowerPoint, Outlook, etc.
        that don't have simple shell commands.
        """
        try:
            import pyautogui
            import time
            
            # Open Start Menu
            pyautogui.press('win')
            time.sleep(0.5)
            
            # Type the app name to search
            pyautogui.typewrite(app_name, interval=0.03)
            time.sleep(0.8)  # Wait for search results
            
            # Press Enter to launch the first result
            pyautogui.press('enter')
            
            return True, f"Launching {app_name} from Start Menu"
        except ImportError:
            # Fallback without pyautogui
            try:
                import ctypes
                # Press Win key
                ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)
                ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0)
                time.sleep(0.5)
                
                # Type using SendInput (simplified - just open Start)
                return True, f"Start Menu opened. Please type '{app_name}' to search."
            except (OSError, AttributeError) as e:
                return False, f"Could not find application: {app_name} ({e})"
        except Exception as e:
            return False, f"Failed to launch {app_name}: {e}"
    
    def launch_url(self, url: str) -> Tuple[bool, str]:
        """Open a URL in default browser"""
        try:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            os.startfile(url)
            return True, f"Opened {url}"
        except Exception as e:
            return False, f"Failed to open URL: {e}"
    
    def launch_file(self, filepath: str) -> Tuple[bool, str]:
        """Open a file with default application"""
        try:
            os.startfile(filepath)
            return True, f"Opened {filepath}"
        except Exception as e:
            return False, f"Failed to open file: {e}"


class WindowManager:
    """Manage open windows"""
    
    def __init__(self):
        if not HAS_WIN32:
            raise ImportError("pywin32 is required for window management")
    
    def get_open_windows(self) -> List[WindowInfo]:
        """Get list of all open windows"""
        windows = []
        
        def enum_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    try:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        process = psutil.Process(pid)
                        process_name = process.name()
                        
                        rect = win32gui.GetWindowRect(hwnd)
                        placement = win32gui.GetWindowPlacement(hwnd)
                        
                        windows.append(WindowInfo(
                            hwnd=hwnd,
                            title=title,
                            process_name=process_name,
                            pid=pid,
                            is_visible=True,
                            is_minimized=placement[1] == win32con.SW_SHOWMINIMIZED,
                            is_maximized=placement[1] == win32con.SW_SHOWMAXIMIZED,
                            rect=rect
                        ))
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            return True
        
        win32gui.EnumWindows(enum_callback, None)
        return windows
    
    def find_window(self, query: str) -> Optional[WindowInfo]:
        """Find a window by title or process name"""
        query_lower = query.lower().strip()
        windows = self.get_open_windows()
        
        # Common app name mappings
        app_mappings = {
            'chrome': ['chrome', 'google chrome'],
            'edge': ['edge', 'msedge'],
            'firefox': ['firefox', 'mozilla'],
            'notepad': ['notepad'],
            'calculator': ['calculator', 'calc'],
            'vs code': ['code', 'visual studio code'],
            'vscode': ['code', 'visual studio code'],
            'code': ['code', 'visual studio code'],
            'word': ['winword', 'word'],
            'excel': ['excel'],
            'teams': ['teams'],
            'slack': ['slack'],
            'terminal': ['terminal', 'windowsterminal', 'powershell', 'cmd'],
            'explorer': ['explorer'],
        }
        
        # Get search terms
        search_terms = [query_lower]
        if query_lower in app_mappings:
            search_terms.extend(app_mappings[query_lower])
        
        # Exact title match
        for win in windows:
            if query_lower == win.title.lower():
                return win
        
        # Partial title match
        for term in search_terms:
            for win in windows:
                if term in win.title.lower():
                    return win
        
        # Process name match (without .exe)
        for term in search_terms:
            for win in windows:
                proc_name = win.process_name.lower().replace('.exe', '')
                if term in proc_name or proc_name in term:
                    return win
        
        return None
    
    def get_foreground_window(self) -> Optional[WindowInfo]:
        """Get the currently focused window"""
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            windows = self.get_open_windows()
            for win in windows:
                if win.hwnd == hwnd:
                    return win
        return None
    
    def focus_window(self, window: WindowInfo) -> bool:
        """Bring a window to foreground"""
        try:
            if window.is_minimized:
                win32gui.ShowWindow(window.hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(window.hwnd)
            return True
        except Exception:
            return False
    
    def minimize_window(self, window: WindowInfo) -> bool:
        """Minimize a window"""
        try:
            win32gui.ShowWindow(window.hwnd, win32con.SW_MINIMIZE)
            return True
        except Exception:
            return False
    
    def maximize_window(self, window: WindowInfo) -> bool:
        """Maximize a window"""
        try:
            win32gui.ShowWindow(window.hwnd, win32con.SW_MAXIMIZE)
            return True
        except Exception:
            return False
    
    def restore_window(self, window: WindowInfo) -> bool:
        """Restore a window to normal size"""
        try:
            win32gui.ShowWindow(window.hwnd, win32con.SW_RESTORE)
            return True
        except Exception:
            return False
    
    def close_window(self, window: WindowInfo) -> bool:
        """Close a window"""
        try:
            win32gui.PostMessage(window.hwnd, win32con.WM_CLOSE, 0, 0)
            return True
        except Exception:
            return False
    
    def snap_window(self, window: WindowInfo, position: str) -> bool:
        """Snap window to a screen position using Windows shortcuts"""
        try:
            # First focus the window
            self.focus_window(window)
            time.sleep(0.1)
            
            # Use Windows keyboard shortcuts for snapping (most reliable)
            import pyautogui
            
            snap_shortcuts = {
                "left": ['win', 'left'],
                "right": ['win', 'right'],
                "top": ['win', 'up'],  # Maximize
                "bottom": ['win', 'down'],  # Minimize/restore
                "maximize": ['win', 'up'],
                "top_left": None,  # Needs two steps
                "top_right": None,
                "bottom_left": None,
                "bottom_right": None,
                "center": None,
            }
            
            if position in snap_shortcuts and snap_shortcuts[position]:
                pyautogui.hotkey(*snap_shortcuts[position])
                return True
            
            # For corner positions, use manual positioning
            screen_width = win32api.GetSystemMetrics(0)
            screen_height = win32api.GetSystemMetrics(1)
            
            positions = {
                "top_left": (0, 0, screen_width // 2, screen_height // 2),
                "top_right": (screen_width // 2, 0, screen_width, screen_height // 2),
                "bottom_left": (0, screen_height // 2, screen_width // 2, screen_height),
                "bottom_right": (screen_width // 2, screen_height // 2, screen_width, screen_height),
                "center": (screen_width // 4, screen_height // 4, 3 * screen_width // 4, 3 * screen_height // 4),
            }
            
            if position in positions:
                x1, y1, x2, y2 = positions[position]
                
                # Restore first if maximized
                if window.is_maximized:
                    win32gui.ShowWindow(window.hwnd, win32con.SW_RESTORE)
                    time.sleep(0.1)
                
                # Move and resize
                win32gui.MoveWindow(window.hwnd, x1, y1, x2 - x1, y2 - y1, True)
                return True
            
            return False
        except Exception:
            return False
    
    def drag_window(self, window: WindowInfo, x: int, y: int) -> bool:
        """Drag a window to a new position"""
        try:
            # Focus window first
            self.focus_window(window)
            time.sleep(0.1)
            
            # Get current position
            rect = win32gui.GetWindowRect(window.hwnd)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]
            
            # Move to new position
            win32gui.MoveWindow(window.hwnd, x, y, width, height, True)
            return True
        except Exception:
            return False
    
    def drag_window_by(self, window: WindowInfo, dx: int, dy: int) -> bool:
        """Drag a window by a relative offset"""
        try:
            rect = win32gui.GetWindowRect(window.hwnd)
            new_x = rect[0] + dx
            new_y = rect[1] + dy
            return self.drag_window(window, new_x, new_y)
        except Exception:
            return False
    
    def minimize_all(self) -> bool:
        """Minimize all windows (show desktop) using Win+D"""
        try:
            import pyautogui
            pyautogui.hotkey('win', 'd')
            return True
        except Exception:
            return False
    
    def show_desktop(self) -> bool:
        """Show desktop using Win+D shortcut"""
        return self.minimize_all()
    
    def cascade_windows(self) -> bool:
        """Cascade all windows"""
        try:
            ctypes.windll.user32.CascadeWindows(None, 0, None, 0, None)
            return True
        except Exception:
            return False
    
    def tile_windows(self, horizontal: bool = False) -> bool:
        """Tile all windows"""
        try:
            flag = 0 if horizontal else 1  # MDITILE_HORIZONTAL = 0, MDITILE_VERTICAL = 1
            ctypes.windll.user32.TileWindows(None, flag, None, 0, None)
            return True
        except Exception:
            return False


class ProcessManager:
    """Manage system processes"""
    
    def get_running_processes(self) -> List[Dict[str, Any]]:
        """Get list of running processes"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = proc.info
                processes.append({
                    'pid': info['pid'],
                    'name': info['name'],
                    'cpu': info['cpu_percent'] or 0,
                    'memory': info['memory_percent'] or 0
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return sorted(processes, key=lambda x: x['cpu'], reverse=True)
    
    def kill_process(self, name_or_pid: str) -> Tuple[bool, str]:
        """Kill a process by name or PID"""
        try:
            if name_or_pid.isdigit():
                pid = int(name_or_pid)
                proc = psutil.Process(pid)
                proc.terminate()
                return True, f"Killed process {pid}"
            else:
                killed = 0
                for proc in psutil.process_iter(['name']):
                    if name_or_pid.lower() in proc.info['name'].lower():
                        proc.terminate()
                        killed += 1
                if killed > 0:
                    return True, f"Killed {killed} process(es) matching '{name_or_pid}'"
                return False, f"No process found matching '{name_or_pid}'"
        except psutil.NoSuchProcess:
            return False, "Process not found"
        except psutil.AccessDenied:
            return False, "Access denied - try running as administrator"
        except Exception as e:
            return False, f"Error: {e}"
    
    def is_running(self, name: str) -> bool:
        """Check if a process is running"""
        name_lower = name.lower()
        for proc in psutil.process_iter(['name']):
            try:
                if name_lower in proc.info['name'].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False


class AppController:
    """Unified app control interface for VoxMind"""
    
    def __init__(self):
        self.registry = AppRegistry()
        self.launcher = AppLauncher(self.registry)
        self.processes = ProcessManager()
        
        # Window manager requires pywin32
        self._window_manager: Optional[WindowManager] = None
    
    @property
    def windows(self) -> Optional[WindowManager]:
        """Lazy load window manager"""
        if self._window_manager is None and HAS_WIN32:
            self._window_manager = WindowManager()
        return self._window_manager
    
    def open(self, app_name: str, wait: bool = False, timeout: float = 3.0) -> Tuple[bool, str]:
        """Open/launch an application, optionally waiting for window to appear"""
        success, msg = self.launcher.launch(app_name)
        
        if success and wait and self.windows:
            # Wait for window to appear
            start = time.time()
            while time.time() - start < timeout:
                if self.windows.find_window(app_name):
                    return True, msg
                time.sleep(0.2)
        
        return success, msg
    
    def wait_for_window(self, app_name: str, timeout: float = 5.0) -> Tuple[bool, str]:
        """Wait for a window to appear"""
        if not self.windows:
            return False, "Window management not available"
        
        start = time.time()
        while time.time() - start < timeout:
            window = self.windows.find_window(app_name)
            if window:
                return True, f"Window found: {window.title}"
            time.sleep(0.2)
        
        return False, f"Window not found after {timeout}s: {app_name}"
    
    def close(self, app_name: str) -> Tuple[bool, str]:
        """Close an application"""
        if self.windows:
            window = self.windows.find_window(app_name)
            if window:
                if self.windows.close_window(window):
                    return True, f"Closed {window.title}"
        
        # Fallback to process kill
        return self.processes.kill_process(app_name)
    
    def switch_to(self, app_name: str) -> Tuple[bool, str]:
        """Switch to an application window"""
        if not self.windows:
            return False, "Window management not available"
        
        window = self.windows.find_window(app_name)
        if window:
            if self.windows.focus_window(window):
                return True, f"Switched to {window.title}"
            return False, f"Could not focus {window.title}"
        return False, f"Window not found: {app_name}"
    
    def minimize(self, app_name: Optional[str] = None) -> Tuple[bool, str]:
        """Minimize a window or current window"""
        if not self.windows:
            return False, "Window management not available"
        
        if app_name:
            window = self.windows.find_window(app_name)
        else:
            window = self.windows.get_foreground_window()
        
        if window:
            if self.windows.minimize_window(window):
                return True, f"Minimized {window.title}"
            return False, f"Could not minimize {window.title}"
        return False, "Window not found"
    
    def maximize(self, app_name: Optional[str] = None) -> Tuple[bool, str]:
        """Maximize a window or current window"""
        if not self.windows:
            return False, "Window management not available"
        
        if app_name:
            window = self.windows.find_window(app_name)
        else:
            window = self.windows.get_foreground_window()
        
        if window:
            if self.windows.maximize_window(window):
                return True, f"Maximized {window.title}"
            return False, f"Could not maximize {window.title}"
        return False, "Window not found"
    
    def snap(self, position: str, app_name: Optional[str] = None) -> Tuple[bool, str]:
        """Snap a window to a screen position"""
        if not self.windows:
            return False, "Window management not available"
        
        if app_name:
            window = self.windows.find_window(app_name)
        else:
            window = self.windows.get_foreground_window()
        
        if window:
            if self.windows.snap_window(window, position):
                return True, f"Snapped {window.title} to {position}"
            return False, f"Could not snap {window.title}"
        return False, "Window not found"
    
    def show_desktop(self) -> Tuple[bool, str]:
        """Show desktop using Win+D shortcut"""
        if self.windows:
            if self.windows.show_desktop():
                return True, "Showing desktop"
            return False, "Could not show desktop"
        return False, "Window management not available"
    
    def drag_window(self, x: int, y: int, app_name: Optional[str] = None) -> Tuple[bool, str]:
        """Drag a window to a new position"""
        if not self.windows:
            return False, "Window management not available"
        
        if app_name:
            window = self.windows.find_window(app_name)
        else:
            window = self.windows.get_foreground_window()
        
        if window:
            if self.windows.drag_window(window, x, y):
                return True, f"Moved {window.title} to ({x}, {y})"
            return False, f"Could not move {window.title}"
        return False, "Window not found"
    
    def drag_window_by(self, dx: int, dy: int, app_name: Optional[str] = None) -> Tuple[bool, str]:
        """Drag a window by a relative offset"""
        if not self.windows:
            return False, "Window management not available"
        
        if app_name:
            window = self.windows.find_window(app_name)
        else:
            window = self.windows.get_foreground_window()
        
        if window:
            if self.windows.drag_window_by(window, dx, dy):
                return True, f"Moved {window.title} by ({dx}, {dy})"
            return False, f"Could not move {window.title}"
        return False, "Window not found"
    
    def list_windows(self) -> List[str]:
        """List all open windows"""
        if not self.windows:
            return []
        return [w.title for w in self.windows.get_open_windows()]
    
    def search_apps(self, query: str) -> List[str]:
        """Search for installed apps"""
        apps = self.registry.search_apps(query)
        return [app.name for app in apps]
    
    def open_url(self, url: str) -> Tuple[bool, str]:
        """Open a URL"""
        return self.launcher.launch_url(url)
    
    def open_file(self, filepath: str) -> Tuple[bool, str]:
        """Open a file"""
        return self.launcher.launch_file(filepath)


# Singleton instance
_controller: Optional[AppController] = None

def get_app_controller() -> AppController:
    """Get the singleton AppController instance"""
    global _controller
    if _controller is None:
        _controller = AppController()
    return _controller


# Command parsing for voice commands
def parse_app_command(text: str) -> Optional[Dict[str, Any]]:
    """Parse app control commands from voice input"""
    text_lower = text.lower().strip()
    
    # Open/Launch patterns
    open_patterns = [
        r"(?:open|launch|start|run)\s+(.+)",
        r"(?:go to|navigate to)\s+(.+)",
    ]
    for pattern in open_patterns:
        match = re.match(pattern, text_lower)
        if match:
            target = match.group(1).strip()
            # Check if it's a URL
            if any(x in target for x in [".com", ".org", ".net", ".io", "www.", "http"]):
                return {"action": "open_url", "url": target}
            return {"action": "open", "app": target}
    
    # Close patterns
    close_patterns = [
        r"(?:close|exit|quit|kill)\s+(.+)",
        r"(?:shut down|end)\s+(.+)",
    ]
    for pattern in close_patterns:
        match = re.match(pattern, text_lower)
        if match:
            return {"action": "close", "app": match.group(1).strip()}
    
    # Show desktop - check BEFORE switch patterns to avoid "show" matching
    if any(x in text_lower for x in ["show desktop", "minimize all", "hide all windows", "go to desktop"]):
        return {"action": "show_desktop"}
    
    # List windows - check before switch patterns
    if any(x in text_lower for x in ["list windows", "what's open", "open windows", "running apps", "what windows are open"]):
        return {"action": "list_windows"}
    
    # Switch patterns
    switch_patterns = [
        r"(?:switch to|go to|focus|alt tab to)\s+(.+)",
        r"(?:bring up|show)\s+(.+)",
    ]
    for pattern in switch_patterns:
        match = re.match(pattern, text_lower)
        if match:
            return {"action": "switch", "app": match.group(1).strip()}
    
    # Minimize patterns
    if re.match(r"minimize\s+(.+)", text_lower):
        match = re.match(r"minimize\s+(.+)", text_lower)
        return {"action": "minimize", "app": match.group(1).strip()}
    if text_lower in ["minimize", "minimize window", "minimize this"]:
        return {"action": "minimize", "app": None}
    
    # Maximize patterns
    if re.match(r"maximize\s+(.+)", text_lower):
        match = re.match(r"maximize\s+(.+)", text_lower)
        return {"action": "maximize", "app": match.group(1).strip()}
    if text_lower in ["maximize", "maximize window", "maximize this"]:
        return {"action": "maximize", "app": None}
    
    # Snap patterns - check longer phrases first (corners before edges)
    snap_positions = [
        ("snap top left", "top_left"),
        ("snap top right", "top_right"),
        ("snap bottom left", "bottom_left"),
        ("snap bottom right", "bottom_right"),
        ("snap left", "left"),
        ("snap right", "right"),
        ("snap top", "top"),
        ("snap bottom", "bottom"),
        ("snap center", "center"),
        ("move to left", "left"),
        ("move to right", "right"),
    ]
    for phrase, position in snap_positions:
        if phrase in text_lower:
            return {"action": "snap", "position": position, "app": None}
    
    # Drag window patterns
    drag_patterns = [
        r"(?:drag|move) (?:window )?(?:to )?\(?(\d+)[,\s]+(\d+)\)?",
        r"(?:drag|move) (?:window )?(\d+) pixels? (left|right|up|down)",
        r"(?:drag|move) (?:window )?(left|right|up|down)(?: (\d+))?",
    ]
    for pattern in drag_patterns:
        match = re.match(pattern, text_lower)
        if match:
            groups = match.groups()
            # Absolute position: drag to 100, 200
            if len(groups) >= 2 and groups[0].isdigit() and groups[1].isdigit():
                return {"action": "drag", "x": int(groups[0]), "y": int(groups[1]), "app": None}
            # Relative with pixels: drag 100 pixels left
            if len(groups) >= 2 and groups[0].isdigit():
                amount = int(groups[0])
                direction = groups[1]
                dx = -amount if direction == 'left' else (amount if direction == 'right' else 0)
                dy = -amount if direction == 'up' else (amount if direction == 'down' else 0)
                return {"action": "drag_by", "dx": dx, "dy": dy, "app": None}
            # Direction only: drag left
            if groups[0] in ('left', 'right', 'up', 'down'):
                direction = groups[0]
                amount = int(groups[1]) if len(groups) > 1 and groups[1] else 100
                dx = -amount if direction == 'left' else (amount if direction == 'right' else 0)
                dy = -amount if direction == 'up' else (amount if direction == 'down' else 0)
                return {"action": "drag_by", "dx": dx, "dy": dy, "app": None}
    
    # Search apps
    search_match = re.match(r"(?:search|find) (?:app|apps|application)\s*(.+)?", text_lower)
    if search_match:
        query = search_match.group(1) or ""
        return {"action": "search", "query": query.strip()}
    
    return None


if __name__ == "__main__":
    # Demo
    print("=" * 60)
    print("VoxMind App Control Module")
    print("=" * 60)
    
    controller = get_app_controller()
    
    print("\n[Installed Apps Sample]")
    for i, name in enumerate(list(controller.registry.apps.keys())[:20]):
        print(f"  {i+1}. {controller.registry.apps[name].name}")
    print(f"  ... and {len(controller.registry.apps) - 20} more")
    
    if controller.windows:
        print("\n[Open Windows]")
        for win in controller.windows.get_open_windows()[:10]:
            status = "📌" if win.is_maximized else ("📉" if win.is_minimized else "📄")
            print(f"  {status} {win.title[:50]} ({win.process_name})")
    
    print("\n[Command Examples]")
    examples = [
        "open chrome",
        "close notepad",
        "switch to vs code",
        "minimize",
        "snap left",
        "show desktop",
        "list windows",
    ]
    for cmd in examples:
        result = parse_app_command(cmd)
        print(f"  '{cmd}' -> {result}")
