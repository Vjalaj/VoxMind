"""
VoxMind Knowledge Aggregator
============================
Retrieves and synthesizes information from multiple sources WITHOUT opening browsers.

Sources supported:
- Wikipedia (free API)
- DuckDuckGo (instant answers + search)
- Reddit (public API)
- YouTube (transcripts/subtitles)
- Stack Overflow/Exchange
- News APIs
- Wikidata (structured facts)
- ArXiv (academic papers)

Usage:
    from core.knowledge_engine import ask_knowledge
    
    # Brief answer
    result = await ask_knowledge("What is quantum computing?", detail_level="brief")
    
    # Detailed with sources
    result = await ask_knowledge("Who is Elon Musk?", detail_level="detailed")
    
    # With video resources
    result = await ask_knowledge("How to learn Python?", include_videos=True)
"""

import asyncio
import json
import re
import time
import logging
import hashlib
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from abc import ABC, abstractmethod
from urllib.parse import quote_plus, urlencode
import html

logger = logging.getLogger('VoxMind.Knowledge')


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class SourceResult:
    """Result from a single source."""
    source: str
    title: str
    content: str
    url: str = ""
    confidence: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)
    retrieved_at: float = field(default_factory=time.time)


@dataclass
class VideoResource:
    """A video resource with transcript."""
    title: str
    url: str
    platform: str  # youtube, vimeo, etc.
    duration: str = ""
    channel: str = ""
    transcript: str = ""
    thumbnail: str = ""
    views: str = ""


@dataclass 
class KnowledgeResponse:
    """Aggregated knowledge response."""
    query: str
    summary: str  # Brief answer
    detailed: str  # Full detailed answer
    sources: List[SourceResult]
    videos: List[VideoResource]
    related_topics: List[str]
    confidence: float
    retrieval_time: float
    source_count: int


# ============================================================================
# SOURCE ADAPTERS
# ============================================================================

class SourceAdapter(ABC):
    """Base class for source adapters."""
    
    name: str = "base"
    priority: int = 5  # 1 = highest priority
    
    # Default headers with User-Agent (required by Wikipedia and others)
    DEFAULT_HEADERS = {
        'User-Agent': 'VoxMind/2.0 (Knowledge Assistant; https://github.com/voxmind)',
        'Accept': 'application/json'
    }
    
    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> List[SourceResult]:
        """Search this source."""
        pass
    
    async def _fetch_json(self, url: str, headers: Dict = None) -> Optional[Dict]:
        """Fetch JSON from URL."""
        try:
            import aiohttp
            merged_headers = {**self.DEFAULT_HEADERS, **(headers or {})}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=merged_headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    elif resp.status == 202:
                        # Some APIs return 202 for async processing
                        await asyncio.sleep(0.5)
                        async with session.get(url, headers=merged_headers) as retry_resp:
                            if retry_resp.status == 200:
                                return await retry_resp.json()
        except asyncio.TimeoutError:
            logger.warning(f"{self.name} timeout")
        except Exception as e:
            logger.warning(f"{self.name} fetch error: {e}")
        return None
    
    async def _fetch_text(self, url: str, headers: Dict = None) -> Optional[str]:
        """Fetch text from URL."""
        try:
            import aiohttp
            merged_headers = {**self.DEFAULT_HEADERS, **(headers or {})}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=merged_headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return await resp.text()
        except asyncio.TimeoutError:
            logger.warning(f"{self.name} timeout")
        except Exception as e:
            logger.warning(f"{self.name} fetch error: {e}")
        return None


