"""
VoxMind App Discovery Module
Comprehensive app discovery for complete PC autonomy.
Scans: Start Menu, Program Files, Registry, UWP apps
"""

import os
import subprocess
import json
import winreg
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from pathlib import Path
import re

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredApp:
    """Information about a discovered application"""
    name: str
    display_name: str
    executable: Optional[str] = None
    app_id: Optional[str] = None
    install_location: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    is_uwp: bool = False
    category: str = "other"
    source: str = "unknown"  # start_menu, registry, program_files, uwp
    
    def matches(self, query: str) -> bool:
        """Check if query matches this app"""
        q = query.lower().strip()
        if q in self.name.lower():
            return True
        if q in self.display_name.lower():
            return True
        for alias in self.aliases:
            if q == alias.lower() or alias.lower() in q or q in alias.lower():
                return True
        return False


class AppDiscovery:
    """Comprehensive application discovery system"""
    
    CACHE_FILE = "cache/discovered_apps.json"
    
    # Category keywords for auto-categorization
    CATEGORY_KEYWORDS = {
        "browser": ["chrome", "firefox", "edge", "brave", "opera", "safari", "vivaldi", "browser"],
        "office": ["word", "excel", "powerpoint", "outlook", "onenote", "access", "publisher", "office", "libreoffice", "openoffice"],
        "development": ["code", "visual studio", "pycharm", "intellij", "android studio", "xcode", "git", "github", "terminal", "cmd", "powershell", "python", "node", "npm"],
        "media": ["vlc", "spotify", "music", "video", "player", "photo", "image", "camera", "movie", "netflix", "youtube", "audacity", "obs"],
        "communication": ["teams", "slack", "discord", "zoom", "skype", "whatsapp", "telegram", "signal", "messenger", "mail", "outlook"],
        "gaming": ["steam", "epic", "origin", "ubisoft", "blizzard", "gog", "xbox", "game"],
        "graphics": ["photoshop", "illustrator", "gimp", "paint", "inkscape", "figma", "canva", "blender", "3d"],
        "utilities": ["notepad", "calculator", "7zip", "winrar", "ccleaner", "snipping", "clock", "alarm", "todo", "sticky"],
        "system": ["settings", "control panel", "task manager", "registry", "services", "device manager", "disk"],
        "security": ["antivirus", "defender", "firewall", "kaspersky", "norton", "avast", "malware"],
    }
    
    # Alias expansion for common apps
    ALIAS_MAP = {
        "chrome": ["google chrome", "web browser", "internet"],
        "firefox": ["mozilla firefox", "web browser"],
        "edge": ["microsoft edge", "web browser"],
        "code": ["vscode", "visual studio code", "vs code"],
        "notepad": ["text editor", "editor", "notes"],
        "calc": ["calculator", "math"],
        "explorer": ["file explorer", "files", "folders", "my computer", "this pc"],
        "paint": ["mspaint", "drawing"],
        "word": ["microsoft word", "documents", "doc"],
        "excel": ["microsoft excel", "spreadsheet", "xlsx"],
        "powerpoint": ["microsoft powerpoint", "slides", "presentation", "ppt"],
        "outlook": ["microsoft outlook", "email", "mail"],
        "teams": ["microsoft teams", "meeting"],
        "settings": ["control panel", "preferences", "system settings"],
        "terminal": ["windows terminal", "console", "cmd", "command prompt"],
        "spotify": ["music", "songs"],
        "discord": ["chat", "voice chat", "gaming chat"],
        "vlc": ["media player", "video player", "player"],
        "zoom": ["video call", "meeting", "conference"],
    }
    
    def __init__(self, cache_dir: str = None):
        self.apps: Dict[str, DiscoveredApp] = {}
        self.cache_file = Path(cache_dir or "cache") / "discovered_apps.json"
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        
    def discover_all(self, force_refresh: bool = False) -> Dict[str, DiscoveredApp]:
        """Discover all installed applications"""
        if not force_refresh and self._load_cache():
            return self.apps
        
        logger.info("Starting comprehensive app discovery...")
        
        # Clear existing apps
        self.apps = {}
        
        # Discover from multiple sources
        self._discover_start_menu()
        self._discover_registry()
        self._discover_program_files()
        self._discover_uwp_apps()
        
        # Add aliases and categories
        self._enrich_apps()
        
        # Save cache
        self._save_cache()
        
        logger.info(f"Discovered {len(self.apps)} applications")
        return self.apps
    
    def _discover_start_menu(self):
        """Discover apps from Start Menu"""
        try:
            result = subprocess.run(
                ["powershell", "-Command", 
                 "Get-StartApps | Select-Object Name, AppID | ConvertTo-Json -Compress"],
                capture_output=True, text=True, timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode == 0 and result.stdout.strip():
                apps_data = json.loads(result.stdout)
                if isinstance(apps_data, dict):
                    apps_data = [apps_data]
                
                for app in apps_data:
                    name = app.get("Name", "")
                    app_id = app.get("AppID", "")
                    if name and app_id:
                        key = self._normalize_name(name)
                        if key not in self.apps:
                            self.apps[key] = DiscoveredApp(
                                name=key,
                                display_name=name,
                                app_id=app_id,
                                is_uwp="_" in app_id and "!" in app_id,
                                source="start_menu"
                            )
        except Exception as e:
            logger.warning(f"Start menu discovery failed: {e}")
    
    def _discover_registry(self):
        """Discover apps from Windows Registry (installed programs)"""
        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        
        for hkey, path in registry_paths:
            try:
                with winreg.OpenKey(hkey, path) as key:
                    subkey_count = winreg.QueryInfoKey(key)[0]
                    for i in range(subkey_count):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                try:
                                    name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                    if not name or len(name) < 2:
                                        continue
                                    
                                    # Get additional info
                                    executable = None
                                    install_location = None
                                    try:
                                        executable = winreg.QueryValueEx(subkey, "DisplayIcon")[0]
                                        if executable:
                                            executable = executable.split(",")[0].strip('"')
                                    except:
                                        pass
                                    try:
                                        install_location = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                                    except:
                                        pass
                                    
                                    key_name = self._normalize_name(name)
                                    if key_name not in self.apps:
                                        self.apps[key_name] = DiscoveredApp(
                                            name=key_name,
                                            display_name=name,
                                            executable=executable,
                                            install_location=install_location,
                                            source="registry"
                                        )
                                except:
                                    pass
                        except:
                            continue
            except Exception as e:
                logger.debug(f"Registry path {path} failed: {e}")
    
    def _discover_program_files(self):
        """Discover apps from Program Files directories"""
        program_dirs = [
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
            os.path.expanduser("~\\AppData\\Local\\Programs"),
        ]
        
        executables_found = set()
        
        for prog_dir in program_dirs:
            if not os.path.exists(prog_dir):
                continue
            try:
                for item in os.listdir(prog_dir):
                    item_path = os.path.join(prog_dir, item)
                    if os.path.isdir(item_path):
                        # Look for .exe files in the directory
                        for exe in self._find_executables(item_path, max_depth=2):
                            exe_name = os.path.basename(exe).lower().replace(".exe", "")
                            if exe_name in executables_found:
                                continue
                            executables_found.add(exe_name)
                            
                            key = self._normalize_name(item)
                            if key not in self.apps:
                                self.apps[key] = DiscoveredApp(
                                    name=key,
                                    display_name=item,
                                    executable=exe,
                                    install_location=item_path,
                                    source="program_files"
                                )
            except Exception as e:
                logger.debug(f"Program files scan failed for {prog_dir}: {e}")
    
    def _discover_uwp_apps(self):
        """Discover UWP (Microsoft Store) apps"""
        try:
            result = subprocess.run(
                ["powershell", "-Command", 
                 "Get-AppxPackage | Select-Object Name, PackageFamilyName | ConvertTo-Json -Compress"],
                capture_output=True, text=True, timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode == 0 and result.stdout.strip():
                apps_data = json.loads(result.stdout)
                if isinstance(apps_data, dict):
                    apps_data = [apps_data]
                
                for app in apps_data:
                    name = app.get("Name", "")
                    family_name = app.get("PackageFamilyName", "")
                    if name and family_name and not name.startswith("Microsoft.") or \
                       name in ["Microsoft.WindowsCalculator", "Microsoft.Paint", "Microsoft.WindowsNotepad"]:
                        # Clean up the name
                        display_name = name.split(".")[-1] if "." in name else name
                        display_name = re.sub(r'([A-Z])', r' \1', display_name).strip()
                        
                        key = self._normalize_name(display_name)
                        if key and key not in self.apps:
                            self.apps[key] = DiscoveredApp(
                                name=key,
                                display_name=display_name,
                                app_id=family_name,
                                is_uwp=True,
                                source="uwp"
                            )
        except Exception as e:
            logger.warning(f"UWP discovery failed: {e}")
    
    def _find_executables(self, directory: str, max_depth: int = 2, current_depth: int = 0) -> List[str]:
        """Find executable files in a directory"""
        executables = []
        if current_depth > max_depth:
            return executables
        
        try:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if item.lower().endswith(".exe") and os.path.isfile(item_path):
                    # Skip installers and uninstallers
                    if not any(x in item.lower() for x in ["unins", "setup", "install", "update"]):
                        executables.append(item_path)
                elif os.path.isdir(item_path) and current_depth < max_depth:
                    executables.extend(self._find_executables(item_path, max_depth, current_depth + 1))
        except PermissionError:
            pass
        
        return executables[:5]  # Limit per directory
    
    def _normalize_name(self, name: str) -> str:
        """Normalize app name for consistent lookup"""
        # Remove version numbers, (TM), (R), etc.
        cleaned = re.sub(r'\s*[\(\[\{].*?[\)\]\}]', '', name)
        cleaned = re.sub(r'\s+\d+(\.\d+)*\s*$', '', cleaned)
        cleaned = re.sub(r'[™®©]', '', cleaned)
        return cleaned.lower().strip()
    
    def _enrich_apps(self):
        """Add aliases and categories to discovered apps"""
        for key, app in self.apps.items():
            # Add category
            app.category = self._categorize_app(app.name)
            
            # Add aliases
            for alias_key, aliases in self.ALIAS_MAP.items():
                if alias_key in app.name or alias_key in app.display_name.lower():
                    app.aliases.extend(aliases)
            
            # Add the key and display name as aliases
            if app.display_name.lower() != app.name:
                app.aliases.append(app.display_name.lower())
    
    def _categorize_app(self, name: str) -> str:
        """Auto-categorize an app based on its name"""
        name_lower = name.lower()
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            if any(kw in name_lower for kw in keywords):
                return category
        return "other"
    
    def _load_cache(self) -> bool:
        """Load apps from cache file"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, app_data in data.items():
                        self.apps[key] = DiscoveredApp(**app_data)
                logger.info(f"Loaded {len(self.apps)} apps from cache")
                return True
        except Exception as e:
            logger.warning(f"Cache load failed: {e}")
        return False
    
    def _save_cache(self):
        """Save apps to cache file"""
        try:
            data = {key: asdict(app) for key, app in self.apps.items()}
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.apps)} apps to cache")
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")
    
    def find_app(self, query: str) -> Optional[DiscoveredApp]:
        """Find an app by name or alias"""
        if not self.apps:
            self.discover_all()
        
        q = query.lower().strip()
        
        # Direct key match
        if q in self.apps:
            return self.apps[q]
        
        # Exact display name match
        for app in self.apps.values():
            if q == app.display_name.lower():
                return app
        
        # Partial key/name match
        for key, app in self.apps.items():
            if q in key or key in q:
                return app
        
        # Alias match
        for app in self.apps.values():
            if app.matches(q):
                return app
        
        return None
    
    def search_apps(self, query: str, limit: int = 10) -> List[DiscoveredApp]:
        """Search for apps matching a query"""
        if not self.apps:
            self.discover_all()
        
        q = query.lower().strip()
        results = []
        
        for app in self.apps.values():
            if q in app.name or q in app.display_name.lower() or app.matches(q):
                results.append(app)
                if len(results) >= limit:
                    break
        
        return results
    
    def get_all_apps(self) -> List[DiscoveredApp]:
        """Get all discovered apps"""
        if not self.apps:
            self.discover_all()
        return list(self.apps.values())
    
    def get_apps_by_category(self) -> Dict[str, List[DiscoveredApp]]:
        """Get apps grouped by category"""
        if not self.apps:
            self.discover_all()
        
        categories = {}
        for app in self.apps.values():
            if app.category not in categories:
                categories[app.category] = []
            categories[app.category].append(app)
        
        return categories


# Singleton instance
_discovery_instance: Optional[AppDiscovery] = None

def get_app_discovery() -> AppDiscovery:
    """Get the singleton app discovery instance"""
    global _discovery_instance
    if _discovery_instance is None:
        _discovery_instance = AppDiscovery()
    return _discovery_instance


def discover_all_apps(force_refresh: bool = False) -> Dict[str, DiscoveredApp]:
    """Discover all apps on the system"""
    return get_app_discovery().discover_all(force_refresh)


def find_app(query: str) -> Optional[DiscoveredApp]:
    """Find an app by name or alias"""
    return get_app_discovery().find_app(query)


def list_all_apps() -> List[str]:
    """Get a list of all discovered app names"""
    discovery = get_app_discovery()
    discovery.discover_all()
    return sorted([app.display_name for app in discovery.apps.values()])


if __name__ == "__main__":
    # Test app discovery
    logging.basicConfig(level=logging.INFO)
    
    discovery = AppDiscovery()
    apps = discovery.discover_all(force_refresh=True)
    
    print(f"\n=== Discovered {len(apps)} Applications ===\n")
    
    # Show by category
    by_category = discovery.get_apps_by_category()
    for category, app_list in sorted(by_category.items()):
        print(f"\n{category.upper()} ({len(app_list)}):")
        for app in sorted(app_list, key=lambda x: x.display_name)[:10]:
            print(f"  - {app.display_name}")
        if len(app_list) > 10:
            print(f"  ... and {len(app_list) - 10} more")
    
    # Test search
    print("\n=== Search Tests ===")
    test_queries = ["chrome", "code", "notepad", "browser", "music"]
    for query in test_queries:
        result = discovery.find_app(query)
        if result:
            print(f"'{query}' -> {result.display_name} ({result.source})")
        else:
            print(f"'{query}' -> Not found")
