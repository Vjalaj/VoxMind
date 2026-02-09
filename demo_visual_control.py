"""
VoxMind Visual Demo - Watch Vox control windows in real-time
Records screen changes while performing window operations
"""
import time
import threading
from datetime import datetime

print("=" * 60)
print("VoxMind Visual Window Control Demo")
print("=" * 60)
print("\nThis demo will:")
print("1. Start screen monitoring")
print("2. Launch Calculator and Notepad")
print("3. Snap windows to different positions")
print("4. Show you the screen changes detected")
print("\nWatch your screen!\n")

# Import modules
from core.app_control import get_app_controller
from core.screen_monitor import get_screen_monitor

controller = get_app_controller()
monitor = get_screen_monitor()

# Track changes
changes_detected = []

def on_change(frame):
    if frame.change_percent > 5:
        changes_detected.append({
            'time': datetime.now().strftime('%H:%M:%S'),
            'change': frame.change_percent,
            'app': frame.active_app
        })
        print(f"  📸 Screen change: {frame.change_percent:.1f}%")

monitor.on_change(on_change)

# Start monitoring
print("[1] Starting screen monitor...")
monitor.start()
time.sleep(1)

# Launch Calculator
print("\n[2] Launching Calculator...")
success, msg = controller.open('calculator', wait=True, timeout=3.0)
print(f"    {msg}")
time.sleep(0.5)

# Snap Calculator right
print("\n[3] Snapping Calculator to RIGHT...")
success, msg = controller.snap('right', 'calculator')
print(f"    {msg}")
time.sleep(1.5)

# Launch Notepad  
print("\n[4] Launching Notepad...")
success, msg = controller.open('notepad', wait=True, timeout=3.0)
print(f"    {msg}")
time.sleep(0.5)

# Snap Notepad left
print("\n[5] Snapping Notepad to LEFT...")
success, msg = controller.snap('left', 'notepad')
print(f"    {msg}")
time.sleep(1.5)

# Move Notepad to top-left corner
print("\n[6] Snapping Notepad to TOP-LEFT corner...")
success, msg = controller.snap('top_left', 'notepad')
print(f"    {msg}")
time.sleep(1.5)

# Move Calculator to bottom-right
print("\n[7] Snapping Calculator to BOTTOM-RIGHT corner...")
success, msg = controller.snap('bottom_right', 'calculator')
print(f"    {msg}")
time.sleep(1.5)

# Show desktop
print("\n[8] Showing desktop (Win+D)...")
success, msg = controller.show_desktop()
print(f"    {msg}")
time.sleep(2)

# Restore windows
print("\n[9] Pressing Win+D again to restore...")
success, msg = controller.show_desktop()
print(f"    {msg}")
time.sleep(1.5)

# Close demo apps
print("\n[10] Cleaning up - closing demo apps...")
controller.close('calculator')
controller.close('notepad')
time.sleep(1)

# Get summary
print("\n" + "=" * 60)
print("DEMO COMPLETE - Activity Summary")
print("=" * 60)

summary = monitor.get_activity_summary(30)
print(f"\n{summary}")

print(f"\nTotal screen changes detected: {len(changes_detected)}")
if changes_detected:
    print("\nChange log:")
    for change in changes_detected[-10:]:
        print(f"  [{change['time']}] {change['change']:.1f}% change" + 
              (f" - {change['app']}" if change['app'] else ""))

# Stop monitoring
monitor.stop()

print("\n" + "=" * 60)
print("Visual demo finished!")
print("=" * 60)
