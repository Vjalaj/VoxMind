"""
VoxMind Math Solver Engine
==========================
Solves complex mathematics using SymPy with LaTeX output.

Supports:
- Calculus: Integration, Differentiation, Limits, Series
- Linear Algebra: Matrix operations, Eigenvalues, Determinants
- Statistics: Distributions, Probability, Combinatorics
- Physics: Mechanics, Electromagnetism formulas
- Pure Math: Number theory, Algebra, Trigonometry
"""

import re
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, field
import logging

logger = logging.getLogger('VoxMind.MathSolver')

# Lazy load sympy (it's heavy)
_sympy_loaded = False
_sp = None

def _load_sympy():
    """Lazy load SymPy and common symbols."""
    global _sympy_loaded, _sp
    if not _sympy_loaded:
        import sympy as sp
        _sp = sp
        _sympy_loaded = True
    return _sp


@dataclass
class MathResult:
    """Result of a math computation."""
    query: str
    problem_type: str
    input_latex: str
    result_latex: str
    result_text: str
    steps: List[str] = field(default_factory=list)
    explanation: str = ""
    success: bool = True
    error: str = ""


class MathSolver:
    """
    Solves mathematical problems with step-by-step solutions.
    """
    
    def __init__(self):
        self.sp = _load_sympy()
        # Common symbols
        self.x, self.y, self.z = self.sp.symbols('x y z')
        self.t, self.n, self.k = self.sp.symbols('t n k')
        self.a, self.b, self.c = self.sp.symbols('a b c')
        
        # Problem type patterns
        self.patterns = self._build_patterns()
    
    def _build_patterns(self) -> Dict[str, List[Tuple[str, str]]]:
        """Build regex patterns for problem detection."""
        return {
            'integral': [
                (r'(?:what\s+is\s+)?(?:the\s+)?integr(?:al|ate)\s+(?:of\s+)?(.+?)(?:\s+d([a-z]))?$', 'indefinite'),
                (r'(?:∫|int)\s*(.+?)\s*d([a-z])', 'indefinite'),
                (r'integr(?:al|ate)\s+(.+?)\s+from\s+([\d\w\-\.]+)\s+to\s+([\d\w\-\.]+)', 'definite'),
                (r'definite\s+integral\s+(?:of\s+)?(.+?)\s+from\s+([\d\w\-\.]+)\s+to\s+([\d\w\-\.]+)', 'definite'),
            ],
            'derivative': [
                (r'(?:what\s+is\s+)?(?:the\s+)?(?:derivative|differentiate|diff)\s+(?:of\s+)?(.+?)(?:\s+(?:with\s+respect\s+to|wrt)\s+([a-z]))?$', 'first'),
                (r'd/d([a-z])\s*\[?\s*(.+?)\s*\]?$', 'first'),
                (r'(\d+)(?:st|nd|rd|th)\s+derivative\s+(?:of\s+)?(.+)', 'nth'),
                (r'second\s+derivative\s+(?:of\s+)?(.+)', 'second'),
                (r'partial\s+derivative\s+(?:of\s+)?(.+?)\s+(?:with\s+respect\s+to|wrt)\s+([a-z])', 'partial'),
            ],
            'limit': [
                (r'(?:what\s+is\s+)?(?:the\s+)?limit\s+(?:of\s+)?(.+?)\s+as\s+([a-z])\s*(?:->|→|approaches?|goes\s+to)\s*(.+)$', 'limit'),
                (r'lim\s*(?:_{([a-z])\s*(?:->|→)\s*(.+?)})?\s*(.+)', 'limit'),
            ],
            'solve': [
                (r'solve\s+(?:for\s+([a-z])\s*[:\s]+)?(.+?)(?:\s*=\s*(.+))?$', 'equation'),
                (r'(?:find|what\s+is)\s+([a-z])\s+(?:if|when|where)\s+(.+)', 'equation'),
                (r'roots?\s+(?:of\s+)?(.+)', 'roots'),
                (r'factor(?:ize)?\s+(.+)', 'factor'),
            ],
            'simplify': [
                (r'simplify\s+(.+)', 'simplify'),
                (r'expand\s+(.+)', 'expand'),
                (r'(?:reduce|cancel)\s+(.+)', 'simplify'),
            ],
            'series': [
                (r'taylor\s+(?:series\s+)?(?:of\s+)?(.+?)\s+(?:around|at|about)\s+([a-z])\s*=\s*(.+)', 'taylor'),
                (r'maclaurin\s+(?:series\s+)?(?:of\s+)?(.+)', 'maclaurin'),
                (r'fourier\s+(?:series\s+)?(?:of\s+)?(.+)', 'fourier'),
            ],
            'matrix': [
                (r'determinant\s+(?:of\s+)?(.+)', 'determinant'),
                (r'inverse\s+(?:of\s+)?(?:matrix\s+)?(.+)', 'inverse'),
                (r'eigenvalues?\s+(?:of\s+)?(.+)', 'eigenvalues'),
                (r'eigenvectors?\s+(?:of\s+)?(.+)', 'eigenvectors'),
                (r'transpose\s+(?:of\s+)?(.+)', 'transpose'),
                (r'rank\s+(?:of\s+)?(.+)', 'rank'),
            ],
            'statistics': [
                (r'mean\s+(?:of\s+)?(.+)', 'mean'),
                (r'(?:standard\s+)?deviation\s+(?:of\s+)?(.+)', 'std'),
                (r'variance\s+(?:of\s+)?(.+)', 'variance'),
                (r'median\s+(?:of\s+)?(.+)', 'median'),
                (r'probability\s+(?:of\s+)?(.+)', 'probability'),
                # Combinations: "10 choose 5", "n choose k", "C(10,5)"
                (r'(\d+)\s+choose\s+(\d+)', 'combination'),
                (r'C\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)', 'combination'),
                # Factorial: "5!", "5 factorial", "factorial of 5"
                (r'(\d+)\s*!', 'factorial'),
                (r'(\d+)\s+factorial', 'factorial'),
                (r'factorial\s+(?:of\s+)?(\d+)', 'factorial'),
                # Permutations: "P(5,3)", "permutation 5 3"
                (r'P\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)', 'permutation'),
                (r'permutation\s+(\d+)\s+(\d+)', 'permutation'),
            ],
            'trig': [
                (r'(?:prove|show|verify)\s+(.+?)\s*=\s*(.+)', 'identity'),
                (r'(?:convert|express)\s+(.+?)\s+(?:in|to)\s+(.+)', 'convert'),
            ],
            'physics': [
                (r'kinetic\s+energy\s+(?:of\s+)?(?:mass\s+)?(.+?)\s+(?:velocity|speed)\s+(.+)', 'kinetic'),
                (r'potential\s+energy\s+(?:of\s+)?(?:mass\s+)?(.+?)\s+(?:height\s+)?(.+)', 'potential'),
                (r'force\s+(?:of\s+)?(?:mass\s+)?(.+?)\s+(?:acceleration\s+)?(.+)', 'force'),
                (r'wave(?:length)?\s+(?:of\s+)?(?:frequency\s+)?(.+)', 'wave'),
            ],
        }
    
    def parse_expression(self, expr_str: str) -> Any:
        """Parse a string expression into SymPy expression."""
        sp = self.sp
        
        # Preprocessing
        expr_str = expr_str.strip()
        
        # Common replacements - order matters!
        replacements = [
            # Handle spoken "squared" / "square" for trig functions FIRST
            # "cos squared x", "cos square x", "cosine squared x"
            (r'\b(?:cos(?:ine)?)\s+(?:squared?|sq)\s*\(?([^)\s,]+)\)?', r'cos(\1)**2'),
            (r'\b(?:sin(?:e)?)\s+(?:squared?|sq)\s*\(?([^)\s,]+)\)?', r'sin(\1)**2'),
            (r'\b(?:tan(?:gent)?)\s+(?:squared?|sq)\s*\(?([^)\s,]+)\)?', r'tan(\1)**2'),
            (r'\b(?:sec(?:ant)?)\s+(?:squared?|sq)\s*\(?([^)\s,]+)\)?', r'sec(\1)**2'),
            (r'\b(?:csc|cosec(?:ant)?)\s+(?:squared?|sq)\s*\(?([^)\s,]+)\)?', r'csc(\1)**2'),
            (r'\b(?:cot(?:angent)?)\s+(?:squared?|sq)\s*\(?([^)\s,]+)\)?', r'cot(\1)**2'),
            # Trig squared with caret notation: cos^2(x), cos^2 x
            (r'\bcos\^2\s*\(?([^)\s,]+)\)?', r'cos(\1)**2'),
            (r'\bsin\^2\s*\(?([^)\s,]+)\)?', r'sin(\1)**2'),
            (r'\btan\^2\s*\(?([^)\s,]+)\)?', r'tan(\1)**2'),
            (r'\bsec\^2\s*\(?([^)\s,]+)\)?', r'sec(\1)**2'),
            (r'\bcsc\^2\s*\(?([^)\s,]+)\)?', r'csc(\1)**2'),
            (r'\bcot\^2\s*\(?([^)\s,]+)\)?', r'cot(\1)**2'),
            # Handle "x squared", "x cubed" - must come before word operators
            (r'\b([a-z])\s+squared\b', r'(\1**2)'),
            (r'\b([a-z])\s+cubed\b', r'(\1**3)'),
            # Word operators to symbols
            (r'\bplus\b', '+'),
            (r'\bminus\b', '-'),
            (r'\btimes\b', '*'),
            (r'\bmultiplied\s+by\b', '*'),
            (r'\bdivided\s+by\b', '/'),
            (r'\bover\b', '/'),
            (r'\bto\s+the\s+power\s+(?:of\s+)?(\d+)', r'**\1'),
            # Power notation
            (r'\^', '**'),
            # Implicit multiplication: 2x -> 2*x (but not in function names)
            (r'(\d)([a-z])(?![a-z])', r'\1*\2'),
            # Natural log
            (r'\bln\s*\(', 'log('),
            # Log base 10
            (r'\blog10\s*\(([^)]+)\)', r'log(\1, 10)'),
            # Constants
            (r'\bpi\b', 'pi'),
            (r'(?<![a-z])\be\b(?![a-z])', 'E'),  # Euler's number (isolated 'e')
            (r'\binfinity\b|\binf\b', 'oo'),
        ]
        
        for pattern, replacement in replacements:
            expr_str = re.sub(pattern, replacement, expr_str, flags=re.IGNORECASE)
        
        # Define local dict for parsing
        local_dict = {
            'x': self.x, 'y': self.y, 'z': self.z,
            't': self.t, 'n': self.n, 'k': self.k,
            'a': self.a, 'b': self.b, 'c': self.c,
            'pi': sp.pi, 'e': sp.E, 'E': sp.E,
            'I': sp.I, 'i': sp.I,
            'oo': sp.oo, 'inf': sp.oo,
            'sin': sp.sin, 'cos': sp.cos, 'tan': sp.tan,
            'sec': sp.sec, 'csc': sp.csc, 'cot': sp.cot,
            'asin': sp.asin, 'acos': sp.acos, 'atan': sp.atan,
            'sinh': sp.sinh, 'cosh': sp.cosh, 'tanh': sp.tanh,
            'log': sp.log, 'ln': sp.log, 'exp': sp.exp,
            'sqrt': sp.sqrt, 'abs': sp.Abs,
            'factorial': sp.factorial,
        }
        
        try:
            return sp.sympify(expr_str, locals=local_dict)
        except Exception as e:
            # Try parsing with transformations
            from sympy.parsing.sympy_parser import (
                parse_expr, standard_transformations, 
                implicit_multiplication_application, convert_xor
            )
            transformations = standard_transformations + (
                implicit_multiplication_application,
                convert_xor,
            )
            return parse_expr(expr_str, local_dict=local_dict, 
                            transformations=transformations)
    
    def solve(self, query: str) -> MathResult:
        """
        Solve a math problem from natural language query.
        """
        query = query.strip().lower()
        
        # Try each problem type
        for problem_type, patterns in self.patterns.items():
            for pattern, subtype in patterns:
                match = re.match(pattern, query, re.IGNORECASE)
                if match:
                    try:
                        if problem_type == 'integral':
                            return self._solve_integral(match, subtype, query)
                        elif problem_type == 'derivative':
                            return self._solve_derivative(match, subtype, query)
                        elif problem_type == 'limit':
                            return self._solve_limit(match, subtype, query)
                        elif problem_type == 'solve':
                            return self._solve_equation(match, subtype, query)
                        elif problem_type == 'simplify':
                            return self._solve_simplify(match, subtype, query)
                        elif problem_type == 'series':
                            return self._solve_series(match, subtype, query)
                        elif problem_type == 'matrix':
                            return self._solve_matrix(match, subtype, query)
                        elif problem_type == 'statistics':
                            return self._solve_statistics(match, subtype, query)
                        elif problem_type == 'trig':
                            return self._solve_trig(match, subtype, query)
                        elif problem_type == 'physics':
                            return self._solve_physics(match, subtype, query)
                    except Exception as e:
                        return MathResult(
                            query=query,
                            problem_type=problem_type,
                            input_latex="",
                            result_latex="",
                            result_text=str(e),
                            success=False,
                            error=str(e)
                        )
        
        # If no pattern matched, try direct evaluation
        return self._direct_eval(query)
    
    def _solve_integral(self, match, subtype: str, query: str) -> MathResult:
        """Solve integration problems."""
        sp = self.sp
        steps = []
        
        if subtype == 'indefinite':
            groups = match.groups()
            expr_str = groups[0].strip()
            var_str = groups[1] if len(groups) > 1 and groups[1] else 'x'
            
            # Clean up "dx" from expression if present
            expr_str = re.sub(r'\s*d[a-z]\s*$', '', expr_str)
            
            var = sp.Symbol(var_str)
            expr = self.parse_expression(expr_str)
            
            steps.append(f"Given: ∫ {sp.latex(expr)} d{var_str}")
            steps.append(f"Integrating with respect to {var_str}...")
            
            result = sp.integrate(expr, var)
            
            # Add constant of integration
            C = sp.Symbol('C')
            result_with_c = result + C
            
            steps.append(f"Result: {sp.latex(result_with_c)}")
            
            return MathResult(
                query=query,
                problem_type="Indefinite Integral",
                input_latex=f"\\int {sp.latex(expr)} \\, d{var_str}",
                result_latex=sp.latex(result_with_c),
                result_text=str(result_with_c),
                steps=steps,
                explanation=f"The integral of {expr} with respect to {var_str} is {result} + C"
            )
        
        elif subtype == 'definite':
            expr_str, lower, upper = match.groups()[:3]
            
            expr = self.parse_expression(expr_str)
            lower_val = self.parse_expression(lower)
            upper_val = self.parse_expression(upper)
            
            # Determine variable (usually x)
            free_syms = expr.free_symbols
            var = self.x if self.x in free_syms else list(free_syms)[0] if free_syms else self.x
            
            steps.append(f"Given: ∫ from {lower} to {upper} of {sp.latex(expr)} d{var}")
            
            result = sp.integrate(expr, (var, lower_val, upper_val))
            
            steps.append(f"First find antiderivative: {sp.latex(sp.integrate(expr, var))}")
            steps.append(f"Evaluate at bounds: F({upper}) - F({lower})")
            steps.append(f"Result: {sp.latex(result)}")
            
            return MathResult(
                query=query,
                problem_type="Definite Integral",
                input_latex=f"\\int_{{{sp.latex(lower_val)}}}^{{{sp.latex(upper_val)}}} {sp.latex(expr)} \\, d{var}",
                result_latex=sp.latex(result),
                result_text=str(result),
                steps=steps,
                explanation=f"The definite integral equals {result}"
            )
    
    def _solve_derivative(self, match, subtype: str, query: str) -> MathResult:
        """Solve differentiation problems."""
        sp = self.sp
        steps = []
        
        groups = match.groups()
        
        if subtype == 'first':
            if len(groups) >= 2 and groups[0] and len(groups[0]) == 1:
                # d/dx format
                var_str = groups[0]
                expr_str = groups[1]
            else:
                expr_str = groups[0]
                var_str = groups[1] if len(groups) > 1 and groups[1] else 'x'
            
            var = sp.Symbol(var_str)
            expr = self.parse_expression(expr_str)
            
            steps.append(f"Given: d/d{var_str} [{sp.latex(expr)}]")
            steps.append(f"Applying differentiation rules...")
            
            result = sp.diff(expr, var)
            
            steps.append(f"Result: {sp.latex(result)}")
            
            return MathResult(
                query=query,
                problem_type="First Derivative",
                input_latex=f"\\frac{{d}}{{d{var_str}}} \\left[ {sp.latex(expr)} \\right]",
                result_latex=sp.latex(result),
                result_text=str(result),
                steps=steps,
                explanation=f"The derivative of {expr} with respect to {var_str} is {result}"
            )
        
        elif subtype == 'second':
            expr_str = groups[0]
            expr = self.parse_expression(expr_str)
            var = self.x
            
            first = sp.diff(expr, var)
            result = sp.diff(first, var)
            
            steps.append(f"Given: d²/dx² [{sp.latex(expr)}]")
            steps.append(f"First derivative: {sp.latex(first)}")
            steps.append(f"Second derivative: {sp.latex(result)}")
            
            return MathResult(
                query=query,
                problem_type="Second Derivative",
                input_latex=f"\\frac{{d^2}}{{dx^2}} \\left[ {sp.latex(expr)} \\right]",
                result_latex=sp.latex(result),
                result_text=str(result),
                steps=steps,
                explanation=f"The second derivative is {result}"
            )
        
        elif subtype == 'nth':
            n = int(groups[0])
            expr_str = groups[1]
            expr = self.parse_expression(expr_str)
            var = self.x
            
            result = sp.diff(expr, var, n)
            
            ordinal = {1: 'st', 2: 'nd', 3: 'rd'}.get(n, 'th')
            
            return MathResult(
                query=query,
                problem_type=f"{n}{ordinal} Derivative",
                input_latex=f"\\frac{{d^{n}}}{{dx^{n}}} \\left[ {sp.latex(expr)} \\right]",
                result_latex=sp.latex(result),
                result_text=str(result),
                steps=[f"Computing {n}{ordinal} derivative of {sp.latex(expr)}", f"Result: {sp.latex(result)}"],
                explanation=f"The {n}{ordinal} derivative is {result}"
            )
        
        elif subtype == 'partial':
            expr_str = groups[0]
            var_str = groups[1]
            expr = self.parse_expression(expr_str)
            var = sp.Symbol(var_str)
            
            result = sp.diff(expr, var)
            
            return MathResult(
                query=query,
                problem_type="Partial Derivative",
                input_latex=f"\\frac{{\\partial}}{{\\partial {var_str}}} \\left[ {sp.latex(expr)} \\right]",
                result_latex=sp.latex(result),
                result_text=str(result),
                steps=[f"Computing partial derivative with respect to {var_str}", f"Result: {sp.latex(result)}"],
                explanation=f"The partial derivative with respect to {var_str} is {result}"
            )
    
    def _solve_limit(self, match, subtype: str, query: str) -> MathResult:
        """Solve limit problems."""
        sp = self.sp
        groups = match.groups()
        
        # Parse groups based on pattern
        if len(groups) == 3:
            expr_str, var_str, point_str = groups
        else:
            var_str = groups[0] if groups[0] else 'x'
            point_str = groups[1] if len(groups) > 1 else '0'
            expr_str = groups[2] if len(groups) > 2 else groups[0]
        
        if not expr_str:
            expr_str = query.split('limit')[-1].split('as')[0].strip()
        
        var = sp.Symbol(var_str) if var_str else self.x
        expr = self.parse_expression(expr_str)
        point = self.parse_expression(point_str)
        
        result = sp.limit(expr, var, point)
        
        steps = [
            f"Given: lim ({var_str} → {point_str}) of {sp.latex(expr)}",
            f"Evaluating the limit...",
            f"Result: {sp.latex(result)}"
        ]
        
        return MathResult(
            query=query,
            problem_type="Limit",
            input_latex=f"\\lim_{{{var_str} \\to {sp.latex(point)}}} {sp.latex(expr)}",
            result_latex=sp.latex(result),
            result_text=str(result),
            steps=steps,
            explanation=f"The limit as {var_str} approaches {point} is {result}"
        )
    
    def _solve_equation(self, match, subtype: str, query: str) -> MathResult:
        """Solve equations."""
        sp = self.sp
        groups = match.groups()
        
        if subtype == 'equation':
            var_str = groups[0] if groups[0] else 'x'
            lhs_str = groups[1]
            rhs_str = groups[2] if len(groups) > 2 and groups[2] else '0'
            
            var = sp.Symbol(var_str)
            lhs = self.parse_expression(lhs_str)
            rhs = self.parse_expression(rhs_str)
            
            equation = sp.Eq(lhs, rhs)
            solutions = sp.solve(equation, var)
            
            result_latex = ', '.join([sp.latex(s) for s in solutions]) if solutions else "\\text{No solution}"
            
            return MathResult(
                query=query,
                problem_type="Equation",
                input_latex=f"{sp.latex(lhs)} = {sp.latex(rhs)}",
                result_latex=f"{var_str} = {result_latex}",
                result_text=f"{var_str} = {solutions}",
                steps=[f"Solving {sp.latex(equation)} for {var_str}", f"Solutions: {result_latex}"],
                explanation=f"The solution(s) for {var_str} are: {solutions}"
            )
        
        elif subtype == 'roots':
            expr_str = groups[0]
            expr = self.parse_expression(expr_str)
            
            roots = sp.solve(expr)
            result_latex = ', '.join([sp.latex(r) for r in roots]) if roots else "\\text{No real roots}"
            
            return MathResult(
                query=query,
                problem_type="Roots",
                input_latex=f"{sp.latex(expr)} = 0",
                result_latex=result_latex,
                result_text=str(roots),
                steps=[f"Finding roots of {sp.latex(expr)} = 0", f"Roots: {result_latex}"],
                explanation=f"The roots are: {roots}"
            )
        
        elif subtype == 'factor':
            expr_str = groups[0]
            expr = self.parse_expression(expr_str)
            
            result = sp.factor(expr)
            
            return MathResult(
                query=query,
                problem_type="Factorization",
                input_latex=sp.latex(expr),
                result_latex=sp.latex(result),
                result_text=str(result),
                steps=[f"Factoring {sp.latex(expr)}", f"Result: {sp.latex(result)}"],
                explanation=f"The factored form is {result}"
            )
    
    def _solve_simplify(self, match, subtype: str, query: str) -> MathResult:
        """Simplify or expand expressions."""
        sp = self.sp
        expr_str = match.group(1)
        expr = self.parse_expression(expr_str)
        
        if subtype == 'expand':
            result = sp.expand(expr)
            problem_type = "Expansion"
        else:
            result = sp.simplify(expr)
            problem_type = "Simplification"
        
        return MathResult(
            query=query,
            problem_type=problem_type,
            input_latex=sp.latex(expr),
            result_latex=sp.latex(result),
            result_text=str(result),
            steps=[f"Original: {sp.latex(expr)}", f"Result: {sp.latex(result)}"],
            explanation=f"The simplified form is {result}"
        )
    
    def _solve_series(self, match, subtype: str, query: str) -> MathResult:
        """Solve series expansion problems."""
        sp = self.sp
        groups = match.groups()
        
        if subtype == 'taylor':
            expr_str, var_str, point_str = groups
            var = sp.Symbol(var_str)
            expr = self.parse_expression(expr_str)
            point = self.parse_expression(point_str)
            
            result = sp.series(expr, var, point, n=6)
            
            return MathResult(
                query=query,
                problem_type="Taylor Series",
                input_latex=f"\\text{{Taylor series of }} {sp.latex(expr)} \\text{{ around }} {var_str}={sp.latex(point)}",
                result_latex=sp.latex(result),
                result_text=str(result),
                steps=[f"Expanding {sp.latex(expr)} around {var_str}={point}", f"Result: {sp.latex(result)}"],
                explanation=f"The Taylor series is {result}"
            )
        
        elif subtype == 'maclaurin':
            expr_str = groups[0]
            expr = self.parse_expression(expr_str)
            
            result = sp.series(expr, self.x, 0, n=6)
            
            return MathResult(
                query=query,
                problem_type="Maclaurin Series",
                input_latex=f"\\text{{Maclaurin series of }} {sp.latex(expr)}",
                result_latex=sp.latex(result),
                result_text=str(result),
                steps=[f"Maclaurin series (Taylor at x=0) of {sp.latex(expr)}", f"Result: {sp.latex(result)}"],
                explanation=f"The Maclaurin series is {result}"
            )
    
    def _solve_matrix(self, match, subtype: str, query: str) -> MathResult:
        """Solve matrix problems."""
        sp = self.sp
        expr_str = match.group(1)
        
        # Parse matrix from string like [[1,2],[3,4]] or 1,2;3,4
        matrix_str = expr_str.strip()
        
        # Try to parse as matrix
        if '[[' in matrix_str:
            # Python list format
            import ast
            data = ast.literal_eval(matrix_str)
            matrix = sp.Matrix(data)
        elif ';' in matrix_str:
            # Semicolon separated rows
            rows = matrix_str.split(';')
            data = [[self.parse_expression(x.strip()) for x in row.split(',')] for row in rows]
            matrix = sp.Matrix(data)
        else:
            # Try as single expression
            matrix = sp.Matrix([[self.parse_expression(matrix_str)]])
        
        if subtype == 'determinant':
            result = matrix.det()
            result_latex = sp.latex(result)
            explanation = f"The determinant is {result}"
        elif subtype == 'inverse':
            result = matrix.inv()
            result_latex = sp.latex(result)
            explanation = "The inverse matrix"
        elif subtype == 'eigenvalues':
            result = matrix.eigenvals()
            result_latex = ', '.join([f"{sp.latex(k)}: {v}" for k, v in result.items()])
            explanation = f"Eigenvalues with multiplicities: {result}"
        elif subtype == 'eigenvectors':
            result = matrix.eigenvects()
            result_latex = str(result)
            explanation = "Eigenvectors"
        elif subtype == 'transpose':
            result = matrix.T
            result_latex = sp.latex(result)
            explanation = "The transpose"
        elif subtype == 'rank':
            result = matrix.rank()
            result_latex = str(result)
            explanation = f"The rank is {result}"
        else:
            result = matrix
            result_latex = sp.latex(matrix)
            explanation = "Matrix"
        
        return MathResult(
            query=query,
            problem_type=f"Matrix {subtype.title()}",
            input_latex=sp.latex(matrix),
            result_latex=result_latex,
            result_text=str(result),
            steps=[f"Given matrix: {sp.latex(matrix)}", f"Computing {subtype}...", f"Result: {result_latex}"],
            explanation=explanation
        )
    
    def _solve_statistics(self, match, subtype: str, query: str) -> MathResult:
        """Solve statistics problems."""
        sp = self.sp
        from sympy.stats import Normal, E as ExpectedValue, variance, std
        from sympy import binomial, factorial, Rational
        
        if subtype == 'combination':
            n, k = int(match.group(1)), int(match.group(2))
            result = binomial(n, k)
            return MathResult(
                query=query,
                problem_type="Combination",
                input_latex=f"\\binom{{{n}}}{{{k}}}",
                result_latex=sp.latex(result),
                result_text=str(result),
                steps=[f"C({n},{k}) = {n}! / ({k}! × ({n}-{k})!)", f"= {result}"],
                explanation=f"{n} choose {k} = {result}"
            )
        
        elif subtype == 'factorial':
            n = int(match.group(1))
            result = factorial(n)
            return MathResult(
                query=query,
                problem_type="Factorial",
                input_latex=f"{n}!",
                result_latex=sp.latex(result),
                result_text=str(result),
                steps=[f"{n}! = {n} × {n-1} × ... × 1", f"= {result}"],
                explanation=f"{n}! = {result}"
            )
        
        elif subtype == 'permutation':
            n, r = int(match.group(1)), int(match.group(2))
            result = factorial(n) / factorial(n - r)
            return MathResult(
                query=query,
                problem_type="Permutation",
                input_latex=f"P({n},{r})",
                result_latex=sp.latex(result),
                result_text=str(result),
                steps=[f"P({n},{r}) = {n}! / ({n}-{r})!", f"= {result}"],
                explanation=f"P({n},{r}) = {result}"
            )
        
        else:
            # For mean, variance, std - parse data
            data_str = match.group(1)
            # Parse as list of numbers
            data = [float(x.strip()) for x in data_str.replace('[', '').replace(']', '').split(',')]
            
            if subtype == 'mean':
                result = sum(data) / len(data)
                result_latex = f"{result:.4f}"
            elif subtype == 'variance':
                mean = sum(data) / len(data)
                result = sum((x - mean)**2 for x in data) / len(data)
                result_latex = f"{result:.4f}"
            elif subtype == 'std':
                mean = sum(data) / len(data)
                variance = sum((x - mean)**2 for x in data) / len(data)
                result = variance ** 0.5
                result_latex = f"{result:.4f}"
            elif subtype == 'median':
                sorted_data = sorted(data)
                n = len(sorted_data)
                if n % 2 == 0:
                    result = (sorted_data[n//2 - 1] + sorted_data[n//2]) / 2
                else:
                    result = sorted_data[n//2]
                result_latex = f"{result:.4f}"
            else:
                result = data
                result_latex = str(data)
            
            return MathResult(
                query=query,
                problem_type=f"Statistics ({subtype})",
                input_latex=f"\\text{{Data: }} {data}",
                result_latex=result_latex,
                result_text=str(result),
                steps=[f"Data: {data}", f"{subtype.title()}: {result_latex}"],
                explanation=f"The {subtype} is {result}"
            )
    
    def _solve_trig(self, match, subtype: str, query: str) -> MathResult:
        """Solve trigonometry problems."""
        sp = self.sp
        
        if subtype == 'identity':
            lhs_str, rhs_str = match.groups()
            lhs = self.parse_expression(lhs_str)
            rhs = self.parse_expression(rhs_str)
            
            # Try to simplify difference to 0
            diff = sp.simplify(lhs - rhs)
            verified = diff == 0
            
            return MathResult(
                query=query,
                problem_type="Trig Identity Verification",
                input_latex=f"{sp.latex(lhs)} = {sp.latex(rhs)}",
                result_latex="\\text{True}" if verified else f"\\text{{Difference: }} {sp.latex(diff)}",
                result_text=str(verified),
                steps=[f"LHS: {sp.latex(lhs)}", f"RHS: {sp.latex(rhs)}", 
                       f"LHS - RHS = {sp.latex(diff)}", 
                       "Identity verified!" if verified else "Identity not verified"],
                explanation="The identity is " + ("true" if verified else "false")
            )
        
        return self._direct_eval(query)
    
    def _solve_physics(self, match, subtype: str, query: str) -> MathResult:
        """Solve physics problems."""
        sp = self.sp
        groups = match.groups()
        
        if subtype == 'kinetic':
            m = self.parse_expression(groups[0])
            v = self.parse_expression(groups[1])
            result = sp.Rational(1, 2) * m * v**2
            formula = "KE = \\frac{1}{2}mv^2"
        elif subtype == 'potential':
            m = self.parse_expression(groups[0])
            h = self.parse_expression(groups[1])
            g = sp.Symbol('g')
            result = m * g * h
            formula = "PE = mgh"
        elif subtype == 'force':
            m = self.parse_expression(groups[0])
            a = self.parse_expression(groups[1])
            result = m * a
            formula = "F = ma"
        else:
            return self._direct_eval(query)
        
        return MathResult(
            query=query,
            problem_type=f"Physics ({subtype})",
            input_latex=formula,
            result_latex=sp.latex(result),
            result_text=str(result),
            steps=[f"Using {formula}", f"Result: {sp.latex(result)}"],
            explanation=f"The result is {result}"
        )
    
    def _direct_eval(self, query: str) -> MathResult:
        """Try to directly evaluate an expression."""
        sp = self.sp
        
        try:
            # Try to parse and simplify
            expr = self.parse_expression(query)
            result = sp.simplify(expr)
            
            return MathResult(
                query=query,
                problem_type="Evaluation",
                input_latex=sp.latex(expr),
                result_latex=sp.latex(result),
                result_text=str(result),
                steps=[f"Evaluating: {sp.latex(expr)}", f"Result: {sp.latex(result)}"],
                explanation=f"The result is {result}"
            )
        except Exception as e:
            return MathResult(
                query=query,
                problem_type="Unknown",
                input_latex="",
                result_latex="",
                result_text="",
                success=False,
                error=f"Could not parse: {query}. Error: {e}"
            )


# Global solver instance
_solver: Optional[MathSolver] = None

def get_solver() -> MathSolver:
    """Get the global math solver."""
    global _solver
    if _solver is None:
        _solver = MathSolver()
    return _solver


def solve_math(query: str) -> MathResult:
    """Convenience function to solve math problems."""
    return get_solver().solve(query)


# Demo
if __name__ == '__main__':
    solver = MathSolver()
    
    test_problems = [
        "integral of cos^2 x dx",
        "derivative of x^3 + 2x",
        "limit of sin(x)/x as x -> 0",
        "solve x^2 - 5x + 6 = 0",
        "factor x^2 - 4",
        "10 choose 5",
        "expand (x + 2)^3",
        "taylor series of e^x around x = 0",
    ]
    
    for problem in test_problems:
        print(f"\n{'='*60}")
        print(f"Problem: {problem}")
        result = solver.solve(problem)
        print(f"Type: {result.problem_type}")
        print(f"Input LaTeX: {result.input_latex}")
        print(f"Result LaTeX: {result.result_latex}")
        print(f"Result: {result.result_text}")
        if result.steps:
            print("Steps:")
            for step in result.steps:
                print(f"  - {step}")
