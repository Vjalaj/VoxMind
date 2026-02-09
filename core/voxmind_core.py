"""
VoxMind VoxMind Core
===================
A multi-agent orchestration system that creates a "intelligent" experience.

This is NOT conscious AI - it's a sophisticated automation system that:
- Runs multiple specialized agents in parallel
- Maintains long-term memory across sessions
- Proactively monitors and alerts
- Aggregates information from multiple sources
- Learns user preferences over time

"The appearance of intelligence through sophisticated orchestration"

Usage:
    voxmind = VoxMindCore()
    await voxmind.start()
    
    # Process a command (may trigger multiple agents)
    result = await voxmind.process("Research quantum computing while 
                                   checking my calendar for tomorrow")
    
    # VoxMind responds with aggregated results
    print(result.response)  # "I found 15 articles on quantum computing. 
                            #  Also, you have 3 meetings tomorrow..."
"""

import asyncio
import json
import time
import threading
import logging
import hashlib
import sqlite3
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Callable, Set, Tuple
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from abc import ABC, abstractmethod
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

logger = logging.getLogger('VoxMind.Core')


# ============================================================================
# MEMORY SYSTEM (Long-term, Episodic, Semantic)
# ============================================================================

class MemoryType(Enum):
    """Types of memory VoxMind maintains."""
    EPISODIC = "episodic"      # Specific events/conversations
    SEMANTIC = "semantic"       # Facts and knowledge
    PROCEDURAL = "procedural"   # How to do things
    PREFERENCE = "preference"   # User preferences


@dataclass
class Memory:
    """A single memory unit."""
    id: str
    type: MemoryType
    content: str
    context: Dict[str, Any]
    importance: float  # 0-1, affects retention
    timestamp: float
    access_count: int = 0
    last_accessed: float = 0
    embedding: Optional[List[float]] = None  # For semantic search


class MemoryStore:
    """
    Persistent memory store with semantic search.
    VoxMind remembers everything - conversations, facts, preferences.
    """
    
    def __init__(self, db_path: str = "data/voxmind_memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._embedding_model = None
        self._lock = threading.Lock()
    
    def _init_db(self):
        """Initialize SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    type TEXT,
                    content TEXT,
                    context TEXT,
                    importance REAL,
                    timestamp REAL,
                    access_count INTEGER,
                    last_accessed REAL,
                    embedding BLOB
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_type ON memories(type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON memories(timestamp)
            """)
    
    def store(self, memory: Memory):
        """Store a memory."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO memories 
                    (id, type, content, context, importance, timestamp, 
                     access_count, last_accessed, embedding)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    memory.id,
                    memory.type.value,
                    memory.content,
                    json.dumps(memory.context),
                    memory.importance,
                    memory.timestamp,
                    memory.access_count,
                    memory.last_accessed,
                    json.dumps(memory.embedding) if memory.embedding else None
                ))
    
    def recall(self, query: str, memory_type: MemoryType = None, 
               limit: int = 10) -> List[Memory]:
        """Recall memories matching a query."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                if memory_type:
                    rows = conn.execute("""
                        SELECT * FROM memories 
                        WHERE type = ? AND content LIKE ?
                        ORDER BY importance DESC, timestamp DESC
                        LIMIT ?
                    """, (memory_type.value, f"%{query}%", limit)).fetchall()
                else:
                    rows = conn.execute("""
                        SELECT * FROM memories 
                        WHERE content LIKE ?
                        ORDER BY importance DESC, timestamp DESC
                        LIMIT ?
                    """, (f"%{query}%", limit)).fetchall()
                
                return [self._row_to_memory(row) for row in rows]
    
    def get_recent(self, hours: int = 24, limit: int = 50) -> List[Memory]:
        """Get recent memories."""
        cutoff = time.time() - (hours * 3600)
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT * FROM memories 
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (cutoff, limit)).fetchall()
                return [self._row_to_memory(row) for row in rows]
    
    def get_preferences(self) -> Dict[str, Any]:
        """Get all user preferences."""
        memories = self.recall("", MemoryType.PREFERENCE, limit=100)
        prefs = {}
        for mem in memories:
            prefs.update(mem.context)
        return prefs
    
    def _row_to_memory(self, row) -> Memory:
        """Convert database row to Memory object."""
        return Memory(
            id=row[0],
            type=MemoryType(row[1]),
            content=row[2],
            context=json.loads(row[3]),
            importance=row[4],
            timestamp=row[5],
            access_count=row[6],
            last_accessed=row[7],
            embedding=json.loads(row[8]) if row[8] else None
        )
    
    def remember_conversation(self, user_input: str, response: str, 
                              intent: str = None):
        """Remember a conversation turn."""
        memory = Memory(
            id=hashlib.md5(f"{time.time()}{user_input}".encode()).hexdigest(),
            type=MemoryType.EPISODIC,
            content=f"User: {user_input}\nvoxmind: {response}",
            context={"intent": intent, "user_input": user_input},
            importance=0.5,
            timestamp=time.time()
        )
        self.store(memory)
    
    def remember_fact(self, fact: str, source: str = None, importance: float = 0.6):
        """Remember a fact/piece of knowledge."""
        memory = Memory(
            id=hashlib.md5(fact.encode()).hexdigest(),
            type=MemoryType.SEMANTIC,
            content=fact,
            context={"source": source},
            importance=importance,
            timestamp=time.time()
        )
        self.store(memory)
    
    def remember_preference(self, key: str, value: Any):
        """Remember a user preference."""
        memory = Memory(
            id=hashlib.md5(f"pref:{key}".encode()).hexdigest(),
            type=MemoryType.PREFERENCE,
            content=f"User prefers {key}: {value}",
            context={key: value},
            importance=0.8,
            timestamp=time.time()
        )
        self.store(memory)


