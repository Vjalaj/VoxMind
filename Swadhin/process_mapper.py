"""
VoxMind Process Mapper Module
=============================
Maps running processes to app names/icons using Task Manager-like access.

This module solves problematic app/icon mapping by:
1. Enumerating running processes with full details
2. Extracting app icons and names from executables
3. Handling edge cases (UWP apps, system processes, etc.)
4. Caching process information for performance

Author: Swadhin
"""

import os
import sys
import ctypes
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple, Any, Set
from enum import Enum
from functools import lru_cache
import time
import json
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

# Windows API imports
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logger.warning("psutil not installed. Process mapping will be limited.")

try:
    import win32gui
    import win32con
    import win32process
    import win32api
    import win32ui
    from win32com.shell import shell, shellcon
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    logger.warning("pywin32 not installed. Icon extraction will be limited.")

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("Pillow not installed. Icon processing will be limited.")


# === Data Classes ===

class ProcessCategory(Enum):
    """Categories for process classification"""
    SYSTEM = "system"
    BROWSER = "browser"
    OFFICE = "office"
    DEVELOPMENT = "development"
    MEDIA = "media"
    COMMUNICATION = "communication"
    UTILITY = "utility"
    GAME = "game"
    BACKGROUND = "background"
    UWP = "uwp"
    UNKNOWN = "unknown"


@dataclass
class ProcessInfo:
    """Complete information about a running process"""
    pid: int
    name: str                                # Process name (e.g., "chrome.exe")
    friendly_name: str                       # Display name (e.g., "Google Chrome")
    exe_path: Optional[str] = None          # Full path to executable
    cmdline: Optional[str] = None           # Command line arguments
    username: Optional[str] = None          # User running the process
    memory_mb: float = 0.0                  # Memory usage in MB
    cpu_percent: float = 0.0                # CPU usage percentage
    status: str = "running"                 # Process status
    category: ProcessCategory = ProcessCategory.UNKNOWN
    icon_path: Optional[str] = None         # Path to extracted icon
    window_titles: List[str] = field(default_factory=list)
    parent_pid: Optional[int] = None
    create_time: float = 0.0
    is_uwp: bool = False
    company: Optional[str] = None           # Publisher/company name
    description: Optional[str] = None       # File description
    version: Optional[str] = None           # File version


@dataclass
class AppIconInfo:
    """Information about an app's icon"""
    app_name: str
    icon_path: str
    icon_size: Tuple[int, int] = (32, 32)
    source: str = "executable"  # "executable", "shell", "cache", "default"


# === Process Name Mappings ===

# Problematic process names that need special handling
PROCESS_FRIENDLY_NAMES: Dict[str, str] = {
    # Browsers
    "chrome.exe": "Google Chrome",
    "msedge.exe": "Microsoft Edge",
    "firefox.exe": "Mozilla Firefox",
    "brave.exe": "Brave Browser",
    "opera.exe": "Opera",
    "vivaldi.exe": "Vivaldi",
    "iexplore.exe": "Internet Explorer",
    
    # Microsoft Office
    "winword.exe": "Microsoft Word",
    "excel.exe": "Microsoft Excel",
    "powerpnt.exe": "Microsoft PowerPoint",
    "outlook.exe": "Microsoft Outlook",
    "onenote.exe": "Microsoft OneNote",
    "msteams.exe": "Microsoft Teams",
    "teams.exe": "Microsoft Teams",
    
    # Development
    "code.exe": "Visual Studio Code",
    "devenv.exe": "Visual Studio",
    "pycharm64.exe": "PyCharm",
    "idea64.exe": "IntelliJ IDEA",
    "webstorm64.exe": "WebStorm",
    "rider64.exe": "JetBrains Rider",
    "notepad++.exe": "Notepad++",
    "sublime_text.exe": "Sublime Text",
    "atom.exe": "Atom",
    "cursor.exe": "Cursor",
    
    # Communication
    "slack.exe": "Slack",
    "discord.exe": "Discord",
    "zoom.exe": "Zoom",
    "telegram.exe": "Telegram",
    "whatsapp.exe": "WhatsApp",
    "signal.exe": "Signal",
    "skype.exe": "Skype",
    
    # Media
    "spotify.exe": "Spotify",
    "vlc.exe": "VLC Media Player",
    "wmplayer.exe": "Windows Media Player",
    "itunes.exe": "iTunes",
    "audacity.exe": "Audacity",
    
    # Utilities
    "notepad.exe": "Notepad",
    "calc.exe": "Calculator",
    "mspaint.exe": "Paint",
    "snippingtool.exe": "Snipping Tool",
    "snippingool.exe": "Snipping Tool",
    "7zfm.exe": "7-Zip",
    "winrar.exe": "WinRAR",
    
    # System
    "explorer.exe": "File Explorer",
    "taskmgr.exe": "Task Manager",
    "regedit.exe": "Registry Editor",
    "cmd.exe": "Command Prompt",
    "powershell.exe": "PowerShell",
    "windowsterminal.exe": "Windows Terminal",
    "wt.exe": "Windows Terminal",
    "systemsettings.exe": "Settings",
    "control.exe": "Control Panel",
    "mmc.exe": "Microsoft Management Console",
    
    # Games & Launchers
    "steam.exe": "Steam",
    "epicgameslauncher.exe": "Epic Games",
    "gog galaxy.exe": "GOG Galaxy",
    "origin.exe": "EA Origin",
    "battle.net.exe": "Battle.net",
    
    # UWP Apps (ApplicationFrameHost children)
    "applicationframehost.exe": "UWP App Host",
    "microsoftedge.exe": "Microsoft Edge",
    "photos.exe": "Photos",
    "calculator.exe": "Calculator",
    "windowscalculator.exe": "Calculator",
    "mail.exe": "Mail",
    "calendar.exe": "Calendar",
}

