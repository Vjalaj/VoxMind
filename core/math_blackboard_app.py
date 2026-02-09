"""
VoxMind Math Blackboard - Native Desktop App
=============================================
A beautiful blackboard-style native app for solving mathematics.
Uses matplotlib for LaTeX rendering - no browser needed!

Launch with: python run_math_app.py
"""

import sys
import os
from typing import Optional, List
from dataclasses import dataclass

# Add project root
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Check for PyQt6 or PySide6
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLineEdit, QPushButton, QLabel, QScrollArea, QFrame, QListWidget,
        QListWidgetItem, QSplitter, QGroupBox, QSizePolicy, QTextEdit
    )
    from PyQt6.QtCore import Qt, QSize, QTimer
    from PyQt6.QtGui import QFont, QColor, QPalette, QPixmap, QImage, QIcon
    QT_VERSION = "PyQt6"
except ImportError:
    try:
        from PySide6.QtWidgets import (
            QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
            QLineEdit, QPushButton, QLabel, QScrollArea, QFrame, QListWidget,
            QListWidgetItem, QSplitter, QGroupBox, QSizePolicy, QTextEdit
        )
        from PySide6.QtCore import Qt, QSize, QTimer
        from PySide6.QtGui import QFont, QColor, QPalette, QPixmap, QImage, QIcon
        QT_VERSION = "PySide6"
    except ImportError:
        print("ERROR: PyQt6 or PySide6 is required!")
        print("Install with: pip install PyQt6")
        sys.exit(1)

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import numpy as np
from io import BytesIO


# Style constants
BLACKBOARD_COLOR = "#1a331a"
CHALK_WHITE = "#f5f5f5"
CHALK_YELLOW = "#ffd54f"
CHALK_BLUE = "#4fc3f7"
CHALK_GREEN = "#81c784"
CHALK_PINK = "#f48fb1"
FRAME_COLOR = "#4a3f2f"


class LaTeXRenderer:
    """Renders LaTeX expressions to QPixmap using matplotlib."""
    
    def __init__(self):
        plt.rcParams['text.usetex'] = False  # Use mathtext, not full LaTeX
        plt.rcParams['mathtext.fontset'] = 'cm'  # Computer Modern font
    
    def render(self, latex: str, fontsize: int = 20, color: str = CHALK_WHITE, 
               bg_color: str = BLACKBOARD_COLOR) -> Optional[QPixmap]:
        """Render LaTeX string to QPixmap."""
        if not latex:
            return None
        
        try:
            # Create figure
            fig = Figure(figsize=(10, 2), dpi=100)
            fig.patch.set_facecolor(bg_color)
            
            # Add text
            ax = fig.add_axes([0, 0, 1, 1])
            ax.set_facecolor(bg_color)
            ax.axis('off')
            
            # Wrap in $ if not already
            if not latex.startswith('$'):
                latex = f'${latex}$'
            
            ax.text(0.5, 0.5, latex, fontsize=fontsize, color=color,
                   ha='center', va='center', transform=ax.transAxes)
            
            # Render to buffer
            buf = BytesIO()
            fig.savefig(buf, format='png', facecolor=bg_color, 
                       bbox_inches='tight', pad_inches=0.1)
            plt.close(fig)
            
            # Convert to QPixmap
            buf.seek(0)
            img_data = buf.read()
            
            qimg = QImage()
            qimg.loadFromData(img_data)
            return QPixmap.fromImage(qimg)
            
        except Exception as e:
            print(f"LaTeX render error: {e}")
            return None