# ============================================================================
# AGENT SYSTEM (Specialized workers)
# ============================================================================

class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentTask:
    """A task for an agent to execute."""
    id: str
    type: str
    params: Dict[str, Any]
    priority: int = 5  # 1=highest
    created_at: float = field(default_factory=time.time)
    deadline: Optional[float] = None


@dataclass
class AgentResult:
    """Result from an agent."""
    task_id: str
    agent_name: str
    success: bool
    data: Any
    error: Optional[str] = None
    duration: float = 0
    

class BaseAgent(ABC):
    """Base class for all VoxMind agents."""
    
    def __init__(self, name: str, voxmind: 'VoxMindCore'):
        self.name = name
        self.voxmind = voxmind
        self.status = AgentStatus.IDLE
        self._running = False
    
    @abstractmethod
    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute a task. Override in subclasses."""
        pass
    
    @abstractmethod
    def can_handle(self, task_type: str) -> bool:
        """Check if this agent can handle a task type."""
        pass


class WebSearchAgent(BaseAgent):
    """Agent for web searches and information retrieval."""
    
    def __init__(self, voxmind: 'VoxMindCore'):
        super().__init__("WebSearch", voxmind)
        self._search_engines = ['duckduckgo', 'google', 'bing']
    
    def can_handle(self, task_type: str) -> bool:
        return task_type in ('web_search', 'research', 'lookup', 'find_info')
    
    async def execute(self, task: AgentTask) -> AgentResult:
        start = time.time()
        self.status = AgentStatus.RUNNING
        
        try:
            query = task.params.get('query', '')
            
            # Try DuckDuckGo (no API key needed)
            results = await self._search_duckduckgo(query)
            
            self.status = AgentStatus.COMPLETED
            return AgentResult(
                task_id=task.id,
                agent_name=self.name,
                success=True,
                data={'query': query, 'results': results},
                duration=time.time() - start
            )
        except Exception as e:
            self.status = AgentStatus.FAILED
            return AgentResult(
                task_id=task.id,
                agent_name=self.name,
                success=False,
                data=None,
                error=str(e),
                duration=time.time() - start
            )
    
    async def _search_duckduckgo(self, query: str) -> List[Dict]:
        """Search using DuckDuckGo Instant Answer API."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url = "https://api.duckduckgo.com/"
                params = {'q': query, 'format': 'json', 'no_html': 1}
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = []
                        
                        # Abstract (main answer)
                        if data.get('Abstract'):
                            results.append({
                                'title': data.get('Heading', 'Answer'),
                                'snippet': data['Abstract'],
                                'url': data.get('AbstractURL', ''),
                                'source': data.get('AbstractSource', '')
                            })
                        
                        # Related topics
                        for topic in data.get('RelatedTopics', [])[:5]:
                            if isinstance(topic, dict) and 'Text' in topic:
                                results.append({
                                    'title': topic.get('Text', '')[:100],
                                    'snippet': topic.get('Text', ''),
                                    'url': topic.get('FirstURL', '')
                                })
                        
                        return results
        except ImportError:
            logger.warning("aiohttp not installed, using mock search")
        except Exception as e:
            logger.error(f"Search error: {e}")
        
        return [{'title': query, 'snippet': f'Search results for: {query}', 'url': ''}]


