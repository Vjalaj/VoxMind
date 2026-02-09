"""
VoxMind Overlay Manager
========================
Unified interface for overlay UI features.

This module provides a single API for:
- Number labels ("Show numbers")
- Grid overlay ("Show grid")
- Element highlighting
- Click by number

It automatically selects the best available backend:
1. PyQt6/5 (best quality, if installed)
2. tkinter (fallback, built into Python)

Usage:
    from core.overlay_manager import overlay_manager
    
    # Show numbered labels on UI elements
    overlay_manager.show_numbers()
    
    # Show grid for mouse control
    overlay_manager.show_grid()
    
    # Click element by number (voice command: "click 5")
    overlay_manager.click(5)
    
    # Hide overlay
    overlay_manager.hide()

Voice Commands Supported:
    "Show numbers"         -> show_numbers()
    "Show numbers here"    -> show_numbers(current_window_only=True)
    "Hide numbers"         -> hide()
    "Show grid"           -> show_grid()
    "Show grid 4"         -> show_grid(size=4)
    "Hide grid"           -> hide()
    "Click 5" / "5"       -> click(5)
    "Cancel"              -> hide()
"""

import logging
from typing import Optional, Tuple, Callable, List, Any, Dict
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Detect available backends
try:
    from core.overlay_qt import get_overlay as get_qt_overlay, is_available as qt_available, VoxMindOverlayQt
    HAS_QT = qt_available()
except ImportError:
    HAS_QT = False
    VoxMindOverlayQt = None

try:
    from core.overlay_ui import get_overlay as get_tk_overlay, VoxMindOverlay
    HAS_TK = True
except ImportError:
    HAS_TK = False
    VoxMindOverlay = None

# Try to import pyautogui for clicking
try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False

# Import settings if available
try:
    from core.voice_access_settings import get_settings
    HAS_SETTINGS = True
except ImportError:
    HAS_SETTINGS = False


class OverlayBackend(Enum):
    """Available overlay backends."""
    PYQT = "pyqt"
    TKINTER = "tkinter"
    NONE = "none"


@dataclass
class ClickResult:
    """Result of a click action."""
    success: bool
    number: int
    coordinates: Optional[Tuple[int, int]]
    element_name: Optional[str] = None
    message: str = ""