class ResultCard(QFrame):
    """A card showing a math result."""
    
    def __init__(self, result, renderer: LaTeXRenderer, parent=None):
        super().__init__(parent)
        self.result = result
        self.renderer = renderer
        self.setup_ui()
    
    def setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 15px;
                padding: 15px;
                margin: 10px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Problem type header
        type_label = QLabel(f"📊 {self.result.problem_type}")
        type_label.setStyleSheet(f"""
            QLabel {{
                color: {CHALK_YELLOW};
                font-size: 16px;
                font-weight: bold;
                background: rgba(255, 213, 79, 0.1);
                padding: 8px 15px;
                border-radius: 15px;
            }}
        """)
        layout.addWidget(type_label)
        
        # Input expression
        input_group = QHBoxLayout()
        input_label = QLabel("Problem:")
        input_label.setStyleSheet(f"color: rgba(255,255,255,0.6); font-size: 12px;")
        input_group.addWidget(input_label)
        input_group.addStretch()
        layout.addLayout(input_group)
        
        if self.result.input_latex:
            input_pixmap = self.renderer.render(self.result.input_latex, fontsize=18)
            if input_pixmap:
                input_img = QLabel()
                input_img.setPixmap(input_pixmap)
                input_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(input_img)
        
        # Equals separator
        equals = QLabel("=")
        equals.setStyleSheet(f"color: {CHALK_BLUE}; font-size: 36px; font-weight: bold;")
        equals.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(equals)
        
        # Result expression
        result_label = QLabel("Solution:")
        result_label.setStyleSheet(f"color: rgba(255,255,255,0.6); font-size: 12px;")
        layout.addWidget(result_label)
        
        if self.result.result_latex:
            result_pixmap = self.renderer.render(self.result.result_latex, fontsize=22, 
                                                  color=CHALK_GREEN)
            if result_pixmap:
                result_img = QLabel()
                result_img.setPixmap(result_pixmap)
                result_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(result_img)
        else:
            result_text = QLabel(self.result.result_text)
            result_text.setStyleSheet(f"color: {CHALK_GREEN}; font-size: 20px;")
            result_text.setWordWrap(True)
            layout.addWidget(result_text)
        
        # Steps
        if self.result.steps:
            steps_label = QLabel("📝 Solution Steps")
            steps_label.setStyleSheet(f"color: {CHALK_BLUE}; font-size: 14px; margin-top: 10px;")
            layout.addWidget(steps_label)
            
            for i, step in enumerate(self.result.steps, 1):
                step_widget = QLabel(f"  {i}. {step}")
                step_widget.setStyleSheet(f"color: rgba(255,255,255,0.8); font-size: 13px;")
                step_widget.setWordWrap(True)
                layout.addWidget(step_widget)
        
        # Explanation
        if self.result.explanation:
            expl = QLabel(f"💡 {self.result.explanation}")
            expl.setStyleSheet(f"""
                color: rgba(255,255,255,0.9);
                font-size: 13px;
                background: rgba(255, 213, 79, 0.1);
                border-left: 4px solid {CHALK_YELLOW};
                padding: 10px;
                border-radius: 0 10px 10px 0;
                margin-top: 10px;
            """)
            expl.setWordWrap(True)
            layout.addWidget(expl)


