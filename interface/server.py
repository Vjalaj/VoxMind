"""
VoxMind Web Interface Server
============================
Real-time conversational interface with:
- WebSocket streaming (like ChatGPT)
- LaTeX math rendering
- Interactive Plotly graphs
- Code syntax highlighting
- Voice transcription display
"""

import os
import sys
import json
import time
import uuid
import threading
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS

from interface.conversation_engine import (
    Message, StreamingResponse, MathEngine, CodeEngine
)

# Initialize Flask app
app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')
app.config['SECRET_KEY'] = 'voxmind-secret-key'
CORS(app)

# Initialize SocketIO for real-time streaming
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Conversation history
conversations = {}


def get_session_id():
    """Get or create session ID."""
    return str(uuid.uuid4())[:8]


def process_message(message: str, session_id: str) -> dict:
    """Process user message and generate response."""
    
    # Initialize conversation if needed
    if session_id not in conversations:
        conversations[session_id] = []
    
    # Add user message
    user_msg = Message(
        id=str(uuid.uuid4()),
        role='user',
        content=message,
        timestamp=time.time()
    )
    conversations[session_id].append(user_msg)
    
    # Determine response type
    message_lower = message.lower()
    
    # Check for math/physics queries
    math_keywords = ['derivative', 'integral', 'equation', 'matrix', 'plot', 'graph',
                     'schrodinger', 'quantum', 'lagrangian', 'maxwell', 'relativity',
                     'hamiltonian', 'eigenvalue', 'fourier', 'laplace', 'wave']
    
    code_keywords = ['code', 'program', 'algorithm', 'implement', 'function',
                     'sort', 'search', 'fibonacci', 'linked list', 'tree',
                     'python', 'javascript', 'numerical', 'simulation']
    
    is_math = any(kw in message_lower for kw in math_keywords)
    is_code = any(kw in message_lower for kw in code_keywords)
    
    if is_math:
        result = MathEngine.parse_math_query(message)
    elif is_code:
        result = CodeEngine.generate_code_response(message)
    else:
        # General response
        result = {
            'type': 'general',
            'content': generate_general_response(message),
            'has_math': False,
            'has_code': False,
            'has_graph': False
        }
    
    # Create assistant message
    assistant_msg = Message(
        id=str(uuid.uuid4()),
        role='assistant',
        content=result['content'],
        timestamp=time.time(),
        has_math=result.get('has_math', False),
        has_code=result.get('has_code', False),
        has_graph=result.get('has_graph', False),
        graph_data=result.get('graph_data')
    )
    conversations[session_id].append(assistant_msg)
    
    return result


def generate_general_response(message: str) -> str:
    """Generate response for general queries."""
    message_lower = message.lower()
    
    if 'hello' in message_lower or 'hi' in message_lower:
        return """Hello! I'm **VoxMind**, your physics and mathematics assistant.

I can help you with:

🔢 **Mathematics**
- Calculus (derivatives, integrals)
- Linear Algebra (matrices, eigenvalues)
- Differential Equations
- Plot mathematical functions

⚛️ **Physics**
- Quantum Mechanics (Schrödinger equation)
- Classical Mechanics (Lagrangian/Hamiltonian)
- Electromagnetism (Maxwell's equations)
- Relativity (Special & General)

💻 **Coding**
- Data Structures & Algorithms
- Numerical Methods
- Physics Simulations

Try asking:
- "Plot sin(x)"
- "Explain the Schrödinger equation"
- "Show me sorting algorithms"
- "Derive the wave equation"
"""
    
    elif 'help' in message_lower:
        return """# VoxMind Help

## Mathematics Commands
- `plot <function>` - Graph functions (sin, cos, exp, etc.)
- `derivative` - Calculus differentiation
- `integral` - Integration concepts
- `matrix` - Linear algebra
- `solve equation` - Equation solving

## Physics Topics
- `quantum` / `schrodinger` - Quantum mechanics
- `lagrangian` / `hamiltonian` - Analytical mechanics
- `maxwell` - Electromagnetism
- `relativity` - Special/General relativity

## Coding Topics
- `algorithm` - Data structures & algorithms
- `numerical methods` - Newton-Raphson, RK4, etc.
- `physics simulation` - Oscillators, N-body, etc.

## Examples
- "Plot a gaussian distribution"
- "Explain Maxwell's equations"
- "Show me binary search"
- "Simulate a damped pendulum"
"""
    
    elif 'who' in message_lower and 'you' in message_lower:
        return """I'm **VoxMind** — a voice-first AI assistant specialized in physics, mathematics, and programming.

Built for enthusiasts who love the elegance of:
- ∫ Calculus and Analysis
- ⟨ψ|H|ψ⟩ Quantum Mechanics
- ∇×E = -∂B/∂t Maxwell's Equations
- O(n log n) Algorithms

I render LaTeX equations, create interactive graphs, and explain complex concepts clearly.

*"The universe is written in the language of mathematics." — Galileo*
"""
    
    else:
        return f"""I understand you said: *"{message}"*

I'm specialized in **physics**, **mathematics**, and **coding**. Try asking about:

- 📊 **Graph something**: "Plot sin(x)" or "Graph x squared"
- ⚛️ **Physics**: "Explain quantum mechanics" or "Maxwell's equations"
- 🧮 **Math**: "What is a derivative?" or "Explain eigenvalues"
- 💻 **Code**: "Show sorting algorithms" or "Fibonacci sequence"

What would you like to explore?
"""