# Process names that indicate system/background processes
SYSTEM_PROCESSES: Set[str] = {
    "system", "smss.exe", "csrss.exe", "wininit.exe", "services.exe",
    "lsass.exe", "svchost.exe", "dwm.exe", "conhost.exe", "sihost.exe",
    "taskhostw.exe", "runtimebroker.exe", "searchhost.exe", "ctfmon.exe",
    "securityhealthservice.exe", "securityhealthsystray.exe", "dllhost.exe",
    "fontdrvhost.exe", "wmiprvse.exe", "searchindexer.exe", "spoolsv.exe",
    "audiodg.exe", "ntoskrnl.exe", "registry", "memory compression",
    "searchapp.exe", "startmenuexperiencehost.exe", "textinputhost.exe",
    "shellexperiencehost.exe", "lockapp.exe", "yourphone.exe",
    "gamebarpresencewriter.exe", "gamebar.exe", "gamebarftserver.exe",
}

# Category mappings for process classification
CATEGORY_KEYWORDS: Dict[ProcessCategory, List[str]] = {
    ProcessCategory.BROWSER: ["chrome", "edge", "firefox", "brave", "opera", "browser", "vivaldi", "safari"],
    ProcessCategory.OFFICE: ["word", "excel", "powerpoint", "outlook", "office", "onenote", "access"],
    ProcessCategory.DEVELOPMENT: ["code", "visual studio", "pycharm", "intellij", "webstorm", "notepad++", "sublime", "rider", "android studio", "xcode"],
    ProcessCategory.MEDIA: ["spotify", "vlc", "media", "player", "itunes", "music", "video", "audacity", "obs", "photoshop", "premiere"],
    ProcessCategory.COMMUNICATION: ["teams", "slack", "discord", "zoom", "telegram", "whatsapp", "skype", "signal", "webex"],
    ProcessCategory.UTILITY: ["notepad", "calculator", "paint", "snipping", "7z", "winrar", "screenshot"],
    ProcessCategory.GAME: ["steam", "epic", "origin", "battle.net", "game", "gaming"],
}


# === Process Mapper Class ===

