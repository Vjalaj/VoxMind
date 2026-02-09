"""
VoxMind Interactive Interface
=============================
A sophisticated web interface with:
- Real-time streaming responses (like Gemini/ChatGPT)
- LaTeX math rendering (KaTeX)
- Interactive graphs (Plotly)
- Code syntax highlighting
- Voice transcription display

For physics, mathematics, and coding enthusiasts.
"""

import json
import time
import re
from dataclasses import dataclass, asdict
from typing import Optional, Generator, Dict, Any, List, Callable
from datetime import datetime
import math

# For math/physics computations
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None


@dataclass
class Message:
    """Chat message structure."""
    id: str
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: float
    is_streaming: bool = False
    has_math: bool = False
    has_code: bool = False
    has_graph: bool = False
    graph_data: Optional[Dict] = None


class StreamingResponse:
    """Handles streaming text generation like ChatGPT."""
    
    def __init__(self, text: str, delay: float = 0.02):
        self.text = text
        self.delay = delay
        self._chunks = self._prepare_chunks()
    
    def _prepare_chunks(self) -> List[str]:
        """Split text into natural chunks for streaming."""
        # Split by words but keep punctuation attached
        words = self.text.split(' ')
        chunks = []
        for i, word in enumerate(words):
            if i < len(words) - 1:
                chunks.append(word + ' ')
            else:
                chunks.append(word)
        return chunks
    
    def stream(self) -> Generator[str, None, None]:
        """Yield text chunks with delay."""
        for chunk in self._chunks:
            yield chunk
            time.sleep(self.delay)


