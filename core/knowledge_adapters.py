"""
VoxMind Additional Source Adapters
==================================
More source adapters for comprehensive knowledge retrieval.

Includes:
- Quora (via web parsing)
- GitHub (code examples)
- Twitter/X (social media)
- Medium (articles)
- HackerNews (tech community)
- Google Scholar (academic)
"""

import asyncio
import re
import json
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus
from dataclasses import dataclass, field

from core.knowledge_engine import SourceAdapter, SourceResult, VideoResource

logger = logging.getLogger('VoxMind.Knowledge.Adapters')


class QuoraAdapter(SourceAdapter):
    """
    Quora answers adapter.
    Uses web parsing since Quora has no public API.
    """
    
    name = "Quora"
    priority = 4
    
    async def search(self, query: str, limit: int = 3) -> List[SourceResult]:
        results = []
        
        # Quora blocks most scrapers, so we use DuckDuckGo to find Quora answers
        url = f"https://api.duckduckgo.com/?q=site:quora.com+{quote_plus(query)}&format=json"
        data = await self._fetch_json(url)
        
        if data and data.get('RelatedTopics'):
            for topic in data['RelatedTopics'][:limit]:
                if isinstance(topic, dict) and 'quora.com' in topic.get('FirstURL', ''):
                    results.append(SourceResult(
                        source="Quora",
                        title=topic.get('Text', '')[:100],
                        content=topic.get('Text', ''),
                        url=topic.get('FirstURL', ''),
                        confidence=0.65
                    ))
        
        return results


class GitHubAdapter(SourceAdapter):
    """
    GitHub code search adapter.
    Great for finding code examples and documentation.
    """
    
    name = "GitHub"
    priority = 4
    
    async def search(self, query: str, limit: int = 5) -> List[SourceResult]:
        results = []
        
        # Use GitHub search API (no auth needed for basic search)
        url = f"https://api.github.com/search/repositories?q={quote_plus(query)}&sort=stars&per_page={limit}"
        headers = {'Accept': 'application/vnd.github.v3+json'}
        data = await self._fetch_json(url, headers)
        
        if data and 'items' in data:
            for repo in data['items']:
                description = repo.get('description', '') or 'No description'
                
                results.append(SourceResult(
                    source="GitHub",
                    title=repo.get('full_name', ''),
                    content=f"{description}\n\nStars: {repo.get('stargazers_count', 0):,} | "
                           f"Language: {repo.get('language', 'Unknown')} | "
                           f"Forks: {repo.get('forks_count', 0):,}",
                    url=repo.get('html_url', ''),
                    confidence=0.7,
                    metadata={
                        'stars': repo.get('stargazers_count', 0),
                        'language': repo.get('language'),
                        'topics': repo.get('topics', [])
                    }
                ))
        
        return results
    
    async def search_code(self, query: str, language: str = None, 
                          limit: int = 5) -> List[SourceResult]:
        """Search for code snippets."""
        results = []
        
        q = query
        if language:
            q += f" language:{language}"
        
        url = f"https://api.github.com/search/code?q={quote_plus(q)}&per_page={limit}"
        headers = {'Accept': 'application/vnd.github.v3+json'}
        data = await self._fetch_json(url, headers)
        
        if data and 'items' in data:
            for item in data['items']:
                results.append(SourceResult(
                    source="GitHub Code",
                    title=item.get('name', ''),
                    content=f"Repository: {item.get('repository', {}).get('full_name', '')}\n"
                           f"Path: {item.get('path', '')}",
                    url=item.get('html_url', ''),
                    confidence=0.75,
                    metadata={'path': item.get('path', '')}
                ))
        
        return results


class HackerNewsAdapter(SourceAdapter):
    """
    Hacker News adapter.
    Great for tech discussions and opinions.
    """
    
    name = "HackerNews"
    priority = 5
    
    async def search(self, query: str, limit: int = 5) -> List[SourceResult]:
        results = []
        
        # Use Algolia HN Search API
        url = f"https://hn.algolia.com/api/v1/search?query={quote_plus(query)}&tags=story&hitsPerPage={limit}"
        data = await self._fetch_json(url)
        
        if data and 'hits' in data:
            for hit in data['hits']:
                title = hit.get('title', '')
                url_link = hit.get('url') or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                
                # Get comment preview as content
                content = f"Title: {title}\n"
                content += f"Points: {hit.get('points', 0)} | Comments: {hit.get('num_comments', 0)}\n"
                if hit.get('story_text'):
                    content += hit['story_text'][:500]
                
                results.append(SourceResult(
                    source="Hacker News",
                    title=title,
                    content=content,
                    url=url_link,
                    confidence=0.65,
                    metadata={
                        'points': hit.get('points', 0),
                        'comments': hit.get('num_comments', 0),
                        'author': hit.get('author', '')
                    }
                ))
        
        return results


