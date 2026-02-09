"""
VoxMind Daemon Launcher
=======================
Start VoxMind as an always-on background service.

Usage:
    python run_daemon.py          # Start daemon interactively
    python run_daemon.py --tray   # Start minimized to system tray
    python run_daemon.py --help   # Show all options
    
Features when running:
    - Win+Shift+V : Activate voice listening
    - Win+Shift+M : Toggle mute
    - Say "Hey Vox" or "Vox" to activate
    - System tray icon for quick access
    - IPC pipe for external app integration
"""

import sys
import os

# Add project root to path
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def check_dependencies():
    """Check if required dependencies are installed."""
    missing = []
    
    # Core dependencies
    deps = [
        ('pystray', 'System tray'),
        ('PIL', 'Icon creation (Pillow)'),
        ('win32gui', 'Windows API (pywin32)'),
        ('win32clipboard', 'Clipboard monitoring (pywin32)'),
        ('psutil', 'Process management'),
    ]
    
    for module, name in deps:
        try:
            __import__(module)
        except ImportError:
            missing.append(f"  - {name}: pip install {module.replace('PIL', 'Pillow').replace('win32gui', 'pywin32').replace('win32clipboard', 'pywin32')}")
    
    if missing:
        print("Missing dependencies for full daemon functionality:")
        for m in missing:
            print(m)
        print("\nThe daemon will start with reduced functionality.")
        print("Install missing packages with: pip install pystray Pillow pywin32 psutil")
        print()
        return False
    return True


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='VoxMind Daemon - Always-on voice assistant',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Hotkeys (when running):
  Win+Shift+V    Activate voice listening
  Win+Shift+M    Toggle mute

Wake words:
  "Hey Vox", "Vox", "OK Vox", "Computer"

Examples:
  python run_daemon.py              Start daemon
  python run_daemon.py --no-voice   Start without voice (hotkey only)
  python run_daemon.py --no-tray    Start without system tray
        """
    )
    parser.add_argument('--no-voice', action='store_true',
                        help='Disable voice activation (hotkey only)')
    parser.add_argument('--no-tray', action='store_true',
                        help='Disable system tray icon')
    parser.add_argument('--no-hotkeys', action='store_true',
                        help='Disable global hotkeys')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    args = parser.parse_args()
    
    # Check dependencies
    check_dependencies()
    
    # Set logging level
    if args.verbose:
        import logging
        logging.getLogger('VoxMind').setLevel(logging.DEBUG)
    
    # Import and start daemon
    from core.voxmind_daemon import VoxMindDaemon
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    VoxMind Daemon                            ║
║                    Always-On Voice Assistant                 ║
╚══════════════════════════════════════════════════════════════╝
    
    Hotkeys:
      Win+Shift+V : Activate voice listening
      Win+Shift+M : Toggle mute
    
    Wake words:
      "Hey Vox", "Vox", "OK Vox", "Computer"
    
    Press Ctrl+C to stop
    """)
    
    daemon = VoxMindDaemon()
    
    # Apply options
    # (In a full implementation, we'd disable services based on args)
    
    try:
        daemon.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
        daemon.stop()


if __name__ == '__main__':
    main()
