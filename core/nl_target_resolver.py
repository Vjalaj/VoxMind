"""
VoxMind Natural Language Target Resolver
==========================================
Resolves natural language descriptions to specific UI elements.

This is the "brain" that understands commands like:
- "Click the settings icon"
- "The red error message at the top"
- "Submit button next to cancel"
- "The first option in the dropdown"

Architecture:
    User Command
         ↓
    ┌─────────────────────────────────┐
    │   Natural Language Parser       │
    │   - Extract intent              │
    │   - Extract constraints         │
    │   - Extract references          │
    └─────────────────────────────────┘
         ↓
    ┌─────────────────────────────────┐
    │   Multimodal Matcher            │
    │   - Visual: icons, colors       │
    │   - Textual: labels, OCR        │
    │   - Spatial: position, relation │
    │   - Context: app state          │
    └─────────────────────────────────┘
         ↓
    ┌─────────────────────────────────┐
    │   Candidate Ranker              │
    │   - Score each element          │
    │   - Apply disambiguation        │
    │   - Select best match           │
    └─────────────────────────────────┘
         ↓
    Target Element
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict, Any, Set
from enum import Enum

logger = logging.getLogger(__name__)


# === Import sibling modules ===

try:
    from core.icon_semantics import get_icon_library, IconDefinition
    HAS_ICONS = True
except ImportError:
    HAS_ICONS = False

try:
    from core.color_analyzer import get_color_analyzer, ColorName, ColorSemantic
    HAS_COLORS = True
except ImportError:
    HAS_COLORS = False

try:
    from core.spatial_analyzer import (
        get_spatial_analyzer, 
        BoundingBox, 
        ScreenRegion,
        SpatialRelation
    )
    HAS_SPATIAL = True
except ImportError:
    HAS_SPATIAL = False


# === Enums ===

class QueryIntent(Enum):
    """What the user wants to do."""
    CLICK = "click"
    FIND = "find"
    READ = "read"
    TYPE = "type"
    SELECT = "select"
    SCROLL = "scroll"
    HOVER = "hover"
    FOCUS = "focus"


class ConstraintType(Enum):
    """Types of element constraints."""
    TEXT = "text"           # Has specific text
    ICON = "icon"           # Has specific icon
    COLOR = "color"         # Has specific color
    POSITION = "position"   # In specific region
    RELATION = "relation"   # Relative to another element
    TYPE = "type"           # Element type (button, link, etc.)
    ORDER = "order"         # Ordinal position (first, second, etc.)
    STATE = "state"         # Element state (enabled, focused, etc.)


# === Data Classes ===

@dataclass
class Constraint:
    """A constraint on which elements can match."""
    type: ConstraintType
    value: Any
    confidence: float = 1.0
    negated: bool = False  # "not the red one"


@dataclass
class ElementReference:
    """A reference to another element for relative positioning."""
    description: str
    resolved_id: Optional[int] = None


@dataclass
class ParsedQuery:
    """Parsed natural language query."""
    original: str
    intent: QueryIntent
    constraints: List[Constraint]
    references: List[ElementReference]
    
    # Extracted entities
    text_targets: List[str] = field(default_factory=list)
    icon_targets: List[str] = field(default_factory=list)
    color_targets: List[str] = field(default_factory=list)
    position_targets: List[str] = field(default_factory=list)
    type_targets: List[str] = field(default_factory=list)


@dataclass
class MatchScore:
    """Scoring breakdown for an element match."""
    element_id: int
    total_score: float
    text_score: float = 0.0
    icon_score: float = 0.0
    color_score: float = 0.0
    position_score: float = 0.0
    type_score: float = 0.0
    context_score: float = 0.0
    reasons: List[str] = field(default_factory=list)


@dataclass
class ResolvedTarget:
    """A resolved target element."""
    element_id: int
    confidence: float
    score: MatchScore
    alternatives: List[MatchScore] = field(default_factory=list)


# === Query Parser ===

class QueryParser:
    """
    Parses natural language queries into structured representations.
    
    Examples:
        "click the settings button" ->
            intent: CLICK
            constraints: [type=button, icon=settings]
        
        "red error message at the top" ->
            intent: FIND
            constraints: [color=red, text=error, position=top]
    """
    
    # Intent patterns
    INTENT_PATTERNS = {
        QueryIntent.CLICK: r"\b(click|press|tap|hit|select|choose|pick)\b",
        QueryIntent.FIND: r"\b(find|locate|show|where|look for)\b",
        QueryIntent.READ: r"\b(read|what does|what's|tell me)\b",
        QueryIntent.TYPE: r"\b(type|enter|input|write)\b",
        QueryIntent.SCROLL: r"\b(scroll|swipe)\b",
        QueryIntent.HOVER: r"\b(hover|mouse over)\b",
        QueryIntent.FOCUS: r"\b(focus|go to|move to)\b",
    }
    
    # Type patterns
    TYPE_PATTERNS = {
        "button": r"\b(button|btn)\b",
        "link": r"\b(link|hyperlink)\b",
        "input": r"\b(input|field|textbox|text box|edit)\b",
        "checkbox": r"\b(checkbox|check box|toggle)\b",
        "dropdown": r"\b(dropdown|drop down|select|combobox)\b",
        "menu": r"\b(menu)\b",
        "tab": r"\b(tab)\b",
        "icon": r"\b(icon)\b",
        "image": r"\b(image|picture|photo)\b",
        "text": r"\b(text|label|message)\b",
    }
    
    # Position patterns
    POSITION_PATTERNS = {
        "top": r"\b(top|upper|above)\b",
        "bottom": r"\b(bottom|lower|below)\b",
        "left": r"\b(left)\b",
        "right": r"\b(right)\b",
        "center": r"\b(center|middle)\b",
        "corner": r"\b(corner)\b",
    }
    
    # Color patterns
    COLOR_PATTERNS = {
        "red": r"\b(red)\b",
        "green": r"\b(green)\b",
        "blue": r"\b(blue)\b",
        "yellow": r"\b(yellow)\b",
        "orange": r"\b(orange)\b",
        "gray": r"\b(gray|grey)\b",
        "black": r"\b(black)\b",
        "white": r"\b(white)\b",
    }
    
    # Order patterns
    ORDER_PATTERNS = {
        1: r"\b(first|1st)\b",
        2: r"\b(second|2nd)\b",
        3: r"\b(third|3rd)\b",
        4: r"\b(fourth|4th)\b",
        5: r"\b(fifth|5th)\b",
        -1: r"\b(last|final)\b",
        -2: r"\b(second.?last|2nd.?last)\b",
    }
    
    # Relation patterns
    RELATION_PATTERNS = {
        "next_to": r"\b(next to|beside|by|near)\b",
        "left_of": r"\b(left of|before)\b",
        "right_of": r"\b(right of|after)\b",
        "above": r"\b(above|over)\b",
        "below": r"\b(below|under|beneath)\b",
        "inside": r"\b(in|inside|within)\b",
    }
    
    # State patterns
    STATE_PATTERNS = {
        "enabled": r"\b(enabled|active)\b",
        "disabled": r"\b(disabled|inactive|grayed)\b",
        "focused": r"\b(focused|selected|highlighted)\b",
        "checked": r"\b(checked|ticked|on)\b",
        "unchecked": r"\b(unchecked|unticked|off)\b",
    }
    
    def __init__(self):
        # Compile patterns
        self._intent_compiled = {
            intent: re.compile(pattern, re.IGNORECASE)
            for intent, pattern in self.INTENT_PATTERNS.items()
        }
        
        # Get icon library for icon detection
        self._icon_library = get_icon_library() if HAS_ICONS else None
    
    def parse(self, query: str) -> ParsedQuery:
        """
        Parse a natural language query.
        
        Args:
            query: User's natural language command
        
        Returns:
            ParsedQuery with extracted intent and constraints
        """
        query_lower = query.lower()
        
        # Detect intent
        intent = self._detect_intent(query_lower)
        
        # Extract constraints
        constraints = []
        
        # Text constraints - quoted text or remaining nouns
        text_targets = self._extract_quoted_text(query)
        if text_targets:
            for text in text_targets:
                constraints.append(Constraint(
                    type=ConstraintType.TEXT,
                    value=text,
                ))
        
        # Type constraints
        type_targets = self._extract_types(query_lower)
        for t in type_targets:
            constraints.append(Constraint(
                type=ConstraintType.TYPE,
                value=t,
            ))
        
        # Icon constraints
        icon_targets = self._extract_icons(query_lower)
        for icon in icon_targets:
            constraints.append(Constraint(
                type=ConstraintType.ICON,
                value=icon,
            ))
        
        # Color constraints
        color_targets = self._extract_colors(query_lower)
        for color in color_targets:
            constraints.append(Constraint(
                type=ConstraintType.COLOR,
                value=color,
            ))
        
        # Position constraints
        position_targets = self._extract_positions(query_lower)
        for pos in position_targets:
            constraints.append(Constraint(
                type=ConstraintType.POSITION,
                value=pos,
            ))
        
        # Order constraints
        order = self._extract_order(query_lower)
        if order is not None:
            constraints.append(Constraint(
                type=ConstraintType.ORDER,
                value=order,
            ))
        
        # State constraints
        state = self._extract_state(query_lower)
        if state:
            constraints.append(Constraint(
                type=ConstraintType.STATE,
                value=state,
            ))
        
        # Extract references to other elements
        references = self._extract_references(query_lower)
        
        return ParsedQuery(
            original=query,
            intent=intent,
            constraints=constraints,
            references=references,
            text_targets=text_targets,
            icon_targets=icon_targets,
            color_targets=color_targets,
            position_targets=position_targets,
            type_targets=type_targets,
        )
    
    def _detect_intent(self, query: str) -> QueryIntent:
        """Detect the user's intent."""
        for intent, pattern in self._intent_compiled.items():
            if pattern.search(query):
                return intent
        return QueryIntent.CLICK  # Default
    
    def _extract_quoted_text(self, query: str) -> List[str]:
        """Extract text in quotes."""
        patterns = [
            r'"([^"]+)"',
            r"'([^']+)'",
            r'\u201c([^\u201d]+)\u201d',  # Unicode curly double quotes
            r'\u2018([^\u2019]+)\u2019',  # Unicode curly single quotes
        ]
        
        results = []
        for pattern in patterns:
            results.extend(re.findall(pattern, query))
        return results
    
    def _extract_types(self, query: str) -> List[str]:
        """Extract element type references."""
        types = []
        for type_name, pattern in self.TYPE_PATTERNS.items():
            if re.search(pattern, query):
                types.append(type_name)
        return types
    
    def _extract_icons(self, query: str) -> List[str]:
        """Extract icon references."""
        if not self._icon_library:
            return []
        
        icons = []
        icon = self._icon_library.identify_from_text(query)
        if icon:
            icons.append(icon.name)
        return icons
    
    def _extract_colors(self, query: str) -> List[str]:
        """Extract color references."""
        colors = []
        for color, pattern in self.COLOR_PATTERNS.items():
            if re.search(pattern, query):
                colors.append(color)
        return colors
    
    def _extract_positions(self, query: str) -> List[str]:
        """Extract position references."""
        positions = []
        for pos, pattern in self.POSITION_PATTERNS.items():
            if re.search(pattern, query):
                positions.append(pos)
        return positions
    
    def _extract_order(self, query: str) -> Optional[int]:
        """Extract ordinal position."""
        for order, pattern in self.ORDER_PATTERNS.items():
            if re.search(pattern, query):
                return order
        return None
    
    def _extract_state(self, query: str) -> Optional[str]:
        """Extract element state."""
        for state, pattern in self.STATE_PATTERNS.items():
            if re.search(pattern, query):
                return state
        return None
    
    def _extract_references(self, query: str) -> List[ElementReference]:
        """Extract references to other elements."""
        refs = []
        
        for relation, pattern in self.RELATION_PATTERNS.items():
            match = re.search(pattern + r"\s+(?:the\s+)?(.+?)(?:\s|$)", query)
            if match:
                refs.append(ElementReference(
                    description=match.group(1),
                ))
        
        return refs