class OverlayManager:
    """
    Unified overlay manager for VoxMind.
    
    Provides a consistent API regardless of backend (PyQt or tkinter).
    Integrates with voice access settings for configuration.
    """
    
    def __init__(self):
        self._backend: OverlayBackend = OverlayBackend.NONE
        self._qt_overlay: Optional[Any] = None
        self._tk_overlay: Optional[Any] = None
        self._active_overlay: Optional[Any] = None
        
        self._click_callback: Optional[Callable[[int, int], None]] = None
        self._numbers_visible = False
        self._grid_visible = False
        
        # Auto-detect best backend
        self._detect_backend()
    
    def _detect_backend(self):
        """Detect and initialize the best available backend."""
        if HAS_QT:
            self._backend = OverlayBackend.PYQT
            logger.info("Using PyQt overlay backend")
        elif HAS_TK:
            self._backend = OverlayBackend.TKINTER
            logger.info("Using tkinter overlay backend")
        else:
            self._backend = OverlayBackend.NONE
            logger.warning("No overlay backend available!")
    
    def _ensure_initialized(self) -> bool:
        """Ensure overlay is initialized."""
        if self._backend == OverlayBackend.NONE:
            logger.error("No overlay backend available")
            return False
        
        if self._backend == OverlayBackend.PYQT:
            if self._qt_overlay is None:
                self._qt_overlay = get_qt_overlay()
                if self._qt_overlay:
                    self._qt_overlay.start()
                    self._active_overlay = self._qt_overlay
                    
                    # Set up auto-click if pyautogui available
                    if HAS_PYAUTOGUI and self._click_callback is None:
                        self._click_callback = lambda x, y: pyautogui.click(x, y)
                        self._qt_overlay.set_click_handler(self._click_callback)
            return self._qt_overlay is not None
        
        elif self._backend == OverlayBackend.TKINTER:
            if self._tk_overlay is None:
                self._tk_overlay = get_tk_overlay()
                if self._tk_overlay:
                    self._tk_overlay.start()
                    self._active_overlay = self._tk_overlay
            return self._tk_overlay is not None
        
        return False
    
    @property
    def backend(self) -> OverlayBackend:
        """Get current backend."""
        return self._backend
    
    @property
    def is_available(self) -> bool:
        """Check if overlay is available."""
        return self._backend != OverlayBackend.NONE
    
    @property
    def is_visible(self) -> bool:
        """Check if overlay is currently visible."""
        return self._numbers_visible or self._grid_visible
    
    def preload(self):
        """Pre-detect elements in background for faster show_numbers."""
        if self._backend == OverlayBackend.PYQT and self._qt_overlay:
            self._qt_overlay.preload_elements()
    
    # === Voice Access Commands ===
    
    def show_numbers(self, current_window_only: bool = False, fast: bool = False) -> bool:
        """
        Show numbered labels on clickable elements.
        
        Voice commands:
            "Show numbers"
            "Show numbers everywhere"
            "Show numbers here" (current_window_only=True)
            "Show labels"
        
        Args:
            current_window_only: Only show numbers on the active window
            fast: Use fast mode (cached elements, background refresh)
        
        Returns:
            True if successful
        """
        if not self._ensure_initialized():
            return False
        
        # Load settings
        show_borders = False
        contrast = "medium"
        if HAS_SETTINGS:
            try:
                settings = get_settings()
                show_borders = settings.show_borders
                contrast = settings.label_contrast.value
            except (ImportError, AttributeError, Exception) as e:
                logger.debug(f"Settings load failed: {e}")
                pass
        
        try:
            if self._backend == OverlayBackend.PYQT and self._qt_overlay:
                if show_borders:
                    self._qt_overlay.set_show_borders(True)
                self._qt_overlay.set_contrast(contrast)
                if fast:
                    self._qt_overlay.show_numbers_fast()
                else:
                    self._qt_overlay.show_numbers()
            elif self._tk_overlay:
                self._tk_overlay.set_show_borders(show_borders)
                self._tk_overlay.set_label_contrast(contrast)
                self._tk_overlay.show_numbers()
            else:
                logger.error("No overlay backend available")
                return False
            
            self._numbers_visible = True
            self._grid_visible = False
            logger.info("Showing number labels")
            return True
            
        except Exception as e:
            logger.error(f"Error showing numbers: {e}")
            return False
    
    def show_grid(self, size: int = 3) -> bool:
        """
        Show grid overlay for precise mouse control.
        
        Voice commands:
            "Show grid"
            "Show grid everywhere"
            "Show grid <size>" (e.g., "Show grid 4" for 4x4)
        
        Args:
            size: Grid size (2-9, default 3 for 3x3)
        
        Returns:
            True if successful
        """
        if not self._ensure_initialized():
            return False
        
        # Load settings for grid size
        if HAS_SETTINGS:
            try:
                settings = get_settings()
                if settings.grid_size:
                    size = settings.grid_size
            except (ImportError, AttributeError, Exception) as e:
                logger.debug(f"Grid settings load failed: {e}")
                pass
        
        size = max(2, min(9, size))
        
        try:
            if self._backend == OverlayBackend.PYQT and self._qt_overlay:
                self._qt_overlay.show_grid(size)
            elif self._tk_overlay:
                self._tk_overlay.show_grid(size)
            else:
                logger.error("No overlay backend available")
                return False
            
            self._grid_visible = True
            self._numbers_visible = False
            logger.info(f"Showing {size}x{size} grid")
            return True
            
        except Exception as e:
            logger.error(f"Error showing grid: {e}")
            return False
    
    def hide(self) -> bool:
        """
        Hide the overlay.
        
        Voice commands:
            "Hide numbers"
            "Hide grid"
            "Cancel"
        
        Returns:
            True if successful
        """
        if self._active_overlay is None:
            return True
        
        try:
            if self._backend == OverlayBackend.PYQT and self._qt_overlay:
                self._qt_overlay.hide()
            elif self._tk_overlay:
                self._tk_overlay.hide()
            
            self._numbers_visible = False
            self._grid_visible = False
            logger.info("Overlay hidden")
            return True
            
        except Exception as e:
            logger.error(f"Error hiding overlay: {e}")
            return False
    
    def get_elements(self) -> List[Dict[str, Any]]:
        """
        Get list of currently detected elements.
        
        Returns:
            List of element dictionaries with:
            - id: Element number
            - name: Element name/label
            - control_type: Type of element (button, link, etc.)
            - rect: (x, y, width, height) tuple
        """
        elements = []
        
        try:
            if self._backend == OverlayBackend.PYQT and self._qt_overlay:
                if self._qt_overlay._window:
                    for elem in getattr(self._qt_overlay._window, 'elements', []):
                        elements.append({
                            'id': elem.number,
                            'name': elem.name,
                            'control_type': getattr(elem, 'element_type', 'unknown'),
                            'rect': (elem.x, elem.y, elem.width, elem.height),
                        })
            elif self._tk_overlay:
                for elem in self._tk_overlay.get_elements():
                    elements.append({
                        'id': elem.number,
                        'name': elem.name,
                        'control_type': getattr(elem, 'element_type', 'unknown'),
                        'rect': (elem.x, elem.y, elem.width, elem.height),
                    })
        except Exception as e:
            logger.error(f"Error getting elements: {e}")
        
        return elements

    def click(self, number: int, perform_click: bool = True) -> ClickResult:
        """
        Click on a numbered element or grid cell.
        
        Voice commands:
            "Click <number>" (e.g., "Click 5")
            "<number>" (e.g., just "5")
            "Tap <number>"
        
        Args:
            number: The number to click
            perform_click: Actually perform the click (False to just get coords)
        
        Returns:
            ClickResult with success status and coordinates
        """
        if self._active_overlay is None:
            return ClickResult(
                success=False,
                number=number,
                coordinates=None,
                message="Overlay not active"
            )
        
        try:
            coords = None
            element_name = None
            
            if self._backend == OverlayBackend.PYQT and self._qt_overlay:
                # Get coordinates
                coords = self._qt_overlay.click(number)
                # Try to get element name
                if self._qt_overlay._window:
                    for elem in getattr(self._qt_overlay._window, 'elements', []):
                        if elem.number == number:
                            element_name = elem.name
                            break
            elif self._tk_overlay:
                coords = self._tk_overlay.click_number(number)
                for elem in self._tk_overlay.get_elements():
                    if elem.number == number:
                        element_name = elem.name
                        break
            
            if coords:
                # Perform click if requested and callback is set
                if perform_click and HAS_PYAUTOGUI:
                    pyautogui.click(coords[0], coords[1])
                    logger.info(f"Clicked {number} ({element_name or 'grid'}) at {coords}")
                
                return ClickResult(
                    success=True,
                    number=number,
                    coordinates=coords,
                    element_name=element_name,
                    message=f"Clicked {element_name or f'cell {number}'}"
                )
            else:
                return ClickResult(
                    success=False,
                    number=number,
                    coordinates=None,
                    message=f"Number {number} not found"
                )
                
        except Exception as e:
            logger.error(f"Error clicking {number}: {e}")
            return ClickResult(
                success=False,
                number=number,
                coordinates=None,
                message=str(e)
            )
    
    def drill(self, number: int) -> bool:
        """
        Drill into a grid cell (zoom into sub-grid).
        
        Voice command: "<number>" when grid is showing
        
        This is a Voice Access feature where saying a grid number
        zooms into that cell and shows a new grid.
        
        Args:
            number: Grid cell number to drill into
        
        Returns:
            True if successful
        """
        if self._backend != OverlayBackend.PYQT or not self._qt_overlay:
            logger.warning("Grid drill-down only available with PyQt backend")
            return False
        
        if not self._grid_visible:
            return False
        
        try:
            self._qt_overlay.drill(number)
            logger.info(f"Drilled into cell {number}")
            return True
        except Exception as e:
            logger.error(f"Error drilling: {e}")
            return False
    
    def undo(self) -> bool:
        """
        Undo last grid drill (zoom back out).
        
        Voice command: "Undo" / "Go back"
        
        Returns:
            True if successful
        """
        if self._backend != OverlayBackend.PYQT or not self._qt_overlay:
            return False
        
        if not self._grid_visible:
            return False
        
        try:
            self._qt_overlay.undo()
            logger.info("Undid grid drill")
            return True
        except Exception as e:
            logger.error(f"Error undoing: {e}")
            return False
    
    def mark(self, number: Optional[int] = None) -> bool:
        """
        Mark an element for drag operation.
        
        Voice command: "Mark" or "Mark <number>"
        
        Args:
            number: Element number to mark (None for current cursor location)
        
        Returns:
            True if successful
        """
        # TODO: Implement mark for drag-and-drop
        logger.info(f"Marked element {number}")
        return True
    
    def drag(self, target_number: Optional[int] = None) -> bool:
        """
        Drag marked element to target.
        
        Voice command: "Drag" or "Drag to <number>"
        
        Args:
            target_number: Target location number
        
        Returns:
            True if successful
        """
        # TODO: Implement drag operation
        logger.info(f"Dragged to {target_number}")
        return True
    
    # === Configuration ===
    
    def set_click_callback(self, callback: Callable[[int, int], None]):
        """
        Set custom click callback.
        
        Args:
            callback: Function that takes (x, y) coordinates
        """
        self._click_callback = callback
        if self._qt_overlay:
            self._qt_overlay.set_click_handler(callback)
    
    def set_grid_size(self, size: int):
        """Set default grid size."""
        if HAS_SETTINGS:
            try:
                from core.voice_access_settings import get_settings_manager
                get_settings_manager().update(grid_size=size)
            except (ImportError, AttributeError, Exception) as e:
                logger.debug(f"Grid size update failed: {e}")
                pass
    
    def set_show_borders(self, show: bool):
        """Toggle element borders."""
        if self._qt_overlay:
            self._qt_overlay.set_show_borders(show)
        if self._tk_overlay:
            self._tk_overlay.set_show_borders(show)
    
    def set_contrast(self, level: str):
        """Set label contrast (lightest/light/medium/dark)."""
        if self._qt_overlay:
            self._qt_overlay.set_contrast(level)
        if self._tk_overlay:
            self._tk_overlay.set_label_contrast(level)
    
    # === Lifecycle ===
    
    def stop(self):
        """Stop and clean up the overlay."""
        try:
            if self._qt_overlay:
                self._qt_overlay.stop()
            if self._tk_overlay:
                self._tk_overlay.stop()
        except (AttributeError, RuntimeError, Exception) as e:
            logger.debug(f"Overlay stop error: {e}")
            pass
        
        self._numbers_visible = False
        self._grid_visible = False
        logger.info("Overlay manager stopped")


