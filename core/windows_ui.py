"""
VoxMind Windows UI Automation Module
=====================================
Provides voice-controlled access to Windows shell elements:
- Taskbar (click app icons, system tray)
- Start Menu (open, search)
- Desktop icons
- Window controls

Uses Windows UI Automation API for reliable interaction.
"""

import ctypes
import time
import subprocess
import logging
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Windows API constants
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
VK_LWIN = 0x5B
VK_TAB = 0x09
VK_ESCAPE = 0x1B
VK_RETURN = 0x0D
KEYEVENTF_KEYUP = 0x0002

# Try to import pyautogui
try:
    import pyautogui
    pyautogui.FAILSAFE = True
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

# Try to import win32 APIs
try:
    import win32gui
    import win32con
    import win32api
    import win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

# Try to import UI Automation
try:
    import comtypes
    from comtypes import client
    from comtypes.automation import VARIANT
    UIAutomationCore = client.GetModule("UIAutomationCore.dll")
    HAS_UIAUTOMATION = True
except (ImportError, OSError, AttributeError) as e:
    HAS_UIAUTOMATION = False
    logger.info(f"UI Automation not available ({e}), using fallback methods")


@dataclass
class UIElement:
    """Represents a UI element on screen"""
    name: str
    control_type: str
    bounding_box: Tuple[int, int, int, int]  # left, top, right, bottom
    automation_id: str = ""
    class_name: str = ""
    is_enabled: bool = True
    
    @property
    def center(self) -> Tuple[int, int]:
        """Get center point of element"""
        left, top, right, bottom = self.bounding_box
        return ((left + right) // 2, (top + bottom) // 2)
    
    @property
    def width(self) -> int:
        return self.bounding_box[2] - self.bounding_box[0]
    
    @property
    def height(self) -> int:
        return self.bounding_box[3] - self.bounding_box[1]


class TaskbarPosition(Enum):
    BOTTOM = "bottom"
    TOP = "top"
    LEFT = "left"
    RIGHT = "right"


class WindowsUIController:
    """
    Controls Windows UI elements through various methods:
    1. Keyboard shortcuts (most reliable)
    2. pyautogui clicks (visual)
    3. UI Automation API (programmatic)
    """
    
    def __init__(self):
        self.screen_width, self.screen_height = self._get_screen_size()
        self.taskbar_position = self._detect_taskbar_position()
        self._cached_taskbar_apps: List[UIElement] = []
        self._cache_time = 0
    
    def _get_screen_size(self) -> Tuple[int, int]:
        """Get primary screen dimensions"""
        if PYAUTOGUI_AVAILABLE:
            return pyautogui.size()
        try:
            user32 = ctypes.windll.user32
            return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        except (OSError, AttributeError) as e:
            logger.debug(f"Could not get screen size via ctypes: {e}")
            return 1920, 1080
    
    def _detect_taskbar_position(self) -> TaskbarPosition:
        """Detect where the taskbar is located"""
        if not HAS_WIN32:
            return TaskbarPosition.BOTTOM
        
        try:
            taskbar = win32gui.FindWindow("Shell_TrayWnd", None)
            if taskbar:
                rect = win32gui.GetWindowRect(taskbar)
                left, top, right, bottom = rect
                width = right - left
                height = bottom - top
                
                # Determine position based on dimensions and location
                if height < width:
                    if top < self.screen_height // 2:
                        return TaskbarPosition.TOP
                    return TaskbarPosition.BOTTOM
                else:
                    if left < self.screen_width // 2:
                        return TaskbarPosition.LEFT
                    return TaskbarPosition.RIGHT
        except (OSError, AttributeError) as e:
            logger.debug(f"Could not detect taskbar position: {e}")
        return TaskbarPosition.BOTTOM
    
    def _get_taskbar_rect(self) -> Tuple[int, int, int, int]:
        """Get taskbar bounding rectangle"""
        if HAS_WIN32:
            try:
                taskbar = win32gui.FindWindow("Shell_TrayWnd", None)
                if taskbar:
                    return win32gui.GetWindowRect(taskbar)
            except (OSError, AttributeError) as e:
                logger.debug(f"Could not get taskbar rect: {e}")
        
        # Default for bottom taskbar
        return (0, self.screen_height - 48, self.screen_width, self.screen_height)
    
    # =========================================================================
    # START MENU
    # =========================================================================
    
    def open_start_menu(self) -> Tuple[bool, str]:
        """Open the Windows Start Menu"""
        try:
            # Method 1: Windows key (most reliable)
            if PYAUTOGUI_AVAILABLE:
                pyautogui.press('win')
                time.sleep(0.3)
                return True, "Start menu opened"
            
            # Method 2: Click Start button
            return self.click_start_button()
        except Exception as e:
            return False, f"Failed to open Start menu: {e}"
    
    def close_start_menu(self) -> Tuple[bool, str]:
        """Close the Start Menu if open"""
        try:
            if PYAUTOGUI_AVAILABLE:
                pyautogui.press('escape')
                return True, "Start menu closed"
            return False, "pyautogui not available"
        except Exception as e:
            return False, f"Failed to close Start menu: {e}"
    
    def click_start_button(self) -> Tuple[bool, str]:
        """Click the Start button directly"""
        try:
            # Get Start button position based on taskbar location
            if self.taskbar_position == TaskbarPosition.BOTTOM:
                x, y = 24, self.screen_height - 24
            elif self.taskbar_position == TaskbarPosition.TOP:
                x, y = 24, 24
            elif self.taskbar_position == TaskbarPosition.LEFT:
                x, y = 24, 24
            else:  # RIGHT
                x, y = self.screen_width - 24, 24
            
            if PYAUTOGUI_AVAILABLE:
                pyautogui.click(x, y)
                time.sleep(0.2)
                return True, "Clicked Start button"
            
            return False, "pyautogui not available"
        except Exception as e:
            return False, f"Failed to click Start button: {e}"
    
    def search_start_menu(self, query: str) -> Tuple[bool, str]:
        """Open Start menu and search"""
        try:
            # Open start menu
            if PYAUTOGUI_AVAILABLE:
                pyautogui.press('win')
                time.sleep(0.4)
                # Type search query
                pyautogui.typewrite(query, interval=0.05)
                time.sleep(0.3)
                return True, f"Searching for '{query}' in Start menu"
            return False, "pyautogui not available"
        except Exception as e:
            return False, f"Failed to search Start menu: {e}"
    
    def run_from_start(self, query: str, press_enter: bool = True) -> Tuple[bool, str]:
        """Search in Start menu and run the result"""
        success, msg = self.search_start_menu(query)
        if success and press_enter:
            time.sleep(0.5)
            if PYAUTOGUI_AVAILABLE:
                pyautogui.press('enter')
                return True, f"Launched '{query}' from Start menu"
        return success, msg
    
    # =========================================================================
    # TASKBAR
    # =========================================================================
    
    def get_taskbar_apps(self) -> List[UIElement]:
        """Get list of apps pinned/running on taskbar"""
        apps = []
        
        # Try UI Automation first
        if HAS_UIAUTOMATION:
            try:
                apps = self._get_taskbar_apps_uia()
                if apps:
                    return apps
            except Exception as e:
                logger.debug(f"UI Automation taskbar query failed: {e}")
        
        # Fallback: estimate positions for common Windows 11 layout
        taskbar_rect = self._get_taskbar_rect()
        left, top, right, bottom = taskbar_rect
        
        # Windows 11 centered taskbar starts around screen center
        if self.taskbar_position == TaskbarPosition.BOTTOM:
            # Start button is at ~24px from left edge
            # Search is next
            # Apps start after that
            app_start_x = self.screen_width // 2 - 200
            icon_width = 44
            icon_height = 44
            icon_y = top + (bottom - top - icon_height) // 2
            
            # Add estimated app positions
            for i in range(10):
                x = app_start_x + i * (icon_width + 4)
                apps.append(UIElement(
                    name=f"Taskbar App {i+1}",
                    control_type="Button",
                    bounding_box=(x, icon_y, x + icon_width, icon_y + icon_height),
                    automation_id=f"taskbar_app_{i}"
                ))
        
        return apps
    
    def _get_taskbar_apps_uia(self) -> List[UIElement]:
        """Get taskbar apps using UI Automation"""
        apps = []
        # This would use the UI Automation API
        # Simplified implementation
        return apps
    
    def click_taskbar_app(self, index: int = None, name: str = None) -> Tuple[bool, str]:
        """Click an app on the taskbar by index (1-based) or name"""
        try:
            if index is not None:
                apps = self.get_taskbar_apps()
                if 1 <= index <= len(apps):
                    app = apps[index - 1]
                    x, y = app.center
                    if PYAUTOGUI_AVAILABLE:
                        pyautogui.click(x, y)
                        return True, f"Clicked taskbar app {index}"
                return False, f"Invalid taskbar app index: {index}"
            
            if name:
                # Try to find by name (would need UI Automation for real names)
                # For now, open the app by name
                return self.run_from_start(name)
            
            return False, "Specify index or name"
        except Exception as e:
            return False, f"Failed to click taskbar app: {e}"
    
    def show_taskbar(self) -> Tuple[bool, str]:
        """Show the taskbar (if auto-hidden)"""
        try:
            taskbar_rect = self._get_taskbar_rect()
            x = taskbar_rect[0] + (taskbar_rect[2] - taskbar_rect[0]) // 2
            
            if self.taskbar_position == TaskbarPosition.BOTTOM:
                y = self.screen_height - 1
            elif self.taskbar_position == TaskbarPosition.TOP:
                y = 1
            elif self.taskbar_position == TaskbarPosition.LEFT:
                x = 1
                y = self.screen_height // 2
            else:
                x = self.screen_width - 1
                y = self.screen_height // 2
            
            if PYAUTOGUI_AVAILABLE:
                pyautogui.moveTo(x, y)
                time.sleep(0.3)
                return True, "Taskbar shown"
            return False, "pyautogui not available"
        except Exception as e:
            return False, f"Failed to show taskbar: {e}"
    
    def click_system_tray(self, item: str = None) -> Tuple[bool, str]:
        """Click in the system tray area"""
        try:
            taskbar_rect = self._get_taskbar_rect()
            
            if self.taskbar_position == TaskbarPosition.BOTTOM:
                # System tray is on the right side of taskbar
                x = taskbar_rect[2] - 100
                y = (taskbar_rect[1] + taskbar_rect[3]) // 2
            else:
                x = (taskbar_rect[0] + taskbar_rect[2]) // 2
                y = taskbar_rect[3] - 100
            
            if PYAUTOGUI_AVAILABLE:
                pyautogui.click(x, y)
                return True, "Clicked system tray"
            return False, "pyautogui not available"
        except Exception as e:
            return False, f"Failed to click system tray: {e}"
    
    def click_notification_center(self) -> Tuple[bool, str]:
        """Open notification center / action center"""
        try:
            if PYAUTOGUI_AVAILABLE:
                # Windows + N for notification center (Windows 11)
                pyautogui.hotkey('win', 'n')
                return True, "Opened notification center"
            return False, "pyautogui not available"
        except Exception as e:
            return False, f"Failed to open notification center: {e}"
    
    def click_quick_settings(self) -> Tuple[bool, str]:
        """Open quick settings (WiFi, Bluetooth, etc.)"""
        try:
            if PYAUTOGUI_AVAILABLE:
                # Windows + A for quick settings (Windows 11)
                pyautogui.hotkey('win', 'a')
                return True, "Opened quick settings"
            return False, "pyautogui not available"
        except Exception as e:
            return False, f"Failed to open quick settings: {e}"
    
    def click_date_time(self) -> Tuple[bool, str]:
        """Click the date/time in taskbar to show calendar"""
        try:
            taskbar_rect = self._get_taskbar_rect()
            
            if self.taskbar_position == TaskbarPosition.BOTTOM:
                # Date/time is near the right side
                x = taskbar_rect[2] - 60
                y = (taskbar_rect[1] + taskbar_rect[3]) // 2
            else:
                x = (taskbar_rect[0] + taskbar_rect[2]) // 2
                y = taskbar_rect[3] - 30
            
            if PYAUTOGUI_AVAILABLE:
                pyautogui.click(x, y)
                return True, "Clicked date/time"
            return False, "pyautogui not available"
        except Exception as e:
            return False, f"Failed to click date/time: {e}"
    
    # =========================================================================
    # DESKTOP ICONS
    # =========================================================================
    
    def show_desktop(self) -> Tuple[bool, str]:
        """Show the desktop (minimize all windows)"""
        try:
            if PYAUTOGUI_AVAILABLE:
                pyautogui.hotkey('win', 'd')
                return True, "Showing desktop"
            return False, "pyautogui not available"
        except Exception as e:
            return False, f"Failed to show desktop: {e}"
    
    def click_desktop_icon(self, name: str) -> Tuple[bool, str]:
        """Click a desktop icon by name"""
        try:
            # First, show desktop
            self.show_desktop()
            time.sleep(0.3)
            
            # Focus on desktop
            if HAS_WIN32:
                desktop = win32gui.FindWindow("Progman", None)
                if not desktop:
                    desktop = win32gui.FindWindow("WorkerW", None)
                if desktop:
                    win32gui.SetForegroundWindow(desktop)
            
            # Use keyboard to find icon
            if PYAUTOGUI_AVAILABLE:
                # Type the first letter(s) to jump to icon
                first_letter = name[0].lower()
                pyautogui.press(first_letter)
                time.sleep(0.1)
                pyautogui.press('enter')
                return True, f"Activated desktop icon starting with '{first_letter}'"
            
            return False, "Could not click desktop icon"
        except Exception as e:
            return False, f"Failed to click desktop icon: {e}"
    
    def get_desktop_icons(self) -> List[UIElement]:
        """Get list of desktop icons"""
        icons = []
        
        # This would use UI Automation or shell COM objects
        # Simplified: return empty list for now
        
        return icons
    
    # =========================================================================
    # WINDOW MANAGEMENT SHORTCUTS
    # =========================================================================
    
    def task_view(self) -> Tuple[bool, str]:
        """Open Task View (Windows + Tab)"""
        try:
            if PYAUTOGUI_AVAILABLE:
                pyautogui.hotkey('win', 'tab')
                return True, "Opened Task View"
            return False, "pyautogui not available"
        except Exception as e:
            return False, f"Failed to open Task View: {e}"
    
    def switch_window(self) -> Tuple[bool, str]:
        """Switch to next window (Alt + Tab)"""
        try:
            if PYAUTOGUI_AVAILABLE:
                pyautogui.hotkey('alt', 'tab')
                return True, "Switched window"
            return False, "pyautogui not available"
        except Exception as e:
            return False, f"Failed to switch window: {e}"
    
    def snap_window(self, direction: str) -> Tuple[bool, str]:
        """Snap current window to a position"""
        try:
            if not PYAUTOGUI_AVAILABLE:
                return False, "pyautogui not available"
            
            direction = direction.lower()
            
            if direction in ['left', 'l']:
                pyautogui.hotkey('win', 'left')
            elif direction in ['right', 'r']:
                pyautogui.hotkey('win', 'right')
            elif direction in ['up', 'top', 'maximize']:
                pyautogui.hotkey('win', 'up')
            elif direction in ['down', 'bottom', 'minimize']:
                pyautogui.hotkey('win', 'down')
            elif direction in ['top-left', 'topleft', 'tl']:
                pyautogui.hotkey('win', 'left')
                time.sleep(0.1)
                pyautogui.hotkey('win', 'up')
            elif direction in ['top-right', 'topright', 'tr']:
                pyautogui.hotkey('win', 'right')
                time.sleep(0.1)
                pyautogui.hotkey('win', 'up')
            elif direction in ['bottom-left', 'bottomleft', 'bl']:
                pyautogui.hotkey('win', 'left')
                time.sleep(0.1)
                pyautogui.hotkey('win', 'down')
            elif direction in ['bottom-right', 'bottomright', 'br']:
                pyautogui.hotkey('win', 'right')
                time.sleep(0.1)
                pyautogui.hotkey('win', 'down')
            else:
                return False, f"Unknown snap direction: {direction}"
            
            return True, f"Snapped window {direction}"
        except Exception as e:
            return False, f"Failed to snap window: {e}"
    
    def close_window(self) -> Tuple[bool, str]:
        """Close current window (Alt + F4)"""
        try:
            if PYAUTOGUI_AVAILABLE:
                pyautogui.hotkey('alt', 'F4')
                return True, "Closed window"
            return False, "pyautogui not available"
        except Exception as e:
            return False, f"Failed to close window: {e}"
    
    def minimize_window(self) -> Tuple[bool, str]:
        """Minimize current window"""
        try:
            if PYAUTOGUI_AVAILABLE:
                pyautogui.hotkey('win', 'down')
                return True, "Minimized window"
            return False, "pyautogui not available"
        except Exception as e:
            return False, f"Failed to minimize window: {e}"
    
    def maximize_window(self) -> Tuple[bool, str]:
        """Maximize current window"""
        try:
            if PYAUTOGUI_AVAILABLE:
                pyautogui.hotkey('win', 'up')
                return True, "Maximized window"
            return False, "pyautogui not available"
        except Exception as e:
            return False, f"Failed to maximize window: {e}"
    
    def restore_window(self) -> Tuple[bool, str]:
        """Restore current window from minimized/maximized state"""
        try:
            if HAS_WIN32:
                hwnd = win32gui.GetForegroundWindow()
                if hwnd:
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    return True, "Restored window"
            if PYAUTOGUI_AVAILABLE:
                # Win + Down from maximized goes to normal, then minimizes
                # So we press Win + Up first to ensure it's maximized, then do nothing more
                # Actually, just restore via keypress
                pyautogui.hotkey('win', 'down')  # If maximized, this restores
                return True, "Restored window"
            return False, "No restore method available"
        except Exception as e:
            return False, f"Failed to restore window: {e}"
    
    # =========================================================================
    # RUN DIALOG & SHORTCUTS
    # =========================================================================
    
    def open_run_dialog(self) -> Tuple[bool, str]:
        """Open Windows Run dialog (Win + R)"""
        try:
            if PYAUTOGUI_AVAILABLE:
                pyautogui.hotkey('win', 'r')
                return True, "Opened Run dialog"
            return False, "pyautogui not available"
        except Exception as e:
            return False, f"Failed to open Run dialog: {e}"
    
    def run_command(self, command: str) -> Tuple[bool, str]:
        """Open Run dialog and execute command"""
        try:
            success, msg = self.open_run_dialog()
            if success:
                time.sleep(0.3)
                if PYAUTOGUI_AVAILABLE:
                    pyautogui.typewrite(command, interval=0.02)
                    time.sleep(0.1)
                    pyautogui.press('enter')
                    return True, f"Executed: {command}"
            return False, msg
        except Exception as e:
            return False, f"Failed to run command: {e}"
    
    def open_file_explorer(self) -> Tuple[bool, str]:
        """Open File Explorer (Win + E)"""
        try:
            if PYAUTOGUI_AVAILABLE:
                pyautogui.hotkey('win', 'e')
                return True, "Opened File Explorer"
            return False, "pyautogui not available"
        except Exception as e:
            return False, f"Failed to open File Explorer: {e}"
    
    def open_settings(self) -> Tuple[bool, str]:
        """Open Windows Settings (Win + I)"""
        try:
            if PYAUTOGUI_AVAILABLE:
                pyautogui.hotkey('win', 'i')
                return True, "Opened Settings"
            return False, "pyautogui not available"
        except Exception as e:
            return False, f"Failed to open Settings: {e}"
    
    def lock_screen(self) -> Tuple[bool, str]:
        """Lock the screen (Win + L)"""
        try:
            if PYAUTOGUI_AVAILABLE:
                pyautogui.hotkey('win', 'l')
                return True, "Screen locked"
            return False, "pyautogui not available"
        except Exception as e:
            return False, f"Failed to lock screen: {e}"
    
    def open_clipboard_history(self) -> Tuple[bool, str]:
        """Open clipboard history (Win + V)"""
        try:
            if PYAUTOGUI_AVAILABLE:
                pyautogui.hotkey('win', 'v')
                return True, "Opened clipboard history"
            return False, "pyautogui not available"
        except Exception as e:
            return False, f"Failed to open clipboard history: {e}"
    
    def take_screenshot(self, mode: str = "full") -> Tuple[bool, str]:
        """Take a screenshot"""
        try:
            if not PYAUTOGUI_AVAILABLE:
                return False, "pyautogui not available"
            
            if mode == "full":
                pyautogui.hotkey('win', 'printscreen')
                return True, "Full screenshot saved to Pictures/Screenshots"
            elif mode == "snip":
                pyautogui.hotkey('win', 'shift', 's')
                return True, "Snipping tool opened"
            elif mode == "window":
                pyautogui.hotkey('alt', 'printscreen')
                return True, "Window screenshot copied to clipboard"
            else:
                return False, f"Unknown screenshot mode: {mode}"
        except Exception as e:
            return False, f"Failed to take screenshot: {e}"
    
    def emoji_picker(self) -> Tuple[bool, str]:
        """Open emoji picker (Win + .)"""
        try:
            if PYAUTOGUI_AVAILABLE:
                pyautogui.hotkey('win', '.')
                return True, "Opened emoji picker"
            return False, "pyautogui not available"
        except Exception as e:
            return False, f"Failed to open emoji picker: {e}"
    
    # =========================================================================
    # ACTIVE WINDOW MANAGEMENT
    # =========================================================================
    
    def get_active_windows(self) -> List[Dict[str, Any]]:
        """
        Get list of active/visible windows (excludes background processes).
        Returns list of dicts with 'hwnd', 'title', 'process_name', 'is_foreground'.
        """
        windows = []
        try:
            if not HAS_WIN32:
                return windows
            
            import psutil
            
            foreground_hwnd = win32gui.GetForegroundWindow()
            
            def enum_callback(hwnd, results):
                if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title and len(title.strip()) > 0:
                        # Get window rect
                        try:
                            rect = win32gui.GetWindowRect(hwnd)
                            width = rect[2] - rect[0]
                            height = rect[3] - rect[1]
                            # Filter out tiny windows (background/invisible)
                            if width > 100 and height > 50:
                                # Get process info
                                try:
                                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                                    proc = psutil.Process(pid)
                                    proc_name = proc.name()
                                except (OSError, psutil.NoSuchProcess, psutil.AccessDenied) as e:
                                    logger.debug(f"Could not get process name for hwnd {hwnd}: {e}")
                                    proc_name = "Unknown"
                                
                                # Skip system background windows
                                skip_processes = ['ApplicationFrameHost.exe', 'TextInputHost.exe',
                                                  'ShellExperienceHost.exe', 'SearchHost.exe',
                                                  'LockApp.exe', 'SystemSettings.exe']
                                skip_titles = ['Program Manager', 'Windows Input Experience',
                                              'Microsoft Text Input Application']
                                
                                if proc_name not in skip_processes and title not in skip_titles:
                                    results.append({
                                        'hwnd': hwnd,
                                        'title': title,
                                        'process_name': proc_name,
                                        'is_foreground': hwnd == foreground_hwnd,
                                        'rect': rect
                                    })
                        except (OSError, AttributeError) as e:
                            logger.debug(f"Error processing window {hwnd}: {e}")
                return True
            
            win32gui.EnumWindows(enum_callback, windows)
            
            # Sort: foreground first, then by Z-order (approximated by enum order)
            windows.sort(key=lambda w: (not w['is_foreground'], 0))
            
        except Exception as e:
            print(f"Error getting active windows: {e}")
        
        return windows
    
    def list_active_apps(self) -> Tuple[bool, str]:
        """List all active/visible applications."""
        try:
            windows = self.get_active_windows()
            if not windows:
                return True, "No active windows found"
            
            app_list = []
            for i, w in enumerate(windows, 1):
                status = " (active)" if w['is_foreground'] else ""
                app_list.append(f"{i}. {w['title']}{status}")
            
            result = "Active apps:\n" + "\n".join(app_list)
            return True, result
        except Exception as e:
            return False, f"Failed to list apps: {e}"
    
    def focus_window(self, identifier: str) -> Tuple[bool, str]:
        """
        Focus/activate a window by name or number.
        identifier can be a number (1, 2, 3) or partial window title.
        """
        try:
            if not HAS_WIN32:
                return False, "win32gui not available"
            
            windows = self.get_active_windows()
            if not windows:
                return False, "No active windows found"
            
            target_hwnd = None
            target_title = ""
            
            # Try as number first
            try:
                idx = int(identifier) - 1  # 1-based to 0-based
                if 0 <= idx < len(windows):
                    target_hwnd = windows[idx]['hwnd']
                    target_title = windows[idx]['title']
            except ValueError:
                # Search by name
                identifier_lower = identifier.lower()
                for w in windows:
                    if identifier_lower in w['title'].lower() or identifier_lower in w['process_name'].lower():
                        target_hwnd = w['hwnd']
                        target_title = w['title']
                        break
            
            if target_hwnd:
                # Restore if minimized
                import win32con
                placement = win32gui.GetWindowPlacement(target_hwnd)
                if placement[1] == win32con.SW_SHOWMINIMIZED:
                    win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
                
                # Bring to foreground
                win32gui.SetForegroundWindow(target_hwnd)
                return True, f"Focused: {target_title}"
            
            return False, f"Could not find window: {identifier}"
        except Exception as e:
            return False, f"Failed to focus window: {e}"
    
    def previous_window(self) -> Tuple[bool, str]:
        """Switch to previous window (Alt+Tab)."""
        try:
            if PYAUTOGUI_AVAILABLE:
                pyautogui.hotkey('alt', 'tab')
                time.sleep(0.1)
                return True, "Switched to previous window"
            return False, "pyautogui not available"
        except Exception as e:
            return False, f"Failed to switch window: {e}"
    
    def next_window(self) -> Tuple[bool, str]:
        """Switch to next window (Alt+Shift+Tab or cycle forward)."""
        try:
            if PYAUTOGUI_AVAILABLE:
                pyautogui.hotkey('alt', 'tab')
                return True, "Switched to next window"
            return False, "pyautogui not available"
        except Exception as e:
            return False, f"Failed to switch window: {e}"
    
    def switch_between_windows(self) -> Tuple[bool, str]:
        """Quick switch between last two windows."""
        try:
            if PYAUTOGUI_AVAILABLE:
                pyautogui.hotkey('alt', 'tab')
                return True, "Switched windows"
            return False, "pyautogui not available"
        except Exception as e:
            return False, f"Failed to switch: {e}"
    
    def split_screen(self, layout: str = "half") -> Tuple[bool, str]:
        """
        Split screen with current and previous window.
        layout: 'half' (50/50), 'left', 'right', 'vertical', 'horizontal'
        """
        try:
            if not HAS_WIN32 or not PYAUTOGUI_AVAILABLE:
                return False, "Required modules not available"
            
            windows = self.get_active_windows()
            if len(windows) < 2:
                return False, "Need at least 2 windows for split screen"
            
            # Get current and previous window
            current_hwnd = windows[0]['hwnd']
            prev_hwnd = windows[1]['hwnd']
            
            if layout in ('half', 'left', 'horizontal'):
                # Snap current to left
                win32gui.SetForegroundWindow(current_hwnd)
                time.sleep(0.1)
                pyautogui.hotkey('win', 'left')
                time.sleep(0.3)
                
                # Snap previous to right
                win32gui.SetForegroundWindow(prev_hwnd)
                time.sleep(0.1)
                pyautogui.hotkey('win', 'right')
                
                return True, f"Split screen: {windows[0]['title'][:30]} | {windows[1]['title'][:30]}"
            
            elif layout == 'right':
                # Current on right, previous on left
                win32gui.SetForegroundWindow(prev_hwnd)
                time.sleep(0.1)
                pyautogui.hotkey('win', 'left')
                time.sleep(0.3)
                
                win32gui.SetForegroundWindow(current_hwnd)
                time.sleep(0.1)
                pyautogui.hotkey('win', 'right')
                
                return True, f"Split screen: {windows[1]['title'][:30]} | {windows[0]['title'][:30]}"
            
            elif layout == 'vertical':
                # Top and bottom split (Win 11 feature)
                win32gui.SetForegroundWindow(current_hwnd)
                time.sleep(0.1)
                pyautogui.hotkey('win', 'up')
                time.sleep(0.3)
                
                win32gui.SetForegroundWindow(prev_hwnd)
                time.sleep(0.1)
                pyautogui.hotkey('win', 'down')
                
                return True, "Split screen vertically"
            
            return False, f"Unknown layout: {layout}"
        except Exception as e:
            return False, f"Failed to split screen: {e}"
    
    def snap_app(self, app_name: str, direction: str = "left") -> Tuple[bool, str]:
        """
        Snap a specific app/window to a direction.
        app_name: partial name of the app/window to snap
        direction: 'left', 'right', 'top', 'bottom'
        """
        try:
            if not HAS_WIN32 or not PYAUTOGUI_AVAILABLE:
                return False, "Required modules not available"
            
            # Find the window by name
            windows = self.get_active_windows()
            target_hwnd = None
            target_title = None
            
            app_name_lower = app_name.lower()
            for w in windows:
                if app_name_lower in w['title'].lower() or app_name_lower in w.get('app', '').lower():
                    target_hwnd = w['hwnd']
                    target_title = w['title']
                    break
            
            if not target_hwnd:
                return False, f"Could not find window matching '{app_name}'"
            
            # Focus and snap
            win32gui.SetForegroundWindow(target_hwnd)
            time.sleep(0.15)
            
            direction_map = {
                'left': 'left',
                'right': 'right',
                'top': 'up',
                'bottom': 'down',
                'up': 'up',
                'down': 'down'
            }
            key = direction_map.get(direction.lower(), 'left')
            pyautogui.hotkey('win', key)
            
            return True, f"Snapped {target_title[:30]} to {direction}"
        except Exception as e:
            return False, f"Failed to snap app: {e}"
    
    def snap_apps_together(self, app1: str, app2: str) -> Tuple[bool, str]:
        """
        Snap two apps side by side (app1 on left, app2 on right).
        app1: partial name of first app (left side)
        app2: partial name of second app (right side)
        """
        try:
            if not HAS_WIN32 or not PYAUTOGUI_AVAILABLE:
                return False, "Required modules not available"
            
            windows = self.get_active_windows()
            
            # Find both windows
            hwnd1, title1 = None, None
            hwnd2, title2 = None, None
            
            app1_lower = app1.lower()
            app2_lower = app2.lower()
            
            for w in windows:
                title_lower = w['title'].lower()
                app_lower = w.get('app', '').lower()
                
                if not hwnd1 and (app1_lower in title_lower or app1_lower in app_lower):
                    hwnd1, title1 = w['hwnd'], w['title']
                elif not hwnd2 and (app2_lower in title_lower or app2_lower in app_lower):
                    hwnd2, title2 = w['hwnd'], w['title']
                
                if hwnd1 and hwnd2:
                    break
            
            if not hwnd1:
                return False, f"Could not find window matching '{app1}'"
            if not hwnd2:
                return False, f"Could not find window matching '{app2}'"
            
            # Snap app1 to left
            win32gui.SetForegroundWindow(hwnd1)
            time.sleep(0.15)
            pyautogui.hotkey('win', 'left')
            time.sleep(0.3)
            
            # Snap app2 to right
            win32gui.SetForegroundWindow(hwnd2)
            time.sleep(0.15)
            pyautogui.hotkey('win', 'right')
            
            return True, f"Snapped: {title1[:25]} | {title2[:25]}"
        except Exception as e:
            return False, f"Failed to snap apps together: {e}"
    
    # Mapping of spoken app names to window title search terms and process names
    APP_NAME_MAP = {
        'word': {'search': ['word', 'document'], 'process': 'WINWORD.EXE'},
        'microsoft word': {'search': ['word', 'document'], 'process': 'WINWORD.EXE'},
        'excel': {'search': ['excel', 'workbook'], 'process': 'EXCEL.EXE'},
        'microsoft excel': {'search': ['excel', 'workbook'], 'process': 'EXCEL.EXE'},
        'powerpoint': {'search': ['powerpoint', 'presentation', 'slide'], 'process': 'POWERPNT.EXE'},
        'microsoft powerpoint': {'search': ['powerpoint', 'presentation', 'slide'], 'process': 'POWERPNT.EXE'},
        'outlook': {'search': ['outlook', 'mail', 'inbox'], 'process': 'OUTLOOK.EXE'},
        'microsoft outlook': {'search': ['outlook', 'mail', 'inbox'], 'process': 'OUTLOOK.EXE'},
        'onenote': {'search': ['onenote', 'one note'], 'process': 'ONENOTE.EXE'},
        'microsoft onenote': {'search': ['onenote', 'one note'], 'process': 'ONENOTE.EXE'},
        'chrome': {'search': ['chrome', 'google chrome'], 'process': 'chrome.exe'},
        'google chrome': {'search': ['chrome', 'google chrome'], 'process': 'chrome.exe'},
        'edge': {'search': ['edge', 'microsoft edge'], 'process': 'msedge.exe'},
        'microsoft edge': {'search': ['edge', 'microsoft edge'], 'process': 'msedge.exe'},
        'firefox': {'search': ['firefox', 'mozilla'], 'process': 'firefox.exe'},
        'notepad': {'search': ['notepad', 'untitled'], 'process': 'notepad.exe'},
        'vs code': {'search': ['visual studio code', 'code'], 'process': 'Code.exe'},
        'vscode': {'search': ['visual studio code', 'code'], 'process': 'Code.exe'},
        'visual studio code': {'search': ['visual studio code', 'code'], 'process': 'Code.exe'},
        'spotify': {'search': ['spotify'], 'process': 'Spotify.exe'},
        'discord': {'search': ['discord'], 'process': 'Discord.exe'},
        'teams': {'search': ['teams', 'microsoft teams'], 'process': 'ms-teams.exe'},
        'microsoft teams': {'search': ['teams', 'microsoft teams'], 'process': 'ms-teams.exe'},
    }
    
    def control_app_window(self, app_name: str, action: str) -> Tuple[bool, str]:
        """
        Control a specific app's window (minimize, maximize, close, restore).
        app_name: partial name of the app/window
        action: 'minimize', 'maximize', 'close', 'restore'
        """
        import os
        try:
            if not HAS_WIN32:
                return False, "win32gui not available"
            
            # Find the window by name
            windows = self.get_active_windows()
            target_hwnd = None
            target_title = None
            
            app_name_lower = app_name.lower()
            
            # Get search terms from mapping or use app name directly
            app_info = self.APP_NAME_MAP.get(app_name_lower, {})
            search_terms = app_info.get('search', [app_name_lower])
            process_name = app_info.get('process', f'{app_name_lower}.exe')
            
            # Try to find window by search terms
            for w in windows:
                title_lower = w['title'].lower()
                app_lower = w.get('app', '').lower()
                
                # Check if any search term matches
                for term in search_terms:
                    if term in title_lower or term in app_lower:
                        target_hwnd = w['hwnd']
                        target_title = w['title']
                        break
                if target_hwnd:
                    break
            
            # Fallback: direct match on app name
            if not target_hwnd:
                for w in windows:
                    if app_name_lower in w['title'].lower() or app_name_lower in w.get('app', '').lower():
                        target_hwnd = w['hwnd']
                        target_title = w['title']
                        break
            
            if not target_hwnd:
                # For close action, try taskkill as fallback
                if action == 'close':
                    try:
                        result = os.system(f'taskkill /f /im {process_name} 2>nul')
                        if result == 0:
                            return True, f"Closed {app_name}"
                    except:
                        pass
                return False, f"Could not find window matching '{app_name}'"
            
            if action == 'minimize':
                win32gui.ShowWindow(target_hwnd, win32con.SW_MINIMIZE)
                return True, f"Minimized {target_title[:40]}"
            elif action == 'maximize':
                win32gui.ShowWindow(target_hwnd, win32con.SW_MAXIMIZE)
                return True, f"Maximized {target_title[:40]}"
            elif action == 'close':
                win32gui.PostMessage(target_hwnd, win32con.WM_CLOSE, 0, 0)
                return True, f"Closed {target_title[:40]}"
            elif action == 'restore':
                win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
                return True, f"Restored {target_title[:40]}"
            else:
                return False, f"Unknown action: {action}"
                
        except Exception as e:
            return False, f"Failed to {action} app: {e}"
    
    def focus_window_by_index(self, index: int) -> Tuple[bool, str]:
        """Focus window by its index in the active windows list."""
        return self.focus_window(str(index))
    
    def bring_window_to_front(self, title_part: str) -> Tuple[bool, str]:
        """Bring a window to front by partial title match."""
        return self.focus_window(title_part)

    # =========================================================================
    # ICON RECOGNITION AND CLICKING
    # =========================================================================
    
    def find_and_click_icon(self, name: str) -> Tuple[bool, str]:
        """
        Find an icon or text on screen using OCR and click it.
        Works for taskbar icons, desktop icons, and any visible text.
        """
        try:
            from core.screen_context import get_screen_engine
            engine = get_screen_engine()
            
            if engine.click_on_text(name):
                return True, f"Clicked on '{name}'"
            
            # Try fuzzy matching
            matches = engine.find_text_on_screen(name)
            if matches:
                # Click the best match
                best = matches[0]
                x, y = best.region.center
                if PYAUTOGUI_AVAILABLE:
                    pyautogui.click(x, y)
                    return True, f"Clicked on '{best.text}' (similar to '{name}')"
            
            return False, f"Could not find '{name}' on screen"
        except Exception as e:
            return False, f"Icon search failed: {e}"
    
    def find_taskbar_icon(self, name: str) -> Tuple[bool, str]:
        """Find and click an icon on the taskbar by name."""
        try:
            # First, make sure taskbar is visible
            self.show_taskbar()
            time.sleep(0.2)
            
            # Try to find it using OCR in the taskbar region
            taskbar_rect = self._get_taskbar_rect()
            
            # Use screen context to find text in taskbar area
            from core.screen_context import get_screen_engine
            engine = get_screen_engine()
            
            # Capture and search
            matches = engine.find_text_on_screen(name)
            
            # Filter matches to taskbar region
            for match in matches:
                mx, my = match.region.center
                left, top, right, bottom = taskbar_rect
                if left <= mx <= right and top <= my <= bottom:
                    if PYAUTOGUI_AVAILABLE:
                        pyautogui.click(mx, my)
                        return True, f"Clicked taskbar icon '{match.text}'"
            
            # If not found, try hovering over taskbar icons
            # Windows shows tooltips with app names
            return False, f"Could not find '{name}' on taskbar"
        except Exception as e:
            return False, f"Taskbar icon search failed: {e}"
    
    def click_at_position(self, x: int, y: int) -> Tuple[bool, str]:
        """Click at a specific screen position."""
        try:
            if PYAUTOGUI_AVAILABLE:
                pyautogui.click(x, y)
                return True, f"Clicked at ({x}, {y})"
            return False, "pyautogui not available"
        except Exception as e:
            return False, f"Click failed: {e}"


# Singleton instance
_windows_ui: Optional[WindowsUIController] = None


def get_windows_ui() -> WindowsUIController:
    """Get the global Windows UI controller instance"""
    global _windows_ui
    if _windows_ui is None:
        _windows_ui = WindowsUIController()
    return _windows_ui


def parse_windows_ui_command(text: str) -> Optional[Dict[str, Any]]:
    """Parse voice commands for Windows UI control"""
    import re
    t = text.lower().strip()
    
    # Start Menu commands
    start_patterns = [
        (r'^(?:open|show|click)\s+(?:the\s+)?start(?:\s+menu)?$', 'open_start'),
        (r'^(?:close|hide)\s+(?:the\s+)?start(?:\s+menu)?$', 'close_start'),
        (r'^start\s+menu$', 'open_start'),
        (r'^start$', 'open_start'),  # Bare 'start' opens start menu
        (r'^(?:search|look\s+for)\s+(.+?)(?:\s+in\s+start)?$', 'search_start'),
        (r'^find\s+(.+?)\s+in\s+(?:the\s+)?start(?:\s+menu)?$', 'search_start'),
    ]
    
    for pattern, action in start_patterns:
        match = re.match(pattern, t)
        if match:
            if action == 'search_start':
                return {'type': 'windows_ui', 'action': action, 'query': match.group(1)}
            return {'type': 'windows_ui', 'action': action}
    
    # Taskbar commands
    taskbar_patterns = [
        (r'^(?:click|open)\s+taskbar\s+(?:app\s+)?(\d+)$', 'click_taskbar_app'),
        (r'^(?:click|open)\s+(?:the\s+)?(?:first|1st)\s+(?:taskbar\s+)?app$', 'click_taskbar_1'),
        (r'^(?:click|open)\s+(?:the\s+)?(?:second|2nd)\s+(?:taskbar\s+)?app$', 'click_taskbar_2'),
        (r'^(?:click|open)\s+(?:the\s+)?(?:third|3rd)\s+(?:taskbar\s+)?app$', 'click_taskbar_3'),
        (r'^show\s+(?:the\s+)?taskbar$', 'show_taskbar'),
        (r'^(?:click|open)\s+(?:the\s+)?system\s+tray$', 'system_tray'),
        (r'^(?:click|open)\s+(?:the\s+)?notification(?:s)?(?:\s+center)?$', 'notifications'),
        (r'^(?:click|open)\s+(?:the\s+)?quick\s+settings$', 'quick_settings'),
        (r'^(?:click|open)\s+(?:the\s+)?(?:date|time|clock|calendar)$', 'date_time'),
    ]
    
    for pattern, action in taskbar_patterns:
        match = re.match(pattern, t)
        if match:
            if action == 'click_taskbar_app':
                return {'type': 'windows_ui', 'action': action, 'index': int(match.group(1))}
            if action.startswith('click_taskbar_'):
                index = int(action.split('_')[-1])
                return {'type': 'windows_ui', 'action': 'click_taskbar_app', 'index': index}
            return {'type': 'windows_ui', 'action': action}
    
    # Desktop commands
    desktop_patterns = [
        (r'^show\s+(?:the\s+)?desktop$', 'show_desktop'),
        (r'^(?:click|open)\s+(?:the\s+)?desktop\s+icon\s+(.+)$', 'click_desktop_icon'),
        (r'^(?:open|click)\s+(.+?)\s+(?:on\s+)?desktop$', 'click_desktop_icon'),
    ]
    
    for pattern, action in desktop_patterns:
        match = re.match(pattern, t)
        if match:
            if action == 'click_desktop_icon':
                return {'type': 'windows_ui', 'action': action, 'name': match.group(1)}
            return {'type': 'windows_ui', 'action': action}
    
    # Window management
    window_patterns = [
        (r'^task\s+view$', 'task_view'),
        (r'^(?:next|switch)\s+window$', 'switch_window'),
        (r'^snap\s+(?:window\s+)?(?:to\s+)?(left|right|top|bottom|up|down)$', 'snap'),
        (r'^snap\s+(?:to\s+)?(top-?left|top-?right|bottom-?left|bottom-?right)$', 'snap'),
        (r'^close\s+(?:this\s+)?window$', 'close_window'),
        (r'^minimize\s+(?:this\s+)?window$', 'minimize_window'),
        (r'^maximize\s+(?:this\s+)?window$', 'maximize_window'),
        # Active windows listing
        (r'^(?:show|list|what are)\s+(?:the\s+)?(?:active|open|running)\s+(?:apps?|windows?|programs?)$', 'list_active'),
        (r'^(?:active|open)\s+(?:apps?|windows?)$', 'list_active'),
        (r'^what(?:\'s| is)\s+(?:running|open)$', 'list_active'),
        # Previous/next window
        (r'^(?:previous|prev|last)\s+window$', 'previous_window'),
        (r'^(?:go\s+)?back(?:\s+to)?\s+(?:previous\s+)?window$', 'previous_window'),
        (r'^(?:switch|go)\s+(?:to\s+)?(?:the\s+)?(?:previous|last)\s+(?:window|app)?$', 'previous_window'),
        (r'^alt\s*tab$', 'previous_window'),
        # Focus specific window
        (r'^(?:focus|activate|enable|switch\s+to|go\s+to)\s+(?:window\s+)?(\d+)$', 'focus_window_num'),
        (r'^(?:focus|activate|enable|switch\s+to|go\s+to)\s+(.+?)(?:\s+window)?$', 'focus_window_name'),
        (r'^(?:bring|show)\s+(.+?)\s+(?:to\s+)?(?:front|foreground)$', 'focus_window_name'),
        (r'^(?:this|current)\s+window$', 'focus_current'),
        # Split screen
        (r'^split\s+(?:the\s+)?screen$', 'split_half'),
        (r'^split\s+(?:screen\s+)?(?:in\s+)?half$', 'split_half'),
        (r'^(?:side\s+by\s+side|50\s*50|fifty\s+fifty)$', 'split_half'),
        (r'^split\s+(?:screen\s+)?(left|right|vertical|horizontal)$', 'split_layout'),
    ]
    
    for pattern, action in window_patterns:
        match = re.match(pattern, t)
        if match:
            if action == 'snap':
                direction = match.group(1).replace('-', '')
                return {'type': 'windows_ui', 'action': action, 'direction': direction}
            elif action == 'focus_window_num':
                return {'type': 'windows_ui', 'action': 'focus_window', 'identifier': match.group(1)}
            elif action == 'focus_window_name':
                return {'type': 'windows_ui', 'action': 'focus_window', 'identifier': match.group(1)}
            elif action == 'split_layout':
                return {'type': 'windows_ui', 'action': 'split_screen', 'layout': match.group(1)}
            elif action == 'split_half':
                return {'type': 'windows_ui', 'action': 'split_screen', 'layout': 'half'}
            return {'type': 'windows_ui', 'action': action}
    
    # System shortcuts
    shortcut_patterns = [
        (r'^(?:open\s+)?run(?:\s+dialog)?$', 'run_dialog'),
        (r'^run\s+(.+)$', 'run_command'),
        (r'^(?:open\s+)?(?:file\s+)?explorer$', 'file_explorer'),
        (r'^(?:open\s+)?settings$', 'settings'),
        (r'^lock\s+(?:the\s+)?(?:screen|computer|pc)$', 'lock'),
        (r'^(?:open\s+)?clipboard(?:\s+history)?$', 'clipboard'),
        (r'^(?:take\s+)?(?:a\s+)?screenshot$', 'screenshot_full'),
        (r'^(?:take\s+)?(?:a\s+)?snip(?:ping)?(?:\s+tool)?$', 'screenshot_snip'),
        (r'^(?:open\s+)?emoji(?:s)?(?:\s+picker)?$', 'emoji'),
    ]
    
    for pattern, action in shortcut_patterns:
        match = re.match(pattern, t)
        if match:
            if action == 'run_command':
                return {'type': 'windows_ui', 'action': action, 'command': match.group(1)}
            return {'type': 'windows_ui', 'action': action}
    
    # Icon/element clicking by name (OCR-based)
    click_patterns = [
        (r'^click\s+(?:on\s+)?(?:the\s+)?(.+?)\s+icon$', 'click_icon'),
        (r'^click\s+on\s+(.+)$', 'click_element'),
        (r'^find\s+(?:and\s+)?click\s+(?:on\s+)?(.+)$', 'click_element'),
        (r'^(?:click|tap|press)\s+(?:the\s+)?(.+?)\s+button$', 'click_element'),
    ]
    
    for pattern, action in click_patterns:
        match = re.match(pattern, t)
        if match:
            target = match.group(1).strip()
            if target and len(target) > 1:  # Avoid matching single chars
                return {'type': 'windows_ui', 'action': action, 'target': target}
    
    return None


def execute_windows_ui_command(parsed: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute a Windows UI command"""
    action = parsed.get('action', '')
    ui = get_windows_ui()
    
    # Start menu
    if action == 'open_start':
        return ui.open_start_menu()
    elif action == 'close_start':
        return ui.close_start_menu()
    elif action == 'search_start':
        query = parsed.get('query', '')
        return ui.run_from_start(query)
    
    # Taskbar
    elif action == 'click_taskbar_app':
        index = parsed.get('index', 1)
        return ui.click_taskbar_app(index=index)
    elif action == 'show_taskbar':
        return ui.show_taskbar()
    elif action == 'system_tray':
        return ui.click_system_tray()
    elif action == 'notifications':
        return ui.click_notification_center()
    elif action == 'quick_settings':
        return ui.click_quick_settings()
    elif action == 'date_time':
        return ui.click_date_time()
    
    # Desktop
    elif action == 'show_desktop':
        return ui.show_desktop()
    elif action == 'click_desktop_icon':
        name = parsed.get('name', '')
        return ui.click_desktop_icon(name)
    
    # Window management
    elif action == 'task_view':
        return ui.task_view()
    elif action == 'switch_window':
        return ui.switch_window()
    elif action == 'snap':
        direction = parsed.get('direction', 'left')
        return ui.snap_window(direction)
    elif action == 'close_window':
        return ui.close_window()
    elif action == 'minimize_window':
        return ui.minimize_window()
    elif action == 'maximize_window':
        return ui.maximize_window()
    elif action == 'restore_window':
        return ui.restore_window()
    
    # Active windows and switching
    elif action == 'list_active':
        return ui.list_active_apps()
    elif action == 'previous_window':
        return ui.previous_window()
    elif action == 'focus_window':
        identifier = parsed.get('identifier', '')
        return ui.focus_window(identifier)
    elif action == 'focus_current':
        return True, "Already on current window"
    elif action == 'split_screen':
        layout = parsed.get('layout', 'half')
        return ui.split_screen(layout)
    
    # Snap specific apps
    elif action == 'snap_app':
        app_name = parsed.get('app_name', '')
        direction = parsed.get('direction', 'left')
        return ui.snap_app(app_name, direction)
    elif action == 'snap_with':
        app1 = parsed.get('app1', '')
        app2 = parsed.get('app2', '')
        return ui.snap_apps_together(app1, app2)
    
    # Window control for specific apps (minimize/maximize/close)
    elif action == 'minimize_app':
        app_name = parsed.get('app_name', '')
        return ui.control_app_window(app_name, 'minimize')
    elif action == 'maximize_app':
        app_name = parsed.get('app_name', '')
        return ui.control_app_window(app_name, 'maximize')
    elif action == 'close_app':
        app_name = parsed.get('app_name', '')
        return ui.control_app_window(app_name, 'close')
    elif action == 'restore_app':
        app_name = parsed.get('app_name', '')
        return ui.control_app_window(app_name, 'restore')
    
    # Shortcuts
    elif action == 'run_dialog':
        return ui.open_run_dialog()
    elif action == 'run_command':
        command = parsed.get('command', '')
        return ui.run_command(command)
    elif action == 'file_explorer':
        return ui.open_file_explorer()
    elif action == 'settings':
        return ui.open_settings()
    elif action == 'lock':
        return ui.lock_screen()
    elif action == 'clipboard':
        return ui.open_clipboard_history()
    elif action == 'screenshot_full':
        return ui.take_screenshot('full')
    elif action == 'screenshot_snip':
        return ui.take_screenshot('snip')
    elif action == 'emoji':
        return ui.emoji_picker()
    
    # Icon/element clicking
    elif action in ('click_icon', 'click_element'):
        target = parsed.get('target', '')
        return ui.find_and_click_icon(target)
    
    return False, f"Unknown Windows UI action: {action}"


if __name__ == "__main__":
    print("=" * 60)
    print("VoxMind Windows UI Controller")
    print("=" * 60)
    
    ui = get_windows_ui()
    print(f"\nScreen size: {ui.screen_width}x{ui.screen_height}")
    print(f"Taskbar position: {ui.taskbar_position.value}")
    print(f"Taskbar rect: {ui._get_taskbar_rect()}")
    
    print("\n[Command Examples]")
    examples = [
        "open start menu",
        "click taskbar 1",
        "show desktop",
        "task view",
        "snap left",
        "open settings",
        "take a screenshot",
    ]
    
    for cmd in examples:
        result = parse_windows_ui_command(cmd)
        print(f"  '{cmd}' -> {result}")