class MediumAdapter(SourceAdapter):
    """
    Medium articles adapter.
    Uses RSS feeds since Medium has no public API.
    """
    
    name = "Medium"
    priority = 5
    
    async def search(self, query: str, limit: int = 3) -> List[SourceResult]:
        results = []
        
        # Medium doesn't have a search API, use DuckDuckGo
        url = f"https://api.duckduckgo.com/?q=site:medium.com+{quote_plus(query)}&format=json"
        data = await self._fetch_json(url)
        
        if data and data.get('RelatedTopics'):
            for topic in data['RelatedTopics'][:limit]:
                if isinstance(topic, dict) and 'medium.com' in topic.get('FirstURL', ''):
                    results.append(SourceResult(
                        source="Medium",
                        title=topic.get('Text', '')[:100],
                        content=topic.get('Text', ''),
                        url=topic.get('FirstURL', ''),
                        confidence=0.6
                    ))
        
        return results


class TwitterAdapter(SourceAdapter):
    """
    Twitter/X adapter.
    Note: Twitter API requires authentication. This uses alternative methods.
    """
    
    name = "Twitter"
    priority = 6
    
    async def search(self, query: str, limit: int = 5) -> List[SourceResult]:
        results = []
        
        # Twitter/X requires auth. Use Nitter (open source frontend) as alternative
        nitter_instances = [
            "https://nitter.net",
            "https://nitter.it",
        ]
        
        for instance in nitter_instances:
            try:
                # Note: This may not work as Nitter instances come and go
                # In production, use official Twitter API with auth
                url = f"{instance}/search?q={quote_plus(query)}"
                # Would need to parse HTML here
                break
            except Exception as e:
                continue
        
        # Fallback to DuckDuckGo for Twitter results
        url = f"https://api.duckduckgo.com/?q=site:twitter.com+{quote_plus(query)}&format=json"
        data = await self._fetch_json(url)
        
        if data and data.get('RelatedTopics'):
            for topic in data['RelatedTopics'][:limit]:
                if isinstance(topic, dict) and 'twitter.com' in topic.get('FirstURL', ''):
                    results.append(SourceResult(
                        source="Twitter",
                        title=topic.get('Text', '')[:100],
                        content=topic.get('Text', ''),
                        url=topic.get('FirstURL', ''),
                        confidence=0.55
                    ))
        
        return results


class GoogleScholarAdapter(SourceAdapter):
    """
    Google Scholar adapter for academic sources.
    Uses Semantic Scholar API as alternative (free, no auth).
    """
    
    name = "Google Scholar"
    priority = 4
    
    async def search(self, query: str, limit: int = 3) -> List[SourceResult]:
        results = []
        
        # Use Semantic Scholar API (free alternative to Google Scholar)
        url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={quote_plus(query)}&limit={limit}&fields=title,abstract,authors,year,citationCount,url"
        data = await self._fetch_json(url)
        
        if data and 'data' in data:
            for paper in data['data']:
                authors = ', '.join([a.get('name', '') for a in paper.get('authors', [])[:3]])
                if len(paper.get('authors', [])) > 3:
                    authors += ' et al.'
                
                abstract = paper.get('abstract', '') or 'No abstract available'
                
                results.append(SourceResult(
                    source="Semantic Scholar",
                    title=paper.get('title', ''),
                    content=f"Authors: {authors}\nYear: {paper.get('year', 'N/A')}\n"
                           f"Citations: {paper.get('citationCount', 0)}\n\n{abstract[:500]}",
                    url=paper.get('url', ''),
                    confidence=0.9,
                    metadata={
                        'year': paper.get('year'),
                        'citations': paper.get('citationCount', 0),
                        'authors': authors
                    }
                ))
        
        return results


class VimeoAdapter(SourceAdapter):
    """
    Vimeo video adapter.
    Vimeo has a more open API than YouTube.
    """
    
    name = "Vimeo"
    priority = 5
    
    async def search(self, query: str, limit: int = 3) -> List[SourceResult]:
        """Search returns as SourceResult."""
        return []
    
    async def search_videos(self, query: str, limit: int = 3) -> List[VideoResource]:
        """Search for videos."""
        videos = []
        
        # Vimeo search requires OAuth for full API
        # Use their oEmbed for basic info if we have a URL
        # For search, we'd need to use their authenticated API
        
        return videos


class DailyMotionAdapter(SourceAdapter):
    """
    DailyMotion video adapter.
    Has a free API.
    """
    
    name = "DailyMotion"
    priority = 6
    
    async def search(self, query: str, limit: int = 3) -> List[SourceResult]:
        return []
    
    async def search_videos(self, query: str, limit: int = 3) -> List[VideoResource]:
        """Search for videos."""
        videos = []
        
        url = f"https://api.dailymotion.com/videos?search={quote_plus(query)}&limit={limit}&fields=id,title,description,duration,owner.screenname,views_total,thumbnail_url"
        data = await self._fetch_json(url)
        
        if data and 'list' in data:
            for video in data['list']:
                videos.append(VideoResource(
                    title=video.get('title', ''),
                    url=f"https://www.dailymotion.com/video/{video.get('id', '')}",
                    platform="DailyMotion",
                    duration=self._format_duration(video.get('duration', 0)),
                    channel=video.get('owner.screenname', ''),
                    transcript="",  # DailyMotion doesn't provide easy transcript access
                    thumbnail=video.get('thumbnail_url', ''),
                    views=self._format_views(video.get('views_total', 0))
                ))
        
        return videos
    
    def _format_duration(self, seconds: int) -> str:
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
    
    def _format_views(self, views: int) -> str:
        if views >= 1_000_000:
            return f"{views/1_000_000:.1f}M views"
        if views >= 1_000:
            return f"{views/1_000:.1f}K views"
        return f"{views} views"


