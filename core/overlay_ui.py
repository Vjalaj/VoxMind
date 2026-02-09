"""
VoxMind Overlay UI System
==========================
Transparent overlay for displaying:
- Number labels on clickable elements (like Windows/Google Voice Access)
- Grid overlay for mouse control
- Visual feedback for voice commands

Inspired by:
- Windows Voice Access "Show numbers" / "Show grid"
- Google Voice Access number labels and grid selection

Requirements:
- tkinter (built into Python)
- pywinauto (for UI element detection on Windows)
- pyautogui (for screen size)
"""

import tkinter as tk
from tkinter import font as tkfont
import threading
import time
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple, Callable
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Try to import Windows UI Automation
try:
    from pywinauto import Desktop  # type: ignore[import-untyped]
    from pywinauto.controls.uiawrapper import UIAWrapper  # type: ignore[import-untyped]
    HAS_PYWINAUTO = True
except ImportError:
    HAS_PYWINAUTO = False
    logger.warning("pywinauto not installed. UI element detection will be limited.")

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False


class OverlayMode(Enum):
    """Current overlay display mode."""
    HIDDEN = "hidden"
    NUMBERS = "numbers"
    GRID = "grid"
    BOTH = "both"


@dataclass
class ClickableElement:
    """Represents a clickable UI element with its bounding box."""
    number: int
    name: str
    x: int
    y: int
    width: int
    height: int
    element_type: str = "button"
    
    @property
    def center(self) -> Tuple[int, int]:
        """Get center point of element."""
        return (self.x + self.width // 2, self.y + self.height // 2)


@dataclass 
class GridCell:
    """Represents a grid cell."""
    number: int
    x: int
    y: int
    width: int
    height: int
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)


class OverlayConfig:
    """Configuration for overlay appearance."""
    
    # Label appearance
    LABEL_BG_COLOR = "#FFD700"  # Gold/Yellow like Windows Voice Access
    LABEL_FG_COLOR = "#000000"  # Black text
    LABEL_FONT_SIZE = 12
    LABEL_PADDING = 4
    LABEL_BORDER_COLOR = "#000000"
    
    # Grid appearance
    GRID_LINE_COLOR = "#00BFFF"  # Deep sky blue
    GRID_LINE_WIDTH = 2
    GRID_LABEL_BG = "#00BFFF"
    GRID_LABEL_FG = "#FFFFFF"
    
    # Label contrast settings (from Google Voice Access)
    CONTRAST_LEVELS = {
        "lightest": {"bg": "#FFFFCC", "alpha": 0.6},
        "light": {"bg": "#FFD700", "alpha": 0.75},
        "medium": {"bg": "#FFA500", "alpha": 0.85},
        "dark": {"bg": "#FF8C00", "alpha": 0.95},
    }
    
    # Element border when show_borders is on
    ELEMENT_BORDER_COLOR = "#FF69B4"  # Hot pink
    ELEMENT_BORDER_WIDTH = 2


