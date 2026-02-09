"""
VoxMind Advanced Overlay (PyQt6 version)
=========================================
A professional overlay UI with true transparency and modern appearance.

Features:
- True transparent overlay (click-through)
- Smooth animations
- High DPI support
- Modern label styling
- Grid with drill-down capability

Install:
    pip install PyQt6

Fallback:
    If PyQt6 is not available, use overlay_ui.py (tkinter version)
"""

import sys
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple, Callable, Dict, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Try PyQt6 first, then PyQt5
try:
    from PyQt6.QtWidgets import (  # type: ignore[import-untyped]
        QApplication, QWidget, QLabel, QVBoxLayout, QGridLayout,
        QGraphicsDropShadowEffect
    )
    from PyQt6.QtCore import Qt, QTimer, QRect, QPoint, pyqtSignal, QPropertyAnimation, QEasingCurve  # type: ignore[import-untyped]
    from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QScreen  # type: ignore[import-untyped]
    HAS_PYQT = True
    PYQT_VERSION = 6
except ImportError:
    try:
        from PyQt5.QtWidgets import (  # type: ignore[import-untyped]
            QApplication, QWidget, QLabel, QVBoxLayout, QGridLayout,
            QGraphicsDropShadowEffect
        )
        from PyQt5.QtCore import Qt, QTimer, QRect, QPoint, pyqtSignal, QPropertyAnimation, QEasingCurve  # type: ignore[import-untyped]
        from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QBrush, QScreen  # type: ignore[import-untyped]
        HAS_PYQT = True
        PYQT_VERSION = 5
    except ImportError:
        HAS_PYQT = False
        PYQT_VERSION = 0
        logger.warning("PyQt not installed. Use overlay_ui.py instead.")

# Try to import UI Automation - Initialize BEFORE Qt to avoid COM conflicts
try:
    from pywinauto import Desktop  # type: ignore[import-untyped]
    # Pre-initialize COM by creating a Desktop instance
    # This must happen before QApplication is created
    _pre_init_desktop = Desktop(backend='uia')
    HAS_PYWINAUTO = True
except ImportError:
    HAS_PYWINAUTO = False
except Exception:
    # COM initialization failed, disable pywinauto
    HAS_PYWINAUTO = False

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False


@dataclass
class UIElement:
    """Detected UI element."""
    number: int
    name: str
    rect: Tuple[int, int, int, int]  # x, y, width, height
    element_type: str = "button"
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self.rect[0] + self.rect[2] // 2, self.rect[1] + self.rect[3] // 2)


@dataclass
class GridCell:
    """Grid cell for grid selection mode."""
    number: int
    rect: Tuple[int, int, int, int]
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self.rect[0] + self.rect[2] // 2, self.rect[1] + self.rect[3] // 2)


class OverlayStyle:
    """Styling constants for the overlay."""
    
    # Number label styling (Voice Access inspired)
    LABEL_COLORS = {
        "default": {"bg": "#FFD700", "fg": "#000000", "border": "#B8860B"},
        "hover": {"bg": "#FFA500", "fg": "#000000", "border": "#FF8C00"},
        "active": {"bg": "#32CD32", "fg": "#FFFFFF", "border": "#228B22"},
    }
    
    # Contrast levels (Google Voice Access)
    CONTRAST = {
        "lightest": 0.5,
        "light": 0.65,
        "medium": 0.8,
        "dark": 0.95,
    }
    
    # Grid styling
    GRID_LINE_COLOR = QColor(0, 191, 255, 180) if HAS_PYQT else None  # DeepSkyBlue
    GRID_FILL_COLOR = QColor(0, 191, 255, 30) if HAS_PYQT else None
    GRID_TEXT_COLOR = QColor(255, 255, 255) if HAS_PYQT else None
    
    # Element border styling
    ELEMENT_BORDER_COLOR = QColor(255, 105, 180, 200) if HAS_PYQT else None  # HotPink
    
    # Fonts
    LABEL_FONT_SIZE = 14
    GRID_FONT_SIZE = 24


