"""
VoxMind Multimodal Semiotic Analyzer
=====================================
Analyzes screen content across multiple modes to understand meaning:

1. VISUAL MODE   - Icons, colors, shapes, UI patterns
2. TEXTUAL MODE  - Labels, tooltips, OCR text
3. SPATIAL MODE  - Layout, relationships, grouping
4. CONTEXTUAL MODE - App state, task flow, history

This enables natural language targeting like:
    "Click the settings icon"
    "Go to the error message"  
    "Select the submit button"

Instead of just:
    "Click 5"

Architecture:
    ┌─────────────────────────────────────────────────────┐
    │              SemioticAnalyzer (Main)                │
    ├─────────────────────────────────────────────────────┤
    │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
    │  │ Visual   │ │ Textual  │ │ Spatial  │ │Context │ │
    │  │ Analyzer │ │ Analyzer │ │ Analyzer │ │Analyzer│ │
    │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬────┘ │
    │       │            │            │           │      │
    │       └────────────┴────────────┴───────────┘      │
    │                        │                            │
    │              ┌─────────▼─────────┐                  │
    │              │  Semantic Fusion  │                  │
    │              └─────────┬─────────┘                  │
    │                        │                            │
    │              ┌─────────▼─────────┐                  │
    │              │ Element Resolver  │                  │
    │              └───────────────────┘                  │
    └─────────────────────────────────────────────────────┘

Usage:
    from core.semiotic_analyzer import SemioticAnalyzer
    
    analyzer = SemioticAnalyzer()
    
    # Analyze current screen
    screen_model = analyzer.analyze_screen()
    
    # Natural language query
    element = analyzer.find_element("the settings icon")
    element = analyzer.find_element("red error message")
    element = analyzer.find_element("submit button on the right")
    
    # Get element coordinates
    if element:
        x, y = element.center
        click(x, y)
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple, Set
from enum import Enum
from abc import ABC, abstractmethod
import time
import re

logger = logging.getLogger(__name__)


# === Enums ===

class SemanticCategory(Enum):
    """Semantic categories for UI elements."""
    # Actions
    SUBMIT = "submit"
    CANCEL = "cancel"
    CLOSE = "close"
    SAVE = "save"
    DELETE = "delete"
    EDIT = "edit"
    ADD = "add"
    REMOVE = "remove"
    SEARCH = "search"
    REFRESH = "refresh"
    
    # Navigation
    BACK = "back"
    FORWARD = "forward"
    HOME = "home"
    MENU = "menu"
    SETTINGS = "settings"
    HELP = "help"
    
    # Status
    ERROR = "error"
    WARNING = "warning"
    SUCCESS = "success"
    INFO = "info"
    LOADING = "loading"
    
    # Content
    LINK = "link"
    BUTTON = "button"
    INPUT = "input"
    CHECKBOX = "checkbox"
    DROPDOWN = "dropdown"
    TAB = "tab"
    IMAGE = "image"
    TEXT = "text"
    
    # Special
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"
    NOTIFICATION = "notification"
    PROFILE = "profile"
    UNKNOWN = "unknown"


class ColorSemantic(Enum):
    """Color meanings in UI context."""
    ERROR = "error"           # Red
    WARNING = "warning"       # Yellow/Orange
    SUCCESS = "success"       # Green
    INFO = "info"             # Blue
    LINK = "link"             # Blue (underlined)
    DISABLED = "disabled"     # Gray
    PRIMARY = "primary"       # Brand color
    SECONDARY = "secondary"   # Muted
    NEUTRAL = "neutral"       # Default


class SpatialRelation(Enum):
    """Spatial relationships between elements."""
    LEFT_OF = "left of"
    RIGHT_OF = "right of"
    ABOVE = "above"
    BELOW = "below"
    INSIDE = "inside"
    CONTAINS = "contains"
    NEXT_TO = "next to"
    GROUPED_WITH = "grouped with"
    FAR_FROM = "far from"


# === Data Classes ===

@dataclass
class VisualFeatures:
    """Visual features of an element."""
    dominant_color: Tuple[int, int, int] = (128, 128, 128)  # RGB
    color_semantic: ColorSemantic = ColorSemantic.NEUTRAL
    has_icon: bool = False
    icon_type: Optional[str] = None  # "gear", "search", "close", etc.
    shape: str = "rectangle"  # rectangle, circle, rounded
    border_color: Optional[Tuple[int, int, int]] = None
    is_highlighted: bool = False
    is_focused: bool = False


@dataclass
class TextualFeatures:
    """Textual features of an element."""
    label: str = ""
    tooltip: str = ""
    ocr_text: str = ""
    aria_label: str = ""
    placeholder: str = ""
    all_text: str = ""  # Combined
    language: str = "en"
    is_heading: bool = False
    is_link_text: bool = False


@dataclass
class SpatialFeatures:
    """Spatial features and relationships."""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    center: Tuple[int, int] = (0, 0)
    
    # Relative position
    screen_region: str = "center"  # top-left, top, top-right, left, center, right, bottom-left, bottom, bottom-right
    depth: int = 0  # Z-order
    
    # Relationships
    parent_id: Optional[int] = None
    child_ids: List[int] = field(default_factory=list)
    sibling_ids: List[int] = field(default_factory=list)
    nearest_neighbors: List[Tuple[int, SpatialRelation]] = field(default_factory=list)


@dataclass
class ContextualFeatures:
    """Contextual features from app state."""
    app_name: str = ""
    window_title: str = ""
    control_type: str = ""
    automation_id: str = ""
    is_enabled: bool = True
    is_visible: bool = True
    is_modal: bool = False
    has_focus: bool = False
    state: str = ""  # normal, pressed, checked, etc.


@dataclass
class SemanticElement:
    """
    A UI element with full multimodal semantic analysis.
    
    This is the core data structure that combines all modes:
    - Visual features (icons, colors)
    - Textual features (labels, OCR)
    - Spatial features (position, relationships)
    - Contextual features (app state)
    - Semantic category (what it MEANS)
    """
    id: int
    
    # Multimodal features
    visual: VisualFeatures = field(default_factory=VisualFeatures)
    textual: TextualFeatures = field(default_factory=TextualFeatures)
    spatial: SpatialFeatures = field(default_factory=SpatialFeatures)
    context: ContextualFeatures = field(default_factory=ContextualFeatures)
    
    # Semantic understanding
    categories: List[SemanticCategory] = field(default_factory=list)
    semantic_labels: List[str] = field(default_factory=list)  # ["settings", "gear icon", "preferences"]
    confidence: float = 0.0
    
    # Matching
    match_score: float = 0.0  # Score for NL query matching
    match_reasons: List[str] = field(default_factory=list)
    
    @property
    def center(self) -> Tuple[int, int]:
        return self.spatial.center
    
    @property
    def rect(self) -> Tuple[int, int, int, int]:
        return (self.spatial.x, self.spatial.y, self.spatial.width, self.spatial.height)
    
    @property
    def name(self) -> str:
        """Best human-readable name for this element."""
        if self.textual.label:
            return self.textual.label
        if self.textual.aria_label:
            return self.textual.aria_label
        if self.visual.icon_type:
            return f"{self.visual.icon_type} icon"
        if self.categories:
            return self.categories[0].value
        return f"element {self.id}"
    
    def __str__(self):
        return f"SemanticElement({self.id}: {self.name}, {self.categories})"


@dataclass
class ScreenModel:
    """
    Complete semantic model of the current screen.
    """
    elements: List[SemanticElement] = field(default_factory=list)
    timestamp: float = 0.0
    
    # Screen context
    active_app: str = ""
    active_window: str = ""
    screen_size: Tuple[int, int] = (1920, 1080)
    
    # Detected patterns
    has_modal: bool = False
    has_error: bool = False
    has_form: bool = False
    detected_layout: str = ""  # "sidebar", "tabbed", "wizard", etc.
    
    def find_by_id(self, element_id: int) -> Optional[SemanticElement]:
        for elem in self.elements:
            if elem.id == element_id:
                return elem
        return None
    
    def find_by_category(self, category: SemanticCategory) -> List[SemanticElement]:
        return [e for e in self.elements if category in e.categories]
    
    def find_by_text(self, text: str) -> List[SemanticElement]:
        text_lower = text.lower()
        return [e for e in self.elements if text_lower in e.textual.all_text.lower()]


# === Analyzers ===

class BaseAnalyzer(ABC):
    """Base class for modal analyzers."""
    
    @abstractmethod
    def analyze(self, element: SemanticElement, screenshot: Any = None) -> None:
        """Analyze element and update its features."""
        pass


class VisualAnalyzer(BaseAnalyzer):
    """
    Analyzes visual features: icons, colors, shapes.
    
    Uses:
    - Color analysis for semantic meaning
    - Icon recognition via template matching or ML
    - Shape detection for UI patterns
    """
    
    # Icon patterns (text that indicates icon type)
    ICON_PATTERNS = {
        "settings": ["gear", "cog", "settings", "⚙", "🔧", "preferences", "config"],
        "search": ["search", "find", "🔍", "magnif", "lookup"],
        "close": ["close", "x", "×", "✕", "❌", "exit", "dismiss"],
        "menu": ["menu", "☰", "≡", "hamburger", "three lines"],
        "back": ["back", "←", "◄", "<", "previous", "⬅"],
        "forward": ["forward", "→", "►", ">", "next", "➡"],
        "home": ["home", "🏠", "⌂", "house"],
        "refresh": ["refresh", "reload", "🔄", "↻", "sync"],
        "add": ["add", "+", "plus", "new", "create", "➕"],
        "delete": ["delete", "trash", "🗑", "remove", "bin", "×"],
        "edit": ["edit", "✏", "pencil", "modify", "pen", "🖊"],
        "save": ["save", "💾", "disk", "floppy"],
        "help": ["help", "?", "❓", "support", "info", "ℹ"],
        "user": ["user", "profile", "👤", "account", "person", "avatar"],
        "notification": ["notification", "bell", "🔔", "alert", "notify"],
        "download": ["download", "⬇", "↓", "save as"],
        "upload": ["upload", "⬆", "↑", "attach"],
        "copy": ["copy", "📋", "clipboard", "duplicate"],
        "paste": ["paste", "📋"],
        "minimize": ["minimize", "_", "−"],
        "maximize": ["maximize", "□", "⬜", "fullscreen"],
        "play": ["play", "▶", "►", "start"],
        "pause": ["pause", "⏸", "❚❚"],
        "stop": ["stop", "■", "◼"],
    }
    
    # Color semantic mappings (RGB ranges)
    COLOR_SEMANTICS = {
        ColorSemantic.ERROR: [(180, 0, 0), (255, 100, 100)],      # Red
        ColorSemantic.WARNING: [(200, 150, 0), (255, 220, 100)],   # Yellow/Orange
        ColorSemantic.SUCCESS: [(0, 150, 0), (100, 255, 100)],     # Green
        ColorSemantic.INFO: [(0, 100, 200), (100, 180, 255)],      # Blue
        ColorSemantic.LINK: [(0, 0, 200), (100, 100, 255)],        # Blue
        ColorSemantic.DISABLED: [(100, 100, 100), (180, 180, 180)],# Gray
    }
    
    def analyze(self, element: SemanticElement, screenshot: Any = None) -> None:
        """Analyze visual features of an element."""
        # Detect icon type from text hints
        self._detect_icon(element)
        
        # Analyze colors if screenshot available
        if screenshot is not None:
            self._analyze_colors(element, screenshot)
        
        # Update semantic categories based on visual
        self._update_categories(element)
    
    def _detect_icon(self, element: SemanticElement) -> None:
        """Detect icon type from textual hints."""
        all_text = (
            element.textual.label + " " +
            element.textual.aria_label + " " +
            element.textual.tooltip + " " +
            element.context.automation_id
        ).lower()
        
        for icon_type, patterns in self.ICON_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in all_text:
                    element.visual.has_icon = True
                    element.visual.icon_type = icon_type
                    element.semantic_labels.append(f"{icon_type} icon")
                    return
    
    def _analyze_colors(self, element: SemanticElement, screenshot: Any) -> None:
        """Analyze dominant color and semantic meaning."""
        try:
            # Get element region from screenshot
            x, y, w, h = element.rect
            if w <= 0 or h <= 0:
                return
                
            # This would use PIL/OpenCV to get actual colors
            # For now, use placeholder
            # TODO: Implement actual color extraction
            pass
        except Exception as e:
            logger.debug(f"Color analysis error: {e}")
    
    def _update_categories(self, element: SemanticElement) -> None:
        """Update semantic categories based on visual features."""
        icon = element.visual.icon_type
        if icon:
            category_map = {
                "settings": SemanticCategory.SETTINGS,
                "search": SemanticCategory.SEARCH,
                "close": SemanticCategory.CLOSE,
                "menu": SemanticCategory.MENU,
                "back": SemanticCategory.BACK,
                "forward": SemanticCategory.FORWARD,
                "home": SemanticCategory.HOME,
                "refresh": SemanticCategory.REFRESH,
                "add": SemanticCategory.ADD,
                "delete": SemanticCategory.DELETE,
                "edit": SemanticCategory.EDIT,
                "save": SemanticCategory.SAVE,
                "help": SemanticCategory.HELP,
                "user": SemanticCategory.PROFILE,
                "notification": SemanticCategory.NOTIFICATION,
                "minimize": SemanticCategory.MINIMIZE,
                "maximize": SemanticCategory.MAXIMIZE,
            }
            if icon in category_map:
                element.categories.append(category_map[icon])
        
        # Color-based categories
        color_sem = element.visual.color_semantic
        if color_sem == ColorSemantic.ERROR:
            element.categories.append(SemanticCategory.ERROR)
        elif color_sem == ColorSemantic.WARNING:
            element.categories.append(SemanticCategory.WARNING)
        elif color_sem == ColorSemantic.SUCCESS:
            element.categories.append(SemanticCategory.SUCCESS)
        elif color_sem == ColorSemantic.LINK:
            element.categories.append(SemanticCategory.LINK)


class TextualAnalyzer(BaseAnalyzer):
    """
    Analyzes textual content: labels, OCR, tooltips.
    
    Uses:
    - UI Automation text properties
    - OCR for unlabeled elements
    - NLP for understanding text meaning
    """
    
    # Action word patterns
    ACTION_PATTERNS = {
        SemanticCategory.SUBMIT: ["submit", "send", "confirm", "ok", "done", "apply", "continue", "proceed", "go"],
        SemanticCategory.CANCEL: ["cancel", "abort", "discard", "no", "never mind", "dismiss"],
        SemanticCategory.CLOSE: ["close", "exit", "quit", "x"],
        SemanticCategory.SAVE: ["save", "store", "keep", "preserve"],
        SemanticCategory.DELETE: ["delete", "remove", "erase", "clear", "trash"],
        SemanticCategory.EDIT: ["edit", "modify", "change", "update", "rename"],
        SemanticCategory.ADD: ["add", "new", "create", "insert", "plus"],
        SemanticCategory.SEARCH: ["search", "find", "look", "query", "filter"],
        SemanticCategory.REFRESH: ["refresh", "reload", "update", "sync"],
        SemanticCategory.BACK: ["back", "previous", "return", "go back"],
        SemanticCategory.FORWARD: ["forward", "next", "continue", "proceed"],
        SemanticCategory.SETTINGS: ["settings", "preferences", "options", "configure", "config"],
        SemanticCategory.HELP: ["help", "support", "faq", "guide", "how to"],
    }
    
    def __init__(self):
        self._ocr_engine = None
    
    def analyze(self, element: SemanticElement, screenshot: Any = None) -> None:
        """Analyze textual features of an element."""
        # Combine all text sources
        self._combine_text(element)
        
        # Detect semantic category from text
        self._detect_category(element)
        
        # Build semantic labels
        self._build_labels(element)
    
    def _combine_text(self, element: SemanticElement) -> None:
        """Combine all text sources."""
        texts = [
            element.textual.label,
            element.textual.tooltip,
            element.textual.aria_label,
            element.textual.placeholder,
            element.textual.ocr_text,
        ]
        element.textual.all_text = " ".join(t for t in texts if t).strip()
    
    def _detect_category(self, element: SemanticElement) -> None:
        """Detect semantic category from text patterns."""
        text = element.textual.all_text.lower()
        
        for category, patterns in self.ACTION_PATTERNS.items():
            for pattern in patterns:
                if pattern in text:
                    if category not in element.categories:
                        element.categories.append(category)
                    element.match_reasons.append(f"text contains '{pattern}'")
                    return  # First match wins for primary category
    
    def _build_labels(self, element: SemanticElement) -> None:
        """Build semantic labels from text."""
        if element.textual.label:
            element.semantic_labels.append(element.textual.label.lower())
        
        # Add control type as label
        control_type = element.context.control_type.lower()
        if control_type:
            element.semantic_labels.append(control_type)
            
            # Map control types to categories
            type_map = {
                "button": SemanticCategory.BUTTON,
                "link": SemanticCategory.LINK,
                "edit": SemanticCategory.INPUT,
                "text": SemanticCategory.TEXT,
                "checkbox": SemanticCategory.CHECKBOX,
                "combobox": SemanticCategory.DROPDOWN,
                "tab": SemanticCategory.TAB,
                "image": SemanticCategory.IMAGE,
            }
            for type_name, category in type_map.items():
                if type_name in control_type:
                    if category not in element.categories:
                        element.categories.append(category)


class SpatialAnalyzer(BaseAnalyzer):
    """
    Analyzes spatial relationships: position, grouping.
    
    Understands:
    - "the button on the left"
    - "next to the search box"
    - "at the top of the page"
    - "in the sidebar"
    """
    
    def __init__(self, screen_size: Tuple[int, int] = (1920, 1080)):
        self.screen_width, self.screen_height = screen_size
    
    def analyze(self, element: SemanticElement, screenshot: Any = None) -> None:
        """Analyze spatial features."""
        self._compute_center(element)
        self._compute_region(element)
    
    def analyze_relationships(self, elements: List[SemanticElement]) -> None:
        """Analyze relationships between all elements."""
        for elem in elements:
            self._find_neighbors(elem, elements)
    
    def _compute_center(self, element: SemanticElement) -> None:
        """Compute element center."""
        x, y, w, h = element.rect
        element.spatial.center = (x + w // 2, y + h // 2)
    
    def _compute_region(self, element: SemanticElement) -> None:
        """Determine which screen region the element is in."""
        cx, cy = element.spatial.center
        
        # Divide screen into 3x3 grid
        col = "left" if cx < self.screen_width * 0.33 else "right" if cx > self.screen_width * 0.66 else ""
        row = "top" if cy < self.screen_height * 0.33 else "bottom" if cy > self.screen_height * 0.66 else ""
        
        if row and col:
            element.spatial.screen_region = f"{row}-{col}"
        elif row:
            element.spatial.screen_region = row
        elif col:
            element.spatial.screen_region = col
        else:
            element.spatial.screen_region = "center"
        
        element.semantic_labels.append(f"in {element.spatial.screen_region}")
    
    def _find_neighbors(self, element: SemanticElement, all_elements: List[SemanticElement]) -> None:
        """Find nearby elements and their spatial relationships."""
        cx, cy = element.spatial.center
        neighbors = []
        
        for other in all_elements:
            if other.id == element.id:
                continue
            
            ox, oy = other.spatial.center
            dx = ox - cx
            dy = oy - cy
            distance = (dx**2 + dy**2) ** 0.5
            
            if distance < 200:  # Nearby threshold
                # Determine relationship
                if abs(dx) > abs(dy):
                    relation = SpatialRelation.RIGHT_OF if dx > 0 else SpatialRelation.LEFT_OF
                else:
                    relation = SpatialRelation.BELOW if dy > 0 else SpatialRelation.ABOVE
                
                neighbors.append((other.id, relation))
        
        element.spatial.nearest_neighbors = neighbors[:5]  # Top 5


class ContextualAnalyzer(BaseAnalyzer):
    """
    Analyzes contextual features: app state, focus.
    
    Understands:
    - Current application
    - Modal dialogs
    - Form state
    - Task flow
    """
    
    def analyze(self, element: SemanticElement, screenshot: Any = None) -> None:
        """Analyze contextual features."""
        self._detect_state_categories(element)
    
    def _detect_state_categories(self, element: SemanticElement) -> None:
        """Detect categories based on element state."""
        if not element.context.is_enabled:
            element.semantic_labels.append("disabled")
        
        if element.context.has_focus:
            element.semantic_labels.append("focused")
        
        if element.context.is_modal:
            element.semantic_labels.append("modal")


# === Natural Language Resolver ===

class NaturalLanguageResolver:
    """
    Resolves natural language queries to elements.
    
    Examples:
        "click the settings icon" -> finds gear icon
        "red error message" -> finds error with red color
        "submit button on the right" -> finds submit button in right region
        "the search box" -> finds search input
    """
    
    # Query pattern matchers
    PATTERNS = {
        "color": r"\b(red|blue|green|yellow|orange|gray|grey|white|black)\b",
        "position": r"\b(top|bottom|left|right|center|middle|corner)\b",
        "relation": r"\b(next to|beside|near|above|below|under|over)\b",
        "type": r"\b(button|link|icon|input|text|box|field|menu|tab|image)\b",
        "action": r"\b(submit|cancel|close|save|delete|edit|add|search|refresh|settings|help)\b",
        "ordinal": r"\b(first|second|third|last|1st|2nd|3rd)\b",
    }
    
    def __init__(self):
        self._compiled_patterns = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.PATTERNS.items()
        }
    
    def resolve(self, query: str, elements: List[SemanticElement]) -> List[SemanticElement]:
        """
        Find elements matching a natural language query.
        
        Args:
            query: Natural language description like "the settings icon"
            elements: List of analyzed semantic elements
        
        Returns:
            List of matching elements, sorted by match score
        """
        query_lower = query.lower()
        
        # Extract query components
        components = self._parse_query(query_lower)
        
        # Score each element
        matches = []
        for elem in elements:
            score, reasons = self._score_element(elem, query_lower, components)
            if score > 0:
                elem.match_score = score
                elem.match_reasons = reasons
                matches.append(elem)
        
        # Sort by score descending
        matches.sort(key=lambda e: e.match_score, reverse=True)
        
        return matches
    
    def _parse_query(self, query: str) -> Dict[str, List[str]]:
        """Parse query into components."""
        components = {}
        
        for name, pattern in self._compiled_patterns.items():
            matches = pattern.findall(query)
            if matches:
                components[name] = matches
        
        return components
    
    def _score_element(
        self, 
        elem: SemanticElement, 
        query: str, 
        components: Dict[str, List[str]]
    ) -> Tuple[float, List[str]]:
        """Score how well an element matches the query."""
        score = 0.0
        reasons = []
        
        # Direct text match
        elem_text = elem.textual.all_text.lower()
        for word in query.split():
            if len(word) > 2 and word in elem_text:
                score += 2.0
                reasons.append(f"text contains '{word}'")
        
        # Semantic label match
        for label in elem.semantic_labels:
            if label in query:
                score += 3.0
                reasons.append(f"label '{label}' matches")
        
        # Category match
        if "action" in components:
            for action in components["action"]:
                for cat in elem.categories:
                    if action in cat.value:
                        score += 5.0
                        reasons.append(f"action '{action}' matches category")
        
        # Icon match
        if elem.visual.icon_type and elem.visual.icon_type in query:
            score += 4.0
            reasons.append(f"icon type '{elem.visual.icon_type}' matches")
        
        # Type match (button, link, etc.)
        if "type" in components:
            for elem_type in components["type"]:
                if elem_type in elem.context.control_type.lower():
                    score += 2.0
                    reasons.append(f"type '{elem_type}' matches")
                for cat in elem.categories:
                    if elem_type in cat.value:
                        score += 2.0
                        reasons.append(f"type '{elem_type}' matches category")
        
        # Position match
        if "position" in components:
            for pos in components["position"]:
                if pos in elem.spatial.screen_region:
                    score += 1.5
                    reasons.append(f"position '{pos}' matches region")
        
        # Color match
        if "color" in components:
            for color in components["color"]:
                color_map = {
                    "red": ColorSemantic.ERROR,
                    "green": ColorSemantic.SUCCESS,
                    "blue": ColorSemantic.INFO,
                    "yellow": ColorSemantic.WARNING,
                    "orange": ColorSemantic.WARNING,
                    "gray": ColorSemantic.DISABLED,
                    "grey": ColorSemantic.DISABLED,
                }
                if color in color_map and elem.visual.color_semantic == color_map[color]:
                    score += 2.0
                    reasons.append(f"color '{color}' matches")
        
        return score, reasons
    
    def find_best(self, query: str, elements: List[SemanticElement]) -> Optional[SemanticElement]:
        """Find the single best matching element."""
        matches = self.resolve(query, elements)
        return matches[0] if matches else None


# === Main Analyzer ===

class SemioticAnalyzer:
    """
    Main multimodal semiotic analyzer.
    
    Coordinates all analysis modes and provides unified interface.
    """
    
    def __init__(self, screen_size: Tuple[int, int] = (1920, 1080)):
        self.screen_size = screen_size
        
        # Initialize analyzers
        self.visual = VisualAnalyzer()
        self.textual = TextualAnalyzer()
        self.spatial = SpatialAnalyzer(screen_size)
        self.contextual = ContextualAnalyzer()
        self.resolver = NaturalLanguageResolver()
        
        # State
        self._current_model: Optional[ScreenModel] = None
        self._last_analysis_time = 0.0
    
    def analyze_screen(self, screenshot: Any = None) -> ScreenModel:
        """
        Analyze current screen and build semantic model.
        
        Args:
            screenshot: Optional screenshot image for color/OCR analysis
        
        Returns:
            ScreenModel with analyzed elements
        """
        from core.overlay_ui import VoxMindOverlay
        
        model = ScreenModel(
            timestamp=time.time(),
            screen_size=self.screen_size,
        )
        
        # Get raw elements from UI Automation
        try:
            overlay = VoxMindOverlay()
            raw_elements = overlay._detect_ui_elements()
            overlay.stop()
        except Exception as e:
            logger.error(f"Element detection failed: {e}")
            raw_elements = []
        
        # Convert to semantic elements and analyze
        for raw in raw_elements:
            elem = SemanticElement(
                id=raw.number,
                spatial=SpatialFeatures(
                    x=raw.x,
                    y=raw.y,
                    width=raw.width,
                    height=raw.height,
                ),
                textual=TextualFeatures(
                    label=raw.name,
                ),
                context=ContextualFeatures(
                    control_type=raw.control_type,
                ),
            )
            
            # Run all analyzers
            self.visual.analyze(elem, screenshot)
            self.textual.analyze(elem, screenshot)
            self.spatial.analyze(elem, screenshot)
            self.contextual.analyze(elem, screenshot)
            
            model.elements.append(elem)
        
        # Analyze relationships
        self.spatial.analyze_relationships(model.elements)
        
        # Detect screen patterns
        self._detect_patterns(model)
        
        self._current_model = model
        self._last_analysis_time = time.time()
        
        logger.info(f"Analyzed {len(model.elements)} elements")
        return model
    
    def _detect_patterns(self, model: ScreenModel) -> None:
        """Detect high-level patterns in the screen."""
        # Check for modals
        for elem in model.elements:
            if elem.context.is_modal:
                model.has_modal = True
                break
        
        # Check for errors
        model.has_error = any(
            SemanticCategory.ERROR in e.categories
            for e in model.elements
        )
        
        # Check for forms (multiple inputs)
        input_count = sum(
            1 for e in model.elements
            if SemanticCategory.INPUT in e.categories
        )
        model.has_form = input_count >= 2
    
    def find_element(self, query: str) -> Optional[SemanticElement]:
        """
        Find an element by natural language description.
        
        Examples:
            "the settings icon"
            "red error message"
            "submit button"
            "search box on top"
        
        Args:
            query: Natural language description
        
        Returns:
            Best matching SemanticElement or None
        """
        if self._current_model is None:
            self.analyze_screen()
        
        return self.resolver.find_best(query, self._current_model.elements)
    
    def find_elements(self, query: str) -> List[SemanticElement]:
        """Find all elements matching a query."""
        if self._current_model is None:
            self.analyze_screen()
        
        return self.resolver.resolve(query, self._current_model.elements)
    
    def get_element_at(self, x: int, y: int) -> Optional[SemanticElement]:
        """Get the element at specific coordinates."""
        if self._current_model is None:
            return None
        
        for elem in self._current_model.elements:
            ex, ey, ew, eh = elem.rect
            if ex <= x <= ex + ew and ey <= y <= ey + eh:
                return elem
        
        return None
    
    def describe_element(self, element: SemanticElement) -> str:
        """Generate human-readable description of an element."""
        parts = []
        
        # Type
        if element.categories:
            parts.append(element.categories[0].value)
        
        # Name
        if element.textual.label:
            parts.append(f'"{element.textual.label}"')
        elif element.visual.icon_type:
            parts.append(f"{element.visual.icon_type} icon")
        
        # Position
        parts.append(f"in {element.spatial.screen_region}")
        
        # State
        if not element.context.is_enabled:
            parts.append("(disabled)")
        
        return " ".join(parts)
    
    def describe_screen(self) -> str:
        """Generate human-readable description of current screen."""
        if self._current_model is None:
            return "Screen not analyzed"
        
        model = self._current_model
        lines = []
        
        lines.append(f"Screen: {model.active_window or 'Unknown'}")
        lines.append(f"Elements: {len(model.elements)}")
        
        if model.has_modal:
            lines.append("⚠ Modal dialog detected")
        if model.has_error:
            lines.append("❌ Error message detected")
        if model.has_form:
            lines.append("📝 Form detected")
        
        # Key elements
        for cat in [SemanticCategory.SUBMIT, SemanticCategory.CANCEL, SemanticCategory.ERROR]:
            elems = model.find_by_category(cat)
            if elems:
                lines.append(f"  {cat.value}: {elems[0].name}")
        
        return "\n".join(lines)


# === Singleton Instance ===

_analyzer: Optional[SemioticAnalyzer] = None


def get_analyzer() -> SemioticAnalyzer:
    """Get the global semiotic analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = SemioticAnalyzer()
    return _analyzer


# === Demo ===

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("VoxMind Semiotic Analyzer")
    print("=" * 40)
    
    analyzer = get_analyzer()
    
    print("\nAnalyzing screen...")
    model = analyzer.analyze_screen()
    
    print(f"\nFound {len(model.elements)} elements:")
    for elem in model.elements[:10]:
        print(f"  {elem.id}: {elem.name} - {elem.categories}")
    
    print("\n" + analyzer.describe_screen())
    
    # Test natural language queries
    test_queries = [
        "settings icon",
        "submit button",
        "close button",
        "search",
        "the menu",
    ]
    
    print("\nNatural Language Queries:")
    for query in test_queries:
        result = analyzer.find_element(query)
        if result:
            print(f"  '{query}' -> {result.name} (score: {result.match_score:.1f})")
        else:
            print(f"  '{query}' -> not found")
