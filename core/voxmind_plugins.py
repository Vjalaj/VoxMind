"""
VoxMind Plugin System
============================
Extensible architecture for adding new data sources and capabilities.

This allows VoxMind to get information from:
- APIs (weather, news, stocks, etc.)
- Local files and databases
- Web scraping
- Custom integrations

Example:
    # Create a weather plugin
    @plugin("weather")
    class WeatherPlugin(VoxMindPlugin):
        async def execute(self, query):
            return await self.fetch_weather(query.location)
    
    # Use it
    result = await voxmind.ask("What's the weather in New York?")
"""

import asyncio
import json
import logging
import time
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable, Type
from datetime import datetime
from pathlib import Path
import re

logger = logging.getLogger('VoxMind.Plugins')


# ============================================================================
# PLUGIN BASE
# ============================================================================

@dataclass
class PluginQuery:
    """Query passed to a plugin."""
    text: str
    params: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginResult:
    """Result from a plugin."""
    success: bool
    data: Any
    source: str
    cached: bool = False
    expires: Optional[float] = None
    error: Optional[str] = None


class VoxMindPlugin(ABC):
    """Base class for all VoxMind plugins."""
    
    name: str = "base_plugin"
    description: str = "Base plugin"
    version: str = "1.0.0"
    
    # Patterns that trigger this plugin
    triggers: List[str] = []
    
    def __init__(self):
        self.enabled = True
        self._cache: Dict[str, PluginResult] = {}
        self._cache_ttl = 300  # 5 minutes default
    
    @abstractmethod
    async def execute(self, query: PluginQuery) -> PluginResult:
        """Execute the plugin. Override in subclasses."""
        pass
    
    def matches(self, text: str) -> bool:
        """Check if text triggers this plugin."""
        text_lower = text.lower()
        for pattern in self.triggers:
            if re.search(pattern, text_lower):
                return True
        return False
    
    def extract_params(self, text: str) -> Dict[str, Any]:
        """Extract parameters from text. Override for custom extraction."""
        return {'text': text}
    
    def _cache_key(self, query: PluginQuery) -> str:
        """Generate cache key for a query."""
        content = f"{self.name}:{query.text}:{json.dumps(query.params, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get_cached(self, query: PluginQuery) -> Optional[PluginResult]:
        """Get cached result if valid."""
        key = self._cache_key(query)
        if key in self._cache:
            result = self._cache[key]
            if result.expires and time.time() < result.expires:
                result.cached = True
                return result
            else:
                del self._cache[key]
        return None
    
    def cache_result(self, query: PluginQuery, result: PluginResult):
        """Cache a result."""
        result.expires = time.time() + self._cache_ttl
        self._cache[self._cache_key(query)] = result


# ============================================================================
# PLUGIN REGISTRY
# ============================================================================