if HAS_PYQT:
    
    class NumberLabel(QWidget):
        """A single number label widget."""
        
        clicked = pyqtSignal(int)
        
        def __init__(self, number: int, parent=None):
            super().__init__(parent)
            self.number = number
            self.is_hovered = False
            
            self.setFixedSize(28, 22)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            
            # Add shadow effect
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(8)
            shadow.setOffset(2, 2)
            shadow.setColor(QColor(0, 0, 0, 100))
            self.setGraphicsEffect(shadow)
        
        def paintEvent(self, event):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Get colors based on state
            colors = OverlayStyle.LABEL_COLORS["hover" if self.is_hovered else "default"]
            
            # Draw rounded rectangle background
            bg_color = QColor(colors["bg"])
            border_color = QColor(colors["border"])
            
            painter.setBrush(QBrush(bg_color))
            painter.setPen(QPen(border_color, 2))
            painter.drawRoundedRect(1, 1, self.width() - 2, self.height() - 2, 4, 4)
            
            # Draw number
            painter.setPen(QPen(QColor(colors["fg"])))
            font = QFont("Arial", OverlayStyle.LABEL_FONT_SIZE, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, str(self.number))
        
        def enterEvent(self, event):
            self.is_hovered = True
            self.update()
        
        def leaveEvent(self, event):
            self.is_hovered = False
            self.update()
        
        def mousePressEvent(self, event):
            self.clicked.emit(self.number)
    
    
    class OverlayWindow(QWidget):
        """Main transparent overlay window."""
        
        element_selected = pyqtSignal(int)
        grid_selected = pyqtSignal(int)
        
        def __init__(self):
            super().__init__()
            
            self.elements: List[UIElement] = []
            self.grid_cells: List[GridCell] = []
            self.grid_size = 3
            self.show_numbers_mode = False
            self.show_grid_mode = False
            self.show_borders = False
            self.contrast_level = "medium"
            
            self._labels: List[NumberLabel] = []
            self._grid_drill_path: List[int] = []  # For grid drill-down
            
            self._setup_window()
        
        def _setup_window(self):
            """Configure the overlay window."""
            # Frameless, transparent, always on top
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.Tool |
                Qt.WindowType.WindowTransparentForInput
            )
            
            # Enable transparency
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
            
            # Get screen geometry
            screen = QApplication.primaryScreen()
            if screen:
                geometry = screen.geometry()
                self.setGeometry(geometry)
            else:
                self.setGeometry(0, 0, 1920, 1080)
            
            # Update timer
            self.update_timer = QTimer()
            self.update_timer.timeout.connect(self.update)
            self.update_timer.start(100)  # 10 FPS
        
        def paintEvent(self, event):
            """Paint the overlay elements."""
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            if self.show_grid_mode:
                self._paint_grid(painter)
            
            if self.show_borders and self.show_numbers_mode:
                self._paint_element_borders(painter)
        
        def _paint_grid(self, painter: QPainter):
            """Paint the grid overlay."""
            width = self.width()
            height = self.height()
            
            # Calculate current grid area (considering drill-down)
            grid_rect = self._get_current_grid_rect()
            cell_width = grid_rect[2] // self.grid_size
            cell_height = grid_rect[3] // self.grid_size
            
            self.grid_cells = []
            cell_num = 1
            
            for row in range(self.grid_size):
                for col in range(self.grid_size):
                    x = grid_rect[0] + col * cell_width
                    y = grid_rect[1] + row * cell_height
                    
                    # Store cell
                    self.grid_cells.append(GridCell(
                        number=cell_num,
                        rect=(x, y, cell_width, cell_height)
                    ))
                    
                    # Draw cell fill
                    painter.setBrush(QBrush(OverlayStyle.GRID_FILL_COLOR))
                    painter.setPen(QPen(OverlayStyle.GRID_LINE_COLOR, 2))
                    painter.drawRect(x, y, cell_width, cell_height)
                    
                    # Draw number in center
                    center_x = x + cell_width // 2
                    center_y = y + cell_height // 2
                    
                    # Number background circle
                    painter.setBrush(QBrush(OverlayStyle.GRID_LINE_COLOR))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(QPoint(center_x, center_y), 25, 25)
                    
                    # Number text
                    painter.setPen(QPen(OverlayStyle.GRID_TEXT_COLOR))
                    font = QFont("Arial", OverlayStyle.GRID_FONT_SIZE, QFont.Weight.Bold)
                    painter.setFont(font)
                    painter.drawText(
                        QRect(center_x - 25, center_y - 25, 50, 50),
                        Qt.AlignmentFlag.AlignCenter,
                        str(cell_num)
                    )
                    
                    cell_num += 1
        
        def _paint_element_borders(self, painter: QPainter):
            """Paint borders around detected elements."""
            painter.setPen(QPen(OverlayStyle.ELEMENT_BORDER_COLOR, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            for elem in self.elements:
                x, y, w, h = elem.rect
                painter.drawRect(x, y, w, h)
        
        def _get_current_grid_rect(self) -> Tuple[int, int, int, int]:
            """Get current grid rectangle (for drill-down support)."""
            rect = (0, 0, self.width(), self.height())
            
            # Apply drill-down path
            for cell_num in self._grid_drill_path:
                cell_width = rect[2] // self.grid_size
                cell_height = rect[3] // self.grid_size
                
                # Find cell position
                idx = cell_num - 1
                row = idx // self.grid_size
                col = idx % self.grid_size
                
                rect = (
                    rect[0] + col * cell_width,
                    rect[1] + row * cell_height,
                    cell_width,
                    cell_height
                )
            
            return rect
        
        def show_numbers(self, elements: List[UIElement]):
            """Display number labels on elements."""
            self.elements = elements
            self.show_numbers_mode = True
            
            # Clear existing labels
            for label in self._labels:
                label.deleteLater()
            self._labels = []
            
            # Create new labels
            for elem in elements:
                label = NumberLabel(elem.number, self)
                label.move(elem.rect[0], elem.rect[1])
                label.clicked.connect(self._on_label_clicked)
                label.show()
                self._labels.append(label)
            
            self.show()
            self.update()
        
        def show_grid(self, size: int = 3):
            """Display grid overlay."""
            self.grid_size = max(2, min(9, size))
            self.show_grid_mode = True
            self._grid_drill_path = []
            
            self.show()
            self.update()
        
        def drill_grid(self, cell_number: int):
            """Drill into a grid cell (Voice Access feature)."""
            if 1 <= cell_number <= self.grid_size * self.grid_size:
                self._grid_drill_path.append(cell_number)
                self.update()
        
        def undo_drill(self):
            """Go back one level in grid drill-down."""
            if self._grid_drill_path:
                self._grid_drill_path.pop()
                self.update()
        
        def hide_all(self):
            """Hide all overlays."""
            self.show_numbers_mode = False
            self.show_grid_mode = False
            
            for label in self._labels:
                label.hide()
            
            self.hide()
        
        def _on_label_clicked(self, number: int):
            """Handle label click."""
            self.element_selected.emit(number)
        
        def get_cell_center(self, number: int) -> Optional[Tuple[int, int]]:
            """Get center coordinates of a grid cell."""
            for cell in self.grid_cells:
                if cell.number == number:
                    return cell.center
            return None
        
        def get_element_center(self, number: int) -> Optional[Tuple[int, int]]:
            """Get center coordinates of an element."""
            for elem in self.elements:
                if elem.number == number:
                    return elem.center
            return None
    
    
    class VoxMindOverlayQt:
        """
        Manager for the PyQt overlay.
        
        Usage:
            overlay = VoxMindOverlayQt()
            overlay.start()
            overlay.show_numbers()  # Detect and show numbers
            overlay.show_grid()     # Show 3x3 grid
            overlay.click(5)        # Click element/cell 5
            overlay.hide()
        """
        
        def __init__(self):
            self._app: Optional[QApplication] = None
            self._window: Optional[OverlayWindow] = None
            self._running = False
            self._on_click: Optional[Callable[[int, int], None]] = None
        
        def start(self):
            """Initialize the Qt application and overlay window."""
            if self._running:
                return
            
            # Create Qt app if needed
            if QApplication.instance() is None:
                self._app = QApplication(sys.argv)
            else:
                self._app = QApplication.instance()
            
            self._window = OverlayWindow()
            self._window.element_selected.connect(self._handle_selection)
            self._window.grid_selected.connect(self._handle_selection)
            
            self._running = True
        
        def stop(self):
            """Stop the overlay."""
            if self._window:
                self._window.hide()
                self._window.close()
                self._window.deleteLater()
                self._window = None
            if self._app:
                self._app.processEvents()
            self._running = False
        
        def show_numbers(self):
            """Detect UI elements and show number labels."""
            if not self._running:
                self.start()
            
            if not self._window:
                return
            
            # Use cached elements if available and fresh (within 2 seconds)
            import time
            current_time = time.time()
            if (hasattr(self, '_cached_elements') and 
                hasattr(self, '_cache_time') and
                current_time - self._cache_time < 2.0):
                elements = self._cached_elements
            else:
                elements = self._detect_elements()
                self._cached_elements = elements
                self._cache_time = current_time
            
            self._window.show_numbers(elements)
        
        def show_numbers_fast(self):
            """Show numbers using pre-cached elements (instant)."""
            if not self._running:
                self.start()
            
            if not self._window:
                return
            
            # Use cached elements or get mock elements for instant response
            if hasattr(self, '_cached_elements') and self._cached_elements:
                elements = self._cached_elements
            else:
                elements = self._get_mock_elements()
            
            self._window.show_numbers(elements)
            
            # Start background refresh
            self._refresh_elements_async()
        
        def _refresh_elements_async(self):
            """Refresh elements in background thread."""
            import threading
            def refresh():
                import time
                elements = self._detect_elements()
                self._cached_elements = elements
                self._cache_time = time.time()
                # Update overlay if still visible
                if self._window and hasattr(self._window, '_numbers_visible') and self._window._numbers_visible:
                    self._window.show_numbers(elements)
            
            thread = threading.Thread(target=refresh, daemon=True)
            thread.start()
        
        def preload_elements(self):
            """Pre-detect elements in background for faster show_numbers."""
            import threading
            def preload():
                import time
                elements = self._detect_elements()
                self._cached_elements = elements
                self._cache_time = time.time()
                logger.info(f"Preloaded {len(elements)} UI elements")
            
            thread = threading.Thread(target=preload, daemon=True)
            thread.start()
        
        def show_grid(self, size: int = 3):
            """Show grid overlay."""
            if not self._running:
                self.start()
            
            if not self._window:
                return
                
            self._window.show_grid(size)
        
        def hide(self):
            """Hide the overlay."""
            if self._window:
                self._window.hide_all()
        
        def click(self, number: int) -> Optional[Tuple[int, int]]:
            """
            Get coordinates for a number and optionally click.
            
            Returns:
                (x, y) coordinates or None
            """
            if not self._window:
                return None
            
            # Try element first
            coords = self._window.get_element_center(number)
            if not coords:
                coords = self._window.get_cell_center(number)
            
            if coords and self._on_click:
                self._on_click(coords[0], coords[1])
            
            return coords
        
        def drill(self, number: int):
            """Drill into grid cell."""
            if self._window:
                self._window.drill_grid(number)
        
        def undo(self):
            """Undo last grid drill."""
            if self._window:
                self._window.undo_drill()
        
        def set_click_handler(self, handler: Callable[[int, int], None]):
            """Set handler for when a number is clicked."""
            self._on_click = handler
        
        def set_show_borders(self, show: bool):
            """Toggle element borders."""
            if self._window:
                self._window.show_borders = show
        
        def set_contrast(self, level: str):
            """Set label contrast level."""
            if self._window:
                self._window.contrast_level = level
        
        def _handle_selection(self, number: int):
            """Handle element/cell selection."""
            coords = self.click(number)
            if coords:
                logger.info(f"Selected {number} at {coords}")
        
        def _detect_elements(self) -> List[UIElement]:
            """Detect clickable elements on screen - optimized version."""
            elements = []
            
            if not HAS_PYWINAUTO:
                # Return mock elements
                return self._get_mock_elements()
            
            try:
                # Only scan the foreground window for speed
                import win32gui
                fg_hwnd = win32gui.GetForegroundWindow()
                
                desktop = Desktop(backend='uia')
                
                # Get foreground window only for faster detection
                try:
                    fg_window = desktop.window(handle=fg_hwnd)
                    windows = [fg_window]
                except (LookupError, AttributeError, Exception) as e:
                    # Fallback to top 2 windows
                    logger.debug(f"Foreground window lookup failed: {e}")
                    windows = desktop.windows()[:2]
                
                num = 1
                # Only scan essential control types
                control_types = ['Button', 'Edit', 'MenuItem', 'TabItem', 'ListItem', 'Hyperlink']
                
                for window in windows:
                    try:
                        # Limit scan depth and count for speed
                        for ctrl_type in control_types:
                            try:
                                for ctrl in window.descendants(control_type=ctrl_type, depth=5)[:10]:
                                    try:
                                        rect = ctrl.rectangle()
                                        # Skip tiny or off-screen elements
                                        if rect.width() < 15 or rect.height() < 15:
                                            continue
                                        if rect.left < -10 or rect.top < -10:
                                            continue
                                        if rect.right > 4000 or rect.bottom > 3000:
                                            continue
                                        
                                        elements.append(UIElement(
                                            number=num,
                                            name=ctrl.window_text() or f"{ctrl_type} {num}",
                                            rect=(rect.left, rect.top, rect.width(), rect.height()),
                                            element_type=ctrl_type.lower()
                                        ))
                                        num += 1
                                        
                                        if num > 30:  # Limit for usability
                                            break
                                    except (AttributeError, OSError, Exception):
                                        continue
                                
                                if num > 30:
                                    break
                            except (AttributeError, OSError, Exception):
                                continue
                        
                        if num > 30:
                            break
                    except (AttributeError, OSError, Exception):
                        continue
                
            except Exception as e:
                logger.error(f"Element detection error: {e}")
                elements = self._get_mock_elements()
            
            return elements
        
        def _detect_elements_fast(self) -> List[UIElement]:
            """Ultra-fast element detection using win32 only."""
            elements = []
            try:
                import win32gui
                import win32con
                
                num = 1
                
                def enum_child(hwnd, results):
                    nonlocal num
                    if num > 20:
                        return True
                    try:
                        if win32gui.IsWindowVisible(hwnd):
                            rect = win32gui.GetWindowRect(hwnd)
                            w, h = rect[2] - rect[0], rect[3] - rect[1]
                            if 15 < w < 500 and 15 < h < 100:
                                text = win32gui.GetWindowText(hwnd) or f"Element {num}"
                                elements.append(UIElement(
                                    number=num,
                                    name=text[:30],
                                    rect=(rect[0], rect[1], w, h)
                                ))
                                num += 1
                    except (OSError, AttributeError, Exception):
                        pass
                    return True
                
                fg_hwnd = win32gui.GetForegroundWindow()
                win32gui.EnumChildWindows(fg_hwnd, enum_child, None)
                
            except Exception as e:
                logger.warning(f"Fast detection failed: {e}")
                elements = self._get_mock_elements()
            
            return elements
        
        def _get_mock_elements(self) -> List[UIElement]:
            """Mock elements for testing."""
            screen_height = self._window.height() if self._window else 1080
            return [
                UIElement(1, "Start", (0, screen_height - 48, 48, 48)),
                UIElement(2, "Search", (50, screen_height - 48, 200, 48)),
                UIElement(3, "Browser", (300, screen_height - 48, 48, 48)),
            ]
        
        def process_events(self):
            """Process Qt events (call in main loop)."""
            if self._app:
                self._app.processEvents()


# === Public API ===

_qt_overlay: Optional['VoxMindOverlayQt'] = None


def get_overlay() -> Optional['VoxMindOverlayQt']:
    """Get the overlay instance (PyQt version)."""
    global _qt_overlay
    
    if not HAS_PYQT:
        logger.error("PyQt not installed. Install with: pip install PyQt6")
        return None
    
    if _qt_overlay is None:
        _qt_overlay = VoxMindOverlayQt()
    
    return _qt_overlay


def is_available() -> bool:
    """Check if PyQt overlay is available."""
    return HAS_PYQT


# === Demo ===

if __name__ == "__main__":
    if not HAS_PYQT:
        print("PyQt not installed!")
        print("Install with: pip install PyQt6")
        sys.exit(1)
    
    print("VoxMind Qt Overlay Demo")
    print("=" * 40)
    print("Commands:")
    print("  n - Show numbers")
    print("  g - Show grid")
    print("  h - Hide")
    print("  1-9 - Click number")
    print("  d<num> - Drill into grid cell")
    print("  u - Undo drill")
    print("  q - Quit")
    print()
    
    overlay = get_overlay()
    if not overlay:
        print("Failed to create overlay")
        sys.exit(1)
    
    # Type assertion for Pylance - overlay is definitely not None here
    active_overlay: VoxMindOverlayQt = overlay
        
    active_overlay.start()
    
    # Set up click handler to actually click
    if HAS_PYAUTOGUI:
        active_overlay.set_click_handler(lambda x, y: pyautogui.click(x, y))
    
    import threading
    from queue import Queue, Empty
    
    # Use a queue to pass commands from input thread to main thread
    cmd_queue: Queue[str] = Queue()
    
    def input_loop():
        while True:
            try:
                cmd = input("> ").strip().lower()
                cmd_queue.put(cmd)
                if cmd == 'q':
                    break
            except EOFError:
                break
            except Exception as e:
                print(f"Input error: {e}")
    
    # Run input in a thread
    input_thread = threading.Thread(target=input_loop, daemon=True)
    input_thread.start()
    
    # Main Qt event loop - process commands here (in main thread)
    try:
        while active_overlay._running:
            # Process Qt events
            active_overlay.process_events()
            
            # Check for commands from input thread
            try:
                cmd = cmd_queue.get_nowait()
                
                if cmd == 'q':
                    active_overlay.stop()
                    break
                elif cmd == 'n':
                    active_overlay.show_numbers()
                    print("Showing numbers...")
                elif cmd == 'g':
                    active_overlay.show_grid()
                    print("Showing grid...")
                elif cmd == 'h':
                    active_overlay.hide()
                    print("Hidden")
                elif cmd.startswith('d') and len(cmd) > 1:
                    num = int(cmd[1:])
                    active_overlay.drill(num)
                    print(f"Drilled into cell {num}")
                elif cmd == 'u':
                    active_overlay.undo()
                    print("Undid drill")
                elif cmd.isdigit():
                    num = int(cmd)
                    coords = active_overlay.click(num)
                    if coords:
                        print(f"Clicked at {coords}")
                    else:
                        print("Number not found")
            except Empty:
                pass
            except Exception as e:
                print(f"Command error: {e}")
            
            time.sleep(0.01)
    except KeyboardInterrupt:
        pass
    finally:
        active_overlay.stop()