class SystemMonitorAgent(BaseAgent):
    """Agent that monitors system state and can act proactively."""
    
    def __init__(self, voxmind: 'VoxMindCore'):
        super().__init__("SystemMonitor", voxmind)
        self._monitors: Dict[str, Callable] = {}
        self._alerts: List[Dict] = []
    
    def can_handle(self, task_type: str) -> bool:
        return task_type in ('system_check', 'monitor', 'health_check')
    
    async def execute(self, task: AgentTask) -> AgentResult:
        start = time.time()
        self.status = AgentStatus.RUNNING
        
        try:
            check_type = task.params.get('check', 'all')
            results = {}
            
            if check_type in ('all', 'system'):
                results['system'] = await self._check_system()
            if check_type in ('all', 'battery'):
                results['battery'] = await self._check_battery()
            if check_type in ('all', 'disk'):
                results['disk'] = await self._check_disk()
            
            self.status = AgentStatus.COMPLETED
            return AgentResult(
                task_id=task.id,
                agent_name=self.name,
                success=True,
                data=results,
                duration=time.time() - start
            )
        except Exception as e:
            self.status = AgentStatus.FAILED
            return AgentResult(
                task_id=task.id,
                agent_name=self.name,
                success=False,
                data=None,
                error=str(e),
                duration=time.time() - start
            )
    
    async def _check_system(self) -> Dict:
        """Check system resources."""
        try:
            import psutil
            return {
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory_percent': psutil.virtual_memory().percent,
                'uptime_hours': (time.time() - psutil.boot_time()) / 3600
            }
        except ImportError:
            return {'error': 'psutil not available'}
    
    async def _check_battery(self) -> Dict:
        """Check battery status."""
        try:
            import psutil
            battery = psutil.sensors_battery()
            if battery:
                return {
                    'percent': battery.percent,
                    'plugged_in': battery.power_plugged,
                    'time_left_hours': battery.secsleft / 3600 if battery.secsleft > 0 else None
                }
            return {'available': False}
        except ImportError:
            return {'error': 'psutil not available'}
    
    async def _check_disk(self) -> Dict:
        """Check disk usage."""
        try:
            import psutil
            disk = psutil.disk_usage('/')
            return {
                'total_gb': disk.total / (1024**3),
                'used_gb': disk.used / (1024**3),
                'free_gb': disk.free / (1024**3),
                'percent': disk.percent
            }
        except ImportError:
            return {'error': 'psutil not available'}


class CalendarAgent(BaseAgent):
    """Agent for calendar/scheduling tasks."""
    
    def __init__(self, voxmind: 'VoxMindCore'):
        super().__init__("Calendar", voxmind)
        self._events: List[Dict] = []  # Simple in-memory for demo
    
    def can_handle(self, task_type: str) -> bool:
        return task_type in ('calendar', 'schedule', 'reminder', 'event')
    
    async def execute(self, task: AgentTask) -> AgentResult:
        start = time.time()
        self.status = AgentStatus.RUNNING
        
        try:
            action = task.params.get('action', 'list')
            
            if action == 'list':
                data = self._get_upcoming_events()
            elif action == 'add':
                data = self._add_event(task.params)
            elif action == 'check_tomorrow':
                data = self._get_tomorrow_events()
            else:
                data = {'events': []}
            
            self.status = AgentStatus.COMPLETED
            return AgentResult(
                task_id=task.id,
                agent_name=self.name,
                success=True,
                data=data,
                duration=time.time() - start
            )
        except Exception as e:
            self.status = AgentStatus.FAILED
            return AgentResult(
                task_id=task.id,
                agent_name=self.name,
                success=False,
                data=None,
                error=str(e),
                duration=time.time() - start
            )
    
    def _get_upcoming_events(self) -> Dict:
        """Get upcoming events."""
        now = datetime.now()
        upcoming = [e for e in self._events 
                    if datetime.fromisoformat(e['start']) > now]
        return {'events': upcoming[:10]}
    
    def _get_tomorrow_events(self) -> Dict:
        """Get tomorrow's events."""
        tomorrow = datetime.now() + timedelta(days=1)
        tomorrow_start = tomorrow.replace(hour=0, minute=0, second=0)
        tomorrow_end = tomorrow.replace(hour=23, minute=59, second=59)
        
        events = [e for e in self._events 
                  if tomorrow_start <= datetime.fromisoformat(e['start']) <= tomorrow_end]
        return {'events': events, 'date': tomorrow.strftime('%Y-%m-%d')}
    
    def _add_event(self, params: Dict) -> Dict:
        """Add an event."""
        event = {
            'id': hashlib.md5(f"{time.time()}".encode()).hexdigest()[:8],
            'title': params.get('title', 'Untitled'),
            'start': params.get('start', datetime.now().isoformat()),
            'end': params.get('end'),
            'description': params.get('description', '')
        }
        self._events.append(event)
        return {'added': event}