# === Element Matcher ===

class ElementMatcher:
    """
    Matches constraints against elements using multimodal features.
    """
    
    def __init__(self):
        self._icon_library = get_icon_library() if HAS_ICONS else None
        self._color_analyzer = get_color_analyzer() if HAS_COLORS else None
        self._spatial_analyzer = get_spatial_analyzer() if HAS_SPATIAL else None
    
    def score_element(
        self, 
        element: Dict[str, Any], 
        constraints: List[Constraint]
    ) -> MatchScore:
        """
        Score how well an element matches constraints.
        
        Args:
            element: Element with features (from semiotic analyzer)
            constraints: List of constraints to check
        
        Returns:
            MatchScore with breakdown
        """
        score = MatchScore(
            element_id=element.get('id', 0),
            total_score=0.0,
        )
        
        for constraint in constraints:
            points, reason = self._score_constraint(element, constraint)
            
            if constraint.negated:
                points = -points
            
            score.total_score += points
            
            if points > 0:
                score.reasons.append(reason)
                
                # Track by type
                if constraint.type == ConstraintType.TEXT:
                    score.text_score += points
                elif constraint.type == ConstraintType.ICON:
                    score.icon_score += points
                elif constraint.type == ConstraintType.COLOR:
                    score.color_score += points
                elif constraint.type == ConstraintType.POSITION:
                    score.position_score += points
                elif constraint.type == ConstraintType.TYPE:
                    score.type_score += points
        
        return score
    
    def _score_constraint(
        self, 
        element: Dict[str, Any], 
        constraint: Constraint
    ) -> Tuple[float, str]:
        """Score a single constraint."""
        
        if constraint.type == ConstraintType.TEXT:
            return self._score_text(element, constraint.value)
        
        elif constraint.type == ConstraintType.ICON:
            return self._score_icon(element, constraint.value)
        
        elif constraint.type == ConstraintType.COLOR:
            return self._score_color(element, constraint.value)
        
        elif constraint.type == ConstraintType.POSITION:
            return self._score_position(element, constraint.value)
        
        elif constraint.type == ConstraintType.TYPE:
            return self._score_type(element, constraint.value)
        
        elif constraint.type == ConstraintType.ORDER:
            return self._score_order(element, constraint.value)
        
        elif constraint.type == ConstraintType.STATE:
            return self._score_state(element, constraint.value)
        
        return 0.0, ""
    
    def _score_text(self, element: Dict, target: str) -> Tuple[float, str]:
        """Score text match."""
        target_lower = target.lower()
        
        # Check all text fields
        for field in ['label', 'text', 'name', 'tooltip', 'aria_label']:
            text = element.get(field, '').lower()
            
            if target_lower == text:
                return 5.0, f"exact text match: '{target}'"
            
            if target_lower in text:
                return 3.0, f"text contains: '{target}'"
            
            if text and target_lower in text.split():
                return 2.0, f"word match: '{target}'"
        
        return 0.0, ""
    
    def _score_icon(self, element: Dict, target: str) -> Tuple[float, str]:
        """Score icon match."""
        elem_icon = element.get('icon_type', '').lower()
        
        if elem_icon == target:
            return 4.0, f"icon match: {target}"
        
        # Check aliases
        if self._icon_library:
            icon_def = self._icon_library.identify(target)
            if icon_def and (elem_icon == icon_def.name or elem_icon in icon_def.aliases):
                return 3.0, f"icon alias match: {target}"
        
        return 0.0, ""
    
    def _score_color(self, element: Dict, target: str) -> Tuple[float, str]:
        """Score color match."""
        elem_color = element.get('color_name', '').lower()
        elem_semantic = element.get('color_semantic', '').lower()
        
        if target == elem_color:
            return 3.0, f"color match: {target}"
        
        # Semantic match (red = error, green = success)
        color_semantic_map = {
            'red': 'error',
            'green': 'success',
            'blue': 'info',
            'yellow': 'warning',
            'orange': 'warning',
            'gray': 'disabled',
        }
        
        if target in color_semantic_map:
            if color_semantic_map[target] == elem_semantic:
                return 2.0, f"color semantic match: {target}={elem_semantic}"
        
        return 0.0, ""
    
    def _score_position(self, element: Dict, target: str) -> Tuple[float, str]:
        """Score position match."""
        region = element.get('screen_region', '').lower()
        
        if target in region:
            return 2.0, f"position match: {target}"
        
        return 0.0, ""
    
    def _score_type(self, element: Dict, target: str) -> Tuple[float, str]:
        """Score element type match."""
        control_type = element.get('control_type', '').lower()
        
        # Normalize type names
        type_aliases = {
            'button': ['button', 'btn'],
            'link': ['link', 'hyperlink'],
            'input': ['edit', 'text', 'input', 'textbox'],
            'checkbox': ['checkbox', 'check'],
            'dropdown': ['combobox', 'dropdown', 'select'],
        }
        
        for type_name, aliases in type_aliases.items():
            if target == type_name:
                if any(alias in control_type for alias in aliases):
                    return 2.0, f"type match: {target}"
        
        if target in control_type:
            return 1.5, f"type contains: {target}"
        
        return 0.0, ""
    
    def _score_order(self, element: Dict, target: int) -> Tuple[float, str]:
        """Score ordinal position match."""
        order = element.get('reading_order', -1)
        total = element.get('total_count', 1)
        
        if target > 0:
            # Positive ordinal (first, second, etc.)
            if order == target - 1:
                return 3.0, f"order match: position {target}"
        else:
            # Negative ordinal (last, second-last, etc.)
            if order == total + target:
                return 3.0, f"order match: position {target} from end"
        
        return 0.0, ""
    
    def _score_state(self, element: Dict, target: str) -> Tuple[float, str]:
        """Score element state match."""
        state_map = {
            'enabled': element.get('is_enabled', True),
            'disabled': not element.get('is_enabled', True),
            'focused': element.get('has_focus', False),
            'checked': element.get('is_checked', False),
            'unchecked': not element.get('is_checked', True),
        }
        
        if target in state_map and state_map[target]:
            return 2.0, f"state match: {target}"
        
        return 0.0, ""


