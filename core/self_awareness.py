"""
VoxMind Self-Awareness System
=============================
Makes VoxMind "aware" of its own state and capabilities.

This is NOT conscious AI - it's a sophisticated introspection system that:
- Monitors its own performance
- Knows what it can and cannot do
- Learns from interactions
- Adapts behavior based on patterns
- Reports on its own status

"I am not conscious, but I know what I'm doing"
"""

import asyncio
import json
import time
import threading
import logging
import psutil
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Callable, Set, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import statistics

logger = logging.getLogger('VoxMind.SelfAware')


# ============================================================================
# CAPABILITY REGISTRY
# ============================================================================

@dataclass
class Capability:
    """Something VoxMind can do."""
    name: str
    description: str
    category: str
    confidence: float  # How well can I do this? 0-1
    requirements: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)


class CapabilityRegistry:
    """
    Registry of what VoxMind can and cannot do.
    
    When user asks "Can you do X?", we check here.
    When task fails, we might discover a new limitation.
    """
    
    def __init__(self):
        self.capabilities: Dict[str, Capability] = {}
        self.limitations: Set[str] = set()
        self._init_core_capabilities()
    
    def _init_core_capabilities(self):
        """Initialize known capabilities."""
        caps = [
            Capability(
                name="voice_recognition",
                description="Convert spoken words to text",
                category="input",
                confidence=0.85,
                requirements=["microphone", "speech_recognition"],
                examples=["Listen to voice commands", "Transcribe speech"],
                limitations=["Background noise affects accuracy", 
                            "Heavy accents may be challenging"]
            ),
            Capability(
                name="text_to_speech",
                description="Convert text to spoken words",
                category="output",
                confidence=0.95,
                requirements=["speaker", "pyttsx3 or edge_tts"],
                examples=["Read text aloud", "Speak responses"]
            ),
            Capability(
                name="app_control",
                description="Open, close, and interact with applications",
                category="automation",
                confidence=0.75,
                requirements=["pywin32", "windows"],
                examples=["Open Chrome", "Close Notepad", "Switch windows"],
                limitations=["Some apps may not respond to automation",
                            "Admin apps may require elevated permissions"]
            ),
            Capability(
                name="web_search",
                description="Search the web for information",
                category="information",
                confidence=0.80,
                requirements=["internet", "aiohttp"],
                examples=["Search for AI news", "Look up weather"]
            ),
            Capability(
                name="calculations",
                description="Perform mathematical calculations",
                category="computation",
                confidence=0.99,
                examples=["Calculate 15 * 24", "What is 2^10?"]
            ),
            Capability(
                name="file_operations",
                description="Create, read, and manage files",
                category="automation",
                confidence=0.85,
                examples=["Create a document", "Find files named X"],
                limitations=["Cannot access protected system files"]
            ),
            Capability(
                name="screen_analysis",
                description="Understand what's on the screen",
                category="perception",
                confidence=0.70,
                requirements=["pillow", "easyocr"],
                examples=["Read text on screen", "Find buttons"],
                limitations=["OCR accuracy varies", "Complex UIs are harder"]
            ),
            Capability(
                name="calendar_management",
                description="Manage calendar events and reminders",
                category="organization",
                confidence=0.80,
                examples=["Add meeting tomorrow", "What's my schedule?"]
            ),
            Capability(
                name="multitasking",
                description="Handle multiple tasks in parallel",
                category="execution",
                confidence=0.90,
                examples=["Search while checking calendar", "Multiple queries"]
            )
        ]
        
        for cap in caps:
            self.capabilities[cap.name] = cap
        
        # Known limitations (things we CANNOT do)
        self.limitations = {
            "true_understanding",  # I don't actually understand like humans
            "consciousness",  # I'm not conscious
            "physical_actions",  # Can't interact with physical world
            "internet_without_connection",  # Need network for web tasks
            "admin_without_elevation",  # Some system tasks need admin
            "learning_in_realtime",  # Can't update my own model
            "perfect_accuracy",  # All AI has error rates
            "emotions",  # I don't have feelings
            "creativity_from_nothing",  # I work with patterns
        }
    
    def can_do(self, task: str) -> Tuple[bool, str]:
        """
        Check if VoxMind can do a task.
        
        Returns (can_do, explanation)
        """
        task_lower = task.lower()
        
        # Check explicit limitations first
        for limitation in self.limitations:
            limit_words = limitation.replace('_', ' ').split()
            if all(w in task_lower for w in limit_words):
                return False, f"I cannot {limitation.replace('_', ' ')}."
        
        # Check capabilities
        best_match = None
        best_confidence = 0
        
        for name, cap in self.capabilities.items():
            # Simple keyword matching
            keywords = name.replace('_', ' ').split() + cap.description.lower().split()
            matches = sum(1 for kw in keywords if kw in task_lower)
            
            if matches > 0 and cap.confidence > best_confidence:
                best_match = cap
                best_confidence = cap.confidence
        
        if best_match:
            limitations = ""
            if best_match.limitations:
                limitations = f" However, {best_match.limitations[0].lower()}"
            return True, f"Yes, I can {best_match.description.lower()}.{limitations}"
        
        return False, "I'm not sure if I can do that. Could you be more specific?"
    
    def list_capabilities(self, category: str = None) -> List[Capability]:
        """List all or filtered capabilities."""
        if category:
            return [c for c in self.capabilities.values() 
                    if c.category == category]
        return list(self.capabilities.values())
    
    def update_confidence(self, capability: str, success: bool):
        """Update confidence based on success/failure."""
        if capability in self.capabilities:
            cap = self.capabilities[capability]
            # Bayesian-ish update
            if success:
                cap.confidence = min(1.0, cap.confidence + 0.01)
            else:
                cap.confidence = max(0.1, cap.confidence - 0.02)


