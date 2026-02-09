"""VoxMind App Control Demo Script"""
import time
from core.app_control import get_app_controller, parse_app_command

controller = get_app_controller()

print('=' * 60)
print('VoxMind App Control Demo')
print('=' * 60)

# Demo 1: Voice command parsing first
print('\n[1] Voice Command Parsing Examples:')
commands = [
    'open chrome',
    'open notepad',
    'close notepad',
    'switch to vs code',
    'minimize',
    'maximize calculator',
    'snap left',
    'snap top right',
    'show desktop',
    'list windows',
    'go to github.com',
]
for cmd in commands:
    result = parse_app_command(cmd)
    action = result.get('action') if result else None
    print(f'    "{cmd}" -> {action}')

# Demo 2: Launch an app
print('\n[2] Launching Calculator...')
success, msg = controller.open('calculator')
print(f'    {msg}')
time.sleep(2)

# Demo 3: List windows
print('\n[3] Current windows:')
for win in controller.list_windows()[:8]:
    print(f'    - {win[:50]}')

# Demo 4: Snap window
print('\n[4] Snapping Calculator to right side...')
success, msg = controller.snap('right', 'calculator')
print(f'    {msg}')
time.sleep(1)

# Demo 5: Launch Notepad
print('\n[5] Launching Notepad...')
success, msg = controller.open('notepad')
print(f'    {msg}')
time.sleep(2)

# Demo 6: Snap notepad left
print('\n[6] Snapping Notepad to left side...')
success, msg = controller.snap('left', 'notepad')
print(f'    {msg}')
time.sleep(1)

# Demo 7: Switch to VS Code
print('\n[7] Switching to VS Code...')
success, msg = controller.switch_to('vs code')
print(f'    {msg}')
time.sleep(1)

# Demo 8: Close demo apps
print('\n[8] Closing demo apps...')
success, msg = controller.close('calculator')
print(f'    {msg}')
success, msg = controller.close('notepad')
print(f'    {msg}')

print('\n' + '=' * 60)
print('Demo complete! App control is working.')
print('=' * 60)
print('\nVoice commands you can use:')
print('  "open chrome" / "launch notepad"')
print('  "close calculator"')
print('  "switch to vs code"')
print('  "minimize" / "maximize"')
print('  "snap left" / "snap right" / "snap top right"')
print('  "show desktop"')
print('  "list windows" / "what windows are open"')
