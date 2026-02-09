"""Test snap, show desktop, and drag functionality"""
from core.app_control import get_app_controller, parse_app_command
import time

controller = get_app_controller()

print('=' * 60)
print('VoxMind App Control - Testing Snap, Desktop, and Drag')
print('=' * 60)

# Test command parsing
print('\n[1] Command Parsing:')
commands = [
    'snap left',
    'snap right',
    'snap top left',
    'snap top right',
    'snap bottom left',
    'snap bottom right',
    'show desktop',
    'drag left',
    'drag right 200',
    'drag up 50',
    'move window to 100, 200',
]
for cmd in commands:
    result = parse_app_command(cmd)
    action = result.get('action') if result else None
    extra = ''
    if result:
        if 'position' in result:
            extra = f" -> {result['position']}"
        elif 'dx' in result:
            extra = f" -> dx={result['dx']}, dy={result['dy']}"
        elif 'x' in result:
            extra = f" -> x={result['x']}, y={result['y']}"
    print(f'    "{cmd}" -> {action}{extra}')

# Test snap operations
print('\n[2] Testing snap left...')
success, msg = controller.snap('left')
print(f'    {msg}')
time.sleep(1)

print('\n[3] Testing snap right...')
success, msg = controller.snap('right')
print(f'    {msg}')
time.sleep(1)

print('\n[4] Testing snap top right (corner)...')
success, msg = controller.snap('top_right')
print(f'    {msg}')
time.sleep(1)

print('\n[5] Testing snap bottom left (corner)...')
success, msg = controller.snap('bottom_left')
print(f'    {msg}')
time.sleep(1)

# Maximize and drag
print('\n[6] Maximizing...')
success, msg = controller.maximize()
print(f'    {msg}')

print('\n' + '=' * 60)
print('All tests complete!')
print('=' * 60)
print('\nVoice commands available:')
print('  Snap: "snap left/right/top/bottom"')
print('  Corners: "snap top left/top right/bottom left/bottom right"')
print('  Desktop: "show desktop"')
print('  Drag: "drag left/right/up/down", "drag to 100, 200"')
