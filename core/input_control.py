"""
VoxMind Input Control Module
=============================
Voice-driven mouse and keyboard automation inspired by:
- Microsoft Voice Access (Windows 11)
- Google Voice Access (Android)

Features:
- Mouse movement (absolute, relative, directional)
- Mouse clicks (left, right, double, drag)
- Grid overlay for precise clicking
- Scroll control
- Keyboard input
- UI element interaction

References:
- https://support.microsoft.com/en-us/topic/use-voice-access-to-control-your-pc-voice-commands
- https://support.google.com/accessibility/android/answer/6151848
"""

import threading
import logging
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Try to import pyautogui for mouse/keyboard control
try:
    import pyautogui
    pyautogui.FAILSAFE = True  # Move mouse to corner to abort
    pyautogui.PAUSE = 0.05  # Small delay between actions
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    logger.warning("pyautogui not installed. Mouse/keyboard control disabled.")

# Try to import screen info
try:
    import pyautogui
    SCREEN_WIDTH, SCREEN_HEIGHT = pyautogui.size()
except (ImportError, Exception) as e:
    logger.debug(f"Could not get screen size via pyautogui: {e}")
    SCREEN_WIDTH, SCREEN_HEIGHT = 1920, 1080


class MouseButton(Enum):
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


class Direction(Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    UP_LEFT = "up_left"
    UP_RIGHT = "up_right"
    DOWN_LEFT = "down_left"
    DOWN_RIGHT = "down_right"


@dataclass
class GridCell:
    """Represents a cell in the screen grid overlay."""
    number: int
    x: int
    y: int
    width: int
    height: int
    center_x: int
    center_y: int


class MouseController:
    """
    Voice-controlled mouse operations.
    
    Supports Microsoft Voice Access style commands:
    - "Mouse grid" - Show numbered grid overlay
    - "Click <number>" - Click on grid cell
    - "Move mouse <direction>" - Move in direction
    - "Move mouse to <x> <y>" - Move to coordinates
    - "Click" / "Double click" / "Right click"
    - "Drag from <n> to <n>"
    - "Scroll up/down"
    """
    
    def __init__(self):
        self.grid_active = False
        self.grid_cells: Dict[int, GridCell] = {}
        self.grid_size = 9  # 3x3 default, can be 9x9 for precision
        self.last_position: Tuple[int, int] = (0, 0)
        self._lock = threading.Lock()
        
        # Movement speed settings
        self.move_speed = 50  # pixels per movement command
        self.fine_move_speed = 10  # for precise movements
        
    def _check_available(self) -> bool:
        """Check if mouse control is available."""
        if not PYAUTOGUI_AVAILABLE:
            logger.error("Mouse control unavailable: pyautogui not installed")
            return False
        return True
    
    # =========================================================================
    # BASIC MOUSE OPERATIONS
    # =========================================================================
    
    def get_position(self) -> Tuple[int, int]:
        """Get current mouse position."""
        if not self._check_available():
            return (0, 0)
        return pyautogui.position()
    
    def move_to(self, x: int, y: int, duration: float = 0.2) -> bool:
        """Move mouse to absolute coordinates."""
        if not self._check_available():
            return False
        
        try:
            # Clamp to screen bounds
            x = max(0, min(x, SCREEN_WIDTH - 1))
            y = max(0, min(y, SCREEN_HEIGHT - 1))
            
            pyautogui.moveTo(x, y, duration=duration)
            self.last_position = (x, y)
            logger.info(f"Mouse moved to ({x}, {y})")
            return True
        except Exception as e:
            logger.error(f"Failed to move mouse: {e}")
            return False
    
    def move_relative(self, dx: int, dy: int, duration: float = 0.1) -> bool:
        """Move mouse relative to current position."""
        if not self._check_available():
            return False
        
        try:
            pyautogui.moveRel(dx, dy, duration=duration)
            self.last_position = pyautogui.position()
            logger.info(f"Mouse moved by ({dx}, {dy})")
            return True
        except Exception as e:
            logger.error(f"Failed to move mouse: {e}")
            return False
    
    def move_direction(self, direction: Direction, distance: Optional[int] = None,
                       fine: bool = False) -> bool:
        """Move mouse in a direction."""
        if distance is None:
            distance = self.fine_move_speed if fine else self.move_speed
        
        direction_map = {
            Direction.UP: (0, -distance),
            Direction.DOWN: (0, distance),
            Direction.LEFT: (-distance, 0),
            Direction.RIGHT: (distance, 0),
            Direction.UP_LEFT: (-distance, -distance),
            Direction.UP_RIGHT: (distance, -distance),
            Direction.DOWN_LEFT: (-distance, distance),
            Direction.DOWN_RIGHT: (distance, distance),
        }
        
        dx, dy = direction_map.get(direction, (0, 0))
        return self.move_relative(dx, dy)
    
    def click(self, button: MouseButton = MouseButton.LEFT,
              clicks: int = 1, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Perform mouse click."""
        if not self._check_available():
            return False
        
        try:
            if x is not None and y is not None:
                pyautogui.click(x, y, clicks=clicks, button=button.value)
            else:
                pyautogui.click(clicks=clicks, button=button.value)
            
            action = "Double clicked" if clicks == 2 else "Clicked"
            logger.info(f"{action} {button.value} button")
            return True
        except Exception as e:
            logger.error(f"Failed to click: {e}")
            return False
    
    def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Double click."""
        return self.click(MouseButton.LEFT, clicks=2, x=x, y=y)
    
    def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Right click."""
        return self.click(MouseButton.RIGHT, clicks=1, x=x, y=y)
    
    def triple_click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Triple click (select paragraph/line)."""
        return self.click(MouseButton.LEFT, clicks=3, x=x, y=y)
    
    def drag_to(self, x: int, y: int, duration: float = 0.5,
                button: MouseButton = MouseButton.LEFT) -> bool:
        """Drag from current position to target."""
        if not self._check_available():
            return False
        
        try:
            pyautogui.dragTo(x, y, duration=duration, button=button.value)
            logger.info(f"Dragged to ({x}, {y})")
            return True
        except Exception as e:
            logger.error(f"Failed to drag: {e}")
            return False
    
    def drag_relative(self, dx: int, dy: int, duration: float = 0.5) -> bool:
        """Drag relative to current position."""
        if not self._check_available():
            return False
        
        try:
            pyautogui.drag(dx, dy, duration=duration)
            logger.info(f"Dragged by ({dx}, {dy})")
            return True
        except Exception as e:
            logger.error(f"Failed to drag: {e}")
            return False
    
    # =========================================================================
    # SCROLL OPERATIONS
    # =========================================================================
    
    def scroll(self, clicks: int, direction: str = "down") -> bool:
        """Scroll the mouse wheel."""
        if not self._check_available():
            return False
        
        try:
            # Negative for down, positive for up
            amount = -clicks if direction == "down" else clicks
            pyautogui.scroll(amount)
            logger.info(f"Scrolled {direction} by {clicks}")
            return True
        except Exception as e:
            logger.error(f"Failed to scroll: {e}")
            return False
    
    def scroll_up(self, clicks: int = 3) -> bool:
        """Scroll up."""
        return self.scroll(clicks, "up")
    
    def scroll_down(self, clicks: int = 3) -> bool:
        """Scroll down."""
        return self.scroll(clicks, "down")
    
    def scroll_to_top(self) -> bool:
        """Scroll to top of page (Ctrl+Home)."""
        if not self._check_available():
            return False
        try:
            pyautogui.hotkey('ctrl', 'Home')
            return True
        except Exception as e:
            logger.warning(f"Failed to scroll to top: {e}")
            return False
    
    def scroll_to_bottom(self) -> bool:
        """Scroll to bottom of page (Ctrl+End)."""
        if not self._check_available():
            return False
        try:
            pyautogui.hotkey('ctrl', 'End')
            return True
        except Exception as e:
            logger.warning(f"Failed to scroll to bottom: {e}")
            return False
    
    # =========================================================================
    # GRID OVERLAY (Microsoft Voice Access Style)
    # =========================================================================
    
    def create_grid(self, rows: int = 3, cols: int = 3) -> Dict[int, GridCell]:
        """
        Create a numbered grid overlay for the screen.
        
        Like Microsoft Voice Access:
        - Say "Mouse grid" to show grid
        - Say "<number>" to click that cell
        - Say "<number> <number>" to zoom into sub-grid
        """
        cell_width = SCREEN_WIDTH // cols
        cell_height = SCREEN_HEIGHT // rows
        
        self.grid_cells = {}
        cell_num = 1
        
        for row in range(rows):
            for col in range(cols):
                x = col * cell_width
                y = row * cell_height
                center_x = x + cell_width // 2
                center_y = y + cell_height // 2
                
                self.grid_cells[cell_num] = GridCell(
                    number=cell_num,
                    x=x,
                    y=y,
                    width=cell_width,
                    height=cell_height,
                    center_x=center_x,
                    center_y=center_y
                )
                cell_num += 1
        
        self.grid_active = True
        self.grid_size = rows * cols
        logger.info(f"Created {rows}x{cols} grid ({self.grid_size} cells)")
        return self.grid_cells
    
    def click_grid(self, cell_number: int) -> bool:
        """Click the center of a grid cell."""
        if cell_number not in self.grid_cells:
            logger.error(f"Invalid grid cell: {cell_number}")
            return False
        
        cell = self.grid_cells[cell_number]
        return self.click(x=cell.center_x, y=cell.center_y)
    
    def zoom_grid(self, cell_number: int, subdivisions: int = 3) -> Dict[int, GridCell]:
        """
        Zoom into a grid cell and create a sub-grid.
        For precision clicking in small areas.
        """
        if cell_number not in self.grid_cells:
            logger.error(f"Invalid grid cell: {cell_number}")
            return {}
        
        parent = self.grid_cells[cell_number]
        cell_width = parent.width // subdivisions
        cell_height = parent.height // subdivisions
        
        self.grid_cells = {}
        cell_num = 1
        
        for row in range(subdivisions):
            for col in range(subdivisions):
                x = parent.x + col * cell_width
                y = parent.y + row * cell_height
                center_x = x + cell_width // 2
                center_y = y + cell_height // 2
                
                self.grid_cells[cell_num] = GridCell(
                    number=cell_num,
                    x=x,
                    y=y,
                    width=cell_width,
                    height=cell_height,
                    center_x=center_x,
                    center_y=center_y
                )
                cell_num += 1
        
        logger.info(f"Zoomed into cell {cell_number}, created {subdivisions}x{subdivisions} sub-grid")
        return self.grid_cells
    
    def close_grid(self):
        """Close the grid overlay."""
        self.grid_active = False
        self.grid_cells = {}
        logger.info("Grid closed")


class KeyboardController:
    """
    Voice-controlled keyboard operations.
    
    Supports:
    - Text input: "Type <text>"
    - Keys: "Press enter", "Press escape"
    - Hotkeys: "Press control c", "Press alt f4"
    - Selection: "Select all", "Select word"
    - Editing: "Copy", "Paste", "Cut", "Undo", "Redo"
    - Navigation: "Go to start", "Go to end"
    """
    
    def __init__(self):
        self._lock = threading.Lock()
    
    def _check_available(self) -> bool:
        if not PYAUTOGUI_AVAILABLE:
            logger.error("Keyboard control unavailable: pyautogui not installed")
            return False
        return True
    
    # =========================================================================
    # TEXT INPUT
    # =========================================================================
    
    def type_text(self, text: str, interval: float = 0.02) -> bool:
        """Type text character by character."""
        if not self._check_available():
            return False
        
        try:
            pyautogui.typewrite(text, interval=interval)
            logger.info(f"Typed: {text[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to type: {e}")
            return False
    
    def type_unicode(self, text: str) -> bool:
        """Type text with Unicode support (slower but handles all chars)."""
        if not self._check_available():
            return False
        
        try:
            # pyautogui.write handles Unicode on Windows
            pyautogui.write(text)
            logger.info(f"Typed unicode: {text[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to type unicode: {e}")
            return False
    
    # =========================================================================
    # KEY PRESSES
    # =========================================================================
    
    def press_key(self, key: str) -> bool:
        """Press a single key."""
        if not self._check_available():
            return False
        
        try:
            pyautogui.press(key)
            logger.info(f"Pressed: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to press key: {e}")
            return False
    
    def hotkey(self, *keys: str) -> bool:
        """Press a key combination."""
        if not self._check_available():
            return False
        
        try:
            pyautogui.hotkey(*keys)
            logger.info(f"Hotkey: {'+'.join(keys)}")
            return True
        except Exception as e:
            logger.error(f"Failed to press hotkey: {e}")
            return False
    
    def hold_key(self, key: str) -> bool:
        """Hold down a key."""
        if not self._check_available():
            return False
        try:
            pyautogui.keyDown(key)
            return True
        except Exception as e:
            logger.warning(f"Failed to hold key '{key}': {e}")
            return False
    
    def release_key(self, key: str) -> bool:
        """Release a held key."""
        if not self._check_available():
            return False
        try:
            pyautogui.keyUp(key)
            return True
        except Exception as e:
            logger.warning(f"Failed to release key '{key}': {e}")
            return False
    
    # =========================================================================
    # COMMON ACTIONS
    # =========================================================================
    
    def copy(self) -> bool:
        """Copy selection (Ctrl+C)."""
        return self.hotkey('ctrl', 'c')
    
    def paste(self) -> bool:
        """Paste clipboard (Ctrl+V)."""
        return self.hotkey('ctrl', 'v')
    
    def cut(self) -> bool:
        """Cut selection (Ctrl+X)."""
        return self.hotkey('ctrl', 'x')
    
    def undo(self) -> bool:
        """Undo (Ctrl+Z)."""
        return self.hotkey('ctrl', 'z')
    
    def redo(self) -> bool:
        """Redo (Ctrl+Y or Ctrl+Shift+Z)."""
        return self.hotkey('ctrl', 'y')
    
    def select_all(self) -> bool:
        """Select all (Ctrl+A)."""
        return self.hotkey('ctrl', 'a')
    
    def delete(self) -> bool:
        """Delete selection."""
        return self.press_key('delete')
    
    def backspace(self) -> bool:
        """Backspace."""
        return self.press_key('backspace')
    
    def enter(self) -> bool:
        """Press Enter."""
        return self.press_key('enter')
    
    def escape(self) -> bool:
        """Press Escape."""
        return self.press_key('escape')
    
    def tab(self) -> bool:
        """Press Tab."""
        return self.press_key('tab')
    
    def space(self) -> bool:
        """Press Space."""
        return self.press_key('space')
    
    # =========================================================================
    # NAVIGATION
    # =========================================================================
    
    def go_to_start(self) -> bool:
        """Go to start of document (Ctrl+Home)."""
        return self.hotkey('ctrl', 'Home')
    
    def go_to_end(self) -> bool:
        """Go to end of document (Ctrl+End)."""
        return self.hotkey('ctrl', 'End')
    
    def go_to_line_start(self) -> bool:
        """Go to start of line (Home)."""
        return self.press_key('Home')
    
    def go_to_line_end(self) -> bool:
        """Go to end of line (End)."""
        return self.press_key('End')
    
    def next_word(self) -> bool:
        """Move to next word (Ctrl+Right)."""
        return self.hotkey('ctrl', 'Right')
    
    def prev_word(self) -> bool:
        """Move to previous word (Ctrl+Left)."""
        return self.hotkey('ctrl', 'Left')
    
    # =========================================================================
    # SELECTION
    # =========================================================================
    
    def select_word(self) -> bool:
        """Select current word (Ctrl+Shift+Right from word start)."""
        return self.hotkey('ctrl', 'shift', 'Right')
    
    def select_line(self) -> bool:
        """Select current line."""
        self.go_to_line_start()
        return self.hotkey('shift', 'End')
    
    def select_to_start(self) -> bool:
        """Select from cursor to start (Ctrl+Shift+Home)."""
        return self.hotkey('ctrl', 'shift', 'Home')
    
    def select_to_end(self) -> bool:
        """Select from cursor to end (Ctrl+Shift+End)."""
        return self.hotkey('ctrl', 'shift', 'End')
    
    # =========================================================================
    # WINDOW MANAGEMENT
    # =========================================================================
    
    def switch_window(self) -> bool:
        """Switch to next window (Alt+Tab)."""
        return self.hotkey('alt', 'tab')
    
    def close_window(self) -> bool:
        """Close current window (Alt+F4)."""
        return self.hotkey('alt', 'F4')
    
    def minimize_window(self) -> bool:
        """Minimize window (Win+Down)."""
        return self.hotkey('win', 'Down')
    
    def maximize_window(self) -> bool:
        """Maximize window (Win+Up)."""
        return self.hotkey('win', 'Up')
    
    def snap_left(self) -> bool:
        """Snap window left (Win+Left)."""
        return self.hotkey('win', 'Left')
    
    def snap_right(self) -> bool:
        """Snap window right (Win+Right)."""
        return self.hotkey('win', 'Right')
    
    def show_desktop(self) -> bool:
        """Show desktop (Win+D)."""
        return self.hotkey('win', 'd')
    
    def task_view(self) -> bool:
        """Open task view (Win+Tab)."""
        return self.hotkey('win', 'tab')
    
    def screenshot(self) -> bool:
        """Take screenshot (Win+Shift+S)."""
        return self.hotkey('win', 'shift', 's')


class InputController:
    """
    Unified voice input controller combining mouse and keyboard.
    
    This is the main interface for voice commands.
    """
    
    def __init__(self):
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        self._lock = threading.Lock()
    
    @property
    def available(self) -> bool:
        """Check if input control is available."""
        return PYAUTOGUI_AVAILABLE
    
    def get_screen_size(self) -> Tuple[int, int]:
        """Get screen dimensions."""
        return SCREEN_WIDTH, SCREEN_HEIGHT
    
    def get_mouse_position(self) -> Tuple[int, int]:
        """Get current mouse position."""
        return self.mouse.get_position()


# ============================================================================
# COMMAND PARSER FOR INPUT CONTROL
# ============================================================================

def parse_input_command(text: str) -> Dict[str, Any]:
    """
    Parse voice commands for input control.
    
    Supported commands:
    Mouse:
    - "click" / "double click" / "right click" / "triple click"
    - "move mouse up/down/left/right"
    - "move mouse to <x> <y>"
    - "scroll up/down"
    - "mouse grid" / "show grid" / "show mouse grid"
    - "click <number>" (grid mode)
    - "drag to <x> <y>"
    - "activate mouse mode" / "deactivate mouse mode"
    
    Keyboard:
    - "type <text>"
    - "press <key>"
    - "press control <key>"
    - "copy" / "paste" / "cut" / "undo" / "redo"
    - "select all" / "select word" / "select line"
    - "go to start" / "go to end"
    - "switch window" / "close window"
    - "take screenshot"
    """
    import re
    
    t = text.lower().strip()
    result = {"type": "unknown", "raw": text}
    
    # -------------------------------------------------------------------------
    # MOUSE COMMANDS
    # -------------------------------------------------------------------------
    
    # Click commands
    if re.search(r'\b(?:triple\s+click|click\s+three\s+times)\b', t):
        return {"type": "mouse_click", "button": "left", "clicks": 3, "raw": text}
    
    if re.search(r'\b(?:double\s+click|click\s+twice)\b', t):
        return {"type": "mouse_click", "button": "left", "clicks": 2, "raw": text}
    
    if re.search(r'\b(?:right\s+click|secondary\s+click)\b', t):
        return {"type": "mouse_click", "button": "right", "clicks": 1, "raw": text}
    
    if re.search(r'\b(?:middle\s+click)\b', t):
        return {"type": "mouse_click", "button": "middle", "clicks": 1, "raw": text}
    
    # Grid click: "click 5" or "5"
    grid_match = re.search(r'\b(?:click\s+)?(\d{1,2})\b', t)
    if grid_match and len(t.split()) <= 2:
        return {"type": "grid_click", "cell": int(grid_match.group(1)), "raw": text}
    
    if re.search(r'\bclick\b', t):
        return {"type": "mouse_click", "button": "left", "clicks": 1, "raw": text}
    
    # Mouse grid
    if re.search(r'\b(?:mouse\s+grid|show\s+grid|grid\s+overlay|show\s+mouse\s+grid)\b', t):
        return {"type": "mouse_grid", "action": "show", "raw": text}
    
    if re.search(r'\b(?:close\s+grid|hide\s+grid|cancel\s+grid)\b', t):
        return {"type": "mouse_grid", "action": "hide", "raw": text}
    
    # Mouse mode activation/deactivation
    if re.search(r'\b(?:activate\s+mouse\s+mode|enable\s+mouse\s+mode|mouse\s+mode\s+on|start\s+mouse\s+mode)\b', t):
        return {"type": "mouse_mode", "action": "activate", "raw": text}
    
    if re.search(r'\b(?:deactivate\s+mouse\s+mode|disable\s+mouse\s+mode|mouse\s+mode\s+off|stop\s+mouse\s+mode|exit\s+mouse\s+mode)\b', t):
        return {"type": "mouse_mode", "action": "deactivate", "raw": text}
    
    # Mouse movement - directional
    dir_match = re.search(
        r'\bmove\s+(?:mouse\s+)?(?:cursor\s+)?(up|down|left|right|'
        r'up\s*left|up\s*right|down\s*left|down\s*right)'
        r'(?:\s+(\d+)(?:\s*(?:pixels?|px))?)?\b', t
    )
    if dir_match:
        direction = dir_match.group(1).replace(" ", "_")
        distance = int(dir_match.group(2)) if dir_match.group(2) else None
        return {"type": "mouse_move", "direction": direction, "distance": distance, "raw": text}
    
    # Scroll - MUST come before shorthand directional to avoid "scroll down" -> "mouse move down"
    scroll_match = re.search(r'\bscroll\s+(up|down)(?:\s+(\d+))?\b', t)
    if scroll_match:
        direction = scroll_match.group(1)
        amount = int(scroll_match.group(2)) if scroll_match.group(2) else 3
        return {"type": "scroll", "direction": direction, "amount": amount, "raw": text}
    
    if re.search(r'\bscroll\s+to\s+(?:the\s+)?top\b', t):
        return {"type": "scroll", "direction": "top", "raw": text}
    
    if re.search(r'\bscroll\s+to\s+(?:the\s+)?bottom\b', t):
        return {"type": "scroll", "direction": "bottom", "raw": text}
    
    # Mouse movement - shorthand directional (e.g., "left 50 pixels", "up 100")
    # Must NOT match if there's a word before the direction like "scroll down"
    shorthand_match = re.search(
        r'\b(up|down|left|right)(?:\s+(\d+)(?:\s*(?:pixels?|px))?)?\b', t
    )
    # Only match if it's a simple directional command (1-3 words) AND starts with the direction
    if shorthand_match and len(t.split()) <= 3 and t.startswith(shorthand_match.group(1)):
        direction = shorthand_match.group(1)
        distance = int(shorthand_match.group(2)) if shorthand_match.group(2) else 50
        return {"type": "mouse_move", "direction": direction, "distance": distance, "raw": text}
    
    # Mouse movement - coordinates
    coord_match = re.search(r'\bmove\s+(?:mouse\s+)?(?:cursor\s+)?to\s+(\d+)\s*,?\s*(\d+)\b', t)
    if coord_match:
        return {
            "type": "mouse_move",
            "x": int(coord_match.group(1)),
            "y": int(coord_match.group(2)),
            "raw": text
        }
    
    # Drag
    drag_match = re.search(r'\bdrag\s+(?:to\s+)?(\d+)\s*,?\s*(\d+)\b', t)
    if drag_match:
        return {
            "type": "drag",
            "x": int(drag_match.group(1)),
            "y": int(drag_match.group(2)),
            "raw": text
        }
    
    # -------------------------------------------------------------------------
    # KEYBOARD COMMANDS
    # -------------------------------------------------------------------------
    
    # Type text
    type_match = re.search(r'\b(?:type|write|enter\s+text)\s+(.+)', t)
    if type_match:
        return {"type": "type_text", "text": type_match.group(1), "raw": text}
    
    # Press key with modifiers
    hotkey_match = re.search(
        r'\bpress\s+(control|ctrl|alt|shift|win|windows|command|cmd)'
        r'(?:\s+(control|ctrl|alt|shift))?\s+(\w+)\b', t
    )
    if hotkey_match:
        modifiers = [hotkey_match.group(1)]
        if hotkey_match.group(2):
            modifiers.append(hotkey_match.group(2))
        # Normalize modifier names
        mod_map = {'control': 'ctrl', 'windows': 'win', 'command': 'ctrl', 'cmd': 'ctrl'}
        modifiers = [mod_map.get(m, m) for m in modifiers]
        key = hotkey_match.group(3)
        return {"type": "hotkey", "modifiers": modifiers, "key": key, "raw": text}
    
    # Press single key
    key_match = re.search(r'\bpress\s+(\w+)\b', t)
    if key_match:
        return {"type": "press_key", "key": key_match.group(1), "raw": text}
    
    # Common actions
    if re.search(r'\bcopy\b', t):
        return {"type": "hotkey", "modifiers": ["ctrl"], "key": "c", "raw": text}
    if re.search(r'\bpaste\b', t):
        return {"type": "hotkey", "modifiers": ["ctrl"], "key": "v", "raw": text}
    if re.search(r'\bcut\b', t):
        return {"type": "hotkey", "modifiers": ["ctrl"], "key": "x", "raw": text}
    if re.search(r'\bundo\b', t):
        return {"type": "hotkey", "modifiers": ["ctrl"], "key": "z", "raw": text}
    if re.search(r'\bredo\b', t):
        return {"type": "hotkey", "modifiers": ["ctrl"], "key": "y", "raw": text}
    if re.search(r'\bselect\s+all\b', t):
        return {"type": "hotkey", "modifiers": ["ctrl"], "key": "a", "raw": text}
    
    # Selection
    if re.search(r'\bselect\s+word\b', t):
        return {"type": "select", "target": "word", "raw": text}
    if re.search(r'\bselect\s+line\b', t):
        return {"type": "select", "target": "line", "raw": text}
    if re.search(r'\bselect\s+(?:to\s+)?(?:the\s+)?start\b', t):
        return {"type": "select", "target": "to_start", "raw": text}
    if re.search(r'\bselect\s+(?:to\s+)?(?:the\s+)?end\b', t):
        return {"type": "select", "target": "to_end", "raw": text}
    
    # Navigation
    if re.search(r'\bgo\s+(?:to\s+)?(?:the\s+)?start\b', t):
        return {"type": "navigate", "target": "start", "raw": text}
    if re.search(r'\bgo\s+(?:to\s+)?(?:the\s+)?end\b', t):
        return {"type": "navigate", "target": "end", "raw": text}
    if re.search(r'\bnext\s+word\b', t):
        return {"type": "navigate", "target": "next_word", "raw": text}
    if re.search(r'\bprevious\s+word\b', t):
        return {"type": "navigate", "target": "prev_word", "raw": text}
    
    # Window management
    if re.search(r'\bswitch\s+window\b', t):
        return {"type": "window", "action": "switch", "raw": text}
    if re.search(r'\bclose\s+window\b', t):
        return {"type": "window", "action": "close", "raw": text}
    if re.search(r'\bminimize\s+window\b', t):
        return {"type": "window", "action": "minimize", "raw": text}
    if re.search(r'\bmaximize\s+window\b', t):
        return {"type": "window", "action": "maximize", "raw": text}
    if re.search(r'\bsnap\s+(?:window\s+)?left\b', t):
        return {"type": "window", "action": "snap_left", "raw": text}
    if re.search(r'\bsnap\s+(?:window\s+)?right\b', t):
        return {"type": "window", "action": "snap_right", "raw": text}
    if re.search(r'\bshow\s+desktop\b', t):
        return {"type": "window", "action": "show_desktop", "raw": text}
    if re.search(r'\btask\s+view\b', t):
        return {"type": "window", "action": "task_view", "raw": text}
    if re.search(r'\b(?:take\s+)?screenshot\b', t):
        return {"type": "window", "action": "screenshot", "raw": text}
    
    # Help/Control commands for mouse - show available commands
    if re.search(r'\b(?:show|control|help)\s+(?:mouse|cursor)\s*(?:controls?|commands?)?\b', t):
        return {"type": "help", "topic": "mouse", "raw": text}
    if re.search(r'\b(?:mouse|cursor)\s+(?:controls?|commands?|help)\b', t):
        return {"type": "help", "topic": "mouse", "raw": text}
    
    # Help for keyboard
    if re.search(r'\b(?:show|control|help)\s+keyboard\s*(?:controls?|commands?)?\b', t):
        return {"type": "help", "topic": "keyboard", "raw": text}
    if re.search(r'\bkeyboard\s+(?:controls?|commands?|help)\b', t):
        return {"type": "help", "topic": "keyboard", "raw": text}
    
    # General input help
    if re.search(r'\b(?:show|what)\s+(?:are\s+)?(?:the\s+)?(?:voice\s+)?(?:input\s+)?(?:controls?|commands?)\b', t):
        return {"type": "help", "topic": "all", "raw": text}
    
    return result


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_controller: Optional[InputController] = None

def get_controller() -> InputController:
    """Get singleton InputController instance."""
    global _controller
    if _controller is None:
        _controller = InputController()
    return _controller


# ============================================================================
# TEST / DEMO
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("VoxMind Input Control Module")
    print("=" * 60)
    
    controller = get_controller()
    
    print(f"\nPyAutoGUI Available: {PYAUTOGUI_AVAILABLE}")
    print(f"Screen Size: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
    
    if PYAUTOGUI_AVAILABLE:
        pos = controller.get_mouse_position()
        print(f"Current Mouse Position: {pos}")
    
    # Test command parsing
    print("\n[Command Parsing Tests]")
    test_commands = [
        "click",
        "double click",
        "right click",
        "move mouse up",
        "move mouse down 100 pixels",
        "move mouse to 500, 300",
        "scroll down",
        "scroll up 5",
        "mouse grid",
        "show mouse grid",
        "activate mouse mode",
        "deactivate mouse mode",
        "click 5",
        "type hello world",
        "press enter",
        "press control c",
        "copy",
        "paste",
        "select all",
        "switch window",
        "take screenshot",
    ]
    
    for cmd in test_commands:
        parsed = parse_input_command(cmd)
        print(f"  '{cmd}' -> {parsed['type']}")
    
    print("\n" + "=" * 60)
    print("Input Control ready for voice commands!")
    print("=" * 60)