class VoxMindOverlay:
    """
    Transparent overlay window for Voice Access features.
    
    Features:
    - Show numbered labels on UI elements ("Show numbers")
    - Show grid for precise mouse control ("Show grid")
    - Click-through transparency
    - Always on top
    """
    
    def __init__(self):
        self._root: Optional[tk.Tk] = None
        self._canvas: Optional[tk.Canvas] = None
        self._mode = OverlayMode.HIDDEN
        self._elements: List[ClickableElement] = []
        self._grid_cells: List[GridCell] = []
        self._grid_size = 3  # 3x3 default
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._label_contrast = "medium"
        self._show_borders = False
        self._on_element_selected: Optional[Callable[[ClickableElement], None]] = None
        self._on_grid_selected: Optional[Callable[[GridCell], None]] = None
        
        # Screen dimensions
        self._screen_width = 1920
        self._screen_height = 1080
        self._update_screen_size()
    
    def _update_screen_size(self):
        """Get current screen dimensions."""
        if HAS_PYAUTOGUI:
            self._screen_width, self._screen_height = pyautogui.size()
        else:
            # Fallback - will be updated when window is created
            pass
    
    def start(self):
        """Start the overlay in a background thread."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_overlay, daemon=True)
        self._thread.start()
        
        # Give it a moment to initialize
        time.sleep(0.2)
    
    def stop(self):
        """Stop the overlay."""
        self._running = False
        if self._root:
            try:
                self._root.quit()
                self._root.destroy()
            except (tk.TclError, RuntimeError, Exception) as e:
                logger.debug(f"Overlay window destroy error: {e}")
                pass
        self._root = None
    
    def _run_overlay(self):
        """Run the tkinter main loop in a thread."""
        try:
            self._create_window()
            if self._root:
                self._root.mainloop()
        except Exception as e:
            logger.error(f"Overlay error: {e}")
        finally:
            self._running = False
    
    def _create_window(self):
        """Create the transparent overlay window."""
        self._root = tk.Tk()
        self._root.title("VoxMind Overlay")
        
        # Get screen size
        self._screen_width = self._root.winfo_screenwidth()
        self._screen_height = self._root.winfo_screenheight()
        
        # Make fullscreen
        self._root.geometry(f"{self._screen_width}x{self._screen_height}+0+0")
        
        # Remove window decorations
        self._root.overrideredirect(True)
        
        # Always on top
        self._root.attributes('-topmost', True)
        
        # Make click-through on Windows
        try:
            # Windows-specific: make window click-through
            self._root.attributes('-transparentcolor', 'gray1')
            bg_color = 'gray1'
        except (tk.TclError, AttributeError, Exception) as e:
            # Fallback for other platforms
            logger.debug(f"Transparent window not supported: {e}")
            self._root.attributes('-alpha', 0.8)
            bg_color = 'black'
        
        # Create canvas
        self._canvas = tk.Canvas(
            self._root,
            width=self._screen_width,
            height=self._screen_height,
            bg=bg_color,
            highlightthickness=0
        )
        self._canvas.pack(fill=tk.BOTH, expand=True)
        
        # Bind escape to hide
        self._root.bind('<Escape>', lambda e: self.hide())
        
        # Start hidden
        self._root.withdraw()
        
        # Schedule periodic updates
        self._schedule_update()
    
    def _schedule_update(self):
        """Schedule periodic overlay updates."""
        if self._running and self._root:
            self._update_display()
            self._root.after(100, self._schedule_update)  # Update every 100ms
    
    def _update_display(self):
        """Update the overlay display based on current mode."""
        if not self._canvas or not self._root:
            return
        
        # Clear canvas
        self._canvas.delete("all")
        
        if self._mode == OverlayMode.HIDDEN:
            self._root.withdraw()
            return
        
        self._root.deiconify()
        
        if self._mode in (OverlayMode.NUMBERS, OverlayMode.BOTH):
            self._draw_element_labels()
        
        if self._mode in (OverlayMode.GRID, OverlayMode.BOTH):
            self._draw_grid()
    
    def _draw_element_labels(self):
        """Draw numbered labels on UI elements."""
        if not self._canvas:
            return
            
        config = OverlayConfig.CONTRAST_LEVELS.get(
            self._label_contrast, 
            OverlayConfig.CONTRAST_LEVELS["medium"]
        )
        bg_color = config["bg"]
        
        for elem in self._elements:
            # Draw border around element if enabled
            if self._show_borders:
                self._canvas.create_rectangle(
                    elem.x, elem.y,
                    elem.x + elem.width, elem.y + elem.height,
                    outline=OverlayConfig.ELEMENT_BORDER_COLOR,
                    width=OverlayConfig.ELEMENT_BORDER_WIDTH
                )
            
            # Draw number label (top-left corner of element)
            label_text = str(elem.number)
            
            # Create label background
            label_x = elem.x
            label_y = elem.y
            
            # Create text to measure size
            text_id = self._canvas.create_text(
                label_x + OverlayConfig.LABEL_PADDING,
                label_y + OverlayConfig.LABEL_PADDING,
                text=label_text,
                anchor=tk.NW,
                font=('Arial', OverlayConfig.LABEL_FONT_SIZE, 'bold'),
                fill=OverlayConfig.LABEL_FG_COLOR
            )
            
            # Get text bounding box
            bbox = self._canvas.bbox(text_id)
            if bbox:
                # Draw background rectangle
                pad = OverlayConfig.LABEL_PADDING
                self._canvas.create_rectangle(
                    bbox[0] - pad, bbox[1] - pad,
                    bbox[2] + pad, bbox[3] + pad,
                    fill=bg_color,
                    outline=OverlayConfig.LABEL_BORDER_COLOR,
                    width=1
                )
                
                # Redraw text on top
                self._canvas.tag_raise(text_id)
    
    def _draw_grid(self):
        """Draw grid overlay for mouse control."""
        if not self._canvas:
            return
            
        cell_width = self._screen_width // self._grid_size
        cell_height = self._screen_height // self._grid_size
        
        self._grid_cells = []
        cell_num = 1
        
        for row in range(self._grid_size):
            for col in range(self._grid_size):
                x = col * cell_width
                y = row * cell_height
                
                # Store grid cell
                cell = GridCell(
                    number=cell_num,
                    x=x, y=y,
                    width=cell_width,
                    height=cell_height
                )
                self._grid_cells.append(cell)
                
                # Draw cell border
                self._canvas.create_rectangle(
                    x, y, x + cell_width, y + cell_height,
                    outline=OverlayConfig.GRID_LINE_COLOR,
                    width=OverlayConfig.GRID_LINE_WIDTH
                )
                
                # Draw cell number in center
                center_x = x + cell_width // 2
                center_y = y + cell_height // 2
                
                # Background for number
                self._canvas.create_oval(
                    center_x - 20, center_y - 20,
                    center_x + 20, center_y + 20,
                    fill=OverlayConfig.GRID_LABEL_BG,
                    outline=OverlayConfig.GRID_LINE_COLOR,
                    width=2
                )
                
                # Number text
                self._canvas.create_text(
                    center_x, center_y,
                    text=str(cell_num),
                    font=('Arial', 16, 'bold'),
                    fill=OverlayConfig.GRID_LABEL_FG
                )
                
                cell_num += 1
    
    # === Public API ===
    
    def show_numbers(self, refresh_elements: bool = True):
        """
        Show number labels on UI elements.
        
        Voice command: "Show numbers"
        """
        if refresh_elements:
            self._detect_ui_elements()
        self._mode = OverlayMode.NUMBERS
        logger.info(f"Showing {len(self._elements)} numbered elements")
    
    def show_grid(self, size: int = 3):
        """
        Show grid overlay.
        
        Voice command: "Show grid"
        
        Args:
            size: Grid size (3 = 3x3, 4 = 4x4, etc.)
        """
        self._grid_size = max(2, min(9, size))  # Clamp to 2-9
        self._mode = OverlayMode.GRID
        logger.info(f"Showing {self._grid_size}x{self._grid_size} grid")
    
    def show_both(self):
        """Show both numbers and grid."""
        self._detect_ui_elements()
        self._mode = OverlayMode.BOTH
    
    def hide(self):
        """
        Hide the overlay.
        
        Voice command: "Hide numbers" / "Hide grid" / "Cancel"
        """
        self._mode = OverlayMode.HIDDEN
        logger.info("Overlay hidden")
    
    def click_number(self, number: int) -> Optional[Tuple[int, int]]:
        """
        Get coordinates for a numbered element.
        
        Voice command: "Click 5" or just "5"
        
        Returns:
            (x, y) center coordinates or None if not found
        """
        # Check elements first
        for elem in self._elements:
            if elem.number == number:
                logger.info(f"Clicking element {number}: {elem.name}")
                if self._on_element_selected:
                    self._on_element_selected(elem)
                return elem.center
        
        # Check grid cells
        for cell in self._grid_cells:
            if cell.number == number:
                logger.info(f"Clicking grid cell {number}")
                if self._on_grid_selected:
                    self._on_grid_selected(cell)
                return cell.center
        
        logger.warning(f"Number {number} not found")
        return None
    
    def set_label_contrast(self, level: str):
        """
        Set label contrast level.
        
        Args:
            level: "lightest", "light", "medium", "dark"
        """
        if level in OverlayConfig.CONTRAST_LEVELS:
            self._label_contrast = level
    
    def set_show_borders(self, show: bool):
        """Toggle element borders."""
        self._show_borders = show
    
    def set_grid_size(self, size: int):
        """Set grid density."""
        self._grid_size = max(2, min(9, size))
    
    def get_elements(self) -> List[ClickableElement]:
        """Get current list of detected elements."""
        return self._elements.copy()
    
    def get_grid_cells(self) -> List[GridCell]:
        """Get current grid cells."""
        return self._grid_cells.copy()
    
    def _detect_ui_elements(self):
        """Detect clickable UI elements on screen."""
        self._elements = []
        
        if not HAS_PYWINAUTO:
            logger.warning("pywinauto not available, using mock elements")
            self._elements = self._get_mock_elements()
            return
        
        try:
            # Get elements from foreground window
            desktop = Desktop(backend='uia')
            
            # Get all windows
            windows = desktop.windows()
            
            element_num = 1
            for window in windows[:3]:  # Limit to top 3 windows for performance
                try:
                    # Get clickable descendants
                    for elem in window.descendants(control_type='Button')[:20]:
                        try:
                            rect = elem.rectangle()
                            # Skip off-screen or tiny elements
                            if rect.width() < 10 or rect.height() < 10:
                                continue
                            if rect.left < 0 or rect.top < 0:
                                continue
                            if rect.left > self._screen_width or rect.top > self._screen_height:
                                continue
                            
                            self._elements.append(ClickableElement(
                                number=element_num,
                                name=elem.window_text() or f"Button {element_num}",
                                x=rect.left,
                                y=rect.top,
                                width=rect.width(),
                                height=rect.height(),
                                element_type="Button"
                            ))
                            element_num += 1
                            
                            if element_num > 99:  # Limit to 99 elements
                                break
                        except (AttributeError, OSError, Exception):
                            continue
                except (AttributeError, OSError, Exception):
                    continue
            
            # Also get links, text boxes, etc.
            # This is simplified - full implementation would detect more control types
            
        except Exception as e:
            logger.error(f"Error detecting UI elements: {e}")
            self._elements = self._get_mock_elements()
    
    def _get_mock_elements(self) -> List[ClickableElement]:
        """Return mock elements for testing when pywinauto unavailable."""
        return [
            ClickableElement(1, "Start Menu", 0, self._screen_height - 48, 48, 48),
            ClickableElement(2, "Search", 50, self._screen_height - 48, 48, 48),
            ClickableElement(3, "Task View", 100, self._screen_height - 48, 48, 48),
            ClickableElement(4, "File Explorer", 150, self._screen_height - 48, 48, 48),
            ClickableElement(5, "Browser", 200, self._screen_height - 48, 48, 48),
        ]
    
    # === Callbacks ===
    
    def on_element_selected(self, callback: Callable[[ClickableElement], None]):
        """Set callback for when an element is selected."""
        self._on_element_selected = callback
    
    def on_grid_selected(self, callback: Callable[[GridCell], None]):
        """Set callback for when a grid cell is selected."""
        self._on_grid_selected = callback


# === Global overlay instance ===

_overlay: Optional[VoxMindOverlay] = None


def get_overlay() -> VoxMindOverlay:
    """Get or create the global overlay instance."""
    global _overlay
    if _overlay is None:
        _overlay = VoxMindOverlay()
    return _overlay


def show_numbers():
    """Show number labels on screen elements."""
    overlay = get_overlay()
    if not overlay._running:
        overlay.start()
    overlay.show_numbers()


def show_grid(size: int = 3):
    """Show grid overlay."""
    overlay = get_overlay()
    if not overlay._running:
        overlay.start()
    overlay.show_grid(size)


def hide_overlay():
    """Hide the overlay."""
    overlay = get_overlay()
    overlay.hide()


def click_by_number(number: int) -> Optional[Tuple[int, int]]:
    """Get coordinates for numbered element/cell."""
    return get_overlay().click_number(number)


# === Demo ===

if __name__ == "__main__":
    import pyautogui
    
    print("VoxMind Overlay Demo")
    print("=" * 40)
    print("Commands:")
    print("  1 - Show numbers")
    print("  2 - Show grid (3x3)")
    print("  3 - Show grid (4x4)")
    print("  4 - Hide overlay")
    print("  5 - Click number (enter number)")
    print("  q - Quit")
    print()
    
    overlay = get_overlay()
    overlay.start()
    
    try:
        while True:
            cmd = input("Enter command: ").strip().lower()
            
            if cmd == 'q':
                break
            elif cmd == '1':
                overlay.show_numbers()
                print("Showing numbers...")
            elif cmd == '2':
                overlay.show_grid(3)
                print("Showing 3x3 grid...")
            elif cmd == '3':
                overlay.show_grid(4)
                print("Showing 4x4 grid...")
            elif cmd == '4':
                overlay.hide()
                print("Hidden")
            elif cmd == '5':
                num = int(input("Enter number to click: "))
                coords = overlay.click_number(num)
                if coords:
                    print(f"Clicking at {coords}")
                    pyautogui.click(coords[0], coords[1])
                else:
                    print("Number not found")
            elif cmd.isdigit():
                coords = overlay.click_number(int(cmd))
                if coords:
                    print(f"Would click at {coords}")
    finally:
        overlay.stop()
