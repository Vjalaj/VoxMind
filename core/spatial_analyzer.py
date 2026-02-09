"""
VoxMind Spatial Analyzer
=========================
Analyzes spatial relationships between UI elements.

This enables natural language targeting like:
- "the button on the left"
- "next to the search box"
- "above the submit button"
- "in the sidebar"
- "the first option"
- "the menu at the top"

Spatial Concepts:
1. Absolute position (top, bottom, left, right, center)
2. Relative position (next to, above, below, inside)
3. Grouping (sidebar, toolbar, form, menu)
4. Ordering (first, second, last)
5. Distance (near, far, closest)
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict
from enum import Enum
import math

logger = logging.getLogger(__name__)


# === Enums ===

class ScreenRegion(Enum):
    """Named screen regions."""
    TOP_LEFT = "top-left"
    TOP = "top"
    TOP_RIGHT = "top-right"
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM = "bottom"
    BOTTOM_RIGHT = "bottom-right"


class SpatialRelation(Enum):
    """Spatial relationships between elements."""
    LEFT_OF = "left of"
    RIGHT_OF = "right of"
    ABOVE = "above"
    BELOW = "below"
    NEXT_TO = "next to"
    NEAR = "near"
    FAR_FROM = "far from"
    INSIDE = "inside"
    CONTAINS = "contains"
    OVERLAPS = "overlaps"
    ALIGNED_WITH = "aligned with"
    GROUPED_WITH = "grouped with"


class LayoutPattern(Enum):
    """Common layout patterns."""
    SIDEBAR_LEFT = "left sidebar"
    SIDEBAR_RIGHT = "right sidebar"
    TOP_NAV = "top navigation"
    BOTTOM_NAV = "bottom navigation"
    TOOLBAR = "toolbar"
    FORM = "form"
    LIST = "list"
    GRID = "grid"
    CARD = "card"
    MODAL = "modal dialog"
    MENU = "menu"
    DROPDOWN = "dropdown"


# === Data Classes ===

@dataclass
class BoundingBox:
    """Rectangle bounding box."""
    x: int
    y: int
    width: int
    height: int
    
    @property
    def left(self) -> int:
        return self.x
    
    @property
    def right(self) -> int:
        return self.x + self.width
    
    @property
    def top(self) -> int:
        return self.y
    
    @property
    def bottom(self) -> int:
        return self.y + self.height
    
    @property
    def center_x(self) -> int:
        return self.x + self.width // 2
    
    @property
    def center_y(self) -> int:
        return self.y + self.height // 2
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self.center_x, self.center_y)
    
    @property
    def area(self) -> int:
        return self.width * self.height
    
    def contains_point(self, x: int, y: int) -> bool:
        return self.left <= x <= self.right and self.top <= y <= self.bottom
    
    def contains_box(self, other: 'BoundingBox') -> bool:
        return (self.left <= other.left and 
                self.right >= other.right and
                self.top <= other.top and 
                self.bottom >= other.bottom)
    
    def overlaps(self, other: 'BoundingBox') -> bool:
        return not (self.right < other.left or 
                    self.left > other.right or
                    self.bottom < other.top or 
                    self.top > other.bottom)
    
    def distance_to(self, other: 'BoundingBox') -> float:
        """Distance between centers."""
        dx = self.center_x - other.center_x
        dy = self.center_y - other.center_y
        return math.sqrt(dx*dx + dy*dy)
    
    def edge_distance_to(self, other: 'BoundingBox') -> float:
        """Minimum distance between edges."""
        dx = max(0, max(self.left - other.right, other.left - self.right))
        dy = max(0, max(self.top - other.bottom, other.top - self.bottom))
        return math.sqrt(dx*dx + dy*dy)


@dataclass
class SpatialInfo:
    """Spatial information about an element."""
    bbox: BoundingBox
    region: ScreenRegion
    layout_context: Optional[LayoutPattern] = None
    
    # Relationships (filled by analyzer)
    relations: List[Tuple[int, SpatialRelation]] = field(default_factory=list)
    group_id: Optional[int] = None
    order_in_group: int = 0
    
    # Reading order
    reading_order: int = 0  # Position in left-to-right, top-to-bottom order


@dataclass 
class ElementGroup:
    """A group of spatially related elements."""
    id: int
    elements: List[int]  # Element IDs
    pattern: LayoutPattern
    bbox: BoundingBox
    label: str = ""


# === Spatial Analyzer ===

class SpatialAnalyzer:
    """
    Analyzes spatial relationships between UI elements.
    
    Usage:
        analyzer = SpatialAnalyzer()
        
        # Get region
        region = analyzer.get_region(x, y)
        
        # Check relationship
        relation = analyzer.get_relation(elem1, elem2)
        
        # Find elements by spatial query
        matches = analyzer.find_by_query("button on the left", elements)
    """
    
    # Keywords for spatial queries
    POSITION_KEYWORDS = {
        "top": ["top", "upper", "above", "high"],
        "bottom": ["bottom", "lower", "below", "down"],
        "left": ["left", "leftmost", "leftside"],
        "right": ["right", "rightmost", "rightside"],
        "center": ["center", "middle", "central"],
    }
    
    RELATION_KEYWORDS = {
        SpatialRelation.LEFT_OF: ["left of", "to the left", "before"],
        SpatialRelation.RIGHT_OF: ["right of", "to the right", "after"],
        SpatialRelation.ABOVE: ["above", "over", "on top of"],
        SpatialRelation.BELOW: ["below", "under", "beneath"],
        SpatialRelation.NEXT_TO: ["next to", "beside", "adjacent", "by"],
        SpatialRelation.NEAR: ["near", "close to", "around"],
        SpatialRelation.INSIDE: ["in", "inside", "within"],
    }
    
    ORDER_KEYWORDS = {
        1: ["first", "1st", "top", "initial"],
        2: ["second", "2nd"],
        3: ["third", "3rd"],
        -1: ["last", "final", "bottom", "end"],
    }
    
    LAYOUT_KEYWORDS = {
        LayoutPattern.SIDEBAR_LEFT: ["sidebar", "left panel", "nav panel"],
        LayoutPattern.TOP_NAV: ["navbar", "navigation bar", "header", "top bar"],
        LayoutPattern.TOOLBAR: ["toolbar", "tool bar", "action bar"],
        LayoutPattern.FORM: ["form", "input area"],
        LayoutPattern.MENU: ["menu", "dropdown"],
        LayoutPattern.MODAL: ["dialog", "modal", "popup", "overlay"],
    }
    
    def __init__(self, screen_width: int = 1920, screen_height: int = 1080):
        self.screen_width = screen_width
        self.screen_height = screen_height
    
    def get_region(self, x: int, y: int) -> ScreenRegion:
        """
        Determine which screen region a point is in.
        
        Divides screen into 3x3 grid.
        """
        # Calculate column (left, center, right)
        if x < self.screen_width * 0.33:
            col = 0
        elif x < self.screen_width * 0.66:
            col = 1
        else:
            col = 2
        
        # Calculate row (top, middle, bottom)
        if y < self.screen_height * 0.33:
            row = 0
        elif y < self.screen_height * 0.66:
            row = 1
        else:
            row = 2
        
        # Map to region
        regions = [
            [ScreenRegion.TOP_LEFT, ScreenRegion.TOP, ScreenRegion.TOP_RIGHT],
            [ScreenRegion.LEFT, ScreenRegion.CENTER, ScreenRegion.RIGHT],
            [ScreenRegion.BOTTOM_LEFT, ScreenRegion.BOTTOM, ScreenRegion.BOTTOM_RIGHT],
        ]
        
        return regions[row][col]
    
    def get_region_for_bbox(self, bbox: BoundingBox) -> ScreenRegion:
        """Get region for a bounding box (uses center)."""
        return self.get_region(bbox.center_x, bbox.center_y)
    
    def get_relation(self, elem1: BoundingBox, elem2: BoundingBox) -> SpatialRelation:
        """
        Determine spatial relationship between two elements.
        
        Returns the relation of elem2 TO elem1.
        "elem2 is ___ elem1"
        """
        # Check containment
        if elem1.contains_box(elem2):
            return SpatialRelation.CONTAINS
        if elem2.contains_box(elem1):
            return SpatialRelation.INSIDE
        
        # Check overlap
        if elem1.overlaps(elem2):
            return SpatialRelation.OVERLAPS
        
        # Calculate direction
        dx = elem2.center_x - elem1.center_x
        dy = elem2.center_y - elem1.center_y
        
        # Check proximity
        distance = elem1.edge_distance_to(elem2)
        if distance < 10:
            return SpatialRelation.NEXT_TO
        elif distance < 50:
            return SpatialRelation.NEAR
        
        # Determine primary direction
        if abs(dx) > abs(dy):
            return SpatialRelation.RIGHT_OF if dx > 0 else SpatialRelation.LEFT_OF
        else:
            return SpatialRelation.BELOW if dy > 0 else SpatialRelation.ABOVE
    
    def is_aligned(
        self, 
        elem1: BoundingBox, 
        elem2: BoundingBox, 
        tolerance: int = 10
    ) -> Tuple[bool, bool]:
        """
        Check if elements are aligned.
        
        Returns:
            (horizontally_aligned, vertically_aligned)
        """
        h_aligned = abs(elem1.center_y - elem2.center_y) < tolerance
        v_aligned = abs(elem1.center_x - elem2.center_x) < tolerance
        
        return (h_aligned, v_aligned)
    
    def detect_groups(
        self, 
        elements: List[Tuple[int, BoundingBox]],
        distance_threshold: int = 100
    ) -> List[ElementGroup]:
        """
        Detect groups of spatially related elements.
        
        Uses clustering based on proximity.
        """
        if not elements:
            return []
        
        groups = []
        used = set()
        group_id = 0
        
        for i, (elem_id, bbox) in enumerate(elements):
            if elem_id in used:
                continue
            
            # Start new group
            group_elements = [elem_id]
            group_bbox = BoundingBox(bbox.x, bbox.y, bbox.width, bbox.height)
            used.add(elem_id)
            
            # Find nearby elements
            for j, (other_id, other_bbox) in enumerate(elements):
                if other_id in used:
                    continue
                
                # Check if close to any element in group
                if bbox.edge_distance_to(other_bbox) < distance_threshold:
                    group_elements.append(other_id)
                    used.add(other_id)
                    
                    # Expand group bbox
                    group_bbox = BoundingBox(
                        min(group_bbox.x, other_bbox.x),
                        min(group_bbox.y, other_bbox.y),
                        max(group_bbox.right, other_bbox.right) - min(group_bbox.x, other_bbox.x),
                        max(group_bbox.bottom, other_bbox.bottom) - min(group_bbox.y, other_bbox.y),
                    )
            
            if len(group_elements) > 1:
                # Detect layout pattern
                pattern = self._detect_pattern(group_elements, elements)
                
                groups.append(ElementGroup(
                    id=group_id,
                    elements=group_elements,
                    pattern=pattern,
                    bbox=group_bbox,
                ))
                group_id += 1
        
        return groups
    
    def _detect_pattern(
        self, 
        group_ids: List[int], 
        all_elements: List[Tuple[int, BoundingBox]]
    ) -> LayoutPattern:
        """Detect layout pattern for a group."""
        
        # Get bboxes for group
        bboxes = []
        for elem_id, bbox in all_elements:
            if elem_id in group_ids:
                bboxes.append(bbox)
        
        if not bboxes:
            return LayoutPattern.LIST
        
        # Check if vertical list (stacked)
        if all(abs(b.center_x - bboxes[0].center_x) < 50 for b in bboxes):
            return LayoutPattern.LIST
        
        # Check if horizontal toolbar
        if all(abs(b.center_y - bboxes[0].center_y) < 30 for b in bboxes):
            return LayoutPattern.TOOLBAR
        
        # Check if grid
        x_positions = set(b.x for b in bboxes)
        y_positions = set(b.y for b in bboxes)
        if len(x_positions) > 1 and len(y_positions) > 1:
            return LayoutPattern.GRID
        
        return LayoutPattern.LIST
    
    def compute_reading_order(
        self, 
        elements: List[Tuple[int, BoundingBox]]
    ) -> Dict[int, int]:
        """
        Compute reading order (left-to-right, top-to-bottom).
        
        Returns:
            Dict mapping element ID to order position
        """
        # Sort by Y first (top to bottom), then X (left to right)
        sorted_elements = sorted(
            elements,
            key=lambda e: (e[1].center_y // 50, e[1].center_x)  # Group by rows
        )
        
        return {elem_id: i for i, (elem_id, _) in enumerate(sorted_elements)}
    
    def find_by_query(
        self, 
        query: str, 
        elements: List[Tuple[int, BoundingBox]]
    ) -> List[Tuple[int, float]]:
        """
        Find elements matching a spatial query.
        
        Args:
            query: Natural language like "button on the left"
            elements: List of (id, bbox) tuples
        
        Returns:
            List of (id, score) tuples
        """
        query_lower = query.lower()
        scores = {elem_id: 0.0 for elem_id, _ in elements}
        
        # Check position keywords
        for position, keywords in self.POSITION_KEYWORDS.items():
            for kw in keywords:
                if kw in query_lower:
                    for elem_id, bbox in elements:
                        region = self.get_region_for_bbox(bbox)
                        if position in region.value:
                            scores[elem_id] += 2.0
        
        # Check order keywords
        reading_order = self.compute_reading_order(elements)
        for order, keywords in self.ORDER_KEYWORDS.items():
            for kw in keywords:
                if kw in query_lower:
                    for elem_id, pos in reading_order.items():
                        if order == 1 and pos == 0:
                            scores[elem_id] += 3.0
                        elif order == -1 and pos == len(elements) - 1:
                            scores[elem_id] += 3.0
                        elif order > 0 and pos == order - 1:
                            scores[elem_id] += 3.0
        
        # Check layout keywords
        groups = self.detect_groups(elements)
        for pattern, keywords in self.LAYOUT_KEYWORDS.items():
            for kw in keywords:
                if kw in query_lower:
                    for group in groups:
                        if group.pattern == pattern:
                            for elem_id in group.elements:
                                scores[elem_id] += 2.0
        
        # Return sorted by score
        results = [(elem_id, score) for elem_id, score in scores.items() if score > 0]
        results.sort(key=lambda x: x[1], reverse=True)
        return results
    
    def find_nearest(
        self, 
        target: BoundingBox, 
        candidates: List[Tuple[int, BoundingBox]],
        direction: Optional[SpatialRelation] = None
    ) -> Optional[int]:
        """
        Find nearest element to target.
        
        Args:
            target: Reference element
            candidates: Elements to search
            direction: Optional direction filter (LEFT_OF, RIGHT_OF, etc.)
        
        Returns:
            ID of nearest element or None
        """
        best_id = None
        best_distance = float('inf')
        
        for elem_id, bbox in candidates:
            # Check direction filter
            if direction:
                relation = self.get_relation(target, bbox)
                if relation != direction:
                    continue
            
            distance = target.edge_distance_to(bbox)
            if distance < best_distance:
                best_distance = distance
                best_id = elem_id
        
        return best_id
    
    def describe_position(self, bbox: BoundingBox) -> str:
        """Generate human-readable position description."""
        region = self.get_region_for_bbox(bbox)
        
        # Map to natural language
        descriptions = {
            ScreenRegion.TOP_LEFT: "in the top-left corner",
            ScreenRegion.TOP: "at the top",
            ScreenRegion.TOP_RIGHT: "in the top-right corner",
            ScreenRegion.LEFT: "on the left side",
            ScreenRegion.CENTER: "in the center",
            ScreenRegion.RIGHT: "on the right side",
            ScreenRegion.BOTTOM_LEFT: "in the bottom-left corner",
            ScreenRegion.BOTTOM: "at the bottom",
            ScreenRegion.BOTTOM_RIGHT: "in the bottom-right corner",
        }
        
        return descriptions.get(region, "on screen")


# === Singleton ===

_spatial_analyzer: Optional[SpatialAnalyzer] = None


def get_spatial_analyzer() -> SpatialAnalyzer:
    """Get the global spatial analyzer instance."""
    global _spatial_analyzer
    if _spatial_analyzer is None:
        _spatial_analyzer = SpatialAnalyzer()
    return _spatial_analyzer


# === Demo ===

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("VoxMind Spatial Analyzer")
    print("=" * 40)
    
    analyzer = get_spatial_analyzer()
    
    # Create test elements
    elements = [
        (1, BoundingBox(10, 10, 100, 30)),      # Top-left
        (2, BoundingBox(200, 10, 100, 30)),     # Top
        (3, BoundingBox(1800, 10, 100, 30)),    # Top-right
        (4, BoundingBox(10, 500, 100, 30)),     # Left
        (5, BoundingBox(900, 500, 100, 30)),    # Center
        (6, BoundingBox(1800, 500, 100, 30)),   # Right
        (7, BoundingBox(10, 1000, 100, 30)),    # Bottom-left
    ]
    
    print("\nElement Regions:")
    for elem_id, bbox in elements:
        region = analyzer.get_region_for_bbox(bbox)
        print(f"  Element {elem_id}: {region.value}")
    
    print("\nSpatial Relationships:")
    for i, (id1, bbox1) in enumerate(elements[:3]):
        for id2, bbox2 in elements[i+1:4]:
            relation = analyzer.get_relation(bbox1, bbox2)
            print(f"  {id2} is {relation.value} {id1}")
    
    print("\nReading Order:")
    order = analyzer.compute_reading_order(elements)
    for elem_id, pos in sorted(order.items(), key=lambda x: x[1]):
        print(f"  {pos+1}. Element {elem_id}")
    
    print("\nSpatial Queries:")
    queries = [
        "button on the left",
        "top right",
        "first element",
        "last element",
    ]
    for query in queries:
        matches = analyzer.find_by_query(query, elements)
        if matches:
            print(f"  '{query}' -> Element {matches[0][0]} (score: {matches[0][1]:.1f})")
        else:
            print(f"  '{query}' -> no match")
