"""
VoxMind Performance Analytics Module
=====================================
Statistical analysis tools to measure and track VoxMind's performance index.

Metrics Tracked:
- Command recognition accuracy
- Response time (latency)
- Success/failure rates
- Wake word detection accuracy
- Session statistics
- Command category performance
- User interaction patterns
"""

import time
import json
import statistics
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from pathlib import Path
import threading
import numpy as np


def json_serializable(obj):
    """Convert numpy types to Python native types for JSON serialization."""
    if isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [json_serializable(i) for i in obj]
    return obj


@dataclass
class CommandMetric:
    """Single command execution metric."""
    timestamp: float
    command_text: str
    command_type: str
    category: str
    success: bool
    response_time_ms: float
    confidence: float = 1.0
    error_message: str = ""
    retries: int = 0


@dataclass
class SessionMetric:
    """Session-level metrics."""
    session_id: str
    start_time: float
    end_time: float = 0
    total_commands: int = 0
    successful_commands: int = 0
    failed_commands: int = 0
    wake_word_attempts: int = 0
    wake_word_successes: int = 0
    avg_response_time_ms: float = 0
    categories_used: Dict[str, int] = field(default_factory=dict)


@dataclass
class PerformanceIndex:
    """Overall performance index calculation."""
    overall_score: float  # 0-100
    accuracy_score: float  # Command success rate
    speed_score: float  # Response time score
    reliability_score: float  # Consistency score
    wake_word_score: float  # Wake word detection accuracy
    category_scores: Dict[str, float] = field(default_factory=dict)
    grade: str = "A"  # A, B, C, D, F
    
    def to_dict(self) -> dict:
        return asdict(self)


