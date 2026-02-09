"""
VoxMind Smart Overlay Integration
===================================
Bridges the multimodal semiotic analysis system with the overlay UI.

This module enables natural language targeting like:
    "Click the settings icon"
    "The red error message"
    "Submit button next to cancel"

Architecture:
    ┌─────────────────────────────────────────────────────┐
    │                   Smart Overlay                     │
    │  ┌────────────────┐    ┌────────────────────────┐   │
    │  │  Overlay UI    │◄───│  Semiotic Analyzer     │   │
    │  │  (numbers/grid)│    │  (screen understanding)│   │
    │  └────────────────┘    └────────────────────────┘   │
    │          │                       │                  │
    │          ▼                       ▼                  │
    │  ┌────────────────┐    ┌────────────────────────┐   │
    │  │  Element Cache │◄───│  NL Target Resolver    │   │
    │  └────────────────┘    └────────────────────────┘   │
    └─────────────────────────────────────────────────────┘
                             │
                             ▼
                    User Voice Command
                    "click the save button"
"""

import logging
import threading
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple, Callable
from enum import Enum

logger = logging.getLogger(__name__)


# === Import modules ===

try:
    from core.overlay_manager import OverlayManager, ClickResult
    HAS_OVERLAY = True
except ImportError:
    HAS_OVERLAY = False
    logger.warning("Overlay manager not available")
    OverlayManager = None  # type: ignore
    ClickResult = None  # type: ignore

try:
    from core.semiotic_analyzer import (
        SemioticAnalyzer,
        ScreenModel,
        SemanticElement,
        SemanticCategory,
    )
    HAS_SEMIOTIC = True
except ImportError:
    HAS_SEMIOTIC = False
    logger.warning("Semiotic analyzer not available")

try:
    from core.nl_target_resolver import (
        NLTargetResolver,
        ResolvedTarget,
        ParsedQuery,
        QueryIntent,
    )
    HAS_RESOLVER = True
except ImportError:
    HAS_RESOLVER = False
    logger.warning("NL target resolver not available")

try:
    from core.icon_semantics import get_icon_library, IconLibrary
    HAS_ICONS = True
except ImportError:
    HAS_ICONS = False

try:
    from core.color_analyzer import get_color_analyzer, ColorAnalyzer
    HAS_COLORS = True
except ImportError:
    HAS_COLORS = False

try:
    from core.spatial_analyzer import get_spatial_analyzer, SpatialAnalyzer
    HAS_SPATIAL = True
except ImportError:
    HAS_SPATIAL = False


# === Enums ===

class TargetMode(Enum):
    """How to target elements."""
    NUMBER = "number"           # Traditional "click 5"
    NATURAL = "natural"         # "click the settings button"
    GRID = "grid"               # Grid-based targeting
    HYBRID = "hybrid"           # Try natural first, fall back to number


# === Data Classes ===