# === Target Resolver ===

class NLTargetResolver:
    """
    Main resolver that combines parsing and matching.
    
    Usage:
        resolver = NLTargetResolver()
        
        # From semiotic analyzer elements
        elements = analyzer.analyze_screen().elements
        
        # Resolve query
        target = resolver.resolve("click the settings button", elements)
        if target:
            print(f"Found: {target.element_id}")
    """
    
    def __init__(self):
        self.parser = QueryParser()
        self.matcher = ElementMatcher()
    
    def resolve(
        self, 
        query: str, 
        elements: List[Dict[str, Any]]
    ) -> Optional[ResolvedTarget]:
        """
        Resolve a natural language query to an element.
        
        Args:
            query: Natural language command
            elements: List of elements from semiotic analyzer
        
        Returns:
            ResolvedTarget with best match or None
        """
        # Parse query
        parsed = self.parser.parse(query)
        
        logger.debug(f"Parsed query: intent={parsed.intent}, "
                    f"constraints={len(parsed.constraints)}")
        
        # Score all elements
        scores = []
        for elem in elements:
            score = self.matcher.score_element(elem, parsed.constraints)
            if score.total_score > 0:
                scores.append(score)
        
        if not scores:
            return None
        
        # Sort by score
        scores.sort(key=lambda s: s.total_score, reverse=True)
        
        best = scores[0]
        alternatives = scores[1:5]  # Top 4 alternatives
        
        # Calculate confidence
        if len(scores) == 1:
            confidence = min(1.0, best.total_score / 5.0)
        else:
            # Higher confidence if best is significantly better than second
            gap = best.total_score - scores[1].total_score
            confidence = min(1.0, 0.5 + gap / 10.0)
        
        return ResolvedTarget(
            element_id=best.element_id,
            confidence=confidence,
            score=best,
            alternatives=alternatives,
        )
    
    def resolve_all(
        self, 
        query: str, 
        elements: List[Dict[str, Any]]
    ) -> List[ResolvedTarget]:
        """Resolve query to multiple matching elements."""
        parsed = self.parser.parse(query)
        
        scores = []
        for elem in elements:
            score = self.matcher.score_element(elem, parsed.constraints)
            if score.total_score > 0:
                scores.append(ResolvedTarget(
                    element_id=score.element_id,
                    confidence=min(1.0, score.total_score / 5.0),
                    score=score,
                ))
        
        scores.sort(key=lambda t: t.confidence, reverse=True)
        return scores
    
    def explain(
        self, 
        query: str, 
        elements: List[Dict[str, Any]]
    ) -> str:
        """
        Explain how a query was resolved.
        
        Useful for debugging and user feedback.
        """
        parsed = self.parser.parse(query)
        target = self.resolve(query, elements)
        
        lines = [
            f"Query: {query}",
            f"Intent: {parsed.intent.value}",
            f"Constraints: {len(parsed.constraints)}",
        ]
        
        for c in parsed.constraints:
            lines.append(f"  - {c.type.value}: {c.value}")
        
        if target:
            lines.append(f"\nBest Match: Element {target.element_id}")
            lines.append(f"Confidence: {target.confidence:.1%}")
            lines.append("Reasons:")
            for reason in target.score.reasons:
                lines.append(f"  + {reason}")
            
            if target.alternatives:
                lines.append("\nAlternatives:")
                for alt in target.alternatives[:3]:
                    lines.append(f"  - Element {alt.element_id} (score: {alt.total_score:.1f})")
        else:
            lines.append("\nNo match found")
        
        return "\n".join(lines)