# =============================================================================
# Routes
# =============================================================================

@app.route('/')
def index():
    """Serve the main interface."""
    return render_template('index.html')


@app.route('/api/message', methods=['POST'])
def handle_message():
    """Handle non-streaming message."""
    data = request.json
    message = data.get('message', '')
    session_id = data.get('session_id', get_session_id())
    
    result = process_message(message, session_id)
    
    return jsonify({
        'success': True,
        'session_id': session_id,
        'response': result
    })


@app.route('/api/history/<session_id>')
def get_history(session_id):
    """Get conversation history."""
    if session_id in conversations:
        return jsonify({
            'success': True,
            'messages': [
                {
                    'id': m.id,
                    'role': m.role,
                    'content': m.content,
                    'timestamp': m.timestamp,
                    'has_math': m.has_math,
                    'has_code': m.has_code,
                    'has_graph': m.has_graph,
                    'graph_data': m.graph_data
                }
                for m in conversations[session_id]
            ]
        })
    return jsonify({'success': True, 'messages': []})


# =============================================================================
# WebSocket Events (Real-time Streaming)
# =============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print(f"[WebSocket] Client connected: {request.sid}")
    emit('connected', {'status': 'Connected to VoxMind'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    print(f"[WebSocket] Client disconnected: {request.sid}")


@socketio.on('message')
def handle_stream_message(data):
    """Handle streaming message request."""
    message = data.get('message', '')
    session_id = data.get('session_id', get_session_id())
    
    print(f"[WebSocket] Received: {message[:50]}...")
    
    # Process message
    result = process_message(message, session_id)
    content = result['content']
    
    # Stream response character by character (like ChatGPT)
    emit('stream_start', {
        'session_id': session_id,
        'has_math': result.get('has_math', False),
        'has_code': result.get('has_code', False),
        'has_graph': result.get('has_graph', False)
    })
    
    # Stream in chunks
    streamer = StreamingResponse(content, delay=0.01)
    full_content = ""
    
    for chunk in streamer.stream():
        full_content += chunk
        emit('stream_chunk', {'chunk': chunk})
    
    # Send completion with graph data if any
    emit('stream_end', {
        'content': full_content,
        'graph_data': result.get('graph_data'),
        'has_math': result.get('has_math', False)
    })


@socketio.on('voice_transcript')
def handle_voice_transcript(data):
    """Handle real-time voice transcription."""
    transcript = data.get('transcript', '')
    is_final = data.get('is_final', False)
    
    emit('transcript_update', {
        'transcript': transcript,
        'is_final': is_final
    })
    
    # If final transcript, process as message
    if is_final and transcript.strip():
        handle_stream_message({'message': transcript})


# =============================================================================
# Main
# =============================================================================

def run_server(host='127.0.0.1', port=5000, debug=True):
    """Run the web server."""
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                     V O X M I N D                             ║
║              Interactive Math & Physics Interface             ║
╠══════════════════════════════════════════════════════════════╣
║  🌐 Open in browser: http://{host}:{port}                     ║
║  📊 Real-time LaTeX, Graphs, Code highlighting               ║
║  🎤 Voice input supported                                    ║
╚══════════════════════════════════════════════════════════════╝
    """)
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    run_server()