class PerformanceAnalytics:
    """
    VoxMind Performance Analytics Engine.
    
    Tracks, analyzes, and reports on VoxMind's performance metrics.
    """
    
    # Performance thresholds
    EXCELLENT_RESPONSE_MS = 500
    GOOD_RESPONSE_MS = 1000
    ACCEPTABLE_RESPONSE_MS = 2000
    
    # Category weights for scoring
    CATEGORY_WEIGHTS = {
        'browser': 1.0,
        'search': 1.0,
        'time': 0.8,
        'media': 1.0,
        'volume': 0.9,
        'brightness': 0.9,
        'app_control': 1.2,
        'window': 1.1,
        'mouse': 1.3,
        'keyboard': 1.2,
        'screen': 1.3,
        'monitor': 1.0,
        'system': 1.0,
        'help': 0.5,
        'unknown': 0.3
    }
    
    def __init__(self, data_dir: str = "data/analytics"):
        """Initialize performance analytics."""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Current session
        self.current_session: Optional[SessionMetric] = None
        self.session_commands: List[CommandMetric] = []
        
        # Historical data
        self.all_sessions: List[SessionMetric] = []
        self.all_commands: List[CommandMetric] = []
        
        # Real-time tracking
        self._command_start_time: float = 0
        self._lock = threading.Lock()
        
        # Load historical data
        self._load_historical_data()
    
    def _load_historical_data(self):
        """Load historical analytics data."""
        try:
            sessions_file = self.data_dir / "sessions.json"
            if sessions_file.exists():
                with open(sessions_file, 'r') as f:
                    data = json.load(f)
                    self.all_sessions = [
                        SessionMetric(**s) for s in data.get('sessions', [])
                    ]
            
            commands_file = self.data_dir / "commands.json"
            if commands_file.exists():
                with open(commands_file, 'r') as f:
                    data = json.load(f)
                    # Only load last 10000 commands to save memory
                    self.all_commands = [
                        CommandMetric(**c) for c in data.get('commands', [])[-10000:]
                    ]
        except Exception as e:
            print(f"[Analytics] Error loading historical data: {e}")
    
    def _save_data(self):
        """Save analytics data to disk."""
        try:
            # Save sessions - convert numpy types
            sessions_file = self.data_dir / "sessions.json"
            sessions_data = [json_serializable(asdict(s)) for s in self.all_sessions[-1000:]]
            with open(sessions_file, 'w') as f:
                json.dump({'sessions': sessions_data}, f, indent=2)
            
            # Save commands - convert numpy types
            commands_file = self.data_dir / "commands.json"
            commands_data = [json_serializable(asdict(c)) for c in self.all_commands[-10000:]]
            with open(commands_file, 'w') as f:
                json.dump({'commands': commands_data}, f, indent=2)
        except Exception as e:
            print(f"[Analytics] Error saving data: {e}")
    
    # =========================================================================
    # Session Management
    # =========================================================================
    
    def start_session(self) -> str:
        """Start a new analytics session."""
        session_id = f"session_{int(time.time())}_{id(self)}"
        
        self.current_session = SessionMetric(
            session_id=session_id,
            start_time=time.time()
        )
        self.session_commands = []
        
        print(f"[Analytics] Session started: {session_id}")
        return session_id
    
    def end_session(self) -> Optional[SessionMetric]:
        """End current session and calculate metrics."""
        if not self.current_session:
            return None
        
        self.current_session.end_time = time.time()
        
        # Calculate session metrics
        if self.session_commands:
            response_times = [c.response_time_ms for c in self.session_commands]
            self.current_session.avg_response_time_ms = statistics.mean(response_times)
            
            # Count categories
            for cmd in self.session_commands:
                cat = cmd.category
                self.current_session.categories_used[cat] = \
                    self.current_session.categories_used.get(cat, 0) + 1
        
        # Store session
        self.all_sessions.append(self.current_session)
        self.all_commands.extend(self.session_commands)
        
        # Save to disk
        self._save_data()
        
        session = self.current_session
        self.current_session = None
        self.session_commands = []
        
        print(f"[Analytics] Session ended. Commands: {session.total_commands}, "
              f"Success rate: {self._calc_success_rate(session):.1f}%")
        
        return session
    
    def _calc_success_rate(self, session: SessionMetric) -> float:
        """Calculate success rate for a session."""
        if session.total_commands == 0:
            return 100.0
        return (session.successful_commands / session.total_commands) * 100
    
    # =========================================================================
    # Command Tracking
    # =========================================================================
    
    def start_command(self):
        """Mark the start of command processing."""
        self._command_start_time = time.time()
    
    def record_command(
        self,
        command_text: str,
        command_type: str,
        category: str,
        success: bool,
        confidence: float = 1.0,
        error_message: str = "",
        retries: int = 0
    ) -> CommandMetric:
        """Record a command execution."""
        
        # Calculate response time
        if self._command_start_time:
            response_time_ms = (time.time() - self._command_start_time) * 1000
        else:
            response_time_ms = 0
        
        metric = CommandMetric(
            timestamp=time.time(),
            command_text=command_text,
            command_type=command_type,
            category=category,
            success=success,
            response_time_ms=response_time_ms,
            confidence=confidence,
            error_message=error_message,
            retries=retries
        )
        
        # Update session
        with self._lock:
            if self.current_session:
                self.current_session.total_commands += 1
                if success:
                    self.current_session.successful_commands += 1
                else:
                    self.current_session.failed_commands += 1
            
            self.session_commands.append(metric)
        
        self._command_start_time = 0
        return metric
    
    def record_wake_word(self, success: bool):
        """Record wake word detection attempt."""
        if self.current_session:
            self.current_session.wake_word_attempts += 1
            if success:
                self.current_session.wake_word_successes += 1
    
    # =========================================================================
    # Performance Index Calculation
    # =========================================================================
    
    def calculate_performance_index(
        self,
        timeframe_hours: int = 24
    ) -> PerformanceIndex:
        """
        Calculate comprehensive performance index.
        
        Args:
            timeframe_hours: Hours of data to analyze (default 24)
        
        Returns:
            PerformanceIndex with scores 0-100
        """
        cutoff_time = time.time() - (timeframe_hours * 3600)
        
        # Filter relevant commands
        recent_commands = [
            c for c in (self.all_commands + self.session_commands)
            if c.timestamp >= cutoff_time
        ]
        
        recent_sessions = [
            s for s in self.all_sessions
            if s.start_time >= cutoff_time
        ]
        if self.current_session:
            recent_sessions.append(self.current_session)
        
        if not recent_commands:
            return PerformanceIndex(
                overall_score=100.0,
                accuracy_score=100.0,
                speed_score=100.0,
                reliability_score=100.0,
                wake_word_score=100.0,
                grade="A"
            )
        
        # 1. Accuracy Score (command success rate)
        total = len(recent_commands)
        successful = sum(1 for c in recent_commands if c.success)
        accuracy_score = (successful / total) * 100 if total > 0 else 100
        
        # 2. Speed Score (response time)
        response_times = [c.response_time_ms for c in recent_commands if c.response_time_ms > 0]
        if response_times:
            avg_response = statistics.mean(response_times)
            if avg_response <= self.EXCELLENT_RESPONSE_MS:
                speed_score = 100
            elif avg_response <= self.GOOD_RESPONSE_MS:
                speed_score = 90 - ((avg_response - self.EXCELLENT_RESPONSE_MS) / 50)
            elif avg_response <= self.ACCEPTABLE_RESPONSE_MS:
                speed_score = 70 - ((avg_response - self.GOOD_RESPONSE_MS) / 100)
            else:
                speed_score = max(30, 50 - ((avg_response - self.ACCEPTABLE_RESPONSE_MS) / 200))
        else:
            speed_score = 100
        
        # 3. Reliability Score (consistency - low variance)
        # Also factor in command confidence scores for reliability
        if len(response_times) >= 3:
            try:
                stdev = statistics.stdev(response_times)
                mean_time = statistics.mean(response_times)
                cv = stdev / mean_time if mean_time > 0 else 0
                # CV is typically 0-2, map to score (lower CV = higher reliability)
                time_consistency = max(0, 100 - (cv * 50))  # Less aggressive penalty
                
                # Factor in confidence scores
                confidences = [c.confidence for c in recent_commands if c.confidence > 0]
                avg_confidence = statistics.mean(confidences) if confidences else 0.8
                confidence_score = avg_confidence * 100
                
                # Blend time consistency and confidence
                reliability_score = (time_consistency * 0.4) + (confidence_score * 0.6)
            except (ValueError, statistics.StatisticsError, ZeroDivisionError):
                reliability_score = 80
        else:
            reliability_score = 85
        
        # 4. Wake Word Score
        total_wake = sum(s.wake_word_attempts for s in recent_sessions)
        success_wake = sum(s.wake_word_successes for s in recent_sessions)
        wake_word_score = (success_wake / total_wake) * 100 if total_wake > 0 else 100
        
        # 5. Category Scores
        category_scores = {}
        categories = defaultdict(list)
        for cmd in recent_commands:
            categories[cmd.category].append(cmd)
        
        for cat, commands in categories.items():
            cat_success = sum(1 for c in commands if c.success)
            cat_total = len(commands)
            category_scores[cat] = (cat_success / cat_total) * 100 if cat_total > 0 else 100
        
        # 6. Overall Score (weighted average)
        weights = {
            'accuracy': 0.35,
            'speed': 0.25,
            'reliability': 0.20,
            'wake_word': 0.20
        }
        
        overall_score = (
            accuracy_score * weights['accuracy'] +
            speed_score * weights['speed'] +
            reliability_score * weights['reliability'] +
            wake_word_score * weights['wake_word']
        )
        
        # Determine grade
        if overall_score >= 90:
            grade = "A"
        elif overall_score >= 80:
            grade = "B"
        elif overall_score >= 70:
            grade = "C"
        elif overall_score >= 60:
            grade = "D"
        else:
            grade = "F"
        
        return PerformanceIndex(
            overall_score=round(overall_score, 1),
            accuracy_score=round(accuracy_score, 1),
            speed_score=round(speed_score, 1),
            reliability_score=round(reliability_score, 1),
            wake_word_score=round(wake_word_score, 1),
            category_scores={k: round(v, 1) for k, v in category_scores.items()},
            grade=grade
        )
    
    # =========================================================================
    # Statistical Analysis
    # =========================================================================
    
    def get_response_time_stats(
        self,
        timeframe_hours: int = 24
    ) -> Dict[str, float]:
        """Get response time statistics."""
        cutoff_time = time.time() - (timeframe_hours * 3600)
        
        times = [
            c.response_time_ms
            for c in (self.all_commands + self.session_commands)
            if c.timestamp >= cutoff_time and c.response_time_ms > 0
        ]
        
        if not times:
            return {
                'count': 0,
                'mean': 0,
                'median': 0,
                'min': 0,
                'max': 0,
                'stdev': 0,
                'p95': 0,
                'p99': 0
            }
        
        sorted_times = sorted(times)
        
        return {
            'count': len(times),
            'mean': round(statistics.mean(times), 2),
            'median': round(statistics.median(times), 2),
            'min': round(min(times), 2),
            'max': round(max(times), 2),
            'stdev': round(statistics.stdev(times), 2) if len(times) > 1 else 0,
            'p95': round(sorted_times[int(len(sorted_times) * 0.95)], 2),
            'p99': round(sorted_times[int(len(sorted_times) * 0.99)], 2)
        }
    
    def get_category_breakdown(
        self,
        timeframe_hours: int = 24
    ) -> Dict[str, Dict[str, Any]]:
        """Get performance breakdown by category."""
        cutoff_time = time.time() - (timeframe_hours * 3600)
        
        categories = defaultdict(lambda: {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'response_times': [],
            'errors': []
        })
        
        for cmd in (self.all_commands + self.session_commands):
            if cmd.timestamp < cutoff_time:
                continue
            
            cat = categories[cmd.category]
            cat['total'] += 1
            if cmd.success:
                cat['successful'] += 1
            else:
                cat['failed'] += 1
                if cmd.error_message:
                    cat['errors'].append(cmd.error_message)
            
            if cmd.response_time_ms > 0:
                cat['response_times'].append(cmd.response_time_ms)
        
        # Calculate stats for each category
        result = {}
        for cat_name, data in categories.items():
            result[cat_name] = {
                'total': data['total'],
                'successful': data['successful'],
                'failed': data['failed'],
                'success_rate': round((data['successful'] / data['total']) * 100, 1) if data['total'] > 0 else 100,
                'avg_response_ms': round(statistics.mean(data['response_times']), 2) if data['response_times'] else 0,
                'common_errors': list(set(data['errors']))[:5]
            }
        
        return result
    
    def get_trend_analysis(
        self,
        days: int = 7
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get performance trends over time."""
        now = time.time()
        trends = {
            'daily_scores': [],
            'daily_commands': [],
            'daily_response_times': []
        }
        
        for day in range(days, 0, -1):
            day_start = now - (day * 86400)
            day_end = now - ((day - 1) * 86400)
            
            day_commands = [
                c for c in self.all_commands
                if day_start <= c.timestamp < day_end
            ]
            
            if day_commands:
                successful = sum(1 for c in day_commands if c.success)
                response_times = [c.response_time_ms for c in day_commands if c.response_time_ms > 0]
                
                trends['daily_scores'].append({
                    'date': datetime.fromtimestamp(day_start).strftime('%Y-%m-%d'),
                    'success_rate': round((successful / len(day_commands)) * 100, 1)
                })
                
                trends['daily_commands'].append({
                    'date': datetime.fromtimestamp(day_start).strftime('%Y-%m-%d'),
                    'total': len(day_commands),
                    'successful': successful,
                    'failed': len(day_commands) - successful
                })
                
                trends['daily_response_times'].append({
                    'date': datetime.fromtimestamp(day_start).strftime('%Y-%m-%d'),
                    'avg_ms': round(statistics.mean(response_times), 2) if response_times else 0
                })
        
        return trends
    
    def get_error_analysis(
        self,
        timeframe_hours: int = 24
    ) -> Dict[str, Any]:
        """Analyze errors and failure patterns."""
        cutoff_time = time.time() - (timeframe_hours * 3600)
        
        failed_commands = [
            c for c in (self.all_commands + self.session_commands)
            if c.timestamp >= cutoff_time and not c.success
        ]
        
        if not failed_commands:
            return {
                'total_failures': 0,
                'failure_rate': 0,
                'by_category': {},
                'common_errors': [],
                'retry_stats': {'total_retries': 0, 'avg_retries': 0}
            }
        
        total_commands = len([
            c for c in (self.all_commands + self.session_commands)
            if c.timestamp >= cutoff_time
        ])
        
        # Group by category
        by_category = defaultdict(int)
        errors = []
        retries = []
        
        for cmd in failed_commands:
            by_category[cmd.category] += 1
            if cmd.error_message:
                errors.append(cmd.error_message)
            retries.append(cmd.retries)
        
        # Count error frequencies
        error_counts = defaultdict(int)
        for err in errors:
            error_counts[err] += 1
        common_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_failures': len(failed_commands),
            'failure_rate': round((len(failed_commands) / total_commands) * 100, 2) if total_commands > 0 else 0,
            'by_category': dict(by_category),
            'common_errors': [{'error': e, 'count': c} for e, c in common_errors],
            'retry_stats': {
                'total_retries': sum(retries),
                'avg_retries': round(statistics.mean(retries), 2) if retries else 0
            }
        }
    
    # =========================================================================
    # Reports
    # =========================================================================
    
    def generate_report(
        self,
        timeframe_hours: int = 24,
        include_trends: bool = True
    ) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        
        perf_index = self.calculate_performance_index(timeframe_hours)
        response_stats = self.get_response_time_stats(timeframe_hours)
        category_breakdown = self.get_category_breakdown(timeframe_hours)
        error_analysis = self.get_error_analysis(timeframe_hours)
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'timeframe_hours': timeframe_hours,
            'performance_index': perf_index.to_dict(),
            'response_time_stats': response_stats,
            'category_breakdown': category_breakdown,
            'error_analysis': error_analysis
        }
        
        if include_trends:
            report['trends'] = self.get_trend_analysis(7)
        
        return report
    
    def print_summary(self, timeframe_hours: int = 24):
        """Print a human-readable performance summary."""
        perf = self.calculate_performance_index(timeframe_hours)
        stats = self.get_response_time_stats(timeframe_hours)
        
        print("\n" + "=" * 60)
        print("📊 VOXMIND PERFORMANCE INDEX")
        print("=" * 60)
        print(f"\n🎯 Overall Score: {perf.overall_score}/100 (Grade: {perf.grade})")
        print(f"\n📈 Component Scores:")
        print(f"   • Accuracy:    {perf.accuracy_score}%")
        print(f"   • Speed:       {perf.speed_score}%")
        print(f"   • Reliability: {perf.reliability_score}%")
        print(f"   • Wake Word:   {perf.wake_word_score}%")
        
        print(f"\n⏱️ Response Time Statistics:")
        print(f"   • Mean:   {stats['mean']:.0f}ms")
        print(f"   • Median: {stats['median']:.0f}ms")
        print(f"   • P95:    {stats['p95']:.0f}ms")
        print(f"   • P99:    {stats['p99']:.0f}ms")
        
        if perf.category_scores:
            print(f"\n📁 Category Performance:")
            for cat, score in sorted(perf.category_scores.items(), key=lambda x: x[1]):
                bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
                print(f"   • {cat:15} [{bar}] {score}%")
        
        print("\n" + "=" * 60)
        return perf


# Singleton instance
_analytics: Optional[PerformanceAnalytics] = None


def get_analytics() -> PerformanceAnalytics:
    """Get the global analytics instance."""
    global _analytics
    if _analytics is None:
        _analytics = PerformanceAnalytics()
    return _analytics


# =========================================================================
# Demo / Test
# =========================================================================

if __name__ == "__main__":
    import random
    
    print("VoxMind Performance Analytics Demo")
    print("=" * 50)
    
    analytics = get_analytics()
    
    # Simulate a session
    analytics.start_session()
    
    # Simulate wake word detection
    for _ in range(5):
        analytics.record_wake_word(random.random() > 0.1)  # 90% success
    
    # Simulate various commands
    test_commands = [
        ("open chrome", "open", "browser", True),
        ("what time is it", "time", "time", True),
        ("search for weather", "search", "search", True),
        ("play music", "play", "media", True),
        ("volume up", "volume", "volume", True),
        ("snap left", "snap", "window", True),
        ("click", "click", "mouse", True),
        ("type hello", "type", "keyboard", True),
        ("what's on screen", "describe", "screen", True),
        ("open unknown app", "open", "app_control", False),
        ("move mouse left", "move", "mouse", True),
        ("close notepad", "close", "app_control", True),
    ]
    
    for cmd_text, cmd_type, category, success in test_commands:
        analytics.start_command()
        time.sleep(random.uniform(0.1, 0.5))  # Simulate processing
        analytics.record_command(
            command_text=cmd_text,
            command_type=cmd_type,
            category=category,
            success=success,
            confidence=random.uniform(0.7, 1.0),
            error_message="" if success else "Command failed"
        )
    
    # End session
    analytics.end_session()
    
    # Print summary
    analytics.print_summary(24)
    
    # Generate full report
    report = analytics.generate_report(24)
    print("\n📄 Full Report (JSON preview):")
    print(json.dumps(report, indent=2, default=str)[:1000] + "...")