# ============================================================================
# PERFORMANCE TRACKER
# ============================================================================

@dataclass
class PerformanceMetric:
    """A single performance measurement."""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    unit: str = ""


class PerformanceTracker:
    """
    Tracks VoxMind's own performance.
    
    "I know how well I'm doing"
    """
    
    def __init__(self, history_size: int = 1000):
        self.metrics: Dict[str, List[PerformanceMetric]] = defaultdict(list)
        self.history_size = history_size
        self._lock = threading.Lock()
        
        # Key metrics to track
        self.tracked_metrics = {
            'response_time': 'ms',
            'recognition_accuracy': '%',
            'command_success_rate': '%',
            'memory_usage': 'MB',
            'cpu_usage': '%',
            'tasks_completed': 'count',
            'tasks_failed': 'count'
        }
    
    def record(self, name: str, value: float, unit: str = ""):
        """Record a metric."""
        with self._lock:
            metric = PerformanceMetric(name, value, unit=unit)
            self.metrics[name].append(metric)
            
            # Trim history
            if len(self.metrics[name]) > self.history_size:
                self.metrics[name] = self.metrics[name][-self.history_size:]
    
    def get_stats(self, name: str, window_minutes: int = 60) -> Dict[str, float]:
        """Get statistics for a metric."""
        cutoff = time.time() - (window_minutes * 60)
        
        with self._lock:
            values = [m.value for m in self.metrics.get(name, []) 
                      if m.timestamp > cutoff]
        
        if not values:
            return {'count': 0}
        
        return {
            'count': len(values),
            'mean': statistics.mean(values),
            'min': min(values),
            'max': max(values),
            'median': statistics.median(values) if len(values) > 1 else values[0],
            'stdev': statistics.stdev(values) if len(values) > 1 else 0
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get overall performance summary."""
        summary = {}
        
        for name in self.tracked_metrics:
            stats = self.get_stats(name)
            if stats['count'] > 0:
                summary[name] = {
                    'current': stats['mean'],
                    'unit': self.tracked_metrics[name],
                    'trend': self._calculate_trend(name)
                }
        
        return summary
    
    def _calculate_trend(self, name: str) -> str:
        """Calculate if metric is improving or declining."""
        values = [m.value for m in self.metrics.get(name, [])]
        if len(values) < 10:
            return 'stable'
        
        first_half = statistics.mean(values[:len(values)//2])
        second_half = statistics.mean(values[len(values)//2:])
        
        diff_pct = (second_half - first_half) / first_half * 100 if first_half else 0
        
        if diff_pct > 5:
            return 'improving' if 'success' in name or 'accuracy' in name else 'declining'
        elif diff_pct < -5:
            return 'declining' if 'success' in name or 'accuracy' in name else 'improving'
        return 'stable'


# ============================================================================
# LEARNING ENGINE (Pattern Recognition)
# ============================================================================

@dataclass
class LearnedPattern:
    """A pattern learned from interactions."""
    pattern: str
    action: str
    confidence: float
    occurrences: int
    last_seen: float
    success_rate: float = 1.0


class LearningEngine:
    """
    Learns patterns from user interactions.
    
    NOT machine learning in the neural net sense - this is
    statistical pattern recognition from interactions.
    
    "I remember what you like"
    """
    
    def __init__(self, storage_path: str = "data/learned_patterns.json"):
        self.storage_path = Path(storage_path)
        self.patterns: Dict[str, LearnedPattern] = {}
        self.user_preferences: Dict[str, Any] = {}
        self.interaction_history: List[Dict] = []
        self._load()
    
    def _load(self):
        """Load learned patterns from disk."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path) as f:
                    data = json.load(f)
                    self.patterns = {
                        k: LearnedPattern(**v) 
                        for k, v in data.get('patterns', {}).items()
                    }
                    self.user_preferences = data.get('preferences', {})
            except Exception as e:
                logger.error(f"Failed to load patterns: {e}")
    
    def _save(self):
        """Save patterns to disk."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.storage_path, 'w') as f:
                json.dump({
                    'patterns': {k: asdict(v) for k, v in self.patterns.items()},
                    'preferences': self.user_preferences
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save patterns: {e}")
    
    def learn_from_interaction(self, user_input: str, action: str, 
                               success: bool, context: Dict = None):
        """Learn from a user interaction."""
        # Extract pattern (simplified - in production, use NLP)
        pattern = self._extract_pattern(user_input)
        
        if pattern in self.patterns:
            p = self.patterns[pattern]
            p.occurrences += 1
            p.last_seen = time.time()
            # Update success rate (moving average)
            p.success_rate = (p.success_rate * (p.occurrences - 1) + 
                              (1 if success else 0)) / p.occurrences
            p.confidence = min(1.0, p.occurrences * 0.1) * p.success_rate
        else:
            self.patterns[pattern] = LearnedPattern(
                pattern=pattern,
                action=action,
                confidence=0.5 if success else 0.1,
                occurrences=1,
                last_seen=time.time(),
                success_rate=1.0 if success else 0.0
            )
        
        # Record interaction
        self.interaction_history.append({
            'input': user_input,
            'action': action,
            'success': success,
            'timestamp': time.time(),
            'context': context
        })
        
        # Keep last 1000 interactions
        if len(self.interaction_history) > 1000:
            self.interaction_history = self.interaction_history[-1000:]
        
        # Learn preferences from context
        if context:
            self._update_preferences(context)
        
        self._save()
    
    def _extract_pattern(self, text: str) -> str:
        """Extract a pattern from text (simplified)."""
        # Normalize
        text = text.lower().strip()
        
        # Remove specific values but keep structure
        import re
        # Replace numbers with placeholder
        text = re.sub(r'\d+', '<NUM>', text)
        # Replace quoted strings
        text = re.sub(r'"[^"]*"', '<STR>', text)
        text = re.sub(r"'[^']*'", '<STR>', text)
        
        return text
    
    def _update_preferences(self, context: Dict):
        """Update user preferences from interaction context."""
        # Learn things like preferred apps, times, etc.
        if 'app' in context:
            self.user_preferences.setdefault('frequent_apps', {})
            app = context['app']
            self.user_preferences['frequent_apps'][app] = \
                self.user_preferences['frequent_apps'].get(app, 0) + 1
        
        if 'time_of_day' in context:
            hour = datetime.now().hour
            period = 'morning' if hour < 12 else 'afternoon' if hour < 18 else 'evening'
            self.user_preferences['active_periods'] = period
    
    def predict_action(self, user_input: str) -> Optional[Tuple[str, float]]:
        """Predict most likely action for input."""
        pattern = self._extract_pattern(user_input)
        
        if pattern in self.patterns:
            p = self.patterns[pattern]
            if p.confidence > 0.3:
                return (p.action, p.confidence)
        
        # Try partial matches
        best_match = None
        best_score = 0
        
        for patt, learned in self.patterns.items():
            # Simple overlap score
            words_input = set(pattern.split())
            words_pattern = set(patt.split())
            overlap = len(words_input & words_pattern) / max(len(words_input), 1)
            
            score = overlap * learned.confidence
            if score > best_score and score > 0.2:
                best_match = (learned.action, score)
                best_score = score
        
        return best_match
    
    def get_user_insight(self) -> Dict[str, Any]:
        """Get insights about user behavior."""
        insights = {
            'total_interactions': len(self.interaction_history),
            'patterns_learned': len(self.patterns),
            'top_patterns': [],
            'preferences': self.user_preferences
        }
        
        # Top patterns by confidence
        sorted_patterns = sorted(
            self.patterns.values(), 
            key=lambda p: p.confidence * p.occurrences,
            reverse=True
        )[:5]
        
        for p in sorted_patterns:
            insights['top_patterns'].append({
                'pattern': p.pattern,
                'action': p.action,
                'times_used': p.occurrences
            })
        
        return insights


# ============================================================================
# SELF-REFLECTION ENGINE
# ============================================================================

class SelfReflection:
    """
    VoxMind's ability to introspect and report on itself.
    
    "Let me tell you about myself"
    """
    
    def __init__(self, capabilities: CapabilityRegistry, 
                 performance: PerformanceTracker,
                 learning: LearningEngine):
        self.capabilities = capabilities
        self.performance = performance
        self.learning = learning
        self._start_time = time.time()
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status report."""
        uptime = time.time() - self._start_time
        
        return {
            'identity': {
                'name': 'VoxMind',
                'version': '2.0.0',
                'type': 'AI Assistant (Not Conscious)',
            },
            'uptime': {
                'seconds': uptime,
                'formatted': str(timedelta(seconds=int(uptime)))
            },
            'health': self._get_health(),
            'capabilities': {
                'total': len(self.capabilities.capabilities),
                'categories': list(set(
                    c.category for c in self.capabilities.capabilities.values()
                )),
                'known_limitations': len(self.capabilities.limitations)
            },
            'learning': {
                'patterns_learned': len(self.learning.patterns),
                'interactions_recorded': len(self.learning.interaction_history)
            },
            'system': self._get_system_status()
        }
    
    def _get_health(self) -> Dict[str, Any]:
        """Assess overall health."""
        perf = self.performance.get_summary()
        
        # Calculate health score
        issues = []
        
        success_rate = perf.get('command_success_rate', {}).get('current', 100)
        if success_rate < 80:
            issues.append(f"Command success rate is {success_rate:.0f}%")
        
        response_time = perf.get('response_time', {}).get('current', 0)
        if response_time > 2000:  # > 2 seconds
            issues.append(f"Response time is slow ({response_time:.0f}ms)")
        
        if issues:
            health = 'degraded'
        else:
            health = 'healthy'
        
        return {
            'status': health,
            'issues': issues
        }
    
    def _get_system_status(self) -> Dict[str, Any]:
        """Get system resource status."""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent
            }
        except Exception:
            return {'error': 'Could not get system status'}
    
    def introspect(self, query: str) -> str:
        """
        Answer questions about self.
        
        "What are you?", "What can you do?", "How are you doing?"
        """
        query_lower = query.lower()
        
        # Identity questions
        if any(w in query_lower for w in ['what are you', 'who are you', 'tell me about yourself']):
            return self._describe_self()
        
        # Capability questions
        if any(w in query_lower for w in ['what can you do', 'capabilities', 'features']):
            return self._describe_capabilities()
        
        # Limitation questions
        if any(w in query_lower for w in ["can't", 'cannot', 'limitation', 'unable']):
            return self._describe_limitations()
        
        # Health/status questions
        if any(w in query_lower for w in ['how are you', 'status', 'health']):
            return self._describe_status()
        
        # Can you do X?
        if 'can you' in query_lower:
            specific_task = query_lower.split('can you', 1)[1].strip()
            can_do, explanation = self.capabilities.can_do(specific_task)
            return explanation
        
        return "I'm not sure what you're asking about me. Try 'What can you do?' or 'How are you?'"
    
    def _describe_self(self) -> str:
        """Describe what VoxMind is."""
        return (
            "I am VoxMind, a voice-controlled AI assistant. "
            "I can help you with tasks like opening apps, searching the web, "
            "managing files, and answering questions. "
            "While I try to be helpful and seem intelligent, I want to be clear: "
            "I am not conscious or self-aware in the human sense. "
            "I'm a sophisticated pattern-matching system that learns from our interactions. "
            "Think of me as a very advanced tool that can understand natural language."
        )
    
    def _describe_capabilities(self) -> str:
        """Describe what VoxMind can do."""
        categories = defaultdict(list)
        for cap in self.capabilities.capabilities.values():
            categories[cap.category].append(cap.name.replace('_', ' '))
        
        parts = ["Here's what I can help you with:"]
        for cat, items in categories.items():
            parts.append(f"\n{cat.title()}: {', '.join(items)}")
        
        return ''.join(parts)
    
    def _describe_limitations(self) -> str:
        """Describe what VoxMind cannot do."""
        key_limitations = [
            "I cannot truly understand like a human - I recognize patterns",
            "I'm not conscious or self-aware",
            "I can't interact with the physical world",
            "I need an internet connection for web searches",
            "I can't update or improve my own code",
            "Some system operations require administrator access"
        ]
        
        return "To be transparent about my limitations:\n" + \
               "\n".join(f"• {lim}" for lim in key_limitations)
    
    def _describe_status(self) -> str:
        """Describe current status."""
        status = self.get_status()
        health = status['health']['status']
        uptime = status['uptime']['formatted']
        
        if health == 'healthy':
            base = f"I'm running well. Uptime: {uptime}. "
        else:
            issues = ', '.join(status['health']['issues'])
            base = f"I'm operational but experiencing some issues: {issues}. "
        
        learning = status['learning']
        base += f"I've learned {learning['patterns_learned']} patterns from " \
                f"{learning['interactions_recorded']} interactions."
        
        return base