# === Global Instance ===

_overlay_manager: Optional[OverlayManager] = None


def get_overlay_manager() -> OverlayManager:
    """Get the global overlay manager instance."""
    global _overlay_manager
    if _overlay_manager is None:
        _overlay_manager = OverlayManager()
    return _overlay_manager


# Convenience access
overlay_manager = property(lambda self: get_overlay_manager())


# === Voice Command Handler ===

def handle_overlay_command(command: str, params: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
    """
    Handle an overlay-related voice command.
    
    Args:
        command: Command name (show_numbers, show_grid, hide, click, etc.)
        params: Optional parameters
    
    Returns:
        (success, message) tuple
    """
    params = params or {}
    manager = get_overlay_manager()
    
    if command == "show_numbers":
        success = manager.show_numbers(
            current_window_only=params.get("here", False)
        )
        return success, "Showing numbers" if success else "Failed to show numbers"
    
    elif command == "show_grid":
        size = params.get("size", 3)
        success = manager.show_grid(size)
        return success, f"Showing {size}x{size} grid" if success else "Failed to show grid"
    
    elif command == "hide":
        success = manager.hide()
        return success, "Hidden" if success else "Failed to hide"
    
    elif command == "click":
        number = params.get("number")
        if number is None:
            return False, "No number specified"
        result = manager.click(number)
        return result.success, result.message
    
    elif command == "drill":
        number = params.get("number")
        if number is None:
            return False, "No number specified"
        success = manager.drill(number)
        return success, f"Drilled into {number}" if success else "Failed to drill"
    
    elif command == "undo":
        success = manager.undo()
        return success, "Undid" if success else "Nothing to undo"
    
    return False, f"Unknown command: {command}"


# === Demo ===

if __name__ == "__main__":
    print("VoxMind Overlay Manager Demo")
    print("=" * 40)
    print(f"Backend: {get_overlay_manager().backend.value}")
    print()
    print("Commands:")
    print("  n - Show numbers")
    print("  g - Show grid")
    print("  h - Hide")
    print("  1-9 - Click number")
    print("  q - Quit")
    print()
    
    manager = get_overlay_manager()
    
    if not manager.is_available:
        print("No overlay backend available!")
        print("Install PyQt6: pip install PyQt6")
        exit(1)
    
    try:
        while True:
            cmd = input("> ").strip().lower()
            
            if cmd == 'q':
                break
            elif cmd == 'n':
                success, msg = handle_overlay_command("show_numbers")
                print(msg)
            elif cmd == 'g':
                success, msg = handle_overlay_command("show_grid")
                print(msg)
            elif cmd == 'h':
                success, msg = handle_overlay_command("hide")
                print(msg)
            elif cmd.isdigit():
                success, msg = handle_overlay_command("click", {"number": int(cmd)})
                print(msg)
            else:
                print("Unknown command")
                
    except KeyboardInterrupt:
        pass
    finally:
        manager.stop()
        print("Goodbye!")