class ProcessMapper:
    """
    Maps running processes to friendly app names and icons.
    Provides Task Manager-like access to process information.
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize the process mapper.
        
        Args:
            cache_dir: Directory to cache extracted icons (default: ./cache/icons)
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path("./cache/icons")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self._process_cache: Dict[int, ProcessInfo] = {}
        self._icon_cache: Dict[str, AppIconInfo] = {}
        self._last_refresh: float = 0
        self._cache_ttl: float = 5.0  # Cache TTL in seconds
        
        # Load icon cache from disk
        self._load_icon_cache()
    
    def _load_icon_cache(self):
        """Load cached icon mappings from disk"""
        cache_file = self.cache_dir / "icon_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    for app_name, info in data.items():
                        self._icon_cache[app_name] = AppIconInfo(
                            app_name=info['app_name'],
                            icon_path=info['icon_path'],
                            icon_size=tuple(info.get('icon_size', [32, 32])),
                            source=info.get('source', 'cache')
                        )
            except Exception as e:
                logger.warning(f"Failed to load icon cache: {e}")
    
    def _save_icon_cache(self):
        """Save icon cache to disk"""
        cache_file = self.cache_dir / "icon_cache.json"
        try:
            data = {}
            for app_name, info in self._icon_cache.items():
                data[app_name] = {
                    'app_name': info.app_name,
                    'icon_path': info.icon_path,
                    'icon_size': list(info.icon_size),
                    'source': info.source
                }
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save icon cache: {e}")
    
    def get_running_processes(self, include_system: bool = False) -> List[ProcessInfo]:
        """
        Get all running processes with detailed information.
        Similar to Task Manager's process list.
        
        Args:
            include_system: Include system/background processes
            
        Returns:
            List of ProcessInfo objects
        """
        if not HAS_PSUTIL:
            logger.error("psutil required for process enumeration")
            return []
        
        # Check cache validity
        now = time.time()
        if now - self._last_refresh < self._cache_ttl and self._process_cache:
            processes = list(self._process_cache.values())
            if not include_system:
                processes = [p for p in processes if p.category != ProcessCategory.SYSTEM]
            return processes
        
        processes = []
        self._process_cache.clear()
        
        for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline', 'username', 
                                          'memory_info', 'cpu_percent', 'status',
                                          'ppid', 'create_time']):
            try:
                pinfo = proc.info
                name_lower = pinfo['name'].lower() if pinfo['name'] else ""
                
                # Skip system processes if not requested
                if not include_system and name_lower in SYSTEM_PROCESSES:
                    continue
                
                # Get friendly name
                friendly_name = self._get_friendly_name(pinfo['name'], pinfo.get('exe'))
                
                # Classify the process
                category = self._classify_process(name_lower, pinfo.get('exe', ''))
                
                # Skip background processes unless explicitly requested
                if not include_system and category == ProcessCategory.BACKGROUND:
                    continue
                
                # Get window titles for this process
                window_titles = self._get_window_titles(pinfo['pid'])
                
                # Check if UWP app
                is_uwp = self._is_uwp_process(pinfo.get('exe', ''), name_lower)
                
                # Get file info (company, description, version)
                company, description, version = self._get_file_info(pinfo.get('exe'))
                
                # Calculate memory in MB
                memory_mb = 0.0
                if pinfo.get('memory_info'):
                    memory_mb = pinfo['memory_info'].rss / (1024 * 1024)
                
                process_info = ProcessInfo(
                    pid=pinfo['pid'],
                    name=pinfo['name'] or "Unknown",
                    friendly_name=friendly_name,
                    exe_path=pinfo.get('exe'),
                    cmdline=' '.join(pinfo.get('cmdline') or []),
                    username=pinfo.get('username'),
                    memory_mb=memory_mb,
                    cpu_percent=pinfo.get('cpu_percent', 0.0),
                    status=pinfo.get('status', 'unknown'),
                    category=category,
                    window_titles=window_titles,
                    parent_pid=pinfo.get('ppid'),
                    create_time=pinfo.get('create_time', 0),
                    is_uwp=is_uwp,
                    company=company,
                    description=description,
                    version=version
                )
                
                processes.append(process_info)
                self._process_cache[pinfo['pid']] = process_info
                
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        self._last_refresh = now
        return processes
    
    def _get_friendly_name(self, process_name: str, exe_path: Optional[str] = None) -> str:
        """
        Get a user-friendly name for a process.
        
        Args:
            process_name: The raw process name (e.g., "chrome.exe")
            exe_path: Full path to the executable
            
        Returns:
            User-friendly display name
        """
        if not process_name:
            return "Unknown Process"
        
        name_lower = process_name.lower()
        
        # Check our mapping first
        if name_lower in PROCESS_FRIENDLY_NAMES:
            return PROCESS_FRIENDLY_NAMES[name_lower]
        
        # Try to get name from file description
        if exe_path and HAS_WIN32:
            try:
                info = win32api.GetFileVersionInfo(exe_path, '\\')
                lang_info = win32api.GetFileVersionInfo(exe_path, '\\VarFileInfo\\Translation')
                if lang_info:
                    lang = lang_info[0]
                    lang_str = f"\\StringFileInfo\\{lang[0]:04x}{lang[1]:04x}\\FileDescription"
                    description = win32api.GetFileVersionInfo(exe_path, lang_str)
                    if description:
                        return description
            except (OSError, AttributeError, Exception):
                pass
        
        # Fallback: Clean up the process name
        friendly = process_name.replace('.exe', '').replace('_', ' ').replace('-', ' ')
        return friendly.title()
    
    def _classify_process(self, name_lower: str, exe_path: str) -> ProcessCategory:
        """Classify a process into a category"""
        
        # Check system processes
        if name_lower in SYSTEM_PROCESSES:
            return ProcessCategory.SYSTEM
        
        # Check UWP
        if 'windowsapps' in exe_path.lower() if exe_path else False:
            return ProcessCategory.UWP
        
        # Check against category keywords
        for category, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in name_lower:
                    return category
        
        # Check friendly name mapping for hints
        if name_lower in PROCESS_FRIENDLY_NAMES:
            friendly = PROCESS_FRIENDLY_NAMES[name_lower].lower()
            for category, keywords in CATEGORY_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in friendly:
                        return category
        
        return ProcessCategory.UNKNOWN
    
    def _is_uwp_process(self, exe_path: Optional[str], name_lower: str) -> bool:
        """Check if a process is a UWP (Universal Windows Platform) app"""
        if not exe_path:
            return False
        
        exe_lower = exe_path.lower()
        return (
            'windowsapps' in exe_lower or
            'systemapps' in exe_lower or
            name_lower == 'applicationframehost.exe'
        )
    
    def _get_window_titles(self, pid: int) -> List[str]:
        """Get all window titles for a process"""
        if not HAS_WIN32:
            return []
        
        titles = []
        
        def enum_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
                if window_pid == pid:
                    title = win32gui.GetWindowText(hwnd)
                    if title and title not in titles:
                        titles.append(title)
            return True
        
        try:
            win32gui.EnumWindows(enum_callback, None)
        except (OSError, Exception):
            pass
        
        return titles
    
    def _get_file_info(self, exe_path: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Get file version info (company, description, version)"""
        if not exe_path or not HAS_WIN32:
            return None, None, None
        
        try:
            info = win32api.GetFileVersionInfo(exe_path, '\\')
            lang_info = win32api.GetFileVersionInfo(exe_path, '\\VarFileInfo\\Translation')
            
            if lang_info:
                lang = lang_info[0]
                base_str = f"\\StringFileInfo\\{lang[0]:04x}{lang[1]:04x}\\"
                
                company = win32api.GetFileVersionInfo(exe_path, base_str + 'CompanyName')
                description = win32api.GetFileVersionInfo(exe_path, base_str + 'FileDescription')
                version = win32api.GetFileVersionInfo(exe_path, base_str + 'FileVersion')
                
                return company, description, version
        except (OSError, AttributeError, Exception):
            pass
        
        return None, None, None
    
    def find_process_by_name(self, query: str) -> Optional[ProcessInfo]:
        """
        Find a process by name or friendly name.
        
        Args:
            query: Process name to search for
            
        Returns:
            ProcessInfo if found, None otherwise
        """
        query_lower = query.lower().strip()
        processes = self.get_running_processes(include_system=True)
        
        # Exact match on process name
        for proc in processes:
            if proc.name.lower() == query_lower or proc.name.lower() == f"{query_lower}.exe":
                return proc
        
        # Match on friendly name
        for proc in processes:
            if query_lower in proc.friendly_name.lower():
                return proc
        
        # Match on window title
        for proc in processes:
            for title in proc.window_titles:
                if query_lower in title.lower():
                    return proc
        
        return None
    
    def get_processes_by_category(self, category: ProcessCategory) -> List[ProcessInfo]:
        """Get all processes in a specific category"""
        processes = self.get_running_processes()
        return [p for p in processes if p.category == category]
    
    def extract_icon(self, exe_path: str, size: int = 32) -> Optional[str]:
        """
        Extract icon from an executable file.
        
        Args:
            exe_path: Path to the executable
            size: Icon size (default 32x32)
            
        Returns:
            Path to extracted icon file, or None if failed
        """
        if not HAS_WIN32 or not exe_path:
            return None
        
        # Check cache first
        cache_key = f"{exe_path}_{size}"
        if cache_key in self._icon_cache:
            cached = self._icon_cache[cache_key]
            if os.path.exists(cached.icon_path):
                return cached.icon_path
        
        try:
            # Generate unique filename for cached icon
            exe_name = os.path.basename(exe_path).replace('.exe', '')
            icon_filename = f"{exe_name}_{size}.png"
            icon_path = str(self.cache_dir / icon_filename)
            
            # Extract icon using Windows Shell
            large_icons, small_icons = win32gui.ExtractIconEx(exe_path, 0)
            
            if large_icons:
                icon_handle = large_icons[0]
                
                if HAS_PIL:
                    # Convert to PIL Image and save
                    icon_info = win32gui.GetIconInfo(icon_handle)
                    bmp_handle = icon_info[4]  # hbmColor
                    
                    bmp_dc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
                    bmp = win32ui.CreateBitmap()
                    bmp.CreateCompatibleBitmap(bmp_dc, size, size)
                    
                    mem_dc = bmp_dc.CreateCompatibleDC()
                    mem_dc.SelectObject(bmp)
                    mem_dc.DrawIcon((0, 0), icon_handle)
                    
                    bmp_info = bmp.GetInfo()
                    bmp_bits = bmp.GetBitmapBits(True)
                    
                    img = Image.frombuffer(
                        'RGBA',
                        (bmp_info['bmWidth'], bmp_info['bmHeight']),
                        bmp_bits, 'raw', 'BGRA', 0, 1
                    )
                    img = img.resize((size, size), Image.LANCZOS)
                    img.save(icon_path, 'PNG')
                    
                    mem_dc.DeleteDC()
                    bmp_dc.DeleteDC()
                
                # Cleanup icon handles
                for icon in large_icons:
                    win32gui.DestroyIcon(icon)
                for icon in small_icons:
                    win32gui.DestroyIcon(icon)
                
                # Cache the result
                self._icon_cache[cache_key] = AppIconInfo(
                    app_name=exe_name,
                    icon_path=icon_path,
                    icon_size=(size, size),
                    source='executable'
                )
                self._save_icon_cache()
                
                return icon_path
                
        except Exception as e:
            logger.debug(f"Failed to extract icon from {exe_path}: {e}")
        
        return None
    
    def get_app_icon(self, process_name: str) -> Optional[str]:
        """
        Get the icon path for an app by process name.
        
        Args:
            process_name: The process name (e.g., "chrome.exe")
            
        Returns:
            Path to icon file, or None if not found
        """
        proc = self.find_process_by_name(process_name)
        if proc and proc.exe_path:
            return self.extract_icon(proc.exe_path)
        return None
    
    def get_process_summary(self) -> Dict[str, Any]:
        """
        Get a summary of running processes (like Task Manager overview).
        
        Returns:
            Dictionary with process statistics
        """
        processes = self.get_running_processes(include_system=True)
        
        # Calculate statistics
        total_memory = sum(p.memory_mb for p in processes)
        total_cpu = sum(p.cpu_percent for p in processes)
        
        # Count by category
        category_counts = {}
        for proc in processes:
            cat_name = proc.category.value
            category_counts[cat_name] = category_counts.get(cat_name, 0) + 1
        
        # Top memory consumers
        top_memory = sorted(processes, key=lambda p: p.memory_mb, reverse=True)[:5]
        
        # Top CPU consumers  
        top_cpu = sorted(processes, key=lambda p: p.cpu_percent, reverse=True)[:5]
        
        return {
            'total_processes': len(processes),
            'total_memory_mb': round(total_memory, 2),
            'total_cpu_percent': round(total_cpu, 2),
            'category_counts': category_counts,
            'top_memory': [
                {'name': p.friendly_name, 'memory_mb': round(p.memory_mb, 2)}
                for p in top_memory
            ],
            'top_cpu': [
                {'name': p.friendly_name, 'cpu_percent': round(p.cpu_percent, 2)}
                for p in top_cpu
            ]
        }
    
    def map_window_to_app(self, hwnd: int) -> Optional[ProcessInfo]:
        """
        Map a window handle to its application.
        Handles UWP apps and other problematic cases.
        
        Args:
            hwnd: Window handle
            
        Returns:
            ProcessInfo for the application
        """
        if not HAS_WIN32:
            return None
        
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            
            # Check cache first
            if pid in self._process_cache:
                return self._process_cache[pid]
            
            # Get process info
            proc = psutil.Process(pid)
            name_lower = proc.name().lower()
            
            # Handle ApplicationFrameHost (UWP container)
            if name_lower == 'applicationframehost.exe':
                # Try to find the actual UWP app
                for child in proc.children():
                    child_info = self.find_process_by_name(child.name())
                    if child_info:
                        return child_info
                
                # Fall back to window title
                title = win32gui.GetWindowText(hwnd)
                if title:
                    # Search by window title
                    for p in self._process_cache.values():
                        if title in p.window_titles:
                            return p
            
            # Standard process lookup
            return self.find_process_by_name(proc.name())
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None
    
    def resolve_problematic_mapping(self, app_query: str) -> Optional[ProcessInfo]:
        """
        Resolve problematic app/icon mappings.
        Handles edge cases like:
        - Apps with multiple processes
        - UWP apps
        - Apps with different display names
        - Background apps becoming foreground
        
        Args:
            app_query: User's query for the app
            
        Returns:
            Best matching ProcessInfo
        """
        query_lower = app_query.lower().strip()
        processes = self.get_running_processes()
        
        candidates = []
        
        for proc in processes:
            score = 0
            
            # Exact process name match
            if proc.name.lower().replace('.exe', '') == query_lower:
                score += 100
            
            # Friendly name match
            if query_lower in proc.friendly_name.lower():
                score += 80
            
            # Partial process name match
            if query_lower in proc.name.lower():
                score += 50
            
            # Window title match
            for title in proc.window_titles:
                if query_lower in title.lower():
                    score += 60
                    break
            
            # Company name match
            if proc.company and query_lower in proc.company.lower():
                score += 30
            
            # Description match
            if proc.description and query_lower in proc.description.lower():
                score += 40
            
            if score > 0:
                candidates.append((proc, score))
        
        if not candidates:
            return None
        
        # Sort by score and return best match
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
    
    def refresh(self):
        """Force refresh the process cache"""
        self._last_refresh = 0
        self._process_cache.clear()


