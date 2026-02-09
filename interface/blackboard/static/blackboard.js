/**
 * VoxMind Mathematics Blackboard - Client-side Logic
 */

// History storage
const MAX_HISTORY = 10;
let history = JSON.parse(localStorage.getItem('mathHistory') || '[]');

// DOM Elements
const mathInput = document.getElementById('mathInput');
const solveBtn = document.getElementById('solveBtn');
const resultsArea = document.getElementById('resultsArea');
const examplesContainer = document.getElementById('examplesContainer');
const historyContainer = document.getElementById('historyContainer');
const loadingOverlay = document.getElementById('loadingOverlay');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadExamples();
    renderHistory();
    
    // Event listeners
    solveBtn.addEventListener('click', solveProblem);
    mathInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            solveProblem();
        }
    });
    
    // Initialize KaTeX auto-render
    if (typeof renderMathInElement !== 'undefined') {
        renderMathInElement(document.body, {
            delimiters: [
                {left: '$$', right: '$$', display: true},
                {left: '$', right: '$', display: false},
                {left: '\\[', right: '\\]', display: true},
                {left: '\\(', right: '\\)', display: false}
            ]
        });
    }
});

/**
 * Solve a math problem
 */
async function solveProblem() {
    const query = mathInput.value.trim();
    if (!query) {
        showNotification('Please enter a math problem');
        return;
    }
    
    showLoading(true);
    
    try {
        const response = await fetch('/solve', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query })
        });
        
        const result = await response.json();
        displayResult(result);
        
        if (result.success) {
            addToHistory(query, result.result_latex || result.result_text);
        }
    } catch (error) {
        displayError('Failed to connect to server: ' + error.message);
    } finally {
        showLoading(false);
    }
}

/**
 * Display the result
 */
function displayResult(result) {
    if (!result.success) {
        displayError(result.error);
        return;
    }
    
    const html = `
        <div class="result-card">
            <div class="result-header">
                <span class="problem-type">📊 ${escapeHtml(result.problem_type)}</span>
            </div>
            
            <div class="result-main">
                <div class="input-box">
                    <span class="math-label">Problem</span>
                    <div class="math-expression" id="inputMath"></div>
                </div>
                
                <div class="equals-sign">=</div>
                
                <div class="output-box">
                    <span class="math-label">Solution</span>
                    <div class="math-expression" id="outputMath"></div>
                </div>
            </div>
            
            ${result.steps && result.steps.length > 0 ? `
                <div class="steps-section">
                    <h3 class="steps-title">📝 Solution Steps</h3>
                    ${result.steps.map((step, i) => `
                        <div class="step-item">
                            <span class="step-number">${i + 1}</span>
                            <span class="step-text">${escapeHtml(step)}</span>
                        </div>
                    `).join('')}
                </div>
            ` : ''}
            
            ${result.explanation ? `
                <div class="explanation">
                    💡 ${escapeHtml(result.explanation)}
                </div>
            ` : ''}
        </div>
    `;
    
    resultsArea.innerHTML = html;
    
    // Render LaTeX
    const inputMathEl = document.getElementById('inputMath');
    const outputMathEl = document.getElementById('outputMath');
    
    try {
        if (result.input_latex) {
            katex.render(result.input_latex, inputMathEl, {
                throwOnError: false,
                displayMode: true
            });
        } else {
            inputMathEl.textContent = result.query;
        }
        
        if (result.result_latex) {
            katex.render(result.result_latex, outputMathEl, {
                throwOnError: false,
                displayMode: true
            });
        } else {
            outputMathEl.textContent = result.result_text;
        }
    } catch (e) {
        console.warn('KaTeX render error:', e);
        inputMathEl.textContent = result.query;
        outputMathEl.textContent = result.result_text;
    }
    
    // Scroll to results
    resultsArea.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/**
 * Display an error
 */
function displayError(message) {
    resultsArea.innerHTML = `
        <div class="result-card result-error">
            <div class="error-message">
                ❌ ${escapeHtml(message)}
            </div>
        </div>
    `;
}

/**
 * Load example problems
 */
async function loadExamples() {
    try {
        const response = await fetch('/examples');
        const examples = await response.json();
        
        let html = '';
        for (const [category, problems] of Object.entries(examples)) {
            html += `
                <div class="example-category">
                    <h3 class="category-title">${escapeHtml(category)}</h3>
                    ${problems.map(p => `
                        <div class="example-item" onclick="useExample('${escapeHtml(p)}')">${escapeHtml(p)}</div>
                    `).join('')}
                </div>
            `;
        }
        
        examplesContainer.innerHTML = html;
    } catch (error) {
        console.error('Failed to load examples:', error);
        examplesContainer.innerHTML = '<p class="history-empty">Could not load examples</p>';
    }
}

/**
 * Use an example problem
 */
function useExample(problem) {
    mathInput.value = problem;
    mathInput.focus();
    solveProblem();
}

/**
 * Add to history
 */
function addToHistory(query, result) {
    // Remove duplicate if exists
    history = history.filter(h => h.query !== query);
    
    // Add new entry
    history.unshift({ query, result, timestamp: Date.now() });
    
    // Limit size
    if (history.length > MAX_HISTORY) {
        history = history.slice(0, MAX_HISTORY);
    }
    
    // Save and render
    localStorage.setItem('mathHistory', JSON.stringify(history));
    renderHistory();
}

/**
 * Render history
 */
function renderHistory() {
    if (history.length === 0) {
        historyContainer.innerHTML = '<p class="history-empty">No recent problems yet. Try solving something!</p>';
        return;
    }
    
    const html = history.map(h => `
        <div class="history-item" onclick="useExample('${escapeHtml(h.query)}')">
            <span class="history-query">${escapeHtml(h.query)}</span>
            <span class="history-result">${truncate(h.result, 30)}</span>
        </div>
    `).join('');
    
    historyContainer.innerHTML = html;
}

/**
 * Show/hide loading overlay
 */
function showLoading(show) {
    if (show) {
        loadingOverlay.classList.remove('hidden');
    } else {
        loadingOverlay.classList.add('hidden');
    }
}

/**
 * Show a notification
 */
function showNotification(message) {
    // Simple alert for now, could be enhanced
    alert(message);
}

/**
 * Escape HTML
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Truncate text
 */
function truncate(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// Expose functions globally
window.useExample = useExample;