class PluginRegistry:
    """Registry for all VoxMind plugins."""
    
    _instance: Optional['PluginRegistry'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._plugins: Dict[str, VoxMindPlugin] = {}
        return cls._instance
    
    def register(self, plugin: VoxMindPlugin):
        """Register a plugin."""
        self._plugins[plugin.name] = plugin
        logger.info(f"Registered plugin: {plugin.name}")
    
    def unregister(self, name: str):
        """Unregister a plugin."""
        if name in self._plugins:
            del self._plugins[name]
    
    def get(self, name: str) -> Optional[VoxMindPlugin]:
        """Get a plugin by name."""
        return self._plugins.get(name)
    
    def find_matching(self, text: str) -> List[VoxMindPlugin]:
        """Find all plugins that match a text query."""
        return [p for p in self._plugins.values() 
                if p.enabled and p.matches(text)]
    
    def all(self) -> List[VoxMindPlugin]:
        """Get all plugins."""
        return list(self._plugins.values())


def plugin(name: str):
    """Decorator to register a plugin class."""
    def decorator(cls: Type[VoxMindPlugin]):
        cls.name = name
        instance = cls()
        PluginRegistry().register(instance)
        return cls
    return decorator


# ============================================================================
# BUILT-IN PLUGINS
# ============================================================================

@plugin("weather")
class WeatherPlugin(VoxMindPlugin):
    """Get weather information."""
    
    name = "weather"
    description = "Get current weather and forecasts"
    triggers = [
        r'weather\s+(?:in\s+)?(.+)?',
        r"what's?\s+(?:the\s+)?weather",
        r'is\s+it\s+(?:going\s+to\s+)?(?:rain|snow|sunny)',
        r'temperature\s+(?:in\s+)?(.+)?',
        r'forecast\s+(?:for\s+)?(.+)?'
    ]
    
    def __init__(self):
        super().__init__()
        self._cache_ttl = 600  # 10 minutes for weather
    
    def extract_params(self, text: str) -> Dict[str, Any]:
        """Extract location from weather query."""
        # Try to extract location
        patterns = [
            r'weather\s+(?:in\s+)?([a-zA-Z\s,]+)',
            r'temperature\s+(?:in\s+)?([a-zA-Z\s,]+)',
            r'forecast\s+(?:for\s+)?([a-zA-Z\s,]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return {'location': match.group(1).strip()}
        
        return {'location': 'current location'}
    
    async def execute(self, query: PluginQuery) -> PluginResult:
        """Fetch weather data."""
        location = query.params.get('location', 'London')
        
        # Check cache first
        cached = self.get_cached(query)
        if cached:
            return cached
        
        try:
            # Try Open-Meteo (free, no API key needed)
            weather_data = await self._fetch_open_meteo(location)
            
            result = PluginResult(
                success=True,
                data=weather_data,
                source="Open-Meteo"
            )
            self.cache_result(query, result)
            return result
            
        except Exception as e:
            return PluginResult(
                success=False,
                data=None,
                source="Weather",
                error=str(e)
            )
    
    async def _fetch_open_meteo(self, location: str) -> Dict:
        """Fetch from Open-Meteo API."""
        try:
            import aiohttp
            
            # First, geocode the location
            async with aiohttp.ClientSession() as session:
                # Geocoding
                geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1"
                async with session.get(geo_url) as resp:
                    if resp.status == 200:
                        geo_data = await resp.json()
                        if geo_data.get('results'):
                            loc = geo_data['results'][0]
                            lat, lon = loc['latitude'], loc['longitude']
                            name = loc['name']
                        else:
                            return {'error': f'Location not found: {location}'}
                    else:
                        return {'error': 'Geocoding failed'}
                
                # Weather
                weather_url = (
                    f"https://api.open-meteo.com/v1/forecast?"
                    f"latitude={lat}&longitude={lon}"
                    f"&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
                    f"&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
                    f"&timezone=auto"
                )
                async with session.get(weather_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        current = data.get('current', {})
                        
                        return {
                            'location': name,
                            'temperature': current.get('temperature_2m'),
                            'humidity': current.get('relative_humidity_2m'),
                            'wind_speed': current.get('wind_speed_10m'),
                            'condition': self._weather_code_to_text(
                                current.get('weather_code', 0)
                            ),
                            'unit': '°C'
                        }
        except ImportError:
            pass
        
        # Fallback mock data
        return {
            'location': location,
            'temperature': 22,
            'humidity': 65,
            'condition': 'Partly cloudy',
            'unit': '°C',
            'note': 'Mock data (install aiohttp for real weather)'
        }
    
    def _weather_code_to_text(self, code: int) -> str:
        """Convert WMO weather code to text."""
        codes = {
            0: 'Clear sky', 1: 'Mainly clear', 2: 'Partly cloudy',
            3: 'Overcast', 45: 'Foggy', 48: 'Depositing rime fog',
            51: 'Light drizzle', 53: 'Moderate drizzle', 55: 'Dense drizzle',
            61: 'Slight rain', 63: 'Moderate rain', 65: 'Heavy rain',
            71: 'Slight snow', 73: 'Moderate snow', 75: 'Heavy snow',
            95: 'Thunderstorm'
        }
        return codes.get(code, 'Unknown')


@plugin("news")
class NewsPlugin(VoxMindPlugin):
    """Get news headlines."""
    
    name = "news"
    description = "Get latest news and headlines"
    triggers = [
        r'news\s*(?:about\s+)?(.+)?',
        r"what's?\s+(?:the\s+)?(?:latest\s+)?news",
        r'headlines?\s*(?:about\s+)?(.+)?',
        r'tell\s+me\s+(?:the\s+)?news'
    ]
    
    def __init__(self):
        super().__init__()
        self._cache_ttl = 900  # 15 minutes for news
    
    def extract_params(self, text: str) -> Dict[str, Any]:
        """Extract topic from news query."""
        patterns = [
            r'news\s+about\s+(.+)',
            r'headlines?\s+(?:about|on)\s+(.+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return {'topic': match.group(1).strip()}
        
        return {'topic': 'general'}
    
    async def execute(self, query: PluginQuery) -> PluginResult:
        """Fetch news."""
        topic = query.params.get('topic', 'general')
        
        cached = self.get_cached(query)
        if cached:
            return cached
        
        try:
            # Try to fetch real news (requires API key for most services)
            # For demo, we'll use a simple RSS approach
            news = await self._fetch_news(topic)
            
            result = PluginResult(
                success=True,
                data={'topic': topic, 'headlines': news},
                source="News"
            )
            self.cache_result(query, result)
            return result
            
        except Exception as e:
            return PluginResult(
                success=False,
                data=None,
                source="News",
                error=str(e)
            )
    
    async def _fetch_news(self, topic: str) -> List[Dict]:
        """Fetch news headlines."""
        # In production, would use NewsAPI, Google News RSS, etc.
        # Mock data for demo
        return [
            {'title': f'Latest developments in {topic}', 'source': 'Mock News'},
            {'title': f'Breaking: Major {topic} announcement', 'source': 'Mock News'},
            {'title': f'Experts discuss {topic} trends', 'source': 'Mock News'},
        ]


@plugin("calculator")
class CalculatorPlugin(VoxMindPlugin):
    """Perform calculations."""
    
    name = "calculator"
    description = "Perform mathematical calculations"
    triggers = [
        r'calculate\s+(.+)',
        r'what\s+is\s+(\d+[\s\d\+\-\*\/\^\%\.\(\)]+)',
        r'(\d+)\s*[\+\-\*\/\^]\s*(\d+)',
        r'how\s+much\s+is\s+(.+)',
        r'solve\s+(.+)'
    ]
    
    def extract_params(self, text: str) -> Dict[str, Any]:
        """Extract math expression."""
        patterns = [
            r'calculate\s+(.+)',
            r'what\s+is\s+(.+)',
            r'how\s+much\s+is\s+(.+)',
            r'solve\s+(.+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return {'expression': match.group(1).strip()}
        
        # Try to find any math expression
        math_match = re.search(r'([\d\s\+\-\*\/\^\%\.\(\)]+)', text)
        if math_match:
            return {'expression': math_match.group(1).strip()}
        
        return {'expression': text}
    
    async def execute(self, query: PluginQuery) -> PluginResult:
        """Calculate result."""
        expr = query.params.get('expression', '')
        
        try:
            # Sanitize and evaluate
            # Only allow safe characters
            clean_expr = re.sub(r'[^\d\+\-\*\/\.\(\)\s\^]', '', expr)
            clean_expr = clean_expr.replace('^', '**')  # Power operator
            
            # Safe eval using ast
            import ast
            import operator
            
            ops = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.Pow: operator.pow,
                ast.USub: operator.neg,
            }
            
            def eval_expr(node):
                if isinstance(node, ast.Num):
                    return node.n
                elif isinstance(node, ast.BinOp):
                    return ops[type(node.op)](eval_expr(node.left), eval_expr(node.right))
                elif isinstance(node, ast.UnaryOp):
                    return ops[type(node.op)](eval_expr(node.operand))
                else:
                    raise ValueError(f"Unsupported operation")
            
            tree = ast.parse(clean_expr, mode='eval')
            result = eval_expr(tree.body)
            
            return PluginResult(
                success=True,
                data={'expression': expr, 'result': result},
                source="Calculator"
            )
            
        except Exception as e:
            return PluginResult(
                success=False,
                data=None,
                source="Calculator",
                error=f"Could not calculate: {e}"
            )


@plugin("time")
class TimePlugin(VoxMindPlugin):
    """Get time and date information."""
    
    name = "time"
    description = "Get current time, date, and timezone info"
    triggers = [
        r'what\s+time\s+is\s+it',
        r'what\'?s?\s+the\s+time',
        r'current\s+time',
        r'what\s+(?:is\s+)?(?:today\'?s?\s+)?date',
        r'what\s+day\s+is\s+(?:it|today)',
        r'time\s+in\s+(.+)'
    ]
    
    def extract_params(self, text: str) -> Dict[str, Any]:
        """Extract timezone or location."""
        match = re.search(r'time\s+in\s+(.+)', text, re.IGNORECASE)
        if match:
            return {'location': match.group(1).strip()}
        return {}
    
    async def execute(self, query: PluginQuery) -> PluginResult:
        """Get time information."""
        now = datetime.now()
        
        data = {
            'time': now.strftime('%H:%M:%S'),
            'time_12h': now.strftime('%I:%M %p'),
            'date': now.strftime('%Y-%m-%d'),
            'day': now.strftime('%A'),
            'full': now.strftime('%A, %B %d, %Y at %I:%M %p')
        }
        
        location = query.params.get('location')
        if location:
            # Would need timezone conversion here
            data['note'] = f'Timezone for {location} not yet implemented'
        
        return PluginResult(
            success=True,
            data=data,
            source="System Time"
        )


@plugin("wikipedia")
class WikipediaPlugin(VoxMindPlugin):
    """Get information from Wikipedia."""
    
    name = "wikipedia"
    description = "Search Wikipedia for information"
    triggers = [
        r'who\s+(?:is|was)\s+(.+)',
        r'what\s+(?:is|was|are|were)\s+(?:a\s+|an\s+|the\s+)?(.+)',
        r'tell\s+me\s+about\s+(.+)',
        r'(?:wikipedia|wiki)\s+(.+)',
        r'define\s+(.+)',
        r'explain\s+(.+)'
    ]
    
    def __init__(self):
        super().__init__()
        self._cache_ttl = 3600  # 1 hour for wiki content
    
    def extract_params(self, text: str) -> Dict[str, Any]:
        """Extract search term."""
        patterns = [
            r'who\s+(?:is|was)\s+(.+)',
            r'what\s+(?:is|was|are|were)\s+(?:a\s+|an\s+|the\s+)?(.+)',
            r'tell\s+me\s+about\s+(.+)',
            r'(?:wikipedia|wiki)\s+(.+)',
            r'define\s+(.+)',
            r'explain\s+(.+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                term = match.group(1).strip()
                # Clean up common endings
                term = re.sub(r'\?+$', '', term)
                return {'term': term}
        
        return {'term': text}
    
    async def execute(self, query: PluginQuery) -> PluginResult:
        """Search Wikipedia."""
        term = query.params.get('term', '')
        
        cached = self.get_cached(query)
        if cached:
            return cached
        
        try:
            summary = await self._fetch_wikipedia(term)
            
            result = PluginResult(
                success=True,
                data={'term': term, 'summary': summary},
                source="Wikipedia"
            )
            self.cache_result(query, result)
            return result
            
        except Exception as e:
            return PluginResult(
                success=False,
                data=None,
                source="Wikipedia",
                error=str(e)
            )
    
    async def _fetch_wikipedia(self, term: str) -> str:
        """Fetch Wikipedia summary."""
        try:
            import aiohttp
            
            url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + term.replace(' ', '_')
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get('extract', 'No summary available')
                    elif resp.status == 404:
                        return f"No Wikipedia article found for '{term}'"
                    else:
                        return f"Wikipedia search failed"
        except ImportError:
            pass
        
        return f"Information about {term} (install aiohttp for real Wikipedia data)"


@plugin("knowledge")
class KnowledgePlugin(VoxMindPlugin):
    """
    Comprehensive knowledge retrieval from multiple sources.
    
    Aggregates information from:
    - Wikipedia, Wikidata
    - Reddit, Quora, StackOverflow
    - News, Academic papers
    - YouTube (with transcripts)
    - GitHub (for code topics)
    """
    
    name = "knowledge"
    description = "Research any topic from multiple sources"
    triggers = [
        r'research\s+(.+)',
        r'tell\s+me\s+(?:everything\s+)?about\s+(.+)',
        r'(?:in\s+)?(?:brief|detail)\s+(?:about\s+)?(.+)',
        r'explain\s+(?:in\s+detail\s+)?(.+)',
        r'what\s+do\s+(?:you\s+)?know\s+about\s+(.+)',
        r'gather\s+(?:information|info)\s+(?:about|on)\s+(.+)',
        r'comprehensive\s+(?:search|info)\s+(?:on|about)\s+(.+)',
    ]
    
    def __init__(self):
        super().__init__()
        self._cache_ttl = 1800  # 30 minutes
        self._engine = None
    
    def _get_engine(self):
        """Lazy load knowledge engine."""
        if self._engine is None:
            try:
                from core.knowledge_engine import KnowledgeEngine
                self._engine = KnowledgeEngine()
            except ImportError:
                pass
        return self._engine
    
    def extract_params(self, text: str) -> Dict[str, Any]:
        """Extract topic and detail level."""
        text_lower = text.lower()
        
        # Determine detail level
        detail_level = "brief"
        if any(w in text_lower for w in ['detail', 'comprehensive', 'everything', 'in depth']):
            detail_level = "detailed"
        
        # Check for video request
        include_videos = any(w in text_lower for w in ['video', 'youtube', 'tutorial', 'watch'])
        
        # Extract topic
        patterns = [
            r'research\s+(.+)',
            r'tell\s+me\s+(?:everything\s+)?about\s+(.+)',
            r'(?:in\s+)?(?:brief|detail)\s+(?:about\s+)?(.+)',
            r'explain\s+(?:in\s+detail\s+)?(.+)',
            r'what\s+do\s+(?:you\s+)?know\s+about\s+(.+)',
            r'gather\s+(?:information|info)\s+(?:about|on)\s+(.+)',
        ]
        
        topic = text
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                topic = match.group(1).strip()
                break
        
        # Clean up
        topic = re.sub(r'\?+$', '', topic)
        topic = re.sub(r'^(a|an|the)\s+', '', topic, flags=re.IGNORECASE)
        
        return {
            'topic': topic,
            'detail_level': detail_level,
            'include_videos': include_videos
        }
    
    async def execute(self, query: PluginQuery) -> PluginResult:
        """Research topic from multiple sources."""
        topic = query.params.get('topic', '')
        detail_level = query.params.get('detail_level', 'brief')
        include_videos = query.params.get('include_videos', False)
        
        engine = self._get_engine()
        if not engine:
            return PluginResult(
                success=False,
                data=None,
                source="Knowledge",
                error="Knowledge engine not available"
            )
        
        # Check cache
        cached = self.get_cached(query)
        if cached:
            return cached
        
        try:
            response = await engine.query(
                topic,
                detail_level=detail_level,
                include_videos=include_videos,
                include_academic=detail_level == "detailed"
            )
            
            result = PluginResult(
                success=True,
                data={
                    'topic': topic,
                    'summary': response.summary,
                    'detailed': response.detailed,
                    'source_count': response.source_count,
                    'videos': [
                        {'title': v.title, 'url': v.url, 'duration': v.duration}
                        for v in response.videos[:3]
                    ],
                    'sources': [
                        {'source': s.source, 'title': s.title[:50]}
                        for s in response.sources[:5]
                    ],
                    'confidence': response.confidence,
                    'detail_level': detail_level
                },
                source="Knowledge Engine"
            )
            
            self.cache_result(query, result)
            return result
            
        except Exception as e:
            return PluginResult(
                success=False,
                data=None,
                source="Knowledge",
                error=str(e)
            )


@plugin("file_search")
class FileSearchPlugin(VoxMindPlugin):
    """Search for files on the system."""
    
    name = "file_search"
    description = "Search for files and folders"
    triggers = [
        r'find\s+(?:files?\s+)?(?:named?\s+)?(.+)',
        r'search\s+(?:for\s+)?(?:files?\s+)?(.+)',
        r'where\s+is\s+(.+)',
        r'locate\s+(.+)'
    ]
    
    def extract_params(self, text: str) -> Dict[str, Any]:
        """Extract file pattern."""
        patterns = [
            r'find\s+(?:files?\s+)?(?:named?\s+)?(.+)',
            r'search\s+(?:for\s+)?(?:files?\s+)?(.+)',
            r'where\s+is\s+(.+)',
            r'locate\s+(.+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return {'pattern': match.group(1).strip()}
        
        return {'pattern': text}
    
    async def execute(self, query: PluginQuery) -> PluginResult:
        """Search for files."""
        pattern = query.params.get('pattern', '')
        
        try:
            # Search in common locations
            results = []
            search_paths = [
                Path.home() / "Documents",
                Path.home() / "Desktop",
                Path.home() / "Downloads",
            ]
            
            for base_path in search_paths:
                if base_path.exists():
                    for path in base_path.rglob(f"*{pattern}*"):
                        if len(results) >= 10:
                            break
                        results.append({
                            'path': str(path),
                            'name': path.name,
                            'is_dir': path.is_dir(),
                            'size': path.stat().st_size if path.is_file() else None
                        })
            
            return PluginResult(
                success=True,
                data={'pattern': pattern, 'files': results},
                source="File System"
            )
            
        except Exception as e:
            return PluginResult(
                success=False,
                data=None,
                source="File System",
                error=str(e)
            )


# ============================================================================
# PLUGIN EXECUTOR
# ============================================================================

class PluginExecutor:
    """
    Executes plugins and aggregates results.
    """
    
    def __init__(self):
        self.registry = PluginRegistry()
    
    async def execute(self, text: str) -> List[PluginResult]:
        """Execute all matching plugins."""
        plugins = self.registry.find_matching(text)
        
        if not plugins:
            return []
        
        results = []
        tasks = []
        
        for plugin in plugins:
            params = plugin.extract_params(text)
            query = PluginQuery(text=text, params=params)
            tasks.append(plugin.execute(query))
        
        completed = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in completed:
            if isinstance(result, PluginResult):
                results.append(result)
            elif isinstance(result, Exception):
                results.append(PluginResult(
                    success=False,
                    data=None,
                    source="Plugin",
                    error=str(result)
                ))
        
        return results
    
    def format_results(self, results: List[PluginResult]) -> str:
        """Format plugin results as a response."""
        parts = []
        
        for result in results:
            if not result.success:
                continue
            
            data = result.data
            source = result.source
            
            if source == "Weather" and data:
                temp = data.get('temperature', 'N/A')
                cond = data.get('condition', 'unknown')
                loc = data.get('location', 'your area')
                parts.append(f"It's currently {temp}{data.get('unit', '°C')} and {cond.lower()} in {loc}.")
            
            elif source == "System Time" and data:
                parts.append(f"It's {data.get('time_12h', data.get('time'))} on {data.get('day', 'today')}.")
            
            elif source == "Calculator" and data:
                parts.append(f"The answer is {data.get('result')}.")
            
            elif source == "Wikipedia" and data:
                summary = data.get('summary', '')
                if len(summary) > 300:
                    summary = summary[:297] + "..."
                parts.append(summary)
            
            elif source == "Knowledge Engine" and data:
                # Format knowledge response based on detail level
                detail_level = data.get('detail_level', 'brief')
                
                if detail_level == 'brief':
                    parts.append(data.get('summary', 'No information found.'))
                else:
                    parts.append(data.get('detailed', data.get('summary', '')))
                
                # Add video info if available
                videos = data.get('videos', [])
                if videos:
                    parts.append("\n📹 Video Resources:")
                    for v in videos[:3]:
                        parts.append(f"  • {v.get('title', '')} ({v.get('duration', '')})")
                        parts.append(f"    {v.get('url', '')}")
                
                # Add source count
                source_count = data.get('source_count', 0)
                confidence = data.get('confidence', 0)
                parts.append(f"\n[Aggregated from {source_count} sources | Confidence: {confidence:.0%}]")
            
            elif source == "News" and data:
                headlines = data.get('headlines', [])[:3]
                if headlines:
                    parts.append(f"Here are the latest headlines on {data.get('topic', 'news')}:")
                    for h in headlines:
                        parts.append(f"  • {h.get('title', '')}")
            
            elif source == "File System" and data:
                files = data.get('files', [])
                if files:
                    parts.append(f"Found {len(files)} matching files:")
                    for f in files[:5]:
                        parts.append(f"  • {f.get('name', '')}")
                else:
                    parts.append(f"No files found matching '{data.get('pattern', '')}'")
        
        return "\n".join(parts) if parts else None


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demo the plugin system."""
    print("=" * 60)
    print("VOXMIND PLUGIN SYSTEM DEMO")
    print("=" * 60)
    
    executor = PluginExecutor()
    
    queries = [
        "What time is it?",
        "What's the weather in London?",
        "Calculate 15 * 24 + 100",
        "Who is Albert Einstein?",
        "What's the latest news about technology?",
    ]
    
    for query in queries:
        print(f"\n👤 Query: {query}")
        results = await executor.execute(query)
        response = executor.format_results(results)
        
        if response:
            print(f"🤖 VoxMind: {response}")
        else:
            print("🤖 VoxMind: I couldn't find information for that.")
        
        # Show which plugins were used
        plugins_used = [r.source for r in results if r.success]
        if plugins_used:
            print(f"   [Plugins: {', '.join(plugins_used)}]")


if __name__ == "__main__":
    asyncio.run(demo())
