"""Quick test for knowledge engine."""
import asyncio
import aiohttp

HEADERS = {
    'User-Agent': 'VoxMind/2.0 (Knowledge Assistant; https://github.com/voxmind)',
    'Accept': 'application/json'
}

async def test_wikipedia():
    print("Testing Wikipedia API...")
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/Machine_learning"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=HEADERS, timeout=10) as resp:
                print(f"Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    title = data.get('title', 'N/A')
                    extract = data.get('extract', '')
                    print(f"Title: {title}")
                    print(f"Extract: {extract[:200]}...")
                else:
                    text = await resp.text()
                    print(f"Error: {text[:200]}")
    except Exception as e:
        print(f"Exception: {e}")

async def test_duckduckgo():
    print("\nTesting DuckDuckGo API...")
    url = "https://api.duckduckgo.com/?q=machine+learning&format=json&no_html=1"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                print(f"Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    abstract = data.get('Abstract', '')
                    heading = data.get('Heading', '')
                    print(f"Heading: {heading}")
                    print(f"Abstract: {abstract[:200]}...")
    except Exception as e:
        print(f"Exception: {e}")

async def test_knowledge_engine():
    print("\nTesting Knowledge Engine...")
    from core.knowledge_engine import KnowledgeEngine
    
    engine = KnowledgeEngine()
    response = await engine.query("machine learning", detail_level="brief")
    
    print(f"Summary: {response.summary[:200]}...")
    print(f"Sources: {response.source_count}")
    print(f"Confidence: {response.confidence:.0%}")

async def main():
    await test_wikipedia()
    await test_duckduckgo()
    await test_knowledge_engine()

if __name__ == "__main__":
    asyncio.run(main())