@dataclass
class EnrichedElement:
    """
    Element with both overlay info and semantic analysis.
    """
    # From overlay
    id: int
    rect: Tuple[int, int, int, int]  # x, y, w, h
    control_type: str
    name: str
    
    # From semiotic analysis
    category: str = "unknown"
    icon_type: Optional[str] = None
    color_name: Optional[str] = None
    color_semantic: Optional[str] = None
    screen_region: Optional[str] = None
    ocr_text: Optional[str] = None
    
    # Relationships
    related_elements: List[int] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for resolver."""
        return {
            'id': self.id,
            'label': self.name,
            'control_type': self.control_type,
            'icon_type': self.icon_type or '',
            'color_name': self.color_name or '',
            'color_semantic': self.color_semantic or '',
            'screen_region': self.screen_region or '',
            'ocr_text': self.ocr_text or '',
            'rect': self.rect,
        }


@dataclass
class SmartClickResult:
    """Result of a smart click operation."""
    success: bool
    message: str
    element_id: Optional[int] = None
    element_name: Optional[str] = None
    confidence: float = 0.0
    method: str = "unknown"  # "number", "natural", "grid"
    alternatives: List[int] = field(default_factory=list)


# === Smart Overlay Manager ===

class SmartOverlay:
    """
    Enhanced overlay system with natural language understanding.
    
    Combines:
    - Visual overlay (numbers, grid)
    - Semiotic analysis (understanding what elements are)
    - Natural language targeting (finding elements by description)
    
    Usage:
        smart = SmartOverlay()
        smart.show()
        
        # By number (traditional)
        result = smart.click("5")
        
        # By description (natural language)
        result = smart.click("the settings button")
        result = smart.click("red error message")
        result = smart.click("submit button at bottom")
    """
    
    def __init__(self, mode: TargetMode = TargetMode.HYBRID):
        """
        Initialize smart overlay.
        
        Args:
            mode: Default targeting mode
        """
        self.mode = mode
        
        # Components
        self._overlay: Optional[OverlayManager] = None
        self._analyzer: Optional[SemioticAnalyzer] = None
        self._resolver: Optional[NLTargetResolver] = None
        self._icon_library: Optional[IconLibrary] = None
        self._color_analyzer: Optional[ColorAnalyzer] = None
        self._spatial_analyzer: Optional[SpatialAnalyzer] = None
        
        # Cache
        self._enriched_elements: List[EnrichedElement] = []
        self._last_screen_model: Optional[ScreenModel] = None
        self._lock = threading.Lock()
        
        # Initialize components
        self._init_components()
    
    def _init_components(self):
        """Initialize all available components."""
        if HAS_OVERLAY:
            self._overlay = OverlayManager()
        else:
            logger.error("Overlay manager is required but not available!")
            raise RuntimeError("Overlay manager not available")
        
        if HAS_SEMIOTIC:
            self._analyzer = SemioticAnalyzer()
        
        if HAS_RESOLVER:
            self._resolver = NLTargetResolver()
        
        if HAS_ICONS:
            self._icon_library = get_icon_library()
        
        if HAS_COLORS:
            self._color_analyzer = get_color_analyzer()
        
        if HAS_SPATIAL:
            self._spatial_analyzer = get_spatial_analyzer()
        
        logger.info(f"SmartOverlay initialized: "
                   f"semiotic={HAS_SEMIOTIC}, resolver={HAS_RESOLVER}, "
                   f"icons={HAS_ICONS}, colors={HAS_COLORS}, spatial={HAS_SPATIAL}")
    
    # === Basic Operations ===
    
    def show(self) -> bool:
        """Show the overlay with numbered elements."""
        if not self._overlay:
            return False
        
        result = self._overlay.show()
        
        if result:
            # Enrich elements with semantic analysis
            self._analyze_and_enrich()
        
        return result
    
    def hide(self) -> bool:
        """Hide the overlay."""
        if not self._overlay:
            return False
        return self._overlay.hide()
    
    def toggle(self) -> bool:
        """Toggle overlay visibility."""
        if not self._overlay:
            return False
        
        if self._overlay.is_visible():
            return self.hide()
        else:
            return self.show()
    
    def refresh(self) -> bool:
        """Refresh overlay and re-analyze screen."""
        if not self._overlay:
            return False
        
        result = self._overlay.refresh()
        
        if result:
            self._analyze_and_enrich()
        
        return result
    
    def show_grid(self, region: Optional[Tuple[int, int, int, int]] = None) -> bool:
        """Show targeting grid overlay."""
        if not self._overlay:
            return False
        return self._overlay.show_grid(region)
    
    # === Semantic Analysis ===
    
    def _analyze_and_enrich(self):
        """Analyze current screen and enrich elements."""
        with self._lock:
            if not self._overlay:
                return
            
            # Get basic elements from overlay
            overlay_elements = self._overlay.get_elements()
            
            # Enrich each element
            enriched = []
            for elem in overlay_elements:
                enriched_elem = self._enrich_element(elem)
                enriched.append(enriched_elem)
            
            self._enriched_elements = enriched
            
            logger.debug(f"Enriched {len(enriched)} elements")
    
    def _enrich_element(self, elem: Dict[str, Any]) -> EnrichedElement:
        """Add semantic information to an element."""
        # Extract from dict
        elem_id = elem.get('id', 0)
        elem_name = elem.get('name', '')
        elem_rect = elem.get('rect', (0, 0, 0, 0))
        elem_type = elem.get('control_type', 'unknown')
        
        enriched = EnrichedElement(
            id=elem_id,
            rect=elem_rect,
            control_type=elem_type,
            name=elem_name,
        )
        
        # Icon detection
        if self._icon_library and elem_name:
            # Try to identify icon from name/automation ID
            icon = self._icon_library.identify_from_text(elem_name)
            if icon:
                enriched.icon_type = icon.name
                enriched.category = icon.category.value if hasattr(icon.category, 'value') else str(icon.category)
        
        # Color analysis (would need screenshot)
        # For now, infer from control type and name
        if self._color_analyzer and elem_name:
            if any(word in elem_name.lower() for word in ['error', 'fail', 'invalid']):
                enriched.color_semantic = 'error'
            elif any(word in elem_name.lower() for word in ['success', 'complete', 'done']):
                enriched.color_semantic = 'success'
            elif any(word in elem_name.lower() for word in ['warning', 'caution']):
                enriched.color_semantic = 'warning'
        
        # Spatial analysis
        if self._spatial_analyzer and elem_rect:
            from core.spatial_analyzer import BoundingBox
            x, y, w, h = elem_rect
            bbox = BoundingBox(left=x, top=y, right=x+w, bottom=y+h)
            region = self._spatial_analyzer.get_region(bbox)
            enriched.screen_region = region.value if hasattr(region, 'value') else str(region)
        
        return enriched
    
    # === Targeting ===
    
    def click(self, target: str) -> SmartClickResult:
        """
        Click a target element.
        
        Args:
            target: Number ("5") or natural language ("the settings button")
        
        Returns:
            SmartClickResult with success info
        """
        target = target.strip()
        
        # Determine targeting method
        if target.isdigit():
            # Pure number
            return self._click_by_number(int(target))
        
        # Check for grid coordinates (e.g., "A5", "B3")
        if len(target) == 2 and target[0].isalpha() and target[1].isdigit():
            return self._click_by_grid(target)
        
        # Natural language
        if self.mode in (TargetMode.NATURAL, TargetMode.HYBRID):
            result = self._click_by_description(target)
            
            if result.success or self.mode == TargetMode.NATURAL:
                return result
            
            # Hybrid: fall back to searching for number in text
            import re
            numbers = re.findall(r'\d+', target)
            if numbers:
                return self._click_by_number(int(numbers[0]))
        
        return SmartClickResult(
            success=False,
            message=f"Could not understand target: '{target}'",
        )
    
    def _click_by_number(self, number: int) -> SmartClickResult:
        """Click element by its number."""
        if not self._overlay:
            return SmartClickResult(
                success=False,
                message="Overlay not available",
            )
        
        result = self._overlay.click_element(number)
        
        if result.success:
            return SmartClickResult(
                success=True,
                message=f"Clicked element {number}",
                element_id=number,
                element_name=result.element_name,
                confidence=1.0,
                method="number",
            )
        else:
            return SmartClickResult(
                success=False,
                message=result.error_message or f"Element {number} not found",
            )
    
    def _click_by_grid(self, coord: str) -> SmartClickResult:
        """Click by grid coordinate."""
        if not self._overlay:
            return SmartClickResult(
                success=False,
                message="Overlay not available",
            )
        
        result = self._overlay.click_grid_cell(coord)
        
        if result.success:
            return SmartClickResult(
                success=True,
                message=f"Clicked grid cell {coord}",
                confidence=1.0,
                method="grid",
            )
        else:
            return SmartClickResult(
                success=False,
                message=result.error_message or f"Grid cell {coord} not valid",
            )
    
    def _click_by_description(self, description: str) -> SmartClickResult:
        """Click element by natural language description."""
        if not self._resolver:
            return SmartClickResult(
                success=False,
                message="Natural language resolver not available",
            )
        
        with self._lock:
            if not self._enriched_elements:
                self._analyze_and_enrich()
        
        # Convert to resolver format
        elements_dict = [e.to_dict() for e in self._enriched_elements]
        
        # Resolve target
        resolved = self._resolver.resolve(description, elements_dict)
        
        if not resolved:
            return SmartClickResult(
                success=False,
                message=f"No element matches '{description}'",
            )
        
        # Click the resolved element
        click_result = self._click_by_number(resolved.element_id)
        
        if click_result.success:
            return SmartClickResult(
                success=True,
                message=f"Clicked '{click_result.element_name}' (matched: {description})",
                element_id=resolved.element_id,
                element_name=click_result.element_name,
                confidence=resolved.confidence,
                method="natural",
                alternatives=[alt.element_id for alt in resolved.alternatives],
            )
        else:
            return SmartClickResult(
                success=False,
                message=click_result.message,
                element_id=resolved.element_id,
                confidence=resolved.confidence,
                alternatives=[alt.element_id for alt in resolved.alternatives],
            )
    
    # === Query API ===
    
    def find(self, description: str) -> List[EnrichedElement]:
        """
        Find elements matching a description.
        
        Args:
            description: Natural language description
        
        Returns:
            List of matching elements
        """
        if not self._resolver:
            return []
        
        with self._lock:
            if not self._enriched_elements:
                self._analyze_and_enrich()
        
        elements_dict = [e.to_dict() for e in self._enriched_elements]
        resolved = self._resolver.resolve_all(description, elements_dict)
        
        # Get elements by ID
        matches = []
        for res in resolved:
            for elem in self._enriched_elements:
                if elem.id == res.element_id:
                    matches.append(elem)
                    break
        
        return matches
    
    def explain(self, description: str) -> str:
        """
        Explain how a description would be resolved.
        
        Args:
            description: Natural language description
        
        Returns:
            Human-readable explanation
        """
        if not self._resolver:
            return "Natural language resolver not available"
        
        with self._lock:
            if not self._enriched_elements:
                self._analyze_and_enrich()
        
        elements_dict = [e.to_dict() for e in self._enriched_elements]
        return self._resolver.explain(description, elements_dict)
    
    def get_element_info(self, element_id: int) -> Optional[EnrichedElement]:
        """Get detailed info about an element."""
        with self._lock:
            for elem in self._enriched_elements:
                if elem.id == element_id:
                    return elem
        return None
    
    def list_elements(self) -> List[EnrichedElement]:
        """List all detected elements."""
        with self._lock:
            return list(self._enriched_elements)
    
    # === Voice Command Handler ===
    
    def handle_command(self, command: str) -> SmartClickResult:
        """
        Handle a voice command.
        
        Supports:
        - "show overlay" / "show numbers"
        - "hide overlay" / "hide numbers"
        - "click 5"
        - "click the settings button"
        - "click red error"
        - "show grid"
        - "click A5"
        - "refresh"
        
        Args:
            command: Voice command
        
        Returns:
            SmartClickResult
        """
        cmd = command.lower().strip()
        
        # Show commands
        if any(x in cmd for x in ['show overlay', 'show numbers', 'start overlay']):
            success = self.show()
            return SmartClickResult(
                success=success,
                message="Overlay shown" if success else "Failed to show overlay",
                method="command",
            )
        
        # Hide commands
        if any(x in cmd for x in ['hide overlay', 'hide numbers', 'stop overlay', 'close overlay']):
            success = self.hide()
            return SmartClickResult(
                success=success,
                message="Overlay hidden" if success else "Failed to hide overlay",
                method="command",
            )
        
        # Grid commands
        if 'show grid' in cmd:
            success = self.show_grid()
            return SmartClickResult(
                success=success,
                message="Grid shown" if success else "Failed to show grid",
                method="command",
            )
        
        # Refresh
        if 'refresh' in cmd:
            success = self.refresh()
            return SmartClickResult(
                success=success,
                message="Overlay refreshed" if success else "Failed to refresh",
                method="command",
            )
        
        # Click commands
        import re
        click_match = re.match(r'(?:click|press|tap|select)\s+(.+)', cmd)
        if click_match:
            target = click_match.group(1)
            return self.click(target)
        
        # Unknown command
        return SmartClickResult(
            success=False,
            message=f"Unknown command: {command}",
        )


# === Singleton ===

_smart_overlay: Optional[SmartOverlay] = None


def get_smart_overlay() -> SmartOverlay:
    """Get the global smart overlay instance."""
    global _smart_overlay
    if _smart_overlay is None:
        _smart_overlay = SmartOverlay()
    return _smart_overlay


# === Demo ===

if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("VoxMind Smart Overlay Demo")
    print("=" * 50)
    print()
    print("This demo shows the integration of:")
    print("  - Visual overlay (numbers)")
    print("  - Semiotic analysis (understanding)")
    print("  - Natural language targeting")
    print()
    print("Commands:")
    print("  show - Show overlay with numbers")
    print("  hide - Hide overlay")
    print("  grid - Show targeting grid")
    print("  click <target> - Click by number or description")
    print("  find <description> - Find matching elements")
    print("  explain <description> - Explain resolution")
    print("  list - List all elements")
    print("  quit - Exit")
    print()
    
    smart = SmartOverlay()
    
    while True:
        try:
            cmd = input("\n> ").strip()
            
            if not cmd:
                continue
            
            if cmd == "quit":
                smart.hide()
                break
            
            if cmd == "show":
                smart.show()
                print("Overlay shown")
                continue
            
            if cmd == "hide":
                smart.hide()
                print("Overlay hidden")
                continue
            
            if cmd == "grid":
                smart.show_grid()
                print("Grid shown")
                continue
            
            if cmd == "list":
                elements = smart.list_elements()
                print(f"\n{len(elements)} elements:")
                for elem in elements[:20]:
                    icon = f" [{elem.icon_type}]" if elem.icon_type else ""
                    region = f" @{elem.screen_region}" if elem.screen_region else ""
                    print(f"  {elem.id}: {elem.name}{icon}{region}")
                if len(elements) > 20:
                    print(f"  ... and {len(elements) - 20} more")
                continue
            
            if cmd.startswith("click "):
                target = cmd[6:]
                result = smart.click(target)
                print(f"\n{result.message}")
                if result.confidence > 0:
                    print(f"  Confidence: {result.confidence:.0%}")
                if result.alternatives:
                    print(f"  Alternatives: {result.alternatives}")
                continue
            
            if cmd.startswith("find "):
                desc = cmd[5:]
                matches = smart.find(desc)
                print(f"\n{len(matches)} matches:")
                for elem in matches[:10]:
                    print(f"  {elem.id}: {elem.name}")
                continue
            
            if cmd.startswith("explain "):
                desc = cmd[8:]
                explanation = smart.explain(desc)
                print(f"\n{explanation}")
                continue
            
            # Try as a full command
            result = smart.handle_command(cmd)
            print(f"\n{result.message}")
            
        except KeyboardInterrupt:
            smart.hide()
            break
        except Exception as e:
            print(f"Error: {e}")
            logger.exception("Command error")