class TaskExecutionAgent(BaseAgent):
    """Agent for executing system tasks (apps, files, etc.)."""
    
    def __init__(self, voxmind: 'VoxMindCore'):
        super().__init__("TaskExecution", voxmind)
    
    def can_handle(self, task_type: str) -> bool:
        return task_type in ('open_app', 'run_command', 'file_operation', 
                            'execute', 'automation')
    
    async def execute(self, task: AgentTask) -> AgentResult:
        start = time.time()
        self.status = AgentStatus.RUNNING
        
        try:
            action = task.params.get('action', '')
            
            if action == 'open_app':
                result = await self._open_app(task.params.get('app', ''))
            elif action == 'run_command':
                result = await self._run_command(task.params.get('command', ''))
            else:
                result = {'status': 'unknown action'}
            
            self.status = AgentStatus.COMPLETED
            return AgentResult(
                task_id=task.id,
                agent_name=self.name,
                success=True,
                data=result,
                duration=time.time() - start
            )
        except Exception as e:
            self.status = AgentStatus.FAILED
            return AgentResult(
                task_id=task.id,
                agent_name=self.name,
                success=False,
                data=None,
                error=str(e),
                duration=time.time() - start
            )
    
    async def _open_app(self, app: str) -> Dict:
        """Open an application."""
        try:
            from core.app_control import get_app_controller
            controller = get_app_controller()
            success = controller.open_app(app)
            return {'app': app, 'opened': success}
        except ImportError:
            return {'app': app, 'error': 'app_control not available'}
    
    async def _run_command(self, command: str) -> Dict:
        """Run a shell command."""
        import subprocess
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, 
                text=True, timeout=30
            )
            return {
                'command': command,
                'stdout': result.stdout[:1000],
                'stderr': result.stderr[:500],
                'returncode': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {'command': command, 'error': 'timeout'}


# ============================================================================
# TASK DECOMPOSER (Break complex requests into sub-tasks)
# ============================================================================

class TaskDecomposer:
    """
    Breaks complex user requests into parallel sub-tasks.
    
    "Research AI while checking my calendar" becomes:
      - Task 1: WebSearch("AI research")
      - Task 2: Calendar(action="list")
    """
    
    # Patterns that indicate multiple tasks
    CONJUNCTIONS = ['while', 'and also', 'and then', 'also', 'plus', 'as well as']
    
    # Task type mappings
    TASK_PATTERNS = {
        'web_search': [
            r'research\s+(.+)', r'search\s+(?:for\s+)?(.+)', 
            r'look\s+up\s+(.+)', r'find\s+(?:info|information)\s+(?:about|on)\s+(.+)',
            r'what\s+is\s+(.+)', r'tell\s+me\s+about\s+(.+)'
        ],
        'calendar': [
            r'check\s+(?:my\s+)?calendar', r'what.*schedule',
            r'(?:my\s+)?meetings?\s+(?:today|tomorrow|this week)',
            r'(?:any\s+)?appointments?', r'(?:am\s+I\s+)?free\s+(?:today|tomorrow)'
        ],
        'system_check': [
            r'system\s+status', r'check\s+(?:the\s+)?(?:battery|disk|memory|cpu)',
            r'how.*(?:battery|storage|memory)'
        ],
        'open_app': [
            r'open\s+(.+)', r'launch\s+(.+)', r'start\s+(.+)'
        ],
        'reminder': [
            r'remind\s+me\s+(?:to\s+)?(.+)', r'set\s+(?:a\s+)?reminder\s+(.+)'
        ]
    }
    
    def decompose(self, text: str) -> List[AgentTask]:
        """Decompose a complex request into tasks."""
        tasks = []
        
        # Check for conjunctions that indicate multiple tasks
        parts = self._split_by_conjunctions(text)
        
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
            
            task = self._classify_task(part, i)
            if task:
                tasks.append(task)
        
        # If no tasks found, create a generic one
        if not tasks:
            tasks.append(AgentTask(
                id=hashlib.md5(f"{time.time()}{text}".encode()).hexdigest()[:8],
                type='unknown',
                params={'text': text}
            ))
        
        return tasks
    
    def _split_by_conjunctions(self, text: str) -> List[str]:
        """Split text by task-separating conjunctions."""
        pattern = '|'.join(self.CONJUNCTIONS)
        parts = re.split(pattern, text, flags=re.IGNORECASE)
        return [p.strip() for p in parts if p.strip()]
    
    def _classify_task(self, text: str, index: int) -> Optional[AgentTask]:
        """Classify a text segment into a task."""
        text_lower = text.lower()
        
        for task_type, patterns in self.TASK_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    params = {'text': text}
                    if match.groups():
                        params['query'] = match.group(1)
                        params['target'] = match.group(1)
                    
                    if task_type == 'calendar':
                        params['action'] = 'list'
                        if 'tomorrow' in text_lower:
                            params['action'] = 'check_tomorrow'
                    
                    if task_type == 'open_app' and match.groups():
                        params['action'] = 'open_app'
                        params['app'] = match.group(1)
                    
                    return AgentTask(
                        id=hashlib.md5(f"{time.time()}{index}{text}".encode()).hexdigest()[:8],
                        type=task_type,
                        params=params,
                        priority=5 - index  # Earlier tasks have higher priority
                    )
        
        return None


# ============================================================================
# RESPONSE SYNTHESIZER (Combine agent results into coherent response)
# ============================================================================

class ResponseSynthesizer:
    """
    Combines results from multiple agents into a coherent VoxMind response.
    """
    
    def synthesize(self, results: List[AgentResult], original_query: str) -> str:
        """Synthesize agent results into a response."""
        if not results:
            return "I apologize, I wasn't able to complete that request."
        
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        parts = []
        
        # Process successful results
        for result in successful:
            part = self._format_result(result)
            if part:
                parts.append(part)
        
        # Add failure notes if any
        if failed:
            failed_agents = [r.agent_name for r in failed]
            parts.append(f"I encountered issues with: {', '.join(failed_agents)}.")
        
        if not parts:
            return "I've completed the task, but there's nothing specific to report."
        
        # Combine with intelligent phrasing
        if len(parts) == 1:
            return parts[0]
        else:
            intro = "I've completed multiple tasks. "
            return intro + " Additionally, ".join(parts)
    
    def _format_result(self, result: AgentResult) -> str:
        """Format a single agent result."""
        data = result.data
        
        if result.agent_name == "WebSearch":
            if data and data.get('results'):
                results = data['results']
                if results:
                    first = results[0]
                    return f"Regarding {data.get('query', 'your search')}: {first.get('snippet', 'Found results.')}"
            return f"I searched for {data.get('query', 'that')} but didn't find specific results."
        
        elif result.agent_name == "Calendar":
            events = data.get('events', [])
            if events:
                count = len(events)
                date_info = data.get('date', 'upcoming')
                return f"You have {count} event{'s' if count > 1 else ''} {date_info}."
            return "Your calendar is clear."
        
        elif result.agent_name == "SystemMonitor":
            system = data.get('system', {})
            battery = data.get('battery', {})
            parts = []
            
            if system.get('cpu_percent'):
                parts.append(f"CPU at {system['cpu_percent']:.0f}%")
            if system.get('memory_percent'):
                parts.append(f"memory at {system['memory_percent']:.0f}%")
            if battery.get('percent'):
                plugged = "charging" if battery.get('plugged_in') else "on battery"
                parts.append(f"battery at {battery['percent']}% ({plugged})")
            
            if parts:
                return "System status: " + ", ".join(parts) + "."
            return "System is running normally."
        
        elif result.agent_name == "TaskExecution":
            if data.get('opened'):
                return f"I've opened {data.get('app', 'the application')}."
            if data.get('command'):
                return f"Command executed successfully."
            return "Task completed."
        
        return None


# ============================================================================
# PROACTIVE MONITOR (VoxMind anticipates needs)
# ============================================================================

class ProactiveMonitor:
    """
    Monitors for conditions that should trigger proactive responses.
    
    Examples:
    - "Sir, your battery is below 20%"
    - "You have a meeting in 15 minutes"
    - "It's getting late, you've been working for 4 hours"
    """
    
    def __init__(self, voxmind: 'VoxMindCore'):
        self.voxmind = voxmind
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._check_interval = 60  # seconds
        self._last_alerts: Dict[str, float] = {}  # Prevent spam
        self._alert_cooldown = 300  # 5 minutes between same alerts
    
    def start(self):
        """Start proactive monitoring."""
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Proactive monitor started")
    
    def stop(self):
        """Stop monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                alerts = self._check_conditions()
                for alert in alerts:
                    self._trigger_alert(alert)
            except Exception as e:
                logger.error(f"Monitor error: {e}")
            
            time.sleep(self._check_interval)
    
    def _check_conditions(self) -> List[Dict]:
        """Check all monitoring conditions."""
        alerts = []
        
        # Battery check
        try:
            import psutil
            battery = psutil.sensors_battery()
            if battery and not battery.power_plugged:
                if battery.percent < 20:
                    alerts.append({
                        'type': 'battery_low',
                        'message': f"Sir, your battery is at {battery.percent}%. You may want to plug in.",
                        'priority': 1
                    })
                elif battery.percent < 10:
                    alerts.append({
                        'type': 'battery_critical',
                        'message': f"Critical: Battery at {battery.percent}%! Please save your work.",
                        'priority': 0
                    })
        except ImportError:
            pass
        
        # Work session length
        # (Would need to track session start time)
        
        return alerts
    
    def _trigger_alert(self, alert: Dict):
        """Trigger an alert if not in cooldown."""
        alert_type = alert['type']
        now = time.time()
        
        # Check cooldown
        last_time = self._last_alerts.get(alert_type, 0)
        if now - last_time < self._alert_cooldown:
            return
        
        self._last_alerts[alert_type] = now
        
        # Notify through VoxMind
        logger.info(f"Proactive alert: {alert['message']}")
        # In full implementation, would speak/display this


# ============================================================================
# VoxMind Core (Main orchestrator)
# ============================================================================

@dataclass
class VoxMindResponse:
    """Response from VoxMind."""
    text: str
    tasks_completed: int
    duration: float
    agent_results: List[AgentResult]
    context: Dict[str, Any] = field(default_factory=dict)


class VoxMindCore:
    """
    The main VoxMind orchestration engine.
    
    This is what makes VoxMind feel like a real voxmind:
    - Parallel task execution
    - Long-term memory
    - Proactive monitoring
    - Context-aware responses
    """
    
    def __init__(self, memory_path: str = "data/voxmind_memory.db"):
        # Core components
        self.memory = MemoryStore(memory_path)
        self.decomposer = TaskDecomposer()
        self.synthesizer = ResponseSynthesizer()
        self.monitor = ProactiveMonitor(self)
        
        # Agents
        self.agents: List[BaseAgent] = []
        self._register_default_agents()
        
        # Execution
        self._executor = ThreadPoolExecutor(max_workers=5)
        self._running = False
        
        # State
        self._current_tasks: Dict[str, AgentTask] = {}
        self._personality = {
            'name': 'VoxMind',
            'formal': True,
            'proactive': True
        }
    
    def _register_default_agents(self):
        """Register default agents."""
        self.agents = [
            WebSearchAgent(self),
            SystemMonitorAgent(self),
            CalendarAgent(self),
            TaskExecutionAgent(self),
        ]
    
    def register_agent(self, agent: BaseAgent):
        """Register a custom agent."""
        self.agents.append(agent)
    
    async def start(self):
        """Start VoxMind."""
        self._running = True
        self.monitor.start()
        logger.info("VoxMind Core started")
    
    async def stop(self):
        """Stop VoxMind."""
        self._running = False
        self.monitor.stop()
        self._executor.shutdown(wait=True)
        logger.info("VoxMind Core stopped")
    
    async def process(self, text: str) -> VoxMindResponse:
        """
        Process a user request.
        
        This is the main entry point. It:
        1. Decomposes the request into tasks
        2. Dispatches tasks to appropriate agents (in parallel)
        3. Synthesizes results into a coherent response
        4. Stores the interaction in memory
        """
        start_time = time.time()
        
        # Decompose into tasks
        tasks = self.decomposer.decompose(text)
        logger.info(f"Decomposed into {len(tasks)} tasks: {[t.type for t in tasks]}")
        
        # Find agents for each task and execute in parallel
        results = await self._execute_tasks_parallel(tasks)
        
        # Synthesize response
        response_text = self.synthesizer.synthesize(results, text)
        
        # Remember this interaction
        self.memory.remember_conversation(text, response_text)
        
        duration = time.time() - start_time
        
        return VoxMindResponse(
            text=response_text,
            tasks_completed=len([r for r in results if r.success]),
            duration=duration,
            agent_results=results
        )
    
    async def _execute_tasks_parallel(self, tasks: List[AgentTask]) -> List[AgentResult]:
        """Execute multiple tasks in parallel."""
        results = []
        
        # Create coroutines for each task
        coroutines = []
        for task in tasks:
            agent = self._find_agent(task.type)
            if agent:
                coroutines.append(agent.execute(task))
            else:
                results.append(AgentResult(
                    task_id=task.id,
                    agent_name="Unknown",
                    success=False,
                    data=None,
                    error=f"No agent for task type: {task.type}"
                ))
        
        # Execute all coroutines in parallel
        if coroutines:
            completed = await asyncio.gather(*coroutines, return_exceptions=True)
            for result in completed:
                if isinstance(result, AgentResult):
                    results.append(result)
                elif isinstance(result, Exception):
                    results.append(AgentResult(
                        task_id="error",
                        agent_name="Unknown",
                        success=False,
                        data=None,
                        error=str(result)
                    ))
        
        return results
    
    def _find_agent(self, task_type: str) -> Optional[BaseAgent]:
        """Find an agent that can handle a task type."""
        for agent in self.agents:
            if agent.can_handle(task_type):
                return agent
        return None
    
    def recall_memory(self, query: str, limit: int = 5) -> List[Memory]:
        """Recall memories related to a query."""
        return self.memory.recall(query, limit=limit)
    
    def get_preferences(self) -> Dict[str, Any]:
        """Get user preferences."""
        return self.memory.get_preferences()
    
    def set_preference(self, key: str, value: Any):
        """Set a user preference."""
        self.memory.remember_preference(key, value)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_voxmind_instance: Optional[VoxMindCore] = None


def get_voxmind() -> VoxMindCore:
    """Get the global VoxMind instance."""
    global _voxmind_instance
    if _voxmind_instance is None:
        _voxmind_instance = VoxMindCore()
    return _voxmind_instance


async def ask_voxmind(query: str) -> str:
    """
    Simple function to ask VoxMind something.
    
    Usage:
        response = await ask_voxmind("Research quantum computing while checking my battery")
        print(response)  # "Regarding quantum computing: ... Battery at 85%..."
    """
    voxmind = get_voxmind()
    result = await voxmind.process(query)
    return result.text


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate VoxMind capabilities."""
    print("=" * 60)
    print("VoxMind Core DEMO")
    print("=" * 60)
    
    voxmind = VoxMindCore()
    await voxmind.start()
    
    # Test queries
    queries = [
        "What time is it?",
        "Check my system status",
        "Research artificial intelligence while checking my calendar",
        "Open notepad and check my battery",
    ]
    
    for query in queries:
        print(f"\n👤 User: {query}")
        result = await voxmind.process(query)
        print(f"🤖 voxmind: {result.text}")
        print(f"   [Tasks: {result.tasks_completed}, Duration: {result.duration:.2f}s]")
    
    await voxmind.stop()


if __name__ == "__main__":
    asyncio.run(demo())