class WikipediaAdapter(SourceAdapter):
    """Wikipedia API adapter."""
    
    name = "Wikipedia"
    priority = 1
    
    def _normalize_query(self, query: str) -> List[str]:
        """
        Generate normalized query variations for better Wikipedia matches.
        Returns multiple variations to try.
        """
        queries = []
        q = query.strip()
        
        # Remove leading articles (the, a, an)
        cleaned = re.sub(r'^(the|a|an)\s+', '', q, flags=re.IGNORECASE)
        
        # Original (without leading article)
        if cleaned != q:
            queries.append(cleaned)
        queries.append(q)
        
        # For "X brand" queries, try "X Inc" or "X (company)"
        brand_match = re.match(r'^(.+?)\s+brand$', cleaned, re.IGNORECASE)
        if brand_match:
            name = brand_match.group(1)
            queries.insert(0, f"{name} Inc")  # Try "Apple Inc" first
            queries.insert(1, name)  # Then just "Apple"
            queries.append(f"{name} (company)")
        
        # For "X company" queries, try "X Inc"
        company_match = re.match(r'^(.+?)\s+company$', cleaned, re.IGNORECASE)
        if company_match:
            name = company_match.group(1)
            queries.insert(0, f"{name} Inc")
        
        return queries
    
    async def search(self, query: str, limit: int = 3) -> List[SourceResult]:
        results = []
        
        # Try normalized query variations
        query_variations = self._normalize_query(query)
        data = None
        
        for q in query_variations:
            # Get summary
            summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote_plus(q)}"
            data = await self._fetch_json(summary_url)
            
            if data and data.get('extract'):
                # Check it's a real article, not a disambiguation
                if data.get('type') != 'disambiguation':
                    results.append(SourceResult(
                        source="Wikipedia",
                        title=data.get('title', query),
                        content=data['extract'],
                        url=data.get('content_urls', {}).get('desktop', {}).get('page', ''),
                        confidence=0.95,
                        metadata={
                            'type': data.get('type', 'standard'),
                            'description': data.get('description', '')
                        }
                    ))
                    break  # Found a good result, stop trying variations
        
        # If no direct match, search for related articles
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote_plus(query_variations[0])}&format=json&srlimit={limit}"
        search_data = await self._fetch_json(search_url)
        
        if search_data and 'query' in search_data:
            for item in search_data['query'].get('search', [])[:limit-1]:
                # Skip if we already have this title
                title = item.get('title', '')
                if title and not any(r.title == title for r in results):
                    article_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote_plus(title)}"
                    article_data = await self._fetch_json(article_url)
                    
                    if article_data and article_data.get('extract'):
                        results.append(SourceResult(
                            source="Wikipedia",
                            title=title,
                            content=article_data['extract'],
                            url=f"https://en.wikipedia.org/wiki/{quote_plus(title)}",
                            confidence=0.9
                        ))
        
        return results


class DuckDuckGoAdapter(SourceAdapter):
    """DuckDuckGo Instant Answer API adapter."""
    
    name = "DuckDuckGo"
    priority = 2
    
    async def search(self, query: str, limit: int = 5) -> List[SourceResult]:
        results = []
        
        url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&skip_disambig=1"
        
        # DuckDuckGo returns application/x-javascript, so we need custom handling
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.DEFAULT_HEADERS, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        # Read as text first, then parse as JSON
                        text = await resp.text()
                        data = json.loads(text)
                    else:
                        return results
        except Exception as e:
            logger.warning(f"DuckDuckGo error: {e}")
            return results
        
        if not data:
            return results
        
        # Main abstract
        if data.get('Abstract'):
            results.append(SourceResult(
                source="DuckDuckGo",
                title=data.get('Heading', query),
                content=data['Abstract'],
                url=data.get('AbstractURL', ''),
                confidence=0.85,
                metadata={'source': data.get('AbstractSource', '')}
            ))
        
        # Answer box (direct answer)
        if data.get('Answer'):
            results.append(SourceResult(
                source="DuckDuckGo Answer",
                title=f"Answer: {query}",
                content=data['Answer'],
                url="",
                confidence=0.9
            ))
        
        # Related topics
        for topic in data.get('RelatedTopics', [])[:limit]:
            if isinstance(topic, dict) and topic.get('Text'):
                results.append(SourceResult(
                    source="DuckDuckGo",
                    title=topic.get('Text', '')[:80],
                    content=topic.get('Text', ''),
                    url=topic.get('FirstURL', ''),
                    confidence=0.7
                ))
        
        return results