# === Singleton ===

_resolver: Optional[NLTargetResolver] = None


def get_resolver() -> NLTargetResolver:
    """Get the global resolver instance."""
    global _resolver
    if _resolver is None:
        _resolver = NLTargetResolver()
    return _resolver


# === Demo ===

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    print("VoxMind Natural Language Target Resolver")
    print("=" * 50)
    
    resolver = get_resolver()
    
    # Mock elements (normally from semiotic analyzer)
    mock_elements = [
        {
            'id': 1,
            'label': 'Settings',
            'control_type': 'Button',
            'icon_type': 'settings',
            'screen_region': 'top-right',
            'reading_order': 0,
            'total_count': 5,
        },
        {
            'id': 2,
            'label': 'Search',
            'control_type': 'Button',
            'icon_type': 'search',
            'screen_region': 'top',
            'reading_order': 1,
            'total_count': 5,
        },
        {
            'id': 3,
            'label': 'Error: Invalid input',
            'control_type': 'Text',
            'color_name': 'red',
            'color_semantic': 'error',
            'screen_region': 'center',
            'reading_order': 2,
            'total_count': 5,
        },
        {
            'id': 4,
            'label': 'Submit',
            'control_type': 'Button',
            'screen_region': 'bottom-right',
            'reading_order': 3,
            'total_count': 5,
        },
        {
            'id': 5,
            'label': 'Cancel',
            'control_type': 'Button',
            'screen_region': 'bottom-right',
            'reading_order': 4,
            'total_count': 5,
        },
    ]
    
    # Test queries
    test_queries = [
        "click the settings button",
        "the search icon",
        "red error message",
        "submit button",
        "first button",
        "last button",
        "button at the top",
    ]
    
    print("\nResolving queries:")
    print("-" * 50)
    
    for query in test_queries:
        target = resolver.resolve(query, mock_elements)
        if target:
            elem = next(e for e in mock_elements if e['id'] == target.element_id)
            print(f"'{query}'")
            print(f"  -> {elem['label']} (id={target.element_id}, conf={target.confidence:.0%})")
            print(f"     Reasons: {', '.join(target.score.reasons)}")
        else:
            print(f"'{query}' -> No match")
        print()
    
    # Detailed explanation
    print("\n" + "=" * 50)
    print("Detailed explanation:")
    print("-" * 50)
    print(resolver.explain("click the settings button", mock_elements))
