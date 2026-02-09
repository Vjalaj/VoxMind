"""
VoxMind Linux Platform Implementation
=======================================
Linux-specific implementations of platform abstractions.
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
    BaseHotkeyController, BaseNotificationController
)

logger = logging.getLogger(__name__)

# =============================================================================
# LINUX IMPORTS (Guarded)
# =============================================================================

try:
    import Xlib
    from Xlib import X, display, Xatom
    HAS_XLIB = True
except ImportError:
    HAS_XLIB = False
    logger.warning("python-xlib not installed - window control limited")

try:
    import pulsectl
    HAS_PULSECTL = True
except ImportError:
    HAS_PULSECTL = False
    logger.warning("pulsectl not installed - using pactl fallback")


# =============================================================================
# LINUX WINDOW CONTROLLER
# =============================================================================

class LinuxWindowController(WindowController):
    """Linux window control using wmctrl/xdotool."""
    
    def __init__(self):
        self._has_wmctrl = self._check_command('wmctrl')
        self._has_xdotool = self._check_command('xdotool')
    
    def _check_command(self, cmd: str) -> bool:
        try:
            subprocess.run(['which', cmd], capture_output=True, check=True)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def _run_wmctrl(self, args: List[str]) -> Optional[str]:
        if not self._has_wmctrl:
            return None
        try:
            result = subprocess.run(
                ['wmctrl'] + args,
                capture_output=True, text=True
            )
            return result.stdout if result.returncode == 0 else None
        except subprocess.SubprocessError as e:
            logger.debug(f"wmctrl failed: {e}")
            return None
    
    def _run_xdotool(self, args: List[str]) -> Optional[str]:
        if not self._has_xdotool:
            return None
        try:
            result = subprocess.run(
                ['xdotool'] + args,
                capture_output=True, text=True
            )
            return result.stdout if result.returncode == 0 else None
        except subprocess.SubprocessError as e:
            logger.debug(f"xdotool failed: {e}")
            return None
    
    def get_active_window(self) -> Optional[WindowInfo]:
        window_id = self._run_xdotool(['getactivewindow'])
        if not window_id:
            return None
        
        window_id = window_id.strip()
        name = self._run_xdotool(['getwindowname', window_id])
        pid = self._run_xdotool(['getwindowpid', window_id])
        
        return WindowInfo(
            handle=int(window_id),
            title=name.strip() if name else "",
            process_name="",
            pid=int(pid.strip()) if pid else 0,
            rect=(0, 0, 0, 0),
        )
    
    def get_all_windows(self) -> List[WindowInfo]:
        output = self._run_wmctrl(['-l', '-p'])
        if not output:
            return []
        
        windows = []
        for line in output.strip().split('\n'):
            parts = line.split(None, 4)
            if len(parts) >= 5:
                try:
                    hwnd = int(parts[0], 16)
                    pid = int(parts[2])
                    title = parts[4] if len(parts) > 4 else ""
                    
                    windows.append(WindowInfo(
                        handle=hwnd,
                        title=title,
                        process_name="",
                        pid=pid,
                        rect=(0, 0, 0, 0),
                    ))
                except (ValueError, IndexError) as e:
                    logger.debug(f"Failed to parse window: {e}")
                    continue
        
        return windows
    
    def focus(self, window: WindowInfo) -> bool:
        result = self._run_wmctrl(['-i', '-a', hex(window.handle)])
        return result is not None
    
    def minimize(self, window: WindowInfo) -> bool:
        return self._run_xdotool(['windowminimize', str(window.handle)]) is not None
    
    def maximize(self, window: WindowInfo) -> bool:
        return self._run_wmctrl(['-i', '-r', hex(window.handle), 
                                  '-b', 'add,maximized_vert,maximized_horz']) is not None
    
    def restore(self, window: WindowInfo) -> bool:
        return self._run_wmctrl(['-i', '-r', hex(window.handle),
                                  '-b', 'remove,maximized_vert,maximized_horz']) is not None
    
    def close(self, window: WindowInfo) -> bool:
        return self._run_wmctrl(['-i', '-c', hex(window.handle)]) is not None
    
    def snap_left(self, window: WindowInfo) -> bool:
        # Get screen size
        try:
            import pyautogui
            w, h = pyautogui.size()
            return self._run_wmctrl(['-i', '-r', hex(window.handle),
                                      '-e', f'0,0,0,{w//2},{h}']) is not None
        except (ImportError, Exception) as e:
            logger.debug(f"snap_left failed: {e}")
            return False
    
    def snap_right(self, window: WindowInfo) -> bool:
        try:
            import pyautogui
            w, h = pyautogui.size()
            return self._run_wmctrl(['-i', '-r', hex(window.handle),
                                      '-e', f'0,{w//2},0,{w//2},{h}']) is not None
        except (ImportError, Exception) as e:
            logger.debug(f"snap_right failed: {e}")
            return False


# =============================================================================
# LINUX AUDIO CONTROLLER
# =============================================================================

class LinuxAudioController(AudioController):
    """Linux audio control using PulseAudio/PipeWire."""
    
    def __init__(self):
        self._pulse = None
        if HAS_PULSECTL:
            try:
                self._pulse = pulsectl.Pulse('voxmind')
            except pulsectl.PulseError as e:
                logger.debug(f"Failed to connect to PulseAudio: {e}")
    
    def _get_default_sink(self):
        if self._pulse:
            try:
                sinks = self._pulse.sink_list()
                for sink in sinks:
                    if sink.name == self._pulse.server_info().default_sink_name:
                        return sink
                return sinks[0] if sinks else None
            except pulsectl.PulseError as e:
                logger.debug(f"Failed to get default sink: {e}")
        return None
    
    def get_volume(self) -> float:
        sink = self._get_default_sink()
        if sink:
            return sink.volume.value_flat
        
        # Fallback to pactl
        try:
            result = subprocess.run(
                ['pactl', 'get-sink-volume', '@DEFAULT_SINK@'],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                # Parse "Volume: front-left: 65536 / 100%"
                import re
                match = re.search(r'(\d+)%', result.stdout)
                if match:
                    return int(match.group(1)) / 100.0
        except subprocess.SubprocessError as e:
            logger.debug(f"pactl get-volume failed: {e}")
        return 0.5
    
    def set_volume(self, level: float) -> bool:
        level = max(0.0, min(1.0, level))
        
        sink = self._get_default_sink()
        if sink and self._pulse:
            try:
                self._pulse.volume_set_all_chans(sink, level)
                return True
            except pulsectl.PulseError as e:
                logger.debug(f"PulseAudio set_volume failed: {e}")
        
        # Fallback to pactl
        try:
            subprocess.run(
                ['pactl', 'set-sink-volume', '@DEFAULT_SINK@', f'{int(level * 100)}%'],
                check=True
            )
            return True
        except subprocess.SubprocessError as e:
            logger.debug(f"pactl set-volume failed: {e}")
            return False
    
    def is_muted(self) -> bool:
        sink = self._get_default_sink()
        if sink:
            return sink.mute == 1
        
        try:
            result = subprocess.run(
                ['pactl', 'get-sink-mute', '@DEFAULT_SINK@'],
                capture_output=True, text=True
            )
            return 'yes' in result.stdout.lower()
        except subprocess.SubprocessError:
            return False
    
    def mute(self) -> bool:
        sink = self._get_default_sink()
        if sink and self._pulse:
            try:
                self._pulse.mute(sink, True)
                return True
            except pulsectl.PulseError as e:
                logger.debug(f"PulseAudio mute failed: {e}")
        
        try:
            subprocess.run(['pactl', 'set-sink-mute', '@DEFAULT_SINK@', '1'], check=True)
            return True
        except subprocess.SubprocessError as e:
            logger.debug(f"pactl mute failed: {e}")
            return False
    
    def unmute(self) -> bool:
        sink = self._get_default_sink()
        if sink and self._pulse:
            try:
                self._pulse.mute(sink, False)
                return True
            except pulsectl.PulseError as e:
                logger.debug(f"PulseAudio unmute failed: {e}")
        
        try:
            subprocess.run(['pactl', 'set-sink-mute', '@DEFAULT_SINK@', '0'], check=True)
            return True
        except subprocess.SubprocessError as e:
            logger.debug(f"pactl unmute failed: {e}")
            return False


# =============================================================================
# LINUX APP CONTROLLER
# =============================================================================

class LinuxAppController(AppController):
    """Linux application control."""
    
    def list_installed(self) -> List[AppInfo]:
        """List installed applications from .desktop files."""
        apps = []
        desktop_dirs = [
            '/usr/share/applications',
            '/usr/local/share/applications',
            os.path.expanduser('~/.local/share/applications'),
        ]
        
        for desktop_dir in desktop_dirs:
            if not os.path.isdir(desktop_dir):
                continue
            
            for filename in os.listdir(desktop_dir):
                if not filename.endswith('.desktop'):
                    continue
                
                filepath = os.path.join(desktop_dir, filename)
                try:
                    name = None
                    exec_cmd = None
                    
                    with open(filepath, 'r') as f:
                        for line in f:
                            if line.startswith('Name='):
                                name = line.split('=', 1)[1].strip()
                            elif line.startswith('Exec='):
                                exec_cmd = line.split('=', 1)[1].strip()
                                # Remove field codes
                                exec_cmd = exec_cmd.split()[0]
                    
                    if name and exec_cmd:
                        apps.append(AppInfo(
                            name=name,
                            path=exec_cmd,
                        ))
                except (IOError, UnicodeDecodeError) as e:
                    logger.debug(f"Failed to parse desktop file: {e}")
                    continue
        
        return apps
    
    def launch(self, app_name: str) -> Tuple[bool, str]:
        """Launch an application."""
        app_lower = app_name.lower()
        
        # Common app mappings
        app_map = {
            'chrome': 'google-chrome',
            'google chrome': 'google-chrome',
            'firefox': 'firefox',
            'terminal': 'gnome-terminal',
            'files': 'nautilus',
            'file manager': 'nautilus',
            'settings': 'gnome-control-center',
            'calculator': 'gnome-calculator',
            'text editor': 'gedit',
            'code': 'code',
            'vscode': 'code',
        }
        
        executable = app_map.get(app_lower, app_name)
        
        try:
            subprocess.Popen(
                [executable],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True, f"Launched {app_name}"
        except Exception as e:
            # Try gtk-launch for .desktop files
            try:
                subprocess.Popen(
                    ['gtk-launch', app_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return True, f"Launched {app_name}"
            except subprocess.SubprocessError as e2:
                return False, f"Could not launch {app_name}: {e} / {e2}"
    
    def terminate(self, app_name: str) -> Tuple[bool, str]:
        """Terminate an application."""
        try:
            subprocess.run(['pkill', '-f', app_name], check=True)
            return True, f"Terminated {app_name}"
        except subprocess.SubprocessError as e:
            return False, f"Could not terminate {app_name}: {e}"
    
    def is_running(self, app_name: str) -> bool:
        try:
            result = subprocess.run(
                ['pgrep', '-f', app_name],
                capture_output=True
            )
            return result.returncode == 0
        except subprocess.SubprocessError:
            return False


# =============================================================================
# LINUX SYSTEM CONTROLLER
# =============================================================================

class LinuxSystemController(SystemController):
    """Linux system operations."""
    
    def lock(self) -> bool:
        commands = [
            ['loginctl', 'lock-session'],
            ['xdg-screensaver', 'lock'],
            ['gnome-screensaver-command', '-l'],
        ]
        
        for cmd in commands:
            try:
                subprocess.run(cmd, check=True)
                return True
            except subprocess.SubprocessError:
                continue
        return False
    
    def sleep(self) -> bool:
        commands = [
            ['systemctl', 'suspend'],
            ['pm-suspend'],
        ]
        
        for cmd in commands:
            try:
                subprocess.run(cmd, check=True)
                return True
            except subprocess.SubprocessError:
                continue
        return False
    
    def shutdown(self, delay: int = 0) -> bool:
        try:
            if delay > 0:
                subprocess.run(['shutdown', f'+{delay // 60}'], check=True)
            else:
                subprocess.run(['shutdown', 'now'], check=True)
            return True
        except subprocess.SubprocessError as e:
            logger.debug(f"shutdown failed: {e}")
            return False
    
    def restart(self, delay: int = 0) -> bool:
        try:
            if delay > 0:
                subprocess.run(['shutdown', '-r', f'+{delay // 60}'], check=True)
            else:
                subprocess.run(['reboot'], check=True)
            return True
        except subprocess.SubprocessError as e:
            logger.debug(f"restart failed: {e}")
            return False
    
    def get_screen_size(self) -> Tuple[int, int]:
        try:
            result = subprocess.run(
                ['xdpyinfo'],
                capture_output=True, text=True
            )
            import re
            match = re.search(r'dimensions:\s+(\d+)x(\d+)', result.stdout)
            if match:
                return (int(match.group(1)), int(match.group(2)))
        except subprocess.SubprocessError as e:
            logger.debug(f"xdpyinfo failed: {e}")
        
        try:
            import pyautogui
            return pyautogui.size()
        except (ImportError, Exception) as e:
            logger.debug(f"pyautogui screen size failed: {e}")
            return (1920, 1080)
    
    def take_screenshot(self, filepath: str = None) -> Optional[str]:
        if not filepath:
            filepath = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        commands = [
            ['gnome-screenshot', '-f', filepath],
            ['scrot', filepath],
            ['import', '-window', 'root', filepath],
        ]
        
        for cmd in commands:
            try:
                subprocess.run(cmd, check=True)
                return filepath
            except subprocess.SubprocessError:
                continue
        
        # Fallback to pyautogui
        try:
            import pyautogui
            pyautogui.screenshot(filepath)
            return filepath
        except (ImportError, Exception) as e:
            logger.debug(f"Screenshot failed: {e}")
            return None


# =============================================================================
# LINUX NOTIFICATION CONTROLLER
# =============================================================================

class LinuxNotificationController(NotificationController):
    """Linux notifications using notify-send."""
    
    def show(self, title: str, message: str, icon: str = None,
             duration: int = 5) -> bool:
        try:
            cmd = ['notify-send', title, message, '-t', str(duration * 1000)]
            if icon:
                cmd.extend(['-i', icon])
            subprocess.run(cmd, check=True)
            return True
        except subprocess.SubprocessError as e:
            logger.debug(f"notify-send failed: {e}")
            # Fallback to plyer
            try:
                from plyer import notification
                notification.notify(
                    title=title,
                    message=message,
                    timeout=duration
                )
                return True
            except (ImportError, Exception) as e2:
                logger.debug(f"plyer notification failed: {e2}")
                return False


# =============================================================================
# LINUX PLATFORM
# =============================================================================

class Platform(BasePlatform):
    """Linux platform implementation."""
    
    def __init__(self):
        self.window = LinuxWindowController()
        self.audio = LinuxAudioController()
        self.app = LinuxAppController()
        self.system = LinuxSystemController()
        self.clipboard = BaseClipboardController()  # pyperclip works on Linux
        self.hotkey = BaseHotkeyController()  # pynput works on Linux
        self.notification = LinuxNotificationController()
    
    @property
    def name(self) -> str:
        return "Linux"
    
    def open_file(self, path: str) -> bool:
        try:
            subprocess.Popen(['xdg-open', path])
            return True
        except Exception as e:
            logger.error(f"Failed to open {path}: {e}")
            return False
