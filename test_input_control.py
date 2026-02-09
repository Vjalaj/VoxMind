"""
Test suite for VoxMind Input Control (Voice Access)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.input_control import (
    parse_input_command,
    MouseController,
    KeyboardController,
    InputController,
    get_controller,
    PYAUTOGUI_AVAILABLE,
    MouseButton,
    Direction,
)

def test_command_parsing():
    """Test voice command parsing for input control."""
    print("\n[Testing Command Parsing]")
    
    # Mouse click commands
    tests = [
        # Basic clicks
        ("click", "mouse_click", {"button": "left", "clicks": 1}),
        ("double click", "mouse_click", {"button": "left", "clicks": 2}),
        ("triple click", "mouse_click", {"button": "left", "clicks": 3}),
        ("right click", "mouse_click", {"button": "right", "clicks": 1}),
        ("middle click", "mouse_click", {"button": "middle", "clicks": 1}),
        
        # Grid
        ("click 5", "grid_click", {"cell": 5}),
        ("click 9", "grid_click", {"cell": 9}),
        ("mouse grid", "mouse_grid", {"action": "show"}),
        ("show grid", "mouse_grid", {"action": "show"}),
        ("close grid", "mouse_grid", {"action": "hide"}),
        
        # Mouse movement
        ("move mouse up", "mouse_move", {"direction": "up"}),
        ("move mouse down 50 pixels", "mouse_move", {"direction": "down", "distance": 50}),
        ("move cursor left", "mouse_move", {"direction": "left"}),
        ("move mouse to 100, 200", "mouse_move", {"x": 100, "y": 200}),
        
        # Scrolling
        ("scroll up", "scroll", {"direction": "up"}),
        ("scroll down 5", "scroll", {"direction": "down", "amount": 5}),
        ("scroll to top", "scroll", {"direction": "top"}),
        ("scroll to bottom", "scroll", {"direction": "bottom"}),
        
        # Typing
        ("type hello world", "type_text", {"text": "hello world"}),
        ("type test message", "type_text", {"text": "test message"}),
        
        # Key presses
        ("press enter", "press_key", {"key": "enter"}),
        ("press escape", "press_key", {"key": "escape"}),
        ("press control c", "hotkey", {"modifiers": ["ctrl"], "key": "c"}),
        ("press alt f4", "hotkey", {"modifiers": ["alt"], "key": "f4"}),
        
        # Common actions
        ("copy", "hotkey", {"modifiers": ["ctrl"], "key": "c"}),
        ("paste", "hotkey", {"modifiers": ["ctrl"], "key": "v"}),
        ("cut", "hotkey", {"modifiers": ["ctrl"], "key": "x"}),
        ("undo", "hotkey", {"modifiers": ["ctrl"], "key": "z"}),
        ("redo", "hotkey", {"modifiers": ["ctrl"], "key": "y"}),
        ("select all", "hotkey", {"modifiers": ["ctrl"], "key": "a"}),
        
        # Window management
        ("switch window", "window", {"action": "switch"}),
        ("show desktop", "window", {"action": "show_desktop"}),
        ("take screenshot", "window", {"action": "screenshot"}),
    ]
    
    passed = 0
    failed = 0
    
    for cmd, expected_type, expected_params in tests:
        result = parse_input_command(cmd)
        
        if result.get('type') == expected_type:
            # Check specific params
            params_match = True
            for key, val in expected_params.items():
                if result.get(key) != val:
                    params_match = False
                    break
            
            if params_match:
                print(f"  ✓ '{cmd}' -> {expected_type}")
                passed += 1
            else:
                print(f"  ✗ '{cmd}' -> type OK but params mismatch: {result}")
                failed += 1
        else:
            print(f"  ✗ '{cmd}' -> expected {expected_type}, got {result.get('type')}")
            failed += 1
    
    print(f"\n  Passed: {passed}/{passed + failed}")
    return failed == 0


def test_controller_availability():
    """Test that controller is available."""
    print("\n[Testing Controller Availability]")
    
    controller = get_controller()
    
    print(f"  PyAutoGUI Available: {PYAUTOGUI_AVAILABLE}")
    print(f"  Controller Available: {controller.available}")
    
    if controller.available:
        pos = controller.get_mouse_position()
        print(f"  Current Mouse Position: {pos}")
        
        screen = controller.get_screen_size()
        print(f"  Screen Size: {screen[0]}x{screen[1]}")
    
    return controller.available


def test_mouse_grid():
    """Test grid creation."""
    print("\n[Testing Mouse Grid]")
    
    mouse = MouseController()
    
    # Create 3x3 grid
    cells = mouse.create_grid(3, 3)
    assert len(cells) == 9, f"Expected 9 cells, got {len(cells)}"
    print(f"  Created 3x3 grid: {len(cells)} cells")
    
    # Check cell centers are calculated
    for i in range(1, 10):
        cell = cells[i]
        assert cell.center_x > 0, f"Cell {i} has invalid center_x"
        assert cell.center_y > 0, f"Cell {i} has invalid center_y"
    
    print("  All cell centers valid")
    
    # Test zoom
    sub_cells = mouse.zoom_grid(5, 3)  # Zoom into cell 5
    assert len(sub_cells) == 9, f"Expected 9 sub-cells, got {len(sub_cells)}"
    print("  Zoom into cell 5: 9 sub-cells")
    
    mouse.close_grid()
    assert not mouse.grid_active, "Grid should be closed"
    print("  Grid closed")
    
    return True


def test_integration_with_parser():
    """Test integration with main command parser."""
    print("\n[Testing Integration with Main Parser]")
    
    from Priyapal.command_parser import parse_command
    
    test_commands = [
        ("click", "input_control"),
        ("double click", "input_control"),
        ("move mouse up", "input_control"),
        ("type hello", "input_control"),
        ("press enter", "input_control"),
        ("copy", "input_control"),
        ("paste", "input_control"),
        ("screenshot", "input_control"),
    ]
    
    passed = 0
    for cmd, expected in test_commands:
        result = parse_command(cmd)
        if result.get('command') == expected:
            print(f"  ✓ '{cmd}' -> {expected}")
            passed += 1
        else:
            print(f"  ✗ '{cmd}' -> expected {expected}, got {result.get('command')}")
    
    print(f"\n  Passed: {passed}/{len(test_commands)}")
    return passed == len(test_commands)


def main():
    print("=" * 60)
    print("VoxMind Input Control Test Suite")
    print("=" * 60)
    
    results = []
    
    results.append(("Command Parsing", test_command_parsing()))
    results.append(("Controller Availability", test_controller_availability()))
    results.append(("Mouse Grid", test_mouse_grid()))
    results.append(("Parser Integration", test_integration_with_parser()))
    
    print("\n" + "=" * 60)
    print("Results Summary:")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {name}: {status}")
    
    all_passed = all(r[1] for r in results)
    print("\n" + ("All tests passed!" if all_passed else "Some tests failed."))
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
