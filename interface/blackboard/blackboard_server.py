"""
VoxMind Blackboard Math UI Server
=================================
A beautiful blackboard-style interface for solving mathematics.
"""

import os
import sys
import json
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

from core.math_solver import solve_math, MathResult

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')
CORS(app)


@app.route('/')
def index():
    """Render the blackboard UI."""
    return render_template('blackboard.html')


@app.route('/solve', methods=['POST'])
def solve():
    """Solve a math problem."""
    data = request.get_json()
    query = data.get('query', '')
    
    if not query:
        return jsonify({
            'success': False,
            'error': 'No query provided'
        })
    
    try:
        result = solve_math(query)
        return jsonify({
            'success': result.success,
            'query': result.query,
            'problem_type': result.problem_type,
            'input_latex': result.input_latex,
            'result_latex': result.result_latex,
            'result_text': result.result_text,
            'steps': result.steps,
            'explanation': result.explanation,
            'error': result.error
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/examples')
def examples():
    """Get example problems."""
    examples = {
        'Calculus': [
            'integral of cos^2 x dx',
            'integral of e^x sin(x) dx',
            'definite integral of x^2 from 0 to 1',
            'derivative of x^3 + 2x^2 - 5x + 3',
            'second derivative of sin(x)',
            'partial derivative of x^2*y + y^3 wrt x',
            'limit of sin(x)/x as x -> 0',
            'limit of (1 + 1/n)^n as n -> infinity',
        ],
        'Algebra': [
            'solve x^2 - 5x + 6 = 0',
            'solve 2x + 3 = 7',
            'factor x^2 - 9',
            'expand (x + 2)^4',
            'simplify (x^2 - 1)/(x - 1)',
            'roots of x^3 - 6x^2 + 11x - 6',
        ],
        'Series': [
            'taylor series of sin(x) around x = 0',
            'taylor series of e^x around x = 0',
            'maclaurin series of cos(x)',
            'taylor series of ln(1+x) around x = 0',
        ],
        'Linear Algebra': [
            'determinant of [[1,2],[3,4]]',
            'inverse of [[1,2],[3,4]]',
            'eigenvalues of [[4,2],[1,3]]',
            'transpose of [[1,2,3],[4,5,6]]',
            'rank of [[1,2,3],[2,4,6]]',
        ],
        'Statistics': [
            '10 choose 5',
            '5 factorial',
            'permutation 5 3',
            'mean of [1, 2, 3, 4, 5]',
            'variance of [2, 4, 6, 8, 10]',
            'standard deviation of [1, 2, 3, 4, 5]',
        ],
        'Trigonometry': [
            'simplify sin^2(x) + cos^2(x)',
            'simplify tan(x) * cos(x)',
            'expand sin(2x)',
        ],
        'Physics': [
            'kinetic energy of mass 10 velocity 5',
            'potential energy of mass 5 height 10',
            'force of mass 10 acceleration 9.8',
        ]
    }
    return jsonify(examples)


def run_server(host='127.0.0.1', port=5050, debug=False):
    """Run the blackboard server."""
    print(f"""
╔══════════════════════════════════════════════════════════╗
║       VoxMind Mathematics Blackboard                     ║
║       ─────────────────────────────────                  ║
║       Server running at http://{host}:{port}             ║
║       Press Ctrl+C to stop                               ║
╚══════════════════════════════════════════════════════════╝
    """)
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='VoxMind Math Blackboard')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5050, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    
    run_server(args.host, args.port, args.debug)