# === Convenience Functions ===

def get_process_mapper() -> ProcessMapper:
    """Get a singleton ProcessMapper instance"""
    if not hasattr(get_process_mapper, '_instance'):
        get_process_mapper._instance = ProcessMapper()
    return get_process_mapper._instance


def list_running_apps() -> List[Dict[str, Any]]:
    """
    Get a list of running applications (user-facing apps only).
    
    Returns:
        List of dicts with app info
    """
    mapper = get_process_mapper()
    processes = mapper.get_running_processes()
    
    # Filter to only apps with windows
    apps = [
        {
            'name': p.friendly_name,
            'process': p.name,
            'pid': p.pid,
            'category': p.category.value,
            'windows': p.window_titles,
            'memory_mb': round(p.memory_mb, 2)
        }
        for p in processes
        if p.window_titles  # Only apps with visible windows
    ]
    
    return apps


def find_app(query: str) -> Optional[Dict[str, Any]]:
    """
    Find a running app by name.
    
    Args:
        query: App name to search for
        
    Returns:
        Dict with app info if found
    """
    mapper = get_process_mapper()
    proc = mapper.resolve_problematic_mapping(query)
    
    if proc:
        return {
            'name': proc.friendly_name,
            'process': proc.name,
            'pid': proc.pid,
            'category': proc.category.value,
            'windows': proc.window_titles,
            'exe_path': proc.exe_path,
            'company': proc.company
        }
    
    return None