class RedditAdapter(SourceAdapter):
    """Reddit public API adapter."""
    
    name = "Reddit"
    priority = 4
    
    async def search(self, query: str, limit: int = 5) -> List[SourceResult]:
        results = []
        
        # Search Reddit
        url = f"https://www.reddit.com/search.json?q={quote_plus(query)}&limit={limit}&sort=relevance"
        headers = {'User-Agent': 'VoxMind/1.0'}
        data = await self._fetch_json(url, headers)
        
        if not data or 'data' not in data:
            return results
        
        for post in data['data'].get('children', []):
            post_data = post.get('data', {})
            
            # Get selftext or title
            content = post_data.get('selftext', '')
            if not content or len(content) < 50:
                content = post_data.get('title', '')
            
            if content:
                results.append(SourceResult(
                    source=f"Reddit r/{post_data.get('subreddit', 'unknown')}",
                    title=post_data.get('title', '')[:100],
                    content=content[:1000],
                    url=f"https://reddit.com{post_data.get('permalink', '')}",
                    confidence=0.6,
                    metadata={
                        'score': post_data.get('score', 0),
                        'comments': post_data.get('num_comments', 0),
                        'subreddit': post_data.get('subreddit', '')
                    }
                ))
        
        return results


class StackExchangeAdapter(SourceAdapter):
    """Stack Exchange API adapter."""
    
    name = "StackExchange"
    priority = 3
    
    async def search(self, query: str, limit: int = 3) -> List[SourceResult]:
        results = []
        
        # Search Stack Overflow
        params = {
            'order': 'desc',
            'sort': 'relevance',
            'intitle': query,
            'site': 'stackoverflow',
            'filter': 'withbody',
            'pagesize': limit
        }
        url = f"https://api.stackexchange.com/2.3/search/advanced?{urlencode(params)}"
        data = await self._fetch_json(url)
        
        if not data or 'items' not in data:
            return results
        
        for item in data['items']:
            # Clean HTML from body
            body = item.get('body', '')
            body = re.sub(r'<[^>]+>', '', body)  # Remove HTML tags
            body = html.unescape(body)
            
            results.append(SourceResult(
                source="Stack Overflow",
                title=item.get('title', ''),
                content=body[:1000],
                url=item.get('link', ''),
                confidence=0.8 if item.get('is_answered') else 0.6,
                metadata={
                    'score': item.get('score', 0),
                    'answered': item.get('is_answered', False),
                    'tags': item.get('tags', [])
                }
            ))
        
        return results


class WikidataAdapter(SourceAdapter):
    """Wikidata structured knowledge adapter."""
    
    name = "Wikidata"
    priority = 2
    
    async def search(self, query: str, limit: int = 3) -> List[SourceResult]:
        results = []
        
        # Search Wikidata
        url = f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={quote_plus(query)}&language=en&format=json&limit={limit}"
        data = await self._fetch_json(url)
        
        if not data or 'search' not in data:
            return results
        
        for item in data['search']:
            entity_id = item.get('id', '')
            description = item.get('description', '')
            label = item.get('label', '')
            
            if description:
                results.append(SourceResult(
                    source="Wikidata",
                    title=label,
                    content=f"{label}: {description}",
                    url=f"https://www.wikidata.org/wiki/{entity_id}",
                    confidence=0.85,
                    metadata={'entity_id': entity_id}
                ))
        
        return results


