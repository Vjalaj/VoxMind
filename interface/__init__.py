"""
VoxMind Interactive Interface Module
=====================================
Real-time conversational AI interface with:
- ChatGPT-like streaming responses
- LaTeX math rendering (KaTeX)
- Interactive graphs (Plotly)
- Code syntax highlighting (Prism.js)
- Voice input support (Web Speech API)
"""

from interface.conversation_engine import (
    Message,
    StreamingResponse,
    MathEngine,
    CodeEngine
)

from interface.server import (
    app,
    socketio,
    run_server
)

__all__ = [
    'Message',
    'StreamingResponse', 
    'MathEngine',
    'CodeEngine',
    'app',
    'socketio',
    'run_server'
]

__version__ = '1.0.0'
