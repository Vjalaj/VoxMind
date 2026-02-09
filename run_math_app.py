"""
VoxMind Math Blackboard App Launcher
====================================
Launch the native desktop math solver.

Usage:
    python run_math_app.py
"""

import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

def main():
    # Check dependencies
    try:
        import matplotlib
    except ImportError:
        print("Installing matplotlib...")
        os.system(f"{sys.executable} -m pip install matplotlib")
    
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:
            print("Installing PyQt6...")
            os.system(f"{sys.executable} -m pip install PyQt6")
    
    # Run the app
    from core.math_blackboard_app import run_app
    run_app()


if __name__ == '__main__':
    main()