class NewsAdapter(SourceAdapter):
    """News aggregation adapter (using DuckDuckGo news)."""
    
    name = "News"
    priority = 4
    
    async def search(self, query: str, limit: int = 5) -> List[SourceResult]:
        results = []
        
        # Use DuckDuckGo news
        # Note: This is a workaround - in production you'd use NewsAPI or similar
        url = f"https://duckduckgo.com/news.js?q={quote_plus(query)}&o=json"
        
        # DuckDuckGo news requires different handling
        # For now, we'll use the HTML version and parse
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                headers = {'User-Agent': 'Mozilla/5.0'}
                async with session.get(
                    f"https://html.duckduckgo.com/html/?q={quote_plus(query)}+news",
                    headers=headers, timeout=10
                ) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        # Parse results (simplified)
                        # In production, use proper news APIs
                        pass
        except Exception as e:
            logger.warning(f"News fetch error: {e}")
        
        return results


class ArxivAdapter(SourceAdapter):
    """ArXiv academic papers adapter."""
    
    name = "ArXiv"
    priority = 5
    
    async def search(self, query: str, limit: int = 3) -> List[SourceResult]:
        results = []
        
        url = f"http://export.arxiv.org/api/query?search_query=all:{quote_plus(query)}&start=0&max_results={limit}"
        text = await self._fetch_text(url)
        
        if not text:
            return results
        
        # Parse Atom feed (simplified)
        import xml.etree.ElementTree as ET
        try:
            root = ET.fromstring(text)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns)
                summary = entry.find('atom:summary', ns)
                link = entry.find('atom:id', ns)
                
                if title is not None and summary is not None:
                    results.append(SourceResult(
                        source="ArXiv",
                        title=title.text.strip() if title.text else "",
                        content=summary.text.strip() if summary.text else "",
                        url=link.text if link is not None and link.text else "",
                        confidence=0.9,
                        metadata={'type': 'academic_paper'}
                    ))
        except ET.ParseError:
            pass
        
        return results


# ============================================================================
# VIDEO/TRANSCRIPT ADAPTERS
# ============================================================================

