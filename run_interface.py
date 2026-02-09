"""
VoxMind Web Interface Launcher
==============================
Quick-start script to launch the interactive web interface.

Usage:
    python run_interface.py [--host HOST] [--port PORT] [--debug]
    
Examples:
    python run_interface.py                      # Default: 127.0.0.1:5000
    python run_interface.py --port 8080          # Custom port
    python run_interface.py --host 0.0.0.0       # Allow external access
"""

import argparse
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(
        description='VoxMind Interactive Web Interface',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_interface.py                # Start on localhost:5000
  python run_interface.py --port 8080    # Use port 8080
  python run_interface.py --host 0.0.0.0 # Allow network access
        """
    )
    parser.add_argument(
        '--host', 
        default='127.0.0.1',
        help='Host address (default: 127.0.0.1)'
    )
    parser.add_argument(
        '--port', 
        type=int, 
        default=5000,
        help='Port number (default: 5000)'
    )
    parser.add_argument(
        '--debug', 
        action='store_true',
        help='Enable debug mode'
    )
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='Do not open browser automatically'
    )
    
    args = parser.parse_args()
    
    # Check dependencies
    try:
        import flask
        import flask_socketio
    except ImportError as e:
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║  ⚠️  Missing Dependencies                                     ║
╠══════════════════════════════════════════════════════════════╣
║  Please install required packages:                           ║
║                                                              ║
║    pip install flask flask-socketio flask-cors               ║
║                                                              ║
║  Or install all requirements:                                ║
║                                                              ║
║    pip install -r requirements.txt                           ║
╚══════════════════════════════════════════════════════════════╝
        """)
        sys.exit(1)
    
    # Open browser if not disabled
    if not args.no_browser:
        import webbrowser
        import threading
        url = f"http://{args.host}:{args.port}"
        if args.host == '0.0.0.0':
            url = f"http://127.0.0.1:{args.port}"
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    
    # Start server
    from interface.server import run_server
    run_server(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
