"""
VoxMind Multi-Modal Context Fusion
==================================
Combines voice, screen, and system context into unified understanding.

Features:
- Fuse OCR text with voice command context
- Use screen content to disambiguate voice commands
- Resolve ambiguous references using screen context
- Context-aware command suggestions

Inspired by:
- Google Assistant Screen Context
- Microsoft Copilot Vision
- Apple Intelligence Screen Awareness
"""

import logging
import threading
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

# ============================================================================
# DATA STRUCTURES
# ============================================================================

class ContextSource(Enum):
    """Sources of context information."""
    VOICE = "voice"
    SCREEN = "screen"
    SYSTEM = "system"
    MEMORY = "memory"


@dataclass
class VoiceContext:
    """Current voice command context."""
    raw_text: str
    parsed_command: str
    entities: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    is_ambiguous: bool = False


@dataclass
class ScreenContext:
    """Current screen context."""
    detected_app: Optional[str] = None
    page_title: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    urls: List[str] = field(default_factory=list)
    text_content: str = ""
    clickable_elements: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class SystemContext:
    """Current system state."""
    active_window: Optional[str] = None
    running_apps: List[str] = field(default_factory=list)
    user_location: Optional[str] = None


@dataclass
class UnifiedContext:
    """Fused context from all sources."""
    voice: Optional[VoiceContext] = None
    screen: Optional[ScreenContext] = None
    system: Optional[SystemContext] = None
    
    # Fusion results
    disambiguated_entities: Dict[str, Any] = field(default_factory=dict)
    suggested_actions: List[str] = field(default_factory=list)
    confidence_boost: float = 0.0
    
    # Metadata
    fusion_method: str = "none"
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# CONTEXT FUSION ENGINE
# ============================================================================