# ============================================================================
# SELF-AWARE VOXMIND (Main Class)
# ============================================================================

class SelfAwareVoxMind:
    """
    VoxMind with self-monitoring, capability awareness, and learning.
    
    This is the "appears self-aware" layer on top of VoxMind Core.
    """
    
    def __init__(self):
        self.capabilities = CapabilityRegistry()
        self.performance = PerformanceTracker()
        self.learning = LearningEngine()
        self.reflection = SelfReflection(
            self.capabilities, 
            self.performance, 
            self.learning
        )
        
        self._voxmind_core = None  # Will be set if integrated
    
    async def process_with_awareness(self, user_input: str, 
                                     context: Dict = None) -> Dict[str, Any]:
        """
        Process a request with full self-awareness.
        """
        start_time = time.time()
        
        # Check if this is a question about VoxMind itself
        if self._is_introspective_query(user_input):
            response = self.reflection.introspect(user_input)
            return {
                'response': response,
                'type': 'introspection',
                'duration': time.time() - start_time
            }
        
        # Check if we've seen this pattern before
        prediction = self.learning.predict_action(user_input)
        
        # Process normally (would call VoxMind Core here)
        result = await self._process(user_input, context)
        
        # Record performance
        duration = (time.time() - start_time) * 1000
        self.performance.record('response_time', duration, 'ms')
        
        success = result.get('success', True)
        self.performance.record(
            'command_success_rate', 
            100 if success else 0, 
            '%'
        )
        
        # Learn from this interaction
        self.learning.learn_from_interaction(
            user_input,
            result.get('action', 'unknown'),
            success,
            context
        )
        
        # Update capability confidence
        if result.get('capability'):
            self.capabilities.update_confidence(
                result['capability'],
                success
            )
        
        return result
    
    def _is_introspective_query(self, text: str) -> bool:
        """Check if query is about VoxMind itself."""
        patterns = [
            r'what are you',
            r'who are you',
            r'tell me about yourself',
            r'what can you do',
            r'can you\s+\w+',
            r'your (capabilities|features|limitations)',
            r'how are you',
            r'are you (conscious|alive|real|ai)',
        ]
        
        text_lower = text.lower()
        import re
        return any(re.search(p, text_lower) for p in patterns)
    
    async def _process(self, user_input: str, context: Dict) -> Dict:
        """Process the actual request."""
        # Placeholder - would integrate with VoxMindCore
        return {
            'response': f"Processing: {user_input}",
            'success': True,
            'action': 'general',
            'capability': None
        }
    
    def get_self_report(self) -> str:
        """Generate a full self-report."""
        status = self.reflection.get_status()
        insights = self.learning.get_user_insight()
        
        report = [
            "=" * 50,
            "VOXMIND SELF-REPORT",
            "=" * 50,
            "",
            f"Identity: {status['identity']['name']} v{status['identity']['version']}",
            f"Type: {status['identity']['type']}",
            f"Uptime: {status['uptime']['formatted']}",
            "",
            f"Health: {status['health']['status'].upper()}",
        ]
        
        if status['health']['issues']:
            report.append("Issues:")
            for issue in status['health']['issues']:
                report.append(f"  - {issue}")
        
        report.extend([
            "",
            f"Capabilities: {status['capabilities']['total']} across "
            f"{len(status['capabilities']['categories'])} categories",
            f"Known Limitations: {status['capabilities']['known_limitations']}",
            "",
            f"Learning Status:",
            f"  - Patterns Learned: {insights['patterns_learned']}",
            f"  - Total Interactions: {insights['total_interactions']}",
        ])
        
        if insights['top_patterns']:
            report.append("  - Most Used Patterns:")
            for p in insights['top_patterns'][:3]:
                report.append(f"    • \"{p['pattern']}\" → {p['action']} ({p['times_used']}x)")
        
        report.extend([
            "",
            f"System Resources:",
            f"  - CPU: {status['system'].get('cpu_percent', 'N/A')}%",
            f"  - Memory: {status['system'].get('memory_percent', 'N/A')}%",
            "",
            "=" * 50
        ])
        
        return "\n".join(report)


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate self-awareness features."""
    print("=" * 60)
    print("VOXMIND SELF-AWARENESS DEMO")
    print("=" * 60)
    
    voxmind = SelfAwareVoxMind()
    
    # Simulate some interactions to build learning
    test_interactions = [
        ("open chrome", "app_control", True),
        ("search for python tutorials", "web_search", True),
        ("what's the weather", "weather", True),
        ("open chrome", "app_control", True),
        ("calculate 25 * 4", "calculator", True),
    ]
    
    for text, action, success in test_interactions:
        voxmind.learning.learn_from_interaction(text, action, success)
    
    print("\n--- Introspection Queries ---\n")
    
    queries = [
        "What are you?",
        "What can you do?",
        "Can you browse the internet?",
        "Can you feel emotions?",
        "How are you doing?",
    ]
    
    for query in queries:
        print(f"👤 User: {query}")
        result = await voxmind.process_with_awareness(query)
        print(f"🤖 VoxMind: {result['response']}")
        print()
    
    print("\n--- Self-Report ---\n")
    print(voxmind.get_self_report())


if __name__ == "__main__":
    asyncio.run(demo())
