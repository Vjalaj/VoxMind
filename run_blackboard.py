"""
VoxMind Math Blackboard Launcher
================================
Quick launcher for the Mathematics Blackboard UI.

Usage:
    python run_blackboard.py
    python run_blackboard.py --port 5050
    python run_blackboard.py --debug
"""

import sys
import os

# Add project root to path
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Launch VoxMind Math Blackboard')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5050, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--open', action='store_true', help='Open browser automatically')
    args = parser.parse_args()
    
    # Import and run
    from interface.blackboard.blackboard_server import run_server
    
    if args.open:
        import webbrowser
        import threading
        def open_browser():
            import time
            time.sleep(1.5)  # Wait for server to start
            webbrowser.open(f'http://{args.host}:{args.port}')
        threading.Thread(target=open_browser, daemon=True).start()
    
    run_server(args.host, args.port, args.debug)


if __name__ == '__main__':
    main()
