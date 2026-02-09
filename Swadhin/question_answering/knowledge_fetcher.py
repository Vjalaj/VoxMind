"""
Knowledge Fetcher for VoxMind
==============================
Fetches large chunks of information from multiple online sources.

Integrates with the existing knowledge_engine but adds:
- Bulk content retrieval
- Deep page scraping
- Multi-source aggregation for comprehensive answers
- Source reliability scoring
"""

import asyncio
import re
import time
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import quote_plus, urlparse

logger = logging.getLogger(__name__)


@dataclass
class FetchedContent:
    """Content fetched from a source."""
    source: str
    title: str
    content: str
    url: str
    content_type: str  # 'article', 'discussion', 'answer', 'definition', 'tutorial'
    reliability_score: float = 0.8
    word_count: int = 0
    sections: List[Dict[str, str]] = field(default_factory=list)
    key_points: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregatedKnowledge:
    """Aggregated knowledge from multiple sources."""
    query: str
    total_sources: int
    total_words: int
    contents: List[FetchedContent]
    main_facts: List[str]
    different_perspectives: List[Dict[str, str]]
    consensus_points: List[str]
    debate_points: List[str]
    timeline: List[Dict[str, str]]
    retrieval_time: float


class KnowledgeFetcher:
    """
    Fetches comprehensive knowledge from multiple sources.
    Designed to get LARGE chunks of information for elaborate answers.
    """
    
    # Default headers
    HEADERS = {
        'User-Agent': 'VoxMind/2.0 (Knowledge Assistant; Elaborate QA System)',
        'Accept': 'text/html,application/json,application/xhtml+xml',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    # Source reliability weights
    SOURCE_RELIABILITY = {
        'wikipedia': 0.95,
        'britannica': 0.95,
        'scholarpedia': 0.93,
        'stackexchange': 0.85,
        'stackoverflow': 0.85,
        'reddit': 0.65,
        'quora': 0.60,
        'news': 0.70,
        'blog': 0.50,
        'forum': 0.45,
        'other': 0.40,
    }
    
    def __init__(self):
        """Initialize the fetcher."""
        self._session = None
        self._cache: Dict[str, AggregatedKnowledge] = {}
        self._cache_ttl = 1800  # 30 minutes
        self._default_timeout = None  # Will be set on first use
        self._loop_id = None  # Track which event loop our session belongs to
    
    async def _get_session(self):
        """Get or create aiohttp session. Creates new session if event loop changed."""
        import aiohttp
        current_loop_id = id(asyncio.get_event_loop())
        
        # If event loop changed, close old session and create new one
        if self._session is not None and self._loop_id != current_loop_id:
            try:
                if not self._session.closed:
                    await self._session.close()
            except Exception:
                pass
            self._session = None
        
        if self._session is None or self._session.closed:
            self._default_timeout = aiohttp.ClientTimeout(total=10)
            self._session = aiohttp.ClientSession(headers=self.HEADERS)
            self._loop_id = current_loop_id
        return self._session
    
    async def _get_timeout(self, seconds: int = 10):
        """Get a ClientTimeout object."""
        import aiohttp
        return aiohttp.ClientTimeout(total=seconds)
    
    async def close(self):
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def fetch_comprehensive(
        self,
        queries: List[str],
        question_type: str = "what",
        max_sources: int = 10,
        min_content_length: int = 200,
        include_discussions: bool = True,
        include_academic: bool = False,
    ) -> AggregatedKnowledge:
        """
        Fetch comprehensive knowledge for a set of queries.
        
        Args:
            queries: List of search queries to execute
            question_type: Type of question (affects source priority)
            max_sources: Maximum sources to aggregate
            min_content_length: Minimum content length to include
            include_discussions: Include Reddit/Quora discussions
            include_academic: Include academic sources
            
        Returns:
            AggregatedKnowledge with all collected information
        """
        start_time = time.time()
        
        # Check cache
        cache_key = "|".join(sorted(queries))
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached.retrieval_time < self._cache_ttl:
                logger.info(f"Returning cached knowledge for: {queries[0]}")
                return cached
        
        # Gather from all sources in parallel
        all_contents: List[FetchedContent] = []
        
        fetch_tasks = []
        
        # Always fetch from core sources (Wikipedia is primary for factual content)
        fetch_tasks.append(self._fetch_wikipedia_bulk(queries))
        fetch_tasks.append(self._fetch_duckduckgo_bulk(queries))
        
        # StackExchange ONLY for technical/programming questions, not general knowledge
        # Check if query looks technical (programming, coding, software, etc.)
        technical_keywords = ['code', 'programming', 'python', 'javascript', 'software', 
                              'algorithm', 'database', 'api', 'function', 'error', 'bug',
                              'install', 'compile', 'debug', 'server', 'linux', 'windows']
        is_technical = any(kw in queries[0].lower() for kw in technical_keywords)
        
        if question_type == 'how' and is_technical:
            fetch_tasks.append(self._fetch_stackexchange(queries))
        
        # Only include Reddit for opinion-based questions, NOT factual topics
        # Factual question types: what, when, where, who, is_boolean
        factual_types = ('what', 'when', 'where', 'who', 'is_boolean')
        if include_discussions and question_type not in factual_types:
            # Only for 'why', 'how', 'which', 'if' - where opinions/discussion matter
            fetch_tasks.append(self._fetch_reddit_discussions(queries))
        
        if include_academic and question_type in ('why', 'what', 'how'):
            fetch_tasks.append(self._fetch_arxiv(queries))
        
        # Fetch Wikidata for factual questions
        if question_type in ('when', 'where', 'who', 'is_boolean'):
            fetch_tasks.append(self._fetch_wikidata(queries))
        
        # Execute all fetches in parallel
        results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
        
        # Collect results
        for result in results:
            if isinstance(result, list):
                all_contents.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"Fetch error: {result}")
        
        # Extract topic keywords from queries for relevance filtering
        topic_keywords = self._extract_topic_keywords(queries)
        
        # Filter by minimum content length AND relevance to topic
        filtered_contents = []
        for c in all_contents:
            if len(c.content) < min_content_length:
                continue
            # Check if content is relevant to the topic
            if self._is_content_relevant(c.content, topic_keywords):
                # Re-extract key points with topic filtering
                c.key_points = self._extract_key_points(c.content, topic_keywords)
                filtered_contents.append(c)
        
        all_contents = filtered_contents
        
        # Sort by reliability (strongly prioritize Wikipedia), then content length
        # Wikipedia reliability is 0.95, give it extra boost
        def sort_key(x):
            # Give Wikipedia a significant boost
            base_score = x.reliability_score
            if x.source == 'Wikipedia':
                base_score += 0.5  # Ensure Wikipedia always comes first
            elif 'Reddit' in x.source:
                base_score -= 0.3  # Penalize Reddit for factual queries
            return (base_score, x.word_count)
        
        all_contents.sort(key=sort_key, reverse=True)
        
        # Limit sources
        all_contents = all_contents[:max_sources]
        
        # Calculate word counts
        for content in all_contents:
            content.word_count = len(content.content.split())
        
        # Aggregate and analyze
        knowledge = self._aggregate_knowledge(queries[0], all_contents)
        knowledge.retrieval_time = time.time() - start_time
        
        # Cache
        self._cache[cache_key] = knowledge
        
        return knowledge
    
    async def _fetch_wikipedia_bulk(self, queries: List[str]) -> List[FetchedContent]:
        """Fetch full Wikipedia articles for queries."""
        contents = []
        
        try:
            session = await self._get_session()
            timeout = await self._get_timeout(15)
            
            # Wikipedia requires a descriptive User-Agent
            wiki_headers = {
                'User-Agent': 'VoxMind/2.0 (Voice Assistant; https://github.com/voxmind; priyapal@example.com)',
                'Accept': 'application/json',
            }
            
            for query in queries[:3]:  # Limit to 3 queries
                try:
                    # Search for pages
                    search_url = (
                        f"https://en.wikipedia.org/w/api.php?"
                        f"action=query&format=json&list=search"
                        f"&srsearch={quote_plus(query)}&srlimit=2"
                    )
                    
                    async with session.get(search_url, headers=wiki_headers, timeout=timeout) as resp:
                        if resp.status != 200:
                            logger.warning(f"Wikipedia search returned {resp.status}")
                            continue
                        data = await resp.json(content_type=None)
                    
                    search_results = data.get('query', {}).get('search', [])
                    
                    for result in search_results[:2]:
                        page_title = result.get('title', '')
                        if not page_title:
                            continue
                        
                        # Get full extract
                        extract_url = (
                            f"https://en.wikipedia.org/w/api.php?"
                            f"action=query&format=json&prop=extracts"
                            f"&exintro=false&explaintext=true&exsectionformat=plain"
                            f"&titles={quote_plus(page_title)}"
                        )
                        
                        async with session.get(extract_url, headers=wiki_headers, timeout=timeout) as resp:
                            if resp.status != 200:
                                continue
                            data = await resp.json(content_type=None)
                        
                        pages = data.get('query', {}).get('pages', {})
                        for page_id, page in pages.items():
                            if page_id == '-1':
                                continue
                            
                            extract = page.get('extract', '')
                            if not extract:
                                continue
                            
                            # Parse sections
                            sections = self._parse_wikipedia_sections(extract)
                            
                            contents.append(FetchedContent(
                                source='Wikipedia',
                                title=page.get('title', query),
                                content=extract,
                                url=f"https://en.wikipedia.org/wiki/{quote_plus(page_title.replace(' ', '_'))}",
                                content_type='article',
                                reliability_score=0.95,
                                sections=sections,
                                key_points=self._extract_key_points(extract),
                            ))
                except Exception as e:
                    logger.debug(f"Wikipedia query error for '{query}': {e}")
                    continue
                        
        except asyncio.TimeoutError:
            logger.warning("Wikipedia fetch timeout")
        except Exception as e:
            logger.warning(f"Wikipedia fetch error: {e}")
        
        return contents
    
    async def _fetch_duckduckgo_bulk(self, queries: List[str]) -> List[FetchedContent]:
        """Fetch from DuckDuckGo instant answers and search."""
        contents = []
        
        try:
            session = await self._get_session()
            timeout = await self._get_timeout(10)
            
            for query in queries[:3]:
                # Instant answer API - use no_redirect=1 and skip_disambig=1 for better JSON
                url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&skip_disambig=1"
                
                try:
                    async with session.get(url, timeout=timeout) as resp:
                        if resp.status != 200:
                            continue
                        
                        # Check content type - DuckDuckGo sometimes returns JS
                        content_type = resp.headers.get('Content-Type', '')
                        if 'json' not in content_type.lower() and 'javascript' in content_type.lower():
                            # Skip if it's JavaScript instead of JSON
                            continue
                        
                        try:
                            data = await resp.json(content_type=None)  # Accept any content type
                        except Exception:
                            continue
                        
                        # Abstract (main answer)
                        abstract = data.get('Abstract', '')
                        if abstract and len(abstract) > 100:
                            contents.append(FetchedContent(
                                source='DuckDuckGo',
                                title=data.get('Heading', query),
                                content=abstract,
                                url=data.get('AbstractURL', ''),
                                content_type='definition',
                                reliability_score=0.85,
                                key_points=[abstract[:200]],
                            ))
                        
                        # Related topics
                        for topic in data.get('RelatedTopics', [])[:5]:
                            if isinstance(topic, dict):
                                text = topic.get('Text', '')
                                if text and len(text) > 50:
                                    contents.append(FetchedContent(
                                        source='DuckDuckGo Related',
                                        title=topic.get('FirstURL', '').split('/')[-1].replace('_', ' '),
                                        content=text,
                                        url=topic.get('FirstURL', ''),
                                        content_type='related',
                                        reliability_score=0.75,
                                    ))
                except Exception as e:
                    logger.debug(f"DuckDuckGo query error for '{query}': {e}")
                    continue
                
        except asyncio.TimeoutError:
            logger.warning("DuckDuckGo fetch timeout")
        except Exception as e:
            logger.warning(f"DuckDuckGo fetch error: {e}")
        
        return contents
    
    async def _fetch_reddit_discussions(self, queries: List[str]) -> List[FetchedContent]:
        """Fetch Reddit discussions for different perspectives."""
        contents = []
        
        try:
            session = await self._get_session()
            timeout = await self._get_timeout(10)
            
            for query in queries[:2]:
                # Search Reddit
                url = (
                    f"https://www.reddit.com/search.json?"
                    f"q={quote_plus(query)}&limit=5&sort=relevance&t=all"
                )
                
                headers = {**self.HEADERS, 'User-Agent': 'VoxMind/2.0'}
                
                async with session.get(url, headers=headers, timeout=timeout) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.json()
                
                posts = data.get('data', {}).get('children', [])
                
                for post in posts[:3]:
                    post_data = post.get('data', {})
                    
                    title = post_data.get('title', '')
                    selftext = post_data.get('selftext', '')
                    subreddit = post_data.get('subreddit', '')
                    
                    if selftext and len(selftext) > 100:
                        contents.append(FetchedContent(
                            source=f'Reddit r/{subreddit}',
                            title=title,
                            content=selftext[:3000],  # Limit content
                            url=f"https://reddit.com{post_data.get('permalink', '')}",
                            content_type='discussion',
                            reliability_score=0.65,
                            metadata={
                                'score': post_data.get('score', 0),
                                'num_comments': post_data.get('num_comments', 0),
                                'subreddit': subreddit,
                            }
                        ))
                        
        except asyncio.TimeoutError:
            logger.warning("Reddit fetch timeout")
        except Exception as e:
            logger.warning(f"Reddit fetch error: {e}")
        
        return contents
    
    async def _fetch_stackexchange(self, queries: List[str]) -> List[FetchedContent]:
        """Fetch from StackExchange network."""
        contents = []
        
        try:
            session = await self._get_session()
            timeout = await self._get_timeout(10)
            
            for query in queries[:2]:
                # Search Stack Overflow and related sites
                for site in ['stackoverflow', 'superuser', 'askubuntu']:
                    url = (
                        f"https://api.stackexchange.com/2.3/search/advanced?"
                        f"order=desc&sort=relevance&q={quote_plus(query)}"
                        f"&site={site}&filter=withbody"
                    )
                    
                    async with session.get(url, timeout=timeout) as resp:
                        if resp.status != 200:
                            continue
                        data = await resp.json()
                    
                    items = data.get('items', [])[:2]
                    
                    for item in items:
                        body = item.get('body', '')
                        # Clean HTML
                        body = re.sub(r'<[^>]+>', ' ', body)
                        body = re.sub(r'\s+', ' ', body).strip()
                        
                        if body and len(body) > 100:
                            contents.append(FetchedContent(
                                source=f'StackExchange ({site})',
                                title=item.get('title', query),
                                content=body[:2000],
                                url=item.get('link', ''),
                                content_type='answer',
                                reliability_score=0.85,
                                metadata={
                                    'score': item.get('score', 0),
                                    'is_answered': item.get('is_answered', False),
                                }
                            ))
                            
        except asyncio.TimeoutError:
            logger.warning("StackExchange fetch timeout")
        except Exception as e:
            logger.warning(f"StackExchange fetch error: {e}")
        
        return contents
    
    async def _fetch_wikidata(self, queries: List[str]) -> List[FetchedContent]:
        """Fetch structured facts from Wikidata."""
        contents = []
        
        try:
            session = await self._get_session()
            timeout = await self._get_timeout(10)
            
            for query in queries[:2]:
                # Search Wikidata
                search_url = (
                    f"https://www.wikidata.org/w/api.php?"
                    f"action=wbsearchentities&search={quote_plus(query)}"
                    f"&language=en&format=json&limit=3"
                )
                
                async with session.get(search_url, timeout=timeout) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.json()
                
                entities = data.get('search', [])
                
                for entity in entities[:2]:
                    entity_id = entity.get('id', '')
                    label = entity.get('label', '')
                    description = entity.get('description', '')
                    
                    if entity_id and description:
                        # Get more details
                        entity_url = (
                            f"https://www.wikidata.org/w/api.php?"
                            f"action=wbgetentities&ids={entity_id}"
                            f"&languages=en&format=json"
                        )
                        
                        async with session.get(entity_url, timeout=timeout) as resp:
                            if resp.status != 200:
                                continue
                            entity_data = await resp.json()
                        
                        entities_data = entity_data.get('entities', {})
                        entity_info = entities_data.get(entity_id, {})
                        
                        # Extract claims (facts)
                        claims = entity_info.get('claims', {})
                        facts = self._extract_wikidata_facts(claims)
                        
                        content = f"{label}: {description}\n\n"
                        if facts:
                            content += "Key Facts:\n" + "\n".join(f"- {f}" for f in facts)
                        
                        contents.append(FetchedContent(
                            source='Wikidata',
                            title=label,
                            content=content,
                            url=f"https://www.wikidata.org/wiki/{entity_id}",
                            content_type='definition',
                            reliability_score=0.90,
                            key_points=facts[:5],
                        ))
                        
        except asyncio.TimeoutError:
            logger.warning("Wikidata fetch timeout")
        except Exception as e:
            logger.warning(f"Wikidata fetch error: {e}")
        
        return contents
    
    async def _fetch_arxiv(self, queries: List[str]) -> List[FetchedContent]:
        """Fetch academic papers from ArXiv."""
        contents = []
        
        try:
            session = await self._get_session()
            timeout = await self._get_timeout(15)
            
            for query in queries[:1]:  # Limit ArXiv queries
                url = (
                    f"http://export.arxiv.org/api/query?"
                    f"search_query=all:{quote_plus(query)}&start=0&max_results=3"
                )
                
                async with session.get(url, timeout=timeout) as resp:
                    if resp.status != 200:
                        continue
                    text = await resp.text()
                
                # Parse Atom feed
                entries = re.findall(r'<entry>(.*?)</entry>', text, re.DOTALL)
                
                for entry in entries[:2]:
                    title_match = re.search(r'<title>([^<]+)</title>', entry)
                    summary_match = re.search(r'<summary>([^<]+)</summary>', entry)
                    link_match = re.search(r'<id>([^<]+)</id>', entry)
                    
                    if title_match and summary_match:
                        title = title_match.group(1).strip()
                        summary = summary_match.group(1).strip()
                        link = link_match.group(1).strip() if link_match else ''
                        
                        contents.append(FetchedContent(
                            source='ArXiv',
                            title=title,
                            content=summary,
                            url=link,
                            content_type='academic',
                            reliability_score=0.90,
                        ))
                        
        except asyncio.TimeoutError:
            logger.warning("ArXiv fetch timeout")
        except Exception as e:
            logger.warning(f"ArXiv fetch error: {e}")
        
        return contents
    
    def _parse_wikipedia_sections(self, content: str) -> List[Dict[str, str]]:
        """Parse Wikipedia content into sections."""
        sections = []
        
        # Split by section headers (== Header ==)
        parts = re.split(r'\n(=+\s*[^=]+\s*=+)\n', content)
        
        current_section = {'title': 'Introduction', 'content': ''}
        
        for i, part in enumerate(parts):
            if re.match(r'=+\s*[^=]+\s*=+', part):
                # Save previous section
                if current_section['content'].strip():
                    sections.append(current_section)
                # Start new section
                title = re.sub(r'=+\s*|\s*=+', '', part).strip()
                current_section = {'title': title, 'content': ''}
            else:
                current_section['content'] += part
        
        # Add last section
        if current_section['content'].strip():
            sections.append(current_section)
        
        return sections
    
    def _extract_key_points(self, content: str, topic_keywords: List[str] = None) -> List[str]:
        """Extract key points from content, filtering for relevance."""
        points = []
        
        # Get first meaningful sentences
        sentences = re.split(r'(?<=[.!?])\s+', content)
        
        # If we have topic keywords, prioritize sentences that contain them
        if topic_keywords:
            topic_keywords_lower = [kw.lower() for kw in topic_keywords]
            # First pass: get sentences with topic keywords
            for sentence in sentences[:15]:
                sentence = sentence.strip()
                sentence_lower = sentence.lower()
                # Check if sentence contains any topic keyword
                if len(sentence) > 50 and not sentence.startswith('See also'):
                    if any(kw in sentence_lower for kw in topic_keywords_lower):
                        points.append(sentence)
                        if len(points) >= 5:
                            break
        
        # Fallback to first meaningful sentences if no topic matches
        if len(points) < 3:
            for sentence in sentences[:10]:
                sentence = sentence.strip()
                if len(sentence) > 50 and not sentence.startswith('See also'):
                    if sentence not in points:
                        points.append(sentence)
                        if len(points) >= 5:
                            break
        
        return points
    
    def _extract_topic_keywords(self, queries: List[str]) -> List[str]:
        """Extract important topic keywords from search queries."""
        # Common stop words to exclude
        stopwords = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'to', 'of', 'in', 'for',
            'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during',
            'what', 'why', 'how', 'when', 'where', 'which', 'who', 'whom',
            'this', 'that', 'these', 'those', 'it', 'its', 'and', 'or', 'but',
            'process', 'steps', 'guide', 'tutorial', 'definition', 'explained',
            'reasons', 'causes', 'physics', 'mechanism', 'principle', 'working'
        }
        
        keywords = []
        for query in queries:
            words = re.findall(r'\b[a-zA-Z]+\b', query.lower())
            for word in words:
                if len(word) > 2 and word not in stopwords and word not in keywords:
                    keywords.append(word)
        
        return keywords[:10]  # Limit to 10 keywords
    
    def _is_content_relevant(self, content: str, topic_keywords: List[str], threshold: float = 0.3) -> bool:
        """Check if content is relevant to the topic keywords."""
        if not topic_keywords:
            return True
        
        content_lower = content.lower()
        content_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', content_lower))
        
        # Check what fraction of topic keywords appear in the content
        matches = sum(1 for kw in topic_keywords if kw in content_lower or kw in content_words)
        relevance = matches / len(topic_keywords) if topic_keywords else 0
        
        # Also check that the first 500 chars contain at least one keyword
        first_part = content_lower[:500]
        has_early_match = any(kw in first_part for kw in topic_keywords)
        
        return relevance >= threshold and has_early_match
    
    def _extract_wikidata_facts(self, claims: Dict) -> List[str]:
        """Extract readable facts from Wikidata claims."""
        facts = []
        
        # Property labels (simplified)
        property_labels = {
            'P31': 'is a',
            'P279': 'subclass of',
            'P569': 'born',
            'P570': 'died',
            'P27': 'citizenship',
            'P106': 'occupation',
            'P131': 'located in',
            'P17': 'country',
            'P571': 'founded',
            'P577': 'published',
            'P580': 'start date',
            'P582': 'end date',
            'P18': 'image',
        }
        
        for prop_id, values in claims.items():
            if prop_id in property_labels and values:
                label = property_labels[prop_id]
                for value in values[:2]:  # Limit values
                    mainsnak = value.get('mainsnak', {})
                    datavalue = mainsnak.get('datavalue', {})
                    
                    if datavalue.get('type') == 'time':
                        time_val = datavalue.get('value', {}).get('time', '')
                        if time_val:
                            # Parse date
                            date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', time_val)
                            if date_match:
                                facts.append(f"{label}: {date_match.group(0)}")
                    elif datavalue.get('type') == 'wikibase-entityid':
                        # Would need another API call to resolve - skip for now
                        pass
        
        return facts
    
    def _aggregate_knowledge(
        self,
        query: str,
        contents: List[FetchedContent]
    ) -> AggregatedKnowledge:
        """Aggregate and analyze all fetched content."""
        
        # Extract main facts from high-reliability sources
        main_facts = []
        seen_facts = set()
        
        for content in contents:
            if content.reliability_score >= 0.8:
                for point in content.key_points[:3]:
                    point_lower = point.lower()[:50]
                    if point_lower not in seen_facts:
                        seen_facts.add(point_lower)
                        main_facts.append(point)
        
        # Identify different perspectives (from discussions)
        perspectives = []
        for content in contents:
            if content.content_type == 'discussion':
                perspectives.append({
                    'source': content.source,
                    'viewpoint': content.content[:300],
                })
        
        # Find consensus points (mentioned in multiple sources)
        word_freq: Dict[str, int] = {}
        for content in contents:
            words = set(re.findall(r'\b[a-zA-Z]{4,}\b', content.content.lower()))
            for word in words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Words appearing in 3+ sources indicate consensus topics
        consensus_words = [w for w, c in word_freq.items() if c >= 3]
        
        # Build consensus points from key points containing consensus words
        consensus_points = []
        for content in contents:
            for point in content.key_points:
                if any(cw in point.lower() for cw in consensus_words[:10]):
                    if point not in consensus_points:
                        consensus_points.append(point)
                        if len(consensus_points) >= 5:
                            break
            if len(consensus_points) >= 5:
                break
        
        # Extract timeline if temporal content exists
        timeline = []
        date_pattern = r'\b(\d{4}|\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4})\b'
        for content in contents:
            dates = re.findall(date_pattern, content.content)
            for date in dates[:2]:
                # Find sentence containing the date
                for sentence in content.content.split('.'):
                    if date in sentence:
                        timeline.append({
                            'date': date,
                            'event': sentence.strip()[:150],
                        })
                        break
        
        # Sort timeline by date if possible
        timeline = timeline[:5]
        
        return AggregatedKnowledge(
            query=query,
            total_sources=len(contents),
            total_words=sum(c.word_count for c in contents),
            contents=contents,
            main_facts=main_facts[:10],
            different_perspectives=perspectives[:3],
            consensus_points=consensus_points[:5],
            debate_points=[],  # Would need more sophisticated analysis
            timeline=timeline,
            retrieval_time=0,  # Set by caller
        )


# Singleton instance
_fetcher: Optional[KnowledgeFetcher] = None


def get_fetcher() -> KnowledgeFetcher:
    """Get the global knowledge fetcher."""
    global _fetcher
    if _fetcher is None:
        _fetcher = KnowledgeFetcher()
    return _fetcher


async def fetch_knowledge(
    queries: List[str],
    question_type: str = "what",
    max_sources: int = 10,
) -> AggregatedKnowledge:
    """
    Convenience function to fetch comprehensive knowledge.
    
    Usage:
        knowledge = await fetch_knowledge(
            ["machine learning", "how ML works"],
            question_type="how"
        )
    """
    fetcher = get_fetcher()
    return await fetcher.fetch_comprehensive(
        queries=queries,
        question_type=question_type,
        max_sources=max_sources,
        include_discussions=True,
    )