# ============================================================================
# EXTENDED KNOWLEDGE ENGINE
# ============================================================================

class ExtendedKnowledgeEngine:
    """
    Extended knowledge engine with all additional adapters.
    """
    
    def __init__(self):
        from core.knowledge_engine import (
            KnowledgeEngine, WikipediaAdapter, DuckDuckGoAdapter,
            RedditAdapter, StackExchangeAdapter, WikidataAdapter,
            ArxivAdapter, YouTubeAdapter, KnowledgeSynthesizer
        )
        
        # All adapters
        self.adapters = [
            # Core (high priority)
            WikipediaAdapter(),
            DuckDuckGoAdapter(),
            WikidataAdapter(),
            
            # Community
            RedditAdapter(),
            StackExchangeAdapter(),
            QuoraAdapter(),
            HackerNewsAdapter(),
            
            # Social/News
            TwitterAdapter(),
            MediumAdapter(),
            
            # Academic
            ArxivAdapter(),
            GoogleScholarAdapter(),
            
            # Code
            GitHubAdapter(),
        ]
        
        # Video adapters
        self.video_adapters = [
            YouTubeAdapter(),
            DailyMotionAdapter(),
        ]
        
        self.synthesizer = KnowledgeSynthesizer()
    
    async def comprehensive_search(self, query: str,
                                   include_videos: bool = True,
                                   include_social: bool = True,
                                   include_academic: bool = True,
                                   include_code: bool = False) -> Dict[str, Any]:
        """
        Comprehensive search across all sources.
        """
        from core.knowledge_engine import KnowledgeResponse
        
        # Filter adapters based on options
        adapters = []
        for a in self.adapters:
            if not include_social and a.name in ['Twitter', 'Reddit', 'HackerNews']:
                continue
            if not include_academic and a.name in ['ArXiv', 'Google Scholar', 'Semantic Scholar']:
                continue
            if not include_code and a.name in ['GitHub']:
                continue
            adapters.append(a)
        
        # Search all sources in parallel
        tasks = [a.search(query) for a in adapters]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten
        all_sources = []
        source_breakdown = {}
        
        for adapter, result in zip(adapters, results):
            if isinstance(result, list):
                all_sources.extend(result)
                source_breakdown[adapter.name] = len(result)
            else:
                source_breakdown[adapter.name] = f"Error: {result}"
        
        # Get videos
        all_videos = []
        if include_videos:
            video_tasks = [a.search_videos(query) for a in self.video_adapters 
                          if hasattr(a, 'search_videos')]
            video_results = await asyncio.gather(*video_tasks, return_exceptions=True)
            
            for result in video_results:
                if isinstance(result, list):
                    all_videos.extend(result)
        
        # Synthesize
        response = self.synthesizer.synthesize(query, all_sources, all_videos, "detailed")
        
        return {
            'query': query,
            'summary': response.summary,
            'detailed': response.detailed,
            'sources': all_sources,
            'videos': all_videos,
            'source_breakdown': source_breakdown,
            'total_sources': len(all_sources),
            'total_videos': len(all_videos)
        }


# ============================================================================
# REGISTER WITH KNOWLEDGE ENGINE
# ============================================================================

def register_all_adapters():
    """Register all additional adapters with the main engine."""
    from core.knowledge_engine import get_engine
    
    engine = get_engine()
    
    additional_adapters = [
        QuoraAdapter(),
        GitHubAdapter(),
        HackerNewsAdapter(),
        MediumAdapter(),
        TwitterAdapter(),
        GoogleScholarAdapter(),
    ]
    
    for adapter in additional_adapters:
        if adapter not in engine.adapters:
            engine.adapters.append(adapter)
    
    return engine


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demo extended knowledge search."""
    print("=" * 60)
    print("EXTENDED KNOWLEDGE SEARCH DEMO")
    print("=" * 60)
    
    engine = ExtendedKnowledgeEngine()
    
    query = "What is machine learning and how do I get started?"
    print(f"\nQuery: {query}\n")
    
    result = await engine.comprehensive_search(
        query,
        include_videos=True,
        include_social=True,
        include_academic=True,
        include_code=True
    )
    
    print(f"Sources found: {result['total_sources']}")
    print(f"Videos found: {result['total_videos']}")
    print(f"\nSource breakdown:")
    for source, count in result['source_breakdown'].items():
        print(f"  - {source}: {count}")
    
    print(f"\n{'='*60}")
    print("SUMMARY:")
    print("=" * 60)
    print(result['summary'])
    
    print(f"\n{'='*60}")
    print("DETAILED (first 2000 chars):")
    print("=" * 60)
    print(result['detailed'][:2000])


if __name__ == "__main__":
    asyncio.run(demo())