class MathBlackboardApp(QMainWindow):
    """Main blackboard application window."""
    
    def __init__(self):
        super().__init__()
        self.renderer = LaTeXRenderer()
        self.history: List = []
        self.setup_ui()
        self.load_examples()
    
    def setup_ui(self):
        self.setWindowTitle("📐 VoxMind Mathematics Blackboard")
        self.setMinimumSize(1000, 700)
        
        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Apply blackboard styling
        main_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {BLACKBOARD_COLOR};
                font-family: 'Segoe UI', sans-serif;
            }}
            QLineEdit {{
                background-color: rgba(0, 0, 0, 0.3);
                border: 2px dashed rgba(255, 255, 255, 0.3);
                border-radius: 10px;
                color: white;
                font-size: 18px;
                padding: 12px 20px;
            }}
            QLineEdit:focus {{
                border-color: rgba(255, 255, 255, 0.6);
            }}
            QPushButton {{
                background-color: #4caf50;
                border: none;
                border-radius: 10px;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 12px 30px;
            }}
            QPushButton:hover {{
                background-color: #66bb6a;
            }}
            QPushButton:pressed {{
                background-color: #388e3c;
            }}
            QListWidget {{
                background-color: rgba(0, 0, 0, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                color: white;
                font-size: 13px;
                padding: 5px;
            }}
            QListWidget::item {{
                padding: 8px;
                border-radius: 5px;
            }}
            QListWidget::item:hover {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
            QListWidget::item:selected {{
                background-color: rgba(79, 195, 247, 0.3);
            }}
            QScrollBar:vertical {{
                background: rgba(0, 0, 0, 0.2);
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 0.2);
                border-radius: 5px;
            }}
        """)
        
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        header = QLabel("📐 VoxMind Mathematics")
        header.setStyleSheet(f"""
            color: white;
            font-size: 36px;
            font-weight: bold;
            font-family: 'Georgia', serif;
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        subtitle = QLabel("Solve any math problem with step-by-step solutions")
        subtitle.setStyleSheet("color: rgba(255,255,255,0.6); font-size: 14px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        # Input area
        input_layout = QHBoxLayout()
        input_layout.setSpacing(15)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter a math problem... (e.g., integral of cos squared x)")
        self.input_field.returnPressed.connect(self.solve)
        input_layout.addWidget(self.input_field)
        
        solve_btn = QPushButton("Solve ✨")
        solve_btn.clicked.connect(self.solve)
        solve_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        input_layout.addWidget(solve_btn)
        
        layout.addLayout(input_layout)
        
        # Voice hint
        voice_hint = QLabel("🎤 Or say: \"Hey Vox, what is the integral of cos squared x\"")
        voice_hint.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 12px;")
        voice_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(voice_hint)
        
        # Main content area with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Results area (scrollable)
        results_container = QWidget()
        results_layout = QVBoxLayout(results_container)
        results_layout.setContentsMargins(0, 0, 0, 0)
        
        self.results_area = QScrollArea()
        self.results_area.setWidgetResizable(True)
        self.results_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.results_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.results_area.setWidget(self.results_widget)
        
        results_layout.addWidget(self.results_area)
        splitter.addWidget(results_container)
        
        # Side panel with examples
        side_panel = QWidget()
        side_layout = QVBoxLayout(side_panel)
        side_layout.setSpacing(15)
        
        # Examples section
        examples_label = QLabel("📚 Examples")
        examples_label.setStyleSheet(f"color: {CHALK_YELLOW}; font-size: 18px; font-weight: bold;")
        side_layout.addWidget(examples_label)
        
        self.examples_list = QListWidget()
        self.examples_list.itemDoubleClicked.connect(self.use_example)
        side_layout.addWidget(self.examples_list)
        
        # History section
        history_label = QLabel("📜 Recent")
        history_label.setStyleSheet(f"color: {CHALK_YELLOW}; font-size: 18px; font-weight: bold;")
        side_layout.addWidget(history_label)
        
        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self.use_history)
        self.history_list.setMaximumHeight(150)
        side_layout.addWidget(self.history_list)
        
        side_panel.setMaximumWidth(300)
        splitter.addWidget(side_panel)
        
        splitter.setSizes([700, 300])
        layout.addWidget(splitter, 1)
        
        # Welcome message
        self.show_welcome()
    
    def load_examples(self):
        """Load example problems."""
        examples = [
            "integral of cos squared x",
            "derivative of x^3 + sin(x)",
            "limit of sin(x)/x as x -> 0",
            "solve x^2 - 5x + 6 = 0",
            "expand (x + 2)^3",
            "factor x^2 - 9",
            "10 choose 5",
            "taylor series of e^x around x = 0",
            "determinant of [[1,2],[3,4]]",
            "simplify sin^2(x) + cos^2(x)",
        ]
        
        for ex in examples:
            item = QListWidgetItem(ex)
            self.examples_list.addItem(item)
    
    def show_welcome(self):
        """Show welcome message."""
        welcome = QLabel("""
            <div style='text-align: center; padding: 50px;'>
                <p style='font-size: 48px;'>🧮</p>
                <p style='color: rgba(255,255,255,0.7); font-size: 18px;'>
                    Enter a math problem above or double-click an example
                </p>
                <p style='color: rgba(255,255,255,0.5); font-size: 14px; margin-top: 20px;'>
                    Supports: Calculus, Algebra, Statistics, Linear Algebra, Physics
                </p>
            </div>
        """)
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.results_layout.addWidget(welcome)
    
    def solve(self):
        """Solve the math problem."""
        query = self.input_field.text().strip()
        if not query:
            return
        
        # Clear previous results
        self.clear_results()
        
        try:
            from core.math_solver import solve_math
            result = solve_math(query)
            
            if result.success:
                # Show result card
                card = ResultCard(result, self.renderer)
                self.results_layout.addWidget(card)
                
                # Add to history
                self.add_to_history(query)
            else:
                self.show_error(result.error)
                
        except ImportError as e:
            self.show_error(f"Math solver not available: {e}")
        except Exception as e:
            self.show_error(f"Error: {e}")
    
    def clear_results(self):
        """Clear the results area."""
        while self.results_layout.count():
            child = self.results_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def show_error(self, message: str):
        """Show an error message."""
        error = QLabel(f"""
            <div style='text-align: center; padding: 30px;'>
                <p style='font-size: 36px;'>❌</p>
                <p style='color: #ef5350; font-size: 16px;'>{message}</p>
            </div>
        """)
        error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.results_layout.addWidget(error)
    
    def add_to_history(self, query: str):
        """Add to history."""
        # Remove if exists
        for i in range(self.history_list.count()):
            if self.history_list.item(i).text() == query:
                self.history_list.takeItem(i)
                break
        
        # Add at top
        self.history_list.insertItem(0, query)
        
        # Limit to 10
        while self.history_list.count() > 10:
            self.history_list.takeItem(self.history_list.count() - 1)
    
    def use_example(self, item: QListWidgetItem):
        """Use an example problem."""
        self.input_field.setText(item.text())
        self.solve()
    
    def use_history(self, item: QListWidgetItem):
        """Use a history item."""
        self.input_field.setText(item.text())
        self.solve()


def run_app():
    """Run the math blackboard app."""
    app = QApplication(sys.argv)
    
    # Set app icon if available
    icon_path = os.path.join(ROOT, 'cache', 'icons', 'math.png')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = MathBlackboardApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    run_app()