class YouTubeAdapter(SourceAdapter):
    """YouTube video and transcript adapter."""
    
    name = "YouTube"
    priority = 3
    
    async def search(self, query: str, limit: int = 5) -> List[SourceResult]:
        """Search for videos (returns as SourceResult)."""
        # Note: Full YouTube API requires API key
        # Using Invidious (open source YouTube frontend) as alternative
        return []
    
    async def search_videos(self, query: str, limit: int = 5) -> List[VideoResource]:
        """Search for videos with transcripts."""
        videos = []
        
        # Try Invidious API (no key needed)
        invidious_instances = [
            "https://vid.puffyan.us",
            "https://invidious.snopyta.org",
            "https://yewtu.be"
        ]
        
        for instance in invidious_instances:
            try:
                url = f"{instance}/api/v1/search?q={quote_plus(query)}&type=video"
                data = await self._fetch_json(url)
                
                if data:
                    for item in data[:limit]:
                        video_id = item.get('videoId', '')
                        
                        # Get transcript
                        transcript = await self._get_transcript(instance, video_id)
                        
                        videos.append(VideoResource(
                            title=item.get('title', ''),
                            url=f"https://youtube.com/watch?v={video_id}",
                            platform="YouTube",
                            duration=self._format_duration(item.get('lengthSeconds', 0)),
                            channel=item.get('author', ''),
                            transcript=transcript,
                            thumbnail=item.get('videoThumbnails', [{}])[0].get('url', ''),
                            views=self._format_views(item.get('viewCount', 0))
                        ))
                    
                    break  # Success, don't try other instances
                    
            except Exception as e:
                logger.warning(f"Invidious {instance} error: {e}")
                continue
        
        return videos
    
    async def _get_transcript(self, instance: str, video_id: str) -> str:
        """Get video transcript/captions."""
        try:
            url = f"{instance}/api/v1/captions/{video_id}"
            data = await self._fetch_json(url)
            
            if data and isinstance(data, list):
                # Find English captions
                for caption in data:
                    if caption.get('language_code', '').startswith('en'):
                        caption_url = f"{instance}{caption.get('url', '')}"
                        caption_text = await self._fetch_text(caption_url)
                        
                        if caption_text:
                            # Parse and clean VTT/SRT
                            return self._parse_captions(caption_text)
        except Exception as e:
            logger.debug(f"Transcript fetch error: {e}")
        
        return ""
    
    def _parse_captions(self, text: str) -> str:
        """Parse VTT/SRT caption text."""
        lines = []
        for line in text.split('\n'):
            # Skip timestamps and metadata
            if '-->' in line or line.strip().isdigit():
                continue
            if line.strip().startswith('WEBVTT'):
                continue
            if line.strip():
                # Remove HTML tags
                clean = re.sub(r'<[^>]+>', '', line)
                lines.append(clean.strip())
        
        return ' '.join(lines)
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration."""
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"
    
    def _format_views(self, views: int) -> str:
        """Format view count."""
        if views >= 1_000_000:
            return f"{views/1_000_000:.1f}M views"
        if views >= 1_000:
            return f"{views/1_000:.1f}K views"
        return f"{views} views"


# ============================================================================
# KNOWLEDGE SYNTHESIZER
# ============================================================================

class KnowledgeSynthesizer:
    """
    Synthesizes information from multiple sources into coherent responses.
    """
    
    def synthesize(self, query: str, sources: List[SourceResult], 
                   videos: List[VideoResource],
                   detail_level: str = "brief") -> KnowledgeResponse:
        """Synthesize all gathered knowledge."""
        
        if not sources and not videos:
            return KnowledgeResponse(
                query=query,
                summary=f"I couldn't find information about '{query}'.",
                detailed="No sources returned results for this query.",
                sources=[],
                videos=[],
                related_topics=[],
                confidence=0,
                retrieval_time=0,
                source_count=0
            )
        
        # Sort sources by confidence
        sources = sorted(sources, key=lambda x: x.confidence, reverse=True)
        
        # Generate summary (brief)
        summary = self._generate_summary(query, sources)
        
        # Generate detailed response
        detailed = self._generate_detailed(query, sources, videos)
        
        # Extract related topics
        related = self._extract_related_topics(sources)
        
        # Calculate overall confidence
        if sources:
            confidence = sum(s.confidence for s in sources) / len(sources)
        else:
            confidence = 0.5
        
        return KnowledgeResponse(
            query=query,
            summary=summary,
            detailed=detailed,
            sources=sources,
            videos=videos,
            related_topics=related,
            confidence=confidence,
            retrieval_time=0,  # Set by caller
            source_count=len(sources)
        )
    
    def _generate_summary(self, query: str, sources: List[SourceResult]) -> str:
        """Generate a brief summary from top sources."""
        if not sources:
            return f"No information found for '{query}'."
        
        # Use the highest confidence source for summary
        top_source = sources[0]
        content = top_source.content
        
        # Truncate to ~200 chars at sentence boundary
        if len(content) > 200:
            sentences = content.split('. ')
            summary = sentences[0]
            for s in sentences[1:]:
                if len(summary) + len(s) < 200:
                    summary += '. ' + s
                else:
                    break
            if not summary.endswith('.'):
                summary += '.'
        else:
            summary = content
        
        return summary
    
    def _generate_detailed(self, query: str, sources: List[SourceResult],
                           videos: List[VideoResource]) -> str:
        """Generate detailed response with all sources."""
        parts = []
        
        # Group sources by type
        by_source: Dict[str, List[SourceResult]] = {}
        for s in sources:
            source_name = s.source.split()[0]  # Get primary name
            by_source.setdefault(source_name, []).append(s)
        
        # Main content (from top sources)
        parts.append(f"## {query}\n")
        
        # Wikipedia first if available
        if 'Wikipedia' in by_source:
            wiki = by_source['Wikipedia'][0]
            parts.append(f"### Overview\n{wiki.content}\n")
        elif sources:
            parts.append(f"### Overview\n{sources[0].content}\n")
        
        # Additional perspectives
        other_sources = [s for s in sources[1:5] if 'Wikipedia' not in s.source]
        if other_sources:
            parts.append("\n### Additional Information\n")
            for s in other_sources:
                # Clean and truncate
                content = s.content[:300]
                if len(s.content) > 300:
                    content += "..."
                parts.append(f"**{s.source}:** {content}\n")
        
        # Community insights (Reddit, etc.)
        community = [s for s in sources if 'Reddit' in s.source or 'Quora' in s.source]
        if community:
            parts.append("\n### Community Perspectives\n")
            for s in community[:2]:
                parts.append(f"From {s.source}:\n> {s.content[:200]}...\n")
        
        # Academic (ArXiv)
        academic = [s for s in sources if s.source == 'ArXiv']
        if academic:
            parts.append("\n### Academic Research\n")
            for s in academic[:2]:
                parts.append(f"**{s.title}**\n{s.content[:200]}...\n")
        
        # Video resources
        if videos:
            parts.append("\n### Video Resources\n")
            for v in videos[:3]:
                parts.append(f"🎥 **{v.title}** ({v.duration})")
                parts.append(f"   Channel: {v.channel} | {v.views}")
                parts.append(f"   URL: {v.url}")
                if v.transcript:
                    # Show transcript excerpt
                    excerpt = v.transcript[:150] + "..." if len(v.transcript) > 150 else v.transcript
                    parts.append(f"   Transcript: \"{excerpt}\"")
                parts.append("")
        
        # Sources list
        parts.append("\n### Sources\n")
        seen_urls = set()
        for s in sources:
            if s.url and s.url not in seen_urls:
                parts.append(f"- [{s.source}]({s.url})")
                seen_urls.add(s.url)
        
        return '\n'.join(parts)
    
    def _extract_related_topics(self, sources: List[SourceResult]) -> List[str]:
        """Extract related topics from sources."""
        topics = set()
        
        for s in sources:
            # From metadata
            if 'tags' in s.metadata:
                topics.update(s.metadata['tags'][:3])
            
            # From content (simple extraction)
            # Look for capitalized phrases
            words = s.content.split()
            for i, word in enumerate(words[:-1]):
                if word[0].isupper() and words[i+1][0].isupper():
                    phrase = f"{word} {words[i+1]}"
                    if len(phrase) < 30:
                        topics.add(phrase)
        
        return list(topics)[:5]


# ============================================================================
# MAIN KNOWLEDGE ENGINE
# ============================================================================

class KnowledgeEngine:
    """
    Main knowledge aggregation engine.
    
    Queries multiple sources in parallel, synthesizes results.
    """
    
    def __init__(self):
        self.adapters: List[SourceAdapter] = [
            WikipediaAdapter(),
            DuckDuckGoAdapter(),
            RedditAdapter(),
            StackExchangeAdapter(),
            WikidataAdapter(),
            ArxivAdapter(),
        ]
        self.video_adapter = YouTubeAdapter()
        self.synthesizer = KnowledgeSynthesizer()
        
        # Cache
        self._cache: Dict[str, KnowledgeResponse] = {}
        self._cache_ttl = 3600  # 1 hour
    
    async def query(self, query: str, 
                    detail_level: str = "brief",
                    include_videos: bool = False,
                    include_academic: bool = False,
                    max_sources: int = 10) -> KnowledgeResponse:
        """
        Query all sources and synthesize response.
        
        Args:
            query: The search query
            detail_level: "brief" or "detailed"
            include_videos: Whether to include video resources
            include_academic: Whether to include ArXiv papers
            max_sources: Maximum sources to use
        """
        start_time = time.time()
        
        # Check cache
        cache_key = f"{query}:{detail_level}:{include_videos}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached.retrieval_time < self._cache_ttl:
                return cached
        
        # Select adapters
        adapters = self.adapters.copy()
        if not include_academic:
            adapters = [a for a in adapters if a.name != "ArXiv"]
        
        # Query all sources in parallel
        tasks = [adapter.search(query) for adapter in adapters]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results
        all_sources: List[SourceResult] = []
        for result in results:
            if isinstance(result, list):
                all_sources.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"Source error: {result}")
        
        # Get videos if requested
        videos: List[VideoResource] = []
        if include_videos:
            videos = await self.video_adapter.search_videos(query)
        
        # Limit sources
        all_sources = sorted(all_sources, key=lambda x: x.confidence, reverse=True)
        all_sources = all_sources[:max_sources]
        
        # Synthesize
        response = self.synthesizer.synthesize(query, all_sources, videos, detail_level)
        response.retrieval_time = time.time() - start_time
        
        # Cache
        self._cache[cache_key] = response
        
        return response
    
    async def ask_brief(self, query: str) -> str:
        """Get a brief answer."""
        response = await self.query(query, detail_level="brief")
        return response.summary
    
    async def ask_detailed(self, query: str, include_videos: bool = True) -> str:
        """Get a detailed answer with sources."""
        response = await self.query(query, detail_level="detailed", 
                                    include_videos=include_videos)
        return response.detailed
    
    def format_for_speech(self, response: KnowledgeResponse) -> str:
        """Format response for text-to-speech."""
        # Just the summary, cleaned up
        text = response.summary
        
        # Remove markdown
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # Limit length
        if len(text) > 300:
            sentences = text.split('. ')
            text = '. '.join(sentences[:3])
            if not text.endswith('.'):
                text += '.'
        
        return text


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_engine: Optional[KnowledgeEngine] = None


def get_engine() -> KnowledgeEngine:
    """Get the global knowledge engine."""
    global _engine
    if _engine is None:
        _engine = KnowledgeEngine()
    return _engine


async def ask_knowledge(query: str, 
                        detail_level: str = "brief",
                        include_videos: bool = False) -> str:
    """
    Simple interface to ask about any topic.
    
    Usage:
        answer = await ask_knowledge("What is machine learning?")
        print(answer)
        
        # Detailed with videos
        answer = await ask_knowledge("How to learn Python?", 
                                     detail_level="detailed",
                                     include_videos=True)
    """
    engine = get_engine()
    response = await engine.query(query, detail_level, include_videos)
    
    if detail_level == "brief":
        return response.summary
    return response.detailed


async def research(query: str) -> KnowledgeResponse:
    """
    Do comprehensive research on a topic.
    
    Returns full KnowledgeResponse with all sources.
    """
    engine = get_engine()
    return await engine.query(
        query, 
        detail_level="detailed",
        include_videos=True,
        include_academic=True,
        max_sources=15
    )


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demo the knowledge engine."""
    print("=" * 60)
    print("KNOWLEDGE AGGREGATION ENGINE DEMO")
    print("=" * 60)
    
    engine = KnowledgeEngine()
    
    queries = [
        ("What is quantum computing?", "brief", False),
        ("Who is Elon Musk?", "brief", False),
        ("How to learn Python programming?", "detailed", True),
    ]
    
    for query, detail, videos in queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"Detail: {detail}, Videos: {videos}")
        print("-" * 60)
        
        response = await engine.query(query, detail, videos)
        
        if detail == "brief":
            print(f"\n📝 Summary:\n{response.summary}")
        else:
            print(f"\n📚 Detailed Response:\n{response.detailed}")
        
        print(f"\n📊 Stats:")
        print(f"   - Sources: {response.source_count}")
        print(f"   - Videos: {len(response.videos)}")
        print(f"   - Confidence: {response.confidence:.0%}")
        print(f"   - Time: {response.retrieval_time:.2f}s")
        
        if response.related_topics:
            print(f"   - Related: {', '.join(response.related_topics[:3])}")


if __name__ == "__main__":
    asyncio.run(demo())
