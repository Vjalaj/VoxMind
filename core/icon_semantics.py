"""
VoxMind Icon Semantics Engine
==============================
Maps visual icons and symbols to semantic meanings.

Supports:
- Common UI icon patterns (gear, search, close, etc.)
- Unicode symbols (⚙, 🔍, ✕, etc.)
- Icon name detection from automation IDs
- Template matching for icon images (with OpenCV)

This enables commands like:
    "Click the gear icon"  -> Settings
    "Click the X"          -> Close
    "The magnifying glass" -> Search
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Set
from enum import Enum
import re

logger = logging.getLogger(__name__)


# === Icon Definitions ===

@dataclass
class IconDefinition:
    """Definition of an icon and its semantic meaning."""
    name: str                           # Canonical name: "settings"
    aliases: List[str]                  # Alternative names: ["gear", "cog", "preferences"]
    unicode_symbols: List[str]          # Unicode: ["⚙", "🔧", "⛭"]
    text_patterns: List[str]           # Text hints: ["setting", "config", "preference"]
    automation_patterns: List[str]     # AutomationId patterns: ["settings", "config"]
    semantic_category: str              # Category: "navigation"
    action: str                         # Default action: "open settings"
    description: str = ""               # Human description


class IconLibrary:
    """
    Library of known icons and their meanings.
    
    Usage:
        library = IconLibrary()
        icon = library.identify("⚙")  # Returns "settings"
        icon = library.identify_from_text("gear button")  # Returns "settings"
    """
    
    # Complete icon definitions
    ICONS: List[IconDefinition] = [
        # === Navigation ===
        IconDefinition(
            name="settings",
            aliases=["gear", "cog", "preferences", "options", "config", "configuration"],
            unicode_symbols=["⚙", "🔧", "⛭", "⚒", "🛠"],
            text_patterns=["setting", "prefer", "config", "option"],
            automation_patterns=["settings", "preferences", "options", "config"],
            semantic_category="navigation",
            action="open settings",
            description="Settings or preferences icon",
        ),
        IconDefinition(
            name="search",
            aliases=["magnifier", "magnifying glass", "find", "lookup"],
            unicode_symbols=["🔍", "🔎", "⌕"],
            text_patterns=["search", "find", "lookup", "query"],
            automation_patterns=["search", "find", "query"],
            semantic_category="navigation",
            action="search",
            description="Search or find icon",
        ),
        IconDefinition(
            name="home",
            aliases=["house", "main", "start"],
            unicode_symbols=["🏠", "🏡", "⌂"],
            text_patterns=["home", "main", "start"],
            automation_patterns=["home", "main", "start"],
            semantic_category="navigation",
            action="go home",
            description="Home or main page icon",
        ),
        IconDefinition(
            name="menu",
            aliases=["hamburger", "three lines", "nav menu", "navigation"],
            unicode_symbols=["☰", "≡", "⋮", "⁝", "︙"],
            text_patterns=["menu", "nav", "hamburger"],
            automation_patterns=["menu", "nav", "hamburger"],
            semantic_category="navigation",
            action="open menu",
            description="Menu icon (hamburger)",
        ),
        IconDefinition(
            name="back",
            aliases=["previous", "left arrow", "go back", "return"],
            unicode_symbols=["←", "◄", "⬅", "⇦", "↩", "🔙"],
            text_patterns=["back", "prev", "return"],
            automation_patterns=["back", "previous", "return"],
            semantic_category="navigation",
            action="go back",
            description="Back/previous navigation",
        ),
        IconDefinition(
            name="forward",
            aliases=["next", "right arrow", "go forward"],
            unicode_symbols=["→", "►", "➡", "⇨", "↪", "🔜"],
            text_patterns=["forward", "next"],
            automation_patterns=["forward", "next"],
            semantic_category="navigation",
            action="go forward",
            description="Forward/next navigation",
        ),
        IconDefinition(
            name="refresh",
            aliases=["reload", "sync", "update", "circular arrow"],
            unicode_symbols=["🔄", "↻", "⟳", "↺", "🔃"],
            text_patterns=["refresh", "reload", "sync", "update"],
            automation_patterns=["refresh", "reload", "sync"],
            semantic_category="navigation",
            action="refresh",
            description="Refresh or reload icon",
        ),
        IconDefinition(
            name="help",
            aliases=["question", "support", "info", "faq"],
            unicode_symbols=["❓", "❔", "ℹ", "🛈", "⍰"],
            text_patterns=["help", "support", "faq", "info"],
            automation_patterns=["help", "support", "info"],
            semantic_category="navigation",
            action="get help",
            description="Help or information icon",
        ),
        
        # === Window Controls ===
        IconDefinition(
            name="close",
            aliases=["x", "exit", "dismiss", "cross"],
            unicode_symbols=["✕", "✖", "✗", "❌", "×", "╳", "🗙"],
            text_patterns=["close", "exit", "dismiss"],
            automation_patterns=["close", "exit", "dismiss"],
            semantic_category="window",
            action="close",
            description="Close button",
        ),
        IconDefinition(
            name="minimize",
            aliases=["minus", "hide", "dock"],
            unicode_symbols=["−", "➖", "🗕"],
            text_patterns=["minimize", "hide"],
            automation_patterns=["minimize", "min"],
            semantic_category="window",
            action="minimize",
            description="Minimize window",
        ),
        IconDefinition(
            name="maximize",
            aliases=["fullscreen", "expand", "square"],
            unicode_symbols=["□", "⬜", "🗖", "⛶"],
            text_patterns=["maximize", "fullscreen", "expand"],
            automation_patterns=["maximize", "max", "fullscreen"],
            semantic_category="window",
            action="maximize",
            description="Maximize window",
        ),
        IconDefinition(
            name="restore",
            aliases=["resize", "windowed"],
            unicode_symbols=["🗗", "⧉"],
            text_patterns=["restore", "resize"],
            automation_patterns=["restore"],
            semantic_category="window",
            action="restore",
            description="Restore window size",
        ),
        
        # === Actions ===
        IconDefinition(
            name="add",
            aliases=["plus", "new", "create", "insert"],
            unicode_symbols=["➕", "+", "✚", "⊕"],
            text_patterns=["add", "new", "create", "insert"],
            automation_patterns=["add", "new", "create"],
            semantic_category="action",
            action="add new",
            description="Add or create new item",
        ),
        IconDefinition(
            name="delete",
            aliases=["trash", "remove", "bin", "garbage"],
            unicode_symbols=["🗑", "🗑️", "␡", "✂"],
            text_patterns=["delete", "remove", "trash", "bin"],
            automation_patterns=["delete", "remove", "trash"],
            semantic_category="action",
            action="delete",
            description="Delete or remove item",
        ),
        IconDefinition(
            name="edit",
            aliases=["pencil", "pen", "modify", "write"],
            unicode_symbols=["✏", "✏️", "🖊", "📝", "✎"],
            text_patterns=["edit", "modify", "change"],
            automation_patterns=["edit", "modify"],
            semantic_category="action",
            action="edit",
            description="Edit or modify item",
        ),
        IconDefinition(
            name="save",
            aliases=["disk", "floppy", "store"],
            unicode_symbols=["💾", "🖫"],
            text_patterns=["save", "store"],
            automation_patterns=["save", "store"],
            semantic_category="action",
            action="save",
            description="Save item",
        ),
        IconDefinition(
            name="copy",
            aliases=["duplicate", "clipboard"],
            unicode_symbols=["📋", "⎘", "⧉"],
            text_patterns=["copy", "duplicate"],
            automation_patterns=["copy", "duplicate"],
            semantic_category="action",
            action="copy",
            description="Copy to clipboard",
        ),
        IconDefinition(
            name="paste",
            aliases=["clipboard paste"],
            unicode_symbols=["📋", "📄"],
            text_patterns=["paste"],
            automation_patterns=["paste"],
            semantic_category="action",
            action="paste",
            description="Paste from clipboard",
        ),
        IconDefinition(
            name="undo",
            aliases=["revert", "back arrow"],
            unicode_symbols=["↶", "⎌", "↩"],
            text_patterns=["undo", "revert"],
            automation_patterns=["undo", "revert"],
            semantic_category="action",
            action="undo",
            description="Undo last action",
        ),
        IconDefinition(
            name="redo",
            aliases=["forward arrow"],
            unicode_symbols=["↷", "↪"],
            text_patterns=["redo"],
            automation_patterns=["redo"],
            semantic_category="action",
            action="redo",
            description="Redo last action",
        ),
        
        # === Media ===
        IconDefinition(
            name="play",
            aliases=["start", "resume", "triangle"],
            unicode_symbols=["▶", "►", "⏵", "▷"],
            text_patterns=["play", "start", "resume"],
            automation_patterns=["play", "start"],
            semantic_category="media",
            action="play",
            description="Play media",
        ),
        IconDefinition(
            name="pause",
            aliases=["hold", "suspend"],
            unicode_symbols=["⏸", "❚❚", "⏯", "▐▐"],
            text_patterns=["pause", "hold"],
            automation_patterns=["pause"],
            semantic_category="media",
            action="pause",
            description="Pause media",
        ),
        IconDefinition(
            name="stop",
            aliases=["halt", "square"],
            unicode_symbols=["⏹", "■", "◼"],
            text_patterns=["stop", "halt"],
            automation_patterns=["stop"],
            semantic_category="media",
            action="stop",
            description="Stop media",
        ),
        IconDefinition(
            name="volume",
            aliases=["speaker", "sound", "audio"],
            unicode_symbols=["🔊", "🔉", "🔈", "🔇", "🔕"],
            text_patterns=["volume", "sound", "audio", "speaker"],
            automation_patterns=["volume", "sound", "audio"],
            semantic_category="media",
            action="adjust volume",
            description="Volume control",
        ),
        IconDefinition(
            name="mute",
            aliases=["silence", "no sound"],
            unicode_symbols=["🔇", "🔕"],
            text_patterns=["mute", "silence"],
            automation_patterns=["mute"],
            semantic_category="media",
            action="mute",
            description="Mute audio",
        ),
        
        # === Files ===
        IconDefinition(
            name="file",
            aliases=["document", "doc", "page"],
            unicode_symbols=["📄", "📃", "📝", "🗎"],
            text_patterns=["file", "document", "doc"],
            automation_patterns=["file", "document"],
            semantic_category="file",
            action="open file",
            description="File or document",
        ),
        IconDefinition(
            name="folder",
            aliases=["directory", "dir"],
            unicode_symbols=["📁", "📂", "🗀", "🗁"],
            text_patterns=["folder", "directory", "dir"],
            automation_patterns=["folder", "directory"],
            semantic_category="file",
            action="open folder",
            description="Folder or directory",
        ),
        IconDefinition(
            name="download",
            aliases=["save as", "down arrow"],
            unicode_symbols=["⬇", "⬇️", "↓", "📥"],
            text_patterns=["download", "save as"],
            automation_patterns=["download"],
            semantic_category="file",
            action="download",
            description="Download file",
        ),
        IconDefinition(
            name="upload",
            aliases=["attach", "up arrow"],
            unicode_symbols=["⬆", "⬆️", "↑", "📤"],
            text_patterns=["upload", "attach"],
            automation_patterns=["upload", "attach"],
            semantic_category="file",
            action="upload",
            description="Upload file",
        ),
        
        # === User ===
        IconDefinition(
            name="user",
            aliases=["profile", "account", "person", "avatar"],
            unicode_symbols=["👤", "👨", "👩", "🧑", "👥"],
            text_patterns=["user", "profile", "account", "person"],
            automation_patterns=["user", "profile", "account"],
            semantic_category="user",
            action="view profile",
            description="User profile",
        ),
        IconDefinition(
            name="notification",
            aliases=["bell", "alert", "notify"],
            unicode_symbols=["🔔", "🔕", "🛎", "📢"],
            text_patterns=["notification", "alert", "bell"],
            automation_patterns=["notification", "alert", "bell"],
            semantic_category="user",
            action="view notifications",
            description="Notifications",
        ),
        
        # === Status ===
        IconDefinition(
            name="error",
            aliases=["danger", "critical", "fail"],
            unicode_symbols=["❌", "❗", "⛔", "🚫", "⚠"],
            text_patterns=["error", "fail", "critical"],
            automation_patterns=["error", "fail"],
            semantic_category="status",
            action="view error",
            description="Error indicator",
        ),
        IconDefinition(
            name="warning",
            aliases=["caution", "alert"],
            unicode_symbols=["⚠", "⚠️", "⛔", "🔶"],
            text_patterns=["warning", "caution", "alert"],
            automation_patterns=["warning", "caution"],
            semantic_category="status",
            action="view warning",
            description="Warning indicator",
        ),
        IconDefinition(
            name="success",
            aliases=["check", "ok", "done", "complete"],
            unicode_symbols=["✓", "✔", "✅", "☑", "🗸"],
            text_patterns=["success", "complete", "done", "ok"],
            automation_patterns=["success", "complete", "done"],
            semantic_category="status",
            action="confirm",
            description="Success indicator",
        ),
        IconDefinition(
            name="info",
            aliases=["information", "about"],
            unicode_symbols=["ℹ", "ℹ️", "🛈"],
            text_patterns=["info", "about"],
            automation_patterns=["info", "about"],
            semantic_category="status",
            action="view info",
            description="Information indicator",
        ),
        IconDefinition(
            name="loading",
            aliases=["spinner", "progress", "wait"],
            unicode_symbols=["⏳", "⌛", "🔄"],
            text_patterns=["loading", "wait", "progress"],
            automation_patterns=["loading", "progress", "spinner"],
            semantic_category="status",
            action="wait",
            description="Loading indicator",
        ),
        
        # === Misc ===
        IconDefinition(
            name="calendar",
            aliases=["date", "schedule"],
            unicode_symbols=["📅", "📆", "🗓"],
            text_patterns=["calendar", "date", "schedule"],
            automation_patterns=["calendar", "date"],
            semantic_category="misc",
            action="open calendar",
            description="Calendar or date picker",
        ),
        IconDefinition(
            name="clock",
            aliases=["time", "timer"],
            unicode_symbols=["🕐", "⏰", "⌚", "🕑"],
            text_patterns=["clock", "time", "timer"],
            automation_patterns=["clock", "time"],
            semantic_category="misc",
            action="view time",
            description="Clock or time",
        ),
        IconDefinition(
            name="link",
            aliases=["chain", "url", "hyperlink"],
            unicode_symbols=["🔗", "⛓"],
            text_patterns=["link", "url", "hyperlink"],
            automation_patterns=["link", "url"],
            semantic_category="misc",
            action="follow link",
            description="Link or URL",
        ),
        IconDefinition(
            name="share",
            aliases=["send", "forward"],
            unicode_symbols=["📤", "🔗", "↗"],
            text_patterns=["share", "send"],
            automation_patterns=["share", "send"],
            semantic_category="misc",
            action="share",
            description="Share content",
        ),
        IconDefinition(
            name="print",
            aliases=["printer"],
            unicode_symbols=["🖨", "🖶"],
            text_patterns=["print", "printer"],
            automation_patterns=["print"],
            semantic_category="misc",
            action="print",
            description="Print document",
        ),
        IconDefinition(
            name="star",
            aliases=["favorite", "bookmark"],
            unicode_symbols=["⭐", "★", "☆", "🌟"],
            text_patterns=["star", "favorite", "bookmark"],
            automation_patterns=["favorite", "bookmark", "star"],
            semantic_category="misc",
            action="toggle favorite",
            description="Favorite or bookmark",
        ),
        IconDefinition(
            name="lock",
            aliases=["locked", "secure", "password"],
            unicode_symbols=["🔒", "🔐", "🔏"],
            text_patterns=["lock", "secure", "password"],
            automation_patterns=["lock", "secure"],
            semantic_category="misc",
            action="lock",
            description="Lock or security",
        ),
        IconDefinition(
            name="unlock",
            aliases=["unlocked", "open"],
            unicode_symbols=["🔓"],
            text_patterns=["unlock", "open"],
            automation_patterns=["unlock"],
            semantic_category="misc",
            action="unlock",
            description="Unlock",
        ),
    ]
    
    def __init__(self):
        # Build lookup indices for fast matching
        self._by_name: Dict[str, IconDefinition] = {}
        self._by_alias: Dict[str, IconDefinition] = {}
        self._by_symbol: Dict[str, IconDefinition] = {}
        
        for icon in self.ICONS:
            self._by_name[icon.name.lower()] = icon
            
            for alias in icon.aliases:
                self._by_alias[alias.lower()] = icon
            
            for symbol in icon.unicode_symbols:
                self._by_symbol[symbol] = icon
    
    def identify(self, text: str) -> Optional[IconDefinition]:
        """
        Identify an icon from text/symbol.
        
        Args:
            text: Text that might contain icon name, alias, or unicode symbol
        
        Returns:
            IconDefinition if found, None otherwise
        """
        text = text.strip()
        
        # Check unicode symbols first
        for char in text:
            if char in self._by_symbol:
                return self._by_symbol[char]
        
        # Check name
        text_lower = text.lower()
        if text_lower in self._by_name:
            return self._by_name[text_lower]
        
        # Check aliases
        if text_lower in self._by_alias:
            return self._by_alias[text_lower]
        
        # Check partial matches
        for name, icon in self._by_name.items():
            if name in text_lower:
                return icon
        
        for alias, icon in self._by_alias.items():
            if alias in text_lower:
                return icon
        
        return None
    
    def identify_from_text(self, text: str) -> Optional[IconDefinition]:
        """
        Identify icon from descriptive text.
        
        Args:
            text: Descriptive text like "the gear button" or "click settings"
        
        Returns:
            IconDefinition if found
        """
        text_lower = text.lower()
        
        # Try each icon's text patterns
        for icon in self.ICONS:
            for pattern in icon.text_patterns:
                if pattern in text_lower:
                    return icon
            
            # Also check name and aliases
            if icon.name in text_lower:
                return icon
            
            for alias in icon.aliases:
                if alias in text_lower:
                    return icon
        
        return None
    
    def identify_from_automation_id(self, automation_id: str) -> Optional[IconDefinition]:
        """
        Identify icon from UI Automation ID.
        
        Args:
            automation_id: The AutomationId property of a UI element
        
        Returns:
            IconDefinition if found
        """
        id_lower = automation_id.lower()
        
        for icon in self.ICONS:
            for pattern in icon.automation_patterns:
                if pattern in id_lower:
                    return icon
        
        return None
    
    def get_all_names(self) -> List[str]:
        """Get all icon names."""
        return list(self._by_name.keys())
    
    def get_by_category(self, category: str) -> List[IconDefinition]:
        """Get all icons in a category."""
        return [
            icon for icon in self.ICONS
            if icon.semantic_category == category
        ]
    
    def search(self, query: str) -> List[Tuple[IconDefinition, float]]:
        """
        Search icons with relevance scoring.
        
        Returns:
            List of (IconDefinition, score) tuples
        """
        query_lower = query.lower()
        results = []
        
        for icon in self.ICONS:
            score = 0.0
            
            # Exact name match
            if icon.name == query_lower:
                score = 10.0
            elif icon.name in query_lower:
                score = 5.0
            
            # Alias match
            for alias in icon.aliases:
                if alias == query_lower:
                    score = max(score, 8.0)
                elif alias in query_lower:
                    score = max(score, 4.0)
            
            # Pattern match
            for pattern in icon.text_patterns:
                if pattern in query_lower:
                    score = max(score, 3.0)
            
            if score > 0:
                results.append((icon, score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results


# === Singleton ===

_library: Optional[IconLibrary] = None


def get_icon_library() -> IconLibrary:
    """Get the global icon library instance."""
    global _library
    if _library is None:
        _library = IconLibrary()
    return _library


# === Demo ===

if __name__ == "__main__":
    library = get_icon_library()
    
    print("VoxMind Icon Semantics Library")
    print("=" * 40)
    print(f"Total icons: {len(library.ICONS)}")
    print()
    
    # Test identification
    test_cases = [
        "⚙",           # Settings symbol
        "gear",        # Alias
        "🔍",           # Search symbol
        "the close button",  # Descriptive
        "click settings",    # Action
        "hamburger menu",    # Alias
    ]
    
    print("Icon Identification Tests:")
    for test in test_cases:
        icon = library.identify_from_text(test)
        if icon:
            print(f"  '{test}' -> {icon.name} ({icon.semantic_category})")
        else:
            print(f"  '{test}' -> not found")
    
    print()
    print("Categories:")
    categories = set(icon.semantic_category for icon in library.ICONS)
    for cat in sorted(categories):
        icons = library.get_by_category(cat)
        print(f"  {cat}: {len(icons)} icons")