class MathEngine:
    """
    Mathematical computation engine for physics and math.
    Supports LaTeX generation and interactive graphs.
    """
    
    @staticmethod
    def parse_math_query(query: str) -> Dict[str, Any]:
        """Parse a math/physics query and generate response."""
        query_lower = query.lower()
        
        # Detect query type
        if any(w in query_lower for w in ['plot', 'graph', 'draw', 'visualize']):
            return MathEngine._handle_plot_query(query)
        elif any(w in query_lower for w in ['derivative', 'differentiate', 'd/dx']):
            return MathEngine._handle_derivative(query)
        elif any(w in query_lower for w in ['integral', 'integrate', '∫']):
            return MathEngine._handle_integral(query)
        elif any(w in query_lower for w in ['solve', 'equation', 'find x']):
            return MathEngine._handle_equation(query)
        elif any(w in query_lower for w in ['matrix', 'determinant', 'eigenvalue']):
            return MathEngine._handle_matrix(query)
        elif any(w in query_lower for w in ['schrodinger', 'wave function', 'quantum']):
            return MathEngine._handle_quantum(query)
        elif any(w in query_lower for w in ['lagrangian', 'hamiltonian', 'mechanics']):
            return MathEngine._handle_classical_mechanics(query)
        elif any(w in query_lower for w in ['maxwell', 'electric', 'magnetic', 'field']):
            return MathEngine._handle_electromagnetism(query)
        elif any(w in query_lower for w in ['relativity', 'lorentz', 'spacetime']):
            return MathEngine._handle_relativity(query)
        else:
            return MathEngine._handle_general_math(query)
    
    @staticmethod
    def _handle_plot_query(query: str) -> Dict[str, Any]:
        """Handle plot/graph requests."""
        # Extract function to plot
        # Common patterns: "plot sin(x)", "graph x^2", "draw e^x"
        
        # Default: sine wave
        x = np.linspace(-2*np.pi, 2*np.pi, 500).tolist()
        
        if 'sin' in query.lower():
            y = np.sin(np.array(x)).tolist()
            title = "Sine Function: f(x) = sin(x)"
            latex = r"f(x) = \sin(x)"
        elif 'cos' in query.lower():
            y = np.cos(np.array(x)).tolist()
            title = "Cosine Function: f(x) = cos(x)"
            latex = r"f(x) = \cos(x)"
        elif 'tan' in query.lower():
            y = np.tan(np.array(x)).tolist()
            y = [min(max(yi, -10), 10) for yi in y]  # Clip
            title = "Tangent Function: f(x) = tan(x)"
            latex = r"f(x) = \tan(x)"
        elif 'x^2' in query or 'x squared' in query.lower():
            x = np.linspace(-5, 5, 500).tolist()
            y = (np.array(x)**2).tolist()
            title = "Quadratic: f(x) = x²"
            latex = r"f(x) = x^2"
        elif 'x^3' in query or 'cubic' in query.lower():
            x = np.linspace(-3, 3, 500).tolist()
            y = (np.array(x)**3).tolist()
            title = "Cubic: f(x) = x³"
            latex = r"f(x) = x^3"
        elif 'exp' in query.lower() or 'e^x' in query:
            x = np.linspace(-2, 3, 500).tolist()
            y = np.exp(np.array(x)).tolist()
            title = "Exponential: f(x) = eˣ"
            latex = r"f(x) = e^x"
        elif 'log' in query.lower() or 'ln' in query.lower():
            x = np.linspace(0.1, 5, 500).tolist()
            y = np.log(np.array(x)).tolist()
            title = "Natural Logarithm: f(x) = ln(x)"
            latex = r"f(x) = \ln(x)"
        elif 'gaussian' in query.lower() or 'normal' in query.lower():
            x = np.linspace(-4, 4, 500).tolist()
            y = (np.exp(-np.array(x)**2/2) / np.sqrt(2*np.pi)).tolist()
            title = "Gaussian Distribution"
            latex = r"f(x) = \frac{1}{\sqrt{2\pi}} e^{-x^2/2}"
        elif 'wave' in query.lower():
            x = np.linspace(0, 4*np.pi, 500).tolist()
            y = (np.sin(np.array(x)) * np.exp(-np.array(x)/10)).tolist()
            title = "Damped Wave"
            latex = r"f(x) = \sin(x) \cdot e^{-x/10}"
        else:
            # Default sine
            y = np.sin(np.array(x)).tolist()
            title = "Sine Function"
            latex = r"f(x) = \sin(x)"
        
        return {
            'type': 'graph',
            'content': f"Here's the graph of ${latex}$:",
            'has_math': True,
            'has_graph': True,
            'graph_data': {
                'x': x,
                'y': y,
                'title': title,
                'xaxis': 'x',
                'yaxis': 'f(x)',
                'type': 'line'
            }
        }
    
    @staticmethod
    def _handle_derivative(query: str) -> Dict[str, Any]:
        """Handle derivative questions."""
        content = """Let me explain differentiation:

**The Derivative** measures instantaneous rate of change:

$$\\frac{df}{dx} = \\lim_{h \\to 0} \\frac{f(x+h) - f(x)}{h}$$

**Common Derivatives:**

| Function | Derivative |
|----------|------------|
| $x^n$ | $nx^{n-1}$ |
| $e^x$ | $e^x$ |
| $\\ln(x)$ | $\\frac{1}{x}$ |
| $\\sin(x)$ | $\\cos(x)$ |
| $\\cos(x)$ | $-\\sin(x)$ |

**Chain Rule:** $\\frac{d}{dx}[f(g(x))] = f'(g(x)) \\cdot g'(x)$

**Product Rule:** $\\frac{d}{dx}[f \\cdot g] = f'g + fg'$

**Quotient Rule:** $\\frac{d}{dx}\\left[\\frac{f}{g}\\right] = \\frac{f'g - fg'}{g^2}$
"""
        return {
            'type': 'math',
            'content': content,
            'has_math': True,
            'has_graph': False
        }
    
    @staticmethod
    def _handle_integral(query: str) -> Dict[str, Any]:
        """Handle integral questions."""
        content = """Let me explain integration:

**The Definite Integral** represents area under a curve:

$$\\int_a^b f(x) \\, dx = F(b) - F(a)$$

where $F(x)$ is the antiderivative of $f(x)$.

**Fundamental Theorem of Calculus:**

$$\\frac{d}{dx} \\int_a^x f(t) \\, dt = f(x)$$

**Common Integrals:**

| Function | Integral |
|----------|----------|
| $x^n$ | $\\frac{x^{n+1}}{n+1} + C$ |
| $e^x$ | $e^x + C$ |
| $\\frac{1}{x}$ | $\\ln|x| + C$ |
| $\\sin(x)$ | $-\\cos(x) + C$ |
| $\\cos(x)$ | $\\sin(x) + C$ |

**Gaussian Integral:** $\\int_{-\\infty}^{\\infty} e^{-x^2} dx = \\sqrt{\\pi}$
"""
        
        # Add a graph of area under curve
        x = np.linspace(0, np.pi, 500).tolist()
        y = np.sin(np.array(x)).tolist()
        
        return {
            'type': 'math',
            'content': content,
            'has_math': True,
            'has_graph': True,
            'graph_data': {
                'x': x,
                'y': y,
                'title': 'Area under sin(x) from 0 to π = 2',
                'xaxis': 'x',
                'yaxis': 'sin(x)',
                'type': 'area',
                'fill': True
            }
        }
    
    @staticmethod
    def _handle_quantum(query: str) -> Dict[str, Any]:
        """Handle quantum mechanics questions."""
        content = """# Quantum Mechanics Foundations

**Schrödinger Equation** (time-dependent):

$$i\\hbar \\frac{\\partial}{\\partial t} \\Psi(\\mathbf{r}, t) = \\hat{H} \\Psi(\\mathbf{r}, t)$$

**Time-Independent Schrödinger Equation:**

$$\\hat{H} \\psi = E \\psi$$

where the Hamiltonian is:

$$\\hat{H} = -\\frac{\\hbar^2}{2m} \\nabla^2 + V(\\mathbf{r})$$

**Key Principles:**

1. **Wave-Particle Duality:** $\\lambda = \\frac{h}{p}$ (de Broglie)

2. **Uncertainty Principle:** $\\Delta x \\cdot \\Delta p \\geq \\frac{\\hbar}{2}$

3. **Normalization:** $\\int_{-\\infty}^{\\infty} |\\Psi|^2 dx = 1$

**Infinite Square Well:**
$$E_n = \\frac{n^2 \\pi^2 \\hbar^2}{2mL^2}, \\quad \\psi_n = \\sqrt{\\frac{2}{L}} \\sin\\left(\\frac{n\\pi x}{L}\\right)$$

**Harmonic Oscillator:**
$$E_n = \\hbar\\omega\\left(n + \\frac{1}{2}\\right)$$
"""
        
        # Wave function visualization
        x = np.linspace(0, 1, 500).tolist()
        psi1 = (np.sqrt(2) * np.sin(np.pi * np.array(x))).tolist()
        psi2 = (np.sqrt(2) * np.sin(2 * np.pi * np.array(x))).tolist()
        psi3 = (np.sqrt(2) * np.sin(3 * np.pi * np.array(x))).tolist()
        
        return {
            'type': 'physics',
            'content': content,
            'has_math': True,
            'has_graph': True,
            'graph_data': {
                'type': 'multi',
                'traces': [
                    {'x': x, 'y': psi1, 'name': 'ψ₁ (n=1)'},
                    {'x': x, 'y': psi2, 'name': 'ψ₂ (n=2)'},
                    {'x': x, 'y': psi3, 'name': 'ψ₃ (n=3)'},
                ],
                'title': 'Infinite Square Well Wave Functions',
                'xaxis': 'x/L',
                'yaxis': 'ψ(x)'
            }
        }
    
    @staticmethod
    def _handle_classical_mechanics(query: str) -> Dict[str, Any]:
        """Handle classical mechanics (Lagrangian/Hamiltonian)."""
        content = """# Analytical Mechanics

## Lagrangian Mechanics

**Lagrangian:** $L = T - V$ (Kinetic - Potential)

**Euler-Lagrange Equation:**
$$\\frac{d}{dt}\\left(\\frac{\\partial L}{\\partial \\dot{q}_i}\\right) - \\frac{\\partial L}{\\partial q_i} = 0$$

**Example - Simple Pendulum:**
$$L = \\frac{1}{2}ml^2\\dot{\\theta}^2 + mgl\\cos\\theta$$

Equation of motion: $\\ddot{\\theta} + \\frac{g}{l}\\sin\\theta = 0$

## Hamiltonian Mechanics

**Canonical Momentum:** $p_i = \\frac{\\partial L}{\\partial \\dot{q}_i}$

**Hamiltonian:** $H = \\sum_i p_i \\dot{q}_i - L = T + V$

**Hamilton's Equations:**
$$\\dot{q}_i = \\frac{\\partial H}{\\partial p_i}, \\quad \\dot{p}_i = -\\frac{\\partial H}{\\partial q_i}$$

**Poisson Bracket:**
$$\\{f, g\\} = \\sum_i \\left(\\frac{\\partial f}{\\partial q_i}\\frac{\\partial g}{\\partial p_i} - \\frac{\\partial f}{\\partial p_i}\\frac{\\partial g}{\\partial q_i}\\right)$$

**Liouville's Theorem:** Phase space volume is conserved.
"""
        
        # Pendulum phase portrait
        theta = np.linspace(-np.pi, np.pi, 100)
        omega_vals = []
        for E in [0.5, 1.0, 1.5, 1.99]:  # Different energy levels
            omega = np.sqrt(2 * (E - (1 - np.cos(theta))))
            omega = np.where(np.isnan(omega), 0, omega)
            omega_vals.append(omega.tolist())
        
        return {
            'type': 'physics',
            'content': content,
            'has_math': True,
            'has_graph': True,
            'graph_data': {
                'type': 'multi',
                'traces': [
                    {'x': theta.tolist(), 'y': omega_vals[0], 'name': 'E=0.5'},
                    {'x': theta.tolist(), 'y': omega_vals[1], 'name': 'E=1.0'},
                    {'x': theta.tolist(), 'y': omega_vals[2], 'name': 'E=1.5'},
                ],
                'title': 'Pendulum Phase Portrait',
                'xaxis': 'θ',
                'yaxis': 'ω'
            }
        }
    
    @staticmethod
    def _handle_electromagnetism(query: str) -> Dict[str, Any]:
        """Handle electromagnetism questions."""
        content = """# Maxwell's Equations

**Differential Form:**

| Equation | Formula |
|----------|---------|
| Gauss's Law | $\\nabla \\cdot \\mathbf{E} = \\frac{\\rho}{\\epsilon_0}$ |
| Gauss's Law (B) | $\\nabla \\cdot \\mathbf{B} = 0$ |
| Faraday's Law | $\\nabla \\times \\mathbf{E} = -\\frac{\\partial \\mathbf{B}}{\\partial t}$ |
| Ampère-Maxwell | $\\nabla \\times \\mathbf{B} = \\mu_0\\mathbf{J} + \\mu_0\\epsilon_0\\frac{\\partial \\mathbf{E}}{\\partial t}$ |

**Wave Equation:**
$$\\nabla^2 \\mathbf{E} = \\mu_0\\epsilon_0 \\frac{\\partial^2 \\mathbf{E}}{\\partial t^2}$$

Speed of light: $c = \\frac{1}{\\sqrt{\\mu_0\\epsilon_0}}$

**Electromagnetic Wave:**
$$\\mathbf{E} = E_0 \\cos(kz - \\omega t) \\hat{x}$$
$$\\mathbf{B} = B_0 \\cos(kz - \\omega t) \\hat{y}$$

**Poynting Vector:** $\\mathbf{S} = \\frac{1}{\\mu_0} \\mathbf{E} \\times \\mathbf{B}$
"""
        
        # EM wave visualization
        z = np.linspace(0, 4*np.pi, 500).tolist()
        E = np.sin(np.array(z)).tolist()
        B = np.sin(np.array(z)).tolist()
        
        return {
            'type': 'physics',
            'content': content,
            'has_math': True,
            'has_graph': True,
            'graph_data': {
                'type': 'multi',
                'traces': [
                    {'x': z, 'y': E, 'name': 'E (electric)'},
                    {'x': z, 'y': B, 'name': 'B (magnetic)'},
                ],
                'title': 'Electromagnetic Wave',
                'xaxis': 'z (propagation)',
                'yaxis': 'Field amplitude'
            }
        }
    
    @staticmethod
    def _handle_relativity(query: str) -> Dict[str, Any]:
        """Handle relativity questions."""
        content = """# Special & General Relativity

## Special Relativity

**Lorentz Factor:**
$$\\gamma = \\frac{1}{\\sqrt{1 - v^2/c^2}}$$

**Time Dilation:** $\\Delta t' = \\gamma \\Delta t$

**Length Contraction:** $L' = L/\\gamma$

**Energy-Momentum:**
$$E^2 = (pc)^2 + (mc^2)^2$$
$$E = \\gamma mc^2$$

**Lorentz Transformation:**
$$x' = \\gamma(x - vt), \\quad t' = \\gamma\\left(t - \\frac{vx}{c^2}\\right)$$

## General Relativity

**Einstein Field Equations:**
$$G_{\\mu\\nu} + \\Lambda g_{\\mu\\nu} = \\frac{8\\pi G}{c^4} T_{\\mu\\nu}$$

where $G_{\\mu\\nu} = R_{\\mu\\nu} - \\frac{1}{2}Rg_{\\mu\\nu}$ is the Einstein tensor.

**Schwarzschild Metric:**
$$ds^2 = -\\left(1-\\frac{r_s}{r}\\right)c^2dt^2 + \\left(1-\\frac{r_s}{r}\\right)^{-1}dr^2 + r^2d\\Omega^2$$

where $r_s = \\frac{2GM}{c^2}$ is the Schwarzschild radius.
"""
        
        # Lorentz factor visualization
        v = np.linspace(0, 0.99, 500)
        gamma = 1 / np.sqrt(1 - v**2)
        
        return {
            'type': 'physics',
            'content': content,
            'has_math': True,
            'has_graph': True,
            'graph_data': {
                'x': v.tolist(),
                'y': gamma.tolist(),
                'title': 'Lorentz Factor γ vs velocity (v/c)',
                'xaxis': 'v/c',
                'yaxis': 'γ',
                'type': 'line'
            }
        }
    
    @staticmethod
    def _handle_matrix(query: str) -> Dict[str, Any]:
        """Handle matrix/linear algebra questions."""
        content = """# Linear Algebra

**Matrix Operations:**

$$A = \\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix}$$

**Determinant:** $\\det(A) = ad - bc$

**Inverse:** $A^{-1} = \\frac{1}{\\det(A)} \\begin{pmatrix} d & -b \\\\ -c & a \\end{pmatrix}$

**Eigenvalue Problem:** $A\\mathbf{v} = \\lambda\\mathbf{v}$

Characteristic equation: $\\det(A - \\lambda I) = 0$

**Diagonalization:** $A = PDP^{-1}$

where $D$ is diagonal with eigenvalues, $P$ has eigenvectors as columns.

**Pauli Matrices (Quantum Mechanics):**

$$\\sigma_x = \\begin{pmatrix} 0 & 1 \\\\ 1 & 0 \\end{pmatrix}, \\quad
\\sigma_y = \\begin{pmatrix} 0 & -i \\\\ i & 0 \\end{pmatrix}, \\quad
\\sigma_z = \\begin{pmatrix} 1 & 0 \\\\ 0 & -1 \\end{pmatrix}$$

**Properties:** $\\sigma_i^2 = I$, $[\\sigma_i, \\sigma_j] = 2i\\epsilon_{ijk}\\sigma_k$
"""
        return {
            'type': 'math',
            'content': content,
            'has_math': True,
            'has_graph': False
        }
    
    @staticmethod
    def _handle_equation(query: str) -> Dict[str, Any]:
        """Handle equation solving."""
        content = """# Equation Solving

**Quadratic Formula:**
For $ax^2 + bx + c = 0$:
$$x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$$

**Cubic Formula (Cardano's):**
For $x^3 + px + q = 0$:
$$x = \\sqrt[3]{-\\frac{q}{2} + \\sqrt{\\frac{q^2}{4} + \\frac{p^3}{27}}} + \\sqrt[3]{-\\frac{q}{2} - \\sqrt{\\frac{q^2}{4} + \\frac{p^3}{27}}}$$

**Newton-Raphson Method:**
$$x_{n+1} = x_n - \\frac{f(x_n)}{f'(x_n)}$$

**Systems of Linear Equations:**
$$A\\mathbf{x} = \\mathbf{b} \\implies \\mathbf{x} = A^{-1}\\mathbf{b}$$

Or use Gaussian elimination/LU decomposition.
"""
        return {
            'type': 'math',
            'content': content,
            'has_math': True,
            'has_graph': False
        }
    
    @staticmethod
    def _handle_general_math(query: str) -> Dict[str, Any]:
        """Handle general math queries."""
        content = """# Mathematical Foundations

**Euler's Identity:**
$$e^{i\\pi} + 1 = 0$$

**Taylor Series:**
$$f(x) = \\sum_{n=0}^{\\infty} \\frac{f^{(n)}(a)}{n!}(x-a)^n$$

**Fourier Transform:**
$$\\hat{f}(\\omega) = \\int_{-\\infty}^{\\infty} f(t) e^{-i\\omega t} dt$$

**Gamma Function:**
$$\\Gamma(n) = (n-1)! = \\int_0^{\\infty} t^{n-1} e^{-t} dt$$

**Riemann Zeta Function:**
$$\\zeta(s) = \\sum_{n=1}^{\\infty} \\frac{1}{n^s}$$

Ask me about specific topics like:
- Calculus (derivatives, integrals)
- Linear Algebra (matrices, eigenvalues)
- Quantum Mechanics (Schrödinger equation)
- Classical Mechanics (Lagrangian, Hamiltonian)
- Electromagnetism (Maxwell's equations)
- Relativity (Lorentz transformations)
"""
        return {
            'type': 'math',
            'content': content,
            'has_math': True,
            'has_graph': False
        }