class ContextFusion:
    """
    Multi-Modal Context Fusion Engine.
    
    Combines voice, screen, and system context to improve command understanding.
    
    Usage:
        fusion = ContextFusion()
        
        # Before parsing a command
        fusion.update_voice_context("open that", "app_control", {"target": "that"})
        
        # Get fused context for better understanding
        unified = fusion.fuse_context()
        
        # Use disambiguated entities
        if unified.disambiguated_entities.get('target'):
            print(f"Resolved 'that' to: {unified.disambiguated_entities['target']}")
    """
    
    def __init__(self):
        self._lock = threading.RLock()
        
        # Current contexts
        self._voice_context: Optional[VoiceContext] = None
        self._screen_context: Optional[ScreenContext] = None
        self._system_context: Optional[SystemContext] = None
        
        # Screen context cache
        self._screen_cache: Optional[ScreenContext] = None
        self._screen_cache_time: float = 0
        self._screen_cache_ttl: float = 5.0  # 5 seconds TTL
        
        # Reference to other modules (lazy loaded)
        self._screen_engine = None
        self._memory = None
        
        # Ambiguous patterns that need screen context
        self._ambiguous_patterns = [
            r'\bthat\b', r'\bthis\b', r'\bit\b', r'\bthem\b',
            r'\bthat\s+file\b', r'\bthat\s+app\b', r'\bthat\s+button\b',
            r'\bthat\s+link\b', r'\bopen\s+that\b', r'\bclick\s+that\b',
            r'\bclose\s+that\b', r'\bthe\s+one\b', r'\bsame\s+one\b',
        ]
    
    # =========================================================================
    # LAZY LOADING
    # =========================================================================
    
    def _get_screen_engine(self):
        """Lazy load screen context engine."""
        if self._screen_engine is None:
            try:
                from core.screen_context import get_screen_engine
                self._screen_engine = get_screen_engine()
            except ImportError:
                logger.warning("Screen context engine not available")
                self._screen_engine = None
        return self._screen_engine
    
    def _get_memory(self):
        """Lazy load unified memory."""
        if self._memory is None:
            try:
                from core.unified_memory import get_memory
                self._memory = get_memory()
            except ImportError:
                logger.warning("Unified memory not available")
                self._memory = None
        return self._memory
    
    # =========================================================================
    # CONTEXT UPDATES
    # =========================================================================
    
    def update_voice_context(self, text: str, command: str, 
                           entities: Dict[str, Any] = None,
                           confidence: float = 0.0):
        """
        Update the voice command context.
        
        Args:
            text: Raw voice command text
            command: Parsed command type
            entities: Extracted entities from command
            confidence: Parsing confidence
        """
        with self._lock:
            # Check if command is ambiguous
            is_ambiguous = self._is_ambiguous(text)
            
            self._voice_context = VoiceContext(
                raw_text=text,
                parsed_command=command,
                entities=entities or {},
                confidence=confidence,
                is_ambiguous=is_ambiguous
            )
            
            logger.debug(f"Updated voice context: {text[:50]}... (ambiguous: {is_ambiguous})")
    
    def update_screen_context(self):
        """Capture and update current screen context."""
        with self._lock:
            # Check cache
            if (self._screen_cache and 
                time.time() - self._screen_cache_time < self._screen_cache_ttl):
                self._screen_context = self._screen_cache
                return
            
            # Get fresh screen context
            engine = self._get_screen_engine()
            if engine and engine.ocr_available:
                try:
                    context = engine.capture_and_analyze()
                    self._screen_context = ScreenContext(
                        detected_app=context.detected_app,
                        page_title=context.page_title,
                        keywords=context.keywords,
                        urls=context.urls,
                        text_content=context.all_text[:500],  # Limit text
                        clickable_elements=self._extract_clickable_elements(context),
                        timestamp=time.time()
                    )
                    # Update cache
                    self._screen_cache = self._screen_context
                    self._screen_cache_time = time.time()
                    
                    logger.debug(f"Updated screen context: app={context.detected_app}")
                except Exception as e:
                    logger.warning(f"Failed to capture screen context: {e}")
            else:
                self._screen_context = None
    
    def update_system_context(self, active_window: str = None, 
                             running_apps: List[str] = None):
        """
        Update system context.
        
        Args:
            active_window: Currently active window title
            running_apps: List of running application names
        """
        with self._lock:
            self._system_context = SystemContext(
                active_window=active_window,
                running_apps=running_apps or []
            )
    
    def _extract_clickable_elements(self, screen_context) -> List[str]:
        """Extract clickable elements from screen context."""
        elements = []
        
        # Add URLs
        elements.extend(screen_context.urls[:5])
        
        # Add keywords that might be clickable
        clickable_keywords = ['button', 'link', 'menu', 'tab', 'icon', 'option']
        for kw in screen_context.keywords:
            for ck in clickable_keywords:
                if ck in kw.lower():
                    elements.append(kw)
                    break
        
        return list(set(elements))[:10]  # Dedupe and limit
    
    def _is_ambiguous(self, text: str) -> bool:
        """Check if text contains ambiguous references."""
        import re
        text_lower = text.lower()
        return any(re.search(p, text_lower) for p in self._ambiguous_patterns)
    
    # =========================================================================
    # CONTEXT FUSION
    # =========================================================================
    
    def fuse_context(self) -> UnifiedContext:
        """
        Fuse all context sources into unified understanding.
        
        Returns:
            UnifiedContext with disambiguated entities and suggestions
        """
        with self._lock:
            # Update screen context if voice is ambiguous
            if (self._voice_context and 
                self._voice_context.is_ambiguous and
                self._screen_context is None):
                self.update_screen_context()
            
            unified = UnifiedContext(
                voice=self._voice_context,
                screen=self._screen_context,
                system=self._system_context
            )
            
            # Perform fusion
            if self._voice_context:
                unified = self._fuse_voice_with_screen(unified)
                unified = self._fuse_with_memory(unified)
                unified = self._generate_suggestions(unified)
            
            return unified
    
    def _fuse_voice_with_screen(self, unified: UnifiedContext) -> UnifiedContext:
        """Fuse voice context with screen context."""
        if not unified.voice or not unified.screen:
            return unified
        
        voice_text = unified.voice.raw_text.lower()
        entities = dict(unified.voice.entities)
        confidence_boost = 0.0
        fusion_method = "none"
        
        screen = unified.screen
        
        # =========================================================================
        # RESOLVE "THAT" / "THIS" / "IT" REFERENCES
        # =========================================================================
        
        # Pattern: "open that" / "click that" / "close that"
        if any(p in voice_text for p in ['that', 'this', 'it']):
            # Try to resolve from screen content
            
            # 1. Check if there's a URL on screen
            if screen.urls:
                # If user says "open that" or "go to that", likely a URL
                if any(w in voice_text for w in ['open', 'go', 'visit', 'browse']):
                    entities['resolved_target'] = screen.urls[0]
                    entities['target_type'] = 'url'
                    confidence_boost += 0.3
                    fusion_method = "screen_url"
            
            # 2. Check for keywords on screen
            if screen.keywords and 'resolved_target' not in entities:
                # Use first keyword as likely target
                entities['resolved_target'] = screen.keywords[0]
                entities['target_type'] = 'keyword'
                confidence_boost += 0.2
                fusion_method = "screen_keyword"
            
            # 3. Check page title
            if screen.page_title and 'resolved_target' not in entities:
                entities['resolved_target'] = screen.page_title
                entities['target_type'] = 'title'
                confidence_boost += 0.15
                fusion_method = "screen_title"
        
        # =========================================================================
        # RESOLVE "THAT FILE" / "THAT APP"
        # =========================================================================
        
        # Pattern: "open that file" / "close that app"
        if 'that' in voice_text:
            if 'file' in voice_text:
                # Try to find file-like content on screen
                file_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', 
                                 '.ppt', '.pptx', '.txt', '.jpg', '.png', '.mp3', '.mp4']
                for url in screen.urls:
                    if any(ext in url.lower() for ext in file_extensions):
                        entities['resolved_target'] = url
                        entities['target_type'] = 'file'
                        confidence_boost += 0.35
                        fusion_method = "screen_file"
                        break
            
            elif 'app' in voice_text or 'application' in voice_text:
                # Use detected app
                if screen.detected_app:
                    entities['resolved_target'] = screen.detected_app
                    entities['target_type'] = 'app'
                    confidence_boost += 0.35
                    fusion_method = "screen_app"
        
        # =========================================================================
        # RESOLVE "THE ONE" / "SAME ONE"
        # =========================================================================
        
        if 'the same' in voice_text or 'one more' in voice_text:
            # Get from memory
            memory = self._get_memory()
            if memory:
                last = memory.get_last_command()
                if last and last.entities:
                    # Copy last entities
                    for k, v in last.entities.items():
                        if k not in entities:
                            entities[f'resolved_{k}'] = v
                    confidence_boost += 0.25
                    fusion_method = "memory"
        
        # =========================================================================
        # SCREEN-AWARE COMMAND MODIFICATION
        # =========================================================================
        
        # If user is in a browser and says generic "search", use screen context
        if (screen.detected_app == 'browser' and 
            unified.voice.parsed_command in ['search', 'open_browser']):
            # Could extract search query from screen
            if screen.text_content:
                # Use first line of visible text as hint
                lines = screen.text_content.split('\n')
                if lines:
                    entities['search_hint'] = lines[0][:50]
                    confidence_boost += 0.1
        
        unified.disambiguated_entities = entities
        unified.confidence_boost = confidence_boost
        unified.fusion_method = fusion_method
        
        return unified
    
    def _fuse_with_memory(self, unified: UnifiedContext) -> UnifiedContext:
        """Fuse with conversation memory for context."""
        if not unified.voice:
            return unified
        
        memory = self._get_memory()
        if not memory:
            return unified
        
        # Check if this is a follow-up
        is_follow_up = memory.is_follow_up(unified.voice.raw_text)
        
        if is_follow_up:
            # Get last entities for pronoun resolution
            last_entity = memory.get_last_entity('app')
            if last_entity and 'app' not in unified.disambiguated_entities:
                unified.disambiguated_entities['app'] = last_entity
                unified.fusion_method = unified.fusion_method or "memory"
            
            last_entity = memory.get_last_entity('file')
            if last_entity and 'file' not in unified.disambiguated_entities:
                unified.disambiguated_entities['file'] = last_entity
            
            last_entity = memory.get_last_entity('query')
            if last_entity and 'query' not in unified.disambiguated_entities:
                unified.disambiguated_entities['query'] = last_entity
        
        return unified
    
    def _generate_suggestions(self, unified: UnifiedContext) -> UnifiedContext:
        """Generate context-aware action suggestions."""
        suggestions = []
        
        if not unified.screen:
            return unified
        
        screen = unified.screen
        
        # Add suggestions based on detected app (rule-based)
        if screen.detected_app == 'browser':
            if screen.urls:
                suggestions.append("open that link")
            suggestions.append("search for something")
        
        elif screen.detected_app == 'code_editor':
            suggestions.append("run this code")
            suggestions.append("explain this code")
        
        elif screen.detected_app == 'document':
            suggestions.append("read this document")
            suggestions.append("summarize this")
        
        elif screen.detected_app == 'terminal':
            suggestions.append("run this command")
        
        # Dedupe and limit
        unified.suggested_actions = list(set(suggestions))[:3]
        
        return unified
    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    def resolve_ambiguous_command(self, text: str, command: str,
                                  entities: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Resolve an ambiguous command using screen context.
        
        Args:
            text: Voice command text
            command: Parsed command type
            entities: Already extracted entities
            
        Returns:
            Updated entities with resolved references
        """
        # Update voice context
        self.update_voice_context(text, command, entities)
        
        # Update screen context
        self.update_screen_context()
        
        # Fuse contexts
        unified = self.fuse_context()
        
        # Return merged entities
        merged = dict(entities or {})
        merged.update(unified.disambiguated_entities)
        
        return merged
    
    def get_context_for_command(self, text: str) -> UnifiedContext:
        """
        Get full fused context for a command.
        
        Useful for debugging and understanding context fusion.
        """
        self.update_screen_context()
        self.update_voice_context(text, "unknown", {"type": "unknown"})
        return self.fuse_context()
    
    def get_screen_description(self) -> str:
        """Get a quick description of what's on screen."""
        self.update_screen_context()
        
        if not self._screen_context:
            return "Screen context not available."
        
        screen = self._screen_context
        
        parts = []
        if screen.detected_app:
            parts.append(f"Using {screen.detected_app}")
        if screen.page_title:
            parts.append(f"on '{screen.page_title}'")
        if screen.keywords:
            parts.append(f"Keywords: {', '.join(screen.keywords[:3])}")
        
        return " | ".join(parts) if parts else "Nothing notable on screen"


# ============================================================================
# SINGLETON & CONVENIENCE FUNCTIONS
# ============================================================================

_fusion_engine: Optional[ContextFusion] = None


def get_context_fusion() -> ContextFusion:
    """Get the singleton ContextFusion instance."""
    global _fusion_engine
    if _fusion_engine is None:
        _fusion_engine = ContextFusion()
    return _fusion_engine


def resolve_with_screen(text: str, command: str, 
                       entities: Dict[str, Any] = None) -> Dict[str, Any]:
    """Resolve ambiguous references using screen context."""
    return get_context_fusion().resolve_ambiguous_command(text, command, entities)


def get_fused_context(text: str) -> UnifiedContext:
    """Get full fused context for a command."""
    return get_context_fusion().get_context_for_command(text)


# ============================================================================
# TEST / DEMO
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("VoxMind Multi-Modal Context Fusion")
    print("=" * 60)
    
    fusion = get_context_fusion()
    
    # Test 1: Ambiguous command resolution
    print("\n[Test 1] Resolving ambiguous 'open that' command:")
    
    # First simulate screen context
    fusion.update_screen_context()
    
    # Now test resolution
    resolved = fusion.resolve_ambiguous_command(
        "open that",
        "control_app",
        {"target": "that"}
    )
    
    print(f"  Input: 'open that'")
    print(f"  Resolved entities: {resolved}")
    
    # Test 2: Get fused context
    print("\n[Test 2] Full context fusion:")
    unified = fusion.get_context_for_command("close that app")
    print(f"  Voice: {unified.voice.raw_text if unified.voice else 'None'}")
    print(f"  Screen app: {unified.screen.detected_app if unified.screen else 'None'}")
    print(f"  Disambiguated: {unified.disambiguated_entities}")
    print(f"  Suggestions: {unified.suggested_actions}")
    print(f"  Fusion method: {unified.fusion_method}")
    print(f"  Confidence boost: {unified.confidence_boost:.2f}")
    
    # Test 3: Screen description
    print("\n[Test 3] Screen description:")
    desc = fusion.get_screen_description()
    print(f"  {desc}")
    
    print("\n✅ Context Fusion module ready!")
