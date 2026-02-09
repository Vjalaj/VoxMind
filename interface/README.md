# VoxMind Interactive Web Interface

A sophisticated ChatGPT-like interface for physics, mathematics, and coding assistance.

## Features

### 🌐 Real-time Streaming
- Word-by-word response streaming like ChatGPT/Gemini
- WebSocket-based for instant updates
- Typing indicators during generation

### 🧮 LaTeX Math Rendering
- Beautiful equation rendering with KaTeX
- Supports inline ($...$) and display ($$...$$) math
- All physics/math symbols supported

### 📊 Interactive Graphs
- Powered by Plotly.js
- Zoomable, pannable, hoverable
- Auto-generated for function plots

### 💻 Code Highlighting
- Syntax highlighting with Prism.js
- Python, JavaScript, and more
- Algorithm demonstrations

### 🎤 Voice Input
- Web Speech API integration
- Real-time transcription display
- Speak naturally to VoxMind

## Quick Start

```bash
# Install dependencies
pip install flask flask-socketio flask-cors

# Run the interface
python run_interface.py

# Or with custom options
python run_interface.py --port 8080
python run_interface.py --host 0.0.0.0  # Allow network access
```

## Physics Topics

The interface can explain and visualize:

- **Quantum Mechanics**: Schrödinger equation, wave functions, infinite well
- **Classical Mechanics**: Lagrangian, Hamiltonian, phase portraits
- **Electromagnetism**: Maxwell's equations, EM wave propagation
- **Relativity**: Lorentz transformations, Einstein field equations
- **Calculus**: Derivatives, integrals, area visualization
- **Linear Algebra**: Matrices, eigenvalues, Pauli matrices

## Example Queries

- "Plot sin(x) and cos(x)"
- "Explain the Schrödinger equation"
- "Show me Maxwell's equations"
- "What is a Lagrangian?"
- "Demonstrate sorting algorithms"
- "Explain eigenvalues"

## Architecture

```
interface/
├── __init__.py           # Module exports
├── server.py             # Flask + WebSocket server
├── conversation_engine.py # Response generation
└── templates/
    └── index.html        # Main UI (KaTeX, Plotly, Prism)
```

## API Endpoints

### HTTP
- `GET /` - Main interface
- `POST /api/message` - Send message (non-streaming)
- `GET /api/history/<session_id>` - Get conversation history

### WebSocket Events
- `connect` - Client connected
- `message` - Send message (streaming)
- `stream_start` - Response starting
- `stream_chunk` - Response chunk
- `stream_end` - Response complete with graph data

## Integration with VoxMind

The interface integrates with the main VoxMind voice assistant:

```python
# In main.py, say "open interface" to launch
# The web UI opens automatically in your browser
```

Voice commands:
- "open interface" / "launch interface"
- "show dashboard" / "web mode"

## Customization

### Adding Physics Topics

Edit `conversation_engine.py` and add a handler:

```python
@staticmethod
def _handle_my_topic(query: str) -> dict:
    return {
        'type': 'math',
        'content': """
## My Physics Topic

The equation is:

$$E = mc^2$$

**Explanation**: ...
        """,
        'has_math': True,
        'has_graph': True,
        'graph_data': {...}
    }
```

### Styling

Customize CSS variables in `templates/index.html`:

```css
:root {
    --accent-primary: #6366f1;    /* Primary purple */
    --bg-primary: #0a0a0f;        /* Dark background */
    --text-primary: #f8fafc;      /* Light text */
}
```

## Dependencies

- Flask >= 3.0.0
- Flask-SocketIO >= 5.3.0
- Flask-CORS >= 4.0.0
- NumPy >= 1.24.0 (for graph data)

## Browser Requirements

Modern browser with support for:
- WebSocket
- Web Speech API (for voice input)
- ES6 JavaScript