class CodeEngine:
    """Handles code-related queries with syntax highlighting."""
    
    LANGUAGES = {
        'python': 'python',
        'javascript': 'javascript',
        'typescript': 'typescript',
        'cpp': 'cpp',
        'c++': 'cpp',
        'java': 'java',
        'rust': 'rust',
        'go': 'go',
    }
    
    @staticmethod
    def detect_code_query(query: str) -> bool:
        """Check if query is code-related."""
        keywords = ['code', 'program', 'function', 'algorithm', 'implement', 
                   'write', 'python', 'javascript', 'sort', 'search', 'class']
        return any(kw in query.lower() for kw in keywords)
    
    @staticmethod
    def generate_code_response(query: str) -> Dict[str, Any]:
        """Generate code examples."""
        query_lower = query.lower()
        
        if 'sort' in query_lower:
            return CodeEngine._sorting_algorithms()
        elif 'fibonacci' in query_lower:
            return CodeEngine._fibonacci()
        elif 'binary search' in query_lower:
            return CodeEngine._binary_search()
        elif 'linked list' in query_lower:
            return CodeEngine._linked_list()
        elif 'tree' in query_lower:
            return CodeEngine._binary_tree()
        elif 'graph' in query_lower and 'algorithm' in query_lower:
            return CodeEngine._graph_algorithms()
        elif 'numerical' in query_lower or 'newton' in query_lower:
            return CodeEngine._numerical_methods()
        elif 'physics simulation' in query_lower or 'simulate' in query_lower:
            return CodeEngine._physics_simulation()
        else:
            return CodeEngine._general_code()
    
    @staticmethod
    def _sorting_algorithms() -> Dict[str, Any]:
        content = """# Sorting Algorithms

## Quick Sort - O(n log n) average

```python
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    
    return quicksort(left) + middle + quicksort(right)
```

## Merge Sort - O(n log n) guaranteed

```python
def mergesort(arr):
    if len(arr) <= 1:
        return arr
    
    mid = len(arr) // 2
    left = mergesort(arr[:mid])
    right = mergesort(arr[mid:])
    
    return merge(left, right)

def merge(left, right):
    result = []
    i = j = 0
    
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    
    result.extend(left[i:])
    result.extend(right[j:])
    return result
```

**Time Complexity Comparison:**

| Algorithm | Best | Average | Worst | Space |
|-----------|------|---------|-------|-------|
| Quick Sort | O(n log n) | O(n log n) | O(n²) | O(log n) |
| Merge Sort | O(n log n) | O(n log n) | O(n log n) | O(n) |
| Heap Sort | O(n log n) | O(n log n) | O(n log n) | O(1) |
"""
        return {
            'type': 'code',
            'content': content,
            'has_code': True,
            'has_math': True,
            'has_graph': False
        }
    
    @staticmethod
    def _numerical_methods() -> Dict[str, Any]:
        content = """# Numerical Methods in Python

## Newton-Raphson Method

Find roots of $f(x) = 0$ using: $x_{n+1} = x_n - \\frac{f(x_n)}{f'(x_n)}$

```python
import numpy as np

def newton_raphson(f, df, x0, tol=1e-10, max_iter=100):
    \"\"\"
    Find root using Newton-Raphson method.
    
    Args:
        f: Function to find root of
        df: Derivative of f
        x0: Initial guess
        tol: Tolerance for convergence
        max_iter: Maximum iterations
    
    Returns:
        Root approximation
    \"\"\"
    x = x0
    for i in range(max_iter):
        fx = f(x)
        if abs(fx) < tol:
            return x
        
        dfx = df(x)
        if dfx == 0:
            raise ValueError("Derivative is zero")
        
        x = x - fx / dfx
    
    raise ValueError("Did not converge")

# Example: Find sqrt(2) by solving x² - 2 = 0
f = lambda x: x**2 - 2
df = lambda x: 2*x
root = newton_raphson(f, df, x0=1.0)
print(f"√2 ≈ {root}")  # 1.4142135623730951
```

## Numerical Integration (Simpson's Rule)

```python
def simpsons_rule(f, a, b, n=100):
    \"\"\"
    Integrate f from a to b using Simpson's rule.
    
    ∫f(x)dx ≈ (h/3)[f(x₀) + 4f(x₁) + 2f(x₂) + ... + f(xₙ)]
    \"\"\"
    if n % 2:
        n += 1  # n must be even
    
    h = (b - a) / n
    x = np.linspace(a, b, n + 1)
    y = f(x)
    
    return h/3 * (y[0] + y[-1] + 4*sum(y[1:-1:2]) + 2*sum(y[2:-1:2]))

# Example: ∫sin(x)dx from 0 to π = 2
result = simpsons_rule(np.sin, 0, np.pi)
print(f"∫sin(x)dx = {result}")  # ≈ 2.0
```

## Runge-Kutta 4th Order (ODE Solver)

Solve $\\frac{dy}{dx} = f(x, y)$

```python
def rk4(f, x0, y0, x_end, h=0.01):
    \"\"\"
    Solve ODE using 4th order Runge-Kutta.
    \"\"\"
    x_vals = [x0]
    y_vals = [y0]
    
    x, y = x0, y0
    while x < x_end:
        k1 = h * f(x, y)
        k2 = h * f(x + h/2, y + k1/2)
        k3 = h * f(x + h/2, y + k2/2)
        k4 = h * f(x + h, y + k3)
        
        y = y + (k1 + 2*k2 + 2*k3 + k4) / 6
        x = x + h
        
        x_vals.append(x)
        y_vals.append(y)
    
    return np.array(x_vals), np.array(y_vals)

# Example: dy/dx = -y (solution: y = e^(-x))
f = lambda x, y: -y
x, y = rk4(f, 0, 1, 5)
```
"""
        # Add graph showing RK4 solution
        x = np.linspace(0, 5, 500).tolist()
        y_exact = np.exp(-np.array(x)).tolist()
        
        return {
            'type': 'code',
            'content': content,
            'has_code': True,
            'has_math': True,
            'has_graph': True,
            'graph_data': {
                'x': x,
                'y': y_exact,
                'title': "Solution of dy/dx = -y: y = e^(-x)",
                'xaxis': 'x',
                'yaxis': 'y',
                'type': 'line'
            }
        }
    
    @staticmethod
    def _physics_simulation() -> Dict[str, Any]:
        content = """# Physics Simulation in Python

## Simple Harmonic Oscillator

Equation of motion: $\\ddot{x} + \\omega^2 x = 0$

```python
import numpy as np
import matplotlib.pyplot as plt

class HarmonicOscillator:
    def __init__(self, m=1.0, k=1.0, x0=1.0, v0=0.0):
        self.m = m  # mass
        self.k = k  # spring constant
        self.omega = np.sqrt(k/m)
        self.x = x0
        self.v = v0
        self.t = 0
        
    def step(self, dt):
        \"\"\"Verlet integration.\"\"\"
        a = -self.omega**2 * self.x
        self.x += self.v * dt + 0.5 * a * dt**2
        a_new = -self.omega**2 * self.x
        self.v += 0.5 * (a + a_new) * dt
        self.t += dt
        
    def energy(self):
        T = 0.5 * self.m * self.v**2  # Kinetic
        V = 0.5 * self.k * self.x**2   # Potential
        return T + V

# Simulate
osc = HarmonicOscillator(m=1, k=4, x0=1, v0=0)
t_vals, x_vals, E_vals = [], [], []

for _ in range(1000):
    t_vals.append(osc.t)
    x_vals.append(osc.x)
    E_vals.append(osc.energy())
    osc.step(0.01)
```

## N-Body Gravitational Simulation

```python
class Body:
    G = 6.674e-11  # Gravitational constant
    
    def __init__(self, mass, pos, vel):
        self.mass = mass
        self.pos = np.array(pos, dtype=float)
        self.vel = np.array(vel, dtype=float)
        self.acc = np.zeros(3)
    
    def compute_acceleration(self, bodies):
        self.acc = np.zeros(3)
        for other in bodies:
            if other is self:
                continue
            r = other.pos - self.pos
            dist = np.linalg.norm(r)
            if dist > 0:
                self.acc += self.G * other.mass * r / dist**3
    
    def update(self, dt):
        self.vel += self.acc * dt
        self.pos += self.vel * dt

def simulate_nbody(bodies, dt, steps):
    trajectories = [[] for _ in bodies]
    
    for _ in range(steps):
        for body in bodies:
            body.compute_acceleration(bodies)
        for i, body in enumerate(bodies):
            body.update(dt)
            trajectories[i].append(body.pos.copy())
    
    return trajectories
```

## Pendulum with Damping

$\\ddot{\\theta} + \\gamma\\dot{\\theta} + \\omega_0^2 \\sin\\theta = 0$

```python
def damped_pendulum(t, state, gamma=0.1, omega0=1.0):
    theta, omega = state
    dtheta = omega
    domega = -gamma * omega - omega0**2 * np.sin(theta)
    return [dtheta, domega]

from scipy.integrate import solve_ivp

sol = solve_ivp(
    damped_pendulum,
    [0, 20],
    [np.pi/4, 0],  # Initial: 45°, no velocity
    dense_output=True
)
```
"""
        # Damped oscillator graph
        t = np.linspace(0, 10, 500)
        gamma = 0.3
        omega = 2.0
        x = np.exp(-gamma * t) * np.cos(omega * t)
        
        return {
            'type': 'code',
            'content': content,
            'has_code': True,
            'has_math': True,
            'has_graph': True,
            'graph_data': {
                'x': t.tolist(),
                'y': x.tolist(),
                'title': "Damped Harmonic Oscillator: x(t) = e^(-γt)cos(ωt)",
                'xaxis': 't',
                'yaxis': 'x(t)',
                'type': 'line'
            }
        }
    
    @staticmethod
    def _fibonacci() -> Dict[str, Any]:
        content = """# Fibonacci Sequence

The sequence: 0, 1, 1, 2, 3, 5, 8, 13, 21, ...

Defined by: $F_n = F_{n-1} + F_{n-2}$, with $F_0 = 0$, $F_1 = 1$

**Closed Form (Binet's Formula):**
$$F_n = \\frac{\\phi^n - \\psi^n}{\\sqrt{5}}$$

where $\\phi = \\frac{1+\\sqrt{5}}{2}$ (golden ratio) and $\\psi = \\frac{1-\\sqrt{5}}{2}$

## Implementations

```python
# 1. Recursive (slow - O(2^n))
def fib_recursive(n):
    if n <= 1:
        return n
    return fib_recursive(n-1) + fib_recursive(n-2)

# 2. Memoized - O(n)
from functools import lru_cache

@lru_cache(maxsize=None)
def fib_memo(n):
    if n <= 1:
        return n
    return fib_memo(n-1) + fib_memo(n-2)

# 3. Iterative - O(n) time, O(1) space
def fib_iter(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

# 4. Matrix exponentiation - O(log n)
import numpy as np

def fib_matrix(n):
    if n <= 1:
        return n
    
    def matrix_power(M, p):
        if p == 1:
            return M
        if p % 2 == 0:
            half = matrix_power(M, p // 2)
            return half @ half
        return M @ matrix_power(M, p - 1)
    
    M = np.array([[1, 1], [1, 0]], dtype=object)
    result = matrix_power(M, n)
    return result[0, 1]
```
"""
        return {
            'type': 'code',
            'content': content,
            'has_code': True,
            'has_math': True,
            'has_graph': False
        }
    
    @staticmethod
    def _binary_search() -> Dict[str, Any]:
        content = """# Binary Search

**Time Complexity:** O(log n)

```python
def binary_search(arr, target):
    \"\"\"
    Find target in sorted array.
    Returns index or -1 if not found.
    \"\"\"
    left, right = 0, len(arr) - 1
    
    while left <= right:
        mid = (left + right) // 2
        
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    
    return -1

# Recursive version
def binary_search_recursive(arr, target, left=0, right=None):
    if right is None:
        right = len(arr) - 1
    
    if left > right:
        return -1
    
    mid = (left + right) // 2
    
    if arr[mid] == target:
        return mid
    elif arr[mid] < target:
        return binary_search_recursive(arr, target, mid + 1, right)
    else:
        return binary_search_recursive(arr, target, left, mid - 1)

# Using bisect module
import bisect

arr = [1, 3, 5, 7, 9, 11, 13]
idx = bisect.bisect_left(arr, 7)  # Returns 3
```
"""
        return {
            'type': 'code',
            'content': content,
            'has_code': True,
            'has_math': False,
            'has_graph': False
        }
    
    @staticmethod
    def _linked_list() -> Dict[str, Any]:
        content = """# Linked List Implementation

```python
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

class LinkedList:
    def __init__(self):
        self.head = None
    
    def append(self, val):
        new_node = ListNode(val)
        if not self.head:
            self.head = new_node
            return
        
        curr = self.head
        while curr.next:
            curr = curr.next
        curr.next = new_node
    
    def prepend(self, val):
        new_node = ListNode(val)
        new_node.next = self.head
        self.head = new_node
    
    def delete(self, val):
        if not self.head:
            return
        
        if self.head.val == val:
            self.head = self.head.next
            return
        
        curr = self.head
        while curr.next:
            if curr.next.val == val:
                curr.next = curr.next.next
                return
            curr = curr.next
    
    def reverse(self):
        prev, curr = None, self.head
        while curr:
            next_node = curr.next
            curr.next = prev
            prev = curr
            curr = next_node
        self.head = prev
    
    def find_middle(self):
        \"\"\"Floyd's tortoise and hare.\"\"\"
        slow = fast = self.head
        while fast and fast.next:
            slow = slow.next
            fast = fast.next.next
        return slow.val
    
    def has_cycle(self):
        slow = fast = self.head
        while fast and fast.next:
            slow = slow.next
            fast = fast.next.next
            if slow == fast:
                return True
        return False
```
"""
        return {
            'type': 'code',
            'content': content,
            'has_code': True,
            'has_math': False,
            'has_graph': False
        }
    
    @staticmethod
    def _binary_tree() -> Dict[str, Any]:
        content = """# Binary Tree & BST

```python
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

class BinarySearchTree:
    def __init__(self):
        self.root = None
    
    def insert(self, val):
        self.root = self._insert(self.root, val)
    
    def _insert(self, node, val):
        if not node:
            return TreeNode(val)
        if val < node.val:
            node.left = self._insert(node.left, val)
        else:
            node.right = self._insert(node.right, val)
        return node
    
    def search(self, val):
        return self._search(self.root, val)
    
    def _search(self, node, val):
        if not node or node.val == val:
            return node
        if val < node.val:
            return self._search(node.left, val)
        return self._search(node.right, val)
    
    # Traversals
    def inorder(self, node, result=None):
        \"\"\"Left -> Root -> Right (sorted for BST)\"\"\"
        if result is None:
            result = []
        if node:
            self.inorder(node.left, result)
            result.append(node.val)
            self.inorder(node.right, result)
        return result
    
    def preorder(self, node, result=None):
        \"\"\"Root -> Left -> Right\"\"\"
        if result is None:
            result = []
        if node:
            result.append(node.val)
            self.preorder(node.left, result)
            self.preorder(node.right, result)
        return result
    
    def postorder(self, node, result=None):
        \"\"\"Left -> Right -> Root\"\"\"
        if result is None:
            result = []
        if node:
            self.postorder(node.left, result)
            self.postorder(node.right, result)
            result.append(node.val)
        return result
    
    def level_order(self):
        \"\"\"BFS traversal.\"\"\"
        if not self.root:
            return []
        
        result = []
        queue = [self.root]
        
        while queue:
            level = []
            for _ in range(len(queue)):
                node = queue.pop(0)
                level.append(node.val)
                if node.left:
                    queue.append(node.left)
                if node.right:
                    queue.append(node.right)
            result.append(level)
        
        return result
```
"""
        return {
            'type': 'code',
            'content': content,
            'has_code': True,
            'has_math': False,
            'has_graph': False
        }
    
    @staticmethod
    def _graph_algorithms() -> Dict[str, Any]:
        content = """# Graph Algorithms

```python
from collections import defaultdict, deque
import heapq

class Graph:
    def __init__(self, directed=False):
        self.graph = defaultdict(list)
        self.directed = directed
    
    def add_edge(self, u, v, weight=1):
        self.graph[u].append((v, weight))
        if not self.directed:
            self.graph[v].append((u, weight))
    
    def bfs(self, start):
        \"\"\"Breadth-First Search - O(V + E)\"\"\"
        visited = set([start])
        queue = deque([start])
        order = []
        
        while queue:
            node = queue.popleft()
            order.append(node)
            
            for neighbor, _ in self.graph[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        
        return order
    
    def dfs(self, start):
        \"\"\"Depth-First Search - O(V + E)\"\"\"
        visited = set()
        order = []
        
        def _dfs(node):
            visited.add(node)
            order.append(node)
            for neighbor, _ in self.graph[node]:
                if neighbor not in visited:
                    _dfs(neighbor)
        
        _dfs(start)
        return order
    
    def dijkstra(self, start):
        \"\"\"
        Shortest path - O((V + E) log V)
        Returns: dict of {node: shortest_distance}
        \"\"\"
        distances = {start: 0}
        pq = [(0, start)]
        
        while pq:
            dist, node = heapq.heappop(pq)
            
            if dist > distances.get(node, float('inf')):
                continue
            
            for neighbor, weight in self.graph[node]:
                new_dist = dist + weight
                if new_dist < distances.get(neighbor, float('inf')):
                    distances[neighbor] = new_dist
                    heapq.heappush(pq, (new_dist, neighbor))
        
        return distances
    
    def topological_sort(self):
        \"\"\"Kahn's algorithm - O(V + E)\"\"\"
        in_degree = defaultdict(int)
        for u in self.graph:
            for v, _ in self.graph[u]:
                in_degree[v] += 1
        
        queue = deque([u for u in self.graph if in_degree[u] == 0])
        order = []
        
        while queue:
            node = queue.popleft()
            order.append(node)
            
            for neighbor, _ in self.graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return order if len(order) == len(self.graph) else []
```
"""
        return {
            'type': 'code',
            'content': content,
            'has_code': True,
            'has_math': False,
            'has_graph': False
        }
    
    @staticmethod
    def _general_code() -> Dict[str, Any]:
        content = """# Programming Concepts

Ask me about:

**Data Structures:**
- Arrays, Linked Lists, Stacks, Queues
- Trees (Binary, BST, AVL, Red-Black)
- Graphs, Hash Tables, Heaps

**Algorithms:**
- Sorting (Quick, Merge, Heap)
- Searching (Binary, DFS, BFS)
- Dynamic Programming
- Graph algorithms (Dijkstra, A*)

**Numerical Methods:**
- Newton-Raphson, Bisection
- Numerical integration
- ODE solvers (Euler, RK4)

**Physics Simulations:**
- N-body problems
- Oscillators, Pendulums
- Wave equations

What would you like to explore?
"""
        return {
            'type': 'info',
            'content': content,
            'has_code': False,
            'has_math': False,
            'has_graph': False
        }


# Export classes
__all__ = ['Message', 'StreamingResponse', 'MathEngine', 'CodeEngine']