def get_app_icon_path(app_name: str) -> Optional[str]:
    """
    Get the icon path for an app.
    
    Args:
        app_name: The app name to get icon for
        
    Returns:
        Path to icon file
    """
    mapper = get_process_mapper()
    return mapper.get_app_icon(app_name)


# === CLI Testing ===

if __name__ == "__main__":
    print("VoxMind Process Mapper - Testing")
    print("=" * 50)
    
    mapper = ProcessMapper()
    
    # Get running processes
    print("\n📋 Running Applications:")
    processes = mapper.get_running_processes()
    
    for proc in processes[:15]:  # Show first 15
        icons = "🪟" if proc.window_titles else "📦"
        print(f"  {icons} {proc.friendly_name} ({proc.name}) - {proc.category.value}")
        for title in proc.window_titles[:2]:
            print(f"      └─ {title[:50]}...")
    
    # Get summary
    print("\n📊 Process Summary:")
    summary = mapper.get_process_summary()
    print(f"  Total processes: {summary['total_processes']}")
    print(f"  Total memory: {summary['total_memory_mb']:.1f} MB")
    print(f"  Categories: {summary['category_counts']}")
    
    # Test problematic mapping
    print("\n🔍 Testing App Resolution:")
    test_queries = ["chrome", "code", "notepad", "teams", "explorer"]
    for query in test_queries:
        result = find_app(query)
        if result:
            print(f"  '{query}' → {result['name']} ({result['process']})")
        else:
            print(f"  '{query}' → Not found")
